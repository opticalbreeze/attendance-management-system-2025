# アーキテクチャ改善提案書

## 概要
プロのアーキテクト視点から、メンテナンス性向上とエラー・警告モニタリングシステムの改善提案をまとめました。

---

## 1. 構造化ログシステムの導入

### 現状の問題点
- プレーンテキスト形式のログで、解析が困難
- エラー・警告・情報が混在し、フィルタリングが困難
- ログレベル別の出力先分離がない

### 提案内容

#### 1.1 JSON形式の構造化ログ
```python
# logger_config.py に追加
import json
from datetime import datetime

class StructuredFormatter(logging.Formatter):
    """JSON形式の構造化ログフォーマッター"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # エラー情報を追加
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # 追加のコンテキスト情報
        if hasattr(record, 'context'):
            log_data['context'] = record.context
        
        # エラー・警告の分類
        if record.levelname in ['ERROR', 'WARNING']:
            log_data['category'] = self._categorize_error(record)
            log_data['severity'] = self._get_severity(record)
        
        return json.dumps(log_data, ensure_ascii=False)
    
    def _categorize_error(self, record):
        """エラーをカテゴリ分類"""
        message = record.getMessage().lower()
        if 'database' in message or 'sql' in message:
            return 'database'
        elif 'api' in message or 'http' in message:
            return 'api'
        elif 'attendance' in message or '打刻' in message:
            return 'attendance'
        elif 'notification' in message or 'お知らせ' in message:
            return 'notification'
        else:
            return 'general'
    
    def _get_severity(self, record):
        """重要度を判定"""
        if record.levelname == 'ERROR':
            return 'high'
        elif record.levelname == 'WARNING':
            return 'medium'
        else:
            return 'low'
```

#### 1.2 ログレベル別の出力先分離
```python
# logger_config.py に追加
def setup_separated_loggers():
    """ログレベル別のロガーを設定"""
    
    # エラー専用ロガー
    error_logger = logging.getLogger('errors')
    error_handler = logging.FileHandler('logs/errors.jsonl', encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter())
    error_logger.addHandler(error_handler)
    
    # 警告専用ロガー
    warning_logger = logging.getLogger('warnings')
    warning_handler = logging.FileHandler('logs/warnings.jsonl', encoding='utf-8')
    warning_handler.setLevel(logging.WARNING)
    warning_handler.setFormatter(StructuredFormatter())
    warning_logger.addHandler(warning_handler)
    
    # デバッグ専用ロガー（開発環境のみ）
    if os.environ.get('FLASK_ENV') == 'development':
        debug_logger = logging.getLogger('debug')
        debug_handler = logging.FileHandler('logs/debug.jsonl', encoding='utf-8')
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(StructuredFormatter())
        debug_logger.addHandler(debug_handler)
```

### 効果
- ログの解析と検索が容易になる
- エラー・警告の自動分類が可能
- ログ分析ツールとの連携が容易

---

## 2. エラー・警告専用モニタリングAPI

### 提案内容

