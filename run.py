#!/usr/bin/env python3
"""
ForexScalperAI - Advanced Automated Forex Trading Bot
Main entry point for starting the trading bot
"""

import os
import sys
import time
import yaml
import logging
from pathlib import Path
import argparse
from loguru import logger

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# Import core components
from data.market_data import MarketDataFeed
from strategies.scalping_strategy import ScalpingStrategy
from models.prediction_model import PricePredictionModel
from risk.risk_manager import RiskManager
from execution.order_executor import OrderExecutor
from api.server import APIServer

def load_config(config_path):
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as config_file:
            return yaml.safe_load(config_file)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

def setup_logging(log_level):
    """Configure logging settings"""
    log_levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR
    }
    selected_level = log_levels.get(log_level.lower(), logging.INFO)
    
    # Configure logger
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level=selected_level)
    logger.add("logs/trading_{time}.log", rotation="500 MB", retention="10 days", level=selected_level)
    
    logger.info(f"Logging initialized at {log_level.upper()} level")

def main():
    """Main entry point for the trading bot"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ForexScalperAI Trading Bot")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="Path to configuration file")
    parser.add_argument("--log-level", type=str, default="info", choices=["debug", "info", "warning", "error"], 
                        help="Logging level")
    parser.add_argument("--api-only", action="store_true", help="Start only the API server without trading")
    args = parser.parse_args()
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Set up logging
    setup_logging(args.log_level)
    
    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    
    config = load_config(config_path)
    logger.info(f"Configuration loaded from {config_path}")
    
    # Initialize components
    try:
        # Initialize market data feed
        logger.info("Initializing market data feed...")
        market_data = MarketDataFeed(config['api'], config['data'], config['trading']['pairs'])
        
        # Initialize prediction models
        logger.info("Initializing prediction models...")
        prediction_model = PricePredictionModel(config['models']['price_prediction'])
        
        # Initialize risk manager
        logger.info("Initializing risk manager...")
        risk_manager = RiskManager(config['risk'])
        
        # Initialize trading strategy
        logger.info("Initializing scalping strategy...")
        strategy = ScalpingStrategy(config['strategy'], prediction_model)
        
        # Initialize order executor
        logger.info("Initializing order executor...")
        executor = OrderExecutor(config['api'], config['trading'], risk_manager)
        
        # Start API server if enabled
        if config['api_server']['enabled'] or args.api_only:
            logger.info("Starting API server...")
            api_server = APIServer(config['api_server'], market_data, strategy, risk_manager, executor)
            api_server.start()
            
            if args.api_only:
                logger.info("Running in API-only mode")
                # Keep the server running
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Shutting down API server...")
                    api_server.stop()
                    sys.exit(0)
        
        if not args.api_only:
            # Start trading bot
            logger.info("Starting trading bot...")
            
            # Connect to exchange
            market_data.connect()
            
            # Main trading loop
            try:
                while True:
                    # Get latest market data
                    data = market_data.get_latest_data()
                    
                    # Generate trading signals
                    signals = strategy.generate_signals(data)
                    
                    # Execute orders based on signals
                    if signals:
                        executor.execute_signals(signals)
                    
                    # Sleep to avoid hammering the API
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Trading bot shutting down...")
            finally:
                # Cleanup resources
                market_data.disconnect()
                if config['api_server']['enabled']:
                    api_server.stop()
                
    except Exception as e:
        logger.exception(f"Error starting trading bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
