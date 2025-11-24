#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベースユーティリティモジュール
データベース接続とトランザクション管理の専門モジュール
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime

from config import Config
from logger_config import setup_logger

logger = setup_logger(__name__)

def get_database_connection():
    """
    データベース接続を取得（共通関数）
    
    Returns:
        sqlite3.Connection: データベース接続オブジェクト
    """
    return sqlite3.connect(Config.DATABASE_PATH)

@contextmanager
def get_db_connection():
    """
    データベース接続のコンテキストマネージャー（推奨）
    
    使用例:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ...")
            # 自動的にコミット・クローズされる
    
    Yields:
        sqlite3.Connection: データベース接続オブジェクト
    """
    conn = None
    try:
        conn = get_database_connection()
        yield conn
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def check_duplicate_attendance(idm, timestamp, terminal_id, threshold_seconds=None):
    """
    チャタリング防止: 重複打刻をチェック
    同じIDm、端末で指定秒数以内の打刻は重複と判定
    """
    if threshold_seconds is None:
        threshold_seconds = Config.CHATTERING_THRESHOLD_SECONDS
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 同じIDm、端末での最新の打刻を取得
            cursor.execute("""
                SELECT timestamp, received_at 
                FROM attendance 
                WHERE idm = ? AND terminal_id = ?
                ORDER BY received_at DESC 
                LIMIT 1
            """, (idm, terminal_id))
            
            last_record = cursor.fetchone()
        
        if not last_record:
            return {'is_duplicate': False, 'time_diff': None}
        
        # 時刻差を計算
        try:
            last_timestamp = datetime.fromisoformat(last_record[0].replace('Z', '+00:00'))
            current_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_diff = abs((current_timestamp - last_timestamp).total_seconds())
            
            is_duplicate = time_diff <= threshold_seconds
            
            return {
                'is_duplicate': is_duplicate,
                'time_diff': time_diff,
                'last_record': {
                    'timestamp': last_record[0],
                    'received_at': last_record[1]
                }
            }
            
        except ValueError as e:
            logger.warning(f"時刻解析エラー: {e}")
            return {'is_duplicate': False, 'time_diff': None}
            
    except sqlite3.Error as e:
        logger.error(f"重複チェック失敗: {e}")
        return {'is_duplicate': False, 'time_diff': None}

