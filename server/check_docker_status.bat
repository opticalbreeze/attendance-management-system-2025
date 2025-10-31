@echo off
chcp 65001 >nul
echo ========================================
echo 🔍 Docker起動状態確認
echo ========================================
echo.

cd /d %~dp0

echo [1] Dockerコンテナの状態確認...
echo.
docker-compose ps

echo.
echo [2] Dockerコンテナのログ（最新10行）...
echo.
docker-compose logs --tail=10

echo.
echo [3] ポート5000の使用状況確認...
echo.
netstat -ano | findstr :5000

echo.
echo ========================================
echo ✅ 確認完了
echo ========================================
echo.
echo コンテナが起動していない場合:
echo   start_docker.bat を実行してください
echo.
pause

