# 勤怠打刻システム - サーバー# 勤怠打刻システム - サーバー



ICカード打刻システムのサーバー側プログラムです。クライアントからの打刻データを受信・保存し、Web画面で管理できます。ICカード打刻システムのサーバー側プログラムです。クライアントからの打刻データを受信・保存し、Web画面で管理できます。



## 🎯 システム概要## 🎯 システム概要



打刻データの受信・保存・検索・統計機能を提供するFlaskベースのWebサーバーです。打刻データの受信・保存・検索・統計機能を提供するFlaskベースのWebサーバーです。



### 主な機能### 主な機能



- ✅ 打刻データの受信・保存（REST API）- ✅ 打刻データの受信・保存（REST API）

- ✅ チャタリング防止機能（重複打刻の自動除外）- ✅ チャタリング防止機能（重複打刻の自動除外）

- ✅ Web画面での検索・CSV出力- ✅ Web画面での検索・CSV出力

- ✅ リアルタイム統計情報表示- ✅ リアルタイム統計情報表示

- ✅ 重複データクリーンアップ機能- ✅ 重複データクリーンアップ機能

- ✅ Docker対応で簡単デプロイ- ✅ Docker対応で簡単デプロイ



## 📁 プロジェクト構成## 📁 プロジェクト構成



``````

card_reader_improved/simple_card_reader-main/

├── server/                            # サーバー側プログラム├── client_card_reader.py              # Windowsクライアント（CUI版）

│   ├── server_improved.py             # Flaskサーバー（改善版）├── client_card_reader_windows_gui.py  # Windowsクライアント（GUI版）

│   ├── templates/                     # HTMLテンプレート├── client_card_reader_unified.py      # ラズパイ統合版

│   │   ├── index.html                 # トップページ├── client_config_gui.py               # 設定GUI

│   │   └── search.html                # 検索ページ├── gpio_config.py                     # GPIO設定（ラズパイ用）

│   ├── start_server.bat               # サーバー起動├── lcd_i2c.py                         # LCD制御（ラズパイ用）

│   ├── start_docker.bat               # Docker起動├── start_client.bat                   # Windows CUI版起動

│   ├── stop_docker.bat                # Docker停止├── start_windows_gui.bat              # Windows GUI版起動

│   ├── requirements_server.txt        # サーバー依存パッケージ├── start_unified.sh                   # ラズパイ統合版起動

│   ├── docker-compose.yml             # Docker構成├── start_client_config.bat            # 設定GUI起動

│   ├── Dockerfile                     # Dockerイメージ├── requirements_windows.txt           # Windows依存パッケージ

│   └── data/                          # データ保存ディレクトリ├── requirements_unified.txt           # ラズパイ依存パッケージ

├── README.md                          # このファイル├── server/                            # サーバー側プログラム

├── SYSTEM_OVERVIEW.md                 # システム概要│   ├── server.py                      # Flaskサーバー

└── LICENSE                            # ライセンス│   ├── start_server.bat               # サーバー起動

```│   ├── requirements_server.txt        # サーバー依存パッケージ

│   ├── docker-compose.yml             # Docker構成

## 🚀 クイックスタート│   ├── Dockerfile                     # Dockerイメージ

│   └── templates/                     # HTMLテンプレート

### Docker起動（推奨）├── SETUP_GUIDE.md                     # セットアップガイド

```bash├── SYSTEM_OVERVIEW.md                 # システム概要

cd server└── README_ATTENDANCE.md               # 詳細説明

docker-compose up -d```

```

## 🚀 クイックスタート

### 通常起動

```bash### 1. サーバー側のセットアップ

cd server

pip install -r requirements_server.txt#### 通常起動

python server_improved.py```bash

```cd server

pip install -r requirements_server.txt

サーバーは `http://localhost:5000` で起動します。python server.py

```

## 🌐 アクセス方法

#### Docker起動（推奨）

- **トップページ**: http://localhost:5000```bash

- **検索ページ**: http://localhost:5000/searchcd server

