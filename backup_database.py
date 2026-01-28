#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベースバックアップ作成スクリプト
"""

import sqlite3
import shutil
import os
from datetime import datetime

# データベースパス
DB_PATH = r'c:\Users\take_me_hospital\attendance\data\attendance.db'
BACKUP_DIR = r'c:\Users\take_me_hospital\attendance\backup\database'

def create_database_backup():
    """データベースバックアップを作成"""
    print("="*60)
    print("データベースバックアップ作成")
    print("="*60)
    
    # バックアップディレクトリ作成
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # タイムスタンプ付きバックアップファイル名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"attendance_backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        # データベースファイルをコピー
        shutil.copy2(DB_PATH, backup_path)
        
        # バックアップ内容確認
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM attend_schedule")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM attend_schedule 
            WHERE work_date BETWEEN '2026-01-16' AND '2026-02-15'
        """)
        period_count = cursor.fetchone()[0]
        
        conn.close()
        
        file_size = os.path.getsize(backup_path)
        
        print(f"✅ バックアップ作成成功!")
        print(f"📁 バックアップファイル: {backup_path}")
        print(f"📊 総レコード数: {total_count}")
        print(f"📅 対象期間レコード数: {period_count}")
        print(f"💾 ファイルサイズ: {file_size:,} bytes")
        
        return backup_path
        
    except Exception as e:
        print(f"❌ バックアップ作成失敗: {e}")
        return None

def main():
    """メイン処理"""
    print("データベースバックアップツール")
    
    backup_path = create_database_backup()
    
    if backup_path:
        print(f"\n{'='*60}")
        print("バックアップ完了 - 安全に作業を続行できます")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print("バックアップ失敗 - 作業を中断してください")
        print(f"{'='*60}")

if __name__ == "__main__":
    main()