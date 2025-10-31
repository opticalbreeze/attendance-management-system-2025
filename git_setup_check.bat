@echo off
chcp 65001 >nul
echo ========================================
echo 🔍 Git設定確認
echo ========================================
echo.

cd /d %~dp0

echo [1] Gitのバージョン確認...
git --version
echo.

echo [2] リモートリポジトリ確認...
git remote -v
if %errorlevel% neq 0 (
    echo.
    echo ⚠️ リモートリポジトリが設定されていません
    echo.
    echo 以下のコマンドで設定してください:
    echo   git remote add origin https://github.com/opticalbreeze/attend_server.git
    echo.
)
echo.

echo [3] 現在のブランチ確認...
git branch
echo.

echo [4] Gitの状態確認...
git status
echo.

echo [5] 最新のコミット履歴（5件）...
git log --oneline -5
echo.

echo ========================================
echo ✅ 確認完了
echo ========================================
echo.
pause

