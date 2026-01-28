#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSVファイルから勤怠スケジュールデータを一括挿入するスクリプト（全データ）
"""

import sqlite3
import csv
import os
from datetime import datetime

# データベースパス
DB_PATH = r'c:\Users\take_me_hospital\attendance\data\attendance.db'
CSV_PATH = r'c:\Users\take_me_hospital\attendance\統合勤怠データ_20260122_093843.csv'

def insert_all_csv_data():
    """CSVファイルから勤怠スケジュールデータを読み込んで一括挿入"""
    print("="*60)
    print("CSVから全勤怠スケジュールデータ一括挿入")
    print("="*60)
    
    # CSVファイルの存在確認
    if not os.path.exists(CSV_PATH):
        print(f"❌ CSVファイルが見つかりません: {CSV_PATH}")
        return
    
    # データベース接続
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 既存の同期間データを削除
    print("🗑️  2026年1月16日～2月15日の既存データを削除中...")
    cursor.execute("""
        DELETE FROM attend_schedule 
        WHERE work_date BETWEEN '2026-01-16' AND '2026-02-15'
    """)
    deleted_count = cursor.rowcount
    print(f"✅ {deleted_count}件の既存データを削除しました")
    
    # CSVファイル読み込み
    schedule_data = []
    
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            header = next(csv_reader)  # ヘッダー行をスキップ
            print(f"📁 CSVヘッダー: {header}")
            
            for row_num, row in enumerate(csv_reader, start=2):
                if len(row) < 7:
                    print(f"⚠️  行{row_num}: データが不完全です - {row}")
                    continue
                
                sheet_number, employee_id, employee_name, date_str, work_type, start_time, end_time = row
                
                # 日付フォーマット変換 (2026/1/16 → 2026-01-16)
                try:
                    date_parts = date_str.split('/')
                    work_date = f"{date_parts[0]}-{date_parts[1]:0>2}-{date_parts[2]:0>2}"
                except:
                    print(f"⚠️  行{row_num}: 日付フォーマットエラー - {date_str}")
                    continue
                
                # 空の時間をNullに変換
                start_time = start_time if start_time.strip() else None
                end_time = end_time if end_time.strip() else None
                
                schedule_data.append((
                    sheet_number,
                    employee_id,
                    employee_name,
                    work_date,
                    work_type,
                    start_time,
                    end_time
                ))
                
        print(f"📊 CSVから読み込んだデータ件数: {len(schedule_data)}")
        
        # データ挿入
        insert_sql = """
            INSERT INTO attend_schedule 
            (sheet_number, employee_id, employee_name, work_date, work_type, start_time, end_time) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor.executemany(insert_sql, schedule_data)
        conn.commit()
        
        print(f"✅ {len(schedule_data)} 件のスケジュールデータを挿入しました")
        
        # 挿入結果確認
        cursor.execute("SELECT COUNT(*) FROM attend_schedule")
        total_count = cursor.fetchone()[0]
        print(f"📊 データベース総レコード数: {total_count}")
        
        # 期間別確認
        cursor.execute("""
            SELECT COUNT(*) FROM attend_schedule 
            WHERE work_date BETWEEN '2026-01-16' AND '2026-02-15'
        """)
        period_count = cursor.fetchone()[0]
        print(f"📅 2026/01/16-02/15期間のレコード数: {period_count}")
        
        # 従業員別の件数確認
        cursor.execute("""
            SELECT employee_name, COUNT(*) 
            FROM attend_schedule 
            WHERE work_date BETWEEN '2026-01-16' AND '2026-02-15'
            GROUP BY employee_id, employee_name 
            ORDER BY employee_name
        """)
        employee_counts = cursor.fetchall()
        
        print(f"\n📋 従業員別レコード数 (2026/01/16-02/15):")
        for name, count in employee_counts:
            print(f"  {name}: {count}件")
        
        print(f"\n🎯 データ例 (最初の5件):")
        cursor.execute("""
            SELECT employee_name, work_date, work_type, start_time, end_time
            FROM attend_schedule 
            WHERE work_date BETWEEN '2026-01-16' AND '2026-02-15'
            ORDER BY work_date, employee_name
            LIMIT 5
        """)
        sample_data = cursor.fetchall()
        for data in sample_data:
            print(f"  {data[0]} | {data[1]} | {data[2]} | {data[3]} - {data[4]}")
            
    except Exception as e:
        print(f"❌ CSV処理エラー: {e}")
        conn.rollback()
        return
    
    conn.close()
    print(f"\n{'='*60}")
    print("CSV一括挿入完了！")
    print(f"{'='*60}")

def main():
    """メイン処理"""
    print("勤怠スケジュールCSV一括挿入ツール（全データ）")
    print(f"CSVファイル: {CSV_PATH}")
    print(f"データベース: {DB_PATH}")
    
    # 確認
    choice = input("\nCSVファイルから全データを一括挿入しますか？ (y/n): ")
    if choice.lower() != 'y':
        print("キャンセルしました")
        return
    
    insert_all_csv_data()

if __name__ == "__main__":
    main()