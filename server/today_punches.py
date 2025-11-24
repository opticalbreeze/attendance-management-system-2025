import sqlite3
from datetime import datetime

conn = sqlite3.connect('/app/data/attendance.db')
cursor = conn.cursor()

today = datetime.now().date()

print(f'📅 今日（{today}）の従業員別打刻回数')
print('=' * 80)

# 今日の打刻データを従業員別に集計
cursor.execute('''
    SELECT 
        em.employee_num,
        em.name,
        em.section,
        COUNT(a.id) as punch_count,
        MIN(a.timestamp) as first_punch,
        MAX(a.timestamp) as last_punch
    FROM employee_master em
    LEFT JOIN attendance a ON em.idm = a.idm AND DATE(a.timestamp) = ?
    GROUP BY em.employee_num, em.name, em.section
    ORDER BY punch_count DESC, em.employee_num
''', (str(today),))

results = cursor.fetchall()

total_employees = 0
employees_with_punches = 0
total_punches = 0

print('👤 従業員別打刻状況:')
print('-' * 80)

for row in results:
    emp_num = row[0]
    name = row[1]
    section = row[2] or '設備'
    punch_count = row[3]
    first_punch = row[4]
    last_punch = row[5]
    
    total_employees += 1
    total_punches += punch_count
    
    if punch_count > 0:
        employees_with_punches += 1
        # 時刻のみを抽出
        first_time = first_punch[11:19] if first_punch else ''
        last_time = last_punch[11:19] if last_punch else ''
        if first_time == last_time:
            time_range = first_time
        else:
            time_range = f'{first_time} - {last_time}'
        
        status_icon = '✅' if punch_count >= 2 else '⚠️'
        print(f'  {status_icon} {emp_num:7} {name:12} [{section:4}] {punch_count:2}回 ({time_range})')
    else:
        print(f'  ❌ {emp_num:7} {name:12} [{section:4}]  0回 (打刻なし)')

print('=' * 80)
print(f'📊 集計結果:')
print(f'  👥 総従業員数: {total_employees}名')
print(f'  ✅ 打刻あり: {employees_with_punches}名')
print(f'  ❌ 打刻なし: {total_employees - employees_with_punches}名')
print(f'  📱 総打刻回数: {total_punches}回')
if employees_with_punches > 0:
    avg_punches = total_punches / employees_with_punches
    print(f'  📈 打刻者平均: {avg_punches:.1f}回/人')

print()
print('🔍 今日の全打刻データ（時系列順）:')
print('-' * 80)

cursor.execute('''
    SELECT 
        em.employee_num,
        em.name,
        a.timestamp,
        a.terminal_id
    FROM attendance a
    LEFT JOIN employee_master em ON a.idm = em.idm
    WHERE DATE(a.timestamp) = ?
    ORDER BY a.timestamp
''', (str(today),))

punch_details = cursor.fetchall()

for i, row in enumerate(punch_details, 1):
    emp_num = row[0] or 'Unknown'
    name = row[1] or 'IDM不明'
    timestamp = row[2]
    terminal_id = row[3]
    time_only = timestamp[11:19] if len(timestamp) > 19 else timestamp
    
    print(f'  {i:2}. {time_only} - {emp_num:7} {name:12} (端末:{terminal_id})')

conn.close()
print('\n✅ 打刻データ確認完了')