# 📋 作業日報

## 2026年1月30日

### 作業内容

#### 1. スレッドセーフティ問題の修正（CODE_AUDIT_REPORT.md対応）

**目的**: `database.py`のスレッドセーフティ問題を修正

**問題点**:
- `_database_initialized`グローバル変数によるレースコンディション
- マルチスレッド環境（Flask `THREADED = True`）での初期化競合の可能性

**実装内容**:
- `DatabaseInitializer`クラスを追加（スレッドセーフな初期化管理）
- Double-Checked Lockingパターンの実装
- `threading.Lock()`による同期制御
- 後方互換性のため`init_database()`関数をラッパー関数として維持

**変更ファイル**:
- `database.py`: 
  - `threading`モジュールのインポート追加
  - `DatabaseInitializer`クラスの追加
  - `init_database()`関数をラッパー関数に変更

**実装日時**: 2026-01-30

---

#### 2. monthly_report.pyのリファクタリング（CODE_AUDIT_REPORT.md対応）

**目的**: `monthly_report.py`の巨大化問題を解決し、モジュール性を向上

**問題点**:
- `monthly_report.py`が1411行と巨大
- Excel生成ロジックとデータ取得ロジックが混在
- 保守性と可読性の低下

**実装内容**:
- `excel_generator.py`モジュールを新規作成
- Excel生成関数（`generate_monthly_report_excel`, `generate_all_employees_report_excel`）を`excel_generator.py`に移動
- `monthly_report.py`からExcel生成関連のインポートを削除
- `api_monthly_report.py`のインポートを更新

**変更ファイル**:

1. **`excel_generator.py`（新規作成）**:
   - Excel生成専用モジュール
   - `generate_monthly_report_excel`関数: 個人別月間レポート生成
   - `generate_all_employees_report_excel`関数: 全従業員一括レポート生成
   - 必要なインポート: `openpyxl`, `datetime`, `os`, `time`, `Config`, `utils`, `constants`, `alert_utils`, `work_type_constants`, `logger_config`, `monthly_report`

2. **`monthly_report.py`**:
   - Excel生成関数を削除（約1000行削減）
   - ファイルサイズ: 1411行 → 380行
   - Excel生成関連のインポートを削除（`openpyxl`, `Workbook`, `Font`, `Alignment`, `Border`, `Side`, `os`, `time`）
   - `excel_generator`からExcel生成関数をインポート

3. **`api_monthly_report.py`**:
   - インポートを更新:
     - `from monthly_report import get_monthly_attendance_data`
     - `from excel_generator import generate_monthly_report_excel, generate_all_employees_report_excel`

**効果**:
- モジュールの責務が明確化（データ取得 vs Excel生成）
- 保守性の向上（Excel生成ロジックの変更が他のコードに影響しない）
- 可読性の向上（ファイルサイズが約73%削減）
- テスト容易性の向上（各モジュールを独立してテスト可能）

**実装日時**: 2026-01-30

---

# 📋 作業日報（過去分）

## 2026年1月29日

### 作業内容

#### 1. search画面の5000と5001の差異調査

**調査目的**: search画面で5000と5001の動作が異なる原因を特定

**調査結果**:

##### ファイルサイズの差異
- `attendance-check.js`:
  - 5000（static）: 22,768バイト（531行）
  - 5001（static_dev）: 29,222バイト（677行）
  - **差異**: 約6,454バイト（146行多い）

- `attendance-common.js`:
  - 5000（static）: 365行
  - 5001（static_dev）: 376行
  - **差異**: 11行多い

##### 主な機能の差異

**1. `updateCheckStatus`関数の実装が異なる**

**5000（static）の実装**:
- チェック時の表示: 時間外申告の有無で「打刻もれチェック済み時間外有り」「打刻もれチェック済　時間外無」など
- チェック解除時: 単純に「未確認」に戻す
- アラート表示の更新なし

**5001（static_dev）の実装**:
- チェック時の表示: 「打刻なし確認済」「打刻漏れ確認済」「確認済み」など
- チェックボックスとラベルの非表示処理あり
- チェック解除時: チェックボックスとラベルを再表示
- アラート表示の更新あり（`updateAlertsDisplay`呼び出し）
- アラート削除処理あり（`removePunchLeakAlerts`, `removeMissingPunchAlerts`呼び出し）

