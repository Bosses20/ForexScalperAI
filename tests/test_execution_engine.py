"""
Execution Engine Test Module

This module contains tests for the Execution Engine functionality,
ensuring proper signal execution, position management, and exchange interaction.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import ccxt

from src.execution.execution_engine import ExecutionEngine
from src.risk.risk_manager import RiskManager


class TestExecutionEngine(unittest.TestCase):
    """Test suite for ExecutionEngine class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock risk manager
        self.risk_manager = MagicMock(spec=RiskManager)
        
        # Set up risk manager mock methods
        self.risk_manager.calculate_position_size.return_value = 0.1
        self.risk_manager.validate_trade.return_value = True
        self.risk_manager.update_trade = MagicMock()
        self.risk_manager.close_trade.return_value = {
            'pair': 'EURUSD',
            'entry_price': 1.1000,
            'exit_price': 1.1050,
            'direction': 'buy',
            'pnl_pips': 50,
            'pnl_money': 50.0,
            'exit_reason': 'take_profit',
            'position_size': 0.1,
            'entry_time': datetime.now() - timedelta(hours=1),
            'exit_time': datetime.now()
        }
        
        # Create a mock configuration
        self.execution_config = {
            'simulation_mode': True,  # Use simulation mode for testing
            'exchange_id': 'binance',
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'slippage_model': {
                'simulation': {
                    'min_pips': 0,
                    'max_pips': 2,
                    'distribution': 'normal'
                }
            },
            'execution_timing': {
                'simulation': {
                    'min_ms': 50,
                    'max_ms': 200
                }
            }
        }
        
        # Initialize the execution engine
        self.engine = ExecutionEngine(self.execution_config, self.risk_manager)
        
        # Create mock signal for testing
        self.signal = {
            'pair': 'EURUSD',
            'direction': 'buy',
            'price': 1.1000,
            'stop_loss': 1.0950,
            'take_profit': 1.1100,
            'position_size': None,  # Let risk manager calculate
            'strategy': 'test_strategy',
            'confidence': 0.8,
            'timestamp': datetime.now().isoformat()
        }
    
    @patch('asyncio.run')
    async def test_execute_signal_simulation(self, mock_asyncio_run):
        """Test execution of trade signals in simulation mode."""
        # Set up mock
        mock_asyncio_run.return_value = True
        
        # Execute signal
        result = await self.engine.execute_signal(self.signal)
        
        # Check that the signal was processed
        self.assertIsNotNone(result)
        self.assertEqual(result['pair'], 'EURUSD')
        self.assertEqual(result['direction'], 'buy')
        self.assertTrue('execution_price' in result)
        self.assertTrue('position_size' in result)
        self.assertTrue('execution_time' in result)
        
        # Verify risk manager was called
        self.risk_manager.calculate_position_size.assert_called_once()
        self.risk_manager.validate_trade.assert_called_once()
        self.risk_manager.register_trade.assert_called_once()
    
    @patch('ccxt.binance')
    @patch('asyncio.run')
    async def test_execute_signal_real(self, mock_asyncio_run, mock_binance):
        """Test execution of trade signals with a real exchange."""
        # Disable simulation mode
        self.engine.simulation_mode = False
        
        # Set up exchange mock
        mock_exchange = MagicMock()
        mock_exchange.markets = {'EURUSD/USD': {'id': 'EURUSD/USD'}}
        mock_exchange.create_order.return_value = {
            'id': '12345',
            'price': 1.1002,
            'amount': 0.1,
            'status': 'closed'
        }
        mock_exchange.fetch_order.return_value = {
            'id': '12345',
            'price': 1.1002,
            'amount': 0.1,
            'status': 'closed'
        }
        mock_binance.return_value = mock_exchange
        self.engine.exchange = mock_exchange
        
        # Set up normalization mock
        self.engine._normalize_pair = MagicMock(return_value='EURUSD/USD')
        
        # Execute signal
        result = await self.engine.execute_signal(self.signal)
        
        # Check that the signal was processed
        self.assertIsNotNone(result)
        self.assertEqual(result['pair'], 'EURUSD')
        self.assertTrue('execution_price' in result)
        
        # Verify exchange API was called
        mock_exchange.create_order.assert_called_once()
    
    def test_normalize_pair(self):
        """Test currency pair normalization for different exchanges."""
        # Test for standard forex syntax
        self.engine.config['exchange_id'] = 'oanda'
        pair = 'EUR/USD'
        normalized = self.engine._normalize_pair(pair)
        self.assertEqual(normalized, 'EUR_USD')
        
        # Test for binance-style syntax
        self.engine.config['exchange_id'] = 'binance'
        normalized = self.engine._normalize_pair(pair)
        self.assertEqual(normalized, 'EURUSD')
        
        # Test for crypto pairs
        crypto_pair = 'BTC/USDT'
        self.engine.config['exchange_id'] = 'binance'
        normalized = self.engine._normalize_pair(crypto_pair)
        self.assertEqual(normalized, 'BTCUSDT')
    
    async def test_simulate_execution(self):
        """Test simulated trade execution."""
        # Call the simulation method directly
        result = self.engine._simulate_execution(
            'EURUSD', 'buy', 1.1000, 0.1, 1.0950, 1.1100
        )
        
        # Check the simulation results
        self.assertEqual(result['pair'], 'EURUSD')
        self.assertEqual(result['direction'], 'buy')
        self.assertIsNotNone(result['execution_price'])
        self.assertIsNotNone(result['execution_time'])
        self.assertIsNotNone(result['slippage_pips'])
        
        # Test sell direction
        result = self.engine._simulate_execution(
            'EURUSD', 'sell', 1.1000, 0.1, 1.1050, 1.0900
        )
        
        self.assertEqual(result['direction'], 'sell')
        
    @patch('asyncio.run')
    async def test_close_position(self, mock_asyncio_run):
        """Test closing an active position."""
        # Add a position to close
        self.engine.active_positions['EURUSD'] = {
            'pair': 'EURUSD',
            'direction': 'buy',
            'entry_price': 1.1000,
            'stop_loss': 1.0950,
            'take_profit': 1.1100,
            'position_size': 0.1,
            'entry_time': datetime.now() - timedelta(hours=1)
        }
        
        # Mock market price
        self.engine._get_market_price = MagicMock(return_value=1.1050)
        
        # Close the position
        result = await self.engine.close_position('EURUSD', 'take_profit')
        
        # Check the results
        self.assertTrue('exit_price' in result)
        self.assertEqual(result['exit_reason'], 'take_profit')
        
        # Verify the position was removed
        self.assertNotIn('EURUSD', self.engine.active_positions)
        
        # Verify risk manager was called
        self.risk_manager.close_trade.assert_called_once()
    
    def test_get_market_price(self):
        """Test retrieving market price."""
        # Test in simulation mode
        price = self.engine._get_market_price('EURUSD')
        self.assertIsNotNone(price)
        
        # Test with mock exchange
        self.engine.simulation_mode = False
        mock_exchange = MagicMock()
        mock_exchange.fetch_ticker.return_value = {'last': 1.1025}
        self.engine.exchange = mock_exchange
        self.engine._normalize_pair = MagicMock(return_value='EURUSD')
        
        price = self.engine._get_market_price('EURUSD')
        self.assertEqual(price, 1.1025)
        mock_exchange.fetch_ticker.assert_called_once()
    
    def test_update_positions(self):
        """Test updating active positions with market data."""
        # Add an active position
        self.engine.active_positions['EURUSD'] = {
            'pair': 'EURUSD',
            'direction': 'buy',
            'entry_price': 1.1000,
            'stop_loss': 1.0950,
            'take_profit': 1.1100,
            'position_size': 0.1,
            'entry_time': datetime.now() - timedelta(hours=1)
        }
        
        # Create market data
        market_data = {
            'EURUSD': pd.DataFrame({
                'open': [1.0990, 1.1010, 1.1030],
                'high': [1.1010, 1.1030, 1.1050],
                'low': [1.0980, 1.1000, 1.1020],
                'close': [1.1010, 1.1030, 1.1050],
                'volume': [100, 150, 120]
            })
        }
        
        # Patch close_position method
        with patch.object(ExecutionEngine, 'close_position', new_callable=AsyncMock) as mock_close:
            mock_close.return_value = {'pair': 'EURUSD', 'exit_reason': 'take_profit'}
            
            # Update positions to hit take profit
            self.engine.update_positions(market_data)
            
            # Verify position updates and closures
            mock_close.assert_called_once()
            self.risk_manager.update_trade.assert_called_once_with('EURUSD', 1.1050)
    
    def test_get_execution_stats(self):
        """Test retrieving execution statistics."""
        # Populate with some test data
        self.engine.execution_stats = {
            'orders_placed': 10,
            'orders_filled': 8,
            'orders_canceled': 1,
            'orders_rejected': 1,
            'slippage_total_pips': 16,
            'execution_latency_ms': [75, 120, 82, 95, 105, 88, 92, 110]
        }
        
        # Get stats
        stats = self.engine.get_execution_stats()
        
        # Verify calculations
        self.assertEqual(stats['orders_placed'], 10)
        self.assertEqual(stats['orders_filled'], 8)
        self.assertEqual(stats['avg_slippage_pips'], 2.0)  # 16 / 8
        self.assertAlmostEqual(stats['avg_execution_latency_ms'], 95.875, places=3)
        self.assertEqual(stats['max_execution_latency_ms'], 120)
        self.assertEqual(stats['min_execution_latency_ms'], 75)
    
    def test_empty_positions_update(self):
        """Test updating positions when none are active."""
        # Ensure no active positions
        self.engine.active_positions = {}
        
        # Create market data
        market_data = {
            'EURUSD': pd.DataFrame({
                'open': [1.0990, 1.1010, 1.1030],
                'high': [1.1010, 1.1030, 1.1050],
                'low': [1.0980, 1.1000, 1.1020],
                'close': [1.1010, 1.1030, 1.1050],
                'volume': [100, 150, 120]
            })
        }
        
        # Update should return empty list and not raise errors
        result = self.engine.update_positions(market_data)
        self.assertEqual(result, [])
    
    @patch('ccxt.binance')
    def test_initialize_exchange(self, mock_binance):
        """Test exchange initialization."""
        # Set up a mock exchange
        mock_exchange = MagicMock()
        mock_exchange.load_markets.return_value = {'EURUSD': {}, 'GBPUSD': {}}
        mock_binance.return_value = mock_exchange
        
        # Create a new execution engine with simulation mode off
        config = self.execution_config.copy()
        config['simulation_mode'] = False
        engine = ExecutionEngine(config, self.risk_manager)
        
        # Verify exchange initialization
        mock_binance.assert_called_once()
        mock_exchange.load_markets.assert_called_once()
    
    def test_error_handling_no_exchange(self):
        """Test error handling when no exchange is configured in real mode."""
        # Create config with simulation off but no exchange
        bad_config = {
            'simulation_mode': False
        }
        
        # Should raise ValueError
        with self.assertRaises(ValueError):
            ExecutionEngine(bad_config, self.risk_manager)
    
    def test_error_handling_no_credentials(self):
        """Test error handling when no API credentials are provided."""
        # Create config with simulation off but no credentials
        bad_config = {
            'simulation_mode': False,
            'exchange_id': 'binance'
        }
        
        # Should raise ValueError
        with self.assertRaises(ValueError):
            ExecutionEngine(bad_config, self.risk_manager)
    
    def test_error_handling_invalid_exchange(self):
        """Test error handling for invalid exchange."""
        # Create config with invalid exchange
        bad_config = {
            'simulation_mode': False,
            'exchange_id': 'invalid_exchange_name',
            'api_key': 'test',
            'api_secret': 'test'
        }
        
        # Should raise ValueError
        with self.assertRaises(ValueError):
            ExecutionEngine(bad_config, self.risk_manager)
    
    async def test_execute_signal_validation_failure(self):
        """Test signal execution when validation fails."""
        # Set up risk manager to fail validation
        self.risk_manager.validate_trade.return_value = False
        
        # Execute signal
        result = await self.engine.execute_signal(self.signal)
        
        # Should return with error
        self.assertFalse(result['success'])
        self.assertTrue('validation_failed' in result['reason'])
        
        # No trade should be registered
        self.risk_manager.register_trade.assert_not_called()


if __name__ == '__main__':
    unittest.main()
