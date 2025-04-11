"""
JHook Pattern Strategy Test Module

This module contains tests for the JHook Pattern strategy functionality,
ensuring proper signal generation and risk management.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategies.jhook_pattern_strategy import JHookPatternStrategy


class TestJHookPatternStrategy(unittest.TestCase):
    """Test suite for JHookPatternStrategy class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock configuration
        self.config = {
            'name': 'JHook Pattern Strategy',
            'timeframe': 'H1',
            'symbols': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD'],
            'min_trend_strength': 0.6,  # Minimum trend strength required
            'retracement_threshold': 0.382,  # Fibonacci retracement level (38.2%)
            'extension_threshold': 0.618,  # Fibonacci extension level (61.8%)
            'trend_ema_period': 50,  # EMA period for trend detection
            'confirmation_candles': 2,  # Candles needed to confirm pattern
            'volume_confirmation': True,  # Require volume increase for confirmation
            'volume_factor': 1.2,  # Volume must be this times the average
            'atr_period': 14,
            'atr_multiplier': 1.5,
            'risk_reward_ratio': 2.5,
            'risk_per_trade': 0.01,
            'max_spread_pips': 4.0
        }
        
        # Initialize the strategy
        self.strategy = JHookPatternStrategy(self.config)
        
    def generate_bullish_jhook_data(self, length=200):
        """Generate sample data for bullish JHook pattern (uptrend, pullback, continuation)."""
        base = 1.1000
        dates = [datetime.now() - timedelta(hours=i) for i in range(length, 0, -1)]
        
        data = []
        
        # Define key points in the pattern
        uptrend_length = length // 3
        retracement_length = length // 4
        continuation_length = length - uptrend_length - retracement_length
        
        # Initial low point
        initial_low = base - 0.0100
        
        # High point of trend
        trend_high = initial_low + 0.0200
        
        # Retracement level (38.2% of the move)
        retracement_price = trend_high - (0.0200 * 0.382)
        
        for i in range(length):
            if i < uptrend_length:
                # Initial uptrend phase
                progress = i / uptrend_length
                price = initial_low + progress * 0.0200
            elif i < uptrend_length + retracement_length:
                # Retracement phase
                progress = (i - uptrend_length) / retracement_length
                retracement_amount = 0.0200 * 0.382 * progress  # 38.2% Fibonacci retracement
                price = trend_high - retracement_amount
            else:
                # Continuation phase - J-shape completion
                progress = (i - uptrend_length - retracement_length) / continuation_length
                price = retracement_price + progress * 0.0300  # Continue higher than original high
            
            # Add some noise
            noise = np.random.normal(0, 0.0002)
            close = price + noise
            
            # Calculate OHLC values
            high = close + abs(np.random.normal(0, 0.0003))
            low = close - abs(np.random.normal(0, 0.0003))
            open_price = close - np.random.normal(0, 0.0003) * (1 if np.random.random() > 0.5 else -1)
            
            # Add volume characteristics
            if i < uptrend_length:
                volume = 100 + np.random.randint(0, 40)  # Normal volume during uptrend
            elif i < uptrend_length + retracement_length:
                volume = 80 + np.random.randint(0, 30)  # Lower volume during retracement
            else:
                volume = 130 + np.random.randint(0, 50)  # Higher volume during continuation
            
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
    
    def generate_bearish_jhook_data(self, length=200):
        """Generate sample data for bearish JHook pattern (downtrend, pullback, continuation)."""
        base = 1.1000
        dates = [datetime.now() - timedelta(hours=i) for i in range(length, 0, -1)]
        
        data = []
        
        # Define key points in the pattern
        downtrend_length = length // 3
        retracement_length = length // 4
        continuation_length = length - downtrend_length - retracement_length
        
        # Initial high point
        initial_high = base + 0.0100
        
        # Low point of trend
        trend_low = initial_high - 0.0200
        
        # Retracement level (38.2% of the move)
        retracement_price = trend_low + (0.0200 * 0.382)
        
        for i in range(length):
            if i < downtrend_length:
                # Initial downtrend phase
                progress = i / downtrend_length
                price = initial_high - progress * 0.0200
            elif i < downtrend_length + retracement_length:
                # Retracement phase
                progress = (i - downtrend_length) / retracement_length
                retracement_amount = 0.0200 * 0.382 * progress  # 38.2% Fibonacci retracement
                price = trend_low + retracement_amount
            else:
                # Continuation phase - J-shape completion
                progress = (i - downtrend_length - retracement_length) / continuation_length
                price = retracement_price - progress * 0.0300  # Continue lower than original low
            
            # Add some noise
            noise = np.random.normal(0, 0.0002)
            close = price + noise
            
            # Calculate OHLC values
            high = close + abs(np.random.normal(0, 0.0003))
            low = close - abs(np.random.normal(0, 0.0003))
            open_price = close - np.random.normal(0, 0.0003) * (1 if np.random.random() > 0.5 else -1)
            
            # Add volume characteristics
            if i < downtrend_length:
                volume = 100 + np.random.randint(0, 40)  # Normal volume during downtrend
            elif i < downtrend_length + retracement_length:
                volume = 80 + np.random.randint(0, 30)  # Lower volume during retracement
            else:
                volume = 130 + np.random.randint(0, 50)  # Higher volume during continuation
            
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
    
    def generate_no_pattern_data(self, length=200):
        """Generate sample data without clear JHook patterns."""
        base = 1.1000
        dates = [datetime.now() - timedelta(hours=i) for i in range(length, 0, -1)]
        
        data = []
        for i in range(length):
            # Create a choppy market with no clear trend direction
            oscillation = np.sin(i / 15) * 0.0030 + np.sin(i / 30) * 0.0020
            
            # Add some noise
            noise = np.random.normal(0, 0.0002)
            
            # Calculate OHLC values
            close = base + oscillation + noise
            high = close + abs(np.random.normal(0, 0.0003))
            low = close - abs(np.random.normal(0, 0.0003))
            open_price = close - np.random.normal(0, 0.0003) * (1 if np.random.random() > 0.5 else -1)
            
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
    
    def test_analyze_bullish_jhook_signal(self):
        """Test that buy signals are correctly generated for bullish JHook patterns."""
        data = self.generate_bullish_jhook_data()
        result = self.strategy.analyze('EURUSD', data)
        
        # We should get a buy signal from the bullish JHook pattern
        self.assertEqual(result['signal'], 'buy', 
                        f"Expected 'buy' signal from bullish JHook pattern, got {result['signal']}")
        
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
    
    def test_analyze_bearish_jhook_signal(self):
        """Test that sell signals are correctly generated for bearish JHook patterns."""
        data = self.generate_bearish_jhook_data()
        result = self.strategy.analyze('EURUSD', data)
        
        # We should get a sell signal from the bearish JHook pattern
        self.assertEqual(result['signal'], 'sell', 
                        f"Expected 'sell' signal from bearish JHook pattern, got {result['signal']}")
        
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
    
    def test_no_signal_without_pattern(self):
        """Test that no signal is generated without clear JHook patterns."""
        data = self.generate_no_pattern_data()
        result = self.strategy.analyze('EURUSD', data)
        
        # We should not get a trade signal in choppy markets without patterns
        self.assertEqual(result['signal'], 'none', 
                        f"Expected 'none' signal without clear JHook pattern, got {result['signal']}")
    
    def test_position_size_calculation(self):
        """Test position size calculation based on risk."""
        # Mock account info
        account_info = {
            'balance': 10000,
            'equity': 10000,
            'currency': 'USD',
            'margin_used': 0
        }
        
        # For a stop loss of 25 pips
        entry_price = 1.1000
        stop_loss_price = 1.0975
        
        position_size = self.strategy.calculate_position_size('EURUSD', account_info, entry_price, stop_loss_price)
        
        # Expected position size: 
        # Risk amount = 10000 * 0.01 = 100 USD
        # Risk per pip = 100 / 25 = 4 USD per pip
        # For EURUSD, 0.1 lot is roughly 10 USD per pip, so expected size ~ 0.04 lot
        self.assertGreater(position_size, 0, "Position size should be greater than 0")
        self.assertLess(position_size, 0.06, "Position size should be less than 0.06 for 1% risk on $10k account with 25 pip stop")
    
    def test_should_trade(self):
        """Test that trading conditions are correctly evaluated."""
        # Should trade with valid JHook data
        data = self.generate_bullish_jhook_data()
        should_trade = self.strategy.should_trade('EURUSD', data)
        self.assertTrue(should_trade, "Should recommend trading with JHook pattern")
        
        # Should not trade with insufficient data
        insufficient_data = data.iloc[-50:]  # Only 50 candles
        should_trade = self.strategy.should_trade('EURUSD', insufficient_data)
        self.assertFalse(should_trade, "Should not recommend trading with insufficient data")
        
        # Test max spread condition
        original_max_spread = self.strategy.max_spread_pips
        self.strategy.max_spread_pips = 0.1  # Set very low max spread
        should_trade = self.strategy.should_trade('EURUSD', data)
        self.assertFalse(should_trade, "Should not trade when spread exceeds max allowed")
        self.strategy.max_spread_pips = original_max_spread  # Restore original value


if __name__ == '__main__':
    unittest.main()
