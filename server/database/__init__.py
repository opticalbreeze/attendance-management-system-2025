#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベースモジュール
後方互換性のための再エクスポート
"""

# スキーマ管理
from .schema import (
    DatabaseInitializer,
    init_database,
    migrate_employee_master_table,
    init_late_early_requests_tables,
    init_leave_request_table_internal,
    init_overtime_table_internal,
    migrate_overtime_table,
    init_attendance_check_status_table,
    init_notification_exclusions_table
)

# DAO - 打刻データ
from .dao.attendance_dao import (
    insert_attendance,
    get_attendance_for_schedule,
    cleanup_duplicates
)

# DAO - スケジュール
from .dao.schedule_dao import (
    search_schedule
)

# DAO - 従業員マスタ
from .dao.employee_dao import (
    get_employees,
    get_stats
)

# DAO - リクエスト管理
from .dao.request_dao import (
    insert_late_arrival_request,
    insert_early_leave_request,
    get_late_arrival_requests,
    get_early_leave_requests
)

# DAO - チェック状態
from .dao.check_status_dao import (
    get_attendance_check_status,
    update_attendance_check_status
)

# DAO - 除外リスト
from .dao.exclusion_dao import (
    get_all_excluded_employee_ids,
    set_excluded_employee_ids,
    add_excluded_employee_id,
    remove_excluded_employee_id,
    is_excluded
)

# ビジネスロジック
from .business_logic import (
    check_off_day_shift_attendance,
    get_night_shift_end_time_from_next_day,
    check_attendance_vs_schedule
)

__all__ = [
    # スキーマ管理
    'DatabaseInitializer',
    'init_database',
    'migrate_employee_master_table',
    'init_late_early_requests_tables',
    'init_leave_request_table_internal',
    'init_overtime_table_internal',
    'migrate_overtime_table',
    'init_attendance_check_status_table',
    'init_notification_exclusions_table',
    # DAO - 打刻データ
    'insert_attendance',
    'get_attendance_for_schedule',
    'cleanup_duplicates',
    # DAO - スケジュール
    'search_schedule',
    # DAO - 従業員マスタ
    'get_employees',
    'get_stats',
    # DAO - リクエスト管理
    'insert_late_arrival_request',
    'insert_early_leave_request',
    'get_late_arrival_requests',
    'get_early_leave_requests',
    # DAO - チェック状態
    'get_attendance_check_status',
    'update_attendance_check_status',
    # DAO - 除外リスト
    'get_all_excluded_employee_ids',
    'set_excluded_employee_ids',
    'add_excluded_employee_id',
    'remove_excluded_employee_id',
    'is_excluded',
    # ビジネスロジック
    'check_off_day_shift_attendance',
    'get_night_shift_end_time_from_next_day',
    'check_attendance_vs_schedule'
]
