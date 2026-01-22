#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def main():
    """松浦氏全テーブル修正結果の確認"""
    
    # データベースパス
    db_path = os.path.join('..', '..', 'data', 'attendance.db')
    
    try:
        # データベース接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=== 松浦氏 全テーブル修正結果確認 ===\n")
        
        # 各テーブルの4552899レコード数
        tables_to_check = ['attend_schedule', 'leave_request', 'overtime']
        
        for table in tables_to_check:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table} WHERE employee_id = "4552899"')
                count_4552899 = cursor.fetchone()[0]
                
                cursor.execute(f'SELECT COUNT(*) FROM {table} WHERE employee_id = "4452133"')
                count_4452133 = cursor.fetchone()[0]
                
                print(f"{table}:")
                print(f"  4552899: {count_4552899}件")
                print(f"  4452133: {count_4452133}件 {'❌ 残存あり' if count_4452133 > 0 else '✅ 完全移行'}")
                print()
                
            except Exception as e:
                print(f"{table}: テーブル確認エラー - {e}")
        
        # employee_master確認
        print("employee_master:")
        cursor.execute('SELECT employee_num, name FROM employee_master WHERE name LIKE "%松浦%"')
        masters = cursor.fetchall()
        for master in masters:
            print(f"  社員番号: {master[0]}, 名前: {master[1]}")
        print()
        
        conn.close()
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()