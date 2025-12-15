#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存の時間外申告データを新しいロジックで再計算するスクリプト
"""
import sys
sys.path.append('/app')

from overtime import calculate_overtime_categories
from database import get_db_connection

def recalculate_overtime_data():
    """既存の時間外申告データを再計算"""
    import sqlite3
    
    conn = sqlite3.connect('/app/data/attendance.db')
    cursor = conn.cursor()
    
    # 従業員3652025の12/9の時間外申告を取得
    cursor.execute("""
        SELECT id, employee_num, work_date, start_time, end_time, description
        FROM overtime_applications 
        WHERE employee_num = '3652025' AND work_date = '2025-12-09'
        ORDER BY start_time
    """)
    
    applications = cursor.fetchall()
    
    for app in applications:
        app_id, employee_num, work_date, start_time, end_time, description = app
        
        print(f"\n=== 再計算: {work_date} {start_time}-{end_time} ===")
        print(f"内容: {description}")
        
        # 新しいロジックで時間外分類を計算
        result = calculate_overtime_categories(employee_num, work_date, start_time, end_time)
        
        print(f"計算結果:")
        print(f"  分類: {result['overtime_type']}")
        print(f"  内残業: {result['inner_overtime_minutes']}分")
        print(f"  外残業: {result['outer_overtime_minutes']}分") 
        print(f"  深夜時間: {result['night_overtime_minutes']}分")
        
        # データベースを更新
        cursor.execute("""
            UPDATE overtime_applications SET 
                overtime_type = ?,
                inner_overtime_minutes = ?,
                outer_overtime_minutes = ?,
                night_overtime_minutes = ?
            WHERE id = ?
        """, (
            result['overtime_type'],
            result['inner_overtime_minutes'], 
            result['outer_overtime_minutes'],
            result['night_overtime_minutes'],
            app_id
        ))
        
        print(f"  → データベース更新完了")
    
    conn.commit()
    conn.close()
    
    print(f"\n=== 再計算完了 ===")

if __name__ == "__main__":
    recalculate_overtime_data()