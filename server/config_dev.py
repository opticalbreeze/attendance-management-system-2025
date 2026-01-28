#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
開発環境用設定
本番環境と開発環境を区別して設定を管理
"""

import os
from config import Config


class DevelopmentConfig(Config):
    """開発環境用設定"""
    
    # ==================== 開発環境固有設定 ====================
    DEBUG = True
    DEVELOPMENT = True
    
    # 開発用ログ設定
    LOG_LEVEL = 'DEBUG'
    LOG_FILE_PATH = '/app/logs/dev_server.log'  # コンテナ内パス
    
    # 開発用セッション設定（セキュリティを緩める）
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SESSION_COOKIE_SECURE = False  # 開発環境ではHTTPでOK
    
    # ==================== データベース設定（本番と共有） ====================
    # データベースパスは本番と同じ（共有DB）
    DATABASE_PATH = os.environ.get('DATABASE_PATH', '/app/data/attendance.db')
    PDF_SAVE_DIR = os.environ.get('PDF_SAVE_DIR', '/app/data/PDF')
    
    # ==================== 開発用機能設定 ====================
    # お知らせ機能のテスト用設定
    NOTIFICATION_TEST_MODE = True  # テストユーザー用の通知を有効
    NOTIFICATION_CHECK_INTERVAL = 60  # 通知チェック間隔（秒）
    
    # API レスポンス設定
    JSON_AS_ASCII = False
    TEMPLATES_AUTO_RELOAD = True
    
    # セキュリティ設定（開発環境用）
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class ProductionConfig(Config):
    """本番環境用設定"""
    
    DEBUG = False
    DEVELOPMENT = False
    
    # セキュリティ強化
    SESSION_COOKIE_SECURE = True  # HTTPS必須
    SECRET_KEY = os.environ.get('SECRET_KEY')  # 環境変数から必須取得
    
    # 本番用ログ設定
    LOG_LEVEL = 'INFO'
    LOG_FILE_PATH = '/app/logs/server.log'


def get_config():
    """環境に応じた設定を取得"""
    if os.environ.get('DEV_MODE', '').lower() in ('true', '1', 'yes'):
        return DevelopmentConfig
    else:
        return ProductionConfig