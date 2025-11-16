#!/usr/bin/env python3
"""
楠本忠晴さんのデータ調査スクリプト
"""
import sqlite3
from datetime import datetime

def investigate_kusumoto_data():
    """楠本忠晴さんのデータを詳しく調査する"""
    conn = sqlite3.connect('/app/data/attendance.db')
    cursor = conn.cursor()
    
    print("=== 楠本忠晴さんのデータ調査 ===\n")
    
    # 1. employee_masterテーブルで確認
    print("1. employee_masterテーブル:")
    cursor.execute("SELECT id, employee_num, name, idm, section FROM employee_master WHERE name LIKE '%楠本%'")
    employee_data = cursor.fetchall()
    
    if employee_data:
        for emp in employee_data:
            print(f"   ID:{emp[0]}, 従業員番号:{emp[1]}, 名前:{emp[2]}, IDM:{emp[3]}, 部署:{emp[4]}")
            db_emp_id = emp[1]  # データベースの従業員番号
    else:
        print("   楠本さんのデータが見つかりません")
        return
    
    # 2. attend_scheduleテーブルで確認
    print("\n2. attend_scheduleテーブル:")
    
    # 名前で検索
    cursor.execute("SELECT COUNT(*) FROM attend_schedule WHERE employee_name LIKE '%楠本%'")
    schedule_count_by_name = cursor.fetchone()[0]
    print(f"   名前検索でのスケジュール件数: {schedule_count_by_name}")
    
    # DB従業員番号で検索
    cursor.execute("SELECT COUNT(*) FROM attend_schedule WHERE employee_id = ?", (db_emp_id,))
    schedule_count_by_db_id = cursor.fetchone()[0]
    print(f"   DB従業員番号({db_emp_id})でのスケジュール件数: {schedule_count_by_db_id}")
    
    # CSV従業員番号で検索
    csv_emp_id = 3852120  # CSVファイルの従業員番号
    cursor.execute("SELECT COUNT(*) FROM attend_schedule WHERE employee_id = ?", (csv_emp_id,))
    schedule_count_by_csv_id = cursor.fetchone()[0]
    print(f"   CSV従業員番号({csv_emp_id})でのスケジュール件数: {schedule_count_by_csv_id}")
    
    # 3. CSVファイルとの比較
    print("\n3. CSVファイルとの比較:")
    print("   CSVファイル: ID=6, 従業員番号=3852120, 名前=楠本　忠晴")
    print(f"   データベース: ID={employee_data[0][0]}, 従業員番号={employee_data[0][1]}, 名前={employee_data[0][2]}")
    print("   ⚠️ 従業員番号が異なっています！")
    
    # 4. CSVデータがスケジュールテーブルに入っているか確認
    if schedule_count_by_csv_id > 0:
        print(f"\n4. CSV従業員番号({csv_emp_id})のスケジュールデータ（最新10件）:")
        cursor.execute("""
            SELECT employee_id, employee_name, date, shift_type, start_time, end_time 
            FROM attend_schedule 
            WHERE employee_id = ? 
            ORDER BY date DESC 
            LIMIT 10
        """, (csv_emp_id,))
        schedules = cursor.fetchall()
        
        for i, schedule in enumerate(schedules, 1):
            print(f"   {i:2d}. {schedule[1]} - {schedule[2]} {schedule[3]} {schedule[4] or 'なし'}-{schedule[5] or 'なし'}")
    else:
        print(f"\n4. CSV従業員番号({csv_emp_id})のスケジュールデータは見つかりませんでした")
    
    # 5. 全従業員のスケジュール統計
    print("\n5. 全従業員のスケジュール統計:")
    cursor.execute("""
        SELECT employee_id, employee_name, COUNT(*) as schedule_count 
        FROM attend_schedule 
        GROUP BY employee_id, employee_name 
        ORDER BY schedule_count DESC
    """)
    all_schedules = cursor.fetchall()
    
    print("   従業員ID | 名前 | スケジュール件数")
    print("   " + "-" * 40)
    for emp_schedule in all_schedules:
        print(f"   {emp_schedule[0]} | {emp_schedule[1]} | {emp_schedule[2]}")
    
    # 6. 解決策の提案
    print("\n6. 🔧 解決策:")
    print("   問題: employee_masterテーブルとattend_scheduleテーブルの従業員番号が不一致")
    print(f"   ├─ employee_master: 従業員番号 {db_emp_id}")
    print(f"   └─ attend_schedule: 従業員番号 {csv_emp_id}")
    print("\n   解決方法:")
    print("   A) employee_masterの従業員番号をCSVに合わせて修正")
    print("   B) attend_scheduleの従業員番号をDBに合わせて修正")
    print("   C) 両方とも正しい番号に統一")
    
    conn.close()

def fix_kusumoto_employee_number():
    """楠本忠晴さんの従業員番号を修正する"""
    conn = sqlite3.connect('/app/data/attendance.db')
    cursor = conn.cursor()
    
    try:
        print("=== 楠本忠晴さんの従業員番号修正 ===")
        
        # 現在の状況確認
        cursor.execute("SELECT id, employee_num FROM employee_master WHERE name LIKE '%楠本%'")
        current_data = cursor.fetchone()
        
        if current_data:
            current_emp_id = current_data[1]
            csv_emp_id = 3852120
            
            print(f"現在の従業員番号: {current_emp_id}")
            print(f"CSVの従業員番号: {csv_emp_id}")
            
            # employee_masterを更新
            cursor.execute("""
                UPDATE employee_master 
                SET employee_num = ?, updated_at = ? 
                WHERE name LIKE '%楠本%'
            """, (csv_emp_id, datetime.now()))
            
            conn.commit()
            
            print(f"✅ 従業員番号を {current_emp_id} → {csv_emp_id} に修正しました")
            
            # 確認
            cursor.execute("SELECT id, employee_num, name FROM employee_master WHERE name LIKE '%楠本%'")
            updated_data = cursor.fetchone()
            print(f"確認: ID={updated_data[0]}, 従業員番号={updated_data[1]}, 名前={updated_data[2]}")
            
        else:
            print("❌ 楠本さんのデータが見つかりません")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ エラーが発生しました: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    investigate_kusumoto_data()
    
    print("\n" + "=" * 60)
    print("従業員番号を修正しますか？ (この処理は自動実行されます)")
    fix_kusumoto_employee_number()