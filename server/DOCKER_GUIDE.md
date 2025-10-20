# 打刻システム - Docker起動ガイド

## 📦 Docker版の特徴

- ✅ Pythonやパッケージのインストール不要
- ✅ 環境の違いによるトラブルを回避
- ✅ 簡単に起動・停止
- ✅ データベースは永続化（コンテナ削除しても残る）

---

## 🚀 クイックスタート

### 必要なもの
- Docker Desktop（インストール済み）
- サーバーファイル一式

### ファイル配置

以下のフォルダにサーバーファイルを配置：
```
C:\Users\take_me_hospital\Desktop\N100\
├── Dockerfile
├── docker-compose.yml
├── server.py
├── requirements_server.txt
├── templates/
│   ├── index.html
│   └── search.html
├── start_docker.bat
├── stop_docker.bat
└── data/ (自動作成)
```

---

## 📝 起動手順

### 方法1: バッチファイルで起動（簡単）

```cmd
# サーバーディレクトリに移動
cd C:\Users\take_me_hospital\Desktop\N100

# Docker起動
start_docker.bat をダブルクリック
```

### 方法2: コマンドで起動

```cmd
# サーバーディレクトリに移動
cd C:\Users\take_me_hospital\Desktop\N100

# 初回: イメージをビルド
docker-compose build

# サーバー起動（バックグラウンド）
docker-compose up -d

# ログ確認
docker-compose logs -f
```

---

## 🌐 アクセス

サーバーが起動したら、ブラウザで以下にアクセス：

```
http://192.168.1.31:5000
```

または

```
http://localhost:5000
```

---

## 🔄 Docker コマンド一覧

### サーバー起動
```bash
docker-compose up -d
```

### サーバー停止
```bash
docker-compose down
```

### ログ確認（リアルタイム）
```bash
docker-compose logs -f
```

### コンテナ状態確認
```bash
docker-compose ps
```

### コンテナ内に入る
```bash
docker-compose exec attendance-server bash
```

### イメージ再ビルド（コード変更時）
```bash
docker-compose build --no-cache
docker-compose up -d
```

### すべて削除（データベースは残る）
```bash
docker-compose down
docker rmi $(docker images -q attendance-server)
```

---

## 📊 データ永続化

### データベースの保存場所

```
C:\Users\take_me_hospital\Desktop\N100\attendance.db
```

このファイルはコンテナを削除しても残ります。

### バックアップ方法

```cmd
# データベースをバックアップ
copy attendance.db attendance_backup_%date:~0,4%%date:~5,2%%date:~8,2%.db
```

### データベースの復元

```cmd
# バックアップから復元
copy attendance_backup_YYYYMMDD.db attendance.db

# Docker再起動
docker-compose restart
```

---

## 🔧 カスタマイズ

### ポート番号の変更

`docker-compose.yml` を編集：

```yaml
services:
  attendance-server:
    ports:
      - "5001:5000"  # 左側を変更（5001に変更した例）
```

変更後：
```bash
docker-compose down
docker-compose up -d
```

### タイムゾーンの変更

`docker-compose.yml` を編集：

```yaml
environment:
  - TZ=America/New_York  # 例: ニューヨーク
```

---

## 🐛 トラブルシューティング

### ❌ ポート5000が既に使用されている

**エラーメッセージ:**
```
Error: Bind for 0.0.0.0:5000 failed: port is already allocated
```

**解決策1: 使用中のプロセスを確認**
```cmd
netstat -ano | findstr :5000
```

**解決策2: ポート番号を変更**
`docker-compose.yml` でポート番号を変更（上記参照）

---

### ❌ Docker Desktopが起動していない

**エラーメッセージ:**
```
Cannot connect to the Docker daemon
```

**解決策:**
1. Docker Desktopを起動
2. タスクトレイのDockerアイコンが緑色になるまで待つ
3. 再度 `docker-compose up -d` を実行

---

### ❌ コンテナが起動しない

**ログを確認:**
```bash
docker-compose logs
```