- **API エンドポイント**:docker-compose up -d

  - ヘルスチェック: `GET /api/health````

  - 打刻データ受信: `POST /api/attendance`

  - データ検索: `GET /api/search`サーバーは `http://サーバーIP:5000` で起動します。

  - 統計情報: `GET /api/stats`

  - 重複削除: `POST /api/cleanup_duplicates`### 2. クライアント側のセットアップ



## ⚡ チャタリング防止機能#### Windows（CUI版）

```cmd

同じカードからの短時間での連続打刻を自動的に検出・除外します。pip install -r requirements_windows.txt

start_client_config.bat  # 設定（初回のみ）

- **デフォルト閾値**: 10秒start_client.bat         # クライアント起動

- **設定変更**: 環境変数 `CHATTERING_THRESHOLD` で調整可能```

- **ログ出力**: チャタリング検出時は詳細ログを出力

#### Windows（GUI版）

### 環境変数設定例```cmd

```bashpip install -r requirements_windows.txt

# チャタリング防止の閾値を15秒に設定start_client_config.bat  # 設定（初回のみ）

export CHATTERING_THRESHOLD=15start_windows_gui.bat    # GUI版起動

docker-compose up -d```

```

#### Raspberry Pi（統合版）

## 🗂️ データベース```bash

pip3 install -r requirements_unified.txt

- **形式**: SQLite3./start_client_config.bat  # 設定（初回のみ）

- **場所**: `server/data/attendance.db`./start_unified.sh         # 統合版起動

- **テーブル**: `attendance````

  - `id`: レコードID

  - `idm`: カードID## 🔧 対応カードリーダー

  - `timestamp`: 打刻日時

  - `terminal_id`: 端末ID### 動作確認済み

  - `received_at`: 受信日時- **Sony RC-S380** (PaSoRi) - FeliCa対応

- **Sony RC-S330** (PaSoRi)

## 🔧 重複データクリーンアップ- **Circle CIR315 CL** - USB NFC Reader

- **ACS ACR122U**

既存の重複データをクリーンアップできます。

### 動作予想

### プレビュー（削除前確認）- Identiv uTrust 3700 F

```bash- SCM SCL3711

curl -X POST http://localhost:5000/api/cleanup_duplicates \

  -H "Content-Type: application/json" \## 📱 対応ICカード

  -d '{"threshold_seconds":10,"dry_run":true}'

```- **Mifare Classic** (1K, 4K)

- **Mifare Ultralight** (C)

### 実際の削除- **FeliCa** (Suica、PASMO、WAON、nanaco等)

```bash- **ISO14443 Type A/B**

curl -X POST http://localhost:5000/api/cleanup_duplicates \

  -H "Content-Type: application/json" \## 🌐 システム構成

  -d '{"threshold_seconds":10,"dry_run":false}'

``````

┌─────────────────────────────┐          ┌─────────────────────────────┐

## 📊 統計情報│  クライアント（複数台可能）  │  WiFi    │  サーバー（1台）             │

│                             │  /LAN    │                             │

Web画面では以下の統計情報をリアルタイム表示：│  ┌─────────────────────┐   │ ─────→  │  ┌─────────────────────┐   │

│  │ カードリーダー       │   │          │  │ Flask Webサーバー    │   │

- 総打刻件数│  │ + Python Client     │   │ ←─────  │  │ (port 5000)         │   │

- ユニークIDm数│  └─────────────────────┘   │ Response │  └─────────────────────┘   │

- ユニーク端末数│                             │          │                             │

- 今日の打刻件数│  • IDm読み取り              │          │  • データ受信               │

- 最新の打刻履歴│  • 打刻時刻記録             │          │  • SQLite保存              │

│  • サーバー送信             │          │  • Web検索画面             │

## 🐳 Docker設定│  • ローカルキャッシュ       │          │  • CSV出力                │

└─────────────────────────────┘          └─────────────────────────────┘

### 起動```

```bash

cd server## 💻 Web画面

docker-compose up -d

```ブラウザで `http://サーバーIP:5000` にアクセスすると、以下の機能が利用できます：



