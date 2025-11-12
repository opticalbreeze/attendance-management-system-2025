/**
 * 従業員リスト管理共通モジュール
 * セクションによるフィルタリングと従業員選択を提供
 */

// グローバル変数: 全従業員データ
let allEmployees = [];

/**
 * 従業員リストをAPIから読み込む
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
        const response = await fetch('/api/employees');
        const result = await response.json();
        
        if (result.status === 'success' && result.data) {
            // 全従業員データを保存
            allEmployees = result.data;
            
            // セクション一覧を取得・設定
            const sections = [...new Set(result.data.map(emp => emp.section || '設備'))].sort();
            sectionSelect.innerHTML = '<option value="">すべてのセクション</option>';
            sections.forEach(section => {
                const option = document.createElement('option');
                option.value = section;
                option.textContent = section;
                sectionSelect.appendChild(option);
            });
            
            // 従業員リストを更新
            updateEmployeeList(employeeSelectId, sectionSelectId, defaultOptionText);
            
            // 成功コールバックを実行
            if (onSuccess && typeof onSuccess === 'function') {
                onSuccess(allEmployees);
            }
        } else {
            throw new Error(result.message || '従業員データの読み込みに失敗');
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
    
    employeeSelect.innerHTML = `<option value="">▼ ${defaultOptionText}</option>`;
    
    // セクションでフィルタリング
    const filteredEmployees = selectedSection 
        ? allEmployees.filter(emp => (emp.section || '設備') === selectedSection)
        : allEmployees;
    
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
        employeeSelect.appendChild(option);
    });
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

