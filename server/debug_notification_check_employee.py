#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
検証用: 特定係員のお知らせ対象を確認
「玉置　公一」係員のみを対象に、打刻漏れ・時刻差異のチェック状況を確認
"""

import sys
import os
from datetime import datetime

# パス設定
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(parent_dir)

# 作業ディレクトリをサーバーディレクトリに変更（database.pyのパス解決のため）
os.chdir(current_dir)

from database import get_db_connection, get_attendance_check_status
from attendance_check_service import check_attendance_vs_schedule
from validation_utils import calculate_date_range
from constants import AttendanceConstants

def get_check_type_from_alert(message: str) -> str:
    """アラートメッセージからcheck_typeを判定"""
    if not message:
        return None
    
    # 打刻漏れ関連
    if ('打刻漏れ' in message or 
        '打刻なし' in message or 
        '遅刻なのに退勤' in message or
        '退勤' in message and ('漏れ' in message or 'なし' in message)):
        return 'punch_leak'
    
    # 時刻差異関連
    if ('時刻に差異あり' in message or 
        '出退勤時刻に差異あり' in message or
        '出勤時刻に差異あり' in message or
        '退勤時刻に差異あり' in message):
        return 'time_difference'
    
    return None

def is_checked(employee_id: str, work_date: str, check_type: str) -> bool:
    """attendance_check_statusテーブルでチェック済みかどうかを確認"""
    try:
        status = get_attendance_check_status(employee_id, work_date, check_type)
        if status and status.get('is_checked'):
            return True
        return False
    except Exception as e:
        print(f"  警告: チェック状況取得エラー: {e}")
        return False

def main():
    """メイン処理"""
    target_employee_name = '玉置　公一'
    target_month = None  # Noneの場合は現在の月度
    
    print("=" * 80)
    print(f"検証用: {target_employee_name}係員のお知らせ対象確認")
    print("=" * 80)
    
    # 月度計算
    if target_month is None:
        today = datetime.now()
        year = today.year
        month = today.month
        day = today.day
        
        if day >= 16:
            if month == 12:
                current_payroll_month = f"{year + 1}/1"
            else:
                current_payroll_month = f"{year}/{month + 1}"
        else:
            current_payroll_month = f"{year}/{month}"
    else:
        current_payroll_month = target_month
    
    print(f"\n対象月度: {current_payroll_month}")
    
    # 期間計算
    start_date, end_date = calculate_date_range(current_payroll_month)
    print(f"チェック期間: {start_date} ～ {end_date}")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 対象係員のemployee_idを取得
        cursor.execute("""
            SELECT employee_num
            FROM employee_master
            WHERE name = ?
        """, (target_employee_name,))
        
        employee_row = cursor.fetchone()
        if not employee_row:
            print(f"\nエラー: 「{target_employee_name}」係員が見つかりません")
            return
        
        target_employee_id = employee_row[0]
        print(f"\n対象係員: {target_employee_name} (employee_id={target_employee_id})")
        
        # スケジュール取得
        cursor.execute("""
            SELECT DISTINCT employee_id, work_date
            FROM attend_schedule
            WHERE employee_id = ? AND work_date >= ? AND work_date <= ?
            ORDER BY work_date ASC
        """, (target_employee_id, start_date, end_date))
        
        schedule_data = cursor.fetchall()
        print(f"チェック対象: {len(schedule_data)}件")
        
        # 今日の日付を取得（当日以降はスキップ）
        today = datetime.now().date()
        
        checked_count = 0
        unchecked_count = 0
        no_alert_count = 0
        
        print("\n" + "-" * 80)
        print("チェック結果:")
        print("-" * 80)
        
        for employee_id, work_date in schedule_data:
            try:
                # 当日以降の日付はスキップ
                try:
                    work_date_obj = datetime.strptime(work_date, '%Y-%m-%d').date()
                    if work_date_obj >= today:
                        continue
                except (ValueError, TypeError):
                    pass
                
                # 差異チェック
                result = check_attendance_vs_schedule(str(employee_id), work_date)
                
                if result['status'] == 'success':
                    data = result['data']
                    alerts = data.get('alerts', [])
                    
                    # エラーと警告のみを対象
                    for alert in alerts:
                        if alert['type'] in ['error', 'warning']:
                            alert_message = alert.get('message', '')
                            check_type = get_check_type_from_alert(alert_message)
                            
                            if check_type:
                                is_checked_flag = is_checked(str(employee_id), work_date, check_type)
                                
                                if is_checked_flag:
                                    checked_count += 1
                                    print(f"\n[チェック済み] {work_date}: {alert_message}")
                                    print(f"  check_type={check_type}, employee_id={employee_id}")
                                else:
                                    unchecked_count += 1
                                    print(f"\n[通知対象] {work_date}: {alert_message}")
                                    print(f"  check_type={check_type}, employee_id={employee_id}")
                            else:
                                unchecked_count += 1
                                print(f"\n[通知対象（check_type判定不可）] {work_date}: {alert_message}")
                                print(f"  employee_id={employee_id}")
                    else:
                        if not alerts:
                            no_alert_count += 1
            
            except Exception as e:
                print(f"\nエラー: {work_date}のチェックでエラー: {e}")
                continue
        
        print("\n" + "=" * 80)
        print("集計結果:")
        print(f"  チェック済み（お知らせ対象外）: {checked_count}件")
        print(f"  未チェック（お知らせ対象）: {unchecked_count}件")
        print(f"  アラートなし: {no_alert_count}件")
        print(f"  合計: {checked_count + unchecked_count + no_alert_count}件")
        print("=" * 80)

if __name__ == "__main__":
    main()
