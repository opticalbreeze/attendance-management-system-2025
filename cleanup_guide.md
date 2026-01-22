# 検証用ファイル整理リスト

## ✅ 整理完了項目

### 移動したフォルダ
- `utilities/` - 再利用可能なユーティリティツール
- `archive/` - アーカイブファイル

## ❗ 手動整理が必要なファイル

以下のファイルはserverフォルダに残っている一時的な検証用ファイルです：

### データベース修正関連ファイル（削除推奨）
- `add_matsuura_master.py` - 松浦氏社員マスタ追加スクリプト（完了済み）
- `check_employees.py` - 社員データ確認スクリプト
- `check_final_result.py` - 最終結果確認スクリプト
- `check_matsuura_status.py` - 松浦氏データ状況確認
- `fix_matsuura_attendance.py` - 松浦氏勤怠データ修正（完了済み）
- `fix_matsuura_master.py` - 松浦氏マスタデータ修正（完了済み）
- `matsuura_fix_final.py` - 松浦氏最終修正処理（完了済み）
- `update_matsuura.py` - 松浦氏データ更新（完了済み）

### SQLファイル（削除推奨）
- `check_all_matsuura_tables.sql` - 全テーブル松浦氏データ確認
- `check_work_types.sql` - 勤務種別確認
- `final_check.sql` - 最終確認クエリ
- `fix_all_matsuura_tables.sql` - 全テーブル松浦氏データ修正
- `fix_matsuura.sql` - 松浦氏データ修正
- `update_matsuura_simple.sql` - 松浦氏簡易更新

### 分析関連ファイル（移動推奨）
- `analyze_work_types.py` - 勤務種別分析（有用）
- `check_import_result.py` - CSVインポート結果確認
- `check_leave_data.py` - 休暇データ確認
- `check_schema.py` - データベーススキーマ確認

### バックアップファイル（アーカイブ推奨）
- `backup_20260114_133532.db` - 2026/01/14のバックアップ
- `backup_20260114_133931.db` - 2026/01/14のバックアップ

## 🔧 手動整理コマンド

### 1. 完了済み修正ファイルの削除
```powershell
cd "c:\Users\take_me_hospital\attendance\work_attend_server\server"
Remove-Item add_matsuura_master.py, fix_matsuura_attendance.py, fix_matsuura_master.py, matsuura_fix_final.py, update_matsuura.py -Force
Remove-Item fix_all_matsuura_tables.sql, fix_matsuura.sql, update_matsuura_simple.sql -Force
```

### 2. 有用なファイルの保管
```powershell
# 分析ファイルをutilities/analysisに移動
Move-Item analyze_work_types.py, check_import_result.py, check_leave_data.py, check_schema.py ..\utilities\analysis\
Move-Item check_work_types.sql ..\utilities\analysis\

# 確認用ファイルをutilities/database_maintenanceに移動
Move-Item check_employees.py, check_final_result.py, check_matsuura_status.py ..\utilities\database_maintenance\
Move-Item check_all_matsuura_tables.sql, final_check.sql ..\utilities\database_maintenance\

# バックアップをアーカイブに移動
Move-Item backup_20260114_133532.db, backup_20260114_133931.db ..\archive\old_backups\
```

## 📋 削除前確認事項
- 松浦氏の社員番号変更作業は完了済み
- データベースの一貫性は確認済み
- 勤務種別「欠」の追加は完了済み

これらのファイルは目的を果たしているため、安全に削除できます。