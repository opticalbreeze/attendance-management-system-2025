#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
詳細デバッグ用の時間外計算テスト
"""
import sys
import logging
sys.path.append('/app')

# ログレベルを設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from overtime import calculate_overtime_categories

def debug_overtime_calc():
    """12/9の4:00-6:00の時間外計算を詳細にデバッグ"""
    
    employee_num = '3652025'
    work_date = '2025-12-09'
    start_time = '04:00' 
    end_time = '06:00'
    
    print(f"=== デバッグ: {work_date} {start_time}-{end_time} ===")
    print(f"従業員: {employee_num}")
    
    result = calculate_overtime_categories(employee_num, work_date, start_time, end_time)
    
    print(f"\n計算結果:")
    print(f"  分類: {result['overtime_type']}")
    print(f"  内残業: {result['inner_overtime_minutes']}分")
    print(f"  外残業: {result['outer_overtime_minutes']}分") 
    print(f"  深夜時間: {result['night_overtime_minutes']}分")

if __name__ == "__main__":
    debug_overtime_calc()