**2. `loadCheckStatuses`関数の実装が異なる**

**5000（static）の実装**:
- 簡易版（293-368行目）
- チェック済みの場合、時間外申告の有無で表示を変更
- アラート表示の更新なし

**5001（static_dev）の実装**:
- 詳細版（411-517行目）
- エラーハンドリングが強化
- チェック済みの場合、チェックボックスとラベルを非表示
- エラー・警告列のチェックボックスもチェック
- アラート表示の更新あり（`updateAlertsDisplay`呼び出し）

**3. 追加関数（5001のみ）**

- `updateAlertsDisplay`関数（333-389行目）: エラー・警告列のアラート表示を更新
- `removePunchLeakAlerts`関数（394-396行目）: 打刻漏れアラートを削除
- `removeMissingPunchAlerts`関数（401-403行目）: 打刻なしアラートを削除

**4. `performSearch`関数の差異**

- 5000（static）: 114行目で即座に`loading`を非表示
- 5001（static_dev）: 114-115行目で`loading`の非表示をコメントアウト、124行目で非表示（検索中表示を維持）

**5. `displayResults`関数の差異**

- 5000（static）: 144行目で`no-results`を表示後、即座にreturn
- 5001（static_dev）: 149行目で`loading`を非表示してから`no-results`を表示、217行目でも`loading`を非表示（結果表示完了後）

##### マウント設定の差異

- 5000: `./templates` → `/app/templates`, `./static` → `/app/static`
- 5001: `./templates_dev` → `/app/templates`, `./static_dev` → `/app/static`

##### 環境変数の差異

- `FLASK_DEBUG`: 5000は`False`、5001は`True`
- `FLASK_ENV`: 5000は`docker`、5001は`development`

##### 影響

1. **UIの動作が異なる**:
   - 5001はアラート表示の更新機能がある
   - 5001はチェックボックスの表示/非表示制御がある

2. **ユーザー体験の差異**:
   - 5001は確認済みの視覚的フィードバックが強化されている
   - 5001は検索中の表示が維持される

3. **機能の有無**:
   - 5000には`updateAlertsDisplay`などの関数がない
   - 5001には時間外申告の有無による表示変更がない

**結論**: 5001の方が機能が充実しており、UIの動作も改善されている。5001の仕様に統一することを推奨。

---

## 今後の作業計画

### 統一作業（✅ 実施済み）

**目標**: 5001の仕様に統一

**作業内容**:
1. ✅ `static/js/attendance-check.js`を`static_dev/js/attendance-check.js`の内容に統一
2. ✅ `static/js/attendance-common.js`を`static_dev/js/attendance-common.js`の内容に統一
3. ⏳ 動作確認（5000環境で） - 未実施

**注意事項**:
- 変更前にバックアップを取得
- 変更後は5000環境で動作確認を実施
- 問題が発生した場合は即座にロールバック

---

## 変更履歴

### 2026年1月29日

#### 午前
- search画面の5000と5001の差異調査を実施
- 作業日報を作成

#### 午後
- **5001の仕様に統一作業を実施**

**変更内容**:

1. **`static/js/attendance-check.js`を5001の仕様に統一**
   - ファイルサイズ: 22,768バイト（531行）→ 29,222バイト（677行）
   - 追加された機能:
     - `updateAlertsDisplay`関数: エラー・警告列のアラート表示を更新
     - `removePunchLeakAlerts`関数: 打刻漏れアラートを削除
     - `removeMissingPunchAlerts`関数: 打刻なしアラートを削除
   - 改善された機能:
     - `updateCheckStatus`関数: チェックボックスとラベルの表示/非表示制御を追加、アラート表示の更新機能を追加
     - `loadCheckStatuses`関数: エラーハンドリングを強化、チェック済み時のUI更新を改善
     - `performSearch`関数: 検索中表示を維持するように改善
     - `displayResults`関数: 結果表示完了後に検索中表示を非表示にする処理を追加

2. **`static/js/attendance-common.js`を5001の仕様に統一**
   - ファイルサイズ: 365行 → 376行
   - 変更内容: `processNightShiftEndTimes`関数の実装を5001の仕様に統一

**変更後の状態**:
- 5000と5001のJavaScriptファイルが統一され、同じ機能を持つようになった
- 5001の改善されたUI機能（アラート表示更新、チェックボックス制御など）が5000にも反映された

