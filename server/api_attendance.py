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
    get_employees, check_attendance_vs_schedule,
    insert_late_arrival_request, insert_early_leave_request,
    get_late_arrival_requests, get_early_leave_requests
)
from utils import (
    check_duplicate_attendance, calculate_date_range,
    validate_employee_id, validate_search_month, format_response, safe_int,
    get_db_connection
)
from logger_config import setup_logger

logger = setup_logger(__name__)

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
                return jsonify(format_response('duplicate', message='重複データ', time_diff=duplicate_check['time_diff'])), 200
            
            attendance_id = insert_attendance(idm, timestamp, terminal_id)
            
            return jsonify(format_response('success', message='打刻データを保存しました', attendance_id=attendance_id))
            
        except Exception as e:
            logger.error(f"打刻データ受信エラー: {e}", exc_info=True)
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
            logger.error(f"検索エラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'検索エラー: {str(e)}')), 500

    @app.route('/api/stats', methods=['GET'])
    def get_stats_api():
        """統計情報API"""
        try:
            stats = get_stats()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"統計情報取得エラー: {e}", exc_info=True)
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
            logger.error(f"クリーンアップエラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/employees', methods=['GET'])
    def get_employees_api():
        """従業員一覧取得API"""
        try:
            employees = get_employees()
            return jsonify(format_response('success',
                message=f'{len(employees)}名の従業員情報を取得しました', data=employees))
            
        except Exception as e:
            logger.error(f"従業員情報取得エラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/attendance_check', methods=['GET'])
    def attendance_check_api():
        """勤怠チェックAPI（単日または月度）"""
        try:
            employee_id = request.args.get('employee_id', '').strip()
            check_date = request.args.get('check_date', '').strip()
            search_month = request.args.get('search_month', '').strip()
            section = request.args.get('section', '').strip()
            check_all = request.args.get('check_all', '').strip().lower() == 'true'
            
            # 月度検索モード
            if search_month:
                return attendance_check_monthly_api(search_month, employee_id, section, check_all)
            
            # 単日検索モード（既存の処理）
            if not employee_id:
                return jsonify(format_response('error', message='従業員IDが指定されていません')), 400
            
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
            
            # format_responseは辞書を直接マージするため、明示的に'data'キーでラップ
            response_data = {
                'status': 'success',
                'message': '勤怠チェックが完了しました',
                'data': result['data']
            }
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"勤怠チェックエラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500
    
    def attendance_check_monthly_api(search_month, employee_id_filter=None, section_filter=None, check_all=False):
        """月度勤怠チェックAPI（複数従業員・複数日）"""
        try:
            from database import get_employees
            from utils import calculate_date_range, validate_search_month, get_db_connection
            from datetime import date
            
            # 月度バリデーション
            valid, search_month_or_error = validate_search_month(search_month)
            if not valid:
                return jsonify(format_response('error', message=search_month_or_error)), 400
            search_month = search_month_or_error
            
            # 実行日（今日）を取得（未来の日付を除外するため）
            today = date.today()
            
            # 日付範囲を計算
            try:
                start_date_str, end_date_str = calculate_date_range(search_month)
                # 文字列をdateオブジェクトに変換
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError as e:
                return jsonify(format_response('error', message=str(e))), 400
            
            # 未来の日付を除外するため、end_dateを今日までに制限
            if end_date > today:
                end_date = today
            
            # SQLクエリ用に文字列形式に戻す
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # 従業員一覧を取得
            all_employees = get_employees()
            
            # フィルタリング
            filtered_employees = all_employees
            if section_filter:
                filtered_employees = [e for e in filtered_employees if (e.get('section') or '設備') == section_filter]
            if employee_id_filter:
                filtered_employees = [e for e in filtered_employees if str(e['employee_num']) == str(employee_id_filter)]
            
            if not filtered_employees:
                return jsonify(format_response('error', message='該当する従業員が見つかりませんでした')), 400
            
            # 各従業員の各日付をチェック
            results = []
            total_errors = 0
            total_warnings = 0
            
            for employee in filtered_employees:
                emp_id = str(employee['employee_num'])
                emp_name = employee['name']
                emp_section = employee.get('section', '設備')
                
                # 該当月度のスケジュール日付を取得
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT DISTINCT work_date
                        FROM attend_schedule
                        WHERE employee_id = ? AND work_date >= ? AND work_date <= ?
                        ORDER BY work_date
                    """, (emp_id, start_date_str, end_date_str))
                    work_dates = [row[0] for row in cursor.fetchall()]
                
                employee_results = {
                    'employee_id': emp_id,
                    'employee_name': emp_name,
                    'section': emp_section,
                    'dates': [],
                    'error_count': 0,
                    'warning_count': 0
                }
                
                checked_count = 0
                skipped_count = 0
                
                for work_date in work_dates:
                    # 未来の日付はスキップ（実行日より後の日付はチェックしない）
                    try:
                        # work_dateをdateオブジェクトに変換
                        if isinstance(work_date, str):
                            work_date_obj = datetime.strptime(work_date, '%Y-%m-%d').date()
                        elif isinstance(work_date, date):
                            work_date_obj = work_date
                        else:
                            # その他の型の場合は文字列に変換してからパース
                            work_date_str = str(work_date)
                            work_date_obj = datetime.strptime(work_date_str, '%Y-%m-%d').date()
                        
                        # 今日より後の日付はスキップ
                        if work_date_obj > today:
                            skipped_count += 1
                            continue
                    except Exception as e:
                        # パースエラーの場合はログを出力してスキップ
                        logger.warning(f"日付パースエラー: 従業員ID={emp_id}, 日付={work_date}, 型={type(work_date)}, エラー={e}")
                        skipped_count += 1
                        continue
                    
                    checked_count += 1
                    
                    try:
                        result = check_attendance_vs_schedule(emp_id, work_date)
                        if result['status'] == 'success':
                            data = result['data']
                            alerts = data.get('alerts', [])
                            
                            errors = [a for a in alerts if a['type'] == 'error']
                            warnings = [a for a in alerts if a['type'] == 'warning']
                            
                            if errors or warnings:
                                employee_results['dates'].append({
                                    'date': work_date,
                                    'schedule': data.get('schedule'),
                                    'errors': errors,
                                    'warnings': warnings
                                })
                                employee_results['error_count'] += len(errors)
                                employee_results['warning_count'] += len(warnings)
                                total_errors += len(errors)
                                total_warnings += len(warnings)
                    except Exception as e:
                        pass  # エラーは無視して続行
                
                if employee_results['dates']:
                    results.append(employee_results)
            
            return jsonify(format_response(
                'success',
                message=f'月度勤怠チェックが完了しました',
                data={
                    'search_month': search_month,
                    'start_date': start_date,
                    'end_date': end_date,
                    'total_errors': total_errors,
                    'total_warnings': total_warnings,
                    'results': results
                }
            ))
            
        except Exception as e:
            logger.error(f"月度勤怠チェックエラー: {e}", exc_info=True)
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
            logger.error(f"遅刻申告エラー: {e}", exc_info=True)
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
            logger.error(f"早退申告エラー: {e}", exc_info=True)
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
            logger.error(f"遅刻申告取得エラー: {e}", exc_info=True)
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
            logger.error(f"早退申告取得エラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

