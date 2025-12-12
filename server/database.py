#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベース管理モジュール
打刻システムのデータベース操作を担当
"""

import sqlite3
import os
from datetime import datetime, timedelta

from config import Config
from utils import calculate_time_diff_minutes, get_database_connection, get_db_connection, extract_time_from_timestamp
from work_type_constants import (
    is_off_day_shift,
    is_24hour_or_night_shift,
    is_holiday_shift,
    WORK_TYPE_OFF_DAY
)
from logger_config import setup_logger

logger = setup_logger(__name__)

# データベースファイルのパス（config.pyから取得）
DB_FILE = Config.DATABASE_PATH

# デバッグ情報（開発時のみ）
if os.environ.get('DEBUG', '').lower() in ('true', '1', 'yes'):
    logger.debug(f"Database path: {DB_FILE}")
    logger.debug(f"File exists: {os.path.exists(DB_FILE)}")

def init_database():
    """
    データベースを初期化
    すべてのテーブルを一元管理して作成
    """
    conn = get_database_connection()
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
    
    # employee_masterテーブルのマイグレーション（sectionカラム追加）
    migrate_employee_master_table(cursor)
    
    # 遅刻早退申告テーブルの作成
    init_late_early_requests_tables(cursor)
    
    # 休暇願テーブルの作成
    init_leave_request_table_internal(cursor)
    
    # 時間外申告テーブルの作成
    init_overtime_table_internal(cursor)
    
    # 打刻チェック状況テーブルの作成
    init_attendance_check_status_table(cursor)
    
    conn.commit()
    conn.close()
    logger.info("データベース初期化完了（全テーブル統合管理）")

def migrate_employee_master_table(cursor):
    """
    employee_masterテーブルにsectionカラムを追加するマイグレーション
    既存データに対して「設備」を設定
    """
    try:
        # テーブルが存在するか確認
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='employee_master'
        """)
        table_exists = cursor.fetchone()
        
        if table_exists:
            # カラムが存在するか確認
            cursor.execute("PRAGMA table_info(employee_master)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # sectionカラムが存在しない場合は追加
            if 'section' not in columns:
                cursor.execute("""
                    ALTER TABLE employee_master 
                    ADD COLUMN section TEXT DEFAULT '設備'
                """)
                
                # 既存データに対して全員「設備」を設定
                cursor.execute("""
                    UPDATE employee_master 
                    SET section = '設備'
                """)
                
                updated_count = cursor.rowcount
                logger.info(f"employee_masterテーブルにsectionカラムを追加しました（既存{updated_count}件のデータを「設備」に設定）")
            else:
                # カラムが既に存在する場合も、NULLや空の値があれば「設備」に設定
                cursor.execute("""
                    UPDATE employee_master 
                    SET section = '設備' 
                    WHERE section IS NULL OR section = ''
                """)
                updated_count = cursor.rowcount
                if updated_count > 0:
                    logger.info(f"employee_masterテーブルのsectionカラムを確認しました（{updated_count}件のデータを「設備」に更新）")
                else:
                    logger.debug("employee_masterテーブルのsectionカラムを確認しました")
        else:
            # テーブルが存在しない場合は作成（sectionカラムを含む）
            # ユーザー指定のスキーマに合わせて作成
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS employee_master (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_num INTEGER NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    idm TEXT NOT NULL UNIQUE,
                    section TEXT DEFAULT '設備',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("employee_masterテーブルを作成しました（sectionカラムを含む）")
            
    except sqlite3.Error as e:
        logger.error(f"employee_masterテーブルのマイグレーションエラー: {e}")

def init_late_early_requests_tables(cursor):
    """
    遅刻早退申告テーブルの初期化
    """
    try:
        # 遅刻申告テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS late_arrival_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_num INTEGER NOT NULL,
                employee_name TEXT NOT NULL,
                request_date TEXT NOT NULL,
                work_date TEXT NOT NULL,
                late_minutes INTEGER NOT NULL,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # 早退申告テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS early_leave_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_num INTEGER NOT NULL,
                employee_name TEXT NOT NULL,
                request_date TEXT NOT NULL,
                work_date TEXT NOT NULL,
                early_minutes INTEGER NOT NULL,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_late_employee ON late_arrival_requests(employee_num)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_late_work_date ON late_arrival_requests(work_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_late_status ON late_arrival_requests(status)")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_early_employee ON early_leave_requests(employee_num)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_early_work_date ON early_leave_requests(work_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_early_status ON early_leave_requests(status)")
        
        logger.info("遅刻早退申告テーブル初期化完了")
        
    except sqlite3.Error as e:
        logger.error(f"遅刻早退申告テーブルの初期化エラー: {e}")

def init_leave_request_table_internal(cursor):
    """
    休暇願テーブルの初期化（内部関数）
    cursorを受け取ってテーブルを作成
    """
    try:
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
        
        logger.info("休暇願テーブル初期化完了")
        
    except sqlite3.Error as e:
        logger.error(f"休暇願テーブルの初期化エラー: {e}")

def init_overtime_table_internal(cursor):
    """
    時間外申告テーブルの初期化（内部関数）
    cursorを受け取ってテーブルを作成
    """
    try:
        # 時間外申告テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS overtime_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_num TEXT NOT NULL,
                employee_name TEXT NOT NULL,
                application_date TEXT NOT NULL,
                work_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                overtime_type TEXT,
                inner_overtime_minutes INTEGER DEFAULT 0,
                outer_overtime_minutes INTEGER DEFAULT 0,
                night_overtime_minutes INTEGER DEFAULT 0,
                approved_by TEXT,
                approved_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_overtime_employee ON overtime_applications(employee_num)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_overtime_work_date ON overtime_applications(work_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_overtime_status ON overtime_applications(status)")
        
        logger.info("時間外申告テーブル初期化完了")
        
    except sqlite3.Error as e:
        logger.error(f"時間外申告テーブルの初期化エラー: {e}")

def insert_attendance(idm, timestamp, terminal_id):
    """打刻データを挿入"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            received_at = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO attendance (idm, timestamp, terminal_id, received_at)
                VALUES (?, ?, ?, ?)
            """, (idm, timestamp, terminal_id, received_at))
            
            attendance_id = cursor.lastrowid
            return attendance_id
    except sqlite3.Error as e:
        logger.error(f"打刻データ挿入エラー: {e}", exc_info=True)
        raise e

def search_schedule(employee_id, start_date, end_date, limit=None):
    """勤怠スケジュールを検索（打刻データ付き）"""
    if limit is None:
        limit = Config.DEFAULT_SEARCH_LIMIT
    try:
        with get_db_connection() as conn:
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
            
            return results
        
    except sqlite3.Error as e:
        logger.error(f"スケジュール検索エラー: {e}", exc_info=True)
        raise e

def get_stats():
    """
    統計情報を取得
    AI_DEVELOPMENT_GUIDE.mdに従い、エラーハンドリングと
    環境適応性を強化した実装
    """
    try:
        # データベース接続状態の事前確認
        if not os.path.exists(DB_FILE):
            return {
                'status': 'error',
                'message': f'Database file not found: {DB_FILE}',
                'latest': []
            }
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # テーブル存在確認（AI_DEVELOPMENT_GUIDEの推奨事項）
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['attendance', 'attend_schedule', 'employee_master']
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            if missing_tables:
                return {
                    'status': 'error',
                    'message': f'Missing tables: {", ".join(missing_tables)}',
                    'latest': []
                }
            
            # 基本統計（安全なフィールドアクセス）
            stats = {}
            
            # 打刻データ統計
            cursor.execute("SELECT COUNT(*) FROM attendance")
            stats['total_records'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT idm) FROM attendance")
            stats['unique_cards'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT terminal_id) FROM attendance")
            stats['unique_terminals'] = cursor.fetchone()[0]
            
            # スケジュール統計
            cursor.execute("SELECT COUNT(*) FROM attend_schedule")
            stats['schedule_records'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT employee_id) FROM attend_schedule")
            stats['unique_employees'] = cursor.fetchone()[0]
            
            # 従業員マスタ統計
            cursor.execute("SELECT COUNT(*) FROM employee_master")
            stats['employee_master_records'] = cursor.fetchone()[0]
            
            # 最新の打刻履歴（従業員情報を含む）
            cursor.execute("""
                SELECT 
                    a.idm, 
                    a.timestamp, 
                    a.terminal_id, 
                    a.received_at,
                    em.employee_num,
                    em.name
                FROM attendance a
                LEFT JOIN employee_master em ON a.idm = em.idm
                ORDER BY a.received_at DESC 
                LIMIT ?
            """, (Config.STATS_LATEST_RECORDS,))
            latest_records = cursor.fetchall()
            
            # 今日の打刻件数（安全な日付処理）
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT COUNT(*) FROM attendance 
                WHERE DATE(received_at) = ?
            """, (today,))
            stats['today_count'] = cursor.fetchone()[0]
            
            # 安全な最新打刻履歴整形（従業員情報を含む）
            latest_list = []
            if latest_records:
                for record in latest_records:
                    try:
                        latest_list.append({
                            'idm': record[0] if record[0] is not None else '',
                            'timestamp': record[1] if record[1] is not None else '',
                            'terminal_id': record[2] if record[2] is not None else '',
                            'received_at': record[3] if record[3] is not None else '',
                            'employee_num': record[4] if record[4] is not None else '',
                            'employee_name': record[5] if record[5] is not None else ''
                        })
                    except (IndexError, TypeError) as e:
                        logger.warning(f"レコード処理失敗: {record}, エラー: {e}")
                        continue
            
            # 統一されたレスポンス形式
            result = {
                'status': 'success',
                'total_records': stats['total_records'],
                'unique_cards': stats['unique_cards'], 
                'unique_terminals': stats['unique_terminals'],
                'schedule_records': stats['schedule_records'],
                'unique_employees': stats['unique_employees'],
                'employee_master_records': stats['employee_master_records'],
                'today_count': stats['today_count'],
                'latest': latest_list
            }
            
            return result
        
    except sqlite3.Error as e:
        logger.error(f"get_stats()でデータベースエラー: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Database error: {str(e)}',
            'latest': []
        }
    except Exception as e:
        logger.error(f"get_stats()で予期しないエラー: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}',
            'latest': []
        }

def cleanup_duplicates(threshold_seconds=None):
    """重複データのクリーンアップ"""
    if threshold_seconds is None:
        threshold_seconds = Config.CHATTERING_THRESHOLD_SECONDS
    try:
        with get_db_connection() as conn:
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
                # 重複レコードを削除（SQLインジェクション対策：パラメータバインディングを使用）
                duplicate_ids = [dup[0] for dup in duplicates]
                placeholders = ','.join(['?'] * len(duplicate_ids))
                cursor.execute(f"DELETE FROM attendance WHERE id IN ({placeholders})", duplicate_ids)
                
            deleted_count = len(duplicates) if duplicates else 0
            return deleted_count
        
    except sqlite3.Error as e:
        logger.error(f"重複データクリーンアップエラー: {e}", exc_info=True)
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
            # timestampから時刻のみを抽出（統一関数を使用）
            timestamp_str = att_row[2]
            time_only = extract_time_from_timestamp(timestamp_str)
            
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

def check_off_day_shift_attendance(cursor, employee_id, employee_num, idm, check_date, work_type, prev_day_night_shift_schedule, actual_end, prev_date):
    """
    「明」勤務の退勤時刻チェック処理
    
    「明」勤務の日の打刻は前日の24勤・夜勤の退勤時刻として扱い、
    前日の24勤・夜勤のスケジュール退勤時刻と比較して差異をチェックする
    
    Args:
        cursor: データベースカーソル
        employee_id: 従業員ID
        employee_num: 従業員番号
        idm: IDm
        check_date: チェック日付（「明」勤務の日）
        work_type: 勤務タイプ
        prev_day_night_shift_schedule: 前日の24勤・夜勤スケジュール（タプル）
        actual_end: 「明」勤務の日の打刻時刻（前日の退勤時刻）
        prev_date: 前日の日付
        
    Returns:
        list: アラートのリスト
    """
    alerts = []
    
    if not prev_day_night_shift_schedule:
        # 前日の24勤・夜勤スケジュールが見つからない場合の処理
        # 「明」勤務なのに前日に24勤・夜勤がない場合は警告を出す
        # （打刻がある場合のみ警告）
        return alerts
    
    prev_schedule_start = prev_day_night_shift_schedule[2]  # start_time
    prev_schedule_end = prev_day_night_shift_schedule[3]  # end_time
    
    # 注意: 前日の24勤・夜勤の出勤時刻のチェックは、前日（24勤・夜勤）の画面で行うため、
    # 「明」勤務の画面では退勤時刻のみをチェックする
    
    # 前日の24勤・夜勤の退勤時刻をチェック（「明」勤務の打刻）
    # actual_endは「明」勤務の日の打刻時刻（前日の退勤時刻）
    # 「明」勤務の日の打刻は前日の24勤・夜勤の退勤時刻として扱う
    if prev_schedule_end:
        # 前日の24勤・夜勤のスケジュール退勤時刻と、「明」勤務の実際の退勤打刻を比較
        # actual_endがNoneの場合は、「明」勤務の日の打刻がないことを意味する
        if actual_end:
            diff_end = calculate_time_diff_minutes(prev_schedule_end, actual_end)
            if diff_end is not None:
                # 「明」勤務の日の早退申告を取得
                # get_early_leave_requestsはdatabase.py内で定義されているため、インポート不要
                prev_day_early = get_early_leave_requests(employee_num=employee_num, work_date=check_date, status='approved')
                prev_day_early_adjustment = sum(req['early_minutes'] for req in prev_day_early)
                adjusted_diff_end = diff_end + prev_day_early_adjustment
                if abs(adjusted_diff_end) >= 30:
                    alerts.append({
                        'type': 'warning',
                        'message': '出退勤時刻に差異あり',
                        'details': f'退勤時刻（{check_date}の打刻、前日{prev_date}の{prev_day_night_shift_schedule[1]}の退勤）: スケジュール {prev_schedule_end} / 実際 {actual_end} (差異: {diff_end:+d}分, 早退申告調整後: {adjusted_diff_end:+d}分)'
                    })
        else:
            # 「明」勤務の日の打刻がない場合（前日の24勤・夜勤の退勤打刻がない）
            alerts.append({
                'type': 'warning',
                'message': '退勤打刻なし',
                'details': f'前日{prev_date}の{prev_day_night_shift_schedule[1]}の退勤時刻（翌日「明」の打刻）が見つかりません'
            })
    
    return alerts

def get_night_shift_end_time_from_next_day(cursor, employee_id, work_date):
    """
    24勤・夜勤の終了時間を翌日の「明」勤務の打刻から取得する共通関数
    
    Args:
        cursor: データベースカーソル
        employee_id: 従業員番号
        work_date: 24勤・夜勤の日付（YYYY-MM-DD形式の文字列）
    
    Returns:
        str or None: 翌日の「明」勤務の最後の打刻時刻（HH:MM形式）、取得できない場合はNone
    """
    try:
        # employee_masterからIDmを取得
        cursor.execute("""
            SELECT idm FROM employee_master 
            WHERE employee_num = ?
        """, (employee_id,))
        
        idm_result = cursor.fetchone()
        if not idm_result:
            return None
        
        idm = idm_result[0]
        
        # 翌日の日付を計算
        work_date_obj = datetime.strptime(work_date, '%Y-%m-%d').date()
        next_date = (work_date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 翌日の「明」勤務のスケジュールが存在するか確認
        cursor.execute("""
            SELECT work_date, work_type
            FROM attend_schedule
            WHERE employee_id = ? AND work_date = ? AND work_type LIKE ?
        """, (employee_id, next_date, f'%{WORK_TYPE_OFF_DAY}%'))
        
        next_day_schedule = cursor.fetchone()
        if not next_day_schedule:
            return None
        
        # 翌日の打刻データを取得（「明」勤務の日の打刻）
        cursor.execute("""
            SELECT timestamp
            FROM attendance
            WHERE idm = ? AND date(timestamp) = ?
            ORDER BY timestamp ASC
        """, (idm, next_date))
        
        next_day_attendance_rows = cursor.fetchall()
        
        if not next_day_attendance_rows:
            return None
        
        # 最後の打刻時刻を取得（退勤時刻）
        last_timestamp = next_day_attendance_rows[-1][0]
        
        # 時刻のみを抽出（HH:MM形式、統一関数を使用）
        time_only = extract_time_from_timestamp(last_timestamp)
        return time_only if time_only else None
        
    except Exception as e:
        return None

def init_attendance_check_status_table(cursor):
    """
    打刻チェック状況テーブルの初期化
    管理者が打刻なし・時刻差異エラーを確認済みかどうかを記録
    """
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance_check_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_num TEXT NOT NULL,
                work_date TEXT NOT NULL,
                check_type TEXT NOT NULL,  -- 'missing_punch' or 'time_difference'
                is_checked BOOLEAN DEFAULT FALSE,
                checked_by TEXT,
                checked_at TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(employee_num, work_date, check_type)
            )
        """)
        
        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_check_status_employee ON attendance_check_status(employee_num)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_check_status_date ON attendance_check_status(work_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_check_status_type ON attendance_check_status(check_type)")
        
        logger.info("打刻チェック状況テーブル初期化完了")
        
    except sqlite3.Error as e:
        logger.error(f"打刻チェック状況テーブルの初期化エラー: {e}")

def get_attendance_check_status(employee_num, work_date, check_type):
    """
    打刻チェック状況を取得
    
    Args:
        employee_num: 従業員番号
        work_date: 勤務日
        check_type: チェックタイプ ('missing_punch', 'time_difference', or 'punch_leak')
    
    Returns:
        dict: チェックステータス情報またはNone
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, employee_num, work_date, check_type, is_checked, 
                       checked_by, checked_at, notes, created_at, updated_at
                FROM attendance_check_status
                WHERE employee_num = ? AND work_date = ? AND check_type = ?
            """, (employee_num, work_date, check_type))
            
            row = cursor.fetchone()
            if row:
                result = {
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
                }
                # チェック済みデータがある場合のみデバッグ出力
                if result['is_checked']:
                    logger.info(f"[DB] ✓ チェック済みデータ取得: employee_num={employee_num}, work_date={work_date}, check_type={check_type}, is_checked={result['is_checked']}, id={result['id']}")
                return result
            return None
            
    except Exception as e:
        logger.error(f"打刻チェックステータス取得エラー: {e}", exc_info=True)
        return None

def update_attendance_check_status(employee_num, work_date, check_type, is_checked, checked_by=None, notes=None):
    """
    打刻チェック状況を更新
    
    Args:
        employee_num: 従業員番号
        work_date: 勤務日
        check_type: チェックタイプ ('missing_punch', 'time_difference', or 'punch_leak')
        is_checked: チェック済みかどうか
        checked_by: チェックした人
        notes: 備考
    
    Returns:
        bool: 成功したかどうか
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            # UPSERT操作: 既存レコードの場合は更新、新規の場合は挿入
            # SQLiteのバージョン互換性のため、INSERT OR REPLACEとCOALESCEを使用
            # 
            # ロジック:
            # 1. 既存レコードがある場合: created_atを保持し、その他のフィールドを更新
            # 2. 新規レコードの場合: created_atとupdated_atの両方を現在時刻に設定
            # 
            # 注意: SQLite 3.24.0以降ではON CONFLICT構文が使えるが、
            #       互換性のためINSERT OR REPLACEを使用
            cursor.execute("""
                INSERT OR REPLACE INTO attendance_check_status 
                (employee_num, work_date, check_type, is_checked, checked_by, checked_at, notes, 
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 
                        COALESCE((SELECT created_at FROM attendance_check_status 
                                 WHERE employee_num = ? AND work_date = ? AND check_type = ?), ?), ?)
            """, (employee_num, work_date, check_type, is_checked, checked_by, now if is_checked else None, notes,
                  employee_num, work_date, check_type, now, now))
            
            logger.info(f"打刻チェックステータス更新: 従業員={employee_num}, 日付={work_date}, タイプ={check_type}, チェック済み={is_checked}")
            return True
            
    except Exception as e:
        logger.error(f"打刻チェックステータス更新エラー: {e}", exc_info=True)
        return False

def get_employees():
    """従業員マスタから全従業員情報を取得"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 従業員マスタから基本情報を取得し、24勤シフトの有無を判定
            # sectionカラムが存在するか確認
            cursor.execute("PRAGMA table_info(employee_master)")
            columns = [col[1] for col in cursor.fetchall()]
            has_section = 'section' in columns
            
            if has_section:
                query = """
                    SELECT 
                        em.employee_num,
                        em.name,
                        em.idm,
                        em.section,
                        CASE 
                            WHEN COUNT(CASE WHEN as_.work_type LIKE '%24勤%' THEN 1 END) > 0 
                            THEN 1 
                            ELSE 0 
                        END as has_24hour_shifts,
                        COUNT(DISTINCT as_.work_date) as total_schedules
                    FROM employee_master em
                    LEFT JOIN attend_schedule as_ ON em.employee_num = as_.employee_id
                    GROUP BY em.employee_num, em.name, em.idm, em.section
                    ORDER BY em.employee_num
                """
            else:
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
            
            logger.info(f"従業員情報取得: {len(rows)}件のレコードを取得")
            
            employees = []
            for row in rows:
                # nameがNULLまたは空文字列の場合の処理
                employee_name = row[1] if row[1] else None
                
                if has_section:
                    employee_data = {
                        'employee_num': row[0],
                        'name': employee_name,
                        'idm': row[2],
                        'section': row[3] or '設備',  # NULLの場合はデフォルト値
                        'has_24hour_shifts': bool(row[4]),
                        'total_schedules': row[5]
                    }
                else:
                    employee_data = {
                        'employee_num': row[0],
                        'name': employee_name,
                        'idm': row[2],
                        'section': '設備',  # カラムが存在しない場合はデフォルト値
                        'has_24hour_shifts': bool(row[3]),
                        'total_schedules': row[4]
                    }
                
                # デバッグログ（最初の3件のみ）
                if len(employees) < 3:
                    logger.info(f"従業員データ例: employee_num={employee_data['employee_num']}, name={employee_data['name']}, section={employee_data['section']}")
                
                employees.append(employee_data)
            
            logger.info(f"従業員情報取得完了: {len(employees)}件")
            return employees
        
    except sqlite3.Error as e:
        logger.error(f"従業員情報取得エラー: {e}", exc_info=True)
        raise e

def check_attendance_vs_schedule(employee_id, check_date):
    """
    勤怠スケジュールと打刻実績の差異をチェック
    
    注意: この関数は attendance_check_service.py に移行されました。
    後方互換性のためにラッパー関数として残しています。
    
    Args:
        employee_id: 従業員ID
        check_date: チェック日付 (YYYY-MM-DD形式)
    
    Returns:
        チェック結果のリスト（日付ごとのスケジュールと打刻実績、アラート情報）
    """
    # 新しいサービスを使用
    from attendance_check_service import check_attendance_vs_schedule as new_check
    return new_check(employee_id, check_date)

def insert_late_arrival_request(employee_num, employee_name, request_date, work_date, late_minutes, reason=''):
    """
    遅刻申告を登録
    
    Args:
        employee_num: 従業員番号
        employee_name: 従業員名
        request_date: 申告日
        work_date: 勤務日
        late_minutes: 遅刻分数
        reason: 理由
    
    Returns:
        int: 登録されたIDまたはNone
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO late_arrival_requests (
                    employee_num, employee_name, request_date, work_date,
                    late_minutes, reason, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """, (employee_num, employee_name, request_date, work_date, late_minutes, reason, now, now))
            
            request_id = cursor.lastrowid
            logger.info(f"遅刻申告登録: ID={request_id}, 従業員={employee_name}, 勤務日={work_date}, 遅刻={late_minutes}分")
            return request_id
        
    except Exception as e:
        logger.error(f"遅刻申告登録エラー: {e}", exc_info=True)
        return None

