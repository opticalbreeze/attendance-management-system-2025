// 打刻チェック確認画面専用JavaScript
// グローバル変数を名前空間に移動
AttendanceSystem.Check = AttendanceSystem.Check || {};
AttendanceSystem.Check.searchResults = [];

// 後方互換性のためのグローバル変数
let searchResults = AttendanceSystem.Check.searchResults;

document.addEventListener('DOMContentLoaded', async function() {
    // 従業員情報を動的に読み込み（共通関数を使用）
    await initializeEmployeeList();
    
    // 現在の日付から適切な月度を計算して設定
    function calculateCurrentPayrollMonth() {
        const today = new Date();
        const year = today.getFullYear();
        const month = today.getMonth() + 1;
        const day = today.getDate();
        
        if (day >= 16) {
            if (month === 12) {
                return `${year + 1}/1`;
            } else {
                return `${year}/${month + 1}`;
            }
        } else {
            return `${year}/${month}`;
        }
    }
    
    document.getElementById('search-month').value = calculateCurrentPayrollMonth();
    
    // セクション変更時に従業員リストを更新
    const sectionSelect = document.getElementById('section-select');
    if (sectionSelect) {
        sectionSelect.addEventListener('change', updateEmployeeList);
    }
});

// employee-list.js の共通関数を使用するようにラップ関数を作成
async function initializeEmployeeList() {
    // employee-list.js の loadEmployees 関数を呼び出し
    return loadEmployees('employee-id', 'section-select', '従業員を選択してください', function(employees) {
        console.log('従業員データ取得成功:', employees);
        console.log('最初の従業員:', employees[0]);
        
        // ヒント表示を有効化
        const employeeHint = document.getElementById('employee-hint');
        if (employeeHint) {
            employeeHint.style.display = 'block';
            employeeHint.textContent = `${employees.length}名の従業員が読み込まれました`;
        }
    });
}

// employee-list.js の共通関数を使用するようにラップ関数を作成
function refreshEmployeeList() {
    updateEmployeeList('employee-id', 'section-select', '従業員を選択してください');
}

// 検索実行
async function performSearch(event) {
    event.preventDefault();
    
    const employeeId = document.getElementById('employee-id').value;
    const searchMonth = document.getElementById('search-month').value;
    
    // バリデーション
    if (!employeeId) {
        const errorMsg = '従業員IDを入力してください';
        if (typeof showError !== 'undefined') {
            showError(errorMsg);
        } else {
            alert(errorMsg);
        }
        return;
    }
    
    if (!searchMonth) {
        const errorMsg = '検索月を入力してください（yyyy/mm形式）';
        if (typeof showError !== 'undefined') {
            showError(errorMsg);
        } else {
            alert(errorMsg);
        }
        return;
    }
    
    // 検索月の形式チェック
    const monthPattern = /^[0-9]{4}\/[0-9]{1,2}$/;
    if (!monthPattern.test(searchMonth)) {
        const errorMsg = '検索月はyyyy/mm形式で入力してください（例: 2025/10）';
        if (typeof showError !== 'undefined') {
            showError(errorMsg);
        } else {
            alert(errorMsg);
        }
        return;
    }
    
    // UIリセット
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('no-results').style.display = 'none';
    document.getElementById('error-message').style.display = 'none';
    document.getElementById('loading').style.display = 'block';
    
    // 統一APIサービスを使用
    try {
        const searchResponse = await AttendanceSystem.API.Search.attendance({
            employee_id: employeeId,
            search_month: searchMonth
        });

        document.getElementById('loading').style.display = 'none';

        if (searchResponse.success && searchResponse.data.status === 'success') {
            // 名前空間とグローバル変数の両方に保存
            AttendanceSystem.Check.searchResults = searchResponse.data.results;
            searchResults = searchResponse.data.results;
            await displayResults(searchResponse.data.results, searchResponse.data.search_params);
        } else {
            const errorMsg = searchResponse.message || searchResponse.data?.message || '検索エラーが発生しました';
            if (typeof showError !== 'undefined') {
                showError(errorMsg);
            } else {
                alert(errorMsg);
            }
        }
    } catch (error) {
        document.getElementById('loading').style.display = 'none';
        console.error('検索エラー:', error);
        const errorMsg = 'サーバーとの通信エラーが発生しました';
        if (typeof showError !== 'undefined') {
            showError(errorMsg);
        } else {
            alert(errorMsg);
        }
    }
}

