@echo off
chcp 65001 >nul
echo ========================================
echo 🔖 打刻システム - Docker起動（ルート版）
echo ========================================
echo.

cd /d %~dp0

echo [1/3] Dockerイメージのビルド...
docker-compose build
if %errorlevel% neq 0 (
    echo ❌ ビルドエラーが発生しました
    pause
    exit /b 1
)

echo.
echo [2/3] コンテナの起動...
docker-compose up -d
if %errorlevel% neq 0 (
    echo ❌ 起動エラーが発生しました
    echo Docker Desktopが起動しているか確認してください
    pause
    exit /b 1
)

echo.
echo [3/3] 起動確認...
timeout /t 3 >nul
docker-compose ps

echo.
echo ========================================
echo ✅ Docker起動完了！
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

