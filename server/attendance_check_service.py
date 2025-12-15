#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
勤怠チェック関連のビジネスロジック
database.pyから分離した勤怠チェック専用モジュール
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from utils import get_db_connection, calculate_time_diff_minutes, extract_time_from_timestamp, time_to_minutes
from work_type_constants import is_off_day_shift, is_24hour_or_night_shift, is_holiday_shift, WORK_TYPE_OFF_DAY
from logger_config import setup_logger
from constants import AttendanceConstants

logger = setup_logger(__name__)

def _add_alert(result: 'AttendanceCheckResult', alert_type: str, message: str, details: str) -> None:
    """アラート追加のヘルパー関数"""
    result.alerts.append({
        'type': alert_type,
        'message': message,
        'details': details
    })

class AttendanceCheckResult:
    """勤怠チェック結果を格納するデータクラス"""
    
    def __init__(self, employee_id: str, employee_name: str, check_date: str):
        self.employee_id = employee_id
        self.employee_name = employee_name
        self.check_date = check_date
        self.schedule: Optional[Dict] = None
        self.attendance_records: List[Dict] = []
        self.actual_clock_in: Optional[str] = None
        self.actual_clock_out: Optional[str] = None
        self.alerts: List[Dict] = []
        self.prev_day_night_shift: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """辞書形式で返す"""
        return {
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'check_date': self.check_date,
            'schedule': self.schedule,
            'attendance_records': self.attendance_records,
            'actual_clock_in': self.actual_clock_in,
            'actual_clock_out': self.actual_clock_out,
            'alerts': self.alerts,
            'prev_day_night_shift': self.prev_day_night_shift
        }

def get_employee_info(cursor, employee_id: str) -> Optional[Tuple[int, str, str]]:
    """従業員情報を取得"""
    cursor.execute("""
        SELECT employee_num, name, idm FROM employee_master 
        WHERE employee_num = ?
    """, (employee_id,))
    return cursor.fetchone()

def get_schedule_info(cursor, employee_id: str, check_date: str) -> Optional[Tuple]:
    """スケジュール情報を取得"""
    cursor.execute("""
        SELECT id, work_date, work_type, start_time, end_time
        FROM attend_schedule
        WHERE employee_id = ? AND work_date = ?
    """, (employee_id, check_date))
    return cursor.fetchone()

def get_attendance_records(cursor, idm: str, check_date: str) -> List[Tuple]:
    """打刻記録を取得"""
    cursor.execute("""
        SELECT id, timestamp, terminal_id
        FROM attendance
        WHERE idm = ? AND date(timestamp) = ?
        ORDER BY timestamp ASC
    """, (idm, check_date))
    return cursor.fetchall()

def get_prev_day_night_shift(cursor, employee_id: str, prev_date: str) -> Optional[Tuple]:
    """前日の24勤・夜勤スケジュールを取得"""
    cursor.execute("""
        SELECT work_date, work_type, start_time, end_time
        FROM attend_schedule
        WHERE employee_id = ? AND work_date = ? AND (work_type LIKE '%24勤%' OR work_type LIKE '%夜勤%')
    """, (employee_id, prev_date))
    return cursor.fetchone()

def extract_time_from_timestamp(timestamp_str: str) -> str:
    """タイムスタンプから時刻部分を抽出"""
    try:
        if 'T' in timestamp_str:
            return timestamp_str.split('T')[1].split('.')[0][:5]
        elif ' ' in timestamp_str:
            return timestamp_str.split(' ')[1][:5]
        else:
            return timestamp_str[:5]
    except:
        return timestamp_str

def calculate_actual_clock_times(result: AttendanceCheckResult, cursor) -> None:
    """実際の打刻時刻を計算"""
    work_type = result.schedule['work_type'] if result.schedule else None
    
    if not result.attendance_records:
        return
    
    if is_24hour_or_night_shift(work_type):
        # 24勤・夜勤: 一番早い時間が出勤
        result.actual_clock_in = result.attendance_records[0]['time']
        
        # 翌日の「明」勤務の打刻から終了時間を取得
        end_time = get_night_shift_end_time_from_next_day(cursor, result.employee_id, result.check_date)
        if end_time:
            result.actual_clock_out = end_time
    
    elif is_off_day_shift(work_type):
        # 「明」勤務: 前日の24勤・夜勤の退勤時刻を表示
        result.actual_clock_in = None
        if result.attendance_records:
            result.actual_clock_out = result.attendance_records[-1]['time']
    
    else:
        # 日勤: 一番早い時間が出勤、一番遅い時間が退勤
        if result.attendance_records:
            result.actual_clock_in = result.attendance_records[0]['time']
            result.actual_clock_out = result.attendance_records[-1]['time']

