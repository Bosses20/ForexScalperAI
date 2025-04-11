#!/usr/bin/env python
"""
ForexScalperAI Desktop Application

This desktop application provides a user-friendly wrapper around the 
ForexScalperAI trading bot, allowing for:
- One-click start/stop of the trading bot
- System tray integration for easy access
- Automatic startup with Windows
- Status monitoring and notifications
"""

import os
import sys
import time
import json
import signal
import logging
import subprocess
import threading
import webbrowser
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, 
                            QSystemTrayIcon, QMenu, QAction, QStyle, QWidget,
                            QVBoxLayout, QHBoxLayout, QGroupBox, QProgressBar,
                            QCheckBox, QComboBox, QFormLayout, QTabWidget,
                            QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSettings, QThread
from PyQt5.QtGui import QIcon, QFont, QPixmap

# Import the updater
from updater import Updater

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), "desktop_app.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
APP_NAME = "ForexScalperAI"
try:
    from version import __version__
    APP_VERSION = __version__
except ImportError:
    APP_VERSION = "1.0.0"
BOT_PROCESS = None
API_PROCESS = None
API_URL = "http://localhost:8000"

class BotThread(QThread):
    signal_status_update = pyqtSignal(dict)
    signal_error = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self.bot_process = None
        self.api_process = None
        self.project_root = self._get_project_root()
        
    def _get_project_root(self):
        """Get the root directory of the project"""
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def run(self):
        """Main thread execution"""
        self.running = True
        
        try:
            # Start the bot and API server process
            run_local_path = os.path.join(self.project_root, "run_local.py")
            
            logger.info(f"Starting bot from {run_local_path}")
            
            # Start the bot process with run_local.py
            self.bot_process = subprocess.Popen(
                [sys.executable, run_local_path],
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Monitor the bot process and emit updates
            while self.running:
                # Check if bot is still running
                if self.bot_process.poll() is not None:
                    self.signal_error.emit(f"Bot process exited with code {self.bot_process.returncode}")
                    break
                
                # Try to get the status from the API
                status = self._get_bot_status()
                if status:
                    self.signal_status_update.emit(status)
                
                # Sleep for a bit to avoid hammering CPU
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in bot thread: {str(e)}")
            self.signal_error.emit(f"Error: {str(e)}")
        finally:
            self._cleanup()
    
    def _get_bot_status(self):
        """Get the status of the bot from the API"""
        try:
            import requests
            response = requests.get(f"{API_URL}/status", timeout=2)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Could not get status: {str(e)}")
        return None
    
    def stop(self):
        """Stop the thread and cleanup processes"""
        self.running = False
        self._cleanup()
        self.wait()
    
    def _cleanup(self):
        """Clean up processes when stopping"""
        if self.bot_process and self.bot_process.poll() is None:
            logger.info("Terminating bot process")
            try:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.bot_process.kill()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Setup UI
        self.setWindowTitle(f"{APP_NAME} - v{APP_VERSION}")
        self.setMinimumSize(800, 600)
        
        # Load application settings
        self.settings = QSettings("ForexScalperAI", "DesktopApp")
        
        # Initialize bot thread
        self.bot_thread = None
        
        # Initialize updater
        self.updater = Updater()
        self.checking_for_updates = False
        
        # Create system tray
        self.create_tray_icon()
        
        # Create UI
        self.init_ui()
        
        # Check if auto-start is enabled
        if self.settings.value("auto_start", False, type=bool):
            QTimer.singleShot(1000, self.start_bot)
            
        # Start timer for status updates
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_display)
        self.status_timer.start(5000)  # Update every 5 seconds
        
        # Check for updates on startup if enabled
        if self.settings.value("check_updates_on_startup", True, type=bool):
            QTimer.singleShot(5000, self.check_for_updates)
        
        logger.info(f"{APP_NAME} desktop application started")
    
    def init_ui(self):
        """Initialize the user interface"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Logo and title
        title_layout = QHBoxLayout()
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "logo.png")
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
        else:
            logo_label.setText("🤖")
            logo_label.setFont(QFont("Arial", 24))
        
        title_label = QLabel(f"{APP_NAME}")
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        
        title_layout.addWidget(logo_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Dashboard tab
        dashboard_widget = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_widget)
        
        # Status group
        status_group = QGroupBox("Bot Status")
        status_layout = QFormLayout()
        
        self.status_label = QLabel("Stopped")
        self.status_label.setStyleSheet("font-weight: bold; color: red;")
        
        self.running_time_label = QLabel("Not running")
        self.active_pairs_label = QLabel("None")
        self.open_trades_label = QLabel("0")
        self.profit_label = QLabel("$0.00")
        
        status_layout.addRow("Status:", self.status_label)
        status_layout.addRow("Running time:", self.running_time_label)
        status_layout.addRow("Active pairs:", self.active_pairs_label)
        status_layout.addRow("Open trades:", self.open_trades_label)
        status_layout.addRow("Current profit:", self.profit_label)
        
        status_group.setLayout(status_layout)
        
        # Controls group
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()
        
        self.start_button = QPushButton("Start Bot")
        self.start_button.clicked.connect(self.start_bot)
        self.start_button.setMinimumHeight(50)
        self.start_button.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.stop_button = QPushButton("Stop Bot")
        self.stop_button.clicked.connect(self.stop_bot)
        self.stop_button.setMinimumHeight(50)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.open_app_button = QPushButton("Open Mobile App")
        self.open_app_button.clicked.connect(self.open_mobile_app)
        
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.open_app_button)
        
        controls_group.setLayout(controls_layout)
        
        # Add to dashboard
        dashboard_layout.addWidget(status_group)
        dashboard_layout.addWidget(controls_group)
        dashboard_layout.addStretch()
        
        # Settings tab
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        
        # Auto start settings
        startup_group = QGroupBox("Startup Settings")
        startup_layout = QVBoxLayout()
        
        self.auto_start_checkbox = QCheckBox("Start bot automatically when application launches")
        self.auto_start_checkbox.setChecked(self.settings.value("auto_start", False, type=bool))
        self.auto_start_checkbox.toggled.connect(self.on_auto_start_toggled)
        
        self.windows_startup_checkbox = QCheckBox("Launch application on Windows startup")
        self.windows_startup_checkbox.setChecked(self.is_in_windows_startup())
        self.windows_startup_checkbox.toggled.connect(self.on_windows_startup_toggled)
        
        startup_layout.addWidget(self.auto_start_checkbox)
        startup_layout.addWidget(self.windows_startup_checkbox)
        startup_group.setLayout(startup_layout)
        
        # Update settings
        update_group = QGroupBox("Update Settings")
        update_layout = QVBoxLayout()
        
        self.check_updates_checkbox = QCheckBox("Check for updates on startup")
        self.check_updates_checkbox.setChecked(self.settings.value("check_updates_on_startup", True, type=bool))
        self.check_updates_checkbox.toggled.connect(self.on_check_updates_toggled)
        
        update_layout.addWidget(self.check_updates_checkbox)
        
        # Update action buttons
        update_buttons_layout = QHBoxLayout()
        
        self.check_updates_button = QPushButton("Check for Updates")
        self.check_updates_button.clicked.connect(lambda: self.check_for_updates(silent=False))
        
        self.install_update_button = QPushButton("Install Update")
        self.install_update_button.setEnabled(self.updater.update_available)
        self.install_update_button.clicked.connect(self.install_update)
        
        update_buttons_layout.addWidget(self.check_updates_button)
        update_buttons_layout.addWidget(self.install_update_button)
        
        update_layout.addLayout(update_buttons_layout)
        update_group.setLayout(update_layout)
        
        # Add to settings
        settings_layout.addWidget(startup_group)
        settings_layout.addWidget(update_group)
        settings_layout.addStretch()
        
        # Add tabs
        tab_widget.addTab(dashboard_widget, "Dashboard")
        tab_widget.addTab(settings_widget, "Settings")
        
        # Add to main layout
        main_layout.addLayout(title_layout)
        main_layout.addWidget(tab_widget)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def create_tray_icon(self):
        """Create system tray icon and menu"""
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Set icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icon.png")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # Create tray menu
        tray_menu = QMenu()
        
        # Add actions
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        
        start_action = QAction("Start Bot", self)
        start_action.triggered.connect(self.start_bot)
        
        stop_action = QAction("Stop Bot", self)
        stop_action.triggered.connect(self.stop_bot)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close_application)
        
        # Add actions to menu
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(start_action)
        tray_menu.addAction(stop_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        # Set tray menu
        self.tray_icon.setContextMenu(tray_menu)
        
        # Show tray icon
        self.tray_icon.show()
        
        # Connect tray icon activation
        self.tray_icon.activated.connect(self.on_tray_activated)
    
    def on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()
    
    def closeEvent(self, event):
        """Handle window close event"""
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            self.close_application()
    
    def close_application(self):
        """Close application and clean up"""
        # Stop bot if running
        self.stop_bot()
        
        # Close application
        QApplication.quit()
    
    def start_bot(self):
        """Start the trading bot"""
        if self.bot_thread is None or not self.bot_thread.isRunning():
            # Create and start bot thread
            self.bot_thread = BotThread()
            self.bot_thread.signal_status_update.connect(self.on_status_update)
            self.bot_thread.signal_error.connect(self.on_bot_error)
            self.bot_thread.start()
            
            # Update UI
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.status_label.setText("Starting...")
            self.status_label.setStyleSheet("font-weight: bold; color: orange;")
            
            # Show notification
            self.tray_icon.showMessage(APP_NAME, "Bot started", QSystemTrayIcon.Information, 5000)
            
            # Update status bar
            self.statusBar().showMessage("Bot starting...")
            
            logger.info("Bot started")
    
    def stop_bot(self):
        """Stop the trading bot"""
        if self.bot_thread and self.bot_thread.isRunning():
            # Stop bot thread
            self.bot_thread.stop()
            
            # Update UI
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.status_label.setText("Stopped")
            self.status_label.setStyleSheet("font-weight: bold; color: red;")
            
            # Show notification
            self.tray_icon.showMessage(APP_NAME, "Bot stopped", QSystemTrayIcon.Information, 5000)
            
            # Update status bar
            self.statusBar().showMessage("Bot stopped")
            
            logger.info("Bot stopped")
    
    def on_status_update(self, status):
        """Handle status update from bot thread"""
        if status.get("status") == "running":
            self.status_label.setText("Running")
            self.status_label.setStyleSheet("font-weight: bold; color: green;")
        
        # Update other status fields
        # These would need to match what your API returns
        running_since = status.get("running_since")
        if running_since:
            try:
                start_time = datetime.fromisoformat(running_since)
                running_time = datetime.now() - start_time
                hours, remainder = divmod(running_time.total_seconds(), 3600)
                minutes, seconds = divmod(remainder, 60)
                self.running_time_label.setText(f"{int(hours)}h {int(minutes)}m {int(seconds)}s")
            except Exception as e:
                logger.error(f"Error parsing running time: {str(e)}")
                self.running_time_label.setText("Unknown")
        
        # Update active pairs
        active_pairs = status.get("active_pairs", [])
        if active_pairs:
            self.active_pairs_label.setText(", ".join(active_pairs[:5]) + 
                                        (f" +{len(active_pairs) - 5} more" if len(active_pairs) > 5 else ""))
        
        # Update open trades
        open_trades = status.get("open_trades", 0)
        self.open_trades_label.setText(str(open_trades))
        
        # Update profit
        profit = status.get("current_profit", 0)
        self.profit_label.setText(f"${profit:.2f}")
        
        # Update status bar
        self.statusBar().showMessage(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
    
    def on_bot_error(self, error_message):
        """Handle error from bot thread"""
        # Update UI
        self.status_label.setText("Error")
        self.status_label.setStyleSheet("font-weight: bold; color: red;")
        
        # Enable start button
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # Show notification
        self.tray_icon.showMessage(APP_NAME, f"Bot error: {error_message}", QSystemTrayIcon.Critical, 10000)
        
        # Update status bar
        self.statusBar().showMessage(f"Error: {error_message}")
        
        logger.error(f"Bot error: {error_message}")
    
    def update_status_display(self):
        """Update status display periodically"""
        if self.bot_thread and self.bot_thread.isRunning():
            # Status is updated via signal from thread
            pass
        else:
            # Update UI for stopped state
            self.status_label.setText("Stopped")
            self.status_label.setStyleSheet("font-weight: bold; color: red;")
            self.running_time_label.setText("Not running")
    
    def open_mobile_app(self):
        """Open mobile app in browser"""
        webbrowser.open(API_URL)
        self.statusBar().showMessage("Opening mobile app interface...")
    
    def on_auto_start_toggled(self, checked):
        """Handle auto start checkbox toggle"""
        self.settings.setValue("auto_start", checked)
        logger.info(f"Auto start set to: {checked}")
    
    def on_windows_startup_toggled(self, checked):
        """Handle Windows startup checkbox toggle"""
        if checked:
            self.add_to_windows_startup()
        else:
            self.remove_from_windows_startup()
    
    def is_in_windows_startup(self):
        """Check if application is set to start with Windows"""
        import winreg
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ
            )
            
            try:
                value, _ = winreg.QueryValueEx(key, APP_NAME)
                winreg.CloseKey(key)
                return True
            except WindowsError:
                winreg.CloseKey(key)
                return False
                
        except WindowsError:
            return False
    
    def add_to_windows_startup(self):
        """Add application to Windows startup"""
        import winreg
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_WRITE
            )
            
            executable = sys.executable
            script_path = os.path.abspath(__file__)
            
            winreg.SetValueEx(
                key, 
                APP_NAME, 
                0, 
                winreg.REG_SZ, 
                f'"{executable}" "{script_path}"'
            )
            
            winreg.CloseKey(key)
            logger.info("Added to Windows startup")
            return True
            
        except WindowsError as e:
            logger.error(f"Error adding to Windows startup: {str(e)}")
            return False
    
    def remove_from_windows_startup(self):
        """Remove application from Windows startup"""
        import winreg
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_WRITE
            )
            
            winreg.DeleteValue(key, APP_NAME)
            winreg.CloseKey(key)
            logger.info("Removed from Windows startup")
            return True
            
        except WindowsError as e:
            logger.error(f"Error removing from Windows startup: {str(e)}")
            return False
            
    def check_for_updates(self, silent=False):
        """Check for updates and prompt user if updates are available"""
        if self.checking_for_updates:
            return
            
        self.checking_for_updates = True
        
        try:
            if not silent:
                self.statusBar().showMessage("Checking for updates...")
                
            # Check for updates using the updater
            has_update = self.updater.check_for_updates(force=True)
            
            if has_update:
                # Update is available
                update_version = self.updater.update_info.get('version', 'Unknown')
                
                if not silent:
                    # Show update notification
                    result = QMessageBox.question(
                        self,
                        "Update Available",
                        f"A new version of {APP_NAME} is available (v{update_version}).\n\n"
                        f"Would you like to update now?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if result == QMessageBox.Yes:
                        self.install_update()
                else:
                    # In silent mode, just show tray notification
                    self.tray_icon.showMessage(
                        f"{APP_NAME} Update Available", 
                        f"Version {update_version} is available. Check the Updates tab to install.",
                        QSystemTrayIcon.Information,
                        5000
                    )
                    
                # Update status bar
                if not silent:
                    self.statusBar().showMessage(f"Update available: v{update_version}")
            else:
                # No update available
                if not silent:
                    self.statusBar().showMessage("No updates available")
        except Exception as e:
            logger.error(f"Error checking for updates: {str(e)}")
            if not silent:
                self.statusBar().showMessage("Error checking for updates")
        finally:
            self.checking_for_updates = False
    
    def install_update(self):
        """Install available update"""
        try:
            # Check if bot is running
            if self.bot_thread and self.bot_thread.isRunning():
                result = QMessageBox.question(
                    self,
                    "Bot is Running",
                    f"The trading bot is currently running. It will be stopped during the update.\n\n"
                    f"Do you want to continue?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if result != QMessageBox.Yes:
                    return
                
                # Stop the bot
                self.stop_bot()
            
            # Show update progress dialog
            self.statusBar().showMessage("Installing update...")
            
            # Apply the update
            if self.updater.update():
                # Update successful
                QMessageBox.information(
                    self,
                    "Update Successful",
                    f"{APP_NAME} has been updated successfully. The application will now restart.",
                    QMessageBox.Ok
                )
                
                # Restart the application
                self._restart_application()
            else:
                # Update failed
                QMessageBox.critical(
                    self,
                    "Update Failed",
                    f"Failed to update {APP_NAME}. Please try again later.",
                    QMessageBox.Ok
                )
                
                self.statusBar().showMessage("Update failed")
        except Exception as e:
            logger.error(f"Error installing update: {str(e)}")
            QMessageBox.critical(
                self,
                "Update Error",
                f"An error occurred while updating {APP_NAME}:\n\n{str(e)}",
                QMessageBox.Ok
            )
            
            self.statusBar().showMessage("Update error")
    
    def _restart_application(self):
        """Restart the application"""
        try:
            # Get path to main.py
            main_script = os.path.abspath(__file__)
            
            # Start new instance of the application
            subprocess.Popen([sys.executable, main_script])
            
            # Exit current instance
            QApplication.quit()
        except Exception as e:
            logger.error(f"Error restarting application: {str(e)}")
    
    def on_check_updates_toggled(self, checked):
        """Handle check updates checkbox toggle"""
        self.settings.setValue("check_updates_on_startup", checked)
        logger.info(f"Check updates on startup set to: {checked}")


if __name__ == "__main__":
    # Create application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Don't quit when window is closed
    
    # Create main window
    main_window = MainWindow()
    main_window.show()
    
    # Start event loop
    sys.exit(app.exec_())
