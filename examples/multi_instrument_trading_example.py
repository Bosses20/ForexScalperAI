"""
Multi-Instrument Trading Example
Demonstrates how to use the forex bot to trade both standard forex pairs
and Deriv synthetic indices simultaneously
"""

import sys
import asyncio
import pandas as pd
from datetime import datetime
import os
import time
from pathlib import Path
import yaml

# Add parent directory to path for imports
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

# Import bot components
from src.mt5.instrument_manager import InstrumentManager
from src.risk.risk_manager import RiskManager
from src.strategies.strategy_selector import StrategySelector
from src.mt5.connector import MT5Connector
from src.mt5.data_feed import MT5DataFeed
from src.execution.execution_engine import ExecutionEngine

async def main():
    """Example of automated trading with multiple instrument types"""
    try:
        print("\n===== Multi-Instrument Trading Example =====")
        print("Demonstrating forex pairs and synthetic indices trading")
        
        # Load configuration
        config_path = os.path.join(parent_dir, "config", "mt5_config.yaml")
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            
        print(f"✅ Configuration loaded from {config_path}")
        
        # Initialize MT5 connection
        mt5_config = config.get('mt5', {})
        connector = MT5Connector(
            login=mt5_config.get('login'),
            password=mt5_config.get('password'),
            server=mt5_config.get('server')
        )
        
        connected = await connector.connect()
        if not connected:
            print("❌ Failed to connect to MT5 terminal")
            return
            
        print("✅ Connected to MT5 terminal")
        account_info = await connector.get_account_info()
        print(f"Account: {account_info['login']}, Balance: ${account_info['balance']:.2f}")
        
        # Initialize instrument manager
        instrument_manager = InstrumentManager(config)
        print("✅ Instrument manager initialized")
        
        # Get active instruments
        active_instruments = instrument_manager.get_all_active_instruments()
        
        print(f"\nActive Trading Instruments ({len(active_instruments)}):")
        print("-" * 60)
        print(f"{'Instrument':<20} {'Type':<10} {'Subtype':<15} {'Min Lot':<10}")
        print("-" * 60)
        
        for instrument in active_instruments:
            instrument_name = instrument['name']
            instrument_type = instrument_manager.get_instrument_type(instrument_name)
            instrument_subtype = instrument_manager.get_synthetic_subtype(instrument_name) or 'N/A'
            min_lot = instrument_manager.get_min_lot_size(instrument_name)
            
            print(f"{instrument_name:<20} {instrument_type:<10} {instrument_subtype:<15} {min_lot:<10}")
        
        # Initialize MT5 data feed
        data_feed = MT5DataFeed(connector, config.get('data_feed', {}))
        print("\n✅ MT5 data feed initialized")
        
        # Initialize risk manager
        risk_manager = RiskManager(config.get('risk_management', {}))
        risk_manager.update_account_balance(account_info['balance'])
        print("✅ Risk manager initialized")
        
        # Initialize strategy selector
        strategy_selector = StrategySelector(config.get('strategy_selector', {}))
        print("✅ Strategy selector initialized")
        
        # Initialize execution engine
        execution_engine = ExecutionEngine(config.get('execution', {}), risk_manager)
        print("✅ Execution engine initialized")
        
        # Fetch market data for demo
        print("\nFetching market data for analysis...")
        
        # Get timeframes for analysis
        timeframes = config.get('trading', {}).get('timeframes', ['M1', 'M5'])
        primary_timeframe = config.get('trading', {}).get('strategy_timeframe', 'M5')
        
        # Sample a few instruments for demonstration
        sample_forex = instrument_manager.get_all_forex_pairs()[:2]  # Get first 2 forex pairs
        sample_synthetic = instrument_manager.get_all_synthetic_indices()[:2]  # Get first 2 synthetic indices
        
        sample_instruments = sample_forex + sample_synthetic
        
        # Create a data dictionary to store results
        instrument_data = {}
        
        # Fetch data for each instrument
        for instrument in sample_instruments:
            print(f"Fetching data for {instrument}...")
            instrument_type = instrument_manager.get_instrument_type(instrument)
            
            # Get data for primary timeframe
            data = await data_feed.get_historical_data(instrument, primary_timeframe, 100)
            
            if data is not None and not data.empty:
                instrument_data[instrument] = data
                print(f"  ✅ Received {len(data)} candles for {instrument}")
            else:
                print(f"  ❌ No data available for {instrument}")
        
        # Analyze market conditions and select strategies
        print("\nAnalyzing market conditions and selecting strategies:")
        print("-" * 60)
        print(f"{'Instrument':<20} {'Strategy':<25} {'Signal':<15}")
        print("-" * 60)
        
        all_signals = []
        
        for instrument, data in instrument_data.items():
            # Get instrument type
            instrument_type = instrument_manager.get_instrument_type(instrument)
            instrument_subtype = instrument_manager.get_synthetic_subtype(instrument) or None
            
            # Select best strategy for current market conditions
            best_strategy = strategy_selector.select_strategy(instrument, data)
            
            if best_strategy:
                # Simple simulation of strategy signal generation
                signal_type = "BUY" if data['close'].iloc[-1] > data['open'].iloc[-1] else "SELL"
                
                # Create signal object
                signal = {
                    'pair': instrument,
                    'type': signal_type,
                    'price': data['close'].iloc[-1],
                    'time': datetime.now(),
                    'strategy': best_strategy,
                    'instrument_type': instrument_type
                }
                
                if instrument_subtype:
                    signal['instrument_subtype'] = instrument_subtype
                
                # Set stop loss based on ATR if available, otherwise use fixed value
                if 'atr' in data.columns:
                    atr_value = data['atr'].iloc[-1]
                    sl_distance = atr_value * 1.5
                else:
                    sl_distance = 0.0010  # Fixed 10 pip distance for forex
                
                # Add stop loss to signal
                if signal_type == "BUY":
                    signal['stop_loss'] = signal['price'] - sl_distance
                else:
                    signal['stop_loss'] = signal['price'] + sl_distance
                
                all_signals.append(signal)
                print(f"{instrument:<20} {best_strategy:<25} {signal_type:<15}")
            else:
                print(f"{instrument:<20} {'No suitable strategy':<25} {'NONE':<15}")
        
        # Calculate position sizes
        print("\nCalculating position sizes based on risk management:")
        print("-" * 70)
        print(f"{'Instrument':<20} {'Signal':<10} {'Account Tier':<15} {'Risk %':<10} {'Position Size':<15}")
        print("-" * 70)
        
        for signal in all_signals:
            # Calculate position size
            position_size = risk_manager.calculate_position_size(signal, account_info['balance'])
            account_tier = risk_manager.get_account_tier(account_info['balance'])
            
            tier_info = risk_manager._get_account_tier(account_info['balance'])
            risk_percent = tier_info['risk_percent'] * 100
            
            print(f"{signal['pair']:<20} {signal['type']:<10} {account_tier:<15} {risk_percent:<10.2f}% {position_size:<15.2f}")
        
        # Show which trades would be executed
        print("\nTrades to be executed:")
        valid_trades = 0
        
        for signal in all_signals:
            # Calculate position size
            position_size = risk_manager.calculate_position_size(signal, account_info['balance'])
            
            # Validate trade
            is_valid = risk_manager.validate_trade(signal, position_size)
            
            if is_valid and position_size > 0:
                valid_trades += 1
                print(f"✅ EXECUTE: {signal['type']} {signal['pair']} at {signal['price']:.5f}, "
                      f"SL: {signal['stop_loss']:.5f}, Size: {position_size} lots")
            else:
                print(f"❌ REJECTED: {signal['type']} {signal['pair']} - Risk management rules")
        
        print(f"\nSummary: {valid_trades}/{len(all_signals)} trades approved by risk management")
        
        print("\n===== Multi-Instrument Trading Example Complete =====")
        
    except Exception as e:
        print(f"Error in example: {str(e)}")
    finally:
        # Disconnect from MT5
        if 'connector' in locals() and connector:
            await connector.disconnect()
            print("Disconnected from MT5")

if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
