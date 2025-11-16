#!/usr/bin/env python3
import sqlite3

# データベースに接続
conn = sqlite3.connect('/app/data/attendance.db')

# テーブルスキーマ確認
print("=== attend_schedule テーブルスキーマ ===")
cursor = conn.execute('PRAGMA table_info(attend_schedule)')
rows = cursor.fetchall()

print(f"{'列番号':<5} {'列名':<20} {'型':<15} {'NULL許可':<8} {'デフォルト':<10} {'主キー':<5}")
print("-" * 70)

for row in rows:
    col_id, col_name, col_type, not_null, default_val, primary_key = row
    null_allowed = "No" if not_null else "Yes"
    is_primary = "Yes" if primary_key else "No"
    default_str = str(default_val) if default_val is not None else "NULL"
    
    print(f"{col_id:<5} {col_name:<20} {col_type:<15} {null_allowed:<8} {default_str:<10} {is_primary:<5}")

print("\n=== CSVカラムマッピング ===")
print("CSVファイルのカラムとattend_scheduleテーブルカラムの対応:")
print()
print("CSVカラム名     -> テーブルカラム名")
print("-" * 40)
print("ID            -> employee_id")
print("名前          -> employee_name") 
print("日付          -> work_date")
print("区分          -> work_type")
print("開始時間      -> start_time")
print("終了時間      -> end_time")
print()
print("※ sheet_number カラムがNOT NULL制約でエラーになっています")
print("※ このカラムに対応するCSVカラムがないため、デフォルト値を設定する必要があります")

conn.close()