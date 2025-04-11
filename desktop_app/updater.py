#!/usr/bin/env python
"""
ForexScalperAI Desktop Application Updater

This module provides functionality to check for updates and apply them automatically.
Since the application is running locally without a cloud deployment, this updater
implements a simple file-based update mechanism that works with your local setup.
"""

import os
import sys
import json
import time
import shutil
import logging
import zipfile
import tempfile
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
import urllib.request
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), "updater.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ForexScalperAI-Updater")

# Constants
APP_VERSION = "1.0.0"  # Current version
UPDATE_CHECK_INTERVAL = 3600  # Check for updates every hour
LOCAL_UPDATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "updates")
VERSION_FILE = os.path.join(LOCAL_UPDATE_DIR, "version.json")


class Updater:
    """
    Handles checking for and applying updates to the desktop application.
    Implements a file-based update system compatible with local execution.
    """
    
    def __init__(self):
        """Initialize the updater"""
        self.current_version = APP_VERSION
        self.update_available = False
        self.update_info = None
        self.last_check_time = 0
        
        # Create updates directory if it doesn't exist
        os.makedirs(LOCAL_UPDATE_DIR, exist_ok=True)
        
        logger.info(f"Updater initialized. Current version: {self.current_version}")
    
    def check_for_updates(self, force=False):
        """
        Check for updates from the local update directory
        
        Args:
            force (bool): If True, force an update check regardless of the last check time
            
        Returns:
            bool: True if an update is available, False otherwise
        """
        # Skip check if the interval hasn't passed, unless forced
        current_time = time.time()
        if not force and (current_time - self.last_check_time) < UPDATE_CHECK_INTERVAL:
            return self.update_available
        
        self.last_check_time = current_time
        logger.info("Checking for updates...")
        
        try:
            # In a local environment, check the version file in the update directory
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, 'r') as f:
                    version_data = json.load(f)
                
                latest_version = version_data.get('version')
                if latest_version and self._is_newer_version(latest_version):
                    self.update_available = True
                    self.update_info = version_data
                    logger.info(f"Update available: v{latest_version}")
                    return True
                else:
                    logger.info(f"No updates available. Current version is {self.current_version}")
                    return False
            else:
                logger.info("No version file found in update directory")
                return False
        except Exception as e:
            logger.error(f"Error checking for updates: {str(e)}")
            return False
    
    def _is_newer_version(self, version):
        """
        Check if the given version is newer than the current version
        
        Args:
            version (str): Version to check
            
        Returns:
            bool: True if the version is newer, False otherwise
        """
        try:
            # Split version strings and convert to integers
            current_parts = [int(x) for x in self.current_version.split('.')]
            new_parts = [int(x) for x in version.split('.')]
            
            # Compare version components
            for i in range(max(len(current_parts), len(new_parts))):
                current_part = current_parts[i] if i < len(current_parts) else 0
                new_part = new_parts[i] if i < len(new_parts) else 0
                
                if new_part > current_part:
                    return True
                elif new_part < current_part:
                    return False
            
            # If we get here, versions are equal
            return False
        except Exception as e:
            logger.error(f"Error comparing versions: {str(e)}")
            return False
    
    def download_update(self):
        """
        Download the update package from the local update directory
        
        Returns:
            str: Path to the downloaded update package, or None if failed
        """
        if not self.update_available or not self.update_info:
            logger.warning("No update available to download")
            return None
        
        try:
            # In a local environment, the update package should already be in the update directory
            package_filename = self.update_info.get('package_filename')
            if not package_filename:
                logger.error("No package filename specified in version data")
                return None
            
            package_path = os.path.join(LOCAL_UPDATE_DIR, package_filename)
            if not os.path.exists(package_path):
                logger.error(f"Update package not found: {package_path}")
                return None
            
            # Verify package integrity if checksum is provided
            if 'checksum' in self.update_info:
                if not self._verify_checksum(package_path, self.update_info['checksum']):
                    logger.error("Update package checksum verification failed")
                    return None
            
            logger.info(f"Update package verified: {package_path}")
            return package_path
        except Exception as e:
            logger.error(f"Error downloading update: {str(e)}")
            return None
    
    def _verify_checksum(self, file_path, expected_checksum):
        """
        Verify the integrity of a file using its checksum
        
        Args:
            file_path (str): Path to the file to verify
            expected_checksum (str): Expected checksum
            
        Returns:
            bool: True if the checksum matches, False otherwise
        """
        try:
            # Calculate MD5 hash of the file
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            
            calculated_checksum = hash_md5.hexdigest()
            return calculated_checksum == expected_checksum
        except Exception as e:
            logger.error(f"Error verifying checksum: {str(e)}")
            return False
    
    def apply_update(self, package_path):
        """
        Apply the downloaded update package
        
        Args:
            package_path (str): Path to the update package
            
        Returns:
            bool: True if update was applied successfully, False otherwise
        """
        if not package_path or not os.path.exists(package_path):
            logger.error("Invalid update package path")
            return False
        
        # Create a temporary directory for the update
        temp_dir = tempfile.mkdtemp()
        
        try:
            logger.info(f"Extracting update package to {temp_dir}")
            
            # Extract the update package
            with zipfile.ZipFile(package_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Look for install script
            install_script = os.path.join(temp_dir, "install.py")
            if os.path.exists(install_script):
                logger.info("Running update install script")
                # Execute the install script
                result = subprocess.run(
                    [sys.executable, install_script],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    logger.error(f"Install script failed with exit code {result.returncode}")
                    logger.error(f"Output: {result.stdout}")
                    logger.error(f"Error: {result.stderr}")
                    return False
                
                logger.info("Install script completed successfully")
                return True
            else:
                # No install script, just copy the files
                logger.info("No install script found, copying files manually")
                return self._copy_update_files(temp_dir)
        except Exception as e:
            logger.error(f"Error applying update: {str(e)}")
            logger.error(traceback.format_exc())
            return False
        finally:
            # Clean up the temporary directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.error(f"Error cleaning up temporary directory: {str(e)}")
    
    def _copy_update_files(self, update_dir):
        """
        Copy files from the update directory to the application directory
        
        Args:
            update_dir (str): Path to the directory containing update files
            
        Returns:
            bool: True if files were copied successfully, False otherwise
        """
        try:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            desktop_app_dir = os.path.join(update_dir, "desktop_app")
            
            # Check if the update contains a desktop_app directory
            if os.path.exists(desktop_app_dir):
                source_dir = desktop_app_dir
            else:
                source_dir = update_dir
            
            logger.info(f"Copying update files from {source_dir} to {app_dir}")
            
            # Copy all files except the updater itself
            for item in os.listdir(source_dir):
                source_path = os.path.join(source_dir, item)
                dest_path = os.path.join(app_dir, item)
                
                # Skip updater.py to avoid conflicts
                if item == 'updater.py':
                    continue
                
                if os.path.isdir(source_path):
                    # If directory exists, remove it first
                    if os.path.exists(dest_path):
                        shutil.rmtree(dest_path)
                    shutil.copytree(source_path, dest_path)
                else:
                    # For files, just copy and replace
                    shutil.copy2(source_path, dest_path)
            
            logger.info("Update files copied successfully")
            return True
        except Exception as e:
            logger.error(f"Error copying update files: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def update(self, silent=False):
        """
        Check for and apply updates
        
        Args:
            silent (bool): If True, suppress user prompts and notifications
            
        Returns:
            bool: True if update was successful or no update was needed, False if update failed
        """
        try:
            # Check for updates
            if not self.check_for_updates():
                logger.info("No updates available")
                return True
            
            # Download update
            package_path = self.download_update()
            if not package_path:
                logger.error("Failed to download update")
                return False
            
            # Apply update
            if self.apply_update(package_path):
                logger.info(f"Update to v{self.update_info['version']} applied successfully")
                
                # Update current version
                self.current_version = self.update_info['version']
                self.update_available = False
                
                # Restart application if not silent
                if not silent:
                    logger.info("Restarting application")
                    self._restart_application()
                
                return True
            else:
                logger.error("Failed to apply update")
                return False
        except Exception as e:
            logger.error(f"Error updating application: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _restart_application(self):
        """Restart the application"""
        try:
            # Get path to main.py
            main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
            
            # Start new instance of the application
            subprocess.Popen([sys.executable, main_script])
            
            # Exit current instance
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error restarting application: {str(e)}")
    
    def create_update_package(self, version, files_or_dirs, output_dir=None):
        """
        Create an update package (for development purposes)
        
        Args:
            version (str): Version number for the update
            files_or_dirs (list): List of files or directories to include in the update
            output_dir (str): Directory to save the update package, defaults to LOCAL_UPDATE_DIR
            
        Returns:
            str: Path to the created update package, or None if failed
        """
        if output_dir is None:
            output_dir = LOCAL_UPDATE_DIR
        
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Create a temporary directory for the update files
            temp_dir = tempfile.mkdtemp()
            
            # Copy files to the temporary directory
            for path in files_or_dirs:
                if not os.path.exists(path):
                    logger.error(f"Path does not exist: {path}")
                    continue
                
                if os.path.isdir(path):
                    shutil.copytree(
                        path, 
                        os.path.join(temp_dir, os.path.basename(path)),
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc')
                    )
                else:
                    shutil.copy2(path, temp_dir)
            
            # Create the update package
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            package_filename = f"forexscalperai_update_v{version}_{timestamp}.zip"
            package_path = os.path.join(output_dir, package_filename)
            
            # Create zip file
            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
            
            # Calculate checksum
            hash_md5 = hashlib.md5()
            with open(package_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            checksum = hash_md5.hexdigest()
            
            # Create version file
            version_data = {
                "version": version,
                "package_filename": package_filename,
                "checksum": checksum,
                "release_date": datetime.now().isoformat(),
                "changes": ["Update package created by the developer"]
            }
            
            with open(os.path.join(output_dir, "version.json"), 'w') as f:
                json.dump(version_data, f, indent=4)
            
            logger.info(f"Update package created: {package_path}")
            return package_path
        except Exception as e:
            logger.error(f"Error creating update package: {str(e)}")
            return None
        finally:
            # Clean up the temporary directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.error(f"Error cleaning up temporary directory: {str(e)}")


# If run directly, create an update package
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python updater.py create <version> <file1> [file2 ...]")
        print("   or: python updater.py check")
        print("   or: python updater.py update")
        sys.exit(1)
    
    updater = Updater()
    
    if sys.argv[1] == "create":
        version = sys.argv[2]
        files = sys.argv[3:]
        
        if not files:
            print("Error: No files specified")
            sys.exit(1)
        
        package_path = updater.create_update_package(version, files)
        if package_path:
            print(f"Update package created: {package_path}")
        else:
            print("Failed to create update package")
            sys.exit(1)
    elif sys.argv[1] == "check":
        if updater.check_for_updates(force=True):
            print(f"Update available: v{updater.update_info['version']}")
            print(f"Changes: {updater.update_info.get('changes', ['No change log available'])}")
        else:
            print("No updates available")
    elif sys.argv[1] == "update":
        if updater.update():
            print("Update applied successfully")
        else:
            print("Failed to apply update")
            sys.exit(1)
    else:
        print(f"Unknown command: {sys.argv[1]}")
        sys.exit(1)
