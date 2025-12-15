#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/app/data/attendance.db')
cursor = conn.cursor()

print("=== overtime_applicationsテーブル構造 ===")
cursor.execute("PRAGMA table_info(overtime_applications)")
columns = cursor.fetchall()
for col in columns:
    print(f"列: {col[1]}, 型: {col[2]}")

print("\n=== 12/9の時間外申告データ ===")
cursor.execute("""
    SELECT * FROM overtime_applications 
    WHERE employee_id = '3652025' AND work_date = '2025-12-09'
    ORDER BY start_time
""")

results = cursor.fetchall()
for row in results:
    print(f"レコード: {row}")

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