**次のステップ**:
- 5000環境で動作確認を実施
- 問題が発生した場合はロールバックを検討

#### 文字化け問題の発生と修正

**問題**: 統一作業後、`static/js/attendance-check.js`で日本語が「????」と表示される文字化けが発生

**原因**: `write`ツールでファイルを書き込む際に、UTF-8エンコーディングが正しく設定されなかった

**修正方法**: PowerShellの`[System.IO.File]::WriteAllText`を使用して、UTF-8エンコーディングを明示的に指定してファイルをコピー

**修正内容**:
- `static_dev/js/attendance-check.js`をUTF-8で読み込み、`static/js/attendance-check.js`にUTF-8で書き込み
- `static_dev/js/attendance-common.js`をUTF-8で読み込み、`static/js/attendance-common.js`にUTF-8で書き込み

**教訓**: 
- 日本語を含むファイルを書き込む際は、必ずUTF-8エンコーディングを明示的に指定する
- `write`ツールの代わりに、PowerShellの`[System.IO.File]::WriteAllText`を使用するか、ファイルコピーを使用する

#### 時間外申告によるエラー・警告回避機能の確認

**確認目的**: 打刻時刻に差異があるとき、時間外申告の開始時間あるいは終了時間を参照してエラー・警告を回避するコードが実装されているか確認

**確認結果**: ✅ **実装済み**

**実装されている機能**:

1. **`_check_overtime_time_within_tolerance`関数**（`attendance_check_service.py` 748-788行目）:
   - 時間外申告の開始時間または終了時間と打刻時間が±15分以内かチェック
   - 開始時間と打刻時間の差異が15分以内なら`True`を返す
   - 終了時間と打刻時間の差異が15分以内なら`True`を返す
   - 許容範囲: `AttendanceConstants.TOLERANCE_MINUTES = 15分`

2. **出勤時刻差異チェック**（`_check_clock_in_time_diff`関数 653-656行目）:
   - 時間外申告の開始時間と出勤打刻時間が±15分以内かチェック
   - `_check_overtime_time_within_tolerance(actual_start, overtime_apps)`を呼び出し
   - `True`の場合、エラーをスキップ（`return`で処理を終了）

3. **退勤時刻差異チェック**（`_check_clock_out_time_diff`関数 715-718行目）:
   - 時間外申告の開始時間または終了時間と退勤打刻時間が±15分以内かチェック
   - `_check_overtime_time_within_tolerance(actual_end, overtime_apps)`を呼び出し
   - `True`の場合、エラーをスキップ（`return`で処理を終了）

4. **退勤時刻が遅い場合の追加チェック**（`_check_clock_out_time_diff`関数 720-734行目）:
   - 退勤時刻が遅い場合（`diff_end > 0`）、時間外申告が実際の残業時間をカバーしているかチェック
   - `_check_overtime_coverage(schedule_end, actual_end, overtime_apps)`を呼び出し
   - 時間外申告がない場合のみエラーを出す

5. **`_check_overtime_coverage`関数**（790-798行目）:
   - 時間外申告が実際の残業時間をカバーしているかチェック
   - `_check_overtime_overlap`を呼び出し

6. **`_check_overtime_overlap`関数**（502-530行目）:
   - 時間外申告と実際の退勤時間の重複チェック
   - 許容範囲（±15分）も考慮

**処理フロー**:

1. `check_time_difference_errors`関数（532行目）で出退勤時刻差異チェックを開始
2. 時間外申告を取得（560行目: `_get_overtime_applications_safe`）
3. 出勤時刻差異チェック（604行目: `_check_clock_in_time_diff`）
   - 653-656行目: 時間外申告の開始時間と出勤打刻時間が±15分以内ならエラーをスキップ
4. 退勤時刻差異チェック（607行目: `_check_clock_out_time_diff`）
   - 715-718行目: 時間外申告の開始時間または終了時間と退勤打刻時間が±15分以内ならエラーをスキップ
   - 720-734行目: 退勤時刻が遅い場合、時間外申告が実際の残業時間をカバーしているかチェック

**結論**: 
- ✅ 打刻時刻に差異があるとき、時間外申告の開始時間あるいは終了時間を参照してエラー・警告を回避するコードは実装されている
- ✅ 出勤時刻差異: 時間外申告の開始時間と±15分以内ならエラーをスキップ
- ✅ 退勤時刻差異: 時間外申告の開始時間または終了時間と±15分以内ならエラーをスキップ
- ✅ 退勤時刻が遅い場合: 時間外申告が実際の残業時間をカバーしているかチェック

