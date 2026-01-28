@echo off
REM 開発用サーバー停止スクリプト

echo ================================
echo 開発用勤怠管理サーバーを停止中...
echo ================================

cd /d %~dp0

REM 開発用コンテナを停止
docker-compose -f docker-compose-dev.yml down

echo.
echo 開発用サーバーを停止しました。
echo.
echo 本番環境は引き続き稼働中:
echo   http://localhost:5000
echo.
pause