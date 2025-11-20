# 勤怠打刻システム（サーバーアプリ）

勤怠打刻データの管理、時間外申告、勤怠チェックをWeb画面で一元管理するサーバーアプリケーションです。

## 🎯 システム概要

このシステムは以下のコンポーネントで構成されています：

- **サーバー**: 打刻データの受信・保存・管理（Flask）
- **Web UI**: 打刻データ検索、勤怠チェック、時間外申告管理、月間集計レポート

### 主な機能

#### 📊 基本機能
- ✅ 打刻データの受信・保存（REST API）
- ✅ チャタリング防止機能（重複打刻の自動除外）
- ✅ Web画面での検索・表示
- ✅ リアルタイム統計情報表示
- ✅ 重複データクリーンアップ機能
- ✅ Docker対応で簡単デプロイ

#### ⏰ 時間外申告機能（NEW!）
- ✅ 時間外作業の申告（最大4件/日）
- ✅ 内残業/外残業の自動分類
- ✅ 深夜時間（20:00-05:00）の自動計算
- ✅ 申告の承認・却下機能
- ✅ 月次集計（前月16日〜当月15日）

#### ✓ 勤怠チェック機能
- ✅ スケジュールと実績の差異チェック
- ✅ 休日打刻アラート
- ✅ 未打刻アラート
- ✅ 時間外申告との照合

---

## 📁 プロジェクト構成

```
work_attend_server/
├── server/                         # サーバーアプリケーション
│   ├── server.py                   # メインサーバー
│   ├── api_attendance.py           # 打刻API
│   ├── api_overtime.py             # 時間外申告API
│   ├── api_leave.py                # 休暇申請API
│   ├── database.py                 # データベース操作
│   ├── overtime.py                 # 時間外申告管理
│   ├── leave_request.py            # 休暇申請管理
│   ├── monthly_report.py           # 月間集計レポート
│   ├── auth.py                     # 認証・認可
│   ├── utils.py                    # ユーティリティ
│   ├── config.py                   # 設定管理
│   ├── templates/                  # HTMLテンプレート
│   │   ├── index.html             # トップページ
│   │   ├── search.html            # 打刻検索
│   │   ├── check.html             # 勤怠チェック
│   │   ├── overtime.html          # 時間外申告
│   │   ├── overtime_list.html     # 時間外一覧
│   │   ├── leave.html             # 休暇申請
│   │   ├── leave_list.html        # 休暇一覧
│   │   └── monthly_report.html    # 月間集計レポート
│   ├── docker-compose.yml         # Docker設定
│   ├── Dockerfile                 # Dockerイメージ
│   ├── requirements_server.txt    # Python依存パッケージ
│   └── SECURITY_SETUP.md          # セキュリティ設定ガイド
├── data/                           # データベース（Dockerの外）
│   └── attendance.db              # SQLiteデータベース
├── DOCKER_GUIDE.md                # Docker環境構築ガイド
├── QUICK_REFERENCE.md             # クイックリファレンス
├── TROUBLESHOOTING.md             # トラブルシューティング
└── LICENSE                        # ライセンス
```

---

## 🚀 クイックスタート

### Docker環境で起動（推奨）

```bash
# 1. serverディレクトリに移動
cd server

# 2. Docker起動
start_docker.bat
# または
docker-compose up -d



# 3. ブラウザでアクセス
# http://localhost:5000
```

### ローカル環境で起動

```bash
# 1. 依存パッケージインストール
cd server
pip install -r requirements_server.txt

# 2. データディレクトリ作成
mkdir -p ../data

# 3. サーバー起動
python server.py
```

---

## 🌐 Web画面

### アクセスURL

| ページ | URL | 説明 |
|--------|-----|------|
| トップページ | http://localhost:5000 | システムダッシュボード |
| 打刻検索 | http://localhost:5000/search | 打刻データの検索・表示 |
| 勤怠チェック | http://localhost:5000/check | スケジュールと実績の照合 |
| 時間外申告 | http://localhost:5000/overtime | 時間外作業の申告 |
| 時間外一覧 | http://localhost:5000/overtime/list | 時間外申告の確認・承認 |

---

## 📡 API エンドポイント

### 打刻データ

```
POST   /api/attendance           # 打刻データ受信
GET    /api/stats                # 統計情報取得
GET    /api/search               # 打刻データ検索
```

### 時間外申告

```
POST   /api/overtime             # 時間外申告登録
GET    /api/overtime             # 時間外申告取得
POST   /api/overtime/<id>/approve   # 承認
POST   /api/overtime/<id>/reject    # 却下
GET    /api/overtime/monthly_summary  # 月次集計
```

### その他

```
GET    /api/health               # ヘルスチェック
GET    /api/employees            # 従業員一覧
GET    /api/attendance_check     # 勤怠チェック
POST   /api/cleanup_duplicates   # 重複削除
```

---

## 🗄️ データベース構造

### 主要テーブル

#### `attendance` - 打刻データ
```sql
- id: 自動採番
- idm: カードID
- timestamp: 打刻時刻
- terminal_id: 端末ID
- received_at: 受信時刻
```

#### `employee_master` - 従業員マスタ
```sql
- employee_num: 従業員番号
- name: 氏名
- idm: カードID
```

#### `attend_schedule` - 勤怠スケジュール
```sql
- employee_id: 従業員ID
- work_date: 勤務日
- work_type: 勤務区分
- start_time: 開始時刻
- end_time: 終了時刻
```

