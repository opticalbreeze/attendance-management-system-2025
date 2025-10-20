#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ラズパイ統合版クライアント（改善版）
- LCD I2C 1602対応
- GPIO制御（LED + ブザー）
- nfcpy + PC/SC両対応
- MACアドレスベースの端末ID自動取得
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

# ============================================================================
# ライブラリ依存関係の確認
# ============================================================================

# LCD制御
try:
    from lcd_i2c import LCD_I2C
    LCD_AVAILABLE = True
except ImportError:
    LCD_AVAILABLE = False
    print("[警告] LCD機能無効 - lcd_i2c.pyが見つかりません")

# GPIO制御
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("[警告] GPIO機能無効 - Raspberry Pi以外の環境")

# nfcpy（Sony RC-S380など）
try:
    import nfc
    NFCPY_AVAILABLE = True
except ImportError:
    NFCPY_AVAILABLE = False
    print("[情報] nfcpy未インストール - PC/SCのみで動作")

# pyscard（PC/SC対応リーダー）
try:
    from smartcard.System import readers as pcsc_readers
    from smartcard.Exceptions import CardConnectionException, NoCardException
    PYSCARD_AVAILABLE = True
except ImportError:
    PYSCARD_AVAILABLE = False
    print("[情報] pyscard未インストール - nfcpyのみで動作")

# GPIO設定をインポート
try:
    from gpio_config import *
except ImportError:
    # デフォルト設定
    BUZZER_PIN = 18
    LED_RED_PIN, LED_GREEN_PIN, LED_BLUE_PIN = 13, 19, 26
    BUZZER_PATTERNS = {
        "startup": [(0.2, 1000), (0.1, 1000), (0.2, 1000)],
        "connect": [(0.1, 1500), (0.1, 1500), (0.1, 1500)],
        "card_read": [(0.05, 2000)],
        "success": [(0.1, 2500), (0.05, 2500), (0.1, 2500)],
        "failure": [(0.3, 800), (0.1, 800), (0.3, 800)]
    }
    LED_COLORS = {
        "off": (0, 0, 0),
        "red": (100, 0, 0),
        "green": (0, 100, 0),
        "blue": (0, 0, 100),
        "orange": (100, 50, 0)
    }


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
# GPIO制御クラス
# ============================================================================

class GPIO_Control:
    """
    GPIO制御（LED + ブザー）
    Raspberry Pi上でLEDとブザーを制御
    """
    
    def __init__(self):
        """GPIO初期化"""
        self.available = GPIO_AVAILABLE
        self.blink_running = False
        
        if not self.available:
            return
        
        try:
            # GPIO設定
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(BUZZER_PIN, GPIO.OUT)
            GPIO.setup([LED_RED_PIN, LED_GREEN_PIN, LED_BLUE_PIN], GPIO.OUT)
            
            # PWM設定（LED用）
            self.pwms = [
                GPIO.PWM(LED_RED_PIN, 1000),
                GPIO.PWM(LED_GREEN_PIN, 1000),
                GPIO.PWM(LED_BLUE_PIN, 1000)
            ]
            for pwm in self.pwms:
                pwm.start(0)
        except Exception as e:
            print(f"[警告] GPIO初期化失敗: {e}")
            self.available = False
    
    def sound(self, pattern):
        """
        ブザーを鳴らす
        
        Args:
            pattern (str): 音パターン名（"startup", "card_read", "success", "failure"など）
        """
        if not self.available:
            return
        
        for duration, freq in BUZZER_PATTERNS.get(pattern, [(0.1, 1000)]):
            try:
                pwm = GPIO.PWM(BUZZER_PIN, freq)
                pwm.start(50)  # デューティ比50%
                time.sleep(duration)
                pwm.stop()
                time.sleep(0.05)
            except Exception:
                pass
    
    def led(self, color):
        """
        LEDの色を設定
        
        Args:
            color (str): 色名（"off", "red", "green", "blue", "orange"など）
        """
        if not self.available:
            return
        
        self.stop_blink()
        r, g, b = LED_COLORS.get(color, (0, 0, 0))
        try:
            self.pwms[0].ChangeDutyCycle(r)
            self.pwms[1].ChangeDutyCycle(g)
            self.pwms[2].ChangeDutyCycle(b)
        except Exception:
            pass
    
    def blink_orange(self):
        """
        オレンジ色で点滅（サーバー接続エラー時など）
        バックグラウンドスレッドで実行
        """
        if not self.available:
            return
        
        self.stop_blink()
        self.blink_running = True
        
        def worker():
            while self.blink_running:
                self.led("orange")
                time.sleep(0.5)
                self.led("off")
                time.sleep(0.5)
        
        threading.Thread(target=worker, daemon=True).start()
    
    def stop_blink(self):
        """点滅を停止"""
        self.blink_running = False
        time.sleep(0.1)
    
    def cleanup(self):
        """GPIOのクリーンアップ（終了時に呼び出し）"""
        if not self.available:
            return
        
        try:
            self.stop_blink()
            for pwm in self.pwms:
                pwm.stop()
            GPIO.cleanup()
        except Exception:
            pass


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
# 統合版クライアントクラス
# ============================================================================

