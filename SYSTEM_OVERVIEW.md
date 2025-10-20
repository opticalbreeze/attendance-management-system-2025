# 打刻システム - システム概要

## 🎯 システム全体像

```
┌────────────────────────────────────────────────────────────────┐
│                    打刻システム全体構成                          │
└────────────────────────────────────────────────────────────────┘

クライアント側（複数台可能）            サーバー側（1台）
┌─────────────────────┐               ┌──────────────────────┐
│  カードリーダー       │  WiFi/LAN    │  Flask Webサーバー   │
│  + Python Client    │ ─────────→   │  (192.168.1.31:5000) │
│                     │               │                      │
│  • IDm読み取り       │ ←─────────   │  • データ受信        │
│  • 打刻時刻記録     │  レスポンス    │  • DB保存           │
│  • MACアドレス取得  │               │  • Web検索画面      │
│  • サーバー送信     │               │                      │
│                     │               │  SQLiteデータベース  │
│  送信失敗時:         │               │  ├─ IDm             │
│  ├─ ローカルDB保存  │               │  ├─ 打刻時刻        │
│  └─ 10分後に再送信  │               │  ├─ 端末ID          │
│                     │               │  └─ 受信時刻        │
└─────────────────────┘               └──────────────────────┘

ブラウザからアクセス
┌─────────────────────┐
│  http://192.168.1.31:5000           │
│  ├─ トップページ: 統計情報          │
│  └─ 検索ページ: IDm検索・CSV出力    │
└─────────────────────┘
```

## 📁 ファイル構成

### クライアント側ファイル

```
プロジェクトフォルダ/
│
├─ client_card_reader.py          ★ メインプログラム
│   ├─ カードリーダー制御
│   ├─ サーバー送信機能
│   ├─ ローカルキャッシュ管理
│   └─ 自動リトライ機能（10分間隔）
│
├─ client_config_gui.py            ★ 設定GUI
│   ├─ サーバーIP設定
│   ├─ ポート設定
│   ├─ 接続テスト機能
│   └─ クライアント起動機能
│
├─ start_client.bat                起動バッチファイル
├─ start_client_config.bat         設定バッチファイル
│
├─ client_config.json              設定ファイル（自動生成）
│   └─ { "server_url": "http://192.168.1.31:5000" }
│
├─ local_cache.db                  ローカルキャッシュDB（自動生成）
│   └─ 送信失敗時のデータを一時保存
│
└─ requirements.txt                依存パッケージ
    ├─ pyscard
    ├─ flask>=2.0.0
    └─ requests>=2.25.0
```

### サーバー側ファイル

```
C:\Users\take_me_hospital\Desktop\N100\
│
├─ server.py                       ★ Flaskサーバー
│   ├─ API: /api/health           (ヘルスチェック)
│   ├─ API: /api/attendance       (打刻データ受信)
│   ├─ API: /api/search           (データ検索)
│   ├─ API: /api/stats            (統計情報)
│   └─ Web: /, /search            (Web画面)
│
├─ start_server.bat                起動バッチファイル
│
├─ requirements_server.txt         依存パッケージ
│   └─ flask>=2.0.0
│
├─ templates/                      HTMLテンプレート
│   ├─ index.html                 (トップページ)
│   └─ search.html                (検索ページ)
│
└─ attendance.db                   SQLiteデータベース（自動生成）
    └─ テーブル: attendance
        ├─ id (主キー)
        ├─ idm (カードID)
        ├─ timestamp (打刻時刻)
        ├─ terminal_id (端末ID/MACアドレス)
        └─ received_at (受信時刻)
```

### ドキュメント

```
├─ README_ATTENDANCE.md            詳細な説明書
├─ SETUP_GUIDE.md                  セットアップガイド
└─ SYSTEM_OVERVIEW.md              このファイル
```

## 🔄 データフロー

### 正常系（送信成功）