#### 2.1 リアルタイムエラー取得API
```python
# api_monitoring.py (新規作成)
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import json
from pathlib import Path

monitoring_bp = Blueprint('monitoring', __name__)

@monitoring_bp.route('/api/monitoring/errors', methods=['GET'])
def get_errors():
    """エラー一覧を取得"""
    try:
        hours = int(request.args.get('hours', 24))
        category = request.args.get('category')
        severity = request.args.get('severity')
        
        errors = []
        error_log_path = Path('logs/errors.jsonl')
        
        if error_log_path.exists():
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            with open(error_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        log_time = datetime.fromisoformat(log_entry['timestamp'])
                        
                        if log_time >= cutoff_time:
                            # フィルタリング
                            if category and log_entry.get('category') != category:
                                continue
                            if severity and log_entry.get('severity') != severity:
                                continue
                            
                            errors.append(log_entry)
                    except json.JSONDecodeError:
                        continue
        
        # 時系列でソート（新しい順）
        errors.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'status': 'success',
            'count': len(errors),
            'errors': errors[:100]  # 最新100件まで
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monitoring_bp.route('/api/monitoring/warnings', methods=['GET'])
def get_warnings():
    """警告一覧を取得"""
    # 同様の実装
    pass

@monitoring_bp.route('/api/monitoring/stats', methods=['GET'])
def get_error_stats():
    """エラー統計を取得"""
    try:
        hours = int(request.args.get('hours', 24))
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        stats = {
            'total_errors': 0,
            'total_warnings': 0,
            'by_category': {},
            'by_severity': {},
            'recent_errors': []
        }
        
        # エラーログを解析
        error_log_path = Path('logs/errors.jsonl')
        if error_log_path.exists():
            with open(error_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        log_time = datetime.fromisoformat(log_entry['timestamp'])
                        
                        if log_time >= cutoff_time:
                            stats['total_errors'] += 1
                            
                            category = log_entry.get('category', 'unknown')
                            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
                            
                            severity = log_entry.get('severity', 'unknown')
                            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
                            
                            if len(stats['recent_errors']) < 10:
                                stats['recent_errors'].append(log_entry)
                    except json.JSONDecodeError:
                        continue
        
        # 警告ログも同様に解析
        warning_log_path = Path('logs/warnings.jsonl')
        if warning_log_path.exists():
            with open(warning_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        log_time = datetime.fromisoformat(log_entry['timestamp'])
                        
                        if log_time >= cutoff_time:
                            stats['total_warnings'] += 1
                    except json.JSONDecodeError:
                        continue
        
        return jsonify({
            'status': 'success',
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
```

#### 2.2 WebSocketによるリアルタイム通知（オプション）
```python
# api_monitoring.py に追加（Flask-SocketIO使用）
from flask_socketio import SocketIO, emit

socketio = SocketIO(cors_allowed_origins="*")

@socketio.on('connect')
def handle_connect():
    """クライアント接続時の処理"""
    emit('connected', {'message': 'モニタリング接続完了'})

@socketio.on('subscribe_errors')
def handle_subscribe_errors():
    """エラー通知の購読"""
    # エラーログファイルを監視して、新しいエラーを通知
    pass
```

### 効果
- リアルタイムでエラー・警告を監視可能
- エラー統計の可視化が容易
- 問題の早期発見が可能

---

## 3. ブラウザ開発者向けデバッグパネル

### 提案内容

