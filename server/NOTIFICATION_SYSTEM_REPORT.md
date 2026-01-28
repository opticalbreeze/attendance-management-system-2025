# お知らせ通知システム 詳細レポート

## 📋 概要

このレポートは、クライアントPCへのお知らせ通知機能と、5000（本番）・5001（開発）コンテナでの動作状況について詳細に分析したものです。

**作成日**: 2026-01-27  
**対象**: お知らせ通知システム、通知除外リスト機能

---

## 🎯 システム構成

### 1. コンポーネント一覧

| コンポーネント | ファイル名 | 配置場所 | 役割 |
|--------------|----------|---------|------|
| **サーバー側API** | `api_notifications.py` | `server/` | 通知データの提供、除外リスト管理 |
| **クライアント通知システム** | `notification_system.py` | `work_attend_server/` | Tkinter GUIで通知表示 |
| **通知スケジューラー** | `notification_scheduler.py` | `work_attend_server/` | 毎日深夜2:00に自動チェック |
| **クライアント通知クライアント** | `notification_client.py` | `card-reder-for-win/` | クライアントPC用通知受信 |
| **打刻PC通知** | `punch_pc_notification.py` | `work_attend_server/` | 打刻PC用通知 |

### 2. データファイル

| ファイル名 | 配置場所 | 用途 |
|----------|---------|------|
| `notification_data.json` | `work_attend_server/` | 通知データの保存 |
| `acknowledged_notifications.json` | `work_attend_server/` | 確認済み通知の管理 |
| `notification_exclusions.json` | `work_attend_server/` | **除外リスト（重要）** |

---

## 🔍 5000と5001の差異分析

### 1. Docker Compose設定の差異

#### 5000（本番環境） - `docker-compose.yml`

```yaml
volumes:
  # notification_system.py: マウントなし
  # notification_scheduler.py: マウントなし
  - ../notification_exclusions.json → /app/notification_exclusions.json  # ✅ マウントあり
```

#### 5001（開発環境） - `docker-compose.dev.yml`

```yaml
volumes:
  - ../notification_system.py → /app/notification_system.py  # ✅ マウントあり
  - ../notification_scheduler.py → /app/notification_scheduler.py  # ✅ マウントあり
  - ../notification_exclusions.json → /app/notification_exclusions.json  # ✅ マウントあり
```

**差異の影響**:
- `notification_system.py`と`notification_scheduler.py`は**5001のみ**にマウント
- ただし、これらは**クライアントPCで実行するスクリプト**のため、サーバーコンテナへのマウントは不要
- **除外リストファイル**は両方でマウントされている（共有）

---

## 📡 サーバー側API (`api_notifications.py`) の動作

### 1. 通知取得API (`GET /api/notifications`)

**処理フロー**:
1. `notification_data.json`から通知データを読み込み
2. `acknowledged_notifications.json`から確認済み通知を読み込み
3. **`notification_exclusions.json`から除外リストを読み込み**
4. フィルタリング:
   - 確認済み通知を除外（デフォルト）
   - 除外リストに含まれる従業員IDの通知を除外
   - 従業員IDでフィルタリング（指定時）

**重要なコード** (行244-250):
```python
# 除外リストフィルター（除外リストが空でない場合のみチェック）
if excluded_str_set:
    if notification_emp_id in excluded_str_set:
        excluded_count += 1
        logger.info(f"[通知API] 通知除外実行: employee_id={notification_emp_id}")
        continue
```

### 2. 除外リスト読み込み (`load_notification_exclusions`)

**パス優先順位**:
1. `/app/notification_exclusions.json`（コンテナ内パス）← **優先**
2. `../notification_exclusions.json`（ホスト側相対パス）

**問題点**:
- コンテナ内パス（`/app/notification_exclusions.json`）が存在しない場合、空のセットを返す
- ファイルが存在しない場合は空のファイルを作成しようとするが、権限エラーで失敗する可能性がある

**デバッグログ** (行89-91):
```python
logger.info(f"[除外リスト読み込み] 試行パス1: {EXCLUSIONS_FILE}")
logger.info(f"[除外リスト読み込み] 試行パス2: {EXCLUSIONS_FILE_CONTAINER}")
```

---

## 💻 クライアントPC側の動作

### 1. `notification_client.py` - サーバーAPI連携型通知クライアント（主要）

**役割**: クライアントPCで動作し、サーバーAPIから通知を取得して表示する

**主な機能**:

1. **サーバーAPIからの通知取得** (`fetch_notifications_from_server`)
   - `GET /api/notifications`を呼び出し
   - 従業員IDフィルターを指定可能（`employee_filter`）
   - **重要**: サーバー側で除外リストによるフィルタリングが実行される
   - クライアント側でも確認済み通知を除外

2. **通知表示**:
   - 従業員ごとにグループ化して表示
   - エラーと警告で色分け
   - 個別確認・全確認機能

3. **定期チェック**:
   - 5分間隔でサーバーから通知を取得
   - 新しい通知がある場合は自動更新

