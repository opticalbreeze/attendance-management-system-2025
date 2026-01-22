#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
データベーススキーマ確認スクリプト
"""

import sqlite3
import os

# データベースファイルのパス
DB_PATH = r'c:\Users\take_me_hospital\attendance\data\attendance.db'

def check_schema():
    """データベースのスキーマ確認"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 全テーブル一覧
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("=== データベース内のテーブル一覧 ===")
        for table in tables:
            print(f"  - {table[0]}")
        
        # attend_scheduleテーブルの詳細
        if any('attend_schedule' in table for table in tables):
            print("\n=== attend_schedule テーブル構造 ===")
            cursor.execute("PRAGMA table_info(attend_schedule);")
            columns = cursor.fetchall()
            for column in columns:
                print(f"  {column[1]}: {column[2]} (NULL={column[3]==0})")
            
            # サンプルデータ表示
            print("\n=== attend_schedule サンプルデータ (最新3件) ===")
            cursor.execute("SELECT * FROM attend_schedule ORDER BY id DESC LIMIT 3;")
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    print(f"  {row}")
            else:
                print("  データが見つかりません")
        
        # employee_masterテーブルの確認
        if any('employee_master' in table for table in tables):
            print("\n=== employee_master テーブル構造 ===")
            cursor.execute("PRAGMA table_info(employee_master);")
            columns = cursor.fetchall()
            for column in columns:
                print(f"  {column[1]}: {column[2]} (NULL={column[3]==0})")
            
            # サンプルデータ表示
            print("\n=== employee_master サンプルデータ ===")
            cursor.execute("SELECT * FROM employee_master LIMIT 5;")
            rows = cursor.fetchall()
            for row in rows:
                print(f"  {row}")
        
        conn.close()
        print("\n✓ スキーマ確認完了")
        
    except Exception as e:
        print(f"✗ エラー: {e}")

if __name__ == "__main__":
    check_schema()
    input("\nEnterキーを押して終了してください...")