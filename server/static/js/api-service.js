/**
 * 統一APIサービスモジュール
 * 全てのAPI呼び出しを集約し、一貫したエラーハンドリングを提供
 */

// AttendanceSystemが存在しない場合は初期化
if (typeof AttendanceSystem === 'undefined') {
    window.AttendanceSystem = window.AttendanceSystem || {};
}

// API統一サービス名前空間
AttendanceSystem.API = AttendanceSystem.API || {};

/**
 * APIレスポンスのラッパークラス
 */
class ApiResponse {
    constructor(success, data, message, error = null) {
        this.success = success;
        this.data = data;
        this.message = message;
        this.error = error;
    }
    
    static success(data, message = 'OK') {
        return new ApiResponse(true, data, message);
    }
    
    static error(message, error = null, data = null) {
        return new ApiResponse(false, data, message, error);
    }
}

/**
 * 統一されたHTTPリクエスト処理
 * @param {string} url - API URL
 * @param {Object} options - fetch オプション
 * @returns {Promise<ApiResponse>}
 */
async function makeRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    };
    
    try {
        console.log(`[API] ${options.method || 'GET'} ${url}`);
        
        const response = await fetch(url, defaultOptions);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`[API] HTTP Error ${response.status}:`, errorText);
            return ApiResponse.error(
                `HTTP ${response.status}: ${errorText.substring(0, 100)}`,
                response,
                null
            );
        }
        
        // Content-Type を確認
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const errorText = await response.text();
            console.error('[API] 無効なContent-Type:', contentType);
            return ApiResponse.error(
                `無効なレスポンス形式: ${contentType}`,
                response,
                null
            );
        }
        
        const data = await response.json();
        console.log(`[API] Success:`, data);
        
        return ApiResponse.success(data, 'API呼び出し成功');
        
    } catch (error) {
        console.error('[API] リクエストエラー:', error);
        return ApiResponse.error(
            `ネットワークエラー: ${error.message}`,
            error,
            null
        );
    }
}

/**
 * 従業員API統一サービス
 */
AttendanceSystem.API.Employees = {
    /**
     * 全従業員データを取得
     * @returns {Promise<ApiResponse>}
     */
    async getAll() {
        const response = await makeRequest('/api/employees');
        if (response.success && response.data.status === 'success') {
            // AttendanceSystem.Data.employees にキャッシュ
            AttendanceSystem.Data.employees = response.data.data || [];
            return ApiResponse.success(response.data.data, '従業員データ取得成功');
        } else {
            return ApiResponse.error(
                response.data?.message || response.message || '従業員データの取得に失敗',
                response.error,
                null
            );
        }
    },

    /**
     * セクション一覧を取得
     * @returns {Promise<ApiResponse>}
     */
    async getSections() {
        const employeesResponse = await this.getAll();
        if (!employeesResponse.success) {
            return employeesResponse;
        }
        
        const sections = [...new Set(employeesResponse.data.map(emp => emp.section || '設備'))].sort();
        return ApiResponse.success(sections, 'セクション一覧取得成功');
    },

    /**
     * セクションでフィルタリングされた従業員を取得
     * @param {string} sectionName - セクション名
     * @returns {Promise<ApiResponse>}
     */
    async getBySection(sectionName = null) {
        const employeesResponse = await this.getAll();
        if (!employeesResponse.success) {
            return employeesResponse;
        }
        
        let filtered = employeesResponse.data;
        if (sectionName) {
            filtered = employeesResponse.data.filter(emp => (emp.section || '設備') === sectionName);
        }
        
        // 名前でソート
        filtered.sort((a, b) => {
            const nameA = a.name || '';
            const nameB = b.name || '';
            return nameA.localeCompare(nameB, 'ja');
        });
        
        return ApiResponse.success(filtered, `従業員データ取得成功 (${filtered.length}名)`);
    }
};

/**
 * 検索API統一サービス
 */
AttendanceSystem.API.Search = {
    /**
     * 勤怠検索
     * @param {Object} params - 検索パラメータ
     * @returns {Promise<ApiResponse>}
     */
    async attendance(params) {
        const queryParams = new URLSearchParams();
        Object.keys(params).forEach(key => {
            if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
                queryParams.append(key, params[key]);
            }
        });
        
        const url = `/api/search?${queryParams}`;
        const response = await makeRequest(url);
        
        if (response.success && response.data.status === 'success') {
            // AttendanceSystem.Data.searchResults にキャッシュ
            AttendanceSystem.Data.searchResults = response.data.results || [];
            return ApiResponse.success(response.data, '検索成功');
        } else {
            return ApiResponse.error(
                response.data?.message || response.message || '検索に失敗',
                response.error,
                null
            );
        }
    }
};

/**
 * 勤怠チェックAPI統一サービス
 */
AttendanceSystem.API.Check = {
    /**
     * 勤怠チェック実行
     * @param {Object} params - チェックパラメータ
     * @returns {Promise<ApiResponse>}
     */
    async attendance(params) {
        const queryParams = new URLSearchParams();
        Object.keys(params).forEach(key => {
            if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
                queryParams.append(key, params[key]);
            }
        });
        
        const url = `/api/attendance_check?${queryParams}`;
        const response = await makeRequest(url);
        
        if (response.success && response.data.status === 'success') {
            return ApiResponse.success(response.data.data || response.data, 'チェック成功');
        } else {
            return ApiResponse.error(
                response.data?.message || response.message || '勤怠チェックに失敗',
                response.error,
                null
            );
        }
    },

    /**
     * チェックステータス取得
     * @param {string} employeeNum - 従業員番号
     * @param {string} workDate - 勤務日
     * @param {string} checkType - チェックタイプ
     * @returns {Promise<ApiResponse>}
     */
    async getStatus(employeeNum, workDate, checkType) {
        const params = new URLSearchParams();
        params.append('employee_num', employeeNum);
        params.append('work_date', workDate);
        params.append('check_type', checkType);
        
        const url = `/api/attendance-check-status?${params}`;
        const response = await makeRequest(url);
        
        if (response.success) {
            return ApiResponse.success(response.data, 'ステータス取得成功');
        } else {
            return response;
        }
    },

    /**
     * チェックステータス更新
     * @param {Object} statusData - ステータスデータ
     * @returns {Promise<ApiResponse>}
     */
    async updateStatus(statusData) {
        const response = await makeRequest('/api/attendance-check-status', {
            method: 'POST',
            body: JSON.stringify(statusData)
        });
        
        if (response.success) {
            return ApiResponse.success(response.data, 'ステータス更新成功');
        } else {
            return response;
        }
    }
};

/**
 * 汎用APIサービス
 */
AttendanceSystem.API.Common = {
    /**
     * ヘルスチェック
     * @returns {Promise<ApiResponse>}
     */
    async health() {
        const response = await makeRequest('/api/health');
        
        if (response.success) {
            return ApiResponse.success(response.data, 'サーバー正常');
        } else {
            return response;
        }
    }
};

console.log('[API Service] 統一APIサービスが初期化されました');