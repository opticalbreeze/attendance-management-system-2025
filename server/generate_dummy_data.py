#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ダミーデータ生成スクリプト
サーバー検証用に30件のテストデータを生成
"""

import sqlite3
import random
from datetime import datetime, timedelta

# ダミーデータ設定
DUMMY_IDMS = [
    "012E447C1234ABCD",
    "012E447C5678EFGH",
    "012E447C9012IJKL",
    "012E447CMNOPQRST",
    "012E447CUVWXYZ01",
    "A1B2C3D4E5F60718",
    "F9E8D7C6B5A49382",
    "123456789ABCDEF0",
    "FEDCBA9876543210",
    "0A1B2C3D4E5F6789",
]

DUMMY_TERMINALS = [
    "AA:BB:CC:DD:EE:FF",
    "11:22:33:44:55:66",
    "A1:B2:C3:D4:E5:F6",
    "00:11:22:33:44:55",
    "FF:EE:DD:CC:BB:AA",
]


def generate_dummy_data(db_path="attendance.db", num_records=30):
    """ダミーデータを生成"""
    
    print("="*60)
    print("ダミーデータ生成スクリプト")
    print("="*60)
    print(f"📁 データベース: {db_path}")
    print(f"📊 生成件数: {num_records}件")
    print()
    
    # データベース接続
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # テーブル作成（存在しない場合）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idm TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            terminal_id TEXT NOT NULL,
            received_at TEXT NOT NULL
        )
    """)
    
    # 既存データ数を確認
    cursor.execute("SELECT COUNT(*) FROM attendance")
    existing_count = cursor.fetchone()[0]
    print(f"📋 既存データ: {existing_count}件")
    
    # ダミーデータ生成
    base_date = datetime.now() - timedelta(days=7)  # 7日前から
    
    print(f"🔄 {num_records}件のダミーデータを生成中...")
    
    for i in range(num_records):
        # ランダムなIDmと端末IDを選択
        idm = random.choice(DUMMY_IDMS)
        terminal_id = random.choice(DUMMY_TERMINALS)
        
        # ランダムな日時を生成（過去7日間）
        random_hours = random.randint(0, 7 * 24)
        random_minutes = random.randint(0, 59)
        random_seconds = random.randint(0, 59)
        
        timestamp = base_date + timedelta(
            hours=random_hours,
            minutes=random_minutes,
            seconds=random_seconds
        )
        
        # 受信時刻は打刻時刻の数秒後
        received_at = timestamp + timedelta(seconds=random.randint(0, 5))
        
        # データ挿入
        cursor.execute("""
            INSERT INTO attendance (idm, timestamp, terminal_id, received_at)
            VALUES (?, ?, ?, ?)
        """, (
            idm,
            timestamp.isoformat(),
            terminal_id,
            received_at.isoformat()
        ))
        
        if (i + 1) % 10 == 0:
            print(f"  ✓ {i + 1}件完了...")
    
    conn.commit()
    
    # 最終確認
    cursor.execute("SELECT COUNT(*) FROM attendance")
    total_count = cursor.fetchone()[0]
    
    # 統計情報
    cursor.execute("SELECT COUNT(DISTINCT idm) FROM attendance")
    unique_idm = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT terminal_id) FROM attendance")
    unique_terminals = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT idm, timestamp, terminal_id 
        FROM attendance 
        ORDER BY timestamp DESC 
        LIMIT 5
    """)
    latest = cursor.fetchall()
    
    conn.close()
    
    print()
    print("="*60)
    print("✅ ダミーデータ生成完了！")
    print("="*60)
    print(f"📊 統計情報:")
    print(f"  • 総レコード数: {total_count}件")
    print(f"  • ユニークIDm: {unique_idm}種類")
    print(f"  • ユニーク端末: {unique_terminals}台")
    print()
    print(f"📋 最新5件:")
    for record in latest:
        idm, timestamp, terminal_id = record
        print(f"  • IDm: {idm} | {timestamp[:19]} | {terminal_id}")
    print()
    print(f"🌐 ブラウザで http://192.168.1.31:5000 にアクセスして確認してください")


if __name__ == "__main__":
    import sys
    
    # コマンドライン引数で件数を指定可能
    num_records = 30
    if len(sys.argv) > 1:
        try:
            num_records = int(sys.argv[1])
        except ValueError:
            print("❌ エラー: 件数は数値で指定してください")
            sys.exit(1)
    
    generate_dummy_data(num_records=num_records)

