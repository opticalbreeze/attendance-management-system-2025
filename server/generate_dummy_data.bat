@echo off
chcp 65001 >nul
echo ======================================
echo   ダミーデータ生成
echo ======================================
echo.

python generate_dummy_data.py

echo.
pause

