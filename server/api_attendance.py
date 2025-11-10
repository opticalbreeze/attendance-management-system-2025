#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打刻・勤怠API
打刻データ受信、勤怠チェック、従業員管理など
"""

from flask import request, jsonify
from datetime import datetime

from config import Config
from database import (
    insert_attendance, search_schedule, get_stats, cleanup_duplicates,
    get_employees, check_attendance_vs_schedule, get_database_connection,
    insert_late_arrival_request, insert_early_leave_request,
    get_late_arrival_requests, get_early_leave_requests
)
from utils import (
    check_duplicate_attendance, calculate_date_range,
    validate_employee_id, validate_search_month, format_response, safe_int
)

def register_attendance_api_routes(app):
    """打刻・勤怠APIルートを登録"""
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """ヘルスチェックAPI"""
        return jsonify({
            'status': 'ok',
            'message': 'サーバーは正常に動作しています',
            'timestamp': datetime.now().isoformat(),
            'version': Config.API_VERSION
        })

    @app.route('/api/attendance', methods=['POST'])
    def receive_attendance():
        """打刻データ受信API"""
        try:
            data = request.get_json()
            if not data:
                return jsonify(format_response('error', message='データが送信されていません')), 400
            
            idm = data.get('idm')
            timestamp = data.get('timestamp')
            terminal_id = data.get('terminal_id')
            
            if not all([idm, timestamp, terminal_id]):
                return jsonify(format_response('error', message='必須フィールドが不足しています')), 400
            
            # チャタリング防止チェック
            duplicate_check = check_duplicate_attendance(idm, timestamp, terminal_id)
            if duplicate_check['is_duplicate']:
                print(f"[チャタリング検出] IDm:{idm} | 差:{duplicate_check['time_diff']:.1f}秒")
                return jsonify(format_response('duplicate', message='重複データ', time_diff=duplicate_check['time_diff'])), 200
            
            attendance_id = insert_attendance(idm, timestamp, terminal_id)
            print(f"[打刻受信] ID:{attendance_id} | IDm:{idm}")
            
            return jsonify(format_response('success', message='打刻データを保存しました', attendance_id=attendance_id))
            
        except Exception as e:
            print(f"[エラー] 打刻データ受信エラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/search', methods=['GET'])
    def search_schedule_api():
        """勤怠スケジュール検索API"""
        try:
            employee_id = request.args.get('employee_id', '').strip()
            search_month = request.args.get('search_month', '').strip()
            limit = safe_int(request.args.get('limit', str(Config.DEFAULT_SEARCH_LIMIT)), Config.DEFAULT_SEARCH_LIMIT)
            
            valid, employee_id_or_error = validate_employee_id(employee_id)
            if not valid:
                return jsonify(format_response('error', message=employee_id_or_error)), 400
            employee_id = employee_id_or_error
            
            valid, search_month_or_error = validate_search_month(search_month)
            if not valid:
                return jsonify(format_response('error', message=search_month_or_error)), 400
            search_month = search_month_or_error
            
            try:
                start_date, end_date = calculate_date_range(search_month)
            except ValueError as e:
                return jsonify(format_response('error', message=str(e))), 400
            
            results = search_schedule(employee_id, start_date, end_date, limit)
            
            return jsonify(format_response(
                'success',
                count=len(results),
                results=results,
                search_params={'employee_id': employee_id, 'search_month': search_month,
                             'date_range': {'start_date': start_date, 'end_date': end_date}}
            ))
            
        except Exception as e:
            print(f"[エラー] 検索エラー: {e}")
            return jsonify(format_response('error', message=f'検索エラー: {str(e)}')), 500

    @app.route('/api/stats', methods=['GET'])
    def get_stats_api():
        """統計情報API"""
        try:
            stats = get_stats()
            return jsonify(stats)
        except Exception as e:
            print(f"[エラー] 統計情報取得エラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/cleanup_duplicates', methods=['POST'])
    def cleanup_duplicates_api():
        """重複データクリーンアップAPI"""
        try:
            data = request.get_json() or {}
            threshold = safe_int(data.get('threshold_seconds', Config.CHATTERING_THRESHOLD_SECONDS),
                               Config.CHATTERING_THRESHOLD_SECONDS)
            
            removed_count = cleanup_duplicates(threshold)
            
            return jsonify(format_response('success',
                message=f'{removed_count}件の重複データを削除しました',
                removed_count=removed_count, threshold_seconds=threshold))
            
        except Exception as e:
            print(f"[エラー] クリーンアップエラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/sample_data', methods=['POST'])
    def add_sample_data_api():
        """サンプルデータ追加API（開発・テスト用）"""
        try:
            sample_data = [
                ('A1B2C3D4', '2025-10-24T09:00:00', 'TERMINAL_01'),
                ('E5F6G7H8', '2025-10-24T09:05:00', 'TERMINAL_01'),
                ('I9J0K1L2', '2025-10-24T09:10:00', 'TERMINAL_02'),
            ]
            
            conn = get_database_connection()
            cursor = conn.cursor()
            
            added_count = 0
            for idm, timestamp, terminal_id in sample_data:
                duplicate_check = check_duplicate_attendance(idm, timestamp, terminal_id)
                if not duplicate_check['is_duplicate']:
                    attendance_id = insert_attendance(idm, timestamp, terminal_id)
                    added_count += 1
                    print(f"[サンプルデータ] 追加: ID={attendance_id}, IDm={idm}")
            
            conn.close()
            
            return jsonify(format_response('success',
                message=f'{added_count}件のサンプルデータを追加しました', added_count=added_count))
            
        except Exception as e:
            print(f"[エラー] サンプルデータ追加エラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/employees', methods=['GET'])
    def get_employees_api():
        """従業員一覧取得API"""
        try:
            employees = get_employees()
            return jsonify(format_response('success',
                message=f'{len(employees)}名の従業員情報を取得しました', data=employees))
            
        except Exception as e:
            print(f"[エラー] 従業員情報取得エラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/attendance_check', methods=['GET'])
    def attendance_check_api():
        """勤怠チェックAPI"""
        try:
            employee_id = request.args.get('employee_id', '').strip()
            check_date = request.args.get('check_date', '').strip()
            
            valid, employee_id_or_error = validate_employee_id(employee_id)
            if not valid:
                return jsonify(format_response('error', message=employee_id_or_error)), 400
            employee_id = employee_id_or_error
            
            if not check_date:
                return jsonify(format_response('error', message='チェック日付が指定されていません')), 400
            
            try:
                datetime.strptime(check_date, '%Y-%m-%d')
            except ValueError:
                return jsonify(format_response('error', message='日付形式が正しくありません')), 400
            
            result = check_attendance_vs_schedule(employee_id, check_date)
            
            if result['status'] == 'error':
                return jsonify(format_response('error', message=result['message'])), 400
            
            return jsonify(format_response('success', message='勤怠チェックが完了しました', data=result['data']))
            
        except Exception as e:
            print(f"[エラー] 勤怠チェックエラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/late_arrival', methods=['POST'])
    def submit_late_arrival():
        """遅刻申告API"""
        try:
            data = request.get_json()
            if not data:
                return jsonify(format_response('error', message='データが送信されていません')), 400
            
            employee_num = data.get('employee_num')
            employee_name = data.get('employee_name')
            request_date = data.get('request_date')
            work_date = data.get('work_date')
            late_minutes = data.get('late_minutes')
            reason = data.get('reason', '')
            
            if not all([employee_num, employee_name, request_date, work_date, late_minutes is not None]):
                return jsonify(format_response('error', message='必須フィールドが不足しています')), 400
            
            try:
                late_minutes = int(late_minutes)
            except ValueError:
                return jsonify(format_response('error', message='遅刻分数は数値で指定してください')), 400
            
            request_id = insert_late_arrival_request(
                employee_num, employee_name, request_date, work_date, late_minutes, reason
            )
            
            if request_id:
                return jsonify(format_response('success', message='遅刻申告を登録しました', request_id=request_id))
            else:
                return jsonify(format_response('error', message='遅刻申告の登録に失敗しました')), 500
                
        except Exception as e:
            print(f"[エラー] 遅刻申告エラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/early_leave', methods=['POST'])
    def submit_early_leave():
        """早退申告API"""
        try:
            data = request.get_json()
            if not data:
                return jsonify(format_response('error', message='データが送信されていません')), 400
            
            employee_num = data.get('employee_num')
            employee_name = data.get('employee_name')
            request_date = data.get('request_date')
            work_date = data.get('work_date')
            early_minutes = data.get('early_minutes')
            reason = data.get('reason', '')
            
            if not all([employee_num, employee_name, request_date, work_date, early_minutes is not None]):
                return jsonify(format_response('error', message='必須フィールドが不足しています')), 400
            
            try:
                early_minutes = int(early_minutes)
            except ValueError:
                return jsonify(format_response('error', message='早退分数は数値で指定してください')), 400
            
            request_id = insert_early_leave_request(
                employee_num, employee_name, request_date, work_date, early_minutes, reason
            )
            
            if request_id:
                return jsonify(format_response('success', message='早退申告を登録しました', request_id=request_id))
            else:
                return jsonify(format_response('error', message='早退申告の登録に失敗しました')), 500
                
        except Exception as e:
            print(f"[エラー] 早退申告エラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/late_arrival', methods=['GET'])
    def get_late_arrival():
        """遅刻申告取得API"""
        try:
            employee_num = request.args.get('employee_num')
            work_date = request.args.get('work_date')
            status = request.args.get('status')
            
            if employee_num:
                try:
                    employee_num = int(employee_num)
                except ValueError:
                    return jsonify(format_response('error', message='従業員番号は数値で指定してください')), 400
            
            requests = get_late_arrival_requests(
                employee_num=employee_num,
                work_date=work_date,
                status=status
            )
            
            return jsonify(format_response('success', data=requests))
            
        except Exception as e:
            print(f"[エラー] 遅刻申告取得エラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/early_leave', methods=['GET'])
    def get_early_leave():
        """早退申告取得API"""
        try:
            employee_num = request.args.get('employee_num')
            work_date = request.args.get('work_date')
            status = request.args.get('status')
            
            if employee_num:
                try:
                    employee_num = int(employee_num)
                except ValueError:
                    return jsonify(format_response('error', message='従業員番号は数値で指定してください')), 400
            
            requests = get_early_leave_requests(
                employee_num=employee_num,
                work_date=work_date,
                status=status
            )
            
            return jsonify(format_response('success', data=requests))
            
        except Exception as e:
            print(f"[エラー] 早退申告取得エラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

