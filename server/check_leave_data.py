#!/usr/bin/env python3

from database import get_db_connection

with get_db_connection() as conn:
    cursor = conn.cursor()
    
    # 全テーブル一覧
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print('=== 利用可能なテーブル ===')
    for table in tables:
        print(table[0])
    
    print()
    print('=== 休暇申請テーブルの確認 ===')
    try:
        cursor.execute('PRAGMA table_info(leave_requests)')
        columns = cursor.fetchall()
        if columns:
            print('leave_requestsテーブル構造:')
            for col in columns:
                print(f'  {col[1]} ({col[2]})')
            
            print()
            print('=== 2025年12月の休暇申請一覧 ===')
            cursor.execute("SELECT * FROM leave_requests WHERE date LIKE '2025-12%' ORDER BY date")
            requests = cursor.fetchall()
            print(f'件数: {len(requests)}')
            for req in requests:
                print(req)
        else:
            print('leave_requestsテーブルが存在しません')
    except Exception as e:
        print(f'leave_requestsテーブルエラー: {e}')
        
    print()
    print('=== attendanceテーブルで2025/12/23のデータ確認 ===')
    try:
        cursor.execute("SELECT * FROM attendance WHERE date = '2025-12-23' ORDER BY employee_num")
        attendance_data = cursor.fetchall()
        print(f'件数: {len(attendance_data)}')
        for data in attendance_data:
            print(data)
    except Exception as e:
        print(f'attendanceテーブルエラー: {e}')