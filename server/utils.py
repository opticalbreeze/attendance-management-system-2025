#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ユーティリティモジュール統合インターフェース
後方互換性を保つための統合インポートモジュール
"""

# 分割されたモジュールからインポート
from database_utils import (
    get_database_connection,
    get_db_connection,
    check_duplicate_attendance
)
from time_utils import (
    time_to_minutes,
    calculate_time_diff_minutes,
    calculate_duration_minutes,
    extract_time_from_timestamp
)
from validation_utils import (
    validate_employee_id,
    validate_search_month,
    calculate_date_range
)
from api_utils import (
    format_response,
    safe_int,
    update_request_status
)
from pdf_utils import save_pdf_from_html

# 公開インターフェースの定義
__all__ = [
    # データベース関連
    'get_database_connection', 'get_db_connection', 'check_duplicate_attendance',
    # 時刻処理関連
    'time_to_minutes', 'calculate_time_diff_minutes', 'calculate_duration_minutes', 'extract_time_from_timestamp',
    # バリデーション関連
    'validate_employee_id', 'validate_search_month', 'calculate_date_range',
    # API関連
    'format_response', 'safe_int', 'update_request_status',
    # PDF生成関連
    'save_pdf_from_html'
]