**重要なコード** (行94-128):
```python
def fetch_notifications_from_server(self) -> List[Dict[str, Any]]:
    url = f"{self.server_url}/api/notifications"
    params = {}
    if self.employee_filter:
        params['employee_id'] = self.employee_filter
    
    response = requests.get(url, params=params, timeout=10)
    # サーバー側で除外リストによるフィルタリングが実行される
    notifications = data.get('notifications', [])
```

**問題点**:
- クライアントはサーバーAPIに依存している
- サーバー側で除外リストが正しく機能していない場合、クライアントにも影響する

### 2. `notification_system.py` - Tkinter GUI通知システム（ローカル版）

**主な機能**:
- **月度勤怠差異チェック**: `check_monthly_attendance_discrepancies()`
  - 給与計算期間（前月16日〜当月15日）の勤怠差異をチェック
  - `attendance_check_service.check_attendance_vs_schedule()`を使用
  - 当日以降の日付はスキップ
  - エラー・警告のみを通知対象

- **通知データ管理**:
  - `notification_data.json`に保存
  - `acknowledged_notifications.json`で確認済みを管理
  - 通知ID形式: `{employee_id}_{work_date}_{alert_type}`

- **GUI表示**:
  - Tkinterで通知一覧を表示
  - 選択した通知を確認済みにできる
  - 詳細情報を表示

**実行モード**:
- `--check-only`: チェックのみ（GUIなし）
- `--show-gui`: GUI表示のみ
- デフォルト: チェック実行後にGUI表示

### 2. `notification_scheduler.py` - スケジューラー

**機能**:
- `schedule`ライブラリを使用
- 毎日深夜2:00に`run_monthly_check()`を実行
- `notification_system.py --check-only`をサブプロセスで実行

### 3. `notification_client.py` - クライアント通知クライアント

**確認が必要**: このファイルの内容を確認して、サーバーAPIとの連携方法を把握する必要があります。

---

## ⚠️ 現在の問題点

### 問題1: 除外リストが機能しない（5000環境）

**症状**:
- クライアントGUIはお知らせを受信している ✅
- 除外リストに従業員IDを追加しても、通知が除外されない ❌

**クライアント側の動作**:
- `notification_client.py`は`GET /api/notifications`を呼び出している
- サーバー側で除外リストによるフィルタリングが実行される
- クライアント側では追加のフィルタリングは行っていない（サーバー側に依存）

**原因の可能性**:

1. **ファイルパスの問題**:
   - `api_notifications.py`の`load_notification_exclusions()`が`/app/notification_exclusions.json`を優先
   - ファイルが存在しない、または読み込みに失敗している可能性

2. **ファイル同期の問題**:
   - ホスト側の`notification_exclusions.json`とコンテナ内の`/app/notification_exclusions.json`が同期していない
   - docker-composeのマウント設定は正しいが、ファイルが実際に存在しない

3. **型の不一致**:
   - 除外リストの従業員IDが文字列と数値で不一致している可能性
   - `api_notifications.py`では文字列セットに変換しているが、元データが数値の場合に問題が発生する可能性

**デバッグ情報** (APIレスポンス):
```json
{
  "count": 2,
  "debug": {
    "exclusions_file": "/app/../notification_exclusions.json",
    "exclusions_file_container": "/app/notification_exclusions.json",
    "exclusions_file_container_exists": false,  // ← 問題！
    "exclusions_file_exists": true
  },
  "excluded_employee_ids": ["2952089", "3952012"],
  "status": "success"
}
```

**分析**:
- `exclusions_file_exists: true` → ホスト側ファイルは存在
- `exclusions_file_container_exists: false` → **コンテナ内パスにファイルが存在しない**
- しかし、`excluded_employee_ids`には値が入っている → ホスト側パスから読み込めている

**結論**:
- ホスト側パス（`/app/../notification_exclusions.json`）からは読み込めている
- しかし、コンテナ内パス（`/app/notification_exclusions.json`）が存在しない
- **docker-compose.ymlのマウント設定は正しいが、実際にファイルがマウントされていない可能性**

**追加の調査が必要**:
- 除外リストに従業員IDを追加した後、APIレスポンスで除外されているか確認
- サーバーログで除外リストフィルタリングのログを確認
- クライアント側で実際に除外されているか確認

---

## 🔧 解決策

### 解決策1: ファイルパスの確認と修正

**確認事項**:
1. ホスト側の`notification_exclusions.json`が存在するか確認
2. docker-compose.ymlのマウント設定が正しいか確認
3. コンテナ内でファイルが実際に存在するか確認

**確認コマンド**:
```powershell
# ホスト側ファイルの確認
Test-Path ..\notification_exclusions.json

# コンテナ内ファイルの確認
docker compose exec attendance-server ls -la /app/notification_exclusions.json
```

### 解決策2: 除外リストの読み込みロジックを修正

**現状の問題**:
- `load_notification_exclusions()`がコンテナ内パスを優先しているが、ファイルが存在しない
- ホスト側パスから読み込めているが、保存時にコンテナ内パスに保存しようとして失敗している可能性

**修正案**:
- ホスト側パスから読み込めた場合は、そのパスに保存する
- または、両方のパスに保存する

