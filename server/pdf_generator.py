#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF生成用HTML生成モジュール
時間外申告と休暇願のHTMLコンテンツを生成
"""

from datetime import datetime

def generate_overtime_html(employee_name, application_date, work_date, overtime_entries):
    """
    時間外申告のHTMLコンテンツを生成
    
    Args:
        employee_name: 従業員名
        application_date: 申請日
        work_date: 作業日
        overtime_entries: 時間外作業エントリのリスト
    
    Returns:
        str: HTMLコンテンツ
    """
    now = datetime.now()
    print_date = now.strftime('%Y年%m月%d日 %H:%M')
    
    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <style>
        @page {{ size: A4; margin: 15mm; }}
        @font-face {{
            font-family: "Noto Sans CJK JP";
            src: local("Noto Sans CJK JP Regular"), local("Noto Sans CJK JP");
        }}
        body {{ font-family: "Noto Sans CJK JP", "Noto Sans CJK", "Yu Gothic", "YuGothic", "Meiryo", sans-serif; color: #000; background: #fff; }}
        .container {{ border: 2px solid #000; padding: 20mm; }}
        h1 {{ font-size: 20pt; text-align: center; border-bottom: 3px double #000; padding-bottom: 10pt; margin-bottom: 20pt; }}
        .confirmation-section {{ border: 2px solid #000; margin-bottom: 15pt; padding: 12pt; page-break-inside: avoid; break-inside: avoid; }}
        .confirmation-section h3 {{ font-size: 14pt; border-bottom: 2px solid #000; padding-bottom: 5pt; margin-bottom: 10pt; }}
        .info-row {{ padding: 8pt 0; border-bottom: 1px solid #666; font-size: 11pt; display: table; width: 100%; }}
        .info-label {{ font-weight: bold; color: #000; width: 120pt; display: table-cell; vertical-align: top; padding-right: 10pt; }}
        .info-value {{ color: #000; display: table-cell; vertical-align: top; }}
        .overtime-item {{ border: 1px solid #000; padding: 10pt; margin-bottom: 10pt; page-break-inside: avoid; break-inside: avoid; }}
        .overtime-item h4 {{ font-size: 12pt; color: #000; border-bottom: 1px solid #000; padding-bottom: 5pt; margin-bottom: 8pt; }}
        .pdf-footer {{ text-align: right; font-size: 9pt; margin-top: 15pt; padding-top: 10pt; border-top: 1px solid #000; }}
    </style>
</head>
<body>
    <div class="container" data-print-date="{print_date}">
        <h1>時間外作業申告書</h1>
        
        <div class="confirmation-section">
            <h3>基本情報</h3>
            <div class="info-row">
                <div class="info-label">氏名</div>
                <div class="info-value">{employee_name}</div>
            </div>
            <div class="info-row">
                <div class="info-label">申請日</div>
                <div class="info-value">{application_date}</div>
            </div>
            <div class="info-row">
                <div class="info-label">作業日</div>
                <div class="info-value">{work_date}</div>
            </div>
        </div>
        
        <div class="confirmation-section">
            <h3>時間外作業内容</h3>'''
    
    for index, entry in enumerate(overtime_entries, 1):
        start_time = entry.get('start_time', '')
        end_time = entry.get('end_time', '')
        description = entry.get('description', '（未入力）')
        
        # 時間差を計算
        duration = calculate_duration(start_time, end_time)
        
        html += f'''
            <div class="overtime-item">
                <h4>作業 {index}</h4>
                <div class="info-row">
                    <div class="info-label">時間</div>
                    <div class="info-value">{start_time} - {end_time} （{duration}）</div>
                </div>
                <div class="info-row">
                    <div class="info-label">作業内容</div>
                    <div class="info-value">{description}</div>
                </div>
            </div>'''
    
    html += '''
        </div>
        
        <div class="pdf-footer">
            印刷日時: ''' + print_date + '''
        </div>
    </div>
</body>
</html>'''
    
    return html

def generate_leave_html(employee_name, application_date, leave_date_from, leave_date_to,
                        leave_type, leave_subtype=None, substitute_work_date=None, other_reason=None):
    """
    休暇願のHTMLコンテンツを生成
    
    Args:
        employee_name: 従業員名
        application_date: 申請日
        leave_date_from: 休暇開始日
        leave_date_to: 休暇終了日
        leave_type: 休暇種類
        leave_subtype: 特別休暇のサブタイプ
        substitute_work_date: 振替休日の出勤日
        other_reason: その他の理由
    
    Returns:
        str: HTMLコンテンツ
    """
    now = datetime.now()
    print_date = now.strftime('%Y年%m月%d日 %H:%M')
    
    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <style>
        @page {{ size: A4; margin: 15mm; }}
        @font-face {{
            font-family: "Noto Sans CJK JP";
            src: local("Noto Sans CJK JP Regular"), local("Noto Sans CJK JP");
        }}
        body {{ font-family: "Noto Sans CJK JP", "Noto Sans CJK", "Yu Gothic", "YuGothic", "Meiryo", sans-serif; color: #000; background: #fff; }}
        .container {{ border: 2px solid #000; padding: 20mm; }}
        h1 {{ font-size: 20pt; text-align: center; border-bottom: 3px double #000; padding-bottom: 10pt; margin-bottom: 20pt; }}
        .confirmation-section {{ border: 2px solid #000; margin-bottom: 15pt; padding: 12pt; page-break-inside: avoid; break-inside: avoid; }}
        .confirmation-section h3 {{ font-size: 14pt; border-bottom: 2px solid #000; padding-bottom: 5pt; margin-bottom: 10pt; }}
        .info-row {{ padding: 8pt 0; border-bottom: 1px solid #666; font-size: 11pt; display: table; width: 100%; }}
        .info-label {{ font-weight: bold; color: #000; width: 120pt; display: table-cell; vertical-align: top; padding-right: 10pt; }}
        .info-value {{ color: #000; display: table-cell; vertical-align: top; }}
        .pdf-footer {{ text-align: right; font-size: 9pt; margin-top: 15pt; padding-top: 10pt; border-top: 1px solid #000; }}
    </style>
</head>
<body>
    <div class="container" data-print-date="{print_date}">
        <h1>休暇願</h1>
        
        <div class="confirmation-section">
            <h3>基本情報</h3>
            <div class="info-row">
                <div class="info-label">氏名</div>
                <div class="info-value">{employee_name}</div>
            </div>
            <div class="info-row">
                <div class="info-label">申請日</div>
                <div class="info-value">{application_date}</div>
            </div>
            <div class="info-row">
                <div class="info-label">休暇期間</div>
                <div class="info-value">{leave_date_from} ～ {leave_date_to}</div>
            </div>
            <div class="info-row">
                <div class="info-label">休暇種類</div>
                <div class="info-value">{leave_type}{" (" + leave_subtype + ")" if leave_subtype else ""}</div>
            </div>'''
    
    if substitute_work_date:
        html += f'''
            <div class="info-row">
                <div class="info-label">振替出勤日</div>
                <div class="info-value">{substitute_work_date}</div>
            </div>'''
    
    if other_reason:
        html += f'''
            <div class="info-row">
                <div class="info-label">その他理由</div>
                <div class="info-value">{other_reason}</div>
            </div>'''
    
    html += f'''
        </div>
        
        <div class="pdf-footer">
            印刷日時: {print_date}
        </div>
    </div>
</body>
</html>'''
    
    return html

def calculate_duration(start_time, end_time):
    """
    時間差を計算（HH:MM形式）
    
    Args:
        start_time: 開始時刻 (HH:MM)
        end_time: 終了時刻 (HH:MM)
    
    Returns:
        str: 時間差（例: "2時間30分"）
    """
    try:
        start_parts = start_time.split(':')
        end_parts = end_time.split(':')
        
        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
        
        # 日をまたぐ場合
        if end_minutes < start_minutes:
            end_minutes += 24 * 60
        
        total_minutes = end_minutes - start_minutes
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        if hours > 0 and minutes > 0:
            return f"{hours}時間{minutes}分"
        elif hours > 0:
            return f"{hours}時間"
        else:
            return f"{minutes}分"
    except:
        return "計算不可"

