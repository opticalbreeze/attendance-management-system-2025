#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重複打刻除去機能のテスト
"""

import sys
import os
from datetime import datetime, date
from typing import List, Dict, Any

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from attendance_check_service import (
    AttendanceCheckResult, 
    calculate_actual_clock_times,
    extract_time_from_timestamp
)

def create_test_attendance_records(times: List[str]) -> List[Dict[str, Any]]:
    """テスト用の打刻記録を作成"""
    records = []
    for i, time_str in enumerate(times):
        records.append({
            'id': i + 1,
            'time': f"2025-01-22 {time_str}:00",  # 今日の日付で作成
            'terminal_id': 'TERM001'
        })
    return records

def test_duplicate_removal():
    """重複打刻除去のテスト"""
    print("=== 重複打刻除去テスト ===")
    
    # テストケース1: 同一時刻（分単位）の重複打刻
    print("\n【テストケース1】朝の同一時刻重複打刻")
    result1 = AttendanceCheckResult(
        employee_id="EMP001",
        employee_name="テスト太郎",
        check_date="2025-01-22"
    )
    
    # スケジュール情報を設定
    result1.schedule = {'work_type': '日勤', 'start_time': '08:30', 'end_time': '17:30'}
    
    # 08:30 に2回打刻（重複）
    result1.attendance_records = create_test_attendance_records([
        "08:30", "08:30", "17:30"
    ])
    
    print(f"処理前の打刻数: {len(result1.attendance_records)}件")
    for record in result1.attendance_records:
        print(f"  - {record['time']}")
    
    # 重複除去処理を実行
    calculate_actual_clock_times(result1, None)
    
    print(f"処理後の打刻数: {len(result1.attendance_records)}件")
    for record in result1.attendance_records:
        print(f"  - {record['time']}")
    
    print(f"出勤時刻: {result1.actual_clock_in}")
    print(f"退勤時刻: {result1.actual_clock_out}")
    
    # テストケース2: 秒単位での重複（分は異なる）
    print("\n【テストケース2】秒単位の重複（分は異なる）")
    result2 = AttendanceCheckResult(
        employee_id="EMP002",
        employee_name="テスト花子",
        check_date="2025-01-22"
    )
    
    # スケジュール情報を設定
    result2.schedule = {'work_type': '日勤', 'start_time': '09:00', 'end_time': '18:00'}
    
    # 08:59 と 09:00 （異なる分なので重複除去されない）
    result2.attendance_records = create_test_attendance_records([
        "08:59", "09:00", "18:00"
    ])
    
    print(f"処理前の打刻数: {len(result2.attendance_records)}件")
    for record in result2.attendance_records:
        print(f"  - {record['time']}")
    
    calculate_actual_clock_times(result2, None)
    
    print(f"処理後の打刻数: {len(result2.attendance_records)}件")
    for record in result2.attendance_records:
        print(f"  - {record['time']}")
    
    print(f"出勤時刻: {result2.actual_clock_in}")
    print(f"退勤時刻: {result2.actual_clock_out}")
    
    # テストケース3: 3回以上の同一時刻重複
    print("\n【テストケース3】3回の同一時刻重複打刻")
    result3 = AttendanceCheckResult(
        employee_id="EMP003",
        employee_name="テスト次郎",
        check_date="2025-01-22"
    )
    
    # スケジュール情報を設定
    result3.schedule = {'work_type': '日勤', 'start_time': '08:00', 'end_time': '17:00'}
    
    # 08:00 に3回打刻（重複）
    result3.attendance_records = create_test_attendance_records([
        "08:00", "08:00", "08:00", "17:00"
    ])
    
    print(f"処理前の打刻数: {len(result3.attendance_records)}件")
    for record in result3.attendance_records:
        print(f"  - {record['time']}")
    
    calculate_actual_clock_times(result3, None)
    
    print(f"処理後の打刻数: {len(result3.attendance_records)}件")
    for record in result3.attendance_records:
        print(f"  - {record['time']}")
    
    print(f"出勤時刻: {result3.actual_clock_in}")
    print(f"退勤時刻: {result3.actual_clock_out}")

def test_time_extraction():
    """時刻抽出機能のテスト"""
    print("\n=== 時刻抽出テスト ===")
    
    test_timestamps = [
        "2025-01-22 08:30:15",
        "2025-01-22 08:30:45", 
        "2025-01-22 09:00:00",
        "2025-01-22 17:30:30"
    ]
    
    for ts in test_timestamps:
        time_str = extract_time_from_timestamp(ts)
        time_hhmm = time_str[:5] if time_str and len(time_str) >= 5 else time_str
        print(f"{ts} → {time_str} → {time_hhmm}")

if __name__ == "__main__":
    test_time_extraction()
    test_duplicate_removal()
    print("\nテスト完了！")