# ハードウェアブザー付きカードリーダー対応ガイド

## 📋 概要

このガイドでは、エレコム MR-ICA001BKのようなハードウェアブザー/LED付きカードリーダーを使用する際の設定方法を説明します。

## 🔊 問題点

### ハードウェアブザー付きリーダーの特徴

**エレコム MR-ICA001BK** などのリーダーには以下の特徴があります：

- ✅ LEDランプ内蔵
- ✅ ブザー内蔵
- ✅ カードをかざすと**自動的に**音が鳴る（ハードウェア制御）

### 発生する問題

```
ユーザーがカードをかざす
    ↓
【1】ハードウェアのブザーが鳴る（即座に）
    ↓
【2】コード側の読み取り音が鳴る（ほぼ同時）
    ↓
音が重複して混乱！
```

**混乱のポイント：**
- ハードウェアの音 = カード検出時（読み込み前）
- コードの音 = カード読み込み完了時
- ユーザーは「読み込みが完了したのか、まだなのか」が分かりにくい

## ✅ 解決策

### 方法1: カード読み取り音を無効化（推奨）

**`client_config.json`** に以下の設定を追加：

```json
{
  "server_url": "http://192.168.1.31:5000",
  "beep_settings": {
    "enabled": true,
    "card_read": false,
    "success": true,
    "fail": true
  }
}
```

#### 音の設定詳細

| 設定項目 | 説明 | 推奨値（ハードウェアブザー有り） | 推奨値（通常） |
|---------|------|--------------------------------|--------------|
| `enabled` | 全体の音の有効/無効 | `true` | `true` |
| `card_read` | カード読み取り音 | `false` ⭐ | `true` |
| `success` | 送信成功音 | `true` | `true` |
| `fail` | 送信失敗音 | `true` | `true` |

⭐ **重要**: ハードウェアブザー付きリーダーでは `"card_read": false` に設定

### 音のタイミング

```
【ハードウェアブザー有り + 推奨設定】
カードをかざす
  ↓
ピッ（ハードウェア）← カード検出
  ↓
[処理中...]
  ↓
ピピピッ（コード・成功音）← サーバー送信成功
または
ブーブー（コード・失敗音）← サーバー送信失敗
```

これにより：
- ✅ 1回目の音 = カード検出（ハードウェア）
- ✅ 2回目の音 = 処理結果（コード）
- ✅ 明確に区別できる！

## 🎵 音のパターン

### デフォルトの音パターン

| 音の種類 | パターン | タイミング | 設定可能 |
|---------|---------|----------|---------|
| カード読み取り | ピッ（短い高音） | カード検出時 | ✅ |
| 送信成功 | ピピピッ（3回の高音） | サーバー送信成功 | ✅ |
| 送信失敗 | ブーブー（低音） | サーバー送信失敗 | ✅ |
| サーバー接続 | ピピピ（3回） | 起動時/再接続時 | ⚠️ 無効化不可 |
| 起動音 | ピッピッ | プログラム起動時 | ⚠️ 無効化不可 |

## 🔧 設定方法

### ステップ1: 設定ファイルの作成/編集

`client_config.json` を開いて編集：

```json
{
  "server_url": "http://192.168.1.31:5000",
  "beep_settings": {
    "enabled": true,
    "card_read": false,
    "success": true,
    "fail": true
  }
}
```

### ステップ2: プログラムの再起動

```bash
python client_card_reader_windows_gui_improved.py
```

### ステップ3: 動作確認

1. カードをかざす
2. ハードウェアの音が1回だけ鳴る
3. サーバー送信後に成功/失敗の音が鳴る

## 📝 設定例

### 例1: エレコム MR-ICA001BK（ハードウェアブザー有り）

```json
{
  "server_url": "http://192.168.1.31:5000",
  "beep_settings": {
    "enabled": true,
    "card_read": false,  ← 無効化
    "success": true,
    "fail": true
  }
}
```

### 例2: 通常のリーダー（ハードウェアブザー無し）

```json
{
  "server_url": "http://192.168.1.31:5000",
  "beep_settings": {
    "enabled": true,
    "card_read": true,   ← 有効化
    "success": true,
    "fail": true
  }
}
```

