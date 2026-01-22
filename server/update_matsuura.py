#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
松浦真司の社員番号変更スクリプト
"""

from utils import get_db_connection

def check_matsuura_data():
    """松浦真司のデータを確認"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # employee_masterテーブルでの確認
            print("=== employee_masterテーブル ===")
            cursor.execute("SELECT employee_num, name, idm FROM employee_master WHERE name LIKE '%松浦%'")
            rows = cursor.fetchall()
            for row in rows:
                print(f"社員番号: {row[0]}, 名前: {row[1]}, IDM: {row[2]}")
            
            # attend_scheduleテーブルでの確認
            print("\n=== attend_scheduleテーブル ===")
            cursor.execute("""
                SELECT DISTINCT employee_id, employee_name 
                FROM attend_schedule 
                WHERE employee_name LIKE '%松浦%'
                ORDER BY employee_id
            """)
            rows = cursor.fetchall()
            for row in rows:
                print(f"社員ID: {row[0]}, 名前: {row[1]}")
                
            # 社員番号4452133のスケジュール件数確認
            print(f"\n=== 社員番号4452133のスケジュール件数 ===")
            cursor.execute("SELECT employee_name, COUNT(*) FROM attend_schedule WHERE employee_id = '4452133' GROUP BY employee_name")
            rows = cursor.fetchall()
            for row in rows:
                print(f"名前: {row[0]}, 件数: {row[1]}")
                
    except Exception as e:
        print(f'エラー: {e}')

def update_matsuura_employee_num():
    """松浦真司の社員番号を変更"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # employee_masterテーブルの更新
            print("employee_masterテーブルを更新中...")
            cursor.execute("""
                UPDATE employee_master 
                SET employee_num = '4552899' 
                WHERE employee_num = '4452133' AND name = '松浦　信司'
            """)
            master_count = cursor.rowcount
            print(f"employee_master更新件数: {master_count}")
            
            # attend_scheduleテーブルの更新  
            print("attend_scheduleテーブルを更新中...")
            cursor.execute("""
                UPDATE attend_schedule 
                SET employee_id = '4552899' 
                WHERE employee_id = '4452133' AND employee_name LIKE '%松浦%'
            """)
            schedule_count = cursor.rowcount
            print(f"attend_schedule更新件数: {schedule_count}")
            
            # コミット
            conn.commit()
            print("変更をコミットしました")
            
            return master_count, schedule_count
            
    except Exception as e:
        print(f'エラー: {e}')
        return 0, 0

if __name__ == '__main__':
    print("=== 変更前の確認 ===")
    check_matsuura_data()
    
    print("\n=== 社員番号変更実行 ===")
    master_count, schedule_count = update_matsuura_employee_num()
    
    print("\n=== 変更後の確認 ===")
    check_matsuura_data()