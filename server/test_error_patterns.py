#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
勤怠チェック機能の詳細テスト（エラーパターン検証）
"""

from utils import get_db_connection
from database import check_attendance_vs_schedule, get_employees
import json

def test_error_patterns():
    """エラーパターンの勤怠チェック機能をテストする"""
    print("=== 勤怠エラー検出テスト ===")
    
    # 1. 平日に打刻がない場合のテスト
    print("\n1. 平日で打刻がない場合の検出テスト:")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 平日のスケジュール（日勤など）で打刻がない場合を探す
        cursor.execute("""
            SELECT s.employee_id, s.work_date, s.work_type, s.start_time, s.end_time, e.idm
            FROM attend_schedule s
            JOIN employee_master e ON s.employee_id = e.employee_num
            LEFT JOIN attendance a ON e.idm = a.idm AND date(a.timestamp) = s.work_date
            WHERE s.work_type NOT LIKE '%有%' 
            AND s.work_type NOT LIKE '%所%' 
            AND s.work_type NOT LIKE '%法%'
            AND (s.start_time IS NOT NULL OR s.end_time IS NOT NULL)
            AND a.id IS NULL
            LIMIT 5
        """)
        no_punch_cases = cursor.fetchall()
        
        for case in no_punch_cases:
            emp_id, work_date, work_type, start_time, end_time, idm = case
            print(f"\n平日無打刻のチェック: 従業員ID {emp_id}, 日付 {work_date}")
            print(f"  勤務タイプ: {work_type}, スケジュール: {start_time} - {end_time}")
            
            result = check_attendance_vs_schedule(str(emp_id), work_date)
            if result['status'] == 'success':
                alerts = result['data']['alerts']
                if alerts:
                    print(f"  ✓ エラー検出成功: {len(alerts)}件")
                    for alert in alerts:
                        print(f"    - [{alert['type']}] {alert['message']}")
                else:
                    print("  ❌ エラー検出失敗（アラートなし）")
    
    # 2. 休日に打刻がある場合のテスト
    print("\n2. 休日に打刻がある場合の検出テスト:")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 休日のスケジュールで打刻がある場合を探す
        cursor.execute("""
            SELECT s.employee_id, s.work_date, s.work_type, e.idm
            FROM attend_schedule s
            JOIN employee_master e ON s.employee_id = e.employee_num
            JOIN attendance a ON e.idm = a.idm AND date(a.timestamp) = s.work_date
            WHERE (s.work_type LIKE '%有%' OR s.work_type LIKE '%所%' OR s.work_type LIKE '%法%')
            LIMIT 5
        """)
        holiday_punch_cases = cursor.fetchall()
        
        for case in holiday_punch_cases:
            emp_id, work_date, work_type, idm = case
            print(f"\n休日打刻のチェック: 従業員ID {emp_id}, 日付 {work_date}")
            print(f"  勤務タイプ: {work_type}")
            
            result = check_attendance_vs_schedule(str(emp_id), work_date)
            if result['status'] == 'success':
                alerts = result['data']['alerts']
                if alerts:
                    print(f"  ✓ エラー検出成功: {len(alerts)}件")
                    for alert in alerts:
                        print(f"    - [{alert['type']}] {alert['message']}")
                else:
                    print("  ❌ エラー検出失敗（アラートなし）")
    
    # 3. 出退勤時刻の差異チェックテスト
    print("\n3. 出退勤時刻差異の検出テスト:")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 日勤で打刻があるパターンを探す
        cursor.execute("""
            SELECT s.employee_id, s.work_date, s.work_type, s.start_time, s.end_time, e.idm
            FROM attend_schedule s
            JOIN employee_master e ON s.employee_id = e.employee_num
            JOIN attendance a ON e.idm = a.idm AND date(a.timestamp) = s.work_date
            WHERE s.work_type LIKE '%日勤%'
            AND s.start_time IS NOT NULL
            AND s.end_time IS NOT NULL
            GROUP BY s.employee_id, s.work_date, s.work_type, s.start_time, s.end_time, e.idm
            LIMIT 3
        """)
        time_diff_cases = cursor.fetchall()
        
        for case in time_diff_cases:
            emp_id, work_date, work_type, start_time, end_time, idm = case
            print(f"\n時刻差異のチェック: 従業員ID {emp_id}, 日付 {work_date}")
            print(f"  勤務タイプ: {work_type}, スケジュール: {start_time} - {end_time}")
            
            # 実際の打刻時刻を表示
            cursor.execute("""
                SELECT timestamp FROM attendance 
                WHERE idm = ? AND date(timestamp) = ?
                ORDER BY timestamp
            """, (idm, work_date))
            punches = cursor.fetchall()
            print(f"  実際の打刻: {[p[0] for p in punches]}")
            
            result = check_attendance_vs_schedule(str(emp_id), work_date)
            if result['status'] == 'success':
                data = result['data']
                print(f"  出勤時刻: {data['actual_clock_in']}, 退勤時刻: {data['actual_clock_out']}")
                alerts = data['alerts']
                if alerts:
                    print(f"  ✓ アラート検出: {len(alerts)}件")
                    for alert in alerts:
                        print(f"    - [{alert['type']}] {alert['message']}")
                else:
                    print("  問題なし（差異30分未満またはその他の理由）")

    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    test_error_patterns()