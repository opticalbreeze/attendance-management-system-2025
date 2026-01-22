#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
松浦真司さんの休暇申請データを確認するスクリプト
"""

import sqlite3
import sys
import os
sys.path.append('.')
from config import Config

# データベース接続
conn = sqlite3.connect(Config.DATABASE_PATH)
cursor = conn.cursor()

print('=== 松浦真司さん（社員番号4552899）の休暇申請一覧 ===')
cursor.execute('''
    SELECT id, employee_num, leave_date_from, leave_date_to, 
           leave_type, leave_subtype, substitute_work_date,
           application_date, other_reason, created_at
    FROM leave_request 
    WHERE employee_num = 4552899
    ORDER BY leave_date_from DESC
''')

results = cursor.fetchall()
if results:
    print(f'松浦真司さんの休暇申請が{len(results)}件見つかりました：')
    print()
    for row in results:
        print(f'ID: {row[0]}, 社員番号: {row[1]}')
        print(f'休暇期間: {row[2]} ～ {row[3]}')
        print(f'休暇種別: {row[4]}, サブタイプ: {row[5]}')
        print(f'振替出勤日: {row[6]}, 申請日: {row[7]}')
        print(f'その他理由: {row[8]}')
        print(f'登録日時: {row[9]}')
        print('-' * 50)
else:
    print('松浦真司さんの休暇申請は見つかりませんでした。')
    
    # 4452133（旧社員番号）でも確認
    print('\n=== 旧社員番号（4452133）で確認 ===')
    cursor.execute('''
        SELECT id, employee_num, leave_date_from, leave_date_to, 
               leave_type, leave_subtype, substitute_work_date,
               application_date, other_reason, created_at
        FROM leave_request 
        WHERE employee_num = 4452133
        ORDER BY leave_date_from DESC
    ''')
    old_results = cursor.fetchall()
    if old_results:
        print(f'旧社員番号での休暇申請が{len(old_results)}件見つかりました：')
        print()
        for row in old_results:
            print(f'ID: {row[0]}, 社員番号: {row[1]}')
            print(f'休暇期間: {row[2]} ～ {row[3]}')
            print(f'休暇種別: {row[4]}, サブタイプ: {row[5]}')
            print(f'振替出勤日: {row[6]}, 申請日: {row[7]}')
            print(f'その他理由: {row[8]}')
            print(f'登録日時: {row[9]}')
            print('-' * 50)
    else:
        print('旧社員番号でも休暇申請は見つかりませんでした。')

# 従業員マスターで松浦真司さんの現在の状況を確認
print('\n=== 従業員マスター確認 ===')
cursor.execute('''
    SELECT id, name, 
           CASE 
               WHEN id = 4552899 THEN '新社員番号'
               WHEN id = 4452133 THEN '旧社員番号'
               ELSE '不明'
           END as id_type
    FROM employee_master 
    WHERE name = '松浦　真司'
    ORDER BY id
''')

master_results = cursor.fetchall()
if master_results:
    print('従業員マスターでの松浦真司さんの登録状況：')
    for row in master_results:
        print(f'ID: {row[0]}, 名前: {row[1]}, タイプ: {row[2]}')
else:
    print('従業員マスターで松浦真司さんが見つかりません')

conn.close()
print('\n処理完了')