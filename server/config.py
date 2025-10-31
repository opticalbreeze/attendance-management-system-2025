#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
設定管理モジュール
環境変数とデフォルト値を統合管理
"""

import os
from pathlib import Path


class Config:
    """基本設定クラス"""
    
    # ==================== サーバー設定 ====================
    HOST = os.environ.get('SERVER_HOST', '0.0.0.0')
    PORT = int(os.environ.get('SERVER_PORT', '5000'))
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')
    THREADED = True
    
    # ==================== データベース設定 ====================
    # データベースパス（環境に応じて自動判定）
    @staticmethod
    def _get_database_path():
        """環境に応じたデータベースパスを取得（内部関数）"""
        if 'DATABASE_PATH' in os.environ:
            return os.environ['DATABASE_PATH']
        
        # Docker環境（volume mount: ./data:/data）
        if os.path.exists('/data'):
            return '/data/attendance.db'
        
        # ローカル開発環境
        elif os.path.exists('./data'):
            return './data/attendance.db'
        
        # フォールバック（カレントディレクトリ）
        else:
            return 'attendance.db'
    
    DATABASE_PATH = _get_database_path()
    
    # ==================== チャタリング防止設定 ====================
    CHATTERING_THRESHOLD_SECONDS = int(os.environ.get('CHATTERING_THRESHOLD', '10'))
    
    # ==================== API設定 ====================
    API_VERSION = os.environ.get('API_VERSION', '1.0.0')
    DEFAULT_SEARCH_LIMIT = int(os.environ.get('DEFAULT_SEARCH_LIMIT', '100'))
    STATS_LATEST_RECORDS = int(os.environ.get('STATS_LATEST_RECORDS', '10'))
    
    # ==================== 給与計算期間設定 ====================
    PAYROLL_START_DAY = int(os.environ.get('PAYROLL_START_DAY', '16'))  # 前月16日
    PAYROLL_END_DAY = int(os.environ.get('PAYROLL_END_DAY', '15'))      # 当月15日
    
    # ==================== バリデーション設定 ====================
    EMPLOYEE_ID_MIN_LENGTH = int(os.environ.get('EMPLOYEE_ID_MIN_LENGTH', '3'))
    EMPLOYEE_ID_MAX_LENGTH = int(os.environ.get('EMPLOYEE_ID_MAX_LENGTH', '20'))
    YEAR_MIN = int(os.environ.get('YEAR_MIN', '2000'))
    YEAR_MAX = int(os.environ.get('YEAR_MAX', '2100'))
    
    # ==================== Flask設定 ====================
    TEMPLATES_AUTO_RELOAD = True
    JSON_AS_ASCII = False  # 日本語JSON対応
    JSONIFY_PRETTYPRINT_REGULAR = False
    
    # ==================== セキュリティ設定 ====================
    # 本番環境では以下を設定推奨
    # SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
    # SESSION_COOKIE_SECURE = True  # HTTPS必須
    # SESSION_COOKIE_HTTPONLY = True


class DevelopmentConfig(Config):
    """開発環境設定"""
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(Config):
    """本番環境設定"""
    DEBUG = False
    TEMPLATES_AUTO_RELOAD = False
    
    # 本番環境での追加設定例
    # SECRET_KEY = os.environ.get('SECRET_KEY')
    # if not SECRET_KEY:
    #     raise ValueError("本番環境ではSECRET_KEYの設定が必須です")


class DockerConfig(Config):
    """Docker環境設定"""
    # Docker環境では環境変数から読み込む
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')
    DATABASE_PATH = '/data/attendance.db'  # Docker volume mount パス


# 環境に応じた設定を自動選択
def get_config():
    """
    環境変数から設定クラスを選択
    優先順位: DOCKER > PRODUCTION > DEVELOPMENT
    """
    env = os.environ.get('FLASK_ENV', '').lower()
    
    if os.path.exists('/data') or env == 'docker':
        return DockerConfig
    elif env == 'production':
        return ProductionConfig
    else:
        return DevelopmentConfig


# デフォルト設定インスタンス
config = get_config()

