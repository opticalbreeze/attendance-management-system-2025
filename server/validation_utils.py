#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
バリデーションユーティリティモジュール
入力値検証と日付計算の専門モジュール
"""

from datetime import date
from config import Config
from constants import AttendanceConstants
from logger_config import setup_logger

logger = setup_logger(__name__)

def validate_employee_id(employee_id):
    """従業員IDのバリデーション"""
    if not employee_id or not employee_id.strip():
        return False, "従業員IDが指定されていません"
    
    employee_id = employee_id.strip()
    
    if len(employee_id) < Config.EMPLOYEE_ID_MIN_LENGTH:
        return False, f"従業員IDは{Config.EMPLOYEE_ID_MIN_LENGTH}文字以上で入力してください"
    
    if len(employee_id) > Config.EMPLOYEE_ID_MAX_LENGTH:
        return False, f"従業員IDは{Config.EMPLOYEE_ID_MAX_LENGTH}文字以下で入力してください"
    
    return True, employee_id

def validate_search_month(search_month):
    """検索月のバリデーション"""
    if not search_month or not search_month.strip():
        return False, "検索月が指定されていません（yyyy/mm形式で入力してください）"
    
    search_month = search_month.strip()
    
    # 形式チェック
    if '/' not in search_month:
        return False, "検索月はyyyy/mm形式で入力してください"
    
    try:
        year, month = search_month.split('/')
        year = int(year)
        month = int(month)
        
        if year < Config.YEAR_MIN or year > Config.YEAR_MAX:
            return False, f"年は{Config.YEAR_MIN}-{Config.YEAR_MAX}の範囲で入力してください"
            
        if month < 1 or month > 12:
            return False, "月は1-12の範囲で入力してください"
            
        return True, search_month
        
    except ValueError:
        return False, "検索月はyyyy/mm形式で入力してください（例: 2025/10）"

def calculate_date_range(search_month):
    """
    検索月から検索範囲を計算（前月16日から当月15日）
    給与計算期間に基づく期間設定
    
    Args:
        search_month (str): 検索月 (yyyy/mm形式)
        
    Returns:
        tuple: (start_date, end_date)
    """
    try:
        year, month = search_month.split('/')
        year = int(year)
        month = int(month)
        
        if month < 1 or month > 12:
            raise ValueError("月は1-12の範囲で指定してください")
        
        # 前月の計算
        if month == 1:
            prev_year = year - 1
            prev_month = 12
        else:
            prev_year = year
            prev_month = month - 1
        
        # 検索範囲の開始日：前月16日（設定から取得）
        start_date = date(prev_year, prev_month, Config.PAYROLL_START_DAY).strftime(AttendanceConstants.DATE_FORMAT)
        
        # 検索範囲の終了日：当月15日（設定から取得）
        end_date = date(year, month, Config.PAYROLL_END_DAY).strftime(AttendanceConstants.DATE_FORMAT)
        
        return start_date, end_date
        
    except ValueError as e:
        raise ValueError(f"検索月の形式が正しくありません: {str(e)}")

