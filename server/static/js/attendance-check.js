// 打刻チェック確認画面専用JavaScript
let searchResults = [];
let allEmployees = [];

document.addEventListener('DOMContentLoaded', async function() {
    // 従業員情報を動的に読み込み
    await loadEmployees();
    
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

// 従業員情報を動的に読み込む
async function loadEmployees() {
    const employeeSelect = document.getElementById('employee-id');
    const sectionSelect = document.getElementById('section-select');
    const employeeHint = document.getElementById('employee-hint');
    
    try {
        const response = await fetch('/api/employees');
        const result = await response.json();
        
        if (result.status === 'success' && result.data) {
            allEmployees = result.data;
            console.log('従業員データ取得成功:', result.data);
            console.log('最初の従業員:', result.data[0]);
            
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
            updateEmployeeList();
            
            // ヒント表示を有効化
            employeeHint.style.display = 'block';
            employeeHint.textContent = `${result.data.length}名の従業員が読み込まれました`;
        } else {
            throw new Error(result.message || '従業員データの読み込みに失敗');
        }
    } catch (error) {
        employeeSelect.innerHTML = '<option value="">❌ 従業員データ読み込み失敗</option>';
        employeeHint.style.display = 'block';
        employeeHint.textContent = '従業員データの読み込みに失敗しました';
        employeeHint.style.color = '#e74c3c';
    }
}

// セクションで絞り込んだ従業員リストを更新
function updateEmployeeList() {
    const employeeSelect = document.getElementById('employee-id');
    const sectionSelect = document.getElementById('section-select');
    const selectedSection = sectionSelect.value;
    
    employeeSelect.innerHTML = '<option value="">▼ 従業員を選択してください</option>';
    
    const filteredEmployees = selectedSection 
        ? allEmployees.filter(emp => (emp.section || '設備') === selectedSection)
        : allEmployees;
    
    filteredEmployees.forEach(emp => {
        const option = document.createElement('option');
        option.value = emp.employee_num;
        console.log('従業員情報:', emp); // デバッグログ
        option.textContent = `${emp.employee_num} - ${emp.name || '名前なし'} (${emp.section || '設備'})`;
        employeeSelect.appendChild(option);
    });
}

// 検索実行
async function performSearch(event) {
    event.preventDefault();
    
    const employeeId = document.getElementById('employee-id').value;
    const searchMonth = document.getElementById('search-month').value;
    
    if (!employeeId) {
        showError('従業員を選択してください');
        return;
    }
    
    if (!searchMonth) {
        showError('検索月を入力してください');
        return;
    }
    
    const monthPattern = /^[0-9]{4}\/[0-9]{1,2}$/;
    if (!monthPattern.test(searchMonth)) {
        showError('検索月はyyyy/mm形式で入力してください（例: 2025/10）');
        return;
    }
    
    // UIリセット
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('no-results').style.display = 'none';
    document.getElementById('error-message').style.display = 'none';
    document.getElementById('loading').style.display = 'block';
    
    // クエリパラメータ構築
    const params = new URLSearchParams();
    params.append('employee_id', employeeId);
    params.append('search_month', searchMonth);
    
    const searchUrl = `/api/search?${params}`;

    try {
        const response = await fetch(searchUrl);
        const data = await response.json();

        document.getElementById('loading').style.display = 'none';

        if (data.status === 'success') {
            searchResults = data.results;
            displayResults(data.results, data.search_params);
        } else {
            showError(data.message || '検索エラーが発生しました');
        }
    } catch (error) {
        document.getElementById('loading').style.display = 'none';
        showError('サーバーとの通信エラーが発生しました');
    }
}

// 検索結果を表示
function displayResults(results, searchParams) {
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
        
        // 打刻時間を整形（有効な打刻に色を付けるため、全結果を渡す）- search.htmlと同じ
        const attendanceTimesHtml = formatAttendanceTimes(item.attendance_records || [], item.work_type, item.work_date, results);
        
        // デバッグ: 最初の3件のみログ出力
        if (results.indexOf(item) < 3) {
            const validTimes = getValidClockTimes(item.attendance_records || [], item.work_type, item.work_date, results);
            console.log(`[${item.work_date}] validTimes:`, validTimes);
            console.log(`[${item.work_date}] attendanceTimesHtml:`, attendanceTimesHtml.substring(0, 200));
        }
        
        tr.innerHTML = `
            <td class="idm-cell">${item.employee_id}</td>
            <td><strong>${item.employee_name || ''}</strong></td>
            <td>${formatDate(item.work_date)}</td>
            <td><span class="work-type ${getWorkTypeClass(item.work_type)}">${item.work_type || ''}</span></td>
            <td>${formatTime(item.start_time)}</td>
            <td>${formatEndTime(item)}</td>
            <td class="attendance-times">${attendanceTimesHtml}</td>
            <td id="alerts-${item.work_date}" style="font-size: 0.85em;">${alertsHtml}</td>
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
    
    // 検索範囲の情報を表示
    let rangeInfo = '';
    if (searchParams && searchParams.date_range) {
        rangeInfo = ` (${searchParams.date_range.start_date} 〜 ${searchParams.date_range.end_date})`;
    }
    
    document.getElementById('results-count').textContent = `検索結果: ${results.length} 件${rangeInfo}`;
    document.getElementById('results-section').style.display = 'block';
}

// 確認チェックボックスのHTML生成
function generateCheckStatusHTML(item, alerts) {
    const hasMissingPunch = alerts.some(alert => alert.message && alert.message.includes('打刻なし'));
    const hasTimeDifference = alerts.some(alert => alert.message && alert.message.includes('時刻差異'));
    
    if (!hasMissingPunch && !hasTimeDifference) {
        return '<span style="color: #999;">-</span>';
    }
    
    let html = '<div class="check-container">';
    
    if (hasMissingPunch) {
        html += `
            <div class="check-item">
                <input type="checkbox" 
                       id="missing-${item.employee_id}-${item.work_date}" 
                       data-type="missing_punch"
                       data-employee="${item.employee_id}"
                       data-date="${item.work_date}"
                       onchange="updateCheckStatus(this)">
                <label for="missing-${item.employee_id}-${item.work_date}">打刻なし</label>
            </div>
            <div id="missing-status-${item.employee_id}-${item.work_date}" class="check-status">未確認</div>
        `;
    }
    
    if (hasTimeDifference) {
        html += `
            <div class="check-item">
                <input type="checkbox" 
                       id="timediff-${item.employee_id}-${item.work_date}" 
                       data-type="time_difference"
                       data-employee="${item.employee_id}"
                       data-date="${item.work_date}"
                       onchange="updateCheckStatus(this)">
                <label for="timediff-${item.employee_id}-${item.work_date}">差異あり</label>
            </div>
            <div id="timediff-status-${item.employee_id}-${item.work_date}" class="check-status">未確認</div>
        `;
    }
    
    html += '</div>';
    return html;
}

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
        const response = await fetch('/api/attendance-check-status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                employee_num: employeeNum,
                work_date: workDate,
                check_type: checkType,
                is_checked: isChecked
            })
        });
        
        // ステータスコードをチェック
        if (!response.ok) {
            showErrorMessage('ステータス更新に失敗しました（HTTP ' + response.status + '）');
            checkbox.checked = !isChecked;
            return;
        }
        
        // Content-TypeをチェックしてJSONかどうかを確認
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            // JSONでない場合は認証エラーの可能性がある
            showErrorMessage('認証エラーが発生しました。再度ログインしてください。');
            checkbox.checked = !isChecked;
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            const statusId = `${checkType === 'missing_punch' ? 'missing' : 'timediff'}-status-${employeeNum}-${workDate}`;
            const statusElement = document.getElementById(statusId);
            
            if (statusElement) {
                if (isChecked) {
                    if (checkType === 'missing_punch') {
                        statusElement.textContent = '打刻もれチェック済　時間外無';
                    } else {
                        statusElement.textContent = '時間外チェック済　時間外無';
                    }
                    statusElement.classList.add('completed');
                } else {
                    statusElement.textContent = '未確認';
                    statusElement.classList.remove('completed');
                }
            }
        } else {
            showErrorMessage('ステータス更新に失敗しました: ' + (result.message || '不明なエラー'));
            checkbox.checked = !isChecked;
        }
    } catch (error) {
        // JSONパースエラーの場合
        if (error instanceof SyntaxError) {
            showErrorMessage('認証エラーが発生しました。再度ログインしてください。');
        } else {
            console.error('ステータス更新エラー:', error);
            showErrorMessage('ステータス更新中にエラーが発生しました');
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
        for (const checkType of ['missing_punch', 'time_difference']) {
            try {
                const response = await fetch(`/api/attendance-check-status?employee_num=${item.employee_id}&work_date=${item.work_date}&check_type=${checkType}`);
                
                // ステータスコードをチェック
                if (!response.ok) {
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
                    const checkboxId = `${checkType === 'missing_punch' ? 'missing' : 'timediff'}-${item.employee_id}-${item.work_date}`;
                    const statusId = `${checkType === 'missing_punch' ? 'missing' : 'timediff'}-status-${item.employee_id}-${item.work_date}`;
                    
                    const checkbox = document.getElementById(checkboxId);
                    const statusElement = document.getElementById(statusId);
                    
                    if (checkbox && statusElement) {
                        checkbox.checked = true;
                        
                        if (checkType === 'missing_punch') {
                            statusElement.textContent = '打刻もれチェック済　時間外無';
                        } else {
                            statusElement.textContent = '時間外チェック済　時間外無';
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

// ヘルパー関数群
function formatDate(dateStr) {
    if (!dateStr) return '';
    const dt = new Date(dateStr);
    return dt.toLocaleDateString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

function formatTime(timeStr) {
    if (!timeStr) return '';
    // ISO時刻文字列の場合
    if (timeStr.includes('T') || timeStr.includes(' ')) {
        const dt = new Date(timeStr);
        return dt.toLocaleTimeString('ja-JP', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    // HH:MM形式の場合はそのまま返す
    return timeStr;
}

// 退勤時刻表示（24勤の場合は翌日明に表示）- search.htmlと同じ
function formatEndTime(item) {
    // 明の行で、前日24勤の退勤時刻がある場合
    if (item.work_type === '明' && item.night_shift_end_time) {
        const timeStr = formatTime(item.night_shift_end_time);
        return `${timeStr} <span style="color: #3498db; font-size: 0.8em;">(${item.night_shift_work_type}退勤)</span>`;
    }
    
    // 24勤の場合は退勤時刻を表示しない（翌日明に移動済み）
    if (item.work_type && item.work_type.includes('24勤')) {
        return '<span style="color: #999; font-style: italic;">翌日明に表示</span>';
    }
    
    // 通常勤務の場合はそのまま
    return formatTime(item.end_time);
}

// 打刻時間を整形する関数（有効な打刻に色を付ける）- search.htmlと完全に同じ
function formatAttendanceTimes(attendanceRecords, workType, workDate, allResults) {
    if (!attendanceRecords || attendanceRecords.length === 0) {
        return '<span class="no-attendance">打刻なし</span>';
    }
    
    // 有効な出勤・退勤時刻を判定
    const validTimes = getValidClockTimes(attendanceRecords, workType, workDate, allResults);
    
    // デバッグ: 最初の3件のみログ出力
    const isDebug = attendanceRecords.length > 0 && attendanceRecords[0].time_only;
    if (isDebug && workDate) {
        console.log(`[formatAttendanceTimes] ${workDate} - validTimes:`, validTimes);
        console.log(`[formatAttendanceTimes] ${workDate} - 全打刻:`, attendanceRecords.map(r => r.time_only));
    }
    
    const timeSpans = attendanceRecords.map(record => {
        const timeStr = record.time_only;
        let className = 'attendance-time';
        let title = `端末: ${record.terminal_id}`;
        
        // 有効な出勤時刻かチェック
        if (validTimes.clockIn === timeStr) {
            className += ' valid-clock-in';
            title += ' (有効な出勤時刻)';
            if (isDebug && workDate) console.log(`[formatAttendanceTimes] ${workDate} - ${timeStr} に出勤時刻の色分けを適用`);
        }
        // 有効な退勤時刻かチェック
        else if (validTimes.clockOut === timeStr) {
            className += ' valid-clock-out';
            title += ' (有効な退勤時刻)';
            if (isDebug && workDate) console.log(`[formatAttendanceTimes] ${workDate} - ${timeStr} に退勤時刻の色分けを適用`);
        }
        
        return `<span class="${className}" title="${title}">${timeStr}</span>`;
    });
    
    const result = timeSpans.join(' ');
    if (isDebug && workDate) {
        console.log(`[formatAttendanceTimes] ${workDate} - 生成されたHTML:`, result.substring(0, 300));
    }
    
    return result;
}

function formatAlerts(alerts) {
    if (!alerts || alerts.length === 0) {
        return '<span style="color: #999;">-</span>';
    }
    
    if (!Array.isArray(alerts)) {
        return '<span style="color: #999;">-</span>';
    }
    
    const formatted = alerts.map(alert => {
        if (!alert || typeof alert !== 'object') {
            return '';
        }
        
        const icon = alert.type === 'error' ? '❌' : alert.type === 'warning' ? '⚠️' : 'ℹ️';
        const className = alert.type === 'error' ? 'error' : alert.type === 'warning' ? 'warning' : 'info';
        const title = alert.details ? `${alert.message}: ${alert.details}` : alert.message;
        
        return `<div class="alert-item ${className}" title="${title.replace(/"/g, '&quot;')}">
            <span class="alert-icon">${icon}</span>
            <span>${alert.message}</span>
        </div>`;
    }).join('');
    
    return formatted;
}

function getWorkTypeClass(workType) {
    if (!workType) return '';
    if (workType.includes('24勤')) return 'shift-24';
    if (workType.includes('日勤')) return 'day-shift';
    if (workType.includes('夜勤')) return 'night-shift';
    if (workType.includes('所')) return 'office';
    if (workType.includes('明')) return 'off-day';
    if (workType.includes('法')) return 'holiday';
    if (workType.includes('有')) return 'paid-leave';
    return '';
}

// 時間外・休暇願データ取得（既存のsearch.htmlから移植）
async function fetchOvertimeDataForMonth(employeeId, results) {
    try {
        const response = await fetch(`/api/overtime?employee_num=${employeeId}&limit=1000`);
        const result = await response.json();
        
        if (result.status === 'success' && result.data) {
            result.data.forEach(overtime => {
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
function getValidClockTimes(attendanceRecords, workType, workDate, allResults) {
    const result = {
        clockIn: null,
        clockOut: null
    };
    
    if (!attendanceRecords || attendanceRecords.length === 0) {
        return result;
    }
    
    // 時刻でソート（早い順）
    const sortedRecords = [...attendanceRecords].sort((a, b) => {
        return a.time_only.localeCompare(b.time_only);
    });
    
    // 24勤A/B、夜勤の場合
    if (workType && (workType.includes('24勤') || workType.includes('夜勤'))) {
        // 一番早い時間が出勤
        result.clockIn = sortedRecords[0].time_only;
        
        // 翌日の「明」の日の一番遅い時間が退勤
        const currentDate = new Date(workDate);
        const nextDate = new Date(currentDate);
        nextDate.setDate(currentDate.getDate() + 1);
        const nextDateStr = nextDate.toISOString().split('T')[0];
        
        // 翌日の明のスケジュールを探す
        if (allResults) {
            const nextDayOffItem = allResults.find(item => 
                item.work_date === nextDateStr && item.work_type === '明'
            );
            
            if (nextDayOffItem && nextDayOffItem.attendance_records && nextDayOffItem.attendance_records.length > 0) {
                // 翌日の打刻データを時刻でソート
                const nextDaySorted = [...nextDayOffItem.attendance_records].sort((a, b) => {
                    return a.time_only.localeCompare(b.time_only);
                });
                // 一番遅い時間が退勤
                result.clockOut = nextDaySorted[nextDaySorted.length - 1].time_only;
            }
        }
    } else {
        // 日勤の場合：一番早い時間が出勤、一番遅い時間が退勤
        result.clockIn = sortedRecords[0].time_only;
        result.clockOut = sortedRecords[sortedRecords.length - 1].time_only;
    }
    
    return result;
}

/**
 * 24勤の退勤時刻を翌日の明に移動するための前処理（search.htmlと同じ）
 */
function processNightShiftEndTimes(results) {
    const processedResults = [...results];
    
    for (let i = 0; i < processedResults.length; i++) {
        const currentItem = processedResults[i];
        
        // 24勤の場合
        if (currentItem.work_type && currentItem.work_type.includes('24勤')) {
            // 翌日の明を探す
            const currentDate = new Date(currentItem.work_date);
            const nextDay = new Date(currentDate);
            nextDay.setDate(currentDate.getDate() + 1);
            const nextDateStr = nextDay.toISOString().split('T')[0];
            
            const nextDayOffItem = processedResults.find(item => 
                item.work_date === nextDateStr && item.work_type === '明'
            );
            
            if (nextDayOffItem && currentItem.end_time) {
                // 24勤の退勤時刻を翌日の明に移動
                nextDayOffItem.night_shift_end_time = currentItem.end_time;
                nextDayOffItem.night_shift_work_type = currentItem.work_type;
                
                // 24勤の退勤時刻をクリア
                currentItem.end_time = null;
            }
        }
    }
    
    return processedResults;
}

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