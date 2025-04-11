#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Risk Management System Example
-------------------------------

This example demonstrates how to use the enhanced risk management system
with the different trading strategies. It showcases:

1. Account-based position sizing tiers
2. Advanced risk controls (correlation, spread, drawdown)
3. Multiple stop loss and take profit strategies
4. Position aging and re-evaluation
"""

import os
import sys
import time
from datetime import datetime, timedelta
import argparse
import numpy as np
import matplotlib.pyplot as plt

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import required modules
from src.mt5.integration import MT5Connector
from src.mt5.strategies import create_strategy
from src.mt5.backtester import MT5Backtester
from src.risk.risk_manager import RiskManager
import pandas as pd
import yaml
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/risk_management_{time}.log", rotation="500 MB", level="DEBUG")


def load_config():
    """Load configuration from the YAML file"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'mt5_config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)


def demonstration_with_multiple_strategies():
    """
    Demonstrate the risk management system with multiple strategies
    """
    try:
        # Load configuration
        config = load_config()
        risk_config = config.get('risk_management', {})
        
        # Initialize risk manager
        risk_manager = RiskManager(risk_config)
        
        # Connect to MT5
        mt5_config = config.get('mt5', {})
        connector = MT5Connector(
            login=mt5_config.get('login'),
            password=mt5_config.get('password'),
            server=mt5_config.get('server'),
            path=mt5_config.get('terminal_path')
        )
        
        # Check if connection was successful
        if not connector.initialize():
            logger.error("Failed to initialize MT5 connection")
            return
        
        # Get account information
        account_info = connector.get_account_info()
        account_balance = account_info.balance
        
        # Update risk manager with account balance
        risk_manager.update_account_balance(account_balance)
        
        logger.info(f"Account Balance: {account_balance}")
        logger.info(f"Account Tier: {risk_manager._get_account_tier(account_balance)}")
        
        # Define pairs to analyze
        pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD']
        timeframe = 'M15'  # 15-minute timeframe
        
        # Initialize strategies - using one of each type for demonstration
        strategies = {
            'break_and_retest': create_strategy('break_and_retest', config.get('break_and_retest', {})),
            'break_of_structure': create_strategy('break_of_structure', config.get('break_of_structure', {})),
            'fair_value_gap': create_strategy('fair_value_gap', config.get('fair_value_gap', {})),
            'jhook_pattern': create_strategy('jhook_pattern', config.get('jhook_pattern', {}))
        }
        
        # Dictionary to track signal sources
        signals_by_pair = {}
        
        # Analyze each pair with each strategy
        for pair in pairs:
            # Get historical data
            data = connector.get_historical_data(
                symbol=pair,
                timeframe=timeframe,
                bars=500  # Get 500 bars of historical data
            )
            
            # Continue only if we have data
            if data is None or len(data) < 50:
                logger.warning(f"Insufficient data for {pair}")
                continue
                
            # Calculate ATR for stop loss
            data['tr'] = calculate_tr(data)
            data['atr'] = data['tr'].rolling(window=14).mean()
            current_atr = data['atr'].iloc[-1]
            
            # Update spread information in risk manager
            current_spread = connector.get_spread(pair)
            risk_manager.update_spread_data(pair, current_spread)
            
            logger.info(f"Analyzing {pair} with spread: {current_spread} pips")
            
            # Analyze with each strategy
            for strategy_name, strategy in strategies.items():
                logger.info(f"Applying {strategy_name} strategy to {pair}")
                
                # Get signals from strategy
                signals = strategy.analyze(pair, data)
                
                # Process signals if any
                if signals and signals.get('signal') in ['buy', 'sell']:
                    # Store which strategy generated the signal
                    if pair not in signals_by_pair:
                        signals_by_pair[pair] = []
                    
                    signals_by_pair[pair].append({
                        'strategy': strategy_name,
                        'signal': signals
                    })
                    
                    logger.info(f"Signal generated for {pair} by {strategy_name}: {signals['signal']}")
        
        # Process all signals with risk management
        process_signals_with_risk_management(risk_manager, signals_by_pair, account_balance, connector)
        
        # Demo trade management
        demo_trade_management(risk_manager, connector)
        
        # Close the MT5 connection
        connector.shutdown()
        
        logger.info("Risk management demonstration completed")
        
    except Exception as e:
        logger.exception(f"Error in risk management demonstration: {e}")


