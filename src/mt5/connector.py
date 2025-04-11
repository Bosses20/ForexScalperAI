"""
MetaTrader 5 Connector module
Handles authentication and connection to MT5 terminal
"""

import time
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from loguru import logger
import asyncio
import pandas as pd
import numpy as np

# Import the MetaTrader5 module
try:
    import MetaTrader5 as mt5
except ImportError:
    logger.error("MetaTrader5 package not found. Please install: pip install MetaTrader5")
    mt5 = None

class MT5Connector:
    """
    Connector class for MetaTrader 5 integration
    """
    
    def __init__(self, config: dict):
        """
        Initialize MT5 connector
        
        Args:
            config: Dictionary with MT5 configuration parameters
        """
        self.config = config
        self.mt5_login = config.get('login')
        self.mt5_password = config.get('password')
        self.mt5_server = config.get('server')
        self.mt5_path = config.get('path')
        self.connected = False
        self.last_error = None
        self.ping_interval = config.get('ping_interval', 60)  # seconds
        self.last_ping_time = None
        self.terminal_info = None
        self.account_info = None
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 5)  # seconds
        
        logger.info("MT5 connector initialized")
    
    def connect(self) -> bool:
        """
        Establish connection to MetaTrader 5 terminal
        
        Returns:
            True if connected successfully, False otherwise
        """
        if self.connected and mt5 and mt5.terminal_info():
            logger.debug("Already connected to MT5")
            return True
            
        try:
            # Initialize MT5 connection
            if not mt5:
                logger.error("MetaTrader5 module not available")
                return False
                
            # Shut down MT5 if it was already running
            mt5.shutdown()
            
            # Initialize connection to MT5
            logger.info(f"Initializing MT5 connection to {self.mt5_server}")
            init_result = False
            
            # If path is specified, use it
            if self.mt5_path and os.path.exists(self.mt5_path):
                init_result = mt5.initialize(
                    path=self.mt5_path,
                    login=self.mt5_login,
                    password=self.mt5_password,
                    server=self.mt5_server
                )
            else:
                # Try to initialize without path
                init_result = mt5.initialize(
                    login=self.mt5_login,
                    password=self.mt5_password,
                    server=self.mt5_server
                )
            
            if not init_result:
                error_code = mt5.last_error()
                error_details = f"Error code: {error_code[0]}, Description: {error_code[1]}"
                logger.error(f"MT5 initialization failed: {error_details}")
                self.last_error = error_details
                return False
            
            # Check connection
            if not self.check_connection():
                logger.error("MT5 initialization succeeded but connection check failed")
                return False
            
            # Store terminal info
            self.terminal_info = mt5.terminal_info()._asdict()
            logger.info(f"Connected to MT5 terminal: {self.terminal_info.get('name')} {self.terminal_info.get('version')}")
            
            # Login to trading account
            login_result = self.login()
            if not login_result:
                logger.error("MT5 login failed")
                return False
            
            self.connected = True
            self.last_ping_time = time.time()
            
            logger.info(f"Successfully connected to MT5 server {self.mt5_server}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to MT5: {str(e)}")
            self.last_error = str(e)
            return False
    
    def login(self) -> bool:
        """
        Log in to MT5 account
        
        Returns:
            True if login successful, False otherwise
        """
        if not mt5:
            logger.error("MetaTrader5 module not available")
            return False
            
        try:
            # Check if already logged in
            account_info = mt5.account_info()
            if account_info:
                self.account_info = account_info._asdict()
                logger.info(f"Already logged in to account: {self.account_info.get('login')} ({self.account_info.get('server')})")
                return True
            
            # Login with credentials
            login_result = mt5.login(
                login=self.mt5_login,
                password=self.mt5_password,
                server=self.mt5_server
            )
            
            if not login_result:
                error_code = mt5.last_error()
                error_details = f"Error code: {error_code[0]}, Description: {error_code[1]}"
                logger.error(f"MT5 login failed: {error_details}")
                self.last_error = error_details
                return False
            
            # Store account info
            account_info = mt5.account_info()
            if account_info:
                self.account_info = account_info._asdict()
                logger.info(f"Logged in to account: {self.account_info.get('login')} ({self.account_info.get('server')})")
                return True
            else:
                logger.error("Failed to get account info after login")
                return False
                
        except Exception as e:
            logger.error(f"Error during MT5 login: {str(e)}")
            self.last_error = str(e)
            return False
    
    def check_connection(self) -> bool:
        """
        Verify connection to MT5 terminal
        
        Returns:
            True if connected, False otherwise
        """
        if not mt5:
            return False
            
        try:
            # Check terminal info
            terminal_info = mt5.terminal_info()
            if not terminal_info:
                return False
                
            # Update last ping time
            self.last_ping_time = time.time()
            return True
            
        except Exception as e:
            logger.error(f"Error checking MT5 connection: {str(e)}")
            return False
    
    def ping(self) -> int:
        """
        Test connection latency
        
        Returns:
            Latency in milliseconds, -1 if unsuccessful
        """
        if not self.connected or not mt5:
            return -1
            
        try:
            start_time = time.time()
            terminal_info = mt5.terminal_info()
            if not terminal_info:
                return -1
                
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            # Update last ping time
            self.last_ping_time = time.time()
            
            return latency_ms
            
        except Exception as e:
            logger.error(f"Error pinging MT5: {str(e)}")
            return -1
    
    def reconnect(self) -> bool:
        """
        Handle lost connections by attempting to reconnect
        
        Returns:
            True if reconnected successfully, False otherwise
        """
        if not mt5:
            return False
            
        logger.info("Attempting to reconnect to MT5")
        
        # Try to reconnect with retries
        for attempt in range(1, self.max_retries + 1):
            logger.debug(f"Reconnection attempt {attempt}/{self.max_retries}")
            
            # Close existing connection if any
            mt5.shutdown()
            time.sleep(self.retry_delay)
            
            # Attempt to connect
            if self.connect():
                logger.info(f"Successfully reconnected to MT5 on attempt {attempt}")
                return True
            
            # Wait before next attempt
            if attempt < self.max_retries:
                time.sleep(self.retry_delay)
        
        logger.error(f"Failed to reconnect to MT5 after {self.max_retries} attempts")
        return False
    
    def disconnect(self) -> bool:
        """
        Close connection to MT5 terminal properly
        
        Returns:
            True if disconnected successfully
        """
        if not mt5:
            return True
            
        try:
            mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from MT5 terminal")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from MT5: {str(e)}")
            return False
    
    def get_account_info(self) -> dict:
        """
        Get current account information
        
        Returns:
            Dictionary with account details
        """
        if not self.connected or not mt5:
            logger.warning("Not connected to MT5, cannot get account info")
            return {}
            
        try:
            account_info = mt5.account_info()
            if account_info:
                # Convert named tuple to dict
                info_dict = account_info._asdict()
                
                # Update cached account info
                self.account_info = info_dict
                
                return info_dict
            else:
                logger.warning("Failed to get account info")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return {}
    
    def get_terminal_info(self) -> dict:
        """
        Get terminal information
        
        Returns:
            Dictionary with terminal details
        """
        if not self.connected or not mt5:
            logger.warning("Not connected to MT5, cannot get terminal info")
            return {}
            
        try:
            terminal_info = mt5.terminal_info()
            if terminal_info:
                # Convert named tuple to dict
                info_dict = terminal_info._asdict()
                
                # Update cached terminal info
                self.terminal_info = info_dict
                
                return info_dict
            else:
                logger.warning("Failed to get terminal info")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting terminal info: {str(e)}")
            return {}
    
    def get_symbols(self) -> List[str]:
        """
        Get available trading symbols
        
        Returns:
            List of symbol names
        """
        if not self.connected or not mt5:
            logger.warning("Not connected to MT5, cannot get symbols")
            return []
            
        try:
            symbols = mt5.symbols_get()
            if symbols:
                return [symbol.name for symbol in symbols]
            else:
                logger.warning("Failed to get symbols")
                return []
                
        except Exception as e:
            logger.error(f"Error getting symbols: {str(e)}")
            return []
    
    def get_connection_status(self) -> Dict:
        """
        Get current connection status
        
        Returns:
            Dictionary with connection details
        """
        return {
            "connected": self.connected,
            "last_error": self.last_error,
            "last_ping_time": self.last_ping_time,
            "terminal_info": self.terminal_info,
            "account_info": self.account_info
        }
