#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月間集計レポートAPI
月間レポートの生成、ダウンロード、プレビューなど
"""

from flask import request, jsonify, send_file, Response, stream_with_context
import os
from io import BytesIO
from datetime import datetime
import time
import functools
import tempfile

from config import Config
from auth import login_required
from monthly_report import generate_monthly_report_excel, get_monthly_attendance_data, generate_all_employees_report_excel
from database import get_employees
from utils import format_response, get_db_connection, calculate_date_range
from constants import AttendanceConstants
from logger_config import setup_logger

logger = setup_logger(__name__)

def register_monthly_report_api_routes(app):
    """月間集計レポートAPIルートを登録"""
    
    @app.route('/api/monthly-report/generate', methods=['POST'])
    @login_required
    def generate_monthly_report_api():
        """月間集計レポート生成API"""
        try:
            data = request.get_json()
            if not data:
                return jsonify(format_response('error', message='データが送信されていません')), 400
            
            employee_id = data.get('employee_id', '').strip()
            search_month = data.get('search_month', '').strip()
            
            if not employee_id:
                return jsonify(format_response('error', message='従業員番号を指定してください')), 400
            
            if not search_month:
                return jsonify(format_response('error', message='検索月を指定してください（YYYY/MM形式）')), 400
            
            # Excelファイル生成
            output_path = generate_monthly_report_excel(employee_id, search_month)
            
            if not output_path or not os.path.exists(output_path):
                return jsonify(format_response('error', message='ファイルの生成に失敗しました')), 500
            
            # ファイル名を取得
            filename = os.path.basename(output_path)
            
            return jsonify(format_response('success',
                message='レポートを生成しました',
                filename=filename,
                download_url=f'/api/monthly-report/download/{filename}'))
            
        except Exception as e:
            logger.error(f"月間レポート生成エラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500
    
    @app.route('/api/monthly-report/download/<filename>', methods=['GET'])
    @login_required
    def download_monthly_report(filename):
        """月間集計レポートダウンロードAPI"""
        try:
            # ファイルパス構築
            if Config.PDF_SAVE_DIR:
                output_dir = Config.PDF_SAVE_DIR.replace('PDF', 'reports')
            else:
                # データベースパスと同じディレクトリのreportsフォルダ
                db_dir = os.path.dirname(Config.DATABASE_PATH)
                output_dir = os.path.join(db_dir, 'reports')
            
            file_path = os.path.join(output_dir, filename)
            logger.debug(f"ダウンロードファイルパス: {file_path}")
            
            if not os.path.exists(file_path):
                logger.warning(f"ファイルが見つかりません: {file_path}")
                return jsonify(format_response('error', message='ファイルが見つかりません')), 404
            
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
        except Exception as e:
            logger.error(f"ファイルダウンロードエラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500
    
    @app.route('/api/monthly-report/preview', methods=['GET'])
    @login_required
    def preview_monthly_report_api():
        """月間集計レポートプレビューAPI"""
        try:
            employee_id = request.args.get('employee_id', '').strip()
            search_month = request.args.get('search_month', '').strip()
            
            if not employee_id or not search_month:
                return jsonify(format_response('error', message='従業員番号と検索月を指定してください')), 400
            
            # データ取得
            data = get_monthly_attendance_data(employee_id, search_month)
            
            if not data:
                return jsonify(format_response('error', message='データが見つかりません')), 404
            
            # format_responseは辞書を直接マージするため、明示的に'data'キーでラップ
            return jsonify({
                'status': 'success',
                'data': data
            })
            
        except Exception as e:
            logger.error(f"プレビュー取得エラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500
    
    @app.route('/api/monthly-report/download-all-excel', methods=['GET'])
    @login_required
    def download_all_employees_excel():
        """全員分の月間集計レポートをExcelファイル（1ファイル複数シート）としてダウンロード"""
        try:
            search_month = request.args.get('search_month', '').strip()
            
            if not search_month:
                return jsonify(format_response('error', message='検索月を指定してください')), 400
            
            # 全従業員を取得
            employees = get_employees()
            if not employees:
                return jsonify(format_response('error', message='従業員データが見つかりません')), 404
            
            logger.info(f"全員一括Excelダウンロード開始: 検索月={search_month}, 従業員数={len(employees)}")
            start_time = time.time()
            
            # 全員分のExcelファイルを生成
            try:
                output_path = generate_all_employees_report_excel(search_month, employees)
            except ValueError as e:
                logger.error(f"全員一括Excel生成エラー（データなし）: {e}")
                return jsonify(format_response('error', message=str(e))), 400
            
            if not output_path or not os.path.exists(output_path):
                logger.error(f"ファイルが生成されませんでした: {output_path}")
                return jsonify(format_response('error', message='ファイルの生成に失敗しました')), 500
            
            total_time = time.time() - start_time
            logger.info(f"全員一括Excelダウンロード完了: 処理時間={total_time:.2f}秒, ファイル={output_path}")
            
            # ファイル名を取得
            filename = os.path.basename(output_path)
            
            return send_file(
                output_path,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
            
        except Exception as e:
            logger.error(f"全員一括Excelダウンロードエラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

