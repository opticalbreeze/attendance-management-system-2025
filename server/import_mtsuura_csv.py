#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mtsuura202512.csvをattend_scheduleテーブルにインポートするスクリプト
CSVフォーマット: シート番号,従業員ID,従業員名,日付,区分,開始時間,終了時間
"""

import csv
import sqlite3
from datetime import datetime
import os
import sys

# パスを追加してモジュールをインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from logger_config import setup_logger
from work_type_constants import map_csv_work_type
from database_utils import get_db_connection

logger = setup_logger(__name__)

def import_mtsuura_csv(csv_file_path):
    """mtsuura202512.csvをattend_scheduleテーブルにインポート"""
    
    if not os.path.exists(csv_file_path):
        logger.error(f"CSVファイルが見つかりません: {csv_file_path}")
        return False
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 既存データの確認
            cursor.execute("SELECT COUNT(*) FROM attend_schedule")
            before_count = cursor.fetchone()[0]
            logger.info(f"インポート前のレコード数: {before_count}")
            
            imported_count = 0
            updated_count = 0
            error_count = 0
            
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                
                for row_num, row in enumerate(reader, start=1):
                    try:
                        # カラム数チェック
                        if len(row) < 5:
                            logger.warning(f"行 {row_num}: カラム数が不足しています（{len(row)}列）")
                            error_count += 1
                            continue
                        
                        # CSVのカラム構造:
                        # 0: シート番号
                        # 1: 従業員ID
                        # 2: 従業員名
                        # 3: 日付 (YYYY/MM/DD形式)
                        # 4: 区分
                        # 5: 開始時間 (オプション)
                        # 6: 終了時間 (オプション)
                        
                        sheet_number = row[0].strip() if len(row) > 0 else Config.DEFAULT_SHEET_NUMBER
                        employee_id = row[1].strip() if len(row) > 1 else ''
                        employee_name = row[2].strip() if len(row) > 2 else ''
                        date_str = row[3].strip() if len(row) > 3 else ''
                        work_type = row[4].strip() if len(row) > 4 else ''
                        start_time = row[5].strip() if len(row) > 5 and row[5].strip() else None
                        end_time = row[6].strip() if len(row) > 6 and row[6].strip() else None
                        
                        # 必須項目チェック
                        if not employee_id or not date_str:
                            logger.warning(f"行 {row_num}: 必須項目が不足 (ID: {employee_id}, 日付: {date_str})")
                            error_count += 1
                            continue
                        
                        # 日付フォーマット変換 (YYYY/MM/DD -> YYYY-MM-DD)
                        try:
                            date_obj = datetime.strptime(date_str, '%Y/%m/%d')
                            work_date = date_obj.strftime('%Y-%m-%d')
                        except ValueError:
                            logger.warning(f"行 {row_num}: 日付フォーマットエラー ({date_str})")
                            error_count += 1
                            continue
                        
                        # 勤務区分マッピング
                        mapped_work_type = map_csv_work_type(work_type)
                        
                        # シート番号の処理（空の場合はデフォルト値）
                        if not sheet_number:
                            sheet_number = Config.DEFAULT_SHEET_NUMBER
                        
                        # 重複チェック
                        cursor.execute("""
                            SELECT COUNT(*) FROM attend_schedule 
                            WHERE employee_id = ? AND work_date = ?
                        """, (employee_id, work_date))
                        
                        if cursor.fetchone()[0] > 0:
                            # 既存データを更新
                            cursor.execute("""
                                UPDATE attend_schedule 
                                SET sheet_number = ?, employee_name = ?, start_time = ?, end_time = ?, work_type = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE employee_id = ? AND work_date = ?
                            """, (sheet_number, employee_name, start_time, end_time, mapped_work_type, 
                                  employee_id, work_date))
                            updated_count += 1
                            logger.debug(f"更新: {employee_name} ({employee_id}) - {work_date} - {mapped_work_type}")
                        else:
                            # 新規データを挿入
                            cursor.execute("""
                                INSERT INTO attend_schedule 
                                (sheet_number, employee_id, employee_name, work_date, start_time, end_time, work_type, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            """, (sheet_number, employee_id, employee_name, work_date, start_time, 
                                  end_time, mapped_work_type))
                            imported_count += 1
                            logger.debug(f"追加: {employee_name} ({employee_id}) - {work_date} - {mapped_work_type}")
                        
                    except Exception as e:
                        logger.error(f"行 {row_num}: エラー - {e}", exc_info=True)
                        error_count += 1
                        continue
            
            # 結果確認
            cursor.execute("SELECT COUNT(*) FROM attend_schedule")
            after_count = cursor.fetchone()[0]
            
            logger.info(f"インポート完了: ファイル={os.path.basename(csv_file_path)}")
            logger.info(f"  新規追加: {imported_count}件")
            logger.info(f"  更新: {updated_count}件")
            logger.info(f"  エラー: {error_count}件")
            logger.info(f"  インポート前: {before_count}件 → インポート後: {after_count}件 (増加: {after_count - before_count}件)")
            
            return True
            
    except Exception as e:
        logger.error(f"インポートエラー: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    # コマンドライン引数からCSVファイルパスを取得、またはデフォルトパスを使用
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        # デフォルトパス: プロジェクトルートのdataフォルダ
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        csv_path = os.path.join(project_root, 'data', 'mtsuura202512.csv')
    
    logger.info(f"CSVファイルパス: {csv_path}")
    
    if import_mtsuura_csv(csv_path):
        print("✅ インポートが正常に完了しました")
        sys.exit(0)
    else:
        print("❌ インポート中にエラーが発生しました")
        sys.exit(1)

