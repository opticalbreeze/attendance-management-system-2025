#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""テンプレートファイルの差異を比較するスクリプト"""

import os
import hashlib
from pathlib import Path

def get_file_hash(filepath):
    """ファイルのMD5ハッシュを取得"""
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def compare_templates():
    """templates/とtemplates_dev/のファイルを比較"""
    base_dir = Path(__file__).parent
    templates_dir = base_dir / 'templates'
    templates_dev_dir = base_dir / 'templates_dev'
    
    # HTMLファイルのリスト
    html_files = [
        'admin.html',
        'attendance_check.html',
        'check.html',
        'check.html.backup',
        'index.html',
        'leave_check.html',
        'leave_list.html',
        'leave.html',
        'login.html',
        'monthly_report.html',
        'overtime_check.html',
        'overtime_list.html',
        'overtime.html',
        'search.html'
    ]
    
    different_files = []
    same_files = []
    missing_files = []
    
    print("=" * 60)
    print("テンプレートファイル比較結果")
    print("=" * 60)
    
    for filename in html_files:
        prod_path = templates_dir / filename
        dev_path = templates_dev_dir / filename
        
        prod_exists = prod_path.exists()
        dev_exists = dev_path.exists()
        
        if not prod_exists and not dev_exists:
            print(f"{filename}: 両方に存在しない")
            missing_files.append(filename)
        elif not prod_exists:
            print(f"{filename}: templates/に存在しない")
            missing_files.append(filename)
        elif not dev_exists:
            print(f"{filename}: templates_dev/に存在しない")
            missing_files.append(filename)
        else:
            prod_hash = get_file_hash(prod_path)
            dev_hash = get_file_hash(dev_path)
            
            if prod_hash == dev_hash:
                print(f"{filename}: SAME")
                same_files.append(filename)
            else:
                print(f"{filename}: DIFFERENT")
                print(f"  templates/{filename}:     {prod_hash}")
                print(f"  templates_dev/{filename}: {dev_hash}")
                different_files.append(filename)
    
    print("=" * 60)
    print(f"\n同じファイル: {len(same_files)}件")
    print(f"異なるファイル: {len(different_files)}件")
    print(f"存在しないファイル: {len(missing_files)}件")
    
    if different_files:
        print("\n【差異があるファイル】")
        for f in different_files:
            print(f"  - {f}")
    
    return different_files, same_files, missing_files

if __name__ == '__main__':
    compare_templates()
