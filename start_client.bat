@echo off
chcp 65001 >nul
echo ======================================
echo   打刻システム - クライアント起動
echo ======================================
echo.

python client_card_reader.py

pause

