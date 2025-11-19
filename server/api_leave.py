#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
休暇願API
休暇申請、承認、PDF保存など
"""

from flask import request, jsonify
from datetime import datetime

from config import Config
from database import get_employees
from leave_request import (
    insert_leave_request, get_leave_requests,
    approve_leave_request, reject_leave_request, withdraw_leave_request, get_leaves_for_date_range
)
from utils import format_response, safe_int, save_pdf_from_html
from pdf_generator import generate_leave_html

def register_leave_api_routes(app):
    """休暇願APIルートを登録"""
    
    @app.route('/api/leave', methods=['POST'])
    def create_leave_request():
        """休暇願申告API"""
        try:
            data = request.get_json()
            if not data:
                return jsonify(format_response('error', message='データが送信されていません')), 400
            
            employee_num = safe_int(data.get('employee_num'), None)
            application_date = data.get('application_date')
            leave_date_from = data.get('leave_date_from')
            leave_date_to = data.get('leave_date_to')
            leave_type = data.get('leave_type')
            leave_subtype = data.get('leave_subtype')
            substitute_work_date = data.get('substitute_work_date')
            other_reason = data.get('other_reason')
            
            if not all([employee_num, application_date, leave_date_from, leave_date_to, leave_type]):
                return jsonify(format_response('error', message='必須フィールドが不足しています')), 400
            
            # 従業員名を取得
            employees = get_employees()
            employee = next((emp for emp in employees if emp['employee_num'] == employee_num), None)
            
            if not employee:
                return jsonify(format_response('error', message='従業員が見つかりません')), 404
            
            employee_name = employee['name']
            
            # 休暇願を登録
            leave_id = insert_leave_request(
                employee_num, employee_name, application_date, leave_date_from, leave_date_to,
                leave_type, leave_subtype, substitute_work_date, other_reason
            )
            
            if leave_id:
                # 自動でPDFを保存（バックグラウンドで実行）
                try:
                    print(f"[自動PDF保存開始] 休暇願 - 従業員: {employee_name} ({employee_num}), 休暇日: {leave_date_from}～{leave_date_to}")
                    html_content = generate_leave_html(
                        employee_name=employee_name,
                        application_date=application_date,
                        leave_date_from=leave_date_from,
                        leave_date_to=leave_date_to,
                        leave_type=leave_type,
                        leave_subtype=leave_subtype,
                        substitute_work_date=substitute_work_date,
                        other_reason=other_reason
                    )
                    
                    pdf_result = save_pdf_from_html(
                        html_content=html_content,
                        filename_prefix='休暇願',
                        employee_num=str(employee_num),
                        date_str=leave_date_from,
                        employee_name=employee_name
                    )
                    
                    if pdf_result['success']:
                        print(f"[自動PDF保存成功] 休暇願: {pdf_result['filename']} -> {pdf_result.get('path', 'N/A')}")
                    else:
                        print(f"[自動PDF保存失敗] 休暇願: {pdf_result.get('message', '不明なエラー')}")
                except Exception as pdf_error:
                    import traceback
                    print(f"[警告] PDF自動保存エラー（登録は成功）: {pdf_error}")
                    traceback.print_exc()
                
                return jsonify(format_response('success', message='休暇願を登録しました', leave_id=leave_id))
            else:
                return jsonify(format_response('error', message='休暇願の登録に失敗しました')), 500
            
        except Exception as e:
            print(f"[エラー] 休暇願申告エラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/leave', methods=['GET'])
    def get_leave_requests_api():
        """休暇願取得API"""
        try:
            employee_num = safe_int(request.args.get('employee_num'), None) if request.args.get('employee_num') else None
            leave_date = request.args.get('leave_date')
            status = request.args.get('status')
            limit = safe_int(request.args.get('limit', '100'), 100)
            
            leaves = get_leave_requests(
                employee_num=employee_num, leave_date=leave_date, status=status, limit=limit
            )
            
            return jsonify(format_response('success',
                message=f'{len(leaves)}件の休暇願を取得しました', data=leaves))
            
        except Exception as e:
            print(f"[エラー] 休暇願取得エラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/leave/<int:leave_id>/approve', methods=['POST'])
    def approve_leave_api(leave_id):
        """休暇願承認API"""
        try:
            data = request.get_json() or {}
            approved_by = data.get('approved_by', 'admin')
            
            success = approve_leave_request(leave_id, approved_by)
            
            if success:
                return jsonify(format_response('success', message='休暇願を承認しました', leave_id=leave_id))
            else:
                return jsonify(format_response('error', message='承認処理に失敗しました')), 500
            
        except Exception as e:
            print(f"[エラー] 休暇願承認エラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/leave/<int:leave_id>/reject', methods=['POST'])
    def reject_leave_api(leave_id):
        """休暇願却下API"""
        try:
            data = request.get_json() or {}
            rejected_by = data.get('rejected_by', 'admin')
            
            success = reject_leave_request(leave_id, rejected_by)
            
            if success:
                return jsonify(format_response('success', message='休暇願を却下しました', leave_id=leave_id))
            else:
                return jsonify(format_response('error', message='却下処理に失敗しました')), 500
            
        except Exception as e:
            print(f"[エラー] 休暇願却下エラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/leave/<int:leave_id>/withdraw', methods=['POST'])
    def withdraw_leave_api(leave_id):
        """休暇願取り下げAPI（承認前のみ可能）"""
        try:
            success = withdraw_leave_request(leave_id)
            
            if success:
                return jsonify(format_response('success', message='休暇願を取り下げました', leave_id=leave_id))
            else:
                return jsonify(format_response('error', message='取り下げ処理に失敗しました。承認前の申請のみ取り下げ可能です。')), 400
            
        except Exception as e:
            print(f"[エラー] 休暇願取り下げエラー: {e}")
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/leave/save_pdf', methods=['POST'])
    def save_leave_pdf():
        """休暇願PDFをサーバーに保存"""
        try:
            data = request.get_json()
            if not data:
                return jsonify(format_response('error', message='データが送信されていません')), 400
            
            html_content = data.get('html_content')
            employee_num = data.get('employee_num')
            employee_name = data.get('employee_name', '')
            leave_date = data.get('leave_date')
            
            if not all([html_content, employee_num, leave_date]):
                return jsonify(format_response('error', message='必須フィールドが不足しています')), 400
            
            # 共通関数を使用してPDF保存
            result = save_pdf_from_html(
                html_content=html_content,
                filename_prefix='休暇願',
                employee_num=employee_num,
                date_str=leave_date,
                employee_name=employee_name
            )
            
            if result['success']:
                return jsonify(format_response('success', 
                    message=result['message'], 
                    filename=result['filename'], 
                    path=result['path']))
            else:
                return jsonify(format_response('error', message=result['message'])), 500
            
        except Exception as e:
            print(f"[エラー] PDF保存エラー: {e}")
            import traceback
            traceback.print_exc()
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