def check_holiday_punch_errors(result: AttendanceCheckResult) -> None:
    """休日打刻エラーをチェック"""
    if not result.schedule:
        return
    
    work_type = result.schedule['work_type']
    if work_type and ('有' in work_type or '所' in work_type or '法' in work_type):
        if result.attendance_records:
            # 打刻が1回だけの場合はエラーを出す（休日出勤届があっても）
            if len(result.attendance_records) == 1:
                _add_alert(result, AttendanceConstants.ALERT_ERROR, 
                          AttendanceConstants.MSG_HOLIDAY_PUNCH,
                          f'勤務タイプ: {work_type}、打刻回数: {len(result.attendance_records)}回')
            # 出勤と退勤の打刻がある場合（2回以上）
            elif len(result.attendance_records) >= 2:
                # 休日出勤届があるかチェック
                try:
                    from overtime import get_overtime_applications
                    overtime_apps = get_overtime_applications(
                        employee_num=str(result.employee_id),
                        work_date=result.check_date,
                        status=AttendanceConstants.STATUS_APPROVED,
                        limit=AttendanceConstants.DEFAULT_LIMIT
                    )
                    
                    # 休日出勤届がない場合のみエラーを出す
                    if not overtime_apps:
                        _add_alert(result, AttendanceConstants.ALERT_ERROR,
                                  AttendanceConstants.MSG_HOLIDAY_PUNCH,
                                  f'勤務タイプ: {work_type}、打刻回数: {len(result.attendance_records)}回（休日出勤届なし）')
                except Exception as e:
                    logger.warning(f"休日出勤届チェックエラー: {e}")
                    # チェックエラーの場合はエラーを出す
                    _add_alert(result, AttendanceConstants.ALERT_ERROR,
                              AttendanceConstants.MSG_HOLIDAY_PUNCH,
                              f'勤務タイプ: {work_type}、打刻回数: {len(result.attendance_records)}回')

def check_missing_punch_errors(result: AttendanceCheckResult) -> None:
    """打刻なし・打刻漏れエラーをチェック"""
    if not result.schedule:
        return
    
    # 未来の日付（明日以降）は打刻がないのが正常なので、エラーを出さない
    try:
        from datetime import date
        check_date_obj = datetime.strptime(result.check_date, AttendanceConstants.DATE_FORMAT).date()
        today = date.today()
        if check_date_obj > today:
            logger.info(f"  未来の日付のため打刻なしエラーをスキップ: 日付={result.check_date}, 今日={today}")
            return
    except (ValueError, TypeError) as e:
        logger.warning(f"  日付比較エラー: {e}, check_date={result.check_date}")
        # 日付の解析に失敗した場合は続行（既存の動作を維持）
    
    work_type = result.schedule['work_type']
    if work_type and not is_holiday_shift(work_type):
        should_check = False
        
        if is_off_day_shift(work_type):
            # 「明」勤務の場合は前日の24勤・夜勤の退勤のみなので、1回の打刻は正常
            should_check = True
        elif result.schedule['start_time'] or result.schedule['end_time']:
            should_check = True
        
        if should_check:
            # 休暇申請があるかチェック（承認済みのみ）
            # 承認待ち（pending）の休暇申請もチェック対象に含める（申請されている時点で休暇予定とみなす）
            has_leave_request = False
            try:
                from leave_request import get_leave_requests
                from datetime import datetime as dt
                
                # 日付を正規化（YYYY-MM-DD形式に統一）
                check_date_normalized = result.check_date
                if isinstance(check_date_normalized, str):
                    # 日付文字列を正規化
                    try:
                        # 様々な形式に対応
                        if '/' in check_date_normalized:
                            check_date_normalized = dt.strptime(check_date_normalized, AttendanceConstants.DATE_FORMAT_SLASH).strftime(AttendanceConstants.DATE_FORMAT)
                        elif len(check_date_normalized) == 8:
                            # YYYYMMDD形式
                            check_date_normalized = dt.strptime(check_date_normalized, '%Y%m%d').strftime(AttendanceConstants.DATE_FORMAT)
                    except ValueError:
                        pass  # 既にYYYY-MM-DD形式の可能性がある
                
                # 承認済みの休暇申請をチェック
                approved_leaves = get_leave_requests(
                    employee_num=str(result.employee_id),
                    leave_date=check_date_normalized,
                    status=AttendanceConstants.STATUS_APPROVED,
                    limit=AttendanceConstants.DEFAULT_LIMIT
                )
                
                # 承認待ちの休暇申請もチェック（申請されている時点で休暇予定とみなす）
                pending_leaves = get_leave_requests(
                    employee_num=str(result.employee_id),
                    leave_date=check_date_normalized,
                    status=AttendanceConstants.STATUS_PENDING,
                    limit=AttendanceConstants.DEFAULT_LIMIT
                )
                
                all_leaves = approved_leaves + pending_leaves
                
                logger.info(f"  休暇申請チェック: 日付={check_date_normalized}, 従業員ID={result.employee_id}, 承認済み={len(approved_leaves)}件, 承認待ち={len(pending_leaves)}件, 合計={len(all_leaves)}件")
                
                # get_leave_requestsは既に該当日付を含む休暇申請のみを返すので、
                # 結果が1件以上あれば休暇申請があると判断
                if all_leaves and len(all_leaves) > 0:
                    has_leave_request = True
                    leave_info = all_leaves[0]
                    leave_status = leave_info.get('status', 'unknown')
                    logger.info(f"  休暇申請あり: 日付={check_date_normalized}, 休暇種類={leave_info.get('leave_type', '')}, ステータス={leave_status}, 期間={leave_info.get('leave_date_from', '')}～{leave_info.get('leave_date_to', '')}")
            except Exception as e:
                logger.warning(f"休暇申請チェックエラー: {e}", exc_info=True)
            
            # 休暇申請がある場合は「打刻なし」エラーを出さない
            if has_leave_request:
                logger.info(f"  休暇申請があるため打刻なしエラーをスキップ: 日付={result.check_date}")
                return
            
            punch_count = len(result.attendance_records) if result.attendance_records else 0
            
            logger.info(f"打刻漏れチェック: 日付={result.check_date}, 勤務タイプ={work_type}, 打刻回数={punch_count}, start_time={result.schedule.get('start_time')}, end_time={result.schedule.get('end_time')}")
            logger.info(f"  24勤・夜勤チェック: {is_24hour_or_night_shift(work_type)}")
            logger.info(f"  明勤務チェック: {is_off_day_shift(work_type)}")
            
            # 打刻が全くない場合
            if punch_count == 0:
                logger.info(f"  打刻なしエラーを追加")
                _add_alert(result, AttendanceConstants.ALERT_ERROR,
                          AttendanceConstants.MSG_MISSING_PUNCH,
                          f'勤務タイプ: {work_type}、スケジュール: {result.schedule["start_time"]} - {result.schedule["end_time"]}')
            # 日勤（24勤・夜勤・明勤務以外）で打刻が1回しかない場合
            # この場合はcheck_time_difference_errorsで「出勤打刻漏れ」または「退勤打刻漏れ」を判定するため、
            # ここでは汎用的な「打刻漏れ」エラーを出さない
            elif (punch_count == 1 and 
                  not is_24hour_or_night_shift(work_type) and 
                  not is_off_day_shift(work_type) and
                  result.schedule['start_time'] and 
                  result.schedule['end_time']):
                # 日勤は出勤と退勤の両方が必要だが、どちらが漏れているかはcheck_time_difference_errorsで判定
                logger.info(f"  打刻1回のみ: check_time_difference_errorsで出勤/退勤打刻漏れを判定するため、ここではスキップ")
            else:
                logger.info(f"  打刻漏れチェック条件不一致: punch_count={punch_count}, is_24hour_or_night={is_24hour_or_night_shift(work_type)}, is_off_day={is_off_day_shift(work_type)}, has_start={bool(result.schedule.get('start_time'))}, has_end={bool(result.schedule.get('end_time'))}")

