# 🐳 Docker設定ガイド - 打刻システム

**対象システム**: Flask + SQLite 勤怠管理システム  
**開発環境**: Docker + docker-compose  
**目的**: 開発・本番環境での適切なDocker設定

---

## 📋 システム構成

```
┌─────────────────────────────────────┐
│           Host Machine              │
│  ┌─────────────────────────────────┐│
│  │        Docker Container         ││
│  │  ┌─────────────────────────────┐││
│  │  │      Flask Application      │││
│  │  │   - server.py                │││
│  │  │   - templates/              │││
│  │  │   - Port: 5000             │││
│  │  └─────────────────────────────┘││
│  │  ┌─────────────────────────────┐││
│  │  │      SQLite Database        │││
│  │  │   - /data/attendance.db     │││
│  │  └─────────────────────────────┘││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

---

## 🔧 設定ファイル

### 1. Dockerfile（基本設定）

```dockerfile
# 打刻システム - サーバー用Dockerfile
FROM python:3.11-slim

# 作業ディレクトリ
WORKDIR /app

# システムパッケージの更新（セキュリティ対策）
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# 依存パッケージのインストール
COPY requirements_server.txt .
RUN pip install --no-cache-dir -r requirements_server.txt

# 🚨 重要: 開発時はCOPYではなくマウントを使用
# COPY server.py .              # ← 開発時は❌
# COPY templates/ templates/    # ← 開発時は❌
# COPY config.py .              # ← 開発時は❌

# データベースディレクトリの作成（永続化用）
RUN mkdir -p /data && chmod 777 /data

# ポート5000を公開
EXPOSE 5000

# 環境変数
ENV FLASK_APP=server.py
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/data/attendance.db

# サーバー起動
CMD ["python", "server.py"]
```

### 2. docker-compose.yml（開発環境）

```yaml
version: '3.8'

services:
  attendance-server:
    build: .
    container_name: attendance-server
    ports:
      - "5000:5000"
    volumes:
      # 🎯 重要: 開発時のファイル同期設定
      - ./data:/data                                    # データ永続化
      - ./templates:/app/templates                      # テンプレート同期
      - ./server.py:/app/server.py                      # サーバーコード同期
      - ./database.py:/app/database.py                 # データベースモジュール同期
      - ./api.py:/app/api.py                           # APIモジュール同期
      - ./utils.py:/app/utils.py                       # ユーティリティモジュール同期
      - ./config.py:/app/config.py                     # 設定モジュール同期
      
      # 🚨 注意: requirements.txtは変更頻度が低いためCOPYのまま
      # - ./requirements_server.txt:/app/requirements_server.txt  # 通常は不要
    
    environment:
      - TZ=Asia/Tokyo
      - FLASK_ENV=development          # 開発環境設定
      - FLASK_DEBUG=1                  # デバッグモード有効
    
    restart: unless-stopped
    
    # ヘルスチェック
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    
    networks:
      - attendance-network

networks:
  attendance-network:
    driver: bridge
```

### 3. docker-compose.prod.yml（本番環境）

```yaml
version: '3.8'

services:
  attendance-server:
    build: 
      context: .
      dockerfile: Dockerfile.prod
    container_name: attendance-server-prod
    ports:
      - "80:5000"  # 本番ポート
    volumes:
      # 🎯 本番環境ではデータのみマウント
      - ./data:/data
      - ./logs:/app/logs  # ログ出力用
    
    environment:
      - TZ=Asia/Tokyo
      - FLASK_ENV=production
      - DATABASE_PATH=/data/attendance.db
    
    restart: always
    
    # リソース制限
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    
    # ログ設定
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    
    networks:
      - attendance-network

networks:
  attendance-network:
    driver: bridge
```

### 4. .dockerignore

```dockerignore
# Git関連
.git/
.gitignore

# Python関連
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
pip-log.txt

# 開発環境ファイル
.vscode/
.pytest_cache/
*.log

# OS関連
.DS_Store
Thumbs.db

# ドキュメント（本番では不要）
README.md
*.md
WORK_LOG_*.md

# バックアップファイル
backup_*.db
*.backup

# 一時ファイル
temp/
tmp/
```

---

## 🚀 使用方法

### 開発環境の起動

```bash
# 1. 初回ビルド・起動
docker-compose up --build

# 2. バックグラウンド実行
docker-compose up -d

# 3. ログ確認
docker-compose logs -f

# 4. 停止
docker-compose down
```

### 本番環境の起動

```bash
# 本番環境用の設定で起動
docker-compose -f docker-compose.prod.yml up -d
```

### よく使うコマンド

```bash
# コンテナ内でコマンド実行
docker exec -it attendance-server bash

# データベース確認
docker exec attendance-server python /app/debug_db.py

# ログの確認
docker logs attendance-server --tail=50 -f

# コンテナの再起動
docker restart attendance-server

