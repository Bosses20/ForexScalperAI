"""
Custom logging configuration for the Forex Trading Bot
Provides structured logging with rotation and multi-destination support
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, Optional, Any
from loguru import logger
import json

# Store original logger configuration
_original_logger = logger.configure()
_configured = False


def setup_logger(config: Dict[str, Any]) -> None:
    """
    Set up and configure the logger based on configuration
    
    Args:
        config: Logger configuration dictionary
    """
    global _configured
    
    # Get configuration values with defaults
    log_level = config.get('level', 'INFO')
    log_format = config.get('format', 
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    log_file = config.get('file_path')
    rotation = config.get('rotation', '20 MB')
    retention = config.get('retention', '1 week')
    compression = config.get('compression', 'zip')
    enqueue = config.get('enqueue', True)
    backtrace = config.get('backtrace', True)
    diagnose = config.get('diagnose', True)
    
    # Create log directory if it doesn't exist
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Remove all existing handlers
    logger.remove()
    
    # Add stdout handler
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True,
        backtrace=backtrace,
        diagnose=diagnose
    )
    
    # Add file handler if configured
    if log_file:
        logger.add(
            log_file,
            rotation=rotation,
            retention=retention,
            compression=compression,
            format=log_format,
            level=log_level,
            enqueue=enqueue,
            backtrace=backtrace,
            diagnose=diagnose
        )
    
    # Add JSON file handler for structured logs
    if log_file:
        json_log_file = log_file.rsplit('.', 1)[0] + '.json.' + log_file.rsplit('.', 1)[1]
        
        def json_formatter(record: Dict) -> str:
            """Format the record as a JSON string"""
            data = {
                "timestamp": record["time"].strftime("%Y-%m-%d %H:%M:%S.%f"),
                "level": record["level"].name,
                "message": record["message"],
                "module": record["name"],
                "function": record["function"],
                "line": record["line"],
                "thread_id": record["thread"].id,
                "process_id": record["process"].id,
            }
            
            # Add exception info if present
            if record["exception"]:
                data["exception"] = {
                    "type": record["exception"].type,
                    "value": record["exception"].value,
                    "traceback": record["exception"].traceback
                }
                
            # Add extra fields if present
            if record["extra"]:
                data["extra"] = record["extra"]
                
            return json.dumps(data)
        
        logger.add(
            json_log_file,
            format=json_formatter,
            rotation=rotation,
            retention=retention,
            compression=compression,
            level=log_level,
            enqueue=enqueue,
            serialize=True
        )
    
    logger.info(f"Logger configured with level: {log_level}")
    
    _configured = True


def get_logger(name: Optional[str] = None) -> logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Optional name for the logger
        
    Returns:
        Configured logger instance
    """
    if not _configured:
        # Set up a default configuration if not already configured
        setup_logger({'level': 'INFO'})
    
    # Return a logger with context
    if name:
        return logger.bind(name=name)
    
    return logger


def log_execution_time(func):
    """
    Decorator to log function execution time
    
    Args:
        func: Function to decorate
        
    Returns:
        Wrapped function with execution time logging
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        # Get function name and module
        func_name = func.__name__
        module_name = func.__module__
        
        execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Log execution time
        logger.debug(f"Function {module_name}.{func_name} executed in {execution_time:.2f} ms")
        
        return result
    
    return wrapper


def log_trading_activity(activity_type: str, details: Dict[str, Any]) -> None:
    """
    Log trading activity with structured data
    
    Args:
        activity_type: Type of trading activity (e.g., order, analysis, signal)
        details: Dictionary with activity details
    """
    # Create a copy of details to avoid modifying the original
    log_data = details.copy()
    
    # Add timestamp and activity type
    log_data['timestamp'] = datetime.now().isoformat()
    log_data['activity_type'] = activity_type
    
    # Use a contextual logger
    trade_logger = logger.bind(**log_data)
    
    # Log with appropriate level
    if activity_type == 'error':
        trade_logger.error(f"Trading error: {log_data.get('message', 'Unknown error')}")
    elif activity_type == 'warning':
        trade_logger.warning(f"Trading warning: {log_data.get('message', 'No details')}")
    elif activity_type in ['order', 'position', 'trade']:
        trade_logger.info(f"Trade activity: {activity_type.upper()} - {log_data.get('message', 'No details')}")
    else:
        trade_logger.debug(f"Trading activity: {activity_type} - {log_data.get('message', 'No details')}")
