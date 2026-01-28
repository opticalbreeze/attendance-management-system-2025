/**
 * 勤怠チェック画面専用JavaScript
 * attendance_check.htmlページの機能を管理
 */

// 名前空間を使用してグローバル変数の衝突を回避
AttendanceSystem.Check = AttendanceSystem.Check || {};

// このページ固有のデータを名前空間に保存
AttendanceSystem.Check.searchResults = [];

// 後方互換性のため
let searchResults = AttendanceSystem.Check.searchResults;
let allEmployees = [];

/**
 * ページ初期化処理
 */
document.addEventListener('DOMContentLoaded', async function() {
    // 従業員情報を動的に読み込み
    await loadEmployees();
    
    // 現在の月度を設定
    document.getElementById('search-month').value = calculateCurrentPayrollMonth();
    
    // セクション変更時に従業員リストを更新
    const sectionSelect = document.getElementById('section-select');
    if (sectionSelect) {
        sectionSelect.addEventListener('change', updateEmployeeList);
    }
});

/**
 * 現在の日付から適切な月度を計算して設定
 * @returns {string} 年/月形式の文字列
 */
function calculateCurrentPayrollMonth() {
    const today = new Date();
    const year = today.getFullYear();
    const month = today.getMonth() + 1; // 0ベースなので+1
    const day = today.getDate();
    
    // 16日以降なら翌月度、15日以前なら当月度
    if (day >= 16) {
        // 翌月度
        if (month === 12) {
            return `${year + 1}/1`;
        } else {
            return `${year}/${month + 1}`;
        }
    } else {
        // 当月度
        return `${year}/${month}`;
    }
}

/**
 * 従業員情報を動的に読み込む（統一APIサービス使用）
 */
async function loadEmployees() {
    const employeeSelect = document.getElementById('employee-id');
    const sectionSelect = document.getElementById('section-select');
    const employeeHint = document.getElementById('employee-hint');
    
    try {
        console.log('[loadEmployees] 統一APIサービスで従業員データを読み込み中...');
        
        // 統一APIサービスを使用
        const employeesResponse = await AttendanceSystem.API.Employees.getAll();
        
        if (employeesResponse.success) {
            // 全従業員データを保存
            allEmployees = employeesResponse.data;
            console.log(`[loadEmployees] ${employeesResponse.data.length}名の従業員を読み込みました`);
            
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
                console.warn('[loadEmployees] セクション一覧取得に失敗:', sectionsResponse.message);
            }
            
            // 従業員リストを更新
            updateEmployeeList();
            
            // ヒント表示を有効化
            employeeHint.style.display = 'block';
            employeeHint.textContent = `${employeesResponse.data.length}名の従業員が読み込まれました`;
            employeeHint.style.color = '#28a745';
        } else {
            console.error('[loadEmployees] APIエラー:', employeesResponse.message);
            throw new Error(employeesResponse.message);
        }
    } catch (error) {
        console.error('[loadEmployees] エラー詳細:', error);
        employeeSelect.innerHTML = '<option value="">[エラー] 従業員データ読み込み失敗</option>';
        employeeHint.style.display = 'block';
        employeeHint.textContent = `従業員データの読み込みに失敗しました: ${error.message}`;
        employeeHint.style.color = '#e74c3c';
    }
}

/**
 * セクションで絞り込んだ従業員リストを更新
 */
function updateEmployeeList() {
    const employeeSelect = document.getElementById('employee-id');
    const sectionSelect = document.getElementById('section-select');
    const selectedSection = sectionSelect.value;
    
    // 既存のオプションをクリア
    employeeSelect.innerHTML = '<option value="">▼ 従業員を選択してください</option>';
    
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

console.log('[attendance-check-page.js] 勤怠チェック画面用JavaScriptが読み込まれました');