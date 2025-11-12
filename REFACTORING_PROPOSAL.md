# 🔧 リファクタリング提案

## 発見された冗長な部分と改善提案

### 1. データベース接続の重複 ⚠️ **優先度: 高**

**問題点:**
- `utils.py`の`check_duplicate_attendance`関数内で`sqlite3.connect(Config.DATABASE_PATH)`を直接呼んでいる
- `get_database_connection()`関数が既に存在するのに使用されていない

**場所:**
- `server/utils.py:26`

**改善案:**
```python
# 修正前
conn = sqlite3.connect(Config.DATABASE_PATH)

# 修正後
conn = get_database_connection()
```

---

### 2. テーブル初期化の分散 ⚠️ **優先度: 中**

**問題点:**
- テーブル初期化が3つのファイルに分散している
  - `database.py`: `init_database()` - attendance, employee_master, late_arrival_requests, early_leave_requests
  - `leave_request.py`: `init_leave_request_table()` - leave_requests
  - `overtime.py`: `init_overtime_table()` - overtime_applications

**改善案:**
- すべてのテーブル初期化を`database.py`の`init_database()`に統合
- `leave_request.py`と`overtime.py`の初期化関数は`database.py`から呼び出すように変更

**メリット:**
- テーブル作成の一元管理
- マイグレーション管理が容易
- 初期化順序の制御が容易

---

### 3. 承認/却下/取り下げ処理の重複パターン ⚠️ **優先度: 中**

**問題点:**
- 時間外申告と休暇願で同じような承認/却下/取り下げ処理が重複している
- パターンは同じだが、テーブル名とカラム名が異なるだけ

**場所:**
- `server/overtime.py`: `approve_overtime()`, `reject_overtime()`, `withdraw_overtime()`
- `server/leave_request.py`: `approve_leave_request()`, `reject_leave_request()`, `withdraw_leave_request()`
- `server/api_overtime.py`: 承認/却下/取り下げAPI
- `server/api_leave.py`: 承認/却下/取り下げAPI

**改善案:**
- `utils.py`に汎用的なステータス更新関数を追加
```python
def update_request_status(table_name, request_id, status, updated_by=None):
    """
    申請のステータスを更新（汎用関数）
    
    Args:
        table_name: テーブル名 ('overtime_applications' or 'leave_requests')
        request_id: 申請ID
        status: 新しいステータス ('approved', 'rejected', 'withdrawn')
        updated_by: 更新者（オプション）
    """
    # 共通処理
```

**メリット:**
- コードの重複削減
- バグ修正が1箇所で済む
- 新しい申請タイプの追加が容易

---

### 4. フロントエンドの従業員リスト読み込み処理の重複 ⚠️ **優先度: 低**

**問題点:**
- 6つのHTMLファイルで同じような従業員リスト読み込み処理が重複している
  - `check.html`, `search.html`, `leave_check.html`, `overtime_check.html`, `leave.html`, `overtime.html`

**重複している関数:**
- `loadEmployees()`
- `updateEmployeeList()`
- `allEmployees`変数

**改善案:**
- 共通のJavaScriptファイル（`static/js/common.js`）を作成
- 従業員リスト読み込み処理を共通化

**メリット:**
- コードの重複削減
- バグ修正が1箇所で済む
- メンテナンス性向上

---

### 5. インデックス作成パターンの重複 ⚠️ **優先度: 低**

**問題点:**
- 各テーブル初期化関数で同じようなインデックス作成パターンが繰り返されている

**改善案:**
- インデックス定義を辞書形式で管理し、ループで作成
```python
INDEXES = {
    'late_arrival_requests': [
        ('idx_late_employee', 'employee_num'),
        ('idx_late_work_date', 'work_date'),
        ('idx_late_status', 'status')
    ],
    # ...
}
```

---

## 推奨される改善順序

1. **優先度: 高** - データベース接続の統一（即座に修正可能）
2. **優先度: 中** - テーブル初期化の統合（影響範囲が大きいため慎重に）
3. **優先度: 中** - 承認/却下/取り下げ処理の共通化（テストが必要）
4. **優先度: 低** - フロントエンドの共通化（時間があるときに）

---

## その他の観察事項

### ✅ 良い点
- `get_database_connection()`が`utils.py`に統一されている
- `save_pdf_from_html()`が共通化されている
- `format_response()`が統一されている
- モジュール分割が適切

### 📝 改善の余地がある点
- エラーハンドリングのパターンが一部統一されていない
- ログ出力の形式が統一されていない
- 一部の関数でdocstringが不足している

---

## 実装の推奨

まずは**優先度: 高**の項目から実装することを推奨します。
これにより、コードの一貫性が向上し、メンテナンスが容易になります。

---

## ✅ 実装完了状況

### ✅ 完了した項目

1. **✅ 優先度: 高 - データベース接続の統一**
   - `utils.py`の`check_duplicate_attendance`関数を修正
   - `get_database_connection()`を使用するように変更

2. **✅ 優先度: 中 - テーブル初期化の統合**
   - すべてのテーブル初期化を`database.py`の`init_database()`に統合
   - `init_leave_request_table_internal()`と`init_overtime_table_internal()`を追加
   - `server.py`からは`init_database()`のみを呼び出すように変更
   - 後方互換性のため、既存の関数は残存（内部関数を呼び出すように変更）

3. **✅ 優先度: 中 - 承認/却下/取り下げ処理の共通化**
   - `utils.py`に`update_request_status()`汎用関数を追加
   - `overtime.py`と`leave_request.py`の承認/却下/取り下げ関数を共通関数を使用するように変更
   - コードの重複を大幅に削減

4. **✅ 優先度: 低 - フロントエンドの共通化**
   - `server/static/js/employee-list.js`を作成
   - 共通の従業員リスト管理関数を提供
   - 各HTMLファイルで使用可能（必要に応じて各ファイルを個別に更新）

### 📝 今後の改善点

- 各HTMLファイルで共通JavaScriptファイルを読み込むように更新（必要に応じて）
- エラーハンドリングのパターン統一
- ログ出力の形式統一


