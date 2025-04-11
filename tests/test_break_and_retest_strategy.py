"""
Break and Retest Strategy Test Module

This module contains tests for the Break and Retest strategy functionality,
ensuring proper signal generation and risk management.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategies.break_and_retest_strategy import BreakAndRetestStrategy


class TestBreakAndRetestStrategy(unittest.TestCase):
    """Test suite for BreakAndRetestStrategy class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock configuration
        self.config = {
            'name': 'Break and Retest Strategy',
            'timeframe': 'M15',
            'symbols': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD'],
            'lookback_period': 100,  # Candles to look back for identifying levels
            'level_sensitivity': 0.0001,  # Pip threshold for identifying key levels
            'retest_threshold': 0.0002,  # Maximum distance for valid retest
            'breakout_confirmation_candles': 3,  # Candles needed to confirm breakout
            'min_level_touches': 2,  # Minimum touches to confirm a key level
            'trend_ema_period': 50,  # EMA period for trend direction
            'volume_increase_factor': 1.5,  # Required volume increase for breakout
            'atr_period': 14,
            'atr_multiplier': 1.2,
            'risk_reward_ratio': 2.0,
            'risk_per_trade': 0.01,
            'max_spread_pips': 3.0
        }
        
        # Initialize the strategy
        self.strategy = BreakAndRetestStrategy(self.config)
        
    def generate_support_breakout_data(self, length=300):
        """Generate sample data for support breakout followed by retest (bearish signal)."""
        base = 1.1000
        dates = [datetime.now() - timedelta(minutes=i*15) for i in range(length, 0, -1)]
        
        data = []
        support_level = base - 0.0050  # Support at 1.0950
        
        for i in range(length):
            # Create price action with support level, breakout, and retest
            if i < length // 3:
                # Initial phase - establish support
                if i % 30 < 15:
                    price = support_level + np.random.uniform(0.0010, 0.0080)  # Price stays above support
                else:
                    price = support_level + np.random.uniform(0.0000, 0.0015)  # Price tests support
            elif i < length // 3 * 2:
                # Breakout phase
                if i == length // 3:
                    price = support_level - 0.0020  # Initial breakout candle
                else:
                    price = support_level - np.random.uniform(0.0020, 0.0060)  # Continue lower after breakout
            else:
                # Retest phase
                if length // 3 * 2 <= i < length // 3 * 2 + 10:
                    price = support_level - np.random.uniform(-0.0010, 0.0005)  # Retest the broken level
                else:
                    price = support_level - np.random.uniform(0.0020, 0.0080)  # Continue lower after retest
            
            # Add some noise
            noise = np.random.normal(0, 0.0002)
            close = price + noise
            
            # Calculate OHLC values
            high = close + abs(np.random.normal(0, 0.0003))
            low = close - abs(np.random.normal(0, 0.0003))
            open_price = close - np.random.normal(0, 0.0005) * (1 if np.random.random() > 0.5 else -1)
            
            # Add volume spikes at breakout points
            if i == length // 3 or i == length // 3 * 2:
                volume = 200 + np.random.randint(0, 100)  # Higher volume at breakout and retest
            else:
                volume = 100 + np.random.randint(0, 50)
            
            # Add to data
            data.append({
                'time': dates[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def generate_resistance_breakout_data(self, length=300):
        """Generate sample data for resistance breakout followed by retest (bullish signal)."""
        base = 1.1000
        dates = [datetime.now() - timedelta(minutes=i*15) for i in range(length, 0, -1)]
        
        data = []
        resistance_level = base + 0.0050  # Resistance at 1.1050
        
        for i in range(length):
            # Create price action with resistance level, breakout, and retest
            if i < length // 3:
                # Initial phase - establish resistance
                if i % 30 < 15:
                    price = resistance_level - np.random.uniform(0.0010, 0.0080)  # Price stays below resistance
                else:
                    price = resistance_level - np.random.uniform(0.0000, 0.0015)  # Price tests resistance
            elif i < length // 3 * 2:
                # Breakout phase
                if i == length // 3:
                    price = resistance_level + 0.0020  # Initial breakout candle
                else:
                    price = resistance_level + np.random.uniform(0.0020, 0.0060)  # Continue higher after breakout
            else:
                # Retest phase
                if length // 3 * 2 <= i < length // 3 * 2 + 10:
                    price = resistance_level + np.random.uniform(-0.0010, 0.0005)  # Retest the broken level
                else:
                    price = resistance_level + np.random.uniform(0.0020, 0.0080)  # Continue higher after retest
            
            # Add some noise
            noise = np.random.normal(0, 0.0002)
            close = price + noise
            
            # Calculate OHLC values
            high = close + abs(np.random.normal(0, 0.0003))
            low = close - abs(np.random.normal(0, 0.0003))
            open_price = close - np.random.normal(0, 0.0005) * (1 if np.random.random() > 0.5 else -1)
            
            # Add volume spikes at breakout points
            if i == length // 3 or i == length // 3 * 2:
                volume = 200 + np.random.randint(0, 100)  # Higher volume at breakout and retest
            else:
                volume = 100 + np.random.randint(0, 50)
            
            # Add to data
            data.append({
                'time': dates[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def generate_no_breakout_data(self, length=300):
        """Generate sample data without clear breakouts and retests."""
        base = 1.1000
        dates = [datetime.now() - timedelta(minutes=i*15) for i in range(length, 0, -1)]
        
        data = []
        for i in range(length):
            # Create a choppy, ranging market without clear levels
            oscillation = np.sin(i / 20) * 0.0020
            
            # Add some noise
            noise = np.random.normal(0, 0.0003)
            
            # Calculate OHLC values
            close = base + oscillation + noise
            high = close + abs(np.random.normal(0, 0.0003))
            low = close - abs(np.random.normal(0, 0.0003))
            open_price = close - np.random.normal(0, 0.0004) * (1 if np.random.random() > 0.5 else -1)
            
            # Add to data
            data.append({
                'time': dates[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': 100 + np.random.randint(0, 30)
            })
        
        return pd.DataFrame(data)
    
    def test_analyze_support_breakout_signal(self):
        """Test that sell signals are correctly generated for support breakout retests."""
        data = self.generate_support_breakout_data()
        result = self.strategy.analyze('EURUSD', data)
        
        # We should get a sell signal from the support breakout retest
        self.assertEqual(result['signal'], 'sell', 
                        f"Expected 'sell' signal from support breakout retest, got {result['signal']}")
        
        # Verify that stop loss and take profit are correctly set
        self.assertIsNotNone(result['stop_loss'], "Stop loss should be defined")
        self.assertIsNotNone(result['take_profit'], "Take profit should be defined")
        self.assertGreater(result['stop_loss'], result['entry_price'], "Stop loss should be above entry price for sell signal")
        self.assertLess(result['take_profit'], result['entry_price'], "Take profit should be below entry price for sell signal")
        
        # Risk-reward check
        risk = result['stop_loss'] - result['entry_price'] 
        reward = result['entry_price'] - result['take_profit']
        self.assertAlmostEqual(reward / risk, self.config['risk_reward_ratio'], places=1, 
                              msg=f"Risk-reward ratio should be ~{self.config['risk_reward_ratio']}")
    
    def test_analyze_resistance_breakout_signal(self):
        """Test that buy signals are correctly generated for resistance breakout retests."""
        data = self.generate_resistance_breakout_data()
        result = self.strategy.analyze('EURUSD', data)
        
        # We should get a buy signal from the resistance breakout retest
        self.assertEqual(result['signal'], 'buy', 
                        f"Expected 'buy' signal from resistance breakout retest, got {result['signal']}")
        
        # Verify that stop loss and take profit are correctly set
        self.assertIsNotNone(result['stop_loss'], "Stop loss should be defined")
        self.assertIsNotNone(result['take_profit'], "Take profit should be defined")
        self.assertLess(result['stop_loss'], result['entry_price'], "Stop loss should be below entry price for buy signal")
        self.assertGreater(result['take_profit'], result['entry_price'], "Take profit should be above entry price for buy signal")
        
        # Risk-reward check
        risk = result['entry_price'] - result['stop_loss']
        reward = result['take_profit'] - result['entry_price']
        self.assertAlmostEqual(reward / risk, self.config['risk_reward_ratio'], places=1, 
                              msg=f"Risk-reward ratio should be ~{self.config['risk_reward_ratio']}")
    
    def test_no_signal_without_breakout(self):
        """Test that no signal is generated without clear breakouts and retests."""
        data = self.generate_no_breakout_data()
        result = self.strategy.analyze('EURUSD', data)
        
        # We should not get a trade signal in choppy markets without clear levels
        self.assertEqual(result['signal'], 'none', 
                        f"Expected 'none' signal without clear breakouts, got {result['signal']}")
    
    def test_position_size_calculation(self):
        """Test position size calculation based on risk."""
        # Mock account info
        account_info = {
            'balance': 10000,
            'equity': 10000,
            'currency': 'USD',
            'margin_used': 0
        }
        
        # For a stop loss of 30 pips
        entry_price = 1.1000
        stop_loss_price = 1.0970
        
        position_size = self.strategy.calculate_position_size('EURUSD', account_info, entry_price, stop_loss_price)
        
        # Expected position size: 
        # Risk amount = 10000 * 0.01 = 100 USD
        # Risk per pip = 100 / 30 = 3.33 USD per pip
        # For EURUSD, 0.1 lot is roughly 10 USD per pip, so expected size ~ 0.033 lot
        self.assertGreater(position_size, 0, "Position size should be greater than 0")
        self.assertLess(position_size, 0.05, "Position size should be less than 0.05 for 1% risk on $10k account with 30 pip stop")
    
    def test_should_trade(self):
        """Test that trading conditions are correctly evaluated."""
        # Should trade with normal data
        data = self.generate_support_breakout_data()
        should_trade = self.strategy.should_trade('EURUSD', data)
        self.assertTrue(should_trade, "Should recommend trading with clear breakout and retest")
        
        # Should not trade with insufficient data
        insufficient_data = data.iloc[-50:]  # Only 50 candles
        should_trade = self.strategy.should_trade('EURUSD', insufficient_data)
        self.assertFalse(should_trade, "Should not recommend trading with insufficient data")


if __name__ == '__main__':
    unittest.main()
