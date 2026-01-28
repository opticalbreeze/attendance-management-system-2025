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
    # コンテナ内パスを優先（マウントされているパス）
    # docker-compose.ymlで /app/notification_exclusions.json にマウントされている
    # EXCLUSIONS_FILE (/app/../notification_exclusions.json) は間違ったパスになるため、コンテナ内パスを優先
    file_paths = [EXCLUSIONS_FILE_CONTAINER, EXCLUSIONS_FILE]
    
    # デバッグ: 実際のパスを確認
    logger.info(f"[除外リスト読み込み] 試行パス1: {EXCLUSIONS_FILE} (存在: {os.path.exists(EXCLUSIONS_FILE)}, ファイル: {os.path.isfile(EXCLUSIONS_FILE) if os.path.exists(EXCLUSIONS_FILE) else False})")
    logger.info(f"[除外リスト読み込み] 試行パス2: {EXCLUSIONS_FILE_CONTAINER} (存在: {os.path.exists(EXCLUSIONS_FILE_CONTAINER)}, ファイル: {os.path.isfile(EXCLUSIONS_FILE_CONTAINER) if os.path.exists(EXCLUSIONS_FILE_CONTAINER) else False})")
    logger.info(f"[除外リスト読み込み] __file__: {__file__}, os.path.dirname(__file__): {os.path.dirname(__file__)}")
    
    loaded_data = None
    loaded_path = None
    
    for file_path in file_paths:
        try:
            # ファイルが存在し、かつディレクトリでないことを確認
            if os.path.exists(file_path) and os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    excluded_list = data.get('excluded_employee_ids', [])
                    # 文字列セットに変換（型の不一致を防ぐ）
                    excluded_set = {str(emp_id) for emp_id in excluded_list}
                    logger.info(f"除外リスト読み込み成功: {file_path} ({len(excluded_set)}件) - 除外対象: {list(excluded_set)}")
                    loaded_data = excluded_set
                    loaded_path = file_path
                    # 最初に見つかったファイルを優先
                    break
            elif os.path.exists(file_path) and os.path.isdir(file_path):
                logger.warning(f"除外リストパスがディレクトリです（スキップ）: {file_path}")
                continue
            else:
                logger.debug(f"除外リストファイルが存在しません: {file_path}")
        except json.JSONDecodeError as e:
            logger.error(f"除外リストJSON解析エラー ({file_path}): {e}")
            continue
        except Exception as e:
            logger.warning(f"除外リスト読み込み試行失敗 ({file_path}): {e}", exc_info=True)
            continue
    
    if loaded_data is not None:
        # ファイルは既にマウントされているため、同期は不要
        # docker-compose.ymlとdocker-compose.dev.ymlで同じホスト側ファイルをマウントしている
        logger.info(f"除外リスト読み込み完了: {len(loaded_data)}件 (読み込み元: {loaded_path})")
        return loaded_data
    
    # ファイルが存在しない場合は空のファイルを作成（初期化）
    logger.info(f"除外リストファイルが見つかりません。空のファイルを作成します。試行したパス: {file_paths}")
    empty_set = set()
    # 両方のパスに空のファイルを作成
    for file_path in file_paths:
        try:
            if sync_exclusions_file(empty_set, file_path):
                logger.info(f"空の除外リストファイルを作成: {file_path}")
                break
        except Exception as e:
            logger.warning(f"空の除外リストファイル作成失敗 ({file_path}): {e}")
            continue
    
    return empty_set

def sync_exclusions_file(excluded_set: set, target_path: str):
    """除外リストファイルを同期（内部関数）"""
    try:
        # パスがディレクトリの場合はスキップ
        if os.path.exists(target_path) and os.path.isdir(target_path):
            logger.warning(f"除外リスト同期パスがディレクトリです（スキップ）: {target_path}")
            return False
        
        # ディレクトリが存在するか確認
        dir_path = os.path.dirname(target_path)
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
                logger.info(f"除外リスト保存: ディレクトリ作成成功: {dir_path}")
            except Exception as e:
                logger.error(f"除外リスト保存: ディレクトリ作成失敗 ({dir_path}): {e}")
                return False
        
        # ファイルを保存
        data = {
            'excluded_employee_ids': list(excluded_set),
            'last_updated': datetime.now().isoformat()
        }
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"除外リスト同期成功: {target_path} ({len(excluded_set)}件) - 除外対象: {list(excluded_set)}")
        return True
    except PermissionError as e:
        logger.error(f"除外リスト同期失敗（権限エラー） ({target_path}): {e}")
        return False
    except Exception as e:
        logger.error(f"除外リスト同期失敗 ({target_path}): {e}", exc_info=True)
        return False

def save_notification_exclusions(excluded_set: set):
    """通知除外リストを保存"""
    # docker-compose.ymlとdocker-compose.dev.ymlで同じホスト側ファイルをマウントしているため、
    # /app/notification_exclusions.json に保存すれば両方のコンテナで自動的に反映される
    # コンテナ内パス（/app/notification_exclusions.json）を優先して保存
    file_paths = [EXCLUSIONS_FILE_CONTAINER, EXCLUSIONS_FILE]
    
    saved_count = 0
    saved_paths = []
    for file_path in file_paths:
        if sync_exclusions_file(excluded_set, file_path):
            saved_count += 1
            saved_paths.append(file_path)
            logger.info(f"通知除外リストを保存: {file_path} ({len(excluded_set)}件) - 除外対象: {list(excluded_set)}")
            # マウントされているパスに保存できた場合は、それで十分（両方のコンテナで共有される）
            if file_path == EXCLUSIONS_FILE_CONTAINER:
                break
    
    if saved_count == 0:
        logger.error(f"除外リスト保存に失敗しました。試行したパス: {file_paths}")
    else:
        logger.info(f"除外リスト保存成功: {saved_count}箇所 - {', '.join(saved_paths)}")

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
        
        # フィルタリング
        filtered_notifications = []
        excluded_count = 0
        acknowledged_count = 0
        
        # 除外リストを文字列セットに変換（一度だけ実行）
        excluded_str_set = {str(emp_id) for emp_id in excluded_employee_ids} if excluded_employee_ids else set()
        logger.info(f"[通知API] 除外リスト（文字列セット）: {excluded_str_set}")
        
        for notification in all_notifications:
            notification_emp_id = str(notification.get('employee_id', ''))
            notification_emp_name = notification.get('employee_name', '不明')
            
            # 確認済みフィルター
            if not include_acknowledged and notification['id'] in acknowledged_notifications:
                acknowledged_count += 1
                continue
            
            # 従業員IDフィルター
            if employee_id and notification['employee_id'] != employee_id:
                continue
            
            # 除外リストフィルター（除外リストが空でない場合のみチェック）
            if excluded_str_set:
                if notification_emp_id in excluded_str_set:
                    excluded_count += 1
                    logger.info(f"[通知API] 通知除外実行: employee_id={notification_emp_id} ({notification_emp_name}) が除外リストに含まれています")
                    continue
                else:
                    logger.debug(f"[通知API] 通知通過: employee_id={notification_emp_id} ({notification_emp_name}) は除外リストに含まれていません")
            
            filtered_notifications.append(notification)
        
        logger.info(f"[通知API] フィルタリング結果: 全{len(all_notifications)}件 → 確認済み{acknowledged_count}件, 除外{excluded_count}件 → 返却{len(filtered_notifications)}件")
        if employee_id:
            logger.info(f"[通知API] クライアントPC用リクエスト: employee_id={employee_id} の通知={len([n for n in filtered_notifications if str(n.get('employee_id', '')) == str(employee_id)])}件")
        
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