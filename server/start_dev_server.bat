@echo off
REM 開発用サーバー起動スクリプト

echo ================================
echo 開発用勤怠管理サーバーを起動中...
echo ポート: 5001 (開発用)
echo ================================

cd /d %~dp0

REM 開発用コンテナが既に動いている場合は停止
docker-compose -f docker-compose-dev.yml down

REM 開発用コンテナをビルドして起動
docker-compose -f docker-compose-dev.yml up --build -d

echo.
echo 開発用サーバーが起動しました！
echo.
echo アクセス先:
echo   開発環境: http://localhost:5001
echo   本番環境: http://localhost:5000 (そのまま稼働中)
echo.
echo 開発用ログを確認:
echo   docker logs attendance-server-dev -f
echo.
echo 停止するには:
echo   stop_dev_server.bat を実行
echo.
pause