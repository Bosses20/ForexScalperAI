"""
Backup Manager for the Forex Trading Bot
Handles automated backup procedures for configuration, data, and databases
"""

import os
import re
import shutil
import subprocess
import tarfile
import hashlib
import time
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
import tempfile
import threading
import schedule

from src.monitoring.alert_manager import AlertManager

logger = logging.getLogger(__name__)


class BackupManager:
    """
    Manages backup procedures for the Forex Trading Bot
    Provides both scheduled and on-demand backup capabilities
    """
    
    def __init__(self, config: dict, alert_manager: Optional[AlertManager] = None):
        """
        Initialize the backup manager
        
        Args:
            config: Configuration dictionary with backup settings
            alert_manager: Optional alert manager for notifications
        """
        self.config = config
        self.alert_manager = alert_manager
        
        # Set paths from config with defaults
        self.app_dir = config.get('app_dir', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
        self.backup_dir = config.get('backup_dir', os.path.join(self.app_dir, 'backups'))
        self.temp_dir = config.get('temp_dir', os.path.join(tempfile.gettempdir(), 'forex_bot_backup'))
        
        # Backup settings
        self.retention_days = config.get('backup_retention_days', 30)
        self.backup_frequency = config.get('backup_frequency', 'daily')
        self.max_backup_size = config.get('max_backup_size_mb', 500) * 1024 * 1024  # Convert to bytes
        
        # Secure offsite storage settings
        self.use_s3 = config.get('use_s3_backup', False)
        self.s3_bucket = config.get('s3_bucket', 's3://trading-bot-backups')
        self.s3_region = config.get('s3_region', 'us-east-1')
        
        # Components to backup
        self.backup_components = config.get('backup_components', {
            'config': True,
            'data': True,
            'database': True,
            'logs': True
        })
        
        # Create backup directory if it doesn't exist
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Schedule backups based on frequency setting
        self._scheduler_thread = None
        self._schedule_backups()
        
        logger.info(f"Backup Manager initialized with backup directory: {self.backup_dir}")
    
    def _schedule_backups(self) -> None:
        """
        Set up scheduled backups based on frequency setting
        """
        if self.backup_frequency == 'hourly':
            schedule.every().hour.do(self.perform_backup)
        elif self.backup_frequency == 'daily':
            schedule.every().day.at("01:00").do(self.perform_backup)  # Run at 1 AM
        elif self.backup_frequency == 'weekly':
            schedule.every().monday.at("01:00").do(self.perform_backup)  # Run at 1 AM on Monday
        else:
            logger.warning(f"Unknown backup frequency: {self.backup_frequency}, defaulting to daily")
            schedule.every().day.at("01:00").do(self.perform_backup)
        
        # Start the scheduler in a separate thread
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        self._scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self._scheduler_thread.start()
        
        logger.info(f"Scheduled automatic backups with frequency: {self.backup_frequency}")
    
    def perform_backup(self) -> Tuple[bool, str]:
        """
        Perform a full backup of the system
        
        Returns:
            Tuple of (success, message)
        """
        try:
            backup_start_time = time.time()
            logger.info("Starting backup process...")
            
            if self.alert_manager:
                self.alert_manager.send_alert(
                    level="info",
                    title="Backup Started",
                    message="The system backup process has started."
                )
            
            # Create a unique backup ID with timestamp
            backup_id = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_name = f"forex-trading-bot-backup-{backup_id}"
            
            # Create a temporary directory for the backup
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            os.makedirs(self.temp_dir, exist_ok=True)
            
            # Backup each component as configured
            components_backed_up = []
            
            # Backup config files
            if self.backup_components.get('config', True):
                config_dir = os.path.join(self.app_dir, 'config')
                if os.path.exists(config_dir):
                    backup_config_dir = os.path.join(self.temp_dir, 'config')
                    os.makedirs(backup_config_dir, exist_ok=True)
                    self._copy_files(config_dir, backup_config_dir)
                    components_backed_up.append('config')
                    logger.info("Configuration files backed up successfully")
            
            # Backup data files
            if self.backup_components.get('data', True):
                data_dir = os.path.join(self.app_dir, 'data')
                if os.path.exists(data_dir):
                    backup_data_dir = os.path.join(self.temp_dir, 'data')
                    os.makedirs(backup_data_dir, exist_ok=True)
                    self._copy_files(data_dir, backup_data_dir)
                    components_backed_up.append('data')
                    logger.info("Data files backed up successfully")
            
            # Backup database files
            if self.backup_components.get('database', True):
                db_dir = os.path.join(self.app_dir, 'database')
                if os.path.exists(db_dir):
                    backup_db_dir = os.path.join(self.temp_dir, 'database')
                    os.makedirs(backup_db_dir, exist_ok=True)
                    self._copy_files(db_dir, backup_db_dir)
                    components_backed_up.append('database')
                    logger.info("Database files backed up successfully")
            
            # Backup log files
            if self.backup_components.get('logs', True):
                log_dir = os.path.join(self.app_dir, 'logs')
                if os.path.exists(log_dir):
                    backup_log_dir = os.path.join(self.temp_dir, 'logs')
                    os.makedirs(backup_log_dir, exist_ok=True)
                    self._copy_files(log_dir, backup_log_dir)
                    components_backed_up.append('logs')
                    logger.info("Log files backed up successfully")
            
            # Create a metadata file with backup information
            metadata = {
                'backup_id': backup_id,
                'created_at': datetime.now().isoformat(),
                'components': components_backed_up,
                'forex_bot_version': self.config.get('version', 'unknown'),
                'backup_description': f"Automated backup of {', '.join(components_backed_up)}"
            }
            
            with open(os.path.join(self.temp_dir, 'backup-metadata.json'), 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Create the backup archive
            backup_file = os.path.join(self.backup_dir, f"{backup_name}.tar.gz")
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(self.temp_dir, arcname=".")
            
            # Calculate checksum
            checksum = self._calculate_checksum(backup_file)
            checksum_file = f"{backup_file}.sha256"
            with open(checksum_file, 'w') as f:
                f.write(f"{checksum}  {os.path.basename(backup_file)}")
            
            # Verify the backup
            if not self._verify_backup(backup_file):
                raise Exception("Backup verification failed")
            
            # Upload to S3 if configured
            if self.use_s3:
                self._upload_to_s3(backup_file, checksum_file)
            
            # Clean up old backups
            self._cleanup_old_backups()
            
            # Clean up temporary directory
            shutil.rmtree(self.temp_dir)
            
            backup_duration = time.time() - backup_start_time
            success_message = f"Backup completed successfully in {backup_duration:.1f} seconds. Backup file: {os.path.basename(backup_file)}"
            logger.info(success_message)
            
            if self.alert_manager:
                self.alert_manager.send_alert(
                    level="info",
                    title="Backup Completed",
                    message=success_message
                )
            
            return True, success_message
            
        except Exception as e:
            error_message = f"Backup failed: {str(e)}"
            logger.error(error_message)
            
            if self.alert_manager:
                self.alert_manager.send_alert(
                    level="high",
                    title="Backup Failed",
                    message=error_message
                )
            
            # Clean up temporary directory if it exists
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                
            return False, error_message
    
    def restore_backup(self, backup_file: str, components: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Restore system from a backup file
        
        Args:
            backup_file: Path to the backup file to restore
            components: Optional list of components to restore (if None, restore all)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if not os.path.exists(backup_file):
                return False, f"Backup file not found: {backup_file}"
            
            logger.info(f"Starting restore process from {backup_file}...")
            
            if self.alert_manager:
                self.alert_manager.send_alert(
                    level="medium",
                    title="Restore Started",
                    message=f"Restoring system from backup: {os.path.basename(backup_file)}"
                )
            
            # Verify the backup before restoring
            if not self._verify_backup(backup_file):
                return False, "Backup verification failed, cannot restore"
            
            # Create a temporary directory for restoration
            restore_temp_dir = os.path.join(tempfile.gettempdir(), 'forex_bot_restore')
            if os.path.exists(restore_temp_dir):
                shutil.rmtree(restore_temp_dir)
            os.makedirs(restore_temp_dir, exist_ok=True)
            
            # Extract the backup
            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(path=restore_temp_dir)
            
            # Read metadata
            metadata_file = os.path.join(restore_temp_dir, 'backup-metadata.json')
            if not os.path.exists(metadata_file):
                return False, "Invalid backup: missing metadata file"
                
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Determine which components to restore
            available_components = metadata.get('components', [])
            if components is None:
                # Restore all available components
                components_to_restore = available_components
            else:
                # Restore only specified components if they exist in the backup
                components_to_restore = [c for c in components if c in available_components]
            
            if not components_to_restore:
                return False, "No valid components to restore"
            
            # Restore each component
            restored_components = []
            
            # Create a backup of current state before restoring
            current_state_backup = os.path.join(self.backup_dir, f"pre-restore-{datetime.now().strftime('%Y%m%d-%H%M%S')}.tar.gz")
            logger.info(f"Creating backup of current state before restore: {current_state_backup}")
            self.perform_backup()
            
            # Perform the restoration for each component
            for component in components_to_restore:
                source_dir = os.path.join(restore_temp_dir, component)
                target_dir = os.path.join(self.app_dir, component)
                
                if not os.path.exists(source_dir):
                    logger.warning(f"Component directory {component} not found in backup")
                    continue
                
                if os.path.exists(target_dir):
                    # Create a backup of the component before replacing
                    backup_target_dir = os.path.join(restore_temp_dir, f"original_{component}")
                    shutil.copytree(target_dir, backup_target_dir)
                    
                    # Delete existing directory contents
                    shutil.rmtree(target_dir)
                
                # Create the target directory and copy files
                os.makedirs(target_dir, exist_ok=True)
                self._copy_files(source_dir, target_dir)
                restored_components.append(component)
                logger.info(f"Component {component} restored successfully")
            
            # Clean up temporary directory
            shutil.rmtree(restore_temp_dir)
            
            success_message = f"Restore completed successfully. Restored components: {', '.join(restored_components)}"
            logger.info(success_message)
            
            if self.alert_manager:
                self.alert_manager.send_alert(
                    level="info",
                    title="Restore Completed",
                    message=success_message
                )
            
            return True, success_message
            
        except Exception as e:
            error_message = f"Restore failed: {str(e)}"
            logger.error(error_message)
            
            if self.alert_manager:
                self.alert_manager.send_alert(
                    level="high",
                    title="Restore Failed",
                    message=error_message
                )
            
            # Clean up temporary directory if it exists
            restore_temp_dir = os.path.join(tempfile.gettempdir(), 'forex_bot_restore')
            if os.path.exists(restore_temp_dir):
                shutil.rmtree(restore_temp_dir)
                
            return False, error_message
    
    def list_backups(self) -> List[Dict]:
        """
        List all available backups with metadata
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        backup_files = [f for f in os.listdir(self.backup_dir) 
                      if f.startswith("forex-trading-bot-backup-") and f.endswith(".tar.gz")]
        
        for backup_file in sorted(backup_files, reverse=True):
            file_path = os.path.join(self.backup_dir, backup_file)
            
            # Extract date from filename
            match = re.search(r'forex-trading-bot-backup-(\d{8}-\d{6})\.tar\.gz', backup_file)
            if not match:
                continue
                
            date_str = match.group(1)
            timestamp = datetime.strptime(date_str, "%Y%m%d-%H%M%S")
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Check if checksum file exists
            checksum_file = f"{file_path}.sha256"
            has_checksum = os.path.exists(checksum_file)
            
            # Try to extract metadata (without extracting the entire archive)
            metadata = self._extract_backup_metadata(file_path)
            
            backups.append({
                'filename': backup_file,
                'path': file_path,
                'created_at': timestamp.isoformat(),
                'size': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2),
                'has_checksum': has_checksum,
                'components': metadata.get('components', []) if metadata else [],
                'description': metadata.get('backup_description', '') if metadata else '',
                'forex_bot_version': metadata.get('forex_bot_version', 'unknown') if metadata else 'unknown'
            })
        
        return backups
    
    def _copy_files(self, source_dir: str, target_dir: str) -> None:
        """
        Copy files from source to target directory
        
        Args:
            source_dir: Source directory path
            target_dir: Target directory path
        """
        if not os.path.exists(source_dir):
            return
            
        # Create target directory if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)
        
        # Copy all files and subdirectories
        for item in os.listdir(source_dir):
            source_item = os.path.join(source_dir, item)
            target_item = os.path.join(target_dir, item)
            
            if os.path.isdir(source_item):
                # Recursively copy subdirectory
                shutil.copytree(source_item, target_item, dirs_exist_ok=True)
            else:
                # Copy file
                shutil.copy2(source_item, target_item)
    
    def _calculate_checksum(self, file_path: str) -> str:
        """
        Calculate SHA-256 checksum of a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA-256 checksum as hexadecimal string
        """
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files
            chunk = f.read(65536)
            while chunk:
                hasher.update(chunk)
                chunk = f.read(65536)
        return hasher.hexdigest()
    
    def _verify_backup(self, backup_file: str) -> bool:
        """
        Verify a backup file integrity
        
        Args:
            backup_file: Path to the backup file
            
        Returns:
            True if backup is valid, False otherwise
        """
        try:
            # Check if file exists
            if not os.path.exists(backup_file):
                logger.error(f"Backup file not found: {backup_file}")
                return False
            
            # Check if it's a valid tarfile
            if not tarfile.is_tarfile(backup_file):
                logger.error(f"Invalid backup file format: {backup_file}")
                return False
            
            # Try to read the content
            with tarfile.open(backup_file, "r:gz") as tar:
                # Verify that metadata file exists
                try:
                    tar.getmember('./backup-metadata.json')
                except KeyError:
                    logger.error(f"Missing metadata in backup: {backup_file}")
                    return False
            
            # Verify checksum if available
            checksum_file = f"{backup_file}.sha256"
            if os.path.exists(checksum_file):
                with open(checksum_file, 'r') as f:
                    stored_checksum = f.read().split()[0]
                
                calculated_checksum = self._calculate_checksum(backup_file)
                if stored_checksum != calculated_checksum:
                    logger.error(f"Checksum mismatch for {backup_file}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying backup {backup_file}: {str(e)}")
            return False
    
    def _upload_to_s3(self, backup_file: str, checksum_file: str) -> bool:
        """
        Upload backup and checksum files to S3
        
        Args:
            backup_file: Path to the backup file
            checksum_file: Path to the checksum file
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            logger.info(f"Uploading backup to S3 bucket: {self.s3_bucket}")
            
            # Use AWS CLI for upload
            s3_backup_path = f"{self.s3_bucket}/{os.path.basename(backup_file)}"
            s3_checksum_path = f"{self.s3_bucket}/{os.path.basename(checksum_file)}"
            
            # Upload backup file
            result = subprocess.run(
                ["aws", "s3", "cp", backup_file, s3_backup_path, "--region", self.s3_region],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to upload backup to S3: {result.stderr}")
                return False
            
            # Upload checksum file
            result = subprocess.run(
                ["aws", "s3", "cp", checksum_file, s3_checksum_path, "--region", self.s3_region],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to upload checksum to S3: {result.stderr}")
                return False
            
            logger.info("Backup successfully uploaded to S3")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading backup to S3: {str(e)}")
            return False
    
    def _cleanup_old_backups(self) -> None:
        """
        Remove backups older than retention period
        """
        try:
            logger.info(f"Cleaning up backups older than {self.retention_days} days")
            
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            backup_files = [f for f in os.listdir(self.backup_dir) 
                          if f.startswith("forex-trading-bot-backup-") and f.endswith(".tar.gz")]
            
            for backup_file in backup_files:
                match = re.search(r'forex-trading-bot-backup-(\d{8}-\d{6})\.tar\.gz', backup_file)
                if not match:
                    continue
                    
                date_str = match.group(1)
                timestamp = datetime.strptime(date_str, "%Y%m%d-%H%M%S")
                
                if timestamp < cutoff_date:
                    # Remove backup file
                    file_path = os.path.join(self.backup_dir, backup_file)
                    os.remove(file_path)
                    logger.info(f"Removed old backup: {backup_file}")
                    
                    # Remove checksum file if it exists
                    checksum_file = f"{file_path}.sha256"
                    if os.path.exists(checksum_file):
                        os.remove(checksum_file)
                        
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {str(e)}")
    
    def _extract_backup_metadata(self, backup_file: str) -> Optional[Dict]:
        """
        Extract and return metadata from a backup file without extracting the entire archive
        
        Args:
            backup_file: Path to the backup file
            
        Returns:
            Metadata dictionary or None if extraction failed
        """
        try:
            with tarfile.open(backup_file, "r:gz") as tar:
                try:
                    metadata_member = tar.getmember('./backup-metadata.json')
                    metadata_file = tar.extractfile(metadata_member)
                    if metadata_file:
                        metadata_content = metadata_file.read().decode('utf-8')
                        return json.loads(metadata_content)
                except (KeyError, json.JSONDecodeError):
                    pass
            return None
            
        except Exception:
            return None
                        
    def shutdown(self) -> None:
        """
        Perform cleanup and shutdown operations
        """
        logger.info("Shutting down backup manager")
        
        # Perform a final backup if configured
        if self.config.get('backup_on_shutdown', True):
            logger.info("Performing final backup before shutdown")
            self.perform_backup()