**コンテナを再作成:**
```bash
docker-compose down
docker-compose up -d --force-recreate
```

---

### ❌ データベースファイルが見つからない

**確認:**
```cmd
dir attendance.db
```

**存在しない場合:**
- 初回起動時に自動作成されます
- ブラウザでアクセスして動作確認してください

---

### ❌ イメージのビルドエラー

**キャッシュをクリアして再ビルド:**
```bash
docker-compose build --no-cache
docker-compose up -d
```

---

## 📈 パフォーマンス監視

### リソース使用状況の確認

```bash
docker stats attendance-server
```

出力例:
```
CONTAINER ID   NAME                CPU %   MEM USAGE / LIMIT
abc123def456   attendance-server   0.5%    45MiB / 2GiB
```

---

## 🔄 アップデート手順

### サーバーコードを更新したとき

```bash
# 1. コンテナを停止
docker-compose down

# 2. イメージを再ビルド
docker-compose build

# 3. 再起動
docker-compose up -d

# 4. ログ確認
docker-compose logs -f
```

---

## 🌐 外部からのアクセス設定

### Windowsファイアウォールの設定

```cmd
# PowerShellを管理者権限で実行
New-NetFirewallRule -DisplayName "Attendance Server" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

### ルーターのポートフォワーディング（任意）

外部ネットワークからアクセスしたい場合：
1. ルーターの設定画面にアクセス
2. ポートフォワーディング設定
3. 外部ポート: 5000 → 内部IP: 192.168.1.31:5000

---

## 📊 システム要件

### 最小要件
- CPU: 1コア以上
- RAM: 512MB以上
- ディスク: 1GB以上の空き容量

### 推奨環境
- CPU: 2コア以上
- RAM: 1GB以上
- ディスク: 5GB以上の空き容量

---

## 🔐 セキュリティ

### 本番環境での推奨設定

1. **ファイアウォール設定**
   - 信頼できるIPのみ許可

2. **HTTPS化**
   - リバースプロキシ（nginx）の追加
   - SSL証明書の設定

3. **認証の追加**
   - Basic認証
   - トークン認証

---

## 💡 Tips

### バックグラウンドで常時起動

```yaml
# docker-compose.yml
services:
  attendance-server:
    restart: always  # Dockerが起動すると自動的に起動
```

### ログローテーション

```bash
# 古いログを削除
docker-compose logs --tail=1000 > logs_backup.txt
docker-compose restart
```

---

## 📝 比較: Docker版 vs 通常版

| 項目 | Docker版 | 通常版 |
|------|---------|--------|
| セットアップ | 簡単 | やや複雑 |
| 依存関係 | Dockerのみ | Python + パッケージ |
| ポータビリティ | 高い | 環境依存 |
| 起動速度 | やや遅い | 速い |
| リソース使用量 | やや多い | 少ない |
| トラブル対応 | 簡単 | やや複雑 |

---

## ✅ チェックリスト

### 初回セットアップ

- [ ] Docker Desktopがインストールされている
- [ ] Docker Desktopが起動している
- [ ] ファイルが正しく配置されている
- [ ] `docker-compose build` が成功する
- [ ] `docker-compose up -d` が成功する
- [ ] ブラウザでアクセスできる
- [ ] クライアントから打刻テストが成功する

### 日次運用

- [ ] `docker-compose up -d` でサーバー起動
- [ ] ブラウザで動作確認
- [ ] クライアントから打刻テスト
- [ ] ログにエラーがないか確認
- [ ] 終了時は `docker-compose down` （任意）

---

## 🆘 サポート

問題が発生した場合：

1. **ログを確認**
   ```bash
   docker-compose logs
   ```

2. **コンテナ状態を確認**
   ```bash
   docker-compose ps
   ```

3. **Dockerの再起動**
   - Docker Desktopを再起動
   - `docker-compose restart`

4. **クリーンビルド**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

---

**Docker版のセットアップ完了！** 🐳🎉

`start_docker.bat` をダブルクリックするだけで起動できます。

