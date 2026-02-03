#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベーススキーマ管理モジュール
テーブル作成とマイグレーションを担当
"""

import sqlite3
import threading
from database_utils import get_db_connection
from constants import AttendanceConstants
from logger_config import setup_logger

logger = setup_logger(__name__)

# スレッドセーフなデータベース初期化管理クラス
class DatabaseInitializer:
    """
    データベース初期化をスレッドセーフに管理するクラス
    Double-Checked Lockingパターンを使用してパフォーマンスを最適化
    """
    _lock = threading.Lock()
    _initialized = False
    
    @classmethod
    def is_initialized(cls):
        """初期化済みかどうかを確認（ロック不要の読み取り）"""
        return cls._initialized
    
    @classmethod
    def initialize(cls):
        """
        データベースを初期化（スレッドセーフ）
        
        このメソッドは複数のスレッドから同時に呼び出されても安全です。
        Double-Checked Lockingパターンにより、パフォーマンスを最適化しています。
        """
        # 高速パス: 既に初期化済みの場合は即座にリターン（ロック不要）
        if cls._initialized:
            logger.debug("データベースは既に初期化済みです")
            return
        
        # ロックを取得して初期化処理を実行
        with cls._lock:
            # Double-Checked Locking: ロック取得後に再度チェック
            # （ロック待ちの間に他のスレッドが初期化を完了した可能性があるため）
            if cls._initialized:
                logger.debug("データベースは既に初期化済みです（ロック取得後）")
                return
            
            try:
                # 実際の初期化処理を実行
                cls._do_initialize()
                cls._initialized = True
                logger.info("データベース初期化完了（全テーブル統合管理、スレッドセーフ）")
            except Exception as e:
                logger.error(f"データベース初期化エラー: {e}", exc_info=True)
                # エラーが発生してもフラグを設定して、無限ループを防ぐ
                cls._initialized = True
                raise
    
    @classmethod
    def _do_initialize(cls):
        """
        実際のデータベース初期化処理
        すべてのテーブルを一元管理して作成
        """
        with get_db_connection() as conn:
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
            
            # 時間外申告テーブルのマイグレーション（actual_work_minutesカラム追加）
            migrate_overtime_table(cursor)
            
            # 打刻チェック状況テーブルの作成
            init_attendance_check_status_table(cursor)
            
            # 通知除外リストテーブルの作成
            init_notification_exclusions_table(cursor)
            
            # コンテキストマネージャーが自動的にコミット・クローズする

# 後方互換性のためのラッパー関数
def init_database():
    """
    データベースを初期化
    すべてのテーブルを一元管理して作成
    
    この関数はスレッドセーフです。
    複数のスレッドから同時に呼び出されても安全に動作します。
    
    後方互換性のため、既存のコードから呼び出し可能です。
    """
    DatabaseInitializer.initialize()

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
                actual_work_minutes INTEGER DEFAULT 0,
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

def migrate_overtime_table(cursor):
    """
    overtime_applicationsテーブルにactual_work_minutesカラムを追加するマイグレーション
    既存データに対して0を設定
    """
    try:
        # テーブルが存在するか確認
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='overtime_applications'
        """)
        table_exists = cursor.fetchone()
        
        if table_exists:
            # カラムが存在するか確認
            cursor.execute("PRAGMA table_info(overtime_applications)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # actual_work_minutesカラムが存在しない場合は追加
            if 'actual_work_minutes' not in columns:
                cursor.execute("""
                    ALTER TABLE overtime_applications 
                    ADD COLUMN actual_work_minutes INTEGER DEFAULT 0
                """)
                
                # 既存データに対して0を設定
                cursor.execute("""
                    UPDATE overtime_applications 
                    SET actual_work_minutes = 0
                    WHERE actual_work_minutes IS NULL
                """)
                
                updated_count = cursor.rowcount
                logger.info(f"overtime_applicationsテーブルにactual_work_minutesカラムを追加しました（既存{updated_count}件のデータを0に設定）")
            else:
                logger.debug("overtime_applicationsテーブルのactual_work_minutesカラムを確認しました")
        else:
            logger.debug("overtime_applicationsテーブルが存在しないため、マイグレーションをスキップします")
            
    except sqlite3.Error as e:
        logger.error(f"overtime_applicationsテーブルのマイグレーションエラー: {e}")

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

def init_notification_exclusions_table(cursor):
    """
    通知除外リストテーブルの初期化
    従業員IDの除外リストをデータベースに保存
    """
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_exclusions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exclusions_employee ON notification_exclusions(employee_id)")
        
        logger.info("通知除外リストテーブル初期化完了")
        
    except sqlite3.Error as e:
        logger.error(f"通知除外リストテーブルの初期化エラー: {e}")
