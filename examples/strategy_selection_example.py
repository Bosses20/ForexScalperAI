"""
Strategy Selection Example

This script demonstrates how the trading bot automatically analyzes market conditions
and selects the optimal trading strategy for the current environment.

It showcases the ability of the bot to:
1. Analyze market conditions (volatility, trend strength, market type)
2. Select the best-suited strategy based on these conditions
3. Work with accounts of all sizes, including very small balances
"""

import sys
import os
import time
import pandas as pd
from datetime import datetime
import yaml
from loguru import logger

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import local modules
from src.data.market_data import MarketDataFeed
from src.strategies.strategy_selector import StrategySelector
from src.risk.risk_manager import RiskManager

# Setup logging
logger.remove()
logger.add(sys.stdout, format="{time:HH:mm:ss} | {level: <8} | {message}", level="INFO")

def load_config(config_path="config/mt5_config.yaml"):
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return None

def simulate_different_market_conditions(market_data, symbol):
    """
    Demonstrate strategy selection across various market conditions
    by simulating different market environments
    """
    logger.info("\n" + "="*80)
    logger.info("SIMULATING DIFFERENT MARKET CONDITIONS FOR STRATEGY SELECTION")
    logger.info("="*80)
    
    # Get real market data as baseline
    timeframe = "H1"
    data = market_data.get_historical_data(symbol, timeframe, 200)
    if data is None or len(data) < 100:
        logger.error(f"Insufficient data for {symbol} on {timeframe} timeframe")
        return
    
    # Create data variants for different market conditions
    market_conditions = {
        "Current Market": data.copy(),
        "Strong Uptrend": create_trending_data(data.copy(), direction="up", strength=1.5),
        "Strong Downtrend": create_trending_data(data.copy(), direction="down", strength=1.5),
        "Ranging Market": create_ranging_data(data.copy()),
        "High Volatility": create_volatility_data(data.copy(), multiplier=2.0),
        "Low Volatility": create_volatility_data(data.copy(), multiplier=0.5)
    }
    
    # Initialize strategy selector
    config = load_config()
    strategy_selector = StrategySelector(config.get('strategy_selector', {}))
    
    # Test strategy selection for each market condition
    for condition_name, condition_data in market_conditions.items():
        logger.info(f"\nTesting strategy selection for: {condition_name}")
        
        # Calculate some basic metrics to characterize the market condition
        if len(condition_data) > 20:
            volatility = calculate_volatility(condition_data)
            trend_strength = calculate_trend_strength(condition_data)
            
            logger.info(f"Market metrics - Volatility: {volatility:.6f}, Trend Strength: {trend_strength:.2f}")
            
            # Select the best strategy for this condition
            best_strategy = strategy_selector.select_strategy(symbol, condition_data)
            
            if best_strategy:
                logger.info(f"Selected strategy: {best_strategy}")
                
                # Get the strategy instance
                strategy_instance = strategy_selector.get_strategy_instance(best_strategy)
                
                # Get trading signal if available
                if strategy_instance:
                    signal = strategy_instance.analyze(symbol, condition_data)
                    if signal:
                        logger.info(f"Generated signal: {signal['signal']} at price {signal['price']}")
                        
                        # Demonstrate how this works with different account sizes
                        demonstrate_position_sizing(signal, config)
            else:
                logger.warning("No suitable strategy found for this market condition")
        else:
            logger.warning("Insufficient data for analysis")

def create_trending_data(data, direction="up", strength=1.5):
    """Create a dataset with a stronger trend"""
    trend_data = data.copy()
    
    # Add a stronger trend component
    n = len(trend_data)
    trend = pd.Series([(i/n) * strength for i in range(n)], index=trend_data.index)
    
    if direction == "down":
        trend = -trend
    
    # Apply the trend to close prices while maintaining the same OHLC relationships
    base_close = trend_data['close'].iloc[0]
    trend_values = base_close * (1 + trend)
    
    # Calculate ratio to maintain OHLC relationships
    ratio = trend_values / trend_data['close']
    
    # Apply ratio to all OHLC prices
    trend_data['open'] = trend_data['open'] * ratio
    trend_data['high'] = trend_data['high'] * ratio  
    trend_data['low'] = trend_data['low'] * ratio
    trend_data['close'] = trend_values
    
    return trend_data

