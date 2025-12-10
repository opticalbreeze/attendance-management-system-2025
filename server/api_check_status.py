#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打刻チェック状況管理API
管理者が打刻なし・時刻差異エラーをチェック済みかどうかの状況を管理
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime

from database import (
    get_attendance_check_status, 
    update_attendance_check_status
)
from auth import login_required
from api_utils import format_response
from logger_config import setup_logger

logger = setup_logger(__name__)

# Blueprint 作成
check_status_bp = Blueprint('check_status', __name__)

@check_status_bp.route('/api/attendance-check-status', methods=['GET'])
@login_required
def get_check_status():
    """
    打刻チェック状況を取得
    
    Query parameters:
        employee_num: 従業員番号
        work_date: 勤務日
        check_type: チェックタイプ ('missing_punch' or 'time_difference')
    """
    try:
        employee_num = request.args.get('employee_num')
        work_date = request.args.get('work_date')
        check_type = request.args.get('check_type')
        
        if not all([employee_num, work_date, check_type]):
            response = format_response('error', message='必要なパラメータが不足しています')
            response['success'] = False
            return jsonify(response), 400
        
        if check_type not in ['missing_punch', 'time_difference']:
            response = format_response('error', message='無効なチェックタイプです')
            response['success'] = False
            return jsonify(response), 400
        
        status = get_attendance_check_status(employee_num, work_date, check_type)
        
        # フロントエンドとの互換性のため、successフィールドも含める
        response = format_response('success', data=status, message='打刻チェック状況を取得しました')
        response['success'] = True
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"打刻チェック状況取得エラー: {e}", exc_info=True)
        response = format_response('error', message='システムエラーが発生しました')
        response['success'] = False
        return jsonify(response), 500

@check_status_bp.route('/api/attendance-check-status', methods=['POST'])
@login_required
def update_check_status():
    """
    打刻チェック状況を更新
    
    Request body:
        employee_num: 従業員番号
        work_date: 勤務日
        check_type: チェックタイプ ('missing_punch' or 'time_difference')
        is_checked: チェック済みかどうか
        notes: 備考（任意）
    """
    try:
        data = request.get_json()
        
        if not data:
            response = format_response('error', message='リクエストデータが不正です')
            response['success'] = False
            return jsonify(response), 400
        
        employee_num = data.get('employee_num')
        work_date = data.get('work_date')
        check_type = data.get('check_type')
        is_checked = data.get('is_checked', False)
        notes = data.get('notes', '')
        
        if not all([employee_num, work_date, check_type]):
            response = format_response('error', message='必要なパラメータが不足しています')
            response['success'] = False
            return jsonify(response), 400
        
        if check_type not in ['missing_punch', 'time_difference']:
            response = format_response('error', message='無効なチェックタイプです')
            response['success'] = False
            return jsonify(response), 400
        
        # 管理者情報（セッションから取得）
        # 優先順位: admin_user_id > admin_username > タイムスタンプベースのID
        # チェック済みの場合のみchecked_byを設定し、チェック解除の場合はNoneを設定
        checked_by = (
            session.get('admin_user_id') or 
            session.get('admin_username') or 
            f"admin_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ) if is_checked else None
        
        success = update_attendance_check_status(
            employee_num=employee_num,
            work_date=work_date,
            check_type=check_type,
            is_checked=bool(is_checked),
            checked_by=checked_by,  # 既にis_checkedに応じて設定済み
            notes=notes
        )
        
        if success:
            # フロントエンドとの互換性のため、successフィールドも含める
            response = format_response('success', message='打刻チェック状況を更新しました')
            response['success'] = True
            return jsonify(response)
        else:
            response = format_response('error', message='更新に失敗しました')
            response['success'] = False
            return jsonify(response), 500
            
    except Exception as e:
        logger.error(f"打刻チェック状況更新エラー: {e}", exc_info=True)
        response = format_response('error', message='システムエラーが発生しました')
        response['success'] = False
        return jsonify(response), 500

def register_check_status_api_routes(app):
    """
    打刻チェック状況管理APIルートをアプリケーションに登録
    """
    app.register_blueprint(check_status_bp)
    logger.info("打刻チェック状況管理API routes registered successfully")