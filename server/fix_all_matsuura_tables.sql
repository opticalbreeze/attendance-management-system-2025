-- 松浦氏の全テーブル社員番号を4452133→4552899に統一修正
-- バックアップは事前に作成済み

.headers on
.mode column

-- 修正前の状況確認
SELECT '=== 修正前の状況確認 ===' as info;

-- attend_scheduleテーブル
SELECT 'attend_schedule: ' || COUNT(*) as count FROM attend_schedule WHERE employee_id = '4452133';

-- leave_requestテーブル
SELECT 'leave_request: ' || COUNT(*) as count FROM leave_request WHERE employee_id = '4452133';

-- overtimeテーブル  
SELECT 'overtime: ' || COUNT(*) as count FROM overtime WHERE employee_id = '4452133';

-- 修正実行
SELECT '=== 修正実行 ===' as info;

-- attend_scheduleテーブルの修正
UPDATE attend_schedule SET employee_id = '4552899' WHERE employee_id = '4452133';
SELECT '✅ attend_schedule更新件数: ' || changes() as update_info;

-- leave_requestテーブルの修正
UPDATE leave_request SET employee_id = '4552899' WHERE employee_id = '4452133';
SELECT '✅ leave_request更新件数: ' || changes() as update_info;

-- overtimeテーブルの修正
UPDATE overtime SET employee_id = '4552899' WHERE employee_id = '4452133';
SELECT '✅ overtime更新件数: ' || changes() as update_info;

-- 修正後の確認
SELECT '=== 修正後の確認 ===' as info;

-- 4452133が残っていないか確認
SELECT 'attend_schedule残存: ' || COUNT(*) as remaining FROM attend_schedule WHERE employee_id = '4452133';
SELECT 'leave_request残存: ' || COUNT(*) as remaining FROM leave_request WHERE employee_id = '4452133';
SELECT 'overtime残存: ' || COUNT(*) as remaining FROM overtime WHERE employee_id = '4452133';

-- 4552899の件数確認
SELECT 'attend_schedule(4552899): ' || COUNT(*) as total FROM attend_schedule WHERE employee_id = '4552899';
SELECT 'leave_request(4552899): ' || COUNT(*) as total FROM leave_request WHERE employee_id = '4552899';
SELECT 'overtime(4552899): ' || COUNT(*) as total FROM overtime WHERE employee_id = '4552899';