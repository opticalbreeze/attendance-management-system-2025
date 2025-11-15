#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月間集計レポート生成モジュール
個人別の月間勤務実績表をExcel形式で出力
"""

from datetime import datetime, date, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
import os
from config import Config
from database import get_database_connection, get_night_shift_end_time_from_next_day
from utils import calculate_date_range

def get_monthly_attendance_data(employee_id, search_month):
    """
    月間勤務データを取得（前月16日〜当月15日）
    
    Args:
        employee_id: 従業員番号
        search_month: 検索月（YYYY/MM形式）
    
    Returns:
        dict: 月間データ
    """
    try:
        start_date, end_date = calculate_date_range(search_month)
        
        conn = get_database_connection()
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
            conn.close()
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
        cursor.execute("""
            SELECT work_date, work_type, start_time, end_time
            FROM attend_schedule
            WHERE employee_id = ?
            AND work_date >= ?
            AND work_date <= ?
            ORDER BY work_date ASC
        """, (employee_id, start_date, end_date))
        
        schedule_rows = cursor.fetchall()
        print(f"[DEBUG] スケジュールデータ: {len(schedule_rows)}件")
        
        # 打刻データを取得
        # まず従業員のIDmを取得
        cursor.execute("SELECT idm FROM employee_master WHERE employee_num = ?", (employee_id,))
        idm_row = cursor.fetchone()
        idm_list = []
        if idm_row:
            idm_list = [idm_row[0]]
            print(f"[DEBUG] 従業員IDm: {idm_row[0]}")
        else:
            print(f"[DEBUG] 警告: 従業員番号 {employee_id} のIDmが見つかりません")
        
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
        
        print(f"[DEBUG] 打刻データ: {len(attendance_rows)}件")
        
        # 時間外申告データを取得
        cursor.execute("""
            SELECT work_date, start_time, end_time, inner_overtime_minutes,
                   outer_overtime_minutes, night_overtime_minutes
            FROM overtime_applications
            WHERE employee_num = ?
            AND work_date >= ?
            AND work_date <= ?
            AND status = 'approved'
            ORDER BY work_date ASC
        """, (employee_id, start_date, end_date))
        
        overtime_rows = cursor.fetchall()
        print(f"[DEBUG] 時間外申告データ: {len(overtime_rows)}件")
        print(f"[DEBUG] 検索期間: {start_date} 〜 {end_date}")
        
        conn.close()
        
        # 日付ごとのデータを整理
        daily_data = {}
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
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
                    'transportation_fee': 0
                }
            }
            current += timedelta(days=1)
        
        # スケジュールデータを設定
        for row in schedule_rows:
            work_date = row[0]
            if isinstance(work_date, str):
                # 複数の日付形式に対応
                try:
                    work_date = datetime.strptime(work_date, '%Y-%m-%d').date()
                except:
                    try:
                        work_date = datetime.strptime(work_date, '%Y/%m/%d').date()
                    except:
                        print(f"[DEBUG] 日付解析エラー: {work_date}")
                        continue
            elif isinstance(work_date, datetime):
                work_date = work_date.date()
            
            date_str = work_date.isoformat()
            
            if date_str in daily_data:
                daily_data[date_str]['work_type'] = row[1]
                daily_data[date_str]['start_time'] = row[2]
                daily_data[date_str]['end_time'] = row[3]
            else:
                print(f"[DEBUG] 警告: 日付 {date_str} が範囲外です")
        
        # 打刻データを設定
        for row in attendance_rows:
            work_date = row[0]
            if isinstance(work_date, str):
                try:
                    work_date = datetime.strptime(work_date, '%Y-%m-%d').date()
                except:
                    try:
                        work_date = datetime.strptime(work_date, '%Y/%m/%d').date()
                    except:
                        print(f"[DEBUG] 打刻日付解析エラー: {work_date}")
                        continue
            elif isinstance(work_date, datetime):
                work_date = work_date.date()
            
            date_str = work_date.isoformat()
            
            if date_str in daily_data:
                clock_time = row[1]
                if isinstance(clock_time, str):
                    # HH:MM:SS形式からHH:MM形式に変換
                    clock_time = ':'.join(clock_time.split(':')[:2])
                daily_data[date_str]['clock_times'].append(clock_time)
            else:
                print(f"[DEBUG] 警告: 打刻日付 {date_str} が範囲外です")
        
        # 時間外申告データを設定
        for row in overtime_rows:
            work_date = row[0]
            if isinstance(work_date, str):
                try:
                    work_date = datetime.strptime(work_date, '%Y-%m-%d').date()
                except:
                    try:
                        work_date = datetime.strptime(work_date, '%Y/%m/%d').date()
                    except:
                        print(f"[DEBUG] 時間外日付解析エラー: {work_date}")
                        continue
            elif isinstance(work_date, datetime):
                work_date = work_date.date()
            
            date_str = work_date.isoformat()
            
            if date_str in daily_data:
                daily_data[date_str]['overtime']['outer'] = (row[4] or 0) / 60  # 分→時間
                daily_data[date_str]['overtime']['inner'] = (row[3] or 0) / 60
                daily_data[date_str]['overtime']['night'] = (row[5] or 0) / 60
                daily_data[date_str]['overtime']['transportation_fee'] = 0  # カラムが存在しないため0
        
        # 24勤・夜勤の終了時間を翌日の「明」勤務に設定（共通関数を使用）
        # データベース接続を再取得（カーソルが必要）
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # 日付をソートして処理
        sorted_dates = sorted(daily_data.keys())
        for i, date_str in enumerate(sorted_dates):
            day_data = daily_data[date_str]
            work_type = day_data.get('work_type', '')
            
            # 24勤A、24勤B、夜勤の場合、終了時間を翌日の「明」勤務から取得
            if work_type and ('24勤A' in work_type or '24勤B' in work_type or '夜勤' in work_type):
                # 共通関数を使用して翌日の「明」勤務の打刻から終了時間を取得
                end_time = get_night_shift_end_time_from_next_day(cursor, employee_id, date_str)
                
                if end_time:
                    # 翌日の日付を計算
                    current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    next_date = current_date + timedelta(days=1)
                    next_date_str = next_date.isoformat()
                    
                    # 翌日のデータが存在し、かつ「明」勤務の場合
                    if next_date_str in daily_data:
                        next_day_data = daily_data[next_date_str]
                        if next_day_data.get('work_type') and '明' in next_day_data['work_type']:
                            # 翌日の「明」勤務の終了時間に設定
                            next_day_data['end_time'] = end_time
                            print(f"[DEBUG] {date_str}の{work_type}の終了時間 {end_time} を翌日{next_date_str}の「明」勤務に設定")
        
        conn.close()
        
        # デバッグ: データが存在する日付を確認
        data_exists_days = [date_str for date_str, data in daily_data.items() 
                           if data['work_type'] or data['clock_times'] or 
                           (data['overtime']['outer'] + data['overtime']['inner'] > 0)]
        print(f"[DEBUG] データが存在する日数: {len(data_exists_days)}日")
        if len(data_exists_days) == 0:
            print(f"[DEBUG] 警告: 期間内にデータが存在しません")
        
        return {
            'employee_info': employee_info,
            'search_month': search_month,
            'start_date': start_date,
            'end_date': end_date,
            'daily_data': daily_data
        }
        
    except Exception as e:
        print(f"[エラー] 月間データ取得エラー: {e}")
        import traceback
        traceback.print_exc()
        return None

def calculate_work_hours(work_type, start_time, end_time, clock_times):
    """
    勤務時間を計算
    
    Args:
        work_type: 勤務タイプ
        start_time: 開始時間
        end_time: 終了時間
        clock_times: 打刻時刻リスト
    
    Returns:
        tuple: (基準時間（時間）, 開始時刻, 終了時刻)
    """
    if not work_type:
        return (0, None, None)
    
    # 休日・休暇は0時間
    if '有' in work_type or '所' in work_type or '法' in work_type:
        return (0, None, None)
    
    # 24勤A: 3時間（終了時間は翌日の「明」勤務に表示されるため、ここではNone）
    if '24勤A' in work_type:
        return (3, clock_times[0] if clock_times else start_time, None)
    
    # 24勤B: 5時間（終了時間は翌日の「明」勤務に表示されるため、ここではNone）
    if '24勤B' in work_type:
        return (5, clock_times[0] if clock_times else start_time, None)
    
    # 夜勤: 終了時間は翌日の「明」勤務に表示されるため、ここではNone
    if '夜勤' in work_type:
        # 夜勤の基準時間は開始・終了時刻から計算、またはデフォルト値
        if start_time and end_time:
            try:
                start = datetime.strptime(start_time, '%H:%M')
                end = datetime.strptime(end_time, '%H:%M')
                if end < start:
                    end += timedelta(days=1)
                hours = (end - start).total_seconds() / 3600
                return (hours, clock_times[0] if clock_times else start_time, None)
            except:
                pass
        return (8, clock_times[0] if clock_times else start_time, None)  # デフォルト8時間
    
    # 日勤: 8時間
    if '日勤' in work_type:
        if clock_times and len(clock_times) >= 2:
            return (8, clock_times[0], clock_times[-1])
        elif start_time and end_time:
            return (8, start_time, end_time)
        else:
            return (8, start_time, end_time)
    
    # 明: 0時間（打刻のみ）
    if '明' in work_type:
        return (0, clock_times[0] if clock_times else None, clock_times[-1] if len(clock_times) > 1 else None)
    
    # その他: 開始・終了時刻から計算
    if start_time and end_time:
        try:
            start = datetime.strptime(start_time, '%H:%M')
            end = datetime.strptime(end_time, '%H:%M')
            if end < start:
                end += timedelta(days=1)
            hours = (end - start).total_seconds() / 3600
            return (hours, start_time, end_time)
        except:
            pass
    
    return (0, start_time, end_time)

def generate_monthly_report_excel(employee_id, search_month, output_path=None):
    """
    月間集計レポートをExcel形式で生成
    
    Args:
        employee_id: 従業員番号
        search_month: 検索月（YYYY/MM形式）
        output_path: 出力ファイルパス（Noneの場合は一時ファイル）
    
    Returns:
        str: 生成されたファイルパス
    """
    try:
        # データ取得
        data = get_monthly_attendance_data(employee_id, search_month)
        if not data:
            raise ValueError(f"従業員 {employee_id} のデータが見つかりません")
        
        # 出力パス設定
        if not output_path:
            output_dir = Config.PDF_SAVE_DIR.replace('PDF', 'reports')
            os.makedirs(output_dir, exist_ok=True)
            filename = f"勤務実績表_{data['employee_info']['employee_num']}_{search_month.replace('/', '')}.xlsx"
            output_path = os.path.join(output_dir, filename)
        
        # Excelワークブック作成
        wb = Workbook()
        ws = wb.active
        ws.title = "勤務実績表"
        
        # スタイル定義
        header_font = Font(name='MS Gothic', size=14, bold=True)
        title_font = Font(name='MS Gothic', size=16, bold=True)
        normal_font = Font(name='MS Gothic', size=10)
        center_align = Alignment(horizontal='center', vertical='center')
        left_align = Alignment(horizontal='left', vertical='center')
        right_align = Alignment(horizontal='right', vertical='center')
        
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        header_fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
        
        # ヘッダー情報
        row = 1
        ws.merge_cells(f'A{row}:O{row}')  # 列数をMからOに変更（15列）
        ws[f'A{row}'] = f"{search_month}月度 勤務実績表"
        ws[f'A{row}'].font = title_font
        ws[f'A{row}'].alignment = center_align
        
        row += 1
        ws[f'B{row}'] = f"社員番号: {data['employee_info']['employee_num']}"
        ws[f'B{row}'].font = header_font
        
        row += 1
        ws[f'B{row}'] = f"社員名: {data['employee_info']['name']}"
        ws[f'B{row}'].font = header_font
        
        row += 1
        ws[f'B{row}'] = f"勤務先名: {data['employee_info']['workplace']}"
        ws[f'B{row}'].font = header_font
        
        # テーブルヘッダー
        row += 2
        headers = ['日付', '区分', '開始時間（スケジュール）', '終了時間（スケジュール）', '出勤時間（打刻）', '退勤時間（打刻）', '時間外', '外深夜', '内深夜', '内深夜', '早朝', '基準', '交通費', '備考']
        for col_idx, header in enumerate(headers, start=2):  # B列から開始
            cell = ws.cell(row=row, column=col_idx)
            cell.value = header
            cell.font = header_font
            cell.alignment = center_align
            cell.fill = header_fill
            cell.border = thin_border
            # 改行を含むセルの高さを調整
            if '\n' in header:
                ws.row_dimensions[row].height = 40  # 2行分の高さに設定
        
        # データ行
        row += 1
        total_overtime = 0
        total_standard = 0
        
        daily_data = data['daily_data']
        for date_str in sorted(daily_data.keys()):
            day_data = daily_data[date_str]
            work_date = day_data['date']
            
            # 日付
            ws.cell(row=row, column=2).value = f"{work_date.month}/{work_date.day}"
            ws.cell(row=row, column=2).alignment = center_align
            ws.cell(row=row, column=2).border = thin_border
            
            # 区分
            work_type = day_data['work_type'] or ''
            ws.cell(row=row, column=3).value = work_type
            ws.cell(row=row, column=3).alignment = center_align
            ws.cell(row=row, column=3).border = thin_border
            
            # スケジュール上の開始時間・終了時間
            schedule_start = day_data.get('start_time')
            schedule_end = day_data.get('end_time')
            
            # スケジュール開始時間（列4）
            if schedule_start:
                if isinstance(schedule_start, str):
                    schedule_start_str = schedule_start[:5] if len(schedule_start) >= 5 else schedule_start
                    ws.cell(row=row, column=4).value = schedule_start_str
                else:
                    ws.cell(row=row, column=4).value = schedule_start.strftime('%H:%M')
            else:
                ws.cell(row=row, column=4).value = '-'
            ws.cell(row=row, column=4).alignment = center_align
            ws.cell(row=row, column=4).border = thin_border
            
            # スケジュール終了時間（列5）
            # 24勤・夜勤の場合は翌日の「明」勤務に表示されるため、ここでは空欄
            if work_type and ('24勤A' in work_type or '24勤B' in work_type or '夜勤' in work_type):
                ws.cell(row=row, column=5).value = '-'
            elif schedule_end:
                if isinstance(schedule_end, str):
                    schedule_end_str = schedule_end[:5] if len(schedule_end) >= 5 else schedule_end
                    ws.cell(row=row, column=5).value = schedule_end_str
                else:
                    ws.cell(row=row, column=5).value = schedule_end.strftime('%H:%M')
            else:
                ws.cell(row=row, column=5).value = '-'
            ws.cell(row=row, column=5).alignment = center_align
            ws.cell(row=row, column=5).border = thin_border
            
            # 打刻データから開始時間・終了時間を取得
            clock_times = day_data.get('clock_times', [])
            clock_start = clock_times[0] if clock_times else None
            clock_end = None
            
            # 24勤・夜勤の場合は、翌日の「明」勤務の打刻から終了時間を取得
            if work_type and ('24勤A' in work_type or '24勤B' in work_type or '夜勤' in work_type):
                # 翌日の「明」勤務の終了時間が設定されているか確認
                current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                next_date = current_date + timedelta(days=1)
                next_date_str = next_date.isoformat()
                if next_date_str in daily_data:
                    next_day_data = daily_data[next_date_str]
                    if next_day_data.get('work_type') and '明' in next_day_data['work_type']:
                        clock_end = next_day_data.get('end_time')  # 共通関数で設定された終了時間
            else:
                # 通常の場合は、その日の最後の打刻が終了時間
                clock_end = clock_times[-1] if len(clock_times) > 1 else None
            
            # 打刻開始時間（列6：出勤時間）
            if clock_start:
                clock_start_str = clock_start[:5] if len(clock_start) >= 5 else clock_start
                ws.cell(row=row, column=6).value = clock_start_str
            else:
                ws.cell(row=row, column=6).value = '-'
            ws.cell(row=row, column=6).alignment = center_align
            ws.cell(row=row, column=6).border = thin_border
            
            # 打刻終了時間（列7：退勤時間）
            if clock_end:
                clock_end_str = clock_end[:5] if len(clock_end) >= 5 else clock_end
                ws.cell(row=row, column=7).value = clock_end_str
            else:
                ws.cell(row=row, column=7).value = '-'
            ws.cell(row=row, column=7).alignment = center_align
            ws.cell(row=row, column=7).border = thin_border
            
            # 基準時間を計算（表示用）
            standard_hours, _, _ = calculate_work_hours(
                work_type,
                schedule_start,
                schedule_end,
                clock_times
            )
            
            # 時間外（列8）
            overtime_hours = day_data['overtime']['outer'] + day_data['overtime']['inner']
            if overtime_hours > 0:
                ws.cell(row=row, column=8).value = f"{int(overtime_hours)}:{int((overtime_hours % 1) * 60):02d}"
            ws.cell(row=row, column=8).alignment = center_align
            ws.cell(row=row, column=8).border = thin_border
            total_overtime += overtime_hours
            
            # 外深夜（列9）
            night_outer = day_data['overtime']['night']
            if night_outer > 0:
                ws.cell(row=row, column=9).value = f"{int(night_outer)}:{int((night_outer % 1) * 60):02d}"
            ws.cell(row=row, column=9).alignment = center_align
            ws.cell(row=row, column=9).border = thin_border
            
            # 内深夜（2列：列10, 11）
            night_inner = 0  # 内深夜は別途計算が必要
            ws.cell(row=row, column=10).value = ''
            ws.cell(row=row, column=10).alignment = center_align
            ws.cell(row=row, column=10).border = thin_border
            ws.cell(row=row, column=11).value = ''
            ws.cell(row=row, column=11).alignment = center_align
            ws.cell(row=row, column=11).border = thin_border
            
            # 早朝（列12）
            ws.cell(row=row, column=12).value = ''
            ws.cell(row=row, column=12).alignment = center_align
            ws.cell(row=row, column=12).border = thin_border
            
            # 基準（列13）
            if standard_hours > 0:
                ws.cell(row=row, column=13).value = f"{int(standard_hours)}:{int((standard_hours % 1) * 60):02d}"
            ws.cell(row=row, column=13).alignment = center_align
            ws.cell(row=row, column=13).border = thin_border
            total_standard += standard_hours
            
            # 交通費（列14）
            transportation = day_data['overtime']['transportation_fee']
            if transportation > 0:
                ws.cell(row=row, column=14).value = transportation
            ws.cell(row=row, column=14).alignment = right_align
            ws.cell(row=row, column=14).border = thin_border
            
            # 備考（列15）
            ws.cell(row=row, column=15).value = ''
            ws.cell(row=row, column=15).alignment = left_align
            ws.cell(row=row, column=15).border = thin_border
            
            # フォント設定
            for col in range(2, 16):
                ws.cell(row=row, column=col).font = normal_font
            
            row += 1
        
        # 集計行
        ws.cell(row=row, column=2).value = '計'
        ws.cell(row=row, column=2).font = header_font
        ws.cell(row=row, column=2).alignment = center_align
        ws.cell(row=row, column=2).fill = header_fill
        ws.cell(row=row, column=2).border = thin_border
        
        # 時間外合計（列8）
        ws.cell(row=row, column=8).value = f"{int(total_overtime)}:{int((total_overtime % 1) * 60):02d}"
        ws.cell(row=row, column=8).font = header_font
        ws.cell(row=row, column=8).alignment = center_align
        ws.cell(row=row, column=8).fill = header_fill
        ws.cell(row=row, column=8).border = thin_border
        
        # 基準合計（列13）
        ws.cell(row=row, column=13).value = f"{int(total_standard)}:{int((total_standard % 1) * 60):02d}"
        ws.cell(row=row, column=13).font = header_font
        ws.cell(row=row, column=13).alignment = center_align
        ws.cell(row=row, column=13).fill = header_fill
        ws.cell(row=row, column=13).border = thin_border
        
        # 列幅調整
        column_widths = {
            'B': 8,   # 日付
            'C': 10,  # 区分
            'D': 18,  # 開始時間（スケジュール）
            'E': 18,  # 終了時間（スケジュール）
            'F': 18,  # 出勤時間（打刻）
            'G': 18,  # 退勤時間（打刻）
            'H': 10,  # 時間外
            'I': 10,  # 外深夜
            'J': 10,  # 内深夜
            'K': 10,  # 内深夜
            'L': 10,  # 早朝
            'M': 10,  # 基準
            'N': 10,  # 交通費
            'O': 20   # 備考
        }
        
        for col_letter, width in column_widths.items():
            ws.column_dimensions[col_letter].width = width
        
        # ファイル保存
        wb.save(output_path)
        return output_path
        
    except Exception as e:
        print(f"[エラー] Excel生成エラー: {e}")
        import traceback
        traceback.print_exc()
        raise

