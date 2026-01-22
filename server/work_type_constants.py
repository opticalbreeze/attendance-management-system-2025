#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
勤務タイプ定数定義モジュール
勤務タイプの判定ロジックを一元管理
"""

# 勤務タイプの文字列定数
WORK_TYPE_OFF_DAY = '明'  # 「明」勤務
WORK_TYPE_24HOUR_A = '24勤A'
WORK_TYPE_24HOUR_B = '24勤B'
WORK_TYPE_NIGHT = '夜勤'

# 勤務タイプ判定関数
def is_off_day_shift(work_type):
    """
    「明」勤務かどうかを判定
    
    Args:
        work_type: 勤務タイプ文字列
        
    Returns:
        bool: 「明」勤務の場合True
    """
    return work_type and WORK_TYPE_OFF_DAY in work_type

def is_24hour_shift(work_type):
    """
    24勤（A/B）かどうかを判定
    
    Args:
        work_type: 勤務タイプ文字列
        
    Returns:
        bool: 24勤の場合True
    """
    return work_type and ('24勤' in work_type)

def is_night_shift(work_type):
    """
    夜勤かどうかを判定
    
    Args:
        work_type: 勤務タイプ文字列
        
    Returns:
        bool: 夜勤の場合True
    """
    return work_type and WORK_TYPE_NIGHT in work_type

def is_24hour_or_night_shift(work_type):
    """
    24勤または夜勤かどうかを判定
    
    Args:
        work_type: 勤務タイプ文字列
        
    Returns:
        bool: 24勤または夜勤の場合True
    """
    return is_24hour_shift(work_type) or is_night_shift(work_type)

def is_holiday_shift(work_type):
    """
    休日（有給・所定・法定）かどうかを判定
    
    Args:
        work_type: 勤務タイプ文字列
        
    Returns:
        bool: 休日の場合True
    """
    return work_type and ('有' in work_type or '所' in work_type or '法' in work_type)

def is_absence(work_type):
    """
    欠勤かどうかを判定
    
    Args:
        work_type: 勤務タイプ文字列
        
    Returns:
        bool: 欠勤の場合True
    """
    return work_type and ('欠' in work_type)

def is_non_working_day(work_type):
    """
    労働時間0の勤務タイプかどうかを判定（休日、明け、欠勤）
    
    Args:
        work_type: 勤務タイプ文字列
        
    Returns:
        bool: 労働時間が0の場合True
    """
    return is_holiday_shift(work_type) or is_off_day_shift(work_type) or is_absence(work_type)

# CSVインポート用の勤務区分マッピング（一元管理）
CSV_WORK_TYPE_MAPPING = {
    '日勤': '通常',
    '夜勤': '夜勤',
    '法': '法定休日',
    '所': '所定休日',
    '有': '有給',
    '代': '代休',
    '特': '特休',
    '明': '明',
    '24勤A': '24勤A',
    '24勤B': '24勤B',
    '欠': '欠勤'
}

def map_csv_work_type(csv_work_type):
    """
    CSVファイルの勤務区分をデータベース用の勤務区分にマッピング
    
    Args:
        csv_work_type: CSVファイルの勤務区分文字列
        
    Returns:
        str: マッピング後の勤務区分、マッピングがない場合はそのまま返す
    """
    return CSV_WORK_TYPE_MAPPING.get(csv_work_type, csv_work_type)

