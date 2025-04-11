"""
Test module for the local API endpoints.
"""
import sys
import os
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# Add the src directory to the path so we can import the API module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.api.local_api import app
from src.api.error_handling import create_api_exception

# Create a test client
client = TestClient(app)

# Mock credentials for testing
TEST_USERNAME = "test_user"
TEST_PASSWORD = "test_password"
TEST_TOKEN = "test_token"

# Mock executor for testing
class MockExecutor:
    def __init__(self):
        self.running = True
        self.paused = False
        self.status = {
            "status": "running",
            "uptime": "00:30:45",
            "trades_today": 5,
            "profit_today": 120.50
        }
        
    def get_status(self):
        return self.status
        
    def start(self):
        self.running = True
        return {"success": True, "message": "Bot started"}
        
    def stop(self):
        self.running = False
        return {"success": True, "message": "Bot stopped"}
        
    def pause(self):
        self.paused = True
        return {"success": True, "message": "Bot paused"}
        
    def resume(self):
        self.paused = False
        return {"success": True, "message": "Bot resumed"}
        
    def restart(self):
        return {"success": True, "message": "Bot restarted"}
        
    def place_trade(self, params):
        return {
            "success": True,
            "trade_id": 12345,
            "details": {
                "symbol": params["symbol"],
                "order_type": params["order_type"],
                "volume": params["volume"],
                "price": 1.23456,
                "time": "2025-04-11 17:00:00"
            }
        }
        
    def get_market_conditions(self):
        return {
            "trend": "bullish",
            "volatility": "medium",
            "liquidity": "high",
            "confidence": 0.85,
            "favorable_for_trading": True
        }
        
    def get_active_instruments(self):
        return [
            {
                "symbol": "EURUSD",
                "trend": "bullish",
                "volatility": "medium",
                "is_active": True
            },
            {
                "symbol": "GBPUSD",
                "trend": "bearish",
                "volatility": "high",
                "is_active": True
            }
        ]
        
    def get_instrument_analysis(self, symbol):
        if symbol == "INVALID":
            return None
        return {
            "symbol": symbol,
            "trend": "bullish",
            "volatility": "medium",
            "support_levels": [1.21, 1.20],
            "resistance_levels": [1.25, 1.26]
        }
        
    def get_active_trades(self):
        return [
            {
                "trade_id": 12345,
                "symbol": "EURUSD",
                "order_type": "BUY",
                "volume": 0.01,
                "open_price": 1.23456,
                "current_price": 1.23556,
                "profit": 10.0,
                "open_time": "2025-04-11 15:30:00"
            }
        ]
        
    def close_trade(self, trade_id):
        if trade_id == 9999:
            return {"success": False, "message": "Trade not found"}
        return {
            "success": True,
            "details": {
                "trade_id": trade_id,
                "profit": 10.0,
                "close_price": 1.23556,
                "close_time": "2025-04-11 17:05:00"
            }
        }

