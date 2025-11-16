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
cursor.execute('SELECT employee_id, employee_name, idm FROM employee_master ORDER BY employee_id')
employees = cursor.fetchall()
print('全従業員データ:')
for emp in employees:
    print(f'  従業員ID: {emp[0]}, 名前: {emp[1]}, IDM: {emp[2]}')

print('\n=== IDMが設定されている従業員 ===')
cursor.execute('SELECT employee_id, employee_name, idm FROM employee_master WHERE idm IS NOT NULL AND idm != ""')
employees_with_idm = cursor.fetchall()
if employees_with_idm:
    print('IDMが設定されている従業員:')
    for emp in employees_with_idm:
        print(f'  従業員ID: {emp[0]}, 名前: {emp[1]}, IDM: {emp[2]}')
else:
    print('IDMが設定されている従業員がいません')

print('\n=== 打刻データで使用されているIDMの確認 ===')
cursor.execute('SELECT DISTINCT idm FROM attendance ORDER BY idm')
attendance_idms = cursor.fetchall()
print('打刻データで使用されているIDM:')
for idm in attendance_idms:
    print(f'  {idm[0]}')

conn.close()