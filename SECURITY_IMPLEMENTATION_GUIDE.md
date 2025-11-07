# セキュリティ実装ガイド

## 概要

このドキュメントは、打刻システムを本番運用する際のセキュリティ対策について説明します。
LAN内での運用を前提としていますが、最低限のセキュリティ対策を実装することで、データの保護と不正アクセスの防止を実現します。

---

## 🔒 セキュリティ対策の優先順位

### 【最優先】レベル1: 必須対策

#### 1. データベース読み取り専用モードの実装

**目的:** マスタデータ（従業員情報、スケジュール）への不正な変更を防止

**実装場所:** `server/config.py`

```python
class Config:
    # 既存の設定...
    
    # ========== セキュリティ設定 ==========
    # 変更禁止テーブル（打刻データ以外は保護）
    READ_ONLY_TABLES = ['employee_master', 'attend_schedule']
    
    # 管理者認証用シークレットキー
    ADMIN_SECRET_KEY = os.environ.get('ADMIN_SECRET_KEY', 'change-me-in-production-12345')
    
    # 許可IPアドレス範囲（LAN内）
    ALLOWED_IPS = os.environ.get('ALLOWED_IPS', '192.168.1.0/24').split(',')
```

---

#### 2. 管理者認証の実装

**目的:** マスタデータの変更は管理者のみ可能にする

