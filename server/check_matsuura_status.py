#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from utils import get_db_connection

def main():
    """松浦関連レコードの現在の状況を確認"""
    
    try:
        # データベース接続
        conn = get_db_connection()
        cursor = conn.cursor()

        print("=== employee_master の松浦関連レコード ===")
        cursor.execute('SELECT * FROM employee_master WHERE name LIKE "%松浦%"')
        employees = cursor.fetchall()
        
        if employees:
            for emp in employees:
                print(f"社員番号: {emp[1]}, 名前: {emp[2]}, IDM: {emp[3]}")
        else:
            print("松浦関連のemployee_masterレコードが見つかりません")

        print("\n=== attend_schedule の松浦真司レコード（最新5件） ===")
        cursor.execute('''SELECT employee_id, name, date, work_type 
                         FROM attend_schedule 
                         WHERE name = "松浦　真司" 
                         ORDER BY date DESC LIMIT 5''')
        schedules = cursor.fetchall()
        
        if schedules:
            for schedule in schedules:
                print(f"社員ID: {schedule[0]}, 名前: {schedule[1]}, 日付: {schedule[2]}, 勤務区分: {schedule[3]}")
        else:
            print("松浦真司の勤怠スケジュールが見つかりません")

        print("\n=== attend_schedule の4452133関連レコード数 ===")
        cursor.execute('SELECT COUNT(*) FROM attend_schedule WHERE employee_id = "4452133"')
        count_4452133 = cursor.fetchone()[0]
        print(f"4452133: {count_4452133}件")
        
        print("\n=== attend_schedule の4552899関連レコード数 ===")
        cursor.execute('SELECT COUNT(*) FROM attend_schedule WHERE employee_id = "4552899"')
        count_4552899 = cursor.fetchone()[0]
        print(f"4552899: {count_4552899}件")

        conn.close()
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()