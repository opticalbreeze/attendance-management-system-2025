#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
従業員マスタの内容を確認するスクリプト
"""

from utils import get_db_connection

def check_employee_master():
    """従業員マスタの内容を確認"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 従業員マスタの内容を確認
            cursor.execute('SELECT employee_num, name FROM employee_master ORDER BY employee_num')
            rows = cursor.fetchall()
            
            print(f'従業員マスタの内容（{len(rows)}件）:')
            for row in rows:
                print(f'ID: {row[0]}, 名前: {row[1]}')
            
            # 重複チェック
            cursor.execute('''
                SELECT employee_num, name, COUNT(*) 
                FROM employee_master 
                GROUP BY employee_num 
                HAVING COUNT(*) > 1
            ''')
            duplicates = cursor.fetchall()
            
            if duplicates:
                print('\n重複している従業員ID:')
                for dup in duplicates:
                    print(f'ID: {dup[0]}, 名前: {dup[1]}, 重複数: {dup[2]}')
            else:
                print('\n重複している従業員IDはありません。')
            
    except Exception as e:
        print(f'エラー: {e}')

if __name__ == '__main__':
    check_employee_master()