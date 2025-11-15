#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打刻システム - メインサーバー（リファクタリング版）
簡潔で保守しやすい構造
"""

from flask import Flask, render_template, make_response, request, jsonify, session, redirect, url_for, send_file
import os

# カスタムモジュール
from config import Config
from database import init_database
from api_attendance import register_attendance_api_routes
from api_overtime import register_overtime_api_routes
from api_leave import register_leave_api_routes
from auth import init_auth, login_required, verify_admin_password, verify_db_password, set_db_access_granted
from monthly_report import generate_monthly_report_excel, get_monthly_attendance_data

def create_app():
    """Flaskアプリケーションを作成・設定"""
    app = Flask(__name__)
    app.config['TEMPLATES_AUTO_RELOAD'] = Config.TEMPLATES_AUTO_RELOAD
    app.config['JSON_AS_ASCII'] = Config.JSON_AS_ASCII
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    app.config['SESSION_COOKIE_HTTPONLY'] = Config.SESSION_COOKIE_HTTPONLY
    app.config['SESSION_COOKIE_SAMESITE'] = Config.SESSION_COOKIE_SAMESITE
    
    # 認証機能を初期化
    init_auth(app)
    
    return app

def _add_no_cache_headers(response):
    """キャッシュ制御ヘッダーを追加（開発時のブラウザキャッシュ問題対策）"""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

def register_web_routes(app):
    """Webページのルートを登録"""
    
    @app.route('/')
    def index():
        """トップページ"""
        return render_template('index.html')

    @app.route('/login')
    def login_page():
        """ログインページ"""
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        """ログアウト"""
        session.clear()
        return redirect('/')

    @app.route('/search')
    @login_required
    def search_page():
        """検索ページ（管理画面）"""
        return _add_no_cache_headers(make_response(render_template('search.html')))

    @app.route('/check')
    @login_required
    def check_page():
        """勤怠チェックページ（管理画面）"""
        return _add_no_cache_headers(make_response(render_template('check.html')))

    @app.route('/overtime')
    def overtime_page():
        """時間外申告ページ（一般ユーザー可）"""
        return _add_no_cache_headers(make_response(render_template('overtime.html')))

    @app.route('/overtime/list')
    @login_required
    def overtime_list_page():
        """時間外申告一覧ページ（管理画面）"""
        return _add_no_cache_headers(make_response(render_template('overtime_list.html')))

    @app.route('/overtime/check')
    def overtime_check_page():
        """時間外申告確認ページ（個人用）"""
        return _add_no_cache_headers(make_response(render_template('overtime_check.html')))

    @app.route('/leave')
    def leave_page():
        """休暇願申告ページ（一般ユーザー可）"""
        return _add_no_cache_headers(make_response(render_template('leave.html')))

    @app.route('/leave/check')
    def leave_check_page():
        """休暇願確認ページ（個人用）"""
        return _add_no_cache_headers(make_response(render_template('leave_check.html')))

    @app.route('/leave/list')
    @login_required
    def leave_list_page():
        """休暇願一覧ページ（管理用）"""
        return _add_no_cache_headers(make_response(render_template('leave_list.html')))
    
    @app.route('/monthly-report')
    @login_required
    def monthly_report_page():
        """月間集計レポートページ"""
        return _add_no_cache_headers(make_response(render_template('monthly_report.html')))

def register_auth_routes(app):
    """認証関連のAPIルートを登録"""
    
    @app.route('/api/login', methods=['POST'])
    def login_api():
        """ログインAPI"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'データが送信されていません'
                }), 400
            
            password = data.get('password', '').strip()
            db_access = data.get('db_access', False)
            
            if not password:
                return jsonify({
                    'status': 'error',
                    'message': 'パスワードを入力してください'
                }), 400
            
            # 管理者パスワードを検証
            if verify_admin_password(password):
                session['admin_logged_in'] = True
                session.permanent = True
                
                # データベースアクセス権限の設定
                if db_access:
                    # データベースパスワードも検証
                    db_password = data.get('db_password', '').strip()
                    if db_password and verify_db_password(db_password):
                        set_db_access_granted(True)
                    else:
                        # DBパスワードが提供されていない、または間違っている
                        set_db_access_granted(False)
                else:
                    set_db_access_granted(False)
                
                return jsonify({
                    'status': 'success',
                    'message': 'ログインに成功しました',
                    'db_access': session.get('db_access_granted', False)
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'パスワードが正しくありません'
                }), 401
                
        except Exception as e:
            print(f"[エラー] ログインエラー: {e}")
            return jsonify({
                'status': 'error',
                'message': f'エラー: {str(e)}'
            }), 500
    
    @app.route('/api/logout', methods=['POST'])
    def logout_api():
        """ログアウトAPI"""
        session.clear()
        return jsonify({
            'status': 'success',
            'message': 'ログアウトしました'
        })
    
    @app.route('/api/auth/check', methods=['GET'])
    def check_auth():
        """認証状態確認API"""
        return jsonify({
            'status': 'success',
            'logged_in': session.get('admin_logged_in', False),
            'db_access': session.get('db_access_granted', False)
        })
    
    @app.route('/api/monthly-report/generate', methods=['POST'])
    @login_required
    def generate_monthly_report_api():
        """月間集計レポート生成API"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'データが送信されていません'
                }), 400
            
            employee_id = data.get('employee_id', '').strip()
            search_month = data.get('search_month', '').strip()
            
            if not employee_id:
                return jsonify({
                    'status': 'error',
                    'message': '従業員番号を指定してください'
                }), 400
            
            if not search_month:
                return jsonify({
                    'status': 'error',
                    'message': '検索月を指定してください（YYYY/MM形式）'
                }), 400
            
            # Excelファイル生成
            output_path = generate_monthly_report_excel(employee_id, search_month)
            
            if not output_path or not os.path.exists(output_path):
                return jsonify({
                    'status': 'error',
                    'message': 'ファイルの生成に失敗しました'
                }), 500
            
            # ファイル名を取得
            filename = os.path.basename(output_path)
            
            return jsonify({
                'status': 'success',
                'message': 'レポートを生成しました',
                'filename': filename,
                'download_url': f'/api/monthly-report/download/{filename}'
            })
            
        except Exception as e:
            print(f"[エラー] 月間レポート生成エラー: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'status': 'error',
                'message': f'エラー: {str(e)}'
            }), 500
    
    @app.route('/api/monthly-report/download/<filename>', methods=['GET'])
    @login_required
    def download_monthly_report(filename):
        """月間集計レポートダウンロードAPI"""
        try:
            # ファイルパス構築
            output_dir = Config.PDF_SAVE_DIR.replace('PDF', 'reports')
            file_path = os.path.join(output_dir, filename)
            
            if not os.path.exists(file_path):
                return jsonify({
                    'status': 'error',
                    'message': 'ファイルが見つかりません'
                }), 404
            
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
        except Exception as e:
            print(f"[エラー] ファイルダウンロードエラー: {e}")
            return jsonify({
                'status': 'error',
                'message': f'エラー: {str(e)}'
            }), 500
    
    @app.route('/api/monthly-report/preview', methods=['GET'])
    @login_required
    def preview_monthly_report_api():
        """月間集計レポートプレビューAPI"""
        try:
            employee_id = request.args.get('employee_id', '').strip()
            search_month = request.args.get('search_month', '').strip()
            
            if not employee_id or not search_month:
                return jsonify({
                    'status': 'error',
                    'message': '従業員番号と検索月を指定してください'
                }), 400
            
            # データ取得
            data = get_monthly_attendance_data(employee_id, search_month)
            
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'データが見つかりません'
                }), 404
            
            return jsonify({
                'status': 'success',
                'data': data
            })
            
        except Exception as e:
            print(f"[エラー] プレビュー取得エラー: {e}")
            return jsonify({
                'status': 'error',
                'message': f'エラー: {str(e)}'
            }), 500

def print_startup_info():
    """起動時の情報を表示"""
    print("=" * 79)
    print("🔖 打刻システム - サーバー（改善版）")
    print("=" * 79)
    print()
    
    # データベース情報
    print(f"📁 データベース: {Config.DATABASE_PATH}")
    
    # サーバー情報
    print(f"🌐 サーバー起動: http://{Config.HOST}:{Config.PORT}")
    
    # チャタリング設定
    print(f"⚡ チャタリング防止: {Config.CHATTERING_THRESHOLD_SECONDS}秒以内の重複を除外")
    print()
    
    print("[アクセス方法]")
    print(f"  - ローカル: http://localhost:{Config.PORT}")
    print(f"  - ネットワーク: http://<サーバーのIPアドレス>:{Config.PORT}")
    print()
    
    print("[Web ページ]")
    print("  - トップページ:   GET  /")
    print("  - 検索ページ:     GET  /search")
    print("  - 勤怠チェック:   GET  /check")
    print("  - 時間外申告:     GET  /overtime")
    print("  - 時間外一覧:     GET  /overtime/list")
    print("  - 時間外確認:     GET  /overtime/check")
    print("  - 休暇願申告:     GET  /leave")
    print("  - 休暇願一覧:     GET  /leave/list")
    print("  - 休暇願確認:     GET  /leave/check")
    print()
    print("[API エンドポイント]")
    print("  - ヘルスチェック: GET  /api/health")
    print("  - 打刻データ受信: POST /api/attendance")
    print("  - データ検索:     GET  /api/search")
    print("  - 統計情報:       GET  /api/stats")
    print("  - 重複削除:       POST /api/cleanup_duplicates")
    print("  - サンプルデータ: POST /api/sample_data")
    print("  - 勤怠チェック:   GET  /api/attendance_check")
    print("  - 時間外申告:     POST /api/overtime")
    print("  - 時間外取得:     GET  /api/overtime")
    print("  - 時間外承認:     POST /api/overtime/<id>/approve")
    print("  - 時間外却下:     POST /api/overtime/<id>/reject")
    print("  - 月次集計:       GET  /api/overtime/monthly_summary")
    print("=" * 79)
    print()

def main():
    """メイン関数"""
    # アプリケーション作成
    app = create_app()
    
    # データベース初期化（全テーブルを一元管理）
    init_database()
    
    # ルート登録
    register_web_routes(app)
    register_auth_routes(app)
    register_attendance_api_routes(app)
    register_overtime_api_routes(app)
    register_leave_api_routes(app)
    
    # 起動情報表示
    print_startup_info()
    
    # サーバー起動
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        threaded=Config.THREADED
    )

if __name__ == '__main__':
    main()