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

from flask import Flask, request, jsonify, render_template, make_response
import sqlite3
from datetime import datetime
from pathlib import Path
import json
import os

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# ============================================================================
# 設定
# ============================================================================

# Docker環境では /data/attendance.db を使用、ローカル環境では attendance.db を使用
DB_FILE = os.environ.get('DATABASE_PATH', '/data/attendance.db' if os.path.exists('/data') else 'attendance.db')

# チャタリング防止設定
CHATTERING_THRESHOLD_SECONDS = int(os.environ.get('CHATTERING_THRESHOLD', '10'))  # 重複判定の閾値（秒）


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
    
    # 勤怠スケジュールテーブルの作成
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attend_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            work_date TEXT NOT NULL,
            clock_in_time TEXT,
            clock_out_time TEXT,
            break_start_time TEXT,
            break_end_time TEXT,
            overtime_hours REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
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
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_employee_id ON attend_schedule(employee_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_work_date ON attend_schedule(work_date)
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
    勤怠スケジュールを検索するためのページを表示
    
    Returns:
        HTMLテンプレート
    """
    response = make_response(render_template('search.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response





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
    打刻データ受信API（チャタリング防止機能付き）
    クライアントから送信された打刻データをデータベースに保存
    同じIDmからの短時間での連続打刻を検出して重複を防ぐ
    
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
        
        # チャタリング防止チェック
        duplicate_check = check_duplicate_attendance(idm, timestamp, terminal_id)
        if duplicate_check['is_duplicate']:
            print(f"[チャタリング検出] IDm:{idm} | 端末:{terminal_id} | 前回との差:{duplicate_check['time_diff']:.1f}秒")
            return jsonify({
                'status': 'warning',
                'message': 'チャタリング検出：短時間での重複打刻のため無視しました',
                'idm': idm,
                'time_diff': duplicate_check['time_diff'],
                'previous_record_id': duplicate_check['previous_record_id']
            })
        
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


def check_duplicate_attendance(idm, timestamp, terminal_id, threshold_seconds=None):
    """
    チャタリング（重複打刻）をチェック
    
    Args:
        idm (str): カードID
        timestamp (str): 打刻日時
        terminal_id (str): 端末ID
        threshold_seconds (int): 重複判定の閾値（秒）、Noneの場合は設定値を使用
        
    Returns:
        dict: チェック結果
            - is_duplicate (bool): 重複かどうか
            - time_diff (float): 前回打刻との時間差（秒）
            - previous_record_id (int): 前回の記録ID
    """
    if threshold_seconds is None:
        threshold_seconds = CHATTERING_THRESHOLD_SECONDS
        
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 同じIDmの最新の打刻データを取得（同じ端末からのもの）
        cursor.execute("""
            SELECT id, timestamp, received_at
            FROM attendance
            WHERE idm = ? AND terminal_id = ?
            ORDER BY received_at DESC
            LIMIT 1
        """, (idm, terminal_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            # 初回打刻
            return {
                'is_duplicate': False,
                'time_diff': 0,
                'previous_record_id': None
            }
        
        previous_id, previous_timestamp, previous_received = result
        
        # 時刻の解析と比較
        from datetime import datetime
        try:
            current_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            previous_time = datetime.fromisoformat(previous_timestamp.replace('Z', '+00:00'))
        except:
            # ISO形式でない場合の対応
            current_time = datetime.now()
            previous_time = datetime.fromisoformat(previous_received)
        
        time_diff = abs((current_time - previous_time).total_seconds())
        
        # 閾値以内の場合は重複と判定
        is_duplicate = time_diff <= threshold_seconds
        
        return {
            'is_duplicate': is_duplicate,
            'time_diff': time_diff,
            'previous_record_id': previous_id
        }
        
    except Exception as e:
        print(f"[エラー] 重複チェックエラー: {e}")
        # エラーの場合は重複ではないとして処理続行
        return {
            'is_duplicate': False,
            'time_diff': 0,
            'previous_record_id': None
        }


@app.route('/api/search', methods=['GET'])
def search_schedule():
    """
    勤怠スケジュール検索API
    employee_idと検索月を指定して勤怠スケジュールを検索
    検索月はyyyy/mm形式で、前月16日から当月15日までの範囲で検索
    
    Query Parameters:
        employee_id (str): 従業員ID（必須）
        search_month (str): 検索月（yyyy/mm形式、必須）
        limit (int): 取得件数（デフォルト: 100）
    
    Returns:
        JSON: 検索結果
    """
    try:
        # クエリパラメータの取得
        employee_id = request.args.get('employee_id', '').strip()
        search_month = request.args.get('search_month', '').strip()
        limit = request.args.get('limit', '100')
        
        # バリデーション
        if not employee_id:
            return jsonify({
                'status': 'error',
                'message': '従業員IDが指定されていません'
            }), 400
            
        if not search_month:
            return jsonify({
                'status': 'error',
                'message': '検索月が指定されていません（yyyy/mm形式で入力してください）'
            }), 400
        
        # 検索月の解析
        try:
            year, month = search_month.split('/')
            year = int(year)
            month = int(month)
            
            if month < 1 or month > 12:
                raise ValueError("月は1-12の範囲で指定してください")
                
        except ValueError as e:
            return jsonify({
                'status': 'error',
                'message': f'検索月の形式が正しくありません: {str(e)}'
            }), 400
        
        # 検索範囲の計算（前月16日から当月15日）
        from datetime import date, timedelta
        
        # 前月の計算
        if month == 1:
            prev_year = year - 1
            prev_month = 12
        else:
            prev_year = year
            prev_month = month - 1
        
        # 検索範囲の開始日：前月16日
        start_date = date(prev_year, prev_month, 16).strftime('%Y-%m-%d')
        
        # 検索範囲の終了日：当月15日
        end_date = date(year, month, 15).strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # クエリ構築
        query = """
            SELECT id, employee_id, work_date, clock_in_time, clock_out_time, 
                   break_start_time, break_end_time, overtime_hours, notes,
                   created_at, updated_at
            FROM attend_schedule 
            WHERE employee_id = ? 
            AND work_date >= ? 
            AND work_date <= ?
            ORDER BY work_date DESC 
            LIMIT ?
        """
        params = [employee_id, start_date, end_date, int(limit)]
        
        # クエリ実行
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 結果を辞書形式に整形
        results = []
        for row in rows:
            results.append({
                'id': row[0],
                'employee_id': row[1],
                'work_date': row[2],
                'clock_in_time': row[3],
                'clock_out_time': row[4],
                'break_start_time': row[5],
                'break_end_time': row[6],
                'overtime_hours': row[7],
                'notes': row[8],
                'created_at': row[9],
                'updated_at': row[10]
            })
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'count': len(results),
            'search_params': {
                'employee_id': employee_id,
                'search_month': search_month,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                }
            },
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


@app.route('/api/cleanup_duplicates', methods=['POST'])
def cleanup_duplicates():
    """
    重複データクリーンアップAPI
    指定した時間閾値内の重複打刻データを削除する
    管理者用機能
    
    Request Body (JSON):
        {
            "threshold_seconds": 重複判定の閾値（秒）,
            "dry_run": true/false (実際の削除を行うかどうか)
        }
    
    Returns:
        JSON: クリーンアップ結果
    """
    try:
        # JSONデータを取得
        data = request.get_json() or {}
        threshold_seconds = data.get('threshold_seconds', CHATTERING_THRESHOLD_SECONDS)
        dry_run = data.get('dry_run', True)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 重複データを検出
        cursor.execute("""
            SELECT 
                a1.id, a1.idm, a1.timestamp, a1.terminal_id,
                a2.id as prev_id, a2.timestamp as prev_timestamp,
                (julianday(a1.received_at) - julianday(a2.received_at)) * 86400 as time_diff_seconds
            FROM attendance a1
            JOIN attendance a2 ON (
                a1.idm = a2.idm 
                AND a1.terminal_id = a2.terminal_id 
                AND a1.id > a2.id
                AND (julianday(a1.received_at) - julianday(a2.received_at)) * 86400 <= ?
            )
            ORDER BY a1.idm, a1.received_at
        """, (threshold_seconds,))
        
        duplicates = cursor.fetchall()
        
        if not dry_run and duplicates:
            # 実際の削除を実行
            duplicate_ids = [str(d[0]) for d in duplicates]
            placeholders = ','.join(['?'] * len(duplicate_ids))
            cursor.execute(f"DELETE FROM attendance WHERE id IN ({placeholders})", duplicate_ids)
            deleted_count = cursor.rowcount
            conn.commit()
            print(f"[クリーンアップ] {deleted_count}件の重複データを削除しました")
        else:
            deleted_count = 0
        
        conn.close()
        
        # 結果の整形
        duplicate_info = []
        for d in duplicates:
            duplicate_info.append({
                'id': d[0],
                'idm': d[1],
                'timestamp': d[2],
                'terminal_id': d[3],
                'previous_id': d[4],
                'previous_timestamp': d[5],
                'time_diff_seconds': round(d[6], 1)
            })
        
        return jsonify({
            'status': 'success',
            'dry_run': dry_run,
            'threshold_seconds': threshold_seconds,
            'duplicates_found': len(duplicates),
            'deleted_count': deleted_count if not dry_run else 0,
            'duplicates': duplicate_info[:10],  # 最初の10件のみ表示
            'message': f"{'[プレビュー] ' if dry_run else ''}重複データ{len(duplicates)}件を{'検出' if dry_run else '削除'}しました"
        })
    
    except sqlite3.Error as e:
        print(f"[エラー] データベースエラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'データベースエラー: {str(e)}'
        }), 500
    
    except Exception as e:
        print(f"[エラー] クリーンアップエラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'エラー: {str(e)}'
        }), 500


@app.route('/api/sample_data', methods=['POST'])
def add_sample_data():
    """
    サンプルデータ追加API
    テスト用のサンプル勤怠スケジュールデータを追加する
    
    Returns:
        JSON: 追加結果
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # サンプルデータ
        from datetime import date, timedelta
        now = datetime.now()
        
        sample_data = [
            # 従業員ID: EMP001
            {
                'employee_id': 'EMP001',
                'work_date': (date.today() - timedelta(days=5)).strftime('%Y-%m-%d'),
                'clock_in_time': '09:00',
                'clock_out_time': '18:00',
                'break_start_time': '12:00',
                'break_end_time': '13:00',
                'overtime_hours': 0,
                'notes': 'テストデータ1'
            },
            {
                'employee_id': 'EMP001',
                'work_date': (date.today() - timedelta(days=4)).strftime('%Y-%m-%d'),
                'clock_in_time': '09:15',
                'clock_out_time': '18:30',
                'break_start_time': '12:00',
                'break_end_time': '13:00',
                'overtime_hours': 0.5,
                'notes': 'テストデータ2'
            },
            {
                'employee_id': 'EMP001',
                'work_date': (date.today() - timedelta(days=3)).strftime('%Y-%m-%d'),
                'clock_in_time': '08:45',
                'clock_out_time': '17:45',
                'break_start_time': '12:00',
                'break_end_time': '13:00',
                'overtime_hours': 0,
                'notes': 'テストデータ3'
            },
            # 従業員ID: EMP002
            {
                'employee_id': 'EMP002',
                'work_date': (date.today() - timedelta(days=5)).strftime('%Y-%m-%d'),
                'clock_in_time': '10:00',
                'clock_out_time': '19:00',
                'break_start_time': '12:30',
                'break_end_time': '13:30',
                'overtime_hours': 1,
                'notes': 'テストデータ4'
            },
            {
                'employee_id': 'EMP002',
                'work_date': (date.today() - timedelta(days=4)).strftime('%Y-%m-%d'),
                'clock_in_time': '09:30',
                'clock_out_time': '18:15',
                'break_start_time': '12:30',
                'break_end_time': '13:30',
                'overtime_hours': 0,
                'notes': 'テストデータ5'
            },
        ]
        
        # データを挿入
        inserted_count = 0
        for data in sample_data:
            cursor.execute("""
                INSERT INTO attend_schedule 
                (employee_id, work_date, clock_in_time, clock_out_time, 
                 break_start_time, break_end_time, overtime_hours, notes, 
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['employee_id'],
                data['work_date'],
                data['clock_in_time'],
                data['clock_out_time'],
                data['break_start_time'],
                data['break_end_time'],
                data['overtime_hours'],
                data['notes'],
                now.isoformat(),
                now.isoformat()
            ))
            inserted_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': f'{inserted_count}件のサンプルデータを追加しました',
            'inserted_count': inserted_count
        })
    
    except sqlite3.Error as e:
        print(f"[エラー] データベースエラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'データベースエラー: {str(e)}'
        }), 500
    
    except Exception as e:
        print(f"[エラー] サンプルデータ追加エラー: {e}")
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
    print(f"⚡ チャタリング防止: {CHATTERING_THRESHOLD_SECONDS}秒以内の重複を除外")
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
    print("  - 重複削除:       POST /api/cleanup_duplicates")
    print("  - サンプルデータ: POST /api/sample_data")
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

