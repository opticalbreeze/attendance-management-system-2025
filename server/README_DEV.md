# 勤怠管理システム - 開発環境

## 概要

本番環境と並行して稼働する開発環境です。本番のデータベースを共有しつつ、安全に新機能の開発・テストを行えます。

## 環境構成

```
本番環境  :5000 ←→ 共有DB ←→ 開発環境  :5001
production         ↓        development
                attendance.db
```

## 起動・停止

### 起動
```cmd
start_dev.bat
```
- URL: http://localhost:5001
- デバッグモード有効
- ホットリロード対応

### 停止
```cmd
stop_dev.bat
```

### ログ確認
```cmd
docker logs attendance-server-dev -f
```

## 開発環境の特徴

### ✅ 安全性
- 本番環境とは別コンテナ・別ポート
- データベースのみ共有（読み込み同期）
- 開発用ログが分離
- **テンプレート・静的ファイルが本番環境と完全分離**

### 🔧 開発機能
- Flask デバッグモード有効
- ファイル変更時の自動リロード
- 詳細エラーログ出力

### 📁 ファイル構成

```
server/
├── templates/          # 本番環境用（5000）- 変更禁止
├── static/             # 本番環境用（5000）- 変更禁止
├── templates_dev/      # 開発環境用（5001）- 開発時はこちらを編集
└── static_dev/         # 開発環境用（5001）- 開発時はこちらを編集
```

**重要**: 開発時は必ず`templates_dev/`と`static_dev/`を編集してください。本番環境（`templates/`と`static/`）は直接編集しないでください。

### 📊 今後の開発予定

#### お知らせ機能
- スケジュール vs 実績の差異検出
- 打刻漏れアラート
- 個人向け確認画面

#### 実装予定場所
- 新しいAPI: `/api/notifications`
- 新しい画面: `/notifications`
- カードリーダー連携強化

## 開発ワークフロー

### 📝 ファイル編集時の注意

1. **開発時**: `templates_dev/`と`static_dev/`を編集
   - 開発環境（5001）で即座に反映されます
   - 本番環境（5000）には影響しません

2. **本番反映時**: 検証完了後、本番環境にコピー
   ```cmd
   # 例: attendance_check.htmlを本番環境に反映
   xcopy /Y server\templates_dev\attendance_check.html server\templates\
   xcopy /Y server\static_dev\js\attendance-check.js server\static\js\
   ```

3. **本番環境の再起動**（必要に応じて）
   ```cmd
   docker restart attendance-server
   ```

### ⚠️ データベース共有
- **本番データを直接参照**するため、データ変更は慎重に
- **SELECT操作**中心の開発を推奨
- **INSERT/UPDATE**は十分テスト後に実施

### 🚫 本番影響回避
- 開発環境での大量データ処理は避ける
- 長時間のDB接続を避ける
- 本番時間帯（日中）の重い処理は避ける
- **本番環境のファイル（`templates/`と`static/`）は直接編集しない**

## トラブルシューティング

### ポート競合
```cmd
netstat -ano | findstr :5001
taskkill /PID <PID番号> /F
```

### Docker再構築
```cmd
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up --build -d
```