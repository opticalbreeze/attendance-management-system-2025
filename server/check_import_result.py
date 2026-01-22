#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
インポート結果確認スクリプト
"""

import sqlite3
from datetime import datetime

# データベースファイルのパス
DB_PATH = r'c:\Users\take_me_hospital\attendance\data\attendance.db'

def check_import_result():
    """インポート結果の確認"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("=== CSVインポート結果確認 ===\n")
        
        # 期間別のデータ件数確認
        cursor.execute("""
            SELECT COUNT(*) FROM attend_schedule 
            WHERE work_date BETWEEN '2025-12-16' AND '2026-01-15'
        """)
        total_count = cursor.fetchone()[0]
        print(f"対象期間のデータ件数: {total_count}件 (2025/12/16 - 2026/1/15)")
        
        # 従業員別データ件数
        cursor.execute("""
            SELECT employee_name, COUNT(*) as count
            FROM attend_schedule 
            WHERE work_date BETWEEN '2025-12-16' AND '2026-01-15'
            GROUP BY employee_name
            ORDER BY employee_name
        """)
        emp_counts = cursor.fetchall()
        print(f"\n=== 従業員別データ件数 ({len(emp_counts)}名) ===")
        for name, count in emp_counts:
            print(f"  {name}: {count}件")
        
        # 勤務タイプ別集計
        cursor.execute("""
            SELECT work_type, COUNT(*) as count
            FROM attend_schedule 
            WHERE work_date BETWEEN '2025-12-16' AND '2026-01-15'
            GROUP BY work_type
            ORDER BY count DESC
        """)
        work_types = cursor.fetchall()
        print(f"\n=== 勤務タイプ別集計 ===")
        for work_type, count in work_types:
            print(f"  {work_type}: {count}件")
        
        # 最新のデータ5件をサンプル表示
        cursor.execute("""
            SELECT employee_name, work_date, work_type, start_time, end_time
            FROM attend_schedule 
            WHERE work_date BETWEEN '2025-12-16' AND '2026-01-15'
            ORDER BY work_date DESC, employee_name
            LIMIT 5
        """)
        latest_data = cursor.fetchall()
        print(f"\n=== 最新データサンプル (5件) ===")
        for emp_name, work_date, work_type, start_time, end_time in latest_data:
            print(f"  {emp_name} | {work_date} | {work_type} | {start_time or '-'} - {end_time or '-'}")
        
        # 2026年1月のデータ件数確認
        cursor.execute("""
            SELECT COUNT(*) FROM attend_schedule 
            WHERE work_date >= '2026-01-01' AND work_date <= '2026-01-15'
        """)
        jan_count = cursor.fetchone()[0]
        print(f"\n=== 2026年1月度データ確認 ===")
        print(f"2026年1月のデータ件数: {jan_count}件 (1/1-1/15)")
        
        # 2026年1月の従業員別件数
        cursor.execute("""
            SELECT employee_name, COUNT(*) as count
            FROM attend_schedule 
            WHERE work_date >= '2026-01-01' AND work_date <= '2026-01-15'
            GROUP BY employee_name
            ORDER BY employee_name
        """)
        jan_emp_counts = cursor.fetchall()
        print(f"2026年1月の従業員別データ件数:")
        for name, count in jan_emp_counts:
            print(f"  {name}: {count}件")
        
        conn.close()
        print(f"\n✓ インポート結果確認完了")
        print(f"✓ 総データ数: {total_count}件が正常にインポートされています")
        
    except Exception as e:
        print(f"✗ エラー: {e}")

if __name__ == "__main__":
    check_import_result()
    input("\nEnterキーを押して終了してください...")