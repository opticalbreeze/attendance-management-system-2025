#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
現在のデータベース状況を確認するスクリプト
"""

import sqlite3
import os

# データベースパス
DB_PATH = r'c:\Users\take_me_hospital\attendance\data\attendance.db'

def check_current_data():
    """現在のデータベース状況を確認"""
    print("="*60)
    print("データベース現状確認")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 総レコード数
    cursor.execute("SELECT COUNT(*) FROM attend_schedule")
    total_count = cursor.fetchone()[0]
    print(f"📊 attend_schedule総レコード数: {total_count}")
    
    # 2026/01/16-02/15期間のレコード数
    cursor.execute("""
        SELECT COUNT(*) FROM attend_schedule 
        WHERE work_date BETWEEN '2026-01-16' AND '2026-02-15'
    """)
    period_count = cursor.fetchone()[0]
    print(f"📅 2026/01/16-02/15期間のレコード数: {period_count}")
    
    # 従業員別の件数確認（2026/01/16-02/15期間）
    cursor.execute("""
        SELECT employee_name, COUNT(*) 
        FROM attend_schedule 
        WHERE work_date BETWEEN '2026-01-16' AND '2026-02-15'
        GROUP BY employee_id, employee_name 
        ORDER BY employee_name
    """)
    employee_counts = cursor.fetchall()
    
    if employee_counts:
        print(f"\n📋 従業員別レコード数 (2026/01/16-02/15):")
        for name, count in employee_counts:
            print(f"  {name}: {count}件")
        
        # サンプルデータ表示
        print(f"\n🎯 データサンプル:")
        cursor.execute("""
            SELECT employee_name, work_date, work_type, start_time, end_time
            FROM attend_schedule 
            WHERE work_date BETWEEN '2026-01-16' AND '2026-02-15'
            ORDER BY employee_name, work_date
            LIMIT 10
        """)
        sample_data = cursor.fetchall()
        for data in sample_data:
            print(f"  {data[0]} | {data[1]} | {data[2]} | {data[3]} - {data[4]}")
    else:
        print("\n❌ 2026/01/16-02/15期間のデータはありません")
    
    conn.close()

if __name__ == "__main__":
    check_current_data()