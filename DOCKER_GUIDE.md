# 🐳 Docker環境ガイド

打刻システムのDocker環境構築・運用ガイドです。

---

## 📋 目次

1. [クイックスタート](#クイックスタート)
2. [システム構成](#システム構成)
3. [設定ファイル](#設定ファイル)
4. [開発ワークフロー](#開発ワークフロー)
5. [トラブルシューティング](#トラブルシューティング)

---

## 🚀 クイックスタート

### 前提条件

- Docker Desktopがインストール済み
- Docker Desktopが起動中

### 起動手順

```bash
# 1. serverディレクトリに移動
cd server

# 2. Docker起動（初回はビルドも実行）
start_docker.bat

# または手動で
docker-compose up -d --build

# 3. ブラウザでアクセス
# http://localhost:5000
```

### 停止・再起動

```bash
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

## 🏗️ システム構成

### ディレクトリ構造

```
work_attend_server/
├── data/                          # データベース（Dockerの外）
│   └── attendance.db             # SQLiteデータベース
└── server/                        # サーバー側
    ├── docker-compose.yml        # Docker設定
    ├── Dockerfile                # イメージ定義
    ├── server.py                 # メインサーバー
    ├── api.py                    # API
    ├── database.py               # DB操作
    ├── overtime.py               # 時間外申告
    ├── utils.py                  # ユーティリティ
    ├── config.py                 # 設定
    └── templates/                # HTMLテンプレート
```

### データベースの配置

```
ホスト側:    ../data/attendance.db
            ↓ volumeマウント
Docker内:   /app/data/attendance.db
```

**重要ポイント:**
- データベースはDockerの外（ホスト側）に配置
- コンテナを削除してもデータが消えない
- ホスト側から直接SQLiteツールでアクセス可能

---

## ⚙️ 設定ファイル

### docker-compose.yml

```yaml
services:
  attendance-server:
    build: .
    container_name: attendance-server
    ports:
      - "5000:5000"
    volumes:
      # データベース（Dockerの外）
      - ../../data:/app/data
      # テンプレート（開発時にリアルタイム反映）
      - ./templates:/app/templates
      # Python コード（開発時にリアルタイム反映）
      - ./server.py:/app/server.py
      - ./database.py:/app/database.py
      - ./api.py:/app/api.py
      - ./overtime.py:/app/overtime.py
      - ./utils.py:/app/utils.py
      - ./config.py:/app/config.py
    environment:
      - TZ=Asia/Tokyo
      - FLASK_ENV=docker
      - DATABASE_PATH=/app/data/attendance.db
      - CHATTERING_THRESHOLD=10
    restart: unless-stopped
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 依存パッケージインストール
COPY requirements_server.txt .
RUN pip install --no-cache-dir -r requirements_server.txt

# アプリケーションファイルコピー
COPY server.py database.py api.py overtime.py utils.py config.py ./
COPY templates/ templates/

# データディレクトリ作成
RUN mkdir -p /app/data

EXPOSE 5000

ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/attendance.db

CMD ["python", "server.py"]
```

---

## 🔄 開発ワークフロー

### ファイル変更の反映方法

#### 即座に反映されるファイル（Volumeマウント）

- ✅ `server.py`, `api.py`, `database.py`, `overtime.py`, `utils.py`, `config.py`
- ✅ `templates/` 配下のHTMLファイル

**変更後の操作:**
```bash
# Pythonコード変更時
docker-compose restart

# HTMLテンプレート変更時
# 何もしなくてOK（ブラウザでリロードするだけ）
```

#### 再ビルドが必要なファイル

- ❌ `Dockerfile`
- ❌ `requirements_server.txt`
- ❌ `docker-compose.yml`

**変更後の操作:**
```bash
docker-compose down
docker-compose up -d --build
```

### 開発時の推奨フロー

```bash
# 1. コード変更
# server.py, api.py などを編集

# 2. コンテナ再起動（Pythonコードの場合）
docker-compose restart

# 3. ログ確認
docker-compose logs -f

# 4. ブラウザで動作確認
# http://localhost:5000
```

---

## 🐛 トラブルシューティング

### よくある問題と解決策

#### 1. Docker Desktopが起動していない

**エラー:**
```
error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/version"
```

**解決策:**
```bash
# Docker Desktopを起動
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# 30秒待ってから再試行
docker version
```

#### 2. ポートが使用中

**エラー:**
```
Bind for 0.0.0.0:5000 failed: port is already allocated
```

**解決策:**
```bash
# 既存のコンテナを停止
docker-compose down

# ポートを使用しているプロセスを確認
netstat -ano | findstr :5000

# 必要に応じてプロセスを終了してから再起動
docker-compose up -d
```

#### 3. データベースが見つからない

**症状:** APIリクエストは成功するがデータが空

**確認方法:**
```bash
# Docker内のパスを確認
docker exec attendance-server env | grep DATABASE_PATH

# マウント状態を確認
docker inspect attendance-server --format='{{json .Mounts}}'

# ホスト側のファイル確認
ls -la ../data/attendance.db
```

**解決策:**
```bash
# データディレクトリが存在しない場合
mkdir -p ../data

# コンテナを再作成
docker-compose down
docker-compose up -d
```

#### 4. コード変更が反映されない

**原因:** Volumeマウントが機能していない

**確認:**
```bash
# マウント状態を確認
docker exec attendance-server ls -la /app/

# server.pyの内容を確認
docker exec attendance-server head -20 /app/server.py
```

**解決策:**
```bash
# コンテナを完全に再作成
docker-compose down
docker-compose up -d --build
```

#### 5. ModuleNotFoundError

**エラー:**
```
ModuleNotFoundError: No module named 'overtime'
```

**原因:** 新しいファイルがvolumeマウントされていない

**解決策:**
```bash
# docker-compose.ymlにvolume追加
volumes:
  - ./overtime.py:/app/overtime.py

# コンテナ再作成
docker-compose down
docker-compose up -d
```

---

## 💡 ベストプラクティス

### 開発時

1. **コードはvolumeマウント**
   - リアルタイムで変更を反映
   - 再ビルド不要で効率的

2. **データベースはDockerの外**
   - コンテナ削除してもデータ保持
   - 直接アクセス・バックアップが容易

3. **ログ監視**
   ```bash
   docker-compose logs -f
   ```

### 本番環境

1. **コードはイメージに固定**
   - volumeマウントを最小限に
   - データベースのみマウント

2. **デバッグモードOFF**
   ```yaml
   environment:
     - FLASK_DEBUG=False
     - FLASK_ENV=production
   ```

3. **自動再起動**
   ```yaml
   restart: always
   ```

---

## 📊 コンテナ管理コマンド

### 基本操作

```bash
# 起動
docker-compose up -d

# 停止
docker-compose down

# 再起動
docker-compose restart

# 再ビルド
docker-compose up -d --build

# 完全クリーン
docker-compose down -v
docker-compose up -d --build
```

### 情報確認

```bash
# コンテナ状態
docker-compose ps

# ログ表示
docker-compose logs --tail=50
docker-compose logs -f

# コンテナ内に入る
docker exec -it attendance-server /bin/bash

# 環境変数確認
docker exec attendance-server env

# プロセス確認
docker exec attendance-server ps aux
```

### データベース操作

```bash
# コンテナ内からDB確認
docker exec attendance-server sqlite3 /app/data/attendance.db "SELECT COUNT(*) FROM attendance;"

# ホスト側からDB確認
python check_overtime.py
python check_host_db.py

# バックアップ
cp ../data/attendance.db ../data/attendance_backup_$(date +%Y%m%d).db
```

---

## 🔍 デバッグ方法

### ログレベル設定

```yaml
environment:
  - FLASK_DEBUG=True  # 詳細ログ表示
```

### リアルタイムログ監視

```bash
# すべてのログ
docker-compose logs -f

# エラーのみ
docker-compose logs -f | grep -i error

# 特定のキーワード
docker-compose logs -f | grep -i "時間外"
```

### コンテナ内で直接デバッグ

```bash
# コンテナに入る
docker exec -it attendance-server /bin/bash

# Pythonで直接テスト
python -c "from overtime import *; print(get_overtime_applications())"

# データベース直接確認
sqlite3 /app/data/attendance.db
> SELECT * FROM overtime_applications LIMIT 5;
> .quit
```

---

## 📝 チェックリスト

### 起動前

- [ ] Docker Desktopが起動している
- [ ] `../data/` ディレクトリが存在する
- [ ] ポート5000が空いている

### トラブル時

- [ ] `docker-compose ps` でコンテナ状態確認
- [ ] `docker-compose logs` でエラー確認
- [ ] データベースファイルの存在確認
- [ ] マウント設定の確認

### 開発時

- [ ] コード変更後に `docker-compose restart`
- [ ] HTML変更はブラウザリロードのみ
- [ ] 新規ファイル追加時は volume に追加

---

## 🔗 関連ドキュメント

- [README.md](./README.md) - プロジェクト全体の概要
- [SECURITY_IMPLEMENTATION_GUIDE.md](./SECURITY_IMPLEMENTATION_GUIDE.md) - セキュリティ対策
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - トラブルシューティング

---

**更新日**: 2025-11-06

