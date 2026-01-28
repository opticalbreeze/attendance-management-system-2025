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
from constants import CheckType

logger = setup_logger(__name__)

# Blueprint 作成
check_status_bp = Blueprint('check_status', __name__)

@check_status_bp.route('/api/attendance-check-status', methods=['GET'])
def get_check_status():
    """
    打刻チェック状況を取得
    
    Query parameters:
        employee_num: 従業員番号
        work_date: 勤務日
        check_type: チェックタイプ ('missing_punch', 'time_difference', or 'punch_leak')
    """
    try:
        employee_num = request.args.get('employee_num')
        work_date = request.args.get('work_date')
        check_type = request.args.get('check_type')
        
        # check_typeをトリム（空白や改行を削除）
        if check_type:
            check_type = str(check_type).strip()
        
        if not all([employee_num, work_date, check_type]):
            response = format_response('error', message='必要なパラメータが不足しています')
            response['success'] = False
            return jsonify(response), 400
        
        # チェックタイプの検証
        valid_check_types = CheckType.get_all()
        
        if not CheckType.is_valid(check_type):
            logger.error(f"[GET] 無効なチェックタイプ: check_type={check_type!r}, valid_types={valid_check_types}")
            response = format_response('error', message=f'無効なチェックタイプです: {check_type}')
            response['success'] = False
            response['debug_info'] = {
                'check_type': check_type,
                'valid_types': valid_check_types,
                'check_type_repr': repr(check_type)
            }
            return jsonify(response), 400
        
        status = get_attendance_check_status(employee_num, work_date, check_type)
        
        # チェック済みデータがある場合のみデバッグ出力
        if status and status.get('is_checked'):
            logger.info(f"[API-GET] ✓ チェック済みデータ取得: employee_num={employee_num}, work_date={work_date}, check_type={check_type}, is_checked={status.get('is_checked')}")
        
        # フロントエンドとの互換性のため、successフィールドも含める
        # format_responseは辞書を直接マージするため、dataキーでラップしない
        # statusがNoneの場合はdataフィールドをNoneに設定
        if status:
            response = format_response('success', message='打刻チェック状況を取得しました')
            response['success'] = True
            response['data'] = status
        else:
            response = format_response('success', message='打刻チェック状況を取得しました')
            response['success'] = True
            response['data'] = None
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"打刻チェック状況取得エラー: {e}", exc_info=True)
        response = format_response('error', message='システムエラーが発生しました')
        response['success'] = False
        return jsonify(response), 500

@check_status_bp.route('/api/attendance-check-status', methods=['POST'])
def update_check_status():
    """
    打刻チェック状況を更新
    
    Request body:
        employee_num: 従業員番号
        work_date: 勤務日
        check_type: チェックタイプ ('missing_punch', 'time_difference', or 'punch_leak')
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
        
        # check_typeをトリム（空白や改行を削除）
        if check_type:
            check_type = str(check_type).strip()
        
        if not all([employee_num, work_date, check_type]):
            response = format_response('error', message='必要なパラメータが不足しています')
            response['success'] = False
            return jsonify(response), 400
        
        # チェックタイプの検証
        valid_check_types = CheckType.get_all()
        
        if not CheckType.is_valid(check_type):
            logger.error(f"[POST] 無効なチェックタイプ: check_type={check_type!r}, valid_types={valid_check_types}")
            logger.error(f"[POST] CheckType.is_valid('punch_leak')={CheckType.is_valid('punch_leak')}")
            response = format_response('error', message=f'無効なチェックタイプです: {check_type} (有効なタイプ: {", ".join(valid_check_types)})')
            response['success'] = False
            response['debug_info'] = {
                'check_type': check_type,
                'valid_types': valid_check_types,
                'CheckType.get_all()': CheckType.get_all() if hasattr(CheckType, 'get_all') else 'N/A',
                'CheckType.PUNCH_LEAK': getattr(CheckType, 'PUNCH_LEAK', 'N/A'),
                'is_valid_punch_leak': CheckType.is_valid('punch_leak') if hasattr(CheckType, 'is_valid') else 'N/A'
            }
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
            logger.info(f"[POST] データベースへの保存成功: employee_num={employee_num}, work_date={work_date}, check_type={check_type}, is_checked={is_checked}")
            # フロントエンドとの互換性のため、successフィールドも含める
            response = format_response('success', message='打刻チェック状況を更新しました')
            response['success'] = True
            return jsonify(response)
        else:
            logger.error(f"[POST] データベースへの保存失敗: employee_num={employee_num}, work_date={work_date}, check_type={check_type}, is_checked={is_checked}")
            response = format_response('error', message='更新に失敗しました')
            response['success'] = False
            return jsonify(response), 500
            
    except Exception as e:
        logger.error(f"打刻チェック状況更新エラー: {e}", exc_info=True)
        response = format_response('error', message='システムエラーが発生しました')
        response['success'] = False
        return jsonify(response), 500

@check_status_bp.route('/api/test-check-status', methods=['GET'])
def test_check_status():
    """
    テスト用: 2025年12月度のチェックデータを確認
    """
    try:
        from database import get_db_connection
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, employee_num, work_date, check_type, is_checked, 
                       checked_by, checked_at, notes, created_at, updated_at
                FROM attendance_check_status
                WHERE work_date >= '2025-12-01' AND work_date <= '2025-12-31'
                ORDER BY work_date, employee_num, check_type
            """)
            
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append({
                    'id': row[0],
                    'employee_num': row[1],
                    'work_date': row[2],
                    'check_type': row[3],
                    'is_checked': bool(row[4]),
                    'checked_by': row[5],
                    'checked_at': row[6],
                    'notes': row[7],
                    'created_at': row[8],
                    'updated_at': row[9]
                })
            
            logger.info(f"[TEST] 2025年12月度のチェックデータ: {len(results)}件")
            response = format_response('success', data=results, message=f'2025年12月度のチェックデータ: {len(results)}件')
            response['success'] = True
            return jsonify(response)
            
    except Exception as e:
        logger.error(f"[TEST] エラー: {e}", exc_info=True)
        response = format_response('error', message='システムエラーが発生しました')
        response['success'] = False
        return jsonify(response), 500

def register_check_status_api_routes(app):
    """
    打刻チェック状況管理APIルートをアプリケーションに登録
    """
    app.register_blueprint(check_status_bp)
    logger.info("打刻チェック状況管理API routes registered successfully")