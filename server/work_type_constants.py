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

