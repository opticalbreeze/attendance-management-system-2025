# メンテナンス性改善・モニタリングシステム実装ガイド

## 概要
このガイドでは、提案した改善内容を段階的に実装する手順を説明します。

---

## Phase 1: 構造化ログシステムの導入

### ステップ1: 拡張ログ設定モジュールの導入

#### 1.1 ファイルの配置
既に作成済みの `logger_config_enhanced.py` を使用します。

#### 1.2 既存コードへの統合

**方法A: 段階的移行（推奨）**

既存の `logger_config.py` を以下のように更新：

```python
# logger_config.py の先頭に追加
try:
    from logger_config_enhanced import (
        setup_enhanced_logger,
        ContextLogger,
        StructuredFormatter
    )
    USE_ENHANCED_LOGGING = True
except ImportError:
    USE_ENHANCED_LOGGING = False
    # 既存の実装を維持

def setup_logger(name=None, log_level=None):
    """既存のインターフェースを維持しつつ、拡張ログを使用"""
    if USE_ENHANCED_LOGGING:
        return setup_enhanced_logger(name, log_level)
    else:
        # 既存の実装
        ...
```

**方法B: 完全置き換え**

`logger_config.py` を `logger_config_enhanced.py` の内容で置き換えます。

#### 1.3 使用例

```python
# 既存コード
from logger_config import setup_logger
logger = setup_logger('my_module')
logger.info('メッセージ')

# コンテキスト付きログ（新機能）
from logger_config_enhanced import ContextLogger
context_logger = ContextLogger(logger, employee_id='12345', request_id='req-001')
context_logger.info('従業員の処理を開始')
```

### ステップ2: ログディレクトリの作成

```bash
# ログディレクトリを作成
mkdir -p logs

# Docker環境の場合、docker-compose.ymlに追加
volumes:
  - ./logs:/app/logs
```

### ステップ3: 環境変数の設定

```bash
# .env ファイルまたは docker-compose.yml に追加
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/app.log
FLASK_ENV=development  # または production, docker
```

---

## Phase 2: モニタリングAPIの導入

### ステップ1: API Blueprintの登録

`server.py` に以下を追加：

```python
from api_monitoring import monitoring_bp

# Blueprintを登録
app.register_blueprint(monitoring_bp)
```

### ステップ2: ルートの確認

```bash
# サーバー起動後、以下のエンドポイントが利用可能：
# GET /api/monitoring/errors
# GET /api/monitoring/warnings
# GET /api/monitoring/stats
# POST /api/monitoring/client-error
```

### ステップ3: 動作確認

```bash
# エラー一覧を取得
curl http://localhost:5001/api/monitoring/errors?hours=24

# 統計情報を取得
curl http://localhost:5001/api/monitoring/stats?hours=24
```

---

## Phase 3: ブラウザデバッグパネルの導入

### ステップ1: JavaScriptファイルの配置

`static/js/debug-panel.js` を作成（提案書のコードをコピー）

### ステップ2: CSSファイルの配置

`static/css/debug-panel.css` を作成（提案書のコードをコピー）

### ステップ3: テンプレートへの追加

開発環境のテンプレート（例: `templates_dev/search.html`）の `<head>` セクションに追加：

```html
{% if config.DEBUG %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/debug-panel.css') }}">
<script src="{{ url_for('static', filename='js/debug-panel.js') }}"></script>
{% endif %}
```

### ステップ4: 動作確認

1. 開発環境（5001）にアクセス
2. ブラウザの下部にデバッグパネルが表示されることを確認
3. エラーを発生させて、パネルに表示されることを確認

---

## Phase 4: エラー統計ダッシュボードの導入

### ステップ1: HTMLテンプレートの作成

`templates/monitoring.html` を作成（提案書のコードをコピー）

### ステップ2: JavaScriptファイルの作成

`static/js/monitoring.js` を作成（提案書のコードをコピー）

### ステップ3: CSSファイルの作成

`static/css/monitoring.css` を作成：