#### 許容範囲の変更

**変更内容**: 時間外申告と打刻時刻の許容範囲を15分から30分に変更

**変更ファイル**: `constants.py`

**変更箇所**:
- `AttendanceConstants.TOLERANCE_MINUTES`: 15 → 30

**影響範囲**:
- `_check_overtime_time_within_tolerance`関数: 時間外申告の開始時間または終了時間と打刻時間が±30分以内かチェック
- `_check_clock_in_time_diff`関数: 出勤時刻差異チェック時の許容範囲が±30分に拡大
- `_check_clock_out_time_diff`関数: 退勤時刻差異チェック時の許容範囲が±30分に拡大
- `_check_overtime_overlap`関数: 時間外申告と実際の退勤時間の重複チェック時の許容範囲が±30分に拡大

**変更理由**: ユーザー要求により、時間外申告と打刻時刻の許容範囲を拡大

---

#### 5000と5001での除外リスト動作差異の調査

**調査目的**: 5000コンテナでは除外リストがクライアントで有効となっているが、5001ではそうなっていない理由を調査

**調査結果**:

##### 1. Docker Compose設定の比較

**5000（docker-compose.yml）**:
- `../notification_exclusions.json` → `/app/notification_exclusions.json` にマウント（87-90行目）

**5001（docker-compose.dev.yml）**:
- `../notification_exclusions.json` → `/app/notification_exclusions.json` にマウント（111-114行目）

**結論**: 両方とも同じファイルを同じパスにマウントしているため、設定の違いはない

##### 2. API実装の確認

**`api_notifications.py`の`load_notification_exclusions()`関数**:
- `EXCLUSIONS_FILE_CONTAINER` (`/app/notification_exclusions.json`) を優先して読み込む（86行目）
- `EXCLUSIONS_FILE` (`../notification_exclusions.json`) をフォールバックとして使用
- 両方の環境で同じロジックを使用している

##### 3. クライアント設定の確認

**`client_config.json`**:
- `server_url`: `http://192.168.1.217:5000` （5000環境に接続）
- `employee_filter`: `null` （全従業員対象）

**`notification_client.py`**:
- `fetch_notifications_from_server()`関数で`/api/notifications`を呼び出し
- サーバー側で除外リストによるフィルタリングが実行される（クライアント側では追加のフィルタリングなし）

##### 4. 考えられる原因

**原因1: クライアントが5001に接続していない**
- クライアント設定が5000を指しているため、5001の除外リストは関係ない
- 5001に接続するクライアントが存在しない、または別の設定ファイルを使用している可能性

**原因2: 5001コンテナ内でファイルが存在しない**
- マウントが失敗している可能性
- コンテナ起動時にエラーが発生している可能性

**原因3: 5001のAPIが除外リストを正しく読み込んでいない**
- ログを確認する必要がある
- ファイルパスの問題で読み込みに失敗している可能性

##### 5. 確認が必要な項目

1. **5001コンテナ内でのファイル存在確認**:
   ```powershell
   docker exec attendance-server-dev ls -la /app/notification_exclusions.json
   docker exec attendance-server-dev cat /app/notification_exclusions.json
   ```

2. **5001のAPIログ確認**:
   ```powershell
   docker logs attendance-server-dev --tail=200 | Select-String "除外リスト|exclusions"
   ```

3. **5001のAPIデバッグエンドポイント確認**:
   ```powershell
   curl http://localhost:5001/api/notifications/debug
   ```

4. **クライアントが5001に接続しているか確認**:
   - 別の`client_config.json`が存在するか
   - 5001に接続するクライアントが存在するか

##### 6. 推奨される調査手順

1. **5001コンテナ内でのファイル存在確認**
2. **5001のAPIログで除外リスト読み込みログを確認**
3. **5001のAPIデバッグエンドポイントで除外リストの状態を確認**
4. **クライアントが5001に接続しているか確認**（別の設定ファイルや環境変数の可能性）

**結論**: 
- Docker Compose設定とAPI実装は両方の環境で同じ
- クライアント設定が5000を指しているため、5001の除外リストが有効かどうかは5001に接続するクライアントが存在するかどうかに依存する
- 5001コンテナ内でのファイル存在とAPIログを確認する必要がある

