"""
Run the API Server for the Forex Trading Bot

This script launches the FastAPI server that acts as the backend for the mobile app.
Run this on your VPS/server alongside the MT5 trading bot.
"""

import os
import sys
from pathlib import Path
import argparse
import uvicorn
import yaml
from loguru import logger

# Ensure proper imports from the project
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the FastAPI application
from src.api.server import app


def setup_logging():
    """Configure logging for the API server"""
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "api_server.log"
    
    # Configure loguru
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level="INFO")  # Add stderr handler
    logger.add(log_file, rotation="10 MB", level="DEBUG")  # Add file handler


def main():
    """
    Main entry point for running the API server
    """
    parser = argparse.ArgumentParser(description="Forex Trading Bot API Server")
    parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0",
        help="Host to run the server on"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000,
        help="Port to run the server on"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        default="config/mt5_config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Run in debug mode with auto-reload"
    )
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    logger.info("Starting Forex Trading Bot API Server")
    
    # Check if config file exists
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        print(f"Error: Configuration file not found: {config_path}")
        return 1
    
    try:
        # Set config path as environment variable so the server can access it
        os.environ["MT5_CONFIG_PATH"] = str(config_path)
        
        # Run the server
        uvicorn.run(
            "src.api.server:app",
            host=args.host,
            port=args.port,
            reload=args.debug,
            log_level="info" if not args.debug else "debug",
        )
        
        return 0
        
    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}")
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
