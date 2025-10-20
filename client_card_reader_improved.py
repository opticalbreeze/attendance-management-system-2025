#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
クライアント側ICカードリーダー（改善版・CUI版）
- PC/SC対応リーダー専用
- MACアドレスベースの端末ID自動取得
- マルチリーダー対応
- サーバー送信機能 + ローカルキャッシュ
- 自動リトライ機能
"""

import time
import sys
import json
import sqlite3
import uuid
import requests
from datetime import datetime, timedelta
from pathlib import Path
import threading

try:
    from smartcard.System import readers
    from smartcard.Exceptions import CardConnectionException, NoCardException
except ImportError:
    print("[エラー] pyscardがインストールされていません。")
    print("pip install pyscard requests を実行してください。")
    sys.exit(1)


# ============================================================================
# ユーティリティ関数
# ============================================================================

def get_mac_address():
    """
    端末のMACアドレスを取得
    
    Returns:
        str: MACアドレス（例: "AA:BB:CC:DD:EE:FF"）
    """
    mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
    return ":".join([mac[i:i+2] for i in range(0, 12, 2)]).upper()


# ============================================================================
# ローカルキャッシュクラス
# ============================================================================

class LocalCache:
    """
    ローカルキャッシュ管理（送信失敗時のデータ保存）
    SQLiteを使用して未送信データを保持し、定期的に再送信を試みる
    """
    
    def __init__(self, db_path="local_cache.db"):
        """
        Args:
            db_path (str): データベースファイルのパス
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """データベースの初期化（テーブル作成）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idm TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                terminal_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
    
    def save_record(self, idm, timestamp, terminal_id):
        """
        レコードを保存
        
        Args:
            idm (str): カードID
            timestamp (str): タイムスタンプ（ISO8601形式）
            terminal_id (str): 端末ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pending_records (idm, timestamp, terminal_id, created_at)
            VALUES (?, ?, ?, ?)
        """, (idm, timestamp, terminal_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        print(f"[ローカル保存] IDm: {idm}")
    
    def get_pending_records(self):
        """
        未送信レコードを取得（10分以上経過したもの）
        
        Returns:
            list: (id, idm, timestamp, terminal_id, retry_count) のタプルのリスト
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        ten_minutes_ago = (datetime.now() - timedelta(minutes=10)).isoformat()
        cursor.execute("""
            SELECT id, idm, timestamp, terminal_id, retry_count
            FROM pending_records
            WHERE created_at <= ?
            ORDER BY created_at ASC
        """, (ten_minutes_ago,))
        records = cursor.fetchall()
        conn.close()
        return records
    
    def delete_record(self, record_id):
        """
        送信成功したレコードを削除
        
        Args:
            record_id (int): レコードID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_records WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
    
    def increment_retry_count(self, record_id):
        """
        リトライカウントを増やす
        
        Args:
            record_id (int): レコードID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pending_records 
            SET retry_count = retry_count + 1 
            WHERE id = ?
        """, (record_id,))
        conn.commit()
        conn.close()


# ============================================================================
# 打刻クライアントクラス
# ============================================================================

class AttendanceClient:
    """
    打刻クライアント（CUI版）
    ICカードリーダーからカードを読み取り、サーバーに送信する
    """
    
    def __init__(self, server_url):
        """
        Args:
            server_url (str): サーバーURL
        """
        self.server_url = server_url
        self.terminal_id = get_mac_address()  # MACアドレスを端末IDとして使用
        self.cache = LocalCache()
        self.card_count = 0
        self.card_history = {}  # {card_id: last_seen_time}
        self.lock = threading.Lock()
        self.reader_threads = []
        
        # リトライスレッド開始
        self.running = True
        self.retry_thread = threading.Thread(target=self.retry_pending_records, daemon=True)
        self.retry_thread.start()
    
    # ========================================================================
    # サーバー通信
    # ========================================================================
    
    def send_to_server(self, idm, timestamp):
        """
        サーバーにデータを送信
        
        Args:
            idm (str): カードID
            timestamp (str): タイムスタンプ（ISO8601形式）
        
        Returns:
            bool: 送信成功したかどうか
        """
        data = {
            'idm': idm,
            'timestamp': timestamp,
            'terminal_id': self.terminal_id
        }
        
        try:
            response = requests.post(
                f"{self.server_url}/api/attendance",
                json=data,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    print(f"[送信成功] {result.get('message', 'サーバーに記録')}")
                    return True
                else:
                    print(f"[送信失敗] サーバーエラー: {result.get('message')}")
                    return False
            else:
                print(f"[送信失敗] HTTP {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"[送信失敗] サーバー接続エラー: {self.server_url}")
            return False
        except requests.exceptions.Timeout:
            print(f"[送信失敗] タイムアウト（5秒）")
            return False
        except Exception as e:
            print(f"[送信失敗] 予期しないエラー: {e}")
            return False
    
    def process_card(self, card_id, reader_index):
        """
        カードを処理（サーバー送信またはローカル保存）
        
        Args:
            card_id (str): カードID
            reader_index (int): リーダー番号
        
        Returns:
            bool: 処理成功したかどうか
        """
        timestamp = datetime.now().isoformat()
        
        if self.send_to_server(card_id, timestamp):
            # 送信成功
            return True
        else:
            # 送信失敗 → ローカルに保存
            self.cache.save_record(card_id, timestamp, self.terminal_id)
            return False
    
    def retry_pending_records(self):
        """
        10分ごとに未送信レコードを再送信
        バックグラウンドで動作するデーモンスレッド
        """
        while self.running:
            time.sleep(600)  # 10分待機
            
            records = self.cache.get_pending_records()
            if records:
                print(f"\n[リトライ] {len(records)}件の未送信データを再送信します")
                
                for record in records:
                    record_id, idm, timestamp, terminal_id, retry_count = record
                    
                    if self.send_to_server(idm, timestamp):
                        self.cache.delete_record(record_id)
                        print(f"[リトライ成功] IDm: {idm} (試行回数: {retry_count + 1})")
                    else:
                        self.cache.increment_retry_count(record_id)
                        print(f"[リトライ失敗] IDm: {idm} (試行回数: {retry_count + 1})")
    
    # ========================================================================
    # カードリーダー制御
    # ========================================================================
    
    def get_reader_commands(self, reader_name):
        """
        リーダー種別に応じたAPDUコマンドセットを取得
        
        Args:
            reader_name (str): リーダー名
        
        Returns:
            list: APDUコマンドのリスト（各コマンドはバイトのリスト）
        """
        reader_upper = reader_name.upper()
        
        # Sony/PaSoRi 系（FeliCa対応）
        if any(keyword in reader_upper for keyword in ['SONY', 'RC-S', 'PASORI']):
            return [
                [0xFF, 0xCA, 0x00, 0x00, 0x00],  # UID（可変長）
                [0xFF, 0xCA, 0x00, 0x00, 0x04],  # 4バイト UID
                [0xFF, 0xCA, 0x00, 0x00, 0x07],  # 7バイト UID
                [0xFF, 0xB0, 0x00, 0x00, 0x09, 0x06, 0x00, 0xFF, 0xFF, 0x01, 0x00],  # FeliCa IDm
                [0xFF, 0xCA, 0x01, 0x00, 0x00],  # Get Data
            ]
        
        # Circle CIR315 系
        elif any(keyword in reader_upper for keyword in ['CIRCLE', 'CIR315']):
            return [
                [0xFF, 0xCA, 0x00, 0x00, 0x00],
                [0xFF, 0xCA, 0x00, 0x00, 0x04],
                [0xFF, 0xCA, 0x01, 0x00, 0x00],
                [0xFF, 0xB0, 0x00, 0x00, 0x09, 0x06, 0x00, 0xFF, 0xFF, 0x01, 0x00],
            ]
        
        # 汎用リーダー
        else:
            return [
                [0xFF, 0xCA, 0x00, 0x00, 0x00],  # UID（可変長）
                [0xFF, 0xCA, 0x00, 0x00, 0x04],  # 4バイト UID
                [0xFF, 0xCA, 0x00, 0x00, 0x07],  # 7バイト UID
                [0xFF, 0xCA, 0x01, 0x00, 0x00],  # Get Data
            ]
    
    def read_card_id(self, connection, reader_name):
        """
        カードIDを読み取り
        複数のコマンドを試して、有効なIDを取得
        
        Args:
            connection: smartcard.Connectionオブジェクト
            reader_name (str): リーダー名
        
        Returns:
            str or None: カードID（16進数文字列）、読み取り失敗時はNone
        """
        commands = self.get_reader_commands(reader_name)
        
        for cmd in commands:
            try:
                response, sw1, sw2 = connection.transmit(cmd)
                
                # 成功応答（90 00）かつ有効なデータがある場合
                if sw1 == 0x90 and sw2 == 0x00 and len(response) >= 4:
                    uid_length = min(len(response), 16)
                    card_id = ''.join([f'{b:02X}' for b in response[:uid_length]])
                    
                    # 無効なIDをフィルタリング
                    invalid_ids = ["00000000", "FFFFFFFF", "0000000000000000"]
                    if card_id and card_id not in invalid_ids and len(card_id) >= 8:
                        return card_id
            except Exception:
                # コマンド実行失敗は正常（対応していないコマンド）
                continue
        
        return None
    
    def monitor_reader(self, reader, reader_name, reader_index):
        """
        個別リーダーを監視するスレッド関数
        
        Args:
            reader: smartcard.Readerオブジェクト
            reader_name (str): リーダー名
            reader_index (int): リーダー番号
        """
        last_id = None
        last_time = 0
        
        while self.running:
            try:
                # カードリーダーに接続
                connection = reader.createConnection()
                connection.connect()
                
                # カードID読み取り
                card_id = self.read_card_id(connection, reader_name)
                
                if card_id and card_id != last_id:
                    # 重複チェック（スレッドセーフ）
                    with self.lock:
                        current_time = time.time()
                        
                        # 同じカードが2秒以内に検出された場合はスキップ
                        if card_id in self.card_history:
                            if current_time - self.card_history[card_id] < 2.0:
                                last_id = card_id
                                connection.disconnect()
                                time.sleep(0.3)
                                continue
                        
                        # カード情報を記録
                        self.card_history[card_id] = current_time
                        self.card_count += 1
                        
                        # カード情報を表示
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(f"\n[{timestamp}] [カード#{self.card_count}]")
                        print(f"             IDm: {card_id}")
                        print(f"             リーダー{reader_index}")
                    
                    # サーバーに送信（ロック外で実行）
                    self.process_card(card_id, reader_index)
                    
                    last_id = card_id
                    last_time = current_time
                
                connection.disconnect()
                
            except (CardConnectionException, NoCardException):
                # カードなし、接続エラーは正常な状態
                if time.time() - last_time > 2:
                    last_id = None
            
            except Exception:
                # その他のエラーは無視（複数スレッドで表示が混乱しないように）
                pass
            
            time.sleep(0.3)
    
    # ========================================================================
    # メイン処理
    # ========================================================================
    
    def run(self):
        """
        メイン処理 - マルチリーダー対応
        リーダーを検出し、各リーダーで監視スレッドを起動
        """
        print("="*70)
        print("[打刻システム - クライアント（改善版・マルチリーダー対応）]")
        print("="*70)
        print(f"端末ID: {self.terminal_id}")
        print(f"サーバー: {self.server_url}")
        print()
        
        # リーダー検出
        try:
            reader_list = readers()
            if not reader_list:
                print("[エラー] カードリーダーが見つかりません")
                print("[ヒント] リーダーを接続してプログラムを再起動してください")
                return
            
            print(f"[検出] {len(reader_list)}台のリーダーを検出しました")
            print()
            
            # 検出されたリーダーを表示
            for i, reader in enumerate(reader_list, 1):
                reader_name = str(reader)
                print(f"  リーダー{i}: {reader_name}")
            
        except Exception as e:
            print(f"[エラー] リーダー検出失敗: {e}")
            return
        
        # 使用モードの表示
        if len(reader_list) == 1:
            print(f"\n[モード] シングルリーダーモード")
        else:
            print(f"\n[モード] マルチリーダーモード（{len(reader_list)}台のリーダーを並列監視）")
        
        print(f"\n[操作] カードをかざしてください... (Ctrl+C で終了)")
        print(f"[注意] 複数リーダーで同じカードを検出した場合、2秒間は重複送信を抑制します")
        print()
        
        try:
            # 全てのリーダーでスレッドを起動
            for i, reader in enumerate(reader_list, 1):
                reader_name = str(reader)
                thread = threading.Thread(
                    target=self.monitor_reader,
                    args=(reader, reader_name, i),
                    daemon=True,
                    name=f"Reader-{i}"
                )
                thread.start()
                self.reader_threads.append(thread)
                print(f"[起動] リーダー{i}の監視を開始")
            
            print("\n" + "="*70)
            print("[開始] 全リーダーの監視を開始しました")
            print("="*70 + "\n")
            
            # メインスレッドは待機
            while self.running:
                time.sleep(0.5)
        
        except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("[終了] プログラムを終了します...")
            print("="*70)
            
            # スレッドを停止
            self.running = False
            
            # 全スレッドの終了を待つ
            for thread in self.reader_threads:
                thread.join(timeout=2)
            
            # 統計情報を表示
            print(f"\n[統計] 読み取り統計:")
            print(f"   合計読み取り数: {self.card_count} 枚")
            print(f"   使用リーダー数: {len(reader_list)} 台")
            print(f"   ユニークカード数: {len(self.card_history)} 枚")
            print(f"\n[終了] 終了しました\n")


# ============================================================================
# 設定ファイル管理
# ============================================================================

def load_config():
    """
    設定ファイルを読み込み
    ファイルが存在しない場合はデフォルト設定で作成
    
    Returns:
        dict: 設定辞書
    """
    config_file = "client_config.json"
    default_config = {
        "server_url": "http://192.168.1.31:5000"
    }
    
    config_path = Path(config_file)
    
    if config_path.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[警告] 設定ファイル読み込みエラー: {e}")
            print("[情報] デフォルト設定を使用します")
            return default_config
    else:
        # 設定ファイルを作成
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        print(f"[情報] 設定ファイルを作成しました: {config_file}")
        return default_config


# ============================================================================
# エントリーポイント
# ============================================================================

def main():
    """メイン関数"""
    print("="*70)
    print("打刻システム - クライアント（改善版・CUI版）")
    print("="*70)
    print()
    
    # 設定読み込み
    config = load_config()
    server_url = config.get('server_url', 'http://192.168.1.31:5000')
    
    print(f"サーバーURL: {server_url}")
    print(f"端末ID: {get_mac_address()}")
    print("="*70)
    print()
    
    # クライアント起動
    try:
        client = AttendanceClient(server_url)
        client.run()
    except KeyboardInterrupt:
        print("\n[終了] プログラムを終了します")
    except Exception as e:
        print(f"[エラー] 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