#### 3.1 デバッグパネルコンポーネント
```javascript
// static/js/debug-panel.js (新規作成)
window.DebugPanel = {
    enabled: false,
    panel: null,
    
    init() {
        // 開発環境でのみ有効化
        if (window.location.hostname === 'localhost' || 
            window.location.port === '5001' ||
            localStorage.getItem('debug_panel_enabled') === 'true') {
            this.enabled = true;
            this.createPanel();
            this.startMonitoring();
        }
    },
    
    createPanel() {
        // デバッグパネルのHTMLを作成
        const panel = document.createElement('div');
        panel.id = 'debug-panel';
        panel.innerHTML = `
            <div class="debug-panel-header">
                <h3>🐛 デバッグパネル</h3>
                <button onclick="DebugPanel.toggle()">折りたたむ</button>
            </div>
            <div class="debug-panel-tabs">
                <button onclick="DebugPanel.showTab('errors')">エラー</button>
                <button onclick="DebugPanel.showTab('warnings')">警告</button>
                <button onclick="DebugPanel.showTab('api')">API</button>
                <button onclick="DebugPanel.showTab('performance')">パフォーマンス</button>
            </div>
            <div class="debug-panel-content">
                <div id="debug-errors" class="debug-tab-content"></div>
                <div id="debug-warnings" class="debug-tab-content" style="display:none"></div>
                <div id="debug-api" class="debug-tab-content" style="display:none"></div>
                <div id="debug-performance" class="debug-tab-content" style="display:none"></div>
            </div>
        `;
        document.body.appendChild(panel);
        this.panel = panel;
    },
    
    startMonitoring() {
        // エラー監視
        window.addEventListener('error', (event) => {
            this.logError({
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                error: event.error
            });
        });
        
        // Promise rejection監視
        window.addEventListener('unhandledrejection', (event) => {
            this.logError({
                message: 'Unhandled Promise Rejection',
                error: event.reason
            });
        });
        
        // API呼び出し監視
        this.interceptFetch();
        
        // パフォーマンス監視
        this.monitorPerformance();
    },
    
    interceptFetch() {
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            const startTime = performance.now();
            const url = args[0];
            
            try {
                const response = await originalFetch(...args);
                const endTime = performance.now();
                const duration = endTime - startTime;
                
                this.logAPI({
                    url,
                    method: args[1]?.method || 'GET',
                    status: response.status,
                    duration,
                    timestamp: new Date().toISOString()
                });
                
                return response;
            } catch (error) {
                this.logError({
                    message: `API呼び出しエラー: ${url}`,
                    error: error.message
                });
                throw error;
            }
        };
    },
    
    logError(error) {
        const errorsTab = document.getElementById('debug-errors');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'debug-error-item';
        errorDiv.innerHTML = `
            <div class="error-time">${new Date().toLocaleTimeString()}</div>
            <div class="error-message">${error.message}</div>
            ${error.filename ? `<div class="error-location">${error.filename}:${error.lineno}</div>` : ''}
            ${error.error ? `<pre class="error-stack">${error.error.stack || error.error}</pre>` : ''}
        `;
        errorsTab.insertBefore(errorDiv, errorsTab.firstChild);
        
        // サーバーにも送信
        this.sendToServer('error', error);
    },
    
    logAPI(apiCall) {
        const apiTab = document.getElementById('debug-api');
        const apiDiv = document.createElement('div');
        apiDiv.className = 'debug-api-item';
        const statusClass = apiCall.status >= 400 ? 'error' : 'success';
        apiDiv.innerHTML = `
            <div class="api-time">${new Date(apiCall.timestamp).toLocaleTimeString()}</div>
            <div class="api-method">${apiCall.method}</div>
            <div class="api-url">${apiCall.url}</div>
            <div class="api-status ${statusClass}">${apiCall.status}</div>
            <div class="api-duration">${apiCall.duration.toFixed(2)}ms</div>
        `;
        apiTab.insertBefore(apiDiv, apiTab.firstChild);
    },
    
    monitorPerformance() {
        // ページ読み込み時間の監視
        window.addEventListener('load', () => {
            const perfData = performance.timing;
            const loadTime = perfData.loadEventEnd - perfData.navigationStart;
            
            const perfTab = document.getElementById('debug-performance');
            const perfDiv = document.createElement('div');
            perfDiv.innerHTML = `
                <div>ページ読み込み時間: ${loadTime}ms</div>
                <div>DOM構築時間: ${perfData.domContentLoadedEventEnd - perfData.navigationStart}ms</div>
            `;
            perfTab.appendChild(perfDiv);
        });
    },
    
    sendToServer(type, data) {
        // サーバーにエラー情報を送信
        fetch('/api/monitoring/client-error', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, data, timestamp: new Date().toISOString() })
        }).catch(() => {
            // 送信失敗は無視
        });
    },
    
    showTab(tabName) {
        // タブ切り替え
        document.querySelectorAll('.debug-tab-content').forEach(tab => {
            tab.style.display = 'none';
        });
        document.getElementById(`debug-${tabName}`).style.display = 'block';
    },
    
    toggle() {
        // パネルの表示/非表示
        if (this.panel) {
            this.panel.style.display = this.panel.style.display === 'none' ? 'block' : 'none';
        }
    }
};

// ページ読み込み時に初期化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => DebugPanel.init());
} else {
    DebugPanel.init();
}
```