def check_holiday_work_errors(result: AttendanceCheckResult) -> None:
    """休日出勤エラーをチェック"""
    if not result.schedule:
        return
    
    work_type = result.schedule['work_type']
    if work_type and ('休出' in work_type or '休日出勤' in work_type):
        if not result.attendance_records:
            _add_alert(result, AttendanceConstants.ALERT_ERROR,
                      AttendanceConstants.MSG_HOLIDAY_WORK_NO_PUNCH,
                      f'勤務タイプ: {work_type}、スケジュール: {result.schedule["start_time"]} - {result.schedule["end_time"]}')

def check_leave_request_conflicts(result: AttendanceCheckResult) -> None:
    """休暇申請との競合をチェック"""
    try:
        from leave_request import get_leave_requests
        approved_leaves = get_leave_requests(
            employee_num=str(result.employee_id),
            leave_date=result.check_date,
            status=AttendanceConstants.STATUS_APPROVED,
            limit=AttendanceConstants.DEFAULT_LIMIT
        )
        
        for leave in approved_leaves:
            leave_date_from = leave.get('leave_date_from')
            leave_date_to = leave.get('leave_date_to')
            
            if leave_date_from and leave_date_to:
                if leave_date_from <= result.check_date <= leave_date_to:
                    if result.attendance_records:
                        leave_type = leave.get('leave_type', '')
                        leave_subtype = leave.get('leave_subtype', '')
                        leave_detail = leave_type
                        if leave_subtype:
                            leave_detail += f' ({leave_subtype})'
                        
                        _add_alert(result, AttendanceConstants.ALERT_ERROR,
                                  AttendanceConstants.MSG_LEAVE_WITH_PUNCH,
                                  f'休暇種類: {leave_detail}、打刻回数: {len(result.attendance_records)}回')
                        break
    except Exception as e:
        logger.warning(f"休暇願チェックエラー: {e}")

def get_late_early_adjustments(result: AttendanceCheckResult) -> Tuple[int, int]:
    """遅刻・早退申告による調整分数を取得"""
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        late_minutes_adjustment = 0
        early_minutes_adjustment = 0
        
        # 承認済みの遅刻申告
        cursor.execute("""
            SELECT late_minutes FROM late_arrival_requests 
            WHERE employee_num = ? AND work_date = ? AND status = ?
        """, (result.employee_id, result.check_date, AttendanceConstants.STATUS_APPROVED))
        
        for row in cursor.fetchall():
            late_minutes_adjustment += row[0]
        
        # 承認済みの早退申告
        cursor.execute("""
            SELECT early_minutes FROM early_leave_requests 
            WHERE employee_num = ? AND work_date = ? AND status = ?
        """, (result.employee_id, result.check_date, AttendanceConstants.STATUS_APPROVED))
        
        for row in cursor.fetchall():
            early_minutes_adjustment += row[0]
        
        # 24勤・夜勤の翌日の明勤務の遅刻申告もチェック
        work_type = result.schedule['work_type'] if result.schedule else None
        if is_24hour_or_night_shift(work_type):
            next_date = (datetime.strptime(result.check_date, AttendanceConstants.DATE_FORMAT) + timedelta(days=1)).strftime(AttendanceConstants.DATE_FORMAT)
            cursor.execute("""
                SELECT late_minutes FROM late_arrival_requests 
                WHERE employee_num = ? AND work_date = ? AND status = ?
            """, (result.employee_id, next_date, AttendanceConstants.STATUS_APPROVED))
            
            for row in cursor.fetchall():
                late_minutes_adjustment += row[0]
        
        return late_minutes_adjustment, early_minutes_adjustment

