# セットアップガイド - 打刻システム

## 🚀 クイックスタート（5分で起動）

> **💡 Docker版を使う場合**: [Docker版セットアップ](#docker版サーバー起動推奨)に進んでください

### ステップ1: サーバー側のセットアップ

1. **サーバーファイルを配置**

   以下のフォルダにサーバーファイルをコピーしてください：
   ```
   C:\Users\take_me_hospital\Desktop\N100\
   ```

   必要なファイル：
   - `server.py`
   - `start_server.bat`
   - `requirements_server.txt`
   - `templates/` フォルダ（中身も含む）

2. **依存パッケージのインストール**

   コマンドプロンプトまたはPowerShellを開き、以下を実行：

   ```cmd
   cd C:\Users\take_me_hospital\Desktop\N100
   pip install flask
   ```

3. **サーバー起動**

   `start_server.bat` をダブルクリック

   または：
   ```cmd
   python server.py
   ```

   表示されるメッセージ：
   ```
   ======================================================================
   🔖 打刻システム - サーバー
   ======================================================================
   ✅ データベース初期化完了
   📁 データベース: C:\Users\take_me_hospital\Desktop\N100\attendance.db
   🌐 サーバー起動: http://0.0.0.0:5000
   🔍 ブラウザで http://192.168.1.31:5000 にアクセスしてください
   ======================================================================
   ```

4. **動作確認**

   ブラウザで `http://192.168.1.31:5000` を開く

   トップページが表示されればOK！

---

## 🐳 Docker版サーバー起動（推奨）

Dockerを使うと、Pythonやパッケージのインストールが不要になります！

### 必要なもの
- Docker Desktop（インストール済み）

### 起動手順

1. **サーバーファイルを配置**

   以下のフォルダにサーバーファイルをコピー：
   ```
   C:\Users\take_me_hospital\Desktop\N100\
   ```

2. **Docker起動**

   `start_docker.bat` をダブルクリック

   または：
   ```cmd
   cd C:\Users\take_me_hospital\Desktop\N100
   docker-compose up -d
   ```

3. **動作確認**

   ブラウザで `http://192.168.1.31:5000` を開く

   トップページが表示されればOK！

### Docker操作コマンド

```bash
# サーバー起動
docker-compose up -d

# サーバー停止
docker-compose down

# ログ確認
docker-compose logs -f

# 状態確認
docker-compose ps
```

詳細は `server/DOCKER_GUIDE.md` を参照してください。

---

### ステップ2: クライアント側のセットアップ

1. **依存パッケージのインストール**

   コマンドプロンプトまたはPowerShellを開き、以下を実行：

   ```cmd
   pip install pyscard flask requests
   ```

   **Windows での注意:**
   - `pyscard`のインストールで`Microsoft Visual C++`が必要な場合があります
   - エラーが出た場合は、以下からインストール：
     https://visualstudio.microsoft.com/ja/visual-cpp-build-tools/

2. **カードリーダーを接続**

   - USBポートにカードリーダーを接続
   - デバイスマネージャーで認識を確認

3. **設定**

   `start_client_config.bat` をダブルクリック

   または：
   ```cmd
   python client_config_gui.py
   ```

   設定画面で入力：
   - **サーバーIP**: `192.168.1.31`
   - **ポート**: `5000`

   「💾 保存」をクリック

4. **クライアント起動**

   `start_client.bat` をダブルクリック

   または：
   ```cmd
   python client_card_reader.py
   ```

5. **動作確認**

   カードをかざしてみる → サーバーに送信されればOK！

---

## 📂 ファイル配置

### クライアント側（カードリーダー接続PC）

```
プロジェクトフォルダ/
├── client_card_reader.py        ← メインプログラム
├── client_config_gui.py          ← 設定GUI
├── start_client.bat              ← 起動用バッチファイル
├── start_client_config.bat       ← 設定用バッチファイル
├── requirements.txt              ← 依存パッケージ
├── client_config.json            ← 設定ファイル（自動生成）
└── local_cache.db                ← ローカルキャッシュ（自動生成）
```

### サーバー側

```
C:\Users\take_me_hospital\Desktop\N100\
├── server.py                     ← サーバープログラム
├── start_server.bat              ← 起動用バッチファイル
├── requirements_server.txt       ← 依存パッケージ
├── templates/
│   ├── index.html               ← トップページ
│   └── search.html              ← 検索ページ
└── attendance.db                 ← データベース（自動生成）
```

---

## 🌐 ネットワーク設定

### サーバーのIPアドレスを確認

#### Windows
```cmd
ipconfig
```

#### Linux/Mac
```bash
ifconfig
```

出力例：
```
IPv4 アドレス . . . . . . . . . . . : 192.168.1.31
```

このIPアドレスをクライアント側の設定で使用します。

### ファイアウォール設定

#### Windows Defender ファイアウォール

1. コントロールパネル → Windows Defender ファイアウォール
2. 「詳細設定」をクリック
3. 「受信の規則」→「新しい規則」
4. ポート → TCP → 特定のポート: `5000`
5. 接続を許可 → すべてのプロファイルにチェック
6. 名前: `打刻システムサーバー`

---

## 🔧 よくあるトラブル

### クライアント側

#### ❌ カードリーダーが検出されない

**原因1: ドライバー未インストール**
- デバイスマネージャーで「不明なデバイス」がないか確認
- カードリーダーのドライバーをインストール

**原因2: USBポート**
- 別のUSBポートに差し替えてみる
- USBハブを使っている場合は直接PCに接続

**原因3: pyscardが正しくインストールされていない**
```cmd
pip uninstall pyscard
pip install pyscard
```

#### ❌ サーバーに接続できない

**チェックリスト:**
1. サーバーが起動しているか？
2. IPアドレスは正しいか？（`client_config.json`を確認）
3. ファイアウォールで通信が許可されているか？
4. 同じネットワークに接続されているか？

**接続テスト:**
```cmd
# サーバーへのping
ping 192.168.1.31

# ポートの確認
telnet 192.168.1.31 5000
```

### サーバー側

#### ❌ ポート5000が使用中

**エラーメッセージ:**
```
OSError: [WinError 10048] 各ソケット アドレスに対してプロトコル、ネットワーク アドレス、またはポートのどれか 1 つのみを使用できます。
```

**解決策1: 使用中のプロセスを終了**
```cmd
# ポート使用状況確認
netstat -ano | findstr :5000

# プロセスを終了（PID確認後）
taskkill /PID [PID番号] /F
```

**解決策2: ポート番号を変更**

`server.py` の最終行を編集：
```python
app.run(host='0.0.0.0', port=5001, debug=False)  # 5001に変更
```

クライアント側も `client_config.json` で同じポートに変更：
```json
{
  "server_url": "http://192.168.1.31:5001"
}
```

#### ❌ データベースエラー

**解決策: データベースを再生成**
```cmd
cd C:\Users\take_me_hospital\Desktop\N100
del attendance.db
python server.py
```

---

## ✅ 動作確認チェックリスト

### サーバー側

- [ ] Pythonがインストールされている（3.7以上）
- [ ] Flaskがインストールされている
- [ ] `server.py`が正しく配置されている
- [ ] `templates/`フォルダが存在する
- [ ] ファイアウォールでポート5000が許可されている
- [ ] サーバーが起動している
- [ ] ブラウザでトップページが表示される

### クライアント側

- [ ] Pythonがインストールされている（3.7以上）
- [ ] pyscard, requests がインストールされている
- [ ] カードリーダーが接続されている
- [ ] カードリーダーが認識されている
- [ ] `client_config.json`にサーバーIPが正しく設定されている
- [ ] クライアントが起動している
- [ ] カードをかざして反応がある

---

## 🎓 初回セットアップ手順（詳細版）

### 1. Python環境の準備

#### Pythonのインストール確認
```cmd
python --version
```

表示例: `Python 3.11.0`

**インストールされていない場合:**
https://www.python.org/downloads/ からダウンロード

インストール時の注意:
- ✅ "Add Python to PATH" にチェックを入れる

#### pipのアップグレード
```cmd
python -m pip install --upgrade pip
```

### 2. サーバー側の完全セットアップ

```cmd
# 1. サーバーディレクトリに移動
cd C:\Users\take_me_hospital\Desktop\N100

# 2. 依存パッケージのインストール
pip install flask

# 3. サーバー起動テスト
python server.py
```

**成功メッセージが表示されれば OK！**

ブラウザで http://192.168.1.31:5000 を開く

### 3. クライアント側の完全セットアップ

```cmd
# 1. プロジェクトディレクトリに移動
cd [プロジェクトフォルダ]

# 2. 依存パッケージのインストール
pip install pyscard flask requests

# 3. カードリーダーの接続確認
# （カードリーダーをUSBに接続）

# 4. 設定GUI起動
python client_config_gui.py

# サーバーIP: 192.168.1.31
# ポート: 5000
# 入力後「💾 保存」

# 5. クライアント起動テスト
python client_card_reader.py
```

**カードをかざしてテスト！**

---

## 📊 運用開始後の確認

### 毎日の起動手順

**サーバー側:**
1. `start_server.bat` をダブルクリック
2. ブラウザで動作確認

**クライアント側:**
1. カードリーダーを接続
2. `start_client.bat` をダブルクリック
3. カードをかざしてテスト

### データのバックアップ

定期的に以下のファイルをバックアップ：

```
C:\Users\take_me_hospital\Desktop\N100\attendance.db
```

バックアップ方法:
```cmd
copy attendance.db attendance_backup_%date:~0,4%%date:~5,2%%date:~8,2%.db
```

---

## 🆘 サポート

問題が解決しない場合は、以下の情報を確認してください：

1. **環境情報**
   ```cmd
   python --version
   pip list
   ```

2. **エラーメッセージ**
   - コンソールに表示されたエラーをコピー

3. **ネットワーク情報**
   ```cmd
   ipconfig
   ping 192.168.1.31
   ```

4. **ログ**
   - サーバー側のコンソール出力
   - クライアント側のコンソール出力

---

**これでセットアップ完了です！** 🎉

何か問題があれば、このガイドを参照してください。

