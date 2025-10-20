#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows版GUIクライアント
nfcpy + PCSC両対応、PCスピーカー対応
"""

import time
import sys
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from pathlib import Path
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext

# nfcpy
try:
    import nfc
    NFCPY_AVAILABLE = True
except ImportError:
    NFCPY_AVAILABLE = False

# pyscard
try:
    from smartcard.System import readers as pcsc_readers
    from smartcard.Exceptions import CardConnectionException, NoCardException
    PYSCARD_AVAILABLE = True
except ImportError:
    PYSCARD_AVAILABLE = False

# PCスピーカー
try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False


# 音パターン（周波数, 時間ms）
SOUNDS = {
    "startup": [(1000, 200), (1200, 100), (1000, 200)],
    "connect": [(1500, 100), (1500, 100), (1500, 100)],
    "read": [(2000, 50)],
    "success": [(2500, 100), (2700, 50), (2500, 100)],
    "fail": [(800, 300), (600, 100), (800, 300)]
}


def beep(pattern):
    """PCスピーカーで音"""
    if not WINSOUND_AVAILABLE:
        return
    
    for freq, duration in SOUNDS.get(pattern, [(1000, 100)]):
        try:
            winsound.Beep(freq, duration)
            time.sleep(0.05)
        except:
            pass


def get_reader_commands(reader_name):
    """リーダー名に応じてPC/SCコマンドセットを返す"""
    name = str(reader_name).upper()
    # Sony/PaSoRi 系（FeliCa対応）
    if any(k in name for k in ["SONY", "RC-S", "PASORI"]):
        return [
            [0xFF, 0xCA, 0x00, 0x00, 0x00],  # UID（可変）
            [0xFF, 0xCA, 0x00, 0x00, 0x04],  # 4B UID
            [0xFF, 0xCA, 0x00, 0x00, 0x07],  # 7B UID
            [0xFF, 0xB0, 0x00, 0x00, 0x09, 0x06, 0x00, 0xFF, 0xFF, 0x01, 0x00],  # FeliCa IDm
            [0xFF, 0xCA, 0x01, 0x00, 0x00],  # Get Data
        ]
    # Circle CIR315 系
    if any(k in name for k in ["CIRCLE", "CIR315", "CIR-315"]):
        return [
            [0xFF, 0xCA, 0x00, 0x00, 0x00],
            [0xFF, 0xCA, 0x00, 0x00, 0x04],
            [0xFF, 0xCA, 0x01, 0x00, 0x00],
            [0xFF, 0xB0, 0x00, 0x00, 0x09, 0x06, 0x00, 0xFF, 0xFF, 0x01, 0x00],
            [0xFF, 0xCA, 0x00, 0x00, 0x07],
        ]
    # 汎用
    return [
        [0xFF, 0xCA, 0x00, 0x00, 0x00],
        [0xFF, 0xCA, 0x00, 0x00, 0x04],
        [0xFF, 0xCA, 0x00, 0x00, 0x07],
        [0xFF, 0xCA, 0x00, 0x00, 0x0A],
        [0xFF, 0xCA, 0x01, 0x00, 0x00],
    ]


class LocalCache:
    """ローカルキャッシュ"""
    
    def __init__(self, db_path="local_cache.db"):
        self.db_path = db_path
        conn = sqlite3.connect(self.db_path)
        conn.execute("""CREATE TABLE IF NOT EXISTS pending_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idm TEXT, timestamp TEXT, terminal_id TEXT,
            created_at TEXT, retry_count INTEGER DEFAULT 0)""")
        conn.commit()
        conn.close()
    
    def save_record(self, idm, ts, tid):
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO pending_records (idm, timestamp, terminal_id, created_at) VALUES (?, ?, ?, ?)",
                    (idm, ts, tid, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def get_pending_records(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT id, idm, timestamp, terminal_id, retry_count FROM pending_records WHERE created_at <= ?",
                            ((datetime.now() - timedelta(minutes=10)).isoformat(),))
        records = cursor.fetchall()
        conn.close()
        return records
    
    def delete_record(self, rid):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM pending_records WHERE id = ?", (rid,))
        conn.commit()
        conn.close()


class WindowsClientGUI:
    """Windows GUIクライアント"""
    
    def __init__(self, server_url):
        self.server = server_url
        self.terminal = "Windows-GUI"
        self.cache = LocalCache()
        self.count = 0
        self.history = {}
        self.lock = threading.Lock()
        self.running = True
        self.server_connected = False
        
        # GUI作成
        self.root = tk.Tk()
        self.root.title("打刻システム - Windowsクライアント")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.create_widgets()
        
        # 起動音
        beep("startup")
        
        # スレッド開始
        threading.Thread(target=self.monitor_server, daemon=True).start()
        threading.Thread(target=self.monitor_readers, daemon=True).start()
        threading.Thread(target=self.retry_worker, daemon=True).start()
    
    def create_widgets(self):
        """ウィジェット作成"""
        # タイトル
        title_frame = ttk.Frame(self.root, padding="10")
        title_frame.pack(fill=tk.X)
        
        ttk.Label(title_frame, text="[打刻システム - Windowsクライアント]", 
                 font=("", 14, "bold")).pack()
        
        # ステータスフレーム
        status_frame = ttk.LabelFrame(self.root, text="ステータス", padding="10")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 日時表示
        self.time_label = ttk.Label(status_frame, text="", font=("", 12))
        self.time_label.pack()
        
        # サーバー状態
        server_frame = ttk.Frame(status_frame)
        server_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(server_frame, text="サーバー:").pack(side=tk.LEFT)
        self.server_label = ttk.Label(server_frame, text="接続確認中...", 
                                      font=("", 10, "bold"), foreground="orange")
        self.server_label.pack(side=tk.LEFT, padx=5)
        
        # リーダー状態
        reader_frame = ttk.Frame(status_frame)
        reader_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(reader_frame, text="リーダー:").pack(side=tk.LEFT)
        self.reader_label = ttk.Label(reader_frame, text="検出中...", font=("", 10))
        self.reader_label.pack(side=tk.LEFT, padx=5)
        
        # カウンター
        counter_frame = ttk.Frame(status_frame)
        counter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(counter_frame, text="読み取り数:").pack(side=tk.LEFT)
        self.counter_label = ttk.Label(counter_frame, text="0 枚", 
                                       font=("", 10, "bold"), foreground="blue")
        self.counter_label.pack(side=tk.LEFT, padx=5)
        
        # メッセージエリア
        msg_frame = ttk.LabelFrame(self.root, text="メッセージ", padding="10")
        msg_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.message_label = ttk.Label(msg_frame, text="カードをかざしてください", 
                                       font=("", 12, "bold"), foreground="green")
        self.message_label.pack()
        
        # ログエリア
        log_frame = ttk.LabelFrame(self.root, text="ログ", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, 
                                                   font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # ボタンフレーム
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="設定", command=self.open_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="終了", command=self.on_close).pack(side=tk.RIGHT)
        
        # 時刻更新タイマー
        self.update_time()
        
        # 初期ログ
        self.log(f"サーバー: {self.server}")
        self.log(f"端末ID: {self.terminal}")
        self.log("="*60)
    
    def update_time(self):
        """時刻更新"""
        now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        self.time_label.config(text=now)
        self.root.after(1000, self.update_time)
    
    def log(self, message):
        """ログ出力"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def update_message(self, text, color="black", duration=0):
        """メッセージ更新"""
        self.message_label.config(text=text, foreground=color)
        
        if duration > 0:
            def reset():
                time.sleep(duration)
                self.message_label.config(text="カードをかざしてください", foreground="green")
            threading.Thread(target=reset, daemon=True).start()
    
    def open_config(self):
        """設定GUI起動"""
        import subprocess
        try:
            subprocess.Popen([sys.executable, "client_config_gui.py"])
        except:
            self.log("[エラー] 設定GUIを起動できません")
    
    def monitor_server(self):
        """サーバー監視"""
        retry_count = 0
        max_retries = 2
        
        while self.running:
            try:
                response = requests.get(f"{self.server}/api/health", timeout=5)
                if response.status_code == 200:
                    self.server_connected = True
                    self.server_label.config(text="接続OK", foreground="green")
                    
                    if retry_count > 0:
                        self.log("[OK] サーバー再接続成功")
                        beep("connect")
                    
                    retry_count = 0
                else:
                    self.server_connected = False
                    self.server_label.config(text="接続NG", foreground="red")
                    self.log(f"[NG] サーバー応答異常: {response.status_code}")
            
            except Exception as e:
                self.server_connected = False
                self.server_label.config(text="接続NG", foreground="red")
                
                if retry_count < max_retries:
                    retry_count += 1
                    self.log(f"[再接続] 試行 {retry_count}/{max_retries}")
                    time.sleep(5)
                    continue
                else:
                    if retry_count == max_retries:
                        self.log("[NG] 再接続失敗 - 1時間後に再試行")
                        retry_count += 1
            
            time.sleep(3600)
    
    def monitor_readers(self):
        """リーダー監視"""
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
        
        # PCSC検出
        if PYSCARD_AVAILABLE:
            try:
                pcsc_count = len(pcsc_readers())
            except:
                pass
        
        if nfcpy_count == 0 and pcsc_count == 0:
            self.log("[エラー] カードリーダーが見つかりません")
            self.reader_label.config(text="リーダーなし", foreground="red")
            return
        
        self.log(f"[検出] nfcpy:{nfcpy_count}台 PCSC:{pcsc_count}台")
        self.reader_label.config(text=f"{nfcpy_count+pcsc_count}台検出", foreground="green")
        
        # nfcpy開始
        if nfcpy_count > 0:
            for i in range(nfcpy_count):
                threading.Thread(target=self.nfcpy_worker, args=(f'usb:{i:03d}', i+1), daemon=True).start()
        
        # PCSC開始
        if pcsc_count > 0:
            try:
                reader_list = pcsc_readers()
                for i, reader in enumerate(reader_list, 1):
                    threading.Thread(
                        target=self.pcsc_worker,
                        args=(reader, str(reader), nfcpy_count + i),
                        daemon=True
                    ).start()
            except:
                pass
    
    def nfcpy_worker(self, path, idx):
        """nfcpyワーカー（高速化版）"""
        last_id = None
        clf = None
        
        try:
            # ContactlessFrontendを1回だけ開く（再利用で高速化）
            clf = nfc.ContactlessFrontend(path)
            if not clf:
                self.log(f"[エラー] nfcpyリーダー#{idx}を開けません")
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
    
    def pcsc_worker(self, reader, reader_name, idx):
        """PCSCワーカー"""
        last_id = None
        
        while self.running:
            try:
                connection = reader.createConnection()
                connection.connect()
                
                card_id = None
                commands = get_reader_commands(reader_name)
                for cmd in commands:
                    try:
                        response, sw1, sw2 = connection.transmit(cmd)
                        if sw1 == 0x90 and sw2 == 0x00 and len(response) >= 4:
                            uid_len = min(len(response), 16)
                            card_id = ''.join([f'{b:02X}' for b in response[:uid_len]])
                            if len(card_id) >= 8:
                                break
                    except:
                        continue
                
                if card_id and card_id != last_id:
                    self.process_card(card_id, idx)
                    last_id = card_id
                
                connection.disconnect()
            except (CardConnectionException, NoCardException):
                pass
            except:
                pass
            
            time.sleep(0.3)
    
    def process_card(self, card_id, reader_idx):
        """カード処理"""
        with self.lock:
            now = time.time()
            
            # 重複チェック
            if card_id in self.history and now - self.history[card_id] < 2.0:
                return
            
            self.history[card_id] = now
            self.count += 1
            
            # GUI更新
            self.counter_label.config(text=f"{self.count} 枚")
            self.update_message("カードを読み取りました", "blue", 2)
            
            # ログ出力
            self.log(f"[カード#{self.count}] IDm: {card_id} (リーダー{reader_idx})")
            
            # 音
            beep("read")
            
            # サーバー送信
            ts = datetime.now().isoformat()
            data = {
                'idm': card_id,
                'timestamp': ts,
                'terminal_id': self.terminal
            }
            
            try:
                response = requests.post(f"{self.server}/api/attendance", json=data, timeout=5)
                
                if response.status_code == 200 and response.json().get('status') == 'success':
                    self.log("[送信成功] サーバーに記録")
                    self.update_message("サーバーに記録しました", "green", 2)
                    beep("success")
                else:
                    self.log("[送信失敗] ローカルに保存")
                    self.cache.save_record(card_id, ts, self.terminal)
                    self.update_message("ローカルに保存しました", "orange", 2)
                    beep("fail")
            
            except Exception as e:
                self.log(f"[送信失敗] {e}")
                self.cache.save_record(card_id, ts, self.terminal)
                self.update_message("ローカルに保存しました", "orange", 2)
                beep("fail")
    
    def retry_worker(self):
        """リトライワーカー"""
        while self.running:
            time.sleep(600)
            
            records = self.cache.get_pending_records()
            if records:
                self.log(f"[リトライ] {len(records)}件の未送信データ")
                
                for rid, idm, ts, tid, retry in records:
                    try:
                        response = requests.post(
                            f"{self.server}/api/attendance",
                            json={'idm': idm, 'timestamp': ts, 'terminal_id': tid},
                            timeout=5
                        )
                        
                        if response.status_code == 200 and response.json().get('status') == 'success':
                            self.cache.delete_record(rid)
                            self.log(f"[リトライ成功] IDm: {idm}")
                    except:
                        pass
    
    def on_close(self):
        """終了処理"""
        self.running = False
        self.log("プログラムを終了します...")
        time.sleep(0.5)
        self.root.destroy()
    
    def run(self):
        """実行"""
        self.root.mainloop()


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
    """エントリーポイント"""
    config = load_config()
    server_url = config.get('server_url', 'http://192.168.11.24:5000')
    
    client = WindowsClientGUI(server_url)
    client.run()


if __name__ == "__main__":
    main()

