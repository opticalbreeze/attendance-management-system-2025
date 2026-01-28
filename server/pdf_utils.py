#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF生成ユーティリティモジュール
PDF生成とファイル管理の専門モジュール
"""

import os
import re
from datetime import datetime, date
from config import Config
from constants import AttendanceConstants
from logger_config import setup_logger

logger = setup_logger(__name__)

def calculate_payroll_month_from_date(date_str):
    """
    日付から給与計算月度を計算（前月16日〜当月15日が1つの月度）
    
    Args:
        date_str: 日付文字列（YYYY-MM-DD形式）
    
    Returns:
        str: 月度文字列（YYYY_MM形式、例: 2026_02）
    """
    try:
        date_obj = datetime.strptime(date_str, AttendanceConstants.DATE_FORMAT).date()
        year = date_obj.year
        month = date_obj.month
        day = date_obj.day
        
        # 給与計算期間のルール：前月16日〜当月15日が1つの月度
        # 16日以降なら翌月度、15日以前なら当月度
        if day >= Config.PAYROLL_START_DAY:  # 16日以降
            # 翌月度
            if month == 12:
                payroll_year = year + 1
                payroll_month = 1
            else:
                payroll_year = year
                payroll_month = month + 1
        else:  # 15日以前
            # 当月度
            payroll_year = year
            payroll_month = month
        
        return f'{payroll_year}_{payroll_month:02d}'
    except (ValueError, TypeError) as e:
        # 日付の解析に失敗した場合は現在の年月を使用
        now = datetime.now()
        logger.warning(f"日付の解析に失敗したため、現在の年月を使用: {date_str}, エラー: {e}")
        if now.day >= Config.PAYROLL_START_DAY:
            if now.month == 12:
                return f'{now.year + 1}_01'
            else:
                return f'{now.year}_{now.month + 1:02d}'
        else:
            return f'{now.year}_{now.month:02d}'

def save_pdf_from_html(html_content, filename_prefix, employee_num, date_str, employee_name='', additional_css='', document_id=None):
    """
    HTMLコンテンツからPDFを生成して保存（共通関数）
    
    Args:
        html_content: HTMLコンテンツ
        filename_prefix: ファイル名のプレフィックス（例: '時間外'、'休暇願'）
        employee_num: 従業員番号
        date_str: 日付文字列（YYYY-MM-DD形式）
        employee_name: 従業員名（オプション）
        additional_css: 追加のCSS（オプション）
        document_id: 書類ID（オプション、ファイル名に含める）
    
    Returns:
        dict: {'success': bool, 'filename': str, 'path': str, 'message': str}
    """
    try:
        # PDFフォルダを基準とした保存先に変更
        pdf_base_dir = os.path.join(os.path.dirname(Config.DATABASE_PATH), 'PDF')
        
        # PDFフォルダが存在しない場合は作成
        os.makedirs(pdf_base_dir, exist_ok=True)
        
        # ファイル名に使用できない文字を除去（Windowsのファイル名に使用できない文字）
        safe_employee_name = ''
        if employee_name:
            # ファイル名に使用できない文字を除去: < > : " / \ | ? *
            safe_employee_name = re.sub(r'[<>:"/\\|?*]', '', employee_name)
            safe_employee_name = safe_employee_name.strip()
        
        # 給与計算期間を考慮した月度を取得（YYYY_MM形式）
        # 前月16日〜当月15日が1つの月度
        month_str = calculate_payroll_month_from_date(date_str)
        logger.info(f"日付 {date_str} の給与計算月度: {month_str}")
        
        # 月度フォルダを作成（存在しない場合）
        year_month_folder = os.path.join(pdf_base_dir, month_str)
        os.makedirs(year_month_folder, exist_ok=True)
        
        # 従業員ごとのフォルダを作成（名前_年月形式）
        if safe_employee_name:
            employee_folder_name = f'{safe_employee_name}_{month_str}'
        else:
            employee_folder_name = f'employee_{employee_num}_{month_str}'
        
        final_folder = os.path.join(year_month_folder, employee_folder_name)
        os.makedirs(final_folder, exist_ok=True)
        logger.info(f"PDF保存先フォルダ: {final_folder}")
        logger.info(f"PDFベースディレクトリ: {pdf_base_dir}")
        logger.info(f"月度フォルダ: {year_month_folder}")
        logger.info(f"従業員フォルダ名: {employee_folder_name}")
        
        # ファイル名を生成（名前_日付_書類の種別_ID.pdf形式）
        date_str_clean = date_str.replace('-', '')  # YYYYMMDD形式
        
        # 書類の種別を設定
        document_type = filename_prefix  # '時間外' または '休暇願'
        
        # ファイル名: 名前_日付_書類の種別_ID.pdf
        # 例: 田中宏和_20260215_時間外_123.pdf, 田中宏和_20260220_休暇願_456.pdf
        if document_id:
            if safe_employee_name:
                filename = f'{safe_employee_name}_{date_str_clean}_{document_type}_{document_id}.pdf'
            else:
                filename = f'従業員{employee_num}_{date_str_clean}_{document_type}_{document_id}.pdf'
        else:
            # IDがない場合は時刻を使用（後方互換性のため）
            now = datetime.now()
            timestamp_str = now.strftime(AttendanceConstants.TIME_FORMAT_HMS)
            if safe_employee_name:
                filename = f'{safe_employee_name}_{date_str_clean}_{document_type}_{timestamp_str}.pdf'
            else:
                filename = f'従業員{employee_num}_{date_str_clean}_{document_type}_{timestamp_str}.pdf'
        
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
            logger.info(f"PDF保存成功: {filename}")
            logger.info(f"PDF保存先フォルダ: {final_folder}")
            logger.info(f"PDF保存フルパス: {pdf_path}")
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
        logger.error(f"PDF保存試行時のパラメータ: employee_num={employee_num}, date_str={date_str}, employee_name={employee_name}, filename_prefix={filename_prefix}")
        logger.error(f"PDFベースディレクトリ: {pdf_base_dir if 'pdf_base_dir' in locals() else 'N/A'}")
        return {
            'success': False,
            'filename': None,
            'path': None,
            'message': f'エラー: {str(e)}'
        }