def process_signals_with_risk_management(risk_manager, signals_by_pair, account_balance, connector):
    """
    Process trading signals through risk management system
    
    Args:
        risk_manager: Risk manager instance
        signals_by_pair: Dictionary of signals by pair
        account_balance: Current account balance
        connector: MT5 connector instance
    """
    logger.info("Processing signals through risk management...")
    
    # Counters for statistics
    total_signals = 0
    valid_signals = 0
    rejected_signals = 0
    rejected_reasons = {}
    
    # Process each pair
    for pair, signals in signals_by_pair.items():
        # Get ATR for pair
        data = connector.get_historical_data(
            symbol=pair,
            timeframe='M15',
            bars=50  # Get 50 bars of historical data
        )
        
        # Calculate ATR
        data['tr'] = calculate_tr(data)
        data['atr'] = data['tr'].rolling(window=14).mean()
        current_atr = data['atr'].iloc[-1]
        
        # Get current spread
        current_spread = connector.get_spread(pair)
        
        for signal_data in signals:
            total_signals += 1
            strategy_name = signal_data['strategy']
            signal = signal_data['signal']
            
            # Add spread to signal
            signal['spread'] = current_spread
            
            # Calculate position size based on risk management
            position_size = risk_manager.calculate_position_size(signal, account_balance)
            
            # Validate trade through risk filters
            if risk_manager.validate_trade(signal, position_size):
                valid_signals += 1
                logger.info(f"VALID TRADE: {pair} {signal['signal']} - Size: {position_size} lots")
                
                # Demo - Apply different stop loss strategies
                stop_loss = risk_manager.apply_stop_loss_strategy(signal, 'atr', current_atr)
                signal['stop_loss'] = stop_loss
                
                # Demo - Apply different take profit strategies
                take_profit_config = risk_manager.apply_take_profit_strategy(signal, 'multiple', 2.0)
                
                # Log trade details
                logger.info(f"Trade details for {pair}:")
                logger.info(f"  Entry: {signal['price']}")
                logger.info(f"  Stop Loss: {stop_loss}")
                if 'take_profit' in take_profit_config:
                    logger.info(f"  Take Profit: {take_profit_config['take_profit']}")
                elif 'take_profit_1' in take_profit_config and 'take_profit_2' in take_profit_config:
                    logger.info(f"  Take Profit 1: {take_profit_config['take_profit_1']} ({take_profit_config['tp1_size']*100}%)")
                    logger.info(f"  Take Profit 2: {take_profit_config['take_profit_2']} ({(1-take_profit_config['tp1_size'])*100}%)")
                
                # In a real system, we would execute the trade here
                # For demo, we'll just register the trade in the risk manager
                trade = {
                    'pair': pair,
                    'direction': signal['signal'],
                    'entry_price': signal['price'],
                    'stop_loss': stop_loss,
                    'position_size': position_size,
                    'entry_time': datetime.now(),
                    'strategy': strategy_name
                }
                
                # Add take profit details
                trade.update(take_profit_config)
                
                # Register trade with risk manager
                risk_manager.register_trade(trade)
                
            else:
                rejected_signals += 1
                reason = "General risk control"
                
                # Try to identify specific rejection reason
                if position_size <= 0:
                    reason = "Position size too small"
                elif pair in risk_manager.active_trades:
                    reason = "Already have active trade for pair"
                elif risk_manager.trading_disabled:
                    reason = f"Trading disabled: {risk_manager.trading_disabled_reason}"
                elif current_spread > (risk_manager.average_spreads.get(pair, 0) * risk_manager.max_spread_multiplier):
                    reason = "Spread too wide"
                    
                # Count rejection reasons
                if reason not in rejected_reasons:
                    rejected_reasons[reason] = 0
                rejected_reasons[reason] += 1
                
                logger.warning(f"REJECTED TRADE: {pair} {signal['signal']} - Reason: {reason}")
    
    # Log statistics
    logger.info(f"Signal processing complete:")
    logger.info(f"  Total signals: {total_signals}")
    logger.info(f"  Valid trades: {valid_signals}")
    logger.info(f"  Rejected trades: {rejected_signals}")
    logger.info("  Rejection reasons:")
    for reason, count in rejected_reasons.items():
        logger.info(f"    - {reason}: {count}")


