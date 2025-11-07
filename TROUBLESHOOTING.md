# 🔧 トラブルシューティングガイド

打刻システムでよく発生する問題と解決方法をまとめています。

---

## 📋 目次

1. [Docker関連](#docker関連)
2. [データベース関連](#データベース関連)
3. [時間外申告関連](#時間外申告関連)
4. [API関連](#api関連)
5. [Web画面関連](#web画面関連)

---

## 🐳 Docker関連

### Docker Desktopが起動していない

**症状:**
```
error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine"
```

**解決策:**
```bash
# Docker Desktopを起動
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# 30秒待ってから確認
docker version
```

### ポートが使用中

**症状:**
```
Bind for 0.0.0.0:5000 failed: port is already allocated
```

**解決策:**
```bash
# 既存のコンテナを停止
docker-compose down

# ポートを使用しているプロセスを確認（Windows）
netstat -ano | findstr :5000

# 再起動
docker-compose up -d
```

### コンテナが起動しない

**症状:** `docker-compose ps` でStatusが「Exited」

**確認:**
```bash
# ログを確認
docker-compose logs --tail=50

# エラーメッセージを確認
docker-compose logs | grep -i error
```

**よくある原因:**
1. Pythonのシンタックスエラー
2. モジュールのインポートエラー
3. データベースパスの問題

**解決策:**
```bash
# 完全にクリーンして再作成
docker-compose down -v
docker-compose up -d --build
```

### コード変更が反映されない

**原因:** Volumeマウントの問題またはキャッシュ

**解決策:**
```bash
# Python コード変更時
docker-compose restart

# それでもダメなら完全再ビルド
docker-compose down
docker-compose up -d --build

# volumeマウントを確認
docker inspect attendance-server --format='{{json .Mounts}}'
```

---

## 🗄️ データベース関連

### データベースが見つからない

**症状:** APIは動作するがデータが空

**確認:**
```bash
# Docker内のパスを確認
docker exec attendance-server env | grep DATABASE_PATH

# ホスト側のファイル確認
ls -la C:\Users\take_me_hospital\attendance\data\attendance.db

# Docker内のファイル確認
docker exec attendance-server ls -la /app/data/
```

**解決策:**
```bash
# データディレクトリが存在しない場合
mkdir C:\Users\take_me_hospital\attendance\data

# volumeマウントを確認
# docker-compose.yml の volumes セクション
volumes:
  - ../../data:/app/data

# コンテナ再作成
docker-compose down
docker-compose up -d
```

### テーブルが存在しない

**症状:** `no such table: employee_master`

**原因:** データベースが初期化されていない

**解決策:**
```bash
# サーバーを起動するとテーブルが自動作成される
docker-compose restart

# ログで初期化メッセージを確認
docker-compose logs | grep "初期化"

# 手動でテーブル確認
python check_host_db.py
```

### データベースが破損

**症状:** `database disk image is malformed`

**解決策:**
```bash
# バックアップから復元
cp C:\Users\take_me_hospital\attendance\data\backups\attendance_20251106.db C:\Users\take_me_hospital\attendance\data\attendance.db

# バックアップがない場合は新規作成
docker-compose restart
```

---

## ⏰ 時間外申告関連

### 時間外申告が保存されない

**症状:** 申告ボタンを押しても404エラー

**確認:**
```bash
# ログでエラーを確認
docker-compose logs -f | grep -i overtime

# APIエンドポイントが登録されているか確認
docker-compose logs | grep "/api/overtime"
```

**原因1: employee_numの型不一致**
```
"従業員が見つかりません"
```

**解決策:** 最新版では修正済み。`safe_int()`で型変換

**原因2: overtime.pyがマウントされていない**
```
ModuleNotFoundError: No module named 'overtime'
```

**解決策:**
```yaml
# docker-compose.yml に追加
volumes:
  - ./overtime.py:/app/overtime.py
```

```bash
docker-compose down
docker-compose up -d
```

### 時間外が承認できない

**症状:** 承認ボタンを押してもエラー

**確認:**
```bash
# ブラウザのコンソールでエラー確認
# F12 → Console タブ

# サーバーログ確認
docker-compose logs -f
```

**よくある原因:**
- JavaScriptエラー
- APIパスが間違っている
- ステータスが既に`approved`になっている

---

## 📡 API関連

### 404 Not Found

**症状:** APIリクエストで404エラー

**確認:**
```bash
# 登録されているルートを確認
docker exec attendance-server python -c "from api import *; from flask import Flask; app = Flask(__name__); register_api_routes(app); [print(rule.rule) for rule in app.url_map.iter_rules()]"
```

**原因:**
- ルートが登録されていない
- URLが間違っている

**解決策:**
```python
# api.py で @app.route が正しく定義されているか確認
@app.route('/api/overtime', methods=['POST'])
def create_overtime_application():
    ...
```

### 500 Internal Server Error

**症状:** APIリクエストで500エラー

**確認:**
```bash
# 詳細なエラーログを確認
docker-compose logs --tail=100 | grep -A 10 "Traceback"
```

**よくある原因:**
1. データベース接続エラー
2. SQL構文エラー
3. 型変換エラー（intとstrの混在）
4. Noneチェック漏れ

**解決策:**
- ログで具体的なエラーメッセージを確認
- Pythonコードのエラー箇所を修正
- `docker-compose restart` で再起動

### JSONDecodeError

**症状:** `Expecting value: line 1 column 1 (char 0)`

**原因:** APIレスポンスがJSONではない（HTMLエラーページなど）

**確認:**
```bash
# ブラウザまたはcurlで直接確認
curl http://localhost:5000/api/overtime

# ステータスコードを確認
curl -I http://localhost:5000/api/overtime
```

---

## 🌐 Web画面関連

### ページが表示されない

**症状:** ブラウザで真っ白またはエラー

**確認:**
```bash
# サーバーが起動しているか
docker-compose ps

# ログでエラー確認
docker-compose logs -f

# ブラウザのコンソールでエラー確認（F12）
```

**解決策:**
```bash
# テンプレートファイルが存在するか確認
docker exec attendance-server ls -la /app/templates/

# キャッシュをクリア
# ブラウザで Ctrl+Shift+R（ハードリロード）
```

### JavaScriptが動作しない

**症状:** ボタンを押しても反応がない

**確認:**
```
ブラウザのコンソール（F12 → Console タブ）でエラー確認
```

**よくあるエラー:**
```
Uncaught ReferenceError: functionName is not defined
```

**解決策:**
- HTMLファイルのJavaScriptコードを確認
- 関数名のtypoをチェック
- `async/await` の使い方を確認

### 従業員リストが表示されない

**症状:** ドロップダウンが空

**確認:**
```bash
# APIが動作しているか
curl http://localhost:5000/api/employees

# データベースに従業員データがあるか
python check_host_db.py
```

**解決策:**
```bash
# employee_master テーブルにデータを投入
# または既存のデータベースを配置
```

---

## 🔍 デバッグ方法

### ログの見方

```bash
# リアルタイムでログ監視
docker-compose logs -f

# 最新50行のみ表示
docker-compose logs --tail=50

# エラーのみ抽出
docker-compose logs | grep -i error

# 特定のキーワードで検索
docker-compose logs | grep -i "時間外"
```

### データベース内容の確認

```bash
# 確認スクリプトを使用
python check_overtime.py
python check_host_db.py

# 直接SQLで確認
python -c "import sqlite3; conn=sqlite3.connect(r'C:\Users\take_me_hospital\attendance\data\attendance.db'); [print(row) for row in conn.execute('SELECT * FROM overtime_applications')]; conn.close()"
```

### APIテスト

```bash
# テストスクリプトを使用
python test_overtime_api.py

# curlで直接テスト（Windows PowerShell）
Invoke-WebRequest -Uri "http://localhost:5000/api/health" -Method GET
Invoke-WebRequest -Uri "http://localhost:5000/api/employees" -Method GET
```

---

## 🚨 緊急時の対処

### すべてをリセット

```bash
# 1. コンテナとボリュームを完全削除
docker-compose down -v

# 2. イメージも削除
docker rmi server-attendance-server

# 3. データベースバックアップ（重要！）
cp C:\Users\take_me_hospital\attendance\data\attendance.db C:\Users\take_me_hospital\attendance\data\attendance_backup.db

# 4. 完全に再作成
docker-compose up -d --build

# 5. 起動確認
docker-compose ps
docker-compose logs --tail=30
```

### データベース復元

```bash
# バックアップから復元
cp C:\Users\take_me_hospital\attendance\data\backups\attendance_*.db C:\Users\take_me_hospital\attendance\data\attendance.db

# コンテナ再起動
docker-compose restart
```

---

## 📞 サポート情報

### ログ収集

問題報告時に以下の情報を収集してください：

```bash
# 1. システム情報
docker version
docker-compose version

# 2. コンテナ状態
docker-compose ps > container_status.txt

# 3. ログ
docker-compose logs > container_logs.txt

# 4. 環境変数
docker exec attendance-server env > environment.txt

# 5. データベース状態
python check_overtime.py > db_status.txt
```

### チェックリスト

問題発生時は以下を順番に確認：

- [ ] Docker Desktopが起動している
- [ ] `docker-compose ps` でコンテナがUpになっている
- [ ] ログにエラーが出ていないか
- [ ] データベースファイルが存在するか
- [ ] ブラウザのコンソールにエラーがないか
- [ ] ポート5000が空いているか

---

**更新日**: 2025-11-06

