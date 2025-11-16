#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月間集計レポートAPI
月間レポートの生成、ダウンロード、プレビューなど
"""

from flask import request, jsonify, send_file
from functools import wraps
import os

from config import Config
from auth import login_required
from monthly_report import generate_monthly_report_excel, get_monthly_attendance_data
from utils import format_response

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
            print(f"[エラー] 月間レポート生成エラー: {e}")
            import traceback
            traceback.print_exc()
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500
    
    @app.route('/api/monthly-report/download/<filename>', methods=['GET'])
    @login_required
    def download_monthly_report(filename):
        """月間集計レポートダウンロードAPI"""
        try:
            # ファイルパス構築
            output_dir = Config.PDF_SAVE_DIR.replace('PDF', 'reports')
            file_path = os.path.join(output_dir, filename)
            
            if not os.path.exists(file_path):
                return jsonify(format_response('error', message='ファイルが見つかりません')), 404
            
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
        except Exception as e:
            print(f"[エラー] ファイルダウンロードエラー: {e}")
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
            
            return jsonify(format_response('success', data=data))
            
        except Exception as e:
            print(f"[エラー] プレビュー取得エラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

