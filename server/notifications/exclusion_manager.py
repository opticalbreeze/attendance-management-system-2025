#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
除外リスト管理モジュール
通知除外リストの読み込み、保存、同期を担当
データベースを優先的に使用し、ファイルベースとの互換性も保つ
"""

import json
import os
import shutil
from datetime import datetime
from typing import Set
from logger_config import setup_logger

logger = setup_logger(__name__)

# 通知関連ファイルパス（後方互換性のため保持）
EXCLUSIONS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'notification_exclusions.json')
EXCLUSIONS_FILE_CONTAINER = '/app/notification_exclusions.json'

def load_notification_exclusions() -> Set[str]:
    """
    通知除外リストを読み込み
    データベースを優先的に使用し、データがない場合はファイルから読み込んで移行
    """
    try:
        # データベースから読み込みを試行
        from database.dao.exclusion_dao import get_all_excluded_employee_ids
        excluded_set = get_all_excluded_employee_ids()
        
        if excluded_set:
            logger.info(f"除外リスト読み込み（DB）: {len(excluded_set)}件 - 除外対象: {list(excluded_set)}")
            return excluded_set
        
        # データベースにデータがない場合、ファイルから読み込んで移行
        logger.info("データベースに除外リストがありません。ファイルから読み込んで移行します。")
        file_paths = [EXCLUSIONS_FILE_CONTAINER, EXCLUSIONS_FILE]
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        excluded_list = data.get('excluded_employee_ids', [])
                        excluded_set = {str(emp_id) for emp_id in excluded_list}
                        
                        if excluded_set:
                            # データベースに移行
                            logger.info(f"ファイルから除外リストを読み込み: {file_path} ({len(excluded_set)}件)")
                            save_notification_exclusions(excluded_set)
                            logger.info(f"除外リストをデータベースに移行しました: {len(excluded_set)}件")
                            return excluded_set
                        else:
                            logger.info(f"ファイルから除外リストを読み込みましたが、空でした: {file_path}")
                            return set()
                            
                elif os.path.exists(file_path) and os.path.isdir(file_path):
                    logger.warning(f"除外リストパスがディレクトリです。削除してファイルを作成します: {file_path}")
                    try:
                        shutil.rmtree(file_path)
                        logger.info(f"除外リストディレクトリを削除しました: {file_path}")
                    except Exception as e:
                        logger.error(f"除外リストディレクトリ削除失敗 ({file_path}): {e}")
                    continue
                    
            except json.JSONDecodeError as e:
                logger.error(f"除外リストJSON解析エラー ({file_path}): {e}")
                continue
            except Exception as e:
                logger.warning(f"除外リスト読み込み試行失敗 ({file_path}): {e}", exc_info=True)
                continue
        
        # ファイルも見つからない場合は空のセットを返す
        logger.info("除外リストファイルが見つかりません。空のセットを返します。")
        return set()
        
    except Exception as e:
        logger.error(f"除外リスト読み込みエラー: {e}", exc_info=True)
        # エラーが発生した場合は空のセットを返す
        return set()

def save_notification_exclusions(excluded_set: Set[str]):
    """
    通知除外リストを保存
    データベースに保存し、ファイルにも同期（後方互換性のため）
    """
    try:
        # データベースに保存
        from database.dao.exclusion_dao import set_excluded_employee_ids
        if set_excluded_employee_ids(excluded_set):
            logger.info(f"除外リスト保存（DB）: {len(excluded_set)}件 - 除外対象: {list(excluded_set)}")
        else:
            logger.error("除外リストのデータベース保存に失敗しました")
        
        # ファイルにも同期（後方互換性のため）
        file_paths = [EXCLUSIONS_FILE_CONTAINER, EXCLUSIONS_FILE]
        saved_count = 0
        for file_path in file_paths:
            try:
                if sync_exclusions_file(excluded_set, file_path):
                    saved_count += 1
                    logger.debug(f"除外リストファイル同期: {file_path}")
                    if file_path == EXCLUSIONS_FILE_CONTAINER:
                        break
            except Exception as e:
                logger.warning(f"除外リストファイル同期失敗 ({file_path}): {e}")
                continue
        
        if saved_count > 0:
            logger.debug(f"除外リストファイル同期成功: {saved_count}箇所")
            
    except Exception as e:
        logger.error(f"除外リスト保存エラー: {e}", exc_info=True)

def sync_exclusions_file(excluded_set: Set[str], target_path: str) -> bool:
    """除外リストファイルを同期（内部関数、後方互換性のため）"""
    try:
        # パスがディレクトリの場合は削除してからファイルを作成
        if os.path.exists(target_path) and os.path.isdir(target_path):
            logger.warning(f"除外リスト同期パスがディレクトリです。削除してファイルを作成します: {target_path}")
            try:
                shutil.rmtree(target_path)
                logger.info(f"除外リストディレクトリを削除しました: {target_path}")
            except Exception as e:
                logger.error(f"除外リストディレクトリ削除失敗 ({target_path}): {e}")
                return False
        
        # ディレクトリが存在するか確認
        dir_path = os.path.dirname(target_path)
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
                logger.debug(f"除外リスト保存: ディレクトリ作成成功: {dir_path}")
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
        logger.debug(f"除外リスト同期成功: {target_path} ({len(excluded_set)}件)")
        return True
    except PermissionError as e:
        logger.error(f"除外リスト同期失敗（権限エラー） ({target_path}): {e}")
        return False
    except Exception as e:
        logger.error(f"除外リスト同期失敗 ({target_path}): {e}", exc_info=True)
        return False

def init_notification_files():
    """
    通知関連ファイルの初期化
    サーバー起動時に呼び出して、必要なファイルが存在することを保証する
    （後方互換性のため、ファイルの存在も確認）
    """
    try:
        # データベースから除外リストを読み込んで、ファイルに同期
        excluded_set = load_notification_exclusions()
        
        # ファイルの存在確認と初期化（後方互換性のため）
        file_paths = [EXCLUSIONS_FILE_CONTAINER, EXCLUSIONS_FILE]
        file_exists = False
        
        for file_path in file_paths:
            if os.path.exists(file_path):
                if os.path.isfile(file_path):
                    file_exists = True
                    logger.debug(f"除外リストファイル確認: {file_path} (存在)")
                    break
                elif os.path.isdir(file_path):
                    logger.warning(f"除外リストパスがディレクトリです。削除してファイルを作成します: {file_path}")
                    try:
                        shutil.rmtree(file_path)
                        logger.info(f"除外リストディレクトリを削除しました: {file_path}")
                        if sync_exclusions_file(excluded_set, file_path):
                            logger.info(f"除外リストファイルを作成: {file_path}")
                            file_exists = True
                            break
                    except Exception as e:
                        logger.error(f"除外リストディレクトリ削除失敗 ({file_path}): {e}")
        
        # ファイルが存在しない場合は作成
        if not file_exists:
            logger.info("除外リストファイルが見つかりません。データベースから同期して作成します。")
            for file_path in file_paths:
                try:
                    if sync_exclusions_file(excluded_set, file_path):
                        logger.info(f"除外リストファイルを作成: {file_path}")
                        break
                except Exception as e:
                    logger.warning(f"除外リストファイル作成失敗 ({file_path}): {e}")
                    continue
        
        logger.info("通知関連ファイルの初期化が完了しました")
    except Exception as e:
        logger.error(f"通知関連ファイルの初期化エラー: {e}", exc_info=True)
