# 📋 設定ファイル構造案

## 🎯 提案内容

現在ハードコーディングされている設定値を外部化し、環境変数とデフォルト値で管理する構造を提案します。

---

## 📁 ファイル構成

```
server/
├── config.py              # 設定管理モジュール（新規作成）
├── config.example.py      # 設定サンプルファイル（新規作成）
├── .env.example          # 環境変数サンプル（オプション）
└── ...（既存ファイル）
```

---

## 🔧 設定カテゴリ

### 1. **サーバー設定**
```python
SERVER_HOST = '0.0.0.0'      # デフォルト: 0.0.0.0
SERVER_PORT = 5000           # デフォルト: 5000
DEBUG = False                 # デフォルト: False
```

**環境変数:**
- `SERVER_HOST`
- `SERVER_PORT`
- `FLASK_DEBUG`

---

### 2. **データベース設定**
```python
DATABASE_PATH = auto_detect()  # 環境に応じて自動判定
```

**環境変数:**
- `DATABASE_PATH` (明示的に指定する場合)

**自動判定ロジック:**
1. 環境変数 `DATABASE_PATH` が設定されていれば使用
2. `/data` ディレクトリが存在すれば `/data/attendance.db` (Docker環境)
3. `./data` ディレクトリが存在すれば `./data/attendance.db` (ローカル環境)
4. それ以外は `attendance.db` (カレントディレクトリ)

---

### 3. **チャタリング防止設定**
```python
CHATTERING_THRESHOLD_SECONDS = 10  # デフォルト: 10秒
```

**環境変数:**
- `CHATTERING_THRESHOLD`

**使用箇所:**
- `utils.py`: `check_duplicate_attendance()`
- `api.py`: `cleanup_duplicates_api()`

---

### 4. **API設定**
```python
API_VERSION = '1.0.0'                    # デフォルト: 1.0.0
DEFAULT_SEARCH_LIMIT = 100               # デフォルト: 100件
STATS_LATEST_RECORDS = 10                # デフォルト: 10件
```

**環境変数:**
- `API_VERSION`
- `DEFAULT_SEARCH_LIMIT`
- `STATS_LATEST_RECORDS`

**使用箇所:**
- `api.py`: 検索APIのデフォルト上限
- `database.py`: 統計情報の最新履歴件数

---

### 5. **給与計算期間設定**
```python
PAYROLL_START_DAY = 16   # 前月16日（デフォルト: 16）
PAYROLL_END_DAY = 15     # 当月15日（デフォルト: 15）
```

**環境変数:**
- `PAYROLL_START_DAY`
- `PAYROLL_END_DAY`

**使用箇所:**
- `utils.py`: `calculate_date_range()` - 給与計算期間の計算

---

### 6. **バリデーション設定**
```python
EMPLOYEE_ID_MIN_LENGTH = 3      # デフォルト: 3文字
EMPLOYEE_ID_MAX_LENGTH = 20     # デフォルト: 20文字
YEAR_MIN = 2000                 # デフォルト: 2000年
YEAR_MAX = 2100                 # デフォルト: 2100年
```

**環境変数:**
- `EMPLOYEE_ID_MIN_LENGTH`
- `EMPLOYEE_ID_MAX_LENGTH`
- `YEAR_MIN`
- `YEAR_MAX`

**使用箇所:**
- `utils.py`: `validate_employee_id()`, `validate_search_month()`

---

## 🏗️ 実装パターン

### パターン1: クラスベース設定（推奨）

```python
# config.py
class Config:
    """基本設定"""
    HOST = os.environ.get('SERVER_HOST', '0.0.0.0')
    PORT = int(os.environ.get('SERVER_PORT', '5000'))
    # ...

class DevelopmentConfig(Config):
    """開発環境"""
    DEBUG = True

class ProductionConfig(Config):
    """本番環境"""
    DEBUG = False

# 使用
from config import Config
host = Config.HOST
port = Config.PORT
```

