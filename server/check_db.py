#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""データベース内容確認スクリプト"""

import sqlite3
import os
from config import Config

DB_PATH = Config.DATABASE_PATH

print("=" * 80)
print("📊 データベース内容確認")
print("=" * 80)
print(f"データベースパス: {DB_PATH}")
print(f"ファイル存在: {os.path.exists(DB_PATH)}")
print()

if not os.path.exists(DB_PATH):
    print("❌ データベースファイルが見つかりません")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# テーブル一覧
print("📋 テーブル一覧:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f"  - {table[0]}")
print()

# employee_masterテーブルの確認
if ('employee_master',) in tables:
    print("👥 employee_master テーブルの内容:")
    cursor.execute("SELECT * FROM employee_master LIMIT 10")
    employees = cursor.fetchall()
    
    if employees:
        print(f"  件数: {len(employees)}件")
        cursor.execute("PRAGMA table_info(employee_master)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"  カラム: {', '.join(columns)}")
        print()
        print("  データサンプル:")
        for emp in employees:
            print(f"    {emp}")
    else:
        print("  ⚠️ データが0件です")
    print()
else:
    print("❌ employee_master テーブルが存在しません")
    print()

# attend_scheduleテーブルの確認
if ('attend_schedule',) in tables:
    print("📅 attend_schedule テーブルの内容:")
    cursor.execute("SELECT COUNT(*) FROM attend_schedule")
    count = cursor.fetchone()[0]
    print(f"  件数: {count}件")
    
    if count > 0:
        cursor.execute("SELECT * FROM attend_schedule LIMIT 3")
        schedules = cursor.fetchall()
        print("  データサンプル:")
        for sch in schedules:
            print(f"    {sch}")
    print()
else:
    print("❌ attend_schedule テーブルが存在しません")
    print()

# attendanceテーブルの確認
if ('attendance',) in tables:
    print("⏰ attendance テーブルの内容:")
    cursor.execute("SELECT COUNT(*) FROM attendance")
    count = cursor.fetchone()[0]
    print(f"  件数: {count}件")
    
    if count > 0:
        cursor.execute("SELECT * FROM attendance LIMIT 3")
        attendances = cursor.fetchall()
        print("  データサンプル:")
        for att in attendances:
            print(f"    {att}")
    print()
else:
    print("❌ attendance テーブルが存在しません")
    print()

conn.close()

print("=" * 80)
print("✅ データベース確認完了")
print("=" * 80)

