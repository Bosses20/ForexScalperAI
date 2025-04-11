"""
API Server module for forex trading bot
Provides REST API for mobile applications to interact with the trading bot
"""

from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import asyncio
import time
import datetime
from typing import Dict, List, Optional, Union, Any
from loguru import logger
import os
import json
import secrets
import pandas as pd
import threading
import platform
import psutil
import socket
import uuid
import datetime
from src.services.qr_code_service import get_qr_code_service

# Local imports
from src.bot_controller import BotController

# Models for API requests and responses
class SignalResponse(BaseModel):
    pair: str
    direction: str
    price: float
    confidence: float
    timestamp: str
    prediction: Optional[Dict] = None

class ServerInfoResponse(BaseModel):
    """Response model for server information and discovery"""
    name: str = Field(..., description="Server name")
    version: str = Field(..., description="Server version")
    host: str = Field(..., description="Host or IP address")
    port: int = Field(..., description="Port number")
    requires_auth: bool = Field(..., description="Whether the server requires authentication")
    uptime: Optional[float] = Field(None, description="Server uptime in seconds")
    bot_status: Optional[str] = Field(None, description="Current bot status")
    active_positions: Optional[int] = Field(None, description="Number of active positions")
    mt5_connected: Optional[bool] = Field(None, description="Whether MT5 is connected")
    market_conditions: Optional[Dict[str, Any]] = Field(None, description="Current market conditions")

class PositionResponse(BaseModel):
    pair: str
    direction: str
    entry_price: float
    current_price: Optional[float] = None
    position_size: float
    stop_loss: float
    take_profit: float
    pnl_pips: Optional[float] = None
    pnl_money: Optional[float] = None
    entry_time: str

class PerformanceResponse(BaseModel):
    total_trades: int
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    avg_pnl_pips: Optional[float] = None
    avg_pnl_money: Optional[float] = None
    max_drawdown: Optional[float] = None
    current_balance: Optional[float] = None
    absolute_pnl: Optional[float] = None
    percent_pnl: Optional[float] = None

class HistoricalTradeResponse(BaseModel):
    pair: str
    direction: str
    entry_price: float
    exit_price: float
    position_size: float
    pnl_pips: float
    pnl_money: float
    entry_time: str
    exit_time: str
    exit_reason: str

class BotStatusResponse(BaseModel):
    status: str
    paused: bool
    last_update: Optional[str] = None
    active_positions: int
    trade_count: int

class APIKeyAuth(BaseModel):
    api_key: str

class ClosePositionRequest(BaseModel):
    pair: str

class ModifyPositionRequest(BaseModel):
    pair: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop_enabled: Optional[bool] = None
    trailing_stop_distance: Optional[int] = None

class BotConfigRequest(BaseModel):
    risk_per_trade: Optional[float] = None
    max_daily_risk: Optional[float] = None
    max_drawdown: Optional[float] = None
    confidence_threshold: Optional[float] = None

class MarketDataRequest(BaseModel):
    pairs: List[str]
    timeframe: str = "1m"
    bars: int = 100

