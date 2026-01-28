# 勤怠打刻システム - システムアーキテクチャ

## 📋 目次

1. [システム概要](#システム概要)
2. [アーキテクチャ構成](#アーキテクチャ構成)
3. [主要コンポーネント](#主要コンポーネント)
4. [データフロー](#データフロー)
5. [データベース設計](#データベース設計)
6. [環境分離](#環境分離)

---

## システム概要

勤怠打刻システムは、ICカードリーダーからの打刻データを受信・管理し、Webブラウザで検索・確認・集計を行うシステムです。

### 主要機能

- **打刻データ管理**: ICカードリーダーからの打刻データ受信・保存
- **勤怠チェック**: スケジュールと実績の差異チェック
- **時間外申告**: 時間外作業の申告・承認管理
- **休暇願管理**: 休暇申請の登録・承認管理
- **月間レポート**: 月度集計レポートの生成・出力

---

## アーキテクチャ構成

```
┌─────────────────────────────────────────────────────────────┐
│                     勤怠打刻システム                          │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐
│   クライアント側   │         │    サーバー側     │
│  (ICカードリーダー) │  WiFi  │   (Flask Web)   │
│                   │ ─────→ │                  │
│  - win_client.py  │         │  - server.py     │
│  - カード読み取り  │         │  - API Routes    │
│  - データ送信      │ ←───── │  - Database      │
└──────────────────┘         └──────────────────┘
                                      │
                                      ↓
                              ┌───────────────┐
                              │  SQLite DB    │
                              │  attendance.db│
                              └───────────────┘

┌──────────────────┐
│   Webブラウザ    │
│                  │ ─────→ │  サーバー側      │
│  - 検索画面      │         │  - Templates    │
│  - 勤怠チェック  │         │  - Static Files │
│  - 時間外申告    │         │  - API          │
│  - 月間レポート  │         │                  │
└──────────────────┘         └──────────────────┘
```

---

## 主要コンポーネント

### サーバー側（Flask）

#### コアモジュール

- **`server.py`**: メインサーバーアプリケーション、ルート定義
- **`database.py`**: データベース操作（テーブル作成、CRUD操作）
- **`config.py`**: 設定管理（データベースパス、サーバー設定）
- **`constants.py`**: 定数定義（アラートタイプ、チェックタイプなど）
- **`utils.py`**: ユーティリティ関数（日付計算、レスポンスフォーマットなど）

#### APIモジュール

- **`api_attendance.py`**: 打刻データAPI（受信、検索、統計）
- **`api_overtime.py`**: 時間外申告API（作成、取得、承認・却下）
- **`api_leave.py`**: 休暇願API（作成、取得、承認・却下）
- **`api_monthly_report.py`**: 月間レポートAPI（集計、Excel出力）
- **`api_check_status.py`**: 打刻チェック状況API（確認状態の管理）

#### ビジネスロジックモジュール

- **`attendance_check_service.py`**: 勤怠チェックロジック（スケジュールと実績の照合）
- **`overtime.py`**: 時間外申告管理ロジック
- **`leave_request.py`**: 休暇願管理ロジック
- **`monthly_report.py`**: 月間レポート生成ロジック

#### 認証・管理モジュール

- **`auth.py`**: 認証機能（ログイン、セッション管理）
- **`admin.py`**: 管理者機能（CSVアップロード、データベース管理）

#### フロントエンド

- **`templates/`**: HTMLテンプレート（本番環境）
- **`templates_dev/`**: HTMLテンプレート（開発環境）
- **`static/`**: 静的ファイル（CSS、JavaScript、本番環境）
- **`static_dev/`**: 静的ファイル（CSS、JavaScript、開発環境）

### クライアント側（Windows）

- **`card-reder-for-win/win_client.py`**: ICカードリーダー連携クライアント
- **`card-reder-for-win/notification_client.py`**: 通知クライアント

---

## データフロー

### 打刻データの流れ

```
1. ICカードリーダーでカード読み取り
   ↓
2. win_client.pyがIDmを取得
   ↓
3. 打刻時刻と端末IDを記録
   ↓
4. POST /api/attendance に送信
   ↓
5. server.pyが受信
   ↓
6. database.pyがattendanceテーブルに保存
   ↓
7. レスポンス返却
```

### 勤怠チェックの流れ

```
1. Webブラウザで /check にアクセス
   ↓
2. GET /api/search でスケジュール取得
   ↓
3. GET /api/attendance_check で実績チェック
   ↓
4. attendance_check_service.pyが差異を検出
   ↓
5. アラートを生成
   ↓
6. Web画面に表示
```

---

## データベース設計

### テーブル一覧

#### 1. `attendance` - 打刻データ

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
- `idx_idm`: IDmでの検索高速化
- `idx_timestamp`: 日時での検索高速化
- `idx_terminal_id`: 端末IDでの検索高速化

#### 2. `employee_master` - 従業員マスタ

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

#### 3. `attend_schedule` - 勤務スケジュール

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

#### 4. `overtime_applications` - 時間外申告

```sql
CREATE TABLE overtime_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_num TEXT NOT NULL,
    employee_name TEXT NOT NULL,
    application_date TEXT NOT NULL,
    work_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    inner_overtime_minutes INTEGER DEFAULT 0,
    outer_overtime_minutes INTEGER DEFAULT 0,
    night_overtime_minutes INTEGER DEFAULT 0,
    description TEXT,
    status TEXT DEFAULT 'pending',
    approved_by TEXT,
    approved_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

#### 5. `leave_requests` - 休暇願

```sql
CREATE TABLE leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_num TEXT NOT NULL,
    employee_name TEXT NOT NULL,
    application_date TEXT NOT NULL,
    leave_date_from TEXT NOT NULL,
    leave_date_to TEXT NOT NULL,
    leave_type TEXT NOT NULL,
    leave_subtype TEXT,
    substitute_work_date TEXT,
    other_reason TEXT,
    status TEXT DEFAULT 'pending',
    approved_by TEXT,
    approved_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

#### 6. `late_arrival_requests` - 遅刻申告

```sql
CREATE TABLE late_arrival_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_num INTEGER NOT NULL,
    employee_name TEXT NOT NULL,
    request_date TEXT NOT NULL,
    work_date TEXT NOT NULL,
    late_minutes INTEGER NOT NULL,
    reason TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

#### 7. `early_leave_requests` - 早退申告

```sql
CREATE TABLE early_leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_num INTEGER NOT NULL,
    employee_name TEXT NOT NULL,
    request_date TEXT NOT NULL,
    work_date TEXT NOT NULL,
    early_minutes INTEGER NOT NULL,
    reason TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

#### 8. `attendance_check_status` - 打刻チェック状況

```sql
CREATE TABLE attendance_check_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_num TEXT NOT NULL,
    work_date TEXT NOT NULL,
    check_type TEXT NOT NULL,      -- 'missing_punch', 'time_difference', 'punch_leak'
    is_checked BOOLEAN DEFAULT FALSE,
    checked_by TEXT,
    checked_at TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(employee_num, work_date, check_type)
);
```

---

## 環境分離

システムは開発環境（5001ポート）と本番環境（5000ポート）を分離しています。

### 開発環境

- **ポート**: 5001
- **テンプレート**: `templates_dev/`
- **静的ファイル**: `static_dev/`
- **Docker Compose**: `docker-compose.dev.yml`

### 本番環境

- **ポート**: 5000
- **テンプレート**: `templates/`
- **静的ファイル**: `static/`
- **Docker Compose**: `docker-compose.yml`

### 環境分離の目的

- 開発中の変更が本番環境に影響しないようにする
- 開発環境で検証してから本番環境に反映する

詳細は `server/ENVIRONMENT_SEPARATION.md` を参照してください。

---

## セキュリティ

- **認証**: セッション管理による認証（`auth.py`）
- **パスワード**: 管理者パスワードとデータベースパスワードの分離
- **CSRF対策**: セッションクッキーの設定

詳細は `server/SECURITY_SETUP.md` を参照してください。

---

## 運用

### 起動方法

**開発環境:**
```bash
cd server
docker-compose -f docker-compose.dev.yml up -d
```

**本番環境:**
```bash
cd server
docker-compose up -d
```

### バックアップ

- 自動バックアップ: `auto_save.py`が定期的にデータベースをバックアップ
- 手動バックアップ: `backup_database.py`を実行

### ログ

- サーバーログ: Dockerコンテナのログに出力
- アプリケーションログ: `logger_config.py`で設定

---

## 関連ドキュメント

- [APIリファレンス](API_REFERENCE.md)
- [データベーススキーマ](DATABASE_SCHEMA.md)
- [開発ガイド](../server/README_DEV.md)
- [環境分離ガイド](../server/ENVIRONMENT_SEPARATION.md)

