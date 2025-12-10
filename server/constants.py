#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アプリケーション共通定数
重複した定数やハードコーディングされた値を一元管理
"""

class WorkType:
    """勤務タイプ定数"""
    # 通常勤務
    DAY_SHIFT = "日勤"
    NIGHT_SHIFT = "夜勤"
    SHIFT_24_A = "24勤A"
    SHIFT_24_B = "24勤B"
    
    # 休み関連
    OFF_DAY = "明"
    PAID_LEAVE = "有"
    LEGAL_HOLIDAY = "法"
    SPECIAL_LEAVE = "特"
    OFFICE_WORK = "所"
    
    @classmethod
    def is_24_hour_shift(cls, work_type):
        """24時間勤務かどうか判定"""
        return work_type and "24勤" in work_type
    
    @classmethod
    def is_night_shift(cls, work_type):
        """夜勤かどうか判定"""
        return work_type and "夜勤" in work_type
    
    @classmethod
    def is_continuous_shift(cls, work_type):
        """連続勤務（24勤・夜勤）かどうか判定"""
        return cls.is_24_hour_shift(work_type) or cls.is_night_shift(work_type)
    
    @classmethod
    def is_off_day(cls, work_type):
        """休日かどうか判定"""
        if not work_type:
            return False
        return any(off_type in work_type for off_type in [
            cls.PAID_LEAVE, cls.LEGAL_HOLIDAY, cls.SPECIAL_LEAVE, cls.OFF_DAY
        ])

class AttendanceThreshold:
    """勤怠チェック閾値定数"""
    TIME_DIFF_THRESHOLD_MINUTES = 30  # 時刻差異アラートの閾値（分）
    CHATTERING_THRESHOLD_SECONDS = 30  # チャタリング防止閾値（秒）
    MAX_SEARCH_LIMIT = 1000  # 検索結果上限

class AlertType:
    """アラートタイプ定数"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class AlertMessage:
    """アラートメッセージ定数"""
    NO_ATTENDANCE = "打刻なし"
    HOLIDAY_ATTENDANCE = "休日なのに打刻"
    TIME_DIFFERENCE = "出退勤時刻に差異あり"
    LATE_ARRIVAL = "遅刻"
    EARLY_LEAVE = "早退"

class CheckType:
    """確認タイプ定数"""
    MISSING_PUNCH = "missing_punch"
    TIME_DIFFERENCE = "time_difference"

class UIConfig:
    """UI設定定数"""
    # テーブル列幅設定
    TABLE_COLUMN_WIDTHS = {
        'employee_id': '80px',
        'employee_name': '100px',
        'work_date': '90px',
        'work_type': '90px',
        'start_time': '70px',
        'end_time': '70px',
        'valid_clock': '120px',
        'alerts': '150px',
        'check_status': '120px',
        'overtime': '80px',
        'leave': '80px'
    }
    
    # CSS クラス名
    CSS_CLASSES = {
        'shift_24': 'shift-24',
        'day_shift': 'day-shift',
        'night_shift': 'night-shift',
        'office': 'office',
        'off_day': 'off-day',
        'holiday': 'holiday',
        'paid_leave': 'paid-leave'
    }