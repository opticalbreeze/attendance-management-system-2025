#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
開発用認証モジュール - 認証を無効化
"""

from functools import wraps
from flask import request, session, redirect, url_for, jsonify
import os
from config import Config

def init_auth(app):
    """
    認証機能を初期化（開発モード：無効化）
    
    Args:
        app: Flaskアプリケーションインスタンス
    """
    # セッション用のシークレットキー
    app.secret_key = os.environ.get('SECRET_KEY', Config.SECRET_KEY if hasattr(Config, 'SECRET_KEY') else 'dev-secret-key')

def verify_admin_password(password):
    """
    管理者パスワードを検証（開発モード：常にTrue）
    
    Args:
        password: 入力されたパスワード
    
    Returns:
        bool: 常にTrue
    """
    return True

def verify_db_password(password):
    """
    データベースアクセスパスワードを検証（開発モード：常にTrue）
    
    Args:
        password: 入力されたパスワード
    
    Returns:
        bool: 常にTrue
    """
    return True

def login_required(f):
    """
    ログイン不要デコレータ（開発モード）
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 認証を通す
        return f(*args, **kwargs)
    return decorated_function

def db_access_required(f):
    """
    データベースアクセス不要デコレータ（開発モード）
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # アクセス権限を通す
        return f(*args, **kwargs)
    return decorated_function

def set_db_access_granted():
    """データベースアクセス権限を設定（開発モード：常に権限あり）"""
    return True

def get_admin_status():
    """管理者ログイン状態を取得（開発モード：常にログイン中）"""
    return {
        'logged_in': True,
        'user': 'dev_admin'
    }