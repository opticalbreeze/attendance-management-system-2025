#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特定従業員の詳細データ確認
"""
import sqlite3
from config import Config

# データベース設定（config.pyから取得）
DATABASE_PATH = Config.DATABASE_PATH

def check_specific_employee(employee_id, employee_name):
    """特定従業員の詳細データをチェック"""
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        print(f"\n=== {employee_name} ({employee_id}) の詳細データ ===")
        
        # 11/15-11/16, 12/14-12/15の4日間をチェック
        target_dates = ['2025-11-15', '2025-11-16', '2025-12-14', '2025-12-15']
        
        cursor.execute("""
            SELECT work_date, work_type, start_time, end_time, sheet_number
            FROM attend_schedule 
            WHERE employee_id = ? AND work_date IN (?, ?, ?, ?)
            ORDER BY work_date
        """, (employee_id, *target_dates))
        
        results = cursor.fetchall()
        
        if results:
            print("日付        | 勤務区分    | 開始時間 | 終了時間 | シート")
            print("-" * 55)
            for work_date, work_type, start_time, end_time, sheet_number in results:
                start_str = start_time if start_time else "---"
                end_str = end_time if end_time else "---"
                sheet_str = sheet_number if sheet_number else "---"
                print(f"{work_date} | {work_type:10} | {start_str:8} | {end_str:8} | {sheet_str}")
        else:
            print("データが見つかりません")
    
    finally:
        conn.close()

def main():
    """メイン処理"""
    
    # 問題が見つかった従業員を詳しくチェック
    employees_to_check = [
        ("4452133", "井上　誠二"),  # 区分の不一致
        ("3852120", "楠本　忠晴"),  # 時刻フォーマット
        ("2952089", "横山　正明"),  # 時刻フォーマット
        ("3852035", "大仲　五十夫") # 時刻フォーマット
    ]
    
    for emp_id, emp_name in employees_to_check:
        check_specific_employee(emp_id, emp_name)

if __name__ == "__main__":
    main()