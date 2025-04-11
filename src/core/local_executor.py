"""
Local Executor Module

This module allows the Forex Trading Bot to run locally on a mobile device or laptop
without requiring a VPS. It manages system resources, handles network interruptions,
and provides a bridge between the mobile app and the trading engine.
"""

import os
import sys
import time
import threading
import platform
import psutil
import yaml
from pathlib import Path
import json
import traceback
import signal
from datetime import datetime
import sqlite3
from typing import Dict, Any, Optional, List, Tuple

import logging
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.bot_controller import BotController
from src.utils.config_utils import load_config
from src.utils.exceptions import BotRuntimeError, NetworkError, MarketDataError


class LocalExecutor:
    """
    Manages local execution of the trading bot on mobile devices and laptops.
    Handles resource management, error recovery, and state persistence.
    """
    
    def __init__(self, config_path: str = "config/mt5_config.yaml", 
                 local_config_path: str = "config/local_execution.yaml"):
        """
        Initialize the local executor with configuration.
        
        Args:
            config_path: Path to the main MT5 configuration file
            local_config_path: Path to the local execution configuration file
        """
        self.config_path = Path(config_path)
        if not self.config_path.is_absolute():
            self.config_path = PROJECT_ROOT / self.config_path
            
        self.local_config_path = Path(local_config_path)
        if not self.local_config_path.is_absolute():
            self.local_config_path = PROJECT_ROOT / self.local_config_path
        
        # Load configurations
        self.config = load_config(str(self.config_path))
        
        with open(self.local_config_path, 'r') as f:
            self.local_config = yaml.safe_load(f)
        
        # Initialize state variables
        self.running = False
        self.paused = False
        self.error_count = 0
        self.last_state_save = time.time()
        self.last_error_time = 0
        self.device_type = self._detect_device_type()
        self.bot_controller = None
        self.state_db_path = PROJECT_ROOT / "data" / "local_state.db"
        
        # Setup state database
        self._setup_state_db()
        
        # Running stats
        self.stats = {
            "start_time": None,
            "trades_executed": 0,
            "errors_recovered": 0,
            "last_connection_check": time.time(),
            "is_connected": True,
            "cpu_usage": 0,
            "memory_usage": 0,
            "battery_level": 100 if self.device_type == "mobile" else None,
            "network_status": "connected"
        }
        
        # Initialize monitoring and watchdog threads
        self.threads = {}
    
    def _detect_device_type(self) -> str:
        """Detect if running on mobile or desktop based on platform and system specs"""
        device_config = self.local_config["execution"]["device_type"]
        
        if device_config != "auto":
            return device_config
            
        system = platform.system()
        machine = platform.machine()
        
        # Check for Android using environment variables or partial system name
        if "ANDROID_ROOT" in os.environ or "android" in system.lower():
            return "mobile"
        
        # Check for iOS (unlikely to run Python directly but possible with tools)
        if system == "Darwin" and (machine == "arm64" or machine == "aarch64"):
            # Could be iOS or M1/M2 Mac, check memory as heuristic
            if psutil.virtual_memory().total < 4 * 1024 * 1024 * 1024:  # Less than 4GB
                return "mobile"
        
        # Default to desktop
        return "desktop"
    
    def _setup_state_db(self):
        """Setup SQLite database for storing bot state information"""
        os.makedirs(self.state_db_path.parent, exist_ok=True)
        
        conn = sqlite3.connect(str(self.state_db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_state (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            state_data TEXT,
            running BOOLEAN,
            paused BOOLEAN
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            order_type TEXT,
            volume REAL,
            price REAL,
            sl REAL,
            tp REAL,
            profit REAL,
            strategy TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def _save_state(self):
        """Save the current state of the bot to the database"""
        if not self.bot_controller:
            return
            
        try:
            # Get state from bot controller
            state_data = self.bot_controller.get_state()
            
            # Convert to JSON
            state_json = json.dumps(state_data)
            
            # Save to database
            conn = sqlite3.connect(str(self.state_db_path))
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO bot_state (timestamp, state_data, running, paused) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), state_json, self.running, self.paused)
            )
            
            # Keep only last 10 states to save space
            cursor.execute(
                "DELETE FROM bot_state WHERE id NOT IN (SELECT id FROM bot_state ORDER BY timestamp DESC LIMIT 10)"
            )
            
            conn.commit()
            conn.close()
            
            self.last_state_save = time.time()
            logger.debug("Bot state saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save bot state: {str(e)}")
    
    def _load_last_state(self) -> Optional[Dict[str, Any]]:
        """Load the most recent bot state from the database"""
        try:
            conn = sqlite3.connect(str(self.state_db_path))
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT state_data, running, paused FROM bot_state ORDER BY timestamp DESC LIMIT 1"
            )
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                state_data = json.loads(result[0])
                self.running = result[1] == 1
                self.paused = result[2] == 1
                return state_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load bot state: {str(e)}")
            return None
    
    def _monitor_resources(self):
        """Monitoring thread to check system resources and adjust bot behavior"""
        logger.info(f"Resource monitoring started on {self.device_type} device")
        
        resource_config = self.local_config["execution"]["resource_management"]
        max_cpu = resource_config["max_cpu_percent"]
        max_memory = resource_config["max_memory_mb"] * 1024 * 1024  # Convert to bytes
        
        while self.running:
            try:
                # Get current resource usage
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_usage = psutil.Process(os.getpid()).memory_info().rss
                
                # Update stats
                self.stats["cpu_usage"] = cpu_percent
                self.stats["memory_usage"] = memory_usage
                
                # Check battery on mobile
                if self.device_type == "mobile":
                    try:
                        battery = psutil.sensors_battery()
                        if battery:
                            self.stats["battery_level"] = battery.percent
                            
                            # Check if we need to stop due to low battery
                            if (resource_config["battery_optimization"]["enabled"] and 
                                battery.percent < resource_config["battery_optimization"]["min_battery_percent"]):
                                logger.warning(f"Battery level critical ({battery.percent}%). Pausing bot operations.")
                                self.pause()
                    except:
                        # Some platforms might not support battery check
                        pass
                
                # Apply resource limits if needed
                if resource_config["limit_cpu_usage"] and cpu_percent > max_cpu:
                    logger.warning(f"CPU usage too high ({cpu_percent}%). Slowing down operations.")
                    time.sleep(2)  # Slow down the bot by sleeping
                
                if resource_config["limit_memory"] and memory_usage > max_memory:
                    logger.warning(f"Memory usage too high ({memory_usage / 1024 / 1024:.2f} MB). Optimizing memory.")
                    # Force garbage collection
                    import gc
                    gc.collect()
                
                # Save state based on interval
                if time.time() - self.last_state_save > self.local_config["execution"]["persistence"]["save_state_interval_seconds"]:
                    self._save_state()
                
                # Sleep to reduce monitoring overhead
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in resource monitoring: {str(e)}")
                time.sleep(10)  # Longer sleep on error
    
    def _network_monitor(self):
        """Monitor network connectivity and handle reconnections"""
        logger.info("Network monitoring started")
        
        reconnect_attempts = self.local_config["connection"]["reconnect_attempts"]
        reconnect_interval = self.local_config["connection"]["reconnect_interval_seconds"]
        grace_period = self.local_config["connection"]["disconnect_grace_period_seconds"]
        
        while self.running:
            try:
                # Simple connectivity check (can be enhanced)
                # Check if MT5 API is still responsive
                if self.bot_controller:
                    is_connected = self.bot_controller.check_connection()
                    
                    if is_connected != self.stats["is_connected"]:
                        if is_connected:
                            logger.info("Connection restored!")
                            self.stats["network_status"] = "connected"
                        else:
                            logger.warning("Connection lost. Waiting for restoration...")
                            self.stats["network_status"] = "disconnected"
                        
                    self.stats["is_connected"] = is_connected
                    self.stats["last_connection_check"] = time.time()
                    
                    # Handle disconnection
                    if not is_connected:
                        # Wait for grace period before attempting to reconnect
                        time.sleep(min(grace_period, 10))  # Sleep at most 10 seconds at a time
                        
                        # Check if we've been disconnected for longer than grace period
                        disconnect_time = time.time() - self.stats["last_connection_check"]
                        if disconnect_time > grace_period:
                            logger.warning(f"Disconnected for {disconnect_time:.1f} seconds. Attempting reconnection.")
                            
                            # Try to reconnect
                            for attempt in range(reconnect_attempts):
                                logger.info(f"Reconnection attempt {attempt + 1}/{reconnect_attempts}")
                                
                                if self.bot_controller.reconnect():
                                    logger.info("Reconnection successful!")
                                    break
                                
                                if attempt < reconnect_attempts - 1:
                                    time.sleep(reconnect_interval)
                            
                            # If still not connected, pause operations
                            if not self.bot_controller.check_connection():
                                logger.error("Failed to reconnect after multiple attempts. Pausing operations.")
                                self.pause()
                
                # Normal sleep interval
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in network monitoring: {str(e)}")
                time.sleep(15)  # Longer sleep on error
    
    def _watchdog(self):
        """Watchdog thread to ensure the bot is running properly and recover from issues"""
        logger.info("Watchdog monitor started")
        
        recovery_config = self.local_config["monitoring"]["recovery"]
        
        while self.running:
            try:
                # Check if bot controller thread is still active
                if self.bot_controller and not self.bot_controller.is_running() and not self.paused:
                    logger.warning("Bot controller stopped unexpectedly. Attempting restart.")
                    
                    self.error_count += 1
                    
                    # Check if we've had too many restarts in a short period
                    if (self.error_count > recovery_config["max_retry_attempts"] and 
                        time.time() - self.last_error_time < 300):  # 5 minutes
                        
                        logger.error("Too many restart attempts in a short period. Pausing operations.")
                        self.pause()
                        
                        # Set a longer interval to try again
                        self.last_error_time = time.time()
                        self.error_count = 0
                    else:
                        # Try to restart the bot controller
                        self.last_error_time = time.time()
                        self._restart_bot_controller()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in watchdog: {str(e)}")
                time.sleep(60)  # Longer sleep on error
    
    def _restart_bot_controller(self):
        """Safely restart the bot controller"""
        try:
            logger.info("Restarting bot controller")
            
            # Stop the current instance if it exists
            if self.bot_controller:
                self.bot_controller.stop()
            
            # Reinitialize
            self.initialize_bot_controller()
            
            if self.bot_controller:
                self.bot_controller.start()
                self.stats["errors_recovered"] += 1
                logger.info("Bot controller restarted successfully")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to restart bot controller: {str(e)}")
            return False
    
    def initialize_bot_controller(self):
        """Initialize the bot controller with the proper configuration"""
        try:
            # Create bot controller with configuration
            self.bot_controller = BotController(self.config)
            
            # Load previous state if enabled
            if self.local_config["execution"]["persistence"]["recover_from_last_state"]:
                last_state = self._load_last_state()
                if last_state:
                    logger.info("Restoring from previous state")
                    self.bot_controller.restore_state(last_state)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize bot controller: {str(e)}")
            traceback.print_exc()
            return False
    
    def start(self):
        """Start the local executor and bot controller"""
        if self.running:
            logger.warning("Local executor is already running")
            return
        
        logger.info(f"Starting local executor on {self.device_type} device")
        
        # Initialize
        self.running = True
        self.paused = False
        self.stats["start_time"] = time.time()
        
        # Start monitoring threads
        self.threads["resource_monitor"] = threading.Thread(target=self._monitor_resources)
        self.threads["resource_monitor"].daemon = True
        self.threads["resource_monitor"].start()
        
        self.threads["network_monitor"] = threading.Thread(target=self._network_monitor)
        self.threads["network_monitor"].daemon = True
        self.threads["network_monitor"].start()
        
        self.threads["watchdog"] = threading.Thread(target=self._watchdog)
        self.threads["watchdog"].daemon = True
        self.threads["watchdog"].start()
        
        # Initialize and start bot controller
        success = self.initialize_bot_controller()
        
        if success and self.bot_controller:
            self.bot_controller.start()
            logger.info("Bot controller started successfully")
        else:
            logger.error("Failed to start bot controller")
            self.running = False
            return False
        
        # Set up signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self.handle_shutdown_signal)
        signal.signal(signal.SIGTERM, self.handle_shutdown_signal)
        
        return True
    
    def stop(self):
        """Stop the local executor and bot controller"""
        if not self.running:
            return
        
        logger.info("Stopping local executor")
        
        # Save final state
        self._save_state()
        
        # Set running flag to false to stop threads
        self.running = False
        
        # Stop bot controller
        if self.bot_controller:
            self.bot_controller.stop()
        
        # Wait for threads to finish
        for thread_name, thread in self.threads.items():
            if thread.is_alive():
                logger.info(f"Waiting for {thread_name} to finish...")
                thread.join(timeout=5)
        
        logger.info("Local executor stopped")
    
    def pause(self):
        """Pause trading operations without fully stopping"""
        if self.paused:
            return
        
        logger.info("Pausing trading operations")
        self.paused = True
        
        if self.bot_controller:
            self.bot_controller.pause()
    
    def resume(self):
        """Resume trading operations after pause"""
        if not self.paused:
            return
        
        logger.info("Resuming trading operations")
        self.paused = False
        
        if self.bot_controller:
            self.bot_controller.resume()
    
    def handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signals for clean exit"""
        logger.info(f"Received shutdown signal {signum}")
        self.stop()
        sys.exit(0)
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the local executor and bot"""
        status = {
            "running": self.running,
            "paused": self.paused,
            "device_type": self.device_type,
            "uptime": time.time() - self.stats["start_time"] if self.stats["start_time"] else 0,
            "resource_usage": {
                "cpu_percent": self.stats["cpu_usage"],
                "memory_mb": self.stats["memory_usage"] / (1024 * 1024),
                "battery_level": self.stats["battery_level"]
            },
            "network_status": self.stats["network_status"],
            "trades_executed": self.stats["trades_executed"],
            "errors_recovered": self.stats["errors_recovered"]
        }
        
        # Add bot controller stats if available
        if self.bot_controller:
            bot_status = self.bot_controller.get_status()
            status["bot"] = bot_status
        
        return status
    
    def log_trade(self, trade_data: Dict[str, Any]):
        """Record trade in the local database"""
        try:
            conn = sqlite3.connect(str(self.state_db_path))
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO trade_history 
                (timestamp, symbol, order_type, volume, price, sl, tp, profit, strategy) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(),
                    trade_data.get("symbol", ""),
                    trade_data.get("order_type", ""),
                    trade_data.get("volume", 0.0),
                    trade_data.get("price", 0.0),
                    trade_data.get("sl", 0.0),
                    trade_data.get("tp", 0.0),
                    trade_data.get("profit", 0.0),
                    trade_data.get("strategy", "")
                )
            )
            
            conn.commit()
            conn.close()
            
            self.stats["trades_executed"] += 1
            logger.info(f"Trade logged: {trade_data.get('symbol')} {trade_data.get('order_type')}")
            
        except Exception as e:
            logger.error(f"Failed to log trade: {str(e)}")


# Basic application entry point for testing
if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get config paths from arguments if provided
    import argparse
    parser = argparse.ArgumentParser(description="Local Executor for Forex Trading Bot")
    parser.add_argument("--config", type=str, default="config/mt5_config.yaml", help="Path to MT5 config file")
    parser.add_argument("--local-config", type=str, default="config/local_execution.yaml", help="Path to local execution config")
    
    args = parser.parse_args()
    
    # Create and start local executor
    local_executor = LocalExecutor(args.config, args.local_config)
    
    if local_executor.start():
        print("Local executor started. Press Ctrl+C to stop.")
        
        try:
            while True:
                time.sleep(10)
                status = local_executor.get_status()
                print(f"Status: {'Running' if status['running'] else 'Stopped'}, {'Paused' if status['paused'] else 'Active'}")
                print(f"Resource usage: CPU {status['resource_usage']['cpu_percent']:.1f}%, Memory {status['resource_usage']['memory_mb']:.1f} MB")
                print(f"Network: {status['network_status']}, Trades: {status['trades_executed']}")
                print("-" * 50)
                
        except KeyboardInterrupt:
            print("Shutting down...")
        finally:
            local_executor.stop()
    else:
        print("Failed to start local executor")
