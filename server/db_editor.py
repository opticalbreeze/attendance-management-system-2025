#!/usr/bin/env python3
"""
データベース編集用スクリプト
"""
import sqlite3
import sys
from datetime import datetime
from config import Config

def connect_db():
    """データベースに接続"""
    return sqlite3.connect(Config.DATABASE_PATH)

def show_tables():
    """テーブル一覧を表示"""
    conn = connect_db()
    cursor = conn.cursor()
    
    print("=== データベース内のテーブル一覧 ===")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  - {table[0]}")
    
    conn.close()
    return [table[0] for table in tables]

def show_table_structure(table_name):
    """テーブル構造を表示"""
    conn = connect_db()
    cursor = conn.cursor()
    
    print(f"\n=== {table_name} テーブルの構造 ===")
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    for col in columns:
        print(f"  {col[1]} ({col[2]}) {'PRIMARY KEY' if col[5] else ''} {'NOT NULL' if col[3] else ''}")
    
    conn.close()

def show_table_data(table_name, limit=10):
    """テーブルのデータを表示"""
    conn = connect_db()
    cursor = conn.cursor()
    
    print(f"\n=== {table_name} テーブルのデータ (最新{limit}件) ===")
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    total = cursor.fetchone()[0]
    print(f"総レコード数: {total}")
    
    cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
    records = cursor.fetchall()
    
    for i, record in enumerate(records, 1):
        print(f"  {i}: {record}")
    
    conn.close()

def execute_query(query):
    """SQLクエリを実行"""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(query)
        
        # SELECT文の場合は結果を表示
        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            print(f"\n=== クエリ結果 ({len(results)}件) ===")
            for i, record in enumerate(results, 1):
                print(f"  {i}: {record}")
        else:
            # INSERT/UPDATE/DELETE文の場合はコミット
            conn.commit()
            print(f"\nクエリ実行完了 (影響を受けた行数: {cursor.rowcount})")
            
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        conn.close()

def interactive_mode():
    """対話モード"""
    print("=== データベース編集ツール ===")
    print("コマンド:")
    print("  tables    - テーブル一覧表示")
    print("  desc <table> - テーブル構造表示") 
    print("  show <table> [limit] - テーブルデータ表示")
    print("  sql <query> - SQLクエリ実行")
    print("  quit      - 終了")
    print()
    
    while True:
        try:
            command = input("db> ").strip()
            
            if not command:
                continue
            elif command == "quit":
                break
            elif command == "tables":
                show_tables()
            elif command.startswith("desc "):
                table_name = command.split()[1]
                show_table_structure(table_name)
            elif command.startswith("show "):
                parts = command.split()
                table_name = parts[1]
                limit = int(parts[2]) if len(parts) > 2 else 10
                show_table_data(table_name, limit)
            elif command.startswith("sql "):
                query = command[4:]
                execute_query(query)
            else:
                print("不明なコマンドです")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"エラー: {e}")
    
    print("\n終了しました")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # コマンドライン引数がある場合
        command = sys.argv[1]
        if command == "tables":
            show_tables()
        elif command == "interactive":
            interactive_mode()
        else:
            execute_query(" ".join(sys.argv[1:]))
    else:
        # 引数がない場合は対話モード
        interactive_mode()