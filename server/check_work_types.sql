-- 勤務種別の全種類を確認
.headers on
.mode column

-- attend_scheduleテーブルから実際に使用されている勤務種別を取得
SELECT '=== attend_schedule テーブルの勤務種別 ===' as info;
SELECT DISTINCT work_type as 勤務種別, COUNT(*) as 件数 
FROM attend_schedule 
WHERE work_type IS NOT NULL AND work_type != ''
GROUP BY work_type 
ORDER BY 件数 DESC;

-- 総数も表示
SELECT '=== 勤務種別の総数 ===' as info;
SELECT COUNT(DISTINCT work_type) as 勤務種別総数 
FROM attend_schedule 
WHERE work_type IS NOT NULL AND work_type != '';