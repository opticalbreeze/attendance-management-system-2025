/**
 * 勤怠管理システム共通JavaScriptライブラリ
 * 複数のページで使用される共通関数を集約
 */

// グローバル名前空間オブジェクト
window.AttendanceSystem = window.AttendanceSystem || {};

// 各モジュールの名前空間を作成
AttendanceSystem.Common = AttendanceSystem.Common || {};
AttendanceSystem.Check = AttendanceSystem.Check || {};
AttendanceSystem.Search = AttendanceSystem.Search || {};
AttendanceSystem.Employee = AttendanceSystem.Employee || {};

// 共通データ格納用
AttendanceSystem.Data = {
    employees: [],
    searchResults: [],
    overtimeData: {},
    checkStatuses: {}
};

// チェックタイプ定数
const CheckType = {
    MISSING_PUNCH: 'missing_punch',
    TIME_DIFFERENCE: 'time_difference',
    PUNCH_LEAK: 'punch_leak'
};

// アラートタイプ定数
const AlertType = {
    ERROR: 'error',
    WARNING: 'warning',
    INFO: 'info'
};

/**
 * 日付をフォーマット
 * @param {string} dateStr - 日付文字列
 * @returns {string} フォーマットされた日付
 */
function formatDate(dateStr) {
    if (!dateStr) return '';
    const dt = new Date(dateStr);
    return dt.toLocaleDateString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

/**
 * 時刻をフォーマット
 * @param {string} timeStr - 時刻文字列
 * @returns {string} フォーマットされた時刻
 */
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

/**
 * 有効な出勤・退勤時刻を判定
 * @param {Array} attendanceRecords - 打刻記録配列
 * @param {string} workType - 勤務タイプ
 * @param {string} workDate - 勤務日
 * @param {Array} allResults - 全検索結果
 * @param {Object} item - 現在のアイテム（actual_clock_in/outを含む）
 * @returns {Object} {clockIn: string|null, clockOut: string|null}
 */
function getValidClockTimes(attendanceRecords, workType, workDate, allResults, item) {
    const result = {
        clockIn: null,
        clockOut: null
    };
    
    // サーバー側で計算されたactual_clock_in/actual_clock_outを優先使用
    if (item && (item.actual_clock_in || item.actual_clock_out)) {
        if (item.actual_clock_in) {
            const timeStr = item.actual_clock_in;
            result.clockIn = timeStr.includes('T') || timeStr.includes(' ') 
                ? new Date(timeStr).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })
                : timeStr;
        }
        if (item.actual_clock_out) {
            const timeStr = item.actual_clock_out;
            result.clockOut = timeStr.includes('T') || timeStr.includes(' ') 
                ? new Date(timeStr).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })
                : timeStr;
        }
        return result;
    }
    
    // フォールバック: クライアント側で計算
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
            const nextDayItem = allResults.find(r => r.work_date === nextDateStr && r.work_type && r.work_type.includes('明'));
            if (nextDayItem && nextDayItem.attendance_records && nextDayItem.attendance_records.length > 0) {
                const nextDayRecords = [...nextDayItem.attendance_records].sort((a, b) => {
                    return a.time_only.localeCompare(b.time_only);
                });
                result.clockOut = nextDayRecords[nextDayRecords.length - 1].time_only;
            }
        }
    } else if (workType && workType.includes('明')) {
        // 「明」勤務: 前日の24勤・夜勤の退勤時刻を表示
        result.clockIn = null;
        if (sortedRecords.length > 0) {
            result.clockOut = sortedRecords[sortedRecords.length - 1].time_only;
        }
    } else {
        // 日勤: 一番早い時間が出勤、一番遅い時間が退勤
        result.clockIn = sortedRecords[0].time_only;
        result.clockOut = sortedRecords[sortedRecords.length - 1].time_only;
    }
    
    return result;
}

/**
 * 打刻時間を整形（有効な打刻に色を付ける）
 * @param {Array} attendanceRecords - 打刻記録配列
 * @param {string} workType - 勤務タイプ
 * @param {string} workDate - 勤務日
 * @param {Array} allResults - 全検索結果
 * @param {Object} item - 現在のアイテム（actual_clock_in/outを含む、オプション）
 * @returns {string} HTML文字列
 */
function formatAttendanceTimes(attendanceRecords, workType, workDate, allResults, item) {
    if (!attendanceRecords || attendanceRecords.length === 0) {
        return '<span class="no-attendance">打刻なし</span>';
    }
    
    // 同じ時刻の打刻を除外（最初の1つだけを残す）
    const uniqueRecords = [];
    const seenTimes = new Set();
    for (const record of attendanceRecords) {
        const timeStr = record.time_only;
        if (!seenTimes.has(timeStr)) {
            seenTimes.add(timeStr);
            uniqueRecords.push(record);
        }
    }
    
    // 有効な出勤・退勤時刻を判定（重複除外後のデータを使用）
    const validTimes = getValidClockTimes(uniqueRecords, workType, workDate, allResults, item);
    
    // 有効な打刻のみをフィルタリング（attendance_check.htmlの場合）
    const validRecords = item ? uniqueRecords.filter(record => {
        const timeStr = record.time_only;
        return validTimes.clockIn === timeStr || validTimes.clockOut === timeStr;
    }) : uniqueRecords;
    
    const timeSpans = validRecords.map(record => {
        const timeStr = record.time_only;
        let className = 'attendance-time';
        let title = `端末: ${record.terminal_id}`;
        
        // 有効な出勤時刻かチェック
        if (validTimes.clockIn === timeStr) {
            className += ' valid-clock-in';
            title += ' (有効な出勤時刻)';
        }
        // 有効な退勤時刻かチェック
        else if (validTimes.clockOut === timeStr) {
            className += ' valid-clock-out';
            title += ' (有効な退勤時刻)';
        }
        
        return `<span class="${className}" title="${title}">${timeStr}</span>`;
    });
    
    return timeSpans.join(' ');
}

