#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打刻システム - サーバー側（改善版・Flask）
クライアントから打刻データを受信してデータベースに格納

機能:
- 打刻データの受信と保存
- データ検索API
- 統計情報API
- Webインターフェース
"""

from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime
from pathlib import Path
import json

app = Flask(__name__)

# ============================================================================
# 設定
# ============================================================================

DB_FILE = "attendance.db"  # データベースファイル名


# ============================================================================
# データベース管理
# ============================================================================

def init_database():
    """
    データベースを初期化
    テーブルが存在しない場合は作成
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 打刻テーブルの作成
    # NOTE: SQLiteではINDEXはCREATE INDEX文で作成する必要がある
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idm TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            terminal_id TEXT NOT NULL,
            received_at TEXT NOT NULL
        )
    """)
    
    # インデックスの作成（パフォーマンス向上）
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_idm ON attendance(idm)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON attendance(timestamp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_terminal_id ON attendance(terminal_id)
    """)
    
    conn.commit()
    conn.close()
    print("✅ データベース初期化完了")


# ============================================================================
# Webページ（HTML）
# ============================================================================

@app.route('/')
def index():
    """
    トップページ
    打刻システムのメインページを表示
    
    Returns:
        HTMLテンプレート
    """
    return render_template('index.html')


@app.route('/search')
def search_page():
    """
    検索ページ
    打刻データを検索するためのページを表示
    
    Returns:
        HTMLテンプレート
    """
    return render_template('search.html')


# ============================================================================
# API エンドポイント
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    ヘルスチェックAPI
    サーバーの稼働状態を確認するエンドポイント
    クライアントからの接続テストに使用
    
    Returns:
        JSON: 状態情報
    """
    return jsonify({
        'status': 'ok',
        'message': 'サーバーは正常に動作しています',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


@app.route('/api/attendance', methods=['POST'])
def receive_attendance():
    """
    打刻データ受信API
    クライアントから送信された打刻データをデータベースに保存
    
    Request Body (JSON):
        {
            "idm": "カードID（16進数文字列）",
            "timestamp": "打刻日時（ISO8601形式）",
            "terminal_id": "端末ID（MACアドレスなど）"
        }
    
    Returns:
        JSON: 処理結果
        - 成功: 200 OK
        - エラー: 400 Bad Request または 500 Internal Server Error
    """
    try:
        # JSONデータを取得
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'データが送信されていません'
            }), 400
        
        # 必須フィールドの取得
        idm = data.get('idm')
        timestamp = data.get('timestamp')
        terminal_id = data.get('terminal_id')
        
        # バリデーション
        if not all([idm, timestamp, terminal_id]):
            return jsonify({
                'status': 'error',
                'message': '必須フィールドが不足しています（idm, timestamp, terminal_id）'
            }), 400
        
        # データベースに保存
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO attendance (idm, timestamp, terminal_id, received_at)
            VALUES (?, ?, ?, ?)
        """, (idm, timestamp, terminal_id, datetime.now().isoformat()))
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()
        
        # ログ出力
        print(f"[受信] ID:{record_id} | IDm:{idm} | 端末:{terminal_id} | 時刻:{timestamp}")
        
        return jsonify({
            'status': 'success',
            'message': '打刻データを保存しました',
            'idm': idm,
            'record_id': record_id
        })
    
    except sqlite3.Error as e:
        print(f"[エラー] データベースエラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'データベースエラー: {str(e)}'
        }), 500
    
    except Exception as e:
        print(f"[エラー] データ受信エラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'サーバーエラー: {str(e)}'
        }), 500


@app.route('/api/search', methods=['GET'])
def search_attendance():
    """
    打刻データ検索API
    条件を指定して打刻データを検索
    
    Query Parameters:
        idm (str): カードID（部分一致）
        start_date (str): 開始日（YYYY-MM-DD形式）
        end_date (str): 終了日（YYYY-MM-DD形式）
        terminal_id (str): 端末ID（部分一致）
        limit (int): 取得件数（デフォルト: 100）
    
    Returns:
        JSON: 検索結果
    """
    try:
        # クエリパラメータの取得
        idm = request.args.get('idm', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        terminal_id = request.args.get('terminal_id', '').strip()
        limit = request.args.get('limit', '100')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # クエリ構築（動的にWHERE句を追加）
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
        
        # 並び替えと件数制限
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(int(limit))
        
        # クエリ実行
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 結果を辞書形式に整形
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
    
    except ValueError as e:
        print(f"[エラー] パラメータエラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'パラメータエラー: {str(e)}'
        }), 400
    
    except sqlite3.Error as e:
        print(f"[エラー] データベースエラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'データベースエラー: {str(e)}'
        }), 500
    
    except Exception as e:
        print(f"[エラー] 検索エラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'検索エラー: {str(e)}'
        }), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """
    統計情報取得API
    打刻データの統計情報を取得
    
    Returns:
        JSON: 統計情報
        - total_records: 総レコード数
        - unique_idm: ユニークなカードID数
        - unique_terminals: ユニークな端末数
        - today_count: 今日の打刻数
        - latest: 最新の打刻データ（5件）
    """
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
        
        # 最新の打刻（5件）
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
                'latest': [
                    {
                        'idm': r[0],
                        'timestamp': r[1],
                        'terminal_id': r[2]
                    } for r in latest
                ]
            }
        })
    
    except sqlite3.Error as e:
        print(f"[エラー] データベースエラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'データベースエラー: {str(e)}'
        }), 500
    
    except Exception as e:
        print(f"[エラー] 統計情報取得エラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'エラー: {str(e)}'
        }), 500


# ============================================================================
# エントリーポイント
# ============================================================================

def main():
    """
    サーバーを起動
    データベースを初期化してFlaskサーバーを起動
    """
    print("="*70)
    print("🔖 打刻システム - サーバー（改善版）")
    print("="*70)
    print()
    
    # データベース初期化
    init_database()
    
    # 設定情報を表示
    db_path = Path(DB_FILE).absolute()
    print(f"📁 データベース: {db_path}")
    print(f"🌐 サーバー起動: http://0.0.0.0:5000")
    print()
    print("[アクセス方法]")
    print("  - ローカル: http://localhost:5000")
    print("  - ネットワーク: http://<サーバーのIPアドレス>:5000")
    print()
    print("[API エンドポイント]")
    print("  - ヘルスチェック: GET  /api/health")
    print("  - 打刻データ受信: POST /api/attendance")
    print("  - データ検索:     GET  /api/search")
    print("  - 統計情報:       GET  /api/stats")
    print("="*70)
    print()
    
    # Flaskサーバー起動
    # host='0.0.0.0': 全てのネットワークインターフェースで待ち受け
    # port=5000: ポート番号
    # debug=False: 本番環境では必ずFalseにする
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n[終了] サーバーを停止します")
    except Exception as e:
        print(f"\n[エラー] サーバー起動エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

