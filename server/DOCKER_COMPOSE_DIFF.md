# Docker Compose設定とマウントファイルの差異リスト

## 概要
このドキュメントは、5000（本番環境）と5001（開発環境）のdocker-compose設定とマウントされているファイルの差異をリストアップしたものです。

---

## 1. Docker Compose設定の差異

### 1.1 コンテナ名とポート
- **5000（本番）**: `attendance-server`, ポート `5000:5000`
- **5001（開発）**: `attendance-server-dev`, ポート `5001:5000`

### 1.2 ネットワーク
- **5000（本番）**: `attendance-network`
- **5001（開発）**: `attendance-network-dev`

### 1.3 環境変数の差異

| 環境変数 | 5000（本番） | 5001（開発） |
|---------|------------|------------|
| `FLASK_DEBUG` | `False` | `True` |
| `FLASK_ENV` | `docker` | `development` |
| `API_VERSION` | `1.0.0` | `1.0.0-dev` |
| `SECRET_KEY` | `change-me-in-production-please-set-secure-key` | `dev-key-change-me` |

その他の環境変数は同一です。

---

## 2. マウントされているファイル/ディレクトリの差異

### 2.1 テンプレートディレクトリ
- **5000（本番）**: `./templates` → `/app/templates`
- **5001（開発）**: `./templates_dev` → `/app/templates`

**差異**: 同じコンテナ内パス（`/app/templates`）にマウントされているが、ホスト側のソースディレクトリが異なる。

### 2.2 静的ファイルディレクトリ
- **5000（本番）**: `./static` → `/app/static`
- **5001（開発）**: `./static_dev` → `/app/static`

**差異**: 同じコンテナ内パス（`/app/static`）にマウントされているが、ホスト側のソースディレクトリが異なる。

### 2.3 開発環境専用ディレクトリ（5001のみ）
- **5001（開発）**: `../../dev_logs` → `/app/logs`
- **5000（本番）**: マウントなし

---

## 3. マウントされているPythonファイルの差異

### 3.1 5000のみにマウントされているファイル
- `./auth.py` → `/app/auth.py`
  - **5001**: マウントされていない

### 3.2 5001のみにマウントされているファイル
- `./overtime.py` → `/app/overtime.py`
  - **5000**: マウントされていない
- `../notification_system.py` → `/app/notification_system.py`
  - **5000**: マウントされていない
- `../notification_scheduler.py` → `/app/notification_scheduler.py`
  - **5000**: マウントされていない

### 3.3 両方にマウントされているが順序が異なるファイル
- `pdf_utils.py`
  - **5000**: 77-78行目でマウント
  - **5001**: 33-34行目でマウント（より早い位置）

### 3.4 両方にマウントされている共通ファイル
以下のファイルは両方の環境でマウントされています：

- `server.py`
- `pdf_generator.py`
- `database.py`
- `api_attendance.py`
- `api_overtime.py`
- `api_leave.py`
- `api_monthly_report.py`
- `monthly_report.py`
- `utils.py`
- `work_type_constants.py`
- `attendance_check_service.py`
- `constants.py`
- `api_check_status.py`
- `api_notifications.py`
- `config.py`
- `logger_config.py`
- `auto_save.py`
- `pdf_utils.py`

---

## 4. マウントされているJSONファイル

以下のJSONファイルは両方の環境でマウントされています：

- `../notification_data.json` → `/app/notification_data.json`
- `../acknowledged_notifications.json` → `/app/acknowledged_notifications.json`
- `../notification_exclusions.json` → `/app/notification_exclusions.json`

---

## 5. マウントされているディレクトリ

### 5.1 データベースディレクトリ（共有）
- **両方**: `../../data` → `/app/data`
  - 本番と開発で同じデータベースを共有

### 5.2 バックアップディレクトリ（共有）
- **両方**: `../../backup` → `/backup`
  - 本番と開発で同じバックアップディレクトリを共有

### 5.3 Dドライブバックアップ（両方ともコメントアウト）
- **両方**: コメントアウトされている
  - `D:/AttendanceBackup_Mirror` → `/app/D_drive_backup`

---

