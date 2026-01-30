# 📋 作業日報

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

**作成日**: 2026年1月29日  
**最終更新**: 2026年1月29日（5000/5001除外リスト差異調査・原因特定後）