**実装場所:** `server/auth.py`（新規作成）

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
認証・認可モジュール
管理者権限チェックとアクセス制御
"""

from functools import wraps
from flask import request, jsonify
from config import Config
import os

# 管理者トークン（環境変数から読み込み）
ADMIN_TOKENS = set(os.environ.get('ADMIN_TOKENS', '').split(','))

def require_admin(f):
    """
    管理者権限が必要なAPIを保護するデコレータ
    
    使用例:
        @app.route('/api/admin/employee', methods=['POST'])
        @require_admin
        def manage_employee():
            # 管理者のみアクセス可能
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # トークン確認
        token = request.headers.get('X-Admin-Token')
        
        if not token or token not in ADMIN_TOKENS:
            return jsonify({
                'status': 'error',
                'message': '管理者権限が必要です'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function

def require_write_permission(table_name):
    """
    特定テーブルへの書き込み権限チェックのデコレータ
    
    Args:
        table_name: チェック対象のテーブル名
    
    使用例:
        @require_write_permission('employee_master')
        def update_employee():
            # employee_masterへの書き込みには管理者権限が必要
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 読み取り専用テーブルへの書き込みをブロック
            if table_name in Config.READ_ONLY_TABLES:
                token = request.headers.get('X-Admin-Token')
                if not token or token not in ADMIN_TOKENS:
                    return jsonify({
                        'status': 'error',
                        'message': f'{table_name}への変更には管理者権限が必要です'
                    }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def generate_admin_token():
    """
    新しい管理者トークンを生成
    
    Returns:
        str: ランダムに生成された64文字のトークン
    """
    import secrets
    return secrets.token_urlsafe(48)
```

---

#### 3. IP制限の実装

**目的:** LAN外からのアクセスをブロック

**実装場所:** `server/middleware.py`（新規作成）

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ミドルウェアモジュール
リクエストの事前チェック（IP制限など）
"""

from flask import request, jsonify
from config import Config
import ipaddress

def check_ip_allowed():
    """
    リクエスト元IPが許可範囲内かチェック
    
    Returns:
        bool: 許可されている場合True
    """
    client_ip = request.remote_addr
    
    # 開発環境の場合はスキップ
    if Config.DEBUG:
        return True
    
    try:
        client_ip_obj = ipaddress.ip_address(client_ip)
        
        for allowed_range in Config.ALLOWED_IPS:
            if client_ip_obj in ipaddress.ip_network(allowed_range, strict=False):
                return True
        
        return False
    except:
        return False

def ip_restriction_middleware(app):
    """
    IPチェックミドルウェアをFlaskアプリに適用
    
    Args:
        app: Flaskアプリケーションインスタンス
    """
    @app.before_request
    def check_ip():
        # 静的ファイルとヘルスチェックは除外
        if request.path.startswith('/static') or request.path == '/api/health':
            return None
        
        if not check_ip_allowed():
            return jsonify({
                'status': 'error',
                'message': 'アクセスが許可されていないIPアドレスです',
                'client_ip': request.remote_addr
            }), 403
    
    print(f"✅ IP制限ミドルウェア有効化: {Config.ALLOWED_IPS}")
```

---

### 【重要】レベル2: 推奨対策

#### 4. 監査ログの実装

**目的:** 誰がいつ何をしたかを記録

**実装場所:** `server/audit_log.py`（新規作成）

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
監査ログモジュール
全ての重要な操作を記録
"""

import sqlite3
from datetime import datetime
from config import Config

def init_audit_log():
    """監査ログテーブルの作成"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            table_name TEXT,
            user_ip TEXT,
            details TEXT,
            admin_token_used BOOLEAN DEFAULT 0,
            success BOOLEAN DEFAULT 1
        )
    """)
    
    # インデックス作成
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)")
    
    conn.commit()
    conn.close()
    print("✅ 監査ログテーブル初期化完了")

def log_action(action, table_name=None, details=None, success=True):
    """
    アクションをログに記録
    
    Args:
        action: 実行されたアクション（例: 'INSERT_EMPLOYEE', 'DELETE_SCHEDULE'）
        table_name: 対象テーブル名
        details: 詳細情報（JSON文字列など）
        success: 成功したかどうか
    
    使用例:
        log_action('INSERT_ATTENDANCE', 'attendance', f'IDm: {idm}')
    """
    from flask import request
    
    try:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO audit_log (timestamp, action, table_name, user_ip, details, admin_token_used, success)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            action,
            table_name,
            request.remote_addr if request else 'system',
            details,
            bool(request.headers.get('X-Admin-Token')) if request else False,
            success
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"監査ログ記録エラー: {e}")

def get_audit_logs(limit=100, action_filter=None):
    """
    監査ログを取得
    
    Args:
        limit: 取得件数
        action_filter: アクションでフィルタ（例: 'DELETE_%'）
    
    Returns:
        list: 監査ログのリスト
    """
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    if action_filter:
        cursor.execute("""
            SELECT * FROM audit_log 
            WHERE action LIKE ?
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (action_filter, limit))
    else:
        cursor.execute("""
            SELECT * FROM audit_log 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
    
    logs = cursor.fetchall()
    conn.close()
    
    return logs
```

---

#### 5. データベースバックアップの自動化

**目的:** データ損失を防ぐ

**実装場所:** `server/backup.py`（新規作成）

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
バックアップモジュール
データベースの自動バックアップと管理
"""

import shutil
from datetime import datetime, timedelta
from pathlib import Path
from config import Config

def auto_backup():
    """
    データベースの自動バックアップ
    
    Returns:
        Path: バックアップファイルのパス
    """
    db_path = Path(Config.DATABASE_PATH)
    backup_dir = db_path.parent / 'backups'
    backup_dir.mkdir(exist_ok=True)
    
    # 日時付きバックアップ
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f'attendance_{timestamp}.db'
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✅ バックアップ作成: {backup_path}")
        
        # 古いバックアップを削除
        cleanup_old_backups(backup_dir, days=7)
        
        return backup_path
    except Exception as e:
        print(f"❌ バックアップエラー: {e}")
        return None

def cleanup_old_backups(backup_dir, days=7):
    """
    古いバックアップファイルを削除
    
    Args:
        backup_dir: バックアップディレクトリ
        days: 保持日数
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    
    for old_backup in backup_dir.glob('attendance_*.db'):
        file_time = datetime.fromtimestamp(old_backup.stat().st_mtime)
        if file_time < cutoff_date:
            old_backup.unlink()
            print(f"🗑️ 古いバックアップ削除: {old_backup.name}")

def restore_from_backup(backup_path):
    """
    バックアップからリストア
    
    Args:
        backup_path: バックアップファイルのパス
    
    Returns:
        bool: 成功した場合True
    """
    db_path = Path(Config.DATABASE_PATH)
    
    try:
        # 現在のDBを .bak として保存
        if db_path.exists():
            shutil.copy2(db_path, db_path.with_suffix('.db.bak'))
        
        # バックアップからリストア
        shutil.copy2(backup_path, db_path)
        print(f"✅ リストア完了: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ リストアエラー: {e}")
        return False

def list_backups():
    """
    利用可能なバックアップファイルのリストを取得
    
    Returns:
        list: バックアップファイルのリスト
    """
    db_path = Path(Config.DATABASE_PATH)
    backup_dir = db_path.parent / 'backups'
    
    if not backup_dir.exists():
        return []
    
    backups = []
    for backup_file in sorted(backup_dir.glob('attendance_*.db'), reverse=True):
        backups.append({
            'filename': backup_file.name,
            'path': str(backup_file),
            'size': backup_file.stat().st_size,
            'created': datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
        })
    
    return backups
```

---

### 【推奨】レベル3: 本番運用構成

#### 6. 開発環境と本番環境の分離

**本番用Docker Compose設定:** `server/docker-compose.prod.yml`（新規作成）

```yaml
services:
  attendance-server:
    build: .
    container_name: attendance-server-prod
    ports:
      - "5000:5000"
    volumes:
      # データベースのみマウント（コードは固定）
      - ../../data:/app/data
    environment:
      - TZ=Asia/Tokyo
      # サーバー設定
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=5000
      - FLASK_DEBUG=False
      - FLASK_ENV=production
      
      # セキュリティ設定
      - DATABASE_PATH=/app/data/attendance.db
      - ADMIN_TOKENS=${ADMIN_TOKENS}  # 環境変数から読み込み
      - ALLOWED_IPS=192.168.1.0/24
      - ADMIN_SECRET_KEY=${ADMIN_SECRET_KEY}
      
      # チャタリング防止設定
      - CHATTERING_THRESHOLD=10
      
      # API設定
      - API_VERSION=1.0.0
      - DEFAULT_SEARCH_LIMIT=100
      - STATS_LATEST_RECORDS=10
      
      # 給与計算期間設定
      - PAYROLL_START_DAY=16
      - PAYROLL_END_DAY=15
      
      # バリデーション設定
      - EMPLOYEE_ID_MIN_LENGTH=3
      - EMPLOYEE_ID_MAX_LENGTH=20
      - YEAR_MIN=2000
      - YEAR_MAX=2100
    restart: always
    networks:
      - attendance-network

networks:
  attendance-network:
    driver: bridge
```

**環境変数ファイル:** `.env.production`（新規作成、Gitには含めない）

```bash
# 本番環境用環境変数
# このファイルは機密情報を含むため、.gitignoreに追加すること

# 管理者トークン（カンマ区切りで複数指定可能）
ADMIN_TOKENS=abc123xyz789def456,uvw012ghi345jkl678

# 管理者シークレットキー（64文字以上推奨）
ADMIN_SECRET_KEY=your-very-long-secret-key-change-this-in-production-12345678

# 許可IPアドレス範囲
ALLOWED_IPS=192.168.1.0/24,192.168.10.0/24
```

**本番起動スクリプト:** `server/start_production.bat`（新規作成）

```batch
@echo off
chcp 65001 >nul
echo ========================================
echo 本番環境起動 - 打刻システム
echo ========================================
echo.

cd /d %~dp0

echo [確認] 環境変数ファイルの読み込み...
if not exist .env.production (
    echo ❌ .env.production が見つかりません
    echo    先に .env.production を作成してください
    pause
    exit /b 1
)

echo [1/3] 既存コンテナの停止...
docker-compose -f docker-compose.prod.yml down

echo.
echo [2/3] 本番環境でビルド＆起動...
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d --build

if %errorlevel% neq 0 (
    echo ❌ 起動エラーが発生しました
    pause
    exit /b 1
)

echo.
echo [3/3] 起動確認...
timeout /t 3 >nul
docker-compose -f docker-compose.prod.yml ps

echo.
echo ========================================
echo ✅ 本番環境起動完了！
echo ========================================
echo.
echo 🌐 アクセス: http://localhost:5000
echo 📋 ログ確認: docker-compose -f docker-compose.prod.yml logs -f
echo 🛑 停止: docker-compose -f docker-compose.prod.yml down
echo.
pause
```

---

## 🔐 管理者トークンの生成と運用

### トークン生成

```python
# Pythonで実行
import secrets
token = secrets.token_urlsafe(48)
print(f"新しい管理者トークン: {token}")
```

### トークンの使用例

```bash
# 従業員マスタにデータを追加
curl -X POST http://192.168.1.100:5000/api/admin/employee \
  -H "X-Admin-Token: abc123xyz789def456" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "新入社員",
    "employee_num": "999999",
    "idm": "100999"
  }'
```

### トークン管理のベストプラクティス

1. **複数トークンの発行:** 管理者ごとに異なるトークンを発行
2. **定期的な更新:** 3ヶ月〜6ヶ月に一度更新
3. **安全な保管:** パスワードマネージャーで管理
4. **ログの監視:** 誰がいつトークンを使用したか監査ログで確認

---

## 📋 セキュリティチェックリスト

### 実装前チェック

- [ ] `server/auth.py` 作成
- [ ] `server/middleware.py` 作成
- [ ] `server/audit_log.py` 作成
- [ ] `server/backup.py` 作成
- [ ] `server/docker-compose.prod.yml` 作成
- [ ] `.env.production` 作成（.gitignoreに追加）
- [ ] `server/start_production.bat` 作成

### 設定チェック

- [ ] `Config.READ_ONLY_TABLES` に保護対象テーブルを設定
- [ ] `Config.ALLOWED_IPS` にLAN範囲を設定
- [ ] `.env.production` に管理者トークンを設定
- [ ] `.env.production` にシークレットキーを設定

### 運用開始前チェック

- [ ] 開発環境でセキュリティ機能をテスト
- [ ] IP制限が正しく動作することを確認
- [ ] 管理者トークンなしではマスタデータを変更できないことを確認
- [ ] 監査ログが正しく記録されることを確認
- [ ] バックアップが自動作成されることを確認
- [ ] 本番環境でのデバッグモードがOFFになっていることを確認

### 定期メンテナンス

- [ ] 週次: バックアップファイルの確認
- [ ] 月次: 監査ログの確認
- [ ] 月次: 管理者トークンの使用状況確認
- [ ] 四半期: 管理者トークンの更新検討
- [ ] 四半期: セキュリティ設定の見直し

---

## 🚀 段階的実装プラン

### Phase 1: 最低限のセキュリティ（所要時間: 2-3時間）

1. `server/auth.py` 作成
2. `server/middleware.py` 作成
3. `server/server.py` にミドルウェア適用
4. `.env.production` 作成
5. 動作テスト

### Phase 2: 監査とバックアップ（所要時間: 1-2時間）

1. `server/audit_log.py` 作成
2. `server/backup.py` 作成
3. 重要なAPIに監査ログ追加
4. 定期バックアップの設定

### Phase 3: 本番環境構成（所要時間: 1時間）

1. `docker-compose.prod.yml` 作成
2. `start_production.bat` 作成
3. 本番環境での動作確認

---

## 💡 よくある質問

### Q1: 開発中もセキュリティを有効にすべきか？

**A:** 開発環境では以下を無効化することを推奨：
- IP制限: OFF（localhost以外からもアクセスしたい場合）
- 管理者認証: OFF または簡易トークン
- デバッグモード: ON

本番環境に移行する際に、すべて有効化します。

### Q2: 管理者トークンを忘れた場合は？

**A:** サーバーにログインして `.env.production` ファイルを直接編集するか、新しいトークンを生成して追加します。

```bash
# コンテナ内で確認
docker exec attendance-server-prod env | grep ADMIN_TOKENS
```

### Q3: 監査ログはいつまで保存すべきか？

**A:** 法的要件に依存しますが、一般的には：
- 最低3ヶ月〜6ヶ月
- 重要なイベントは1年以上
- 定期的にアーカイブ（CSVエクスポートなど）

### Q4: バックアップの保存先は？

**A:** 現在は `attendance/data/backups/` に保存されます。
より安全な運用のためには：
- 外付けHDD/NASへの自動コピー
- クラウドストレージへのアップロード
- 定期的なオフサイトバックアップ

---

## 🔗 関連ドキュメント

- `README.md` - システム全体の概要
- `DOCKER_SETUP_GUIDE.md` - Docker環境構築ガイド
- `API_DOCUMENTATION.md` - API仕様書（作成予定）
- `TROUBLESHOOTING.md` - トラブルシューティング

---

## 📝 更新履歴

- 2025-11-06: 初版作成
- セキュリティ実装ガイドの作成
- 段階的実装プランの追加

