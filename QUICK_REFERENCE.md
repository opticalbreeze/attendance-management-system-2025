# 📝 クイックリファレンス

よく使うコマンドとURL一覧です。

---

## 🚀 起動・停止

```bash
# Docker起動
cd server
start_docker.bat

# または
docker-compose up -d

# 停止
docker-compose down

# 再起動
docker-compose restart

# ログ確認
docker-compose logs -f
```

---

## 🌐 Web画面

| ページ | URL |
|--------|-----|
| トップページ | http://localhost:5000 |
| 打刻検索 | http://localhost:5000/search |
| 勤怠チェック | http://localhost:5000/check |
| 時間外申告 | http://localhost:5000/overtime |
| 時間外一覧 | http://localhost:5000/overtime/list |

---

## 📡 API エンドポイント

### 打刻データ

```bash
# 打刻データ送信
POST http://localhost:5000/api/attendance
Content-Type: application/json
{
  "idm": "XXXXX",
  "timestamp": "2025-11-06T09:00:00",
  "terminal_id": "TERMINAL_01"
}

# 統計情報取得
GET http://localhost:5000/api/stats

# 打刻データ検索
GET http://localhost:5000/api/search?employee_id=2952089&search_month=2025/11
```

### 時間外申告

```bash
# 時間外申告
POST http://localhost:5000/api/overtime
{
  "employee_num": "2952089",
  "application_date": "2025-11-06",
  "work_date": "2025-11-05",
  "overtime_entries": [
    {
      "start_time": "18:00",
      "end_time": "20:00",
      "description": "作業内容"
    }
  ]
}

# 時間外一覧取得
GET http://localhost:5000/api/overtime?status=pending

# 承認
POST http://localhost:5000/api/overtime/1/approve
{
  "approved_by": "admin"
}

# 却下
POST http://localhost:5000/api/overtime/1/reject
{
  "rejected_by": "admin"
}

# 月次集計
GET http://localhost:5000/api/overtime/monthly_summary?employee_num=2952089&year=2025&month=11
```

### その他

```bash
# ヘルスチェック
GET http://localhost:5000/api/health

# 従業員一覧
GET http://localhost:5000/api/employees

# 勤怠チェック
GET http://localhost:5000/api/attendance_check?employee_id=2952089&check_date=2025-11-05
```

---

## 🐳 Dockerコマンド

```bash
# コンテナ状態確認
docker-compose ps

# ログ表示（最新50行）
docker-compose logs --tail=50

# リアルタイムログ
docker-compose logs -f

# コンテナに入る
docker exec -it attendance-server /bin/bash

# 環境変数確認
docker exec attendance-server env

# 完全リビルド
docker-compose down
docker-compose up -d --build
```

---

## 🗄️ データベース操作

```bash
# データベース確認スクリプト
python check_overtime.py
python check_host_db.py

# 直接SQL実行
python -c "import sqlite3; conn=sqlite3.connect(r'C:\Users\take_me_hospital\attendance\data\attendance.db'); [print(row) for row in conn.execute('SELECT * FROM overtime_applications LIMIT 5')]; conn.close()"

# Docker内から実行
docker exec attendance-server sqlite3 /app/data/attendance.db "SELECT COUNT(*) FROM attendance;"
```

---

## 🔍 デバッグ

```bash
# エラーログ抽出
docker-compose logs | grep -i error

# 時間外関連ログ
docker-compose logs | grep -i overtime

# データベースパス確認
docker exec attendance-server env | grep DATABASE_PATH

# マウント状態確認
docker inspect attendance-server --format='{{json .Mounts}}'
```

---

## 📊 統計・確認

```bash
# 打刻データ件数
curl http://localhost:5000/api/stats | python -m json.tool

# 時間外申告件数
curl http://localhost:5000/api/overtime | python -m json.tool

# 従業員数
curl http://localhost:5000/api/employees | python -m json.tool
```

---

## 🔧 トラブルシューティング

### Docker起動エラー

```bash
# Docker Desktop起動
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# 30秒待ってから確認
docker version
```

### ポート競合

```bash
# ポート使用状況確認（Windows）
netstat -ano | findstr :5000

# コンテナ停止
docker-compose down
```

### データベースが見つからない

```bash
# ファイル確認
ls C:\Users\take_me_hospital\attendance\data\attendance.db

# volumeマウント確認
docker inspect attendance-server --format='{{json .Mounts}}'

# コンテナ再作成
docker-compose down
docker-compose up -d
```

### コード変更が反映されない

```bash
# 再起動
docker-compose restart

# 完全リビルド
docker-compose down
docker-compose up -d --build
```

---

## 📁 ファイルパス

| 項目 | パス |
|-----|------|
| データベース | `C:\Users\take_me_hospital\attendance\data\attendance.db` |
| サーバーコード | `server/` |
| Docker設定 | `server/docker-compose.yml` |
| テンプレート | `server/templates/` |
| ログ | `docker-compose logs` |

---

## 🎯 よく使う設定

### 環境変数（docker-compose.yml）

```yaml
environment:
  - FLASK_DEBUG=False          # デバッグモード
  - DATABASE_PATH=/app/data/attendance.db
  - CHATTERING_THRESHOLD=10    # 重複除外（秒）
  - PAYROLL_START_DAY=16       # 給与期間開始日
  - PAYROLL_END_DAY=15         # 給与期間終了日
```

### ポート変更

```yaml
ports:
  - "8080:5000"  # ホスト:8080 → コンテナ:5000
```

---

## 📚 ドキュメント

| ドキュメント | 用途 |
|-------------|------|
| [README.md](./README.md) | プロジェクト概要 |
| [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) | Docker詳細ガイド |
| [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md) | システム全体像 |
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | 問題解決 |
| [SECURITY_IMPLEMENTATION_GUIDE.md](./SECURITY_IMPLEMENTATION_GUIDE.md) | セキュリティ |

---

**更新日**: 2025-11-06