// 検索結果を表示
async function displayResults(results, searchParams) {
    if (results.length === 0) {
        document.getElementById('no-results').style.display = 'block';
        return;
    }

    // 日付順でソート（古い順）
    results.sort((a, b) => {
        const dateA = new Date(a.work_date);
        const dateB = new Date(b.work_date);
        return dateA - dateB;
    });

    // 24勤の退勤時刻を翌日の明に移動するための前処理
    results = processNightShiftEndTimes(results);

    const tbody = document.getElementById('results-body');
    tbody.innerHTML = '';
    
    results.forEach(item => {
        const tr = document.createElement('tr');
        const alerts = item.alerts || [];
        const alertsHtml = formatAlerts(alerts);
        
        // 打刻時間を整形（有効な打刻に色を付けるため、全結果を渡す）
        // 「通常」を「日勤」に変換
        if (item.work_type) {
            item.work_type = item.work_type.replace('通常', '日勤');
        }
        const attendanceTimesHtml = formatAttendanceTimes(item.attendance_records || [], item.work_type, item.work_date, results, item);
        
        // 確認状況を生成
        const checkStatusHtml = generateCheckStatusHTML(item, alerts);
        
        tr.innerHTML = `
            <td class="idm-cell">${item.employee_id}</td>
            <td><strong>${item.employee_name || ''}</strong></td>
            <td>${formatDate(item.work_date)}</td>
            <td><span class="work-type ${getWorkTypeClass(item.work_type)}">${item.work_type || ''}</span></td>
            <td>${formatTime(item.start_time)}</td>
            <td>${formatEndTime(item)}</td>
            <td class="attendance-times">${attendanceTimesHtml}</td>
            <td id="alerts-${item.work_date}" style="font-size: 0.85em;">${alertsHtml}</td>
            <td id="check-status-${item.employee_id}-${item.work_date}" style="font-size: 0.85em;">${checkStatusHtml}</td>
            <td id="overtime-${item.work_date}" style="font-size: 0.85em; color: #667eea;">-</td>
            <td id="leave-${item.work_date}" style="font-size: 0.85em; color: #28a745;">-</td>
        `;
        tr.dataset.fullData = JSON.stringify(item);
        tbody.appendChild(tr);
    });
    
    // 時間外・休暇願データを非同期で取得
    const employeeId = searchParams.employee_id;
    fetchOvertimeDataForMonth(employeeId, results);
    fetchLeaveDataForMonth(employeeId, results);
    
    // チェック状況を読み込む
    await loadCheckStatuses(results);
    
    // 検索範囲の情報を表示
    let rangeInfo = '';
    if (searchParams && searchParams.date_range) {
        rangeInfo = ` (${searchParams.date_range.start_date} 〜 ${searchParams.date_range.end_date})`;
    }
    
    document.getElementById('results-count').textContent = `検索結果: ${results.length} 件${rangeInfo}`;
    document.getElementById('results-section').style.display = 'block';
}

// generateCheckStatusHTML は attendance-common.js から使用

/**
 * 確認ステータスを更新する関数
 * APIが認証エラーなどでHTMLを返す場合も適切にハンドリング
 * 
 * @param {HTMLInputElement} checkbox - チェックボックス要素
 */