def create_ranging_data(data):
    """Create a dataset with a ranging market (oscillating prices)"""
    ranging_data = data.copy()
    
    # Create an oscillating component
    n = len(ranging_data)
    cycles = 8  # Number of complete cycles
    oscillation = pd.Series([0.01 * np.sin(i/n * cycles * 2 * np.pi) for i in range(n)], 
                           index=ranging_data.index)
    
    # Apply oscillation to maintain OHLC relationships
    base_close = ranging_data['close'].iloc[0]
    osc_values = base_close * (1 + oscillation)
    
    # Calculate ratio to maintain OHLC relationships
    ratio = osc_values / ranging_data['close']
    
    # Apply ratio to all OHLC prices
    ranging_data['open'] = ranging_data['open'] * ratio
    ranging_data['high'] = ranging_data['high'] * ratio  
    ranging_data['low'] = ranging_data['low'] * ratio
    ranging_data['close'] = osc_values
    
    return ranging_data

def create_volatility_data(data, multiplier=2.0):
    """Create a dataset with different volatility level"""
    vol_data = data.copy()
    
    # Base line (typical price)
    typical_price = (vol_data['high'] + vol_data['low'] + vol_data['close']) / 3
    
    # Adjust high and low to increase/decrease volatility
    vol_data['high'] = typical_price + ((vol_data['high'] - typical_price) * multiplier)
    vol_data['low'] = typical_price - ((typical_price - vol_data['low']) * multiplier)
    
    return vol_data

def calculate_volatility(data, window=14):
    """Calculate volatility as average true range percentage"""
    high = data['high']
    low = data['low']
    close = data['close'].shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)
    
    tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    atr = tr.rolling(window=window).mean().iloc[-1]
    
    return atr / data['close'].iloc[-1]

def calculate_trend_strength(data, window=14):
    """Calculate a simple trend strength indicator (simplified ADX)"""
    # Calculate directional movement
    plus_dm = data['high'].diff()
    minus_dm = data['low'].diff(-1)
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    # Calculate true range
    tr = pd.DataFrame({
        'hl': data['high'] - data['low'],
        'hc': abs(data['high'] - data['close'].shift(1)),
        'lc': abs(data['low'] - data['close'].shift(1))
    }).max(axis=1)
    
    # Average values
    tr14 = tr.rolling(window=window).mean()
    plus_di14 = 100 * (plus_dm.rolling(window=window).mean() / tr14)
    minus_di14 = 100 * (minus_dm.rolling(window=window).mean() / tr14)
    
    # Calculate ADX
    dx = 100 * abs(plus_di14 - minus_di14) / (plus_di14 + minus_di14)
    adx = dx.rolling(window=window).mean()
    
    return adx.iloc[-1] / 100  # Return normalized 0-1 value

def demonstrate_position_sizing(signal, config):
    """Demonstrate position sizing for accounts of various sizes"""
    # Initialize risk manager
    risk_manager = RiskManager(config.get('risk_management', {}))
    
    # Define account sizes to test
    account_sizes = [10, 50, 100, 500, 1000, 5000, 10000]
    
    logger.info("\nDemonstrating position sizing for different account balances:")
    logger.info("-" * 70)
    logger.info(f"{'Account Size':15} | {'Position Size':15} | {'Risk Amount':15} | {'Account Tier':15}")
    logger.info("-" * 70)
    
    for account_size in account_sizes:
        # Calculate position size
        position_size = risk_manager.calculate_position_size(signal, account_size)
        
        # Determine account tier
        account_tier = risk_manager.get_account_tier(account_size)
        
        # Calculate risk amount
        risk_params = risk_manager.account_tiers[account_tier]
        risk_amount = account_size * risk_params['risk_percent']
        
        logger.info(f"${account_size:<14,.2f} | {position_size:<15.3f} | ${risk_amount:<14,.2f} | {account_tier:<15}")
    
    logger.info("-" * 70)

def main():
    """Main execution function"""
    logger.info("Strategy Selection Example - Starting")
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return
    
    try:
        # Connect to market data feed
        market_data = MarketDataFeed(config.get('data_feed', {}))
        connected = market_data.connect()
        
        if not connected:
            logger.error("Failed to connect to MarketDataFeed")
            return
        
        logger.info("Connected to MarketDataFeed successfully")
        
        # Use EURUSD as example symbol
        symbol = "EURUSD"
        
        # Run the strategy selection demonstration
        simulate_different_market_conditions(market_data, symbol)
        
        # Clean up
        market_data.disconnect()
        logger.info("Strategy Selection Example - Completed")
        
    except Exception as e:
        logger.exception(f"Error in main execution: {e}")
    
if __name__ == "__main__":
    # Fix for numpy import
    import numpy as np
    
    main()
