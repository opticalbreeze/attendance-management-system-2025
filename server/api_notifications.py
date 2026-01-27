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
# コンテナ内では /app/ にマウントされているため、相対パスで指定
NOTIFICATION_DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'notification_data.json')
ACKNOWLEDGED_FILE = os.path.join(os.path.dirname(__file__), '..', 'acknowledged_notifications.json')
EXCLUSIONS_FILE = os.path.join(os.path.dirname(__file__), '..', 'notification_exclusions.json')

# コンテナ内のパスも試す（フォールバック）
NOTIFICATION_DATA_FILE_CONTAINER = '/app/notification_data.json'
ACKNOWLEDGED_FILE_CONTAINER = '/app/acknowledged_notifications.json'
EXCLUSIONS_FILE_CONTAINER = '/app/notification_exclusions.json'

def load_notification_data() -> List[Dict[str, Any]]:
    """通知データを読み込み"""
    # 複数のパスを試す
    file_paths = [NOTIFICATION_DATA_FILE, NOTIFICATION_DATA_FILE_CONTAINER]
    
    for file_path in file_paths:
        try:
            # ファイルが存在し、かつディレクトリでないことを確認
            if os.path.exists(file_path) and os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    notifications = data.get('notifications', [])
                    logger.info(f"通知データ読み込み成功: {file_path} ({len(notifications)}件)")
                    return notifications
            elif os.path.exists(file_path) and os.path.isdir(file_path):
                logger.warning(f"通知データパスがディレクトリです（スキップ）: {file_path}")
                continue
        except Exception as e:
            logger.warning(f"通知データ読み込み試行失敗 ({file_path}): {e}")
            continue
    
    logger.warning(f"通知データファイルが見つかりません。試行したパス: {file_paths}")
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

def load_notification_exclusions() -> set:
    """通知除外リストを読み込み"""
    # 複数のパスを試す
    file_paths = [EXCLUSIONS_FILE, EXCLUSIONS_FILE_CONTAINER]
    
    for file_path in file_paths:
        try:
            # ファイルが存在し、かつディレクトリでないことを確認
            if os.path.exists(file_path) and os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    excluded_set = set(data.get('excluded_employee_ids', []))
                    logger.debug(f"除外リスト読み込み成功: {file_path} ({len(excluded_set)}件)")
                    return excluded_set
            elif os.path.exists(file_path) and os.path.isdir(file_path):
                logger.warning(f"除外リストパスがディレクトリです（スキップ）: {file_path}")
                continue
        except Exception as e:
            logger.warning(f"除外リスト読み込み試行失敗 ({file_path}): {e}")
            continue
    
    logger.debug("除外リストファイルが見つかりません（空のセットを返します）")
    return set()

def save_notification_exclusions(excluded_set: set):
    """通知除外リストを保存"""
    # 複数のパスを試す（最初に存在するパスに保存）
    file_paths = [EXCLUSIONS_FILE, EXCLUSIONS_FILE_CONTAINER]
    
    for file_path in file_paths:
        try:
            # パスがディレクトリの場合はスキップ
            if os.path.exists(file_path) and os.path.isdir(file_path):
                logger.warning(f"除外リスト保存パスがディレクトリです（スキップ）: {file_path}")
                continue
            
            # ディレクトリが存在するか確認
            dir_path = os.path.dirname(file_path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            data = {
                'excluded_employee_ids': list(excluded_set),
                'last_updated': datetime.now().isoformat()
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"通知除外リストを保存: {file_path} ({len(excluded_set)}件)")
            return
        except Exception as e:
            logger.warning(f"除外リスト保存試行失敗 ({file_path}): {e}")
            continue
    
    logger.error(f"除外リスト保存に失敗しました。試行したパス: {file_paths}")

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
        
        # デバッグログ
        logger.info(f"通知API: 全通知={len(all_notifications)}件, 除外リスト={len(excluded_employee_ids)}件, 除外対象={list(excluded_employee_ids)}")
        
        # フィルタリング
        filtered_notifications = []
        excluded_count = 0
        acknowledged_count = 0
        
        for notification in all_notifications:
            # 確認済みフィルター
            if not include_acknowledged and notification['id'] in acknowledged_notifications:
                acknowledged_count += 1
                continue
            
            # 従業員IDフィルター
            if employee_id and notification['employee_id'] != employee_id:
                continue
            
            # 除外リストフィルター（隠し機能）
            # employee_idを文字列に変換して比較（型の不一致を防ぐ）
            notification_emp_id = str(notification.get('employee_id', ''))
            # 除外リストも文字列セットに変換
            excluded_str_set = {str(emp_id) for emp_id in excluded_employee_ids}
            if notification_emp_id in excluded_str_set:
                excluded_count += 1
                logger.debug(f"通知除外: employee_id={notification_emp_id} が除外リストに含まれています")
                continue
            
            filtered_notifications.append(notification)
        
        logger.info(f"通知API: 全{len(all_notifications)}件 → 確認済み{acknowledged_count}件, 除外{excluded_count}件 → 返却{len(filtered_notifications)}件 (employee_id={employee_id})")
        
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

@notification_bp.route('/api/notifications/exclusions', methods=['GET'])
def get_notification_exclusions():
    """通知除外リストを取得"""
    try:
        excluded_employee_ids = load_notification_exclusions()
        return jsonify({
            'status': 'success',
            'excluded_employee_ids': list(excluded_employee_ids)
        })
    except Exception as e:
        logger.error(f"通知除外リスト取得APIエラー: {e}")
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