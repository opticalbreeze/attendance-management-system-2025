#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/app/data/attendance.db')
cursor = conn.cursor()

print("=== attend_schedule テーブル構造 ===")
cursor.execute("PRAGMA table_info(attend_schedule)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col[1]} ({col[2]})")

print("\n=== サンプルデータ ===")
cursor.execute("SELECT * FROM attend_schedule LIMIT 3")
samples = cursor.fetchall()
for sample in samples:
    print(f"  {sample}")

conn.close()