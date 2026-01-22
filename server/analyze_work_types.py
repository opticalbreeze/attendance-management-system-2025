#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import csv
from collections import Counter

def main():
    """勤務種別の全種類を調査"""
    
    print("=== 勤務種別 全種類調査 ===\n")
    
    # 1. データベースから取得
    print("【データベース】attend_schedule テーブル:")
    db_path = os.path.join('..', '..', 'data', 'attendance.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''SELECT work_type, COUNT(*) as count 
                         FROM attend_schedule 
                         WHERE work_type IS NOT NULL AND work_type != ''
                         GROUP BY work_type 
                         ORDER BY count DESC''')
        
        db_work_types = cursor.fetchall()
        total_db_records = sum([count for _, count in db_work_types])
        
        for work_type, count in db_work_types:
            percentage = (count / total_db_records) * 100
            print(f"  {work_type}: {count}件 ({percentage:.1f}%)")
        
        print(f"\nデータベース勤務種別数: {len(db_work_types)}種類")
        print(f"総レコード数: {total_db_records}件")
        
        conn.close()
    except Exception as e:
        print(f"データベースエラー: {e}")
    
    # 2. CSVファイルから取得
    print(f"\n【CSVファイル】統合勤怠データ:")
    csv_path = r"c:\Users\take_me_hospital\OneDrive\デスクトップ\統合勤怠データ_20260114_132404.csv"
    
    try:
        work_type_counter = Counter()
        total_csv_records = 0
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                work_type = row['区分'].strip()
                if work_type:
                    work_type_counter[work_type] += 1
                    total_csv_records += 1
        
        print(f"CSVファイルの勤務種別:")
        for work_type, count in work_type_counter.most_common():
            percentage = (count / total_csv_records) * 100
            print(f"  {work_type}: {count}件 ({percentage:.1f}%)")
        
        print(f"\nCSV勤務種別数: {len(work_type_counter)}種類")
        print(f"総レコード数: {total_csv_records}件")
        
    except Exception as e:
        print(f"CSVファイルエラー: {e}")
    
    # 3. システム定義の確認
    print(f"\n【システム定義】work_type_constants.py:")
    CSV_WORK_TYPE_MAPPING = {
        '日勤': '通常',
        '夜勤': '夜勤', 
        '法': '法定休日',
        '所': '所定休日',
        '有': '有給',
        '代': '代休',
        '特': '特休',
        '明': '明',
        '24勤A': '24勤A',
        '24勤B': '24勤B'
    }
    
    print("システムで定義されている勤務種別:")
    for csv_type, db_type in CSV_WORK_TYPE_MAPPING.items():
        print(f"  CSV '{csv_type}' → DB '{db_type}'")
    
    print(f"\nシステム定義勤務種別数: {len(CSV_WORK_TYPE_MAPPING)}種類")

if __name__ == "__main__":
    main()