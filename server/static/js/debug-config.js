/**
 * デバッグ出力設定システム
 * デバッグ出力の有効/無効を簡単に制御できる
 */

// デバッグ設定オブジェクト
window.DebugConfig = {
    // デバッグモード（環境変数またはlocalStorageから取得）
    enabled: (() => {
        // URLパラメータで制御
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('debug')) {
            return urlParams.get('debug') === 'true';
        }
        // localStorageで制御
        const stored = localStorage.getItem('debug_enabled');
        if (stored !== null) {
            return stored === 'true';
        }
        // デフォルト: 開発環境では有効、本番環境では無効
        return window.location.hostname === 'localhost' || 
               window.location.port === '5001' ||
               window.location.hostname.includes('dev');
    })(),
    
    // モジュール別のデバッグ設定
    modules: {
        search: true,
        api: true,
        errors: true,
        warnings: true,
        performance: false
    },
    
    // デバッグレベル
    level: 'info', // 'debug', 'info', 'warn', 'error', 'none'
    
    /**
     * デバッグ出力を有効化/無効化
     */
    setEnabled(enabled) {
        this.enabled = enabled;
        localStorage.setItem('debug_enabled', enabled.toString());
    },
    
    /**
     * モジュール別のデバッグを有効化/無効化
     */
    setModuleEnabled(module, enabled) {
        this.modules[module] = enabled;
        localStorage.setItem(`debug_module_${module}`, enabled.toString());
    },
    
    /**
     * デバッグレベルを設定
     */
    setLevel(level) {
        this.level = level;
        localStorage.setItem('debug_level', level);
    },
    
    /**
     * デバッグ出力が有効かチェック
     */
    isEnabled(module = null) {
        if (!this.enabled) return false;
        if (module && !this.modules[module]) return false;
        return true;
    },
    
    /**
     * デバッグログを出力
     */
    log(module, level, ...args) {
        if (!this.isEnabled(module)) return;
        
        const levels = ['debug', 'info', 'warn', 'error'];
        const currentLevelIndex = levels.indexOf(this.level);
        const messageLevelIndex = levels.indexOf(level);
        
        if (messageLevelIndex < currentLevelIndex) return;
        
        const prefix = `[DEBUG:${module || 'GLOBAL'}]`;
        const timestamp = new Date().toISOString();
        
        switch (level) {
            case 'error':
                console.error(prefix, timestamp, ...args);
                break;
            case 'warn':
                console.warn(prefix, timestamp, ...args);
                break;
            case 'info':
                console.info(prefix, timestamp, ...args);
                break;
            case 'debug':
            default:
                console.log(prefix, timestamp, ...args);
                break;
        }
    }
};

// グローバルなデバッグ関数を提供
window.debugLog = function(module, ...args) {
    DebugConfig.log(module || 'GLOBAL', 'info', ...args);
};

window.debugError = function(module, ...args) {
    DebugConfig.log(module || 'GLOBAL', 'error', ...args);
};

window.debugWarn = function(module, ...args) {
    DebugConfig.log(module || 'GLOBAL', 'warn', ...args);
};

window.debugDebug = function(module, ...args) {
    DebugConfig.log(module || 'GLOBAL', 'debug', ...args);
};

// ブラウザコンソールで簡単に制御できるようにする
if (typeof window !== 'undefined') {
    window.enableDebug = () => DebugConfig.setEnabled(true);
    window.disableDebug = () => DebugConfig.setEnabled(false);
    window.setDebugLevel = (level) => DebugConfig.setLevel(level);
    window.setDebugModule = (module, enabled) => DebugConfig.setModuleEnabled(module, enabled);
}
