#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
差分CSVデータをattend_scheduleテーブルに追加するスクリプト
2025/11/15と2025/12/15の抜けていたデータを追加
"""
import csv
import sqlite3
from datetime import datetime
import os

# データベース設定
DATABASE_PATH = "../../data/attendance.db"

def import_diff_csv_to_schedule(csv_file_path):
    """差分CSVファイルをattend_scheduleテーブルにインポート（重複はスキップ、新規のみ追加）"""
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 既存データの確認
    cursor.execute("SELECT COUNT(*) FROM attend_schedule")
    before_count = cursor.fetchone()[0]
    print(f"インポート前のレコード数: {before_count}")
    
    added_count = 0
    skipped_count = 0
    error_count = 0
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row_num, row in enumerate(reader, start=2):  # ヘッダー行の次から
                try:
                    # データの取得と検証
                    employee_id = row.get('ID', '').strip()
                    employee_name = row.get('名前', '').strip()
                    date_str = row.get('日付', '').strip()
                    work_type = row.get('区分', '').strip()
                    start_time = row.get('開始時間', '').strip()
                    end_time = row.get('終了時間', '').strip()
                    
                    # 必須項目チェック
                    if not employee_id or not date_str:
                        print(f"行 {row_num}: 必須項目が不足 (ID: {employee_id}, 日付: {date_str})")
                        error_count += 1
                        continue
                    
                    # 日付フォーマット変換 (YYYY-MM-DD または YYYY/MM/DD -> YYYY-MM-DD)
                    try:
                        if '/' in date_str:
                            date_obj = datetime.strptime(date_str, '%Y/%m/%d')
                        else:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        work_date = date_obj.strftime('%Y-%m-%d')
                    except ValueError:
                        print(f"行 {row_num}: 日付フォーマットエラー ({date_str})")
                        error_count += 1
                        continue
                    
                    # 勤務区分マッピング
                    work_type_mapping = {
                        '日勤': '通常',
                        '夜勤': '夜勤',
                        '法': '法定休日',
                        '所': '所定休日',
                        '有': '有給',
                        '代': '代休',
                        '特': '特休',
                        '明': '明',      # 24時間勤務後の明け
                        '24勤A': '24勤A',
                        '24勤B': '24勤B'
                    }
                    mapped_work_type = work_type_mapping.get(work_type, work_type)
                    
                    # 時間データの処理 (空の場合はNULLにする)
                    start_time_value = start_time if start_time else None
                    end_time_value = end_time if end_time else None
                    
                    # 重複チェック（既存データがある場合はスキップ）
                    cursor.execute("""
                        SELECT COUNT(*) FROM attend_schedule 
                        WHERE employee_id = ? AND work_date = ?
                    """, (employee_id, work_date))
                    
                    if cursor.fetchone()[0] > 0:
                        # 既存データがあるのでスキップ
                        skipped_count += 1
                        print(f"スキップ（重複）: {employee_name} ({employee_id}) - {work_date}")
                    else:
                        # 新規データを挿入
                        sheet_number = "1"  # デフォルトのシート番号
                        cursor.execute("""
                            INSERT INTO attend_schedule 
                            (sheet_number, employee_id, employee_name, work_date, start_time, end_time, work_type)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (sheet_number, employee_id, employee_name, work_date, start_time_value, 
                              end_time_value, mapped_work_type))
                        added_count += 1
                        print(f"追加: {employee_name} ({employee_id}) - {work_date} - {mapped_work_type}")
                    
                except Exception as e:
                    print(f"行 {row_num}: エラー - {e}")
                    error_count += 1
                    continue
        
        conn.commit()
        
        # 結果確認
        cursor.execute("SELECT COUNT(*) FROM attend_schedule")
        after_count = cursor.fetchone()[0]
        
        print(f"\n=== インポート完了 ===")
        print(f"ファイル: {os.path.basename(csv_file_path)}")
        print(f"追加: {added_count} 件")
        print(f"スキップ（重複）: {skipped_count} 件")
        print(f"エラー: {error_count} 件")
        print(f"インポート後のレコード数: {after_count}")
        print(f"実際の増加数: {after_count - before_count}")
        
        # 特定の日付のデータを確認
        for target_date in ['2025-11-15', '2025-12-15']:
            cursor.execute("SELECT COUNT(*) FROM attend_schedule WHERE work_date = ?", (target_date,))
            count = cursor.fetchone()[0]
            print(f"{target_date} のデータ件数: {count}")
        
    except Exception as e:
        print(f"ファイル読み込みエラー: {e}")
        conn.rollback()
    finally:
        conn.close()

def check_existing_data():
    """既存データの確認"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print("=== 既存データ確認 ===")
    
    # 全体のレコード数
    cursor.execute("SELECT COUNT(*) FROM attend_schedule")
    total_count = cursor.fetchone()[0]
    print(f"全体のレコード数: {total_count}")
    
    # 特定の日付のデータ確認
    for target_date in ['2025-11-15', '2025-12-15']:
        cursor.execute("SELECT COUNT(*) FROM attend_schedule WHERE work_date = ?", (target_date,))
        count = cursor.fetchone()[0]
        print(f"{target_date} のデータ件数: {count}")
        
        if count > 0:
            cursor.execute("""
                SELECT employee_id, employee_name, work_type 
                FROM attend_schedule 
                WHERE work_date = ? 
                ORDER BY employee_id
                LIMIT 5
            """, (target_date,))
            
            results = cursor.fetchall()
            print(f"  サンプルデータ:")
            for emp_id, emp_name, work_type in results:
                print(f"    {emp_id}: {emp_name} - {work_type}")
    
    conn.close()

def main():
    """メイン処理"""
    print("=== attend_schedule 差分CSVインポート開始 ===")
    
    # まず既存データを確認
    check_existing_data()
    
    # CSVファイルのパス（実際のファイルパスに変更してください）
    csv_files = [
        "\\\\DESKTOP-74DASSG\\Users\\take_me_hospital\\attendance\\統合勤怠データ_20251116_140154.csv",  # 2025-11-15のデータ
        "\\\\DESKTOP-74DASSG\\Users\\take_me_hospital\\attendance\\統合勤怠データ_20251116_140306.csv",  # 2025-12-15のデータ
    ]
    
    print(f"\n処理対象ファイル: {len(csv_files)} 件")
    
    if not csv_files or all(not f for f in csv_files):
        print("CSVファイルのパスを指定してください。")
        print("main()関数内のcsv_filesリストに実際のファイルパスを追加してください。")
        return
    
    for csv_file in csv_files:
        if csv_file and os.path.exists(csv_file):
            print(f"\n--- {os.path.basename(csv_file)} の処理開始 ---")
            import_diff_csv_to_schedule(csv_file)
        else:
            print(f"ファイルが見つかりません: {csv_file}")
    
    print("\n=== 処理後のデータ確認 ===")
    check_existing_data()
    
    print("\n=== 全ての処理完了 ===")

if __name__ == "__main__":
    main()