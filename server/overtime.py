#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
時間外申告管理モジュール
時間外作業の申告、承認、集計機能を提供
"""

import sqlite3
from datetime import datetime, time, timedelta
from config import Config
from utils import get_database_connection, get_db_connection, time_to_minutes, calculate_duration_minutes
from logger_config import setup_logger

logger = setup_logger(__name__)

def init_overtime_table():
    """
    時間外申告テーブルの初期化（後方互換性のため残存）
    
    Note: この関数は非推奨です。database.init_database()を使用してください。
    この関数は既存コードとの互換性のために残されています。
    """
    from database import init_overtime_table_internal
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # database.pyの内部関数を呼び出し
        init_overtime_table_internal(cursor)

def calculate_overtime_categories(employee_num, work_date, start_time, end_time):
    """
    時間外の分類を計算
    
    Args:
        employee_num: 従業員番号（整数）
        work_date: 作業日
        start_time: 開始時刻 (HH:MM)
        end_time: 終了時刻 (HH:MM)
    
    Returns:
        dict: {
            'overtime_type': '内残業' or '外残業',
            'inner_overtime_minutes': 内残業時間（分）,
            'outer_overtime_minutes': 外残業時間（分）,
            'night_overtime_minutes': 深夜時間（分）
        }
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # スケジュールから予定勤務時間を取得（employee_numを文字列に変換）
        cursor.execute("""
            SELECT start_time, end_time FROM attend_schedule
            WHERE employee_id = ? AND work_date = ?
        """, (str(employee_num), work_date))
        
        schedule = cursor.fetchone()
    
    if not schedule or not schedule[0] or not schedule[1]:
        # スケジュールがない場合は全て外残業
        total_minutes = calculate_duration_minutes(start_time, end_time)
        night_minutes = calculate_night_overtime(start_time, end_time)
        return {
            'overtime_type': '外残業',
            'inner_overtime_minutes': 0,
            'outer_overtime_minutes': total_minutes,
            'night_overtime_minutes': night_minutes
        }
    
    scheduled_start = schedule[0]  # HH:MM
    scheduled_end = schedule[1]    # HH:MM
    
    # 時刻を分に変換
    overtime_start_min = time_to_minutes(start_time)
    overtime_end_min = time_to_minutes(end_time)
    scheduled_start_min = time_to_minutes(scheduled_start)
    scheduled_end_min = time_to_minutes(scheduled_end)
    
    # 日をまたぐ場合の処理
    if overtime_end_min < overtime_start_min:
        overtime_end_min += 1440  # 24時間を加算
    if scheduled_end_min < scheduled_start_min:
        scheduled_end_min += 1440
    
    inner_minutes = 0
    outer_minutes = 0
    
    # 勤務時間内の時間外（内残業）
    if overtime_start_min >= scheduled_start_min and overtime_end_min <= scheduled_end_min:
        inner_minutes = overtime_end_min - overtime_start_min
    # 勤務時間外の時間外（外残業）
    else:
        # 開始が予定より前
        if overtime_start_min < scheduled_start_min:
            outer_minutes += min(scheduled_start_min, overtime_end_min) - overtime_start_min
        # 終了が予定より後
        if overtime_end_min > scheduled_end_min:
            outer_minutes += overtime_end_min - max(scheduled_end_min, overtime_start_min)
    
    # 深夜時間の計算（20:00-05:00）
    night_minutes = calculate_night_overtime(start_time, end_time)
    
    overtime_type = '内残業' if inner_minutes > 0 else '外残業'
    
    return {
        'overtime_type': overtime_type,
        'inner_overtime_minutes': inner_minutes,
        'outer_overtime_minutes': outer_minutes,
        'night_overtime_minutes': night_minutes
    }

def calculate_night_overtime(start_time, end_time):
    """
    深夜時間帯（20:00-05:00）の時間を計算
    
    Args:
        start_time: 開始時刻 (HH:MM)
        end_time: 終了時刻 (HH:MM)
    
    Returns:
        int: 深夜時間（分）
    """
    start_min = time_to_minutes(start_time)
    end_min = time_to_minutes(end_time)
    
    # 日をまたぐ場合
    if end_min < start_min:
        end_min += 1440
    
    night_start = 20 * 60  # 20:00
    night_end = 29 * 60    # 翌05:00 = 29:00
    
    # 深夜時間帯との重複を計算
    overlap_start = max(start_min, night_start)
    overlap_end = min(end_min, night_end)
    
    if overlap_end > overlap_start:
        return overlap_end - overlap_start
    
    # 深夜時間帯が2日にまたがる場合
    if end_min >= 1440:  # 翌日まで
        night_minutes = 0
        # 1日目の深夜（20:00-24:00）
        if start_min < 1440:
            overlap_end_day1 = min(end_min, 1440)
            if overlap_end_day1 > night_start:
                night_minutes += overlap_end_day1 - max(start_min, night_start)
        # 2日目の深夜（00:00-05:00）
        if end_min > 1440:
            overlap_start_day2 = max(start_min - 1440, 0) if start_min > 1440 else 0
            overlap_end_day2 = min(end_min - 1440, 5 * 60)
            if overlap_end_day2 > overlap_start_day2:
                night_minutes += overlap_end_day2 - overlap_start_day2
        return night_minutes
    
    return 0

