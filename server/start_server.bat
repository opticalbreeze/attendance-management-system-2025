@echo off
chcp 65001 >nul
echo ======================================
echo   打刻システム - サーバー起動
echo ======================================
echo.
echo サーバーを起動しています...
echo ブラウザで http://192.168.1.31:5000 にアクセスしてください
echo.

python server.py

pause