#### 3.2 デバッグパネルのCSS
```css
/* static/css/debug-panel.css (新規作成) */
#debug-panel {
    position: fixed;
    bottom: 0;
    right: 0;
    width: 500px;
    max-height: 400px;
    background: #1e1e1e;
    color: #d4d4d4;
    border-top: 2px solid #007acc;
    z-index: 10000;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    overflow-y: auto;
}

.debug-panel-header {
    background: #007acc;
    color: white;
    padding: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.debug-panel-tabs {
    display: flex;
    background: #252526;
    border-bottom: 1px solid #3e3e42;
}

.debug-panel-tabs button {
    flex: 1;
    padding: 8px;
    background: transparent;
    border: none;
    color: #cccccc;
    cursor: pointer;
}

.debug-panel-tabs button:hover {
    background: #2a2d2e;
}

.debug-tab-content {
    padding: 8px;
    max-height: 300px;
    overflow-y: auto;
}

.debug-error-item {
    padding: 8px;
    margin-bottom: 8px;
    background: #3a1d1d;
    border-left: 3px solid #f48771;
}

.debug-api-item {
    padding: 4px;
    margin-bottom: 4px;
    display: grid;
    grid-template-columns: 60px 60px 1fr 50px 60px;
    gap: 8px;
    font-size: 11px;
}

.api-status.error {
    color: #f48771;
}

.api-status.success {
    color: #89d185;
}
```

### 効果
- ブラウザ上でリアルタイムにデバッグ情報を確認可能
- API呼び出しの監視が容易
- エラーの再現が容易

---

## 4. エラー統計ダッシュボード

### 提案内容

#### 4.1 ダッシュボードHTML
```html
<!-- templates/monitoring.html (新規作成) -->
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>エラー・警告モニタリングダッシュボード</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/monitoring.css') }}">
</head>
<body>
    <div class="dashboard-container">
        <h1>📊 エラー・警告モニタリングダッシュボード</h1>
        
        <div class="stats-grid">
            <div class="stat-card error">
                <div class="stat-value" id="total-errors">-</div>
                <div class="stat-label">エラー（24時間）</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-value" id="total-warnings">-</div>
                <div class="stat-label">警告（24時間）</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="error-rate">-</div>
                <div class="stat-label">エラー率</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>エラーカテゴリ別分布</h2>
            <canvas id="category-chart"></canvas>
        </div>
        
        <div class="error-list">
            <h2>最近のエラー</h2>
            <div id="recent-errors"></div>
        </div>
    </div>
    
    <script src="{{ url_for('static', filename='js/monitoring.js') }}"></script>
</body>
</html>
```

#### 4.2 ダッシュボードJavaScript
```javascript
// static/js/monitoring.js (新規作成)
class MonitoringDashboard {
    constructor() {
        this.updateInterval = 30000; // 30秒ごとに更新
        this.init();
    }
    
    async init() {
        await this.loadStats();
        await this.loadRecentErrors();
        this.startAutoRefresh();
    }
    
    async loadStats() {
        try {
            const response = await fetch('/api/monitoring/stats?hours=24');
            const data = await response.json();
            
            if (data.status === 'success') {
                const stats = data.stats;
                document.getElementById('total-errors').textContent = stats.total_errors;
                document.getElementById('total-warnings').textContent = stats.total_warnings;
                
                // エラー率を計算
                const total = stats.total_errors + stats.total_warnings;
                const errorRate = total > 0 ? (stats.total_errors / total * 100).toFixed(1) : 0;
                document.getElementById('error-rate').textContent = `${errorRate}%`;
                
                // チャートを更新
                this.updateChart(stats.by_category);
            }
        } catch (error) {
            console.error('統計情報の取得に失敗:', error);
        }
    }
    
    async loadRecentErrors() {
        try {
            const response = await fetch('/api/monitoring/errors?hours=24&limit=20');
            const data = await response.json();
            
            if (data.status === 'success') {
                const container = document.getElementById('recent-errors');
                container.innerHTML = '';
                
                data.errors.forEach(error => {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'error-item';
                    errorDiv.innerHTML = `
                        <div class="error-header">
                            <span class="error-time">${new Date(error.timestamp).toLocaleString()}</span>
                            <span class="error-category">${error.category || 'general'}</span>
                            <span class="error-severity ${error.severity}">${error.severity}</span>
                        </div>
                        <div class="error-message">${error.message}</div>
                        ${error.exception ? `<pre class="error-stack">${error.exception.traceback}</pre>` : ''}
                    `;
                    container.appendChild(errorDiv);
                });
            }
        } catch (error) {
            console.error('エラー一覧の取得に失敗:', error);
        }
    }
    
    updateChart(categoryData) {
        // Chart.jsなどを使用してチャートを描画
        // 実装は省略
    }
    
    startAutoRefresh() {
        setInterval(() => {
            this.loadStats();
            this.loadRecentErrors();
        }, this.updateInterval);
    }
}

// ページ読み込み時に初期化
new MonitoringDashboard();
```

