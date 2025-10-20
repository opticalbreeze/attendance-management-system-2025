@echo off
chcp 65001 >nul
echo ======================================
echo   打刻システム - Docker停止
echo ======================================
echo.

echo Docker Composeでサーバーを停止しています...
echo.

docker-compose down

echo.
echo ✅ サーバーを停止しました
echo.

pause