def _get_overtime_applications_safe(result: AttendanceCheckResult) -> List[Dict]:
    """時間外申告を安全に取得するヘルパー関数"""
    try:
        from overtime import get_overtime_applications
        employee_num_str = str(result.employee_id)
        employee_num_int = None
        try:
            employee_num_int = int(result.employee_id)
        except (ValueError, TypeError):
            pass
        
        # 文字列で検索
        overtime_apps = get_overtime_applications(
            employee_num=employee_num_str,
            work_date=result.check_date,
            status=AttendanceConstants.STATUS_APPROVED,
            limit=AttendanceConstants.DEFAULT_LIMIT
        )
        
        # 文字列で取得できなかった場合、整数で再試行
        if not overtime_apps and employee_num_int is not None:
            logger.debug(f"文字列での取得失敗、整数で再試行: {employee_num_int}")
            overtime_apps = get_overtime_applications(
                employee_num=employee_num_int,
                work_date=result.check_date,
                status=AttendanceConstants.STATUS_APPROVED,
                limit=AttendanceConstants.DEFAULT_LIMIT
            )
        
        logger.info(f"時間外申告取得: 従業員={employee_num_str}({employee_num_int}), 日付={result.check_date}, 件数={len(overtime_apps)}")
        return overtime_apps
    except Exception as e:
        logger.error(f"時間外申告取得エラー: {e}", exc_info=True)
        return []

def _check_overtime_overlap(schedule_end_minutes: int, actual_end_minutes: int, overtime_apps: List[Dict]) -> bool:
    """時間外申告と実際の退勤時間の重複チェック"""
    for app in overtime_apps:
        app_start = app.get('start_time')
        app_end = app.get('end_time')
        
        if not app_start or not app_end:
            continue
            
        app_start_minutes = time_to_minutes(app_start)
        app_end_minutes = time_to_minutes(app_end)
        
        if app_start_minutes is None or app_end_minutes is None:
            continue
        
        # 重複チェック
        overlap_condition1 = app_start_minutes <= actual_end_minutes
        overlap_condition2 = app_end_minutes >= schedule_end_minutes
        
        # 許容範囲チェック
        time_diff = abs(app_end_minutes - actual_end_minutes)
        within_tolerance = time_diff <= AttendanceConstants.TOLERANCE_MINUTES
        
        logger.debug(f"時間外申告重複チェック: {app_start}-{app_end}, 重複={overlap_condition1 and overlap_condition2}, 許容範囲内={within_tolerance}")
        
        if (overlap_condition1 and overlap_condition2) or within_tolerance:
            return True
    
    return False

