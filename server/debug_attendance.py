#!/usr/bin/env python3
import sqlite3
from utils import get_database_connection

# attendanceテーブルの該当データを詳細確認
conn = get_database_connection()
cursor = conn.cursor()

target_idm = "0116020034193100"

print(f'=== attendanceテーブルの該当データ (IDM: {target_idm}) ===')
cursor.execute('SELECT * FROM attendance WHERE idm = ? ORDER BY timestamp DESC LIMIT 5', (target_idm,))
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f'ID: {row[0]}, IDM: {row[1]}, timestamp: {row[2]}, terminal: {row[3]}, received_at: {row[4]}')
else:
    print('該当する打刻データが見つかりません')

print(f'\n=== employee_masterテーブルの該当従業員確認 (IDM: {target_idm}) ===')
cursor.execute('SELECT * FROM employee_master WHERE idm = ?', (target_idm,))
employee = cursor.fetchone()
if employee:
    print(f'従業員情報: ID={employee[0]}, 名前={employee[1]}, IDM={employee[2]}')
else:
    print('該当するIDMの従業員がemployee_masterテーブルに見つかりません')

print(f'\n=== employee_masterテーブル全体確認（一部） ===')
cursor.execute('SELECT * FROM employee_master LIMIT 10')
employees = cursor.fetchall()
print('登録済み従業員一覧（最初の10人）:')
for emp in employees:
    print(f'  ID={emp[0]}, 名前={emp[1]}, IDM={emp[2]}')

print(f'\n=== attendanceテーブルの最新データ確認 ===')
cursor.execute('SELECT * FROM attendance ORDER BY received_at DESC LIMIT 5')
latest_records = cursor.fetchall()
print('最新の打刻データ:')
for record in latest_records:
    print(f'  IDM: {record[1]}, timestamp: {record[2]}, terminal: {record[3]}')

conn.close()