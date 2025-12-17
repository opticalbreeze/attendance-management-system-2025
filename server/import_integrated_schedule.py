#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統合勤怠データCSVをattend_scheduleテーブルにインポートするスクリプト
2025/12/16から2026/1/15までの期間のスケジュールを差し替え
"""

import csv
from datetime import datetime
import os
import sys

# データベース接続ユーティリティをインポート
try:
    # 通常の実行環境（utils.py経由）
    from utils import get_db_connection
except ImportError:
    # 直接実行時（database_utils.pyから直接）
    from database_utils import get_db_connection

def import_schedule_data():
    """CSVデータをデータベースにインポート"""
    csv_path = "/app/schedule_data.csv"
    
    print("=== スケジュールデータ差し替え開始 ===")
    print(f"CSV: {csv_path}")
    
    # データベース接続（コンテキストマネージャーを使用）
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            # 1. 指定期間のスケジュールを削除
            print("\n1. 既存スケジュール削除（2025/12/16〜2026/1/15）...")
            cursor.execute("""
                DELETE FROM attend_schedule 
                WHERE work_date >= '2025-12-16' AND work_date <= '2026-01-15'
            """)
            deleted_count = cursor.rowcount
            print(f"削除件数: {deleted_count}件")
            
            # 2. CSVデータを読み込み
            print("\n2. CSVデータ読み込み...")
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                imported_count = 0
                skipped_count = 0
                
                for row in reader:
                    try:
                        # 日付フォーマット変換 (YYYY/M/D → YYYY-MM-DD)
                        date_str = row['日付']
                        date_obj = datetime.strptime(date_str, '%Y/%m/%d')
                        work_date = date_obj.strftime('%Y-%m-%d')
                        
                        employee_id = row['ID']
                        work_type = row['区分']
                        start_time = row['開始時間'] if row['開始時間'].strip() else None
                        end_time = row['終了時間'] if row['終了時間'].strip() else None
                        
                        # データベースに挿入
                        cursor.execute("""
                            INSERT OR REPLACE INTO attend_schedule 
                            (employee_id, work_date, work_type, start_time, end_time)
                            VALUES (?, ?, ?, ?, ?)
                        """, (employee_id, work_date, work_type, start_time, end_time))
                        
                        imported_count += 1
                        
                    except Exception as e:
                        print(f"エラー（行スキップ）: {row} - {e}")
                        skipped_count += 1
                        continue
            
            # 3. コミット（コンテキストマネージャーが自動的にコミット）
            print(f"\n3. インポート完了")
            print(f"インポート件数: {imported_count}件")
            print(f"スキップ件数: {skipped_count}件")
            
            # 4. 確認
            print("\n4. インポート結果確認...")
            cursor.execute("""
                SELECT employee_id, COUNT(*) as count
                FROM attend_schedule 
                WHERE work_date >= '2025-12-16' AND work_date <= '2026-01-15'
                GROUP BY employee_id
                ORDER BY employee_id
            """)
            
            results = cursor.fetchall()
            print("従業員別インポート件数:")
            for emp_id, count in results:
                print(f"  従業員 {emp_id}: {count}件")
                
            total_imported = sum(count for _, count in results)
            print(f"総インポート件数: {total_imported}件")
            
        except Exception as e:
            print(f"エラー: {e}")
            # コンテキストマネージャーが自動的にロールバック
            raise
        
    print("\n=== スケジュールデータ差し替え完了 ===")

if __name__ == '__main__':
    import_schedule_data()