##### 7. 実際の確認結果（ターミナル実行）

**5001のAPIデバッグエンドポイント結果**:
```json
{
  "excluded_count": 0,
  "excluded_employee_ids": [],
  "excluded_notifications": [],
  "excluded_notifications_count": 0,
  "file_paths": {
    "container": "/app/notification_exclusions.json",
    "container_exists": false,  // ← コンテナ内にファイルが存在しない
    "host": "/app/../notification_exclusions.json",
    "host_exists": true  // ← ホスト側パスからは読み込める可能性
  },
  "status": "success",
  "total_notifications": 28
}
```

**5000のAPIデバッグエンドポイント結果**:
```json
{
  "excluded_count": 2,
  "excluded_employee_ids": ["3952012", "2952089"],
  "excluded_notifications": [...11件の通知...],
  "excluded_notifications_count": 11,
  "file_paths": {
    "container": "/app/notification_exclusions.json",
    "container_exists": false,  // ← 5000でもfalseだが、除外リストは読み込めている
    "host": "/app/../notification_exclusions.json",
    "host_exists": true
  },
  "status": "success",
  "total_notifications": 28
}
```

**ホスト側ファイル** (`notification_exclusions.json`):
```json
{
    "excluded_employee_ids": [],
    "last_updated": "2026-01-29T17:27:05"
}
```

##### 8. 原因の特定

**問題点**:
1. **5001では除外リストが空**: `excluded_employee_ids`が空の配列
2. **5000では除外リストが有効**: `excluded_employee_ids`に`["3952012", "2952089"]`が含まれている
3. **ホスト側ファイルは空**: `notification_exclusions.json`の`excluded_employee_ids`が空の配列

**原因**:
- ホスト側の`notification_exclusions.json`ファイルが空の状態になっている
- 5000では以前に設定された除外リストがキャッシュされているか、別の場所から読み込まれている可能性
- 5001では空のファイルが読み込まれているため、除外リストが機能していない

**解決策**:
1. 管理者ページ（`/admin?hidden=true`）で除外リストを再設定する
2. 5001コンテナを再起動して、最新の除外リストを読み込む
3. 5000と5001で同じ除外リストファイルを共有しているため、一度設定すれば両方に反映される

---

#### CSVインポート機能の改善（シートカラム対応・BOM処理追加）

**実施日**: 2026年1月29日

**変更内容**: CSVインポート機能にシートカラムの読み込みとBOM処理を追加

**変更ファイル**: `admin.py`

**変更箇所**:

1. **BOM処理の追加**（51行目）:
   - `encoding='utf-8'` → `encoding='utf-8-sig'`
   - UTF-8 BOMを自動除去してカラム名を正しく取得

2. **シートカラムの読み込み**（63行目）:
   - `sheet_str = row.get('シート', '').strip()` を追加
   - CSVファイルの「シート」カラムから値を取得

3. **シート番号の処理**（89-97行目）:
   - CSVの「シート」カラムの値を使用
   - 空の場合は`Config.DEFAULT_SHEET_NUMBER`を使用
   - 文字列として保存（`str(sheet_str)`）

4. **UPDATE文の修正**（107-112行目）:
   - 既存データ更新時に`sheet_number`も更新するように変更

**テスト結果**:
- 総行数: 372行
- 成功: 372行
- エラー: 0行
- シート番号の種類: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12（各31件）
- BOM処理: 正常動作（カラム名が正しく取得される）

**反映方法**:
- `admin.py`は5000と5001の両方のコンテナで共有されているため、修正すれば両方に反映される
- コンテナ再起動は不要（バインドマウントされているため、ファイル変更が即座に反映される）

**次のステップ**:
- 5001環境で実際のCSVインポートを実行して動作確認
- 5000環境でも動作確認

---

#### お知らせAPIとsearch画面チェック機能の連携実装

**実施日**: 2026年1月29日

**問題**: search画面でチェックを入れても、お知らせ画面にお知らせが出続ける

**原因**: お知らせAPI（`api_notifications.py`）が`attendance_check_status`テーブルを参照していなかった

**実装内容**: お知らせAPIが`attendance_check_status`テーブルを参照して、search画面でチェック済みの通知を除外する機能を追加

