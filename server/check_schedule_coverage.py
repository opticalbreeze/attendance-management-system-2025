#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2025/11/16から2025/12/16までの勤務スケジュール完全性チェック
"""
import sqlite3
from datetime import datetime, timedelta
import sys
import os
from config import Config

# データベース設定（config.pyから取得）
DATABASE_PATH = Config.DATABASE_PATH

def check_schedule_coverage():
    """指定期間の勤務スケジュールカバレッジをチェック"""
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # 期間設定（11/16-12/15: 12月度の勤務期間）
        start_date = datetime(2025, 11, 16)
        end_date = datetime(2025, 12, 15)
        
        print("=== 勤務スケジュールカバレッジチェック ===")
        print(f"対象期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')} (12月度)")
        print(f"期間日数: {(end_date - start_date).days + 1}日")
        
        # 全従業員リストを取得
        cursor.execute("""
            SELECT DISTINCT employee_id, employee_name 
            FROM attend_schedule 
            WHERE employee_id != '0' AND employee_id != '15'
            ORDER BY employee_id
        """)
        employees = cursor.fetchall()
        
        print(f"\n全従業員数: {len(employees)}人")
        
        missing_data = []
        incomplete_employees = []
        
        # 各従業員について期間内のデータをチェック
        for emp_id, emp_name in employees:
            # 期間内のデータ件数を取得
            cursor.execute("""
                SELECT COUNT(*) FROM attend_schedule 
                WHERE employee_id = ? AND work_date >= ? AND work_date <= ?
            """, (emp_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            count = cursor.fetchone()[0]
            expected_count = (end_date - start_date).days + 1
            
            if count < expected_count:
                incomplete_employees.append({
                    'id': emp_id,
                    'name': emp_name,
                    'actual': count,
                    'expected': expected_count,
                    'missing': expected_count - count
                })
            
            # 欠けている具体的な日付を確認
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                cursor.execute("""
                    SELECT COUNT(*) FROM attend_schedule 
                    WHERE employee_id = ? AND work_date = ?
                """, (emp_id, date_str))
                
                if cursor.fetchone()[0] == 0:
                    missing_data.append({
                        'employee_id': emp_id,
                        'employee_name': emp_name,
                        'missing_date': date_str
                    })
                
                current_date += timedelta(days=1)
        
        # 結果表示
        print("\n=== チェック結果 ===")
        
        if not incomplete_employees:
            print("✅ すべての従業員について、指定期間のスケジュールが完備されています！")
        else:
            print(f"❌ {len(incomplete_employees)}人の従業員に不完全なスケジュールがあります:")
            
            for emp in incomplete_employees:
                print(f"  - {emp['name']} ({emp['id']}): {emp['actual']}/{emp['expected']}日 (欠損: {emp['missing']}日)")
        
        # 特定日付の詳細確認
        critical_dates = ['2025-11-15', '2025-11-16', '2025-12-14', '2025-12-15']
        
        print(f"\n=== 重要日付の詳細 ===")
        for date_str in critical_dates:
            cursor.execute("""
                SELECT COUNT(*) FROM attend_schedule 
                WHERE work_date = ? AND employee_id NOT IN ('0', '15')
            """, (date_str,))
            count = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT employee_id, employee_name, work_type 
                FROM attend_schedule 
                WHERE work_date = ? AND employee_id NOT IN ('0', '15')
                ORDER BY employee_id
                LIMIT 5
            """, (date_str,))
            samples = cursor.fetchall()
            
            print(f"{date_str}: {count}件")
            if samples:
                print("  サンプル:")
                for emp_id, emp_name, work_type in samples:
                    print(f"    {emp_id}: {emp_name} - {work_type}")
            print()
        
        # 期間全体の統計
        print("=== 期間統計 ===")
        cursor.execute("""
            SELECT work_date, COUNT(*) as count
            FROM attend_schedule 
            WHERE work_date >= ? AND work_date <= ? AND employee_id NOT IN ('0', '15')
            GROUP BY work_date 
            ORDER BY work_date
        """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        
        daily_counts = cursor.fetchall()
        
        if daily_counts:
            min_count = min(count for _, count in daily_counts)
            max_count = max(count for _, count in daily_counts)
            avg_count = sum(count for _, count in daily_counts) / len(daily_counts)
            
            print(f"日別データ数 - 最小: {min_count}, 最大: {max_count}, 平均: {avg_count:.1f}")
            
            # データが少ない日を確認
            print("\n日別詳細 (データ数が平均より少ない日):")
            for work_date, count in daily_counts:
                if count < avg_count:
                    print(f"  {work_date}: {count}件")
        
        # 不完全データの詳細リスト表示（最初の20件）
        if missing_data:
            print(f"\n=== 欠損データ詳細 (最初の20件) ===")
            for i, data in enumerate(missing_data[:20]):
                print(f"  {i+1}. {data['employee_name']} ({data['employee_id']}) - {data['missing_date']}")
            
            if len(missing_data) > 20:
                print(f"  ... 他 {len(missing_data) - 20}件の欠損データがあります")
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return False
    finally:
        conn.close()
    
    return len(incomplete_employees) == 0

def main():
    """メイン処理"""
    print("勤務スケジュール完全性チェックを開始します...")
    
    # データベースファイルの存在確認
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ データベースファイルが見つかりません: {DATABASE_PATH}")
        sys.exit(1)
    
    # チェック実行
    is_complete = check_schedule_coverage()
    
    if is_complete:
        print("\n✅ スケジュールチェック完了: すべて正常です")
        sys.exit(0)
    else:
        print("\n❌ スケジュールチェック完了: 不完全なデータがあります")
        sys.exit(1)

if __name__ == "__main__":
    main()