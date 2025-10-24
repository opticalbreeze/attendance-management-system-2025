#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベース管理モジュール
打刻システムのデータベース操作を担当
"""

import sqlite3
import os
from datetime import datetime

# データベースファイルのパス（環境自動判定）
def get_database_path():
    """環境に応じたデータベースパスを取得"""
    # 環境変数での指定を最優先
    if 'DATABASE_PATH' in os.environ:
        return os.environ['DATABASE_PATH']
    
    # Docker環境（volume mount: ./data:/data）
    if os.path.exists('/data'):
        return '/data/attendance.db'
    
    # ローカル開発環境
    elif os.path.exists('./data'):
        return './data/attendance.db'
    
    # フォールバック（カレントディレクトリ）
    else:
        return 'attendance.db'

DB_FILE = get_database_path()

# デバッグ情報（開発時のみ）
if os.environ.get('DEBUG', '').lower() in ('true', '1', 'yes'):
    print(f"🗄️ Database path: {DB_FILE}")
    print(f"🗄️ File exists: {os.path.exists(DB_FILE)}")

def init_database():
    """
    データベースを初期化
    テーブルが存在しない場合は作成
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 打刻テーブルの作成
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idm TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            terminal_id TEXT NOT NULL,
            received_at TEXT NOT NULL
        )
    """)
    
    # インデックスの作成（パフォーマンス向上）
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_idm ON attendance(idm)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON attendance(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_terminal_id ON attendance(terminal_id)")
    
    conn.commit()
    conn.close()
    print("✅ データベース初期化完了")

def get_database_connection():
    """データベース接続を取得"""
    return sqlite3.connect(DB_FILE)

def insert_attendance(idm, timestamp, terminal_id):
    """打刻データを挿入"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        received_at = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO attendance (idm, timestamp, terminal_id, received_at)
            VALUES (?, ?, ?, ?)
        """, (idm, timestamp, terminal_id, received_at))
        
        attendance_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return attendance_id
    except sqlite3.Error as e:
        if conn:
            conn.close()
        raise e

def search_schedule(employee_id, start_date, end_date, limit=100):
    """勤怠スケジュールを検索（打刻データ付き）"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, sheet_number, employee_id, employee_name, work_date, 
                   work_type, start_time, end_time, created_at, updated_at
            FROM attend_schedule 
            WHERE employee_id = ? 
            AND work_date >= ? 
            AND work_date <= ?
            ORDER BY work_date ASC 
            LIMIT ?
        """
        
        cursor.execute(query, [employee_id, start_date, end_date, int(limit)])
        rows = cursor.fetchall()
        
        # 結果を辞書形式に整形し、打刻データを追加
        results = []
        for row in rows:
            schedule_item = {
                'id': row[0],
                'sheet_number': row[1],
                'employee_id': row[2],
                'employee_name': row[3],
                'work_date': row[4],
                'work_type': row[5],
                'start_time': row[6],
                'end_time': row[7],
                'created_at': row[8],
                'updated_at': row[9]
            }
            
            # 打刻データを追加取得
            schedule_item['attendance_records'] = get_attendance_for_schedule(cursor, row[2], row[4])
            results.append(schedule_item)
        
        conn.close()
        return results
        
    except sqlite3.Error as e:
        if conn:
            conn.close()
        raise e

def get_stats():
    """統計情報を取得"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # 基本統計
        cursor.execute("SELECT COUNT(*) FROM attendance")
        total_records = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT idm) FROM attendance")
        unique_cards = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT terminal_id) FROM attendance")
        unique_terminals = cursor.fetchone()[0]
        
        # スケジュール統計
        cursor.execute("SELECT COUNT(*) FROM attend_schedule")
        schedule_records = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT employee_id) FROM attend_schedule")
        unique_employees = cursor.fetchone()[0]
        
        # 従業員マスタ統計
        cursor.execute("SELECT COUNT(*) FROM employee_master")
        employee_master_records = cursor.fetchone()[0]
        
        # 最新の打刻
        cursor.execute("""
            SELECT idm, timestamp, terminal_id, received_at 
            FROM attendance 
            ORDER BY received_at DESC 
            LIMIT 1
        """)
        latest_record = cursor.fetchone()
        
        # 今日の打刻件数
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) FROM attendance 
            WHERE received_at LIKE ?
        """, (f"{today}%",))
        today_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_records': total_records,
            'unique_cards': unique_cards, 
            'unique_terminals': unique_terminals,
            'schedule_records': schedule_records,
            'unique_employees': unique_employees,
            'employee_master_records': employee_master_records,
            'today_count': today_count,
            'latest_record': {
                'idm': latest_record[0] if latest_record else None,
                'timestamp': latest_record[1] if latest_record else None,
                'terminal_id': latest_record[2] if latest_record else None,
                'received_at': latest_record[3] if latest_record else None
            } if latest_record else None
        }
        
    except sqlite3.Error as e:
        if conn:
            conn.close()
        raise e

def cleanup_duplicates(threshold_seconds=10):
    """重複データのクリーンアップ"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # 重複レコードを特定
        cursor.execute("""
            SELECT a1.id, a1.idm, a1.timestamp, a1.terminal_id, a1.received_at
            FROM attendance a1
            INNER JOIN attendance a2 ON (
                a1.idm = a2.idm 
                AND a1.terminal_id = a2.terminal_id
                AND a1.id > a2.id
                AND abs(julianday(a1.timestamp) - julianday(a2.timestamp)) * 86400 <= ?
            )
            ORDER BY a1.received_at
        """, (threshold_seconds,))
        
        duplicates = cursor.fetchall()
        
        if duplicates:
            # 重複レコードを削除
            duplicate_ids = [str(dup[0]) for dup in duplicates]
            cursor.execute(f"DELETE FROM attendance WHERE id IN ({','.join(duplicate_ids)})")
            
        deleted_count = len(duplicates) if duplicates else 0
        conn.commit()
        conn.close()
        return deleted_count
        
    except sqlite3.Error as e:
        if conn:
            conn.close()
        raise e