**変更ファイル**: `api_notifications.py`

**追加した関数**:

1. **`get_check_type_from_message`関数**（200-221行目）:
   - 通知メッセージからチェックタイプを判定
   - `打刻なし` → `missing_punch`
   - `打刻漏れ` / `出勤打刻漏れ` / `退勤打刻漏れ` → `punch_leak`
   - `出退勤時刻に差異あり` / `出勤時刻に差異あり` / `退勤時刻に差異あり` → `time_difference`

2. **`is_notification_checked`関数**（223-255行目）:
   - 通知がsearch画面でチェック済みかどうかを確認
   - `attendance_check_status`テーブルを参照してチェック状態を取得

**修正した関数**:

3. **`get_notifications`関数**（257-325行目）:
   - フィルタリング処理にチェック済み通知の除外を追加
   - `is_notification_checked`関数を呼び出してチェック済みの通知を除外
   - レスポンスに`checked_count`を追加

**処理フロー**:

1. 通知データを読み込み
2. 各通知に対して以下をチェック:
   - 確認済みフィルター（`acknowledged_notifications.json`）
   - 従業員IDフィルター
   - 除外リストフィルター
   - **チェック済みフィルター（`attendance_check_status`テーブル）** ← 新規追加
3. フィルタリング結果を返す

**テスト結果**:
- チェックタイプ判定: すべてのテストケースで成功
- データベース連携: 正常動作

**反映方法**:
- `api_notifications.py`は5000と5001の両方のコンテナでバインドマウントされているため、修正すれば両方に反映される
- コンテナ再起動は不要（バインドマウントされているため、ファイル変更が即座に反映される）

**次のステップ**:
- 5001環境で実際の動作確認
  - search画面でチェックを入れる
  - お知らせ画面でお知らせが消えることを確認

---

---

#### 3. attendance_check_service.pyのリファクタリング（CODE_AUDIT_REPORT.md対応）

**目的**: `attendance_check_service.py`の巨大化問題を解決し、モジュール性を向上

**問題点**:
- `attendance_check_service.py`が1,026行と巨大
- データ取得、バリデーション、時刻差異チェックが混在
- 保守性と可読性の低下

**実装内容**:
- `attendance_check/`ディレクトリを作成し、機能別にモジュールを分割
- データ取得関数を`data_access.py`に移動
- バリデーション関数を`validators.py`に移動
- 時刻差異チェック関数を`time_validators.py`に移動
- 特殊勤務チェック関数を`special_shift_validators.py`に移動
- `attendance_check_service.py`をオーケストレーションモジュールに変更
- 後方互換性のため、元の`attendance_check_service.py`をラッパーとして維持

**変更ファイル**:

1. **`attendance_check/__init__.py`（新規作成）**:
   - 後方互換性のための再エクスポート
   - 既存のインポートパスを維持

2. **`attendance_check/data_access.py`（新規作成）**:
   - データ取得専用モジュール
   - `get_employee_info`: 従業員情報取得
   - `get_schedule_info`: スケジュール情報取得
   - `get_attendance_records`: 打刻記録取得
   - `get_prev_day_night_shift`: 前日の24勤・夜勤スケジュール取得

3. **`attendance_check/validators.py`（新規作成）**:
   - バリデーション専用モジュール
   - `check_holiday_punch_errors`: 休日打刻エラーチェック
   - `check_missing_punch_errors`: 打刻なし・打刻漏れエラーチェック
   - `check_holiday_work_errors`: 休日出勤エラーチェック
   - `check_leave_request_conflicts`: 休暇申請競合チェック

4. **`attendance_check/time_validators.py`（新規作成）**:
   - 時刻差異チェック専用モジュール
   - `check_time_difference_errors`: 出退勤時刻差異チェック
   - `get_late_early_adjustments`: 遅刻・早退調整取得
   - `_get_overtime_applications_safe`: 時間外申告取得（安全版）
   - `_check_overtime_time_within_tolerance`: 時間外申告許容範囲チェック
   - `_check_clock_in_time_diff`: 出勤時刻差異チェック
   - `_check_clock_out_time_diff`: 退勤時刻差異チェック

5. **`attendance_check/special_shift_validators.py`（新規作成）**:
   - 特殊勤務チェック専用モジュール
   - `check_off_day_shift_attendance`: 「明」勤務の前日24勤・夜勤チェック
   - `_check_prev_day_24hour_punch_leak`: 前日の24勤打刻漏れチェック

