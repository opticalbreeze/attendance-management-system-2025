# データベーススキーマ

勤怠打刻システムのデータベーススキーマ仕様です。

## 📋 目次

1. [概要](#概要)
2. [テーブル一覧](#テーブル一覧)
3. [テーブル詳細](#テーブル詳細)
4. [インデックス](#インデックス)
5. [リレーション](#リレーション)

---

## 概要

データベース: SQLite  
ファイル名: `attendance.db`  
場所: `data/attendance.db`（Docker環境では `/app/data/attendance.db`）

---

## テーブル一覧

| テーブル名 | 説明 |
|-----------|------|
| `attendance` | 打刻データ |
| `employee_master` | 従業員マスタ |
| `attend_schedule` | 勤務スケジュール |
| `overtime_applications` | 時間外申告 |
| `leave_requests` | 休暇願 |
| `late_arrival_requests` | 遅刻申告 |
| `early_leave_requests` | 早退申告 |
| `attendance_check_status` | 打刻チェック状況 |

---

## テーブル詳細

### attendance

打刻データを格納します。

```sql
CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idm TEXT NOT NULL,              -- カードID（16進数文字列）
    timestamp TEXT NOT NULL,        -- 打刻時刻（ISO 8601形式）
    terminal_id TEXT NOT NULL,      -- 端末ID（MACアドレス）
    received_at TEXT NOT NULL       -- サーバー受信時刻
);
```

**インデックス:**
- `idx_idm`: `idm`
- `idx_timestamp`: `timestamp`
- `idx_terminal_id`: `terminal_id`

---

### employee_master

従業員マスタ情報を格納します。

```sql
CREATE TABLE employee_master (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_num INTEGER NOT NULL UNIQUE,  -- 従業員番号
    name TEXT NOT NULL,                    -- 氏名
    idm TEXT NOT NULL UNIQUE,              -- カードID
    section TEXT DEFAULT '設備',           -- セクション
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**リレーション:**
- `idm` → `attendance.idm`（外部キーなし、論理的な関連）

---

### attend_schedule

勤務スケジュールを格納します。

```sql
CREATE TABLE attend_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,      -- 従業員ID
    work_date TEXT NOT NULL,        -- 勤務日（YYYY-MM-DD）
    work_type TEXT NOT NULL,        -- 勤務タイプ（日勤、24勤、夜勤、明）
    start_time TEXT NOT NULL,       -- 開始時刻（HH:MM）
    end_time TEXT NOT NULL,         -- 終了時刻（HH:MM）
    sheet_number INTEGER,           -- シート番号
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(employee_id, work_date)
);
```

**勤務タイプ:**
- `日勤`: 通常の日勤（例: 8:30-17:30）
- `24勤`: 24時間勤務（例: 8:30-翌8:30）
- `夜勤`: 夜勤（例: 17:30-翌8:30）
- `明`: 「明」勤務（前日の24勤・夜勤の退勤時刻として扱う）

---

### overtime_applications

時間外申告を格納します。

```sql
CREATE TABLE overtime_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_num TEXT NOT NULL,
    employee_name TEXT NOT NULL,
    application_date TEXT NOT NULL,      -- 申告日（YYYY-MM-DD）
    work_date TEXT NOT NULL,            -- 勤務日（YYYY-MM-DD）
    start_time TEXT NOT NULL,           -- 開始時刻（HH:MM）
    end_time TEXT NOT NULL,             -- 終了時刻（HH:MM）
    inner_overtime_minutes INTEGER DEFAULT 0,    -- 内残業（分）
    outer_overtime_minutes INTEGER DEFAULT 0,    -- 外残業（分）
    night_overtime_minutes INTEGER DEFAULT 0,    -- 深夜時間（分、20:00-05:00）
    description TEXT,                   -- 説明
    status TEXT DEFAULT 'pending',      -- ステータス（pending, approved, rejected）
    approved_by TEXT,                   -- 承認者
    approved_at TEXT,                   -- 承認日時
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**ステータス:**
- `pending`: 承認待ち
- `approved`: 承認済み
- `rejected`: 却下

**時間外の分類:**
- **内残業**: 定時内の時間外（例: 8:30-17:30の範囲内）
- **外残業**: 定時外の時間外（例: 17:30以降、8:30以前）
- **深夜時間**: 20:00-05:00の時間外

---

### leave_requests

休暇願を格納します。

```sql
CREATE TABLE leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_num TEXT NOT NULL,
    employee_name TEXT NOT NULL,
    application_date TEXT NOT NULL,      -- 申告日（YYYY-MM-DD）
    leave_date_from TEXT NOT NULL,       -- 休暇開始日（YYYY-MM-DD）
    leave_date_to TEXT NOT NULL,         -- 休暇終了日（YYYY-MM-DD）
    leave_type TEXT NOT NULL,            -- 休暇種別（有給、代休、特別休暇など）
    leave_subtype TEXT,                  -- 休暇サブタイプ
    substitute_work_date TEXT,           -- 振替勤務日（YYYY-MM-DD）
    other_reason TEXT,                   -- その他理由
    status TEXT DEFAULT 'pending',       -- ステータス（pending, approved, rejected）
    approved_by TEXT,                    -- 承認者
    approved_at TEXT,                    -- 承認日時
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

---

### late_arrival_requests

遅刻申告を格納します。

```sql
CREATE TABLE late_arrival_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_num INTEGER NOT NULL,
    employee_name TEXT NOT NULL,
    request_date TEXT NOT NULL,      -- 申告日（YYYY-MM-DD）
    work_date TEXT NOT NULL,         -- 勤務日（YYYY-MM-DD）
    late_minutes INTEGER NOT NULL,   -- 遅刻分数
    reason TEXT,                     -- 理由
    status TEXT DEFAULT 'pending',    -- ステータス（pending, approved, rejected）
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

---

### early_leave_requests

早退申告を格納します。

```sql
CREATE TABLE early_leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_num INTEGER NOT NULL,
    employee_name TEXT NOT NULL,
    request_date TEXT NOT NULL,      -- 申告日（YYYY-MM-DD）
    work_date TEXT NOT NULL,         -- 勤務日（YYYY-MM-DD）
    early_minutes INTEGER NOT NULL,  -- 早退分数
    reason TEXT,                     -- 理由
    status TEXT DEFAULT 'pending',    -- ステータス（pending, approved, rejected）
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

---

### attendance_check_status

打刻チェック状況を格納します（管理者がエラーを確認済みかどうか）。

```sql
CREATE TABLE attendance_check_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_num TEXT NOT NULL,
    work_date TEXT NOT NULL,         -- 勤務日（YYYY-MM-DD）
    check_type TEXT NOT NULL,         -- チェックタイプ（missing_punch, time_difference, punch_leak）
    is_checked BOOLEAN DEFAULT FALSE, -- チェック済みかどうか
    checked_by TEXT,                  -- チェックした人
    checked_at TEXT,                  -- チェック日時
    notes TEXT,                       -- 備考（例: "時間外なし"）
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(employee_num, work_date, check_type)
);
```

**チェックタイプ:**
- `missing_punch`: 打刻なしエラー
- `time_difference`: 時刻差異エラー
- `punch_leak`: 打刻漏れエラー

---

## インデックス

### パフォーマンス向上のためのインデックス

| テーブル | インデックス名 | カラム |
|---------|--------------|--------|
| `attendance` | `idx_idm` | `idm` |
| `attendance` | `idx_timestamp` | `timestamp` |
| `attendance` | `idx_terminal_id` | `terminal_id` |
| `late_arrival_requests` | `idx_late_employee` | `employee_num` |
| `late_arrival_requests` | `idx_late_work_date` | `work_date` |
| `late_arrival_requests` | `idx_late_status` | `status` |
| `early_leave_requests` | `idx_early_employee` | `employee_num` |
| `early_leave_requests` | `idx_early_work_date` | `work_date` |
| `early_leave_requests` | `idx_early_status` | `status` |
| `leave_requests` | `idx_leave_employee` | `employee_num` |
| `leave_requests` | `idx_leave_date` | `leave_date_from` |
| `leave_requests` | `idx_leave_status` | `status` |
| `overtime_applications` | `idx_overtime_employee` | `employee_num` |
| `overtime_applications` | `idx_overtime_work_date` | `work_date` |
| `overtime_applications` | `idx_overtime_status` | `status` |
| `attendance_check_status` | `idx_check_status_employee` | `employee_num` |
| `attendance_check_status` | `idx_check_status_date` | `work_date` |
| `attendance_check_status` | `idx_check_status_type` | `check_type` |

---

## リレーション

### 論理的な関連（外部キー制約なし）

```
employee_master
  └─ idm ──→ attendance.idm

employee_master
  └─ employee_num ──→ attend_schedule.employee_id

employee_master
  └─ employee_num ──→ overtime_applications.employee_num

employee_master
  └─ employee_num ──→ leave_requests.employee_num

employee_master
  └─ employee_num ──→ late_arrival_requests.employee_num

employee_master
  └─ employee_num ──→ early_leave_requests.employee_num

employee_master
  └─ employee_num ──→ attendance_check_status.employee_num
```

**注意**: SQLiteでは外部キー制約を有効化できますが、現在の実装では使用していません。論理的な関連のみです。

---

## データ型

| SQLite型 | 説明 | 例 |
|---------|------|-----|
| `INTEGER` | 整数 | `123` |
| `TEXT` | 文字列 | `"2026-01-15"` |
| `BOOLEAN` | 真偽値 | `TRUE`, `FALSE` |
| `DATETIME` | 日時（SQLiteではTEXTとして保存） | `"2026-01-15T09:30:45"` |

---

## 日付・時刻フォーマット

- **日付**: `YYYY-MM-DD`（例: `2026-01-15`）
- **時刻**: `HH:MM`（例: `09:30`）
- **日時**: `YYYY-MM-DDTHH:MM:SS`（ISO 8601形式、例: `2026-01-15T09:30:45`）

---

## 関連ドキュメント

- [システムアーキテクチャ](SYSTEM_ARCHITECTURE.md)
- [APIリファレンス](API_REFERENCE.md)

