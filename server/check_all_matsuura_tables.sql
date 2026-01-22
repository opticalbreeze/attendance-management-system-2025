-- 松浦氏の社員番号4452133が使用されている全テーブルを確認
.headers on
.mode column

-- attend_scheduleテーブルの確認
SELECT '=== attend_schedule テーブル ===' as info;
SELECT employee_id, COUNT(*) as count FROM attend_schedule 
WHERE employee_id = '4452133' OR employee_id = '4552899'
GROUP BY employee_id;

-- leave_requestテーブルの確認  
SELECT '=== leave_request テーブル ===' as info;
SELECT employee_id, COUNT(*) as count FROM leave_request 
WHERE employee_id = '4452133' OR employee_id = '4552899'
GROUP BY employee_id;

-- overtimeテーブルの確認
SELECT '=== overtime テーブル ===' as info;
SELECT employee_id, COUNT(*) as count FROM overtime 
WHERE employee_id = '4452133' OR employee_id = '4552899'
GROUP BY employee_id;

-- employee_masterの確認
SELECT '=== employee_master テーブル ===' as info;
SELECT employee_num, name FROM employee_master 
WHERE employee_num = '4452133' OR employee_num = '4552899';

-- テーブル一覧確認
SELECT '=== 全テーブル一覧 ===' as info;
.tables