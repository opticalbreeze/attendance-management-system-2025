#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打刻システム - メインサーバー（リファクタリング版）
簡潔で保守しやすい構造
"""

from flask import Flask, render_template, make_response

# カスタムモジュール
from config import Config
from database import init_database
from api import register_api_routes

def create_app():
    """Flaskアプリケーションを作成・設定"""
    app = Flask(__name__)
    app.config['TEMPLATES_AUTO_RELOAD'] = Config.TEMPLATES_AUTO_RELOAD
    app.config['JSON_AS_ASCII'] = Config.JSON_AS_ASCII
    
    return app

def register_web_routes(app):
    """Webページのルートを登録"""
    
    @app.route('/')
    def index():
        """トップページ"""
        return render_template('index.html')

    @app.route('/search')
    def search_page():
        """検索ページ"""
        # キャッシュ制御ヘッダーを追加（開発時のブラウザキャッシュ問題対策）
        response = make_response(render_template('search.html'))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.route('/check')
    def check_page():
        """勤怠チェックページ"""
        # キャッシュ制御ヘッダーを追加（開発時のブラウザキャッシュ問題対策）
        response = make_response(render_template('check.html'))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

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
    print()
    print("[API エンドポイント]")
    print("  - ヘルスチェック: GET  /api/health")
    print("  - 打刻データ受信: POST /api/attendance")
    print("  - データ検索:     GET  /api/search")
    print("  - 統計情報:       GET  /api/stats")
    print("  - 重複削除:       POST /api/cleanup_duplicates")
    print("  - サンプルデータ: POST /api/sample_data")
    print("  - 勤怠チェック:   GET  /api/attendance_check")
    print("=" * 79)
    print()

def main():
    """メイン関数"""
    # アプリケーション作成
    app = create_app()
    
    # データベース初期化
    init_database()
    
    # ルート登録
    register_web_routes(app)
    register_api_routes(app)
    
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