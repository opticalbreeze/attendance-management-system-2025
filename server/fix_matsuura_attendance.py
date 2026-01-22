#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import sys
import os
from datetime import datetime

def get_db_connection():
    """データベース接続を取得"""
    db_path = os.path.join('..', '..', 'data', 'attendance.db')
    return sqlite3.connect(db_path)

def update_matsuura_attendance():
    """松浦真司の勤怠スケジュールを4552899に統一"""
    
    try:
        # バックアップファイル名
        backup_name = f"attendance_backup_matsuura_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = backup_name
        
        # データベース接続
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # バックアップ作成
        print(f"バックアップ作成中: {backup_name}")
        backup_conn = sqlite3.connect(backup_path)
        conn.backup(backup_conn)
        backup_conn.close()
        print("✅ バックアップ完了")
        
        # 現在の状況確認
        print("\n=== 現在の状況確認 ===")
        
        # employee_masterの松浦関連レコード
        cursor.execute('SELECT employee_num, name, idm FROM employee_master WHERE name LIKE "%松浦%"')
        masters = cursor.fetchall()
        print("employee_master:")
        for master in masters:
            print(f"  社員番号: {master[0]}, 名前: {master[1]}, IDM: {master[2]}")
        
        # attend_scheduleの松浦真司の社員ID別件数
        cursor.execute('''SELECT employee_id, COUNT(*) 
                         FROM attend_schedule 
                         WHERE name = "松浦　真司" 
                         GROUP BY employee_id''')
        schedules = cursor.fetchall()
        print("\nattend_schedule（松浦　真司）:")
        total_before = 0
        for schedule in schedules:
            print(f"  社員ID {schedule[0]}: {schedule[1]}件")
            total_before += schedule[1]
        print(f"  合計: {total_before}件")
        
        if not schedules:
            print("❌ 松浦　真司の勤怠スケジュールが見つかりません")
            conn.close()
            return
        
        # 4452133 → 4552899への変更
        print("\n=== 勤怠スケジュールの更新実行 ===")
        cursor.execute('''UPDATE attend_schedule 
                         SET employee_id = "4552899" 
                         WHERE name = "松浦　真司" AND employee_id = "4452133"''')
        
        updated_count = cursor.rowcount
        print(f"✅ {updated_count}件のレコードを4452133 → 4552899に更新しました")
        
        # 変更後の確認
        cursor.execute('''SELECT employee_id, COUNT(*) 
                         FROM attend_schedule 
                         WHERE name = "松浦　真司" 
                         GROUP BY employee_id''')
        schedules_after = cursor.fetchall()
        print("\n=== 更新後の状況 ===")
        print("attend_schedule（松浦　真司）:")
        total_after = 0
        for schedule in schedules_after:
            print(f"  社員ID {schedule[0]}: {schedule[1]}件")
            total_after += schedule[1]
        print(f"  合計: {total_after}件")
        
        # コミット
        conn.commit()
        print(f"\n✅ 変更をデータベースに保存しました")
        print(f"✅ バックアップファイル: {backup_name}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    print("松浦真司の勤怠スケジュール修正を開始します...")
    update_matsuura_attendance()
    print("処理完了")