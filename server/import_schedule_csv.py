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
from constants import AttendanceConstants
from utils import get_db_connection
from logger_config import setup_logger

logger = setup_logger(__name__)

# データベース設定（config.pyから取得）
DATABASE_PATH = Config.DATABASE_PATH

def import_csv_to_schedule(csv_file_path):
    """CSVファイルをattend_scheduleテーブルにインポート"""
    
    imported_count = 0
    error_count = 0
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 既存データの確認
            cursor.execute("SELECT COUNT(*) FROM attend_schedule")
            before_count = cursor.fetchone()[0]
            logger.info(f"インポート前のレコード数: {before_count}")
            
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
                            logger.warning(f"行 {row_num}: 必須項目が不足 (ID: {employee_id}, 日付: {date_str})")
                            error_count += 1
                            continue
                        
                        # 日付フォーマット変換 (YYYY/MM/DD -> YYYY-MM-DD)
                        try:
                            date_obj = datetime.strptime(date_str, AttendanceConstants.DATE_FORMAT_SLASH)
                            work_date = date_obj.strftime(AttendanceConstants.DATE_FORMAT)
                        except ValueError:
                            logger.warning(f"行 {row_num}: 日付フォーマットエラー ({date_str})")
                            error_count += 1
                            continue
                        
                        # 勤務区分マッピング（work_type_constants.pyから取得）
                        from work_type_constants import map_csv_work_type
                        mapped_work_type = map_csv_work_type(work_type)
                        
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
                            logger.debug(f"更新: {employee_name} ({employee_id}) - {work_date} - {mapped_work_type}")
                        else:
                            # 新規データを挿入（sheet_numberにデフォルト値を設定）
                            sheet_number = Config.DEFAULT_SHEET_NUMBER
                            cursor.execute("""
                                INSERT INTO attend_schedule 
                                (sheet_number, employee_id, employee_name, work_date, start_time, end_time, work_type)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (sheet_number, employee_id, employee_name, work_date, start_time_value, 
                                  end_time_value, mapped_work_type))
                            logger.debug(f"追加: {employee_name} ({employee_id}) - {work_date} - {mapped_work_type}")
                        
                        imported_count += 1
                        
                    except Exception as e:
                        logger.error(f"行 {row_num}: エラー - {e}", exc_info=True)
                        error_count += 1
                        continue
            
            # 結果確認
            cursor.execute("SELECT COUNT(*) FROM attend_schedule")
            after_count = cursor.fetchone()[0]
            
            logger.info(f"インポート完了: ファイル={os.path.basename(csv_file_path)}, 処理済み={imported_count}件, エラー={error_count}件")
            logger.info(f"インポート後のレコード数: {after_count}, 増加数: {after_count - before_count}")
            # コンテキストマネージャーが自動的にコミット・クローズする
        
    except Exception as e:
        logger.error(f"ファイル読み込みエラー: {e}", exc_info=True)
        # コンテキストマネージャーが自動的にロールバック・クローズする

# このファイルはコマンドラインから直接実行する場合のユーティリティスクリプトです
# 通常はadmin.pyのimport_csv_to_schedule関数を使用してください