```css
.dashboard-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    background: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stat-card.error {
    border-left: 4px solid #f48771;
}

.stat-card.warning {
    border-left: 4px solid #ffa500;
}

.stat-value {
    font-size: 32px;
    font-weight: bold;
    margin-bottom: 8px;
}

.stat-label {
    color: #666;
    font-size: 14px;
}

.error-list {
    margin-top: 30px;
}

.error-item {
    background: #f5f5f5;
    border-left: 3px solid #f48771;
    padding: 12px;
    margin-bottom: 12px;
    border-radius: 4px;
}

.error-header {
    display: flex;
    gap: 12px;
    margin-bottom: 8px;
    font-size: 12px;
}

.error-time {
    color: #666;
}

.error-category {
    background: #007acc;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
}

.error-severity {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
}

.error-severity.high {
    background: #f48771;
    color: white;
}

.error-severity.medium {
    background: #ffa500;
    color: white;
}

.error-message {
    margin-top: 8px;
    font-weight: 500;
}

.error-stack {
    margin-top: 8px;
    font-size: 11px;
    color: #666;
    white-space: pre-wrap;
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 8px;
    border-radius: 4px;
    overflow-x: auto;
}
```

### ステップ4: ルートの追加

`server.py` に追加：

```python
@app.route('/monitoring')
def monitoring_dashboard():
    """モニタリングダッシュボード"""
    return render_template('monitoring.html')
```

### ステップ5: 動作確認

1. `http://localhost:5001/monitoring` にアクセス
2. エラー統計が表示されることを確認
3. 自動更新（30秒ごと）が動作することを確認

---

## 既存コードへの影響を最小限にする方法

### 1. 後方互換性の維持

既存の `logger_config.py` のインターフェースを維持：

```python
# 既存コードはそのまま動作
from logger_config import setup_logger
logger = setup_logger('my_module')
logger.info('メッセージ')
```

### 2. 環境変数による制御

```python
# 拡張機能を環境変数で制御
ENABLE_ENHANCED_LOGGING = os.environ.get('ENABLE_ENHANCED_LOGGING', 'false').lower() == 'true'
ENABLE_MONITORING_API = os.environ.get('ENABLE_MONITORING_API', 'true').lower() == 'true'
ENABLE_DEBUG_PANEL = os.environ.get('ENABLE_DEBUG_PANEL', 'false').lower() == 'true'
```

### 3. 段階的な導入

1. **開発環境（5001）でテスト**
   - まず5001環境で全ての機能を有効化
   - 動作確認とパフォーマンステスト

2. **本番環境（5000）への展開**
   - モニタリングAPIのみ有効化
   - デバッグパネルは無効化

---

## トラブルシューティング

### ログファイルが作成されない

**原因**: ログディレクトリの権限問題

**解決策**:
```bash
# ログディレクトリの権限を確認
ls -la logs/

# 権限を設定
chmod 755 logs/
```

### JSON形式のログが読みにくい

**原因**: 開発環境でもJSON形式になっている

**解決策**: `logger_config_enhanced.py` の `setup_enhanced_logger` 関数で、開発環境では読みやすい形式を使用する設定を確認

### モニタリングAPIが404エラー

**原因**: Blueprintが登録されていない

**解決策**: `server.py` で `app.register_blueprint(monitoring_bp)` が実行されているか確認

### デバッグパネルが表示されない

**原因**: 開発環境でない、またはJavaScriptエラー

**解決策**:
1. ブラウザのコンソールでエラーを確認
2. `localStorage.setItem('debug_panel_enabled', 'true')` を実行して強制有効化

---

## パフォーマンスへの影響

### ログファイルのサイズ管理

```python
# logger_config_enhanced.py に追加
from logging.handlers import RotatingFileHandler

# ログローテーションを設定
handler = RotatingFileHandler(
    'logs/errors.jsonl',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

### ログ読み込みの最適化

`api_monitoring.py` の `load_log_entries` 関数は、最新のログから読み込むように最適化されていますが、大量のログがある場合は以下の改善を検討：

1. ログファイルを時間別に分割
2. インデックスファイルを作成
3. データベースにログを保存（長期保存が必要な場合）

---

## 次のステップ

1. **Phase 1の実装**: 構造化ログシステムの導入
2. **動作確認**: 開発環境でテスト
3. **Phase 2の実装**: モニタリングAPIの導入
4. **Phase 3の実装**: デバッグパネルの導入
5. **Phase 4の実装**: ダッシュボードの導入
6. **本番環境への展開**: 段階的に本番環境に展開

---

## 参考資料

- `ARCHITECTURE_IMPROVEMENT_PROPOSAL.md`: 詳細な提案書
- `logger_config_enhanced.py`: 拡張ログ設定モジュール
- `api_monitoring.py`: モニタリングAPI
