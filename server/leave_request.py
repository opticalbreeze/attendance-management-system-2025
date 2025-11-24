#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
休暇願管理モジュール
休暇申請、承認、集計機能を提供
"""

import sqlite3
from datetime import datetime
from config import Config
from utils import get_database_connection, get_db_connection
from logger_config import setup_logger

logger = setup_logger(__name__)

def init_leave_request_table():
    """
    休暇願テーブルの初期化（後方互換性のため残存）
    
    Note: この関数は非推奨です。database.init_database()を使用してください。
    この関数は既存コードとの互換性のために残されています。
    """
    from database import init_leave_request_table_internal
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # database.pyの内部関数を呼び出し
        init_leave_request_table_internal(cursor)

def insert_leave_request(employee_num, employee_name, application_date, 
                         leave_date_from, leave_date_to, leave_type,
                         leave_subtype=None, substitute_work_date=None, other_reason=None):
    """
    休暇願を登録
    
    Args:
        employee_num: 従業員番号
        employee_name: 従業員名
        application_date: 申請日
        leave_date_from: 休暇開始日
        leave_date_to: 休暇終了日
        leave_type: 休暇種類（有給休暇、振替休日、特別休暇、その他）
        leave_subtype: 特別休暇のサブタイプ
        substitute_work_date: 振替休日の出勤日
        other_reason: その他の理由
    
    Returns:
        int: 登録されたIDまたはNone
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO leave_requests (
                    employee_num, employee_name, application_date,
                    leave_date_from, leave_date_to, leave_type,
                    leave_subtype, substitute_work_date, other_reason,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """, (
                str(employee_num), employee_name, application_date,
                leave_date_from, leave_date_to, leave_type,
                leave_subtype, substitute_work_date, other_reason,
                now, now
            ))
            
            leave_id = cursor.lastrowid
            logger.info(f"休暇願登録: ID={leave_id}, 従業員={employee_name}, 種類={leave_type}, 期間={leave_date_from}～{leave_date_to}")
            return leave_id
        
    except Exception as e:
        logger.error(f"休暇願登録エラー: {e}", exc_info=True)
        return None

def get_leave_requests(employee_num=None, leave_date=None, status=None, limit=100):
    """
    休暇願を取得
    
    Args:
        employee_num: 従業員番号（フィルタ用）
        leave_date: 休暇日（フィルタ用）
        status: ステータス（フィルタ用）
        limit: 取得件数
    
    Returns:
        list: 休暇願のリスト
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM leave_requests WHERE 1=1"
            params = []
            
            if employee_num:
                query += " AND employee_num = ?"
                params.append(employee_num)
            
            if leave_date:
                query += " AND leave_date_from <= ? AND leave_date_to >= ?"
                params.append(leave_date)
                params.append(leave_date)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # 結果を辞書形式に変換
            columns = [desc[0] for desc in cursor.description]
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            return results
        
    except Exception as e:
        logger.error(f"休暇願取得エラー: {e}", exc_info=True)
        return []

def approve_leave_request(leave_id, approved_by):
    """休暇願を承認（共通関数を使用）"""
    from utils import update_request_status
    
    result = update_request_status(
        table_name='leave_requests',
        request_id=leave_id,
        status='approved',
        updated_by=approved_by
    )
    
    if result['success']:
        logger.info(f"休暇願承認: ID={leave_id}")
    
    return result['success']

def reject_leave_request(leave_id, rejected_by):
    """休暇願を却下（共通関数を使用）"""
    from utils import update_request_status
    
    result = update_request_status(
        table_name='leave_requests',
        request_id=leave_id,
        status='rejected',
        updated_by=rejected_by
    )
    
    if result['success']:
        logger.info(f"休暇願却下: ID={leave_id}")
    
    return result['success']

def withdraw_leave_request(leave_id):
    """
    休暇願を取り下げ（承認前のみ可能）
    データは削除せず、ステータスを'withdrawn'に変更（共通関数を使用）
    
    Args:
        leave_id: 休暇願ID
    
    Returns:
        bool: 成功した場合True、失敗した場合False
    """
    from utils import update_request_status
    
    result = update_request_status(
        table_name='leave_requests',
        request_id=leave_id,
        status='withdrawn'
    )
    
    if result['success']:
        logger.info(f"休暇願取り下げ: ID={leave_id}")
    else:
        logger.error(f"休暇願取り下げ失敗: {result['message']}")
    
    return result['success']

def get_leaves_for_date_range(employee_num, start_date, end_date):
    """
    指定期間の休暇願を取得
    
    Args:
        employee_num: 従業員番号
        start_date: 開始日
        end_date: 終了日
    
    Returns:
        list: 休暇願のリスト
    """
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM leave_requests
            WHERE employee_num = ?
              AND status = 'approved'
              AND (
                  (leave_date_from >= ? AND leave_date_from <= ?)
                  OR (leave_date_to >= ? AND leave_date_to <= ?)
                  OR (leave_date_from <= ? AND leave_date_to >= ?)
              )
            ORDER BY leave_date_from
        """, (employee_num, start_date, end_date, start_date, end_date, start_date, end_date))
        
        rows = cursor.fetchall()
        
        # 結果を辞書形式に変換
        columns = [desc[0] for desc in cursor.description]
        results = []
        for row in rows:
            results.append(dict(zip(columns, row)))
        
        conn.close()
        return results
        
    except Exception as e:
        logger.error(f"休暇願取得エラー: {e}", exc_info=True)
        if conn:
            conn.close()
        return []

