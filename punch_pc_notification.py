#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
打刻PC用通知表示システム
軽量版 - 簡潔な通知表示とワンクリック確認機能
"""

import tkinter as tk
from tkinter import ttk, font, messagebox
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
import logging

# 相対パス設定
current_dir = os.path.dirname(os.path.abspath(__file__))

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(current_dir, 'punch_pc_notification.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PunchPCNotificationDisplay:
    """打刻PC用軽量通知表示"""
    
    def __init__(self, employee_filter: str = None):
        self.employee_filter = employee_filter  # 特定従業員のみ表示する場合
        self.root = None
        self.notifications = []
        self.acknowledged_file = os.path.join(current_dir, 'acknowledged_notifications.json')
        self.notification_file = os.path.join(current_dir, 'notification_data.json')
        
        # 確認済み通知
        self.acknowledged_notifications = set()
        self.load_acknowledged_notifications()
    
    def load_acknowledged_notifications(self):
        """確認済み通知を読み込み"""
        try:
            if os.path.exists(self.acknowledged_file):
                with open(self.acknowledged_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.acknowledged_notifications = set(data.get('acknowledged', []))
        except Exception as e:
            logger.error(f"確認済み通知読み込みエラー: {e}")
            self.acknowledged_notifications = set()
    
    def save_acknowledged_notifications(self):
        """確認済み通知を保存"""
        try:
            data = {
                'acknowledged': list(self.acknowledged_notifications),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.acknowledged_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"確認済み通知保存エラー: {e}")
    
    def load_notifications(self) -> List[Dict[str, Any]]:
        """通知データを読み込み"""
        try:
            if os.path.exists(self.notification_file):
                with open(self.notification_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_notifications = data.get('notifications', [])
                    
                    # フィルタリング
                    filtered_notifications = []
                    for notification in all_notifications:
                        # 確認済みは除外
                        if notification['id'] in self.acknowledged_notifications:
                            continue
                        
                        # 従業員フィルター
                        if self.employee_filter:
                            if notification['employee_id'] != self.employee_filter:
                                continue
                        
                        filtered_notifications.append(notification)
                    
                    return filtered_notifications
            else:
                return []
        except Exception as e:
            logger.error(f"通知データ読み込みエラー: {e}")
            return []
    
    def create_compact_gui(self):
        """コンパクトなGUIを作成"""
        self.root = tk.Tk()
        self.root.title("勤怠お知らせ")
        
        # 通知データを読み込み
        self.notifications = self.load_notifications()
        
        if not self.notifications:
            # 通知がない場合
            self.root.geometry("400x150")
            self.show_no_notifications()
        else:
            # 通知がある場合
            self.root.geometry("600x400")
            self.show_notifications_compact()
        
        self.root.configure(bg='#f5f5f5')
        self.center_window()
        
        # 5分後に自動で閉じる
        self.root.after(300000, self.auto_close)  # 300000ms = 5分
    
    def center_window(self):
        """ウィンドウを画面中央に配置"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def show_no_notifications(self):
        """通知なしの画面"""
        main_frame = tk.Frame(self.root, bg='#f5f5f5', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # アイコン風のラベル
        icon_label = tk.Label(
            main_frame,
            text="✓",
            font=font.Font(size=40, weight="bold"),
            fg='#4caf50',
            bg='#f5f5f5'
        )
        icon_label.pack(pady=(20, 10))
        
        # メッセージ
        message_label = tk.Label(
            main_frame,
            text="現在、勤怠に関する通知はありません",
            font=font.Font(family="Yu Gothic UI", size=12),
            fg='#333333',
            bg='#f5f5f5'
        )
        message_label.pack(pady=10)
        
        # 閉じるボタン
        close_btn = tk.Button(
            main_frame,
            text="閉じる",
            command=self.root.destroy,
            font=font.Font(family="Yu Gothic UI", size=10),
            bg='#e0e0e0',
            relief=tk.FLAT,
            padx=20,
            pady=5
        )
        close_btn.pack(pady=20)
    
    def show_notifications_compact(self):
        """通知ありの簡潔表示"""
        main_frame = tk.Frame(self.root, bg='#f5f5f5', padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_frame = tk.Frame(main_frame, bg='#f5f5f5')
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = tk.Label(
            title_frame,
            text=f"⚠ 勤怠お知らせ ({len(self.notifications)}件)",
            font=font.Font(family="Yu Gothic UI", size=14, weight="bold"),
            fg='#d32f2f',
            bg='#f5f5f5'
        )
        title_label.pack(side=tk.LEFT)
        
        # 通知リスト（簡潔版）
        list_frame = tk.Frame(main_frame, bg='white', relief=tk.SUNKEN, bd=1)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # スクロール可能なフレーム
        canvas = tk.Canvas(list_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 通知アイテムを表示
        for i, notification in enumerate(self.notifications):
            self.create_notification_item(scrollable_frame, notification, i)
        
        # ボタンフレーム
        button_frame = tk.Frame(main_frame, bg='#f5f5f5')
        button_frame.pack(fill=tk.X)
        
        # 全て確認ボタン
        acknowledge_all_btn = tk.Button(
            button_frame,
            text="全て確認しました",
            command=self.acknowledge_all,
            font=font.Font(family="Yu Gothic UI", size=11, weight="bold"),
            bg='#4caf50',
            fg='white',
            relief=tk.FLAT,
            padx=20,
            pady=8
        )
        acknowledge_all_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 詳細表示ボタン
        detail_btn = tk.Button(
            button_frame,
            text="詳細表示",
            command=self.show_detailed_view,
            font=font.Font(family="Yu Gothic UI", size=10),
            bg='#2196f3',
            fg='white',
            relief=tk.FLAT,
            padx=15,
            pady=6
        )
        detail_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 閉じるボタン
        close_btn = tk.Button(
            button_frame,
            text="閉じる",
            command=self.root.destroy,
            font=font.Font(family="Yu Gothic UI", size=10),
            bg='#e0e0e0',
            relief=tk.FLAT,
            padx=15,
            pady=6
        )
        close_btn.pack(side=tk.RIGHT)
    
    def create_notification_item(self, parent, notification, index):
        """個別通知アイテムを作成"""
        # 背景色（エラーと警告で分ける）
        bg_color = '#ffebee' if notification['alert_type'] == 'error' else '#fff3e0'
        
        item_frame = tk.Frame(parent, bg=bg_color, relief=tk.FLAT, bd=1)
        item_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # 内容フレーム
        content_frame = tk.Frame(item_frame, bg=bg_color)
        content_frame.pack(fill=tk.X, padx=10, pady=8)
        
        # 日付と種別
        header_text = f"{notification['work_date']} - {notification['employee_name']}"
        if notification['alert_type'] == 'error':
            header_text += " [エラー]"
        else:
            header_text += " [警告]"
        
        header_label = tk.Label(
            content_frame,
            text=header_text,
            font=font.Font(family="Yu Gothic UI", size=10, weight="bold"),
            fg='#d32f2f' if notification['alert_type'] == 'error' else '#f57c00',
            bg=bg_color,
            anchor='w'
        )
        header_label.pack(fill=tk.X)
        
        # メッセージ
        message_text = notification['message']
        if len(message_text) > 60:
            message_text = message_text[:60] + "..."
        
        message_label = tk.Label(
            content_frame,
            text=message_text,
            font=font.Font(family="Yu Gothic UI", size=9),
            fg='#333333',
            bg=bg_color,
            anchor='w',
            wraplength=500
        )
        message_label.pack(fill=tk.X, pady=(2, 0))
        
        # 個別確認ボタン
        acknowledge_btn = tk.Button(
            content_frame,
            text="確認",
            command=lambda n=notification: self.acknowledge_single(n),
            font=font.Font(family="Yu Gothic UI", size=8),
            bg='#ffffff',
            fg='#666666',
            relief=tk.FLAT,
            padx=8,
            pady=2
        )
        acknowledge_btn.pack(side=tk.RIGHT, pady=(5, 0))
    
    def acknowledge_single(self, notification):
        """個別通知を確認済みにする"""
        self.acknowledged_notifications.add(notification['id'])
        self.save_acknowledged_notifications()
        logger.info(f"通知を確認済みに設定: {notification['id']}")
        
        # 画面を再描画
        self.root.destroy()
        self.create_compact_gui()
        self.root.mainloop()
    
    def acknowledge_all(self):
        """全通知を確認済みにする"""
        for notification in self.notifications:
            self.acknowledged_notifications.add(notification['id'])
        
        self.save_acknowledged_notifications()
        logger.info(f"全通知を確認済みに設定: {len(self.notifications)}件")
        
        messagebox.showinfo("確認完了", "全ての通知を確認済みにしました。")
        self.root.destroy()
    
    def show_detailed_view(self):
        """詳細ビューを起動"""
        try:
            import subprocess
            script_path = os.path.join(current_dir, 'notification_system.py')
            subprocess.Popen([sys.executable, script_path, '--show-gui'])
            logger.info("詳細ビュー起動")
        except Exception as e:
            logger.error(f"詳細ビュー起動エラー: {e}")
            messagebox.showerror("エラー", "詳細ビューの起動に失敗しました。")
    
    def auto_close(self):
        """自動クローズ"""
        logger.info("5分経過により自動クローズ")
        self.root.destroy()
    
    def show(self):
        """通知画面を表示"""
        self.create_compact_gui()
        self.root.mainloop()

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='打刻PC用通知表示')
    parser.add_argument('--employee-id', type=str, help='特定従業員IDのみ表示')
    args = parser.parse_args()
    
    logger.info("打刻PC用通知表示開始")
    
    display = PunchPCNotificationDisplay(employee_filter=args.employee_id)
    display.show()

if __name__ == "__main__":
    main()