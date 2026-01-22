#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
松浦真司さんの2026年1月14-15日の休暇申請データを作成し、PDF再出力を行うスクリプト
"""

import sqlite3
import sys
import os
import requests
import json
from datetime import datetime

# Dockerコンテナ内での実行を想定した設定
DATABASE_PATH = '/app/data/attendance.db'
BASE_URL = 'http://localhost:5000'

def create_leave_request():
    """松浦真司さんの休暇申請を作成"""
    
    # データベース接続
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # 現在のテーブル構造を確認
        cursor.execute("PRAGMA table_info(leave_request)")
        table_info = cursor.fetchall()
        print("=== leave_requestテーブル構造 ===")
        for col in table_info:
            print(f"{col[1]} {col[2]}")
        
        # 松浦真司さんの従業員マスターデータを確認
        cursor.execute("SELECT id, name FROM employee_master WHERE name = '松浦　真司'")
        employee_data = cursor.fetchone()
        
        if not employee_data:
            print("松浦真司さんの従業員データが見つかりません")
            return None
            
        employee_id, employee_name = employee_data
        print(f"従業員データ: ID={employee_id}, 名前={employee_name}")
        
        # 既存の休暇申請をチェック
        cursor.execute("""
            SELECT id, leave_date_from, leave_date_to, leave_type 
            FROM leave_request 
            WHERE employee_num = ? AND leave_date_from = '2026-01-14'
        """, (employee_id,))
        
        existing_request = cursor.fetchone()
        
        if existing_request:
            print(f"既存の休暇申請が見つかりました: ID={existing_request[0]}")
            return existing_request[0]
        
        # 新しい休暇申請を作成
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            INSERT INTO leave_request (
                employee_num, leave_date_from, leave_date_to, 
                leave_type, leave_subtype, substitute_work_date,
                application_date, other_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            employee_id,           # employee_num
            '2026-01-14',         # leave_date_from
            '2026-01-15',         # leave_date_to
            'その他',              # leave_type
            None,                 # leave_subtype
            None,                 # substitute_work_date
            '2026-01-14',         # application_date
            '個人的事由による休暇申請',  # other_reason
            now,                  # created_at
            now                   # updated_at
        ))
        
        leave_id = cursor.lastrowid
        conn.commit()
        
        print(f"新しい休暇申請を作成しました: ID={leave_id}")
        print(f"期間: 2026-01-14 ～ 2026-01-15")
        print(f"種類: その他")
        
        return leave_id
        
    except Exception as e:
        print(f"エラー: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def reprint_pdf(leave_id):
    """PDF再出力APIを呼び出し"""
    try:
        url = f"{BASE_URL}/api/leave/{leave_id}/reprint_pdf"
        response = requests.post(url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                print(f"PDF再出力成功: {data.get('filename')}")
                print(f"保存パス: {data.get('path')}")
                return True
            else:
                print(f"PDF再出力失敗: {data.get('message')}")
                return False
        else:
            print(f"HTTP エラー: {response.status_code}")
            print(f"レスポンス: {response.text}")
            return False
            
    except Exception as e:
        print(f"PDF再出力エラー: {e}")
        return False

def main():
    print("=== 松浦真司さんの休暇申請とPDF再出力 ===")
    
    # 1. 休暇申請データの作成/確認
    leave_id = create_leave_request()
    
    if leave_id:
        print(f"\n=== PDF再出力処理開始 (ID: {leave_id}) ===")
        
        # 2. PDF再出力の実行
        success = reprint_pdf(leave_id)
        
        if success:
            print("\n✅ 処理完了: PDFの再出力に成功しました")
            print("📁 新しいPDFファイル構造で保存されています:")
            print("   data/reports/202601/leave_requests/松浦真司/")
        else:
            print("\n❌ PDF再出力に失敗しました")
    else:
        print("\n❌ 休暇申請データの作成に失敗しました")

if __name__ == "__main__":
    main()