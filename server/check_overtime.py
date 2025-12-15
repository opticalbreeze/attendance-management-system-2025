#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/app/data/attendance.db')
cursor = conn.cursor()

print("=== 12/9の時間外申告データ ===")
cursor.execute("""
    SELECT work_date, start_time, end_time, overtime_type, 
           inner_overtime_hours, outer_overtime_hours, night_overtime_hours, work_content 
    FROM overtime_applications 
    WHERE employee_id = '3652025' AND work_date = '2025-12-09'
    ORDER BY start_time
""")

results = cursor.fetchall()
for row in results:
    print(f"日付: {row[0]}")
    print(f"時間: {row[1]}-{row[2]}")
    print(f"分類: {row[3]}")
    print(f"内残業: {row[4]}h, 外残業: {row[5]}h, 深夜: {row[6]}h")
    print(f"内容: {row[7]}")
    print("---")

print("\n=== 12/8-12/9のスケジュール ===")
cursor.execute("""
    SELECT work_date, work_type, start_time, end_time 
    FROM attend_schedule 
    WHERE employee_id = '3652025' AND (work_date = '2025-12-08' OR work_date = '2025-12-09')
    ORDER BY work_date
""")

results = cursor.fetchall()
for row in results:
    print(f"日付: {row[0]}, 勤務: {row[1]}, 時間: {row[2]}-{row[3]}")

conn.close()