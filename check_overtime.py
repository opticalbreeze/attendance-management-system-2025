#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""時間外申告データ確認スクリプト"""

import sqlite3
import sys
import os

# Windowsコンソールの文字化け対策
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_PATH = r'C:\Users\take_me_hospital\attendance\data\attendance.db'

print("=" * 80)
print("時間外申告データ確認")
print("=" * 80)
print(f"データベースパス: {DB_PATH}")
print(f"ファイル存在: {os.path.exists(DB_PATH)}")
print()

if not os.path.exists(DB_PATH):
    print("ERROR: データベースファイルが見つかりません")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# テーブル存在確認
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='overtime_applications'")
table_exists = cursor.fetchone()

if not table_exists:
    print("【時間外申告テーブル】 テーブルが存在しません")
    print("サーバーを起動してテーブルを作成してください")
    conn.close()
    exit(0)

print("【時間外申告テーブル】 存在確認: OK")
print()

# テーブル構造確認
cursor.execute("PRAGMA table_info(overtime_applications)")
columns = cursor.fetchall()
print("【テーブル構造】")
for col in columns:
    print(f"  - {col[1]}: {col[2]}")
print()

# 件数確認
cursor.execute("SELECT COUNT(*) FROM overtime_applications")
total_count = cursor.fetchone()[0]
print(f"【登録件数】 全体: {total_count}件")

if total_count > 0:
    # ステータス別件数
    cursor.execute("SELECT status, COUNT(*) FROM overtime_applications GROUP BY status")
    status_counts = cursor.fetchall()
    print("【ステータス別】")
    for status, count in status_counts:
        print(f"  - {status}: {count}件")
    print()
    
    # 最新の申告を表示
    cursor.execute("""
        SELECT id, employee_num, employee_name, work_date, start_time, end_time,
               overtime_type, inner_overtime_minutes, outer_overtime_minutes, 
               night_overtime_minutes, status, created_at
        FROM overtime_applications
        ORDER BY created_at DESC
        LIMIT 5
    """)
    records = cursor.fetchall()
    
    print("【最新の時間外申告】 (最大5件)")
    for i, rec in enumerate(records, 1):
        print(f"\n  [{i}] ID: {rec[0]}")
        print(f"      従業員: {rec[2]} ({rec[1]})")
        print(f"      作業日: {rec[3]}")
        print(f"      時間: {rec[4]} - {rec[5]}")
        print(f"      分類: {rec[6]}")
        print(f"      内残業: {rec[7]}分 / 外残業: {rec[8]}分 / 深夜: {rec[9]}分")
        print(f"      ステータス: {rec[10]}")
        print(f"      申告日時: {rec[11]}")
else:
    print()
    print("まだ時間外申告のデータが登録されていません")
    print("ブラウザで http://localhost:5000/overtime にアクセスして申告してください")

conn.close()

print()
print("=" * 80)
print("確認完了")
print("=" * 80)

