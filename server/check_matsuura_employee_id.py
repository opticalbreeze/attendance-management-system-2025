#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
松浦氏のattend_scheduleテーブルの社員番号を確認するスクリプト
"""

import sqlite3
import os
from config import Config

def check_matsuura_employee_ids():
    """松浦氏のattend_scheduleテーブルの社員番号を確認"""
    db_path = Config.DATABASE_PATH
    
    if not os.path.exists(db_path):
        print(f"データベースファイルが見つかりません: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # employee_masterテーブルの松浦氏を確認
        print("=== employee_masterテーブルの松浦氏 ===")
        cursor.execute("SELECT employee_num, name FROM employee_master WHERE name LIKE '%松浦%'")
        employees = cursor.fetchall()
        if employees:
            for emp in employees:
                print(f"  社員番号: {emp[0]}, 名前: {emp[1]}")
        else:
            print("  松浦氏のレコードが見つかりません")
        
        # attend_scheduleテーブルの松浦氏の社員番号を確認
        print("\n=== attend_scheduleテーブルの松浦氏（社員番号別） ===")
        cursor.execute("""
            SELECT employee_id, COUNT(*) as count
            FROM attend_schedule
            WHERE employee_name LIKE '%松浦%'
            GROUP BY employee_id
            ORDER BY employee_id
        """)
        schedules = cursor.fetchall()
        if schedules:
            for sched in schedules:
                print(f"  社員番号: {sched[0]}, 件数: {sched[1]}件")
        else:
            print("  松浦氏のスケジュールが見つかりません")
        
        # 4552099以外の社員番号のレコードを確認
        print("\n=== 4552099以外の社員番号のレコード ===")
        cursor.execute("""
            SELECT employee_id, employee_name, COUNT(*) as count
            FROM attend_schedule
            WHERE employee_name LIKE '%松浦%' AND employee_id != '4552099'
            GROUP BY employee_id, employee_name
            ORDER BY employee_id
        """)
        other_ids = cursor.fetchall()
        if other_ids:
            for oid in other_ids:
                print(f"  社員番号: {oid[0]}, 名前: {oid[1]}, 件数: {oid[2]}件")
        else:
            print("  4552099以外のレコードはありません")
        
    finally:
        conn.close()

if __name__ == '__main__':
    check_matsuura_employee_ids()
