#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知データ管理モジュール
通知データと確認済み通知の読み込み・保存を担当
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Set
from logger_config import setup_logger

logger = setup_logger(__name__)

# 通知関連ファイルパス
# コンテナ内では /app/ にマウントされているため、相対パスで指定
NOTIFICATION_DATA_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'notification_data.json')
ACKNOWLEDGED_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'acknowledged_notifications.json')

# コンテナ内のパスも試す（フォールバック）
NOTIFICATION_DATA_FILE_CONTAINER = '/app/notification_data.json'
ACKNOWLEDGED_FILE_CONTAINER = '/app/acknowledged_notifications.json'

def load_notification_data() -> List[Dict[str, Any]]:
    """通知データを読み込み"""
    # 複数のパスを試す
    file_paths = [NOTIFICATION_DATA_FILE, NOTIFICATION_DATA_FILE_CONTAINER]
    
    for file_path in file_paths:
        try:
            # ファイルが存在し、かつディレクトリでないことを確認
            if os.path.exists(file_path) and os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    notifications = data.get('notifications', [])
                    logger.info(f"通知データ読み込み成功: {file_path} ({len(notifications)}件)")
                    return notifications
            elif os.path.exists(file_path) and os.path.isdir(file_path):
                logger.warning(f"通知データパスがディレクトリです（スキップ）: {file_path}")
                continue
        except Exception as e:
            logger.warning(f"通知データ読み込み試行失敗 ({file_path}): {e}")
            continue
    
    logger.warning(f"通知データファイルが見つかりません。試行したパス: {file_paths}")
    return []

def load_acknowledged_notifications() -> Set[str]:
    """確認済み通知を読み込み"""
    file_paths = [ACKNOWLEDGED_FILE_CONTAINER, ACKNOWLEDGED_FILE]
    
    for file_path in file_paths:
        try:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    acknowledged_set = set(data.get('acknowledged', []))
                    logger.debug(f"確認済み通知読み込み成功: {file_path} ({len(acknowledged_set)}件)")
                    return acknowledged_set
        except Exception as e:
            logger.warning(f"確認済み通知読み込み試行失敗 ({file_path}): {e}")
            continue
    
    logger.debug("確認済み通知ファイルが見つかりません。空のセットを返します。")
    return set()

def save_acknowledged_notifications(acknowledged_set: Set[str]):
    """確認済み通知を保存"""
    file_paths = [ACKNOWLEDGED_FILE_CONTAINER, ACKNOWLEDGED_FILE]
    
    for file_path in file_paths:
        try:
            # ディレクトリが存在するか確認
            dir_path = os.path.dirname(file_path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            data = {
                'acknowledged': list(acknowledged_set),
                'last_updated': datetime.now().isoformat()
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"確認済み通知を保存: {file_path} ({len(acknowledged_set)}件)")
            return
        except Exception as e:
            logger.warning(f"確認済み通知保存試行失敗 ({file_path}): {e}")
            continue
    
    logger.error(f"確認済み通知保存に失敗しました。試行したパス: {file_paths}")
