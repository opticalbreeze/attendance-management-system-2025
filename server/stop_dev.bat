@echo off
echo ====================================
echo   勤怠管理システム - 開発環境停止
echo ====================================
echo.

cd /d "%~dp0"

echo [開発環境] Dockerコンテナを停止中...
docker-compose -f docker-compose.dev.yml down

if %ERRORLEVEL% EQ 0 (
    echo.
    echo ✅ 開発環境を停止しました
    echo.
) else (
    echo.
    echo ❌ 停止に失敗しました
    echo.
)

pause