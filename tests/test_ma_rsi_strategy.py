"""
MA + RSI Combo Strategy Test Module

This module contains tests for the MA + RSI Combo strategy functionality,
ensuring proper signal generation and risk management.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategies.ma_rsi_strategy import MaRsiStrategy


class TestMaRsiStrategy(unittest.TestCase):
    """Test suite for MaRsiStrategy class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock configuration
        self.config = {
            'name': 'MA + RSI Combo',
            'timeframe': 'M5',
            'symbols': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD'],
            'ema_period': 50,
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'price_action_confirmation': True,
            'volume_filter': True,
            'volume_threshold': 1.5,
            'atr_period': 14,
            'atr_multiplier': 1.2,
            'risk_reward_ratio': 2.0,
            'risk_per_trade': 0.01,
            'max_spread_pips': 3
        }
        
        # Initialize the strategy
        self.strategy = MaRsiStrategy(self.config)
        
    def generate_bullish_trend_data(self, length=200):
        """Generate sample data for a bullish trend with oversold RSI."""
        base = 1.0
        dates = [datetime.now() - timedelta(minutes=i*5) for i in range(length, 0, -1)]
        
        data = []
        for i in range(length):
            # Start with downtrend then reverse to uptrend for RSI oversold condition
            if i < length // 4:
                trend = -i / 500.0  # Initial downtrend
            else:
                trend = (i - length // 4) / 300.0  # Reversal to uptrend
            
            # Add some noise
            noise = np.random.normal(0, 0.0005)
            
            # Calculate OHLC values
            close = base + trend + noise
            high = close + abs(np.random.normal(0, 0.0003))
            low = close - abs(np.random.normal(0, 0.0003))
            open_price = close - np.random.normal(0, 0.0005) * (1 if np.random.random() > 0.5 else -1)
            
            # Add volume spikes at key reversal points
            if length // 4 - 5 <= i <= length // 4 + 5:
                volume = 200 + np.random.randint(0, 100)  # Higher volume at reversal
            else:
                volume = 100 + np.random.randint(0, 50)
            
            # Add to data
            data.append({
                'time': dates[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
                'tick_volume': volume * 10
            })
        
        return pd.DataFrame(data)
    
    def generate_bearish_trend_data(self, length=200):
        """Generate sample data for a bearish trend with overbought RSI."""
        base = 1.1
        dates = [datetime.now() - timedelta(minutes=i*5) for i in range(length, 0, -1)]
        
        data = []
        for i in range(length):
            # Start with uptrend then reverse to downtrend for RSI overbought condition
            if i < length // 4:
                trend = i / 500.0  # Initial uptrend
            else:
                trend = -(i - length // 4) / 300.0  # Reversal to downtrend
            
            # Add some noise
            noise = np.random.normal(0, 0.0005)
            
            # Calculate OHLC values
            close = base + trend + noise
            high = close + abs(np.random.normal(0, 0.0003))
            low = close - abs(np.random.normal(0, 0.0003))
            open_price = close - np.random.normal(0, 0.0005) * (1 if np.random.random() > 0.5 else -1)
            
            # Add volume spikes at key reversal points
            if length // 4 - 5 <= i <= length // 4 + 5:
                volume = 200 + np.random.randint(0, 100)  # Higher volume at reversal
            else:
                volume = 100 + np.random.randint(0, 50)
            
            # Add to data
            data.append({
                'time': dates[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
                'tick_volume': volume * 10
            })
        
        return pd.DataFrame(data)
    
    def generate_neutral_data(self, length=200):
        """Generate sample data for neutral market conditions."""
        base = 1.0
        dates = [datetime.now() - timedelta(minutes=i*5) for i in range(length, 0, -1)]
        
        data = []
        for i in range(length):
            # Create a slightly oscillating but overall directionless market
            oscillation = np.sin(i / 10) * 0.002
            
            # Add some noise
            noise = np.random.normal(0, 0.0003)
            
            # Calculate OHLC values
            close = base + oscillation + noise
            high = close + abs(np.random.normal(0, 0.0002))
            low = close - abs(np.random.normal(0, 0.0002))
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
    
    def test_analyze_bullish_signal(self):
        """Test that bullish signals are correctly generated."""
        data = self.generate_bullish_trend_data()
        result = self.strategy.analyze('EURUSD', data)
        
        # At some point in this data, we should have a buy signal after RSI comes out of oversold
        self.assertEqual(result['signal'], 'buy', 
                        f"Expected 'buy' signal in bullish trend with oversold RSI, got {result['signal']}")
        
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
    
    def test_analyze_bearish_signal(self):
        """Test that bearish signals are correctly generated."""
        data = self.generate_bearish_trend_data()
        result = self.strategy.analyze('EURUSD', data)
        
        # At some point in this data, we should have a sell signal after RSI comes out of overbought
        self.assertEqual(result['signal'], 'sell', 
                        f"Expected 'sell' signal in bearish trend with overbought RSI, got {result['signal']}")
        
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
    
    def test_no_signal_in_neutral_market(self):
        """Test that no signal is generated in neutral market conditions."""
        data = self.generate_neutral_data()
        result = self.strategy.analyze('EURUSD', data)
        
        # We should not get a trade signal in neutral conditions
        self.assertEqual(result['signal'], 'none', 
                        f"Expected 'none' signal in neutral market, got {result['signal']}")
    
    def test_position_size_calculation(self):
        """Test position size calculation based on risk."""
        # Mock account info
        account_info = {
            'balance': 10000,
            'equity': 10000,
            'currency': 'USD',
            'margin_used': 0
        }
        
        # For a stop loss of 20 pips
        entry_price = 1.1000
        stop_loss_price = 1.0980
        
        position_size = self.strategy.calculate_position_size('EURUSD', account_info, entry_price, stop_loss_price)
        
        # Expected position size: 
        # Risk amount = 10000 * 0.01 = 100 USD
        # Risk per pip = 100 / 20 = 5 USD per pip
        # For EURUSD, 0.1 lot is roughly 10 USD per pip, so expected size ~ 0.05 lot
        self.assertGreater(position_size, 0, "Position size should be greater than 0")
        self.assertLess(position_size, 0.1, "Position size should be less than 0.1 for 1% risk on $10k account with 20 pip stop")
    
    def test_should_trade(self):
        """Test that trading conditions are correctly evaluated."""
        # Should trade with normal data
        data = self.generate_bullish_trend_data()
        should_trade = self.strategy.should_trade('EURUSD', data)
        self.assertTrue(should_trade, "Should recommend trading in clear trend")
        
        # Should not trade with insufficient data
        insufficient_data = data.iloc[-10:]  # Only 10 candles
        should_trade = self.strategy.should_trade('EURUSD', insufficient_data)
        self.assertFalse(should_trade, "Should not recommend trading with insufficient data")


if __name__ == '__main__':
    unittest.main()
