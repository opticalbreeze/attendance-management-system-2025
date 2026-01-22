#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CSVから勤務シフト予定データをインポートするスクリプト
統合勤怠データ_20260114_132404.csv のデータを attend_schedule テーブルに登録
"""

import sqlite3
import csv
import os
import sys
from datetime import datetime

# データベースファイルのパス
DB_PATH = r'c:\Users\take_me_hospital\attendance\data\attendance.db'

# CSVファイルのパス（デスクトップ上）
CSV_PATH = r'c:\Users\take_me_hospital\OneDrive\デスクトップ\統合勤怠データ_20260114_132404.csv'

def create_backup():
    """データベースのバックアップを作成"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f'backup_{timestamp}.db'
    
    try:
        with open(DB_PATH, 'rb') as original:
            with open(backup_path, 'wb') as backup:
                backup.write(original.read())
        print(f"✓ データベースのバックアップを作成しました: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"✗ バックアップの作成に失敗しました: {e}")
        return None

def clear_existing_schedule(conn, start_date, end_date):
    """指定期間の既存の勤務予定データを削除"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            DELETE FROM attend_schedule 
            WHERE work_date BETWEEN ? AND ?
        """, (start_date, end_date))
        
        deleted_count = cursor.rowcount
        print(f"✓ 既存の勤務予定データを削除しました: {deleted_count}件")
        return deleted_count
    except Exception as e:
        print(f"✗ 既存データの削除に失敗しました: {e}")
        return 0

def get_employee_id_mapping(conn):
    """従業員IDとシステム内IDのマッピングを取得"""
    cursor = conn.cursor()
    cursor.execute("SELECT employee_num, name FROM employee_master")
    employees = cursor.fetchall()
    
    # CSVのIDと名前でマッピングを作成
    csv_id_to_db_id = {}
    name_to_db_id = {}
    
    for emp_num, name in employees:
        # 名前のクリーニング（空白文字統一）
        clean_name = name.replace(' ', '').replace('　', '').strip()
        name_to_db_id[clean_name] = str(emp_num)
        
        # employee_numもマッピング
        csv_id_to_db_id[str(emp_num)] = str(emp_num)
    
    print(f"✓ 従業員マスタから{len(employees)}名のデータを取得")
    return name_to_db_id, csv_id_to_db_id

def convert_date_format(date_str):
    """日付文字列をYYYY-MM-DD形式に変換"""
    try:
        # 2025/12/16 -> 2025-12-16
        parts = date_str.split('/')
        if len(parts) == 3:
            year, month, day = parts
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        return date_str
    except:
        return date_str

def convert_time_format(time_str):
    """時刻文字列をHH:MM形式に変換"""
    if not time_str or time_str.strip() == '':
        return None
    
    try:
        # 8:30 -> 08:30
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 2:
                hour, minute = parts
                return f"{hour.zfill(2)}:{minute.zfill(2)}"
        return time_str
    except:
        return None

def import_csv_data(conn, csv_path, name_to_id, csv_id_to_db_id):
    """CSVデータをインポート"""
    cursor = conn.cursor()
    imported_count = 0
    error_count = 0
    errors = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # ヘッダー行をスキップ
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    if len(row) < 7:
                        continue
                    
                    sheet_no, external_id, name, work_date, work_type, start_time, end_time = row
                    
                    # 名前のクリーニング
                    clean_name = name.replace(' ', '').replace('　', '').strip()
                    
                    # 従業員IDを検索（名前またはCSVのIDから）
                    employee_id = None
                    
                    # まず名前で検索
                    if clean_name in name_to_id:
                        employee_id = name_to_id[clean_name]
                    # 次にCSVのIDで検索
                    elif external_id in csv_id_to_db_id:
                        employee_id = csv_id_to_db_id[external_id]
                    
                    if employee_id is None:
                        error_msg = f"行{row_num}: 従業員が見つかりません - {name} (ID: {external_id})"
                        errors.append(error_msg)
                        error_count += 1
                        continue
                    
                    # 日付・時刻の変換
                    work_date_formatted = convert_date_format(work_date)
                    start_time_formatted = convert_time_format(start_time)
                    end_time_formatted = convert_time_format(end_time)
                    
                    # データベースに挿入（attend_scheduleテーブルの実際のカラムに合わせる）
                    cursor.execute("""
                        INSERT INTO attend_schedule 
                        (sheet_number, employee_id, employee_name, work_date, work_type, start_time, end_time, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                    """, (
                        sheet_no,
                        employee_id,
                        name,
                        work_date_formatted,
                        work_type,
                        start_time_formatted,
                        end_time_formatted
                    ))
                    
                    imported_count += 1
                    
                except Exception as e:
                    error_msg = f"行{row_num}: {str(e)} - {row}"
                    errors.append(error_msg)
                    error_count += 1
    
    except Exception as e:
        print(f"✗ CSVファイルの読み込みエラー: {e}")
        return 0, 0, [str(e)]
    
    return imported_count, error_count, errors

def main():
    """メイン処理"""
    print("=== CSV勤務予定データインポート開始 ===")
    
    # CSVファイルの存在確認
    if not os.path.exists(CSV_PATH):
        print(f"✗ CSVファイルが見つかりません: {CSV_PATH}")
        return False
    
    # データベースの存在確認
    if not os.path.exists(DB_PATH):
        print(f"✗ データベースファイルが見つかりません: {DB_PATH}")
        return False
    
    # バックアップ作成
    backup_path = create_backup()
    if not backup_path:
        print("✗ バックアップ作成失敗のため処理を中止します")
        return False
    
    try:
        # データベース接続
        conn = sqlite3.connect(DB_PATH)
        conn.execute('PRAGMA foreign_keys = ON')  # 外部キー制約を有効化
        
        print("✓ データベースに接続しました")
        
        # 従業員IDマッピング取得
        name_to_id, csv_id_to_db_id = get_employee_id_mapping(conn)
        if not name_to_id:
            print("✗ 従業員マスタデータが見つかりません")
            return False
        
        # 既存データの削除（2025/12/16 ～ 2026/1/15）
        deleted_count = clear_existing_schedule(conn, '2025-12-16', '2026-01-15')
        
        # CSVデータのインポート
        print(f"✓ CSVファイルからデータをインポート開始: {CSV_PATH}")
        imported_count, error_count, errors = import_csv_data(conn, CSV_PATH, name_to_id, csv_id_to_db_id)
        
        if errors:
            print(f"\n⚠ インポート時のエラー ({error_count}件):")
            for error in errors[:5]:  # 最初の5件のみ表示
                print(f"  - {error}")
            if len(errors) > 5:
                print(f"  - ... 他{len(errors) - 5}件")
        
        # トランザクションコミット
        conn.commit()
        print(f"✓ データベースへのコミット完了")
        
        # 結果サマリー
        print(f"\n=== インポート結果 ===")
        print(f"削除した既存データ: {deleted_count}件")
        print(f"インポート成功: {imported_count}件")
        print(f"インポートエラー: {error_count}件")
        print(f"作成したバックアップ: {backup_path}")
        
        # 最終確認クエリ
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM attend_schedule 
            WHERE work_date BETWEEN '2025-12-16' AND '2026-01-15'
        """)
        final_count = cursor.fetchone()[0]
        print(f"最終登録件数: {final_count}件")
        
        return True
        
    except Exception as e:
        print(f"✗ データベース処理エラー: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()
            print("✓ データベース接続を閉じました")

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 CSVデータのインポートが正常に完了しました！")
    else:
        print("\n❌ CSVデータのインポートに失敗しました")
    
    input("\nEnterキーを押して終了してください...")