### 例3: 全ての音を無効化

```json
{
  "server_url": "http://192.168.1.31:5000",
  "beep_settings": {
    "enabled": false,    ← 全体を無効化
    "card_read": false,
    "success": false,
    "fail": false
  }
}
```

### 例4: 失敗音のみ有効

```json
{
  "server_url": "http://192.168.1.31:5000",
  "beep_settings": {
    "enabled": true,
    "card_read": false,
    "success": false,
    "fail": true         ← 失敗時だけ音を鳴らす
  }
}
```

## ⚙️ 対応ファイル

以下のファイルで音の設定に対応：

- ✅ `client_card_reader_windows_gui_improved.py`

他のファイル（`client_card_reader_windows_gui.py`など）は今後対応予定です。

## 🎯 ハードウェアブザー付きリーダーの推奨設定

### エレコム MR-ICA001BK

```json
{
  "server_url": "http://YOUR_SERVER:5000",
  "beep_settings": {
    "enabled": true,
    "card_read": false,     ← 重複を避けるため無効化
    "success": true,        ← 成功を明確に通知
    "fail": true            ← 失敗を明確に通知
  }
}
```

### その他のハードウェアブザー付きリーダー

同様の設定を推奨します：
- Sony PaSoRi RC-S380（一部モデルでブザー有り）
- その他のブザー内蔵リーダー

## ❓ FAQ

### Q1: ハードウェアのブザーを無効化できますか？

**A:** エレコム MR-ICA001BKの場合、ハードウェアのブザーをソフトウェアから無効化する方法は公式には提供されていません。このため、コード側の音を調整することで対応します。

### Q2: 音が全く鳴りません

**A:** 以下を確認してください：

1. `winsound` が利用可能か（起動時のログに表示）
2. PCスピーカーが正常に動作しているか
3. 設定で `"enabled": false` になっていないか

### Q3: カード読み取り音だけを有効にしたい

**A:** 設定を以下のように変更：

```json
{
  "beep_settings": {
    "enabled": true,
    "card_read": true,
    "success": false,
    "fail": false
  }
}
```

### Q4: 音の周波数や長さを変更できますか？

**A:** コード内の `SOUNDS` 辞書を編集することで可能です：

```python
# client_card_reader_windows_gui_improved.py の 63-69行目付近
SOUNDS = {
    "read": [(2000, 50)],      # (周波数Hz, 時間ms)
    "success": [(2500, 100), (2700, 50), (2500, 100)],
    "fail": [(800, 300), (600, 100), (800, 300)]
}
```

## 🔍 トラブルシューティング

### 問題: 音が重複して鳴る

**原因:** `"card_read": true` になっている  
**解決策:** `"card_read": false` に変更

### 問題: 成功/失敗の音が鳴らない

**原因:** `"enabled": false` または個別設定が `false`  
**解決策:** 設定を `true` に変更

### 問題: 設定ファイルを変更しても反映されない

**原因:** プログラムを再起動していない  
**解決策:** プログラムを完全に終了して再起動

## 📚 関連ドキュメント

- [IMPROVEMENTS.md](IMPROVEMENTS.md) - 全体的な改善内容
- [NFCPY_SPEED_OPTIMIZATION.md](NFCPY_SPEED_OPTIMIZATION.md) - 速度最適化
- [README.md](README.md) - プロジェクト全体のドキュメント

## 💡 まとめ

エレコム MR-ICA001BKなどのハードウェアブザー付きリーダーを使用する場合：

1. ✅ `client_config.json` に音の設定を追加
2. ✅ `"card_read": false` に設定（重複を避ける）
3. ✅ `"success": true` と `"fail": true` を維持（結果を通知）
4. ✅ プログラムを再起動

これにより、ユーザーは混乱することなく、カード読み取りとサーバー送信の結果を明確に把握できます！

---

**作成日:** 2025年10月20日  
**対象リーダー:** エレコム MR-ICA001BK 他ハードウェアブザー付きリーダー  
**対応バージョン:** client_card_reader_windows_gui_improved.py v1.x

