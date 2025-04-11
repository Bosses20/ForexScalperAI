#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
JHook Pattern Strategy Example
------------------------------------

This example demonstrates how to use the JHook Pattern strategy
with either live data or backtesting.

The JHook pattern identifies institutional liquidity zones and strong resumption of trend.
It consists of:
1. Initial trend move
2. Retracement phase (forming the hook)
3. Consolidation period
4. Breakout in the direction of the original trend
"""

import os
import sys
import time
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import required modules
from src.mt5.integration import MT5Connector
from src.mt5.strategies import create_strategy
from src.mt5.backtester import MT5Backtester
import pandas as pd
import yaml
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/jhook_pattern_{time}.log", rotation="500 MB", level="DEBUG")


def load_config():
    """Load configuration from the YAML file"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'mt5_config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)


def test_live_strategy():
    """Test the JHook Pattern strategy with live data"""
    try:
        # Load configuration
        config = load_config()
        
        # Create MT5 connector and connect to the broker
        connector = MT5Connector(config['broker'])
        connected = connector.connect()
        
        if not connected:
            logger.error("Failed to connect to MT5")
            return
        
        logger.info("Connected to MT5 successfully")
        
        # Create JHook Pattern strategy
        strategy_config = config['strategies']['jhook_pattern']
        strategy_config['name'] = 'JHook Pattern Live Test'
        
        # Set timeframes and symbols
        # JHook works best on higher timeframes
        timeframe = "M15"  # Using 15-minute timeframe for testing
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        
        # Create strategy instance
        jhook_strategy = create_strategy('jhook_pattern', strategy_config)
        
        # Initialize data feed
        data_feed = connector.get_data_feed()
        
        try:
            # Main loop for live testing
            logger.info(f"Starting live testing with JHook Pattern strategy on {symbols}")
            
            while True:
                for symbol in symbols:
                    # Get latest data
                    bars = 100  # Need enough history for pattern detection
                    data = data_feed.get_rates(symbol, timeframe, bars)
                    
                    if data is None or len(data) < bars:
                        logger.warning(f"Not enough data for {symbol}, skipping")
                        continue
                    
                    # Analyze with the strategy
                    signal = jhook_strategy.analyze(symbol, data)
                    
                    # Log the results
                    if signal['signal'] != 'none':
                        logger.info(f"Signal generated for {symbol}: {signal['signal']}")
                        logger.info(f"Entry price: {signal['entry_price']}, Stop loss: {signal['stop_loss']}, Take profit: {signal['take_profit']}")
                        
                        # Log pattern details if available
                        if 'pattern_details' in signal:
                            pattern = signal['pattern_details']
                            logger.info(f"Pattern type: {signal['pattern']}")
                            logger.info(f"Initial move: {pattern['initial_move']:.2f} pips, Retracement: {pattern['retracement']:.2f}")
                            logger.info(f"Consolidation range: {pattern['consolidation_low']:.5f} to {pattern['consolidation_high']:.5f}")
                    else:
                        logger.debug(f"No signal for {symbol}")
                
                # Wait before next iteration
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
        
        # Cleanup
        connector.disconnect()
        logger.info("Test completed")
        
    except Exception as e:
        logger.exception(f"Error during test: {str(e)}")


def backtest_strategy():
    """Run backtesting for the JHook Pattern strategy"""
    try:
        # Load configuration
        config = load_config()
        
        # Create MT5 connector and connect to the broker
        connector = MT5Connector(config['broker'])
        connected = connector.connect()
        
        if not connected:
            logger.error("Failed to connect to MT5")
            return
        
        logger.info("Connected to MT5 successfully")
        
        # Create JHook Pattern strategy
        strategy_config = config['strategies']['jhook_pattern']
        strategy_config['name'] = 'JHook Pattern Backtest'
        
        # Set backtest parameters
        symbol = "EURUSD"
        timeframe = "M15"
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        # Create strategy instance
        jhook_strategy = create_strategy('jhook_pattern', strategy_config)
        
        # Create backtester
        backtester = MT5Backtester(connector, jhook_strategy)
        
        # Run backtest
        logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")
        results = backtester.run(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_balance=10000,
            lot_size=0.1,
            spread=2.0
        )
        
        # Log results
        logger.info("Backtest completed")
        logger.info(f"Total trades: {results['total_trades']}")
        logger.info(f"Profitable trades: {results['profitable_trades']}")
        logger.info(f"Win rate: {results['win_rate']:.2f}%")
        logger.info(f"Net profit: {results['net_profit']:.2f}")
        logger.info(f"Max drawdown: {results['max_drawdown']:.2f}%")
        
        # Generate performance visualization
        if 'equity_curve' in results:
            equity_curve = results['equity_curve']
            equity_curve.plot(title="Equity Curve")
            
            # Save plot to file
            import matplotlib.pyplot as plt
            plt.savefig("jhook_equity_curve.png")
            logger.info("Equity curve saved to jhook_equity_curve.png")
            
            # Plot trade distribution
            if 'trade_times' in results:
                plt.figure(figsize=(12, 6))
                plt.hist(results['trade_times'], bins=24)
                plt.title("Trade Distribution by Hour")
                plt.xlabel("Hour of Day")
                plt.ylabel("Number of Trades")
                plt.savefig("jhook_trade_distribution.png")
                logger.info("Trade distribution saved to jhook_trade_distribution.png")
        
        # Cleanup
        connector.disconnect()
        
    except Exception as e:
        logger.exception(f"Error during backtest: {str(e)}")