### 効果
- エラー・警告の発生状況を可視化
- 問題の傾向を把握しやすい
- 早期の異常検知が可能

---

## 5. 設定管理の改善

### 提案内容

#### 5.1 環境別設定ファイル
```python
# config/development.py
class DevelopmentConfig:
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    ENABLE_DEBUG_PANEL = True
    ENABLE_MONITORING_API = True

# config/production.py
class ProductionConfig:
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    ENABLE_DEBUG_PANEL = False
    ENABLE_MONITORING_API = True  # 本番でもモニタリングは有効

# config/docker.py
class DockerConfig:
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    ENABLE_DEBUG_PANEL = os.environ.get('ENABLE_DEBUG_PANEL', 'False').lower() == 'true'
```

#### 5.2 設定の一元管理
```python
# config/__init__.py
from .development import DevelopmentConfig
from .production import ProductionConfig
from .docker import DockerConfig

def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'docker': DockerConfig
    }
    
    return config_map.get(env, DevelopmentConfig)
```

### 効果
- 環境別の設定が明確になる
- 設定の変更が容易
- 設定ミスによる問題を防止

---

## 6. テスト容易性の向上

### 提案内容

#### 6.1 モック化しやすい構造
```python
# services/attendance_service.py
class AttendanceService:
    def __init__(self, db_connection=None, logger=None):
        self.db = db_connection or get_db_connection()
        self.logger = logger or setup_logger('attendance_service')
    
    def check_attendance(self, employee_id, date):
        # 実装
        pass

# テスト時はモックを注入可能
def test_check_attendance():
    mock_db = MockDatabase()
    mock_logger = MockLogger()
    service = AttendanceService(db_connection=mock_db, logger=mock_logger)
    # テスト実行
```

#### 6.2 依存性注入パターン
```python
# 依存性を外部から注入可能にする
def create_app(db=None, logger=None):
    app = Flask(__name__)
    
    # 依存性を注入
    app.db = db or get_db_connection()
    app.logger = logger or setup_logger()
    
    return app
```

### 効果
- ユニットテストが書きやすい
- モック化が容易
- テストの実行速度が向上

---

## 実装優先順位

### Phase 1: 即座に実装（高優先度）
1. ✅ 構造化ログシステム（JSON形式）
2. ✅ エラー・警告専用ログファイルの分離
3. ✅ エラー・警告モニタリングAPI

### Phase 2: 短期実装（中優先度）
4. ✅ ブラウザデバッグパネル
5. ✅ エラー統計ダッシュボード

### Phase 3: 長期実装（低優先度）
6. ✅ WebSocketによるリアルタイム通知
7. ✅ 設定管理の改善
8. ✅ テスト容易性の向上

---

## 期待される効果

1. **問題の早期発見**: エラー・警告をリアルタイムで監視可能
2. **デバッグ効率の向上**: 構造化ログとデバッグパネルで問題の特定が容易
3. **メンテナンス性の向上**: コードの構造化と設定管理の改善
4. **運用効率の向上**: エラー統計ダッシュボードで傾向を把握

---

## 次のステップ

1. Phase 1の実装を開始
2. 既存コードへの影響を最小限に抑えながら段階的に導入
3. 開発チームでのレビューとフィードバック収集
4. 本番環境への段階的な展開
