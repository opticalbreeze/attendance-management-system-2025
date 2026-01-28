#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
時間外申告API
時間外作業の申告、承認、PDF保存など
"""

from flask import request, jsonify
from datetime import datetime

from config import Config
from database import get_employees
from overtime import (
    insert_overtime_application, get_overtime_applications,
    approve_overtime, reject_overtime, withdraw_overtime, get_monthly_overtime_summary
)
from utils import format_response, safe_int, save_pdf_from_html
from pdf_generator import generate_overtime_html
from logger_config import setup_logger

logger = setup_logger(__name__)

def register_overtime_api_routes(app):
    """時間外申告APIルートを登録"""
    
    @app.route('/api/overtime', methods=['POST'])
    def create_overtime_application():
        """時間外作業申告API"""
        try:
            data = request.get_json()
            if not data:
                return jsonify(format_response('error', message='データが送信されていません')), 400
            
            employee_num = safe_int(data.get('employee_num'), None)
            application_date = data.get('application_date')
            work_date = data.get('work_date')
            overtime_entries = data.get('overtime_entries', [])
            
            if not all([employee_num, application_date, work_date]):
                return jsonify(format_response('error', message='必須フィールドが不足しています')), 400
            
            if not overtime_entries:
                return jsonify(format_response('error', message='時間外作業内容が入力されていません')), 400
            
            # 従業員名を取得
            employees = get_employees()
            employee = next((emp for emp in employees if emp['employee_num'] == employee_num), None)
            
            if not employee:
                return jsonify(format_response('error', message='従業員が見つかりません')), 404
            
            employee_name = employee['name']
            
            # 複数の時間外作業を登録
            created_ids = []
            for entry in overtime_entries:
                start_time = entry.get('start_time')
                end_time = entry.get('end_time')
                description = entry.get('description', '')
                actual_work_minutes = entry.get('actual_work_minutes', 0)
                
                if start_time and end_time:
                    overtime_id = insert_overtime_application(
                        employee_num=employee_num,
                        employee_name=employee_name,
                        application_date=application_date,
                        work_date=work_date,
                        start_time=start_time,
                        end_time=end_time,
                        description=description,
                        actual_work_minutes=actual_work_minutes
                    )
                    if overtime_id:
                        created_ids.append(overtime_id)
            
            if created_ids:
                # 自動でPDFを保存（バックグラウンドで実行）
                try:
                    logger.info(f"自動PDF保存開始: 時間外申告 - 従業員={employee_name} ({employee_num}), 作業日={work_date}")
                    html_content = generate_overtime_html(
                        employee_name=employee_name,
                        application_date=application_date,
                        work_date=work_date,
                        overtime_entries=overtime_entries
                    )
                    
                    # 最初の作成されたIDを使用（複数の場合は最初の1つ）
                    first_overtime_id = created_ids[0] if created_ids else None
                    pdf_result = save_pdf_from_html(
                        html_content=html_content,
                        filename_prefix='時間外',
                        employee_num=str(employee_num),
                        date_str=work_date,
                        employee_name=employee_name,
                        additional_css='.overtime-item { border: 1px solid #000; padding: 10pt; margin-bottom: 10pt; page-break-inside: avoid; }',
                        document_id=first_overtime_id
                    )
                    
                    if pdf_result['success']:
                        logger.info(f"自動PDF保存成功: 時間外申告 - {pdf_result['filename']} -> {pdf_result.get('path', 'N/A')}")
                    else:
                        logger.warning(f"自動PDF保存失敗: 時間外申告 - {pdf_result.get('message', '不明なエラー')}")
                except Exception as pdf_error:
                    logger.warning(f"PDF自動保存エラー（登録は成功）: {pdf_error}", exc_info=True)
                
                return jsonify(format_response('success',
                    message=f'{len(created_ids)}件の時間外作業申告を登録しました', overtime_ids=created_ids))
            else:
                return jsonify(format_response('error', message='時間外作業申告の登録に失敗しました')), 500
            
        except Exception as e:
            logger.error(f"時間外申告エラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/overtime', methods=['GET'])
    def get_overtime_applications_api():
        """時間外申告取得API"""
        try:
            employee_num = safe_int(request.args.get('employee_num'), None) if request.args.get('employee_num') else None
            work_date = request.args.get('work_date')
            status = request.args.get('status')
            limit = safe_int(request.args.get('limit', '100'), 100)
            
            applications = get_overtime_applications(
                employee_num=employee_num, work_date=work_date, status=status, limit=limit
            )
            
            return jsonify(format_response('success',
                message=f'{len(applications)}件の時間外申告を取得しました', data=applications))
            
        except Exception as e:
            logger.error(f"時間外申告取得エラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/overtime/<int:overtime_id>/approve', methods=['POST'])
    def approve_overtime_api(overtime_id):
        """時間外申告承認API"""
        try:
            data = request.get_json() or {}
            approved_by = data.get('approved_by', 'admin')
            
            success = approve_overtime(overtime_id, approved_by)
            
            if success:
                return jsonify(format_response('success', message='時間外申告を承認しました', overtime_id=overtime_id))
            else:
                return jsonify(format_response('error', message='承認処理に失敗しました')), 500
            
        except Exception as e:
            logger.error(f"時間外承認エラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/overtime/<int:overtime_id>/reject', methods=['POST'])
    def reject_overtime_api(overtime_id):
        """時間外申告却下API"""
        try:
            data = request.get_json() or {}
            rejected_by = data.get('rejected_by', 'admin')
            
            success = reject_overtime(overtime_id, rejected_by)
            
            if success:
                return jsonify(format_response('success', message='時間外申告を却下しました', overtime_id=overtime_id))
            else:
                return jsonify(format_response('error', message='却下処理に失敗しました')), 500
            
        except Exception as e:
            logger.error(f"時間外却下エラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/overtime/<int:overtime_id>/withdraw', methods=['POST'])
    def withdraw_overtime_api(overtime_id):
        """時間外申告取り下げAPI（承認前のみ可能）"""
        try:
            success = withdraw_overtime(overtime_id)
            
            if success:
                return jsonify(format_response('success', message='時間外申告を取り下げました', overtime_id=overtime_id))
            else:
                return jsonify(format_response('error', message='取り下げ処理に失敗しました。承認前の申請のみ取り下げ可能です。')), 400
            
        except Exception as e:
            logger.error(f"時間外取り下げエラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/overtime/monthly_summary', methods=['GET'])
    def get_monthly_overtime_summary_api():
        """月次時間外集計API"""
        try:
            employee_num = safe_int(request.args.get('employee_num'), None) if request.args.get('employee_num') else None
            year = safe_int(request.args.get('year'), datetime.now().year)
            month = safe_int(request.args.get('month'), datetime.now().month)
            
            if not employee_num:
                return jsonify(format_response('error', message='従業員番号が指定されていません')), 400
            
            summary = get_monthly_overtime_summary(employee_num, year, month)
            
            if summary:
                return jsonify(format_response('success', message='月次集計を取得しました', data=summary))
            else:
                return jsonify(format_response('error', message='集計データが見つかりません')), 404
            
        except Exception as e:
            logger.error(f"月次集計エラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/overtime/<int:overtime_id>/reprint_pdf', methods=['POST'])
    def reprint_overtime_pdf(overtime_id):
        """時間外申告PDFを再出力（既存の申請データから）"""
        try:
            from database_utils import get_db_connection
            from constants import DatabaseConstants
            
            # データベースから時間外申告データを取得
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT * FROM {DatabaseConstants.TABLE_OVERTIME_APPLICATIONS}
                    WHERE id = ?
                """, (overtime_id,))
                
                row = cursor.fetchone()
                if not row:
                    return jsonify(format_response('error', message='時間外申告が見つかりません')), 404
                
                # カラム名を取得
                columns = [desc[0] for desc in cursor.description]
                overtime_data = dict(zip(columns, row))
            
            # データから必要な情報を取得
            employee_name = overtime_data.get('employee_name', '')
            employee_num = overtime_data.get('employee_num', '')
            application_date = overtime_data.get('application_date', '')
            work_date = overtime_data.get('work_date', '')
            start_time = overtime_data.get('start_time', '')
            end_time = overtime_data.get('end_time', '')
            description = overtime_data.get('description', '')
            
            # 時間外作業エントリを生成
            overtime_entries = [{
                'start_time': start_time,
                'end_time': end_time,
                'description': description
            }]
            
            # HTMLを生成（既存の関数を使用）
            html_content = generate_overtime_html(
                employee_name=employee_name,
                application_date=application_date,
                work_date=work_date,
                overtime_entries=overtime_entries
            )
            
            # PDFを保存（既存の関数を使用）
            result = save_pdf_from_html(
                html_content=html_content,
                filename_prefix='時間外',
                employee_num=str(employee_num),
                date_str=work_date,
                employee_name=employee_name,
                additional_css='.overtime-item { border: 1px solid #000; padding: 10pt; margin-bottom: 10pt; page-break-inside: avoid; }',
                document_id=overtime_id
            )
            
            if result['success']:
                return jsonify(format_response('success', 
                    message=result['message'], 
                    filename=result['filename'], 
                    path=result['path']))
            else:
                return jsonify(format_response('error', message=result['message'])), 500
            
        except Exception as e:
            logger.error(f"PDF再出力エラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

    @app.route('/api/overtime/save_pdf', methods=['POST'])
    def save_overtime_pdf():
        """時間外申告PDFをサーバーに保存"""
        try:
            data = request.get_json()
            if not data:
                return jsonify(format_response('error', message='データが送信されていません')), 400
            
            html_content = data.get('html_content')
            employee_num = data.get('employee_num')
            employee_name = data.get('employee_name', '')
            work_date = data.get('work_date')
            
            if not all([html_content, employee_num, work_date]):
                return jsonify(format_response('error', message='必須フィールドが不足しています')), 400
            
            # 共通関数を使用してPDF保存
            result = save_pdf_from_html(
                html_content=html_content,
                filename_prefix='時間外',
                employee_num=employee_num,
                date_str=work_date,
                employee_name=employee_name,
                additional_css='.overtime-item { border: 1px solid #000; padding: 10pt; margin-bottom: 10pt; page-break-inside: avoid; }'
            )
            
            if result['success']:
                return jsonify(format_response('success', 
                    message=result['message'], 
                    filename=result['filename'], 
                    path=result['path']))
            else:
                return jsonify(format_response('error', message=result['message'])), 500
            
        except Exception as e:
            logger.error(f"PDF保存エラー: {e}", exc_info=True)
            return jsonify(format_response('error', message=f'エラー: {str(e)}')), 500

