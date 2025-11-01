# 🚀 開発者向けクイックリファレンス

**最終更新**: 2025年11月1日

---

## ⚡ 緊急対応コマンド

### 「変更が反映されない」時の対処
```bash
# Level 1: ブラウザ強制リロード
Ctrl + F5

# Level 2: コンテナ再起動
docker restart attendance-server

# Level 3: イメージ再ビルド  
docker-compose down && docker-compose up -d --build

# Level 4: 完全クリーンアップ
docker-compose down && docker image rm server-attendance-server && docker-compose up -d --build
```

## 🔍 診断コマンド

### ファイル同期確認
```bash
docker exec attendance-server ls -la /app/templates/
docker exec attendance-server grep -n "特定の文字列" /app/templates/check.html
```

### API動作確認
```bash
curl http://192.168.11.24:5000/api/health
curl "http://192.168.11.24:5000/api/attendance_check?employee_id=3652025&check_date=2025-10-09"
```

### ログ確認
```bash
docker logs attendance-server --tail=20
docker logs attendance-server -f  # リアルタイム
```

## 🐛 よくあるエラーと対処

| エラー | 原因 | 対処法 |
|---|---|---|
| 画面が更新されない | ブラウザキャッシュ | `Ctrl + F5` |
| APIが500エラー | Python構文エラー | `docker logs attendance-server` |
| JSが動作しない | JavaScript構文エラー | `F12 → Console` |
| データが表示されない | データアクセス方法の問題 | `console.log`でデバッグ |

## 📁 重要ファイル

| ファイル | 役割 | 変更時の対応 |
|---|---|---|
| `templates/check.html` | フロントエンド | ブラウザリロード |
| `api.py` | APIエンドポイント | コンテナ再起動 |
| `requirements_server.txt` | 依存関係 | `--build` で再ビルド |
| `docker-compose.yml` | Docker設定 | 完全再ビルド |

## 🔧 開発ワークフロー

### 1. Python変更時
```
編集 → 保存 → docker restart attendance-server → curl でテスト
```

### 2. HTML/JS変更時  
```
編集 → 保存 → Ctrl+F5 → F12でエラー確認
```

### 3. 重要な変更時
```
バックアップ → 編集 → テスト → コミット
```

## 📞 サポートファイル

- **詳細ガイド**: `DOCKER_DEVELOPMENT_COMPLETE_GUIDE.md`
- **トラブル履歴**: `TROUBLESHOOTING_HISTORY.md`
- **システム概要**: `SYSTEM_OVERVIEW.md`

---
💡 **覚えておくべき鉄則**: Docker環境では「ファイル変更 ≠ 即座に反映」を常に意識する！