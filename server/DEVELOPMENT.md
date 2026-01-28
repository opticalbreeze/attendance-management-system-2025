# 開発環境セットアップガイド

## 🚀 開発環境の起動

### 1. 開発サーバー起動
```bash
# Windows
start_dev_server.bat

# 手動起動の場合
docker-compose -f docker-compose-dev.yml up --build -d
```

### 2. アクセス先
- **開発環境**: http://localhost:5001
- **本番環境**: http://localhost:5000 (そのまま稼働)

### 3. 停止
```bash
# Windows
stop_dev_server.bat

# 手動停止の場合
docker-compose -f docker-compose-dev.yml down
```

## 📊 データベース共有

- **場所**: `c:\Users\take_me_hospital\attendance\data\attendance.db`
- **共有方式**: 本番と開発で同じDBファイルを使用
- **安全性**: 開発環境では読み取り専用操作を推奨

## 📝 ログ確認

```bash
# 開発環境のログを確認
docker logs attendance-server-dev -f

# ログファイル
c:\Users\take_me_hospital\attendance\data\logs_dev\
```

## 🔧 開発環境の特徴

### 環境分離
- ポート: 5001 (本番は5000)
- コンテナ名: attendance-server-dev
- ログディレクトリ: logs_dev/

### 開発用設定
- `FLASK_DEBUG=True`
- `DEV_MODE=true`
- テンプレート自動リロード有効

### ファイル変更の反映
- すべてのPythonファイルがバインドマウント
- 変更は即座にコンテナに反映
- ブラウザリロードで確認可能

### 📁 開発・本番環境のファイル分離

**開発環境（5001）用ファイル:**
- `server/templates_dev/` - 開発用テンプレート
- `server/static_dev/` - 開発用静的ファイル（CSS/JS）

**本番環境（5000）用ファイル:**
- `server/templates/` - 本番用テンプレート（変更禁止）
- `server/static/` - 本番用静的ファイル（変更禁止）

**開発時の注意:**
- 必ず`templates_dev/`と`static_dev/`を編集してください
- 本番環境（`templates/`と`static/`）は直接編集しないでください
- 検証完了後、本番環境にコピーして反映してください

## 🎯 お知らせ機能開発

### 新機能開発の流れ
1. **開発環境で機能実装**
   - `templates_dev/`と`static_dev/`を編集
   - 開発環境（5001）で動作確認
2. **テスト・デバッグ**
   - 開発環境で十分にテスト
3. **本番環境に反映**
   - 検証完了後、`templates_dev/`から`templates/`へコピー
   - `static_dev/`から`static/`へコピー
   - 本番環境を再起動（必要に応じて）

### 追加予定の機能
- 個人別お知らせ表示
- スケジュール vs 実績差異検出
- 打刻漏れアラート
- 時間外・休暇申請ガイダンス
- 確認済み状態管理

## 🛡️ 安全な開発

### データベース保護
- 本番データの誤削除防止
- バックアップの定期取得推奨
- 重要な変更前はデータ退避

### 切り替え手順
1. 開発完了後、十分なテスト実施
2. 本番環境一時停止
3. 打刻PCの接続先変更 (5000→5001)
4. 本番環境更新
5. 打刻PCを本番環境に戻す (5001→5000)