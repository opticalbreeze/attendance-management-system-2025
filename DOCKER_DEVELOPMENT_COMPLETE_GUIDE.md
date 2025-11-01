# 🐳 Docker開発環境完全ガイド

**作成日**: 2025年11月1日  
**対象システム**: 勤怠管理システム (Flask + SQLite + Docker)  
**目的**: 開発効率向上とトラブル回避のための包括的ガイド

---

## 📋 目次

1. [Docker基礎理解](#docker基礎理解)
2. [ファイル変更反映の仕組み](#ファイル変更反映の仕組み)
3. [開発ワークフロー](#開発ワークフロー)
4. [トラブルシューティング](#トラブルシューティング)
5. [ベストプラクティス](#ベストプラクティス)
6. [よくある問題と解決策](#よくある問題と解決策)

---

## 🎯 Docker基礎理解

### Dockerの3つの重要概念

#### 1. **Dockerfile (設計図)**
```dockerfile
# ビルド時に実行される（1回のみ）
COPY templates/ templates/  # この時点でファイルが固定される
```

#### 2. **Dockerイメージ (製品)**
- Dockerfileから作成される読み取り専用のテンプレート
- 一度ビルドされると内容は変更されない
- ファイルを変更してもイメージ内は古いまま

#### 3. **Dockerコンテナ (実行中のインスタンス)**
- イメージから作成される実行環境
- ボリュームマウントで動的にファイルを変更可能

### 🔄 ファイル変更の2つのアプローチ

#### ❌ **COPY方式 (ビルド時固定)**
```dockerfile
COPY templates/ templates/
```
- **問題**: ファイル変更時にイメージ再ビルドが必要
- **用途**: 本番環境向け

#### ✅ **Volume方式 (ランタイム動的)**
```yaml
volumes:
  - ./templates:/app/templates
```
- **利点**: ファイル変更が即座に反映
- **用途**: 開発環境向け

---

## 🔧 ファイル変更反映の仕組み

### 現在のプロジェクト構成

#### **docker-compose.yml (開発用設定)**
```yaml
services:
  attendance-server:
    build: .
    volumes:
      # ✅ 動的マウント（開発に最適）
      - ./templates:/app/templates
      - ./server.py:/app/server.py
      - ./api.py:/app/api.py
      - ./utils.py:/app/utils.py
      - ./config.py:/app/config.py
      - ./database.py:/app/database.py
      # 💾 データ永続化
      - ./data:/data
```

#### **Dockerfile (基本構造)**
```dockerfile
# 📦 依存関係のみビルド時にインストール
COPY requirements_server.txt .
RUN pip install --no-cache-dir -r requirements_server.txt

# ⚠️ ファイルコピーは基本構造のみ
# （開発時はボリュームマウントで上書きされる）
COPY templates/ templates/
```

### 📊 変更反映のタイミング

| ファイルタイプ | 反映方法 | 所要時間 | 必要なアクション |
|---|---|---|---|
| **Python コード** | ボリュームマウント | 即座 | サーバー再起動 |
| **HTML/CSS/JS** | ボリュームマウント | 即座 | ブラウザリロード |
| **requirements.txt** | イメージ再ビルド | 30秒〜2分 | `--build` フラグ |
| **Dockerfile** | イメージ再ビルド | 30秒〜2分 | `--build` フラグ |

---

## 🚀 開発ワークフロー

### 1. **日常的な開発作業**

#### **Pythonコード変更時**
```bash
# 1. ファイルを編集
# 2. コンテナ再起動（Flask再読み込み）
docker restart attendance-server

# 3. 動作確認
curl http://192.168.11.24:5000/api/health
```

#### **HTML/CSS/JavaScript変更時**
```bash
# 1. ファイルを編集
# 2. ブラウザで強制リロード
# Windows: Ctrl + F5
# Mac: Cmd + Shift + R
```

### 2. **変更確認のベストプラクティス**

#### **ファイル同期確認**
```bash
# コンテナ内のファイルタイムスタンプ確認
docker exec attendance-server ls -la /app/templates/

# ローカルファイルと比較
Get-ChildItem ".\templates\*.html" | Select-Object Name, LastWriteTime
```

#### **コンテナ内ファイル内容確認**
```bash
# 特定の変更が反映されているか確認
docker exec attendance-server grep -n "特定の文字列" /app/templates/check.html
```

### 3. **重要な変更時の手順**

#### **依存関係変更時**
```bash
# requirements.txt を変更した場合
docker-compose down
docker-compose up -d --build
```

#### **Docker設定変更時**
```bash
# Dockerfile や docker-compose.yml を変更した場合
docker-compose down
docker image rm server-attendance-server
docker-compose up -d --build
```

---

## 🚨 トラブルシューティング

### 問題1: 「ファイル変更が反映されない」

#### **診断手順**
```bash
# Step 1: マウント状況確認
docker inspect attendance-server | findstr -i mount

# Step 2: コンテナ内ファイル確認
docker exec attendance-server ls -la /app/templates/

# Step 3: ファイル内容比較
docker exec attendance-server head -20 /app/templates/check.html
```

#### **解決策の優先順位**
1. **レベル1**: ブラウザ強制リロード（Ctrl+F5）
2. **レベル2**: コンテナ再起動
   ```bash
   docker restart attendance-server
   ```
3. **レベル3**: イメージ再ビルド
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```
4. **レベル4**: 完全クリーンアップ
   ```bash
   docker-compose down
   docker image rm server-attendance-server
   docker system prune -f
   docker-compose up -d --build
   ```

### 問題2: 「JavaScript/CSS変更が反映されない」

#### **ブラウザキャッシュ対策**
```html
<!-- HTMLヘッダーに追加済み -->
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
```

#### **強制リロード手順**
1. **F12キー** でDevTools開く
2. **Network タブ** で「Disable cache」にチェック
3. **Ctrl + F5** で強制リロード

### 問題3: 「API変更が反映されない」

#### **Flask再起動確認**
```bash
# サーバーログ確認
docker logs attendance-server --tail=20

# プロセス再起動
docker restart attendance-server

# API動作確認
curl http://192.168.11.24:5000/api/health
```

---

## 🎯 ベストプラクティス

### 開発環境設定

#### **1. エディター設定**
- **自動保存**: 有効化
- **ファイル監視**: 有効化
- **文字エンコーディング**: UTF-8 (BOMなし)

#### **2. Git設定**
```bash
# 改行コード統一
git config core.autocrlf false
git config core.eol lf
```

#### **3. 開発用コマンドエイリアス**
```bash
# PowerShell Profile に追加
function Docker-Restart { docker restart attendance-server }
function Docker-Rebuild { docker-compose down; docker-compose up -d --build }
function Docker-Clean { docker-compose down; docker system prune -f; docker-compose up -d --build }

Set-Alias dr Docker-Restart
Set-Alias drb Docker-Rebuild
Set-Alias dc Docker-Clean
```

### コード管理

#### **1. 変更前のバックアップ**
```bash
# 重要な変更前に必ずバックアップ
Copy-Item "templates\check.html" "templates\check.html.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
```

#### **2. コミット前の確認**
```bash
# 動作確認してからコミット
curl http://192.168.11.24:5000/api/health
curl "http://192.168.11.24:5000/api/attendance_check?employee_id=3652025&check_date=2025-10-09"
```

### デバッグ効率化

#### **1. ログレベル制御**
```python
# config.py
DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')
```

#### **2. APIテスト用スクリプト**
```bash
# api_test.bat 作成
@echo off
echo Testing Health API...
curl http://192.168.11.24:5000/api/health
echo.
echo Testing Employee API...
curl http://192.168.11.24:5000/api/employees
echo.
echo Testing Attendance Check API...
curl "http://192.168.11.24:5000/api/attendance_check?employee_id=3652025&check_date=2025-10-09"
```

---

## ⚠️ よくある問題と解決策

### 1. **「変更したのに古い画面が表示される」**

**原因**: ブラウザキャッシュ  
**解決策**:
```bash
# 1. 強制リロード
Ctrl + F5

# 2. キャッシュクリア
F12 → Application → Storage → Clear storage

# 3. シークレットモードでテスト
Ctrl + Shift + N
```

### 2. **「JavaScript関数が重複している」**

**原因**: 複数回の修正により関数が重複  
**解決策**:
```bash
# 1. コンテナから正常ファイルを取得
docker cp attendance-server:/app/templates/check.html ./check_clean.html

# 2. 差分確認
code --diff check.html check_clean.html

# 3. クリーンファイルに置き換え
Copy-Item check_clean.html check.html -Force
```

### 3. **「APIが500エラーを返す」**

**原因**: Python構文エラーまたは例外  
**解決策**:
```bash
# 1. ログ確認
docker logs attendance-server --tail=50

# 2. コンテナ内でPythonコード確認
docker exec -it attendance-server python -m py_compile /app/api.py

# 3. 対話式デバッグ
docker exec -it attendance-server python
```

### 4. **「データベース変更が反映されない」**

**原因**: データベースファイルがロックまたは権限問題  
**解決策**:
```bash
# 1. データベース接続確認
docker exec attendance-server sqlite3 /data/attendance.db ".tables"

# 2. 権限確認
docker exec attendance-server ls -la /data/

# 3. データベース再作成（最終手段）
docker exec attendance-server rm /data/attendance.db
docker restart attendance-server
```

---

## 📚 開発効率化ツール

### 1. **監視スクリプト**

#### **docker_watch.ps1**
```powershell
# ファイル変更監視とコンテナ自動再起動
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = "C:\Users\take_me_hospital\Desktop\N100\attend_server\server"
$watcher.Filter = "*.py"
$watcher.EnableRaisingEvents = $true

Register-ObjectEvent -InputObject $watcher -EventName "Changed" -Action {
    Write-Host "File changed: $($Event.SourceEventArgs.FullPath)"
    docker restart attendance-server
}
```

### 2. **クイックテストスクリプト**

#### **quick_test.bat**
```batch
@echo off
echo [1/4] Health Check...
curl -s http://192.168.11.24:5000/api/health | jq .status

echo [2/4] Employee API...
curl -s http://192.168.11.24:5000/api/employees | jq ".data | length"

echo [3/4] Attendance Check...
curl -s "http://192.168.11.24:5000/api/attendance_check?employee_id=3652025&check_date=2025-10-09" | jq .status

echo [4/4] Web Page...
curl -s -o NUL -w "%%{http_code}" http://192.168.11.24:5000/check
echo.
```

### 3. **緊急復旧スクリプト**

#### **emergency_restore.bat**
```batch
@echo off
echo Emergency Docker Restore...
docker-compose down
docker system prune -f
docker volume prune -f
docker image prune -a -f
docker-compose up -d --build
echo Restore completed. Waiting for server...
timeout 10
curl http://192.168.11.24:5000/api/health
```

---

## 🔄 定期メンテナンス

### 週次作業
```bash
# 1. 不要なイメージ・コンテナ削除
docker system prune -f

# 2. ログサイズ確認
docker logs attendance-server --tail=1 | wc -l

# 3. データベースバックアップ
docker cp attendance-server:/data/attendance.db ./backup/attendance_$(date +%Y%m%d).db
```

### 月次作業
```bash
# 1. 完全クリーンアップ
docker-compose down
docker system prune -a -f
docker volume prune -f

# 2. 最新Baseイメージ更新
docker pull python:3.11-slim

# 3. 依存関係更新確認
docker exec attendance-server pip list --outdated
```

---

## 📖 参考資料とコマンド集

### よく使うDockerコマンド
```bash
# コンテナ状態確認
docker ps -a

# コンテナ内でコマンド実行
docker exec -it attendance-server bash

# ログリアルタイム監視
docker logs -f attendance-server

# リソース使用量確認
docker stats attendance-server

# ネットワーク確認
docker network ls
docker network inspect server_attendance-network
```

### デバッグ用コマンド
```bash
# ポート使用状況
netstat -ano | findstr :5000

# プロセス確認
tasklist | findstr python

# ファイルロック確認
lsof /data/attendance.db  # Linux/Mac
handle /data/attendance.db  # Windows (要Sysinternals)
```

---

**作成者**: GitHub Copilot  
**最終更新**: 2025年11月1日  
**バージョン**: 1.0.0

> 💡 **重要**: このガイドを定期的に更新し、新しく学んだベストプラクティスを追加してください。開発効率は継続的な改善から生まれます。