# Setup and teardown for tests
@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Setup before each test and teardown after"""
    # Setup - patch the executor and auth_config
    with patch('src.api.local_api.executor', MockExecutor()):
        with patch('src.api.local_api.auth_config', {"username": TEST_USERNAME, "password": TEST_PASSWORD}):
            with patch('src.api.local_api.create_access_token', return_value=TEST_TOKEN):
                with patch('src.api.local_api.decode_access_token', return_value={"sub": TEST_USERNAME}):
                    yield

# Authentication tests
def test_login_success():
    """Test successful login"""
    response = client.post(
        "/token",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["access_token"] == TEST_TOKEN

def test_login_failure():
    """Test failed login"""
    response = client.post(
        "/token",
        data={"username": "wrong_user", "password": "wrong_pass"}
    )
    assert response.status_code == 401
    assert "detail" in response.json()
    assert "Invalid" in response.json()["detail"]["message"]

# Status endpoint tests
def test_get_status_authenticated():
    """Test getting status with authentication"""
    response = client.get(
        "/status",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "running"

def test_get_status_unauthenticated():
    """Test getting status without authentication"""
    response = client.get("/status")
    assert response.status_code == 401

# Command execution tests
def test_execute_start_command():
    """Test executing start command"""
    response = client.post(
        "/command",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={"command": "start"}
    )
    assert response.status_code == 200
    assert response.json()["success"] == True
    assert "Bot started" in response.json()["message"]

def test_execute_stop_command():
    """Test executing stop command"""
    response = client.post(
        "/command",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={"command": "stop"}
    )
    assert response.status_code == 200
    assert response.json()["success"] == True
    assert "Bot stopped" in response.json()["message"]

def test_execute_invalid_command():
    """Test executing invalid command"""
    response = client.post(
        "/command",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={"command": "invalid_command"}
    )
    assert response.status_code != 200
    assert "error" in response.json()

# Trade placement tests
def test_place_trade_success():
    """Test successful trade placement"""
    response = client.post(
        "/trade",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={
            "symbol": "EURUSD",
            "order_type": "BUY",
            "volume": 0.01,
            "stop_loss": 1.2200,
            "take_profit": 1.2500,
            "comment": "Test trade"
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "trade_id" in response.json()

def test_place_trade_invalid_volume():
    """Test trade placement with invalid volume"""
    response = client.post(
        "/trade",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={
            "symbol": "EURUSD",
            "order_type": "BUY",
            "volume": 0,  # Invalid volume
            "stop_loss": 1.2200,
            "take_profit": 1.2500
        }
    )
    assert response.status_code != 200
    assert "error" in response.json()
    assert "volume" in response.json()["detail"]["message"]

def test_place_trade_invalid_order_type():
    """Test trade placement with invalid order type"""
    response = client.post(
        "/trade",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={
            "symbol": "EURUSD",
            "order_type": "INVALID",  # Invalid order type
            "volume": 0.01,
            "stop_loss": 1.2200,
            "take_profit": 1.2500
        }
    )
    assert response.status_code != 200
    assert "error" in response.json()
    assert "order_type" in response.json()["detail"]["message"]

# Settings update tests
@patch('src.api.local_api.load_config')
@patch('src.api.local_api.open')
@patch('yaml.dump')
def test_update_settings_success(mock_yaml_dump, mock_open, mock_load_config):
    """Test successful settings update"""
    mock_load_config.return_value = {
        "risk_management": {
            "risk_per_trade": 1.0,
            "max_trades": 5
        }
    }
    
    response = client.put(
        "/settings",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={
            "section": "risk_management",
            "settings": {
                "risk_per_trade": 2.0
            }
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "risk_management" in response.json()["message"]

@patch('src.api.local_api.load_config')
def test_update_invalid_section(mock_load_config):
    """Test updating invalid settings section"""
    mock_load_config.return_value = {
        "risk_management": {
            "risk_per_trade": 1.0
        }
    }
    
    response = client.put(
        "/settings",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={
            "section": "invalid_section",
            "settings": {
                "some_setting": "value"
            }
        }
    )
    assert response.status_code != 200
    assert "error" in response.json()
    assert "Unknown settings section" in response.json()["detail"]["message"]

@patch('src.api.local_api.load_config')
def test_update_invalid_setting(mock_load_config):
    """Test updating invalid setting in valid section"""
    mock_load_config.return_value = {
        "risk_management": {
            "risk_per_trade": 1.0
        }
    }
    
    response = client.put(
        "/settings",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={
            "section": "risk_management",
            "settings": {
                "invalid_setting": "value"
            }
        }
    )
    assert response.status_code != 200
    assert "error" in response.json()
    assert "Unknown setting" in response.json()["detail"]["message"]

# Market conditions tests
def test_get_market_conditions():
    """Test getting market conditions"""
    response = client.get(
        "/market_conditions",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code == 200
    assert "market_conditions" in response.json()
    assert "trend" in response.json()["market_conditions"]
    assert "volatility" in response.json()["market_conditions"]

# Active instruments tests
def test_get_active_instruments():
    """Test getting active instruments"""
    response = client.get(
        "/active_instruments",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code == 200
    assert "active_instruments" in response.json()
    assert len(response.json()["active_instruments"]) > 0
    assert "symbol" in response.json()["active_instruments"][0]

# Instrument analysis tests
def test_get_instrument_analysis_valid():
    """Test getting valid instrument analysis"""
    response = client.get(
        "/instruments/EURUSD/analysis",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code == 200
    assert "analysis" in response.json()
    assert response.json()["symbol"] == "EURUSD"
    assert "trend" in response.json()["analysis"]

def test_get_instrument_analysis_invalid():
    """Test getting invalid instrument analysis"""
    response = client.get(
        "/instruments/INVALID/analysis",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code != 200
    assert "error" in response.json()
    assert "No analysis available" in response.json()["detail"]["message"]

# Active trades tests
def test_get_active_trades():
    """Test getting active trades"""
    response = client.get(
        "/active_trades",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code == 200
    assert "trades" in response.json()
    assert len(response.json()["trades"]) > 0
    assert "trade_id" in response.json()["trades"][0]

# Close trade tests
def test_close_trade_success():
    """Test successful trade closure"""
    response = client.delete(
        "/trades/12345",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "closed successfully" in response.json()["message"]

def test_close_trade_failure():
    """Test failed trade closure"""
    response = client.delete(
        "/trades/9999",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code != 200
    assert "error" in response.json()
    assert "Trade not found" in response.json()["detail"]["message"]
