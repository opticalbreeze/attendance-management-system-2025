#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知フィルタリングモジュール
通知のフィルタリングロジックを担当
"""

from typing import List, Dict, Any, Optional, Set
from logger_config import setup_logger

logger = setup_logger(__name__)

def get_check_type_from_message(message: str) -> Optional[str]:
    """
    通知メッセージからチェックタイプを判定
    
    Args:
        message: 通知メッセージ
    
    Returns:
        str: チェックタイプ ('missing_punch', 'punch_leak', 'time_difference') または None
    """
    if not message:
        return None
    
    # メッセージからチェックタイプを判定
    if '打刻なし' in message:
        return 'missing_punch'
    elif '打刻漏れ' in message or '出勤打刻漏れ' in message or '退勤打刻漏れ' in message:
        return 'punch_leak'
    elif '時刻に差異' in message or '出退勤時刻に差異' in message or '出勤時刻に差異' in message or '退勤時刻に差異' in message:
        return 'time_difference'
    
    return None

def is_notification_checked(employee_id: str, work_date: str, message: str) -> bool:
    """
    通知がsearch画面でチェック済みかどうかを確認
    
    Args:
        employee_id: 従業員ID
        work_date: 勤務日
        message: 通知メッセージ
    
    Returns:
        bool: チェック済みの場合True
    """
    try:
        # チェックタイプを判定
        check_type = get_check_type_from_message(message)
        if not check_type:
            # チェックタイプが判定できない場合は、チェック済みとみなさない
            return False
        
        # データベースからチェック状態を取得
        from database import get_attendance_check_status
        status = get_attendance_check_status(str(employee_id), work_date, check_type)
        
        if status and status.get('is_checked'):
            logger.info(f"[通知API] チェック済み通知を検出: employee_id={employee_id}, work_date={work_date}, check_type={check_type}, message={message}")
            return True
        
        return False
        
    except Exception as e:
        logger.warning(f"[通知API] チェック状態確認エラー: employee_id={employee_id}, work_date={work_date}, message={message}, error={e}")
        # エラーが発生した場合は、チェック済みとみなさない（通知を表示する）
        return False

def filter_notifications(
    all_notifications: List[Dict[str, Any]],
    employee_id: Optional[str] = None,
    include_acknowledged: bool = False,
    acknowledged_notifications: Optional[Set[str]] = None,
    excluded_employee_ids: Optional[Set[str]] = None
) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    通知をフィルタリング
    
    Args:
        all_notifications: 全通知リスト
        employee_id: フィルタリングする従業員ID（オプション）
        include_acknowledged: 確認済み通知を含めるかどうか
        acknowledged_notifications: 確認済み通知のセット
        excluded_employee_ids: 除外リスト（従業員IDのセット）
    
    Returns:
        tuple: (フィルタリング後の通知リスト, 統計情報)
    """
    if acknowledged_notifications is None:
        acknowledged_notifications = set()
    if excluded_employee_ids is None:
        excluded_employee_ids = set()
    
    filtered_notifications = []
    excluded_count = 0
    acknowledged_count = 0
    checked_count = 0  # search画面でチェック済みの通知数
    
    # 除外リストを文字列セットに変換（一度だけ実行）
    excluded_str_set = {str(emp_id) for emp_id in excluded_employee_ids} if excluded_employee_ids else set()
    logger.info(f"[通知API] 除外リスト（文字列セット）: {excluded_str_set}")
    
    for notification in all_notifications:
        notification_emp_id = str(notification.get('employee_id', ''))
        notification_emp_name = notification.get('employee_name', '不明')
        notification_work_date = notification.get('work_date', '')
        notification_message = notification.get('message', '')
        
        # 確認済みフィルター
        if not include_acknowledged and notification['id'] in acknowledged_notifications:
            acknowledged_count += 1
            continue
        
        # 従業員IDフィルター
        if employee_id and notification['employee_id'] != employee_id:
            continue
        
        # 除外リストフィルター（除外リストが空でない場合のみチェック）
        if excluded_str_set:
            if notification_emp_id in excluded_str_set:
                excluded_count += 1
                logger.info(f"[通知API] 通知除外実行: employee_id={notification_emp_id} ({notification_emp_name}) が除外リストに含まれています")
                continue
            else:
                logger.debug(f"[通知API] 通知通過: employee_id={notification_emp_id} ({notification_emp_name}) は除外リストに含まれていません")
        
        # search画面でチェック済みかどうかを確認
        if is_notification_checked(notification_emp_id, notification_work_date, notification_message):
            checked_count += 1
            logger.info(f"[通知API] チェック済み通知を除外: employee_id={notification_emp_id}, work_date={notification_work_date}, message={notification_message}")
            continue
        
        filtered_notifications.append(notification)
    
    stats = {
        'total': len(all_notifications),
        'acknowledged_count': acknowledged_count,
        'excluded_count': excluded_count,
        'checked_count': checked_count,
        'filtered_count': len(filtered_notifications)
    }
    
    logger.info(f"[通知API] フィルタリング結果: 全{stats['total']}件 → 確認済み{stats['acknowledged_count']}件, 除外{stats['excluded_count']}件, チェック済み{stats['checked_count']}件 → 返却{stats['filtered_count']}件")
    
    return filtered_notifications, stats
