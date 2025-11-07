#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ホスト側のデータベース内容確認スクリプト"""

import sqlite3
import os
import sys

# Windowsコンソールの文字化け対策
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_PATH = r'C:\Users\take_me_hospital\attendance\data\attendance.db'

print("=" * 80)
print("ホスト側データベース内容確認")
print("=" * 80)
print(f"データベースパス: {DB_PATH}")
print(f"ファイル存在: {os.path.exists(DB_PATH)}")

if os.path.exists(DB_PATH):
    size = os.path.getsize(DB_PATH)
    print(f"ファイルサイズ: {size:,} bytes")
print()

if not os.path.exists(DB_PATH):
    print("ERROR: データベースファイルが見つかりません")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# テーブル一覧
print("【テーブル一覧】")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
table_names = [t[0] for t in tables]
for table in tables:
    print(f"  - {table[0]}")
print()

# 各テーブルの件数確認
for table_name in table_names:
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"【{table_name}】 件数: {count}")

print()

# employee_masterテーブルの確認
if 'employee_master' in table_names:
    print("【employee_master テーブルの詳細】")
    cursor.execute("SELECT COUNT(*) FROM employee_master")
    count = cursor.fetchone()[0]
    print(f"  総件数: {count}件")
    
    if count > 0:
        cursor.execute("PRAGMA table_info(employee_master)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"  カラム: {', '.join(columns)}")
        
        cursor.execute("SELECT * FROM employee_master LIMIT 5")
        employees = cursor.fetchall()
        print("  データサンプル (最初の5件):")
        for i, emp in enumerate(employees, 1):
            print(f"    [{i}] {emp}")
    print()
else:
    print("【employee_master】 テーブルが存在しません")
    print()

# attend_scheduleテーブルの確認
if 'attend_schedule' in table_names:
    print("【attend_schedule テーブルの詳細】")
    cursor.execute("SELECT COUNT(*) FROM attend_schedule")
    count = cursor.fetchone()[0]
    print(f"  総件数: {count}件")
    
    if count > 0:
        cursor.execute("SELECT * FROM attend_schedule LIMIT 3")
        schedules = cursor.fetchall()
        print("  データサンプル (最初の3件):")
        for i, sch in enumerate(schedules, 1):
            print(f"    [{i}] {sch}")
    print()
else:
    print("【attend_schedule】 テーブルが存在しません")
    print()

# attendanceテーブルの確認
if 'attendance' in table_names:
    print("【attendance テーブルの詳細】")
    cursor.execute("SELECT COUNT(*) FROM attendance")
    count = cursor.fetchone()[0]
    print(f"  総件数: {count}件")
    
    if count > 0:
        cursor.execute("SELECT * FROM attendance LIMIT 3")
        attendances = cursor.fetchall()
        print("  データサンプル (最初の3件):")
        for i, att in enumerate(attendances, 1):
            print(f"    [{i}] {att}")
    print()
else:
    print("【attendance】 テーブルが存在しません")
    print()

conn.close()

print("=" * 80)
print("データベース確認完了")
print("=" * 80)
