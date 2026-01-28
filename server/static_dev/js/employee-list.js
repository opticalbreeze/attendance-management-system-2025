/**
 * 従業員リスト管理共通モジュール
 * セクションによるフィルタリングと従業員選択を提供
 */

// グローバル変数を名前空間に移動（後方互換性のため残す）
let allEmployees = [];

/**
 * 従業員リストをAPIから読み込む（統一APIサービス使用）
 * @param {string} employeeSelectId - 従業員選択要素のID
 * @param {string} sectionSelectId - セクション選択要素のID
 * @param {string} defaultOptionText - デフォルトオプションのテキスト
 * @param {Function} onSuccess - 成功時のコールバック（オプション）
 */
async function loadEmployees(employeeSelectId, sectionSelectId, defaultOptionText = '従業員を選択してください', onSuccess = null) {
    const employeeSelect = document.getElementById(employeeSelectId);
    const sectionSelect = document.getElementById(sectionSelectId);
    
    if (!employeeSelect || !sectionSelect) {
        console.error('[employee-list] Required elements not found:', { employeeSelectId, sectionSelectId });
        return;
    }
    
    try {
        // 統一APIサービスを使用
        const employeesResponse = await AttendanceSystem.API.Employees.getAll();
        
        if (employeesResponse.success) {
            // 後方互換性のため全従業員データをグローバル変数にも保存
            allEmployees = employeesResponse.data;
            
            // セクション一覧を統一APIサービスから取得
            const sectionsResponse = await AttendanceSystem.API.Employees.getSections();
            
            if (sectionsResponse.success) {
                sectionSelect.innerHTML = '<option value="">すべてのセクション</option>';
                sectionsResponse.data.forEach(section => {
                    const option = document.createElement('option');
                    option.value = section;
                    option.textContent = section;
                    sectionSelect.appendChild(option);
                });
            } else {
                console.warn('[employee-list] セクション一覧取得に失敗:', sectionsResponse.message);
            }
            
            // 従業員リストを更新
            updateEmployeeList(employeeSelectId, sectionSelectId, defaultOptionText);
            
            // 成功コールバックを実行
            if (onSuccess && typeof onSuccess === 'function') {
                onSuccess(allEmployees);
            }
        } else {
            throw new Error(employeesResponse.message);
        }
    } catch (error) {
        console.error('[employee-list] Employee loading error:', error);
        employeeSelect.innerHTML = `<option value="">❌ 従業員データ読み込み失敗</option>`;
    }
}

/**
 * セクションで絞り込んだ従業員リストを更新
 * @param {string} employeeSelectId - 従業員選択要素のID
 * @param {string} sectionSelectId - セクション選択要素のID
 * @param {string} defaultOptionText - デフォルトオプションのテキスト
 */
function updateEmployeeList(employeeSelectId, sectionSelectId, defaultOptionText = '従業員を選択してください') {
    const employeeSelect = document.getElementById(employeeSelectId);
    const sectionSelect = document.getElementById(sectionSelectId);
    
    if (!employeeSelect || !sectionSelect) {
        console.error('[employee-list] Required elements not found:', { employeeSelectId, sectionSelectId });
        return;
    }
    
    const selectedSection = sectionSelect.value;
    
    // URLパラメータから従業員IDを取得
    const urlParams = new URLSearchParams(window.location.search);
    const urlEmployeeId = urlParams.get('employee_id');
    
    // 現在選択されている値を保存（URLパラメータがない場合のため）
    const currentSelectedValue = urlEmployeeId ? null : (employeeSelect.value || null);
    
    employeeSelect.innerHTML = `<option value="">▼ ${defaultOptionText}</option>`;
    
    // 名前空間データを優先、フォールバックでグローバル変数を使用
    const employees = AttendanceSystem.Data.employees.length > 0 
        ? AttendanceSystem.Data.employees 
        : allEmployees;
    
    // セクションでフィルタリング
    const filteredEmployees = selectedSection 
        ? employees.filter(emp => (emp.section || '設備') === selectedSection)
        : employees;
    
    // 従業員名でソート
    filteredEmployees.sort((a, b) => {
        const nameA = a.name || '';
        const nameB = b.name || '';
        return nameA.localeCompare(nameB, 'ja');
    });
    
    // オプションを追加
    filteredEmployees.forEach(emp => {
        const option = document.createElement('option');
        option.value = emp.employee_num;
        option.textContent = `${emp.employee_num} - ${emp.name || '名前なし'}`;
        option.dataset.employeeName = emp.name || '';
        option.dataset.section = emp.section || '設備';
        
        // URLパラメータで指定された従業員IDを優先して選択
        if (urlEmployeeId && emp.employee_num === urlEmployeeId) {
            option.selected = true;
        }
        
        employeeSelect.appendChild(option);
    });
    
    // 選択値を設定（URLパラメータを最優先、なければ現在の選択を維持）
    if (urlEmployeeId) {
        employeeSelect.value = urlEmployeeId;
    } else if (currentSelectedValue && currentSelectedValue !== '') {
        employeeSelect.value = currentSelectedValue;
    }
}

/**
 * セクション変更イベントリスナーを設定
 * @param {string} employeeSelectId - 従業員選択要素のID
 * @param {string} sectionSelectId - セクション選択要素のID
 * @param {string} defaultOptionText - デフォルトオプションのテキスト
 */
function setupSectionChangeListener(employeeSelectId, sectionSelectId, defaultOptionText = '従業員を選択してください') {
    const sectionSelect = document.getElementById(sectionSelectId);
    if (sectionSelect) {
        sectionSelect.addEventListener('change', () => {
            updateEmployeeList(employeeSelectId, sectionSelectId, defaultOptionText);
        });
    }
}

