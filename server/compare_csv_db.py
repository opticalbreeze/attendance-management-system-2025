#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
attend_scheduleテーブルとCSVファイルの比較チェック
"""
import csv
import sqlite3
from datetime import datetime
import os

# データベース設定
DATABASE_PATH = "../../data/attendance.db"

def read_csv_data(csv_file_path):
    """CSVファイルからデータを読み込み"""
    csv_data = {}
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    employee_id = row.get('ID', '').strip()
                    employee_name = row.get('名前', '').strip()
                    date_str = row.get('日付', '').strip()
                    work_type = row.get('区分', '').strip()
                    start_time = row.get('開始時間', '').strip()
                    end_time = row.get('終了時間', '').strip()
                    
                    if not employee_id or not date_str or date_str == "担当者入力実績":
                        continue
                    
                    # 日付フォーマット変換
                    try:
                        if '/' in date_str:
                            date_obj = datetime.strptime(date_str, '%Y/%m/%d')
                        else:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        work_date = date_obj.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
                    
                    # 勤務区分マッピング
                    work_type_mapping = {
                        '日勤': '通常',
                        '夜勤': '夜勤',
                        '法': '法定休日',
                        '所': '所定休日',
                        '有': '有給',
                        '代': '代休',
                        '特': '特休'
                    }
                    mapped_work_type = work_type_mapping.get(work_type, work_type)
                    
                    key = f"{employee_id}_{work_date}"
                    csv_data[key] = {
                        'employee_id': employee_id,
                        'employee_name': employee_name,
                        'work_date': work_date,
                        'work_type': mapped_work_type,
                        'start_time': start_time if start_time else None,
                        'end_time': end_time if end_time else None,
                        'source': os.path.basename(csv_file_path),
                        'row': row_num
                    }
                    
                except Exception as e:
                    print(f"CSV行 {row_num} エラー: {e}")
                    continue
    
    except Exception as e:
        print(f"CSVファイル読み込みエラー: {e}")
    
    return csv_data

def read_db_data():
    """データベースからデータを読み込み"""
    db_data = {}
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT employee_id, employee_name, work_date, work_type, start_time, end_time
            FROM attend_schedule
            WHERE employee_id NOT IN ('0', '15')
            ORDER BY employee_id, work_date
        """)
        
        for row in cursor.fetchall():
            employee_id, employee_name, work_date, work_type, start_time, end_time = row
            key = f"{employee_id}_{work_date}"
            db_data[key] = {
                'employee_id': employee_id,
                'employee_name': employee_name,
                'work_date': work_date,
                'work_type': work_type,
                'start_time': start_time,
                'end_time': end_time
            }
    
    except Exception as e:
        print(f"データベース読み込みエラー: {e}")
    finally:
        conn.close()
    
    return db_data

def compare_data(csv_data, db_data, comparison_dates=None):
    """データを比較"""
    
    print("=== CSVとデータベースの比較結果 ===")
    
    # フィルタリング用の日付リスト
    if comparison_dates:
        print(f"比較対象日付: {', '.join(comparison_dates)}")
        
        # 指定日付のデータのみを抽出
        filtered_csv = {k: v for k, v in csv_data.items() if v['work_date'] in comparison_dates}
        filtered_db = {k: v for k, v in db_data.items() if v['work_date'] in comparison_dates}
        csv_data = filtered_csv
        db_data = filtered_db
    
    print(f"CSV総件数: {len(csv_data)}")
    print(f"DB総件数: {len(db_data)}")
    
    # CSVにあってDBにないデータ
    only_in_csv = []
    for key, csv_record in csv_data.items():
        if key not in db_data:
            only_in_csv.append(csv_record)
    
    # DBにあってCSVにないデータ  
    only_in_db = []
    for key, db_record in db_data.items():
        if key not in csv_data:
            only_in_db.append(db_record)
    
    # 内容が異なるデータ
    different_data = []
    for key in set(csv_data.keys()) & set(db_data.keys()):
        csv_record = csv_data[key]
        db_record = db_data[key]
        
        differences = []
        if csv_record['work_type'] != db_record['work_type']:
            differences.append(f"区分: CSV='{csv_record['work_type']}' vs DB='{db_record['work_type']}'")
        if csv_record['start_time'] != db_record['start_time']:
            differences.append(f"開始: CSV='{csv_record['start_time']}' vs DB='{db_record['start_time']}'")
        if csv_record['end_time'] != db_record['end_time']:
            differences.append(f"終了: CSV='{csv_record['end_time']}' vs DB='{db_record['end_time']}'")
        
        if differences:
            different_data.append({
                'key': key,
                'csv': csv_record,
                'db': db_record,
                'differences': differences
            })
    
    # 結果表示
    print(f"\n=== CSVのみに存在 ===")
    if only_in_csv:
        print(f"件数: {len(only_in_csv)}")
        for record in only_in_csv[:10]:  # 最初の10件のみ表示
            print(f"  {record['employee_name']} ({record['employee_id']}) - {record['work_date']} - {record['work_type']} [{record['source']}]")
        if len(only_in_csv) > 10:
            print(f"  ... 他 {len(only_in_csv) - 10}件")
    else:
        print("該当なし")
    
    print(f"\n=== DBのみに存在 ===")
    if only_in_db:
        print(f"件数: {len(only_in_db)}")
        for record in only_in_db[:10]:  # 最初の10件のみ表示
            print(f"  {record['employee_name']} ({record['employee_id']}) - {record['work_date']} - {record['work_type']}")
        if len(only_in_db) > 10:
            print(f"  ... 他 {len(only_in_db) - 10}件")
    else:
        print("該当なし")
    
    print(f"\n=== 内容が異なるデータ ===")
    if different_data:
        print(f"件数: {len(different_data)}")
        for diff in different_data[:10]:  # 最初の10件のみ表示
            csv_rec = diff['csv']
            print(f"  {csv_rec['employee_name']} ({csv_rec['employee_id']}) - {csv_rec['work_date']}:")
            for d in diff['differences']:
                print(f"    {d}")
        if len(different_data) > 10:
            print(f"  ... 他 {len(different_data) - 10}件")
    else:
        print("該当なし")
    
    return {
        'only_in_csv': only_in_csv,
        'only_in_db': only_in_db,
        'different_data': different_data
    }

def main():
    """メイン処理"""
    
    # CSVファイルパス
    csv_files = [
        "\\\\DESKTOP-74DASSG\\Users\\take_me_hospital\\attendance\\統合勤怠データ_20251116_140154.csv",
        "\\\\DESKTOP-74DASSG\\Users\\take_me_hospital\\attendance\\統合勤怠データ_20251116_140306.csv"
    ]
    
    # 重要な日付に絞って比較
    comparison_dates = ['2025-11-15', '2025-11-16', '2025-12-14', '2025-12-15']
    
    print("attend_scheduleテーブルとCSVファイルの比較を開始します...")
    
    # データベースデータを読み込み
    print("\nデータベースからデータを読み込み中...")
    db_data = read_db_data()
    
    # 各CSVファイルと比較
    for csv_file in csv_files:
        if os.path.exists(csv_file):
            print(f"\n{'='*60}")
            print(f"ファイル: {os.path.basename(csv_file)}")
            print(f"{'='*60}")
            
            csv_data = read_csv_data(csv_file)
            compare_data(csv_data, db_data, comparison_dates)
        else:
            print(f"ファイルが見つかりません: {csv_file}")

if __name__ == "__main__":
    main()