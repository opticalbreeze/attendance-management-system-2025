@echo off
chcp 65001 >nul
echo ======================================
echo   打刻システム - Docker起動
echo ======================================
echo.

echo Docker Composeでサーバーを起動しています...
echo.

docker-compose up -d

echo.
echo ✅ サーバーが起動しました
echo 🌐 ブラウザで http://192.168.1.31:5000 にアクセスしてください
echo.
echo コンテナログを確認: docker-compose logs -f
echo コンテナを停止: docker-compose down
echo.

pause

