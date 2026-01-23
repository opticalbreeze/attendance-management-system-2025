#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通知API - 打刻PC用通知システム
"""

from flask import Flask, request, jsonify, Blueprint
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

# ログ設定
logger = logging.getLogger(__name__)

# 通知APIブループリント
notification_bp = Blueprint('notifications', __name__)

# 通知関連ファイルパス
NOTIFICATION_DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'notification_data.json')
ACKNOWLEDGED_FILE = os.path.join(os.path.dirname(__file__), '..', 'acknowledged_notifications.json')

def load_notification_data() -> List[Dict[str, Any]]:
    """通知データを読み込み"""
    try:
        if os.path.exists(NOTIFICATION_DATA_FILE):
            with open(NOTIFICATION_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('notifications', [])
        else:
            logger.warning(f"通知データファイルが見つかりません: {NOTIFICATION_DATA_FILE}")
            return []
    except Exception as e:
        logger.error(f"通知データ読み込みエラー: {e}")
        return []

def load_acknowledged_notifications() -> set:
    """確認済み通知を読み込み"""
    try:
        if os.path.exists(ACKNOWLEDGED_FILE):
            with open(ACKNOWLEDGED_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('acknowledged', []))
        else:
            return set()
    except Exception as e:
        logger.error(f"確認済み通知読み込みエラー: {e}")
        return set()

def save_acknowledged_notifications(acknowledged_set: set):
    """確認済み通知を保存"""
    try:
        data = {
            'acknowledged': list(acknowledged_set),
            'last_updated': datetime.now().isoformat()
        }
        with open(ACKNOWLEDGED_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"確認済み通知を保存: {len(acknowledged_set)}件")
    except Exception as e:
        logger.error(f"確認済み通知保存エラー: {e}")

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
        
        # フィルタリング
        filtered_notifications = []
        for notification in all_notifications:
            # 確認済みフィルター
            if not include_acknowledged and notification['id'] in acknowledged_notifications:
                continue
            
            # 従業員IDフィルター
            if employee_id and notification['employee_id'] != employee_id:
                continue
            
            filtered_notifications.append(notification)
        
        logger.info(f"通知API: 全{len(all_notifications)}件中{len(filtered_notifications)}件を返却 (employee_id={employee_id})")
        
        return jsonify({
            'status': 'success',
            'notifications': filtered_notifications,
            'total_count': len(all_notifications),
            'filtered_count': len(filtered_notifications),
            'acknowledged_count': len(acknowledged_notifications)
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

@notification_bp.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

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