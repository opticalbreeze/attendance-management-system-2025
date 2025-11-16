#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理者機能モジュール
CSVインポート、データ管理などの管理者専用機能
"""

import os
import csv
import sqlite3
from datetime import datetime
from flask import request, jsonify, flash
from werkzeug.utils import secure_filename

from config import Config
from utils import get_database_connection

# アップロード設定
UPLOAD_FOLDER = '/tmp/uploads'
ALLOWED_EXTENSIONS = {'csv'}

def init_upload_folder():
    """アップロードフォルダを初期化"""
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    """許可されたファイル拡張子かチェック"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def import_csv_to_schedule(csv_file_path):
    """CSVファイルをattend_scheduleテーブルにインポート"""
    
    conn = get_database_connection()
    cursor = conn.cursor()
    
    # 既存データの確認
    cursor.execute("SELECT COUNT(*) FROM attend_schedule")
    before_count = cursor.fetchone()[0]
    
    imported_count = 0
    error_count = 0
    error_messages = []
    
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
                        error_messages.append(f"行 {row_num}: 必須項目が不足 (ID: {employee_id}, 日付: {date_str})")
                        error_count += 1
                        continue
                    
                    # 日付フォーマット変換 (YYYY/MM/DD -> YYYY-MM-DD)
                    try:
                        date_obj = datetime.strptime(date_str, '%Y/%m/%d')
                        work_date = date_obj.strftime('%Y-%m-%d')
                    except ValueError:
                        error_messages.append(f"行 {row_num}: 日付フォーマットエラー ({date_str})")
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
                    else:
                        # 新規データを挿入（sheet_numberにデフォルト値を設定）
                        sheet_number = "1"  # デフォルトのシート番号
                        cursor.execute("""
                            INSERT INTO attend_schedule 
                            (sheet_number, employee_id, employee_name, work_date, start_time, end_time, work_type)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (sheet_number, employee_id, employee_name, work_date, start_time_value, 
                              end_time_value, mapped_work_type))
                    
                    imported_count += 1
                    
                except Exception as e:
                    error_messages.append(f"行 {row_num}: エラー - {str(e)}")
                    error_count += 1
                    continue
        
        conn.commit()
        
        # 結果確認
        cursor.execute("SELECT COUNT(*) FROM attend_schedule")
        after_count = cursor.fetchone()[0]
        
        result = {
            'success': True,
            'message': f'インポート完了: {imported_count}件処理, {error_count}件エラー',
            'details': {
                'processed': imported_count,
                'errors': error_count,
                'before_count': before_count,
                'after_count': after_count,
                'increase': after_count - before_count,
                'error_messages': error_messages[:10]  # 最初の10個のエラーメッセージのみ
            }
        }
        
    except Exception as e:
        conn.rollback()
        result = {
            'success': False,
            'message': f'ファイル読み込みエラー: {str(e)}',
            'details': {'error_messages': [str(e)]}
        }
    finally:
        conn.close()
    
    return result

def register_admin_api_routes(app):
    """管理者機能のAPIルートを登録"""
    
    @app.route('/api/admin/csv/upload', methods=['POST'])
    def upload_csv():
        """CSVファイルアップロード＆インポート"""
        try:
            # アップロードフォルダ初期化
            init_upload_folder()
            
            # ファイル存在チェック
            if 'file' not in request.files:
                return jsonify({
                    'success': False,
                    'message': 'ファイルが選択されていません'
                })
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'message': 'ファイルが選択されていません'
                })
            
            # ファイル形式チェック
            if not allowed_file(file.filename):
                return jsonify({
                    'success': False,
                    'message': '許可されていないファイル形式です（.csvのみ許可）'
                })
            
            # ファイル保存
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
            
            file.save(file_path)
            
            # CSVインポート実行
            result = import_csv_to_schedule(file_path)
            
            # 一時ファイル削除
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'システムエラー: {str(e)}'
            })
    
    @app.route('/api/admin/database/stats', methods=['GET'])
    def get_database_stats():
        """データベース統計情報を取得"""
        try:
            conn = get_database_connection()
            cursor = conn.cursor()
            
            # 基本統計
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT employee_id) as employees,
                    COUNT(*) as total_records,
                    MIN(work_date) as start_date,
                    MAX(work_date) as end_date
                FROM attend_schedule
            """)
            basic_stats = cursor.fetchone()
            
            # 勤務区分別統計
            cursor.execute("""
                SELECT work_type, COUNT(*) as count 
                FROM attend_schedule 
                GROUP BY work_type 
                ORDER BY count DESC
            """)
            work_type_stats = cursor.fetchall()
            
            # 月別統計
            cursor.execute("""
                SELECT 
                    strftime('%Y-%m', work_date) as month,
                    COUNT(*) as records
                FROM attend_schedule 
                GROUP BY strftime('%Y-%m', work_date)
                ORDER BY month DESC
                LIMIT 12
            """)
            monthly_stats = cursor.fetchall()
            
            conn.close()
            
            return jsonify({
                'success': True,
                'data': {
                    'basic': {
                        'employees': basic_stats[0] if basic_stats[0] else 0,
                        'total_records': basic_stats[1] if basic_stats[1] else 0,
                        'start_date': basic_stats[2],
                        'end_date': basic_stats[3]
                    },
                    'work_types': [{'type': row[0], 'count': row[1]} for row in work_type_stats],
                    'monthly': [{'month': row[0], 'records': row[1]} for row in monthly_stats]
                }
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'統計情報取得エラー: {str(e)}'
            })