async function updateCheckStatus(checkbox) {
    const employeeNum = checkbox.dataset.employee;
    const workDate = checkbox.dataset.date;
    const checkType = checkbox.dataset.type;
    const isChecked = checkbox.checked;
    
    try {
        // 統一APIサービスを使用
        const response = await AttendanceSystem.API.Check.updateStatus({
            employee_num: employeeNum,
            work_date: workDate,
            check_type: checkType,
            is_checked: isChecked
        });
        
        if (response.success) {
            let statusId;
            if (checkType === 'missing_punch') {
                statusId = `missing-status-${employeeNum}-${workDate}`;
            } else if (checkType === 'punch_leak') {
                statusId = `punchleak-status-${employeeNum}-${workDate}`;
            } else {
                statusId = `timediff-status-${employeeNum}-${workDate}`;
            }
            const statusElement = document.getElementById(statusId);
            
            if (statusElement) {
                if (isChecked) {
                    // 時間外申告の有無を確認
                    const hasOvertime = hasOvertimeForDate(workDate);
                    
                    if (checkType === 'missing_punch') {
                        statusElement.textContent = hasOvertime ? '打刻もれチェック済み時間外有り' : '打刻もれチェック済　時間外無';
                    } else if (checkType === 'punch_leak') {
                        statusElement.textContent = hasOvertime ? '打刻漏れチェック済み時間外有り' : '打刻漏れチェック済　時間外無';
                    } else {
                        statusElement.textContent = hasOvertime ? '時間外チェック済み時間外有り' : '時間外チェック済　時間外無';
                    }
                    statusElement.classList.add('completed');
                } else {
                    statusElement.textContent = '未確認';
                    statusElement.classList.remove('completed');
                }
            }
        } else {
            // エラーメッセージ表示（showErrorMessage または showError のどちらかが利用可能）
            const errorMsg = response.message || 'ステータス更新に失敗しました';
            if (typeof showErrorMessage !== 'undefined') {
                showErrorMessage(errorMsg);
            } else if (typeof showError !== 'undefined') {
                showError(errorMsg);
            } else {
                console.error('ステータス更新エラー:', errorMsg);
            }
            checkbox.checked = !isChecked;
        }
    } catch (error) {
        console.error('ステータス更新エラー:', error);
        const errorMsg = 'ステータス更新中にエラーが発生しました';
        if (typeof showErrorMessage !== 'undefined') {
            showErrorMessage(errorMsg);
        } else if (typeof showError !== 'undefined') {
            showError(errorMsg);
        }
        checkbox.checked = !isChecked;
    }
}

/**
 * 確認ステータスを読み込む関数
 * APIが認証エラーなどでHTMLを返す場合も適切にハンドリング
 * 
 * @param {Array} results - 検索結果の配列
 */
async function loadCheckStatuses(results) {
    for (const item of results) {
        if (!item || (!item.employee_id && !item.employee_num) || !item.work_date) {
            continue;
        }
        
        // employee_num または employee_id を取得
        const employeeNum = item.employee_num || item.employee_id;
        const employeeId = item.employee_id || item.employee_num; // DOM要素ID用
        
        for (const checkType of Object.values(CheckType)) {
            try {
                const response = await fetch(`/api/attendance-check-status?employee_num=${employeeNum}&work_date=${item.work_date}&check_type=${checkType}`);
                
                // ステータスコードをチェック
                if (!response.ok) {
                    // エラーレスポンスの詳細をログ出力
                    try {
                        const errorData = await response.json();
                        console.error(`[loadCheckStatuses] エラー: check_type=${checkType}, status=${response.status}`, errorData);
                    } catch (e) {
                        console.error(`[loadCheckStatuses] エラー: check_type=${checkType}, status=${response.status}, レスポンス解析失敗`);
                    }
                    // エラーレスポンスの場合はスキップ
                    continue;
                }
                
                // Content-TypeをチェックしてJSONかどうかを確認
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    // JSONでない場合はスキップ（認証エラーなどでHTMLが返される可能性がある）
                    continue;
                }
                
                const result = await response.json();
                
                if (result.success && result.data && result.data.is_checked) {
                    let checkboxId, statusId;
                    if (checkType === 'missing_punch') {
                        checkboxId = `missing-${employeeId}-${item.work_date}`;
                        statusId = `missing-status-${employeeId}-${item.work_date}`;
                    } else if (checkType === 'punch_leak') {
                        checkboxId = `punchleak-${employeeId}-${item.work_date}`;
                        statusId = `punchleak-status-${employeeId}-${item.work_date}`;
                    } else {
                        checkboxId = `timediff-${employeeId}-${item.work_date}`;
                        statusId = `timediff-status-${employeeId}-${item.work_date}`;
                    }
                    
                    const checkbox = document.getElementById(checkboxId);
                    const statusElement = document.getElementById(statusId);
                    
                    if (checkbox && statusElement) {
                        checkbox.checked = true;
                        
                        // 時間外申告の有無を確認
                        const hasOvertime = hasOvertimeForDate(item.work_date);
                        
                        if (checkType === 'missing_punch') {
                            statusElement.textContent = hasOvertime ? '打刻もれチェック済み時間外有り' : '打刻もれチェック済　時間外無';
                        } else if (checkType === 'punch_leak') {
                            statusElement.textContent = hasOvertime ? '打刻漏れチェック済み時間外有り' : '打刻漏れチェック済　時間外無';
                        } else {
                            statusElement.textContent = hasOvertime ? '時間外チェック済み時間外有り' : '時間外チェック済　時間外無';
                        }
                        statusElement.classList.add('completed');
                    }
                }
            } catch (error) {
                // すべてのエラーを無視して続行
                // 認証エラーなどでHTMLが返される場合があるため、エラーをログに出力しない
                continue;
            }
        }
    }
}

