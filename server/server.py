#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打刻システム - メインサーバー（リファクタリング版）
簡潔で保守しやすい構造
"""

from flask import Flask, render_template, make_response, request, jsonify, session, redirect, send_file
import os
import csv
from datetime import datetime
from werkzeug.utils import secure_filename

# カスタムモジュール
from config import Config
from database import init_database
from api_attendance import register_attendance_api_routes
from api_overtime import register_overtime_api_routes
from api_leave import register_leave_api_routes
from api_monthly_report import register_monthly_report_api_routes
from api_check_status import register_check_status_api_routes
from auth import init_auth, login_required, verify_admin_password, verify_db_password, set_db_access_granted
from utils import get_database_connection
from logger_config import setup_logger

logger = setup_logger(__name__)

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
    
    @app.route('/admin')
    @login_required
    def admin_page():
        """管理者ページ"""
        return _add_no_cache_headers(make_response(render_template('admin.html')))
    
    @app.route('/attendance-check')
    @login_required
    def attendance_check_page():
        """打刻チェック確認ページ（管理者専用）"""
        return _add_no_cache_headers(make_response(render_template('attendance_check.html')))


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
                session['admin_user_id'] = 'admin'  # 管理者IDをセッションに保存
                session['admin_username'] = '管理者'  # 管理者名をセッションに保存
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
            logger.error(f"ログインエラー: {e}", exc_info=True)
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

def print_startup_info():
    """起動時の情報を表示"""
    logger.info("=" * 79)
    logger.info("打刻システム - サーバー（改善版）")
    logger.info("=" * 79)
    logger.info("")
    
    # データベース情報
    logger.info(f"データベース: {Config.DATABASE_PATH}")
    
    # サーバー情報
    logger.info(f"サーバー起動: http://{Config.HOST}:{Config.PORT}")
    
    # チャタリング設定
    logger.info(f"チャタリング防止: {Config.CHATTERING_THRESHOLD_SECONDS}秒以内の重複を除外")
    logger.info("")
    
    logger.info("[アクセス方法]")
    logger.info(f"  - ローカル: http://localhost:{Config.PORT}")
    logger.info(f"  - ネットワーク: http://<サーバーのIPアドレス>:{Config.PORT}")
    logger.info("")
    
    logger.info("[Web ページ]")
    logger.info("  - トップページ:   GET  /")
    logger.info("  - 検索ページ:     GET  /search")
    logger.info("  - 勤怠チェック:   GET  /check")
    logger.info("  - 時間外申告:     GET  /overtime")
    logger.info("  - 時間外一覧:     GET  /overtime/list")
    logger.info("  - 時間外確認:     GET  /overtime/check")
    logger.info("  - 休暇願申告:     GET  /leave")
    logger.info("  - 休暇願一覧:     GET  /leave/list")
    logger.info("  - 休暇願確認:     GET  /leave/check")
    logger.info("")
    logger.info("[API エンドポイント]")
    logger.info("  - ヘルスチェック: GET  /api/health")
    logger.info("  - 打刻データ受信: POST /api/attendance")
    logger.info("  - データ検索:     GET  /api/search")
    logger.info("  - 統計情報:       GET  /api/stats")
    logger.info("  - 重複削除:       POST /api/cleanup_duplicates")
    logger.info("  - 勤怠チェック:   GET  /api/attendance_check")
    logger.info("  - 時間外申告:     POST /api/overtime")
    logger.info("  - 時間外取得:     GET  /api/overtime")
    logger.info("  - 時間外承認:     POST /api/overtime/<id>/approve")
    logger.info("  - 時間外却下:     POST /api/overtime/<id>/reject")
    logger.info("  - 月次集計:       GET  /api/overtime/monthly_summary")
    logger.info("  - CSV アップロード: POST /api/admin/csv/upload")
    logger.info("  - DB統計情報:     GET  /api/admin/database/stats")
    logger.info("=" * 79)
    logger.info("")

# 管理者機能はadmin.pyに統合（重複を避けるため）
from admin import register_admin_api_routes

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
    register_monthly_report_api_routes(app)
    register_check_status_api_routes(app)  # 打刻チェック状況管理API
    register_admin_api_routes(app)  # 管理者機能を有効化
    
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