# 🚨 打刻システム - 試行錯誤とトラブルシューティング記録

**作成日**: 2025年10月23日  
**最終更新**: 2025年11月1日  
**対象システム**: 勤怠スケジュール検索システム  
**開発環境**: Docker + Flask + SQLite

---

## 📋 概要

本ドキュメントは、打刻システムの開発過程で発生した問題と解決策を記録し、同様の問題を防ぐためのガイドとして作成されました。

### 🎯 主な問題と解決策

1. **WebUI変更が反映されない問題** ⭐ 重要度: 高
2. **JavaScript修正が無効になる問題** ⭐ 新規追加: 2025/11/01
3. **データベーススキーマの不整合問題**
4. **Dockerコンテナでのファイルマウント問題**

---

## 🔥 問題1: WebUI変更が反映されない

### 📊 問題の詳細
- **現象**: `check.html`や他のテンプレートファイルを更新してもブラウザで変更が表示されない
- **発生頻度**: 開発中に頻繁に発生
- **影響範囲**: フロントエンド全体
- **重要度**: 🔥🔥🔥 開発効率に直結

### 🔍 根本原因の分析
1. **Dockerイメージのキャッシュ**: ビルド時にファイルが固定される
2. **ブラウザキャッシュ**: HTML/CSS/JSファイルがクライアント側でキャッシュされる
3. **ファイル同期の遅延**: マウント設定の問題
4. **複数レイヤーのキャッシュ**: Docker + ブラウザの2重キャッシュ

### ✅ 段階的解決策

#### **レベル1: ブラウザキャッシュ対策**
```html
<!-- HTMLヘッダーに追加 -->
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
```

#### **レベル2: 強制リロード**
```bash
# ブラウザ操作
Ctrl + F5 (Windows)
Cmd + Shift + R (Mac)
```

#### **レベル3: Dockerコンテナ再起動**
```bash
docker restart attendance-server
```

#### **レベル4: 完全イメージ再構築**
```bash
docker-compose down
docker image rm server-attendance-server
docker-compose up -d --build
```

### 🎓 学んだ教訓
- **開発環境では必ずボリュームマウントを使用する**
- **ブラウザとDockerの2重キャッシュを意識する**
- **変更確認時は段階的にアプローチする**
- **緊急時用の完全クリーンアップスクリプトを用意する**

---

## 🔥 問題2: JavaScript修正が無効になる問題 ⭐ 新規追加

### 📊 問題の詳細
- **発生日**: 2025年11月1日
- **現象**: APIからデータは正常に取得できるが、ブラウザで結果が表示されない
- **根本原因**: 複数回の修正により`displayResults(data.data)`の誤った参照が発生
- **データベース**: 正常（打刻データ有り）
- **API**: 正常（JSON応答有り）
- **JavaScript**: データアクセス方法の不整合

### 🔍 詳細分析

#### **APIレスポンス構造**
```json
{
    "status": "success",
    "employee_id": 3652025,
    "employee_name": "藤原　敬史",
    "check_date": "2025-10-09",
    "attendance_records": [...],
    "schedule": {...}
}
```

#### **JavaScript実装の問題**
```javascript
// ❌ 間違い - data.dataは存在しない
if (response.ok && data.status === 'success') {
    displayResults(data.data);  // undefinedを渡している
}

// ✅ 正解 - dataを直接渡す
if (response.ok && data.status === 'success') {
    displayResults(data);  // 正しいデータオブジェクトを渡す
}
```

### ✅ 解決手順

#### **1. 問題特定のデバッグ手法**
```javascript
// 詳細なデバッグログを追加
console.log('[DEBUG] Response data:', data);
console.log('[DEBUG] data.employee_name:', data.employee_name);
console.log('[DEBUG] typeof data:', typeof data);
```

#### **2. 段階的修正**
1. **APIテスト**: `curl`でAPIが正常動作することを確認
2. **JavaScript修正**: データアクセス方法を修正
3. **デバッグログ強化**: try-catch文とエラーハンドリング追加
4. **ファイル同期確認**: Docker内でファイル変更が反映されていることを確認

#### **3. 予防策実装**
```javascript
// エラーハンドリング強化
function displayResults(data) {
    try {
        console.log('[DEBUG] displayResults called with:', data);
        
        // データ存在確認
        if (!data || typeof data !== 'object') {
            throw new Error('Invalid data object');
        }
        
        // 必須フィールド確認
        if (!data.employee_name) {
            throw new Error('employee_name is missing');
        }
        
        // 実際の処理...
        
    } catch (error) {
        console.error('[DEBUG] displayResults error:', error);
        // フォールバック処理
    }
}
```

### 🎓 学んだ教訓
- **複雑な修正時は段階的にコミットする**
- **APIとフロントエンドのデータ構造を明確に把握する**
- **デバッグログは初期から充実させる**
- **重要な変更前には動作テストを実行する**

---

## 🔥 問題3: データベーススキーマの不整合

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

