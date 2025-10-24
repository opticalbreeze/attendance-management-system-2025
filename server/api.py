#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API エンドポイントモジュール
REST API の定義と処理
"""

from flask import request, jsonify
from datetime import datetime
import json

from database import insert_attendance, search_schedule, get_stats, cleanup_duplicates, get_employees
from utils import (
    check_duplicate_attendance, calculate_date_range, 
    validate_employee_id, validate_search_month, format_response, safe_int
)

def register_api_routes(app):
    """APIルートを登録"""
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """ヘルスチェックAPI"""
        return jsonify({
            'status': 'ok',
            'message': 'サーバーは正常に動作しています',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        })

    @app.route('/api/attendance', methods=['POST'])
    def receive_attendance():
        """
        打刻データ受信API
        クライアントからの打刻データを受信・保存
        """
        try:
            # JSONデータの取得
            data = request.get_json()
            if not data:
                return jsonify(format_response(
                    'error', 
                    message='データが送信されていません'
                )), 400
            
            # 必須フィールドの取得
            idm = data.get('idm')
            timestamp = data.get('timestamp')
            terminal_id = data.get('terminal_id')
            
            # バリデーション
            if not all([idm, timestamp, terminal_id]):
                return jsonify(format_response(
                    'error',
                    message='必須フィールドが不足しています（idm, timestamp, terminal_id）'
                )), 400
            
            # チャタリング防止チェック
            duplicate_check = check_duplicate_attendance(idm, timestamp, terminal_id)
            if duplicate_check['is_duplicate']:
                print(f"[チャタリング検出] IDm:{idm} | 端末:{terminal_id} | 前回との差:{duplicate_check['time_diff']:.1f}秒")
                return jsonify(format_response(
                    'duplicate',
                    message='重複データのため保存をスキップしました',
                    time_diff=duplicate_check['time_diff']
                )), 200
            
            # データベースに保存
            attendance_id = insert_attendance(idm, timestamp, terminal_id)
            
            print(f"[打刻受信] ID:{attendance_id} | IDm:{idm} | 端末:{terminal_id}")
            
            return jsonify(format_response(
                'success',
                message='打刻データを正常に保存しました',
                attendance_id=attendance_id
            ))
            
        except Exception as e:
            print(f"[エラー] 打刻データ受信エラー: {e}")
            return jsonify(format_response(
                'error',
                message=f'サーバーエラー: {str(e)}'
            )), 500

    @app.route('/api/search', methods=['GET'])
    def search_schedule_api():
        """
        勤怠スケジュール検索API
        employee_idと検索月を指定して勤怠スケジュールを検索
        """
        try:
            # クエリパラメータの取得
            employee_id = request.args.get('employee_id', '').strip()
            search_month = request.args.get('search_month', '').strip()
            limit = safe_int(request.args.get('limit', '100'), 100)
            
            # バリデーション
            valid, employee_id_or_error = validate_employee_id(employee_id)
            if not valid:
                return jsonify(format_response('error', message=employee_id_or_error)), 400
            employee_id = employee_id_or_error
            
            valid, search_month_or_error = validate_search_month(search_month)
            if not valid:
                return jsonify(format_response('error', message=search_month_or_error)), 400
            search_month = search_month_or_error
            
            # 検索範囲の計算
            try:
                start_date, end_date = calculate_date_range(search_month)
            except ValueError as e:
                return jsonify(format_response('error', message=str(e))), 400
            
            # データベース検索
            results = search_schedule(employee_id, start_date, end_date, limit)
            
            return jsonify(format_response(
                'success',
                count=len(results),
                results=results,
                search_params={
                    'employee_id': employee_id,
                    'search_month': search_month,
                    'date_range': {
                        'start_date': start_date,
                        'end_date': end_date
                    }
                }
            ))
            
        except Exception as e:
            print(f"[エラー] 検索エラー: {e}")
            return jsonify(format_response(
                'error',
                message=f'検索エラー: {str(e)}'
            )), 500

    @app.route('/api/stats', methods=['GET'])
    def get_stats_api():
        """統計情報API"""
        try:
            stats = get_stats()
            return jsonify(format_response('success', **stats))
            
        except Exception as e:
            print(f"[エラー] 統計情報取得エラー: {e}")
            return jsonify(format_response(
                'error',
                message=f'統計情報取得エラー: {str(e)}'
            )), 500

    @app.route('/api/cleanup_duplicates', methods=['POST'])
    def cleanup_duplicates_api():
        """重複データクリーンアップAPI"""
        try:
            # リクエストパラメータ
            data = request.get_json() or {}
            threshold = safe_int(data.get('threshold_seconds', 10), 10)
            
            # クリーンアップ実行
            removed_count = cleanup_duplicates(threshold)
            
            return jsonify(format_response(
                'success',
                message=f'{removed_count}件の重複データを削除しました',
                removed_count=removed_count,
                threshold_seconds=threshold
            ))
            
        except Exception as e:
            print(f"[エラー] クリーンアップエラー: {e}")
            return jsonify(format_response(
                'error',
                message=f'クリーンアップエラー: {str(e)}'
            )), 500

    @app.route('/api/sample_data', methods=['POST'])
    def add_sample_data_api():
        """サンプルデータ追加API（開発・テスト用）"""
        try:
            from database import get_database_connection
            
            # サンプルデータ
            sample_data = [
                ('A1B2C3D4', '2025-10-24T09:00:00', 'TERMINAL_01'),
                ('E5F6G7H8', '2025-10-24T09:05:00', 'TERMINAL_01'),
                ('I9J0K1L2', '2025-10-24T09:10:00', 'TERMINAL_02'),
            ]
            
            conn = get_database_connection()
            cursor = conn.cursor()
            
            added_count = 0
            for idm, timestamp, terminal_id in sample_data:
                # 重複チェック
                duplicate_check = check_duplicate_attendance(idm, timestamp, terminal_id)
                if not duplicate_check['is_duplicate']:
                    attendance_id = insert_attendance(idm, timestamp, terminal_id)
                    added_count += 1
                    print(f"[サンプルデータ] 追加: ID={attendance_id}, IDm={idm}")
            
            conn.close()
            
            return jsonify(format_response(
                'success',
                message=f'{added_count}件のサンプルデータを追加しました',
                added_count=added_count
            ))
            
        except Exception as e:
            print(f"[エラー] サンプルデータ追加エラー: {e}")
            return jsonify(format_response(
                'error',
                message=f'サンプルデータ追加エラー: {str(e)}'
            )), 500

    @app.route('/api/employees', methods=['GET'])
    def get_employees_api():
        """
        従業員一覧取得API
        employee_masterから全従業員情報を動的に取得
        """
        try:
            employees = get_employees()
            
            return jsonify(format_response(
                'success',
                message=f'{len(employees)}名の従業員情報を取得しました',
                data=employees
            ))
            
        except Exception as e:
            print(f"[エラー] 従業員情報取得エラー: {e}")
            return jsonify(format_response(
                'error',
                message=f'従業員情報取得エラー: {str(e)}'
            )), 500