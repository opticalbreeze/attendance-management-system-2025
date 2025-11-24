#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
時刻処理ユーティリティモジュール
時刻計算・変換・解析の専門モジュール
"""

from logger_config import setup_logger

logger = setup_logger(__name__)

def time_to_minutes(time_str):
    """
    HH:MM形式の時刻を分に変換（統一関数）
    
    Args:
        time_str: 時刻文字列 (HH:MM形式)
    
    Returns:
        int: 分単位の時刻、変換失敗時はNone
    """
    if not time_str:
        return None
    try:
        parts = time_str.split(':')
        if len(parts) >= 2:
            return int(parts[0]) * 60 + int(parts[1])
        return None
    except (ValueError, AttributeError):
        return None

def calculate_time_diff_minutes(time1_str, time2_str):
    """
    2つの時刻（HH:MM形式）の差異を分単位で計算
    
    Args:
        time1_str: 時刻1 (HH:MM形式)
        time2_str: 時刻2 (HH:MM形式)
    
    Returns:
        差異（分）、time1が早い場合は負の値、time2が早い場合は正の値、変換失敗時はNone
    """
    try:
        if not time1_str or not time2_str:
            return None
        
        minutes1 = time_to_minutes(time1_str)
        minutes2 = time_to_minutes(time2_str)
        
        if minutes1 is None or minutes2 is None:
            return None
        
        return minutes2 - minutes1
        
    except Exception:
        return None

def calculate_duration_minutes(start_time, end_time):
    """
    開始時刻と終了時刻から時間（分）を計算（統一関数）
    
    Args:
        start_time: 開始時刻 (HH:MM形式)
        end_time: 終了時刻 (HH:MM形式)
    
    Returns:
        int: 時間（分）、日をまたぐ場合は24時間を加算、変換失敗時はNone
    """
    start_min = time_to_minutes(start_time)
    end_min = time_to_minutes(end_time)
    
    if start_min is None or end_min is None:
        return None
    
    if end_min < start_min:
        end_min += 1440  # 日をまたぐ
    
    return end_min - start_min

def extract_time_from_timestamp(timestamp_str):
    """
    タイムスタンプ文字列から時刻部分（HH:MM形式）を抽出（統一関数）
    
    ISO8601形式（'2025-01-01T12:34:56.789'）や
    スペース区切り形式（'2025-01-01 12:34:56.789'）から
    時刻部分（HH:MM）を抽出します。
    
    Args:
        timestamp_str: タイムスタンプ文字列
    
    Returns:
        str: 時刻文字列（HH:MM形式）、抽出失敗時は元の文字列を返す
    """
    if not timestamp_str:
        return timestamp_str
    
    try:
        if 'T' in timestamp_str:
            # ISO8601形式: '2025-01-01T12:34:56.789'
            time_part = timestamp_str.split('T')[1].split('.')[0]  # HH:MM:SS
        elif ' ' in timestamp_str:
            # スペース区切り形式: '2025-01-01 12:34:56.789'
            time_part = timestamp_str.split(' ')[1].split('.')[0]  # HH:MM:SS
        else:
            # その他の形式はそのまま返す
            return timestamp_str
        
        # HH:MM形式に変換（秒を除去）
        time_only = ':'.join(time_part.split(':')[:2])
        return time_only
    except Exception:
        # パース失敗時は元の文字列を返す
        return timestamp_str