// formatDate, formatTime は attendance-common.js から使用

// formatEndTime, processNightShiftEndTimes は attendance-common.js から使用

// formatAttendanceTimes, formatAlerts, getWorkTypeClass は attendance-common.js から使用

// 時間外申告データをグローバル変数に保存（日付をキーとして）
const overtimeDataMap = {};

// 時間外・休暇願データ取得（既存のsearch.htmlから移植）
async function fetchOvertimeDataForMonth(employeeId, results) {
    try {
        const response = await fetch(`/api/overtime?employee_num=${employeeId}&limit=1000`);
        const result = await response.json();
        
        if (result.status === 'success' && result.data) {
            result.data.forEach(overtime => {
                // 時間外申告データをマップに保存
                overtimeDataMap[overtime.work_date] = overtime;
                
                const cell = document.getElementById(`overtime-${overtime.work_date}`);
                if (cell) {
                    const totalMin = (overtime.inner_overtime_minutes || 0) + (overtime.outer_overtime_minutes || 0);
                    const hours = (totalMin / 60).toFixed(1);
                    cell.innerHTML = `${overtime.start_time}-${overtime.end_time}<br><small>(${hours}h)</small>`;
                }
            });
        }
    } catch (error) {
        console.error('[時間外データ取得エラー]', error);
    }
}

// 指定日付に時間外申告があるかチェック
function hasOvertimeForDate(workDate) {
    return overtimeDataMap.hasOwnProperty(workDate);
}

async function fetchLeaveDataForMonth(employeeId, results) {
    try {
        const response = await fetch(`/api/leave?employee_num=${employeeId}&limit=1000`);
        const result = await response.json();
        
        if (result.status === 'success' && result.data) {
            result.data.forEach(leave => {
                const startDate = new Date(leave.leave_date_from);
                const endDate = new Date(leave.leave_date_to);
                
                for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
                    const dateStr = d.toISOString().split('T')[0];
                    const cell = document.getElementById(`leave-${dateStr}`);
                    if (cell) {
                        let detail = leave.leave_type;
                        if (leave.leave_subtype) {
                            detail = leave.leave_subtype.substring(0, 20);
                        }
                        cell.innerHTML = `${detail}`;
                    }
                }
            });
        }
    } catch (error) {
        console.error('[休暇願データ取得エラー]', error);
    }
}

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

