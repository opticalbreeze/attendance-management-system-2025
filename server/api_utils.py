#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APIユーティリティモジュール
API応答フォーマットと汎用処理の専門モジュール
"""

from datetime import datetime
from database_utils import get_db_connection
from logger_config import setup_logger

logger = setup_logger(__name__)

def format_response(status, data=None, message=None, **kwargs):
    """
    統一されたレスポンス形式を生成
    
    Args:
        status: ステータス ('success' or 'error')
        data: データ（辞書の場合は直接マージ、それ以外は'data'キーに設定）
        message: メッセージ
        **kwargs: 追加パラメータ
    
    Returns:
        dict: 統一されたレスポンス形式
        
    Note:
        - dataが辞書の場合: 辞書の内容が直接レスポンスにマージされる
        - dataが辞書以外の場合: response['data']に設定される
        - 辞書を'data'キーでラップしたい場合は、明示的に{'data': dict}を返すこと
    """
    response = {'status': status}
    
    if message:
        response['message'] = message
    
    if data is not None:
        if isinstance(data, dict):
            # 辞書の場合は直接マージ（既存の動作を維持）
            response.update(data)
        else:
            # リストやその他の型の場合は'data'キーに設定
            response['data'] = data
    
    # 追加パラメータ
    response.update(kwargs)
    
    return response

def safe_int(value, default=0):
    """
    安全に整数に変換
    
    Args:
        value: 変換する値
        default: 変換失敗時のデフォルト値
    
    Returns:
        int or default: 変換結果
    """
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default

def update_request_status(table_name, request_id, status, updated_by=None):
    """
    申請のステータスを更新（汎用関数）
    
    Args:
        table_name: テーブル名 ('overtime_applications' or 'leave_requests')
        request_id: 申請ID
        status: 新しいステータス ('approved', 'rejected', 'withdrawn')
        updated_by: 更新者（承認/却下の場合に使用、オプション）
    
    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # テーブル名のバリデーション
            valid_tables = ['overtime_applications', 'leave_requests']
            if table_name not in valid_tables:
                return {
                    'success': False,
                    'message': f'無効なテーブル名: {table_name}'
                }
            
            # ステータスのバリデーション
            valid_statuses = ['approved', 'rejected', 'withdrawn']
            if status not in valid_statuses:
                return {
                    'success': False,
                    'message': f'無効なステータス: {status}'
                }
            
            # 取り下げの場合は現在のステータスを確認
            if status == 'withdrawn':
                cursor.execute(f"SELECT status FROM {table_name} WHERE id = ?", (request_id,))
                result = cursor.fetchone()
                
                if not result:
                    return {
                        'success': False,
                        'message': f'申請ID {request_id} が見つかりません'
                    }
                
                current_status = result[0]
                if current_status != 'pending':
                    return {
                        'success': False,
                        'message': f'申請は既に承認済みまたは却下済みのため取り下げできません（現在のステータス: {current_status}）'
                    }
            
            # ステータス更新
            now = datetime.now().isoformat()
            
            if status in ['approved', 'rejected']:
                # 承認/却下の場合はapproved_byとapproved_atも設定
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET status = ?,
                        approved_by = ?,
                        approved_at = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (status, updated_by or 'admin', now, now, request_id))
            else:
                # 取り下げの場合はupdated_atのみ更新
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET status = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (status, now, request_id))
            
            status_names = {
                'approved': '承認',
                'rejected': '却下',
                'withdrawn': '取り下げ'
            }
            
            return {
                'success': True,
                'message': f'申請を{status_names.get(status, status)}しました'
            }
        
    except Exception as e:
        logger.error(f"ステータス更新エラー: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'エラー: {str(e)}'
        }

