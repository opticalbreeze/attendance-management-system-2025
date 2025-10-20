# ICカード打刻システム

ICカードリーダーを使った勤怠打刻システムです。WindowsとRaspberry Piの両方に対応しています。

## 🎯 システム概要

このシステムは、ICカードリーダーでカードを読み取り、サーバーに打刻データを送信する勤怠管理システムです。

### 主な機能

- ✅ ICカードの読み取り（Mifare、FeliCa等に対応）
- ✅ サーバーへの打刻データ送信
- ✅ 送信失敗時のローカルキャッシュ保存
- ✅ 自動リトライ機能（10分間隔）
- ✅ Web画面での検索・CSV出力
- ✅ マルチリーダー対応

### Windows版の機能
- 🔊 PCスピーカーで音声フィードバック
- 🖥️ GUIで状態表示（GUI版のみ）
- 📊 リアルタイム統計表示

### Raspberry Pi版の機能
- 💡 RGB LED（赤・緑・青）で状態表示
- 🔔 圧電ブザーで音声フィードバック
- 📺 LCD（I2C 1602）でメッセージ表示
- 🔌 GPIO制御による拡張性

## 📁 プロジェクト構成

```
simple_card_reader-main/
├── client_card_reader.py              # Windowsクライアント（CUI版）
├── client_card_reader_windows_gui.py  # Windowsクライアント（GUI版）
├── client_card_reader_unified.py      # ラズパイ統合版
├── client_config_gui.py               # 設定GUI
├── gpio_config.py                     # GPIO設定（ラズパイ用）
├── lcd_i2c.py                         # LCD制御（ラズパイ用）
├── start_client.bat                   # Windows CUI版起動
├── start_windows_gui.bat              # Windows GUI版起動
├── start_unified.sh                   # ラズパイ統合版起動
├── start_client_config.bat            # 設定GUI起動
├── requirements_windows.txt           # Windows依存パッケージ
├── requirements_unified.txt           # ラズパイ依存パッケージ
├── server/                            # サーバー側プログラム
│   ├── server.py                      # Flaskサーバー
│   ├── start_server.bat               # サーバー起動
│   ├── requirements_server.txt        # サーバー依存パッケージ
│   ├── docker-compose.yml             # Docker構成
│   ├── Dockerfile                     # Dockerイメージ
│   └── templates/                     # HTMLテンプレート
├── SETUP_GUIDE.md                     # セットアップガイド
├── SYSTEM_OVERVIEW.md                 # システム概要
└── README_ATTENDANCE.md               # 詳細説明
```

## 🚀 クイックスタート

### 1. サーバー側のセットアップ

#### 通常起動
```bash
cd server
pip install -r requirements_server.txt
python server.py
```

#### Docker起動（推奨）
```bash
cd server
docker-compose up -d
```

サーバーは `http://サーバーIP:5000` で起動します。

### 2. クライアント側のセットアップ

#### Windows（CUI版）
```cmd
pip install -r requirements_windows.txt
start_client_config.bat  # 設定（初回のみ）
start_client.bat         # クライアント起動
```

#### Windows（GUI版）
```cmd
pip install -r requirements_windows.txt
start_client_config.bat  # 設定（初回のみ）
start_windows_gui.bat    # GUI版起動
```

#### Raspberry Pi（統合版）
```bash
pip3 install -r requirements_unified.txt
./start_client_config.bat  # 設定（初回のみ）
./start_unified.sh         # 統合版起動
```

## 🔧 対応カードリーダー

### 動作確認済み
- **Sony RC-S380** (PaSoRi) - FeliCa対応
- **Sony RC-S330** (PaSoRi)
- **Circle CIR315 CL** - USB NFC Reader
- **ACS ACR122U**

### 動作予想
- Identiv uTrust 3700 F
- SCM SCL3711

## 📱 対応ICカード

- **Mifare Classic** (1K, 4K)
- **Mifare Ultralight** (C)
- **FeliCa** (Suica、PASMO、WAON、nanaco等)
- **ISO14443 Type A/B**

## 🌐 システム構成

```
┌─────────────────────────────┐          ┌─────────────────────────────┐
│  クライアント（複数台可能）  │  WiFi    │  サーバー（1台）             │
│                             │  /LAN    │                             │
│  ┌─────────────────────┐   │ ─────→  │  ┌─────────────────────┐   │
│  │ カードリーダー       │   │          │  │ Flask Webサーバー    │   │
│  │ + Python Client     │   │ ←─────  │  │ (port 5000)         │   │
│  └─────────────────────┘   │ Response │  └─────────────────────┘   │
│                             │          │                             │
│  • IDm読み取り              │          │  • データ受信               │
│  • 打刻時刻記録             │          │  • SQLite保存              │
│  • サーバー送信             │          │  • Web検索画面             │
│  • ローカルキャッシュ       │          │  • CSV出力                │
└─────────────────────────────┘          └─────────────────────────────┘
```

## 💻 Web画面

ブラウザで `http://サーバーIP:5000` にアクセスすると、以下の機能が利用できます：

- **トップページ**: 統計情報と最新履歴
- **検索ページ**: カードID検索、CSV出力

## 🔐 セキュリティ

現在の実装は試作版のため、以下の点にご注意ください：

- ⚠️ 認証機能なし（ローカルネットワーク内での使用を想定）
- ⚠️ HTTPS未対応
- ✅ SQLインジェクション対策済み

本番環境への移行時は、認証機能の追加とHTTPS化を推奨します。

## 📖 詳細ドキュメント

- [セットアップガイド](SETUP_GUIDE.md) - 詳細なセットアップ手順
- [システム概要](SYSTEM_OVERVIEW.md) - システム全体の詳細説明
- [勤怠システム詳細](README_ATTENDANCE.md) - 勤怠管理機能の詳細

## 🔧 トラブルシューティング

### カードリーダーが認識されない
1. USBポートを確認
2. ドライバーのインストール確認
3. デバイスマネージャーで認識を確認
4. 別のUSBポートで試す

### サーバーに接続できない
1. サーバーが起動しているか確認
2. ファイアウォール設定を確認
3. 同じネットワークに接続しているか確認
4. `client_config.json` のサーバーIPを確認

### Windows版でpyscardインストールエラー
1. Microsoft Visual C++ Build Tools をインストール
2. https://visualstudio.microsoft.com/ja/visual-cpp-build-tools/

### ラズパイ版でLCD/GPIOが動作しない
1. I2C、GPIOが有効か確認: `sudo raspi-config`
2. 権限を確認: `sudo usermod -a -G gpio,i2c $USER`
3. 再起動後、再度試行

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🙏 謝辞

- pyscard開発チーム
- nfcpy開発チーム
- Flask開発チーム
- NFCカードリーダーメーカー各社

---

⭐ このプロジェクトが役に立ったら、スターをつけていただけると嬉しいです！