#### `overtime_applications` - 時間外申告
```sql
- id: 申告ID
- employee_num: 従業員番号
- work_date: 作業日
- start_time/end_time: 時間
- overtime_type: 内残業/外残業
- inner_overtime_minutes: 内残業時間
- outer_overtime_minutes: 外残業時間
- night_overtime_minutes: 深夜時間
- status: pending/approved/rejected
- approved_by: 承認者
```

---

## ⚙️ 設定

### ネットワーク設定

サーバー用PCのIPアドレスを固定する方法については、以下を参照：

📄 **[NETWORK_SETUP.md](./NETWORK_SETUP.md)**

- WindowsでのIPアドレス固定手順
- ネットワーク設定の確認方法
- トラブルシューティング

### 環境変数

**重要:** これらの環境変数は、**Docker環境では既に`docker-compose.yml`で設定済み**です。通常は変更不要です。

#### Docker環境の場合

環境変数は `server/docker-compose.yml` の `environment` セクションで自動的に設定されます。変更する場合は、`docker-compose.yml` を編集してください。

```yaml
environment:
  - SERVER_HOST=0.0.0.0
  - SERVER_PORT=5000
  - FLASK_DEBUG=False
  # ... その他の設定
```

#### ローカル環境で直接実行する場合のみ

Dockerを使わずに直接Pythonで実行する場合のみ、環境変数を設定する必要があります：

**Windows (PowerShell):**
```powershell
$env:SERVER_HOST="0.0.0.0"
$env:SERVER_PORT="5000"
$env:FLASK_DEBUG="False"
$env:DATABASE_PATH="../../data/attendance.db"
$env:CHATTERING_THRESHOLD="10"
$env:PAYROLL_START_DAY="16"
$env:PAYROLL_END_DAY="15"
python server.py
```

**Windows (コマンドプロンプト):**
```cmd
set SERVER_HOST=0.0.0.0
set SERVER_PORT=5000
set FLASK_DEBUG=False
set DATABASE_PATH=../../data/attendance.db
set CHATTERING_THRESHOLD=10
set PAYROLL_START_DAY=16
set PAYROLL_END_DAY=15
python server.py
```

**注意:** 通常はDocker環境を使用するため、環境変数の手動設定は不要です。

---

## 🔒 セキュリティ

本番運用時のセキュリティ対策については以下を参照：

📄 **[server/SECURITY_SETUP.md](./server/SECURITY_SETUP.md)**

- 管理者認証（パスワード保護）
- データベースアクセス制御
- セッション管理

---

## 🐳 Docker構成

### データベースの配置

```
attendance/data/attendance.db  # ホスト側（Dockerの外）
  ↓ マウント
/app/data/attendance.db        # Docker内
```

### コンテナ管理

```bash
# 起動
docker-compose up -d

# 停止
docker-compose down

# 再起動
docker-compose restart

# ログ確認
docker-compose logs -f

# コンテナ状態確認
docker-compose ps
```

---

## 📊 時間外申告の仕組み

### 自動分類

**内残業**: 勤務時間内の休憩時間を潰した作業
**外残業**: 勤務予定開始前または終了後の作業
**深夜時間**: 20:00-05:00の時間帯

### 計算例

```
勤務予定: 08:30 - 17:30
時間外作業: 18:00 - 20:00

→ 外残業: 2時間
→ 深夜: 0時間
```

```
勤務予定: 08:30 - 17:30
時間外作業: 18:00 - 22:00

→ 外残業: 4時間
→ 深夜: 2時間（20:00-22:00）
```

### 月次集計

給与計算期間（前月16日〜当月15日）で自動集計

---

## 🛠️ トラブルシューティング

### よくある問題

#### Docker起動エラー

```bash
# Docker Desktopが起動していることを確認
docker version

# コンテナを完全に削除して再作成
docker-compose down -v
docker-compose up -d --build
```

#### データベースが見つからない

```bash
# データベースパスを確認
docker exec attendance-server env | grep DATABASE_PATH

# ホスト側のファイル確認
ls -la ../data/attendance.db
```

#### 時間外申告が保存されない

- 従業員番号が正しいか確認
- ブラウザのコンソールでエラーを確認
- サーバーログを確認: `docker-compose logs -f`

詳細は **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** を参照

---

## 📚 関連ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) | Docker環境構築の詳細ガイド |
| [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) | よく使うコマンドとURL一覧 |
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | 問題解決ガイド |
| [server/SECURITY_SETUP.md](./server/SECURITY_SETUP.md) | セキュリティ設定ガイド |

---

## 🔧 開発情報

### 技術スタック

- **バックエンド**: Python 3.11, Flask
- **データベース**: SQLite3
- **フロントエンド**: HTML5, CSS3, JavaScript（Vanilla）
- **コンテナ**: Docker, Docker Compose

### 開発環境

```bash
# 開発モード起動
cd server
FLASK_ENV=development FLASK_DEBUG=True python server.py

# データベース確認
python check_db.py
```

---

## 📝 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

---

## 📞 サポート

問題が発生した場合：

1. [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) を確認
2. ログを確認: `docker-compose logs -f`
3. データベース状態を確認: `cd server && python check_db.py`

---

## 🎉 最新アップデート

### v2.0.0 (2025-11-06)
- ✨ 時間外申告機能の追加
- ✨ 時間外申告一覧・承認機能
- ✨ 内残業/外残業/深夜時間の自動計算
- ✨ 月次集計機能
- 🔧 データベースパスをDockerの外に変更
- 🔧 コードの最適化（100行以上削減）
- 📚 ドキュメントの整理・統合

### v1.0.0
- 🎉 初回リリース
- 打刻データ管理機能
- 勤怠チェック機能
- Docker対応
