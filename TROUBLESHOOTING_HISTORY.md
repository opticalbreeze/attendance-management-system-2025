# 🚨 打刻システム - 試行錯誤とトラブルシューティング記録

**作成日**: 2025年10月23日  
**対象システム**: 勤怠スケジュール検索システム  
**開発環境**: Docker + Flask + SQLite

---

## 📋 概要

本ドキュメントは、打刻システムの開発過程で発生した問題と解決策を記録し、同様の問題を防ぐためのガイドとして作成されました。

### 🎯 主な問題と解決策

1. **WebUI変更が反映されない問題**
2. **データベーススキーマの不整合問題**
3. **Dockerコンテナでのファイルマウント問題**

---

## 🔥 問題1: WebUI変更が反映されない

### 📊 問題の詳細
- **現象**: `search.html`を「勤怠スケジュール検索」に更新したが、ブラウザで古い「打刻データ検索」が表示される
- **発生期間**: 2025年10月23日（PC再起動後）
- **影響範囲**: フロントエンド全体

### 🔍 試行した解決策（失敗）
1. ✗ サーバー再起動（10回以上）
2. ✗ プロセス強制終了・再起動
3. ✗ キャッシュバスティングパラメータ追加
4. ✗ Flask設定でテンプレート自動リロード有効化
5. ✗ ファイル文字エンコーディング変更
6. ✗ 古いファイル削除・新ファイル作成
7. ✗ HTTPレスポンスの直接確認

### ✅ 最終的な解決策
**根本原因**: Dockerコンテナが古いテンプレートファイルを使用していた

**解決手順**:
1. `docker-compose.yml`にテンプレートディレクトリのマウントを追加
2. サーバーコードもマウントして最新版を反映
3. コンテナを完全に再構築

```yaml
# docker-compose.yml の修正
volumes:
  - ./data:/data
  - ./templates:/app/templates          # 追加
  - ./server_improved.py:/app/server_improved.py  # 追加
```

### 🎓 学んだ教訓
- **Dockerでの開発では、コードとテンプレートの両方をマウントする**
- **イメージビルド時のCOPYとランタイムのマウントを混同しない**
- **キャッシュ問題と実際のファイル同期問題を区別する**

---

## 🔥 問題2: データベーススキーマの不整合

### 📊 問題の詳細
- **エラーメッセージ**: `no such column: clock_in_time`
- **根本原因**: データベースの`attend_schedule`テーブルが古いスキーマ構造
- **データ件数**: 330件（移行対象）

### 🔍 スキーマの差異

#### 旧スキーマ
```sql
CREATE TABLE attend_schedule (
    id INTEGER PRIMARY KEY,
    sheet_number TEXT,
    employee_id TEXT,
    employee_name TEXT,
    work_date DATE,
    work_type TEXT,
    start_time TIME,      -- 旧フィールド
    end_time TIME,        -- 旧フィールド
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### 新スキーマ
```sql
CREATE TABLE attend_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    work_date TEXT NOT NULL,
    clock_in_time TEXT,     -- 新フィールド
    clock_out_time TEXT,    -- 新フィールド
    break_start_time TEXT,  -- 新フィールド
    break_end_time TEXT,    -- 新フィールド
    overtime_hours REAL DEFAULT 0,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### ✅ 解決策: データ移行スクリプト

**手順**:
1. 既存データを全件取得してバックアップ
2. 旧テーブルを`attend_schedule_old`にリネーム
3. 新スキーマでテーブルを再作成
4. データを新フィールドにマップして移行
5. インデックスを再作成

**移行結果**: 330件 → 330件（100%成功）

### 🎓 学んだ教訓
- **スキーマ変更前には既存データの構造を必ず確認する**
- **本格的な移行前にテストデータで動作確認する**
- **旧データは即座に削除せず、しばらく保持する**

---

## 🔥 問題3: Dockerでのファイル同期

### 📊 問題の詳細
- **現象**: ローカルファイルを更新してもコンテナ内で反映されない
- **影響**: 開発効率の大幅な低下

### 🔍 原因分析
1. **Dockerfileでのファイルコピー**: ビルド時に固定
2. **docker-composeのボリュームマウント**: ランタイム時に動的

### ✅ 解決策: 適切なマウント設定

```dockerfile
# Dockerfile - 基本構造のみ
FROM python:3.11-slim
WORKDIR /app
COPY requirements_server.txt .
RUN pip install -r requirements_server.txt
# テンプレートとコードはマウントで対応（COPYしない）
```

```yaml
# docker-compose.yml - 開発用設定
volumes:
  - ./data:/data                                    # データ永続化
  - ./templates:/app/templates                      # テンプレート同期
  - ./server_improved.py:/app/server_improved.py   # コード同期
```

### 🎓 学んだ教訓
- **開発環境では動的ファイルはマウント、静的ファイルはCOPYを使い分ける**
- **本番環境では全ファイルをイメージに含める**
- **docker-compose.ymlを開発用と本番用で分ける**

---

## 🛠️ 推奨される開発フロー

### 1. WebUI変更時の手順
```bash
# 1. ファイル編集後
# 2. マウント設定確認
docker-compose config

# 3. コンテナ再起動（必要に応じて）
docker restart attendance-server

# 4. 動作確認
curl http://localhost:5000/search
```

### 2. データベーススキーマ変更時の手順
```bash
# 1. 現在のスキーマを確認
docker exec attendance-server python -c "import sqlite3; conn = sqlite3.connect('/data/attendance.db'); cursor = conn.cursor(); cursor.execute('PRAGMA table_info(attend_schedule)'); print(cursor.fetchall())"

# 2. バックアップ作成
docker cp attendance-server:/data/attendance.db ./backup_$(date +%Y%m%d_%H%M%S).db

# 3. 移行スクリプト実行
docker exec attendance-server python /app/migrate_db.py

# 4. 動作確認
curl "http://localhost:5000/api/search?employee_id=2952089&search_month=2025/10"
```

### 3. デバッグ用コマンド集
```bash
# コンテナ内のファイル確認
docker exec attendance-server ls -la /app/templates/

# データベース内容確認
docker exec attendance-server python /app/debug_db.py

# ログ確認
docker logs attendance-server --tail=50
```

---

## 📈 パフォーマンス改善ポイント

### 1. データベース最適化
- インデックスの適切な設定
- クエリの最適化
- 定期的なVACUUM実行

### 2. Docker最適化
- マルチステージビルドの活用
- 不要なファイルの除外（.dockerignore）
- イメージサイズの最小化

---

## 🚨 よくある落とし穴と回避策

### 1. ブラウザキャッシュ vs サーバーキャッシュ
- **症状**: 変更が反映されない
- **確認方法**: `curl`で直接APIを叩く
- **対策**: HTTPヘッダーでキャッシュ制御

### 2. ファイルエンコーディング問題
- **症状**: 文字化けや読み込みエラー
- **対策**: UTF-8 BOMなしで統一

### 3. ポート競合
- **症状**: コンテナが起動しない
- **確認**: `netstat -ano | findstr :5000`
- **対策**: 別ポートを使用または競合プロセス終了

---

## 📚 関連ドキュメント

- [Docker設定ガイド](./DOCKER_SETUP_GUIDE.md)
- [AI向け開発ガイド](./AI_DEVELOPMENT_GUIDE.md)
- [API仕様書](./API_SPECIFICATION.md)

---

**作成者**: GitHub Copilot  
**最終更新**: 2025年10月23日