#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
今月度分のお知らせ対象を取得して出力する検証コード
"""

import sys
import os

# パス設定
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)

from datetime import datetime
from notification_system import AttendanceNotificationSystem
from database import get_attendance_check_status

# 作業ディレクトリをサーバーディレクトリに変更（database.pyのパス解決のため）
os.chdir(current_dir)

def debug_notification_list():
    """今月度分のお知らせ対象を取得して出力"""
    
    import logging
    # ログレベルをWARNINGに設定して、INFOログを抑制
    logging.getLogger().setLevel(logging.WARNING)
    logging.getLogger('notification_system').setLevel(logging.WARNING)
    logging.getLogger('attendance_check_service').setLevel(logging.WARNING)
    logging.getLogger('database').setLevel(logging.WARNING)
    
    print("=" * 80)
    print("【今月度分のお知らせ対象の取得】")
    print("=" * 80)
    
    # 通知システムのインスタンスを作成
    notification_system = AttendanceNotificationSystem()
    
    # 今月度分のお知らせ対象を取得
    print("\n【お知らせ対象の取得中...】")
    print("-" * 80)
    
    notifications = notification_system.check_monthly_attendance_discrepancies()
    
    print(f"\n[結果] お知らせ対象: {len(notifications)}件")
    print("=" * 80)
    
    # チェック済みの項目を確認
    checked_count = 0
    unchecked_count = 0
    unknown_check_type_count = 0
    
    if notifications:
        # チェック済みの項目を確認
        notification_system = AttendanceNotificationSystem()
        
        # attendance_check_statusテーブルからチェック済みデータを取得
        from database import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT employee_num, work_date, check_type, is_checked
                FROM attendance_check_status
                WHERE is_checked = 1
            """)
            checked_records = {(row[0], row[1], row[2]): row[3] for row in cursor.fetchall()}
        
        for idx, notif in enumerate(notifications, 1):
            employee_id = notif.get('employee_id')
            work_date = notif.get('work_date')
            message = notif.get('message', '')
            
            # check_typeを判定
            check_type = notification_system._get_check_type_from_alert(message)
            
            # チェック済みかどうかを確認
            is_checked = False
            if check_type:
                is_checked = notification_system._is_checked(employee_id, work_date, check_type)
                # データベースからも直接確認
                db_key = (employee_id, work_date, check_type)
                if db_key in checked_records:
                    is_checked_db = checked_records[db_key]
                    if is_checked_db and not is_checked:
                        print(f"  ⚠️ 警告: データベースではチェック済みですが、_is_checkedがFalseを返しています")
            
            print(f"\n【通知{idx}】")
            print(f"  ID: {notif.get('id')}")
            print(f"  従業員ID: {employee_id}")
            print(f"  従業員名: {notif.get('employee_name')}")
            print(f"  日付: {work_date}")
            print(f"  種別: {notif.get('alert_type')}")
            print(f"  メッセージ: {message}")
            print(f"  詳細: {notif.get('detail', '')}")
            print(f"  check_type: {check_type}")
            print(f"  チェック済み: {'はい' if is_checked else 'いいえ'}")
            if is_checked:
                checked_count += 1
                print(f"  ⚠️ 警告: この項目はチェック済みですが、お知らせに含まれています！")
            elif check_type:
                unchecked_count += 1
            else:
                unknown_check_type_count += 1
                print(f"  ⚠️ 警告: check_typeが判定できないため、チェック済み除外の対象外です")
            print(f"  作成日時: {notif.get('created_at')}")
    else:
        print("\n[結果] お知らせ対象は0件です")
    
    print("\n" + "=" * 80)
    print("【統計情報】")
    print("-" * 80)
    print(f"  チェック済みの項目: {checked_count}件")
    print(f"  未チェックの項目: {unchecked_count}件")
    print(f"  check_type判定不可の項目: {unknown_check_type_count}件")
    print("=" * 80)
    print("【出力完了】")
    print("=" * 80)

if __name__ == "__main__":
    debug_notification_list()
