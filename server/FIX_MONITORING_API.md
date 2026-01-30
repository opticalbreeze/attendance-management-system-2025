# モニタリングAPI 404エラー修正

## 問題
`/api/monitoring/stats` にアクセスすると404エラーが発生していました。

## 原因
`server.py`でモニタリングAPIのBlueprintを登録するコードが抜けていました。

## 修正内容
`server.py`の`main()`関数内に、以下のコードを追加しました：

```python
# モニタリングAPI（拡張機能）
if MONITORING_API_AVAILABLE:
    try:
        app.register_blueprint(monitoring_bp)
        logger.info("モニタリングAPIを有効化しました")
    except Exception as e:
        logger.error(f"モニタリングAPIの登録に失敗しました: {e}", exc_info=True)
```

## 次のステップ

1. **コンテナを再起動**:
   ```powershell
   cd C:\Users\take_me_hospital\attendance\work_attend_server\server
   docker compose -f docker-compose.dev.yml restart
   ```

2. **サーバーログを確認**:
   ```powershell
   docker logs attendance-server-dev --tail 50
   ```
   
   「モニタリングAPIを有効化しました」というメッセージが表示されることを確認してください。

3. **APIをテスト**:
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:5001/api/monitoring/stats?hours=24" -Method GET
   ```

   期待される応答:
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

## 確認事項

- [ ] コンテナが正常に再起動した
- [ ] サーバーログに「モニタリングAPIを有効化しました」が表示される
- [ ] `/api/monitoring/stats` が200 OKを返す
- [ ] `/api/monitoring/errors` が200 OKを返す
- [ ] `/api/monitoring/warnings` が200 OKを返す
