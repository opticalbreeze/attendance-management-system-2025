#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ラズパイ統合版クライアント
LCD I2C 1602 + GPIO + nfcpy/PCSC両対応
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

# LCD制御
try:
    from lcd_i2c import LCD_I2C
    LCD_AVAILABLE = True
except:
    LCD_AVAILABLE = False
    print("[警告] LCD機能無効")

# GPIO制御
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except:
    GPIO_AVAILABLE = False
    print("[警告] GPIO機能無効")

# nfcpy
try:
    import nfc
    NFCPY_AVAILABLE = True
except:
    NFCPY_AVAILABLE = False

# pyscard
try:
    from smartcard.System import readers as pcsc_readers
    from smartcard.Exceptions import CardConnectionException, NoCardException
    PYSCARD_AVAILABLE = True
except:
    PYSCARD_AVAILABLE = False

# GPIO設定
try:
    from gpio_config import *
except:
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
        "off": (0, 0, 0), "red": (100, 0, 0), "green": (0, 100, 0),
        "blue": (0, 0, 100), "orange": (100, 50, 0)
    }


def get_mac_address():
    """MACアドレス取得"""
    mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
    return ":".join([mac[i:i+2] for i in range(0, 12, 2)]).upper()


class GPIO_Control:
    """GPIO制御"""
    
    def __init__(self):
        self.available = GPIO_AVAILABLE
        self.blink_running = False
        
        if not self.available:
            return
        
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(BUZZER_PIN, GPIO.OUT)
            GPIO.setup([LED_RED_PIN, LED_GREEN_PIN, LED_BLUE_PIN], GPIO.OUT)
            
            self.pwms = [
                GPIO.PWM(LED_RED_PIN, 1000),
                GPIO.PWM(LED_GREEN_PIN, 1000),
                GPIO.PWM(LED_BLUE_PIN, 1000)
            ]
            for pwm in self.pwms:
                pwm.start(0)
        except:
            self.available = False
    
    def sound(self, pattern):
        """ブザー"""
        if not self.available:
            return
        
        for duration, freq in BUZZER_PATTERNS.get(pattern, [(0.1, 1000)]):
            try:
                pwm = GPIO.PWM(BUZZER_PIN, freq)
                pwm.start(50)
                time.sleep(duration)
                pwm.stop()
                time.sleep(0.05)
            except:
                pass
    
    def led(self, color):
        """LED設定"""
        if not self.available:
            return
        
        self.stop_blink()
        r, g, b = LED_COLORS.get(color, (0, 0, 0))
        try:
            self.pwms[0].ChangeDutyCycle(r)
            self.pwms[1].ChangeDutyCycle(g)
            self.pwms[2].ChangeDutyCycle(b)
        except:
            pass
    
    def blink_orange(self):
        """オレンジ点滅"""
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
        """点滅停止"""
        self.blink_running = False
        time.sleep(0.1)
    
    def cleanup(self):
        """クリーンアップ"""
        if not self.available:
            return
        
        try:
            self.stop_blink()
            for pwm in self.pwms:
                pwm.stop()
            GPIO.cleanup()
        except:
            pass


