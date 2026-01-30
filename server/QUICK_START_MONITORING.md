# モニタリングシステム クイックスタートガイド

## 実装完了内容

Phase 1の実装が完了しました：

1. ✅ **構造化ログシステム**: `logger_config.py`に統合済み
2. ✅ **エラー・警告専用ログファイル**: 自動的に作成されます
3. ✅ **モニタリングAPI**: `api_monitoring.py`を登録済み
4. ✅ **Docker設定**: ログディレクトリのマウントを追加済み

## 使い方

### 1. ログディレクトリの作成

```bash
# プロジェクトルートで実行
mkdir -p logs
```

### 2. Dockerコンテナの再起動

```bash
# 開発環境（5001）
cd work_attend_server/server
docker compose -f docker-compose.dev.yml restart

# 本番環境（5000）
docker compose -f docker-compose.yml restart
```

### 3. モニタリングAPIの確認

#### エラー一覧を取得
```bash
curl http://localhost:5001/api/monitoring/errors?hours=24
```

#### 警告一覧を取得
```bash
curl http://localhost:5001/api/monitoring/warnings?hours=24
```

#### 統計情報を取得
```bash
curl http://localhost:5001/api/monitoring/stats?hours=24
```

### 4. ログファイルの確認

```bash
# エラーログ（JSON形式）
cat logs/errors.jsonl

# 警告ログ（JSON形式）
cat logs/warnings.jsonl

# 全ログ
cat logs/app.log
```

## ログの構造

### JSON形式のログエントリ例

```json
{
  "timestamp": "2026-01-27T12:34:56.789Z",
  "level": "ERROR",
  "logger": "attendance_check_service",
  "message": "打刻データの取得に失敗しました",
  "module": "attendance_check_service",
  "function": "check_attendance_vs_schedule",
  "line": 123,
  "category": "attendance",
  "severity": "high",
  "exception": {
    "type": "DatabaseError",
    "message": "Database connection failed",
    "traceback": "..."
  }
}
```

## コンテキスト付きログの使用例

```python
from logger_config import setup_logger, ContextLogger

# 通常のロガー
logger = setup_logger('my_module')
logger.info('通常のログメッセージ')

# コンテキスト付きロガー
context_logger = ContextLogger(logger, employee_id='12345', request_id='req-001')
context_logger.info('従業員の処理を開始')
context_logger.error('処理中にエラーが発生')
```

## 環境変数による制御

### 拡張ログ機能の有効/無効

```bash
# 有効化（デフォルト）
ENABLE_ENHANCED_LOGGING=true

# 無効化（従来のログ形式を使用）
ENABLE_ENHANCED_LOGGING=false
```

### ログレベルの設定

```bash
# 開発環境
LOG_LEVEL=DEBUG

# 本番環境
LOG_LEVEL=INFO
```

## トラブルシューティング

### ログファイルが作成されない

**原因**: ログディレクトリの権限問題

**解決策**:
```bash
# ログディレクトリの権限を確認
ls -la logs/

# 権限を設定（Linux/Mac）
chmod 755 logs/

# Windowsの場合、ディレクトリの作成権限を確認
```

### モニタリングAPIが404エラー

**原因**: Blueprintが登録されていない、または`api_monitoring.py`が見つからない

**解決策**:
1. `api_monitoring.py`が`server/`ディレクトリに存在するか確認
2. Dockerコンテナを再起動
3. サーバーログでエラーメッセージを確認

### JSON形式のログが読みにくい

**解決策**: 開発環境では自動的に読みやすい形式が使用されます。本番環境でも読みやすい形式を使用する場合は、`ENABLE_ENHANCED_LOGGING=false`を設定してください。

## 次のステップ

1. **動作確認**: エラーを発生させて、ログファイルが正しく作成されるか確認
2. **モニタリングAPIのテスト**: ブラウザまたはcurlでAPIを呼び出して動作確認
3. **Phase 2の実装**: ブラウザデバッグパネルとエラー統計ダッシュボードの実装

## 参考資料

- `ARCHITECTURE_IMPROVEMENT_PROPOSAL.md`: 詳細な提案書
- `IMPLEMENTATION_GUIDE.md`: 実装ガイド
- `logger_config.py`: 拡張ログ設定モジュール
- `api_monitoring.py`: モニタリングAPI
