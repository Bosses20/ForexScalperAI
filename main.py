"""
Main entry point for the Forex Trading Bot application.

This module launches the user interface and connects all components.
Run this file to start the application.
"""

import os
import sys
from pathlib import Path
import argparse
from loguru import logger

# Ensure proper imports from the project
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ui.bot_ui import BotUI


def setup_logging():
    """Configure logging for the application"""
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "bot_application.log"
    
    # Configure loguru
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level="INFO")  # Add stderr handler
    logger.add(log_file, rotation="10 MB", level="DEBUG")  # Add file handler


def main():
    """
    Main entry point for the application
    """
    parser = argparse.ArgumentParser(description="Forex Trading Bot")
    parser.add_argument(
        "--config", 
        type=str, 
        default="config/mt5_config.yaml",
        help="Path to configuration file"
    )
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    logger.info("Starting Forex Trading Bot application")
    
    # Check if config file exists
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        print(f"Error: Configuration file not found: {config_path}")
        return 1
    
    try:
        # Launch the UI
        ui = BotUI(str(config_path))
        ui.run()
        return 0
        
    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}")
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
