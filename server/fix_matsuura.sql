-- 松浦真司の勤怠スケジュールを4552899に修正
-- まず現在の状況を確認

-- employee_masterの松浦関連レコード確認
.headers on
.mode column

SELECT '=== employee_master の松浦関連レコード ===' as info;
SELECT employee_num, name, idm FROM employee_master WHERE name LIKE '%松浦%';

-- attend_scheduleの松浦真司レコード確認
SELECT '=== attend_schedule の松浦真司（社員ID別） ===' as info;
SELECT employee_id, COUNT(*) as count FROM attend_schedule 
WHERE name = '松浦　真司' 
GROUP BY employee_id;

-- 4452133を4552899に更新
SELECT '=== 4452133 → 4552899 更新実行 ===' as info;
UPDATE attend_schedule 
SET employee_id = '4552899' 
WHERE name = '松浦　真司' AND employee_id = '4452133';

SELECT '更新件数: ' || changes() as update_info;

-- 更新後の確認
SELECT '=== 更新後の状況 ===' as info;
SELECT employee_id, COUNT(*) as count FROM attend_schedule 
WHERE name = '松浦　真司' 
GROUP BY employee_id;

-- 4452133レコードが残っていないか最終確認
SELECT '=== 4452133残存確認 ===' as info;
SELECT COUNT(*) as remaining_4452133_count FROM attend_schedule 
WHERE name = '松浦　真司' AND employee_id = '4452133';