# APIリファレンス

勤怠打刻システムのAPIエンドポイント一覧です。

## 📋 目次

1. [共通仕様](#共通仕様)
2. [打刻・勤怠API](#打刻勤怠api)
3. [時間外申告API](#時間外申告api)
4. [休暇願API](#休暇願api)
5. [月間レポートAPI](#月間レポートapi)
6. [打刻チェック状況API](#打刻チェック状況api)
7. [管理者API](#管理者api)

---

## 共通仕様

### ベースURL

- 開発環境: `http://localhost:5001`
- 本番環境: `http://localhost:5000`

### レスポンス形式

```json
{
  "status": "success" | "error",
  "message": "メッセージ",
  "data": { ... }
}
```

### エラーレスポンス

```json
{
  "status": "error",
  "message": "エラーメッセージ"
}
```

---

## 打刻・勤怠API

### POST /api/attendance

打刻データを受信します。

**リクエスト:**
```json
{
  "idm": "012E447C1234ABCD",
  "timestamp": "2026-01-15T09:30:45",
  "terminal_id": "AA:BB:CC:DD:EE:FF"
}
```

**レスポンス:**
```json
{
  "status": "success",
  "message": "打刻データを保存しました",
  "attendance_id": 123
}
```

**重複データの場合:**
```json
{
  "status": "duplicate",
  "message": "重複データ",
  "time_diff": 5
}
```

---

### GET /api/search

勤怠スケジュールを検索します。

**クエリパラメータ:**
- `employee_id` (必須): 従業員ID
- `search_month` (必須): 検索月（YYYY-MM形式）
- `limit` (オプション): 取得件数上限（デフォルト: 1000）

**レスポンス:**
```json
{
  "status": "success",
  "count": 31,
  "results": [
    {
      "employee_id": "2952089",
      "employee_name": "横山 正明",
      "work_date": "2026-01-16",
      "work_type": "日勤",
      "start_time": "08:30",
      "end_time": "17:30",
      "alerts": [
        {
          "type": "warning",
          "message": "出勤時刻に差異あり",
          "details": "出勤時刻: スケジュール 08:30 / 実際 07:37 (差異: -53分)"
        }
      ],
      "actual_clock_in": "07:37",
      "actual_clock_out": null
    }
  ],
  "search_params": {
    "employee_id": "2952089",
    "search_month": "2026-01",
    "date_range": {
      "start_date": "2026-01-16",
      "end_date": "2026-02-15"
    }
  }
}
```

---

### GET /api/attendance_check

指定日の勤怠をチェックします。

**クエリパラメータ:**
- `employee_id` (必須): 従業員ID
- `work_date` (必須): 勤務日（YYYY-MM-DD形式）

**レスポンス:**
```json
{
  "status": "success",
  "data": {
    "employee_id": "2952089",
    "work_date": "2026-01-16",
    "schedule": {
      "work_type": "日勤",
      "start_time": "08:30",
      "end_time": "17:30"
    },
    "actual_clock_in": "07:37",
    "actual_clock_out": null,
    "alerts": [
      {
        "type": "warning",
        "message": "出勤時刻に差異あり",
        "details": "..."
      }
    ]
  }
}
```

---

### GET /api/stats

統計情報を取得します。

**レスポンス:**
```json
{
  "status": "success",
  "data": {
    "total_records": 12345,
    "today_records": 45,
    "unique_employees": 120
  }
}
```

---

### GET /api/employees

従業員一覧を取得します。

**レスポンス:**
```json
{
  "status": "success",
  "data": [
    {
      "employee_num": "2952089",
      "name": "横山 正明",
      "idm": "012E447C1234ABCD",
      "section": "設備"
    }
  ]
}
```

---

## 時間外申告API

### POST /api/overtime

時間外申告を作成します。

**リクエスト:**
```json
{
  "employee_num": "2952089",
  "employee_name": "横山 正明",
  "application_date": "2026-01-15",
  "work_date": "2026-01-16",
  "start_time": "07:00",
  "end_time": "08:30",
  "description": "早朝作業"
}
```

**レスポンス:**
```json
{
  "status": "success",
  "message": "時間外作業申告を登録しました",
  "data": {
    "id": 123,
    "inner_overtime_minutes": 60,
    "outer_overtime_minutes": 30,
    "night_overtime_minutes": 0
  }
}
```

---

### GET /api/overtime

時間外申告一覧を取得します。

**クエリパラメータ:**
- `employee_num` (オプション): 従業員番号でフィルタ
- `work_date` (オプション): 勤務日でフィルタ
- `status` (オプション): ステータスでフィルタ（pending, approved, rejected）
- `limit` (オプション): 取得件数上限（デフォルト: 100）

**レスポンス:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 123,
      "employee_num": "2952089",
      "employee_name": "横山 正明",
      "work_date": "2026-01-16",
      "start_time": "07:00",
      "end_time": "08:30",
      "inner_overtime_minutes": 60,
      "outer_overtime_minutes": 30,
      "status": "pending"
    }
  ]
}
```

---

### POST /api/overtime/<id>/approve

時間外申告を承認します。

**認証:** 管理者ログイン必須

**レスポンス:**
```json
{
  "status": "success",
  "message": "時間外申告を承認しました"
}
```

---

### POST /api/overtime/<id>/reject

時間外申告を却下します。

**認証:** 管理者ログイン必須

**リクエスト:**
```json
{
  "reason": "却下理由"
}
```

**レスポンス:**
```json
{
  "status": "success",
  "message": "時間外申告を却下しました"
}
```

---

## 休暇願API

### POST /api/leave

休暇願を作成します。

**リクエスト:**
```json
{
  "employee_num": "2952089",
  "employee_name": "横山 正明",
  "application_date": "2026-01-15",
  "leave_date_from": "2026-01-20",
  "leave_date_to": "2026-01-20",
  "leave_type": "有給",
  "leave_subtype": null,
  "other_reason": null
}
```

**レスポンス:**
```json
{
  "status": "success",
  "message": "休暇願を登録しました",
  "data": {
    "id": 456
  }
}
```

---

### GET /api/leave

休暇願一覧を取得します。

**クエリパラメータ:**
- `employee_num` (オプション): 従業員番号でフィルタ
- `status` (オプション): ステータスでフィルタ
- `limit` (オプション): 取得件数上限

**レスポンス:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 456,
      "employee_num": "2952089",
      "employee_name": "横山 正明",
      "leave_date_from": "2026-01-20",
      "leave_date_to": "2026-01-20",
      "leave_type": "有給",
      "status": "pending"
    }
  ]
}
```

---

### POST /api/leave/<id>/approve

休暇願を承認します。

**認証:** 管理者ログイン必須

---

### POST /api/leave/<id>/reject

休暇願を却下します。

**認証:** 管理者ログイン必須

---

## 月間レポートAPI

### GET /api/monthly-report

月間レポートを生成します。

**クエリパラメータ:**
- `employee_id` (必須): 従業員ID
- `search_month` (必須): 検索月（YYYY-MM形式）

**レスポンス:**
```json
{
  "status": "success",
  "data": {
    "employee_id": "2952089",
    "employee_name": "横山 正明",
    "search_month": "2026-01",
    "summary": {
      "total_work_days": 20,
      "total_overtime_hours": 15.5,
      "total_leave_days": 2
    },
    "daily_data": [ ... ]
  }
}
```

---

### GET /api/monthly-report/excel

月間レポートをExcel形式でダウンロードします。

**クエリパラメータ:**
- `employee_id` (必須): 従業員ID
- `search_month` (必須): 検索月（YYYY-MM形式）

**レスポンス:** Excelファイル（バイナリ）

---

## 打刻チェック状況API

### GET /api/attendance-check-status

打刻チェック状況を取得します。

**クエリパラメータ:**
- `employee_num` (必須): 従業員番号
- `work_date` (必須): 勤務日（YYYY-MM-DD形式）
- `check_type` (必須): チェックタイプ（`missing_punch`, `time_difference`, `punch_leak`）

**レスポンス:**
```json
{
  "status": "success",
  "data": {
    "id": 789,
    "employee_num": "2952089",
    "work_date": "2026-01-16",
    "check_type": "time_difference",
    "is_checked": true,
    "checked_by": "admin",
    "checked_at": "2026-01-16T10:00:00",
    "notes": "時間外なし"
  }
}
```

---

### POST /api/attendance-check-status

打刻チェック状況を更新します。

**認証:** 管理者ログイン必須

**リクエスト:**
```json
{
  "employee_num": "2952089",
  "work_date": "2026-01-16",
  "check_type": "time_difference",
  "is_checked": true,
  "notes": "時間外なし"
}
```

**レスポンス:**
```json
{
  "status": "success",
  "message": "打刻チェック状況を更新しました"
}
```

---

## 管理者API

### POST /api/admin/csv/upload

CSVファイルをアップロードしてスケジュールをインポートします。

**認証:** 管理者ログイン必須

**リクエスト:** multipart/form-data
- `file`: CSVファイル

**レスポンス:**
```json
{
  "status": "success",
  "message": "CSVファイルをアップロードしました",
  "data": {
    "imported_count": 100
  }
}
```

---

### GET /api/admin/database/stats

データベース統計情報を取得します。

**認証:** 管理者ログイン必須

**レスポンス:**
```json
{
  "status": "success",
  "data": {
    "attendance_count": 12345,
    "employee_count": 120,
    "schedule_count": 3600
  }
}
```

---

## エラーコード

| HTTPステータス | 説明 |
|---------------|------|
| 200 | 成功 |
| 400 | リクエストエラー（パラメータ不正など） |
| 401 | 認証エラー（ログイン必須） |
| 500 | サーバーエラー |

---

## 関連ドキュメント

- [システムアーキテクチャ](SYSTEM_ARCHITECTURE.md)
- [データベーススキーマ](DATABASE_SCHEMA.md)

