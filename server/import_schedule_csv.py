#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSVデータをattend_scheduleテーブルに組み込むスクリプト
"""
import csv
import sqlite3
from datetime import datetime
import os
from config import Config

# データベース設定（config.pyから取得）
DATABASE_PATH = Config.DATABASE_PATH

def import_csv_to_schedule(csv_file_path):
    """CSVファイルをattend_scheduleテーブルにインポート"""
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 既存データの確認
    cursor.execute("SELECT COUNT(*) FROM attend_schedule")
    before_count = cursor.fetchone()[0]
    print(f"インポート前のレコード数: {before_count}")
    
    imported_count = 0
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
                    
                    # 日付フォーマット変換 (YYYY/MM/DD -> YYYY-MM-DD)
                    try:
                        date_obj = datetime.strptime(date_str, '%Y/%m/%d')
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
                        '特': '特休'
                    }
                    mapped_work_type = work_type_mapping.get(work_type, work_type)
                    
                    # 時間データの処理 (空の場合はNULLにする)
                    start_time_value = start_time if start_time else None
                    end_time_value = end_time if end_time else None
                    
                    # 重複チェック
                    cursor.execute("""
                        SELECT COUNT(*) FROM attend_schedule 
                        WHERE employee_id = ? AND work_date = ?
                    """, (employee_id, work_date))
                    
                    if cursor.fetchone()[0] > 0:
                        # 既存データを更新
                        cursor.execute("""
                            UPDATE attend_schedule 
                            SET start_time = ?, end_time = ?, work_type = ?
                            WHERE employee_id = ? AND work_date = ?
                        """, (start_time_value, end_time_value, mapped_work_type, 
                              employee_id, work_date))
                        print(f"更新: {employee_name} ({employee_id}) - {work_date} - {mapped_work_type}")
                    else:
                        # 新規データを挿入（sheet_numberにデフォルト値を設定）
                        sheet_number = "1"  # デフォルトのシート番号
                        cursor.execute("""
                            INSERT INTO attend_schedule 
                            (sheet_number, employee_id, employee_name, work_date, start_time, end_time, work_type)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (sheet_number, employee_id, employee_name, work_date, start_time_value, 
                              end_time_value, mapped_work_type))
                        print(f"追加: {employee_name} ({employee_id}) - {work_date} - {mapped_work_type}")
                    
                    imported_count += 1
                    
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
        print(f"処理済み: {imported_count} 件")
        print(f"エラー: {error_count} 件")
        print(f"インポート後のレコード数: {after_count}")
        print(f"増加数: {after_count - before_count}")
        
    except Exception as e:
        print(f"ファイル読み込みエラー: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    """メイン処理"""
    csv_files = [
        "/tmp/統合勤怠データ_20251116_100558.csv",
        "/tmp/統合勤怠データ_20251116_100700.csv"
    ]
    
    print("=== attend_schedule CSVインポート開始 ===")
    
    for csv_file in csv_files:
        if os.path.exists(csv_file):
            print(f"\n--- {os.path.basename(csv_file)} の処理開始 ---")
            import_csv_to_schedule(csv_file)
        else:
            print(f"ファイルが見つかりません: {csv_file}")
    
    print("\n=== 全ての処理完了 ===")

if __name__ == "__main__":
    main()