def check_time_difference_errors(result: AttendanceCheckResult, late_adjust: int, early_adjust: int) -> None:
    """出退勤時刻差異をチェック"""
    if not (result.schedule and result.attendance_records):
        return
    
    schedule_start = result.schedule['start_time']
    schedule_end = result.schedule['end_time']
    actual_start = result.actual_clock_in
    actual_end = result.actual_clock_out
    
    work_type = result.schedule['work_type']
    is_night_shift_day = is_24hour_or_night_shift(work_type)
    
    logger.info(f"出退勤時刻差異チェック開始: 日付={result.check_date}, 従業員={result.employee_id}, スケジュール={schedule_start}-{schedule_end}, 実際={actual_start}-{actual_end}")
    
    # 時間外申告を取得
    overtime_apps = _get_overtime_applications_safe(result)
    
    logger.info(f"出退勤時刻差異チェック: 時間外申告取得完了, 件数={len(overtime_apps)}")
    if overtime_apps:
        for app in overtime_apps:
            logger.info(f"  時間外申告: 開始時間={app.get('start_time')}, 終了時間={app.get('end_time')}")
    
    # 日勤で打刻が1回しかない場合の処理
    punch_count = len(result.attendance_records)
    skip_clock_in_diff = False
    skip_clock_out_diff = False
    
    if (punch_count == 1 and 
        not is_night_shift_day and 
        not is_off_day_shift(work_type) and
        schedule_start and schedule_end and
        actual_start and actual_end):
        # 打刻が1回しかない場合、その打刻時間が開始時間に近いか、終了時間に近いかを判定
        single_punch_time = actual_start  # actual_startとactual_endは同じ値
        
        # 開始時間との差異を計算
        diff_to_start = calculate_time_diff_minutes(schedule_start, single_punch_time)
        # 終了時間との差異を計算
        diff_to_end = calculate_time_diff_minutes(schedule_end, single_punch_time)
        
        if diff_to_start is not None and diff_to_end is not None:
            abs_diff_to_start = abs(diff_to_start)
            abs_diff_to_end = abs(diff_to_end)
            
            logger.info(f"打刻1回のみの判定: 打刻時間={single_punch_time}, 開始時間={schedule_start} (差異={diff_to_start}分), 終了時間={schedule_end} (差異={diff_to_end}分), 許容時間={AttendanceConstants.TOLERANCE_MINUTES}分")
            
            # 開始時間に近い場合（±15分以内）→ 退勤打刻漏れ
            if abs_diff_to_start <= AttendanceConstants.TOLERANCE_MINUTES:
                skip_clock_in_diff = True
                logger.info(f"打刻1回のみ: 開始時間に近いため、出勤時刻差異エラーをスキップし、退勤打刻漏れエラーを追加: 打刻={single_punch_time}, 開始時間={schedule_start}, 差異={diff_to_start}分")
                # 退勤打刻漏れエラーを追加
                _add_alert(result, AttendanceConstants.ALERT_ERROR,
                          AttendanceConstants.MSG_CLOCK_OUT_PUNCH_LEAK,
                          AttendanceConstants.DETAIL_CLOCK_OUT_MISSING_SINGLE_PUNCH.format(schedule=schedule_end))
            
            # 終了時間に近い場合（±15分以内）→ 出勤打刻漏れ
            elif abs_diff_to_end <= AttendanceConstants.TOLERANCE_MINUTES:
                skip_clock_out_diff = True
                logger.info(f"打刻1回のみ: 終了時間に近いため、退勤時刻差異エラーをスキップし、出勤打刻漏れエラーを追加: 打刻={single_punch_time}, 終了時間={schedule_end}, 差異={diff_to_end}分")
                # 出勤打刻漏れエラーを追加
                _add_alert(result, AttendanceConstants.ALERT_ERROR,
                          AttendanceConstants.MSG_CLOCK_IN_PUNCH_LEAK,
                          AttendanceConstants.DETAIL_CLOCK_IN_MISSING_SINGLE_PUNCH.format(schedule=schedule_start))
    
    # 出勤時刻チェック（24勤・夜勤以外）
    _check_clock_in_time_diff(result, schedule_start, actual_start, late_adjust, is_night_shift_day, overtime_apps, skip_clock_in_diff, punch_count)
    
    # 退勤時刻チェック（日勤のみ）
    _check_clock_out_time_diff(result, schedule_end, actual_end, early_adjust, work_type, is_night_shift_day, overtime_apps, skip_clock_out_diff, punch_count)
    
    logger.info(f"出退勤時刻差異チェック完了: 日付={result.check_date}, アラート件数={len(result.alerts)}")

def _has_punch_leak_alert(result: AttendanceCheckResult) -> bool:
    """打刻漏れエラーが既に存在するかチェック"""
    punch_leak_messages = {
        AttendanceConstants.MSG_CLOCK_IN_PUNCH_LEAK,
        AttendanceConstants.MSG_CLOCK_OUT_PUNCH_LEAK,
        AttendanceConstants.MSG_PUNCH_LEAK
    }
    return any(alert['message'] in punch_leak_messages for alert in result.alerts)

def _check_clock_in_time_diff(result: AttendanceCheckResult, schedule_start: str, actual_start: str, late_adjust: int, is_night_shift_day: bool, overtime_apps: List[Dict], skip_diff: bool = False, punch_count: int = 0) -> None:
    """出勤時刻差異をチェック"""
    # 出勤打刻漏れのチェック（スケジュールがあるが打刻がない場合、または打刻が1回のみで終了時間に近い場合）
    if schedule_start and not actual_start and not is_night_shift_day:
        logger.info(f"出勤打刻漏れエラー追加: スケジュール={schedule_start}, 実際の打刻なし")
        _add_alert(result, AttendanceConstants.ALERT_ERROR,
                  AttendanceConstants.MSG_CLOCK_IN_PUNCH_LEAK,
                  AttendanceConstants.DETAIL_CLOCK_IN_MISSING.format(schedule=schedule_start))
        return
    
    # 打刻が1回のみで終了時間に近い場合は既にエラーを追加済みなのでスキップ
    if skip_diff and punch_count == 1:
        logger.info(f"出勤時刻: 打刻1回のみで終了時間に近いため、既に出勤打刻漏れエラーを追加済み")
        return
    
    # 打刻漏れエラーが既に存在する場合は時刻差異エラーを出さない
    if _has_punch_leak_alert(result):
        logger.info(f"出勤時刻: 打刻漏れエラーが既に存在するため、時刻差異エラーをスキップ")
        return
    
    if schedule_start and actual_start and not is_night_shift_day:
        logger.info(f"出勤時刻差異チェック開始: スケジュール={schedule_start}, 実際={actual_start}, 遅刻調整={late_adjust}分, 時間外申告件数={len(overtime_apps)}, skip_diff={skip_diff}")
        
        # 打刻1回のみで開始時間に近い場合はスキップ
        if skip_diff:
            logger.info(f"出勤時刻: 打刻1回のみで開始時間に近いため、エラーをスキップ: 打刻={actual_start}")
            return
        
        # 時間外申告の開始時間と出勤打刻時間が±15分以内かチェック
        if _check_overtime_time_within_tolerance(actual_start, overtime_apps):
            logger.info(f"出勤時刻: 時間外申告の開始時間と打刻時間が±15分以内のため、エラーをスキップ: 打刻={actual_start}")
            return
        
        diff_start = calculate_time_diff_minutes(schedule_start, actual_start)
        if diff_start is not None:
            adjusted_diff_start = diff_start - late_adjust
            logger.info(f"出勤時刻差異計算: スケジュール={schedule_start}, 実際={actual_start}, diff_start={diff_start}分, late_adjust={late_adjust}分, adjusted_diff_start={adjusted_diff_start}分, 閾値={AttendanceConstants.TIME_DIFF_THRESHOLD}分")
            if abs(adjusted_diff_start) >= AttendanceConstants.TIME_DIFF_THRESHOLD:
                logger.info(f"出勤時刻差異エラー追加: 差異={adjusted_diff_start}分 (閾値={AttendanceConstants.TIME_DIFF_THRESHOLD}分)")
                _add_alert(result, AttendanceConstants.ALERT_WARNING,
                          AttendanceConstants.MSG_CLOCK_IN_TIME_DIFF,
                          AttendanceConstants.DETAIL_CLOCK_IN_TIME_DIFF.format(
                              schedule=schedule_start, actual=actual_start, 
                              diff=diff_start, adjusted_diff=adjusted_diff_start))
            else:
                logger.info(f"出勤時刻差異: 差異={adjusted_diff_start}分は閾値未満のためエラーなし")

