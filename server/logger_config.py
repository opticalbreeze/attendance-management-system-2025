#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ログ設定モジュール
loggingモジュールの設定とロガーの取得を提供
"""

import logging
import os
from pathlib import Path

def setup_logger(name=None, log_level=None):
    """
    ロガーを設定して取得
    
    Args:
        name: ロガー名（Noneの場合はモジュール名）
        log_level: ログレベル（Noneの場合は環境変数から取得）
    
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
    
    # フォーマッターの設定
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソールハンドラー（常に出力）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラー（ログファイルが指定されている場合のみ）
    log_file = os.environ.get('LOG_FILE_PATH')
    if log_file:
        try:
            # ログディレクトリを作成
            log_dir = Path(log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # ファイルハンドラーの設定に失敗してもコンソールには出力
            logger.warning(f"ログファイルの設定に失敗しました: {e}")
    
    return logger

# デフォルトロガー（モジュールレベル）
default_logger = setup_logger('attendance_system')

