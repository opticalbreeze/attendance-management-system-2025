#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
休暇願管理モジュール
休暇申請、承認、集計機能を提供
"""

import sqlite3
from datetime import datetime
from config import Config
from utils import get_database_connection

def init_leave_request_table():
    """休暇願テーブルの初期化"""
    conn = get_database_connection()
    cursor = conn.cursor()
    
    # 休暇願テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_num TEXT NOT NULL,
            employee_name TEXT NOT NULL,
            application_date TEXT NOT NULL,
            leave_date_from TEXT NOT NULL,
            leave_date_to TEXT NOT NULL,
            leave_type TEXT NOT NULL,
            leave_subtype TEXT,
            substitute_work_date TEXT,
            other_reason TEXT,
            status TEXT DEFAULT 'pending',
            approved_by TEXT,
            approved_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # インデックス作成
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leave_employee ON leave_requests(employee_num)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leave_date ON leave_requests(leave_date_from)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leave_status ON leave_requests(status)")
    
    conn.commit()
    conn.close()
    print("✅ 休暇願テーブル初期化完了")

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
        conn = get_database_connection()
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
        conn.commit()
        conn.close()
        
        print(f"[休暇願] ID:{leave_id} | {employee_name} | {leave_type} | {leave_date_from}～{leave_date_to}")
        return leave_id
        
    except Exception as e:
        print(f"[エラー] 休暇願登録エラー: {e}")
        if conn:
            conn.close()
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
        conn = get_database_connection()
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
        
        conn.close()
        return results
        
    except Exception as e:
        print(f"[エラー] 休暇願取得エラー: {e}")
        if conn:
            conn.close()
        return []

def approve_leave_request(leave_id, approved_by):
    """休暇願を承認"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE leave_requests
            SET status = 'approved',
                approved_by = ?,
                approved_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (approved_by, datetime.now().isoformat(), datetime.now().isoformat(), leave_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[エラー] 休暇願承認エラー: {e}")
        if conn:
            conn.close()
        return False

def reject_leave_request(leave_id, rejected_by):
    """休暇願を却下"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE leave_requests
            SET status = 'rejected',
                approved_by = ?,
                approved_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (rejected_by, datetime.now().isoformat(), datetime.now().isoformat(), leave_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[エラー] 休暇願却下エラー: {e}")
        if conn:
            conn.close()
        return False

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
        print(f"[エラー] 休暇願取得エラー: {e}")
        if conn:
            conn.close()
        return []

