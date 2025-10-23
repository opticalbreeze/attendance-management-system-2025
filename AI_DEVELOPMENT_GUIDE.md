# 🤖 AI向け開発ガイド - 打刻システム

**対象**: AI開発アシスタント（GitHub Copilot等）  
**目的**: 同様の問題を繰り返さないための開発指針  
**システム**: Flask + Docker + SQLite による勤怠管理システム

---

## 🎯 重要な原則

### 1. 🐳 Docker環境での開発時の鉄則

#### ✅ DO (推奨する行動)
```yaml
# docker-compose.yml - 開発環境設定
services:
  app:
    volumes:
      # 動的ファイルは必ずマウントする
      - ./templates:/app/templates
      - ./static:/app/static  
      - ./server.py:/app/server.py
      # データは永続化
      - ./data:/data
```

#### ❌ DON'T (避けるべき行動)
```dockerfile
# Dockerfile で動的ファイルをCOPY（開発時は❌）
COPY templates/ templates/  # ← 開発時は更新されない
COPY server.py .           # ← 開発時は更新されない
```

**理由**: COPYはビルド時に固定される。開発中は変更が反映されない。

---

### 2. 🗄️ データベーススキーマ変更の手順

#### ⚠️ 必須チェック項目
1. **既存データの確認**
```python
# 必ず実行: 現在のテーブル構造を確認
cursor.execute("PRAGMA table_info(table_name)")
print(cursor.fetchall())
```

2. **データ件数の把握**
```python
# 移行対象データの件数を確認
cursor.execute("SELECT COUNT(*) FROM table_name")
print(f"移行対象: {cursor.fetchone()[0]}件")
```

3. **バックアップの作成**
```bash
# 移行前に必ずバックアップ
docker cp container:/data/database.db ./backup_$(date +%Y%m%d_%H%M%S).db
```

#### 🔄 安全な移行パターン
```python
def safe_migration():
    # 1. 既存テーブルをリネーム（削除しない）
    cursor.execute("ALTER TABLE old_table RENAME TO old_table_backup")
    
    # 2. 新しいスキーマでテーブル作成
    cursor.execute("CREATE TABLE new_table (...)")
    
    # 3. データを移行（エラーハンドリング付き）
    for row in old_data:
        try:
            cursor.execute("INSERT INTO new_table ...", mapped_data)
        except Exception as e:
            print(f"Migration error for row {row[0]}: {e}")
            continue
    
    # 4. インデックス再作成
    cursor.execute("CREATE INDEX ...")
```

---

### 3. 🌐 WebUI変更時の確認手順

#### 📝 変更が反映されない場合のチェックリスト
```bash
# 1. ファイルがコンテナ内に正しく存在するか
docker exec container ls -la /app/templates/

# 2. ファイル内容が更新されているか  
docker exec container head -5 /app/templates/search.html

# 3. HTTPレスポンスを直接確認（ブラウザキャッシュを排除）
curl -H "Cache-Control: no-cache" http://localhost:5000/search

# 4. コンテナ再起動
docker restart container
```

#### 🔧 Flask設定の確認事項
```python
# テンプレート自動リロードの設定
app.config['TEMPLATES_AUTO_RELOAD'] = True

# キャッシュ制御ヘッダーの設定
@app.after_request
def after_request(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
```

---

## 🚨 よくある問題と解決パターン

### 問題1: "no such column" エラー
```
sqlite3.OperationalError: no such column: new_column_name
```

**原因**: データベーススキーマが古い  
**解決**: データ移行スクリプトの実行

**予防策**:
```python
# スキーマ変更時は必ずバージョン管理
def check_schema_version():
    try:
        cursor.execute("SELECT version FROM schema_version")
        return cursor.fetchone()[0]
    except:
        return 0  # 初期バージョン

def migrate_if_needed():
    current_version = check_schema_version()
    if current_version < REQUIRED_VERSION:
        run_migration(current_version)
```

### 問題2: WebUI変更が反映されない
```
期待: 新しいタイトル「勤怠スケジュール検索」
実際: 古いタイトル「打刻データ検索」
```

**原因**: Dockerコンテナが古いファイルを使用  
**解決**: docker-compose.ymlにマウント設定追加

**予防策**:
```bash
# 変更後は必ず確認
echo "=== ローカルファイル ==="
grep -n "title" templates/search.html

echo "=== コンテナ内ファイル ==="
docker exec container grep -n "title" /app/templates/search.html
```

### 問題3: データの不整合
```
データは存在するが検索結果が0件
```

**原因**: フィールド名の不一致  
**解決**: マッピング処理の追加