## 6. テンプレートファイルの内容差異

### 6.1 search.html
- **ファイルハッシュ（MD5）**:
  - `templates/search.html`: `E395DDA64C52B9C2523E121E962072D2`
  - `templates_dev/search.html`: `F5D960B38F6AF2F5985906CFF793B492`
- **差異**: ハッシュ値が異なるため、内容に差異があります。
- **確認済み機能**: 両方のファイルに以下の関数が存在します：
  - `formatAlertsWithOvertimeCheck()`
  - `handleNoOvertimeChange()`
  - `refreshTimeDiffAlerts()`
- **行番号の差異**: 関数の定義位置が異なります（5001の方が行数が多い可能性）。

### 6.2 その他のテンプレートファイル
- ファイル名は同一ですが、内容の差異は未確認です。
- 以下のファイルが存在します：
  - `admin.html`
  - `attendance_check.html`
  - `check.html`
  - `check.html.backup`
  - `index.html`
  - `leave_check.html`
  - `leave_list.html`
  - `leave.html`
  - `login.html`
  - `monthly_report.html`
  - `overtime_check.html`
  - `overtime_list.html`
  - `overtime.html`
  - `search.html`

---

## 7. 静的ファイル（CSS/JS）の差異

### 7.1 ディレクトリ構造
両方の環境で同じ構造を持っています：
- `css/` (minimal-ui.css, modern-ui.css, style.css)
- `js/` (api-service.js, attendance-check-page.js, attendance-check.js, attendance-common.js, employee-list.js, html2pdf.bundle.min.js)
- `favicon.ico`

### 7.2 内容の差異
- ファイル名は同一ですが、内容の差異は未確認です。

---

## 8. 重要な差異のまとめ

### 8.1 本番環境（5000）のみ
1. **認証ファイル**: `auth.py`がマウントされている
2. **本番用テンプレート**: `templates/`ディレクトリを使用
3. **本番用静的ファイル**: `static/`ディレクトリを使用

### 8.2 開発環境（5001）のみ
1. **開発用ログ**: `dev_logs/`ディレクトリがマウントされている
2. **開発用テンプレート**: `templates_dev/`ディレクトリを使用
3. **開発用静的ファイル**: `static_dev/`ディレクトリを使用
4. **追加モジュール**: `overtime.py`, `notification_system.py`, `notification_scheduler.py`がマウントされている

### 8.3 共有リソース
1. **データベース**: 両方の環境で同じデータベース（`../../data/attendance.db`）を使用
2. **バックアップ**: 両方の環境で同じバックアップディレクトリを使用
3. **JSON設定ファイル**: 通知関連のJSONファイルを共有

---

## 9. 推奨事項

### 9.1 本番環境への反映
開発環境（5001）でテストした機能を本番環境（5000）に反映する際は、以下を確認してください：

1. **テンプレートファイル**: `templates_dev/`の変更を`templates/`にコピー
2. **静的ファイル**: `static_dev/`の変更を`static/`にコピー
3. **Pythonファイル**: 共通ファイルの変更は自動的に反映されますが、`overtime.py`など開発環境専用ファイルの追加が必要な場合は検討が必要です

### 9.2 認証の扱い
- 本番環境（5000）では`auth.py`がマウントされていますが、開発環境（5001）ではマウントされていません。
- 認証機能が必要な場合は、開発環境にも`auth.py`をマウントするか、認証を外す（既に実施済み）かの判断が必要です。

### 9.3 通知システム
- `notification_system.py`と`notification_scheduler.py`は開発環境（5001）のみにマウントされています。
- 本番環境でも通知機能が必要な場合は、これらのファイルをマウントする必要があります。

---

## 10. 確認が必要な項目

1. **テンプレートファイルの内容差異**: `search.html`以外のテンプレートファイルの内容比較
2. **静的ファイルの内容差異**: CSS/JSファイルの内容比較
3. **認証の必要性**: 本番環境で`auth.py`が必要かどうかの確認
4. **通知システムの本番展開**: `notification_system.py`と`notification_scheduler.py`の本番環境への追加の必要性

---

作成日: 2026-01-27
更新日: 2026-01-27
