#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月間集計レポート生成モジュール（シンプル版）
個人別の月間勤務実績表をExcel形式で出力
"""

from datetime import datetime, date, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
import os
from config import Config
from database import get_attendance_check_status
from attendance_check_service import check_attendance_vs_schedule
from utils import calculate_date_range, time_to_minutes, get_db_connection
from constants import AttendanceConstants
from work_type_constants import (
    is_off_day_shift,
    is_24hour_or_night_shift,
    is_holiday_shift,
    WORK_TYPE_OFF_DAY,
    WORK_TYPE_24HOUR_A,
    WORK_TYPE_24HOUR_B,
    WORK_TYPE_NIGHT
)
from logger_config import setup_logger

logger = setup_logger(__name__)

def normalize_date_to_str(date_value):
    """
    様々な形式の日付データを文字列（YYYY-MM-DD）に正規化
    
    Args:
        date_value: 日付データ（文字列、date、datetimeオブジェクトなど）
    
    Returns:
        str: YYYY-MM-DD形式の文字列、またはNone（変換できない場合）
    """
    if date_value is None:
        return None
    
    if isinstance(date_value, str):
        # 文字列の場合は、そのまま返す（既にYYYY-MM-DD形式と仮定）
        return date_value
    elif isinstance(date_value, date):
        # dateオブジェクトの場合は文字列に変換
        return date_value.isoformat()
    elif isinstance(date_value, datetime):
        # datetimeオブジェクトの場合は日付部分のみを文字列に変換
        return date_value.date().isoformat()
    else:
        # その他の場合は文字列に変換を試行
        try:
            return str(date_value)
        except:
            return None

def get_monthly_attendance_data(employee_id, search_month):
    """
    従業員の月間勤怠データを取得
    
    Args:
        employee_id: 従業員番号
        search_month: 検索月（YYYY/MM形式）
    
    Returns:
        dict: 月間データ
    """
    try:
        start_date, end_date = calculate_date_range(search_month)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 従業員情報を取得
            cursor.execute("PRAGMA table_info(employee_master)")
            columns = [col[1] for col in cursor.fetchall()]
            has_workplace = 'workplace' in columns
            
            if has_workplace:
                cursor.execute("""
                    SELECT employee_num, name, section, workplace
                    FROM employee_master
                    WHERE employee_num = ?
                """, (employee_id,))
            else:
                cursor.execute("""
                    SELECT employee_num, name, section
                    FROM employee_master
                    WHERE employee_num = ?
                """, (employee_id,))
            
            employee_row = cursor.fetchone()
            if not employee_row:
                return None
        
            if has_workplace:
                employee_info = {
                    'employee_num': employee_row[0],
                    'name': employee_row[1],
                    'section': employee_row[2] or '',
                    'workplace': employee_row[3] or '奈良県医療総合センター'
                }
            else:
                employee_info = {
                    'employee_num': employee_row[0],
                    'name': employee_row[1],
                    'section': employee_row[2] or '',
                    'workplace': '奈良県医療総合センター'  # デフォルト値
                }
            
            # スケジュールデータを取得
            # start_dateの前日（例：12月度なら11月15日）から取得（start_dateが「明」の場合、前日の終了時間を設定するため）
            # end_dateの前日（例：12月度なら12月14日）も取得（15日が「明」の場合、14日の終了時間を設定するため）
            start_date_obj = datetime.strptime(start_date, AttendanceConstants.DATE_FORMAT).date()
            end_date_obj = datetime.strptime(end_date, AttendanceConstants.DATE_FORMAT).date()
            prev_day = (start_date_obj - timedelta(days=1)).strftime(AttendanceConstants.DATE_FORMAT)
            prev_day_of_end = (end_date_obj - timedelta(days=1)).strftime(AttendanceConstants.DATE_FORMAT)
            
            cursor.execute("""
                SELECT work_date, work_type, start_time, end_time
                FROM attend_schedule
                WHERE employee_id = ?
                AND work_date >= ?
                AND work_date <= ?
                ORDER BY work_date ASC
            """, (employee_id, prev_day, end_date))
            
            schedule_rows = cursor.fetchall()
            
            # 15日のデータを取得（15日が「明」の場合、14日の終了時間を設定するため）
            cursor.execute("""
                SELECT work_date, work_type, start_time, end_time
                FROM attend_schedule
                WHERE employee_id = ?
                AND work_date = ?
            """, (employee_id, end_date))
            
            day15_row = cursor.fetchone()
            
            # 打刻データを取得
            # まず従業員のIDmを取得
            cursor.execute("SELECT idm FROM employee_master WHERE employee_num = ?", (employee_id,))
            idm_row = cursor.fetchone()
            idm_list = []
            if idm_row:
                idm_list = [idm_row[0]]
            
            attendance_rows = []
            if idm_list:
                cursor.execute("""
                    SELECT DATE(timestamp) as work_date, TIME(timestamp) as clock_time, terminal_id
                    FROM attendance
                    WHERE idm = ?
                    AND DATE(timestamp) >= ?
                    AND DATE(timestamp) <= ?
                    ORDER BY timestamp ASC
                """, (idm_list[0], start_date, end_date))
                attendance_rows = cursor.fetchall()
            
            # 時間外申告データを取得（日付を正規化、作業内容も含める）
            # COALESCEを使用してNULLの場合は空文字列に変換
            # 注意: DATE()関数を使うと列の順序が変わる可能性があるため、明示的に列を指定
            cursor.execute("""
                SELECT 
                    DATE(work_date) as work_date, 
                    start_time, 
                    end_time, 
                    inner_overtime_minutes,
                    outer_overtime_minutes, 
                    night_overtime_minutes, 
                    COALESCE(description, '') as description
                FROM overtime_applications
                WHERE employee_num = ?
                AND DATE(work_date) >= DATE(?)
                AND DATE(work_date) <= DATE(?)
                AND status = 'approved'
                ORDER BY work_date ASC
            """, (employee_id, start_date, end_date))
            
            overtime_rows = cursor.fetchall()
            
            # 休暇願データを取得（承認済みのみ）
            cursor.execute("""
                SELECT 
                    DATE(leave_date_from) as leave_date_from,
                    DATE(leave_date_to) as leave_date_to,
                    leave_type,
                    leave_subtype
                FROM leave_requests
                WHERE employee_num = ?
                AND status = 'approved'
                AND (
                    (DATE(leave_date_from) >= DATE(?) AND DATE(leave_date_from) <= DATE(?))
                    OR (DATE(leave_date_to) >= DATE(?) AND DATE(leave_date_to) <= DATE(?))
                    OR (DATE(leave_date_from) <= DATE(?) AND DATE(leave_date_to) >= DATE(?))
                )
                ORDER BY leave_date_from ASC
            """, (employee_id, start_date, end_date, start_date, end_date, start_date, end_date))
            
            leave_rows = cursor.fetchall()
            
            # 日付ごとのデータを整理
            daily_data = {}
            start = datetime.strptime(start_date, AttendanceConstants.DATE_FORMAT).date()
            end = datetime.strptime(end_date, AttendanceConstants.DATE_FORMAT).date()
            
            current = start
            while current <= end:
                daily_data[current.isoformat()] = {
                    'date': current,
                    'work_type': None,
                    'start_time': None,
                    'end_time': None,
                    'clock_times': [],
                    'overtime': {
                        'outer': 0,
                        'inner': 0,
                        'night': 0,
                        'transportation_fee': 0,
                        'applications': []  # 時間外申告の詳細リスト
                    },
                    'leave_request': None  # 休暇願情報（Noneまたは辞書）
                }
                current += timedelta(days=1)
            
            # スケジュールデータを設定
            for row in schedule_rows:
                date_str = normalize_date_to_str(row[0])
                if not date_str:
                    continue
                
                if date_str in daily_data:
                    daily_data[date_str]['work_type'] = row[1]
                    daily_data[date_str]['start_time'] = row[2]
                    daily_data[date_str]['end_time'] = row[3]
            
            # 打刻データを設定
            for row in attendance_rows:
                date_str = normalize_date_to_str(row[0])
                if not date_str:
                    continue
                
                if date_str in daily_data:
                    clock_time = row[1]
                    if isinstance(clock_time, str):
                        # HH:MM:SS形式からHH:MM形式に変換
                        clock_time = ':'.join(clock_time.split(':')[:2])
                    daily_data[date_str]['clock_times'].append(clock_time)
            
            # 時間外申告データを設定
            for row in overtime_rows:
                work_date_raw = row[0]
                date_str = normalize_date_to_str(work_date_raw)
                
                if not date_str or date_str not in daily_data:
                    continue
                
                # 時間外申告の詳細を保存
                start_time = row[1]  # HH:MM形式
                end_time = row[2]    # HH:MM形式
                inner_minutes_db = row[3] or 0  # データベースから読み込んだ値（分）
                outer_minutes_db = row[4] or 0
                night_minutes_db = row[5] or 0
                inner_minutes = inner_minutes_db / 60  # 分→時間
                outer_minutes = outer_minutes_db / 60
                night_minutes = night_minutes_db / 60
                # 作業内容を取得（row[6]が存在する場合）
                description = ''
                if len(row) > 6:
                    description = row[6] or ''
                
                # デバッグ出力：データベースから読み込んだ値
                logger.info(f"[時間外申告データ読み込み] 日付={date_str}, 時間={start_time}-{end_time}, DB値: inner={inner_minutes_db}分({inner_minutes:.2f}h), outer={outer_minutes_db}分({outer_minutes:.2f}h), night={night_minutes_db}分({night_minutes:.2f}h)")
                
                # 時間外申告の詳細をリストに追加
                app_data = {
                    'start_time': start_time,
                    'end_time': end_time,
                    'inner': inner_minutes,
                    'outer': outer_minutes,
                    'night': night_minutes,
                    'description': description  # 作業内容を追加
                }
                daily_data[date_str]['overtime']['applications'].append(app_data)
                
                # 複数の時間外申告がある場合は合計する
                daily_data[date_str]['overtime']['outer'] += outer_minutes
                daily_data[date_str]['overtime']['inner'] += inner_minutes
                daily_data[date_str]['overtime']['night'] += night_minutes
            
            # 休暇願データを設定
            for row in leave_rows:
                leave_date_from_str = normalize_date_to_str(row[0])
                leave_date_to_str = normalize_date_to_str(row[1])
                leave_type = row[2] or ''
                leave_subtype = row[3] or ''
                
                if not leave_date_from_str or not leave_date_to_str:
                    continue
                
                # 休暇期間の各日付に休暇願情報を設定
                try:
                    from_date = datetime.strptime(leave_date_from_str, AttendanceConstants.DATE_FORMAT).date()
                    to_date = datetime.strptime(leave_date_to_str, AttendanceConstants.DATE_FORMAT).date()
                    
                    current_leave_date = from_date
                    while current_leave_date <= to_date:
                        date_str = current_leave_date.isoformat()
                        if date_str in daily_data:
                            # 休暇願情報を設定（既に設定されている場合は上書きしない）
                            if daily_data[date_str]['leave_request'] is None:
                                daily_data[date_str]['leave_request'] = {
                                    'leave_type': leave_type,
                                    'leave_subtype': leave_subtype
                                }
                        current_leave_date += timedelta(days=1)
                except Exception:
                    pass
            
            # dateオブジェクトを文字列に変換（JSONシリアライズ対応）
            for date_str, day_data in daily_data.items():
                if isinstance(day_data.get('date'), date):
                    day_data['date'] = day_data['date'].isoformat()
            
            # 各日付に対してアラート情報と確認状況を取得
            for date_str, day_data in daily_data.items():
                try:
                    check_result = check_attendance_vs_schedule(employee_id, date_str)
                    if check_result.get('status') == 'success' and check_result.get('data'):
                        alerts = check_result['data'].get('alerts', [])
                        day_data['alerts'] = alerts
                        if alerts:
                            logger.debug(f"アラート取得: {date_str} - {len(alerts)}件")
                    else:
                        day_data['alerts'] = []
                    
                    # 確認状況を取得（3つのチェックタイプ）
                    check_statuses = {}
                    for check_type in ['missing_punch', 'time_difference', 'punch_leak']:
                        try:
                            status = get_attendance_check_status(employee_id, date_str, check_type)
                            if status and status.get('is_checked'):
                                check_statuses[check_type] = True
                            else:
                                check_statuses[check_type] = False
                        except Exception as e:
                            logger.warning(f"確認状況取得エラー ({date_str}, {check_type}): {e}")
                            check_statuses[check_type] = False
                    day_data['check_statuses'] = check_statuses
                except Exception as e:
                    logger.warning(f"アラート取得エラー ({date_str}): {e}")
                    day_data['alerts'] = []
                    day_data['check_statuses'] = {'missing_punch': False, 'time_difference': False, 'punch_leak': False}
            
            return {
                'employee_info': employee_info,
                'search_month': search_month,
                'start_date': start_date,
                'end_date': end_date,
                'daily_data': daily_data
            }
        
    except Exception as e:
        logger.error(f"月間データ取得エラー: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return None

def generate_monthly_report_excel(employee_id, search_month, output_path=None):
    """
    月間集計レポートをExcel形式で生成（完全シンプル版）
    
    Args:
        employee_id: 従業員番号
        search_month: 検索月（YYYY/MM形式）
        output_path: 出力ファイルパス（Noneの場合は一時ファイル）
    
    Returns:
        str: 生成されたファイルパス
    """
    try:
        logger.info(f"月間レポート生成開始: 従業員ID={employee_id}, 検索月={search_month}")
        
        # データ取得
        data = get_monthly_attendance_data(employee_id, search_month)
        if not data:
            error_msg = f"従業員 {employee_id} のデータが見つかりません"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"データ取得成功: {len(data.get('daily_data', {}))}日分のデータ")
        
        # 出力パス設定
        if not output_path:
            if Config.PDF_SAVE_DIR:
                output_dir = Config.PDF_SAVE_DIR.replace('PDF', 'reports')
            else:
                db_dir = os.path.dirname(Config.DATABASE_PATH)
                output_dir = os.path.join(db_dir, 'reports')
            
            os.makedirs(output_dir, exist_ok=True)
            logger.debug(f"出力ディレクトリ: {output_dir}")
            
            employee_num = data['employee_info']['employee_num']
            employee_name = data['employee_info']['name']
            # ファイル名に使用できない文字を除去
            safe_name = employee_name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
            filename = f"勤務実績表_{employee_num}_{safe_name}_{search_month.replace('/', '')}.xlsx"
            output_path = os.path.join(output_dir, filename)
        
        # Excelワークブック作成（完全シンプル）
        wb = Workbook()
        ws = wb.active
        ws.title = "勤務実績表"
        
        # ヘッダー情報（シンプル）
        row = 1
        cell1 = ws.cell(row=row, column=1, value=f"{search_month}月度 勤務実績表")
        cell1.font = Font(name='游ゴシック', size=10)
        cell2 = ws.cell(row=row, column=4, value=f"社員番号: {data['employee_info']['employee_num']}")
        cell2.font = Font(name='游ゴシック', size=10)
        cell3 = ws.cell(row=row, column=7, value=f"社員名: {data['employee_info']['name']}")
        cell3.font = Font(name='游ゴシック', size=10)
        
        row += 1
        cell4 = ws.cell(row=row, column=1, value=f"勤務先: {data['employee_info']['workplace']}")
        cell4.font = Font(name='游ゴシック', size=10)
        cell5 = ws.cell(row=row, column=4, value=f"期間: {data['start_date']} 〜 {data['end_date']}")
        cell5.font = Font(name='游ゴシック', size=10)
        
        # テーブルヘッダー
        row += 2
        headers = ['日付', '区分', '開始', '終了', '出勤', '退勤', '警告', '確認', '時間外', '休暇']
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=header)
            cell.font = Font(name='游ゴシック', size=10)
        
        # データ行
        row += 1
        daily_data = data['daily_data']
        
        # 集計用の変数を初期化
        total_24hour_days = 0  # 24勤の日数
        total_day_shift_days = 0  # 日勤の日数
        total_night_shift_days = 0  # 夜勤の日数
        total_overtime_outer = 0.0  # 外残業の合計（時間）
        total_overtime_inner = 0.0  # 内残業の合計（時間）
        total_overtime_night = 0.0  # 深夜残業の合計（時間）
        
        for date_str in sorted(daily_data.keys()):
            day_data = daily_data[date_str]
            work_date = day_data['date']
            
            # 日付をdateオブジェクトに変換
            if isinstance(work_date, str):
                work_date = datetime.strptime(work_date, AttendanceConstants.DATE_FORMAT).date()
            elif not isinstance(work_date, date):
                work_date = datetime.strptime(str(work_date), AttendanceConstants.DATE_FORMAT).date()
            
            # データ設定（游ゴシック、省略形）
            # 勤務区分の省略形変換
            work_type = day_data['work_type'] or ''
            # 「通常」を「日勤」に変換
            work_type = work_type.replace('通常', '日勤')
            work_type = work_type.replace('所定休日', '所休').replace('法定休日', '法休')
            
            # 集計用：勤務区分のカウント（元のwork_typeを使用）
            original_work_type = day_data['work_type'] or ''
            if '24勤' in original_work_type:
                total_24hour_days += 1
            elif original_work_type == '通常' or original_work_type == '日勤':
                total_day_shift_days += 1
            elif '夜勤' in original_work_type:
                total_night_shift_days += 1
            
            cell1 = ws.cell(row=row, column=1, value=f"{work_date.month}/{work_date.day}")
            cell1.font = Font(name='游ゴシック', size=10)
            cell2 = ws.cell(row=row, column=2, value=work_type)
            cell2.font = Font(name='游ゴシック', size=10)
            cell3 = ws.cell(row=row, column=3, value=day_data.get('start_time') or '-')
            cell3.font = Font(name='游ゴシック', size=10)
            cell4 = ws.cell(row=row, column=4, value=day_data.get('end_time') or '-')
            cell4.font = Font(name='游ゴシック', size=10)
            
            # 打刻時間
            clock_times = day_data.get('clock_times', [])
            
            # エラー・警告（省略形に変更）
            alerts = day_data.get('alerts', [])
            alert_text = ''
            if alerts:
                alert_messages = []
                for alert in alerts:
                    msg = alert.get('message', '')
                    msg = msg.replace('出勤時刻に差異あり', '出勤差異')
                    msg = msg.replace('退勤時刻に差異あり', '退勤差異')
                    alert_messages.append(msg)
                alert_text = ', '.join(alert_messages)
            else:
                alert_text = '-'
            
            # エラーメッセージから打刻漏れを判定
            has_clock_in_leak = any('出勤打刻漏れ' in alert.get('message', '') for alert in alerts)
            has_clock_out_leak = any('退勤打刻漏れ' in alert.get('message', '') for alert in alerts)
            has_missing_punch = any('打刻漏れ' in alert.get('message', '') or '打刻なし' in alert.get('message', '') for alert in alerts)
            
            # 「明」勤務の場合は、出勤時刻は表示せず、退勤時刻のみ表示（前日の24勤・夜勤の退勤時刻として扱う）
            if original_work_type and is_off_day_shift(original_work_type):
                # 「明」勤務: 出勤列は'-'、退勤列は最初の打刻（前日の退勤時刻）
                # ただし、退勤打刻漏れの場合は'-'を表示
                cell5 = ws.cell(row=row, column=5, value='-')
                cell5.font = Font(name='游ゴシック', size=10)
                if has_clock_out_leak or has_missing_punch:
                    cell6 = ws.cell(row=row, column=6, value='-')
                else:
                    cell6 = ws.cell(row=row, column=6, value=clock_times[0] if clock_times else '-')
                cell6.font = Font(name='游ゴシック', size=10)
            else:
                # 通常勤務: 最初の打刻が出勤、最後の打刻が退勤
                # ただし、打刻漏れの場合は該当する列を'-'に設定
                if has_clock_in_leak or (has_missing_punch and not clock_times):
                    # 出勤打刻漏れまたは打刻なしの場合
                    cell5 = ws.cell(row=row, column=5, value='-')
                else:
                    # 出勤打刻がある場合
                    cell5 = ws.cell(row=row, column=5, value=clock_times[0] if clock_times else '-')
                cell5.font = Font(name='游ゴシック', size=10)
                
                if has_clock_out_leak or (has_missing_punch and len(clock_times) <= 1):
                    # 退勤打刻漏れまたは打刻が1回以下の場合
                    cell6 = ws.cell(row=row, column=6, value='-')
                else:
                    # 退勤打刻がある場合（2回以上）
                    cell6 = ws.cell(row=row, column=6, value=clock_times[-1] if len(clock_times) > 1 else '-')
                cell6.font = Font(name='游ゴシック', size=10)
            cell7 = ws.cell(row=row, column=7, value=alert_text)
            cell7.font = Font(name='游ゴシック', size=10)
            
            # 確認状況（アラートがあるエラータイプのみカウント）
            check_statuses = day_data.get('check_statuses', {})
            alerts = day_data.get('alerts', [])
            
            # アラートが存在するチェックタイプのみカウント
            error_types_with_alerts = set()
            for alert in alerts:
                message = alert.get('message', '')
                if '打刻' in message or '差異' in message:
                    if '出勤' in message or '退勤' in message:
                        error_types_with_alerts.add('punch_leak')
                    elif '差異' in message:
                        error_types_with_alerts.add('time_difference')
                    elif '打刻なし' in message or '打刻漏れ' in message:
                        error_types_with_alerts.add('missing_punch')
            
            # 実際にアラートがあるエラータイプの確認状況のみをカウント
            checked_count = 0
            for check_type in error_types_with_alerts:
                if check_statuses.get(check_type, False):
                    checked_count += 1
            
            # アラートがあるにも関わらず確認件数が0の場合は、エラータイプ数を表示
            if not checked_count and error_types_with_alerts:
                checked_count = len(error_types_with_alerts)
            
            cell8 = ws.cell(row=row, column=8, value=f"{checked_count}件" if checked_count > 0 else '-')
            cell8.font = Font(name='游ゴシック', size=10)
            
            # 時間外（内残業・外残業を区別）
            overtime = day_data.get('overtime', {})
            outer_time = overtime.get('outer', 0)
            inner_time = overtime.get('inner', 0)
            night_time = overtime.get('night', 0)
            
            # デバッグ出力：各日の時間外データ
            if outer_time > 0 or inner_time > 0 or night_time > 0:
                logger.info(f"[時間外集計デバッグ] 日付={date_str}, outer={outer_time}, inner={inner_time}, night={night_time}, 合計={outer_time + inner_time + night_time}")
            
            # 集計用：時間外の合計（データ行の表示で使用している値と同じ値をそのまま使用）
            total_overtime_outer += outer_time
            total_overtime_inner += inner_time
            total_overtime_night += night_time
            
            # デバッグ出力：累積合計
            if outer_time > 0 or inner_time > 0 or night_time > 0:
                logger.info(f"[時間外集計デバッグ] 累積合計: outer={total_overtime_outer}, inner={total_overtime_inner}, night={total_overtime_night}, 総合計={total_overtime_outer + total_overtime_inner + total_overtime_night}")
            
            # 時間外（内残業+外残業の合計値のみ表示）
            total_overtime = outer_time + inner_time
            overtime_text = f"{total_overtime:.2f}h" if total_overtime > 0 else '-'
            cell9 = ws.cell(row=row, column=9, value=overtime_text)
            cell9.font = Font(name='游ゴシック', size=10)
            
            # 休暇願
            leave_request = day_data.get('leave_request')
            leave_text = '-'
            if leave_request:
                leave_type = leave_request.get('leave_type', '')
                leave_subtype = leave_request.get('leave_subtype', '')
                leave_text = f"{leave_type} {leave_subtype}".strip()
            cell10 = ws.cell(row=row, column=10, value=leave_text)
            cell10.font = Font(name='游ゴシック', size=10)
            
            row += 1
        
        # データ行の最終行を取得
        data_end_row = row - 1
        
        # 集計行を追加
        row += 1
        summary_row = row
        
        # 細い実線の罫線スタイルを定義
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        # 中央寄せのスタイルを定義
        center_alignment = Alignment(horizontal='center', vertical='center')
        # 縮小表示のスタイルを定義
        shrink_alignment = Alignment(
            horizontal='center',
            vertical='center',
            shrink_to_fit=True
        )
        
        # 集計行のヘッダー
        ws.cell(row=summary_row, column=1, value="集計").font = Font(name='游ゴシック', size=10)
        ws.cell(row=summary_row, column=1).alignment = center_alignment
        ws.cell(row=summary_row, column=1).border = thin_border
        
        # B-H列をマージして勤務時間の集計を表示
        ws.merge_cells(f'B{summary_row}:H{summary_row}')
        
        # 勤務時間の集計（0日の勤務スタイルは表示しない）
        work_hours_parts = []
        if total_24hour_days > 0:
            work_hours_parts.append(f"24勤:{total_24hour_days}日({total_24hour_days * 16}h)")
        if total_day_shift_days > 0:
            work_hours_parts.append(f"日勤:{total_day_shift_days}日({total_day_shift_days * 8}h)")
        if total_night_shift_days > 0:
            work_hours_parts.append(f"夜勤:{total_night_shift_days}日({total_night_shift_days * 9}h)")
        
        total_work_hours = (total_24hour_days * 16) + (total_day_shift_days * 8) + (total_night_shift_days * 9)
        work_hours_text = f"{' '.join(work_hours_parts)} 合計:{total_work_hours}h" if work_hours_parts else "合計:0h"
        
        cell_b = ws.cell(row=summary_row, column=2, value=work_hours_text)
        cell_b.font = Font(name='游ゴシック', size=10)
        cell_b.alignment = center_alignment
        
        # マージされたセルの罫線を設定（各セルに個別に設定）
        # B列（左端）：左、上、下の罫線
        cell_b_left = ws.cell(row=summary_row, column=2)
        cell_b_left.border = Border(
            left=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        # C列、D列、E列、F列、G列（中間）：上、下の罫線
        for col_idx in [3, 4, 5, 6, 7]:
            cell_mid = ws.cell(row=summary_row, column=col_idx)
            cell_mid.border = Border(
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
        # H列（右端）：右、上、下の罫線
        cell_h = ws.cell(row=summary_row, column=8)
        cell_h.border = Border(
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # 時間外の集計（内残業と外残業を区別して表示）
        # データ行の表示で使用している値と同じ値をそのまま合計しているため、単純に足し算する
        total_overtime_hours = total_overtime_outer + total_overtime_inner + total_overtime_night
        # デバッグ出力：最終集計結果
        logger.info(f"[時間外集計デバッグ] 最終集計: outer={total_overtime_outer}, inner={total_overtime_inner}, night={total_overtime_night}, 総合計={total_overtime_hours}, 表示値={total_overtime_hours:.2f}")
        
        # 集計行の時間外表示（内残業+外残業の合計値のみ）
        total_overtime_summary = total_overtime_outer + total_overtime_inner
        overtime_summary_text = f"{total_overtime_summary:.2f}h" if total_overtime_summary > 0 else ""
        
        # I列（時間外列）に値を設定（縮小表示に設定）
        cell_overtime = ws.cell(row=summary_row, column=9, value=overtime_summary_text)
        cell_overtime.font = Font(name='游ゴシック', size=10)
        cell_overtime.alignment = shrink_alignment  # 縮小表示に設定
        cell_overtime.border = thin_border
        
        # 集計行のI列とJ列にも罫線を設定
        for col_idx in [10]:
            cell = ws.cell(row=summary_row, column=col_idx)
            cell.border = thin_border
            cell.alignment = center_alignment
        
        # データ行のスタイル適用（4行目からデータ最終行まで）
        for row_idx in range(4, data_end_row + 1):
            for col_idx in range(1, 11):  # A-J列（列1-10）
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.alignment = center_alignment
                cell.border = thin_border
        
        # G列（警告列）とI列（時間外列）を縮小して表示に設定（データ行のみ）
        for row_idx in range(4, data_end_row + 1):  # 4行目からデータ最終行まで
            cell_g = ws.cell(row=row_idx, column=7)  # G列（列7：警告列）
            cell_g.alignment = shrink_alignment
            cell_i = ws.cell(row=row_idx, column=9)  # I列（列9：時間外列）
            cell_i.alignment = shrink_alignment
        
        # A-J列の幅を8.2に設定
        for col_letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']:
            ws.column_dimensions[col_letter].width = 8.2
        
        # 時間外申告と休暇申告の詳細を追加
        row += 3  # 空行を追加
        
        # 時間外申告セクション
        row += 1
        header_cell = ws.cell(row=row, column=1, value="時間外申告")
        header_cell.font = Font(name='游ゴシック', size=10, bold=True)
        header_cell.alignment = Alignment(horizontal='left', vertical='center')
        
        # 時間外申告ヘッダー
        row += 1
        overtime_headers = ['日付', '開始時間', '終了時間', '内残業', '外残業', '深夜', '作業内容']
        for col_idx, header in enumerate(overtime_headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=header)
            cell.font = Font(name='游ゴシック', size=10, bold=True)
            cell.alignment = center_alignment
            cell.border = thin_border
        
        # 時間外申告データを取得して表示
        with get_db_connection() as conn:
            cursor = conn.cursor()
            start_date, end_date = calculate_date_range(search_month)
            
            cursor.execute("""
                SELECT 
                    DATE(work_date) as work_date, 
                    start_time, 
                    end_time, 
                    inner_overtime_minutes,
                    outer_overtime_minutes, 
                    night_overtime_minutes, 
                    COALESCE(description, '') as description
                FROM overtime_applications
                WHERE employee_num = ?
                AND DATE(work_date) >= DATE(?)
                AND DATE(work_date) <= DATE(?)
                AND status = 'approved'
                ORDER BY work_date ASC
            """, (employee_id, start_date, end_date))
            
            overtime_rows = cursor.fetchall()
            
            if overtime_rows:
                for overtime_row in overtime_rows:
                    row += 1
                    work_date_raw = overtime_row[0]
                    if isinstance(work_date_raw, str):
                        work_date_obj = datetime.strptime(work_date_raw, AttendanceConstants.DATE_FORMAT).date()
                    else:
                        work_date_obj = work_date_raw
                    
                    ws.cell(row=row, column=1, value=f"{work_date_obj.month}/{work_date_obj.day}").font = Font(name='游ゴシック', size=10)
                    ws.cell(row=row, column=2, value=overtime_row[1] or '-').font = Font(name='游ゴシック', size=10)
                    ws.cell(row=row, column=3, value=overtime_row[2] or '-').font = Font(name='游ゴシック', size=10)
                    ws.cell(row=row, column=4, value=f"{(overtime_row[3] or 0) / 60:.2f}h" if overtime_row[3] else '-').font = Font(name='游ゴシック', size=10)
                    ws.cell(row=row, column=5, value=f"{(overtime_row[4] or 0) / 60:.2f}h" if overtime_row[4] else '-').font = Font(name='游ゴシック', size=10)
                    
                    # 深夜時間は赤文字で表示
                    night_cell = ws.cell(row=row, column=6, value=f"{(overtime_row[5] or 0) / 60:.2f}h" if overtime_row[5] else '-')
                    night_cell.font = Font(name='游ゴシック', size=10, color='FF0000')  # 赤文字
                    
                    # G列からJ列までをマージして作業内容を表示（縮小して表示）
                    ws.merge_cells(f'G{row}:J{row}')
                    cell_g = ws.cell(row=row, column=7, value=overtime_row[6] or '-')
                    cell_g.font = Font(name='游ゴシック', size=10)
                    cell_g.alignment = Alignment(horizontal='center', vertical='center', shrink_to_fit=True)  # 縮小して表示
                    
                    # マージされたセルの罫線を設定（各セルに個別に設定）
                    # G列（左端）：左、上、下の罫線
                    cell_g_left = ws.cell(row=row, column=7)
                    cell_g_left.border = Border(
                        left=Side(style='thin'),
                        top=Side(style='thin'),
                        bottom=Side(style='thin')
                    )
                    # H列、I列（中間）：上、下の罫線
                    for col_idx in [8, 9]:
                        cell_mid = ws.cell(row=row, column=col_idx)
                        cell_mid.border = Border(
                            top=Side(style='thin'),
                            bottom=Side(style='thin')
                        )
                    # J列（右端）：右、上、下の罫線
                    cell_j = ws.cell(row=row, column=10)
                    cell_j.border = Border(
                        right=Side(style='thin'),
                        top=Side(style='thin'),
                        bottom=Side(style='thin')
                    )
                    
                    # スタイル適用（A-F列）
                    for col_idx in range(1, 7):
                        cell = ws.cell(row=row, column=col_idx)
                        cell.alignment = center_alignment
                        cell.border = thin_border
            else:
                row += 1
                ws.cell(row=row, column=1, value="該当なし").font = Font(name='游ゴシック', size=10)
                ws.cell(row=row, column=1).alignment = center_alignment
                ws.cell(row=row, column=1).border = thin_border
        
        # 休暇申告セクション
        row += 2  # 空行を追加
        header_cell = ws.cell(row=row, column=1, value="休暇申告")
        header_cell.font = Font(name='游ゴシック', size=10, bold=True)
        header_cell.alignment = Alignment(horizontal='left', vertical='center')
        
        # 休暇申告ヘッダー
        row += 1
        leave_headers = ['開始日', '終了日', '休暇種類', '休暇詳細']
        for col_idx, header in enumerate(leave_headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=header)
            cell.font = Font(name='游ゴシック', size=10, bold=True)
            cell.alignment = center_alignment
            cell.border = thin_border
        
        # 休暇申告データを取得して表示
        with get_db_connection() as conn:
            cursor = conn.cursor()
            start_date, end_date = calculate_date_range(search_month)
            
            cursor.execute("""
                SELECT 
                    DATE(leave_date_from) as leave_date_from,
                    DATE(leave_date_to) as leave_date_to,
                    leave_type,
                    leave_subtype
                FROM leave_requests
                WHERE employee_num = ?
                AND status = 'approved'
                AND (
                    (DATE(leave_date_from) >= DATE(?) AND DATE(leave_date_from) <= DATE(?))
                    OR (DATE(leave_date_to) >= DATE(?) AND DATE(leave_date_to) <= DATE(?))
                    OR (DATE(leave_date_from) <= DATE(?) AND DATE(leave_date_to) >= DATE(?))
                )
                ORDER BY leave_date_from ASC
            """, (employee_id, start_date, end_date, start_date, end_date, start_date, end_date))
            
            leave_rows = cursor.fetchall()
            
            if leave_rows:
                for leave_row in leave_rows:
                    row += 1
                    leave_date_from_raw = leave_row[0]
                    leave_date_to_raw = leave_row[1]
                    
                    if isinstance(leave_date_from_raw, str):
                        leave_date_from_obj = datetime.strptime(leave_date_from_raw, AttendanceConstants.DATE_FORMAT).date()
                    else:
                        leave_date_from_obj = leave_date_from_raw
                    
                    if isinstance(leave_date_to_raw, str):
                        leave_date_to_obj = datetime.strptime(leave_date_to_raw, AttendanceConstants.DATE_FORMAT).date()
                    else:
                        leave_date_to_obj = leave_date_to_raw
                    
                    ws.cell(row=row, column=1, value=f"{leave_date_from_obj.month}/{leave_date_from_obj.day}").font = Font(name='游ゴシック', size=10)
                    ws.cell(row=row, column=2, value=f"{leave_date_to_obj.month}/{leave_date_to_obj.day}").font = Font(name='游ゴシック', size=10)
                    ws.cell(row=row, column=3, value=leave_row[2] or '-').font = Font(name='游ゴシック', size=10)
                    
                    # D列からJ列までをマージして休暇詳細を表示
                    ws.merge_cells(f'D{row}:J{row}')
                    cell_d = ws.cell(row=row, column=4, value=leave_row[3] or '-')
                    cell_d.font = Font(name='游ゴシック', size=10)
                    cell_d.alignment = center_alignment
                    
                    # マージされたセルの罫線を設定（各セルに個別に設定）
                    # D列（左端）：左、上、下の罫線
                    cell_d_left = ws.cell(row=row, column=4)
                    cell_d_left.border = Border(
                        left=Side(style='thin'),
                        top=Side(style='thin'),
                        bottom=Side(style='thin')
                    )
                    # E列、F列、G列、H列、I列（中間）：上、下の罫線
                    for col_idx in [5, 6, 7, 8, 9]:
                        cell_mid = ws.cell(row=row, column=col_idx)
                        cell_mid.border = Border(
                            top=Side(style='thin'),
                            bottom=Side(style='thin')
                        )
                    # J列（右端）：右、上、下の罫線
                    cell_j = ws.cell(row=row, column=10)
                    cell_j.border = Border(
                        right=Side(style='thin'),
                        top=Side(style='thin'),
                        bottom=Side(style='thin')
                    )
                    
                    # スタイル適用（A-C列）
                    for col_idx in range(1, 4):
                        cell = ws.cell(row=row, column=col_idx)
                        cell.alignment = center_alignment
                        cell.border = thin_border
            else:
                row += 1
                ws.cell(row=row, column=1, value="該当なし").font = Font(name='游ゴシック', size=10)
                ws.cell(row=row, column=1).alignment = center_alignment
                ws.cell(row=row, column=1).border = thin_border
        
        # ファイル保存
        wb.save(output_path)
        logger.info(f"月間レポート生成成功: {output_path}")
        return output_path
        
    except ValueError as e:
        logger.error(f"月間レポート生成エラー（データなし）: {e}")
        raise
    except Exception as e:
        logger.error(f"月間レポート生成エラー: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise