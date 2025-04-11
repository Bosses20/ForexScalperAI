"""
MT5 Integration Example
Demonstrates how to use the MT5 integration framework with the main trading bot
"""

import os
import sys
import time
from loguru import logger

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required modules
from src.bot_controller import BotController
from src.mt5.integration import MT5Integration

def main():
    """Main execution function"""
    # Configure logging
    logger.add("logs/mt5_example.log", rotation="10 MB", level="INFO")
    logger.info("Starting MT5 example application")
    
    try:
        # Initialize main bot controller
        logger.info("Initializing bot controller")
        bot_controller = BotController(config_path="config/config.yaml")
        
        # Initialize MT5 integration
        logger.info("Initializing MT5 integration")
        mt5_integration = MT5Integration(bot_controller, config_path="config/mt5_config.yaml")
        
        if not mt5_integration.initialize():
            logger.error("Failed to initialize MT5 integration")
            return
        
        # Start MT5 trading
        logger.info("Starting MT5 trading")
        if not mt5_integration.start():
            logger.error("Failed to start MT5 trading")
            return
        
        # Display status
        logger.info("MT5 trading started successfully")
        
        # Main application loop
        try:
            logger.info("Press Ctrl+C to stop")
            
            while True:
                # Get status
                if mt5_integration.mt5_controller:
                    status = mt5_integration.mt5_controller.get_status()
                    
                    # Display account information
                    account_info = mt5_integration.mt5_controller.connector.get_account_info()
                    if account_info:
                        logger.info(f"Account Balance: {account_info.get('balance', 0)}")
                        logger.info(f"Account Equity: {account_info.get('equity', 0)}")
                    
                    # Display active trades
                    active_trades = status.get('active_trades', [])
                    if active_trades:
                        logger.info(f"Active trades: {len(active_trades)}")
                        for trade in active_trades:
                            logger.info(f"Trade: {trade['symbol']} {trade['direction']} {trade['volume']} lots")
                    else:
                        logger.info("No active trades")
                    
                    # Display session stats
                    session_stats = status.get('session_stats', {})
                    if session_stats:
                        logger.info(f"Trades executed: {session_stats.get('trades_executed', 0)}")
                        logger.info(f"Win rate: {session_stats.get('win_rate', 0):.2%}")
                        logger.info(f"Total profit: {session_stats.get('total_profit', 0)}")
                
                # Sleep for 10 seconds
                time.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt detected, shutting down")
        
        # Stop MT5 trading
        logger.info("Stopping MT5 trading")
        mt5_integration.stop()
        
        logger.info("MT5 example application stopped")
        
    except Exception as e:
        logger.exception(f"Error in MT5 example application: {str(e)}")

if __name__ == "__main__":
    main()
