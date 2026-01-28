#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
勤怠通知システム (Tkinter版)
毎日深夜に実行し、当月の勤怠差異をチェックして打刻PCに通知表示
"""

import tkinter as tk
from tkinter import ttk, font
from datetime import datetime, timedelta
import sqlite3
import json
import logging
import sys
import os
from typing import Dict, List, Any

# 相対パス設定
current_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.join(current_dir, 'server')
sys.path.append(server_dir)

# 作業ディレクトリをサーバーディレクトリに変更（database.pyのパス解決のため）
os.chdir(server_dir)

# サーバーモジュールをインポート
from attendance_check_service import check_attendance_vs_schedule
from database import get_db_connection
from constants import AttendanceConstants

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(current_dir, 'notification.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AttendanceNotificationSystem:
    """勤怠通知システムメインクラス"""
    
    def __init__(self):
        self.root = None
        self.notification_data = []
        self.acknowledged_notifications = set()
        self.window_width = 1200
        self.window_height = 800
        
        # 通知データ保存ファイル
        self.notification_file = os.path.join(current_dir, 'notification_data.json')
        self.acknowledged_file = os.path.join(current_dir, 'acknowledged_notifications.json')
        
        # 確認済み通知を読み込み
        self.load_acknowledged_notifications()
    
    def load_acknowledged_notifications(self):
        """確認済み通知を読み込み"""
        try:
            if os.path.exists(self.acknowledged_file):
                with open(self.acknowledged_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.acknowledged_notifications = set(data.get('acknowledged', []))
                logger.info(f"確認済み通知を読み込み: {len(self.acknowledged_notifications)}件")
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
            logger.info(f"確認済み通知を保存: {len(self.acknowledged_notifications)}件")
        except Exception as e:
            logger.error(f"確認済み通知保存エラー: {e}")
    
    def generate_notification_id(self, employee_id: str, work_date: str, alert_type: str) -> str:
        """通知IDを生成"""
        return f"{employee_id}_{work_date}_{alert_type}"
    
    def check_monthly_attendance_discrepancies(self, target_month: str = None) -> List[Dict[str, Any]]:
        """月度勤怠差異をチェック（既存ロジックを活用）"""
        logger.info("月度勤怠差異チェック開始")
        
        # 現在の勤怠月度を計算（16日基準）
        if target_month is None:
            today = datetime.now()
            year = today.year
            month = today.month
            day = today.day
            
            # 16日以降なら翌月度、15日以前なら当月度
            if day >= 16:
                # 翌月度
                if month == 12:
                    current_payroll_month = f"{year + 1}/1"
                else:
                    current_payroll_month = f"{year}/{month + 1}"
            else:
                # 当月度
                current_payroll_month = f"{year}/{month}"
        else:
            current_payroll_month = target_month
        
        logger.info(f"対象月度: {current_payroll_month}")
        
        notifications = []
        
        try:
            # calculate_date_rangeを使用して正しい期間を取得
            sys.path.append(os.path.join(current_dir, 'server'))
            from validation_utils import calculate_date_range
            
            start_date, end_date = calculate_date_range(current_payroll_month)
            logger.info(f"チェック期間: {start_date} ～ {end_date}")
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 当月度のスケジュール取得
                cursor.execute("""
                    SELECT DISTINCT employee_id, work_date
                    FROM attend_schedule
                    WHERE work_date >= ? AND work_date <= ?
                    ORDER BY employee_id, work_date
                """, (start_date, end_date))
                
                schedule_data = cursor.fetchall()
                logger.info(f"チェック対象: {len(schedule_data)}件 ({current_payroll_month}月度：{start_date}～{end_date})")
                
                # 今日の日付を取得（当日以降はスキップ）
                today = datetime.now().date()
                
                for employee_id, work_date in schedule_data:
                    try:
                        # 当日以降の日付はスキップ（まだ打刻する時間があるため）
                        try:
                            work_date_obj = datetime.strptime(work_date, '%Y-%m-%d').date()
                            if work_date_obj >= today:
                                logger.debug(f"当日以降のためスキップ: 従業員ID={employee_id}, 日付={work_date}, 今日={today}")
                                continue
                        except (ValueError, TypeError) as e:
                            logger.warning(f"日付解析エラー: {e}, work_date={work_date}")
                            # 日付の解析に失敗した場合は続行（既存の動作を維持）
                        
                        # 既存の差異チェック機能を使用
                        result = check_attendance_vs_schedule(str(employee_id), work_date)
                        
                        if result['status'] == 'success':
                            data = result['data']
                            alerts = data.get('alerts', [])
                            
                            # エラーと警告のみを通知対象とする
                            for alert in alerts:
                                if alert['type'] in ['error', 'warning']:
                                    notification_id = self.generate_notification_id(
                                        str(employee_id), work_date, alert['type']
                                    )
                                    
                                    # 確認済みでない場合のみ追加
                                    if notification_id not in self.acknowledged_notifications:
                                        notifications.append({
                                            'id': notification_id,
                                            'employee_id': str(employee_id),
                                            'employee_name': data.get('employee_name', '不明'),
                                            'work_date': work_date,
                                            'alert_type': alert['type'],
                                            'message': alert['message'],
                                            'detail': alert.get('detail', ''),
                                            'schedule': data.get('schedule', {}),
                                            'actual_clock_in': data.get('actual_clock_in'),
                                            'actual_clock_out': data.get('actual_clock_out'),
                                            'created_at': datetime.now().isoformat()
                                        })
                    
                    except Exception as e:
                        logger.error(f"従業員{employee_id}の{work_date}チェックエラー: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"月度チェックエラー: {e}")
        
        logger.info(f"月度勤怠差異チェック完了: {len(notifications)}件の未確認通知")
        return notifications
    
    def save_notification_data(self, notifications: List[Dict[str, Any]]):
        """通知データを保存"""
        try:
            data = {
                'notifications': notifications,
                'generated_at': datetime.now().isoformat(),
                'total_count': len(notifications)
            }
            with open(self.notification_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"通知データを保存: {len(notifications)}件")
        except Exception as e:
            logger.error(f"通知データ保存エラー: {e}")
    
    def load_notification_data(self) -> List[Dict[str, Any]]:
        """通知データを読み込み"""
        try:
            if os.path.exists(self.notification_file):
                with open(self.notification_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    notifications = data.get('notifications', [])
                logger.info(f"通知データを読み込み: {len(notifications)}件")
                return notifications
            else:
                logger.info("通知データファイルが存在しません")
                return []
        except Exception as e:
            logger.error(f"通知データ読み込みエラー: {e}")
            return []
    
    def create_notification_gui(self):
        """通知画面GUI作成"""
        self.root = tk.Tk()
        self.root.title("勤怠お知らせ - 差異・エラー通知")
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        self.root.configure(bg='#f0f0f0')
        
        # フォント設定
        title_font = font.Font(family="Yu Gothic UI", size=16, weight="bold")
        header_font = font.Font(family="Yu Gothic UI", size=12, weight="bold")
        content_font = font.Font(family="Yu Gothic UI", size=10)
        
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ウィンドウのリサイズ設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # タイトル
        title_label = tk.Label(
            main_frame, 
            text="勤怠差異・エラー通知", 
            font=title_font,
            bg='#f0f0f0',
            fg='#d32f2f'
        )
        title_label.grid(row=0, column=0, pady=(0, 20), sticky=tk.W)
        
        # 通知リスト表示フレーム
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Treeview（一覧表示）
        columns = ('date', 'name', 'type', 'message', 'schedule', 'actual')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # 列の設定
        self.tree.heading('date', text='日付')
        self.tree.heading('name', text='氏名')
        self.tree.heading('type', text='種別')
        self.tree.heading('message', text='内容')
        self.tree.heading('schedule', text='予定時刻')
        self.tree.heading('actual', text='実際時刻')
        
        self.tree.column('date', width=100)
        self.tree.column('name', width=120)
        self.tree.column('type', width=80)
        self.tree.column('message', width=300)
        self.tree.column('schedule', width=120)
        self.tree.column('actual', width=120)
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=(20, 0), sticky=(tk.W, tk.E))
        
        # 確認ボタン
        acknowledge_btn = ttk.Button(
            button_frame,
            text="選択した通知を確認済みにする",
            command=self.acknowledge_selected,
            style='Accent.TButton'
        )
        acknowledge_btn.grid(row=0, column=0, padx=(0, 10))
        
        # 全確認ボタン
        acknowledge_all_btn = ttk.Button(
            button_frame,
            text="全て確認済みにする",
            command=self.acknowledge_all,
            style='Accent.TButton'
        )
        acknowledge_all_btn.grid(row=0, column=1, padx=(0, 10))
        
        # 更新ボタン
        refresh_btn = ttk.Button(
            button_frame,
            text="最新データで更新",
            command=self.refresh_notifications
        )
        refresh_btn.grid(row=0, column=2, padx=(0, 10))
        
        # 閉じるボタン
        close_btn = ttk.Button(
            button_frame,
            text="閉じる",
            command=self.root.quit
        )
        close_btn.grid(row=0, column=3)
        
        # 詳細表示フレーム
        detail_frame = ttk.LabelFrame(main_frame, text="詳細情報", padding="10")
        detail_frame.grid(row=3, column=0, pady=(20, 0), sticky=(tk.W, tk.E))
        detail_frame.columnconfigure(0, weight=1)
        
        self.detail_text = tk.Text(
            detail_frame, 
            height=6, 
            font=content_font,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.detail_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # 詳細表示スクロールバー
        detail_scroll = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=detail_scroll.set)
        detail_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # イベントバインド
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        
        # 通知データを読み込んで表示
        self.load_and_display_notifications()
    
    def on_select(self, event):
        """リスト選択時の詳細表示"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            item_id = item['values'][0] if item['values'] else None
            
            # 該当する通知データを検索
            for notification in self.notification_data:
                if notification['work_date'] == item_id:
                    self.show_detail(notification)
                    break
    
    def show_detail(self, notification: Dict[str, Any]):
        """詳細情報を表示"""
        detail_text = f"""
【日付】 {notification['work_date']}
【従業員】 {notification['employee_name']} (ID: {notification['employee_id']})
【種別】 {notification['alert_type'].upper()}

【通知内容】
{notification['message']}

【詳細】
{notification.get('detail', '詳細情報なし')}

【予定スケジュール】
開始時刻: {notification.get('schedule', {}).get('start_time', '未設定')}
終了時刻: {notification.get('schedule', {}).get('end_time', '未設定')}
勤務区分: {notification.get('schedule', {}).get('work_type', '未設定')}

【実際の打刻】
出勤打刻: {notification.get('actual_clock_in') or '未打刻'}
退勤打刻: {notification.get('actual_clock_out') or '未打刻'}

【作成日時】 {notification.get('created_at', '不明')}
        """.strip()
        
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(1.0, detail_text)
        self.detail_text.config(state=tk.DISABLED)
    
    def load_and_display_notifications(self):
        """通知データを読み込んで表示"""
        self.notification_data = self.load_notification_data()
        self.update_tree_display()
    
    def update_tree_display(self):
        """ツリービューの表示を更新"""
        # 既存のアイテムをクリア
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 未確認の通知のみ表示
        unacknowledged_count = 0
        for notification in self.notification_data:
            if notification['id'] not in self.acknowledged_notifications:
                # スケジュール時刻の表示
                schedule = notification.get('schedule', {})
                schedule_time = f"{schedule.get('start_time', '')}-{schedule.get('end_time', '')}"
                if schedule_time == "-":
                    schedule_time = "未設定"
                
                # 実際の時刻の表示
                actual_in = notification.get('actual_clock_in') or "未打刻"
                actual_out = notification.get('actual_clock_out') or "未打刻"
                actual_time = f"{actual_in}-{actual_out}"
                
                # 種別の色分け
                alert_type = notification['alert_type']
                type_text = "エラー" if alert_type == "error" else "警告"
                
                self.tree.insert('', 'end', values=(
                    notification['work_date'],
                    notification['employee_name'],
                    type_text,
                    notification['message'][:50] + "..." if len(notification['message']) > 50 else notification['message'],
                    schedule_time,
                    actual_time
                ))
                unacknowledged_count += 1
        
        # タイトルに件数を表示
        self.root.title(f"勤怠お知らせ - 差異・エラー通知 ({unacknowledged_count}件)")
    
    def acknowledge_selected(self):
        """選択した通知を確認済みにする"""
        selection = self.tree.selection()
        if not selection:
            return
        
        for item in selection:
            values = self.tree.item(item)['values']
            work_date = values[0]
            
            # 該当する通知を検索して確認済みに追加
            for notification in self.notification_data:
                if notification['work_date'] == work_date:
                    self.acknowledged_notifications.add(notification['id'])
                    logger.info(f"通知を確認済みに設定: {notification['id']}")
                    break
        
        self.save_acknowledged_notifications()
        self.update_tree_display()
    
    def acknowledge_all(self):
        """全ての通知を確認済みにする"""
        for notification in self.notification_data:
            self.acknowledged_notifications.add(notification['id'])
        
        logger.info(f"全通知を確認済みに設定: {len(self.notification_data)}件")
        self.save_acknowledged_notifications()
        self.update_tree_display()
    
    def refresh_notifications(self):
        """最新データで通知を更新"""
        logger.info("通知データを最新情報で更新中...")
        notifications = self.check_monthly_attendance_discrepancies()
        self.save_notification_data(notifications)
        self.load_and_display_notifications()
        logger.info("通知データの更新完了")
    
    def show_notifications(self):
        """通知画面を表示"""
        self.create_notification_gui()
        self.root.mainloop()

def main():
    """メイン実行関数"""
    logger.info("勤怠通知システム開始")
    
    notification_system = AttendanceNotificationSystem()
    
    # 引数チェック
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "--check-only":
            # チェックのみ実行（GUI表示なし）
            logger.info("月度チェックのみ実行")
            notifications = notification_system.check_monthly_attendance_discrepancies()
            notification_system.save_notification_data(notifications)
            logger.info(f"チェック完了: {len(notifications)}件の新規通知")
            return
        
        elif command == "--show-gui":
            # GUI表示のみ
            logger.info("GUI表示のみ")
            notification_system.show_notifications()
            return
    
    # デフォルト: チェック実行後にGUI表示
    logger.info("月度チェック実行 + GUI表示")
    notifications = notification_system.check_monthly_attendance_discrepancies()
    notification_system.save_notification_data(notifications)
    
    if notifications:
        logger.info(f"{len(notifications)}件の新規通知があります")
        notification_system.show_notifications()
    else:
        logger.info("新規通知はありません")

if __name__ == "__main__":
    main()