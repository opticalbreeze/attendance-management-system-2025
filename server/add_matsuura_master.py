#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
松浦真司の従業員マスタレコード追加スクリプト
"""

from utils import get_db_connection

def add_matsuura_master():
    """松浦真司の従業員マスタレコードを追加"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 既存の松浦のIDM情報を取得
            cursor.execute("SELECT idm FROM employee_master WHERE name = '松浦　信司'")
            result = cursor.fetchone()
            idm = result[0] if result else '0116020034196A00'  # デフォルトIDM
            
            # 新しいレコードを挿入
            cursor.execute("""
                INSERT OR REPLACE INTO employee_master (employee_num, name, idm, section)
                VALUES ('4552899', '松浦　真司', ?, '設備')
            """, (idm,))
            
            print(f"松浦真司（社員番号: 4552899）を従業員マスタに追加しました。IDM: {idm}")
            
            conn.commit()
            
            # 確認
            cursor.execute("SELECT employee_num, name, idm FROM employee_master WHERE name LIKE '%松浦%' ORDER BY employee_num")
            rows = cursor.fetchall()
            print("\n=== 更新後の松浦関連レコード ===")
            for row in rows:
                print(f"社員番号: {row[0]}, 名前: {row[1]}, IDM: {row[2]}")
                
    except Exception as e:
        print(f'エラー: {e}')

if __name__ == '__main__':
    add_matsuura_master()