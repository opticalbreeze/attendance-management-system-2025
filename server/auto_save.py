#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動ファイル保存機能
データベースバックアップとレポートの自動保存を管理
"""

import os
import shutil
import sqlite3
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
import schedule
import time
import threading
import traceback

from config import Config
from utils import get_db_connection
from logger_config import setup_logger

logger = setup_logger(__name__)

# 保存先設定（デュアルバックアップ対応）
BACKUP_BASE_DIR_PRIMARY = "C:/AttendanceBackup"
BACKUP_BASE_DIR_SECONDARY = "D:/AttendanceBackup_Mirror"

# プライマリ保存先
DAILY_BACKUP_DIR = os.path.join(BACKUP_BASE_DIR_PRIMARY, "daily")
WEEKLY_BACKUP_DIR = os.path.join(BACKUP_BASE_DIR_PRIMARY, "weekly") 
MONTHLY_BACKUP_DIR = os.path.join(BACKUP_BASE_DIR_PRIMARY, "monthly")
REPORTS_BACKUP_DIR = os.path.join(BACKUP_BASE_DIR_PRIMARY, "reports")

# セカンダリ保存先（Dドライブミラー）
DAILY_BACKUP_DIR_D = os.path.join(BACKUP_BASE_DIR_SECONDARY, "daily")
WEEKLY_BACKUP_DIR_D = os.path.join(BACKUP_BASE_DIR_SECONDARY, "weekly")
MONTHLY_BACKUP_DIR_D = os.path.join(BACKUP_BASE_DIR_SECONDARY, "monthly")
REPORTS_BACKUP_DIR_D = os.path.join(BACKUP_BASE_DIR_SECONDARY, "reports")

class AutoSaveManager:
    """自動保存管理クラス"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.d_drive_available = self._check_d_drive()
        self._create_backup_directories()
        
    def _check_d_drive(self):
        """Dドライブの利用可能性をチェック"""
        try:
            d_drive_path = "D:/"
            if os.path.exists(d_drive_path):
                # テストファイル作成でアクセス権確認
                test_file = os.path.join(d_drive_path, "test_write_access.tmp")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                logger.info("Dドライブが利用可能です")
                return True
            else:
                logger.warning("Dドライブが見つかりません")
                return False
        except Exception as e:
            logger.warning(f"Dドライブアクセス不可: {e}")
            return False
        
    def _create_backup_directories(self):
        """バックアップディレクトリを作成"""
        try:
            # プライマリ（Cドライブ）
            primary_dirs = [DAILY_BACKUP_DIR, WEEKLY_BACKUP_DIR, MONTHLY_BACKUP_DIR, REPORTS_BACKUP_DIR]
            for directory in primary_dirs:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"バックアップディレクトリ作成: {directory}")
            
            # セカンダリ（Dドライブ）
            if self.d_drive_available:
                secondary_dirs = [DAILY_BACKUP_DIR_D, WEEKLY_BACKUP_DIR_D, MONTHLY_BACKUP_DIR_D, REPORTS_BACKUP_DIR_D]
                for directory in secondary_dirs:
                    os.makedirs(directory, exist_ok=True)
                    logger.info(f"ミラーディレクトリ作成: {directory}")
            
        except Exception as e:
            logger.error(f"バックアップディレクトリ作成エラー: {e}")
    
    def backup_database(self, backup_type="daily"):
        """データベースバックアップを実行（デュアル保存）"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # バックアップファイル名とディレクトリ設定
            if backup_type == "daily":
                backup_dir = DAILY_BACKUP_DIR
                backup_dir_d = DAILY_BACKUP_DIR_D
                filename = f"attendance_daily_{timestamp}.db"
            elif backup_type == "weekly":
                backup_dir = WEEKLY_BACKUP_DIR
                backup_dir_d = WEEKLY_BACKUP_DIR_D
                filename = f"attendance_weekly_{timestamp}.db"
            elif backup_type == "monthly":
                backup_dir = MONTHLY_BACKUP_DIR
                backup_dir_d = MONTHLY_BACKUP_DIR_D
                filename = f"attendance_monthly_{timestamp}.db"
            else:
                backup_dir = DAILY_BACKUP_DIR
                backup_dir_d = DAILY_BACKUP_DIR_D
                filename = f"attendance_manual_{timestamp}.db"
            
            if not os.path.exists(Config.DATABASE_PATH):
                logger.warning(f"データベースファイルが見つかりません: {Config.DATABASE_PATH}")
                return None
            
            # プライマリバックアップ（Cドライブ）
            primary_path = os.path.join(backup_dir, filename)
            shutil.copy2(Config.DATABASE_PATH, primary_path)
            
            # 圧縮保存
            primary_zip = primary_path.replace('.db', '.zip')
            with zipfile.ZipFile(primary_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(primary_path, filename)
            os.remove(primary_path)
            
            logger.info(f"プライマリバックアップ完了: {primary_zip}")
            
            # セカンダリバックアップ（Dドライブ）
            secondary_zip = None
            if self.d_drive_available:
                try:
                    secondary_path = os.path.join(backup_dir_d, filename)
                    shutil.copy2(Config.DATABASE_PATH, secondary_path)
                    
                    secondary_zip = secondary_path.replace('.db', '.zip')
                    with zipfile.ZipFile(secondary_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(secondary_path, filename)
                    os.remove(secondary_path)
                    
                    logger.info(f"セカンダリバックアップ完了: {secondary_zip}")
                except Exception as e:
                    logger.error(f"Dドライブバックアップエラー: {e}")
                    # Cドライブは成功しているので、処理は続行
            
            # ファイルサイズをログ出力
            file_size = os.path.getsize(primary_zip) / 1024  # KB
            logger.info(f"バックアップファイルサイズ: {file_size:.2f} KB")
            
            return primary_zip
                
        except Exception as e:
            logger.error(f"データベースバックアップエラー: {e}")
            traceback.print_exc()
            return None
    
    def backup_reports_data(self):
        """レポートデータをエクスポート（デュアル保存）"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_dir = os.path.join(REPORTS_BACKUP_DIR, f"reports_{timestamp}")
            os.makedirs(report_dir, exist_ok=True)
            
            # 各種データをCSV形式でエクスポート
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 従業員データ
                cursor.execute("SELECT * FROM employee_master")
                employees = cursor.fetchall()
                employee_file = os.path.join(report_dir, "employees.csv")
                self._write_csv(employee_file, employees, ['employee_num', 'name', 'section', 'idm'])
                
                # スケジュールデータ（過去1ヶ月）
                one_month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                cursor.execute("SELECT * FROM attend_schedule WHERE work_date >= ?", (one_month_ago,))
                schedules = cursor.fetchall()
                schedule_file = os.path.join(report_dir, "schedules.csv")
                self._write_csv(schedule_file, schedules, ['id', 'employee_id', 'work_date', 'work_type', 'start_time', 'end_time'])
                
                # 打刻データ（過去1ヶ月）
                cursor.execute("SELECT * FROM attendance WHERE DATE(timestamp) >= ?", (one_month_ago,))
                attendance = cursor.fetchall()
                attendance_file = os.path.join(report_dir, "attendance.csv")
                self._write_csv(attendance_file, attendance, ['id', 'idm', 'timestamp', 'terminal_id', 'received_at'])
                
                # プライマリ圧縮保存（Cドライブ）
                primary_zip = report_dir + '.zip'
                with zipfile.ZipFile(primary_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(report_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arc_path = os.path.relpath(file_path, report_dir)
                            zipf.write(file_path, arc_path)
                
                logger.info(f"プライマリレポートバックアップ完了: {primary_zip}")
                
                # セカンダリ保存（Dドライブ）
                if self.d_drive_available:
                    try:
                        secondary_dir = os.path.join(REPORTS_BACKUP_DIR_D, f"reports_{timestamp}")
                        secondary_zip = secondary_dir + '.zip'
                        shutil.copy2(primary_zip, secondary_zip)
                        logger.info(f"セカンダリレポートバックアップ完了: {secondary_zip}")
                    except Exception as e:
                        logger.error(f"Dドライブレポートバックアップエラー: {e}")
                
                # 元のディレクトリを削除
                shutil.rmtree(report_dir)
                
                return primary_zip
                
        except Exception as e:
            logger.error(f"レポートバックアップエラー: {e}")
            traceback.print_exc()
            return None
    
    def _write_csv(self, filepath, data, headers):
        """CSVファイルに書き込み"""
        import csv
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                writer.writerows(data)
        except Exception as e:
            logger.error(f"CSV書き込みエラー ({filepath}): {e}")
    
    def cleanup_old_backups(self):
        """古いバックアップファイルを削除（デュアル対応）"""
        try:
            # プライマリ（Cドライブ）
            self._cleanup_directory(DAILY_BACKUP_DIR, days=30)
            self._cleanup_directory(WEEKLY_BACKUP_DIR, days=90)
            self._cleanup_directory(MONTHLY_BACKUP_DIR, days=365)
            self._cleanup_directory(REPORTS_BACKUP_DIR, days=60)
            
            # セカンダリ（Dドライブ）
            if self.d_drive_available:
                self._cleanup_directory(DAILY_BACKUP_DIR_D, days=30)
                self._cleanup_directory(WEEKLY_BACKUP_DIR_D, days=90)
                self._cleanup_directory(MONTHLY_BACKUP_DIR_D, days=365)
                self._cleanup_directory(REPORTS_BACKUP_DIR_D, days=60)
            
        except Exception as e:
            logger.error(f"古いバックアップ削除エラー: {e}")
    
    def _cleanup_directory(self, directory, days):
        """指定日数以上古いファイルを削除"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    filepath = os.path.join(directory, filename)
                    if os.path.isfile(filepath):
                        file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                        if file_time < cutoff_date:
                            os.remove(filepath)
                            logger.info(f"古いバックアップ削除: {filepath}")
        except Exception as e:
            logger.error(f"ディレクトリクリーンアップエラー ({directory}): {e}")
    
    def get_backup_status(self):
        """バックアップ状況を取得（デュアル対応）"""
        try:
            status = {
                'primary': {
                    'daily': self._get_directory_info(DAILY_BACKUP_DIR),
                    'weekly': self._get_directory_info(WEEKLY_BACKUP_DIR),
                    'monthly': self._get_directory_info(MONTHLY_BACKUP_DIR),
                    'reports': self._get_directory_info(REPORTS_BACKUP_DIR)
                },
                'd_drive_available': self.d_drive_available
            }
            
            if self.d_drive_available:
                status['secondary'] = {
                    'daily': self._get_directory_info(DAILY_BACKUP_DIR_D),
                    'weekly': self._get_directory_info(WEEKLY_BACKUP_DIR_D),
                    'monthly': self._get_directory_info(MONTHLY_BACKUP_DIR_D),
                    'reports': self._get_directory_info(REPORTS_BACKUP_DIR_D)
                }
            
            return status
        except Exception as e:
            logger.error(f"バックアップ状況取得エラー: {e}")
            return {}
    
    def _get_directory_info(self, directory):
        """ディレクトリの情報を取得"""
        try:
            if not os.path.exists(directory):
                return {'count': 0, 'total_size': 0, 'latest': None}
            
            files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
            total_size = sum(os.path.getsize(os.path.join(directory, f)) for f in files)
            
            latest = None
            if files:
                latest_file = max(files, key=lambda f: os.path.getctime(os.path.join(directory, f)))
                latest = datetime.fromtimestamp(os.path.getctime(os.path.join(directory, latest_file)))
            
            return {
                'count': len(files),
                'total_size': total_size,
                'latest': latest.isoformat() if latest else None
            }
        except Exception as e:
            logger.error(f"ディレクトリ情報取得エラー ({directory}): {e}")
            return {'count': 0, 'total_size': 0, 'latest': None}
    
    def start_scheduler(self):
        """スケジューラーを開始"""
        if self.running:
            return False
            
        try:
            # スケジュール設定
            schedule.clear()
            
            # 毎日午前3時にバックアップ
            schedule.every().day.at("03:00").do(self._daily_backup_job)
            
            # 毎週日曜日午前2時にバックアップ
            schedule.every().sunday.at("02:00").do(self._weekly_backup_job)
            
            # 毎月1日午前1時にバックアップ
            schedule.every().month.do(self._monthly_backup_job)
            
            # 毎日午前4時に古いファイル削除
            schedule.every().day.at("04:00").do(self.cleanup_old_backups)
            
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
            
            logger.info("自動バックアップスケジューラー開始")
            return True
            
        except Exception as e:
            logger.error(f"スケジューラー開始エラー: {e}")
            return False
    
    def stop_scheduler(self):
        """スケジューラーを停止"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        schedule.clear()
        logger.info("自動バックアップスケジューラー停止")
    
    def _run_scheduler(self):
        """スケジューラーのメインループ"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 1分間隔でチェック
            except Exception as e:
                logger.error(f"スケジューラー実行エラー: {e}")
                time.sleep(60)
    
    def _daily_backup_job(self):
        """日次バックアップジョブ"""
        logger.info("日次バックアップ開始")
        self.backup_database("daily")
        
    def _weekly_backup_job(self):
        """週次バックアップジョブ"""
        logger.info("週次バックアップ開始")
        self.backup_database("weekly")
        self.backup_reports_data()
        
    def _monthly_backup_job(self):
        """月次バックアップジョブ"""
        logger.info("月次バックアップ開始")
        self.backup_database("monthly")

# グローバルインスタンス
auto_save_manager = AutoSaveManager()