def insert_early_leave_request(employee_num, employee_name, request_date, work_date, early_minutes, reason=''):
    """
    早退申告を登録
    
    Args:
        employee_num: 従業員番号
        employee_name: 従業員名
        request_date: 申告日
        work_date: 勤務日
        early_minutes: 早退分数
        reason: 理由
    
    Returns:
        int: 登録されたIDまたはNone
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO early_leave_requests (
                    employee_num, employee_name, request_date, work_date,
                    early_minutes, reason, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """, (employee_num, employee_name, request_date, work_date, early_minutes, reason, now, now))
            
            request_id = cursor.lastrowid
            logger.info(f"早退申告登録: ID={request_id}, 従業員={employee_name}, 勤務日={work_date}, 早退={early_minutes}分")
            return request_id
        
    except Exception as e:
        logger.error(f"早退申告登録エラー: {e}", exc_info=True)
        return None

def get_late_arrival_requests(employee_num=None, work_date=None, status=None, limit=100):
    """
    遅刻申告を取得
    
    Args:
        employee_num: 従業員番号（オプション）
        work_date: 勤務日（オプション）
        status: ステータス（オプション）
        limit: 取得件数上限
    
    Returns:
        list: 遅刻申告のリスト
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM late_arrival_requests WHERE 1=1"
            params = []
            
            if employee_num:
                query += " AND employee_num = ?"
                params.append(employee_num)
            
            if work_date:
                query += " AND work_date = ?"
                params.append(work_date)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY work_date DESC, created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    'id': row[0],
                    'employee_num': row[1],
                    'employee_name': row[2],
                    'request_date': row[3],
                    'work_date': row[4],
                    'late_minutes': row[5],
                    'reason': row[6],
                    'status': row[7],
                    'created_at': row[8],
                    'updated_at': row[9]
                })
            
            return results
        
    except Exception as e:
        logger.error(f"遅刻申告取得エラー: {e}", exc_info=True)
        return []

def get_early_leave_requests(employee_num=None, work_date=None, status=None, limit=100):
    """
    早退申告を取得
    
    Args:
        employee_num: 従業員番号（オプション）
        work_date: 勤務日（オプション）
        status: ステータス（オプション）
        limit: 取得件数上限
    
    Returns:
        list: 早退申告のリスト
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM early_leave_requests WHERE 1=1"
            params = []
            
            if employee_num:
                query += " AND employee_num = ?"
                params.append(employee_num)
            
            if work_date:
                query += " AND work_date = ?"
                params.append(work_date)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY work_date DESC, created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    'id': row[0],
                    'employee_num': row[1],
                    'employee_name': row[2],
                    'request_date': row[3],
                    'work_date': row[4],
                    'early_minutes': row[5],
                    'reason': row[6],
                    'status': row[7],
                    'created_at': row[8],
                    'updated_at': row[9]
                })
            
            return results
        
    except Exception as e:
        logger.error(f"早退申告取得エラー: {e}", exc_info=True)
        return []