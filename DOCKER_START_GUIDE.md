# 🐳 Docker起動手順

## 前提条件

1. **Docker Desktop** がインストールされ、起動していること
2. **ルートディレクトリ**（`attend_server/`）または **serverディレクトリ**で実行可能

---

## 🚀 起動方法

### 方法1: バッチファイルを使用（Windows推奨）

**ルートディレクトリから実行（推奨）:**
```cmd
start_docker.bat
```

**serverディレクトリから実行:**
```cmd
cd server
start_docker.bat
```

### 方法2: コマンドラインから直接起動

**ルートディレクトリから実行:**
```bash
# ビルドと起動
docker-compose up -d --build

# 起動確認
docker-compose ps

# ログ確認
docker-compose logs -f
```

**serverディレクトリから実行:**
```bash
cd server
docker-compose up -d --build
docker-compose ps
docker-compose logs -f
```

---

## ✅ 起動確認

起動が成功すると、以下のように表示されます：

```
✅ データベース初期化完了
🔖 打刻システム - サーバー（改善版）
🌐 サーバー起動: http://0.0.0.0:5000
```

ブラウザで以下のURLにアクセス：
- **ローカル**: http://localhost:5000
- **ネットワーク**: http://<サーバーのIPアドレス>:5000

---

## 📊 よく使うコマンド

### ログ確認
```bash
docker-compose logs -f
```

### コンテナの状態確認
```bash
docker-compose ps
```

### コンテナの停止
```bash
docker-compose down
```

### コンテナの再起動
```bash
docker-compose restart
```

### コンテナ内でコマンド実行
```bash
docker-compose exec attendance-server bash
```

---

## 🔧 トラブルシューティング

### Docker Desktopが起動していない場合

```
error during connect: The system cannot find the file specified.
```

**解決方法:**
1. Docker Desktopを起動してください
2. Docker Desktopが完全に起動するまで待機（タスクトレイのアイコンが安定するまで）

### ポート5000が既に使用されている場合

```bash
# 使用中のポートを確認（Windows）
netstat -ano | findstr :5000

# docker-compose.ymlの環境変数でポートを変更
# SERVER_PORT=8080 などに変更
```

### ビルドエラーが発生した場合

```bash
# キャッシュなしで再ビルド
docker-compose build --no-cache

# 既存のコンテナとイメージを削除してから再ビルド
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### データベースファイルが見つからない場合

```
Database file not found: /data/attendance.db
```

**解決方法:**
1. `server/data` ディレクトリが存在するか確認
2. 存在しない場合は作成: `mkdir server\data`
3. コンテナを再起動

---

## 📝 設定の変更

環境変数は `docker-compose.yml` の `environment` セクションで変更できます：

```yaml
environment:
  - SERVER_PORT=5000
  - CHATTERING_THRESHOLD=10
  - DEFAULT_SEARCH_LIMIT=100
```

変更後は再起動が必要です：
```bash
docker-compose down
docker-compose up -d
```

---

## 🎯 動作確認

起動後、以下のエンドポイントで動作確認できます：

- **ヘルスチェック**: http://localhost:5000/api/health
- **統計情報**: http://localhost:5000/api/stats
- **トップページ**: http://localhost:5000
- **検索ページ**: http://localhost:5000/search

