#!/usr/bin/env python3
import sqlite3
import sys
from config import Config

def check_schema():
    """テーブルスキーマの詳細情報を確認"""
    try:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        
        print("=== attend_schedule テーブルスキーマ ===")
        cursor = conn.execute('PRAGMA table_info(attend_schedule)')
        print(f"{'列番号':<10} {'列名':<20} {'型':<15} {'NULL許可':<10} {'デフォルト値':<15} {'主キー':<10}")
        print("-" * 90)
        
        for row in cursor:
            col_id, col_name, col_type, not_null, default_val, primary_key = row
            null_allowed = "No" if not_null == 1 else "Yes"
            is_primary = "Yes" if primary_key == 1 else "No"
            default_str = str(default_val) if default_val is not None else "NULL"
            
            print(f"{col_id:<10} {col_name:<20} {col_type:<15} {null_allowed:<10} {default_str:<15} {is_primary:<10}")
        
        print("\n=== 既存データのサンプル ===")
        cursor = conn.execute('SELECT * FROM attend_schedule LIMIT 3')
        rows = cursor.fetchall()
        if rows:
            # カラム名を取得
            cursor = conn.execute('SELECT * FROM attend_schedule LIMIT 0')
            column_names = [description[0] for description in cursor.description]
            print(f"カラム: {', '.join(column_names)}")
            
            for i, row in enumerate(rows, 1):
                print(f"行{i}: {row}")
        else:
            print("既存データなし")
            
        conn.close()
        
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    check_schema()