def _check_clock_out_time_diff(result: AttendanceCheckResult, schedule_end: str, actual_end: str, early_adjust: int, 
                              work_type: str, is_night_shift_day: bool, overtime_apps: List[Dict], skip_diff: bool = False, punch_count: int = 0) -> None:
    """退勤時刻差異をチェック"""
    # 退勤打刻漏れのチェック（スケジュールがあるが打刻がない場合、または打刻が1回のみで開始時間に近い場合）
    if schedule_end and not actual_end and not is_night_shift_day and not is_24hour_or_night_shift(work_type):
        logger.info(f"退勤打刻漏れエラー追加: スケジュール={schedule_end}, 実際の打刻なし")
        _add_alert(result, AttendanceConstants.ALERT_ERROR,
                  AttendanceConstants.MSG_CLOCK_OUT_PUNCH_LEAK,
                  AttendanceConstants.DETAIL_CLOCK_OUT_MISSING.format(schedule=schedule_end))
        return
    
    # 打刻が1回のみで開始時間に近い場合は既にエラーを追加済みなのでスキップ
    if skip_diff and punch_count == 1:
        logger.info(f"退勤時刻: 打刻1回のみで開始時間に近いため、既に退勤打刻漏れエラーを追加済み")
        return
    
    # 打刻漏れエラーが既に存在する場合は時刻差異エラーを出さない
    if _has_punch_leak_alert(result):
        logger.info(f"退勤時刻: 打刻漏れエラーが既に存在するため、時刻差異エラーをスキップ")
        return
    
    if not (schedule_end and actual_end and not is_night_shift_day and not is_24hour_or_night_shift(work_type)):
        logger.debug(f"退勤時刻差異チェックスキップ: schedule_end={schedule_end}, actual_end={actual_end}, is_night_shift_day={is_night_shift_day}, work_type={work_type}")
        return
    
    diff_end = calculate_time_diff_minutes(schedule_end, actual_end)
    if diff_end is None:
        logger.debug(f"退勤時刻差異計算失敗: schedule_end={schedule_end}, actual_end={actual_end}")
        return
    
    adjusted_diff_end = diff_end + early_adjust
    logger.info(f"退勤時刻差異計算: スケジュール={schedule_end}, 実際={actual_end}, diff_end={diff_end}分, early_adjust={early_adjust}分, adjusted_diff_end={adjusted_diff_end}分, 時間外申告件数={len(overtime_apps)}, skip_diff={skip_diff}")
    
    # 打刻1回のみで終了時間に近い場合はスキップ
    if skip_diff:
        logger.info(f"退勤時刻: 打刻1回のみで終了時間に近いため、エラーをスキップ: 打刻={actual_end}")
        return
    
    # 時間外申告の開始時間または終了時間と退勤打刻時間が±15分以内かチェック
    if _check_overtime_time_within_tolerance(actual_end, overtime_apps):
        logger.info(f"退勤時刻: 時間外申告の開始時間または終了時間と打刻時間が±15分以内のため、エラーをスキップ: 打刻={actual_end}")
        return
    
    # 退勤時刻が遅い場合（時間外勤務の可能性）
    if diff_end > 0:
        has_overtime_for_time = _check_overtime_coverage(schedule_end, actual_end, overtime_apps)
        logger.info(f"退勤時刻が遅い場合のチェック: diff_end={diff_end}分, has_overtime_for_time={has_overtime_for_time}, adjusted_diff_end={adjusted_diff_end}分, 閾値={AttendanceConstants.TIME_DIFF_THRESHOLD}分")
        
        # 時間外申告がない場合のみエラーを出す
        if not has_overtime_for_time and abs(adjusted_diff_end) >= AttendanceConstants.TIME_DIFF_THRESHOLD:
            logger.info(f"退勤時刻差異エラー追加: 差異={adjusted_diff_end}分 (閾値={AttendanceConstants.TIME_DIFF_THRESHOLD}分)")
            _add_alert(result, AttendanceConstants.ALERT_WARNING,
                      AttendanceConstants.MSG_CLOCK_OUT_TIME_DIFF,
                      AttendanceConstants.DETAIL_CLOCK_OUT_TIME_DIFF.format(
                          schedule=schedule_end, actual=actual_end,
                          diff=diff_end, adjusted_diff=adjusted_diff_end))
        else:
            logger.info(f"退勤時刻差異: エラーなし (has_overtime_for_time={has_overtime_for_time}, adjusted_diff_end={adjusted_diff_end}分)")
    # 退勤時刻が早い場合（早退）
    elif diff_end < 0:
        logger.info(f"退勤時刻が早い場合のチェック: diff_end={diff_end}分, adjusted_diff_end={adjusted_diff_end}分, 閾値={AttendanceConstants.TIME_DIFF_THRESHOLD}分")
        if abs(adjusted_diff_end) >= AttendanceConstants.TIME_DIFF_THRESHOLD:
            logger.info(f"退勤時刻差異エラー追加: 差異={adjusted_diff_end}分 (閾値={AttendanceConstants.TIME_DIFF_THRESHOLD}分)")
            _add_alert(result, AttendanceConstants.ALERT_WARNING,
                      AttendanceConstants.MSG_CLOCK_OUT_TIME_DIFF,
                      AttendanceConstants.DETAIL_CLOCK_OUT_TIME_DIFF.format(
                          schedule=schedule_end, actual=actual_end,
                          diff=diff_end, adjusted_diff=adjusted_diff_end))
        else:
            logger.info(f"退勤時刻差異: 差異={adjusted_diff_end}分は閾値未満のためエラーなし")