6. **`attendance_check/attendance_check_service.py`（新規作成）**:
   - オーケストレーションモジュール
   - `AttendanceCheckResult`: 勤怠チェック結果データクラス
   - `calculate_actual_clock_times`: 実際の打刻時刻計算
   - `check_attendance_vs_schedule`: メインの勤怠チェック関数
   - `get_night_shift_end_time_from_next_day`: 24勤・夜勤の終了時間取得

7. **`attendance_check_service.py`（変更）**:
   - 後方互換性のためのラッパーに変更
   - 新しい`attendance_check`モジュールから再エクスポート

8. **`docker-compose.dev.yml`（変更）**:
   - `attendance_check/`ディレクトリのマウント設定を追加

9. **`Dockerfile`（変更）**:
   - `attendance_check/`ディレクトリのCOPY設定を追加

**効果**:
- モジュール性の向上: 各モジュールが単一責任を持つ
- 保守性の向上: 機能別にファイルが分割され、変更箇所が明確
- 可読性の向上: 各モジュールが小さく、理解しやすい
- テスト容易性の向上: 各モジュールを独立してテスト可能
- 後方互換性の維持: 既存のインポートパスがそのまま動作

**実装日時**: 2026-01-30

---

#### 4. database.pyのリファクタリング（CODE_AUDIT_REPORT.md対応）

**目的**: `database.py`の巨大化問題を解決し、DAOパターンを導入してスキーマ管理を分離

**問題点**:
- `database.py`が1,040行と巨大
- CRUD操作、スキーマ管理、ビジネスロジックが混在
- 保守性と可読性の低下

**実装内容**:
- `database/`ディレクトリを作成し、機能別にモジュールを分割
- スキーマ管理を`schema.py`に移動
- DAOパターンを導入し、各テーブルのCRUD操作を分離
  - `dao/attendance_dao.py`: 打刻データCRUD
  - `dao/schedule_dao.py`: スケジュールCRUD
  - `dao/employee_dao.py`: 従業員マスタCRUD
  - `dao/request_dao.py`: 遅刻・早退申告CRUD
  - `dao/check_status_dao.py`: チェック状態CRUD
- ビジネスロジックを`business_logic.py`に移動
- `database.py`を後方互換性のためのラッパーに変更

**変更ファイル**:

1. **`database/__init__.py`（新規作成）**:
   - 後方互換性のための再エクスポート
   - 既存のインポートパスを維持

2. **`database/schema.py`（新規作成）**:
   - スキーマ管理専用モジュール
   - `DatabaseInitializer`: スレッドセーフなデータベース初期化クラス
   - `init_database()`: データベース初期化ラッパー関数
   - `migrate_employee_master_table()`: employee_masterテーブルのマイグレーション
   - `init_late_early_requests_tables()`: 遅刻早退申告テーブル初期化
   - `init_leave_request_table_internal()`: 休暇願テーブル初期化
   - `init_overtime_table_internal()`: 時間外申告テーブル初期化
   - `migrate_overtime_table()`: overtime_applicationsテーブルのマイグレーション
   - `init_attendance_check_status_table()`: 打刻チェック状況テーブル初期化

3. **`database/dao/attendance_dao.py`（新規作成）**:
   - 打刻データCRUD専用モジュール
   - `insert_attendance()`: 打刻データ挿入
   - `get_attendance_for_schedule()`: スケジュールに対応する打刻データ取得
   - `cleanup_duplicates()`: 重複データのクリーンアップ

4. **`database/dao/schedule_dao.py`（新規作成）**:
   - スケジュールCRUD専用モジュール
   - `search_schedule()`: 勤怠スケジュール検索（打刻データ付き）

5. **`database/dao/employee_dao.py`（新規作成）**:
   - 従業員マスタCRUD専用モジュール
   - `get_employees()`: 従業員情報取得
   - `get_stats()`: 統計情報取得

6. **`database/dao/request_dao.py`（新規作成）**:
   - リクエスト管理CRUD専用モジュール
   - `insert_late_arrival_request()`: 遅刻申告登録
   - `insert_early_leave_request()`: 早退申告登録
   - `get_late_arrival_requests()`: 遅刻申告取得
   - `get_early_leave_requests()`: 早退申告取得