## 🔥 問題4: Dockerでのファイル同期

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
  - ./server.py:/app/server.py                      # コード同期
  - ./api.py:/app/api.py                           # API同期
  - ./utils.py:/app/utils.py                       # ユーティリティ同期
  - ./config.py:/app/config.py                     # 設定同期
  - ./database.py:/app/database.py                 # データベース同期
```

### 🎓 学んだ教訓
- **開発環境では動的ファイルはマウント、静的ファイルはCOPYを使い分ける**
- **本番環境では全ファイルをイメージに含める**
- **docker-compose.ymlを開発用と本番用で分ける**

---

## 🛠️ 推奨される開発フロー

### 1. **ファイル変更時の新しい手順** 🆕

#### **Python/APIファイル変更時**
```bash
# 1. ファイル編集
# 2. 変更確認
docker exec attendance-server grep -n "変更内容" /app/api.py

# 3. サーバー再起動
docker restart attendance-server

# 4. 動作確認
curl http://192.168.11.24:5000/api/health
```

#### **HTML/JavaScript変更時** 🆕
```bash
# 1. ファイル編集
# 2. マウント確認
docker exec attendance-server ls -la /app/templates/

# 3. ブラウザ強制リロード
# Ctrl + F5

# 4. 開発者ツールでエラー確認
# F12 → Console タブ
```

### 2. **トラブル発生時の診断フロー** 🆕

```bash
# Step 1: 基本確認
curl http://192.168.11.24:5000/api/health

# Step 2: ファイル同期確認
docker exec attendance-server ls -la /app/templates/
docker exec attendance-server head -10 /app/templates/check.html

# Step 3: JavaScript確認（ブラウザ）
# F12 → Console → エラーメッセージ確認

# Step 4: 段階的復旧
# Level 1: ブラウザ強制リロード
# Level 2: docker restart attendance-server
# Level 3: docker-compose down && docker-compose up -d --build
```

### 3. **デバッグ用コマンド集** 🆕

```bash
# コンテナ内のファイル確認
docker exec attendance-server ls -la /app/templates/

# リアルタイムログ監視
docker logs attendance-server -f

# API動作テスト
curl -s "http://192.168.11.24:5000/api/attendance_check?employee_id=3652025&check_date=2025-10-09" | python -m json.tool

# JavaScript構文チェック（コンテナ内）
docker exec attendance-server node -c /app/templates/check.html  # 要Node.js

# データベース内容確認
docker exec attendance-server sqlite3 /data/attendance.db "SELECT COUNT(*) FROM attendance WHERE idm='100009';"
```

---

## 📈 パフォーマンス改善ポイント

### 1. **データベース最適化**
- インデックスの適切な設定
- クエリの最適化
- 定期的なVACUUM実行

### 2. **Docker最適化**
- マルチステージビルドの活用
- 不要なファイルの除外（.dockerignore）
- イメージサイズの最小化

### 3. **フロントエンド最適化** 🆕
- JavaScript非同期処理の適切な実装
- エラーハンドリングの強化
- ユーザビリティ向上（ローディング表示等）

---

## 🚨 よくある落とし穴と回避策

### 1. **ブラウザキャッシュ vs サーバーキャッシュ**
- **症状**: 変更が反映されない
- **確認方法**: `curl`で直接APIを叩く
- **対策**: HTTPヘッダーでキャッシュ制御 + 強制リロード

### 2. **JavaScript構文エラー** 🆕
- **症状**: ページが動作しない、コンソールにエラー
- **確認方法**: F12 → Console でエラーメッセージ確認
- **対策**: try-catchブロック + 詳細なデバッグログ

### 3. **APIレスポンス構造の変更** 🆕
- **症状**: データは取得できるが表示されない
- **確認方法**: `curl`でAPIレスポンス構造を確認
- **対策**: フロントエンドとバックエンドのデータ契約を明確化

### 4. **ファイルエンコーディング問題**
- **症状**: 文字化けや読み込みエラー
- **対策**: UTF-8 BOMなしで統一

### 5. **ポート競合**
- **症状**: コンテナが起動しない
- **確認**: `netstat -ano | findstr :5000`
- **対策**: 別ポートを使用または競合プロセス終了

---

## 📚 関連ドキュメント

- [Docker開発環境完全ガイド](./DOCKER_DEVELOPMENT_COMPLETE_GUIDE.md) 🆕
- [Docker設定ガイド](./DOCKER_SETUP_GUIDE.md)
- [AI向け開発ガイド](./AI_DEVELOPMENT_GUIDE.md)
- [システム概要](./SYSTEM_OVERVIEW.md)

---

## 🔄 今後の改善点

### 短期的改善（1週間以内）
- [ ] 自動テストスクリプトの作成
- [ ] ファイル変更監視スクリプトの導入
- [ ] エラーログ改善

### 中期的改善（1ヶ月以内）
- [ ] CI/CDパイプライン構築
- [ ] 本番環境用Docker設定分離
- [ ] パフォーマンス監視ツール導入

### 長期的改善（3ヶ月以内）
- [ ] マイクロサービス化検討
- [ ] セキュリティ強化
- [ ] スケーラビリティ向上

---

**作成者**: GitHub Copilot  
**最終更新**: 2025年11月1日  
**次回レビュー**: 2025年12月1日

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