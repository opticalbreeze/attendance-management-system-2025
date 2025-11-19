#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
勤務データの修正スクリプト
"""
import sqlite3
import time
from config import Config

# データベース設定（config.pyから取得）
DATABASE_PATH = Config.DATABASE_PATH

def fix_attendance_data():
    """勤務データの問題を修正"""
    
    # データベースロックを避けるため少し待機
    time.sleep(1)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        print("=== 勤務データ修正開始 ===")
        
        # 1. 井上誠二の2025-11-16を「明」に修正
        print("1. 井上誠二 (4452133) - 2025-11-16 の修正:")
        cursor.execute('SELECT work_type FROM attend_schedule WHERE employee_id = ? AND work_date = ?', 
                      ('4452133', '2025-11-16'))
        before = cursor.fetchone()
        print(f"  修正前: {before[0] if before else 'データなし'}")
        
        cursor.execute('UPDATE attend_schedule SET work_type = ? WHERE employee_id = ? AND work_date = ?', 
                      ('明', '4452133', '2025-11-16'))
        
        cursor.execute('SELECT work_type FROM attend_schedule WHERE employee_id = ? AND work_date = ?', 
                      ('4452133', '2025-11-16'))
        after = cursor.fetchone()
        print(f"  修正後: {after[0] if after else 'データなし'}")
        
        # 2. 時刻フォーマットの統一 (08:30 -> 8:30)
        print("\n2. 時刻フォーマットの統一:")
        
        # ゼロパディングされた時刻を修正
        cursor.execute("""
            UPDATE attend_schedule 
            SET start_time = LTRIM(start_time, '0'), end_time = LTRIM(end_time, '0')
            WHERE start_time LIKE '0%' OR end_time LIKE '0%'
        """)
        
        affected_rows = cursor.rowcount
        print(f"  修正したレコード数: {affected_rows}件")
        
        # 3. 無効なデータ（employee_id=0, 15）を削除
        print("\n3. 無効なデータの削除:")
        
        cursor.execute('SELECT COUNT(*) FROM attend_schedule WHERE employee_id IN ("0", "15")')
        invalid_count = cursor.fetchone()[0]
        print(f"  削除対象レコード数: {invalid_count}件")
        
        cursor.execute('DELETE FROM attend_schedule WHERE employee_id IN ("0", "15")')
        print(f"  削除完了")
        
        # 変更をコミット
        conn.commit()
        
        print("\n=== 修正完了 ===")
        
        # 最終確認
        print("\n=== 修正結果確認 ===")
        
        # 井上誠二のデータ確認
        cursor.execute('SELECT work_type, start_time, end_time FROM attend_schedule WHERE employee_id = ? AND work_date = ?', 
                      ('4452133', '2025-11-16'))
        result = cursor.fetchone()
        print(f"井上誠二 (2025-11-16): {result}")
        
        # 全体のレコード数確認
        cursor.execute('SELECT COUNT(*) FROM attend_schedule')
        total_count = cursor.fetchone()[0]
        print(f"総レコード数: {total_count}件")
        
        # 勤務区分の分布確認
        cursor.execute('SELECT work_type, COUNT(*) FROM attend_schedule GROUP BY work_type ORDER BY work_type')
        work_type_counts = cursor.fetchall()
        print("\n勤務区分分布:")
        for work_type, count in work_type_counts:
            if work_type and work_type.strip():  # 空文字列を除外
                print(f"  {work_type}: {count}件")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    """メイン処理"""
    fix_attendance_data()

if __name__ == "__main__":
    main()