7. **`database/dao/check_status_dao.py`（新規作成）**:
   - チェック状態CRUD専用モジュール
   - `get_attendance_check_status()`: 打刻チェック状況取得
   - `update_attendance_check_status()`: 打刻チェック状況更新

8. **`database/business_logic.py`（新規作成）**:
   - ビジネスロジック専用モジュール
   - `check_off_day_shift_attendance()`: 「明」勤務の退勤時刻チェック処理
   - `get_night_shift_end_time_from_next_day()`: 24勤・夜勤の終了時間取得（ラッパー）
   - `check_attendance_vs_schedule()`: 勤怠スケジュールと打刻実績の差異チェック（ラッパー）

9. **`database.py`（変更）**:
   - 後方互換性のためのラッパーに変更
   - 新しい`database`モジュールから再エクスポート

10. **`docker-compose.dev.yml`（変更）**:
    - `database/`ディレクトリのマウント設定を追加

11. **`Dockerfile`（変更）**:
    - `database/`ディレクトリのCOPY設定を追加

**効果**:
- モジュール性の向上: 各モジュールが単一責任を持つ
- DAOパターンの導入: データアクセス層の明確な分離
- スキーマ管理の分離: テーブル定義とマイグレーションが独立
- 保守性の向上: 機能別にファイルが分割され、変更箇所が明確
- 可読性の向上: 各モジュールが小さく、理解しやすい
- テスト容易性の向上: 各モジュールを独立してテスト可能
- 後方互換性の維持: 既存のインポートパスがそのまま動作

**実装日時**: 2026-01-30

---

#### 4. api_notifications.pyのリファクタリング（CODE_AUDIT_REPORT.md対応）

**目的**: `api_notifications.py`の巨大化問題を解決し、責務を明確に分離

**問題点**:
- `api_notifications.py`が640行と巨大
- 通知生成、フィルタリング、除外リスト管理が混在
- 単一責務原則の違反

**実装内容**:
- `notifications/`パッケージを新規作成
- 除外リスト管理を`exclusion_manager.py`に分離
- 通知データ管理を`notification_data.py`に分離
- フィルタリングロジックを`notification_filter.py`に分離
- `api_notifications.py`をAPIエンドポイントのみに整理

**変更ファイル**:

1. **`notifications/__init__.py`（新規作成）**:
   - パッケージ初期化と再エクスポート

2. **`notifications/exclusion_manager.py`（新規作成）**:
   - 除外リスト管理専用モジュール
   - `load_notification_exclusions()`: 除外リスト読み込み
   - `save_notification_exclusions()`: 除外リスト保存
   - `sync_exclusions_file()`: ファイル同期
   - `init_notification_files()`: ファイル初期化

3. **`notifications/notification_data.py`（新規作成）**:
   - 通知データ管理専用モジュール
   - `load_notification_data()`: 通知データ読み込み
   - `load_acknowledged_notifications()`: 確認済み通知読み込み
   - `save_acknowledged_notifications()`: 確認済み通知保存

4. **`notifications/notification_filter.py`（新規作成）**:
   - フィルタリングロジック専用モジュール
   - `get_check_type_from_message()`: チェックタイプ判定
   - `is_notification_checked()`: チェック済み判定
   - `filter_notifications()`: 通知フィルタリング処理

5. **`api_notifications.py`（変更）**:
   - APIエンドポイントのみに整理
   - 新しい`notifications`パッケージからインポート
   - フィルタリング処理を`filter_notifications()`関数に委譲

6. **`server.py`（変更）**:
   - `init_notification_files()`のインポートパスを更新

7. **`docker-compose.dev.yml`（変更）**:
   - `notifications/`ディレクトリのマウント設定を追加

8. **`Dockerfile`（変更）**:
   - `notifications/`ディレクトリのCOPY設定を追加

**効果**:
- 責務の明確化: 各モジュールが単一責任を持つ
- 保守性の向上: 機能別にファイルが分割され、変更箇所が明確
- 可読性の向上: 各モジュールが小さく、理解しやすい
- テスト容易性の向上: 各モジュールを独立してテスト可能
- 再利用性の向上: フィルタリングロジックを他の場所でも使用可能

**実装日時**: 2026-02-03

---

**作成日**: 2026年1月29日  
**最終更新**: 2026年2月3日（api_notifications.pyのリファクタリング完了後）
