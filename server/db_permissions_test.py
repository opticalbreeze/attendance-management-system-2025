#!/usr/bin/env python3
"""
データベース編集権限テストスクリプト
"""
import sqlite3
import os
from datetime import datetime
from config import Config

def test_database_permissions():
    """データベースの読み書き権限をテストする"""
    db_path = Config.DATABASE_PATH
    
    try:
        print('=== データベース編集権限テスト ===')
        print(f'データベースパス: {db_path}')
        
        # ファイル権限確認
        import stat
        file_stat = os.stat(db_path)
        print(f'ファイル権限: {stat.filemode(file_stat.st_mode)}')
        print(f'所有者: {file_stat.st_uid}:{file_stat.st_gid}')
        print(f'実行ユーザー: {os.getuid()}:{os.getgid()}')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 読み取りテスト
        print('\n1. 読み取りテスト...')
        cursor.execute('SELECT COUNT(*) FROM employee_master')
        count = cursor.fetchone()[0]
        print(f'   ✅ employee_master件数: {count}')
        
        # 2. 書き込みテスト（テーブル作成）
        print('\n2. 書き込みテスト...')
        cursor.execute('CREATE TABLE IF NOT EXISTS test_edit_permissions (id INTEGER PRIMARY KEY, test_data TEXT, created_at DATETIME)')
        print('   ✅ テストテーブル作成: OK')
        
        # 3. データ挿入テスト
        print('\n3. データ挿入テスト...')
        now = datetime.now()
        cursor.execute('INSERT OR REPLACE INTO test_edit_permissions (id, test_data, created_at) VALUES (?, ?, ?)', 
                      (1, 'test_insert', now))
        print('   ✅ データ挿入: OK')
        
        # 4. データ更新テスト
        print('\n4. データ更新テスト...')
        cursor.execute('UPDATE test_edit_permissions SET test_data = ? WHERE id = ?', 
                      ('test_update', 1))
        affected_rows = cursor.rowcount
        print(f'   ✅ データ更新: OK (更新行数: {affected_rows})')
        
        # 5. コミットテスト
        print('\n5. コミットテスト...')
        conn.commit()
        print('   ✅ コミット: OK')
        
        # 6. 確認テスト
        print('\n6. 更新確認テスト...')
        cursor.execute('SELECT test_data, created_at FROM test_edit_permissions WHERE id = 1')
        result = cursor.fetchone()
        print(f'   ✅ 更新確認: データ="{result[0]}", 作成日時={result[1]}')
        
        # 7. 実際のテーブル編集テスト（employee_master）
        print('\n7. 実テーブル編集テスト...')
        
        # バックアップ用に現在の値を取得
        cursor.execute('SELECT section FROM employee_master WHERE employee_num = 3952012')
        original_section = cursor.fetchone()
        if original_section:
            original_section = original_section[0]
            print(f'   現在の部署: {original_section}')
            
            # テスト用に部署を更新
            test_section = f'テスト部_{datetime.now().strftime("%H%M%S")}'
            cursor.execute('UPDATE employee_master SET section = ?, updated_at = ? WHERE employee_num = ?', 
                          (test_section, datetime.now(), 3952012))
            conn.commit()
            
            # 確認
            cursor.execute('SELECT section FROM employee_master WHERE employee_num = 3952012')
            new_section = cursor.fetchone()[0]
            print(f'   ✅ 実テーブル更新: {original_section} → {new_section}')
            
            # 元に戻す
            cursor.execute('UPDATE employee_master SET section = ?, updated_at = ? WHERE employee_num = ?', 
                          (original_section, datetime.now(), 3952012))
            conn.commit()
            print(f'   ✅ 元の値に復元: {new_section} → {original_section}')
        
        # 8. クリーンアップ
        print('\n8. クリーンアップ...')
        cursor.execute('DROP TABLE test_edit_permissions')
        conn.commit()
        print('   ✅ テストテーブル削除: OK')
        
        conn.close()
        print('\n🎉 すべてのテストが成功しました - データベース編集は正常に動作します')
        return True
        
    except sqlite3.Error as e:
        print(f'\n❌ SQLiteエラーが発生しました: {e}')
        return False
    except PermissionError as e:
        print(f'\n❌ 権限エラーが発生しました: {e}')
        return False
    except Exception as e:
        print(f'\n❌ 予期しないエラーが発生しました: {e}')
        print(f'エラータイプ: {type(e).__name__}')
        return False

def simple_edit_test():
    """簡単な編集テスト"""
    print('\n=== 簡単な編集テスト ===')
    
    try:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # 従業員一覧表示
        print('現在の従業員一覧:')
        cursor.execute('SELECT id, employee_num, name, section FROM employee_master ORDER BY id')
        employees = cursor.fetchall()
        
        for emp in employees:
            section = emp[3] if emp[3] else '未設定'
            print(f'  ID:{emp[0]} 従業員番号:{emp[1]} 名前:{emp[2]} 部署:{section}')
        
        conn.close()
        
    except Exception as e:
        print(f'エラー: {e}')

if __name__ == "__main__":
    # 権限テスト実行
    success = test_database_permissions()
    
    if success:
        simple_edit_test()
    else:
        print('\n権限テストが失敗したため、編集テストをスキップします')