def _check_overtime_time_within_tolerance(clock_time: str, overtime_apps: List[Dict]) -> bool:
    """時間外申告の開始時間または終了時間と打刻時間が±15分以内かチェック"""
    if not clock_time:
        logger.debug(f"時間外申告チェック: 打刻時間がNoneのためスキップ")
        return False
    
    if not overtime_apps:
        logger.debug(f"時間外申告チェック: 時間外申告が0件のためスキップ (打刻時間={clock_time})")
        return False
    
    clock_minutes = time_to_minutes(clock_time)
    if clock_minutes is None:
        logger.debug(f"時間外申告チェック: 打刻時間の変換失敗 (打刻時間={clock_time})")
        return False
    
    logger.info(f"時間外申告チェック開始: 打刻時間={clock_time}, 時間外申告件数={len(overtime_apps)}")
    
    for app in overtime_apps:
        app_start = app.get('start_time')
        app_end = app.get('end_time')
        
        if app_start:
            app_start_minutes = time_to_minutes(app_start)
            if app_start_minutes is not None:
                time_diff = abs(app_start_minutes - clock_minutes)
                logger.info(f"時間外申告開始時間チェック: 開始時間={app_start}, 打刻時間={clock_time}, 差異={time_diff}分 (閾値={AttendanceConstants.TOLERANCE_MINUTES}分)")
                if time_diff <= AttendanceConstants.TOLERANCE_MINUTES:
                    logger.info(f"✓ 時間外申告開始時間と打刻時間が±15分以内: 開始時間={app_start}, 打刻時間={clock_time}, 差異={time_diff}分")
                    return True
        
        if app_end:
            app_end_minutes = time_to_minutes(app_end)
            if app_end_minutes is not None:
                time_diff = abs(app_end_minutes - clock_minutes)
                logger.info(f"時間外申告終了時間チェック: 終了時間={app_end}, 打刻時間={clock_time}, 差異={time_diff}分 (閾値={AttendanceConstants.TOLERANCE_MINUTES}分)")
                if time_diff <= AttendanceConstants.TOLERANCE_MINUTES:
                    logger.info(f"✓ 時間外申告終了時間と打刻時間が±15分以内: 終了時間={app_end}, 打刻時間={clock_time}, 差異={time_diff}分")
                    return True
    
    logger.info(f"時間外申告チェック完了: 打刻時間={clock_time}は時間外申告の開始時間・終了時間と±15分以内ではない")
    return False

def _check_overtime_coverage(schedule_end: str, actual_end: str, overtime_apps: List[Dict]) -> bool:
    """時間外申告が実際の残業時間をカバーしているかチェック"""
    schedule_end_minutes = time_to_minutes(schedule_end)
    actual_end_minutes = time_to_minutes(actual_end)
    
    if schedule_end_minutes is None or actual_end_minutes is None:
        return False
    
    return _check_overtime_overlap(schedule_end_minutes, actual_end_minutes, overtime_apps)

