#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
除外リストDAO
通知除外リストのCRUD操作を担当
"""

from datetime import datetime
from typing import Set, List
from database_utils import get_db_connection
from logger_config import setup_logger

logger = setup_logger(__name__)

def get_all_excluded_employee_ids() -> Set[str]:
    """
    除外リストに登録されているすべての従業員IDを取得
    
    Returns:
        Set[str]: 除外対象の従業員IDのセット
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT employee_id FROM notification_exclusions")
            rows = cursor.fetchall()
            
            excluded_set = {str(row[0]) for row in rows}
            logger.debug(f"除外リスト取得: {len(excluded_set)}件")
            return excluded_set
            
    except Exception as e:
        logger.error(f"除外リスト取得エラー: {e}", exc_info=True)
        return set()

def set_excluded_employee_ids(employee_ids: Set[str]) -> bool:
    """
    除外リストを設定（全置換）
    
    Args:
        employee_ids: 除外対象の従業員IDのセット
    
    Returns:
        bool: 成功したかどうか
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            # 既存のレコードをすべて削除
            cursor.execute("DELETE FROM notification_exclusions")
            
            # 新しいレコードを挿入
            if employee_ids:
                values = [(str(emp_id), now, now) for emp_id in employee_ids]
                cursor.executemany("""
                    INSERT INTO notification_exclusions (employee_id, created_at, updated_at)
                    VALUES (?, ?, ?)
                """, values)
            
            logger.info(f"除外リスト設定: {len(employee_ids)}件 - {list(employee_ids)}")
            return True
            
    except Exception as e:
        logger.error(f"除外リスト設定エラー: {e}", exc_info=True)
        return False

def add_excluded_employee_id(employee_id: str) -> bool:
    """
    除外リストに従業員IDを追加
    
    Args:
        employee_id: 追加する従業員ID
    
    Returns:
        bool: 成功したかどうか
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            # UPSERT操作
            cursor.execute("""
                INSERT OR REPLACE INTO notification_exclusions 
                (employee_id, created_at, updated_at)
                VALUES (?, 
                        COALESCE((SELECT created_at FROM notification_exclusions WHERE employee_id = ?), ?), 
                        ?)
            """, (employee_id, employee_id, now, now))
            
            logger.info(f"除外リスト追加: {employee_id}")
            return True
            
    except Exception as e:
        logger.error(f"除外リスト追加エラー: {e}", exc_info=True)
        return False

def remove_excluded_employee_id(employee_id: str) -> bool:
    """
    除外リストから従業員IDを削除
    
    Args:
        employee_id: 削除する従業員ID
    
    Returns:
        bool: 成功したかどうか
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM notification_exclusions WHERE employee_id = ?", (employee_id,))
            
            logger.info(f"除外リスト削除: {employee_id}")
            return True
            
    except Exception as e:
        logger.error(f"除外リスト削除エラー: {e}", exc_info=True)
        return False

def is_excluded(employee_id: str) -> bool:
    """
    従業員IDが除外リストに含まれているか確認
    
    Args:
        employee_id: 確認する従業員ID
    
    Returns:
        bool: 除外リストに含まれている場合True
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM notification_exclusions WHERE employee_id = ?", (employee_id,))
            count = cursor.fetchone()[0]
            
            return count > 0
            
    except Exception as e:
        logger.error(f"除外リスト確認エラー: {e}", exc_info=True)
        return False
