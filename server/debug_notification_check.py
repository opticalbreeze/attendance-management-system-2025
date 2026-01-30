#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
お知らせ機能のチェック済み除外機能の検証コード
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
from attendance_check_service import check_attendance_vs_schedule
from database import get_attendance_check_status, get_db_connection
from constants import AttendanceConstants

# 作業ディレクトリをサーバーディレクトリに変更（database.pyのパス解決のため）
os.chdir(current_dir)

def debug_notification_check():
    """お知らせ機能のチェック済み除外機能を検証"""
    
    print("=" * 80)
    print("【お知らせ機能のチェック済み除外機能の検証】")
    print("=" * 80)
    
    # 1. attendance_check_statusテーブルからチェック済みデータを取得
    print("\n【ステップ0】attendance_check_statusテーブルからチェック済みデータを取得")
    print("-" * 80)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT employee_num, work_date, check_type, is_checked, checked_by, checked_at
            FROM attendance_check_status
            WHERE is_checked = 1
            ORDER BY work_date DESC, employee_num
            LIMIT 10
        """)
        
        checked_records = cursor.fetchall()
        print(f"[OK] チェック済みレコード取得: {len(checked_records)}件")
        
        if not checked_records:
            print("[NG] チェック済みレコードが0件のため、検証できません")
            print("   → search画面でチェックボックスにチェックを入れてから再実行してください")
            return
        
        # 最初のレコードを使用
        test_employee_id = checked_records[0][0]
        test_work_date = checked_records[0][1]
        test_check_type = checked_records[0][2]
        
        print(f"\n【テスト対象（チェック済みレコードから選択）】")
        print(f"従業員ID: {test_employee_id}")
        print(f"日付: {test_work_date}")
        print(f"check_type: {test_check_type}")
        print(f"is_checked: {checked_records[0][3]}")
        print("-" * 80)
    
    # 1. 勤怠チェックを実行してアラートを取得
    print("\n【ステップ1】勤怠チェックの実行")
    print("-" * 80)
    result = check_attendance_vs_schedule(test_employee_id, test_work_date)
    
    if result['status'] != 'success':
        print(f"[NG] 勤怠チェック失敗: {result.get('message', '不明なエラー')}")
        return
    
    data = result['data']
    alerts = data.get('alerts', [])
    
    print(f"[OK] 勤怠チェック成功")
    print(f"  アラート件数: {len(alerts)}")
    for idx, alert in enumerate(alerts):
        print(f"  アラート[{idx}]:")
        print(f"    type: {alert.get('type')}")
        print(f"    message: {alert.get('message')}")
        print(f"    details: {alert.get('details')}")
    
    if not alerts:
        print("[NG] アラートが0件のため、検証できません")
        return
    
    # 2. 通知システムのインスタンスを作成
    print("\n【ステップ2】通知システムのインスタンス作成")
    print("-" * 80)
    notification_system = AttendanceNotificationSystem()
    
    # 3. 各アラートに対してcheck_typeを判定
    print("\n【ステップ3】アラートメッセージからcheck_typeを判定")
    print("-" * 80)
    for idx, alert in enumerate(alerts):
        message = alert.get('message', '')
        check_type = notification_system._get_check_type_from_alert(message)
        print(f"アラート[{idx}]:")
        print(f"  メッセージ: {message}")
        print(f"  判定されたcheck_type: {check_type}")
    
    # 4. attendance_check_statusテーブルからチェック状況を取得
    print("\n【ステップ4】attendance_check_statusテーブルからチェック状況を取得")
    print("-" * 80)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT employee_num, work_date, check_type, is_checked, checked_by, checked_at
            FROM attendance_check_status
            WHERE employee_num = ? AND work_date = ?
        """, (test_employee_id, test_work_date))
        
        check_statuses = cursor.fetchall()
        print(f"[OK] チェック状況取得: {len(check_statuses)}件")
        for status in check_statuses:
            print(f"  チェック状況:")
            print(f"    employee_num: {status[0]}")
            print(f"    work_date: {status[1]}")
            print(f"    check_type: {status[2]}")
            print(f"    is_checked: {status[3]}")
            print(f"    checked_by: {status[4]}")
            print(f"    checked_at: {status[5]}")
    
    # 5. _is_checkedメソッドの動作を検証
    print("\n【ステップ5】_is_checkedメソッドの動作検証")
    print("-" * 80)
    for idx, alert in enumerate(alerts):
        message = alert.get('message', '')
        check_type = notification_system._get_check_type_from_alert(message)
        
        if check_type:
            is_checked = notification_system._is_checked(test_employee_id, test_work_date, check_type)
            print(f"アラート[{idx}]:")
            print(f"  メッセージ: {message}")
            print(f"  check_type: {check_type}")
            print(f"  is_checked: {is_checked}")
            if is_checked:
                print(f"  → [OK] チェック済みのため、お知らせから除外されます")
            else:
                print(f"  → [NG] 未チェックのため、お知らせに表示されます")
        else:
            print(f"アラート[{idx}]:")
            print(f"  メッセージ: {message}")
            print(f"  check_type: {check_type} (判定不可)")
            print(f"  → [注意] check_typeが判定できないため、チェック済み除外の対象外です")
    
    # 6. お知らせ生成ロジックの動作を検証
    print("\n【ステップ6】お知らせ生成ロジックの動作検証")
    print("-" * 80)
    
    notifications = []
    for alert in alerts:
        if alert['type'] in ['error', 'warning']:
            # アラートメッセージからcheck_typeを判定
            check_type = notification_system._get_check_type_from_alert(alert.get('message', ''))
            
            # チェック済みかどうかを確認
            if check_type and notification_system._is_checked(test_employee_id, test_work_date, check_type):
                print(f"[スキップ] チェック済みのため除外: message={alert.get('message')}, check_type={check_type}")
                continue
            
            notification_id = notification_system.generate_notification_id(
                test_employee_id, test_work_date, alert['type']
            )
            
            notifications.append({
                'id': notification_id,
                'employee_id': test_employee_id,
                'work_date': test_work_date,
                'alert_type': alert['type'],
                'message': alert['message'],
                'check_type': check_type
            })
    
    print(f"\n[結果] お知らせに追加される項目: {len(notifications)}件")
    for idx, notif in enumerate(notifications):
        print(f"  通知[{idx}]:")
        print(f"    id: {notif['id']}")
        print(f"    message: {notif['message']}")
        print(f"    check_type: {notif['check_type']}")
    
    print("\n" + "=" * 80)
    print("【検証完了】")
    print("=" * 80)

if __name__ == "__main__":
    debug_notification_check()
