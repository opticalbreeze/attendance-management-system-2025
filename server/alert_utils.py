#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アラート判定ユーティリティ
エラータイプの判定を一貫して行うための共通関数
"""

from typing import List, Dict, Set, Optional
from constants import AttendanceConstants, CheckType

def classify_error_type_from_alert(alert: Dict) -> Optional[str]:
    """
    アラートメッセージからエラータイプを判定
    
    Args:
        alert: アラート辞書（'message'キーを含む）
    
    Returns:
        エラータイプ（'punch_leak', 'time_difference', 'missing_punch'）またはNone
    """
    message = alert.get('message', '')
    if not message:
        return None
    
    # 1. 打刻漏れ系（出勤/退勤打刻漏れ）を優先判定
    if (AttendanceConstants.MSG_CLOCK_IN_PUNCH_LEAK in message or 
        AttendanceConstants.MSG_CLOCK_OUT_PUNCH_LEAK in message):
        return CheckType.PUNCH_LEAK
    
    # 2. 時刻差異系（出勤/退勤時刻に差異あり）
    if (AttendanceConstants.MSG_CLOCK_IN_TIME_DIFF in message or 
        AttendanceConstants.MSG_CLOCK_OUT_TIME_DIFF in message):
        return CheckType.TIME_DIFFERENCE
    
    # 3. 打刻なし・打刻漏れ（汎用的なメッセージ）
    # ただし、「出勤打刻漏れ」「退勤打刻漏れ」は既に1で判定済み
    if (AttendanceConstants.MSG_MISSING_PUNCH in message or 
        (AttendanceConstants.MSG_PUNCH_LEAK in message and 
         AttendanceConstants.MSG_CLOCK_IN_PUNCH_LEAK not in message and
         AttendanceConstants.MSG_CLOCK_OUT_PUNCH_LEAK not in message)):
        return CheckType.MISSING_PUNCH
    
    return None

def get_error_types_from_alerts(alerts: List[Dict]) -> Set[str]:
    """
    アラートリストからエラータイプのセットを取得
    
    Args:
        alerts: アラートリスト
    
    Returns:
        エラータイプのセット（'punch_leak', 'time_difference', 'missing_punch'）
    """
    error_types = set()
    for alert in alerts:
        error_type = classify_error_type_from_alert(alert)
        if error_type:
            error_types.add(error_type)
    return error_types

def has_punch_leak_alert(alerts: List[Dict]) -> bool:
    """
    打刻漏れアラートが存在するかチェック
    
    Args:
        alerts: アラートリスト
    
    Returns:
        打刻漏れアラートが存在する場合True
    """
    return CheckType.PUNCH_LEAK in get_error_types_from_alerts(alerts)

def has_time_difference_alert(alerts: List[Dict]) -> bool:
    """
    時刻差異アラートが存在するかチェック
    
    Args:
        alerts: アラートリスト
    
    Returns:
        時刻差異アラートが存在する場合True
    """
    return CheckType.TIME_DIFFERENCE in get_error_types_from_alerts(alerts)

def has_missing_punch_alert(alerts: List[Dict]) -> bool:
    """
    打刻なしアラートが存在するかチェック
    
    Args:
        alerts: アラートリスト
    
    Returns:
        打刻なしアラートが存在する場合True
    """
    return CheckType.MISSING_PUNCH in get_error_types_from_alerts(alerts)

def has_clock_in_leak_alert(alerts: List[Dict]) -> bool:
    """
    出勤打刻漏れアラートが存在するかチェック
    
    Args:
        alerts: アラートリスト
    
    Returns:
        出勤打刻漏れアラートが存在する場合True
    """
    for alert in alerts:
        message = alert.get('message', '')
        if AttendanceConstants.MSG_CLOCK_IN_PUNCH_LEAK in message:
            return True
    return False

def has_clock_out_leak_alert(alerts: List[Dict]) -> bool:
    """
    退勤打刻漏れアラートが存在するかチェック
    
    Args:
        alerts: アラートリスト
    
    Returns:
        退勤打刻漏れアラートが存在する場合True
    """
    for alert in alerts:
        message = alert.get('message', '')
        if AttendanceConstants.MSG_CLOCK_OUT_PUNCH_LEAK in message:
            return True
    return False