/**
 * アラート情報をフォーマット
 * @param {Array} alerts - アラート配列
 * @returns {string} HTML文字列
 */
function formatAlerts(alerts) {
    if (!alerts || alerts.length === 0) {
        return '<span style="color: #999;">正常</span>';
    }
    
    if (!Array.isArray(alerts)) {
        return '<span style="color: #999;">正常</span>';
    }
    
    const formatted = alerts.map(alert => {
        if (!alert || typeof alert !== 'object') {
            return '';
        }
        
        const icon = alert.type === AlertType.ERROR ? '❌' : alert.type === AlertType.WARNING ? '⚠️' : 'ℹ️';
        const className = alert.type === AlertType.ERROR ? 'error' : alert.type === AlertType.WARNING ? 'warning' : 'info';
        
        // メッセージを統一的な表現に変換
        let standardMessage = alert.message;
        if (alert.message && alert.message.includes('打刻データを検索')) {
            standardMessage = alert.message.replace('打刻データを検索', '勤怠データ確認');
        }
        if (alert.message && alert.message.includes('従業員勤怠確認')) {
            standardMessage = alert.message.replace('従業員勤怠確認', '勤怠データ確認');
        }
        
        const title = alert.details ? `${standardMessage}: ${alert.details}` : standardMessage;
        
        return `<div class="alert-item ${className}" title="${title.replace(/"/g, '&quot;')}">
            <span class="alert-icon">${icon}</span>
            <span>${standardMessage}</span>
        </div>`;
    }).join('');
    
    return formatted;
}

/**
 * 勤務タイプに応じたCSSクラスを取得
 * @param {string} workType - 勤務タイプ
 * @returns {string} CSSクラス名
 */
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

/**
 * チェック状況のHTMLを生成
 * @param {Object} item - アイテムオブジェクト
 * @param {Array} alerts - アラート配列
 * @returns {string} HTML文字列
 */
function generateCheckStatusHTML(item, alerts) {
    const hasMissingPunch = alerts.some(alert => alert.message && alert.message.includes('打刻なし'));
    const hasPunchLeak = alerts.some(alert => alert.message && alert.message.includes('打刻漏れ'));
    // 「出勤時刻に差異あり」「退勤時刻に差異あり」「出退勤時刻に差異あり」のいずれかにマッチ
    const hasTimeDifference = alerts.some(alert => alert.message && (
        alert.message.includes('時刻に差異あり') || 
        alert.message.includes('時刻差異')
    ));
    
    if (!hasMissingPunch && !hasPunchLeak && !hasTimeDifference) {
        return '<span style="color: #999;">-</span>';
    }
    
    let html = '<div class="check-container">';
    
    if (hasMissingPunch) {
        html += `
            <div class="check-item">
                <input type="checkbox" 
                       id="missing-${item.employee_id}-${item.work_date}" 
                       data-type="${CheckType.MISSING_PUNCH}"
                       data-employee="${item.employee_id}"
                       data-date="${item.work_date}"
                       onchange="updateCheckStatus(this)">
                <label for="missing-${item.employee_id}-${item.work_date}">打刻なし</label>
            </div>
            <div id="missing-status-${item.employee_id}-${item.work_date}" class="check-status">未確認</div>
        `;
    }
    
    if (hasPunchLeak) {
        html += `
            <div class="check-item">
                <input type="checkbox" 
                       id="punchleak-${item.employee_id}-${item.work_date}" 
                       data-type="${CheckType.PUNCH_LEAK}"
                       data-employee="${item.employee_id}"
                       data-date="${item.work_date}"
                       onchange="updateCheckStatus(this)">
                <label for="punchleak-${item.employee_id}-${item.work_date}">打刻漏れ</label>
            </div>
            <div id="punchleak-status-${item.employee_id}-${item.work_date}" class="check-status">未確認</div>
        `;
    }
    
    if (hasTimeDifference) {
        html += `
            <div class="check-item">
                <input type="checkbox" 
                       id="timediff-${item.employee_id}-${item.work_date}" 
                       data-type="${CheckType.TIME_DIFFERENCE}"
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
 * 24勤の退勤時刻を翌日の明に移動する処理
 * @param {Array} results - 検索結果配列
 * @returns {Array} 処理済み結果配列
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

/**
 * 退勤時刻表示（24勤の場合は翌日明に表示）
 * @param {Object} item - アイテムオブジェクト
 * @returns {string} フォーマットされた退勤時刻
 */
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