def check_off_day_shift_attendance(cursor, result: AttendanceCheckResult, prev_date: str) -> None:
    """明勤務の前日24勤・夜勤チェック"""
    work_type = result.schedule['work_type'] if result.schedule else None
    if not is_off_day_shift(work_type):
        return
    
    # 前日の24勤・夜勤スケジュールがない場合の警告
    if not result.prev_day_night_shift and result.attendance_records:
        _add_alert(result, AttendanceConstants.ALERT_WARNING,
                  AttendanceConstants.MSG_OFF_DAY_NO_PREV_SHIFT,
                  f'前日({prev_date})のスケジュールを確認してください')
        return
    
    # 前日の24勤・夜勤の退勤時刻と「明」勤務の打刻時刻の差異をチェック
    if result.prev_day_night_shift:
        prev_schedule_end = result.prev_day_night_shift.get('end_time')
        actual_end = result.actual_clock_out  # 「明」勤務の日の打刻時刻（前日の退勤時刻）
        
        if prev_schedule_end and actual_end:
            from database import get_early_leave_requests
            
            diff_end = calculate_time_diff_minutes(prev_schedule_end, actual_end)
            if diff_end is not None:
                # 「明」勤務の日の早退申告を取得（前日の24勤・夜勤の早退申告として扱う）
                early_leave_requests = get_early_leave_requests(
                    employee_num=result.employee_num,
                    work_date=result.check_date,
                    status=AttendanceConstants.STATUS_APPROVED
                )
                early_adjust = sum(req['early_minutes'] for req in early_leave_requests)
                adjusted_diff_end = diff_end + early_adjust
                
                logger.info(f"「明」勤務退勤時刻差異: 前日スケジュール={prev_schedule_end}, 実際={actual_end}, diff={diff_end}分, early_adjust={early_adjust}分, adjusted_diff={adjusted_diff_end}分, 閾値={AttendanceConstants.TIME_DIFF_THRESHOLD}分")
                
                if abs(adjusted_diff_end) >= AttendanceConstants.TIME_DIFF_THRESHOLD:
                    _add_alert(result, AttendanceConstants.ALERT_WARNING,
                              AttendanceConstants.MSG_CLOCK_OUT_TIME_DIFF,
                              AttendanceConstants.DETAIL_CLOCK_OUT_TIME_DIFF.format(
                                  schedule=prev_schedule_end,
                                  actual=actual_end,
                                  diff=diff_end,
                                  adjusted_diff=adjusted_diff_end))
        elif prev_schedule_end and not actual_end:
            # 「明」勤務の日の打刻がない場合（前日の24勤・夜勤の退勤打刻がない）
            _add_alert(result, AttendanceConstants.ALERT_ERROR,
                      AttendanceConstants.MSG_CLOCK_OUT_PUNCH_LEAK,
                      AttendanceConstants.DETAIL_CLOCK_OUT_MISSING.format(schedule=prev_schedule_end))

def check_attendance_vs_schedule(employee_id: str, check_date: str) -> Dict[str, Any]:
    """
    勤怠スケジュールと打刻実績の差異をチェック
    （リファクタリング版 - 関数を小さく分割）
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. 従業員情報取得
            emp_info = get_employee_info(cursor, employee_id)
            if not emp_info:
                return {
                    'status': 'error',
                    'message': f'従業員ID {employee_id} が見つかりません'
                }
            
            employee_num, employee_name, idm = emp_info
            result = AttendanceCheckResult(employee_num, employee_name, check_date)
            
            # 2. スケジュール情報取得
            schedule_row = get_schedule_info(cursor, employee_id, check_date)
            if schedule_row:
                result.schedule = {
                    'id': schedule_row[0],
                    'work_date': schedule_row[1],
                    'work_type': schedule_row[2],
                    'start_time': schedule_row[3],
                    'end_time': schedule_row[4]
                }
            
            # 3. 打刻記録取得・整形
            attendance_rows = get_attendance_records(cursor, idm, check_date)
            for att_row in attendance_rows:
                timestamp_str = att_row[1]
                time_only = extract_time_from_timestamp(timestamp_str)
                
                result.attendance_records.append({
                    'id': att_row[0],
                    'time': time_only,
                    'timestamp': timestamp_str,
                    'terminal_id': att_row[2]
                })
            
            # 4. 前日の24勤・夜勤情報取得
            prev_date = (datetime.strptime(check_date, AttendanceConstants.DATE_FORMAT) - timedelta(days=1)).strftime(AttendanceConstants.DATE_FORMAT)
            prev_shift = get_prev_day_night_shift(cursor, employee_id, prev_date)
            if prev_shift:
                result.prev_day_night_shift = {
                    'work_date': prev_shift[0],
                    'work_type': prev_shift[1],
                    'start_time': prev_shift[2],
                    'end_time': prev_shift[3]
                }
            
            # 5. 実際の出退勤時刻計算
            calculate_actual_clock_times(result, cursor)
            
            # 6. 各種エラーチェック
            check_holiday_punch_errors(result)
            check_missing_punch_errors(result)
            check_holiday_work_errors(result)
            check_leave_request_conflicts(result)
            check_off_day_shift_attendance(cursor, result, prev_date)
            
            # 7. 遅刻・早退調整の取得と時刻差異チェック
            late_adjust, early_adjust = get_late_early_adjustments(result)
            check_time_difference_errors(result, late_adjust, early_adjust)
            
            return {
                'status': 'success',
                'data': result.to_dict()
            }
            
    except Exception as e:
        logger.error(f"勤怠チェックエラー: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f'チェックエラー: {str(e)}'
        }

def get_night_shift_end_time_from_next_day(cursor, employee_id: str, work_date: str) -> Optional[str]:
    """
    24勤・夜勤の終了時間を翌日の「明」勤務の打刻から取得する関数
    
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
        work_date_obj = datetime.strptime(work_date, AttendanceConstants.DATE_FORMAT).date()
        next_date = (work_date_obj + timedelta(days=1)).strftime(AttendanceConstants.DATE_FORMAT)
        
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