# 強制的なリビルド
docker-compose build --no-cache
```

---

## 🔍 トラブルシューティング

### 問題1: ファイル変更が反映されない

**症状**:
```
テンプレートファイルを更新したが、ブラウザで古い内容が表示される
```

**原因と解決策**:
```bash
# 1. マウント設定を確認
docker-compose config

# 2. コンテナ内のファイルを確認
docker exec attendance-server ls -la /app/templates/

# 3. ファイル内容を比較
diff templates/search.html <(docker exec attendance-server cat /app/templates/search.html)
```

**予防策**:
- docker-compose.ymlでボリュームマウントを正しく設定
- 開発時はCOPY命令を使わない

### 問題2: データベースが初期化される

**症状**:
```
コンテナを再起動するたびにデータが消える
```

**原因と解決策**:
```bash
# データディレクトリが正しくマウントされているか確認
docker inspect attendance-server | grep -A 5 "Mounts"

# データファイルの確認
ls -la data/
docker exec attendance-server ls -la /data/
```

**予防策**:
- データディレクトリを必ずマウント
- 定期的なバックアップ

### 問題3: ポート競合

**症状**:
```
Error: Port 5000 is already in use
```

**解決策**:
```bash
# 使用中のポートを確認
netstat -ano | findstr :5000

# プロセスを停止
taskkill /PID <PID> /F

# または別のポートを使用
# docker-compose.yml の ports を "5001:5000" に変更
```

### 問題4: パーミッションエラー

**症状**:
```
Permission denied: '/data/attendance.db'
```

**解決策**:
```bash
# ローカルのdataディレクトリの権限を確認
ls -la data/

# 権限を修正（Linux/Mac）
chmod 777 data/

# Windowsの場合はフォルダーのプロパティから設定
```

---

## 📊 監視とメンテナンス

### log管理

```bash
# ログの確認（最新50行）
docker logs attendance-server --tail=50

# リアルタイムログ監視
docker logs attendance-server -f

# 特定の文字列でフィルタ
docker logs attendance-server | grep "ERROR"
```

### パフォーマンス監視

```bash
# コンテナのリソース使用状況
docker stats attendance-server

# システム情報
docker exec attendance-server df -h
docker exec attendance-server free -m
```

### バックアップとリストア

```bash
# データベースバックアップ
docker cp attendance-server:/data/attendance.db ./backup_$(date +%Y%m%d_%H%M%S).db

# リストア
docker cp backup_20251023_120000.db attendance-server:/data/attendance.db
docker restart attendance-server
```

---

## 🔒 セキュリティ設定

### 本番環境でのセキュリティ強化

```dockerfile
# Dockerfile.prod
FROM python:3.11-slim

# セキュリティ: 非rootユーザーの作成
RUN groupadd -r appuser && useradd -r -g appuser appuser

# アプリケーションディレクトリの作成
RUN mkdir /app && chown appuser:appuser /app
WORKDIR /app

# 依存関係のインストール
COPY requirements_server.txt .
RUN pip install --no-cache-dir -r requirements_server.txt

# アプリケーションファイルのコピー
COPY --chown=appuser:appuser server.py .
COPY --chown=appuser:appuser database.py .
COPY --chown=appuser:appuser api.py .
COPY --chown=appuser:appuser utils.py .
COPY --chown=appuser:appuser config.py .
COPY --chown=appuser:appuser templates/ templates/

# データディレクトリの作成
RUN mkdir -p /data && chown appuser:appuser /data

# 非rootユーザーに切り替え
USER appuser

EXPOSE 5000
CMD ["python", "server.py"]
```

### 環境変数の管理

```bash
# .env ファイルの作成（Git管理対象外）
echo "DATABASE_PASSWORD=secure_password_here" > .env
echo "SECRET_KEY=your_secret_key_here" >> .env

# docker-compose.yml で参照
env_file:
  - .env
```

---

## 📈 スケーリング

### 複数インスタンスの起動

```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  attendance-server:
    build: .
    ports:
      - "5000-5002:5000"  # 複数ポート
    volumes:
      - ./data:/data
    deploy:
      replicas: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - attendance-server
```

### ロードバランサー設定（nginx.conf）

```nginx
upstream attendance_backend {
    server attendance-server:5000;
    server attendance-server:5001;
    server attendance-server:5002;
}

server {
    listen 80;
    location / {
        proxy_pass http://attendance_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📚 ベストプラクティス

### 1. 開発環境設定
- ✅ ファイル変更の即座反映のためのマウント設定
- ✅ デバッグモードの有効化
- ✅ ホットリロードの設定

### 2. 本番環境設定
- ✅ セキュリティ強化（非rootユーザー）
- ✅ リソース制限の設定
- ✅ ログ管理の適切な設定
- ✅ ヘルスチェックの実装

### 3. 共通設定
- ✅ 適切な.dockerignoreの設定
- ✅ マルチステージビルドでのイメージサイズ最適化
- ✅ 環境変数による設定の外部化

---

**最終更新**: 2025年10月23日  
**作成者**: GitHub Copilot  
**参考**: [TROUBLESHOOTING_HISTORY.md](./TROUBLESHOOTING_HISTORY.md)