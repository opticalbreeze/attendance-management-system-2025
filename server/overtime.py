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
from constants import AttendanceConstants
from work_type_constants import is_off_day_shift, WORK_TYPE_OFF_DAY

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
        
        # スケジュールから予定勤務時間と勤務タイプを取得（employee_numを文字列に変換）
        cursor.execute("""
            SELECT start_time, end_time, work_type FROM attend_schedule
            WHERE employee_id = ? AND work_date = ?
        """, (str(employee_num), work_date))
        
        schedule = cursor.fetchone()
        
        work_type = schedule[2] if schedule and len(schedule) > 2 else None
        scheduled_start = schedule[0] if schedule else None  # HH:MM
        scheduled_end = schedule[1] if schedule else None   # HH:MM
        
        # 「明」勤務の場合は、前日の24勤スケジュールを取得して判定基準とする
        if work_type and is_off_day_shift(work_type):
            # 前日の日付を計算
            from datetime import datetime, timedelta
            current_date = datetime.strptime(work_date, '%Y-%m-%d').date()
            prev_date = (current_date - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # 前日の24勤・夜勤スケジュールを取得
            cursor.execute("""
                SELECT start_time, end_time, work_type FROM attend_schedule
                WHERE employee_id = ? AND work_date = ? AND (work_type LIKE '%24勤%' OR work_type LIKE '%夜勤%')
            """, (str(employee_num), prev_date))
            
            prev_schedule = cursor.fetchone()
            if prev_schedule and prev_schedule[0] and prev_schedule[1]:
                # 前日の24勤のスケジュールを使用（例：08:30-翌08:30）
                scheduled_start = prev_schedule[0]  # 前日の開始時刻（例：08:30）
                scheduled_end = prev_schedule[1]    # 前日の終了時刻（例：08:30 = 翌日の08:30）
                work_type = prev_schedule[2]        # 24勤の勤務タイプに更新
                logger.info(f"「明」勤務の時間外計算: 前日24勤スケジュール使用 {prev_date} {scheduled_start}-{scheduled_end} ({work_type})")
            else:
                # 前日のスケジュールが見つからない場合は、24勤のデフォルトスケジュール（8:30-翌8:30）を使用
                scheduled_start = '08:30'
                scheduled_end = '08:30'  # 翌日の8:30を意味する
                logger.info(f"「明」勤務の時間外計算: デフォルト24勤スケジュール使用 {scheduled_start}-{scheduled_end}")
        else:
            # 通常勤務の場合は、時間外作業日に該当する24勤スケジュールを確認
            # 時間外作業が深夜に行われた場合、その日の24勤スケジュールを参照
            cursor.execute("""
                SELECT start_time, end_time, work_type FROM attend_schedule
                WHERE employee_id = ? AND work_date = ? AND (work_type LIKE '%24勤%' OR work_type LIKE '%夜勤%')
            """, (str(employee_num), work_date))
            
            same_day_schedule = cursor.fetchone()
            if same_day_schedule and same_day_schedule[0] and same_day_schedule[1]:
                # 時間外作業日の24勤スケジュールを使用
                scheduled_start = same_day_schedule[0]
                scheduled_end = same_day_schedule[1]
                work_type = same_day_schedule[2]  # 正しい勤務タイプを設定
                logger.info(f"時間外作業日の24勤スケジュール使用: {work_date} {scheduled_start}-{scheduled_end}")
            else:
                # 時間外作業が早朝（深夜時間帯）に行われた場合、前日の24勤の可能性を確認
                overtime_start_hour = int(start_time.split(':')[0])
                if overtime_start_hour <= 8:  # 8時以前の場合は前日の24勤の可能性
                    from datetime import datetime, timedelta
                    current_date = datetime.strptime(work_date, '%Y-%m-%d').date()
                    prev_date = (current_date - timedelta(days=1)).strftime('%Y-%m-%d')
                    
                    # 前日の24勤・夜勤スケジュールを取得
                    cursor.execute("""
                        SELECT start_time, end_time, work_type FROM attend_schedule
                        WHERE employee_id = ? AND work_date = ? AND (work_type LIKE '%24勤%' OR work_type LIKE '%夜勤%')
                    """, (str(employee_num), prev_date))
                    
                    prev_schedule = cursor.fetchone()
                    if prev_schedule and prev_schedule[0] and prev_schedule[1]:
                        # 前日の24勤のスケジュールを使用
                        scheduled_start = prev_schedule[0]
                        scheduled_end = prev_schedule[1]
                        work_type = prev_schedule[2]
                        logger.info(f"早朝時間外作業: 前日24勤スケジュール使用 {prev_date} {scheduled_start}-{scheduled_end}")
                # else: 既に取得済みのスケジュール（日勤など）をそのまま使用
    
    # スケジュールがない場合は全て外残業
    if not scheduled_start or not scheduled_end:
        total_minutes = calculate_duration_minutes(start_time, end_time)
        night_minutes = calculate_night_overtime(start_time, end_time)
        return {
            'overtime_type': '外残業',
            'inner_overtime_minutes': 0,
            'outer_overtime_minutes': total_minutes,
            'night_overtime_minutes': night_minutes
        }
    
    # 時刻を分に変換
    overtime_start_min = time_to_minutes(start_time)
    overtime_end_min = time_to_minutes(end_time)
    scheduled_start_min = time_to_minutes(scheduled_start)
    scheduled_end_min = time_to_minutes(scheduled_end)
    
    logger.info(f"[時間外分類デバッグ] 開始: 従業員={employee_num}, 作業日={work_date}, 時間外作業={start_time}-{end_time}, 勤務タイプ={work_type}")
    logger.info(f"[時間外分類デバッグ] スケジュール取得: scheduled_start={scheduled_start}({scheduled_start_min}分), scheduled_end={scheduled_end}({scheduled_end_min}分)")
    logger.info(f"[時間外分類デバッグ] 時間外作業: overtime_start={start_time}({overtime_start_min}分), overtime_end={end_time}({overtime_end_min}分)")
    
    # 日をまたぐ場合の処理
    if overtime_end_min < overtime_start_min:
        overtime_end_min += 1440  # 24時間 = 1440分
        logger.info(f"[時間外分類デバッグ] 時間外作業が日をまたぐため調整: overtime_end_min={overtime_end_min}分")
        
    # スケジュールが日をまたぐ場合の処理（24勤など）
    # 「明」勤務または24勤の場合は、24勤スケジュールの終了時刻が翌日を意味する
    if work_type and (is_off_day_shift(work_type) or '24勤' in work_type):
        # 24勤の終了時刻が翌日の場合（例：8:30 → 翌8:30）
        if scheduled_end == scheduled_start:  # 同じ時刻 = 24時間勤務
            scheduled_end_min = scheduled_start_min + 1440  # 翌日の同時刻
            logger.info(f"[時間外分類デバッグ] 24勤: 終了時刻を翌日に調整 scheduled_end_min={scheduled_end_min}分")
            
            # 時間外作業が翌日の早朝の場合、翌日の時刻として調整
            if overtime_start_min < scheduled_start_min:
                overtime_start_min += 1440  # 翌日の時刻
                overtime_end_min += 1440
                logger.info(f"[時間外分類デバッグ] 24勤の翌日早朝時間外: {overtime_start_min//60:02d}:{overtime_start_min%60:02d}-{overtime_end_min//60:02d}:{overtime_end_min%60:02d} に調整")
                
        elif scheduled_end_min <= scheduled_start_min:
            scheduled_end_min += 1440  # 翌日に調整
            logger.info(f"[時間外分類デバッグ] 24勤: 終了時刻を翌日に調整 scheduled_end_min={scheduled_end_min}分")
    elif scheduled_end_min < scheduled_start_min:
        scheduled_end_min += 1440
        logger.info(f"[時間外分類デバッグ] スケジュールが日をまたぐため調整: scheduled_end_min={scheduled_end_min}分")
    
    inner_minutes = 0
    outer_minutes = 0
    
    # 日勤の場合：勤務予定時間内で発生する時間外作業を考慮（スケジュールベース）
    # 24勤の場合：24時間勤務での時間外作業を考慮（スケジュールベース）
    # 外残業：開始時間より早い時間、または終了時間より遅い時間での時間外作業
    # 内残業：勤務時間内での休憩時間での時間外作業（勤務時間内の時間外作業）
    
    # 時間外作業の総時間を計算
    total_overtime_minutes = overtime_end_min - overtime_start_min
    logger.info(f"[時間外分類デバッグ] 時間外作業総時間: {total_overtime_minutes}分 ({total_overtime_minutes/60:.2f}時間)")
    
    # 内残業の判定：勤務時間内（開始時刻から終了時刻の間）の時間外作業
    # 時間外作業が勤務時間内に一部でも含まれる場合、その部分を内残業とする
    inner_start_min = None
    inner_end_min = None
    logger.info(f"[時間外分類デバッグ] 内残業判定条件チェック: overtime_start_min({overtime_start_min}) < scheduled_end_min({scheduled_end_min}) = {overtime_start_min < scheduled_end_min}")
    logger.info(f"[時間外分類デバッグ] 内残業判定条件チェック: overtime_end_min({overtime_end_min}) > scheduled_start_min({scheduled_start_min}) = {overtime_end_min > scheduled_start_min}")
    
    if overtime_start_min < scheduled_end_min and overtime_end_min > scheduled_start_min:
        # 24勤の場合、当日の終了時刻（例：8:30）以降は外残業とする
        if work_type and '24勤' in work_type and scheduled_end == scheduled_start:
            # 当日の終了時刻（調整前の値）
            original_end_min = scheduled_start_min  # 8:30 = 510分
            
            # 翌日に調整された時間外作業の場合（1440分以上）
            if overtime_start_min >= 1440:
                # 翌日の時間外作業 → 24勤の勤務時間内として処理
                inner_start_min = max(overtime_start_min, scheduled_start_min)
                inner_end_min = min(overtime_end_min, scheduled_end_min)
                logger.info(f"[時間外分類デバッグ] 24勤翌日時間外: inner_start_min={inner_start_min}分, inner_end_min={inner_end_min}分")
                if inner_end_min > inner_start_min:
                    inner_minutes = inner_end_min - inner_start_min
                    logger.info(f"[時間外分類デバッグ] 翌日内残業時間: {inner_minutes}分 ({inner_minutes/60:.2f}時間)")
                else:
                    logger.info(f"[時間外分類デバッグ] 翌日内残業範囲が無効")
            # 当日の時間外作業が当日終了時刻以降の場合は外残業
            elif overtime_start_min >= original_end_min:
                logger.info(f"[時間外分類デバッグ] 24勤当日終了時刻({original_end_min}分)以降の作業 → 外残業")
                inner_minutes = 0
            else:
                # 勤務時間内の時間外作業の範囲を計算（当日終了時刻まで）
                inner_start_min = max(overtime_start_min, scheduled_start_min)
                inner_end_min = min(overtime_end_min, original_end_min)
                logger.info(f"[時間外分類デバッグ] 24勤当日内残業範囲: inner_start_min={inner_start_min}分, inner_end_min={inner_end_min}分")
                if inner_end_min > inner_start_min:
                    inner_minutes = inner_end_min - inner_start_min
                    logger.info(f"[時間外分類デバッグ] 当日内残業時間: {inner_minutes}分 ({inner_minutes/60:.2f}時間)")
                else:
                    logger.info(f"[時間外分類デバッグ] 当日内残業範囲が無効")
        else:
            # 通常の勤務時間内の時間外作業の範囲を計算
            inner_start_min = max(overtime_start_min, scheduled_start_min)
            inner_end_min = min(overtime_end_min, scheduled_end_min)
            logger.info(f"[時間外分類デバッグ] 内残業範囲計算: inner_start_min={inner_start_min}分, inner_end_min={inner_end_min}分")
            if inner_end_min > inner_start_min:
                inner_minutes = inner_end_min - inner_start_min
                logger.info(f"[時間外分類デバッグ] 内残業時間: {inner_minutes}分 ({inner_minutes/60:.2f}時間)")
            else:
                logger.info(f"[時間外分類デバッグ] 内残業範囲が無効: inner_end_min({inner_end_min}) <= inner_start_min({inner_start_min})")
    else:
        logger.info(f"[時間外分類デバッグ] 内残業条件不一致: 時間外作業が勤務時間内に含まれていない")
    
    # 外残業の計算：時間外作業全体から内残業を引いた残り
    outer_minutes = total_overtime_minutes - inner_minutes
    logger.info(f"[時間外分類デバッグ] 外残業計算: total_overtime_minutes({total_overtime_minutes}) - inner_minutes({inner_minutes}) = {outer_minutes}分 ({outer_minutes/60:.2f}時間)")
    
    # 深夜時間の計算（設定値から動的に取得）
    # 内残業と外残業それぞれに対して深夜時間を計算
    night_minutes = 0
    
    # 外残業の深夜時間を計算
    # 外残業は開始時刻より前、または終了時刻より後の部分
    if outer_minutes > 0:
        # 開始時刻より前の部分
        if overtime_start_min < scheduled_start_min:
            outer_start_before_min = overtime_start_min
            outer_end_before_min = min(scheduled_start_min, overtime_end_min)
            night_minutes += _calculate_night_minutes_from_range(outer_start_before_min, outer_end_before_min)
        
        # 終了時刻より後の部分
        if overtime_end_min > scheduled_end_min:
            outer_start_after_min = max(scheduled_end_min, overtime_start_min)
            outer_end_after_min = overtime_end_min
            night_minutes += _calculate_night_minutes_from_range(outer_start_after_min, outer_end_after_min)
    
    # 内残業の深夜時間を計算
    if inner_minutes > 0 and inner_start_min is not None and inner_end_min is not None:
        night_minutes += _calculate_night_minutes_from_range(inner_start_min, inner_end_min)
    
    overtime_type = '内残業' if inner_minutes > 0 else '外残業'
    
    logger.info(f"[時間外分類デバッグ] 最終判定: overtime_type={overtime_type}, inner={inner_minutes}分({inner_minutes/60:.2f}h), outer={outer_minutes}分({outer_minutes/60:.2f}h), night={night_minutes}分({night_minutes/60:.2f}h)")
    
    return {
        'overtime_type': overtime_type,
        'inner_overtime_minutes': inner_minutes,
        'outer_overtime_minutes': outer_minutes,
        'night_overtime_minutes': night_minutes
    }

def _calculate_night_minutes_from_range(start_min, end_min):
    """
    分単位の範囲に対して深夜時間を計算（共通ヘルパー関数）
    
    Args:
        start_min: 開始時刻（分）
        end_min: 終了時刻（分）
    
    Returns:
        int: 深夜時間（分）
    """
    if end_min < start_min:
        end_min += AttendanceConstants.MINUTES_PER_DAY
    
    night_start = AttendanceConstants.get_night_start_minutes()
    night_end_day2 = AttendanceConstants.get_night_end_minutes_day2()
    minutes_per_day = AttendanceConstants.MINUTES_PER_DAY
    
    night_minutes_total = 0
    
    # 1日目の深夜時間帯（設定開始時間-24:00）との重複
    if start_min < minutes_per_day:
        overlap_start_day1 = max(start_min, night_start)
        overlap_end_day1 = min(end_min, minutes_per_day)
        if overlap_end_day1 > overlap_start_day1:
            night_minutes_total += overlap_end_day1 - overlap_start_day1
    
    # 2日目の深夜時間帯（00:00-設定終了時間）との重複
    if end_min > minutes_per_day:
        start_day2 = start_min - minutes_per_day if start_min > minutes_per_day else 0
        end_day2 = end_min - minutes_per_day
        overlap_start_day2 = max(start_day2, 0)
        overlap_end_day2 = min(end_day2, night_end_day2)
        if overlap_end_day2 > overlap_start_day2:
            night_minutes_total += overlap_end_day2 - overlap_start_day2
    
    return night_minutes_total

def calculate_night_overtime(start_time, end_time):
    """
    深夜時間帯の時間を計算（時刻文字列から分単位に変換して計算）
    
    Args:
        start_time: 開始時刻 (HH:MM)
        end_time: 終了時刻 (HH:MM)
    
    Returns:
        int: 深夜時間（分）
    """
    start_min = time_to_minutes(start_time)
    end_min = time_to_minutes(end_time)
    
    return _calculate_night_minutes_from_range(start_min, end_min)

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
        logger.info(f"[時間外申告登録] 開始: 従業員={employee_num}, 作業日={work_date}, 時間={start_time}-{end_time}")
        categories = calculate_overtime_categories(employee_num, work_date, start_time, end_time)
        logger.info(f"[時間外申告登録] 計算結果: type={categories['overtime_type']}, inner={categories['inner_overtime_minutes']}分, outer={categories['outer_overtime_minutes']}分, night={categories['night_overtime_minutes']}分")
        
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
                # 文字列と整数の両方に対応
                params.append(str(employee_num))
            
            if work_date:
                query += " AND work_date = ?"
                # 日付フォーマットを統一（YYYY-MM-DD形式）
                if isinstance(work_date, str):
                    # 既にYYYY-MM-DD形式の場合はそのまま使用
                    work_date_str = work_date.strip()
                    # YYYY/MM/DD形式の場合はYYYY-MM-DDに変換
                    if '/' in work_date_str:
                        try:
                            date_obj = datetime.strptime(work_date_str, '%Y/%m/%d')
                            work_date_str = date_obj.strftime('%Y-%m-%d')
                        except ValueError:
                            pass
                    params.append(work_date_str)
                else:
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

