"""
Risk Manager Test Module

This module contains tests for the Risk Manager functionality,
ensuring position sizing, risk controls, and trade management work correctly.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.risk.risk_manager import RiskManager


class TestRiskManager(unittest.TestCase):
    """Test suite for RiskManager class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock configuration
        self.risk_config = {
            'max_risk_per_trade': 0.01,  # 1% risk per trade
            'max_daily_risk': 0.05,      # 5% max daily risk
            'max_drawdown_percent': 0.15, # 15% max drawdown
            'max_correlation_exposure': 2,
            'max_spread_multiplier': 1.5,
            'max_slippage_pips': 2,
            'position_aging_hours': 24,  # 24 hours position aging for tests
            'account_currency': 'USD',
            'stop_loss_strategies': {
                'fixed': {
                    'pip_distance': 20
                },
                'atr': {
                    'multiplier': 1.5
                },
                'structure': {
                    'min_pip_distance': 10,
                    'max_pip_distance': 50
                }
            },
            'take_profit_strategies': {
                'fixed': {
                    'pip_distance': 40
                },
                'multiple': {
                    'levels': [1.5, 2.5, 3.5],
                    'sizes': [0.3, 0.3, 0.4]
                },
                'trailing': {
                    'activation_pips': 20,
                    'trail_pips': 10
                }
            }
        }
        
        # Initialize the risk manager
        self.risk_manager = RiskManager(self.risk_config)
        
        # Set account balance for testing
        self.risk_manager.update_account_balance(10000.0)
        
        # Mock signals for testing
        self.long_signal = {
            'pair': 'EURUSD',
            'direction': 'buy',
            'price': 1.1000,
            'stop_loss': 1.0950,  # 50 pips SL
            'take_profit': 1.1100, # 100 pips TP
            'strategy': 'moving_average_cross',
            'instrument_type': 'forex'
        }
        
        self.short_signal = {
            'pair': 'GBPUSD',
            'direction': 'sell',
            'price': 1.3000,
            'stop_loss': 1.3050,  # 50 pips SL
            'take_profit': 1.2900, # 100 pips TP
            'strategy': 'support_resistance',
            'instrument_type': 'forex'
        }
        
        self.synthetic_signal = {
            'pair': 'VOLATILITY_75',
            'direction': 'buy',
            'price': 100.00,
            'stop_loss': 99.00,   # 100 points SL (equivalent to 100 pips)
            'take_profit': 102.00, # 200 points TP
            'strategy': 'bollinger_breakout',
            'instrument_type': 'synthetic',
            'sub_type': 'volatility'
        }
    
    def test_update_account_balance(self):
        """Test that account balance updates correctly."""
        # Test initial balance
        self.assertEqual(self.risk_manager.current_balance, 10000.0)
        self.assertEqual(self.risk_manager.highest_balance, 10000.0)
        
        # Test updating to higher balance
        self.risk_manager.update_account_balance(12000.0)
        self.assertEqual(self.risk_manager.current_balance, 12000.0)
        self.assertEqual(self.risk_manager.highest_balance, 12000.0)
        
        # Test updating to lower balance
        self.risk_manager.update_account_balance(11000.0)
        self.assertEqual(self.risk_manager.current_balance, 11000.0)
        self.assertEqual(self.risk_manager.highest_balance, 12000.0)  # Highest should remain at peak
    
    def test_get_account_tier(self):
        """Test account tier determination."""
        # Test nano tier (0-100)
        self.risk_manager.update_account_balance(50.0)
        tier = self.risk_manager.get_account_tier(self.risk_manager.current_balance)
        self.assertEqual(tier, 'nano')
        
        # Test micro tier (101-500)
        self.risk_manager.update_account_balance(250.0)
        tier = self.risk_manager.get_account_tier(self.risk_manager.current_balance)
        self.assertEqual(tier, 'micro')
        
        # Test mini tier (501-2000)
        self.risk_manager.update_account_balance(1000.0)
        tier = self.risk_manager.get_account_tier(self.risk_manager.current_balance)
        self.assertEqual(tier, 'mini')
        
        # Test standard tier (2001-10000)
        self.risk_manager.update_account_balance(5000.0)
        tier = self.risk_manager.get_account_tier(self.risk_manager.current_balance)
        self.assertEqual(tier, 'standard')
        
        # Test professional tier (10001+)
        self.risk_manager.update_account_balance(20000.0)
        tier = self.risk_manager.get_account_tier(self.risk_manager.current_balance)
        self.assertEqual(tier, 'professional')
    
    def test_calculate_position_size_forex(self):
        """Test position size calculation for forex pairs."""
        # Reset balance for consistent testing
        self.risk_manager.update_account_balance(10000.0)
        
        # Test with default 1% risk and 50 pip stop loss
        position_size = self.risk_manager.calculate_position_size(self.long_signal)
        
        # Expected calculation:
        # Risk amount = 10000 * 0.01 = 100
        # Pip value = Risk amount / SL pips = 100 / 50 = 2
        # For EURUSD, lot size = pip value / 10 (approx)
        # Expected lot size around 0.2
        self.assertAlmostEqual(position_size, 0.2, delta=0.05)
        
        # Test with tighter stop loss (25 pips)
        tight_sl_signal = self.long_signal.copy()
        tight_sl_signal['stop_loss'] = 1.0975  # 25 pips SL
        position_size = self.risk_manager.calculate_position_size(tight_sl_signal)
        
        # Expected to be double the previous size since SL is half the distance
        self.assertAlmostEqual(position_size, 0.4, delta=0.05)
        
        # Test with lower balance (should reduce position size proportionally)
        self.risk_manager.update_account_balance(5000.0)
        position_size = self.risk_manager.calculate_position_size(self.long_signal)
        self.assertAlmostEqual(position_size, 0.1, delta=0.05)  # Half the original position size
    
    def test_calculate_position_size_synthetic(self):
        """Test position size calculation for synthetic instruments."""
        # Reset balance for consistent testing
        self.risk_manager.update_account_balance(10000.0)
        
        # Test with synthetic indices
        position_size = self.risk_manager.calculate_position_size(self.synthetic_signal)
        
        # Position size should be adjusted according to the different pip values
        # and minimum lot sizes for synthetic instruments
        self.assertGreater(position_size, 0, "Position size should be positive")
        
        # Test that synthetic indices respect minimum lot size
        min_lot = self.risk_manager._get_min_lot_size(
            self.synthetic_signal['pair'], 
            self.synthetic_signal['instrument_type']
        )
        self.assertGreaterEqual(position_size, min_lot, 
                               f"Position size should respect minimum lot size of {min_lot}")
    
    def test_validate_trade(self):
        """Test trade validation functionality."""
        # Test a valid trade
        self.risk_manager.update_account_balance(10000.0)
        position_size = self.risk_manager.calculate_position_size(self.long_signal)
        is_valid = self.risk_manager.validate_trade(self.long_signal, position_size)
        self.assertTrue(is_valid, "Expected trade to be valid")
        
        # Test when daily risk limit is exceeded
        # Mock the daily risk limit check
        with patch.object(RiskManager, '_check_daily_risk_limit', return_value=True):
            is_valid = self.risk_manager.validate_trade(self.long_signal, position_size)
            self.assertFalse(is_valid, "Expected trade to be invalid due to daily risk limit")
        
        # Test with excessive correlation exposure
        # Register multiple correlated trades first
        self.risk_manager.register_trade({
            'pair': 'EURUSD',
            'direction': 'buy',
            'entry_price': 1.1000,
            'stop_loss': 1.0950,
            'take_profit': 1.1100,
            'position_size': 0.1,
            'entry_time': datetime.now()
        })
        
        self.risk_manager.register_trade({
            'pair': 'EURGBP',
            'direction': 'buy',
            'entry_price': 0.8500,
            'stop_loss': 0.8450,
            'take_profit': 0.8550,
            'position_size': 0.1,
            'entry_time': datetime.now()
        })
        
        # Now try to trade EURJPY which is correlated with both
        eurjpy_signal = {
            'pair': 'EURJPY',
            'direction': 'buy',
            'price': 130.00,
            'stop_loss': 129.50,
            'take_profit': 131.00,
            'strategy': 'moving_average_cross',
            'instrument_type': 'forex'
        }
        
        # Add EURJPY to correlated pairs
        self.risk_manager.correlated_pairs['EURUSD'] = ['EURGBP', 'EURJPY']
        
        position_size = self.risk_manager.calculate_position_size(eurjpy_signal)
        is_valid = self.risk_manager.validate_trade(eurjpy_signal, position_size)
        
        # Should fail due to too many correlated pairs
        # Note: This test might need adjustment based on exact implementation
        # of correlation checks in the validate_trade method
        self.assertFalse(is_valid, "Expected trade to be invalid due to correlation exposure")
    
    def test_stop_loss_strategies(self):
        """Test different stop loss strategies."""
        # Test fixed pip stop loss
        signal = self.long_signal.copy()
        signal['stop_loss'] = None  # Remove predefined stop loss
        
        stop_loss = self.risk_manager.apply_stop_loss_strategy(signal, 'fixed')
        self.assertAlmostEqual(stop_loss, signal['price'] - 0.0020, places=4,
                              msg="Fixed stop loss should be 20 pips from entry")
        
        # Test ATR-based stop loss
        atr_value = 0.0030  # 30 pips ATR
        stop_loss = self.risk_manager.apply_stop_loss_strategy(signal, 'atr', atr_value)
        self.assertAlmostEqual(stop_loss, signal['price'] - (atr_value * 1.5), places=4,
                              msg="ATR stop loss should be 1.5 * ATR from entry")
        
        # Test structure-based stop loss (will depend on implementation)
        # This is just a basic check that it returns something reasonable
        stop_loss = self.risk_manager.apply_stop_loss_strategy(signal, 'structure')
        self.assertLess(stop_loss, signal['price'],
                       "For long trades, stop loss should be below entry price")
        
        # Test for short trade
        short_signal = self.short_signal.copy()
        short_signal['stop_loss'] = None
        
        stop_loss = self.risk_manager.apply_stop_loss_strategy(short_signal, 'fixed')
        self.assertAlmostEqual(stop_loss, short_signal['price'] + 0.0020, places=4,
                              msg="For short trades, fixed stop loss should be above entry price")
    
    def test_take_profit_strategies(self):
        """Test different take profit strategies."""
        # Test fixed pip take profit
        signal = self.long_signal.copy()
        signal['take_profit'] = None  # Remove predefined take profit
        
        tp_result = self.risk_manager.apply_take_profit_strategy(signal, 'fixed')
        self.assertAlmostEqual(tp_result['take_profit'], signal['price'] + 0.0040, places=4,
                              msg="Fixed take profit should be 40 pips from entry")
        
        # Test risk-reward based take profit
        signal['stop_loss'] = signal['price'] - 0.0020  # 20 pips stop loss
        tp_result = self.risk_manager.apply_take_profit_strategy(signal, 'fixed', risk_reward_ratio=2.0)
        self.assertAlmostEqual(tp_result['take_profit'], signal['price'] + 0.0040, places=4,
                              msg="Risk-reward take profit should be 2x the stop loss distance")
        
        # Test multiple take profits
        tp_result = self.risk_manager.apply_take_profit_strategy(signal, 'multiple')
        self.assertIsInstance(tp_result['take_profit_levels'], list,
                             "Multiple take profit strategy should return a list of levels")
        self.assertEqual(len(tp_result['take_profit_levels']), 3,
                        "Should have 3 take profit levels as configured")
        
        # Test trailing stop
        tp_result = self.risk_manager.apply_take_profit_strategy(signal, 'trailing')
        self.assertTrue('trailing_stop' in tp_result,
                       "Trailing stop strategy should include trailing stop settings")
        self.assertAlmostEqual(tp_result['trailing_stop']['activation'], signal['price'] + 0.0020, places=4,
                              msg="Trailing stop activation should be 20 pips from entry")
    
    def test_register_and_close_trade(self):
        """Test registering and closing trades."""
        # Register a trade
        trade = {
            'pair': 'EURUSD',
            'direction': 'buy',
            'entry_price': 1.1000,
            'stop_loss': 1.0950,
            'take_profit': 1.1100,
            'position_size': 0.2,
            'entry_time': datetime.now()
        }
        
        self.risk_manager.register_trade(trade)
        
        # Check it was registered
        self.assertIn('EURUSD', self.risk_manager.active_trades,
                     "Trade should be registered in active trades")
        
        # Close the trade with profit
        closed_trade = self.risk_manager.close_trade('EURUSD', 1.1050, 'manual')
        
        # Check trade is closed
        self.assertNotIn('EURUSD', self.risk_manager.active_trades,
                        "Trade should be removed from active trades")
        
        # Check profit calculation
        self.assertGreater(closed_trade['pnl_money'], 0,
                          "Trade closed with profit should have positive PnL")
        self.assertGreater(closed_trade['pnl_pips'], 0,
                          "Trade closed with profit should have positive pip PnL")
        
        # Register another trade and close with loss
        trade = {
            'pair': 'GBPUSD',
            'direction': 'buy',
            'entry_price': 1.3000,
            'stop_loss': 1.2950,
            'take_profit': 1.3100,
            'position_size': 0.2,
            'entry_time': datetime.now()
        }
        
        self.risk_manager.register_trade(trade)
        closed_trade = self.risk_manager.close_trade('GBPUSD', 1.2980, 'stop_loss')
        
        # Check loss calculation
        self.assertLess(closed_trade['pnl_money'], 0,
                       "Trade closed with loss should have negative PnL")
        self.assertLess(closed_trade['pnl_pips'], 0,
                       "Trade closed with loss should have negative pip PnL")
    
    def test_trailing_stop_adjustment(self):
        """Test trailing stop adjustment."""
        # Register a trade with trailing stop
        trade = {
            'pair': 'EURUSD',
            'direction': 'buy',
            'entry_price': 1.1000,
            'stop_loss': 1.0950,
            'take_profit': 1.1100,
            'position_size': 0.2,
            'entry_time': datetime.now(),
            'trailing_stop': {
                'active': False,
                'activation': 1.1020,  # 20 pips profit to activate
                'trail_pips': 0.0010,  # 10 pips trailing distance
                'current_stop': 1.0950  # Initial stop same as stop_loss
            }
        }
        
        self.risk_manager.register_trade(trade)
        
        # Price moves up but not enough to activate trailing stop
        self.risk_manager._adjust_trailing_stop('EURUSD', 1.1010)
        self.assertFalse(self.risk_manager.active_trades['EURUSD']['trailing_stop']['active'],
                        "Trailing stop should not be activated yet")
        
        # Price moves up enough to activate trailing stop
        self.risk_manager._adjust_trailing_stop('EURUSD', 1.1030)
        self.assertTrue(self.risk_manager.active_trades['EURUSD']['trailing_stop']['active'],
                       "Trailing stop should be activated")
        
        # Get the current trailing stop
        current_stop = self.risk_manager.active_trades['EURUSD']['trailing_stop']['current_stop']
        self.assertGreater(current_stop, 1.0950,
                          "Trailing stop should be moved up from original stop loss")
        
        # Price moves up more, trailing stop should follow
        old_stop = current_stop
        self.risk_manager._adjust_trailing_stop('EURUSD', 1.1050)
        new_stop = self.risk_manager.active_trades['EURUSD']['trailing_stop']['current_stop']
        self.assertGreater(new_stop, old_stop,
                          "Trailing stop should be moved up as price increases")
    
    def test_check_aged_positions(self):
        """Test identifying positions that have exceeded aging limit."""
        # Register a trade that will be considered old
        old_trade_time = datetime.now() - timedelta(hours=25)  # Older than position_aging_hours
        trade = {
            'pair': 'EURUSD',
            'direction': 'buy',
            'entry_price': 1.1000,
            'stop_loss': 1.0950,
            'take_profit': 1.1100,
            'position_size': 0.2,
            'entry_time': old_trade_time
        }
        
        self.risk_manager.register_trade(trade)
        
        # Register a fresh trade
        fresh_trade = {
            'pair': 'GBPUSD',
            'direction': 'buy',
            'entry_price': 1.3000,
            'stop_loss': 1.2950,
            'take_profit': 1.3100,
            'position_size': 0.2,
            'entry_time': datetime.now()
        }
        
        self.risk_manager.register_trade(fresh_trade)
        
        # Check for aged positions
        aged_positions = self.risk_manager.check_aged_positions()
        
        # Should identify EURUSD as aged but not GBPUSD
        self.assertIn('EURUSD', aged_positions,
                     "EURUSD should be identified as an aged position")
        self.assertNotIn('GBPUSD', aged_positions,
                        "GBPUSD should not be identified as an aged position")
    
    def test_re_evaluate_position(self):
        """Test re-evaluating positions based on current market conditions."""
        # Register a trade
        trade = {
            'pair': 'EURUSD',
            'direction': 'buy',
            'entry_price': 1.1000,
            'stop_loss': 1.0950,
            'take_profit': 1.1100,
            'position_size': 0.2,
            'entry_time': datetime.now() - timedelta(hours=2),  # 2 hours old
            'pnl_pips': 20,  # In profit by 20 pips
            'pnl_money': 40  # $40 profit
        }
        
        self.risk_manager.register_trade(trade)
        
        # Re-evaluate profitable position
        action = self.risk_manager.re_evaluate_position('EURUSD', 1.1020, {
            'market_condition': 'bullish',
            'volatility': 'low'
        })
        
        # Should generally recommend holding or adjusting TP/SL for profitable trades
        self.assertIn(action, ['hold', 'adjust_tp', 'adjust_sl'],
                     f"Expected action to be hold/adjust for profitable trade, got {action}")
        
        # Register a losing trade
        losing_trade = {
            'pair': 'GBPUSD',
            'direction': 'buy',
            'entry_price': 1.3000,
            'stop_loss': 1.2950,
            'take_profit': 1.3100,
            'position_size': 0.2,
            'entry_time': datetime.now() - timedelta(hours=6),  # 6 hours old
            'pnl_pips': -30,  # Loss of 30 pips
            'pnl_money': -60  # $60 loss
        }
        
        self.risk_manager.register_trade(losing_trade)
        
        # Re-evaluate losing position in worsening market
        action = self.risk_manager.re_evaluate_position('GBPUSD', 1.2970, {
            'market_condition': 'bearish',  # Adverse condition for long trade
            'volatility': 'high'
        })
        
        # Should generally recommend closing losing trades in adverse conditions
        self.assertIn(action, ['close', 'adjust_sl'],
                     f"Expected action to be close/adjust for losing trade in adverse conditions, got {action}")
    
    def test_get_performance_metrics(self):
        """Test performance metrics calculation."""
        # Set initial balance
        self.risk_manager.update_account_balance(10000.0)
        self.risk_manager.starting_balance = 10000.0
        
        # Add some trade history
        self.risk_manager.trade_history = [
            {
                'pair': 'EURUSD',
                'direction': 'buy',
                'entry_price': 1.1000,
                'exit_price': 1.1050,
                'entry_time': datetime.now() - timedelta(hours=5),
                'exit_time': datetime.now() - timedelta(hours=4),
                'position_size': 0.2,
                'pnl_pips': 50,
                'pnl_money': 100,
                'exit_reason': 'take_profit'
            },
            {
                'pair': 'GBPUSD',
                'direction': 'sell',
                'entry_price': 1.3000,
                'exit_price': 1.3030,
                'entry_time': datetime.now() - timedelta(hours=3),
                'exit_time': datetime.now() - timedelta(hours=2),
                'position_size': 0.1,
                'pnl_pips': -30,
                'pnl_money': -40,
                'exit_reason': 'stop_loss'
            },
            {
                'pair': 'USDJPY',
                'direction': 'buy',
                'entry_price': 110.00,
                'exit_price': 110.50,
                'entry_time': datetime.now() - timedelta(hours=2),
                'exit_time': datetime.now() - timedelta(hours=1),
                'position_size': 0.3,
                'pnl_pips': 50,
                'pnl_money': 150,
                'exit_reason': 'take_profit'
            }
        ]
        
        # Update current balance to reflect trades
        self.risk_manager.update_account_balance(10210.0)  # 10000 + 100 - 40 + 150
        
        # Get performance metrics
        metrics = self.risk_manager.get_performance_metrics()
        
        # Test basic metrics
        self.assertEqual(metrics['starting_balance'], 10000.0)
        self.assertEqual(metrics['current_balance'], 10210.0)
        self.assertEqual(metrics['absolute_pnl'], 210.0)
        self.assertAlmostEqual(metrics['percent_pnl'], 2.1, places=1)
        
        # Test trading metrics
        self.assertEqual(metrics['total_trades'], 3)
        self.assertAlmostEqual(metrics['win_rate'], 66.67, places=1)  # 2 out of 3 winning
        self.assertEqual(metrics['avg_pnl_money'], 70.0)  # (100 - 40 + 150) / 3
        self.assertAlmostEqual(metrics['profit_factor'], 6.25, places=2)  # (100 + 150) / 40


if __name__ == '__main__':
    unittest.main()
