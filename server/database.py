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
from utils import calculate_time_diff_minutes, get_database_connection

# データベースファイルのパス（config.pyから取得）
DB_FILE = Config.DATABASE_PATH

# デバッグ情報（開発時のみ）
if os.environ.get('DEBUG', '').lower() in ('true', '1', 'yes'):
    print(f"🗄️ Database path: {DB_FILE}")
    print(f"🗄️ File exists: {os.path.exists(DB_FILE)}")

def init_database():
    """
    データベースを初期化
    テーブルが存在しない場合は作成
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
    
    conn.commit()
    conn.close()
    print("✅ データベース初期化完了")

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
                print(f"✅ employee_masterテーブルにsectionカラムを追加しました（既存{updated_count}件のデータを「設備」に設定）")
            else:
                # カラムが既に存在する場合も、NULLや空の値があれば「設備」に設定
                cursor.execute("""
                    UPDATE employee_master 
                    SET section = '設備' 
                    WHERE section IS NULL OR section = ''
                """)
                updated_count = cursor.rowcount
                if updated_count > 0:
                    print(f"✅ employee_masterテーブルのsectionカラムを確認しました（{updated_count}件のデータを「設備」に更新）")
                else:
                    print("✅ employee_masterテーブルのsectionカラムを確認しました")
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
            print("✅ employee_masterテーブルを作成しました（sectionカラムを含む）")
            
    except sqlite3.Error as e:
        print(f"⚠️ employee_masterテーブルのマイグレーションエラー: {e}")

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
        
        print("✅ 遅刻早退申告テーブル初期化完了")
        
    except sqlite3.Error as e:
        print(f"⚠️ 遅刻早退申告テーブルの初期化エラー: {e}")

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

def search_schedule(employee_id, start_date, end_date, limit=None):
    """勤怠スケジュールを検索（打刻データ付き）"""
    if limit is None:
        limit = Config.DEFAULT_SEARCH_LIMIT
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
    """
    統計情報を取得
    AI_DEVELOPMENT_GUIDE.mdに従い、エラーハンドリングと
    環境適応性を強化した実装
    """
    conn = None
    try:
        # データベース接続状態の事前確認
        if not os.path.exists(DB_FILE):
            return {
                'status': 'error',
                'message': f'Database file not found: {DB_FILE}',
                'latest': []
            }
        
        conn = get_database_connection()
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
        
        # 最新の打刻履歴（パラメータバインディング使用）
        cursor.execute("""
            SELECT idm, timestamp, terminal_id, received_at 
            FROM attendance 
            ORDER BY received_at DESC 
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
        
        # 安全な最新打刻履歴整形（AIガイドの推奨パターン）
        latest_list = []
        if latest_records:
            for record in latest_records:
                try:
                    latest_list.append({
                        'idm': record[0] if record[0] is not None else '',
                        'timestamp': record[1] if record[1] is not None else '',
                        'terminal_id': record[2] if record[2] is not None else '',
                        'received_at': record[3] if record[3] is not None else ''
                    })
                except (IndexError, TypeError) as e:
                    print(f"Warning: Failed to process record: {record}, Error: {e}")
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
        print(f"Database error in get_stats(): {e}")
        return {
            'status': 'error',
            'message': f'Database error: {str(e)}',
            'latest': []
        }
    except Exception as e:
        print(f"Unexpected error in get_stats(): {e}")
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}',
            'latest': []
        }
    finally:
        if conn:
            conn.close()

def cleanup_duplicates(threshold_seconds=None):
    """重複データのクリーンアップ"""
    if threshold_seconds is None:
        threshold_seconds = Config.CHATTERING_THRESHOLD_SECONDS
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
        
        employees = []
        for row in rows:
            if has_section:
                employees.append({
                    'employee_num': row[0],
                    'name': row[1],
                    'idm': row[2],
                    'section': row[3] or '設備',  # NULLの場合はデフォルト値
                    'has_24hour_shifts': bool(row[4]),
                    'total_schedules': row[5]
                })
            else:
                employees.append({
                    'employee_num': row[0],
                    'name': row[1],
                    'idm': row[2],
                    'section': '設備',  # カラムが存在しない場合はデフォルト値
                    'has_24hour_shifts': bool(row[3]),
                    'total_schedules': row[4]
                })
        
        conn.close()
        return employees
        
    except sqlite3.Error as e:
        if conn:
            conn.close()
        raise e

