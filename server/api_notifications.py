#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通知API - 打刻PC用通知システム
APIエンドポイントのみを担当（リファクタリング版）
"""

from flask import Flask, request, jsonify, Blueprint
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# 新しいモジュールからインポート
from notifications.exclusion_manager import (
    load_notification_exclusions,
    save_notification_exclusions,
    init_notification_files
)
from notifications.notification_data import (
    load_notification_data,
    load_acknowledged_notifications,
    save_acknowledged_notifications
)
from notifications.notification_filter import (
    filter_notifications
)

# ログ設定
logger = logging.getLogger(__name__)

# 通知APIブループリント
notification_bp = Blueprint('notifications', __name__)

# 通知関連ファイルパス（デバッグ用）
EXCLUSIONS_FILE = os.path.join(os.path.dirname(__file__), '..', 'notification_exclusions.json')
EXCLUSIONS_FILE_CONTAINER = '/app/notification_exclusions.json'

@notification_bp.route('/api/notifications', methods=['GET'])
def get_notifications():
    """通知一覧を取得"""
    try:
        # パラメータ取得
        employee_id = request.args.get('employee_id')
        include_acknowledged = request.args.get('include_acknowledged', 'false').lower() == 'true'
        
        # データ読み込み
        all_notifications = load_notification_data()
        acknowledged_notifications = load_acknowledged_notifications()
        excluded_employee_ids = load_notification_exclusions()
        
        # デバッグログ（常に詳細ログを出力）
        logger.info(f"[通知API] リクエスト受信: employee_id={employee_id}, include_acknowledged={include_acknowledged}")
        logger.info(f"[通知API] 全通知={len(all_notifications)}件, 除外リスト={len(excluded_employee_ids)}件")
        if excluded_employee_ids:
            logger.info(f"[通知API] 除外リスト内容: {list(excluded_employee_ids)}")
        else:
            logger.warning(f"[通知API] 除外リストが空です")
        
        # フィルタリング（新しいモジュールを使用）
        filtered_notifications, stats = filter_notifications(
            all_notifications=all_notifications,
            employee_id=employee_id,
            include_acknowledged=include_acknowledged,
            acknowledged_notifications=acknowledged_notifications,
            excluded_employee_ids=excluded_employee_ids
        )
        
        if employee_id:
            logger.info(f"[通知API] クライアントPC用リクエスト: employee_id={employee_id} の通知={len([n for n in filtered_notifications if str(n.get('employee_id', '')) == str(employee_id)])}件")
        
        return jsonify({
            'status': 'success',
            'notifications': filtered_notifications,
            'total_count': stats['total'],
            'filtered_count': stats['filtered_count'],
            'acknowledged_count': len(acknowledged_notifications),
            'checked_count': stats['checked_count']
        })
        
    except Exception as e:
        logger.error(f"通知取得APIエラー: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@notification_bp.route('/api/notifications/acknowledge', methods=['POST'])
def acknowledge_notification():
    """通知を確認済みにする"""
    try:
        data = request.get_json()
        notification_id = data.get('notification_id')
        
        if not notification_id:
            return jsonify({
                'status': 'error',
                'message': '通知IDが指定されていません'
            }), 400
        
        # 確認済み通知に追加
        acknowledged_notifications = load_acknowledged_notifications()
        acknowledged_notifications.add(notification_id)
        save_acknowledged_notifications(acknowledged_notifications)
        
        logger.info(f"通知確認API: {notification_id} を確認済みに設定")
        
        return jsonify({
            'status': 'success',
            'message': '通知を確認済みに設定しました',
            'notification_id': notification_id
        })
        
    except Exception as e:
        logger.error(f"通知確認APIエラー: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@notification_bp.route('/api/notifications/acknowledge-all', methods=['POST'])
def acknowledge_all_notifications():
    """全通知を確認済みにする"""
    try:
        data = request.get_json()
        employee_id = data.get('employee_id')  # 特定従業員のみの場合
        
        # 通知データを読み込み
        all_notifications = load_notification_data()
        acknowledged_notifications = load_acknowledged_notifications()
        
        # 対象通知を確認済みに設定
        count = 0
        for notification in all_notifications:
            if employee_id and notification['employee_id'] != employee_id:
                continue
            
            if notification['id'] not in acknowledged_notifications:
                acknowledged_notifications.add(notification['id'])
                count += 1
        
        save_acknowledged_notifications(acknowledged_notifications)
        
        logger.info(f"全通知確認API: {count}件を確認済みに設定 (employee_id={employee_id})")
        
        return jsonify({
            'status': 'success',
            'message': f'{count}件の通知を確認済みに設定しました',
            'acknowledged_count': count
        })
        
    except Exception as e:
        logger.error(f"全通知確認APIエラー: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@notification_bp.route('/api/notifications/stats', methods=['GET'])
def get_notification_stats():
    """通知統計情報を取得"""
    try:
        all_notifications = load_notification_data()
        acknowledged_notifications = load_acknowledged_notifications()
        
        # 統計計算
        total = len(all_notifications)
        acknowledged = len([n for n in all_notifications if n['id'] in acknowledged_notifications])
        unacknowledged = total - acknowledged
        
        # 種別別統計
        error_count = len([n for n in all_notifications if n['alert_type'] == 'error' and n['id'] not in acknowledged_notifications])
        warning_count = len([n for n in all_notifications if n['alert_type'] == 'warning' and n['id'] not in acknowledged_notifications])
        
        return jsonify({
            'status': 'success',
            'stats': {
                'total_notifications': total,
                'acknowledged_notifications': acknowledged,
                'unacknowledged_notifications': unacknowledged,
                'unacknowledged_errors': error_count,
                'unacknowledged_warnings': warning_count
            }
        })
        
    except Exception as e:
        logger.error(f"通知統計APIエラー: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@notification_bp.route('/api/notifications/exclusions', methods=['GET'])
def get_notification_exclusions():
    """通知除外リストを取得"""
    try:
        # デバッグ: API呼び出しを確実にログに記録
        logger.info("=" * 80)
        logger.info("[除外リスト取得API] API呼び出し受信")
        logger.info(f"[除外リスト取得API] EXCLUSIONS_FILE: {EXCLUSIONS_FILE}")
        logger.info(f"[除外リスト取得API] EXCLUSIONS_FILE_CONTAINER: {EXCLUSIONS_FILE_CONTAINER}")
        
        excluded_employee_ids = load_notification_exclusions()
        
        logger.info(f"[除外リスト取得API] 除外リスト件数: {len(excluded_employee_ids)}件, 内容: {list(excluded_employee_ids)}")
        logger.info("=" * 80)
        
        return jsonify({
            'status': 'success',
            'excluded_employee_ids': list(excluded_employee_ids),
            'count': len(excluded_employee_ids),
            'debug': {
                'exclusions_file': EXCLUSIONS_FILE,
                'exclusions_file_container': EXCLUSIONS_FILE_CONTAINER,
                'exclusions_file_exists': os.path.exists(EXCLUSIONS_FILE) and os.path.isfile(EXCLUSIONS_FILE),
                'exclusions_file_container_exists': os.path.exists(EXCLUSIONS_FILE_CONTAINER) and os.path.isfile(EXCLUSIONS_FILE_CONTAINER)
            }
        })
    except Exception as e:
        logger.error(f"通知除外リスト取得APIエラー: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@notification_bp.route('/api/notifications/exclusions', methods=['POST'])
def update_notification_exclusions():
    """通知除外リストを更新"""
    try:
        data = request.get_json()
        excluded_employee_ids = data.get('excluded_employee_ids', [])
        
        if not isinstance(excluded_employee_ids, list):
            return jsonify({
                'status': 'error',
                'message': 'excluded_employee_idsは配列である必要があります'
            }), 400
        
        # 文字列のセットに変換して保存（空のリストも明示的に保存）
        excluded_set = set(str(emp_id) for emp_id in excluded_employee_ids)
        save_notification_exclusions(excluded_set)
        
        logger.info(f"通知除外リスト更新API: {len(excluded_set)}件を除外リストに設定")
        if excluded_set:
            logger.info(f"除外対象: {list(excluded_set)}")
        else:
            logger.info("除外リストは空です（全従業員にお知らせが届きます）")
        
        return jsonify({
            'status': 'success',
            'message': f'{len(excluded_set)}件の従業員を除外リストに設定しました' if excluded_set else '除外リストをクリアしました（全従業員にお知らせが届きます）',
            'excluded_employee_ids': list(excluded_set),
            'count': len(excluded_set)
        })
        
    except Exception as e:
        logger.error(f"通知除外リスト更新APIエラー: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@notification_bp.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

@notification_bp.route('/api/notifications/debug', methods=['GET'])
def debug_notifications():
    """デバッグ用: 除外リストと通知の状態を確認"""
    try:
        excluded_employee_ids = load_notification_exclusions()
        all_notifications = load_notification_data()
        
        # 除外リストに含まれる従業員の通知を確認
        excluded_notifications = []
        for notification in all_notifications:
            notification_emp_id = str(notification.get('employee_id', ''))
            if notification_emp_id in excluded_employee_ids:
                excluded_notifications.append({
                    'id': notification['id'],
                    'employee_id': notification_emp_id,
                    'employee_name': notification.get('employee_name', '不明'),
                    'message': notification.get('message', ''),
                    'work_date': notification.get('work_date', '')
                })
        
        return jsonify({
            'status': 'success',
            'excluded_employee_ids': list(excluded_employee_ids),
            'excluded_count': len(excluded_employee_ids),
            'total_notifications': len(all_notifications),
            'excluded_notifications': excluded_notifications,
            'excluded_notifications_count': len(excluded_notifications),
            'file_paths': {
                'container': EXCLUSIONS_FILE_CONTAINER,
                'host': EXCLUSIONS_FILE,
                'container_exists': os.path.exists(EXCLUSIONS_FILE_CONTAINER) and os.path.isfile(EXCLUSIONS_FILE_CONTAINER),
                'host_exists': os.path.exists(EXCLUSIONS_FILE) and os.path.isfile(EXCLUSIONS_FILE)
            }
        })
    except Exception as e:
        logger.error(f"デバッグAPIエラー: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def register_notification_api_routes(app):
    """通知APIルートを登録"""
    app.register_blueprint(notification_bp)
    logger.info("通知APIルートを登録しました")

if __name__ == "__main__":
    # テスト用
    from flask import Flask
    app = Flask(__name__)
    register_notification_api_routes(app)
    app.run(debug=True, port=5001)
