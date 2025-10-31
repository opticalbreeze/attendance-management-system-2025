@echo off
chcp 65001 >nul
echo ========================================
echo 📤 GitHubにプッシュ
echo ========================================
echo.

cd /d %~dp0

echo [1/5] Gitの状態確認...
git status
echo.

echo [2/5] リモートリポジトリ確認...
git remote -v
echo.

echo [3/5] すべての変更をステージング...
git add .
if %errorlevel% neq 0 (
    echo ❌ git add エラーが発生しました
    pause
    exit /b 1
)
echo ✅ ステージング完了
echo.

echo [4/5] コミット...
set /p commit_message="コミットメッセージを入力してください（Enterでデフォルト）: "
if "%commit_message%"=="" set commit_message=設定ファイル統合とコード整理: config.py追加、重複関数削除、ドキュメント更新

git commit -m "%commit_message%"
if %errorlevel% neq 0 (
    echo ❌ コミットエラーが発生しました
    echo 変更がないか、すでにコミット済みの可能性があります
    pause
    exit /b 1
)
echo ✅ コミット完了
echo.

echo [5/5] GitHubにプッシュ...
git push origin main
if %errorlevel% neq 0 (
    echo.
    echo ⚠️  mainブランチへのプッシュに失敗しました
    echo masterブランチを試します...
    git push origin master
    if %errorlevel% neq 0 (
        echo ❌ プッシュエラーが発生しました
        echo.
        echo [確認事項]
        echo 1. GitHubの認証情報が正しいか確認
        echo 2. リモートリポジトリが正しく設定されているか確認
        echo 3. ブランチ名を確認: git branch
        pause
        exit /b 1
    )
)
echo.

echo ========================================
echo ✅ GitHubへのプッシュ完了！
echo ========================================
echo.
echo 🌐 https://github.com/opticalbreeze/attend_server で確認できます
echo.
pause

