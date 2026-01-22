#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF生成ユーティリティモジュール
PDF生成とファイル管理の専門モジュール
"""

import os
import re
from datetime import datetime
from config import Config
from constants import AttendanceConstants
from logger_config import setup_logger

logger = setup_logger(__name__)

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
    try:
        # reportsフォルダを基準とした保存先に変更（PDFフォルダは使用しない）
        reports_base_dir = os.path.join(os.path.dirname(Config.DATABASE_PATH), 'reports')
        
        # reportsフォルダが存在しない場合は作成
        os.makedirs(reports_base_dir, exist_ok=True)
        
        # reportsフォルダを基準とした保存先に変更（PDFフォルダは使用しない）
        reports_base_dir = os.path.join(os.path.dirname(Config.DATABASE_PATH), 'reports')
        
        # reportsフォルダが存在しない場合は作成
        os.makedirs(reports_base_dir, exist_ok=True)
        
        # ファイル名に使用できない文字を除去（Windowsのファイル名に使用できない文字）
        safe_employee_name = ''
        if employee_name:
            # ファイル名に使用できない文字を除去: < > : " / \ | ? *
            safe_employee_name = re.sub(r'[<>:"/\\|?*]', '', employee_name)
            safe_employee_name = safe_employee_name.strip()
        
        # 月度を取得（YYYYMM形式）
        try:
            date_obj = datetime.strptime(date_str, AttendanceConstants.DATE_FORMAT)
            month_str = date_obj.strftime(AttendanceConstants.DATE_FORMAT_YM)  # YYYYMM形式
        except (ValueError, TypeError):
            # 日付の解析に失敗した場合は現在の年月を使用
            month_str = datetime.now().strftime(AttendanceConstants.DATE_FORMAT_YM)
            logger.warning(f"日付の解析に失敗したため、現在の年月を使用: {date_str}")
        
        # 申請種別に応じたサブフォルダ名を設定
        document_type = ''
        if filename_prefix == '時間外':
            document_type = 'overtime_applications'  # 時間外申告
        elif filename_prefix == '休暇願':
            document_type = 'leave_requests'  # 休暇申請
        else:
            document_type = 'other_documents'  # その他の書類
        
        # フォルダ構造: reports/{年月}/{申請種別}/{従業員名}
        # 例: reports/202412/overtime_applications/井上誠二/
        year_month_folder = os.path.join(reports_base_dir, month_str)
        document_type_folder = os.path.join(year_month_folder, document_type)
        
        if safe_employee_name:
            final_folder = os.path.join(document_type_folder, safe_employee_name)
        else:
            final_folder = os.path.join(document_type_folder, f'employee_{employee_num}')
        
        # フォルダを作成（存在しない場合）
        os.makedirs(final_folder, exist_ok=True)
        logger.debug(f"PDF保存先: {final_folder}")
        
        # フォルダを作成（存在しない場合）
        os.makedirs(final_folder, exist_ok=True)
        logger.debug(f"PDF保存先: {final_folder}")
        
        # ファイル名を生成（日付_申請種別_名前_時刻.pdf形式）
        now = datetime.now()
        timestamp_str = now.strftime(AttendanceConstants.TIME_FORMAT_HMS)  # 時刻のみ（HHMMSS形式）
        date_str_clean = date_str.replace('-', '')  # YYYYMMDD形式
        
        # ファイル名: 日付_申請種別_従業員名_時刻.pdf
        # 例: 20241215_時間外_井上誠二_143025.pdf, 20241220_休暇願_松浦真司_091530.pdf
        if safe_employee_name:
            filename = f'{date_str_clean}_{filename_prefix}_{safe_employee_name}_{timestamp_str}.pdf'
        else:
            filename = f'{date_str_clean}_{filename_prefix}_従業員{employee_num}_{timestamp_str}.pdf'
        
        pdf_path = os.path.join(final_folder, filename)
        
        # weasyprint を使用してPDF生成
        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            
            font_config = FontConfiguration()
            base_css = '''
                @page { size: A4; margin: 15mm; }
                @font-face {
                    font-family: "Noto Sans CJK JP";
                    src: local("Noto Sans CJK JP Regular"), local("Noto Sans CJK JP");
                }
                body { font-family: "Noto Sans CJK JP", "Noto Sans CJK", "Yu Gothic", "YuGothic", "Meiryo", sans-serif; color: #000; background: #fff; }
                .container { border: 2px solid #000; padding: 20mm; }
                h1 { font-size: 20pt; text-align: center; border-bottom: 3px double #000; padding-bottom: 10pt; margin-bottom: 20pt; }
                .confirmation-section { border: 2px solid #000; margin-bottom: 15pt; padding: 12pt; page-break-inside: avoid; break-inside: avoid; }
                .confirmation-section h3 { font-size: 14pt; border-bottom: 2px solid #000; padding-bottom: 5pt; margin-bottom: 10pt; }
                .info-row { display: table; width: 100%; }
                .info-label { display: table-cell; vertical-align: top; }
                .info-value { display: table-cell; vertical-align: top; }
                .back-link, .button-group, .subtitle, #alert { display: none !important; }
            '''
            css = CSS(string=base_css + additional_css, font_config=font_config)
            
            HTML(string=html_content).write_pdf(pdf_path, stylesheets=[css], font_config=font_config)
            logger.info(f"PDF保存成功: {filename} -> {final_folder}")
            logger.debug(f"PDF保存パス: {pdf_path}")
            return {
                'success': True,
                'filename': filename,
                'path': pdf_path,
                'message': f'PDFを保存しました: {filename}'
            }
            
        except ImportError:
            # weasyprint が利用できない場合は、HTMLとして保存
            txt_filename = filename.replace('.pdf', '.html')
            txt_path = os.path.join(final_folder, txt_filename)
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"HTML保存: {txt_filename}")
            return {
                'success': True,
                'filename': txt_filename,
                'path': txt_path,
                'message': f'HTMLファイルとして保存しました: {txt_filename}'
            }
        
    except Exception as e:
        logger.error(f"PDF保存エラー: {e}", exc_info=True)
        return {
            'success': False,
            'filename': None,
            'path': None,
            'message': f'エラー: {str(e)}'
        }

