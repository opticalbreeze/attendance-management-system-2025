# 打刻システム - ICカードリーダー連携

複数のICカードリーダーに対応した打刻システムです。クライアント端末でカードを読み取り、サーバーに送信してデータベースに格納します。

## 📋 システム構成

```
┌─────────────┐        WiFi         ┌─────────────┐
│  クライアント  │  ─────────────→   │  サーバー    │
│  (カードリーダー) │                  │  (Flask)    │
│  + Python     │  ←─────────────   │  + SQLite   │
└─────────────┘      レスポンス      └─────────────┘
```

### クライアント側
- カードリーダーでIDm（カードID）を読み取り
- 打刻時刻と端末ID（MACアドレス）を記録
- サーバーにHTTP POST送信
- 送信失敗時はローカルDBに保存 → 10分後に自動再送信

### サーバー側
- Flaskで打刻データを受信
- SQLiteデータベースに格納
- Webブラウザで検索・閲覧
- CSV出力機能

## 🔧 セットアップ

### 1. クライアント側（カードリーダー接続PC）

#### 必要なもの
- Python 3.7以上
- ICカードリーダー（Sony PaSoRi, Circle CIR315など）
- Windows / Linux / macOS

#### インストール手順

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# Windows の場合
pip install pyscard flask requests

# Linux の場合
sudo apt install python3-pyscard pcscd
pip install flask requests
```

#### 設定

```bash
# 設定GUIを起動
python client_config_gui.py
```

設定GUI画面で以下を入力：
- **サーバーIP**: `192.168.1.31` (デフォルト)
- **ポート**: `5000` (デフォルト)

「💾 保存」または「▶️ 保存して起動」をクリック

#### クライアント起動

```bash
python client_card_reader.py
```

### 2. サーバー側

#### サーバーファイルの配置

サーバーファイルは以下のディレクトリに配置してください：

```
C:\Users\take_me_hospital\Desktop\N100\
├── server.py
├── requirements_server.txt
├── templates/
│   ├── index.html
│   └── search.html
└── attendance.db (自動生成)
```

#### サーバー起動

```bash
# サーバーディレクトリに移動
cd C:\Users\take_me_hospital\Desktop\N100

# 依存パッケージのインストール
pip install flask

# サーバー起動
python server.py
```

サーバーが起動すると以下のように表示されます：

```
======================================================================
🔖 打刻システム - サーバー
======================================================================
✅ データベース初期化完了
📁 データベース: C:\Users\take_me_hospital\Desktop\N100\attendance.db
🌐 サーバー起動: http://0.0.0.0:5000
🔍 ブラウザで http://192.168.1.31:5000 にアクセスしてください
======================================================================
```

## 📱 使い方

### クライアント（打刻）

1. `client_card_reader.py` を起動
2. カードをかざす
3. 自動的にサーバーに送信される
4. 送信失敗時は10分後に自動再送信

```
======================================================================
🔖 打刻システム - クライアント
======================================================================
📍 端末ID: AA:BB:CC:DD:EE:FF
🌐 サーバー: http://192.168.1.31:5000

✅ [検出] Sony RC-S380 PaSoRi

📱 カードをかざしてください... (Ctrl+C で終了)

[2025-01-15 09:30:45] 🎯 カード#1
             📋 IDm: 012E447C1234ABCD
[送信成功] サーバーレスポンス: 打刻データを保存しました
```

### サーバー（Web管理画面）

#### トップページ
ブラウザで `http://192.168.1.31:5000` にアクセス

- 統計情報（総打刻数、登録カード数など）
- 最新の打刻履歴
- 検索ページへのリンク

#### 検索ページ
`http://192.168.1.31:5000/search` にアクセス

検索条件：
- **IDm（カードID）**: 部分一致検索
- **開始日時**: 指定日時以降の打刻
- **終了日時**: 指定日時以前の打刻
- **端末ID**: MACアドレスで絞り込み

結果をCSV出力可能

## 🗂️ データベース構造

### attendance テーブル

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER | 主キー（自動採番） |
| idm | TEXT | カードID（16進数） |
| timestamp | TEXT | 打刻時刻（ISO 8601形式） |
| terminal_id | TEXT | 端末ID（MACアドレス） |
| received_at | TEXT | サーバー受信時刻 |

## 🔄 データの流れ

```
1. カードをかざす
   ↓
2. クライアントがIDmを読み取り
   ↓
3. サーバーにPOST送信
   {
     "idm": "012E447C1234ABCD",
     "timestamp": "2025-01-15T09:30:45",
     "terminal_id": "AA:BB:CC:DD:EE:FF"
   }
   ↓
4. サーバーがデータベースに保存
   ↓
5. 成功レスポンス
   {
     "status": "success",
     "message": "打刻データを保存しました"
   }
```

### 送信失敗時

```
1. サーバーに接続できない
   ↓
2. ローカルDB (local_cache.db) に保存
   ↓
3. 10分後に自動再送信
   ↓
4. 成功したら local_cache.db から削除
```

## 📊 API仕様

### 1. ヘルスチェック

```
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

### 2. 打刻データ送信

```
POST /api/attendance
Content-Type: application/json

{
  "idm": "012E447C1234ABCD",
  "timestamp": "2025-01-15T09:30:45",
  "terminal_id": "AA:BB:CC:DD:EE:FF"
}
```

**レスポンス:**
```json
{
  "status": "success",
  "message": "打刻データを保存しました",
  "idm": "012E447C1234ABCD"
}
```

### 3. 検索

```
GET /api/search?idm=012E&start_date=2025-01-01&end_date=2025-01-31
```

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

### 4. 統計情報

```
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
    "latest": [...]
  }
}
```

## 🎯 対応カードリーダー

- Sony PaSoRi (RC-S380, RC-S330)
- Circle USB NFC Reader (CIR315 CL)
- ACS ACR122U
- SCM/Identiv NFCリーダー
- その他PC/SC対応リーダー

## 🔧 トラブルシューティング

### クライアント側

**カードリーダーが検出されない**
- USBケーブルを確認
- デバイスマネージャーで認識を確認
- ドライバーを再インストール

**サーバーに接続できない**
- サーバーIPアドレスを確認
- ファイアウォール設定を確認
- サーバーが起動しているか確認

### サーバー側

**ポート5000が使用中**
```python
# server.py の最後を編集
app.run(host='0.0.0.0', port=5001, debug=False)  # ポート変更
```

**データベースエラー**
```bash
# データベースファイルを削除して再生成
del attendance.db
python server.py
```

## 📝 ファイル一覧

### クライアント側
- `client_card_reader.py` - メインプログラム
- `client_config_gui.py` - 設定GUI
- `client_config.json` - 設定ファイル（自動生成）
- `local_cache.db` - ローカルキャッシュ（自動生成）

### サーバー側
- `server/server.py` - Flaskサーバー
- `server/templates/index.html` - トップページ
- `server/templates/search.html` - 検索ページ
- `server/attendance.db` - データベース（自動生成）

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🙋 サポート

問題が発生した場合は、以下を確認してください：

1. Python バージョン: `python --version`
2. 依存パッケージ: `pip list`
3. ログファイル: コンソール出力を確認

---

**作成日**: 2025年1月
**バージョン**: 1.0.0

