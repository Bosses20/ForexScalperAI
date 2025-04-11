"""
Stochastic Cross Strategy Test Module

This module contains tests for the Stochastic Cross strategy functionality,
ensuring proper signal generation and risk management.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategies.stochastic_cross_strategy import StochasticCrossStrategy


class TestStochasticCrossStrategy(unittest.TestCase):
    """Test suite for StochasticCrossStrategy class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock configuration
        self.config = {
            'name': 'Stochastic Cross Strategy',
            'timeframe': 'M5',
            'symbols': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD'],
            'k_period': 14,
            'd_period': 3,
            'slowing': 3,
            'overbought': 80,
            'oversold': 20,
            'trend_filter': True,
            'trend_ema_period': 100,
            'require_crossover': True,
            'atr_period': 14,
            'atr_multiplier': 1.2,
            'risk_reward_ratio': 1.8,
            'risk_per_trade': 0.01,
            'max_spread_pips': 2.5
        }
        
        # Initialize the strategy
        self.strategy = StochasticCrossStrategy(self.config)
        
    def generate_oversold_crossover_data(self, length=200):
        """Generate sample data for stochastic oversold crossover (bullish signal)."""
        base = 1.0
        dates = [datetime.now() - timedelta(minutes=i*5) for i in range(length, 0, -1)]
        
        data = []
        for i in range(length):
            # Create a downtrend followed by uptrend reversal
            if i < length // 2:
                trend = -i / 800.0  # Initial downtrend
            else:
                trend = (i - length // 2) / 600.0  # Reversal to uptrend
            
            # Add cycle component to simulate stochastic oscillations
            cycle = np.sin(i / 15) * 0.002
            
            # Add some noise
            noise = np.random.normal(0, 0.0003)
            
            # Calculate OHLC values
            close = base + trend + cycle + noise
            high = close + abs(np.random.normal(0, 0.0003))
            low = close - abs(np.random.normal(0, 0.0003))
            open_price = close - np.random.normal(0, 0.0005) * (1 if np.random.random() > 0.5 else -1)
            
            # Add to data
            data.append({
                'time': dates[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': 100 + np.random.randint(0, 50)
            })
        
        return pd.DataFrame(data)
    
    def generate_overbought_crossover_data(self, length=200):
        """Generate sample data for stochastic overbought crossover (bearish signal)."""
        base = 1.1
        dates = [datetime.now() - timedelta(minutes=i*5) for i in range(length, 0, -1)]
        
        data = []
        for i in range(length):
            # Create an uptrend followed by downtrend reversal
            if i < length // 2:
                trend = i / 800.0  # Initial uptrend
            else:
                trend = -(i - length // 2) / 600.0  # Reversal to downtrend
            
            # Add cycle component to simulate stochastic oscillations
            cycle = np.sin(i / 15) * 0.002
            
            # Add some noise
            noise = np.random.normal(0, 0.0003)
            
            # Calculate OHLC values
            close = base + trend + cycle + noise
            high = close + abs(np.random.normal(0, 0.0003))
            low = close - abs(np.random.normal(0, 0.0003))
            open_price = close - np.random.normal(0, 0.0005) * (1 if np.random.random() > 0.5 else -1)
            
            # Add to data
            data.append({
                'time': dates[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': 100 + np.random.randint(0, 50)
            })
        
        return pd.DataFrame(data)
    
    def generate_no_signal_data(self, length=200):
        """Generate sample data without clear stochastic crossovers."""
        base = 1.0
        dates = [datetime.now() - timedelta(minutes=i*5) for i in range(length, 0, -1)]
        
        data = []
        for i in range(length):
            # Create a slightly oscillating but overall mid-range stochastic market
            oscillation = np.sin(i / 5) * 0.001  # Faster oscillations but smaller magnitude
            
            # Add some noise
            noise = np.random.normal(0, 0.0002)
            
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
        """Test that bullish signals are correctly generated from oversold crossovers."""
        data = self.generate_oversold_crossover_data()
        result = self.strategy.analyze('EURUSD', data)
        
        # We should get a buy signal from the oversold crossover
        self.assertEqual(result['signal'], 'buy', 
                        f"Expected 'buy' signal from oversold crossover, got {result['signal']}")
        
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
        """Test that bearish signals are correctly generated from overbought crossovers."""
        data = self.generate_overbought_crossover_data()
        result = self.strategy.analyze('EURUSD', data)
        
        # We should get a sell signal from the overbought crossover
        self.assertEqual(result['signal'], 'sell', 
                        f"Expected 'sell' signal from overbought crossover, got {result['signal']}")
        
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
        """Test that no signal is generated without clear stochastic crossovers."""
        data = self.generate_no_signal_data()
        result = self.strategy.analyze('EURUSD', data)
        
        # We should not get a trade signal without crossovers in key zones
        self.assertEqual(result['signal'], 'none', 
                        f"Expected 'none' signal without key stochastic crossovers, got {result['signal']}")
    
    def test_position_size_calculation(self):
        """Test position size calculation based on risk."""
        # Mock account info
        account_info = {
            'balance': 10000,
            'equity': 10000,
            'currency': 'USD',
            'margin_used': 0
        }
        
        # For a stop loss of 15 pips
        entry_price = 1.1000
        stop_loss_price = 1.0985
        
        position_size = self.strategy.calculate_position_size('EURUSD', account_info, entry_price, stop_loss_price)
        
        # Expected position size: 
        # Risk amount = 10000 * 0.01 = 100 USD
        # Risk per pip = 100 / 15 = 6.67 USD per pip
        # For EURUSD, 0.1 lot is roughly 10 USD per pip, so expected size ~ 0.067 lot
        self.assertGreater(position_size, 0, "Position size should be greater than 0")
        self.assertLess(position_size, 0.1, "Position size should be less than 0.1 for 1% risk on $10k account with 15 pip stop")
    
    def test_should_trade(self):
        """Test that trading conditions are correctly evaluated."""
        # Should trade with normal data
        data = self.generate_oversold_crossover_data()
        should_trade = self.strategy.should_trade('EURUSD', data)
        self.assertTrue(should_trade, "Should recommend trading with stochastic crossover")
        
        # Should not trade with insufficient data
        insufficient_data = data.iloc[-10:]  # Only 10 candles
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
