# 🔒 セキュリティ設定ガイド

## 概要

管理画面へのパスワード認証とデータベースアクセス保護を実装しました。

---

## 📋 実装内容

### 1. 管理画面のパスワード認証

- **ログイン画面**: `/login`
- **デフォルトパスワード**: `admin`
- **保護対象ページ**:
  - `/search` - 検索ページ
  - `/check` - 勤怠チェックページ
  - `/overtime/list` - 時間外一覧（管理用）
  - `/leave/list` - 休暇願一覧（管理用）

### 2. データベースアクセス保護

- **データベースパスワード**: ログイン時に別途設定可能
- **デフォルトパスワード**: `dbadmin`
- **機能**: データベース接続時に権限チェック

---

## ⚙️ パスワードの設定方法

### 方法1: 環境変数で設定（推奨）

#### Docker環境の場合

`server/docker-compose.yml`の環境変数セクションを編集：

```yaml
environment:
  # セキュリティ設定（本番環境では必ず変更）
  - SECRET_KEY=your-secure-secret-key-here
  - ADMIN_PASSWORD=your-admin-password-here
  - DB_PASSWORD=your-db-password-here
```

#### ローカル環境の場合

環境変数を設定：

```bash
# Windows (PowerShell)
$env:SECRET_KEY="your-secure-secret-key-here"
$env:ADMIN_PASSWORD="your-admin-password-here"
$env:DB_PASSWORD="your-db-password-here"

# Linux/Mac
export SECRET_KEY="your-secure-secret-key-here"
export ADMIN_PASSWORD="your-admin-password-here"
export DB_PASSWORD="your-db-password-here"
```

### 方法2: .envファイルで設定（推奨）

`server/.env`ファイルを作成：

```env
SECRET_KEY=your-secure-secret-key-here
ADMIN_PASSWORD=your-admin-password-here
DB_PASSWORD=your-db-password-here
```

**注意**: `.env`ファイルは`.gitignore`に追加してください。

---

## 🔐 パスワードの強度について

### 推奨されるパスワード要件

- **管理者パスワード**: 12文字以上、大文字・小文字・数字・記号を含む
- **データベースパスワード**: 16文字以上、大文字・小文字・数字・記号を含む
- **SECRET_KEY**: 32文字以上のランダムな文字列

### パスワード生成例

```python
import secrets
import string

# SECRET_KEY生成
secret_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
print(f"SECRET_KEY={secret_key}")

# パスワード生成
password = ''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(16))
print(f"ADMIN_PASSWORD={password}")
```

---

## 🚀 使用方法

### 1. ログイン

1. ブラウザで `http://localhost:5000/login` にアクセス
2. 管理者パスワードを入力
3. （オプション）データベースアクセス権限が必要な場合は、チェックボックスをONにしてデータベースパスワードを入力
4. 「ログイン」ボタンをクリック

### 2. 管理画面へのアクセス

ログイン後、以下のページにアクセスできます：
- `/search` - 検索ページ
- `/check` - 勤怠チェックページ
- `/overtime/list` - 時間外一覧
- `/leave/list` - 休暇願一覧

### 3. ログアウト

- `/logout` にアクセスするか、セッションが切れるまで待つ

---

## ⚠️ 重要な注意事項

1. **デフォルトパスワードは必ず変更してください**
   - デフォルトの`admin`と`dbadmin`は本番環境では使用しないでください

2. **SECRET_KEYは必ず設定してください**
   - セッションの暗号化に使用されます
   - 推測されにくいランダムな文字列を設定してください

3. **環境変数の管理**
   - パスワードは環境変数で管理し、コードに直接書かないでください
   - `.env`ファイルは`.gitignore`に追加してください

4. **HTTPS環境での設定**
   - HTTPS環境では`SESSION_COOKIE_SECURE = True`を有効化してください
   - `server/config.py`の該当行のコメントを外してください

---

## 🔧 トラブルシューティング

### ログインできない場合

1. パスワードが正しいか確認
2. ブラウザのコンソールでエラーを確認
3. サーバーログを確認: `docker-compose logs -f`

### セッションが切れる場合

- セッションの有効期限はブラウザを閉じるまでです
- 長時間使用する場合は、定期的に再ログインが必要です

### データベースアクセス権限エラー

- データベースアクセスが必要な操作では、ログイン時に「データベースアクセス権限も取得する」にチェックを入れて、データベースパスワードを入力してください

---

## 📝 セキュリティチェックリスト

- [ ] デフォルトパスワードを変更した
- [ ] SECRET_KEYを設定した
- [ ] 環境変数でパスワードを管理している
- [ ] `.env`ファイルを`.gitignore`に追加した
- [ ] HTTPS環境では`SESSION_COOKIE_SECURE`を有効化した
- [ ] パスワードは12文字以上で複雑な文字列にした

