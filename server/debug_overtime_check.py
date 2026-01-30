#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
時間外申告と退勤時刻差異チェックの実証コード
玉置公一（employee_num=4252061）専用デバッグスクリプト
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from attendance_check_service import AttendanceCheckResult, check_time_difference_errors, _get_overtime_applications_safe, _check_overtime_time_within_tolerance
from utils import get_db_connection
from constants import AttendanceConstants

def debug_overtime_check():
    """玉置公一の2026-01-24の退勤時刻差異チェックを実証"""
    
    employee_id = "4252061"
    employee_name = "玉置 公"
    check_date = "2026-01-24"
    
    print("=" * 80)
    print(f"【実証コード実行】")
    print(f"従業員: {employee_name} ({employee_id})")
    print(f"日付: {check_date}")
    print("=" * 80)
    
    # データベース接続を開く（すべてのステップで使用）
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. スケジュール情報を取得
        print("\n【ステップ1】スケジュール情報の取得")
        print("-" * 80)
        cursor.execute("""
            SELECT work_date, work_type, start_time, end_time
            FROM attend_schedule
            WHERE employee_id = ? AND work_date = ?
        """, (employee_id, check_date))
        
        schedule_row = cursor.fetchone()
        if schedule_row:
            schedule = {
                'work_date': schedule_row[0],
                'work_type': schedule_row[1],
                'start_time': schedule_row[2],
                'end_time': schedule_row[3]
            }
            print(f"[OK] スケジュール取得成功:")
            print(f"  work_date: {schedule['work_date']}")
            print(f"  work_type: {schedule['work_type']}")
            print(f"  start_time: {schedule['start_time']}")
            print(f"  end_time: {schedule['end_time']}")
        else:
            print("[NG] スケジュールが見つかりません")
            return
        
        # 2. 打刻記録を取得
        print("\n【ステップ2】打刻記録の取得")
        print("-" * 80)
        cursor.execute("""
            SELECT idm FROM employee_master WHERE employee_num = ?
        """, (employee_id,))
        idm_result = cursor.fetchone()
        
        if not idm_result:
            print("[NG] 従業員マスタが見つかりません")
            return
        
        idm = idm_result[0]
        print(f"[OK] IDm取得: {idm}")
        
        cursor.execute("""
            SELECT id, timestamp, terminal_id
            FROM attendance
            WHERE idm = ? AND date(timestamp) = ?
            ORDER BY timestamp ASC
        """, (idm, check_date))
        
        attendance_records = []
        for row in cursor.fetchall():
            attendance_records.append({
                'id': row[0],
                'time': row[1],
                'terminal_id': row[2]
            })
        
        print(f"[OK] 打刻記録取得: {len(attendance_records)}件")
        for idx, record in enumerate(attendance_records):
            print(f"  打刻[{idx}]: timestamp={record['time']}, terminal_id={record['terminal_id']}")
        
        # 3. AttendanceCheckResultを作成
        print("\n【ステップ3】AttendanceCheckResultの作成")
        print("-" * 80)
        result = AttendanceCheckResult(employee_id, employee_name, check_date)
        result.schedule = schedule
        result.attendance_records = attendance_records
        
        # actual_clock_in/outを計算
        from attendance_check_service import calculate_actual_clock_times
        calculate_actual_clock_times(result, cursor)
        
        print(f"[OK] AttendanceCheckResult作成完了:")
        print(f"  actual_clock_in: {result.actual_clock_in}")
        print(f"  actual_clock_out: {result.actual_clock_out}")
        
        # 4. 時間外申告を取得
        print("\n【ステップ4】時間外申告の取得")
        print("-" * 80)
        overtime_apps = _get_overtime_applications_safe(result)
        
        print(f"[OK] 時間外申告取得完了: {len(overtime_apps)}件")
        if overtime_apps:
            for idx, app in enumerate(overtime_apps):
                print(f"  時間外申告[{idx}]:")
                print(f"    employee_num: {app.get('employee_num')}")
                print(f"    work_date: {app.get('work_date')}")
                print(f"    start_time: {app.get('start_time')}")
                print(f"    end_time: {app.get('end_time')}")
                print(f"    status: {app.get('status')}")
        else:
            print("  [NG] 時間外申告が0件です")
        
        # 5. 前日の24勤・夜勤情報を取得（「明」勤務用）
        print("\n【ステップ5】前日の24勤・夜勤情報の取得")
        print("-" * 80)
        from datetime import timedelta
        prev_date = (datetime.strptime(check_date, AttendanceConstants.DATE_FORMAT) - timedelta(days=1)).strftime(AttendanceConstants.DATE_FORMAT)
        
        from attendance_check_service import get_prev_day_night_shift
        prev_shift = get_prev_day_night_shift(cursor, employee_id, prev_date)
        if prev_shift:
            result.prev_day_night_shift = {
                'work_date': prev_shift[0],
                'work_type': prev_shift[1],
                'start_time': prev_shift[2],
                'end_time': prev_shift[3]
            }
            print(f"[OK] 前日の24勤・夜勤情報取得:")
            print(f"  work_date: {result.prev_day_night_shift['work_date']}")
            print(f"  work_type: {result.prev_day_night_shift['work_type']}")
            print(f"  start_time: {result.prev_day_night_shift['start_time']}")
            print(f"  end_time: {result.prev_day_night_shift['end_time']}")
        else:
            print("[NG] 前日の24勤・夜勤情報が見つかりません")
            return
        
        # 6. check_off_day_shift_attendance関数を実行（「明」勤務用）
        print("\n【ステップ6】check_off_day_shift_attendance関数の実行")
        print("-" * 80)
        
        from attendance_check_service import check_off_day_shift_attendance
        check_off_day_shift_attendance(cursor, result, prev_date)
        
        print(f"\n[OK] check_off_day_shift_attendance実行完了")
        print(f"  アラート件数: {len(result.alerts)}")
        for idx, alert in enumerate(result.alerts):
            print(f"  アラート[{idx}]:")
            print(f"    type: {alert.get('type')}")
            print(f"    message: {alert.get('message')}")
            print(f"    details: {alert.get('details')}")
        
        # 7. 時間外申告の終了時間と退勤打刻時刻の比較
        print("\n【ステップ7】時間外申告の終了時間と退勤打刻時刻の比較")
        print("-" * 80)
        
        actual_end = result.actual_clock_out
        if overtime_apps and actual_end:
            # タイムスタンプ形式を時刻形式（HH:MM）に変換
            from utils import extract_time_from_timestamp
            actual_end_time = extract_time_from_timestamp(actual_end) if actual_end else None
            actual_end_hhmm = actual_end_time[:5] if actual_end_time and len(actual_end_time) >= 5 else actual_end_time
            
            for idx, app in enumerate(overtime_apps):
                app_end = app.get('end_time')
                print(f"\n時間外申告[{idx}]:")
                print(f"  終了時間: {app_end}")
                print(f"  退勤打刻時刻（タイムスタンプ）: {actual_end}")
                print(f"  退勤打刻時刻（HH:MM）: {actual_end_hhmm}")
                
                # _check_overtime_time_within_tolerance関数を直接呼び出し
                is_within_tolerance = _check_overtime_time_within_tolerance(actual_end_hhmm, [app])
                print(f"  ±30分以内か: {is_within_tolerance}")
                
                if is_within_tolerance:
                    print(f"  [OK] 時間外申告の終了時間と退勤打刻時刻が±30分以内のため、エラーを出さない")
                else:
                    print(f"  [NG] 時間外申告の終了時間と退勤打刻時刻が±30分以内ではない")
        else:
            print("[NG] 時間外申告が0件または退勤打刻時刻がありません")
        
        # 8. 結果の判定
        print("\n【ステップ8】結果の判定")
        print("-" * 80)
        
        has_clock_out_time_diff = any(
            '退勤時刻に差異あり' in (alert.get('message') or '')
            for alert in result.alerts
        )
        
        if has_clock_out_time_diff:
            print("[NG] 「退勤時刻に差異あり」アラートが生成されました")
            print("   → 時間外申告の参照が正しく機能していません")
        else:
            print("[OK] 「退勤時刻に差異あり」アラートは生成されませんでした")
            if overtime_apps:
                print("   → 時間外申告の参照が正しく機能しています")
            else:
                print("   → 時間外申告が0件のため、判定できません")
        
        print("\n" + "=" * 80)
        print("【実証コード実行完了】")
        print("=" * 80)

if __name__ == "__main__":
    debug_overtime_check()
