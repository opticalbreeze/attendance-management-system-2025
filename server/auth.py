#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
認証・認可モジュール
管理画面へのアクセス制御とセッション管理
"""

from functools import wraps
from flask import request, session, redirect, url_for, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import os
from config import Config

# 管理者パスワード（環境変数から取得、デフォルトは'admin'）
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', Config.ADMIN_PASSWORD)
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')
if not ADMIN_PASSWORD_HASH:
    # 環境変数から直接パスワードを取得してハッシュ化
    ADMIN_PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD)

# データベースアクセスパスワード（環境変数から取得）
DB_PASSWORD = os.environ.get('DB_PASSWORD', Config.DB_PASSWORD)
DB_ACCESS_PASSWORD_HASH = os.environ.get('DB_ACCESS_PASSWORD_HASH')
if not DB_ACCESS_PASSWORD_HASH:
    # 環境変数から直接パスワードを取得してハッシュ化
    DB_ACCESS_PASSWORD_HASH = generate_password_hash(DB_PASSWORD)

def init_auth(app):
    """
    認証機能を初期化
    
    Args:
        app: Flaskアプリケーションインスタンス
    """
    # セッション用のシークレットキー
    app.secret_key = os.environ.get('SECRET_KEY', Config.SECRET_KEY if hasattr(Config, 'SECRET_KEY') else 'dev-secret-key-change-in-production')
    
    # セッション設定
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    # HTTPS環境では以下を有効化
    # app.config['SESSION_COOKIE_SECURE'] = True

def verify_admin_password(password):
    """
    管理者パスワードを検証
    
    Args:
        password: 入力されたパスワード
    
    Returns:
        bool: パスワードが正しい場合True
    """
    return check_password_hash(ADMIN_PASSWORD_HASH, password)

def verify_db_password(password):
    """
    データベースアクセスパスワードを検証
    
    Args:
        password: 入力されたパスワード
    
    Returns:
        bool: パスワードが正しい場合True
    """
    return check_password_hash(DB_ACCESS_PASSWORD_HASH, password)

def login_required(f):
    """
    ログインが必要なページを保護するデコレータ
    
    使用例:
        @app.route('/admin')
        @login_required
        def admin_page():
            return render_template('admin.html')
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session.get('admin_logged_in'):
            if request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'ログインが必要です'
                }), 401
            # ログインページにリダイレクト（nextパラメータで元のURLを保持）
            next_url = request.url
            return redirect(f'/login?next={next_url}')
        return f(*args, **kwargs)
    return decorated_function

def db_access_required(f):
    """
    データベースアクセス権限が必要なAPIを保護するデコレータ
    
    使用例:
        @app.route('/api/admin/db')
        @db_access_required
        def db_admin():
            # データベース管理操作
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'db_access_granted' not in session or not session.get('db_access_granted'):
            return jsonify({
                'status': 'error',
                'message': 'データベースアクセス権限が必要です'
            }), 403
        return f(*args, **kwargs)
    return decorated_function

def check_db_access():
    """
    データベースアクセス権限をチェック
    
    Returns:
        bool: アクセス権限がある場合True
    """
    return session.get('db_access_granted', False)

def set_db_access_granted(granted=True):
    """
    データベースアクセス権限をセッションに設定
    
    Args:
        granted: 権限を付与するかどうか
    """
    session['db_access_granted'] = granted
    session.permanent = True

