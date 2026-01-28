# 開発・本番環境分離ガイド

## 📋 概要

開発環境（5001）と本番環境（5000）のファイルを完全に分離し、開発環境での変更が本番環境に影響しないようにします。

## 🗂️ ディレクトリ構成

```
server/
├── templates/          # 本番環境用（5000）
├── static/             # 本番環境用（5000）
├── templates_dev/      # 開発環境用（5001）
└── static_dev/         # 開発環境用（5001）
```

## 🔄 開発ワークフロー

### 1. 開発環境での作業（5001）

1. **開発環境を起動**
   ```cmd
   start_dev.bat
   ```

2. **開発環境専用ファイルを編集**
   - `server/templates_dev/` 内のファイルを編集
   - `server/static_dev/` 内のファイルを編集

3. **開発環境で検証**
   - URL: http://localhost:5001
   - 変更は即座に反映されます（バインドマウント）

### 2. 本番環境への反映（5000）

開発環境での検証が完了したら、本番環境に反映します。

#### 方法1: ファイルコピー（推奨）

```cmd
# 開発環境から本番環境へコピー
xcopy /E /I /Y server\templates_dev\* server\templates\
xcopy /E /I /Y server\static_dev\* server\static\
```

#### 方法2: 手動コピー

変更したファイルのみを本番環境にコピー：
- `server/templates_dev/attendance_check.html` → `server/templates/attendance_check.html`
- `server/static_dev/js/attendance-check.js` → `server/static/js/attendance-check.js`

### 3. 本番環境の再起動（必要に応じて）

```cmd
# 本番環境を再起動（ファイル変更を反映）
docker restart attendance-server
```

## ⚠️ 重要な注意事項

### ✅ 開発環境（5001）で作業する場合

- **必ず `templates_dev/` と `static_dev/` を編集**
- 本番環境（`templates/` と `static/`）は**一切変更しない**

### ✅ 本番環境（5000）への反映時

- 開発環境での検証が完了してから反映
- 反映前にバックアップを取得することを推奨
- 本番環境のファイルは直接編集しない

## 📝 ファイル変更の例

### 開発環境で変更する場合

```cmd
# 開発環境専用ファイルを編集
notepad server\templates_dev\attendance_check.html
notepad server\static_dev\js\attendance-check.js

# 開発環境で検証（http://localhost:5001）
```

### 本番環境に反映する場合

```cmd
# 検証完了後、本番環境にコピー
xcopy /Y server\templates_dev\attendance_check.html server\templates\
xcopy /Y server\static_dev\js\attendance-check.js server\static\js\

# 本番環境を再起動（必要に応じて）
docker restart attendance-server
```

## 🔍 現在の状態確認

### 開発環境のファイルパス
- テンプレート: `server/templates_dev/`
- 静的ファイル: `server/static_dev/`
- コンテナ内: `/app/templates`, `/app/static`

### 本番環境のファイルパス
- テンプレート: `server/templates/`
- 静的ファイル: `server/static/`
- コンテナ内: `/app/templates`, `/app/static`

## 🛠️ トラブルシューティング

### 開発環境の変更が反映されない場合

1. 開発環境のコンテナが起動しているか確認
   ```cmd
   docker ps | findstr attendance-server-dev
   ```

2. ファイルパスを確認
   - `templates_dev/` を編集しているか
   - `templates/` を編集していないか

3. コンテナを再起動
   ```cmd
   docker restart attendance-server-dev
   ```

### 本番環境に反映されない場合

1. ファイルが正しくコピーされているか確認
2. 本番環境のコンテナを再起動
   ```cmd
   docker restart attendance-server
   ```

## 📚 関連ファイル

- `docker-compose.dev.yml`: 開発環境設定（`templates_dev`, `static_dev`をマウント）
- `docker-compose.yml`: 本番環境設定（`templates`, `static`をマウント）


