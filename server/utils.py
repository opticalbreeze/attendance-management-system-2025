#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ユーティリティモジュール  
共通で使用される便利な関数を提供
"""

import sqlite3
from datetime import datetime, date, timedelta
import os

# 設定
CHATTERING_THRESHOLD_SECONDS = int(os.environ.get('CHATTERING_THRESHOLD', '10'))
DB_FILE = os.environ.get('DATABASE_PATH', '/data/attendance.db' if os.path.exists('/data') else 'attendance.db')

def check_duplicate_attendance(idm, timestamp, terminal_id, threshold_seconds=None):
    """
    チャタリング防止: 重複打刻をチェック
    同じIDm、端末で指定秒数以内の打刻は重複と判定
    """
    if threshold_seconds is None:
        threshold_seconds = CHATTERING_THRESHOLD_SECONDS
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 同じIDm、端末での最新の打刻を取得
        cursor.execute("""
            SELECT timestamp, received_at 
            FROM attendance 
            WHERE idm = ? AND terminal_id = ?
            ORDER BY received_at DESC 
            LIMIT 1
        """, (idm, terminal_id))
        
        last_record = cursor.fetchone()
        conn.close()
        
        if not last_record:
            return {'is_duplicate': False, 'time_diff': None}
        
        # 時刻差を計算
        try:
            last_timestamp = datetime.fromisoformat(last_record[0].replace('Z', '+00:00'))
            current_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_diff = abs((current_timestamp - last_timestamp).total_seconds())
            
            is_duplicate = time_diff <= threshold_seconds
            
            return {
                'is_duplicate': is_duplicate,
                'time_diff': time_diff,
                'last_record': {
                    'timestamp': last_record[0],
                    'received_at': last_record[1]
                }
            }
            
        except ValueError as e:
            print(f"[警告] 時刻解析エラー: {e}")
            return {'is_duplicate': False, 'time_diff': None}
            
    except sqlite3.Error as e:
        print(f"[エラー] 重複チェック失敗: {e}")
        return {'is_duplicate': False, 'time_diff': None}

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
        
        # 検索範囲の開始日：前月16日
        start_date = date(prev_year, prev_month, 16).strftime('%Y-%m-%d')
        
        # 検索範囲の終了日：当月15日
        end_date = date(year, month, 15).strftime('%Y-%m-%d')
        
        return start_date, end_date
        
    except ValueError as e:
        raise ValueError(f"検索月の形式が正しくありません: {str(e)}")

def validate_employee_id(employee_id):
    """従業員IDのバリデーション"""
    if not employee_id or not employee_id.strip():
        return False, "従業員IDが指定されていません"
    
    # 基本的なフォーマットチェック（必要に応じて調整）
    employee_id = employee_id.strip()
    if len(employee_id) < 3:
        return False, "従業員IDは3文字以上で入力してください"
    
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
        
        if year < 2000 or year > 2100:
            return False, "年は2000-2100の範囲で入力してください"
            
        if month < 1 or month > 12:
            return False, "月は1-12の範囲で入力してください"
            
        return True, search_month
        
    except ValueError:
        return False, "検索月はyyyy/mm形式で入力してください（例: 2025/10）"

def format_response(status, data=None, message=None, **kwargs):
    """統一されたレスポンス形式を生成"""
    response = {'status': status}
    
    if message:
        response['message'] = message
    
    if data is not None:
        if isinstance(data, dict):
            response.update(data)
        else:
            response['data'] = data
    
    # 追加パラメータ
    response.update(kwargs)
    
    return response

def safe_int(value, default=0):
    """安全に整数に変換"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def safe_float(value, default=0.0):
    """安全に浮動小数点数に変換"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default