class UnifiedClient:
    """
    ラズパイ統合版クライアント
    LCD + GPIO + nfcpy/PC/SC全てに対応
    """
    
    def __init__(self, server_url):
        """
        Args:
            server_url (str): サーバーURL
        """
        self.server_url = server_url
        self.terminal_id = get_mac_address()  # MACアドレスを端末IDとして使用
        self.cache = LocalCache()
        self.gpio = GPIO_Control()
        self.lcd = LCD_I2C() if LCD_AVAILABLE else None
        self.count = 0
        self.history = {}  # {card_id: last_seen_time}
        self.lock = threading.Lock()
        self.running = True
        self.server_connected = False
        self.current_message = "カード ヲ タッチ"
        
        # 起動処理
        self.gpio.sound("startup")
        self.gpio.led("red")
        if self.lcd:
            self.lcd.show_with_time("キドウチュウ...")
        
        # バックグラウンドスレッド開始
        threading.Thread(target=self.monitor_server, daemon=True).start()
        threading.Thread(target=self.retry_pending_records, daemon=True).start()
        threading.Thread(target=self.update_lcd_time, daemon=True).start()
    
    # ========================================================================
    # サーバー監視
    # ========================================================================
    
    def monitor_server(self):
        """
        サーバーの接続状態を定期的に監視
        1時間ごとにヘルスチェックを実行
        """
        retry_count = 0
        max_retries = 2
        
        while self.running:
            try:
                response = requests.get(f"{self.server_url}/api/health", timeout=5)
                if response.status_code == 200:
                    self.server_connected = True
                    
                    if retry_count > 0:
                        # 再接続成功
                        print("[サーバー] 再接続成功")
                        if self.lcd:
                            self.lcd.show_with_time("サーバー セツゾクOK")
                            time.sleep(2)
                        self.gpio.sound("connect")
                    else:
                        # 初回接続成功
                        if self.lcd:
                            self.lcd.show_with_time("サーバー カクニンズミ")
                            time.sleep(2)
                            self.lcd.show_with_time("カード ヲ タッチ")
                        self.gpio.sound("connect")
                    
                    self.gpio.led("green")
                    retry_count = 0
                else:
                    raise Exception(f"Server response error: {response.status_code}")
            
            except requests.exceptions.ConnectionError:
                self.server_connected = False
                
                if retry_count < max_retries:
                    retry_count += 1
                    print(f"[サーバー] 再接続試行 {retry_count}/{max_retries}")
                    if self.lcd:
                        self.lcd.show_with_time(f"サイセツゾク{retry_count}/{max_retries}")
                    
                    time.sleep(5)
                    continue
                else:
                    if retry_count == max_retries:
                        print("[サーバー] 再接続失敗 - 1時間後に再試行")
                        if self.lcd:
                            self.lcd.show_with_time("サーバー セツゾクNG")
                        self.gpio.blink_orange()
                        retry_count += 1
            
            except Exception as e:
                print(f"[サーバー] エラー: {e}")
                self.server_connected = False
            
            time.sleep(3600)  # 1時間待機
    
    # ========================================================================
    # LCD制御
    # ========================================================================
    
    def update_lcd_time(self):
        """
        LCDに時刻を定期的に更新表示
        2秒ごとに更新
        """
        if not self.lcd:
            return
        
        while self.running:
            try:
                self.lcd.show_with_time(self.current_message)
            except Exception:
                pass
            time.sleep(2)
    
    def set_lcd_message(self, message, duration=0):
        """
        LCDのメッセージを設定
        
        Args:
            message (str): 表示するメッセージ
            duration (int): 表示時間（秒）。0の場合は自動で戻らない
        """
        self.current_message = message
        if self.lcd:
            try:
                self.lcd.show_with_time(message)
            except Exception:
                pass
        
        if duration > 0:
            def reset():
                time.sleep(duration)
                self.current_message = "カード ヲ タッチ"
            threading.Thread(target=reset, daemon=True).start()
    
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
                    self.set_lcd_message("サーバー ニ キロク", 1)
                    self.gpio.sound("success")
                    self.gpio.led("blue")
                    return True
                else:
                    print(f"[送信失敗] サーバーエラー: {result.get('message')}")
                    self.set_lcd_message("ローカル ニ キロク", 1)
                    self.gpio.sound("failure")
                    self.gpio.led("orange")
                    return False
            else:
                print(f"[送信失敗] HTTP {response.status_code}")
                self.set_lcd_message("ローカル ニ キロク", 1)
                self.gpio.sound("failure")
                self.gpio.led("orange")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"[送信失敗] サーバー接続エラー")
            self.set_lcd_message("ローカル ニ キロク", 1)
            self.gpio.sound("failure")
            self.gpio.led("orange")
            return False
        except requests.exceptions.Timeout:
            print(f"[送信失敗] タイムアウト")
            self.set_lcd_message("ローカル ニ キロク", 1)
            self.gpio.sound("failure")
            self.gpio.led("orange")
            return False
        except Exception as e:
            print(f"[送信失敗] 予期しないエラー: {e}")
            self.set_lcd_message("ローカル ニ キロク", 1)
            self.gpio.sound("failure")
            self.gpio.led("orange")
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
        
        # カード読み込みフィードバック
        self.set_lcd_message("カード ヲ ヨミマシタ", 1)
        self.gpio.sound("card_read")
        self.gpio.led("green")
        
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
    
    def nfcpy_worker(self, path, idx):
        """
        nfcpy用リーダー監視ワーカー
        
        Args:
            path (str): nfcpyデバイスパス（例: 'usb:000'）
            idx (int): リーダー番号
        """
        last_id = None
        clf = None
        
        try:
            # ContactlessFrontendを1回だけ開く（再利用することで高速化）
            clf = nfc.ContactlessFrontend(path)
            if not clf:
                print(f"[エラー] nfcpyリーダー#{idx}を開けません")
                return
            
            while self.running:
                try:
                    # カード検出（短いタイムアウトで高速化）
                    tag = clf.connect(rdwr={
                        'on-connect': lambda tag: False,
                        'beep-on-connect': False
                    }, terminate=lambda: not self.running)
                    
                    if tag:
                        # IDm または identifier を取得
                        card_id = (tag.idm if hasattr(tag, 'idm') else tag.identifier).hex().upper()
                        
                        if card_id and card_id != last_id:
                            now = time.time()
                            # 重複チェック（2秒以内は無視）
                            if card_id not in self.history or now - self.history[card_id] >= 2.0:
                                self.history[card_id] = now
                                self.count += 1
                                
                                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [カード#{self.count}]")
                                print(f"IDm: {card_id} (リーダー{idx})")
                                
                                self.process_card(card_id, idx)
                                last_id = card_id
                
                except IOError:
                    # カードなし - 正常な状態
                    pass
                except Exception:
                    # その他のエラーは無視
                    pass
                
                # 短いスリープで応答性を向上
                time.sleep(0.05)
        
        finally:
            # 終了時にContactlessFrontendをクローズ
            if clf:
                try:
                    clf.close()
                except:
                    pass
    
    def pcsc_worker(self, reader, idx):
        """
        PC/SC用リーダー監視ワーカー
        
        Args:
            reader: smartcard.Readerオブジェクト
            idx (int): リーダー番号
        """
        last_id = None
        
        while self.running:
            try:
                connection = reader.createConnection()
                connection.connect()
                
                # 複数のコマンドを試してカードIDを取得
                card_id = None
                commands = [
                    [0xFF, 0xCA, 0x00, 0x00, 0x00],  # UID（可変長）
                    [0xFF, 0xCA, 0x00, 0x00, 0x04],  # 4バイト UID
                    [0xFF, 0xCA, 0x00, 0x00, 0x07]   # 7バイト UID
                ]
                
                for cmd in commands:
                    try:
                        response, sw1, sw2 = connection.transmit(cmd)
                        # 成功応答（90 00）かつ有効なデータがある場合
                        if sw1 == 0x90 and sw2 == 0x00 and len(response) >= 4:
                            uid_len = min(len(response), 16)
                            card_id = ''.join([f'{b:02X}' for b in response[:uid_len]])
                            if len(card_id) >= 8:
                                break
                    except Exception:
                        continue
                
                if card_id and card_id != last_id:
                    now = time.time()
                    # 重複チェック（2秒以内は無視）
                    if card_id not in self.history or now - self.history[card_id] >= 2.0:
                        self.history[card_id] = now
                        self.count += 1
                        
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [カード#{self.count}]")
                        print(f"IDm: {card_id} (リーダー{idx})")
                        
                        self.process_card(card_id, idx)
                        last_id = card_id
                
                connection.disconnect()
            except (CardConnectionException, NoCardException):
                # カードなし、接続エラーは正常な状態
                pass
            except Exception:
                # その他のエラーは無視
                pass
            
            time.sleep(0.3)
    
    # ========================================================================
    # メイン処理
    # ========================================================================
    
    def run(self):
        """
        メイン処理
        リーダーを検出し、各リーダーで監視スレッドを起動
        """
        print("="*70)
        print("[ラズパイ統合版クライアント（改善版）- LCD + GPIO + nfcpy/PC/SC]")
        print("="*70)
        print(f"端末ID: {self.terminal_id}")
        print(f"サーバー: {self.server_url}")
        print(f"LCD: {'有効' if LCD_AVAILABLE else '無効'}")
        print(f"GPIO: {'有効' if GPIO_AVAILABLE else '無効'}")
        print(f"nfcpy: {'利用可能' if NFCPY_AVAILABLE else '利用不可'}")
        print(f"pyscard: {'利用可能' if PYSCARD_AVAILABLE else '利用不可'}")
        print()
        
        # リーダー検出
        nfcpy_count = 0
        pcsc_count = 0
        
        # nfcpy検出
        if NFCPY_AVAILABLE:
            for i in range(10):
                try:
                    clf = nfc.ContactlessFrontend(f'usb:{i:03d}')
                    if clf:
                        nfcpy_count += 1
                        clf.close()
                except:
                    break
        
        # PC/SC検出
        if PYSCARD_AVAILABLE:
            try:
                pcsc_count = len(pcsc_readers())
            except:
                pass
        
        # リーダーが見つからない場合
        if nfcpy_count == 0 and pcsc_count == 0:
            print("[エラー] カードリーダーが見つかりません")
            print("[ヒント] リーダーを接続してプログラムを再起動してください")
            if self.lcd:
                self.lcd.show_with_time("リーダー ミツカリマセン")
            self.gpio.led("red")
            return
        
        print(f"[検出] nfcpy:{nfcpy_count}台 / PC/SC:{pcsc_count}台")
        
        # nfcpy リーダーの監視開始
        if nfcpy_count > 0:
            for i in range(nfcpy_count):
                path = f'usb:{i:03d}'
                threading.Thread(
                    target=self.nfcpy_worker, 
                    args=(path, i+1), 
                    daemon=True
                ).start()
                print(f"[起動] nfcpyリーダー#{i+1}の監視を開始")
        
        # PC/SC リーダーの監視開始
        if pcsc_count > 0:
            try:
                reader_list = pcsc_readers()
                for i, reader in enumerate(reader_list, 1):
                    reader_idx = nfcpy_count + i
                    threading.Thread(
                        target=self.pcsc_worker, 
                        args=(reader, reader_idx), 
                        daemon=True
                    ).start()
                    print(f"[起動] PC/SCリーダー#{reader_idx}の監視を開始")
            except Exception as e:
                print(f"[エラー] PC/SCリーダー起動失敗: {e}")
        
        print("\n[待機] カードをかざしてください... (Ctrl+C で終了)\n")
        
        try:
            # メインスレッドは待機
            while self.running:
                time.sleep(0.5)
        
        except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("[終了] プログラムを終了します...")
            print("="*70)
            
            self.running = False
            
            # 統計情報を表示
            print(f"\n[統計] 読み取り統計:")
            print(f"   合計読み取り数: {self.count} 枚")
            print(f"   ユニークカード数: {len(self.history)} 枚")
            print(f"\n[終了] 終了しました\n")
            
            # LCD表示
            if self.lcd:
                self.lcd.show_with_time("シュウリョウシマシタ")
            
            # GPIOクリーンアップ
            self.gpio.cleanup()


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
    print("ラズパイ統合版クライアント（改善版）")
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
        client = UnifiedClient(server_url)
        client.run()
    except KeyboardInterrupt:
        print("\n[終了] プログラムを終了します")
    except Exception as e:
        print(f"[エラー] 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

