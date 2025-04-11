"""
Break and Retest Strategy Example
Demonstrates how to use the Break and Retest strategy with MT5 integration
"""

import os
import sys
import time
import yaml
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required modules
from src.mt5.connector import MT5Connector
from src.mt5.data_feed import MT5DataFeed
from src.mt5.strategies import BreakAndRetest, create_strategy
from src.mt5.backtester import MT5Backtester

def load_config():
    """Load MT5 configuration"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              "config", "mt5_config.yaml")
    
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    
    return config

def test_strategy_with_live_data():
    """Test the Break and Retest strategy with live MT5 data"""
    # Configure logging
    logger.add("logs/break_retest_test.log", rotation="10 MB", level="INFO")
    logger.info("Starting Break and Retest strategy test with live data")
    
    # Load configuration
    config = load_config()
    strategy_config = config['strategies']['break_and_retest']
    
    try:
        # Initialize MT5 connector
        logger.info("Initializing MT5 connector")
        connector = MT5Connector(config['mt5'])
        
        if not connector.connect():
            logger.error("Failed to connect to MT5")
            return
        
        # Initialize data feed
        logger.info("Initializing MT5 data feed")
        data_feed = MT5DataFeed(connector, config['data_feed'])
        
        if not data_feed.initialize():
            logger.error("Failed to initialize data feed")
            connector.disconnect()
            return
        
        # Initialize strategy
        logger.info("Initializing Break and Retest strategy")
        strategy = BreakAndRetest(strategy_config)
        
        # Test symbols
        symbols = strategy_config.get('symbols', ["EURUSD"])
        timeframe = strategy_config.get('timeframe', "M5")
        
        logger.info(f"Testing strategy on {symbols} with {timeframe} timeframe")
        
        # Main test loop
        try:
            for i in range(10):  # Test for 10 iterations
                logger.info(f"Test iteration {i+1}")
                
                # Fetch latest data for each symbol
                market_data = {}
                for symbol in symbols:
                    # Get historical data
                    bars = data_feed.get_bars(symbol, timeframe, 500)
                    if bars is not None and len(bars) > 0:
                        market_data[symbol] = bars
                        logger.info(f"Fetched {len(bars)} bars for {symbol}")
                    else:
                        logger.warning(f"No data available for {symbol}")
                
                # Analyze data with strategy
                for symbol, data in market_data.items():
                    # Run strategy analysis
                    signal = strategy.analyze(symbol, data)
                    
                    # Log the results
                    if signal['signal'] != 'none':
                        logger.info(f"Signal generated for {symbol}: {signal['signal']}")
                        logger.info(f"Entry price: {signal['entry_price']}, Stop loss: {signal['stop_loss']}, Take profit: {signal['take_profit']}")
                    else:
                        logger.info(f"No signal for {symbol}")
                
                # Wait before next iteration
                time.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
        
        # Cleanup
        connector.disconnect()
        logger.info("Test completed")
        
    except Exception as e:
        logger.exception(f"Error during test: {str(e)}")

def backtest_strategy():
    """Run backtesting for the Break and Retest strategy"""
    # Configure logging
    logger.add("logs/break_retest_backtest.log", rotation="10 MB", level="INFO")
    logger.info("Starting Break and Retest strategy backtest")
    
    # Load configuration
    config = load_config()
    strategy_config = config['strategies']['break_and_retest']
    
    try:
        # Initialize MT5 connector
        logger.info("Initializing MT5 connector")
        connector = MT5Connector(config['mt5'])
        
        if not connector.connect():
            logger.error("Failed to connect to MT5")
            return
        
        # Initialize strategy
        logger.info("Initializing Break and Retest strategy")
        strategy = BreakAndRetest(strategy_config)
        
        # Test symbols and parameters
        symbols = strategy_config.get('symbols', ["EURUSD"])
        timeframe = strategy_config.get('timeframe', "M5")
        
        # Initialize backtester
        backtester = MT5Backtester(connector, config.get('backtesting', {}))
        
        # Set backtest period (last 3 months)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        # Run backtest for each symbol
        for symbol in symbols:
            logger.info(f"Running backtest for {symbol} on {timeframe} timeframe")
            
            # Run the backtest
            results = backtester.run_backtest(
                strategy=strategy,
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                initial_deposit=10000,
                leverage=100
            )
            
            # Log results
            if results:
                logger.info(f"Backtest results for {symbol}:")
                logger.info(f"Total trades: {results['total_trades']}")
                logger.info(f"Win rate: {results['win_rate']:.2%}")
                logger.info(f"Profit factor: {results['profit_factor']:.2f}")
                logger.info(f"Net profit: {results['net_profit']:.2f}")
                logger.info(f"Max drawdown: {results['max_drawdown']:.2%}")
                logger.info("-----------------------------------")
            else:
                logger.warning(f"No backtest results for {symbol}")
        
        # Cleanup
        connector.disconnect()
        logger.info("Backtest completed")
        
    except Exception as e:
        logger.exception(f"Error during backtest: {str(e)}")

if __name__ == "__main__":
    print("Break and Retest Strategy Example")
    print("1. Test with live data")
    print("2. Run backtest")
    
    choice = input("Select option (1-2): ")
    
    if choice == "1":
        test_strategy_with_live_data()
    elif choice == "2":
        backtest_strategy()
    else:
        print("Invalid option")
