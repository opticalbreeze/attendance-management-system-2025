#!/usr/bin/env python3
from utils import get_database_connection

conn = get_database_connection()
cursor = conn.cursor()

print('=== employee_masterテーブル構造確認 ===')
cursor.execute('PRAGMA table_info(employee_master)')
columns = cursor.fetchall()
for col in columns:
    not_null = "Yes" if col[3] else "No"
    print(f'  {col[1]} ({col[2]}) - NOT NULL: {not_null}')

print('\n=== 全従業員データの確認 ===')
cursor.execute('SELECT id, employee_num, name, idm FROM employee_master ORDER BY id')
employees = cursor.fetchall()
print('全従業員データ:')
for emp in employees:
    print(f'  ID: {emp[0]}, 従業員番号: {emp[1]}, 名前: {emp[2]}, IDM: {emp[3]}')

print('\n=== IDMが設定されている従業員 ===')
cursor.execute('SELECT id, employee_num, name, idm FROM employee_master WHERE idm IS NOT NULL AND idm != ""')
employees_with_idm = cursor.fetchall()
if employees_with_idm:
    print('IDMが設定されている従業員:')
    for emp in employees_with_idm:
        print(f'  ID: {emp[0]}, 従業員番号: {emp[1]}, 名前: {emp[2]}, IDM: {emp[3]}')
else:
    print('IDMが設定されている従業員がいません')

print('\n=== 打刻データで使用されているIDMの確認 ===')
cursor.execute('SELECT DISTINCT idm, COUNT(*) as count FROM attendance GROUP BY idm ORDER BY count DESC')
attendance_idms = cursor.fetchall()
print('打刻データで使用されているIDM (出現回数順):')
for idm_data in attendance_idms:
    print(f'  {idm_data[0]} ({idm_data[1]}回)')

print('\n=== 特定IDMの詳細確認 ===')
target_idm = "0116020034193100"
cursor.execute('SELECT COUNT(*) FROM attendance WHERE idm = ?', (target_idm,))
count = cursor.fetchone()[0]
print(f'IDM {target_idm} の打刻回数: {count}回')

# employee_masterで類似のデータを探す
cursor.execute('SELECT id, employee_num, name, idm FROM employee_master WHERE idm LIKE ?', (f'%{target_idm[-8:]}%',))
similar = cursor.fetchall()
if similar:
    print(f'\n類似するIDMを持つ従業員:')
    for emp in similar:
        print(f'  ID: {emp[0]}, 従業員番号: {emp[1]}, 名前: {emp[2]}, IDM: {emp[3]}')

conn.close()