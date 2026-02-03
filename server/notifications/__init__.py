#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知システムパッケージ
通知生成、フィルタリング、除外リスト管理を担当
"""

# 除外リスト管理
from .exclusion_manager import (
    load_notification_exclusions,
    save_notification_exclusions,
    sync_exclusions_file,
    init_notification_files
)

# 通知データ管理
from .notification_data import (
    load_notification_data,
    load_acknowledged_notifications,
    save_acknowledged_notifications
)

# フィルタリングロジック
from .notification_filter import (
    get_check_type_from_message,
    is_notification_checked,
    filter_notifications
)

__all__ = [
    # 除外リスト管理
    'load_notification_exclusions',
    'save_notification_exclusions',
    'sync_exclusions_file',
    'init_notification_files',
    # 通知データ管理
    'load_notification_data',
    'load_acknowledged_notifications',
    'save_acknowledged_notifications',
    # フィルタリングロジック
    'get_check_type_from_message',
    'is_notification_checked',
    'filter_notifications'
]