```
1. カードをかざす
   ↓
2. クライアントがIDmを読み取り
   - IDm: 012E447C1234ABCD
   - 打刻時刻: 2025-01-15T09:30:45
   - 端末ID: AA:BB:CC:DD:EE:FF
   ↓
3. サーバーにHTTP POST
   POST http://192.168.1.31:5000/api/attendance
   {
     "idm": "012E447C1234ABCD",
     "timestamp": "2025-01-15T09:30:45",
     "terminal_id": "AA:BB:CC:DD:EE:FF"
   }
   ↓
4. サーバーがSQLiteに保存
   INSERT INTO attendance VALUES (...)
   ↓
5. 成功レスポンス
   {
     "status": "success",
     "message": "打刻データを保存しました"
   }
   ↓
6. クライアント側で成功表示
   [送信成功] サーバーレスポンス: 打刻データを保存しました
```

### 異常系（送信失敗）

```
1. カードをかざす
   ↓
2. クライアントがIDmを読み取り
   ↓
3. サーバーへの送信試行
   POST http://192.168.1.31:5000/api/attendance
   ↓
4. ❌ 接続エラー
   - サーバーがダウン
   - ネットワーク切断
   - タイムアウト
   ↓
5. ローカルDB (local_cache.db) に保存
   INSERT INTO pending_records VALUES (...)
   [ローカル保存] IDm: 012E447C1234ABCD
   ↓
6. バックグラウンドで10分待機
   ↓
7. 10分後に自動再送信
   ↓
8. 成功 → local_cache.db から削除
   失敗 → リトライカウント+1、次の10分後に再試行
```

## 🌐 API仕様

### 1. ヘルスチェック

**用途:** サーバー稼働確認、接続テスト

```http
GET /api/health
```

**レスポンス:**
```json
{
  "status": "ok",
  "message": "サーバーは正常に動作しています",
  "timestamp": "2025-01-15T09:30:45"
}
```

### 2. 打刻データ受信

**用途:** クライアントから打刻データを受信

```http
POST /api/attendance
Content-Type: application/json

{
  "idm": "012E447C1234ABCD",
  "timestamp": "2025-01-15T09:30:45",
  "terminal_id": "AA:BB:CC:DD:EE:FF"
}
```

**レスポンス（成功）:**
```json
{
  "status": "success",
  "message": "打刻データを保存しました",
  "idm": "012E447C1234ABCD"
}
```

**レスポンス（エラー）:**
```json
{
  "status": "error",
  "message": "必須フィールドが不足しています"
}
```

### 3. 検索API

**用途:** 打刻データを検索

```http
GET /api/search?idm=012E&start_date=2025-01-01&end_date=2025-01-31&terminal_id=AA:BB&limit=100
```

**パラメータ:**
- `idm`: カードID（部分一致）
- `start_date`: 開始日時
- `end_date`: 終了日時
- `terminal_id`: 端末ID（部分一致）
- `limit`: 最大件数（デフォルト: 100）

**レスポンス:**
```json
{
  "status": "success",
  "count": 15,
  "results": [
    {
      "id": 1,
      "idm": "012E447C1234ABCD",
      "timestamp": "2025-01-15T09:30:45",
      "terminal_id": "AA:BB:CC:DD:EE:FF",
      "received_at": "2025-01-15T09:30:45.123456"
    }
  ]
}
```

### 4. 統計情報API

**用途:** ダッシュボード表示用の統計データ

```http
GET /api/stats
```

**レスポンス:**
```json
{
  "status": "success",
  "stats": {
    "total_records": 1234,
    "unique_idm": 56,
    "unique_terminals": 3,
    "today_count": 89,
    "latest": [
      {
        "idm": "012E447C1234ABCD",
        "timestamp": "2025-01-15T09:30:45",
        "terminal_id": "AA:BB:CC:DD:EE:FF"
      }
    ]
  }
}
```

## 🎨 Web画面

### トップページ (`/`)

**URL:** `http://192.168.1.31:5000/`

**機能:**
- 統計情報カード表示
  - 総打刻数
  - 登録カード数
  - 端末数
  - 今日の打刻数
- 最新の打刻履歴（直近5件）
- 検索ページへのリンク
- 30秒ごとに自動更新

### 検索ページ (`/search`)

**URL:** `http://192.168.1.31:5000/search`