### 解決策3: マウント設定の確認

**docker-compose.ymlの確認**:
```yaml
# 現在の設定（確認済み）
- type: bind
  source: ../notification_exclusions.json
  target: /app/notification_exclusions.json
```

**問題の可能性**:
- ホスト側のファイルパスが間違っている
- ファイルが存在しない
- マウントが失敗している（コンテナ起動時のエラー）

---

## 📊 動作確認チェックリスト

### 5000環境での確認

- [ ] `/app/notification_exclusions.json`がコンテナ内に存在するか
- [ ] ホスト側の`../notification_exclusions.json`が存在するか
- [ ] APIレスポンスの`debug.exclusions_file_container_exists`が`true`か
- [ ] 除外リストに従業員IDを追加した後、通知が除外されるか
- [ ] サーバーログに除外リスト読み込み成功のログが出ているか

### 5001環境での確認

- [ ] 5001でも同様の問題が発生するか
- [ ] 5001と5000で動作が異なるか

---

## 🎯 推奨される調査手順

### ステップ1: ファイル存在確認

```powershell
# ホスト側
cd c:\Users\take_me_hospital\attendance\work_attend_server\server
Test-Path ..\notification_exclusions.json
Get-Content ..\notification_exclusions.json

# コンテナ内（5000）
docker compose exec attendance-server ls -la /app/notification_exclusions.json
docker compose exec attendance-server cat /app/notification_exclusions.json
```

### ステップ2: APIデバッグエンドポイントの確認

```powershell
# 除外リストの状態を確認
curl http://localhost:5000/api/notifications/debug
```

### ステップ3: サーバーログの確認

```powershell
# 除外リスト読み込み関連のログを確認
docker compose logs attendance-server --tail=200 | Select-String "除外リスト|通知API|excluded"
```

### ステップ4: クライアント側の動作確認

**クライアントPCで確認**:
1. `notification_client.py`がどのサーバーURLに接続しているか確認（`client_config.json`）
2. クライアント側のログ（`notification_client.log`）を確認
3. サーバーAPIレスポンスを確認（クライアント側でデバッグログを有効化）

---

## 📝 まとめ

### 現在の状況

1. **クライアントGUIはお知らせを受信している** ✅
   - `notification_client.py`がサーバーAPI（`/api/notifications`）から通知を取得している
   - 通知システム自体は動作している

2. **除外リストが機能していない** ❌
   - 5000環境で除外リストに従業員IDを追加しても通知が除外されない
   - APIレスポンスでは除外リストが読み込めているが、実際のフィルタリングで除外されていない可能性

3. **ファイルパスの問題**
   - コンテナ内パス（`/app/notification_exclusions.json`）が存在しない
   - ホスト側パスからは読み込めているが、保存時に問題が発生している可能性

4. **クライアント側の動作**
   - `notification_client.py`はサーバーAPIに依存している
   - サーバー側で除外リストが正しく機能していない場合、クライアントにも影響する

### 次のアクション

1. **ファイル存在確認**: ホスト側とコンテナ内の両方でファイルの存在を確認
2. **APIデバッグ**: `/api/notifications/debug`エンドポイントで詳細を確認
3. **ログ確認**: サーバーログで除外リスト読み込み・フィルタリングのログを確認
4. **クライアント側確認**: クライアントPCのログと設定を確認
5. **コード修正**: 必要に応じて`api_notifications.py`の読み込み・保存ロジックを修正

### クライアント側の確認事項

1. **設定ファイル** (`client_config.json`):
   - `server_url`: どのサーバー（5000/5001）に接続しているか
   - `employee_filter`: 特定従業員のみ表示する設定があるか

2. **ログファイル** (`notification_client.log`):
   - サーバーからの通知取得ログ
   - エラーログ

3. **除外リストの動作確認**:
   - 除外リストに従業員IDを追加
   - サーバーAPI（`/api/notifications`）を直接呼び出して除外されているか確認
   - クライアントGUIで除外されているか確認

---

## 🔗 関連ファイル

- `server/api_notifications.py` - サーバー側API（除外リスト管理）← **重要**
- `card-reder-for-win/notification_client.py` - **クライアント通知クライアント（主要）** ← **重要**
- `work_attend_server/notification_system.py` - クライアント通知システム（ローカル版）
- `work_attend_server/notification_scheduler.py` - 通知スケジューラー
- `work_attend_server/punch_pc_notification.py` - 打刻PC用軽量通知表示
- `server/docker-compose.yml` - 5000環境設定
- `server/docker-compose.dev.yml` - 5001環境設定

### クライアントPC用ファイルの配置

| ファイル | 配置場所 | 用途 |
|---------|---------|------|
| `notification_client.py` | `card-reder-for-win/` | **サーバーAPI連携型（推奨）** |
| `notification_system.py` | `work_attend_server/` | ローカルファイル読み込み型 |
| `punch_pc_notification.py` | `work_attend_server/` | 軽量版通知表示 |
| `client_config.json` | `card-reder-for-win/` | クライアント設定ファイル |

---

**作成日**: 2026-01-27  
**更新日**: 2026-01-27
