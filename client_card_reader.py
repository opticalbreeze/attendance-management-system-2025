#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
クライアント側ICカードリーダー - サーバー送信機能付き
打刻データをサーバーに送信し、失敗時はローカルキャッシュに保存
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


def get_mac_address():
    """端末のMACアドレスを取得"""
    import uuid
    mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
    return ":".join([mac[i:i+2] for i in range(0, 12, 2)]).upper()


class LocalCache:
    """ローカルキャッシュ管理（送信失敗時のデータ保存）"""
    
    def __init__(self, db_path="local_cache.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """データベース初期化"""
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
        """レコードを保存"""
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
        """未送信レコードを取得（10分以上経過したもの）"""
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
        """送信成功したレコードを削除"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_records WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
    
    def increment_retry_count(self, record_id):
        """リトライカウントを増やす"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pending_records 
            SET retry_count = retry_count + 1 
            WHERE id = ?
        """, (record_id,))
        conn.commit()
        conn.close()


class AttendanceClient:
    """打刻クライアント"""
    
    def __init__(self, server_url):
        self.server_url = server_url
        self.terminal_id = get_mac_address()
        self.cache = LocalCache()
        self.card_count = 0
        self.card_history = {}  # {card_id: last_seen_time}
        self.lock = threading.Lock()
        self.reader_threads = []
        
        # リトライスレッド開始
        self.running = True
        self.retry_thread = threading.Thread(target=self.retry_pending_records, daemon=True)
        self.retry_thread.start()
    
    def send_to_server(self, idm, timestamp):
        """サーバーにデータを送信"""
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
                    print(f"[送信成功] サーバーレスポンス: {result.get('message')}")
                    return True
                else:
                    print(f"[送信失敗] サーバーエラー: {result.get('message')}")
                    return False
            else:
                print(f"[送信失敗] HTTPステータス: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"[送信失敗] サーバーに接続できません: {self.server_url}")
            return False
        except requests.exceptions.Timeout:
            print(f"[送信失敗] タイムアウト")
            return False
        except Exception as e:
            print(f"[送信失敗] エラー: {e}")
            return False
    
    def process_card(self, card_id, reader_index):
        """カードを処理（送信 or ローカル保存）- スレッドセーフ"""
        with self.lock:
            timestamp = datetime.now().isoformat()
            
            if self.send_to_server(card_id, timestamp):
                # 送信成功
                return True
            else:
                # 送信失敗 → ローカルに保存
                self.cache.save_record(card_id, timestamp, self.terminal_id)
                return False
    
    def retry_pending_records(self):
        """10分ごとに未送信レコードを再送信"""
        while self.running:
            time.sleep(600)  # 10分待機
            
            records = self.cache.get_pending_records()
            if records:
                print(f"\n[リトライ] {len(records)}件の未送信データを再送信します")
                
                for record in records:
                    record_id, idm, timestamp, terminal_id, retry_count = record
                    
                    if self.send_to_server(idm, timestamp):
                        self.cache.delete_record(record_id)
                        print(f"[リトライ成功] IDm: {idm}")
                    else:
                        self.cache.increment_retry_count(record_id)
                        print(f"[リトライ失敗] IDm: {idm} (試行回数: {retry_count + 1})")
    
    def get_reader_commands(self, reader_name):
        """リーダー種別に応じたコマンドセットを取得"""
        reader_upper = reader_name.upper()
        
        if any(keyword in reader_upper for keyword in ['SONY', 'RC-S', 'PASORI']):
            return [
                [0xFF, 0xCA, 0x00, 0x00, 0x00],
                [0xFF, 0xCA, 0x00, 0x00, 0x04],
                [0xFF, 0xCA, 0x00, 0x00, 0x07],
                [0xFF, 0xB0, 0x00, 0x00, 0x09, 0x06, 0x00, 0xFF, 0xFF, 0x01, 0x00],
                [0xFF, 0xCA, 0x01, 0x00, 0x00],
            ]
        elif any(keyword in reader_upper for keyword in ['CIRCLE', 'CIR315']):
            return [
                [0xFF, 0xCA, 0x00, 0x00, 0x00],
                [0xFF, 0xCA, 0x00, 0x00, 0x04],
                [0xFF, 0xCA, 0x01, 0x00, 0x00],
                [0xFF, 0xB0, 0x00, 0x00, 0x09, 0x06, 0x00, 0xFF, 0xFF, 0x01, 0x00],
            ]
        else:
            return [
                [0xFF, 0xCA, 0x00, 0x00, 0x00],
                [0xFF, 0xCA, 0x00, 0x00, 0x04],
                [0xFF, 0xCA, 0x00, 0x00, 0x07],
                [0xFF, 0xCA, 0x01, 0x00, 0x00],
            ]
    
    def read_card_id(self, connection, reader_name):
        """カードID読み取り"""
        commands = self.get_reader_commands(reader_name)
        
        for cmd in commands:
            try:
                response, sw1, sw2 = connection.transmit(cmd)
                
                if sw1 == 0x90 and sw2 == 0x00 and len(response) >= 4:
                    uid_length = min(len(response), 16)
                    card_id = ''.join([f'{b:02X}' for b in response[:uid_length]])
                    
                    invalid_ids = ["00000000", "FFFFFFFF", "0000000000000000"]
                    if card_id and card_id not in invalid_ids and len(card_id) >= 8:
                        return card_id
            except Exception:
                continue
        
        return None
    
    def monitor_reader(self, reader, reader_name, reader_index):
        """個別リーダーを監視するスレッド関数"""
        last_id = None
        last_time = 0
        
        while self.running:
            try:
                connection = reader.createConnection()
                connection.connect()
                
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
                        print(f"[{timestamp}] [カード#{self.card_count}]")
                        print(f"             IDm: {card_id}")
                        print(f"             リーダー{reader_index}")
                    
                    # サーバーに送信（ロック外で実行）
                    self.process_card(card_id, reader_index)
                    print()
                    
                    last_id = card_id
                    last_time = current_time
                
                connection.disconnect()
                
            except (CardConnectionException, NoCardException):
                if time.time() - last_time > 2:
                    last_id = None
            
            except Exception as e:
                # エラーは静かに処理（複数スレッドで表示が混乱しないように）
                pass
            
            time.sleep(0.3)
    
    def run(self):
        """メイン処理 - マルチスレッド対応"""
        print("="*70)
        print("[打刻システム - クライアント (マルチリーダー対応)]")
        print("="*70)
        print(f"端末ID: {self.terminal_id}")
        print(f"サーバー: {self.server_url}")
        print()
        
        # リーダー検出
        try:
            reader_list = readers()
            if not reader_list:
                print("[エラー] カードリーダーが見つかりません")
                return
            
            print(f"[OK] 検出されたリーダー数: {len(reader_list)}")
            print()
            
            # 検出されたリーダーを表示
            for i, reader in enumerate(reader_list, 1):
                reader_name = str(reader)
                print(f"リーダー{i}: {reader_name}")
            
        except Exception as e:
            print(f"[エラー] リーダー検出失敗: {e}")
            return
        
        # 使用モードの表示
        if len(reader_list) == 1:
            print(f"\n[モード] シングルリーダーモード")
        else:
            print(f"\n[モード] マルチリーダーモード: {len(reader_list)}台のリーダーを並列監視")
        
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
                print(f"[OK] リーダー{i}の監視を開始しました")
            
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
            
            print(f"\n[統計] 読み取り統計:")
            print(f"   合計送信数: {self.card_count} 枚")
            print(f"   使用リーダー数: {len(reader_list)} 台")
            print(f"   ユニークカード数: {len(self.card_history)} 枚")
            print(f"\n[終了] 終了しました\n")


def load_config():
    """設定ファイルを読み込み"""
    config_file = "client_config.json"
    default_config = {
        "server_url": "http://192.168.1.31:5000"
    }
    
    if Path(config_file).exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        return default_config


def main():
    """エントリーポイント"""
    config = load_config()
    server_url = config.get('server_url', 'http://192.168.1.31:5000')
    
    client = AttendanceClient(server_url)
    client.run()


if __name__ == "__main__":
    main()

