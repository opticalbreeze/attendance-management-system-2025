import sqlite3

conn = sqlite3.connect('/app/data/attendance.db')
cursor = conn.cursor()

print('🗄️ データベーステーブル一覧:')
print('=' * 50)

cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()

for table in tables:
    table_name = table[0]
    cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
    count = cursor.fetchone()[0]
    print(f'📊 {table_name:20} : {count:6}件')

print()

# attend_scheduleテーブルが存在するかチェック
table_names = [t[0] for t in tables]
if 'attend_schedule' in table_names:
    print('🔍 attend_scheduleの最新5件:')
    print('=' * 50)
    cursor.execute('SELECT * FROM attend_schedule ORDER BY created_at DESC LIMIT 5')
    schedule_rows = cursor.fetchall()
    
    for i, row in enumerate(schedule_rows, 1):
        print(f'{i:2}. ID:{row[2]} {row[3]} | 日付:{row[4]} | 時間:{row[5]}-{row[6]} | タイプ:{row[7]}')
else:
    print('❌ attend_scheduleテーブルが存在しません')

print()

# attendanceテーブルの確認
if 'attendance' in table_names:
    print('🔍 attendanceの最新5件:')
    print('=' * 50)
    cursor.execute('SELECT * FROM attendance ORDER BY received_at DESC LIMIT 5')
    attendance_rows = cursor.fetchall()
    
    for i, row in enumerate(attendance_rows, 1):
        print(f'{i:2}. IDM:{row[1]} | 時刻:{row[2]} | 端末:{row[3]} | 受信:{row[4]}')
else:
    print('❌ attendanceテーブルが存在しません')

conn.close()
print('\n✅ データベース確認完了')