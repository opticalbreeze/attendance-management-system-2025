#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
勤怠チェック機能のテストスクリプト
"""

from utils import get_db_connection
from database import check_attendance_vs_schedule, get_employees
import json

def test_attendance_check():
    """勤怠チェック機能をテストする"""
    print("=== 勤怠チェック機能テスト ===")
    
    # 1. 最新の打刻日付を取得
    print("\n1. 最新の打刻日付を確認:")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT date(timestamp) as punch_date 
            FROM attendance 
            ORDER BY punch_date DESC 
            LIMIT 5
        """)
        dates = cursor.fetchall()
        print("最新の打刻日付:")
        for date in dates:
            print(f"  - {date[0]}")
    
    # 2. 従業員リストを取得
    print("\n2. 従業員一覧の確認:")
    employees = get_employees()
    print(f"登録されている従業員数: {len(employees)}")
    for i, emp in enumerate(employees[:3]):
        print(f"  {i+1}. ID: {emp['employee_num']}, 名前: {emp['name']}")
    
    # 3. 具体的な勤怠チェック実行
    print("\n3. 勤怠チェック実行:")
    if dates and employees:
        test_date = dates[0][0]  # 最新の打刻日付
        test_employee = employees[0]['employee_num']  # 最初の従業員
        
        print(f"テスト対象: 従業員ID {test_employee}, 日付 {test_date}")
        
        result = check_attendance_vs_schedule(str(test_employee), test_date)
        
        print(f"ステータス: {result['status']}")
        if result['status'] == 'success':
            data = result['data']
            print(f"従業員名: {data['employee_name']}")
            print(f"スケジュール: {data['schedule']}")
            print(f"打刻記録数: {len(data['attendance_records'])}")
            print(f"アラート数: {len(data['alerts'])}")
            
            if data['alerts']:
                print("検出されたアラート:")
                for alert in data['alerts']:
                    print(f"  - [{alert['type']}] {alert['message']}")
                    print(f"    詳細: {alert['details']}")
            else:
                print("アラートなし（正常）")
        else:
            print(f"エラー: {result.get('message', '不明')}")
    
    # 4. エラー検出パターンのテスト
    print("\n4. エラー検出パターンのテスト:")
    
    # 休日に打刻があるパターンをテスト
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.employee_id, s.work_date, s.work_type
            FROM attend_schedule s
            WHERE s.work_type LIKE '%有%' OR s.work_type LIKE '%所%' OR s.work_type LIKE '%法%'
            LIMIT 3
        """)
        holiday_schedules = cursor.fetchall()
        
        for schedule in holiday_schedules:
            emp_id, work_date, work_type = schedule
            print(f"\n休日スケジュールのチェック: 従業員ID {emp_id}, 日付 {work_date}, 勤務タイプ: {work_type}")
            result = check_attendance_vs_schedule(str(emp_id), work_date)
            if result['status'] == 'success':
                alerts = result['data']['alerts']
                if alerts:
                    print(f"  エラー検出: {len(alerts)}件")
                    for alert in alerts:
                        print(f"    - {alert['message']}")
                else:
                    print("  エラー検出なし")

if __name__ == "__main__":
    test_attendance_check()