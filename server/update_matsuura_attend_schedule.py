#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
attend_scheduleテーブルの松浦氏の社員番号を4552099に統一するスクリプト
"""

import sqlite3
import os
import shutil
from datetime import datetime
from config import Config

def update_matsuura_employee_id():
    """attend_scheduleテーブルの松浦氏の社員番号を4552099に統一"""
    db_path = Config.DATABASE_PATH
    
    if not os.path.exists(db_path):
        print(f"データベースファイルが見つかりません: {db_path}")
        return
    
    # バックアップを作成
    backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'attendance_backup_matsuura_update_{timestamp}.db')
    shutil.copy2(db_path, backup_path)
    print(f"バックアップを作成しました: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 更新前の状態を確認
        print("\n=== 更新前の状態 ===")
        cursor.execute("""
            SELECT employee_id, COUNT(*) as count
            FROM attend_schedule
            WHERE employee_name LIKE '%松浦%'
            GROUP BY employee_id
            ORDER BY employee_id
        """)
        before = cursor.fetchall()
        for row in before:
            print(f"  社員番号: {row[0]}, 件数: {row[1]}件")
        
        # 4452099を4552099に更新
        print("\n=== 4452099 → 4552099 に更新 ===")
        cursor.execute("""
            UPDATE attend_schedule
            SET employee_id = '4552099'
            WHERE employee_name LIKE '%松浦%' AND employee_id = '4452099'
        """)
        updated_445 = cursor.rowcount
        print(f"  更新件数: {updated_445}件")
        
        # 4552899を4552099に更新
        print("\n=== 4552899 → 4552099 に更新 ===")
        cursor.execute("""
            UPDATE attend_schedule
            SET employee_id = '4552099'
            WHERE employee_name LIKE '%松浦%' AND employee_id = '4552899'
        """)
        updated_455 = cursor.rowcount
        print(f"  更新件数: {updated_455}件")
        
        # コミット
        conn.commit()
        print("\n[OK] 更新をコミットしました")
        
        # 更新後の状態を確認
        print("\n=== 更新後の状態 ===")
        cursor.execute("""
            SELECT employee_id, COUNT(*) as count
            FROM attend_schedule
            WHERE employee_name LIKE '%松浦%'
            GROUP BY employee_id
            ORDER BY employee_id
        """)
        after = cursor.fetchall()
        for row in after:
            print(f"  社員番号: {row[0]}, 件数: {row[1]}件")
        
        total_updated = updated_445 + updated_455
        print(f"\n[OK] 合計 {total_updated}件のレコードを更新しました")
        
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] エラーが発生しました: {e}")
        print("変更をロールバックしました")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    print("=== attend_scheduleテーブルの松浦氏の社員番号を4552099に統一 ===")
    confirm = input("\nこの操作を実行しますか？ (yes/no): ")
    if confirm.lower() == 'yes':
        update_matsuura_employee_id()
    else:
        print("操作をキャンセルしました")
