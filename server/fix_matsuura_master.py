#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
従業員マスター松浦レコード確認・修正スクリプト
"""

from utils import get_db_connection

def check_and_fix_matsuura():
    """松浦の従業員マスターレコードを確認・修正"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            print("=== 現在の松浦関連従業員マスタレコード ===")
            cursor.execute("SELECT employee_num, name, idm FROM employee_master WHERE name LIKE '%松浦%'")
            rows = cursor.fetchall()
            for row in rows:
                print(f"社員番号: {row[0]}, 名前: {row[1]}, IDM: {row[2]}")
            
            # 選択肢を提示
            print("\n=== 選択してください ===")
            print("1. 既存の 4552099 松浦　信司 を 4552899 松浦　真司 に変更")
            print("2. 新しく 4552899 松浦　真司 レコードを追加（既存レコードはそのまま）")
            
            choice = input("選択 (1 or 2): ").strip()
            
            if choice == "1":
                # 既存レコードを更新
                cursor.execute("""
                    UPDATE employee_master 
                    SET employee_num = '4552899', name = '松浦　真司' 
                    WHERE employee_num = '4552099' AND name = '松浦　信司'
                """)
                count = cursor.rowcount
                print(f"既存レコードを更新しました。更新件数: {count}")
                
            elif choice == "2":
                # 新しいレコードを追加
                cursor.execute("SELECT idm FROM employee_master WHERE name = '松浦　信司'")
                result = cursor.fetchone()
                idm = result[0] if result else '0116020034196A00'
                
                cursor.execute("""
                    INSERT OR REPLACE INTO employee_master (employee_num, name, idm, section)
                    VALUES ('4552899', '松浦　真司', ?, '設備')
                """, (idm,))
                print("新しいレコードを追加しました。")
                
            else:
                print("無効な選択です。")
                return
            
            conn.commit()
            
            # 確認
            print("\n=== 更新後の松浦関連レコード ===")
            cursor.execute("SELECT employee_num, name, idm FROM employee_master WHERE name LIKE '%松浦%' ORDER BY employee_num")
            rows = cursor.fetchall()
            for row in rows:
                print(f"社員番号: {row[0]}, 名前: {row[1]}, IDM: {row[2]}")
                
    except Exception as e:
        print(f'エラー: {e}')

if __name__ == '__main__':
    check_and_fix_matsuura()