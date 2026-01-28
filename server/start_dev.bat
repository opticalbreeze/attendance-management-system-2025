@echo off
echo ====================================
echo   勤怠管理システム - 開発環境起動
echo ====================================
echo.
echo ポート: 5001 (本番は5000)
echo URL: http://localhost:5001
echo.

cd /d "%~dp0"

echo [開発環境] Dockerコンテナを起動中...
docker-compose -f docker-compose.dev.yml up -d

if %ERRORLEVEL% EQ 0 (
    echo.
    echo ✅ 開発環境が正常に起動しました
    echo 📋 URL: http://localhost:5001
    echo 🔧 デバッグモード: 有効
    echo.
    echo 🚀 カードリーダーテスト用URL:
    echo    http://localhost:5001/api/health
    echo.
    echo ログを確認する場合は docker logs attendance-server-dev -f
    echo.
    pause
) else (
    echo.
    echo ❌ 起動に失敗しました
    echo.
    pause
)