**機能:**
- 検索フォーム
  - IDm（カードID）
  - 開始日時
  - 終了日時
  - 端末ID
- 検索結果テーブル表示
- CSV出力機能
- リアルタイム検索

## 🔐 セキュリティ考慮事項

### 現在の実装（試作版）

- ✅ ローカルネットワーク内での通信を想定
- ✅ SQLインジェクション対策（パラメータ化クエリ使用）
- ⚠️ 認証機能なし（誰でもアクセス可能）
- ⚠️ HTTPS未対応（HTTP通信）

### 本番環境への移行時の推奨事項

1. **認証の追加**
   - Basic認証またはトークン認証
   - ユーザー管理機能

2. **HTTPS化**
   - SSL/TLS証明書の導入
   - 通信の暗号化

3. **アクセス制御**
   - IPアドレス制限
   - ファイアウォール設定

4. **ログ記録**
   - アクセスログ
   - エラーログ
   - 監査ログ

## 📊 データベース設計

### attendance テーブル

```sql
CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 連番ID
    idm TEXT NOT NULL,                     -- カードID（16進数文字列）
    timestamp TEXT NOT NULL,               -- 打刻時刻（ISO 8601形式）
    terminal_id TEXT NOT NULL,             -- 端末ID（MACアドレス）
    received_at TEXT NOT NULL,             -- サーバー受信時刻
    INDEX idx_idm (idm),                   -- IDmでの検索高速化
    INDEX idx_timestamp (timestamp),       -- 日時での検索高速化
    INDEX idx_terminal_id (terminal_id)    -- 端末IDでの検索高速化
);
```

**データ例:**
```
id  | idm              | timestamp           | terminal_id       | received_at
----|------------------|---------------------|-------------------|--------------------
1   | 012E447C1234ABCD | 2025-01-15T09:30:45 | AA:BB:CC:DD:EE:FF | 2025-01-15T09:30:45
2   | 012E447C5678EFGH | 2025-01-15T09:35:20 | AA:BB:CC:DD:EE:FF | 2025-01-15T09:35:21
3   | 012E447C1234ABCD | 2025-01-15T18:15:10 | BB:CC:DD:EE:FF:00 | 2025-01-15T18:15:10
```

## 🚀 運用シナリオ

### 起動手順

**毎朝の起動:**

1. サーバー側
   ```cmd
   C:\Users\take_me_hospital\Desktop\N100\start_server.bat
   ```

2. クライアント側（各端末）
   ```cmd
   start_client.bat
   ```

### 日次運用

```
08:00 - システム起動
08:30 - 出勤打刻開始
12:00 - 昼休憩（打刻続行）
18:00 - 退勤打刻
18:30 - データ確認（Web画面）
19:00 - CSV出力（必要に応じて）
```

### 週次メンテナンス

```
金曜日 18:00
1. データベースバックアップ
   copy attendance.db attendance_backup_20250115.db

2. ログ確認
   - エラーがないか確認

3. ディスク容量確認
   - データベースサイズ確認
```

## 🔧 拡張可能性

### 将来的な機能追加案

1. **複数リーダー同時接続**
   - 現在: 1台のリーダーのみ
   - 拡張: 複数リーダーを並列処理

2. **ユーザー管理**
   - IDmとユーザー情報の紐付け
   - 名前、部署、役職など

3. **勤怠集計機能**
   - 出勤・退勤の自動判定
   - 労働時間の自動計算
   - 月次レポート生成

4. **通知機能**
   - 打刻完了時の音声通知
   - 異常検知時のアラート
   - メール通知

5. **モバイル対応**
   - スマホからの閲覧
   - レスポンシブデザイン

## 📝 バージョン履歴

### v1.0.0 (2025-01-15)
- ✅ 初回リリース
- ✅ カードリーダー対応（複数メーカー）
- ✅ サーバー送信機能
- ✅ ローカルキャッシュ・リトライ機能
- ✅ Web検索画面
- ✅ CSV出力機能

---

**システム開発完了** 🎉

このドキュメントは、打刻システムの全体像を把握するための参照資料です。
詳細な手順は `SETUP_GUIDE.md` を参照してください。

