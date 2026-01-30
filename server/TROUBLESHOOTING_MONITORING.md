# モニタリングAPI トラブルシューティングガイド

## 問題: サーバーに接続できない

### 1. Docker Desktopの確認

**症状**: `curl: リモートサーバーに接続できません` または `Access is denied`

**解決策**:

1. **Docker Desktopが起動しているか確認**
   - Docker Desktopアプリケーションを起動
   - タスクバーのDockerアイコンを確認（緑色になっているか）

2. **Docker Desktopを起動**
   ```powershell
   # Docker Desktopのパスで起動
   Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
   
   # 30秒待ってから確認
   docker version
   ```

### 2. コンテナの状態確認

```powershell
# 開発環境（5001）のコンテナ状態を確認
cd C:\Users\take_me_hospital\attendance\work_attend_server\server
docker compose -f docker-compose.dev.yml ps

# 本番環境（5000）のコンテナ状態を確認
docker compose -f docker-compose.yml ps
```

**期待される出力**:
```
NAME                    STATUS
attendance-server-dev   Up
```

**問題がある場合**:
- `STATUS`が`Exited`の場合 → コンテナが停止しています
- コンテナが存在しない場合 → コンテナが作成されていません

### 3. コンテナの起動

```powershell
# 開発環境（5001）を起動
docker compose -f docker-compose.dev.yml up -d

# 本番環境（5000）を起動
docker compose -f docker-compose.yml up -d
```

### 4. サーバーログの確認

```powershell
# 開発環境（5001）のログを確認
docker compose -f docker-compose.dev.yml logs --tail=50

# エラーメッセージを確認
docker compose -f docker-compose.dev.yml logs | Select-String -Pattern "error|Error|ERROR" -Context 2
```

**よくあるエラー**:

1. **`ModuleNotFoundError: No module named 'api_monitoring'`**
   - **原因**: `api_monitoring.py`がマウントされていない
   - **解決策**: `docker-compose.dev.yml`で`api_monitoring.py`のマウントを確認

2. **`ImportError: cannot import name 'StructuredFormatter'`**
   - **原因**: `logger_config.py`のインポートエラー
   - **解決策**: コンテナを再起動して最新のコードを読み込む

3. **`Port 5001 is already allocated`**
   - **原因**: ポート5001が既に使用されている
   - **解決策**: 既存のコンテナを停止するか、別のポートを使用

### 5. コンテナの再起動

```powershell
# 開発環境（5001）を再起動
docker compose -f docker-compose.dev.yml restart

# 完全に再作成（コード変更を確実に反映）
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d --build
```

### 6. APIエンドポイントの確認

サーバーが起動したら、以下のコマンドでAPIが利用可能か確認：

```powershell
# PowerShellでInvoke-WebRequestを使用
Invoke-WebRequest -Uri "http://localhost:5001/api/health" -Method GET

# またはcurl（PowerShell 7以降）
curl http://localhost:5001/api/health

# モニタリングAPIの確認
Invoke-WebRequest -Uri "http://localhost:5001/api/monitoring/stats?hours=24" -Method GET
```

**期待される応答**:
```json
{
  "status": "success",
  "stats": {
    "total_errors": 0,
    "total_warnings": 0,
    ...
  }
}
```

### 7. ポートの確認

```powershell
# ポート5001が使用されているか確認
netstat -ano | findstr :5001

# ポート5000が使用されているか確認
netstat -ano | findstr :5000
```

### 8. ログディレクトリの確認

```powershell
# ログディレクトリが存在するか確認
Test-Path C:\Users\take_me_hospital\attendance\logs

# 存在しない場合は作成
New-Item -ItemType Directory -Path C:\Users\take_me_hospital\attendance\logs -Force
```

## よくある問題と解決策

### 問題1: api_monitoring.pyが見つからない

**症状**: `ModuleNotFoundError: No module named 'api_monitoring'`

**解決策**:
1. `api_monitoring.py`が`server/`ディレクトリに存在するか確認
2. `docker-compose.dev.yml`でマウントされているか確認
3. コンテナを再起動

### 問題2: StructuredFormatterのインポートエラー

**症状**: `ImportError: cannot import name 'StructuredFormatter'`

**解決策**:
1. `logger_config.py`に`StructuredFormatter`が定義されているか確認
2. コンテナを再起動して最新のコードを読み込む

### 問題3: ログファイルが作成されない

**症状**: APIは動作するが、ログファイルが作成されない

**解決策**:
1. ログディレクトリの権限を確認
2. Dockerコンテナ内でログディレクトリが作成できるか確認
3. 環境変数`ENABLE_ENHANCED_LOGGING=true`が設定されているか確認

## デバッグ手順

1. **Docker Desktopが起動しているか確認**
2. **コンテナが起動しているか確認** (`docker compose ps`)
3. **サーバーログを確認** (`docker compose logs`)
4. **APIエンドポイントをテスト** (`curl`または`Invoke-WebRequest`)
5. **エラーメッセージを確認**して上記の解決策を試す

## 次のステップ

問題が解決したら、以下を確認してください：

1. **モニタリングAPIが動作しているか**
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:5001/api/monitoring/stats?hours=24"
   ```

2. **ログファイルが作成されているか**
   ```powershell
   Get-ChildItem C:\Users\take_me_hospital\attendance\logs
   ```

3. **エラーログが記録されているか**
   ```powershell
   Get-Content C:\Users\take_me_hospital\attendance\logs\errors.jsonl -Tail 10
   ```