class LocalCache:
    """ローカルキャッシュ"""
    
    def __init__(self, db_path="local_cache.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_records WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
    
    def increment_retry_count(self, record_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pending_records 
            SET retry_count = retry_count + 1 
            WHERE id = ?
        """, (record_id,))
        conn.commit()
        conn.close()


class UnifiedClient:
    """統合版クライアント"""
    
    def __init__(self, server_url):
        self.server_url = server_url
        self.terminal_id = get_mac_address()
        self.cache = LocalCache()
        self.gpio = GPIO_Control()
        self.lcd = LCD_I2C() if LCD_AVAILABLE else None
        self.count = 0
        self.history = {}
        self.lock = threading.Lock()
        self.running = True
        self.server_connected = False
        self.current_message = "カード ヲ タッチ"
        
        # 起動
        self.gpio.sound("startup")
        self.gpio.led("red")
        if self.lcd:
            self.lcd.show_with_time("キドウチュウ...")
        
        # スレッド開始
        threading.Thread(target=self.monitor_server, daemon=True).start()
        threading.Thread(target=self.retry_pending_records, daemon=True).start()
        threading.Thread(target=self.update_lcd_time, daemon=True).start()
    
    def monitor_server(self):
        """サーバー監視（1時間ごと）"""
        retry_count = 0
        max_retries = 2
        
        while self.running:
            try:
                response = requests.get(f"{self.server_url}/api/health", timeout=5)
                if response.status_code == 200:
                    self.server_connected = True
                    
                    if retry_count > 0:
                        print("[OK] サーバー再接続成功")
                        if self.lcd:
                            self.lcd.show_with_time("サーバー セツゾクOK")
                            time.sleep(2)
                        self.gpio.sound("connect")
                    else:
                        if self.lcd:
                            self.lcd.show_with_time("サーバー カクニンズミ")
                            time.sleep(2)
                            self.lcd.show_with_time("カード ヲ タッチ")
                        self.gpio.sound("connect")
                    
                    self.gpio.led("green")
                    retry_count = 0
                else:
                    raise Exception("Server response error")
            
            except Exception as e:
                self.server_connected = False
                
                if retry_count < max_retries:
                    retry_count += 1
                    print(f"[再接続] 試行 {retry_count}/{max_retries}")
                    if self.lcd:
                        self.lcd.show_with_time(f"サイセツゾク{retry_count}/{max_retries}")
                    
                    time.sleep(5)
                    continue
                else:
                    if retry_count == max_retries:
                        print("[NG] 再接続失敗 - 1時間後に再試行")
                        if self.lcd:
                            self.lcd.show_with_time("サーバー セツゾクNG")
                        self.gpio.blink_orange()
                        retry_count += 1
            
            time.sleep(3600)  # 1時間待機
    
    def update_lcd_time(self):
        """LCD時刻更新"""
        if not self.lcd:
            return
        
        while self.running:
            try:
                self.lcd.show_with_time(self.current_message)
            except:
                pass
            time.sleep(2)
    
    def set_lcd_message(self, message, duration=0):
        """LCDメッセージ設定"""
        self.current_message = message
        if self.lcd:
            try:
                self.lcd.show_with_time(message)
            except:
                pass
        
        if duration > 0:
            def reset():
                time.sleep(duration)
                self.current_message = "カード ヲ タッチ"
            threading.Thread(target=reset, daemon=True).start()
    
    def send_to_server(self, idm, timestamp):
        """サーバー送信"""
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
                    print(f"[送信成功] {result.get('message')}")
                    self.set_lcd_message("サーバー ニ キロク", 1)
                    self.gpio.sound("success")
                    self.gpio.led("blue")
                    return True
                else:
                    print(f"[送信失敗] {result.get('message')}")
                    self.set_lcd_message("ローカル ニ キロク", 1)
                    self.gpio.sound("failure")
                    self.gpio.led("orange")
                    return False
            else:
                print(f"[送信失敗] HTTPステータス: {response.status_code}")
                self.set_lcd_message("ローカル ニ キロク", 1)
                self.gpio.sound("failure")
                self.gpio.led("orange")
                return False
                
        except Exception as e:
            print(f"[送信失敗] {e}")
            self.set_lcd_message("ローカル ニ キロク", 1)
            self.gpio.sound("failure")
            self.gpio.led("orange")
            return False
    
    def process_card(self, card_id, reader_index):
        """カード処理"""
        with self.lock:
            timestamp = datetime.now().isoformat()
            
            # カード読み込み
            self.set_lcd_message("カード ヲ ヨミマシタ", 1)
            self.gpio.sound("card_read")
            self.gpio.led("green")
            
            if self.send_to_server(card_id, timestamp):
                return True
            else:
                self.cache.save_record(card_id, timestamp, self.terminal_id)
                return False
    
    def retry_pending_records(self):
        """リトライワーカー"""
        while self.running:
            time.sleep(600)
            
            records = self.cache.get_pending_records()
            if records:
                print(f"\n[リトライ] {len(records)}件")
                
                for record in records:
                    record_id, idm, timestamp, terminal_id, retry_count = record
                    
                    if self.send_to_server(idm, timestamp):
                        self.cache.delete_record(record_id)
                        print(f"[リトライ成功] {idm}")
                    else:
                        self.cache.increment_retry_count(record_id)
                        print(f"[リトライ失敗] {idm}")
    
    def nfcpy_worker(self, path, idx):
        """nfcpyワーカー（高速化版）"""
        last_id = None
        clf = None
        
        try:
            # ContactlessFrontendを1回だけ開く（再利用で高速化）
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
                        card_id = (tag.idm if hasattr(tag, 'idm') else tag.identifier).hex().upper()
                        
                        if card_id and card_id != last_id:
                            now = time.time()
                            if card_id not in self.history or now - self.history[card_id] >= 2.0:
                                self.history[card_id] = now
                                self.count += 1
                                
                                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] カード#{self.count}")
                                print(f"IDm: {card_id} (リーダー{idx})")
                                
                                self.process_card(card_id, idx)
                                last_id = card_id
                
                except IOError:
                    # カードなし - 正常な状態
                    pass
                except:
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
        """PCSCワーカー"""
        last_id = None
        
        while self.running:
            try:
                connection = reader.createConnection()
                connection.connect()
                
                card_id = None
                for cmd in [[0xFF,0xCA,0,0,0], [0xFF,0xCA,0,0,4], [0xFF,0xCA,0,0,7]]:
                    try:
                        response, sw1, sw2 = connection.transmit(cmd)
                        if sw1 == 0x90 and sw2 == 0x00 and len(response) >= 4:
                            card_id = ''.join([f'{b:02X}' for b in response[:min(len(response),16)]])
                            if len(card_id) >= 8:
                                break
                    except:
                        continue
                
                if card_id and card_id != last_id:
                    now = time.time()
                    if card_id not in self.history or now - self.history[card_id] >= 2.0:
                        self.history[card_id] = now
                        self.count += 1
                        
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] カード#{self.count}")
                        print(f"IDm: {card_id} (リーダー{idx})")
                        
                        self.process_card(card_id, idx)
                        last_id = card_id
                
                connection.disconnect()
            except (CardConnectionException, NoCardException):
                pass
            except:
                pass
            
            time.sleep(0.3)
    
    def run(self):
        """メイン処理"""
        print("="*70)
        print("[ラズパイ統合版クライアント - LCD + GPIO + nfcpy/PCSC]")
        print("="*70)
        print(f"端末ID: {self.terminal_id}")
        print(f"サーバー: {self.server_url}")
        print()
        
        # モード検出
        nfcpy_count = 0
        pcsc_count = 0
        
        if NFCPY_AVAILABLE:
            for i in range(10):
                try:
                    clf = nfc.ContactlessFrontend(f'usb:{i:03d}')
                    if clf:
                        nfcpy_count += 1
                        clf.close()
                except:
                    break
        
        if PYSCARD_AVAILABLE:
            try:
                pcsc_count = len(pcsc_readers())
            except:
                pass
        
        if nfcpy_count == 0 and pcsc_count == 0:
            print("[エラー] カードリーダーが見つかりません")
            if self.lcd:
                self.lcd.show_with_time("リーダー ミツカリマセン")
            self.gpio.led("red")
            return
        
        print(f"[検出] nfcpy:{nfcpy_count}台 PCSC:{pcsc_count}台")
        
        # nfcpy開始
        if nfcpy_count > 0:
            for i in range(nfcpy_count):
                path = f'usb:{i:03d}'
                threading.Thread(target=self.nfcpy_worker, args=(path, i+1), daemon=True).start()
                print(f"[OK] nfcpyリーダー{i+1}監視開始")
        
        # PCSC開始
        if pcsc_count > 0:
            try:
                reader_list = pcsc_readers()
                for i, reader in enumerate(reader_list, 1):
                    threading.Thread(target=self.pcsc_worker, args=(reader, nfcpy_count+i), daemon=True).start()
                    print(f"[OK] PCSCリーダー{i}監視開始")
            except:
                pass
        
        print("\n[待機] カードをかざしてください (Ctrl+C で終了)\n")
        
        try:
            while self.running:
                time.sleep(0.5)
        
        except KeyboardInterrupt:
            print("\n[終了] プログラムを終了します")
            self.running = False
            print(f"合計: {self.count}枚\n")
            
            if self.lcd:
                self.lcd.show_with_time("シュウリョウシマシタ")
            
            self.gpio.cleanup()


def load_config():
    """設定読み込み"""
    config_file = "client_config.json"
    default = {"server_url": "http://192.168.11.24:5000"}
    
    if Path(config_file).exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        return default


def main():
    config = load_config()
    server_url = config.get('server_url')
    
    client = UnifiedClient(server_url)
    client.run()


if __name__ == "__main__":
    main()

