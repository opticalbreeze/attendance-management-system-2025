#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
松浦真司さんの休暇申請を直接WebUI経由で作成するスクリプト
"""

import requests
import json
import sys

BASE_URL = 'http://localhost:8000'  # Dockerコンテナ外部ポート

def create_leave_request():
    """Web API経由で休暇申請を作成"""
    
    leave_data = {
        'employee_num': 4552899,  # 修正後の社員番号
        'leave_date_from': '2026-01-14',
        'leave_date_to': '2026-01-15',
        'leave_type': 'その他',
        'leave_subtype': '',
        'substitute_work_date': '',
        'other_reason': '個人的事由による休暇申請'
    }
    
    try:
        print("=== 休暇申請データ作成開始 ===")
        print(f"社員番号: {leave_data['employee_num']}")
        print(f"期間: {leave_data['leave_date_from']} ～ {leave_data['leave_date_to']}")
        print(f"種別: {leave_data['leave_type']}")
        
        response = requests.post(
            f"{BASE_URL}/api/leave",
            json=leave_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                leave_id = result.get('leave_id')
                print(f"✅ 休暇申請作成成功: ID = {leave_id}")
                return leave_id
            else:
                print(f"❌ 休暇申請作成失敗: {result.get('message')}")
                return None
        else:
            print(f"❌ HTTP エラー: {response.status_code}")
            print(f"レスポンス: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return None

def reprint_pdf(leave_id):
    """PDF再出力"""
    try:
        print(f"\n=== PDF再出力開始 (ID: {leave_id}) ===")
        
        response = requests.post(
            f"{BASE_URL}/api/leave/{leave_id}/reprint_pdf",
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print(f"✅ PDF再出力成功: {result.get('filename')}")
                print(f"📁 保存パス: {result.get('path')}")
                return True
            else:
                print(f"❌ PDF再出力失敗: {result.get('message')}")
                return False
        else:
            print(f"❌ HTTP エラー: {response.status_code}")
            print(f"レスポンス: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def main():
    print("=== 松浦真司さん 2026年1月14-15日 休暇願PDF再出力 ===")
    
    # 1. 休暇申請作成
    leave_id = create_leave_request()
    
    if leave_id:
        # 2. PDF再出力
        success = reprint_pdf(leave_id)
        
        if success:
            print("\n🎉 全ての処理が完了しました！")
            print("📄 新しいPDF自動整理システムにより以下のフォルダに保存されました：")
            print("   📁 data/reports/202601/leave_requests/松浦真司/")
            print("   📄 ファイル名: 20260114_休暇願_松浦真司_HHMMSS.pdf")
        else:
            print("\n❌ PDF再出力に失敗しました")
    else:
        print("\n❌ 休暇申請の作成に失敗しました")

if __name__ == "__main__":
    main()