# time_to_minutesとcalculate_duration_minutesはutils.pyからインポート（重複を避けるため）

def insert_overtime_application(employee_num, employee_name, application_date, work_date, 
                                 start_time, end_time, description=''):
    """
    時間外申告を登録
    
    Args:
        employee_num: 従業員番号（整数）
        employee_name: 従業員名
        application_date: 申告日
        work_date: 作業日
        start_time: 開始時刻
        end_time: 終了時刻
        description: 作業内容
    
    Returns:
        int: 登録されたIDまたはNone
    """
    try:
        # employee_numを整数として扱う
        employee_num = int(employee_num) if employee_num else None
        if not employee_num:
            return None
        
        # 時間外の分類を計算
        categories = calculate_overtime_categories(employee_num, work_date, start_time, end_time)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO overtime_applications (
                    employee_num, employee_name, application_date, work_date,
                    start_time, end_time, description, status,
                    overtime_type, inner_overtime_minutes, outer_overtime_minutes, night_overtime_minutes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)
            """, (
                str(employee_num), employee_name, application_date, work_date,
                start_time, end_time, description,
                categories['overtime_type'],
                categories['inner_overtime_minutes'],
                categories['outer_overtime_minutes'],
                categories['night_overtime_minutes'],
                now, now
            ))
            
            overtime_id = cursor.lastrowid
            logger.info(f"時間外申告登録: ID={overtime_id}, 従業員={employee_name}, 作業日={work_date}, 時間={start_time}-{end_time}")
            return overtime_id
        
    except Exception as e:
        logger.error(f"時間外申告登録エラー: {e}", exc_info=True)
        return None

def get_overtime_applications(employee_num=None, work_date=None, status=None, limit=100):
    """
    時間外申告を取得
    
    Args:
        employee_num: 従業員番号（フィルタ用）
        work_date: 作業日（フィルタ用）
        status: ステータス（フィルタ用）
        limit: 取得件数
    
    Returns:
        list: 時間外申告のリスト
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM overtime_applications WHERE 1=1"
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
        logger.error(f"時間外申告取得エラー: {e}", exc_info=True)
        return []

def approve_overtime(overtime_id, approved_by):
    """時間外申告を承認（共通関数を使用）"""
    from utils import update_request_status
    
    result = update_request_status(
        table_name='overtime_applications',
        request_id=overtime_id,
        status='approved',
        updated_by=approved_by
    )
    
    if result['success']:
        logger.info(f"時間外申告承認: ID={overtime_id}")
    
    return result['success']

def reject_overtime(overtime_id, rejected_by):
    """時間外申告を却下（共通関数を使用）"""
    from utils import update_request_status
    
    result = update_request_status(
        table_name='overtime_applications',
        request_id=overtime_id,
        status='rejected',
        updated_by=rejected_by
    )
    
    if result['success']:
        logger.info(f"時間外申告却下: ID={overtime_id}")
    
    return result['success']

def withdraw_overtime(overtime_id):
    """
    時間外申告を取り下げ（承認前のみ可能）
    データは削除せず、ステータスを'withdrawn'に変更（共通関数を使用）
    
    Args:
        overtime_id: 時間外申告ID
    
    Returns:
        bool: 成功した場合True、失敗した場合False
    """
    from utils import update_request_status
    
    result = update_request_status(
        table_name='overtime_applications',
        request_id=overtime_id,
        status='withdrawn'
    )
    
    if result['success']:
        logger.info(f"時間外申告取り下げ: ID={overtime_id}")
    else:
        logger.error(f"時間外申告取り下げ失敗: {result['message']}")
    
    return result['success']

def get_monthly_overtime_summary(employee_num, year, month):
    """
    月度の時間外集計（前月16日〜当月15日）
    
    Args:
        employee_num: 従業員番号
        year: 年
        month: 月
    
    Returns:
        dict: 集計結果
    """
    try:
        from datetime import date
        
        # 月度期間の計算
        if month == 1:
            start_date = date(year - 1, 12, Config.PAYROLL_START_DAY)
        else:
            start_date = date(year, month - 1, Config.PAYROLL_START_DAY)
        
        end_date = date(year, month, Config.PAYROLL_END_DAY)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_count,
                    SUM(inner_overtime_minutes) as total_inner,
                    SUM(outer_overtime_minutes) as total_outer,
                    SUM(night_overtime_minutes) as total_night,
                    SUM(inner_overtime_minutes + outer_overtime_minutes) as total_all
                FROM overtime_applications
                WHERE employee_num = ?
                  AND work_date >= ?
                  AND work_date <= ?
                  AND status = 'approved'
            """, (employee_num, start_date.isoformat(), end_date.isoformat()))
            
            row = cursor.fetchone()
            
            if row:
                return {
                    'period_start': start_date.isoformat(),
                    'period_end': end_date.isoformat(),
                    'total_count': row[0] or 0,
                    'inner_overtime_hours': round((row[1] or 0) / 60, 2),
                    'outer_overtime_hours': round((row[2] or 0) / 60, 2),
                    'night_overtime_hours': round((row[3] or 0) / 60, 2),
                    'total_overtime_hours': round((row[4] or 0) / 60, 2)
                }
            
            return None
        
    except Exception as e:
        logger.error(f"月次集計エラー: {e}", exc_info=True)
        return None

