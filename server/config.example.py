#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
設定ファイルのサンプル
このファイルをコピーして config.py を作成するか、
環境変数で設定を上書きしてください
"""

# ==================== 環境変数での設定例 ====================
"""
# Windows (PowerShell)
$env:SERVER_PORT="5000"
$env:CHATTERING_THRESHOLD="15"
$env:DEFAULT_SEARCH_LIMIT="200"

# Linux/Mac (Bash)
export SERVER_PORT=5000
export CHATTERING_THRESHOLD=15
export DEFAULT_SEARCH_LIMIT=200

# Docker Compose (docker-compose.yml)
environment:
  - SERVER_PORT=5000
  - CHATTERING_THRESHOLD=15
  - DEFAULT_SEARCH_LIMIT=200
  - FLASK_ENV=production
"""

# ==================== 設定可能な環境変数一覧 ====================
"""
SERVER_HOST              - サーバーホスト (デフォルト: 0.0.0.0)
SERVER_PORT              - サーバーポート (デフォルト: 5000)
FLASK_DEBUG              - デバッグモード (デフォルト: False)
FLASK_ENV                - 環境設定 (development/production/docker)

DATABASE_PATH            - データベースファイルパス (自動判定可能)

CHATTERING_THRESHOLD     - チャタリング防止閾値（秒） (デフォルト: 10)

API_VERSION              - APIバージョン (デフォルト: 1.0.0)
DEFAULT_SEARCH_LIMIT     - デフォルト検索上限件数 (デフォルト: 100)
STATS_LATEST_RECORDS     - 統計の最新履歴件数 (デフォルト: 10)

PAYROLL_START_DAY        - 給与計算期間開始日 (デフォルト: 16)
PAYROLL_END_DAY          - 給与計算期間終了日 (デフォルト: 15)

EMPLOYEE_ID_MIN_LENGTH   - 従業員ID最小長 (デフォルト: 3)
EMPLOYEE_ID_MAX_LENGTH   - 従業員ID最大長 (デフォルト: 20)
YEAR_MIN                 - 検索可能な年の最小値 (デフォルト: 2000)
YEAR_MAX                 - 検索可能な年の最大値 (デフォルト: 2100)
"""