### 停止- **トップページ**: 統計情報と最新履歴

```bash- **検索ページ**: カードID検索、CSV出力

docker-compose down

```## 🔐 セキュリティ



### ログ確認現在の実装は試作版のため、以下の点にご注意ください：

```bash

docker-compose logs -f- ⚠️ 認証機能なし（ローカルネットワーク内での使用を想定）

```- ⚠️ HTTPS未対応

- ✅ SQLインジェクション対策済み

## 📝 API仕様

本番環境への移行時は、認証機能の追加とHTTPS化を推奨します。

### 打刻データ送信

```http## 📖 詳細ドキュメント

POST /api/attendance

Content-Type: application/json- [セットアップガイド](SETUP_GUIDE.md) - 詳細なセットアップ手順

- [システム概要](SYSTEM_OVERVIEW.md) - システム全体の詳細説明

{- [勤怠システム詳細](README_ATTENDANCE.md) - 勤怠管理機能の詳細

  "idm": "カードID（16進数）",

  "timestamp": "2025-10-23T12:00:00",## 🔧 トラブルシューティング

  "terminal_id": "端末ID"

}### カードリーダーが認識されない

```1. USBポートを確認

2. ドライバーのインストール確認

### レスポンス（正常）3. デバイスマネージャーで認識を確認

```json4. 別のUSBポートで試す

{

  "status": "success",### サーバーに接続できない

  "message": "打刻データを保存しました",1. サーバーが起動しているか確認

  "idm": "カードID",2. ファイアウォール設定を確認

  "record_id": 1233. 同じネットワークに接続しているか確認

}4. `client_config.json` のサーバーIPを確認

```

### Windows版でpyscardインストールエラー

### レスポンス（チャタリング検出）1. Microsoft Visual C++ Build Tools をインストール

```json2. https://visualstudio.microsoft.com/ja/visual-cpp-build-tools/

{

  "status": "warning",### ラズパイ版でLCD/GPIOが動作しない

  "message": "チャタリング検出：短時間での重複打刻のため無視しました",1. I2C、GPIOが有効か確認: `sudo raspi-config`

  "idm": "カードID",2. 権限を確認: `sudo usermod -a -G gpio,i2c $USER`

  "time_diff": 5.2,3. 再起動後、再度試行

  "previous_record_id": 122

}## 📄 ライセンス

```

このプロジェクトはMITライセンスの下で公開されています。

## 🛠️ 開発・デバッグ

## 🙏 謝辞

### ログ監視

```bash- pyscard開発チーム

# Dockerの場合- nfcpy開発チーム

docker-compose logs -f attendance-server- Flask開発チーム

- NFCカードリーダーメーカー各社

# 通常起動の場合

# コンソール出力を確認---

```

⭐ このプロジェクトが役に立ったら、スターをつけていただけると嬉しいです！

### データベース直接アクセス
```bash
# コンテナ内での実行
docker-compose exec attendance-server python -c "
import sqlite3
conn = sqlite3.connect('/data/attendance.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM attendance')
print('総レコード数:', cursor.fetchone()[0])
conn.close()
"
```

## � ドキュメント

### 開発者向けドキュメント
- 📋 **[トラブルシューティング履歴](./TROUBLESHOOTING_HISTORY.md)** - 過去の問題と解決策の詳細記録
- 🤖 **[AI向け開発ガイド](./AI_DEVELOPMENT_GUIDE.md)** - AIアシスタント用の開発指針とベストプラクティス
- 🐳 **[Docker設定ガイド](./DOCKER_SETUP_GUIDE.md)** - 開発・本番環境でのDocker設定の詳細

### システム仕様
- 🔧 **[API仕様書](./API_SPECIFICATION.md)** - RESTful APIの詳細仕様
- 🗄️ **[データベース設計](./DATABASE_SCHEMA.md)** - テーブル構造と関係性

これらのドキュメントは実際の開発で発生した問題をベースに作成されており、同様の問題を避けるための貴重な情報源となります。

## �📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照してください。