**メリット:**
- Flask標準パターンに準拠
- 環境別設定が容易
- 型安全性が高い

---

### パターン2: 辞書ベース設定

```python
# config.py
config = {
    'HOST': os.environ.get('SERVER_HOST', '0.0.0.0'),
    'PORT': int(os.environ.get('SERVER_PORT', '5000')),
    # ...
}

# 使用
from config import config
host = config['HOST']
port = config['PORT']
```

**メリット:**
- シンプル
- 動的な設定変更が容易

**デメリット:**
- タイポ検出が困難
- IDEの補完が効かない

---

## 📝 使用方法

### 方法1: 環境変数で設定（推奨）

```bash
# Linux/Mac
export SERVER_PORT=8080
export CHATTERING_THRESHOLD=15
python server.py

# Windows (PowerShell)
$env:SERVER_PORT="8080"
$env:CHATTERING_THRESHOLD="15"
python server.py
```

### 方法2: Docker Composeで設定

```yaml
# docker-compose.yml
services:
  attendance-server:
    environment:
      - SERVER_PORT=5000
      - CHATTERING_THRESHOLD=15
      - DEFAULT_SEARCH_LIMIT=200
      - FLASK_ENV=production
```

### 方法3: .envファイル（オプション）

```bash
# .env
SERVER_PORT=5000
CHATTERING_THRESHOLD=15
DEFAULT_SEARCH_LIMIT=200
```

※ `.env` を使用する場合は `python-dotenv` パッケージが必要

---

## 🔄 既存コードへの適用例

### Before（現在）
```python
# server.py
app.run(host='0.0.0.0', port=5000, debug=False)

# utils.py
CHATTERING_THRESHOLD_SECONDS = int(os.environ.get('CHATTERING_THRESHOLD', '10'))

# api.py
limit = safe_int(request.args.get('limit', '100'), 100)
```

### After（改善後）
```python
# server.py
from config import Config
app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)

# utils.py
from config import Config
threshold = Config.CHATTERING_THRESHOLD_SECONDS

# api.py
from config import Config
limit = safe_int(request.args.get('limit', str(Config.DEFAULT_SEARCH_LIMIT)), Config.DEFAULT_SEARCH_LIMIT)
```

---

## ✅ メリット

1. **一元管理**: 設定値が一箇所に集約
2. **環境対応**: 開発/本番/Docker環境で簡単に切り替え
3. **柔軟性**: 環境変数で動的に変更可能
4. **保守性**: 設定値の変更が容易
5. **可読性**: 設定の意図が明確

---

## 🚀 実装ステップ

1. ✅ `config.py` の作成（提案済み）
2. ⏳ 既存コードを `config.py` を使用するように変更
3. ⏳ `docker-compose.yml` に環境変数設定を追加
4. ⏳ ドキュメント更新

---

## 📌 推奨事項

### 本番環境での設定例

```yaml
# docker-compose.yml
environment:
  - FLASK_ENV=production
  - SERVER_PORT=5000
  - CHATTERING_THRESHOLD=10
  - DEFAULT_SEARCH_LIMIT=100
  - PAYROLL_START_DAY=16
  - PAYROLL_END_DAY=15
```

### 開発環境での設定例

```bash
# .env（開発用）
FLASK_ENV=development
FLASK_DEBUG=True
SERVER_PORT=5000
CHATTERING_THRESHOLD=5  # 開発時は短めに設定
```

---

## 🔍 設定値の確認方法

```python
# 起動時に設定値を表示
from config import Config
print(f"サーバー: {Config.HOST}:{Config.PORT}")
print(f"チャタリング閾値: {Config.CHATTERING_THRESHOLD_SECONDS}秒")
print(f"検索上限: {Config.DEFAULT_SEARCH_LIMIT}件")
```

---

この構造により、設定値の管理が格段に容易になります。

