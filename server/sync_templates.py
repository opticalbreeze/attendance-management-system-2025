#!/usr/bin/env python3
"""
テンプレートファイル同期スクリプト

5001（開発環境）の templates_dev/ と static_dev/ の変更を
5000（本番環境）の templates/ と static/ に同期します。

使用方法:
    python sync_templates.py [--dry-run] [--force]

オプション:
    --dry-run: 実際にはコピーせず、変更内容を表示するだけ
    --force: 確認なしで強制的に同期する
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# スクリプトのディレクトリを取得
SCRIPT_DIR = Path(__file__).parent.resolve()
BASE_DIR = SCRIPT_DIR.parent

# ディレクトリのパス
TEMPLATES_DEV_DIR = BASE_DIR / 'server' / 'templates_dev'
TEMPLATES_DIR = BASE_DIR / 'server' / 'templates'
STATIC_DEV_DIR = BASE_DIR / 'server' / 'static_dev'
STATIC_DIR = BASE_DIR / 'server' / 'static'

# 同期対象ファイルのパターン（除外するファイル）
EXCLUDE_PATTERNS = [
    '.git',
    '__pycache__',
    '.pyc',
    '.pyo',
    '.DS_Store',
    'Thumbs.db',
]


def should_exclude(file_path: Path) -> bool:
    """ファイルが除外対象かどうかを判定"""
    path_str = str(file_path)
    return any(pattern in path_str for pattern in EXCLUDE_PATTERNS)


def get_file_hash(file_path: Path) -> str:
    """ファイルのハッシュ値を取得（簡易版）"""
    try:
        stat = file_path.stat()
        return f"{stat.st_mtime}_{stat.st_size}"
    except Exception:
        return ""


def sync_directory(source_dir: Path, target_dir: Path, dry_run: bool = False) -> tuple[int, int]:
    """
    ディレクトリを同期
    
    Returns:
        (更新されたファイル数, エラー数)
    """
    updated_count = 0
    error_count = 0
    
    if not source_dir.exists():
        print(f"⚠️  ソースディレクトリが存在しません: {source_dir}")
        return updated_count, error_count
    
    # ターゲットディレクトリが存在しない場合は作成
    if not target_dir.exists():
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 ディレクトリを作成: {target_dir}")
        else:
            print(f"📁 [DRY-RUN] ディレクトリを作成: {target_dir}")
    
    # ソースディレクトリ内のすべてのファイルを走査
    for root, dirs, files in os.walk(source_dir):
        # 除外パターンに一致するディレクトリをスキップ
        dirs[:] = [d for d in dirs if not should_exclude(Path(root) / d)]
        
        for file in files:
            source_file = Path(root) / file
            
            # 除外パターンに一致するファイルをスキップ
            if should_exclude(source_file):
                continue
            
            # ターゲットファイルのパスを計算
            relative_path = source_file.relative_to(source_dir)
            target_file = target_dir / relative_path
            
            # ターゲットディレクトリが存在しない場合は作成
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            # ファイルが存在しない、または内容が異なる場合はコピー
            should_copy = False
            if not target_file.exists():
                should_copy = True
                reason = "新規ファイル"
            else:
                source_hash = get_file_hash(source_file)
                target_hash = get_file_hash(target_file)
                if source_hash != target_hash:
                    should_copy = True
                    reason = "内容が異なる"
            
            if should_copy:
                updated_count += 1
                if dry_run:
                    print(f"📋 [DRY-RUN] {relative_path} ({reason})")
                else:
                    try:
                        shutil.copy2(source_file, target_file)
                        print(f"✅ {relative_path} ({reason})")
                    except Exception as e:
                        error_count += 1
                        print(f"❌ エラー: {relative_path} - {e}")
    
    return updated_count, error_count


def main():
    parser = argparse.ArgumentParser(
        description='5001（開発環境）のテンプレートと静的ファイルを5000（本番環境）に同期します'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='実際にはコピーせず、変更内容を表示するだけ'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='確認なしで強制的に同期する'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("テンプレートファイル同期スクリプト")
    print("=" * 60)
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if args.dry_run:
        print("🔍 DRY-RUN モード: 実際にはコピーしません")
        print()
    
    # 確認プロンプト
    if not args.dry_run and not args.force:
        print("⚠️  警告: 本番環境（5000）のファイルを上書きします")
        response = input("続行しますか？ (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ キャンセルされました")
            return
    
    print()
    print("📂 同期開始...")
    print()
    
    # テンプレートファイルの同期
    print("📄 テンプレートファイルの同期")
    print("-" * 60)
    templates_updated, templates_errors = sync_directory(
        TEMPLATES_DEV_DIR,
        TEMPLATES_DIR,
        dry_run=args.dry_run
    )
    print()
    
    # 静的ファイルの同期
    print("🎨 静的ファイルの同期")
    print("-" * 60)
    static_updated, static_errors = sync_directory(
        STATIC_DEV_DIR,
        STATIC_DIR,
        dry_run=args.dry_run
    )
    print()
    
    # 結果サマリー
    print("=" * 60)
    print("📊 同期結果サマリー")
    print("=" * 60)
    print(f"テンプレートファイル: {templates_updated}件更新, {templates_errors}件エラー")
    print(f"静的ファイル: {static_updated}件更新, {static_errors}件エラー")
    print(f"合計: {templates_updated + static_updated}件更新, {templates_errors + static_errors}件エラー")
    print()
    
    if args.dry_run:
        print("💡 実際に同期するには、--dry-run オプションを外して実行してください")
    elif templates_updated + static_updated > 0:
        print("✅ 同期が完了しました")
        print("💡 Dockerコンテナを再起動して変更を反映してください:")
        print("   docker compose restart attendance-server")
    else:
        print("ℹ️  同期が必要なファイルはありませんでした")


if __name__ == '__main__':
    main()