def demo_trade_management(risk_manager, connector):
    """
    Demonstrate trade management features including position aging and re-evaluation
    
    Args:
        risk_manager: Risk manager instance
        connector: MT5 connector instance
    """
    if not risk_manager.active_trades:
        logger.info("No active trades to demonstrate trade management")
        return
    
    logger.info("Demonstrating trade management features...")
    
    # Simulate the passage of time for position aging
    logger.info("Simulating position aging check...")
    # This is just a demo - in a real scenario, we would check regularly
    aged_positions = risk_manager.check_aged_positions()
    
    if aged_positions:
        logger.info(f"Found {len(aged_positions)} aged positions that would be closed")
        for pair in aged_positions:
            logger.info(f"Position {pair} would be closed due to age limit")
    else:
        logger.info("No aged positions found")
    
    # Demonstrate re-evaluation of positions
    logger.info("Demonstrating position re-evaluation...")
    
    for pair, trade in list(risk_manager.active_trades.items()):
        # Get current price
        current_price = connector.get_current_price(pair)
        
        if current_price:
            # Update trade metrics with current price
            risk_manager.update_trade(pair, current_price)
            
            # Re-evaluate position
            action = risk_manager.re_evaluate_position(pair, current_price)
            
            logger.info(f"Re-evaluation of {pair} recommends: {action}")
            
            # Demonstrate what would happen based on the recommendation
            if action == 'close':
                logger.info(f"Would close position for {pair} based on re-evaluation")
                # In a real system: risk_manager.close_trade(pair, current_price, "re-evaluation")
            elif action == 'adjust_sl':
                logger.info(f"Would adjust stop loss to breakeven for {pair}")
                # In a real system: Modify stop loss
            elif action == 'adjust_tp':
                logger.info(f"Would enable trailing stop for {pair}")
                # In a real system: Enable trailing stop
            
            # Log current trade metrics
            trade_updated = risk_manager.active_trades[pair]
            logger.info(f"Current metrics for {pair}:")
            logger.info(f"  Entry: {trade_updated['entry_price']}")
            logger.info(f"  Current: {current_price}")
            
            # Show profit/loss if available
            if 'current_pnl_pips' in trade_updated and 'current_pnl_money' in trade_updated:
                logger.info(f"  P/L: {trade_updated['current_pnl_pips']:.1f} pips (${trade_updated['current_pnl_money']:.2f})")


def calculate_tr(data):
    """
    Calculate True Range for ATR
    
    Args:
        data: DataFrame with OHLC data
        
    Returns:
        Series with True Range values
    """
    high_low = data['high'] - data['low']
    high_close_prev = abs(data['high'] - data['close'].shift(1))
    low_close_prev = abs(data['low'] - data['close'].shift(1))
    
    tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    return tr


def visualize_risk_performance(risk_manager):
    """
    Visualize risk management performance metrics
    
    Args:
        risk_manager: Risk manager instance
    """
    # Get performance metrics
    metrics = risk_manager.get_performance_metrics()
    
    if not metrics:
        logger.warning("No performance metrics available for visualization")
        return
    
    # Create a figure with multiple subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Plot 1: Equity curve
    if 'equity_curve' in metrics:
        axes[0, 0].plot(metrics['equity_curve'])
        axes[0, 0].set_title('Equity Curve')
        axes[0, 0].set_xlabel('Trades')
        axes[0, 0].set_ylabel('Account Balance')
        axes[0, 0].grid(True)
    
    # Plot 2: Win/Loss distribution
    if 'total_trades' in metrics and metrics['total_trades'] > 0:
        win_rate = metrics.get('win_rate', 0)
        loss_rate = 100 - win_rate
        axes[0, 1].bar(['Win', 'Loss'], [win_rate, loss_rate], color=['green', 'red'])
        axes[0, 1].set_title('Win/Loss Distribution')
        axes[0, 1].set_ylabel('Percentage (%)')
        axes[0, 1].set_ylim(0, 100)
        axes[0, 1].grid(True)
    
    # Plot 3: Trade duration
    if 'avg_winning_duration_seconds' in metrics and 'avg_losing_duration_seconds' in metrics:
        # Convert to minutes for readability
        win_duration = metrics['avg_winning_duration_seconds'] / 60
        lose_duration = metrics['avg_losing_duration_seconds'] / 60
        
        axes[1, 0].bar(['Winning Trades', 'Losing Trades'], [win_duration, lose_duration], 
                      color=['green', 'red'])
        axes[1, 0].set_title('Average Trade Duration')
        axes[1, 0].set_ylabel('Minutes')
        axes[1, 0].grid(True)
    
    # Plot 4: Drawdown
    if 'max_drawdown' in metrics:
        axes[1, 1].bar(['Maximum Drawdown'], [metrics['max_drawdown']], color='orange')
        axes[1, 1].set_title('Maximum Drawdown')
        axes[1, 1].set_ylabel('Percentage (%)')
        axes[1, 1].grid(True)
        # Add warning line at 15%
        axes[1, 1].axhline(y=15, color='r', linestyle='--', label='Circuit Breaker (15%)')
        axes[1, 1].legend()
    
    plt.tight_layout()
    plt.savefig('risk_performance.png')
    logger.info("Risk performance visualization saved to 'risk_performance.png'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Risk Management System Example')
    parser.add_argument('--visualize', action='store_true', help='Visualize risk performance metrics')
    args = parser.parse_args()
    
    if args.visualize:
        # Load saved risk manager and visualize
        # This would require loading from a persistent storage in a real system
        # For the demo, we would run the main function first
        demonstration_with_multiple_strategies()
        
        # Get the risk manager from global variables or reload
        # For this example, we just reference the risk manager from the demonstration
        try:
            # This is just for demonstration
            config = load_config()
            risk_config = config.get('risk_management', {})
            risk_manager = RiskManager(risk_config)
            visualize_risk_performance(risk_manager)
        except Exception as e:
            logger.exception(f"Error visualizing risk performance: {e}")
    else:
        # Run the main demonstration
        demonstration_with_multiple_strategies()
