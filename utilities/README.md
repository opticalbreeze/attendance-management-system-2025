# Utilities フォルダ構成

このフォルダには、勤怠システムのメンテナンス、分析、インポート支援用のユーティリティツールが格納されています。

## フォルダ構成

### 📁 database_maintenance/
データベースの修正・メンテナンス用スクリプト

**Python スクリプト:**
- `add_matsuura_master.py` - 松浦氏の社員マスタ追加
- `check_employees.py` - 社員データ確認
- `check_final_result.py` - 最終結果確認
- `check_matsuura_status.py` - 松浦氏データ状況確認
- `fix_matsuura_attendance.py` - 松浦氏勤怠データ修正
- `fix_matsuura_master.py` - 松浦氏マスタデータ修正
- `matsuura_fix_final.py` - 松浦氏最終修正処理
- `update_matsuura.py` - 松浦氏データ更新

**SQL スクリプト:**
- `check_all_matsuura_tables.sql` - 全テーブルの松浦氏データ確認
- `check_work_types.sql` - 勤務種別確認
- `final_check.sql` - 最終確認クエリ
- `fix_all_matsuura_tables.sql` - 全テーブルの松浦氏データ修正
- `fix_matsuura.sql` - 松浦氏データ修正クエリ
- `update_matsuura_simple.sql` - 松浦氏簡易更新クエリ

### 📁 analysis/
データ分析・調査用スクリプト

- `analyze_work_types.py` - 勤務種別分析（システム定義と実際の使用状況）
- `check_import_result.py` - CSVインポート結果確認
- `check_leave_data.py` - 休暇データ確認
- `check_schema.py` - データベーススキーマ確認
- `temp_schedule_report.py` - 一時的なスケジュールレポート

### 📁 import_tools/
CSVインポート支援ツール

- `import_new_schedule.py` - 新しいスケジュールインポート

## 使用方法

### データベースメンテナンス
```bash
# 社員データ確認
python utilities/database_maintenance/check_employees.py

# 勤務種別分析
python utilities/analysis/analyze_work_types.py
```

### 注意事項
- 本番環境での実行前は必ずバックアップを取得してください
- SQLスクリプトは直接実行せず、必要に応じてPythonスクリプト経由で実行してください
- 一時的な検証用ファイルのため、本番運用には適さないものが含まれています

## 履歴
- 2026/01/17: 検証用ファイルを整理し、用途別にフォルダ分けを実施