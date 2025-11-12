#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ユーティリティモジュール  
共通で使用される便利な関数を提供
"""

import sqlite3
from datetime import datetime, date, timedelta

from config import Config

def get_database_connection():
    """データベース接続を取得（共通関数）"""
    return sqlite3.connect(Config.DATABASE_PATH)

def check_duplicate_attendance(idm, timestamp, terminal_id, threshold_seconds=None):
    """
    チャタリング防止: 重複打刻をチェック
    同じIDm、端末で指定秒数以内の打刻は重複と判定
    """
    if threshold_seconds is None:
        threshold_seconds = Config.CHATTERING_THRESHOLD_SECONDS
    
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # 同じIDm、端末での最新の打刻を取得
        cursor.execute("""
            SELECT timestamp, received_at 
            FROM attendance 
            WHERE idm = ? AND terminal_id = ?
            ORDER BY received_at DESC 
            LIMIT 1
        """, (idm, terminal_id))
        
        last_record = cursor.fetchone()
        conn.close()
        
        if not last_record:
            return {'is_duplicate': False, 'time_diff': None}
        
        # 時刻差を計算
        try:
            last_timestamp = datetime.fromisoformat(last_record[0].replace('Z', '+00:00'))
            current_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_diff = abs((current_timestamp - last_timestamp).total_seconds())
            
            is_duplicate = time_diff <= threshold_seconds
            
            return {
                'is_duplicate': is_duplicate,
                'time_diff': time_diff,
                'last_record': {
                    'timestamp': last_record[0],
                    'received_at': last_record[1]
                }
            }
            
        except ValueError as e:
            print(f"[警告] 時刻解析エラー: {e}")
            return {'is_duplicate': False, 'time_diff': None}
            
    except sqlite3.Error as e:
        print(f"[エラー] 重複チェック失敗: {e}")
        return {'is_duplicate': False, 'time_diff': None}

def calculate_date_range(search_month):
    """
    検索月から検索範囲を計算（前月16日から当月15日）
    給与計算期間に基づく期間設定
    
    Args:
        search_month (str): 検索月 (yyyy/mm形式)
        
    Returns:
        tuple: (start_date, end_date)
    """
    try:
        year, month = search_month.split('/')
        year = int(year)
        month = int(month)
        
        if month < 1 or month > 12:
            raise ValueError("月は1-12の範囲で指定してください")
        
        # 前月の計算
        if month == 1:
            prev_year = year - 1
            prev_month = 12
        else:
            prev_year = year
            prev_month = month - 1
        
        # 検索範囲の開始日：前月16日（設定から取得）
        start_date = date(prev_year, prev_month, Config.PAYROLL_START_DAY).strftime('%Y-%m-%d')
        
        # 検索範囲の終了日：当月15日（設定から取得）
        end_date = date(year, month, Config.PAYROLL_END_DAY).strftime('%Y-%m-%d')
        
        return start_date, end_date
        
    except ValueError as e:
        raise ValueError(f"検索月の形式が正しくありません: {str(e)}")

def validate_employee_id(employee_id):
    """従業員IDのバリデーション"""
    if not employee_id or not employee_id.strip():
        return False, "従業員IDが指定されていません"
    
    employee_id = employee_id.strip()
    
    if len(employee_id) < Config.EMPLOYEE_ID_MIN_LENGTH:
        return False, f"従業員IDは{Config.EMPLOYEE_ID_MIN_LENGTH}文字以上で入力してください"
    
    if len(employee_id) > Config.EMPLOYEE_ID_MAX_LENGTH:
        return False, f"従業員IDは{Config.EMPLOYEE_ID_MAX_LENGTH}文字以下で入力してください"
    
    return True, employee_id

def validate_search_month(search_month):
    """検索月のバリデーション"""
    if not search_month or not search_month.strip():
        return False, "検索月が指定されていません（yyyy/mm形式で入力してください）"
    
    search_month = search_month.strip()
    
    # 形式チェック
    if '/' not in search_month:
        return False, "検索月はyyyy/mm形式で入力してください"
    
    try:
        year, month = search_month.split('/')
        year = int(year)
        month = int(month)
        
        if year < Config.YEAR_MIN or year > Config.YEAR_MAX:
            return False, f"年は{Config.YEAR_MIN}-{Config.YEAR_MAX}の範囲で入力してください"
            
        if month < 1 or month > 12:
            return False, "月は1-12の範囲で入力してください"
            
        return True, search_month
        
    except ValueError:
        return False, "検索月はyyyy/mm形式で入力してください（例: 2025/10）"

def format_response(status, data=None, message=None, **kwargs):
    """統一されたレスポンス形式を生成"""
    response = {'status': status}
    
    if message:
        response['message'] = message
    
    if data is not None:
        if isinstance(data, dict):
            response.update(data)
        else:
            response['data'] = data
    
    # 追加パラメータ
    response.update(kwargs)
    
    return response

def safe_int(value, default=0):
    """
    安全に整数に変換
    
    Args:
        value: 変換する値
        default: 変換失敗時のデフォルト値
    
    Returns:
        int or default: 変換結果
    """
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default

def calculate_time_diff_minutes(time1_str, time2_str):
    """
    2つの時刻（HH:MM形式）の差異を分単位で計算
    
    Args:
        time1_str: 時刻1 (HH:MM形式)
        time2_str: 時刻2 (HH:MM形式)
    
    Returns:
        差異（分）、time1が早い場合は負の値、time2が早い場合は正の値
    """
    try:
        if not time1_str or not time2_str:
            return None
        
        # HH:MM形式を分に変換
        def time_to_minutes(time_str):
            parts = time_str.split(':')
            if len(parts) >= 2:
                return int(parts[0]) * 60 + int(parts[1])
            return None
        
        minutes1 = time_to_minutes(time1_str)
        minutes2 = time_to_minutes(time2_str)
        
        if minutes1 is None or minutes2 is None:
            return None
        
        return minutes2 - minutes1
        
    except:
        return None

def update_request_status(table_name, request_id, status, updated_by=None):
    """
    申請のステータスを更新（汎用関数）
    
    Args:
        table_name: テーブル名 ('overtime_applications' or 'leave_requests')
        request_id: 申請ID
        status: 新しいステータス ('approved', 'rejected', 'withdrawn')
        updated_by: 更新者（承認/却下の場合に使用、オプション）
    
    Returns:
        dict: {'success': bool, 'message': str}
    """
    from datetime import datetime
    
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # テーブル名のバリデーション
        valid_tables = ['overtime_applications', 'leave_requests']
        if table_name not in valid_tables:
            conn.close()
            return {
                'success': False,
                'message': f'無効なテーブル名: {table_name}'
            }
        
        # ステータスのバリデーション
        valid_statuses = ['approved', 'rejected', 'withdrawn']
        if status not in valid_statuses:
            conn.close()
            return {
                'success': False,
                'message': f'無効なステータス: {status}'
            }
        
        # 取り下げの場合は現在のステータスを確認
        if status == 'withdrawn':
            cursor.execute(f"SELECT status FROM {table_name} WHERE id = ?", (request_id,))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return {
                    'success': False,
                    'message': f'申請ID {request_id} が見つかりません'
                }
            
            current_status = result[0]
            if current_status != 'pending':
                conn.close()
                return {
                    'success': False,
                    'message': f'申請は既に承認済みまたは却下済みのため取り下げできません（現在のステータス: {current_status}）'
                }
        
        # ステータス更新
        now = datetime.now().isoformat()
        
        if status in ['approved', 'rejected']:
            # 承認/却下の場合はapproved_byとapproved_atも設定
            cursor.execute(f"""
                UPDATE {table_name}
                SET status = ?,
                    approved_by = ?,
                    approved_at = ?,
                    updated_at = ?
                WHERE id = ?
            """, (status, updated_by or 'admin', now, now, request_id))
        else:
            # 取り下げの場合はupdated_atのみ更新
            cursor.execute(f"""
                UPDATE {table_name}
                SET status = ?,
                    updated_at = ?
                WHERE id = ?
            """, (status, now, request_id))
        
        conn.commit()
        conn.close()
        
        status_names = {
            'approved': '承認',
            'rejected': '却下',
            'withdrawn': '取り下げ'
        }
        
        return {
            'success': True,
            'message': f'申請を{status_names[status]}しました'
        }
        
    except Exception as e:
        print(f"[エラー] ステータス更新エラー: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()
        return {
            'success': False,
            'message': f'エラー: {str(e)}'
        }

def save_pdf_from_html(html_content, filename_prefix, employee_num, date_str, employee_name='', additional_css=''):
    """
    HTMLコンテンツからPDFを生成して保存（共通関数）
    
    Args:
        html_content: HTMLコンテンツ
        filename_prefix: ファイル名のプレフィックス（例: '時間外'、'休暇願'）
        employee_num: 従業員番号
        date_str: 日付文字列（YYYY-MM-DD形式）
        employee_name: 従業員名（オプション）
        additional_css: 追加のCSS（オプション）
    
    Returns:
        dict: {'success': bool, 'filename': str, 'path': str, 'message': str}
    """
    import os
    import re
    from datetime import datetime
    
    try:
        # PDFフォルダのパスを取得（設定から）
        pdf_dir = Config.PDF_SAVE_DIR
        
        # Docker環境の場合は相対パスを絶対パスに変換
        if not os.path.isabs(pdf_dir):
            # 相対パスの場合は、データベースパスと同じディレクトリのPDFフォルダを使用
            pdf_dir = os.path.join(os.path.dirname(Config.DATABASE_PATH), 'PDF')
        
        # フォルダが存在しない場合は作成
        os.makedirs(pdf_dir, exist_ok=True)
        
        # ファイル名に使用できない文字を除去（Windowsのファイル名に使用できない文字）
        safe_employee_name = ''
        if employee_name:
            # ファイル名に使用できない文字を除去: < > : " / \ | ? *
            safe_employee_name = re.sub(r'[<>:"/\\|?*]', '', employee_name)
            safe_employee_name = safe_employee_name.strip()
        
        # ファイル名を生成（「休暇願」または「時間外」+ 従業員名 + 社員番号 + 日付）
        date_str_clean = date_str.replace('-', '')
        if safe_employee_name:
            filename = f'{filename_prefix}{safe_employee_name}{employee_num}{date_str_clean}.pdf'
        else:
            filename = f'{filename_prefix}{employee_num}{date_str_clean}.pdf'
        pdf_path = os.path.join(pdf_dir, filename)
        
        # weasyprint を使用してPDF生成
        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            
            font_config = FontConfiguration()
            base_css = '''
                @page { size: A4; margin: 15mm; }
                body { font-family: "Yu Gothic", "YuGothic", "Meiryo", sans-serif; color: #000; background: #fff; }
                .container { border: 2px solid #000; padding: 20mm; }
                h1 { font-size: 20pt; text-align: center; border-bottom: 3px double #000; padding-bottom: 10pt; margin-bottom: 20pt; }
                .confirmation-section { border: 2px solid #000; margin-bottom: 15pt; padding: 12pt; page-break-inside: avoid; }
                .confirmation-section h3 { font-size: 14pt; border-bottom: 2px solid #000; padding-bottom: 5pt; margin-bottom: 10pt; }
                .back-link, .button-group, .subtitle, #alert { display: none; }
            '''
            css = CSS(string=base_css + additional_css, font_config=font_config)
            
            HTML(string=html_content).write_pdf(pdf_path, stylesheets=[css], font_config=font_config)
            print(f"[PDF保存] {filename} を {pdf_dir} に保存しました")
            return {
                'success': True,
                'filename': filename,
                'path': pdf_path,
                'message': f'PDFを保存しました: {filename}'
            }
            
        except ImportError:
            # weasyprint が利用できない場合は、HTMLとして保存
            txt_filename = filename.replace('.pdf', '.html')
            txt_path = os.path.join(pdf_dir, txt_filename)
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"[HTML保存] {txt_filename}")
            return {
                'success': True,
                'filename': txt_filename,
                'path': txt_path,
                'message': f'HTMLファイルとして保存しました: {txt_filename}'
            }
        
    except Exception as e:
        print(f"[エラー] PDF保存エラー: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'filename': None,
            'path': None,
            'message': f'エラー: {str(e)}'
        }
