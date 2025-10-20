#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
クライアント設定GUI - サーバーIP設定
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import subprocess
import sys


class ConfigGUI:
    """設定GUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("打刻システム - クライアント設定")
        self.root.geometry("600x450")
        self.root.resizable(False, False)
        
        # ウィンドウを中央に配置
        self.center_window()
        
        self.config_file = "client_config.json"
        self.config = self.load_config()
        
        self.create_widgets()
    
    def center_window(self):
        """ウィンドウを画面中央に配置"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def load_config(self):
        """設定ファイルを読み込み"""
        default_config = {
            "server_url": "http://192.168.1.31:5000"
        }
        
        if Path(self.config_file).exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return default_config
        else:
            return default_config
    
    def save_config(self):
        """設定ファイルを保存"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("エラー", f"設定の保存に失敗しました:\n{e}")
            return False
    
    def create_widgets(self):
        """ウィジェット作成"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # タイトル
        title_label = ttk.Label(
            main_frame, 
            text="[打刻システム - クライアント設定]",
            font=("", 14, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 現在の設定表示
        current_frame = ttk.LabelFrame(main_frame, text="現在の設定", padding="10")
        current_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        current_url = self.config.get('server_url', 'http://192.168.1.31:5000')
        ttk.Label(current_frame, text="現在のサーバーURL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.current_url_label = ttk.Label(
            current_frame, 
            text=current_url,
            foreground="blue",
            font=("", 10, "bold")
        )
        self.current_url_label.grid(row=0, column=1, sticky=tk.W, padx=10)
        
        # サーバー設定
        url_frame = ttk.LabelFrame(main_frame, text="サーバー設定", padding="10")
        url_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # IPアドレス設定
        ttk.Label(url_frame, text="サーバーIPアドレス:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.ip_entry = ttk.Entry(url_frame, width=20)
        self.ip_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # ポート設定
        ttk.Label(url_frame, text="ポート番号:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.port_entry = ttk.Entry(url_frame, width=20)
        self.port_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # プリセットボタン
        preset_frame = ttk.Frame(url_frame)
        preset_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Label(preset_frame, text="よく使われるIP:").grid(row=0, column=0, sticky=tk.W)
        
        preset_buttons = [
            ("192.168.1.24", "192.168.1.24"),
            ("192.168.1.31", "192.168.1.31"),
            ("192.168.11.24", "192.168.11.24"),
            ("localhost", "127.0.0.1")
        ]
        
        for i, (text, ip) in enumerate(preset_buttons):
            btn = ttk.Button(
                preset_frame,
                text=text,
                command=lambda ip=ip: self.set_preset_ip(ip),
                width=12
            )
            btn.grid(row=0, column=i+1, padx=2)
        
        # 現在の設定を表示
        if '://' in current_url:
            current_url = current_url.split('://', 1)[1]
        if ':' in current_url:
            ip, port = current_url.split(':', 1)
            self.ip_entry.insert(0, ip)
            self.port_entry.insert(0, port)
        else:
            self.ip_entry.insert(0, current_url)
            self.port_entry.insert(0, "5000")
        
        # プレビュー
        preview_frame = ttk.Frame(main_frame)
        preview_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(preview_frame, text="新しいURL:").grid(row=0, column=0, sticky=tk.W)
        self.url_preview = ttk.Label(
            preview_frame, 
            text=self.config.get('server_url', ''),
            foreground="green",
            font=("", 10, "bold")
        )
        self.url_preview.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # 入力変更時にプレビューを更新
        self.ip_entry.bind('<KeyRelease>', self.update_preview)
        self.port_entry.bind('<KeyRelease>', self.update_preview)
        
        # 接続テストボタン
        test_button = ttk.Button(
            main_frame,
            text="[接続テスト]",
            command=self.test_connection
        )
        test_button.grid(row=4, column=0, columnspan=3, pady=10)
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=20)
        
        save_button = ttk.Button(
            button_frame,
            text="[保存]",
            command=self.save_and_close,
            width=15
        )
        save_button.grid(row=0, column=0, padx=5)
        
        start_button = ttk.Button(
            button_frame,
            text="[保存して起動]",
            command=self.save_and_start,
            width=15
        )
        start_button.grid(row=0, column=1, padx=5)
        
        cancel_button = ttk.Button(
            button_frame,
            text="[キャンセル]",
            command=self.root.quit,
            width=15
        )
        cancel_button.grid(row=0, column=2, padx=5)
        
        # ステータスバー
        self.status_label = ttk.Label(
            main_frame,
            text="設定を編集してください",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def set_preset_ip(self, ip):
        """プリセットIPを設定"""
        self.ip_entry.delete(0, tk.END)
        self.ip_entry.insert(0, ip)
        self.update_preview()
        self.status_label.config(text=f"IPアドレスを {ip} に設定しました")
    
    def update_preview(self, event=None):
        """URLプレビューを更新"""
        ip = self.ip_entry.get().strip()
        port = self.port_entry.get().strip()
        
        if ip and port:
            url = f"http://{ip}:{port}"
            self.url_preview.config(text=url)
        else:
            self.url_preview.config(text="")
    
    def test_connection(self):
        """サーバーへの接続をテスト"""
        ip = self.ip_entry.get().strip()
        port = self.port_entry.get().strip()
        
        if not ip or not port:
            messagebox.showwarning("警告", "IPアドレスとポートを入力してください")
            return
        
        url = f"http://{ip}:{port}"
        self.status_label.config(text="接続テスト中...")
        self.root.update()
        
        try:
            import requests
            response = requests.get(f"{url}/api/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                messagebox.showinfo("成功", f"サーバーに接続できました！\n\nURL: {url}\nメッセージ: {data.get('message')}\n時刻: {data.get('timestamp')}")
                self.status_label.config(text="[OK] 接続成功")
            else:
                messagebox.showwarning("警告", f"サーバーが応答しましたが、ステータスが異常です:\nHTTPステータス: {response.status_code}\nURL: {url}")
                self.status_label.config(text="[WARNING] 異常な応答")
        except ImportError:
            messagebox.showerror("エラー", "requestsモジュールがインストールされていません。\npip install requests を実行してください。")
            self.status_label.config(text="[ERROR] requests未インストール")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("エラー", f"サーバーに接続できません:\n{url}\n\n【確認事項】\n・サーバーが起動しているか\n・IPアドレスが正しいか\n・ファイアウォールの設定")
            self.status_label.config(text="[NG] 接続失敗")
        except requests.exceptions.Timeout:
            messagebox.showerror("エラー", f"接続がタイムアウトしました:\n{url}\n\n【確認事項】\n・ネットワークの接続\n・サーバーの負荷状況")
            self.status_label.config(text="[NG] タイムアウト")
        except Exception as e:
            messagebox.showerror("エラー", f"予期しないエラーが発生しました:\n{url}\n\nエラー: {e}")
            self.status_label.config(text="[NG] エラー発生")
    
    def save_and_close(self):
        """設定を保存して閉じる"""
        ip = self.ip_entry.get().strip()
        port = self.port_entry.get().strip()
        
        if not ip or not port:
            messagebox.showwarning("警告", "IPアドレスとポートを入力してください")
            return
        
        self.config['server_url'] = f"http://{ip}:{port}"
        
        if self.save_config():
            # 現在の設定表示を更新
            self.current_url_label.config(text=self.config['server_url'])
            messagebox.showinfo("成功", f"設定を保存しました\n\n新しいサーバーURL:\n{self.config['server_url']}")
            self.root.quit()
    
    def save_and_start(self):
        """設定を保存してクライアントを起動"""
        ip = self.ip_entry.get().strip()
        port = self.port_entry.get().strip()
        
        if not ip or not port:
            messagebox.showwarning("警告", "IPアドレスとポートを入力してください")
            return
        
        self.config['server_url'] = f"http://{ip}:{port}"
        
        if self.save_config():
            # 現在の設定表示を更新
            self.current_url_label.config(text=self.config['server_url'])
            self.root.quit()
            
            # クライアントを起動
            try:
                if sys.platform == "win32":
                    subprocess.Popen(["python", "client_card_reader.py"], creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:
                    subprocess.Popen(["python3", "client_card_reader.py"])
                
                messagebox.showinfo("起動", f"クライアントを起動しました\n\nサーバーURL: {self.config['server_url']}")
            except Exception as e:
                messagebox.showerror("エラー", f"クライアントの起動に失敗しました:\n{e}")
    
    def run(self):
        """GUIを実行"""
        self.root.mainloop()


def main():
    """エントリーポイント"""
    app = ConfigGUI()
    app.run()


if __name__ == "__main__":
    main()

