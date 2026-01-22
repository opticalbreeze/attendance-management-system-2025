#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
松浦真司さんの休暇申請データと申請日を詳細確認するスクリプト
"""

import sqlite3
import os
import sys
from datetime import datetime

def check_leave_application_date():
    """休暇申請データの申請日を詳しく確認"""
    
    # データベースパス
    db_path = r'c:\Users\take_me_hospital\attendance\data\attendance.db'
    
    if not os.path.exists(db_path):
        print(f"データベースが見つかりません: {db_path}")
        return
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=== 松浦真司さんの休暇申請データ詳細確認 ===\n")
        
        # テーブルの構造確認
        cursor.execute("PRAGMA table_info(leave_request)")
        columns = cursor.fetchall()
        
        print("📋 leave_requestテーブル構造:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        print()
        
        # 松浦真司さんの休暇申請を詳細確認
        cursor.execute("""
            SELECT id, employee_num, application_date, leave_date_from, leave_date_to, 
                   leave_type, leave_subtype, other_reason, created_at, updated_at
            FROM leave_request 
            WHERE employee_num IN (4552899, 4452133)
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        results = cursor.fetchall()
        
        if results:
            print(f"📄 松浦真司さんの休暇申請 ({len(results)}件):")
            print("-" * 80)
            
            for i, row in enumerate(results, 1):
                print(f"【申請 {i}】")
                print(f"  ID: {row[0]}")
                print(f"  社員番号: {row[1]}")
                print(f"  📅 申請日: {row[2]}")  # これが問題の箇所
                print(f"  📅 休暇開始日: {row[3]}")
                print(f"  📅 休暇終了日: {row[4]}")
                print(f"  種別: {row[5]}")
                print(f"  サブタイプ: {row[6] or '(なし)'}")
                print(f"  理由: {row[7] or '(なし)'}")
                print(f"  📅 登録日時: {row[8]}")
                print(f"  📅 更新日時: {row[9]}")
                print()
                
                # 申請日の問題をチェック
                application_date = row[2]
                leave_date_from = row[3]
                created_at = row[8]
                
                print(f"  🔍 申請日チェック:")
                print(f"     申請日 (application_date): {application_date}")
                print(f"     休暇開始日 (leave_date_from): {leave_date_from}")
                
                if application_date != leave_date_from:
                    print(f"     ⚠️  申請日と休暇開始日が異なります！")
                else:
                    print(f"     ✅ 申請日と休暇開始日が一致しています")
                
                # 今日の日付と比較
                today = datetime.now().strftime('%Y-%m-%d')
                print(f"     今日の日付: {today}")
                
                if application_date != today:
                    print(f"     ⚠️  申請日が今日の日付({today})と異なります")
                else:
                    print(f"     ✅ 申請日が今日の日付です")
                    
                print("-" * 50)
        else:
            print("❌ 松浦真司さんの休暇申請データが見つかりませんでした")
            
            # 全体の件数を確認
            cursor.execute("SELECT COUNT(*) FROM leave_request")
            total_count = cursor.fetchone()[0]
            print(f"📊 leave_requestテーブル総件数: {total_count}")
            
            if total_count > 0:
                cursor.execute("SELECT DISTINCT employee_num FROM leave_request ORDER BY employee_num")
                employee_nums = cursor.fetchall()
                print(f"📊 登録されている社員番号一覧:")
                for emp in employee_nums:
                    print(f"   - {emp[0]}")
    
    except Exception as e:
        print(f"❌ エラー: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
        
    print("\n処理完了")

if __name__ == "__main__":
    check_leave_application_date()