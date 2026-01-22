#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
from datetime import datetime

db_path = '/app/data/attendance.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print('=== 13名の勤務予定（2025/12/16 - 2026/1/15）===')
    print()
    
    # 期間の定義
    start_date = '2025-12-16'
    end_date = '2026-01-15'
    
    # 従業員一覧を取得
    cursor.execute('''
        SELECT employee_num, name, section
        FROM employee_master
        ORDER BY employee_num
    ''')
    employees = cursor.fetchall()
    
    # 勤務予定を取得
    cursor.execute('''
        SELECT s.employee_num, s.schedule_date, s.work_type, e.name
        FROM attend_schedule s
        JOIN employee_master e ON s.employee_num = e.employee_num
        WHERE s.schedule_date >= ? AND s.schedule_date <= ?
        ORDER BY s.employee_num, s.schedule_date
    ''', (start_date, end_date))
    
    schedules = cursor.fetchall()
    
    # 従業員ごとに勤務予定を整理
    employee_schedules = {}
    for emp_num, name, section in employees:
        employee_schedules[emp_num] = {
            'name': name, 
            'section': section, 
            'schedules': []
        }
    
    for emp_num, schedule_date, work_type, name in schedules:
        if emp_num in employee_schedules:
            employee_schedules[emp_num]['schedules'].append({
                'date': schedule_date,
                'work_type': work_type
            })
    
    # 結果出力
    total_schedules = 0
    
    for emp_num in sorted(employee_schedules.keys()):
        emp_data = employee_schedules[emp_num]
        schedules_list = emp_data['schedules']
        
        print(f"【{emp_data['name']}】（従業員番号: {emp_num}）")
        print(f"  部署: {emp_data['section']}")
        print(f"  予定件数: {len(schedules_list)}件")
        
        if schedules_list:
            print('  勤務予定:')
            for schedule in schedules_list:
                try:
                    date_obj = datetime.strptime(schedule['date'], '%Y-%m-%d')
                    date_formatted = date_obj.strftime('%Y/%m/%d')
                    weekday = ['月', '火', '水', '木', '金', '土', '日'][date_obj.weekday()]
                    print(f"    {date_formatted}({weekday}) - {schedule['work_type']}")
                except Exception as e:
                    print(f"    {schedule['date']} - {schedule['work_type']}")
            
            # 勤務タイプ別集計
            work_type_count = {}
            for schedule in schedules_list:
                work_type = schedule['work_type']
                work_type_count[work_type] = work_type_count.get(work_type, 0) + 1
            
            print('  勤務タイプ別集計:')
            for work_type, count in work_type_count.items():
                print(f"    {work_type}: {count}件")
        else:
            print('  予定なし')
        
        print()
        total_schedules += len(schedules_list)
    
    print('=== 全体集計 ===')
    print(f"対象期間: {start_date} ～ {end_date}")
    print(f"対象従業員数: {len(employees)}名")
    print(f"総予定件数: {total_schedules}件")
    
    # 全体の勤務タイプ別集計
    cursor.execute('''
        SELECT work_type, COUNT(*) as count
        FROM attend_schedule
        WHERE schedule_date >= ? AND schedule_date <= ?
        GROUP BY work_type
        ORDER BY count DESC
    ''', (start_date, end_date))
    
    overall_work_types = cursor.fetchall()
    print()
    print('全体勤務タイプ別集計:')
    for work_type, count in overall_work_types:
        print(f"  {work_type}: {count}件")
    
    conn.close()
    
except Exception as e:
    print(f'エラー: {e}')