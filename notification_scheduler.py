#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
勤怠通知スケジューラー
毎日深夜2:00に実行して月度差異チェック
"""

import schedule
import time
import logging
import os
import sys
from datetime import datetime, timedelta
import subprocess

# パス設定
current_dir = os.path.dirname(os.path.abspath(__file__))

# ログ設定
log_file = os.path.join(current_dir, 'scheduler.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_monthly_check():
    """月度差異チェックを実行"""
    try:
        logger.info("月度差異チェック開始")
        
        # notification_system.pyを--check-onlyモードで実行
        script_path = os.path.join(current_dir, 'notification_system.py')
        result = subprocess.run(
            [sys.executable, script_path, '--check-only'],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            logger.info("月度差異チェック完了")
            logger.info(f"stdout: {result.stdout}")
            if result.stderr:
                logger.warning(f"stderr: {result.stderr}")
        else:
            logger.error(f"月度差異チェック失敗: returncode={result.returncode}")
            logger.error(f"stdout: {result.stdout}")
            logger.error(f"stderr: {result.stderr}")
            
    except Exception as e:
        logger.error(f"月度差異チェック実行エラー: {e}")

def main():
    """スケジューラーメイン処理"""
    logger.info("勤怠通知スケジューラー開始")
    
    # 毎日深夜2:00に実行
    schedule.every().day.at("02:00").do(run_monthly_check)
    
    # テスト用: 1分後にも実行（開発・検証用）
    test_time = (datetime.now() + timedelta(minutes=1)).strftime("%H:%M")
    schedule.every().day.at(test_time).do(run_monthly_check)
    logger.info(f"テスト実行予定: {test_time}")
    
    logger.info("スケジューラー開始 - 毎日深夜2:00に実行")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1分間隔でチェック
            
    except KeyboardInterrupt:
        logger.info("スケジューラー停止（キーボード割り込み）")
    except Exception as e:
        logger.error(f"スケジューラーエラー: {e}")

if __name__ == "__main__":
    main()