class APIServer:
    """
    API Server for forex trading bot
    """
    
    def __init__(self, bot_controller: BotController, config: dict):
        """
        Initialize the API server
        
        Args:
            bot_controller: Bot controller instance
            config: API configuration
        """
        self.bot = bot_controller
        self.config = config
        self.app = FastAPI(title="Forex Trading Bot API", version="1.0.0")
        
        # Set up CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=config.get('cors_origins', ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Set up API key security
        self.api_key_header = APIKeyHeader(name="X-API-Key")
        
        # Generate or load API key
        self.api_keys = []
        self._initialize_api_keys()
        
        # Register routes
        self._register_routes()
        
        logger.info("API server initialized")
    
    def _initialize_api_keys(self):
        """
        Initialize API keys
        """
        # Load existing API keys if available
        api_keys_file = self.config.get('api_keys_file', 'api_keys.json')
        
        try:
            if os.path.exists(api_keys_file):
                with open(api_keys_file, 'r') as f:
                    self.api_keys = json.load(f)
                    logger.info(f"Loaded {len(self.api_keys)} API keys")
        except Exception as e:
            logger.error(f"Error loading API keys: {str(e)}")
        
        # Generate a key if none exist
        if not self.api_keys:
            key = secrets.token_hex(16)
            self.api_keys.append(key)
            
            # Save the key
            try:
                with open(api_keys_file, 'w') as f:
                    json.dump(self.api_keys, f)
                    logger.info(f"Generated and saved new API key")
            except Exception as e:
                logger.error(f"Error saving API key: {str(e)}")
    
    async def _verify_api_key(self, api_key: str = Security(APIKeyHeader(name="X-API-Key"))):
        """
        Verify the API key
        
        Args:
            api_key: API key from request header
            
        Returns:
            True if valid
        """
        if api_key in self.api_keys:
            return True
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    
    def _register_routes(self):
        """
        Register API routes
        """
        app = self.app
        
        # Health check endpoint (no auth required)
        @app.get("/health")
        async def health_check():
            return {"status": "ok"}
        
        # Server discovery endpoint (no auth required)
        @app.get("/discover", response_model=ServerInfoResponse)
        async def discover_server():
            """
            Endpoint for local network discovery
            Returns server information for discovery by mobile app
            """
            try:
                # Get server hostname, local IP address, and uptime
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                
                # Get uptime
                uptime = time.time() - psutil.boot_time()
                
                # Get bot status if available
                bot_status = "unknown"
                active_positions = 0
                mt5_connected = False
                
                if hasattr(self, 'bot') and self.bot is not None:
                    status_info = self.bot.get_status()
                    bot_status = status_info.get('status', 'unknown')
                    active_positions = status_info.get('active_positions', 0)
                    mt5_connected = self.bot.market_data.is_connected()
                
                # Get current market conditions if available
                market_conditions = None
                if hasattr(self, 'bot') and self.bot is not None and hasattr(self.bot, 'market_condition_detector'):
                    market_conditions = self.bot.market_condition_detector.get_current_conditions()
                
                # Build server information response
                server_info = ServerInfoResponse(
                    name=f"Trading Bot on {hostname}",
                    version="1.0.0",  # Update with actual version
                    host=local_ip,
                    port=self.config.get('port', 8000),
                    requires_auth=len(self.api_keys) > 0,
                    uptime=uptime,
                    bot_status=bot_status,
                    active_positions=active_positions,
                    mt5_connected=mt5_connected,
                    market_conditions=market_conditions
                )
                
                return server_info
                
            except Exception as e:
                logger.error(f"Error in discover endpoint: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Server discovery error: {str(e)}"
                )
        
        # QR code endpoint for one-tap trading connections (no auth required)
        @app.get("/qrcode")
        async def get_connection_qrcode():
            """
            Generate a QR code for connecting to this trading bot server
            Returns a base64 encoded image in PNG format
            """
            try:
                # Get server hostname, local IP address
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                
                # Get QR code service
                qr_service = get_qr_code_service()
                
                # Get bot status if available
                bot_status = "unknown"
                market_conditions = None
                mt5_connected = False
                
                if hasattr(self, 'bot') and self.bot is not None:
                    status_info = self.bot.get_status()
                    bot_status = status_info.get('status', 'unknown')
                    mt5_connected = self.bot.market_data.is_connected()
                    
                    # Get market conditions if available
                    if hasattr(self.bot, 'market_condition_detector'):
                        market_conditions = self.bot.market_condition_detector.get_current_conditions()
                
                # Additional data to include in QR code
                extra_data = {
                    "status": bot_status,
                    "mt5_connected": str(mt5_connected).lower(),
                }
                
                # Include market conditions summary if available
                if market_conditions:
                    market_summary = {
                        "trend": market_conditions.get("trend", "unknown"),
                        "volatility": market_conditions.get("volatility", "unknown"),
                        "favorable": str(market_conditions.get("favorable_for_trading", False)).lower()
                    }
                    extra_data["market"] = json.dumps(market_summary)
                
                # Generate QR code
                qr_code_base64 = qr_service.generate_connection_qr_base64(
                    host=local_ip,
                    port=self.config.get('port', 8000),
                    name=f"Trading Bot on {hostname}",
                    requires_auth=len(self.api_keys) > 0,
                    version="1.0.0",  # Update with actual version
                    extra_data=extra_data
                )
                
                return {
                    "qr_code": qr_code_base64,
                    "server_name": f"Trading Bot on {hostname}",
                    "host": local_ip,
                    "port": self.config.get('port', 8000),
                    "requires_auth": len(self.api_keys) > 0
                }
                
            except Exception as e:
                logger.error(f"Error generating QR code: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"QR code generation error: {str(e)}"
                )
        
        # Status endpoint
        @app.get("/status", response_model=BotStatusResponse)
        async def get_status(authorized: bool = Depends(self._verify_api_key)):
            status = self.bot.get_status()
            return status
        
        # Performance endpoint
        @app.get("/performance", response_model=PerformanceResponse)
        async def get_performance(authorized: bool = Depends(self._verify_api_key)):
            return self.bot.get_performance_metrics()
        
        # Active positions endpoint
        @app.get("/positions", response_model=List[PositionResponse])
        async def get_positions(authorized: bool = Depends(self._verify_api_key)):
            positions = self.bot.execution_engine.get_active_positions()
            return [PositionResponse(
                pair=k,
                direction=v['direction'],
                entry_price=v['entry_price'],
                current_price=v.get('current_price'),
                position_size=v['position_size'],
                stop_loss=v['stop_loss'],
                take_profit=v['take_profit'],
                pnl_pips=v.get('current_pnl_pips'),
                pnl_money=v.get('current_pnl_money'),
                entry_time=v['entry_time'].isoformat() if isinstance(v['entry_time'], datetime.datetime) else v['entry_time']
            ) for k, v in positions.items()]
        
        # Recent signals endpoint
        @app.get("/signals", response_model=List[SignalResponse])
        async def get_signals(authorized: bool = Depends(self._verify_api_key)):
            signals = self.bot.recent_signals
            return [SignalResponse(
                pair=s['pair'],
                direction=s['direction'],
                price=s['price'],
                confidence=s.get('confidence', 0),
                timestamp=s.get('timestamp', datetime.datetime.now().isoformat()),
                prediction=s.get('prediction')
            ) for s in signals]
        
        # Trade history endpoint
        @app.get("/trades", response_model=List[HistoricalTradeResponse])
        async def get_trade_history(authorized: bool = Depends(self._verify_api_key)):
            trades = self.bot.risk_manager.trade_history
            return [HistoricalTradeResponse(
                pair=t['pair'],
                direction=t['direction'],
                entry_price=t['entry_price'],
                exit_price=t['exit_price'],
                position_size=t['position_size'],
                pnl_pips=t['pnl_pips'],
                pnl_money=t['pnl_money'],
                entry_time=t['entry_time'].isoformat() if isinstance(t['entry_time'], datetime.datetime) else t['entry_time'],
                exit_time=t['exit_time'].isoformat() if isinstance(t['exit_time'], datetime.datetime) else t['exit_time'],
                exit_reason=t['exit_reason']
            ) for t in trades]
        
        # Balance history endpoint
        @app.get("/balance-history")
        async def get_balance_history(authorized: bool = Depends(self._verify_api_key)):
            return self.bot.get_account_balance_history()
        
        # Close position endpoint
        @app.post("/close-position")
        async def close_position(request: ClosePositionRequest, authorized: bool = Depends(self._verify_api_key)):
            try:
                result = await self.bot.execution_engine.close_position(request.pair, 'manual_api')
                return result
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Modify position endpoint
        @app.post("/modify-position")
        async def modify_position(request: ModifyPositionRequest, authorized: bool = Depends(self._verify_api_key)):
            try:
                positions = self.bot.execution_engine.get_active_positions()
                if request.pair not in positions:
                    raise HTTPException(status_code=404, detail=f"No active position for {request.pair}")
                
                position = positions[request.pair]
                
                # Update position parameters
                if request.stop_loss is not None:
                    position['stop_loss'] = request.stop_loss
                
                if request.take_profit is not None:
                    position['take_profit'] = request.take_profit
                
                if request.trailing_stop_enabled is not None:
                    position['trailing_stop_enabled'] = request.trailing_stop_enabled
                
                if request.trailing_stop_distance is not None:
                    position['trailing_stop_distance'] = request.trailing_stop_distance
                
                return {"status": "success", "message": f"Position for {request.pair} updated"}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Start bot endpoint
        @app.post("/start")
        async def start_bot(authorized: bool = Depends(self._verify_api_key)):
            if not self.bot.running:
                success = self.bot.start()
                if success:
                    return {"status": "success", "message": "Bot started"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to start bot")
            else:
                return {"status": "success", "message": "Bot already running"}
        
        # Stop bot endpoint
        @app.post("/stop")
        async def stop_bot(authorized: bool = Depends(self._verify_api_key)):
            if self.bot.running:
                await self.bot.shutdown()
                return {"status": "success", "message": "Bot stopped"}
            else:
                return {"status": "success", "message": "Bot already stopped"}
        
        # Pause bot endpoint
        @app.post("/pause")
        async def pause_bot(authorized: bool = Depends(self._verify_api_key)):
            if not self.bot.paused:
                self.bot.pause()
                return {"status": "success", "message": "Bot paused"}
            else:
                return {"status": "success", "message": "Bot already paused"}
        
        # Resume bot endpoint
        @app.post("/resume")
        async def resume_bot(authorized: bool = Depends(self._verify_api_key)):
            if self.bot.paused:
                self.bot.resume()
                return {"status": "success", "message": "Bot resumed"}
            else:
                return {"status": "success", "message": "Bot already running"}
        
        # Update bot configuration endpoint
        @app.post("/update-config")
        async def update_config(request: BotConfigRequest, authorized: bool = Depends(self._verify_api_key)):
            try:
                # Update risk parameters
                if request.risk_per_trade is not None:
                    self.bot.risk_manager.max_risk_per_trade = request.risk_per_trade
                
                if request.max_daily_risk is not None:
                    self.bot.risk_manager.max_daily_risk = request.max_daily_risk
                
                if request.max_drawdown is not None:
                    self.bot.risk_manager.max_drawdown_percent = request.max_drawdown
                
                # Update strategy parameters
                if request.confidence_threshold is not None:
                    self.bot.config['strategy']['confidence_threshold'] = request.confidence_threshold
                
                return {"status": "success", "message": "Configuration updated"}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Get market data endpoint
        @app.post("/market-data")
        async def get_market_data(request: MarketDataRequest, authorized: bool = Depends(self._verify_api_key)):
            try:
                market_data = await self.bot.market_data.get_market_data(request.pairs, [request.timeframe])
                
                # Convert to dictionary of lists for JSON serialization
                result = {}
                for pair, df in market_data.items():
                    if isinstance(df, pd.DataFrame):
                        # Limit to requested number of bars
                        df = df.tail(request.bars)
                        
                        # Convert to dictionary
                        result[pair] = {
                            'timestamp': df.index.astype(str).tolist(),
                            'open': df['open'].tolist(),
                            'high': df['high'].tolist(),
                            'low': df['low'].tolist(),
                            'close': df['close'].tolist(),
                            'volume': df['volume'].tolist() if 'volume' in df.columns else []
                        }
                
                return result
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Get bot configuration endpoint
        @app.get("/config")
        async def get_config(authorized: bool = Depends(self._verify_api_key)):
            # Return safe config (omit sensitive info like API keys)
            safe_config = {
                'risk_management': {
                    'max_risk_per_trade': self.bot.risk_manager.max_risk_per_trade,
                    'max_daily_risk': self.bot.risk_manager.max_daily_risk,
                    'max_drawdown_percent': self.bot.risk_manager.max_drawdown_percent
                },
                'strategy': {
                    'confidence_threshold': self.bot.config.get('strategy', {}).get('confidence_threshold', 0.7)
                },
                'trading': {
                    'pairs': self.bot.config.get('trading', {}).get('pairs', []),
                    'interval_seconds': self.bot.config.get('trading', {}).get('interval_seconds', 60)
                }
            }
            
            return safe_config
        
        # Get API key endpoint (for admin use only)
        @app.get("/api-key")
        async def get_api_key(authorized: bool = Depends(self._verify_api_key)):
            # This should only be used for initial setup or admin purposes
            return {"api_key": self.api_keys[0]}
    
    def start(self, host: str = "0.0.0.0", port: int = 8000):
        """
        Start the API server
        
        Args:
            host: Host to bind to
            port: Port to bind to
        """
        # Get configuration
        host = self.config.get('host', host)
        port = self.config.get('port', port)
        
        # Start in a separate thread
        def run_server():
            uvicorn.run(self.app, host=host, port=port)
        
        thread = threading.Thread(target=run_server)
        thread.daemon = True
        thread.start()
        
        logger.info(f"API server started at http://{host}:{port}")
        return thread
    
    def start_blocking(self, host: str = "0.0.0.0", port: int = 8000):
        """
        Start the API server (blocking)
        
        Args:
            host: Host to bind to
            port: Port to bind to
        """
        # Get configuration
        host = self.config.get('host', host)
        port = self.config.get('port', port)
        
        logger.info(f"Starting API server at http://{host}:{port} (blocking)")
        uvicorn.run(self.app, host=host, port=port)
