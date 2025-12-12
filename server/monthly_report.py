#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月間集計レポート生成モジュール（シンプル版）
個人別の月間勤務実績表をExcel形式で出力
"""

from datetime import datetime, date, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font
import os
from config import Config
from database import get_night_shift_end_time_from_next_day, get_attendance_check_status
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
                inner_minutes = (row[3] or 0) / 60  # 分→時間
                outer_minutes = (row[4] or 0) / 60
                night_minutes = (row[5] or 0) / 60
                # 作業内容を取得（row[6]が存在する場合）
                description = ''
                if len(row) > 6:
                    description = row[6] or ''
                
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
            
            filename = f"勤務実績表_{data['employee_info']['employee_num']}_{search_month.replace('/', '')}.xlsx"
            output_path = os.path.join(output_dir, filename)
        
        # Excelワークブック作成（完全シンプル）
        wb = Workbook()
        ws = wb.active
        ws.title = "勤務実績表"
        
        # ヘッダー情報（シンプル）
        row = 1
        cell1 = ws.cell(row=row, column=1, value=f"{search_month}月度 勤務実績表")
        cell1.font = Font(name='游ゴシック')
        cell2 = ws.cell(row=row, column=4, value=f"社員番号: {data['employee_info']['employee_num']}")
        cell2.font = Font(name='游ゴシック')
        cell3 = ws.cell(row=row, column=7, value=f"社員名: {data['employee_info']['name']}")
        cell3.font = Font(name='游ゴシック')
        
        row += 1
        cell4 = ws.cell(row=row, column=1, value=f"勤務先: {data['employee_info']['workplace']}")
        cell4.font = Font(name='游ゴシック')
        cell5 = ws.cell(row=row, column=4, value=f"期間: {data['start_date']} 〜 {data['end_date']}")
        cell5.font = Font(name='游ゴシック')
        
        # テーブルヘッダー
        row += 2
        headers = ['日付', '区分', '開始', '終了', '出勤', '退勤', '警告', '確認', '時間外', '休暇']
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=header)
            cell.font = Font(name='游ゴシック')
        
        # データ行
        row += 1
        daily_data = data['daily_data']
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
            work_type = work_type.replace('所定休日', '所休').replace('法定休日', '法休')
            
            cell1 = ws.cell(row=row, column=1, value=f"{work_date.month}/{work_date.day}")
            cell1.font = Font(name='游ゴシック')
            cell2 = ws.cell(row=row, column=2, value=work_type)
            cell2.font = Font(name='游ゴシック')
            cell3 = ws.cell(row=row, column=3, value=day_data.get('start_time') or '-')
            cell3.font = Font(name='游ゴシック')
            cell4 = ws.cell(row=row, column=4, value=day_data.get('end_time') or '-')
            cell4.font = Font(name='游ゴシック')
            
            # 打刻時間
            clock_times = day_data.get('clock_times', [])
            cell5 = ws.cell(row=row, column=5, value=clock_times[0] if clock_times else '-')
            cell5.font = Font(name='游ゴシック')
            cell6 = ws.cell(row=row, column=6, value=clock_times[-1] if len(clock_times) > 1 else '-')
            cell6.font = Font(name='游ゴシック')
            
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
            cell7 = ws.cell(row=row, column=7, value=alert_text)
            cell7.font = Font(name='游ゴシック')
            
            # 確認状況
            check_statuses = day_data.get('check_statuses', {})
            checked_count = sum(1 for status in check_statuses.values() if status)
            cell8 = ws.cell(row=row, column=8, value=f"{checked_count}件" if checked_count > 0 else '-')
            cell8.font = Font(name='游ゴシック')
            
            # 時間外（内残業・外残業を区別）
            overtime = day_data.get('overtime', {})
            outer_time = overtime.get('outer', 0)
            inner_time = overtime.get('inner', 0)
            night_time = overtime.get('night', 0)
            
            overtime_parts = []
            if outer_time > 0:
                overtime_parts.append(f"{outer_time:.1f}h外")
            if inner_time > 0:
                overtime_parts.append(f"{inner_time:.1f}h内")
            if night_time > 0:
                overtime_parts.append(f"{night_time:.1f}h夜")
            
            overtime_text = ', '.join(overtime_parts) if overtime_parts else '-'
            cell9 = ws.cell(row=row, column=9, value=overtime_text)
            cell9.font = Font(name='游ゴシック')
            
            # 休暇願
            leave_request = day_data.get('leave_request')
            leave_text = '-'
            if leave_request:
                leave_type = leave_request.get('leave_type', '')
                leave_subtype = leave_request.get('leave_subtype', '')
                leave_text = f"{leave_type} {leave_subtype}".strip()
            cell10 = ws.cell(row=row, column=10, value=leave_text)
            cell10.font = Font(name='游ゴシック')
            
            row += 1
        
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