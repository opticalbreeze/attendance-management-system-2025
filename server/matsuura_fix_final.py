#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import shutil
from datetime import datetime

def main():
    """松浦真司の勤怠スケジュールを4552899に修正"""
    
    # データベースパス
    db_path = os.path.join('..', '..', 'data', 'attendance.db')
    
    print(f"データベースパス: {db_path}")
    print(f"データベース存在確認: {os.path.exists(db_path)}")
    
    if not os.path.exists(db_path):
        print("❌ データベースファイルが見つかりません")
        return
    
    try:
        # バックアップ作成
        backup_name = f"attendance_backup_fix_matsuura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = os.path.join('..', '..', 'data', backup_name)
        
        print(f"バックアップ作成: {backup_path}")
        shutil.copy2(db_path, backup_path)
        print("✅ バックアップ完了")
        
        # データベース接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 現在の状況確認
        print("\n=== 現在の状況確認 ===")
        
        # employee_master確認
        cursor.execute('SELECT employee_num, name, idm FROM employee_master WHERE name LIKE "%松浦%"')
        masters = cursor.fetchall()
        print("employee_master:")
        if masters:
            for master in masters:
                print(f"  社員番号: {master[0]}, 名前: {master[1]}, IDM: {master[2]}")
        else:
            print("  松浦関連レコードなし")
        
        # attend_schedule確認（松浦真司）
        cursor.execute('''SELECT employee_id, COUNT(*) 
                         FROM attend_schedule 
                         WHERE name = "松浦　真司" 
                         GROUP BY employee_id''')
        schedules = cursor.fetchall()
        print("\nattend_schedule（松浦　真司）:")
        total_before = 0
        need_update = False
        for schedule in schedules:
            print(f"  社員ID {schedule[0]}: {schedule[1]}件")
            total_before += schedule[1]
            if schedule[0] == '4452133':
                need_update = True
        
        if total_before == 0:
            print("  松浦　真司のレコードなし")
            conn.close()
            return
            
        print(f"  合計: {total_before}件")
        
        # 更新が必要かチェック
        if not need_update:
            print("✅ 既に4552899に統一されています")
            conn.close()
            return
        
        # 更新実行
        print("\n=== 4452133 → 4552899 への更新実行 ===")
        cursor.execute('''UPDATE attend_schedule 
                         SET employee_id = "4552899" 
                         WHERE name = "松浦　真司" AND employee_id = "4452133"''')
        
        updated_count = cursor.rowcount
        print(f"✅ {updated_count}件のレコードを更新")
        
        # 更新後の確認
        cursor.execute('''SELECT employee_id, COUNT(*) 
                         FROM attend_schedule 
                         WHERE name = "松浦　真司" 
                         GROUP BY employee_id''')
        schedules_after = cursor.fetchall()
        print("\n=== 更新後の状況 ===")
        total_after = 0
        for schedule in schedules_after:
            print(f"  社員ID {schedule[0]}: {schedule[1]}件")
            total_after += schedule[1]
        print(f"  合計: {total_after}件")
        
        # コミット
        conn.commit()
        print(f"\n✅ データベースに保存完了")
        print(f"✅ バックアップ: {backup_name}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()