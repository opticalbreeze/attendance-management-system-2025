# 🚨 データベース緊急復旧ガイド

## 📊 **現在のデータ状況**
- **本番DB**: `C:\Users\take_me_hospital\attendance\data\attendance.db` (425KB)
- **バックアップ**: `C:\Users\take_me_hospital\attendance\buck_up_data\` (4つのファイル)

## 🔄 **即座のバックアップ作成**

### PowerShellでの手動バックアップ
```powershell
# 現在の日時でバックアップ作成
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item "C:\Users\take_me_hospital\attendance\data\attendance.db" "C:\Users\take_me_hospital\attendance\buck_up_data\attendance_$timestamp.db"
Write-Host "✅ バックアップ作成完了: attendance_$timestamp.db"
```

### Dockerコンテナ経由でのバックアップ
```bash
# コンテナ内からのバックアップ作成
cd "c:\Users\take_me_hospital\attendance\work_attend_server\server"
docker-compose exec attendance-server cp /app/data/attendance.db /app/data/attendance_backup_$(date +%Y%m%d_%H%M%S).db
```

## 🔧 **復旧手順**

### 1. 最新バックアップからの復旧
```powershell
# サービス停止
cd "c:\Users\take_me_hospital\attendance\work_attend_server\server"
docker-compose down

# 最新バックアップからの復旧 (例: 11/21のバックアップ)
Copy-Item "C:\Users\take_me_hospital\attendance\buck_up_data\attendance20251121クライアントスリープ対策前.db" "C:\Users\take_me_hospital\attendance\data\attendance.db" -Force

# サービス再開
docker-compose up -d
```

### 2. 特定日時からの復旧
```powershell
# 利用可能なバックアップ一覧表示
Get-ChildItem "C:\Users\take_me_hospital\attendance\buck_up_data\" | Select-Object Name, LastWriteTime, Length

# 選択したバックアップから復旧
# Copy-Item "パス\選択したファイル" "C:\Users\take_me_hospital\attendance\data\attendance.db" -Force
```

## 📋 **データベース初期化の安全実行**

### 安全な初期化手順 (データ保護付き)
```powershell
# Step 1: 事前バックアップ作成
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item "C:\Users\take_me_hospital\attendance\data\attendance.db" "C:\Users\take_me_hospital\attendance\buck_up_data\before_init_$timestamp.db"

# Step 2: Docker停止
cd "c:\Users\take_me_hospital\attendance\work_attend_server\server"
docker-compose down

# Step 3: 初期化実行
docker-compose up -d
docker-compose exec attendance-server python -c "from database import init_database; init_database(); print('初期化完了')"

# Step 4: 結果確認
docker-compose logs attendance-server --tail=10
```

## ⚠️ **重要な注意事項**

### データが消失するケース
1. **`init_database()`を空のDBで実行** - テーブル作成のみ（既存データ保持）
2. **DBファイル自体を削除** - 物理的削除（バックアップから復旧必要）
3. **DROP TABLEやDELETE文実行** - データ削除（バックアップから復旧必要）

### データが保持されるケース
1. **Dockerコンテナの停止・再起動** - データ保持
2. **Docker imageの再ビルド** - データ保持（バインドマウントのため）
3. **サーバープログラムの更新** - データ保持

## 🔄 **自動バックアップの設定**

### 毎日のバックアップスクリプト
```powershell
# backup_script.ps1 として保存
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$sourcePath = "C:\Users\take_me_hospital\attendance\data\attendance.db"
$backupPath = "C:\Users\take_me_hospital\attendance\buck_up_data\daily_backup_$timestamp.db"

if (Test-Path $sourcePath) {
    Copy-Item $sourcePath $backupPath
    Write-Host "✅ 毎日バックアップ完了: daily_backup_$timestamp.db"
    
    # 古いバックアップの削除（7日以上古い）
    Get-ChildItem "C:\Users\take_me_hospital\attendance\buck_up_data\daily_backup_*.db" | 
    Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-7) } | 
    Remove-Item -Force
} else {
    Write-Host "❌ データベースファイルが見つかりません"
}
```

## 📞 **緊急時の連絡先情報**
- **現在の作業ディレクトリ**: `c:\Users\take_me_hospital\attendance\work_attend_server`
- **データディレクトリ**: `c:\Users\take_me_hospital\attendance\data\`
- **バックアップディレクトリ**: `c:\Users\take_me_hospital\attendance\buck_up_data\`
- **Docker設定**: `server\docker-compose.yml`

---

**💡 重要**: このガイドを印刷またはブックマークして、緊急時に備えてください。