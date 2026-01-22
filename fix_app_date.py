#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
松浦真司さんの休暇申請の申請日を修正するスクリプト
"""

import sqlite3
import os
from datetime import datetime

def fix_application_date():
    """データベースの申請日を今日の日付に修正"""
    
    db_path = r'c:\Users\take_me_hospital\attendance\data\attendance.db'
    
    if not os.path.exists(db_path):
        print(f"❌ データベースが見つかりません: {db_path}")
        return
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 現在の松浦真司さんの休暇申請データを確認
        print("=== 修正前の申請データ ===")
        cursor.execute("""
            SELECT id, employee_num, application_date, leave_date_from, leave_date_to, 
                   leave_type, created_at
            FROM leave_request 
            WHERE employee_num IN (4552899, 4452133)
            ORDER BY created_at DESC
            LIMIT 3
        """)
        
        results = cursor.fetchall()
        
        if not results:
            print("❌ 松浦真司さんの休暇申請が見つかりません")
            return
            
        for row in results:
            print(f"ID: {row[0]}, 社員番号: {row[1]}")
            print(f"📅 申請日: {row[2]}")
            print(f"📅 休暇期間: {row[3]} ～ {row[4]}")
            print(f"種別: {row[5]}")
            print(f"登録日時: {row[6]}")
            print("-" * 40)
        
        # 最新の申請を取得
        latest = results[0]
        leave_id = latest[0]
        current_app_date = latest[2]
        
        # 今日の日付で修正
        today = datetime.now().strftime('%Y-%m-%d')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n=== 申請日修正処理 ===")
        print(f"対象申請ID: {leave_id}")
        print(f"修正前申請日: {current_app_date}")
        print(f"修正後申請日: {today}")
        
        # 申請日を更新
        cursor.execute("""
            UPDATE leave_request 
            SET application_date = ?, updated_at = ?
            WHERE id = ?
        """, (today, now, leave_id))
        
        conn.commit()
        
        # 修正後のデータを確認
        print("\n=== 修正後の申請データ ===")
        cursor.execute("""
            SELECT id, employee_num, application_date, leave_date_from, leave_date_to, 
                   leave_type, updated_at
            FROM leave_request 
            WHERE id = ?
        """, (leave_id,))
        
        updated_row = cursor.fetchone()
        
        print(f"✅ 申請日修正完了!")
        print(f"ID: {updated_row[0]}")
        print(f"社員番号: {updated_row[1]}")
        print(f"📅 申請日: {updated_row[2]} (修正済み)")
        print(f"📅 休暇期間: {updated_row[3]} ～ {updated_row[4]}")
        print(f"種別: {updated_row[5]}")
        print(f"更新日時: {updated_row[6]}")
        
        return leave_id
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        if 'conn' in locals():
            conn.rollback()
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    print("=== 松浦真司さん休暇申請の申請日修正 ===")
    print(f"今日の日付: {datetime.now().strftime('%Y-%m-%d')}")
    print()
    
    leave_id = fix_application_date()
    
    if leave_id:
        print(f"\n🎉 申請日修正完了 (申請ID: {leave_id})")
        print("\n📄 PDF再出力の手順:")
        print("1. ブラウザで http://localhost:8000 にアクセス")
        print("2. 「休暇願一覧（管理用）」を開く")  
        print(f"3. ID {leave_id} の申請で「PDF再出力」ボタンをクリック")
        print("4. 修正された申請日でPDFが生成されます")
        print("\n📁 PDFは以下の場所に保存されます:")
        print("   data/reports/202601/leave_requests/松浦真司/")
        print("   ファイル名: 20260114_休暇願_松浦真司_HHMMSS.pdf")
    else:
        print("\n❌ 修正に失敗しました")

if __name__ == "__main__":
    main()