**予防策**:
```python
# APIレスポンス時にフィールドマッピングを確認
def safe_field_access(row, field_name, default=""):
    try:
        return row[field_name] if row[field_name] is not None else default
    except KeyError:
        print(f"Warning: Field '{field_name}' not found")
        return default
```

---

## 🔍 デバッグ支援ツール

### 1. データベース状態確認スクリプト
```python
# debug_db.py - データベースの状態を詳細表示
def debug_database():
    # テーブル一覧
    # スキーマ情報  
    # データ件数
    # サンプルデータ
```

### 2. Docker状態確認コマンド
```bash
# コンテナ状態確認
docker ps
docker logs container --tail=20

# マウント状態確認
docker inspect container | grep -A 10 "Mounts"

# ネットワーク確認
docker port container
```

### 3. API動作確認
```bash
# ヘルスチェック
curl http://localhost:5000/api/health

# 検索API
curl "http://localhost:5000/api/search?employee_id=123&search_month=2025/10"
```

---

## 📋 開発時のチェックリスト

### 🆕 新機能開発時
- [ ] 既存のデータベーススキーマを確認済み
- [ ] 必要に応じて移行スクリプトを作成済み
- [ ] docker-compose.ymlにマウント設定を追加済み
- [ ] テンプレートファイルがコンテナ内で更新されることを確認済み
- [ ] APIのレスポンス形式を確認済み

### 🔧 WebUI変更時  
- [ ] ローカルファイルとコンテナ内ファイルの同期を確認済み
- [ ] ブラウザキャッシュを無効化してテスト済み
- [ ] curlで直接HTTPレスポンスを確認済み
- [ ] 複数ブラウザでの動作を確認済み

### 🗄️ データベース変更時
- [ ] 現在のスキーマ構造を記録済み
- [ ] データのバックアップを作成済み
- [ ] 移行スクリプトをテストデータで検証済み
- [ ] 移行後のデータ整合性を確認済み
- [ ] 既存APIとの互換性を確認済み

---

## 🎨 コード品質ガイドライン

### Python/Flask
```python
# 良い例: エラーハンドリング付きのデータベースアクセス
def get_attendance_data(employee_id, search_month):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # パラメータバインディングを使用（SQLインジェクション対策）
        cursor.execute("""
            SELECT * FROM attend_schedule 
            WHERE employee_id = ? AND work_date BETWEEN ? AND ?
        """, (employee_id, start_date, end_date))
        
        results = cursor.fetchall()
        return {"status": "success", "results": results}
        
    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            conn.close()
```

### HTML/JavaScript
```html
<!-- 良い例: フォームバリデーション付き -->
<form id="search-form">
    <input type="text" id="employee-id" required 
           pattern="[A-Z0-9]+" title="英数字のみ">
    <input type="text" id="search-month" required 
           pattern="[0-9]{4}/[0-9]{1,2}" title="yyyy/mm形式">
    <button type="submit">検索</button>
</form>

<script>
document.getElementById('search-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // バリデーション
    const employeeId = document.getElementById('employee-id').value.trim();
    if (!employeeId) {
        showError('従業員IDを入力してください');
        return;
    }
    
    // API呼び出し（エラーハンドリング付き）
    try {
        const response = await fetch(`/api/search?employee_id=${employeeId}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            displayResults(data.results);
        } else {
            showError(data.message);
        }
    } catch (error) {
        showError('通信エラーが発生しました');
        console.error('API Error:', error);
    }
});
</script>
```

---

## 🚀 パフォーマンス最適化

### データベース
```sql
-- インデックスの適切な設定
CREATE INDEX idx_employee_work_date ON attend_schedule(employee_id, work_date);
CREATE INDEX idx_search_range ON attend_schedule(work_date, employee_id);

-- 定期的なメンテナンス  
PRAGMA optimize;
VACUUM;
```

### Docker
```dockerfile
# マルチステージビルドでイメージサイズ削減
FROM python:3.11-slim as builder
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
# 必要なファイルのみCOPY
```

---

## 📚 参考資料

### 公式ドキュメント
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [SQLite Documentation](https://sqlite.org/docs.html)

### 内部ドキュメント
- [TROUBLESHOOTING_HISTORY.md](./TROUBLESHOOTING_HISTORY.md) - 過去の問題と解決策
- [DOCKER_SETUP_GUIDE.md](./DOCKER_SETUP_GUIDE.md) - Docker環境構築ガイド
- [API_SPECIFICATION.md](./API_SPECIFICATION.md) - API仕様書

---

**重要**: このガイドは実際の開発で発生した問題をベースに作成されています。新しい問題が発生した場合は、このドキュメントを更新してください。

**最終更新**: 2025年10月23日  
**作成者**: GitHub Copilot