#!/usr/bin/env python3
import sys
sys.path.append('/app')
import sqlite3
from work_type_constants import is_off_day_shift

def debug_calculation():
    conn = sqlite3.connect('/app/data/attendance.db')
    cursor = conn.cursor()
    
    employee_num = '3652025'
    work_date = '2025-12-09'
    start_time = '04:00'
    end_time = '06:00'
    
    print(f"=== デバッグ開始 ===")
    print(f"従業員: {employee_num}, 日付: {work_date}, 時間: {start_time}-{end_time}")
    
    # ステップ1: 当日のスケジュールを取得
    cursor.execute("""
        SELECT start_time, end_time, work_type FROM attend_schedule
        WHERE employee_id = ? AND work_date = ?
    """, (str(employee_num), work_date))
    
    schedule = cursor.fetchone()
    print(f"\n当日スケジュール: {schedule}")
    
    if schedule:
        work_type = schedule[2]
        scheduled_start = schedule[0]
        scheduled_end = schedule[1]
        print(f"勤務タイプ: {work_type}")
        print(f"is_off_day_shift(work_type): {is_off_day_shift(work_type)}")
        
        # ステップ2: 「明」勤務かどうか確認
        if work_type and is_off_day_shift(work_type):
            print(f"\n「明」勤務なので前日の24勤を検索...")
            
            from datetime import datetime, timedelta
            current_date = datetime.strptime(work_date, '%Y-%m-%d').date()
            prev_date = (current_date - timedelta(days=1)).strftime('%Y-%m-%d')
            print(f"前日日付: {prev_date}")
            
            # 前日の24勤・夜勤スケジュールを取得
            cursor.execute("""
                SELECT start_time, end_time, work_type FROM attend_schedule
                WHERE employee_id = ? AND work_date = ? AND (work_type LIKE '%24勤%' OR work_type LIKE '%夜勤%')
            """, (str(employee_num), prev_date))
            
            prev_schedule = cursor.fetchone()
            print(f"前日24勤スケジュール: {prev_schedule}")
            
            if prev_schedule and prev_schedule[0] and prev_schedule[1]:
                scheduled_start = prev_schedule[0]
                scheduled_end = prev_schedule[1]
                work_type = prev_schedule[2]
                print(f"採用スケジュール: {scheduled_start}-{scheduled_end} ({work_type})")
            else:
                print("前日の24勤スケジュールが見つかりません")
        
        print(f"\n最終的なスケジュール: {scheduled_start}-{scheduled_end}")
        
        if scheduled_start and scheduled_end:
            # 時刻を分に変換
            def time_to_minutes(time_str):
                h, m = map(int, time_str.split(':'))
                return h * 60 + m
            
            overtime_start_min = time_to_minutes(start_time)
            overtime_end_min = time_to_minutes(end_time)
            scheduled_start_min = time_to_minutes(scheduled_start)
            scheduled_end_min = time_to_minutes(scheduled_end)
            
            print(f"\n分換算:")
            print(f"時間外: {overtime_start_min}-{overtime_end_min}")
            print(f"スケジュール: {scheduled_start_min}-{scheduled_end_min}")
            
            # 24時間勤務の場合、時間外作業が翌日の場合は調整が必要
            if scheduled_end == scheduled_start:  # 8:30-8:30 = 24時間勤務
                scheduled_end_min = scheduled_start_min + 1440
                print(f"24時間勤務として調整: {scheduled_start_min}-{scheduled_end_min}")
                
                # 時間外作業が翌日の早朝の場合、翌日の時刻として調整
                if overtime_start_min < scheduled_start_min:  # 4:00 < 8:30
                    print(f"時間外作業が翌日の早朝 → 翌日の時刻として調整")
                    overtime_start_min += 1440  # 翌日の4:00
                    overtime_end_min += 1440    # 翌日の6:00
                    print(f"時間外（翌日調整後）: {overtime_start_min}-{overtime_end_min}")
            
            # 日をまたぐ場合の処理
            if overtime_end_min < overtime_start_min:
                overtime_end_min += 1440
                print(f"時間外（日跨ぎ調整）: {overtime_start_min}-{overtime_end_min}")
            
            # 内残業の計算
            total_overtime_minutes = overtime_end_min - overtime_start_min
            inner_minutes = 0
            
            # 時間外作業がスケジュール時間内にある部分を計算
            if overtime_start_min < scheduled_end_min and overtime_end_min > scheduled_start_min:
                inner_start_min = max(overtime_start_min, scheduled_start_min)
                inner_end_min = min(overtime_end_min, scheduled_end_min)
                if inner_end_min > inner_start_min:
                    inner_minutes = inner_end_min - inner_start_min
            
            outer_minutes = total_overtime_minutes - inner_minutes
            
            print(f"\n計算結果:")
            print(f"総時間外: {total_overtime_minutes}分")
            print(f"内残業: {inner_minutes}分")
            print(f"外残業: {outer_minutes}分")
            print(f"分類: {'内残業' if inner_minutes > 0 else '外残業'}")
    
    conn.close()

if __name__ == "__main__":
    debug_calculation()