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
    PUNCH_LEAK = "punch_leak"
    
    @classmethod
    def get_all(cls):
        """全てのチェックタイプを取得"""
        return [cls.MISSING_PUNCH, cls.TIME_DIFFERENCE, cls.PUNCH_LEAK]
    
    @classmethod
    def is_valid(cls, check_type):
        """チェックタイプが有効かどうかを判定"""
        return check_type in cls.get_all()

class AttendanceConstants:
    """勤怠チェック関連の定数（統一化）"""
    # 閾値設定
    TIME_DIFF_THRESHOLD = 30  # 時刻差異の閾値（分）
    TOLERANCE_MINUTES = 15    # 許容時間差（分）
    DEFAULT_LIMIT = 100       # デフォルト取得件数
    
    # 時間計算用定数
    MINUTES_PER_HOUR = 60     # 1時間あたりの分数
    MINUTES_PER_DAY = 1440    # 1日あたりの分数（24時間 * 60分）
    HOURS_PER_DAY = 24        # 1日の時間数
    
    # 深夜時間帯設定
    NIGHT_START_HOUR = 20     # 深夜開始時間（20:00）
    NIGHT_END_HOUR = 5        # 深夜終了時間（翌05:00）
    
    @classmethod
    def get_night_start_minutes(cls):
        """深夜開始時間を分で取得"""
        return cls.NIGHT_START_HOUR * cls.MINUTES_PER_HOUR
    
    @classmethod
    def get_night_end_minutes(cls):
        """深夜終了時間を分で取得（翌日の時刻として）"""
        return (cls.HOURS_PER_DAY + cls.NIGHT_END_HOUR) * cls.MINUTES_PER_HOUR
    
    @classmethod
    def get_night_end_minutes_day2(cls):
        """2日目の深夜終了時間を分で取得（当日の時刻として）"""
        return cls.NIGHT_END_HOUR * cls.MINUTES_PER_HOUR
    
    # 日付フォーマット
    DATE_FORMAT = '%Y-%m-%d'  # 標準日付フォーマット（YYYY-MM-DD）
    DATE_FORMAT_SLASH = '%Y/%m/%d'  # スラッシュ区切り日付フォーマット（YYYY/MM/DD）
    
    # ステータス
    STATUS_APPROVED = 'approved'
    STATUS_PENDING = 'pending'
    
    # アラートタイプ
    ALERT_ERROR = 'error'
    ALERT_WARNING = 'warning'
    
    # エラーメッセージ
    MSG_HOLIDAY_PUNCH = '休日なのに打刻'
    MSG_MISSING_PUNCH = '打刻なし'
    MSG_PUNCH_LEAK = '打刻漏れ'
    MSG_CLOCK_IN_PUNCH_LEAK = '出勤打刻漏れ'
    MSG_CLOCK_OUT_PUNCH_LEAK = '退勤打刻漏れ'
    MSG_TIME_DIFF = '出退勤時刻に差異あり'  # 後方互換性のため残す
    MSG_CLOCK_IN_TIME_DIFF = '出勤時刻に差異あり'
    MSG_CLOCK_OUT_TIME_DIFF = '退勤時刻に差異あり'
    MSG_HOLIDAY_WORK_NO_PUNCH = '休日出勤届があるのに打刻なし'
    MSG_LEAVE_WITH_PUNCH = '休暇願があるのに打刻あり'
    MSG_OFF_DAY_NO_PREV_SHIFT = '「明」勤務ですが、前日の24勤・夜勤スケジュールが見つかりません'
    
    # エラーメッセージ詳細テンプレート
    DETAIL_CLOCK_IN_MISSING = '出勤時刻: スケジュール {schedule} / 実際の打刻なし'
    DETAIL_CLOCK_OUT_MISSING = '退勤時刻: スケジュール {schedule} / 実際の打刻なし'
    DETAIL_CLOCK_IN_MISSING_SINGLE_PUNCH = '出勤時刻: スケジュール {schedule} / 実際の打刻なし（打刻1回のみで終了時間に近い）'
    DETAIL_CLOCK_OUT_MISSING_SINGLE_PUNCH = '退勤時刻: スケジュール {schedule} / 実際の打刻なし（打刻1回のみで開始時間に近い）'
    DETAIL_CLOCK_IN_TIME_DIFF = '出勤時刻: スケジュール {schedule} / 実際 {actual} (差異: {diff:+d}分, 遅刻申告調整後: {adjusted_diff:+d}分)'
    DETAIL_CLOCK_OUT_TIME_DIFF = '退勤時刻: スケジュール {schedule} / 実際 {actual} (差異: {diff:+d}分, 早退申告調整後: {adjusted_diff:+d}分)'

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