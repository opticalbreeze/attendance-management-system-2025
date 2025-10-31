@echo off
chcp 65001 >nul
echo ========================================
echo 🚀 Docker起動と確認
echo ========================================
echo.

cd /d %~dp0

echo [1/4] Docker Composeでビルド＆起動...
docker-compose up -d --build
if %errorlevel% neq 0 (
    echo.
    echo ❌ 起動エラーが発生しました
    echo Docker Desktopが起動しているか確認してください
    pause
    exit /b 1
)

echo.
echo [2/4] 3秒待機（コンテナ起動待ち）...
timeout /t 3 >nul

echo.
echo [3/4] コンテナの状態確認...
docker-compose ps

echo.
echo [4/4] 最新のログ確認...
docker-compose logs --tail=20

echo.
echo ========================================
echo ✅ 起動完了！
echo ========================================
echo.
echo 🌐 ブラウザで http://localhost:5000 にアクセスしてください
echo.
echo [コマンド]
echo   ログ確認: docker-compose logs -f
echo   停止:     docker-compose down
echo   再起動:   docker-compose restart
echo.
pause

