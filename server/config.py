#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
設定管理モジュール
環境変数とデフォルト値を統合管理
"""

import os


class Config:
    """基本設定クラス"""
    
    # ==================== サーバー設定 ====================
    HOST = os.environ.get('SERVER_HOST', '0.0.0.0')
    PORT = int(os.environ.get('SERVER_PORT', '5000'))
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')  # 開発環境ではデフォルト有効
    THREADED = True
    
    # ==================== データベース設定 ====================
    # データベースパス（Dockerの外、attendance/dataフォルダに配置）
    # ローカル開発: ../../data/attendance.db (work_attend_server/server/ から見て)
    # Docker環境: /app/data/attendance.db（ホストの attendance/data にマウント）
    DATABASE_PATH = os.environ.get('DATABASE_PATH', '../../data/attendance.db')
    
    # ==================== PDF保存設定 ====================
    # PDF保存先パス（環境変数から取得、未設定の場合はデータベースと同じディレクトリのPDFフォルダを使用）
    # Docker環境: /app/data/PDF（ホストの attendance/data/PDF にマウント）
    # ローカル環境: データベースパスと同じディレクトリのPDFフォルダ
    PDF_SAVE_DIR = os.environ.get('PDF_SAVE_DIR', '')  # 空の場合はutils.pyで自動計算
    
    # ==================== チャタリング防止設定 ====================
    CHATTERING_THRESHOLD_SECONDS = int(os.environ.get('CHATTERING_THRESHOLD', '10'))
    
    # ==================== API設定 ====================
    API_VERSION = os.environ.get('API_VERSION', '1.0.0')
    DEFAULT_SEARCH_LIMIT = int(os.environ.get('DEFAULT_SEARCH_LIMIT', '100'))
    STATS_LATEST_RECORDS = int(os.environ.get('STATS_LATEST_RECORDS', '10'))
    
    # ==================== 給与計算期間設定 ====================
    PAYROLL_START_DAY = int(os.environ.get('PAYROLL_START_DAY', '16'))  # 前月16日
    PAYROLL_END_DAY = int(os.environ.get('PAYROLL_END_DAY', '15'))      # 当月15日
    
    # ==================== CSVインポート設定 ====================
    DEFAULT_SHEET_NUMBER = os.environ.get('DEFAULT_SHEET_NUMBER', '1')  # デフォルトのシート番号
    
    # ==================== ログ設定 ====================
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')  # ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    LOG_FILE_PATH = os.environ.get('LOG_FILE_PATH', '')  # ログファイルパス（空の場合はファイル出力なし）
    
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
    # セッション用シークレットキー（本番環境では必ず変更）
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production-please-set-in-env')
    
    # 管理者パスワード（環境変数 ADMIN_PASSWORD から設定、デフォルト: 'admin'）
    # 本番環境では必ず環境変数で設定してください
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')
    
    # データベースアクセスパスワード（環境変数 DB_PASSWORD から設定、デフォルト: 'dbadmin'）
    # 本番環境では必ず環境変数で設定してください
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'dbadmin')
    
    # セッション設定
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # HTTPS環境では以下を有効化
    # SESSION_COOKIE_SECURE = True  # HTTPS必須


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


# 環境に応じた設定を自動選択
def get_config():
    """
    環境変数から設定クラスを選択
    優先順位: PRODUCTION > DOCKER > DEVELOPMENT
    """
    env = os.environ.get('FLASK_ENV', '').lower()
    
    if env == 'production':
        return ProductionConfig
    elif env == 'docker':
        return DockerConfig
    else:
        return DevelopmentConfig


# デフォルト設定インスタンス
config = get_config()

