#!/usr/bin/env python3
"""
簡単なデータベース操作コマンド
"""
import sqlite3

def main():
    conn = sqlite3.connect('/app/data/attendance.db')
    cursor = conn.cursor()
    
    print("=== データベース編集ツール ===")
    print("\n使用可能なテーブル:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for i, table in enumerate(tables, 1):
        print(f"  {i}. {table[0]}")
    
    print("\n=== employee_master テーブル構造 ===")
    cursor.execute("PRAGMA table_info(employee_master)")
    columns = cursor.fetchall()
    print("カラム名 | データ型 | NULL許可 | 主キー")
    print("-" * 40)
    for col in columns:
        null_ok = "Yes" if col[3] == 0 else "No"
        pk = "Yes" if col[5] == 1 else "No"
        print(f"{col[1]} | {col[2]} | {null_ok} | {pk}")
    
    print("\n=== employee_master データサンプル ===")
    cursor.execute("SELECT id, employee_num, name, idm FROM employee_master LIMIT 5")
    records = cursor.fetchall()
    print("ID | 従業員番号 | 名前 | IDM")
    print("-" * 50)
    for record in records:
        print(f"{record[0]} | {record[1]} | {record[2]} | {record[3]}")
    
    conn.close()

if __name__ == "__main__":
    main()