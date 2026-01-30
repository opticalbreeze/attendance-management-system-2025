# サーバー状態確認ガイド

## サーバーが起動していない場合の確認手順

### 1. ブラウザで確認

ブラウザで以下のURLにアクセスして、サーバーが起動しているか確認：

```
http://localhost:5001/
http://localhost:5001/api/health
```

### 2. サーバーログの確認方法

Docker Desktopが起動している場合：

```powershell
# コンテナのログを確認（最新50行）
docker logs attendance-server-dev --tail 50

# エラーメッセージを検索
docker logs attendance-server-dev 2>&1 | Select-String -Pattern "error|Error|ERROR|Exception" -Context 2
```

### 3. コンテナの状態確認

```powershell
# コンテナが実行中か確認
docker ps -a --filter "name=attendance-server-dev"
```

**期待される出力**:
```
CONTAINER ID   IMAGE                    STATUS
xxxxx          attendance-server-dev    Up X minutes
```

**問題がある場合**:
- `STATUS`が`Exited` → コンテナが停止しています
- コンテナが存在しない → コンテナが作成されていません

### 4. コンテナを再起動

```powershell
cd C:\Users\take_me_hospital\attendance\work_attend_server\server

# コンテナを停止して再起動
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d

# ログをリアルタイムで確認
docker compose -f docker-compose.dev.yml logs -f
```

### 5. よくある起動エラー

#### エラー1: `ModuleNotFoundError: No module named 'api_monitoring'`

**原因**: `api_monitoring.py`がマウントされていない、またはファイルが存在しない

**解決策**:
1. `api_monitoring.py`が`server/`ディレクトリに存在するか確認
2. `docker-compose.dev.yml`でマウントされているか確認
3. コンテナを再作成

#### エラー2: `ImportError: cannot import name 'StructuredFormatter'`

**原因**: `logger_config.py`のインポートエラー

**解決策**:
1. `logger_config.py`に`StructuredFormatter`クラスが定義されているか確認
2. コンテナを再起動

#### エラー3: `Port 5001 is already allocated`

**原因**: ポート5001が既に使用されている

**解決策**:
```powershell
# ポート5001を使用しているプロセスを確認
netstat -ano | findstr :5001

# プロセスを終了（PIDを確認してから）
taskkill /PID <PID> /F
```

### 6. サーバーが起動したか確認

サーバーが正常に起動すると、以下のようなログが表示されます：

```
打刻システム - サーバー（改善版）
================================================================================
データベース: /app/data/attendance.db
サーバー起動: http://0.0.0.0:5000
...
モニタリングAPIを有効化しました
 * Running on http://0.0.0.0:5000
```

### 7. APIエンドポイントのテスト

サーバーが起動したら、以下のコマンドでAPIをテスト：

```powershell
# ヘルスチェック
Invoke-RestMethod -Uri "http://localhost:5001/api/health" -Method GET

# モニタリングAPI（統計情報）
Invoke-RestMethod -Uri "http://localhost:5001/api/monitoring/stats?hours=24" -Method GET
```

**期待される応答**:
```json
{
  "status": "success",
  "stats": {
    "total_errors": 0,
    "total_warnings": 0,
    "by_category": {},
    "by_severity": {},
    "recent_errors": [],
    "error_trend": []
  }
}
```

## トラブルシューティング

### Docker Desktopが起動しない

1. Docker Desktopを管理者権限で起動
2. Windowsの再起動を試す
3. Docker Desktopを再インストール

### コンテナがすぐに停止する

1. ログを確認してエラーメッセージを特定
2. エラーメッセージに基づいて修正
3. コンテナを再作成

### ポートが使用できない

1. 他のアプリケーションがポートを使用していないか確認
2. 別のポートを使用する（`docker-compose.dev.yml`で変更）