def get_attendance_for_schedule(cursor, employee_id, work_date):
    """スケジュールに対応する打刻データを取得"""
    try:
        # employee_masterからIDmを取得
        cursor.execute("""
            SELECT idm FROM employee_master 
            WHERE employee_num = ?
        """, (employee_id,))
        
        idm_result = cursor.fetchone()
        if not idm_result:
            return []  # IDmが見つからない場合は空配列
        
        idm = idm_result[0]
        
        # 該当日の打刻データを取得（timestampの日付部分で一致）
        cursor.execute("""
            SELECT id, idm, timestamp, terminal_id, received_at
            FROM attendance 
            WHERE idm = ? 
            AND date(timestamp) = ?
            ORDER BY timestamp ASC
        """, (idm, work_date))
        
        attendance_rows = cursor.fetchall()
        
        # 打刻データを整形
        attendance_records = []
        for att_row in attendance_rows:
            # timestampから時刻のみを抽出
            timestamp_str = att_row[2]
            try:
                if 'T' in timestamp_str:
                    time_part = timestamp_str.split('T')[1].split('.')[0]  # HH:MM:SS
                else:
                    time_part = timestamp_str.split(' ')[1].split('.')[0] if ' ' in timestamp_str else timestamp_str
                
                # 秒を除去してHH:MM形式に
                time_only = ':'.join(time_part.split(':')[:2])
            except:
                time_only = timestamp_str  # パース失敗時はそのまま
            
            attendance_records.append({
                'attendance_id': att_row[0],
                'idm': att_row[1],
                'time_only': time_only,
                'terminal_id': att_row[3],
                'received_at': att_row[4]
            })
        
        return attendance_records
        
    except sqlite3.Error as e:
        return []  # エラー時は空配列を返す

def get_employees():
    """従業員マスタから全従業員情報を取得"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # 従業員マスタから基本情報を取得し、24勤シフトの有無を判定
        query = """
            SELECT 
                em.employee_num,
                em.name,
                em.idm,
                CASE 
                    WHEN COUNT(CASE WHEN as_.work_type LIKE '%24勤%' THEN 1 END) > 0 
                    THEN 1 
                    ELSE 0 
                END as has_24hour_shifts,
                COUNT(DISTINCT as_.work_date) as total_schedules
            FROM employee_master em
            LEFT JOIN attend_schedule as_ ON em.employee_num = as_.employee_id
            GROUP BY em.employee_num, em.name, em.idm
            ORDER BY em.employee_num
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        employees = []
        for row in rows:
            employees.append({
                'employee_num': row[0],
                'name': row[1],
                'idm': row[2],
                'has_24hour_shifts': bool(row[3]),
                'total_schedules': row[4]
            })
        
        conn.close()
        return employees
        
    except sqlite3.Error as e:
        if conn:
            conn.close()
        raise e