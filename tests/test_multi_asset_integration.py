import unittest
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch

# Add the src directory to the path so we can import the modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.risk.correlation_manager import CorrelationManager
from src.trading.session_manager import SessionManager
from src.portfolio.portfolio_optimizer import PortfolioOptimizer
from src.trading.multi_asset_integrator import MultiAssetIntegrator
from src.utils.config_loader import ConfigLoader


class TestMultiAssetIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        # Mock the config loader
        self.config_patcher = patch('src.utils.config_loader.ConfigLoader')
        self.mock_config_loader = self.config_patcher.start()
        
        # Create a mock configuration
        self.mock_config = {
            'correlation': {
                'high_correlation_threshold': 0.7,
                'medium_correlation_threshold': 0.5,
                'data_lookback_days': 30,
                'max_correlated_exposure': 0.15,
                'max_same_direction_exposure': 0.25,
                'data_dir': 'data',
                'predefined_correlation_groups': {
                    'major_usd_pairs': ['EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD'],
                    'jpy_pairs': ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY'],
                }
            },
            'sessions': {
                'trading_sessions': {
                    'london': {'start': '08:00', 'end': '17:00', 'timezone': 'UTC'},
                    'newyork': {'start': '13:00', 'end': '22:00', 'timezone': 'UTC'},
                },
                'rotation_settings': {
                    'enabled': True,
                    'prefer_forex_in_session_overlaps': True,
                    'prefer_synthetics_in_low_liquidity': True,
                },
            },
            'portfolio': {
                'max_active_instruments': 10,
                'max_same_category': 5,
                'base_allocation': {
                    'forex': 0.6,
                    'synthetic': 0.4,
                },
                'data_dir': 'data',
            },
            'multi_asset': {
                'enabled': True,
                'strategy_strengths': {
                    'forex': {
                        'moving_average_cross': 0.85,
                        'bollinger_breakout': 0.75,
                    },
                    'synthetic': {
                        'volatility': {
                            'moving_average_cross': 0.80,
                            'bollinger_breakout': 0.90,
                        }
                    }
                }
            },
            'trading': {
                'symbols': {
                    'forex': [
                        {'name': 'EURUSD', 'type': 'forex'},
                        {'name': 'GBPUSD', 'type': 'forex'},
                    ],
                    'synthetic': [
                        {'name': 'Volatility 75 Index', 'type': 'synthetic', 'sub_type': 'volatility'},
                        {'name': 'Crash 1000 Index', 'type': 'synthetic', 'sub_type': 'crash_boom'},
                    ]
                }
            }
        }
        
        self.mock_config_loader.return_value.get_config.return_value = self.mock_config
        
        # Create instances of our components with mocked dependencies
        self.correlation_manager = CorrelationManager(self.mock_config)
        self.session_manager = SessionManager(self.mock_config)
        self.portfolio_optimizer = PortfolioOptimizer(self.mock_config)
        
        # Create a MultiAssetIntegrator with mocked components
        self.integrator = MultiAssetIntegrator(
            self.mock_config,
            self.correlation_manager,
            self.session_manager,
            self.portfolio_optimizer
        )
        
        # Mock the market data
        self.market_data = {
            'EURUSD': self._create_mock_data('EURUSD'),
            'GBPUSD': self._create_mock_data('GBPUSD'),
            'Volatility 75 Index': self._create_mock_data('Volatility 75 Index'),
            'Crash 1000 Index': self._create_mock_data('Crash 1000 Index'),
        }
    
    def tearDown(self):
        """Tear down test fixtures"""
        self.config_patcher.stop()
    
    def _create_mock_data(self, symbol):
        """Create mock market data for testing"""
        periods = 100
        index = [datetime.now() - timedelta(minutes=i) for i in range(periods, 0, -1)]
        
        # Create random data with a slight trend
        if 'Volatility' in symbol:
            volatility = 0.002  # Higher volatility for synthetic indices
        else:
            volatility = 0.0005  # Lower volatility for forex
            
        close = np.random.normal(1.0, volatility, periods).cumsum() + 1.0
        
        # Make up some market data with typical OHLCV structure
        data = pd.DataFrame({
            'open': close - np.random.normal(0, volatility/2, periods),
            'high': close + np.random.normal(volatility, volatility/2, periods),
            'low': close - np.random.normal(volatility, volatility/2, periods),
            'close': close,
            'volume': np.random.normal(1000, 200, periods).astype(int)
        }, index=index)
        
        return data
    
    def test_get_active_instruments(self):
        """Test that the integrator correctly selects instruments for trading"""
        # Mock current time to be in the London-NY overlap for predictable results
        current_time = datetime.strptime("14:00", "%H:%M").time()
        
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.combine(datetime.today(), current_time)
            mock_datetime.strptime = datetime.strptime
            
            # Test with overlap session to prioritize forex
            active_instruments = self.integrator.get_active_instruments(self.market_data)
            
            # Should include forex instruments during overlap
            self.assertIn('EURUSD', active_instruments)
            self.assertIn('GBPUSD', active_instruments)
            
            # Should still include some synthetic but with lower priority
            # Verify the correct number of instruments
            self.assertLessEqual(len(active_instruments), self.mock_config['portfolio']['max_active_instruments'])
    
    def test_get_optimal_strategy(self):
        """Test that the optimal strategy is selected based on instrument type"""
        # Test for forex pair
        forex_strategy = self.integrator.get_optimal_strategy('EURUSD', self.market_data['EURUSD'])
        self.assertEqual(forex_strategy, 'moving_average_cross')  # Should be the highest rated for forex
        
        # Test for synthetic index
        synthetic_strategy = self.integrator.get_optimal_strategy('Volatility 75 Index', 
                                                                self.market_data['Volatility 75 Index'])
        self.assertEqual(synthetic_strategy, 'bollinger_breakout')  # Should be the highest rated for volatility
    
    def test_validate_new_position(self):
        """Test position validation based on correlation and portfolio rules"""
        # Setup a mock existing position
        existing_positions = [
            {'symbol': 'EURUSD', 'type': 'forex', 'direction': 'buy', 'size': 0.1, 'strategy': 'moving_average_cross'}
        ]
        
        # Mock correlation data to show high correlation between EURUSD and GBPUSD
        self.correlation_manager.get_correlation = MagicMock(return_value=0.85)
        
        # Test adding a correlated position in the same direction
        is_valid = self.integrator.validate_new_position(
            'GBPUSD', 'buy', 0.1, existing_positions, self.market_data)
        self.assertFalse(is_valid)  # Should be rejected due to high correlation
        
        # Test adding a position in the opposite direction
        is_valid = self.integrator.validate_new_position(
            'GBPUSD', 'sell', 0.1, existing_positions, self.market_data)
        self.assertTrue(is_valid)  # Should be allowed as it hedges the correlation
        
        # Test adding a synthetic index (uncorrelated with forex)
        self.correlation_manager.get_correlation = MagicMock(return_value=0.2)
        is_valid = self.integrator.validate_new_position(
            'Volatility 75 Index', 'buy', 0.1, existing_positions, self.market_data)
        self.assertTrue(is_valid)  # Should be allowed as it's uncorrelated
    
    def test_position_sizing_adjustment(self):
        """Test that position sizes are adjusted based on portfolio allocation"""
        # Mock portfolio allocations
        self.portfolio_optimizer.get_instrument_allocation = MagicMock()
        
        # Higher allocation for EURUSD
        self.portfolio_optimizer.get_instrument_allocation.side_effect = lambda x: 0.15 if x == 'EURUSD' else 0.05
        
        # Test position size adjustment
        adjusted_size = self.integrator.adjust_position_size('EURUSD', 0.1)
        self.assertEqual(adjusted_size, 0.15)  # Should increase based on allocation
        
        adjusted_size = self.integrator.adjust_position_size('Volatility 75 Index', 0.1)
        self.assertEqual(adjusted_size, 0.05)  # Should decrease based on allocation


if __name__ == '__main__':
    unittest.main()
