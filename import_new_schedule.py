#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統合勤怠CSVデータのインポートスクリプト
横山正明の既存データを削除して新しいデータに差し替える
"""

import sqlite3
import csv
import os
import sys
from datetime import datetime

def connect_database():
    """データベース接続"""
    db_path = '/app/data/attendance.db'
    return sqlite3.connect(db_path)

def delete_existing_data(conn, employee_id, start_date, end_date):
    """指定期間の既存データを削除"""
    cursor = conn.cursor()
    
    print(f"削除対象: 従業員ID {employee_id}, 期間: {start_date} ～ {end_date}")
    
    # 削除前の件数確認
    cursor.execute('''
        SELECT COUNT(*) FROM attend_schedule 
        WHERE employee_id = ? AND work_date BETWEEN ? AND ?
    ''', (employee_id, start_date, end_date))
    before_count = cursor.fetchone()[0]
    print(f"削除対象件数: {before_count}件")
    
    # データ削除
    cursor.execute('''
        DELETE FROM attend_schedule 
        WHERE employee_id = ? AND work_date BETWEEN ? AND ?
    ''', (employee_id, start_date, end_date))
    
    deleted_count = cursor.rowcount
    print(f"実際削除件数: {deleted_count}件")
    
    conn.commit()
    return deleted_count

def import_csv_data(conn, csv_file_path):
    """CSVファイルからデータをインポート"""
    cursor = conn.cursor()
    imported_count = 0
    error_count = 0
    
    print(f"CSVファイル読み込み開始: {csv_file_path}")
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            headers = next(csv_reader)  # ヘッダー行をスキップ
            print(f"CSVヘッダー: {headers}")
            
            for row_num, row in enumerate(csv_reader, start=2):
                try:
                    if len(row) < 7:
                        print(f"行{row_num}: データが不完全 - {row}")
                        error_count += 1
                        continue
                    
                    sheet_number = row[0].strip()
                    employee_id = row[1].strip()
                    employee_name = row[2].strip()
                    work_date = row[3].strip()
                    work_type = row[4].strip()
                    start_time = row[5].strip() if row[5].strip() else None
                    end_time = row[6].strip() if row[6].strip() else None
                    
                    # データ検証
                    if not work_date or not work_type:
                        print(f"行{row_num}: 必須データが不足 - {row}")
                        error_count += 1
                        continue
                    
                    # データベースに挿入
                    cursor.execute('''
                        INSERT INTO attend_schedule 
                        (sheet_number, employee_id, employee_name, work_date, work_type, start_time, end_time, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        sheet_number, employee_id, employee_name, work_date, work_type, 
                        start_time, end_time, 
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    
                    imported_count += 1
                    
                    # 進捗表示
                    if imported_count % 100 == 0:
                        print(f"進捗: {imported_count}件インポート完了")
                        
                except Exception as e:
                    print(f"行{row_num}でエラー: {e} - {row}")
                    error_count += 1
                    continue
    
    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません: {csv_file_path}")
        return 0, 1
    except Exception as e:
        print(f"ファイル読み込みエラー: {e}")
        return 0, 1
    
    conn.commit()
    print(f"インポート完了: 成功 {imported_count}件, エラー {error_count}件")
    return imported_count, error_count

def verify_import(conn, employee_id):
    """インポート結果の確認"""
    cursor = conn.cursor()
    
    print(f"\n=== インポート結果確認 (従業員ID: {employee_id}) ===")
    
    # 月別件数
    cursor.execute('''
        SELECT 
            substr(work_date, 1, 7) as month,
            COUNT(*) as count
        FROM attend_schedule
        WHERE employee_id = ?
        GROUP BY substr(work_date, 1, 7)
        ORDER BY month
    ''', (employee_id,))
    
    monthly_data = cursor.fetchall()
    for month, count in monthly_data:
        print(f"  {month}: {count}件")
    
    # 2026年1月のデータ詳細
    cursor.execute('''
        SELECT work_date, work_type, start_time, end_time
        FROM attend_schedule
        WHERE employee_id = ? AND work_date LIKE '2026-01-%'
        ORDER BY work_date
    ''', (employee_id,))
    
    jan_data = cursor.fetchall()
    if jan_data:
        print(f"\n2026年1月データ ({len(jan_data)}件):")
        for date, work_type, start_time, end_time in jan_data:
            print(f"  {date}: {work_type} {start_time or ''} - {end_time or ''}")

def main():
    """メイン処理"""
    print("=== 統合勤怠データインポート処理開始 ===")
    print(f"実行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 設定
    csv_file_path = '/tmp/統合勤怠データ_20260114_090708.csv'
    employee_id = '2952089'  # 横山正明
    delete_start_date = '2025-12-16'
    delete_end_date = '2026-01-14'
    
    try:
        # データベース接続
        conn = connect_database()
        print("データベース接続成功")
        
        # Step 1: 既存データ削除
        print(f"\nStep 1: 既存データ削除")
        deleted_count = delete_existing_data(conn, employee_id, delete_start_date, delete_end_date)
        
        # Step 2: CSVデータインポート
        print(f"\nStep 2: CSVデータインポート")
        imported_count, error_count = import_csv_data(conn, csv_file_path)
        
        # Step 3: 結果確認
        print(f"\nStep 3: インポート結果確認")
        verify_import(conn, employee_id)
        
        # 処理結果サマリー
        print(f"\n=== 処理完了サマリー ===")
        print(f"削除件数: {deleted_count}件")
        print(f"インポート件数: {imported_count}件")
        print(f"エラー件数: {error_count}件")
        
        if error_count == 0:
            print("✅ すべて正常に処理されました")
        else:
            print(f"⚠️ {error_count}件のエラーがありました")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 処理エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()