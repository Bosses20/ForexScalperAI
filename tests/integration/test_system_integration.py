"""
Integration Tests for Forex Trading Bot

This module contains end-to-end integration tests for the trading bot system,
ensuring all components work together correctly.
"""

import os
import sys
import unittest
import logging
import time
from unittest.mock import MagicMock, patch
from datetime import datetime
import pytest
import threading
import json

# Add the parent directory to the path so we can import the src modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the necessary modules
from src.trading.executor import TradingExecutor
from src.api.local_api import app, initialize_executor, get_executor, login
from src.market.market_condition_detector import MarketConditionDetector
from src.trading.multi_asset_integrator import MultiAssetIntegrator
from src.strategies.ai_decision_module import AIDecisionModule
from src.strategies.ai_integration import AIIntegration
from src.execution.low_latency_executor import LowLatencyExecutor
from fastapi.testclient import TestClient

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('integration_tests')

class TestSystemIntegration(unittest.TestCase):
    """Test the end-to-end integration of the trading bot system."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        cls.config = {
            "mt5": {
                "account": "12345678",
                "password": "test_password",
                "server": "MetaQuotes-Demo",
                "timeout": 60000,
                "enable_trading": False,  # Disable actual trading for tests
            },
            "trading": {
                "default_risk_percent": 1.0,
                "max_trades_per_session": 5,
                "enable_trading": False,
            },
            "market_condition_detection": {
                "enabled": True,
                "volatility_lookback": 20,
                "trend_lookback": 100,
                "update_interval": 60,
            },
            "multi_asset_trading": {
                "enabled": True,
                "instruments": ["EURUSD", "GBPUSD", "USDJPY"],
                "correlation_threshold": 0.7,
                "max_correlated_trades": 2,
            },
            "ai_enhanced_trading": {
                "enabled": True,
                "confidence_threshold": 0.65,
                "update_interval_seconds": 60,
            },
            "low_latency_execution": {
                "enabled": True,
                "executor_threads": 2,
            },
            "authentication": {
                "username": "test_user",
                "password": "test_password",
                "token_expire_minutes": 60,
                "secret_key": "test_secret_key",
            }
        }
        
        # Create a temporary directory for test data
        cls.test_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data")
        os.makedirs(cls.test_data_dir, exist_ok=True)
        
        # Initialize components with mocks where needed
        with patch('src.trading.executor.MetaTrader5', MagicMock()):
            cls.executor = TradingExecutor(cls.config, data_dir=cls.test_data_dir)
            cls.market_detector = MarketConditionDetector(cls.config, data_dir=cls.test_data_dir)
            cls.multi_asset = MultiAssetIntegrator(cls.config, data_dir=cls.test_data_dir)
            cls.ai_module = AIDecisionModule(cls.config)
            cls.ai_integration = AIIntegration(cls.config, data_dir=cls.test_data_dir)
            cls.low_latency = LowLatencyExecutor(cls.config, data_dir=cls.test_data_dir)
        
        # Connect components
        cls.executor.set_market_detector(cls.market_detector)
        cls.executor.set_multi_asset_integrator(cls.multi_asset)
        cls.ai_integration.connect_modules(cls.market_detector, cls.multi_asset)
        
        # Initialize API with our executor
        with patch('src.api.local_api.get_executor', return_value=cls.executor):
            initialize_executor(cls.executor)
            cls.client = TestClient(app)
        
        logger.info("Test environment set up")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Clean up test data
        import shutil
        if os.path.exists(cls.test_data_dir):
            shutil.rmtree(cls.test_data_dir)
            
        logger.info("Test environment cleaned up")
    
    def setUp(self):
        """Set up before each test."""
        # Get an auth token for API requests
        response = self.client.post(
            "/login",
            data={"username": "test_user", "password": "test_password"}
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_001_system_startup(self):
        """Test the system startup sequence."""
        logger.info("Testing system startup sequence")
        
        # Start components
        self.executor.start()
        self.market_detector.start()
        self.multi_asset.start()
        self.ai_integration.start()
        self.low_latency.start()
        
        # Check if all components are running
        self.assertTrue(self.executor.is_running())
        
        # Check API status
        response = self.client.get("/status", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        
        status_data = response.json()
        self.assertIn("status", status_data)
        self.assertEqual(status_data["status"], "running")
        
        logger.info("System startup test passed")
    
    def test_002_market_conditions_integration(self):
        """Test integration of market conditions with other components."""
        logger.info("Testing market conditions integration")
        
        # Mock market data for testing
        test_market_conditions = {
            "EURUSD": {
                "trend": "bullish",
                "trend_strength": 0.75,
                "volatility": "medium",
                "liquidity": "high",
                "favorable_for_trading": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Patch the market detector to return our test data
        with patch.object(
            self.market_detector, 
            'analyze_market_conditions', 
            return_value=test_market_conditions["EURUSD"]
        ):
            # Test API endpoint for market conditions
            response = self.client.get(
                "/market_conditions/EURUSD", 
                headers=self.headers
            )
            self.assertEqual(response.status_code, 200)
            
            # Verify response data
            data = response.json()
            self.assertEqual(data["trend"], "bullish")
            self.assertEqual(data["trend_strength"], 0.75)
            
            # Test AI integration with market conditions
            ai_decision = self.ai_module.analyze_trading_opportunity(
                "EURUSD", 
                test_market_conditions["EURUSD"],
                {"active_instruments": ["EURUSD"]}
            )
            self.assertIn("confidence_score", ai_decision)
            self.assertIn("favorable_for_trading", ai_decision)
            
            logger.info("Market conditions integration test passed")
    
    def test_003_trade_execution_flow(self):
        """Test the full trade execution flow."""
        logger.info("Testing trade execution flow")
        
        # Mock functions to avoid actual trading
        with patch.object(self.executor, 'place_trade', return_value={"trade_id": "test123"}), \
             patch.object(self.market_detector, 'analyze_market_conditions', 
                         return_value={"trend": "bullish", "volatility": "medium", "favorable_for_trading": True}), \
             patch.object(self.multi_asset, 'validate_trade', return_value=True), \
             patch.object(self.ai_integration, 'validate_trade', 
                         return_value={"valid": True, "confidence": 0.8}), \
             patch.object(self.low_latency, 'queue_execution', 
                         return_value="exec_12345"):
            
            # 1. Place a trade through the API
            trade_request = {
                "symbol": "EURUSD",
                "trade_type": "buy",
                "volume": 0.1,
                "sl_pips": 20,
                "tp_pips": 40,
                "comment": "Integration test trade"
            }
            
            response = self.client.post(
                "/trade", 
                json=trade_request,
                headers=self.headers
            )
            
            self.assertEqual(response.status_code, 200)
            trade_data = response.json()
            self.assertIn("trade_id", trade_data)
            
            # 2. Check active trades
            response = self.client.get(
                "/active_trades",
                headers=self.headers
            )
            
            self.assertEqual(response.status_code, 200)
            
            # 3. Test trade closure
            with patch.object(self.executor, 'close_trade', return_value=True):
                response = self.client.post(
                    f"/close_trade/{trade_data['trade_id']}",
                    headers=self.headers
                )
                
                self.assertEqual(response.status_code, 200)
                close_data = response.json()
                self.assertTrue(close_data["success"])
            
            logger.info("Trade execution flow test passed")
    
    def test_004_settings_update_propagation(self):
        """Test settings updates propagate to all components."""
        logger.info("Testing settings update propagation")
        
        # Original settings
        original_risk = self.config["trading"]["default_risk_percent"]
        
        # Update settings through API
        new_settings = {
            "default_risk_percent": 0.5
        }
        
        with patch.object(self.executor, 'update_config') as mock_update:
            response = self.client.post(
                "/settings/trading",
                json=new_settings,
                headers=self.headers
            )
            
            self.assertEqual(response.status_code, 200)
            mock_update.assert_called_once()
        
        logger.info("Settings update propagation test passed")
    
    def test_005_error_handling_integration(self):
        """Test error handling across integrated components."""
        logger.info("Testing error handling integration")
        
        # Test invalid auth
        response = self.client.get(
            "/status",
            headers={"Authorization": "Bearer invalid_token"}
        )
        self.assertEqual(response.status_code, 401)
        
        # Test invalid trade parameters
        invalid_trade = {
            "symbol": "EURUSD",
            "trade_type": "buy",
            "volume": -0.1,  # Invalid negative volume
            "sl_pips": 20,
            "tp_pips": 40
        }
        
        response = self.client.post(
            "/trade",
            json=invalid_trade,
            headers=self.headers
        )
        self.assertEqual(response.status_code, 400)
        
        # Test invalid market condition request
        response = self.client.get(
            "/market_conditions/INVALID_SYMBOL",
            headers=self.headers
        )
        self.assertEqual(response.status_code, 404)
        
        logger.info("Error handling integration test passed")
    
    def test_006_ai_decision_integration(self):
        """Test AI decision system integration."""
        logger.info("Testing AI decision system integration")
        
        # Mock market data
        market_data = {
            "trend": "bullish",
            "trend_strength": 0.8,
            "volatility": "medium",
            "liquidity": "high",
            "momentum": 0.6,
            "current_session": "london_ny_overlap",
            "support_levels": [1.1050, 1.1000],
            "resistance_levels": [1.1150, 1.1200],
            "current_price": 1.1100
        }
        
        # Mock multi-asset data
        multi_asset_data = {
            "active_instruments": ["EURUSD", "GBPUSD"],
            "correlations": {
                "EURUSD": {
                    "GBPUSD": 0.65
                }
            },
            "risk_management": {
                "max_risk_per_trade": 0.01
            }
        }
        
        # Test AI decision module
        decision = self.ai_module.analyze_trading_opportunity(
            "EURUSD", market_data, multi_asset_data
        )
        
        self.assertIn("confidence_score", decision)
        self.assertIn("recommended_strategies", decision)
        
        # Ensure we have strategies if conditions are favorable
        if decision["favorable_for_trading"]:
            self.assertTrue(len(decision["recommended_strategies"]) > 0)
            
        # Test trade validation
        validation = self.ai_integration.validate_trade("EURUSD", "buy")
        self.assertIn("valid", validation)
        
        logger.info("AI decision integration test passed")
    
    def test_007_low_latency_execution_integration(self):
        """Test low latency execution integration."""
        logger.info("Testing low latency execution integration")
        
        # Queue an execution request
        execution_request = {
            "symbol": "EURUSD",
            "order_type": "market",
            "volume": 0.1,
            "direction": "buy",
            "price": 1.1100,
            "sl_price": 1.1050,
            "tp_price": 1.1150,
            "market_conditions": {
                "volatility": "medium",
                "liquidity": "high"
            }
        }
        
        # Queue execution
        execution_id = self.low_latency.queue_execution(execution_request, priority="high")
        self.assertTrue(len(execution_id) > 0)
        
        # Allow time for processing
        time.sleep(0.2)
        
        # Check execution stats
        stats = self.low_latency.get_execution_stats()
        self.assertGreaterEqual(stats["total_executions"], 1)
        
        logger.info("Low latency execution integration test passed")
    
    def test_008_system_shutdown(self):
        """Test the system shutdown sequence."""
        logger.info("Testing system shutdown sequence")
        
        # Stop components in reverse order
        self.low_latency.stop()
        self.ai_integration.stop()
        self.multi_asset.stop()
        self.market_detector.stop()
        
        # Stop executor last
        with patch('src.api.local_api.get_executor', return_value=self.executor):
            response = self.client.post(
                "/command/stop",
                headers=self.headers
            )
            self.assertEqual(response.status_code, 200)
            
            # Verify executor is stopped
            self.assertFalse(self.executor.is_running())
        
        logger.info("System shutdown test passed")


if __name__ == "__main__":
    pytest.main(["-xvs", os.path.abspath(__file__)])