def check_attendance_vs_schedule(employee_id, check_date):
    """
    勤怠スケジュールと打刻実績の差異をチェック
    
    Args:
        employee_id: 従業員ID
        check_date: チェック日付 (YYYY-MM-DD形式)
    
    Returns:
        チェック結果のリスト（日付ごとのスケジュールと打刻実績、アラート情報）
    """
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # 従業員情報を取得
        cursor.execute("""
            SELECT employee_num, name, idm FROM employee_master 
            WHERE employee_num = ?
        """, (employee_id,))
        
        emp_result = cursor.fetchone()
        if not emp_result:
            return {
                'status': 'error',
                'message': f'従業員ID {employee_id} が見つかりません'
            }
        
        employee_num, employee_name, idm = emp_result
        
        # チェック日付のスケジュールを取得
        cursor.execute("""
            SELECT id, work_date, work_type, start_time, end_time
            FROM attend_schedule
            WHERE employee_id = ? AND work_date = ?
        """, (employee_id, check_date))
        
        schedule_row = cursor.fetchone()
        
        # チェック日付の打刻データを取得
        cursor.execute("""
            SELECT id, timestamp, terminal_id
            FROM attendance
            WHERE idm = ? AND date(timestamp) = ?
            ORDER BY timestamp ASC
        """, (idm, check_date))
        
        attendance_rows = cursor.fetchall()
        
        # 翌日の「明」勤務のスケジュールを取得（24勤A/B、夜勤用）
        next_date = (datetime.strptime(check_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT work_date, work_type, end_time
            FROM attend_schedule
            WHERE employee_id = ? AND work_date = ? AND work_type = '明'
        """, (employee_id, next_date))
        
        next_day_off_schedule = cursor.fetchone()
        
        # 翌日の打刻データを取得（24勤A/B、夜勤の退勤時刻用）
        cursor.execute("""
            SELECT id, timestamp, terminal_id
            FROM attendance
            WHERE idm = ? AND date(timestamp) = ?
            ORDER BY timestamp ASC
        """, (idm, next_date))
        
        next_day_attendance_rows = cursor.fetchall()
        
        # 結果を構築
        result = {
            'employee_id': employee_num,
            'employee_name': employee_name,
            'check_date': check_date,
            'schedule': None,
            'attendance_records': [],
            'actual_clock_in': None,
            'actual_clock_out': None,
            'alerts': []
        }
        
        # スケジュール情報
        if schedule_row:
            result['schedule'] = {
                'id': schedule_row[0],
                'work_date': schedule_row[1],
                'work_type': schedule_row[2],
                'start_time': schedule_row[3],
                'end_time': schedule_row[4]
            }
        
        # 打刻データを整形
        for att_row in attendance_rows:
            timestamp_str = att_row[1]
            try:
                if 'T' in timestamp_str:
                    time_part = timestamp_str.split('T')[1].split('.')[0]
                else:
                    time_part = timestamp_str.split(' ')[1].split('.')[0] if ' ' in timestamp_str else timestamp_str
                time_only = ':'.join(time_part.split(':')[:2])
            except:
                time_only = timestamp_str
            
            result['attendance_records'].append({
                'id': att_row[0],
                'time': time_only,
                'timestamp': timestamp_str,
                'terminal_id': att_row[2]
            })
        
        # 打刻時間の判定
        work_type = result['schedule']['work_type'] if result['schedule'] else None
        
        if result['attendance_records']:
            if work_type and ('24勤' in work_type or '夜勤' in work_type):
                # 24勤A/B、夜勤: 一番早い時間が出勤、翌日の「明」の日の一番遅い時間が退勤
                result['actual_clock_in'] = result['attendance_records'][0]['time']
                
                if next_day_attendance_rows:
                    # 翌日の打刻データから時刻を抽出
                    next_day_times = []
                    for att_row in next_day_attendance_rows:
                        timestamp_str = att_row[1]
                        try:
                            if 'T' in timestamp_str:
                                time_part = timestamp_str.split('T')[1].split('.')[0]
                            else:
                                time_part = timestamp_str.split(' ')[1].split('.')[0] if ' ' in timestamp_str else timestamp_str
                            time_only = ':'.join(time_part.split(':')[:2])
                            next_day_times.append(time_only)
                        except:
                            pass
                    
                    if next_day_times:
                        result['actual_clock_out'] = next_day_times[-1]  # 一番遅い時間
            else:
                # 日勤: 一番早い時間が出勤、一番遅い時間が退勤
                if len(result['attendance_records']) > 0:
                    result['actual_clock_in'] = result['attendance_records'][0]['time']
                    result['actual_clock_out'] = result['attendance_records'][-1]['time']
        
        # アラートチェック
        alerts = []
        
        # 1. 休みの日に打刻があるかチェック
        if result['schedule']:
            work_type = result['schedule']['work_type']
            if work_type and ('有' in work_type or '所' in work_type or '法' in work_type):
                if result['attendance_records']:
                    alerts.append({
                        'type': 'error',
                        'message': '休日なのに打刻',
                        'details': f'勤務タイプ: {work_type}、打刻回数: {len(result["attendance_records"])}回'
                    })
        
        # 2. スケジュールがあるのに打刻がないかチェック
        if result['schedule']:
            work_type = result['schedule']['work_type']
            # 休み以外で、出退勤スケジュールがあるのに打刻がない
            if work_type and '有' not in work_type and '所' not in work_type and '法' not in work_type and '明' not in work_type:
                if result['schedule']['start_time'] or result['schedule']['end_time']:
                    if not result['attendance_records']:
                        alerts.append({
                            'type': 'error',
                            'message': '打刻なし',
                            'details': f'勤務タイプ: {work_type}、スケジュール: {result["schedule"]["start_time"]} - {result["schedule"]["end_time"]}'
                        })
        
        # 2-1. 休日出勤届が出ている日に打刻時間がない場合のアラート
        if result['schedule']:
            work_type = result['schedule']['work_type']
            if work_type and ('休出' in work_type or '休日出勤' in work_type):
                if not result['attendance_records']:
                    alerts.append({
                        'type': 'error',
                        'message': '休日出勤届があるのに打刻なし',
                        'details': f'勤務タイプ: {work_type}、スケジュール: {result["schedule"]["start_time"]} - {result["schedule"]["end_time"]}'
                    })
        
        # 2-2. 休暇届が出ているのに打刻がある場合のアラート
        try:
            # 承認済みの休暇願を取得（循環インポート回避のため関数内でインポート）
            from leave_request import get_leave_requests
            approved_leaves = get_leave_requests(
                employee_num=str(employee_num),
                leave_date=check_date,
                status='approved',
                limit=100
            )
            
            # チェック日付が休暇期間内かどうかを確認
            for leave in approved_leaves:
                leave_date_from = leave.get('leave_date_from')
                leave_date_to = leave.get('leave_date_to')
                
                if leave_date_from and leave_date_to:
                    # チェック日付が休暇期間内かどうか
                    if leave_date_from <= check_date <= leave_date_to:
                        if result['attendance_records']:
                            leave_type = leave.get('leave_type', '')
                            leave_subtype = leave.get('leave_subtype', '')
                            leave_detail = leave_type
                            if leave_subtype:
                                leave_detail += f' ({leave_subtype})'
                            
                            alerts.append({
                                'type': 'error',
                                'message': '休暇願があるのに打刻あり',
                                'details': f'休暇種類: {leave_detail}、打刻回数: {len(result["attendance_records"])}回'
                            })
                            break  # 1件見つかれば十分
        except Exception as e:
            # 休暇願の取得エラーは無視（ログに出力）
            print(f"[警告] 休暇願チェックエラー: {e}")
        
        # 3. 遅刻早退申告を取得
        late_requests = get_late_arrival_requests(employee_num=employee_num, work_date=check_date, status='pending')
        early_requests = get_early_leave_requests(employee_num=employee_num, work_date=check_date, status='pending')
        
        # 24勤や夜勤の場合、翌日の「明」の日に遅刻申告があるかチェック
        late_minutes_adjustment = 0
        early_minutes_adjustment = 0
        
        if late_requests:
            # 承認済みの遅刻申告の合計分数を取得
            approved_late = get_late_arrival_requests(employee_num=employee_num, work_date=check_date, status='approved')
            late_minutes_adjustment = sum(req['late_minutes'] for req in approved_late)
        
        if early_requests:
            # 承認済みの早退申告の合計分数を取得
            approved_early = get_early_leave_requests(employee_num=employee_num, work_date=check_date, status='approved')
            early_minutes_adjustment = sum(req['early_minutes'] for req in approved_early)
        
        # 24勤や夜勤の場合、翌日の「明」の日に遅刻申告があるかチェック
        if work_type and ('24勤' in work_type or '夜勤' in work_type):
            next_date = (datetime.strptime(check_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            next_day_late_requests = get_late_arrival_requests(employee_num=employee_num, work_date=next_date, status='approved')
            if next_day_late_requests:
                # 翌日の「明」の日に遅刻申告があれば、出勤と退勤を行ったように処理
                late_minutes_adjustment += sum(req['late_minutes'] for req in next_day_late_requests)
        
        # 3. 出退勤時刻の差異チェック（30分以上、遅刻早退申告を考慮）
        if result['schedule'] and result['attendance_records']:
            schedule_start = result['schedule']['start_time']
            schedule_end = result['schedule']['end_time']
            actual_start = result['actual_clock_in']
            actual_end = result['actual_clock_out']
            
            if schedule_start and actual_start:
                diff_start = calculate_time_diff_minutes(schedule_start, actual_start)
                # 遅刻申告がある場合は、その分数を引いて判定
                if diff_start is not None:
                    adjusted_diff_start = diff_start - late_minutes_adjustment
                    if abs(adjusted_diff_start) >= 30:
                        alerts.append({
                            'type': 'warning',
                            'message': '出退勤時刻に差異あり',
                            'details': f'出勤時刻: スケジュール {schedule_start} / 実際 {actual_start} (差異: {diff_start:+d}分, 遅刻申告調整後: {adjusted_diff_start:+d}分)'
                        })
            
            if schedule_end and actual_end:
                diff_end = calculate_time_diff_minutes(schedule_end, actual_end)
                # 早退申告がある場合は、その分数を引いて判定
                if diff_end is not None:
                    adjusted_diff_end = diff_end + early_minutes_adjustment  # 早退は負の値なので加算
                    if abs(adjusted_diff_end) >= 30:
                        alerts.append({
                            'type': 'warning',
                            'message': '出退勤時刻に差異あり',
                            'details': f'退勤時刻: スケジュール {schedule_end} / 実際 {actual_end} (差異: {diff_end:+d}分, 早退申告調整後: {adjusted_diff_end:+d}分)'
                        })
            elif schedule_end and not actual_end:
                # 退勤スケジュールがあるのに退勤打刻がない
                if work_type and ('24勤' not in work_type and '夜勤' not in work_type):
                    alerts.append({
                        'type': 'warning',
                        'message': '出退勤時刻に差異あり',
                        'details': f'退勤時刻: スケジュール {schedule_end} / 実際 打刻なし'
                    })
        
        result['alerts'] = alerts
        
        conn.close()
        return {
            'status': 'success',
            'data': result
        }
        
    except Exception as e:
        if conn:
            conn.close()
        return {
            'status': 'error',
            'message': f'チェックエラー: {str(e)}'
        }

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
        conn = get_database_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO late_arrival_requests (
                employee_num, employee_name, request_date, work_date,
                late_minutes, reason, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (employee_num, employee_name, request_date, work_date, late_minutes, reason, now, now))
        
        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[遅刻申告] ID:{request_id} | {employee_name} | {work_date} | {late_minutes}分")
        return request_id
        
    except Exception as e:
        print(f"[エラー] 遅刻申告登録エラー: {e}")
        if conn:
            conn.close()
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
        conn = get_database_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO early_leave_requests (
                employee_num, employee_name, request_date, work_date,
                early_minutes, reason, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (employee_num, employee_name, request_date, work_date, early_minutes, reason, now, now))
        
        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[早退申告] ID:{request_id} | {employee_name} | {work_date} | {early_minutes}分")
        return request_id
        
    except Exception as e:
        print(f"[エラー] 早退申告登録エラー: {e}")
        if conn:
            conn.close()
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
        conn = get_database_connection()
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
        
        conn.close()
        return results
        
    except Exception as e:
        print(f"[エラー] 遅刻申告取得エラー: {e}")
        if conn:
            conn.close()
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
        conn = get_database_connection()
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
        
        conn.close()
        return results
        
    except Exception as e:
        print(f"[エラー] 早退申告取得エラー: {e}")
        if conn:
            conn.close()
        return []
