# 📤 GitHubへのプッシュ手順

## 🎯 目的

このプロジェクトの最新版を GitHub リポジトリ `https://github.com/opticalbreeze/attend_server` にプッシュします。

---

## 📋 前提条件

1. **Git** がインストールされていること
2. **GitHubアカウント** にアクセス権限があること
3. **リモートリポジトリ** が正しく設定されていること

---

## 🚀 プッシュ手順

### 方法1: バッチファイルを使用（推奨）

**PowerShellの場合:**
```powershell
# 1. Git設定を確認
.\git_setup_check.bat

# 2. GitHubにプッシュ
.\push_to_github.bat
```

**コマンドプロンプト（cmd）の場合:**
```cmd
# 1. Git設定を確認
git_setup_check.bat

# 2. GitHubにプッシュ
push_to_github.bat
```

### 方法2: コマンドラインから直接実行

```bash
# 1. 変更を確認
git status

# 2. すべての変更をステージング
git add .

# 3. コミット
git commit -m "設定ファイル統合とコード整理: config.py追加、重複関数削除、ドキュメント更新"

# 4. GitHubにプッシュ
git push origin main
# または
git push origin master
```

---

## ✅ 確認事項

### リモートリポジトリが設定されていない場合

```bash
git remote add origin https://github.com/opticalbreeze/attend_server.git
```

### ブランチ名を確認

```bash
git branch
```

- `main` ブランチの場合: `git push origin main`
- `master` ブランチの場合: `git push origin master`

### 認証エラーが発生した場合

GitHubでPersonal Access Tokenを使用する必要がある場合があります：

1. GitHub → Settings → Developer settings → Personal access tokens
2. 新しいトークンを作成（`repo` スコープが必要）
3. プッシュ時にトークンを使用

または、Git Credential Managerを使用：

```bash
git config --global credential.helper manager-core
```

---

## 📝 コミットメッセージの例

```
設定ファイル統合とコード整理

- config.pyを追加し、すべての設定値を一元管理
- utils.pyの重複関数を削除（4つの重複関数）
- 未使用関数を削除（json_response, calculate_attendance_period, safe_float）
- ハードコーディングされた設定値をconfig.pyに移行
- docker-compose.ymlをルートディレクトリにも追加
- ドキュメントを実装に合わせて更新
```

---

## 🔍 トラブルシューティング

### エラー: "remote origin already exists"

```bash
# 既存のリモートを確認
git remote -v

# 必要に応じて削除して再追加
git remote remove origin
git remote add origin https://github.com/opticalbreeze/attend_server.git
```

### エラー: "failed to push some refs"

```bash
# リモートの最新版を取得
git pull origin main --rebase

# 再度プッシュ
git push origin main
```

### エラー: "authentication failed"

1. GitHubの認証情報を確認
2. Personal Access Tokenを使用
3. SSH鍵を使用する場合は設定を確認

---

## 📊 プッシュ後の確認

プッシュが成功したら、以下のURLで確認できます：

https://github.com/opticalbreeze/attend_server

---

## 🔄 今後の更新手順

1. 変更を加える
2. `git add .` でステージング
3. `git commit -m "変更内容"` でコミット
4. `git push origin main` でプッシュ

---

**最終更新**: 2025年10月31日
