#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
モニタリングAPI
エラー・警告の取得と統計情報を提供
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# StructuredFormatterをインポート（logger_config.pyから）
try:
    from logger_config import StructuredFormatter
except ImportError:
    # フォールバック: 基本的なフォーマッターを使用
    StructuredFormatter = logging.Formatter

monitoring_bp = Blueprint('monitoring', __name__)


def load_log_entries(log_path: Path, hours: int = 24, 
                     category: Optional[str] = None,
                     severity: Optional[str] = None,
                     limit: int = 100) -> List[Dict[str, Any]]:
    """
    ログファイルからエントリを読み込む
    
    Args:
        log_path: ログファイルのパス
        hours: 取得する時間範囲（時間）
        category: カテゴリでフィルタリング
        severity: 重要度でフィルタリング
        limit: 取得件数の上限
    
    Returns:
        ログエントリのリスト
    """
    entries = []
    
    if not log_path.exists():
        return entries
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    log_entry = json.loads(line.strip())
                    if not log_entry:
                        continue
                    
                    # タイムスタンプでフィルタリング
                    log_time_str = log_entry.get('timestamp', '')
                    if log_time_str:
                        try:
                            log_time = datetime.fromisoformat(log_time_str.replace('Z', '+00:00'))
                            if log_time.replace(tzinfo=None) < cutoff_time:
                                continue
                        except (ValueError, AttributeError):
                            continue
                    
                    # カテゴリでフィルタリング
                    if category and log_entry.get('category') != category:
                        continue
                    
                    # 重要度でフィルタリング
                    if severity and log_entry.get('severity') != severity:
                        continue
                    
                    entries.append(log_entry)
                    
                    # 上限に達したら終了
                    if len(entries) >= limit:
                        break
                        
                except json.JSONDecodeError:
                    # JSON解析エラーは無視して続行
                    continue
    except Exception as e:
        # ファイル読み込みエラーは空リストを返す
        print(f"ログファイル読み込みエラー: {e}")
    
    # 時系列でソート（新しい順）
    entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return entries


@monitoring_bp.route('/api/monitoring/errors', methods=['GET'])
def get_errors():
    """エラー一覧を取得"""
    try:
        hours = int(request.args.get('hours', 24))
        category = request.args.get('category')
        severity = request.args.get('severity')
        limit = int(request.args.get('limit', 100))
        
        log_dir = Path('logs')
        error_log_path = log_dir / 'errors.jsonl'
        
        errors = load_log_entries(
            error_log_path,
            hours=hours,
            category=category,
            severity=severity,
            limit=limit
        )
        
        return jsonify({
            'status': 'success',
            'count': len(errors),
            'errors': errors
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@monitoring_bp.route('/api/monitoring/warnings', methods=['GET'])
def get_warnings():
    """警告一覧を取得"""
    try:
        hours = int(request.args.get('hours', 24))
        category = request.args.get('category')
        severity = request.args.get('severity')
        limit = int(request.args.get('limit', 100))
        
        log_dir = Path('logs')
        warning_log_path = log_dir / 'warnings.jsonl'
        
        warnings = load_log_entries(
            warning_log_path,
            hours=hours,
            category=category,
            severity=severity,
            limit=limit
        )
        
        return jsonify({
            'status': 'success',
            'count': len(warnings),
            'warnings': warnings
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@monitoring_bp.route('/api/monitoring/stats', methods=['GET'])
def get_error_stats():
    """エラー統計を取得"""
    try:
        hours = int(request.args.get('hours', 24))
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        stats: Dict[str, Any] = {
            'total_errors': 0,
            'total_warnings': 0,
            'by_category': {},
            'by_severity': {},
            'recent_errors': [],
            'error_trend': []  # 時間帯別のエラー数
        }
        
        log_dir = Path('logs')
        
        # エラーログを解析
        error_log_path = log_dir / 'errors.jsonl'
        if error_log_path.exists():
            errors = load_log_entries(error_log_path, hours=hours, limit=1000)
            stats['total_errors'] = len(errors)
            
            for error in errors:
                category = error.get('category', 'unknown')
                stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
                
                severity = error.get('severity', 'unknown')
                stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
            
            # 最新10件のエラー
            stats['recent_errors'] = errors[:10]
        
        # 警告ログを解析
        warning_log_path = log_dir / 'warnings.jsonl'
        if warning_log_path.exists():
            warnings = load_log_entries(warning_log_path, hours=hours, limit=1000)
            stats['total_warnings'] = len(warnings)
        
        # 時間帯別のエラー数を集計（簡易版）
        if error_log_path.exists():
            try:
                with open(error_log_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            log_entry = json.loads(line.strip())
                            timestamp_str = log_entry.get('timestamp', '')
                            if timestamp_str:
                                log_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                if log_time.replace(tzinfo=None) >= cutoff_time:
                                    hour_key = log_time.strftime('%Y-%m-%d %H:00')
                                    stats['error_trend'].append(hour_key)
                        except (json.JSONDecodeError, ValueError):
                            continue
                
                # 時間帯別に集計
                from collections import Counter
                trend_counter = Counter(stats['error_trend'])
                stats['error_trend'] = [
                    {'hour': hour, 'count': count}
                    for hour, count in sorted(trend_counter.items())
                ]
            except Exception:
                stats['error_trend'] = []
        
        return jsonify({
            'status': 'success',
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@monitoring_bp.route('/api/monitoring/client-error', methods=['POST'])
def log_client_error():
    """クライアント側のエラーをログに記録"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400
        
        error_type = data.get('type', 'unknown')
        error_data = data.get('data', {})
        timestamp = data.get('timestamp', datetime.utcnow().isoformat())
        
        # クライアントエラー専用ロガー
        client_error_logger = logging.getLogger('client_errors')
        if not client_error_logger.handlers:
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            handler = logging.FileHandler(log_dir / 'client_errors.jsonl', encoding='utf-8')
            handler.setFormatter(StructuredFormatter())
            client_error_logger.addHandler(handler)
        
        client_error_logger.error(
            f"Client {error_type}: {error_data.get('message', 'Unknown error')}",
            extra={
                'context': {
                    'type': error_type,
                    'data': error_data,
                    'timestamp': timestamp,
                    'user_agent': request.headers.get('User-Agent'),
                    'url': error_data.get('url', request.url)
                }
            }
        )
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


