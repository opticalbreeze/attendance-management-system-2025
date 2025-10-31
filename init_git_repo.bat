@echo off
chcp 65001 >nul
echo ========================================
echo 🔧 Gitリポジトリ初期化
echo ========================================
echo.

cd /d %~dp0

echo [1/4] Gitリポジトリを初期化...
git init
if %errorlevel% neq 0 (
    echo ❌ Git初期化エラーが発生しました
    echo Gitがインストールされているか確認してください
    pause
    exit /b 1
)
echo ✅ Gitリポジトリ初期化完了
echo.

echo [2/4] .gitignoreファイルの確認...
if not exist .gitignore (
    echo .gitignoreが存在しません。作成します...
    (
        echo # Python
        echo __pycache__/
        echo *.py[cod]
        echo *$py.class
        echo *.so
        echo .Python
        echo env/
        echo venv/
        echo ENV/
        echo.
        echo # Database
        echo *.db
        echo *.db-journal
        echo *.sqlite
        echo *.sqlite3
        echo.
        echo # IDE
        echo .vscode/
        echo .idea/
        echo *.swp
        echo *.swo
        echo *~
        echo.
        echo # OS
        echo .DS_Store
        echo Thumbs.db
        echo.
        echo # Logs
        echo *.log
        echo.
        echo # Environment
        echo .env
        echo .env.local
        echo.
        echo # Backup
        echo backup_*.db
        echo *.backup
    ) > .gitignore
    echo ✅ .gitignore作成完了
) else (
    echo ✅ .gitignoreは既に存在します
)
echo.

echo [3/4] リモートリポジトリを設定...
git remote remove origin 2>nul
git remote add origin https://github.com/opticalbreeze/attend_server.git
if %errorlevel% neq 0 (
    echo ❌ リモートリポジトリ設定エラーが発生しました
    pause
    exit /b 1
)
echo ✅ リモートリポジトリ設定完了
echo.

echo [4/4] 設定確認...
git remote -v
echo.

echo ========================================
echo ✅ Gitリポジトリ初期化完了！
echo ========================================
echo.
echo 次のステップ:
echo   1. ファイルをステージング: git add .
echo   2. コミット: git commit -m "初期コミット"
echo   3. プッシュ: git push -u origin main
echo.
echo または、push_to_github.bat を実行してください
echo.
pause

