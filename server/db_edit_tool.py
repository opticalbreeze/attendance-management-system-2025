#!/usr/bin/env python3
"""
データベース編集ツール - 実用版
"""
import sqlite3
import sys
from datetime import datetime

class DatabaseEditor:
    def __init__(self):
        self.db_path = '/app/data/attendance.db'
        
    def connect(self):
        """データベースに接続"""
        return sqlite3.connect(self.db_path)
    
    def show_employees(self):
        """従業員一覧表示"""
        conn = self.connect()
        cursor = conn.cursor()
        
        print("=== 従業員一覧 ===")
        cursor.execute('''
            SELECT id, employee_num, name, idm, section, created_at, updated_at 
            FROM employee_master ORDER BY id
        ''')
        
        employees = cursor.fetchall()
        print(f"{'ID':<3} {'従業員番号':<10} {'名前':<15} {'IDM':<17} {'部署':<10} {'作成日':<19}")
        print("-" * 80)
        
        for emp in employees:
            emp_num = str(emp[1]) if emp[1] else "未設定"
            section = emp[4] if emp[4] else "未設定"
            created = emp[5][:10] if emp[5] else "未設定"
            print(f"{emp[0]:<3} {emp_num:<10} {emp[2]:<15} {emp[3]:<17} {section:<10} {created:<19}")
        
        conn.close()
        return employees
    
    def update_employee(self, employee_id, field, new_value):
        """従業員情報を更新"""
        valid_fields = ['employee_num', 'name', 'idm', 'section']
        if field not in valid_fields:
            print(f"エラー: 無効なフィールド '{field}'. 有効なフィールド: {', '.join(valid_fields)}")
            return False
            
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 現在の値を取得
            cursor.execute(f'SELECT {field} FROM employee_master WHERE id = ?', (employee_id,))
            old_value = cursor.fetchone()
            if not old_value:
                print(f"エラー: ID {employee_id} の従業員が見つかりません")
                return False
            old_value = old_value[0]
            
            # 更新実行
            update_sql = f'UPDATE employee_master SET {field} = ?, updated_at = ? WHERE id = ?'
            cursor.execute(update_sql, (new_value, datetime.now(), employee_id))
            
            if cursor.rowcount > 0:
                conn.commit()
                print(f"✅ 更新完了: ID {employee_id} の {field} を '{old_value}' → '{new_value}' に変更")
                return True
            else:
                print(f"❌ 更新失敗: 該当するレコードがありません")
                return False
                
        except Exception as e:
            conn.rollback()
            print(f"❌ エラーが発生しました: {e}")
            return False
        finally:
            conn.close()
    
    def add_employee(self, employee_num, name, idm, section="未設定"):
        """新規従業員を追加"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 重複チェック
            cursor.execute('SELECT id FROM employee_master WHERE employee_num = ? OR idm = ?', 
                          (employee_num, idm))
            existing = cursor.fetchone()
            if existing:
                print(f"❌ エラー: 従業員番号 {employee_num} またはIDM {idm} は既に存在します")
                return False
            
            # 追加実行
            cursor.execute('''
                INSERT INTO employee_master (employee_num, name, idm, section, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (employee_num, name, idm, section, datetime.now(), datetime.now()))
            
            conn.commit()
            new_id = cursor.lastrowid
            print(f"✅ 新規従業員追加完了: ID {new_id}, 従業員番号 {employee_num}, 名前 {name}")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ エラーが発生しました: {e}")
            return False
        finally:
            conn.close()
    
    def delete_employee(self, employee_id):
        """従業員を削除"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 削除前に情報を表示
            cursor.execute('SELECT employee_num, name FROM employee_master WHERE id = ?', (employee_id,))
            employee = cursor.fetchone()
            if not employee:
                print(f"❌ エラー: ID {employee_id} の従業員が見つかりません")
                return False
            
            # 確認
            print(f"⚠️  従業員 ID {employee_id} ({employee[1]}, 従業員番号: {employee[0]}) を削除しますか？")
            print("この操作は元に戻せません。'yes' と入力して確認してください。")
            
            # 削除実行（この例では実際には削除せず、警告のみ表示）
            print("🛡️  安全のため、この例では実際の削除は行いません")
            print("削除が必要な場合は、管理者に相談してください")
            return False
            
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
            return False
        finally:
            conn.close()

def main():
    """メイン関数"""
    editor = DatabaseEditor()
    
    if len(sys.argv) == 1:
        # 対話モード
        print("=== データベース編集ツール ===")
        print("コマンド:")
        print("  show                     - 従業員一覧表示")
        print("  update <ID> <field> <value> - 従業員情報更新")
        print("  add <employee_num> <name> <idm> [section] - 新規従業員追加")
        print("  help                     - ヘルプ表示")
        print("  quit                     - 終了")
        print()
        print("例:")
        print("  update 4 section 総務部")
        print("  add 9999999 新規従業員 0116020034199999 営業部")
        print()
        
        while True:
            try:
                command = input("db_edit> ").strip().split()
                if not command:
                    continue
                    
                if command[0] == "quit":
                    break
                elif command[0] == "show":
                    editor.show_employees()
                elif command[0] == "update" and len(command) >= 4:
                    employee_id = int(command[1])
                    field = command[2]
                    value = " ".join(command[3:])  # スペースを含む値に対応
                    editor.update_employee(employee_id, field, value)
                elif command[0] == "add" and len(command) >= 4:
                    employee_num = int(command[1])
                    name = command[2]
                    idm = command[3]
                    section = command[4] if len(command) > 4 else "未設定"
                    editor.add_employee(employee_num, name, idm, section)
                elif command[0] == "help":
                    print("使用可能なコマンドの説明...")
                else:
                    print("不明なコマンドです。'help' でヘルプを表示")
                    
            except KeyboardInterrupt:
                break
            except ValueError as e:
                print(f"入力エラー: {e}")
            except Exception as e:
                print(f"エラー: {e}")
        
        print("終了しました")
        
    else:
        # コマンドライン引数モード
        if sys.argv[1] == "show":
            editor.show_employees()
        elif sys.argv[1] == "update" and len(sys.argv) >= 5:
            employee_id = int(sys.argv[2])
            field = sys.argv[3]
            value = " ".join(sys.argv[4:])
            editor.update_employee(employee_id, field, value)
        else:
            print("使用方法: python db_edit_tool.py [show|update <ID> <field> <value>]")

if __name__ == "__main__":
    main()