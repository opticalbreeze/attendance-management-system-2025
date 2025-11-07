# 📊 システム概要

勤怠打刻システムの全体像と技術仕様をまとめています。

---

## 🎯 システムの目的

NFCカードリーダーを使用した打刻データの収集・管理、勤怠チェック、時間外申告管理を行う統合システムです。

---

## 🏗️ システムアーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│                    ユーザー                              │
│                    (ブラウザ)                            │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP
                        ↓
┌─────────────────────────────────────────────────────────┐
│               Flask Webサーバー                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  server.py     - メインサーバー                  │   │
│  │  api.py        - REST API                       │   │
│  │  database.py   - データベース操作                │   │
│  │  overtime.py   - 時間外申告管理                  │   │
│  │  utils.py      - ユーティリティ                  │   │
│  │  config.py     - 設定管理                        │   │
│  └─────────────────────────────────────────────────┘   │
│                        │                                 │
│                        ↓                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  SQLite データベース                              │   │
│  │  - attendance (打刻データ)                       │   │
│  │  - employee_master (従業員マスタ)               │   │
│  │  - attend_schedule (勤怠スケジュール)           │   │
│  │  - overtime_applications (時間外申告)           │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                        ↑
                        │ POST /api/attendance
                        │
┌─────────────────────────────────────────────────────────┐
│              NFCクライアント                              │
│         (Raspberry Pi / Windows)                        │
│  - カードリーダー接続                                     │
│  - 打刻データ送信                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 💻 技術スタック

### バックエンド
- **言語**: Python 3.11
- **Webフレームワーク**: Flask 3.x
- **データベース**: SQLite3
- **コンテナ**: Docker / Docker Compose

### フロントエンド
- **HTML5** + **CSS3**
- **JavaScript** (Vanilla JS - フレームワーク不使用)
- **Fetch API** (非同期通信)

### インフラ
- **OS**: Windows / Linux
- **実行環境**: Docker コンテナ
- **データベース配置**: ホスト側（Dockerの外）

---

## 📋 主要機能

### 1. 打刻データ管理

**機能:**
- NFCカードリーダーからの打刻データ受信
- チャタリング防止（重複除外）
- リアルタイム統計表示
- 打刻履歴検索

**API:**
```
POST /api/attendance      # 打刻データ受信
GET  /api/stats           # 統計情報
GET  /api/search          # データ検索
```

### 2. 勤怠チェック

**機能:**
- スケジュールと実績の差異チェック
- 休日打刻アラート
- 未打刻アラート
- 時間外申告との照合

**画面:**
- `/check` - 勤怠チェック画面

**API:**
```
GET /api/attendance_check
```

### 3. 時間外申告管理（NEW!）

**機能:**
- 時間外作業の申告（最大4件/日）
- 内残業/外残業の自動分類
- 深夜時間（20:00-05:00）の自動計算
- 申告の承認・却下
- 月次集計（前月16日〜当月15日）

**画面:**
- `/overtime` - 時間外申告
- `/overtime/list` - 時間外一覧・承認

**API:**
```
POST /api/overtime                  # 申告登録
GET  /api/overtime                  # 申告取得
POST /api/overtime/<id>/approve     # 承認
POST /api/overtime/<id>/reject      # 却下
GET  /api/overtime/monthly_summary  # 月次集計
```

**自動計算ロジック:**

```python
# 内残業: 勤務時間内の休憩時間を潰した作業
if 時間外開始 >= 勤務開始 and 時間外終了 <= 勤務終了:
    内残業

# 外残業: 勤務予定外の作業
if 時間外開始 < 勤務開始 or 時間外終了 > 勤務終了:
    外残業

# 深夜時間: 20:00-05:00
if 時間外時間 ∩ (20:00-05:00):
    深夜時間を計算
```

### 4. 従業員マスタ管理

**機能:**
- 従業員情報管理
- カードIDとの紐付け
- 24勤シフトの判定

**API:**
```
GET /api/employees
```

---

## 🗄️ データベーススキーマ

### attendance（打刻データ）

| カラム名 | 型 | 説明 |
|---------|---|------|
| id | INTEGER | 主キー |
| idm | TEXT | カードID |
| timestamp | TEXT | 打刻時刻 |
| terminal_id | TEXT | 端末ID |
| received_at | TEXT | 受信時刻 |

**インデックス:**
- `idx_idm` - IDmでの検索
- `idx_timestamp` - 日時での検索
- `idx_terminal_id` - 端末での検索

### employee_master（従業員マスタ）

| カラム名 | 型 | 説明 |
|---------|---|------|
| id | INTEGER | 主キー |
| employee_num | INTEGER | 従業員番号 |
| name | TEXT | 氏名 |
| idm | TEXT | カードID |
| created_at | DATETIME | 登録日時 |
| updated_at | DATETIME | 更新日時 |

### attend_schedule（勤怠スケジュール）

| カラム名 | 型 | 説明 |
|---------|---|------|
| id | INTEGER | 主キー |
| sheet_number | TEXT | シート番号 |
| employee_id | TEXT | 従業員ID |
| employee_name | TEXT | 従業員名 |
| work_date | TEXT | 勤務日 |
| work_type | TEXT | 勤務区分 |
| start_time | TEXT | 開始時刻 |
| end_time | TEXT | 終了時刻 |
| created_at | TEXT | 登録日時 |
| updated_at | TEXT | 更新日時 |

### overtime_applications（時間外申告）

