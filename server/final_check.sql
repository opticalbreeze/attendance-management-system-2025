-- 最終確認用シンプルクエリ
-- 4452133が残っていないかチェック

SELECT 'attend_schedule' as table_name, COUNT(*) as count_4452133 FROM attend_schedule WHERE employee_id = '4452133'
UNION ALL
SELECT 'leave_request', COUNT(*) FROM leave_request WHERE employee_id = '4452133'
UNION ALL  
SELECT 'overtime', COUNT(*) FROM overtime WHERE employee_id = '4452133'
UNION ALL
SELECT 'attend_schedule', COUNT(*) FROM attend_schedule WHERE employee_id = '4552899'
UNION ALL
SELECT 'leave_request', COUNT(*) FROM leave_request WHERE employee_id = '4552899'
UNION ALL
SELECT 'overtime', COUNT(*) FROM overtime WHERE employee_id = '4552899';