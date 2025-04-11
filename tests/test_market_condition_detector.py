"""
Market Condition Detector Test Module

This module contains tests for the market condition detector functionality,
ensuring proper detection of different market states and strategy recommendations.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.analysis.market_condition_detector import MarketConditionDetector


class TestMarketConditionDetector(unittest.TestCase):
    """Test suite for MarketConditionDetector class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock configuration
        self.config = {
            'market_condition_detector': {
                'enabled': True,
                'trend_lookback': 50,
                'volatility_window': 10,
                'liquidity_threshold': 0.4,
                'trend_strength_threshold': 0.6,
                'cache_expiry_seconds': 300,
                'volatility_categories': {
                    'low': 0.4,
                    'medium': 0.8,
                    'high': 10.0
                }
            },
            'multi_asset': {
                'strategy_strengths': {
                    'forex': {
                        'moving_average_cross': 0.85,
                        'bollinger_breakout': 0.75,
                        'break_and_retest': 0.85,
                        'break_of_structure': 0.75,
                        'fair_value_gap': 0.70
                    },
                    'synthetic': {
                        'volatility_index': {
                            'bollinger_breakout': 0.90,
                            'moving_average_cross': 0.70
                        }
                    }
                }
            },
            'trading': {
                'symbols': {
                    'forex': [
                        {'name': 'EURUSD', 'type': 'forex'},
                        {'name': 'GBPUSD', 'type': 'forex'}
                    ],
                    'synthetic': [
                        {'name': 'VOLATILITY_10', 'type': 'synthetic', 'sub_type': 'volatility_index'}
                    ]
                }
            }
        }
        
        # Initialize the detector
        self.detector = MarketConditionDetector(self.config)
    
    def generate_uptrend_data(self, length=200):
        """Generate sample data for an uptrend."""
        base = 1.0
        dates = [datetime.now() - timedelta(hours=i) for i in range(length, 0, -1)]
        
        data = []
        for i in range(length):
            # Add small trend component
            trend_factor = i / 500.0
            
            # Add some noise
            noise = np.random.normal(0, 0.001)
            
            # Calculate OHLC values
            close = base + trend_factor + noise
            high = close + abs(np.random.normal(0, 0.0005))
            low = close - abs(np.random.normal(0, 0.0005))
            open_price = close - np.random.normal(0, 0.001) * (1 if np.random.random() > 0.5 else -1)
            
            # Add to data
            data.append({
                'timestamp': dates[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': 100 + np.random.randint(0, 50)
            })
        
        return pd.DataFrame(data)
    
    def generate_downtrend_data(self, length=200):
        """Generate sample data for a downtrend."""
        base = 1.1
        dates = [datetime.now() - timedelta(hours=i) for i in range(length, 0, -1)]
        
        data = []
        for i in range(length):
            # Add small trend component
            trend_factor = i / 500.0
            
            # Add some noise
            noise = np.random.normal(0, 0.001)
            
            # Calculate OHLC values
            close = base - trend_factor + noise
            high = close + abs(np.random.normal(0, 0.0005))
            low = close - abs(np.random.normal(0, 0.0005))
            open_price = close - np.random.normal(0, 0.001) * (1 if np.random.random() > 0.5 else -1)
            
            # Add to data
            data.append({
                'timestamp': dates[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': 100 + np.random.randint(0, 50)
            })
        
        return pd.DataFrame(data)
    
    def generate_ranging_data(self, length=200):
        """Generate sample data for a ranging market."""
        base = 1.05
        dates = [datetime.now() - timedelta(hours=i) for i in range(length, 0, -1)]
        
        data = []
        for i in range(length):
            # Add oscillation component
            oscillation = 0.02 * np.sin(i / 20.0)
            
            # Add some noise
            noise = np.random.normal(0, 0.002)
            
            # Calculate OHLC values
            close = base + oscillation + noise
            high = close + abs(np.random.normal(0, 0.001))
            low = close - abs(np.random.normal(0, 0.001))
            open_price = close - np.random.normal(0, 0.001) * (1 if np.random.random() > 0.5 else -1)
            
            # Add to data
            data.append({
                'timestamp': dates[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': 100 + np.random.randint(0, 50)
            })
        
        return pd.DataFrame(data)
    
    def generate_choppy_data(self, length=200):
        """Generate sample data for a choppy market."""
        base = 1.03
        dates = [datetime.now() - timedelta(hours=i) for i in range(length, 0, -1)]
        
        data = []
        for i in range(length):
            # Add random oscillation
            noise = np.random.normal(0, 0.005)
            
            # Calculate OHLC values
            close = base + noise
            high = close + abs(np.random.normal(0, 0.002))
            low = close - abs(np.random.normal(0, 0.002))
            open_price = close - np.random.normal(0, 0.003) * (1 if np.random.random() > 0.5 else -1)
            
            # Add to data
            data.append({
                'timestamp': dates[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': 100 + np.random.randint(0, 50)
            })
        
        return pd.DataFrame(data)
        
    def test_detect_uptrend(self):
        """Test that uptrend is correctly detected."""
        # Generate uptrend data
        data = self.generate_uptrend_data()
        
        # Detect market condition
        condition = self.detector.detect_market_condition('EURUSD', data)
        
        # Check that trend is correctly identified
        self.assertIn(condition['trend'], ['bullish', 'weak_bullish'], 
                     f"Expected bullish or weak_bullish trend, got {condition['trend']}")
        
        # Check that trend strength is reasonably high
        self.assertGreater(condition['trend_strength'], 0.5, 
                          f"Expected trend strength > 0.5, got {condition['trend_strength']}")
    
    def test_detect_downtrend(self):
        """Test that downtrend is correctly detected."""
        # Generate downtrend data
        data = self.generate_downtrend_data()
        
        # Detect market condition
        condition = self.detector.detect_market_condition('EURUSD', data)
        
        # Check that trend is correctly identified
        self.assertIn(condition['trend'], ['bearish', 'weak_bearish'], 
                     f"Expected bearish or weak_bearish trend, got {condition['trend']}")
        
        # Check that trend strength is reasonably high
        self.assertGreater(condition['trend_strength'], 0.5, 
                          f"Expected trend strength > 0.5, got {condition['trend_strength']}")
    
    def test_detect_ranging_market(self):
        """Test that ranging market is correctly detected."""
        # Generate ranging data
        data = self.generate_ranging_data()
        
        # Detect market condition
        condition = self.detector.detect_market_condition('EURUSD', data)
        
        # Check that trend is correctly identified (might be ranging or weak trend)
        self.assertIn(condition['trend'], ['ranging', 'weak_bullish', 'weak_bearish'], 
                     f"Expected ranging or weak trend, got {condition['trend']}")
        
        # Check recommended strategies for ranging market
        self.assertTrue(any('bollinger' in s for s in condition['recommended_strategies']) or 
                       any('value_gap' in s for s in condition['recommended_strategies']),
                       f"Expected ranging strategies, got {condition['recommended_strategies']}")
    
    def test_detect_choppy_market(self):
        """Test that choppy market is correctly detected."""
        # Generate choppy data
        data = self.generate_choppy_data()
        
        # Detect market condition
        condition = self.detector.detect_market_condition('EURUSD', data)
        
        # Check that volatility is correctly identified
        self.assertEqual(condition['volatility'], 'high', 
                        f"Expected high volatility, got {condition['volatility']}")
        
        # Check that confidence is lower for choppy markets
        self.assertLess(condition['confidence'], 0.7, 
                       f"Expected confidence < 0.7 for choppy market, got {condition['confidence']}")
    
    def test_strategy_selection(self):
        """Test that appropriate strategies are selected for different market conditions."""
        # Test strategy selection for uptrend
        uptrend_data = self.generate_uptrend_data()
        strategy, confidence = self.detector.get_optimal_strategy('EURUSD', uptrend_data)
        
        self.assertIsNotNone(strategy, "Expected a strategy to be selected")
        self.assertGreater(confidence, 0.5, "Expected confidence > 0.5")
        
        # Test strategy selection for downtrend
        downtrend_data = self.generate_downtrend_data()
        strategy, confidence = self.detector.get_optimal_strategy('EURUSD', downtrend_data)
        
        self.assertIsNotNone(strategy, "Expected a strategy to be selected")
        self.assertGreater(confidence, 0.5, "Expected confidence > 0.5")
        
        # Test different strategies for forex vs synthetic
        forex_strategy, _ = self.detector.get_optimal_strategy('EURUSD', uptrend_data)
        synthetic_strategy, _ = self.detector.get_optimal_strategy('VOLATILITY_10', uptrend_data)
        
        # The selected strategies might be the same for this test data, but they should both be valid
        self.assertIn(forex_strategy, self.config['multi_asset']['strategy_strengths']['forex'].keys(),
                     f"Expected forex strategy to be in config, got {forex_strategy}")
    
    def test_should_trade_now(self):
        """Test the trading recommendation functionality."""
        # Should trade in clear uptrend
        uptrend_data = self.generate_uptrend_data()
        should_trade = self.detector.should_trade_now('EURUSD', uptrend_data)
        self.assertTrue(should_trade, "Expected to recommend trading in clear uptrend")
        
        # Should trade in clear downtrend
        downtrend_data = self.generate_downtrend_data()
        should_trade = self.detector.should_trade_now('EURUSD', downtrend_data)
        self.assertTrue(should_trade, "Expected to recommend trading in clear downtrend")
        
        # May or may not recommend trading in choppy market (should be conservative)
        choppy_data = self.generate_choppy_data()
        should_trade = self.detector.should_trade_now('EURUSD', choppy_data, min_confidence=0.7)
        self.assertFalse(should_trade, "Expected not to recommend trading in choppy market with high confidence threshold")
    
    def test_caching(self):
        """Test that caching works correctly."""
        data = self.generate_uptrend_data()
        
        # First detection
        start_time = datetime.now()
        first_condition = self.detector.detect_market_condition('EURUSD', data)
        first_detection_time = datetime.now() - start_time
        
        # Second detection (should use cache)
        start_time = datetime.now()
        second_condition = self.detector.detect_market_condition('EURUSD', data)
        second_detection_time = datetime.now() - start_time
        
        # Check that second detection is using cached result
        self.assertEqual(first_condition, second_condition, "Cached result should match original")
        
        # Force refresh
        start_time = datetime.now()
        refresh_condition = self.detector.detect_market_condition('EURUSD', data, force_refresh=True)
        refresh_detection_time = datetime.now() - start_time
        
        # Check that force refresh calculation time is similar to first detection
        self.assertGreater(refresh_detection_time.total_seconds(), 
                          second_detection_time.total_seconds(), 
                          "Force refresh should take longer than cached result")
        

if __name__ == '__main__':
    unittest.main()