| カラム名 | 型 | 説明 |
|---------|---|------|
| id | INTEGER | 主キー |
| employee_num | TEXT | 従業員番号 |
| employee_name | TEXT | 従業員名 |
| application_date | TEXT | 申告日 |
| work_date | TEXT | 作業日 |
| start_time | TEXT | 開始時刻 |
| end_time | TEXT | 終了時刻 |
| description | TEXT | 作業内容 |
| status | TEXT | pending/approved/rejected |
| overtime_type | TEXT | 内残業/外残業 |
| inner_overtime_minutes | INTEGER | 内残業時間（分） |
| outer_overtime_minutes | INTEGER | 外残業時間（分） |
| night_overtime_minutes | INTEGER | 深夜時間（分） |
| approved_by | TEXT | 承認者 |
| approved_at | TEXT | 承認日時 |
| created_at | TEXT | 登録日時 |
| updated_at | TEXT | 更新日時 |

**インデックス:**
- `idx_overtime_employee` - 従業員番号
- `idx_overtime_work_date` - 作業日
- `idx_overtime_status` - ステータス

---

## 🔄 データフロー

### 打刻データの流れ

```
1. NFCカード読み取り
   ↓
2. クライアント → サーバー (POST /api/attendance)
   {
     "idm": "XXXXX",
     "timestamp": "2025-11-06T09:00:00",
     "terminal_id": "TERMINAL_01"
   }
   ↓
3. チャタリング防止チェック
   - 同じIDm + 端末で10秒以内 → 重複として除外
   ↓
4. データベースに保存 (attendance テーブル)
   ↓
5. レスポンス返却
   {
     "status": "success",
     "attendance_id": 123
   }
```

### 時間外申告の流れ

```
1. Web画面で申告入力
   - 従業員選択
   - 作業日・時間・内容入力
   ↓
2. JavaScript → サーバー (POST /api/overtime)
   {
     "employee_num": "2952089",
     "work_date": "2025-11-05",
     "overtime_entries": [
       {
         "start_time": "18:00",
         "end_time": "20:00",
         "description": "緊急対応"
       }
     ]
   }
   ↓
3. サーバー側で自動計算
   - スケジュールと照合
   - 内残業/外残業を判定
   - 深夜時間を計算
   ↓
4. データベースに保存（status: pending）
   ↓
5. 管理者が承認/却下
   - POST /api/overtime/{id}/approve
   - POST /api/overtime/{id}/reject
   ↓
6. ステータス更新（approved/rejected）
```

---

## ⚙️ 設定管理

### 環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|------------|------|
| SERVER_HOST | 0.0.0.0 | サーバーホスト |
| SERVER_PORT | 5000 | ポート番号 |
| FLASK_DEBUG | False | デバッグモード |
| DATABASE_PATH | ../data/attendance.db | DB パス |
| CHATTERING_THRESHOLD | 10 | チャタリング防止（秒） |
| PAYROLL_START_DAY | 16 | 給与期間開始日 |
| PAYROLL_END_DAY | 15 | 給与期間終了日 |

### 設定クラス

```python
# server/config.py
class Config:
    HOST = os.environ.get('SERVER_HOST', '0.0.0.0')
    PORT = int(os.environ.get('SERVER_PORT', '5000'))
    DATABASE_PATH = os.environ.get('DATABASE_PATH', '../../data/attendance.db')
    CHATTERING_THRESHOLD_SECONDS = int(os.environ.get('CHATTERING_THRESHOLD', '10'))
    PAYROLL_START_DAY = int(os.environ.get('PAYROLL_START_DAY', '16'))
    PAYROLL_END_DAY = int(os.environ.get('PAYROLL_END_DAY', '15'))
```

---

## 🔒 セキュリティ考慮事項

### 現在の実装

- ✅ IP制限（設定可能）
- ✅ チャタリング防止
- ✅ SQLインジェクション対策（パラメータバインディング）
- ✅ データベースをDockerの外に配置

### 今後の実装（本番運用時）

- 📄 管理者認証（トークンベース）
- 📄 監査ログ
- 📄 自動バックアップ
- 📄 HTTPS対応

詳細は **[SECURITY_IMPLEMENTATION_GUIDE.md](./SECURITY_IMPLEMENTATION_GUIDE.md)** を参照

---

## 📊 パフォーマンス

### スケーラビリティ

- **同時接続**: 100接続程度まで対応（開発サーバー）
- **データベース**: SQLite（数万件まで高速）
- **応答時間**: 平均50-100ms

### 制限事項

- SQLiteは1ライターのため、大量の同時書き込みには不向き
- 本格的な運用にはPostgreSQL等への移行を推奨

---

## 🛠️ 拡張性

### 追加可能な機能

1. **通知機能**
   - Discord Webhook
   - メール通知（GAS）

2. **レポート機能**
   - 月次勤怠レポート
   - 時間外集計レポート
   - CSV/PDF出力

3. **認証・認可**
   - ユーザー管理
   - ロールベースアクセス制御

4. **クライアント側機能**
   - オフライン対応
   - 打刻時の音声通知
   - LCD表示対応

---

## 📝 更新履歴

### v2.0.0 (2025-11-06)
- 時間外申告機能の追加
- 自動分類（内残業/外残業/深夜）
- 承認・却下ワークフロー
- 月次集計機能

### v1.0.0 (2025-10-23)
- 初回リリース
- 打刻データ管理
- 勤怠チェック
- Docker対応

---

**更新日**: 2025-11-06