// エラーメッセージを表示する関数（ユーザーフレンドリーな表示）
function showErrorMessage(message) {
    const errorContainer = document.createElement('div');
    errorContainer.className = 'error-toast';
    errorContainer.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #e74c3c;
        color: white;
        padding: 12px 20px;
        border-radius: 5px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        z-index: 1000;
        max-width: 400px;
        word-wrap: break-word;
        animation: slideIn 0.3s ease-out;
    `;
    
    errorContainer.textContent = message;
    document.body.appendChild(errorContainer);
    
    // 5秒後に自動で消す
    setTimeout(() => {
        if (errorContainer.parentNode) {
            errorContainer.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => {
                if (errorContainer.parentNode) {
                    errorContainer.parentNode.removeChild(errorContainer);
                }
            }, 300);
        }
    }, 5000);
}

/**
 * 有効な出勤・退勤時刻を判定する関数
 * 勤務タイプに応じて適切な打刻時刻を選択する
 * 
 * @param {Array} attendanceRecords - 打刻レコードの配列
 * @param {string} workType - 勤務タイプ（例: "日勤", "24勤A", "夜勤", "明"）
 * @param {string} workDate - 勤務日（YYYY-MM-DD形式）
 * @param {Array} allResults - 全検索結果（翌日の「明」勤務を探すために使用）
 * @returns {Object} {clockIn: string|null, clockOut: string|null}
 */
// 有効な出勤・退勤時刻を判定する関数 - search.htmlと完全に同じ
// getValidClockTimes は attendance-common.js から使用
// processNightShiftEndTimes は attendance-common.js から使用

function clearForm() {
    document.getElementById('search-form').reset();
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('no-results').style.display = 'none';
    document.getElementById('error-message').style.display = 'none';
}

function exportCSV() {
    if (searchResults.length === 0) {
        showErrorMessage('出力するデータがありません');
        return;
    }
    
    let csv = '従業員ID,従業員名,勤務日,勤務タイプ,開始時刻,終了時刻,出勤時間,退勤時間,実際の打刻時間,エラー・警告,確認状況\n';
    
    searchResults.forEach(item => {
        // 有効な出勤・退勤時間を取得
        const validTimes = getValidClockTimes(item.attendance_records || [], item.work_type, item.work_date, searchResults);
        
        // 有効な打刻のみをCSVに出力（無効な多重打刻は除外）
        const validTimeSet = new Set();
        if (validTimes.clockIn) validTimeSet.add(validTimes.clockIn);
        if (validTimes.clockOut) validTimeSet.add(validTimes.clockOut);
        const validAttendanceTimes = (item.attendance_records || [])
            .filter(r => validTimeSet.has(r.time_only))
            .map(r => r.time_only)
            .join(';');
        
        const alertsText = (item.alerts || []).map(alert => {
            return alert.details ? `${alert.message}: ${alert.details}` : alert.message;
        }).join('; ').replace(/"/g, '""');
        
        // 確認状況をCSVに追加
        let checkStatus = '';
        const hasMissingPunch = (item.alerts || []).some(alert => alert.message && alert.message.includes('打刻なし'));
        const hasTimeDifference = (item.alerts || []).some(alert => alert.message && alert.message.includes('時刻差異'));
        
        const checkStatuses = [];
        if (hasMissingPunch) {
            const missingCheckbox = document.getElementById(`missing-${item.employee_id}-${item.work_date}`);
            if (missingCheckbox && missingCheckbox.checked) {
                checkStatuses.push('打刻もれチェック済');
            } else {
                checkStatuses.push('打刻もれ未確認');
            }
        }
        if (hasTimeDifference) {
            const timeDiffCheckbox = document.getElementById(`timediff-${item.employee_id}-${item.work_date}`);
            if (timeDiffCheckbox && timeDiffCheckbox.checked) {
                checkStatuses.push('時間外チェック済');
            } else {
                checkStatuses.push('差異未確認');
            }
        }
        checkStatus = checkStatuses.join(', ');
        
        csv += `"${item.employee_id}","${item.employee_name || ''}","${item.work_date}","${item.work_type || ''}","${item.start_time || ''}","${item.end_time || ''}","${validTimes.clockIn || ''}","${validTimes.clockOut || ''}","${validAttendanceTimes}","${alertsText}","${checkStatus}"\n`;
    });
    
    const BOM = '\uFEFF';
    const blob = new Blob([BOM + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `attendance_check_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
}