def optimize_parameters():
    """
    Optimize the parameters for the JHook Pattern strategy.
    This is a simple implementation that tests a grid of parameter combinations.
    """
    try:
        # Load configuration
        config = load_config()
        
        # Create MT5 connector and connect to the broker
        connector = MT5Connector(config['broker'])
        connected = connector.connect()
        
        if not connected:
            logger.error("Failed to connect to MT5")
            return
        
        logger.info("Connected to MT5 successfully")
        
        # Base strategy configuration
        base_config = config['strategies']['jhook_pattern'].copy()
        
        # Set backtest parameters
        symbol = "EURUSD"
        timeframe = "M15"
        start_date = datetime.now() - timedelta(days=60)
        end_date = datetime.now() - timedelta(days=30)  # Use most recent 30 days for verification
        
        # Parameters to optimize
        trend_strength_values = [5, 10, 15]
        retracement_threshold_values = [0.382, 0.5, 0.618]
        consolidation_periods_values = [3, 5, 7]
        
        best_result = {
            'net_profit': -float('inf'),
            'params': {}
        }
        
        # Simple grid search
        for trend_strength in trend_strength_values:
            for retracement_threshold in retracement_threshold_values:
                for consolidation_periods in consolidation_periods_values:
                    # Update config with parameters to test
                    test_config = base_config.copy()
                    test_config['trend_strength'] = trend_strength
                    test_config['retracement_threshold'] = retracement_threshold
                    test_config['consolidation_periods'] = consolidation_periods
                    
                    # Create strategy with these parameters
                    strategy = create_strategy('jhook_pattern', test_config)
                    
                    # Create backtester
                    backtester = MT5Backtester(connector, strategy)
                    
                    # Run backtest
                    logger.info(f"Testing parameters: trend_strength={trend_strength}, "
                                f"retracement_threshold={retracement_threshold}, "
                                f"consolidation_periods={consolidation_periods}")
                    
                    results = backtester.run(
                        symbol=symbol,
                        timeframe=timeframe,
                        start_date=start_date,
                        end_date=end_date,
                        initial_balance=10000,
                        lot_size=0.1,
                        spread=2.0
                    )
                    
                    # Track best parameters
                    if results['net_profit'] > best_result['net_profit']:
                        best_result['net_profit'] = results['net_profit']
                        best_result['params'] = {
                            'trend_strength': trend_strength,
                            'retracement_threshold': retracement_threshold,
                            'consolidation_periods': consolidation_periods,
                            'win_rate': results['win_rate'],
                            'total_trades': results['total_trades']
                        }
                        
                    logger.info(f"Result: net_profit={results['net_profit']:.2f}, "
                                f"win_rate={results['win_rate']:.2f}%, "
                                f"trades={results['total_trades']}")
        
        # Log best parameters
        logger.info("Optimization completed")
        logger.info(f"Best parameters: {best_result['params']}")
        logger.info(f"Best net profit: {best_result['net_profit']:.2f}")
        
        # Cleanup
        connector.disconnect()
        
    except Exception as e:
        logger.exception(f"Error during optimization: {str(e)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="JHook Pattern Strategy Example")
    parser.add_argument("--mode", choices=["live", "backtest", "optimize"], default="live",
                        help="Test mode: live, backtest, or optimize")
    args = parser.parse_args()
    
    if args.mode == "live":
        test_live_strategy()
    elif args.mode == "backtest":
        backtest_strategy()
    else:
        optimize_parameters()
