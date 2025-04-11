"""
Simple UI for the Forex Trading Bot
This module provides a minimal interface for starting and monitoring the trading bot.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import os
import sys
import json
import time
from datetime import datetime
import subprocess
from pathlib import Path

# Adjust the python path to import from parent directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.bot_controller import BotController
from loguru import logger

class BotUI:
    """
    Simple UI for controlling and monitoring the trading bot
    """
    
    def __init__(self, config_path="config/mt5_config.yaml"):
        """
        Initialize the UI
        
        Args:
            config_path (str): Path to the configuration file
        """
        self.config_path = config_path
        self.bot_controller = None
        self.bot_thread = None
        self.running = False
        self.mt5_process = None
        
        # Create credentials directory if it doesn't exist
        self.credentials_dir = Path.home() / "forex_bot_credentials"
        self.credentials_dir.mkdir(exist_ok=True)
        self.credentials_file = self.credentials_dir / "credentials.json"
        
        # Initialize the UI
        self.root = tk.Tk()
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components"""
        self.root.title("Forex Trading Bot")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # Configure styles
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 12))
        self.style.configure("TLabel", font=("Arial", 12))
        self.style.configure("Header.TLabel", font=("Arial", 14, "bold"))
        self.style.configure("Status.TLabel", font=("Arial", 12))
        self.style.configure("Running.TLabel", foreground="green")
        self.style.configure("Stopped.TLabel", foreground="red")
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_label = ttk.Label(main_frame, text="Forex Trading Bot Control Panel", style="Header.TLabel")
        header_label.pack(pady=(0, 20))
        
        # Control frame
        control_frame = ttk.LabelFrame(main_frame, text="Bot Controls", padding="10")
        control_frame.pack(fill=tk.X, pady=10)
        
        # Start/Stop button
        self.toggle_button = ttk.Button(control_frame, text="Start Trading Bot", command=self.toggle_bot)
        self.toggle_button.pack(pady=10)
        
        # MT5 button
        self.mt5_button = ttk.Button(control_frame, text="Launch MetaTrader 5", command=self.launch_mt5)
        self.mt5_button.pack(pady=10)
        
        # Settings button
        self.settings_button = ttk.Button(control_frame, text="Update Credentials", command=self.update_credentials)
        self.settings_button.pack(pady=10)
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Bot Status", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Status indicators
        self.bot_status_label = ttk.Label(status_frame, text="Status: STOPPED", style="Stopped.TLabel")
        self.bot_status_label.pack(anchor=tk.W, pady=5)
        
        self.mt5_status_label = ttk.Label(status_frame, text="MetaTrader 5: Not Running")
        self.mt5_status_label.pack(anchor=tk.W, pady=5)
        
        self.account_label = ttk.Label(status_frame, text="Account: Not Connected")
        self.account_label.pack(anchor=tk.W, pady=5)
        
        self.balance_label = ttk.Label(status_frame, text="Balance: --")
        self.balance_label.pack(anchor=tk.W, pady=5)
        
        self.trades_label = ttk.Label(status_frame, text="Active Trades: 0")
        self.trades_label.pack(anchor=tk.W, pady=5)
        
        # Log frame
        log_frame = ttk.LabelFrame(main_frame, text="Recent Activity", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Log text area
        self.log_text = tk.Text(log_frame, height=8, width=60, font=("Consolas", 10))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar for log
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Make log read-only
        self.log_text.config(state=tk.DISABLED)
        
        # Footer
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill=tk.X, pady=10)
        
        # Version label
        version_label = ttk.Label(footer_frame, text="v1.0.0")
        version_label.pack(side=tk.RIGHT)
        
        # Check for saved credentials
        self.load_credentials()
        
        # Set up a timer to update the UI
        self.root.after(1000, self.update_ui)
        
    def toggle_bot(self):
        """Start or stop the trading bot"""
        if self.running:
            self.stop_bot()
        else:
            self.start_bot()
            
    def start_bot(self):
        """Start the trading bot"""
        # Check if MT5 is running
        if not self.is_mt5_running():
            self.launch_mt5()
            time.sleep(5)  # Give MT5 time to start
            
        # Check if we have credentials
        if not self.verify_credentials():
            messagebox.showerror("Error", "Please set up your MT5 credentials before starting the bot.")
            self.update_credentials()
            return
            
        try:
            # Initialize the bot controller if needed
            if self.bot_controller is None:
                self.bot_controller = BotController(self.config_path)
                self.bot_controller.initialize_components()
            
            # Start the bot in a separate thread
            self.bot_thread = threading.Thread(target=self.run_bot)
            self.bot_thread.daemon = True
            self.bot_thread.start()
            
            # Update UI
            self.running = True
            self.toggle_button.config(text="Stop Trading Bot")
            self.bot_status_label.config(text="Status: RUNNING", style="Running.TLabel")
            self.log_message("Bot started successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start bot: {str(e)}")
            logger.error(f"Failed to start bot: {str(e)}")
            
    def stop_bot(self):
        """Stop the trading bot"""
        try:
            if self.bot_controller:
                self.bot_controller.stop()
                
            # Update UI
            self.running = False
            self.toggle_button.config(text="Start Trading Bot")
            self.bot_status_label.config(text="Status: STOPPED", style="Stopped.TLabel")
            self.log_message("Bot stopped")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop bot: {str(e)}")
            logger.error(f"Failed to stop bot: {str(e)}")
            
    def run_bot(self):
        """Run the bot (called in a separate thread)"""
        try:
            self.bot_controller.run()
        except Exception as e:
            # Log error and update UI from the main thread
            logger.error(f"Bot error: {str(e)}")
            self.root.after(0, lambda: self.handle_bot_error(str(e)))
            
    def handle_bot_error(self, error_msg):
        """Handle bot errors (called from the main thread)"""
        self.running = False
        self.toggle_button.config(text="Start Trading Bot")
        self.bot_status_label.config(text="Status: ERROR", style="Stopped.TLabel")
        self.log_message(f"ERROR: {error_msg}")
        messagebox.showerror("Bot Error", f"The bot encountered an error: {error_msg}")
            
    def launch_mt5(self):
        """Launch MetaTrader 5"""
        try:
            # Get MT5 path from credentials
            credentials = self.load_credentials()
            mt5_path = credentials.get("mt5_path", "")
            
            # If path not set, ask for it
            if not mt5_path or not os.path.exists(mt5_path):
                mt5_path = self.ask_for_mt5_path()
                if not mt5_path:
                    return
                    
            # Launch MT5
            self.mt5_process = subprocess.Popen([mt5_path])
            self.log_message(f"Launched MetaTrader 5")
            
            # Update UI
            self.mt5_status_label.config(text="MetaTrader 5: Running")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch MetaTrader 5: {str(e)}")
            logger.error(f"Failed to launch MetaTrader 5: {str(e)}")
            
    def is_mt5_running(self):
        """Check if MetaTrader 5 is running"""
        # Simple check - if process is alive
        if self.mt5_process and self.mt5_process.poll() is None:
            return True
            
        # Otherwise try to check using other methods
        try:
            # This is a simplified check and might need enhancement
            import psutil
            for proc in psutil.process_iter():
                if "terminal64.exe" in proc.name().lower() or "terminal.exe" in proc.name().lower():
                    return True
            return False
        except:
            # If psutil is not available, assume MT5 is not running
            return False
            
    def ask_for_mt5_path(self):
        """Ask user for MT5 executable path"""
        path = simpledialog.askstring(
            "MetaTrader 5 Path", 
            "Please enter the full path to your MetaTrader 5 executable (terminal64.exe):",
            parent=self.root
        )
        if path and os.path.exists(path):
            # Save to credentials
            credentials = self.load_credentials()
            credentials["mt5_path"] = path
            self.save_credentials(credentials)
            return path
        elif path:
            messagebox.showerror("Invalid Path", "The specified path does not exist.")
        return None
            
    def update_credentials(self):
        """Update MT5 login credentials"""
        credentials = self.load_credentials()
        
        # Ask for credentials
        login = simpledialog.askstring(
            "MT5 Login", 
            "Please enter your MetaTrader 5 login:",
            parent=self.root,
            initialvalue=credentials.get("login", "")
        )
        if login is None:  # User clicked cancel
            return
            
        password = simpledialog.askstring(
            "MT5 Password", 
            "Please enter your MetaTrader 5 password:",
            parent=self.root,
            show="*"
        )
        if password is None:  # User clicked cancel
            return
            
        server = simpledialog.askstring(
            "MT5 Server", 
            "Please enter your MetaTrader 5 server:",
            parent=self.root,
            initialvalue=credentials.get("server", "")
        )
        if server is None:  # User clicked cancel
            return
        
        # Save credentials
        credentials.update({
            "login": login,
            "password": password,
            "server": server,
            "last_updated": datetime.now().isoformat()
        })
        self.save_credentials(credentials)
        
        self.log_message("Credentials updated successfully")
        
    def load_credentials(self):
        """Load saved credentials"""
        if not self.credentials_file.exists():
            return {}
            
        try:
            with open(self.credentials_file, "r") as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Failed to load credentials: {str(e)}")
            return {}
            
    def save_credentials(self, credentials):
        """Save credentials to file"""
        try:
            with open(self.credentials_file, "w") as file:
                json.dump(credentials, file, indent=2)
        except Exception as e:
            logger.error(f"Failed to save credentials: {str(e)}")
            messagebox.showerror("Error", f"Failed to save credentials: {str(e)}")
            
    def verify_credentials(self):
        """Check if credentials are set"""
        credentials = self.load_credentials()
        return all(k in credentials for k in ["login", "password", "server"])
        
    def update_ui(self):
        """Update UI with latest information"""
        # This method is called periodically to update the UI
        
        # Check if MT5 is running
        mt5_running = self.is_mt5_running()
        self.mt5_status_label.config(
            text=f"MetaTrader 5: {'Running' if mt5_running else 'Not Running'}"
        )
        
        # Update bot status indicators if it's running
        if self.running and self.bot_controller:
            try:
                # Get status information from bot controller
                status = self.bot_controller.get_status()
                
                # Update account info
                if "account_info" in status:
                    account_info = status["account_info"]
                    self.account_label.config(text=f"Account: {account_info.get('login', 'Unknown')}")
                    self.balance_label.config(text=f"Balance: {account_info.get('balance', 0):.2f} {account_info.get('currency', '')}")
                
                # Update trade count
                if "active_trades" in status:
                    self.trades_label.config(text=f"Active Trades: {len(status['active_trades'])}")
                
                # Add any recent activity to log
                if "recent_activity" in status:
                    for activity in status["recent_activity"]:
                        self.log_message(activity)
            except Exception as e:
                logger.error(f"Error updating UI: {str(e)}")
        
        # Schedule the next update
        self.root.after(1000, self.update_ui)
        
    def log_message(self, message):
        """Add a message to the log"""
        # Enable text widget for editing
        self.log_text.config(state=tk.NORMAL)
        
        # Add timestamp and message
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        
        # Scroll to the end
        self.log_text.see(tk.END)
        
        # Make text widget read-only again
        self.log_text.config(state=tk.DISABLED)
        
    def run(self):
        """Run the UI application"""
        self.root.mainloop()


if __name__ == "__main__":
    # Initialize and run the UI
    ui = BotUI()
    ui.run()
