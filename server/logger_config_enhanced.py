#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拡張ログ設定モジュール
構造化ログとエラー・警告専用ロガーを提供
"""

import logging
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class StructuredFormatter(logging.Formatter):
    """JSON形式の構造化ログフォーマッター"""
    
    def format(self, record: logging.LogRecord) -> str:
        """ログレコードをJSON形式に変換"""
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # エラー情報を追加
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else 'Unknown',
                'message': str(record.exc_info[1]) if record.exc_info[1] else '',
                'traceback': self.formatException(record.exc_info)
            }
        
        # 追加のコンテキスト情報
        if hasattr(record, 'context'):
            log_data['context'] = record.context
        
        # エラー・警告の分類
        if record.levelname in ['ERROR', 'WARNING', 'CRITICAL']:
            log_data['category'] = self._categorize_error(record)
            log_data['severity'] = self._get_severity(record)
        
        # リクエスト情報（Flask使用時）
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'employee_id'):
            log_data['employee_id'] = record.employee_id
        
        return json.dumps(log_data, ensure_ascii=False)
    
    def _categorize_error(self, record: logging.LogRecord) -> str:
        """エラーをカテゴリ分類"""
        message = record.getMessage().lower()
        
        if any(keyword in message for keyword in ['database', 'sql', 'db', 'sqlite']):
            return 'database'
        elif any(keyword in message for keyword in ['api', 'http', 'request', 'response']):
            return 'api'
        elif any(keyword in message for keyword in ['attendance', '打刻', '勤怠']):
            return 'attendance'
        elif any(keyword in message for keyword in ['notification', 'お知らせ', '通知']):
            return 'notification'
        elif any(keyword in message for keyword in ['overtime', '時間外']):
            return 'overtime'
        elif any(keyword in message for keyword in ['schedule', 'スケジュール']):
            return 'schedule'
        else:
            return 'general'
    
    def _get_severity(self, record: logging.LogRecord) -> str:
        """重要度を判定"""
        if record.levelname == 'CRITICAL':
            return 'critical'
        elif record.levelname == 'ERROR':
            return 'high'
        elif record.levelname == 'WARNING':
            return 'medium'
        else:
            return 'low'


def setup_enhanced_logger(
    name: Optional[str] = None,
    log_level: Optional[str] = None,
    enable_file_logging: bool = True,
    enable_separated_logs: bool = True
) -> logging.Logger:
    """
    拡張ロガーを設定して取得
    
    Args:
        name: ロガー名（Noneの場合はモジュール名）
        log_level: ログレベル（Noneの場合は環境変数から取得）
        enable_file_logging: ファイルログを有効にするか
        enable_separated_logs: エラー・警告専用ログを有効にするか
    
    Returns:
        logging.Logger: 設定済みロガー
    """
    if log_level is None:
        log_level_str = os.environ.get('LOG_LEVEL', 'INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
    
    logger = logging.getLogger(name or __name__)
    
    # 既にハンドラーが設定されている場合はスキップ
    if logger.handlers:
        return logger
    
    logger.setLevel(log_level)
    
    # ログディレクトリの作成
    log_dir = Path('logs')
    if enable_file_logging or enable_separated_logs:
        log_dir.mkdir(exist_ok=True)
    
    # コンソールハンドラー（構造化ログ形式）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # 開発環境では読みやすい形式、本番環境ではJSON形式
    if os.environ.get('FLASK_ENV') == 'development':
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_formatter = StructuredFormatter()
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラー（全ログ）
    if enable_file_logging:
        log_file = os.environ.get('LOG_FILE_PATH', str(log_dir / 'app.log'))
        try:
            log_file_path = Path(log_file)
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(StructuredFormatter())
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"ログファイルの設定に失敗しました: {e}")
    
    # エラー・警告専用ロガー
    if enable_separated_logs:
        setup_separated_loggers(log_dir)
    
    return logger


def setup_separated_loggers(log_dir: Path):
    """ログレベル別のロガーを設定"""
    
    # エラー専用ロガー
    error_logger = logging.getLogger('errors')
    if not error_logger.handlers:
        error_log_path = log_dir / 'errors.jsonl'
        error_handler = logging.FileHandler(error_log_path, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        error_logger.addHandler(error_handler)
        error_logger.setLevel(logging.ERROR)
    
    # 警告専用ロガー
    warning_logger = logging.getLogger('warnings')
    if not warning_logger.handlers:
        warning_log_path = log_dir / 'warnings.jsonl'
        warning_handler = logging.FileHandler(warning_log_path, encoding='utf-8')
        warning_handler.setLevel(logging.WARNING)
        warning_handler.setFormatter(StructuredFormatter())
        warning_logger.addHandler(warning_handler)
        warning_logger.setLevel(logging.WARNING)
    
    # デバッグ専用ロガー（開発環境のみ）
    if os.environ.get('FLASK_ENV') == 'development':
        debug_logger = logging.getLogger('debug')
        if not debug_logger.handlers:
            debug_log_path = log_dir / 'debug.jsonl'
            debug_handler = logging.FileHandler(debug_log_path, encoding='utf-8')
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(StructuredFormatter())
            debug_logger.addHandler(debug_handler)
            debug_logger.setLevel(logging.DEBUG)


class ContextLogger:
    """コンテキスト情報を付与できるロガーラッパー"""
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
    
    def _add_context(self, record: logging.LogRecord):
        """ログレコードにコンテキスト情報を追加"""
        for key, value in self.context.items():
            setattr(record, key, value)
    
    def debug(self, msg, *args, **kwargs):
        if self.logger.isEnabledFor(logging.DEBUG):
            record = self.logger.makeRecord(
                self.logger.name, logging.DEBUG, '', 0, msg, args, None
            )
            self._add_context(record)
            self.logger.handle(record)
    
    def info(self, msg, *args, **kwargs):
        if self.logger.isEnabledFor(logging.INFO):
            record = self.logger.makeRecord(
                self.logger.name, logging.INFO, '', 0, msg, args, None
            )
            self._add_context(record)
            self.logger.handle(record)
    
    def warning(self, msg, *args, **kwargs):
        if self.logger.isEnabledFor(logging.WARNING):
            record = self.logger.makeRecord(
                self.logger.name, logging.WARNING, '', 0, msg, args, None
            )
            self._add_context(record)
            self.logger.handle(record)
            # 警告専用ロガーにも出力
            warnings_logger = logging.getLogger('warnings')
            warnings_logger.warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        if self.logger.isEnabledFor(logging.ERROR):
            record = self.logger.makeRecord(
                self.logger.name, logging.ERROR, '', 0, msg, args, None
            )
            self._add_context(record)
            self.logger.handle(record)
            # エラー専用ロガーにも出力
            errors_logger = logging.getLogger('errors')
            errors_logger.error(msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        if self.logger.isEnabledFor(logging.CRITICAL):
            record = self.logger.makeRecord(
                self.logger.name, logging.CRITICAL, '', 0, msg, args, None
            )
            self._add_context(record)
            self.logger.handle(record)
            # エラー専用ロガーにも出力
            errors_logger = logging.getLogger('errors')
            errors_logger.critical(msg, *args, **kwargs)


# 使用例
if __name__ == '__main__':
    # 基本的な使用方法
    logger = setup_enhanced_logger('test_logger')
    logger.info('通常のログメッセージ')
    logger.warning('警告メッセージ')
    logger.error('エラーメッセージ')
    
    # コンテキスト付きロガー
    context_logger = ContextLogger(logger, employee_id='12345', request_id='req-001')
    context_logger.info('従業員の処理を開始')
    context_logger.error('処理中にエラーが発生')
