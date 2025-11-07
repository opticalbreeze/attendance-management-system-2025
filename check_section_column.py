#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""employee_masterテーブルのsectionカラム確認スクリプト"""

import sqlite3
import os

db_path = r'C:\Users\take_me_hospital\attendance\data\attendance.db'

print("=" * 80)
print("employee_masterテーブルのsectionカラム確認")
print("=" * 80)
print(f"データベースパス: {db_path}")
print(f"ファイル存在: {os.path.exists(db_path)}")
print()

if not os.path.exists(db_path):
    print("❌ データベースファイルが見つかりません")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # カラム一覧を取得
    cursor.execute("PRAGMA table_info(employee_master)")
    cols = cursor.fetchall()
    
    print("【カラム一覧】")
    column_names = []
    for col in cols:
        print(f"  {col[1]} ({col[2]})")
        column_names.append(col[1])
    
    print()
    
    # sectionカラムの存在確認
    has_section = 'section' in column_names
    print(f"【sectionカラムの存在】: {'✅ 存在する' if has_section else '❌ 存在しない'}")
    print()
    
    # レコード数
    cursor.execute("SELECT COUNT(*) FROM employee_master")
    count = cursor.fetchone()[0]
    print(f"【レコード数】: {count}件")
    print()
    
    # サンプルデータ
    if has_section:
        cursor.execute("SELECT employee_num, name, section FROM employee_master LIMIT 10")
        rows = cursor.fetchall()
        print("【サンプルデータ（最初の10件）】")
        for r in rows:
            print(f"  従業員番号: {r[0]}, 名前: {r[1]}, セクション: {r[2]}")
        
        # sectionの値の分布
        cursor.execute("SELECT section, COUNT(*) FROM employee_master GROUP BY section")
        section_dist = cursor.fetchall()
        print()
        print("【セクション別の件数】")
        for sec, cnt in section_dist:
            print(f"  {sec}: {cnt}件")
    else:
        cursor.execute("SELECT employee_num, name FROM employee_master LIMIT 10")
        rows = cursor.fetchall()
        print("【サンプルデータ（最初の10件）】")
        for r in rows:
            print(f"  従業員番号: {r[0]}, 名前: {r[1]}")
        print()
        print("⚠️ sectionカラムが存在しないため、マイグレーションが必要です")
    
    conn.close()
    
except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()

