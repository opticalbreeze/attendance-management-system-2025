#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打刻システム - サーバー側（Flask）
打刻データを受信してデータベースに格納
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
import sqlite3
from datetime import datetime
from pathlib import Path
import json

app = Flask(__name__)

# データベースファイル
DB_FILE = "attendance.db"


def init_database():
    """データベース初期化"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 打刻テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idm TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            terminal_id TEXT NOT NULL,
            received_at TEXT NOT NULL,
            INDEX idx_idm (idm),
            INDEX idx_timestamp (timestamp),
            INDEX idx_terminal_id (terminal_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ データベース初期化完了")


@app.route('/')
def index():
    """トップページ"""
    return render_template('index.html')


@app.route('/search')
def search_page():
    """検索ページ"""
    return render_template('search.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェック（接続テスト用）"""
    return jsonify({
        'status': 'ok',
        'message': 'サーバーは正常に動作しています',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/attendance', methods=['POST'])
def receive_attendance():
    """打刻データを受信"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'データが送信されていません'
            }), 400
        
        idm = data.get('idm')
        timestamp = data.get('timestamp')
        terminal_id = data.get('terminal_id')
        
        if not all([idm, timestamp, terminal_id]):
            return jsonify({
                'status': 'error',
                'message': '必須フィールドが不足しています'
            }), 400
        
        # データベースに保存
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO attendance (idm, timestamp, terminal_id, received_at)
            VALUES (?, ?, ?, ?)
        """, (idm, timestamp, terminal_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        print(f"[受信] IDm: {idm} | 端末: {terminal_id} | 時刻: {timestamp}")
        
        return jsonify({
            'status': 'success',
            'message': '打刻データを保存しました',
            'idm': idm
        })
    
    except Exception as e:
        print(f"[エラー] データ受信エラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'サーバーエラー: {str(e)}'
        }), 500


@app.route('/api/search', methods=['GET'])
def search_attendance():
    """打刻データを検索"""
    try:
        idm = request.args.get('idm', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        terminal_id = request.args.get('terminal_id', '').strip()
        limit = request.args.get('limit', '100')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # クエリ構築
        query = "SELECT id, idm, timestamp, terminal_id, received_at FROM attendance WHERE 1=1"
        params = []
        
        if idm:
            query += " AND idm LIKE ?"
            params.append(f"%{idm}%")
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date + " 23:59:59")
        
        if terminal_id:
            query += " AND terminal_id LIKE ?"
            params.append(f"%{terminal_id}%")
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(int(limit))
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 結果を整形
        results = []
        for row in rows:
            results.append({
                'id': row[0],
                'idm': row[1],
                'timestamp': row[2],
                'terminal_id': row[3],
                'received_at': row[4]
            })
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'count': len(results),
            'results': results
        })
    
    except Exception as e:
        print(f"[エラー] 検索エラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'検索エラー: {str(e)}'
        }), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """統計情報を取得"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 総レコード数
        cursor.execute("SELECT COUNT(*) FROM attendance")
        total_records = cursor.fetchone()[0]
        
        # ユニークなIDm数
        cursor.execute("SELECT COUNT(DISTINCT idm) FROM attendance")
        unique_idm = cursor.fetchone()[0]
        
        # ユニークな端末数
        cursor.execute("SELECT COUNT(DISTINCT terminal_id) FROM attendance")
        unique_terminals = cursor.fetchone()[0]
        
        # 今日の打刻数
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE timestamp LIKE ?", (f"{today}%",))
        today_count = cursor.fetchone()[0]
        
        # 最新の打刻
        cursor.execute("SELECT idm, timestamp, terminal_id FROM attendance ORDER BY received_at DESC LIMIT 5")
        latest = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'stats': {
                'total_records': total_records,
                'unique_idm': unique_idm,
                'unique_terminals': unique_terminals,
                'today_count': today_count,
                'latest': [{'idm': r[0], 'timestamp': r[1], 'terminal_id': r[2]} for r in latest]
            }
        })
    
    except Exception as e:
        print(f"[エラー] 統計情報取得エラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'エラー: {str(e)}'
        }), 500


def main():
    """サーバー起動"""
    print("="*70)
    print("🔖 打刻システム - サーバー")
    print("="*70)
    
    # データベース初期化
    init_database()
    
    print(f"📁 データベース: {Path(DB_FILE).absolute()}")
    print(f"🌐 サーバー起動: http://0.0.0.0:5000")
    print(f"🔍 ブラウザで http://192.168.1.31:5000 にアクセスしてください")
    print("="*70)
    print()
    
    # Flaskサーバー起動
    app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == "__main__":
    main()

