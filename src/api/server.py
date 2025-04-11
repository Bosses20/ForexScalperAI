"""
API Server for Forex Trading Bot

This module provides a REST API and WebSocket server that allows the mobile app
to connect to and control the trading bot running on a VPS or server.

Designed to be the bridge between the Flutter mobile app and the MT5 trading system.
"""

import asyncio
import uvicorn
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import os
import sys
import yaml
import jwt
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import socket
import atexit

# Add project root to path to allow imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.bot_controller import BotController
from src.services.network_discovery_service import NetworkDiscoveryService
from src.api.upnp_helper import setup_port_forwarding, cleanup_port_forwarding

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "logs" / "api_server.log"),
    ],
)
logger = logging.getLogger("api_server")

# Create FastAPI app
app = FastAPI(
    title="Forex Trading Bot API",
    description="API for controlling the Forex Trading Bot from mobile devices",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security settings
SECRET_KEY = "REPLACE_WITH_SECURE_SECRET_KEY"  # In production, load from env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 settings
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# In-memory user database - in production, use a proper database
USERS_DB = {
    "admin": {
        "username": "admin",
        "password": "REPLACE_WITH_HASHED_PASSWORD",  # In production, use hashed passwords
        "disabled": False,
    }
}

# Pydantic Models
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    disabled: Optional[bool] = None


class UserInDB(User):
    password: str


class BotStatus(BaseModel):
    is_running: bool
    active_symbols: List[str]
    active_trades: int
    account_balance: float
    account_equity: float
    daily_profit_loss: float
    last_update: str


class TradeData(BaseModel):
    id: int
    symbol: str
    type: str  # "buy" or "sell"
    open_time: str
    volume: float
    open_price: float
    current_price: float
    take_profit: float
    stop_loss: float
    profit: float
    pips: float


class AccountInfo(BaseModel):
    login: int
    server: str
    balance: float
    equity: float
    margin: float
    margin_level: float
    free_margin: float
    currency: str


class StartBotRequest(BaseModel):
    symbols: List[str] = []
    risk_level: str = "medium"  # low, medium, high
    strategies: List[str] = []


class BotConfig(BaseModel):
    risk_per_trade: float
    max_daily_risk: float
    allowed_symbols: List[str]
    active_strategies: List[str]
    trading_hours: Dict[str, Dict[str, str]]


# Bot controller instance
bot_controller = None
config_path = PROJECT_ROOT / "config" / "mt5_config.yaml"
network_discovery_service = None  # Will be initialized in startup event

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def broadcast_json(self, data: dict):
        json_data = json.dumps(data)
        await self.broadcast(json_data)


manager = ConnectionManager()


# Security functions
def verify_password(plain_password, hashed_password):
    # In production, use passlib or similar for secure password hashing
    return plain_password == hashed_password  # INSECURE - for demo only!


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception
    user = get_user(USERS_DB, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Initialize bot controller
@app.on_event("startup")
async def startup_event():
    """
    Initialize the bot controller on startup
    """
    global bot_controller, network_discovery_service, config_path
    
    try:
        # Load configuration
        if os.environ.get("MT5_CONFIG_PATH"):
            config_path = Path(os.environ.get("MT5_CONFIG_PATH"))
        
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return
        
        logger.info(f"Loading configuration from {config_path}")
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
        
        # Initialize bot controller
        bot_controller = BotController(config)
        
        # Setup UPnP port forwarding for improved network connectivity
        try:
            api_port = config.get("api", {}).get("port", 8000)
            ws_port = config.get("api", {}).get("ws_port", api_port)
            
            # Initialize UPnP port forwarding
            upnp_enabled = config.get("api", {}).get("enable_upnp", True)
            if upnp_enabled:
                logger.info(f"Setting up UPnP port forwarding for ports {api_port} and {ws_port}")
                upnp_success = setup_port_forwarding(api_port, ws_port)
                if upnp_success:
                    logger.info("UPnP port forwarding set up successfully")
                    # Register cleanup on exit
                    atexit.register(cleanup_port_forwarding)
                else:
                    logger.warning("UPnP port forwarding not available")
        except Exception as e:
            logger.error(f"Error setting up UPnP: {str(e)}")
        
        # Initialize network discovery service
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            # Get market condition data for discovery service
            market_conditions = None
            if hasattr(bot_controller, 'market_condition_detector'):
                market_conditions = bot_controller.market_condition_detector.get_current_conditions()
            
            # Initialize network discovery service
            network_discovery_service = NetworkDiscoveryService(
                service_name="Forex Trading Bot",
                service_type="_forexbot._tcp",
                port=config.get("api", {}).get("port", 8000),
                host=local_ip,
                properties={
                    "version": "1.0.0",
                    "requires_auth": "true",
                    "market_conditions": json.dumps(market_conditions) if market_conditions else "{}",
                    "multi_asset": "true"
                }
            )
            
            # Start advertising service on the network
            network_discovery_service.start()
            logger.info(f"Network discovery service started on {local_ip}:{config.get('api', {}).get('port', 8000)}")
        except Exception as e:
            logger.error(f"Error starting network discovery service: {str(e)}")
            network_discovery_service = None
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """
    Shutdown the bot controller gracefully
    """
    global bot_controller, network_discovery_service
    
    try:
        # Stop the network discovery service
        if network_discovery_service:
            try:
                network_discovery_service.stop()
                logger.info("Network discovery service stopped")
            except Exception as e:
                logger.error(f"Error stopping network discovery service: {str(e)}")
        
        # Shutdown the bot controller
        if bot_controller:
            try:
                await bot_controller.shutdown()
                logger.info("Bot controller shutdown successfully")
            except Exception as e:
                logger.error(f"Error during bot controller shutdown: {str(e)}")
        
        # Cleanup port forwarding
        try:
            cleanup_port_forwarding()
            logger.info("UPnP port forwarding cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up UPnP port forwarding: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

# Authentication routes
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user and provide access token
    """
    user = authenticate_user(USERS_DB, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


# Bot control routes
@app.get("/status", response_model=BotStatus)
async def get_bot_status(current_user: User = Depends(get_current_active_user)):
    """
    Get the current status of the trading bot
    """
    global bot_controller
    
    if bot_controller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot controller not initialized",
        )
    
    try:
        # Get status from bot controller
        bot_status = bot_controller.get_status()
        
        # Format the response
        account = bot_status.get('account', {})
        
        return {
            "is_running": bot_controller.is_running(),
            "active_symbols": bot_status.get('multi_asset', {}).get('active_instruments', []),
            "active_trades": len(bot_status.get('positions', [])),
            "account_balance": account.get('balance', 0),
            "account_equity": account.get('equity', 0),
            "daily_profit_loss": bot_status.get('risk_stats', {}).get('daily_pnl', 0),
            "last_update": bot_status.get('last_update', datetime.now().isoformat())
        }
        
    except Exception as e:
        logger.error(f"Error getting bot status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bot status: {str(e)}",
        )


@app.post("/start")
async def start_bot(
    request: StartBotRequest, current_user: User = Depends(get_current_active_user)
):
    """
    Start the trading bot with specified parameters
    """
    global bot_controller
    
    if bot_controller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot controller not initialized",
        )
    
    try:
        # Check if already running
        if bot_controller.is_running():
            return {"status": "success", "message": "Bot is already running"}
        
        # Set active symbols if provided
        if request.symbols:
            bot_controller.set_active_symbols(request.symbols)
        
        # Set active strategies if provided
        if request.strategies:
            bot_controller.set_active_strategies(request.strategies)
        
        # Set risk level
        risk_levels = {
            "low": 0.01,    # 1%
            "medium": 0.02, # 2%
            "high": 0.05    # 5%
        }
        risk_value = risk_levels.get(request.risk_level.lower(), 0.02)
        bot_controller.set_risk_level(risk_value)
        
        # Start the bot
        success = bot_controller.start()
        
        if success:
            # Notify all connected websockets
            await manager.broadcast_json({
                "event": "bot_started",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "symbols": request.symbols,
                    "risk_level": request.risk_level,
                    "strategies": request.strategies
                }
            })
            
            return {
                "status": "success",
                "message": "Bot started successfully",
                "config": {
                    "symbols": request.symbols,
                    "risk_level": request.risk_level,
                    "strategies": request.strategies
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start bot"
            )
        
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start bot: {str(e)}",
        )


@app.post("/stop")
async def stop_bot(current_user: User = Depends(get_current_active_user)):
    """
    Stop the trading bot
    """
    global bot_controller
    
    if bot_controller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot controller not initialized",
        )
    
    try:
        # Check if already stopped
        if not bot_controller.is_running():
            return {"status": "success", "message": "Bot is already stopped"}
        
        # Stop the bot
        success = bot_controller.stop()
        
        if success:
            # Notify all connected websockets
            await manager.broadcast_json({
                "event": "bot_stopped",
                "timestamp": datetime.now().isoformat()
            })
            
            return {"status": "success", "message": "Bot stopped successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop bot"
            )
        
    except Exception as e:
        logger.error(f"Error stopping bot: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop bot: {str(e)}",
        )


@app.get("/trades")
async def get_active_trades(current_user: User = Depends(get_current_active_user)):
    """
    Get all active trades
    """
    global bot_controller
    
    if bot_controller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot controller not initialized",
        )
    
    try:
        # Get bot status to access positions
        status = bot_controller.get_status()
        positions = status.get('positions', [])
        
        # Format trades for response
        trades = []
        for position in positions:
            trade = {
                "id": position.get('ticket', 0),
                "symbol": position.get('symbol', 'unknown'),
                "type": position.get('type', 'unknown').lower(),
                "open_time": position.get('time', datetime.now().isoformat()),
                "volume": position.get('volume', 0.0),
                "open_price": position.get('open_price', 0.0),
                "current_price": position.get('current_price', 0.0),
                "take_profit": position.get('tp', 0.0),
                "stop_loss": position.get('sl', 0.0),
                "profit": position.get('profit', 0.0),
                "pips": position.get('pips', 0.0)
            }
            trades.append(trade)
        
        return {
            "status": "success",
            "count": len(trades),
            "trades": trades
        }
        
    except Exception as e:
        logger.error(f"Error getting active trades: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active trades: {str(e)}",
        )


@app.get("/account")
async def get_account_info(current_user: User = Depends(get_current_active_user)):
    """
    Get account information
    """
    global bot_controller
    
    if bot_controller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot controller not initialized",
        )
    
    try:
        # Get bot status to access account info
        status = bot_controller.get_status()
        account = status.get('account', {})
        
        # Format account info for response
        account_info = {
            "login": account.get('login', 0),
            "server": account.get('server', 'unknown'),
            "balance": account.get('balance', 0.0),
            "equity": account.get('equity', 0.0),
            "margin": account.get('margin', 0.0),
            "margin_level": account.get('margin_level', 0.0),
            "free_margin": account.get('free_margin', 0.0),
            "currency": account.get('currency', 'USD')
        }
        
        # Add performance metrics
        metrics = status.get('performance_metrics', {})
        account_info.update({
            "daily_profit": metrics.get('daily_profit', 0.0),
            "weekly_profit": metrics.get('weekly_profit', 0.0),
            "monthly_profit": metrics.get('monthly_profit', 0.0),
            "win_rate": metrics.get('win_rate', 0.0)
        })
        
        return {
            "status": "success",
            "account": account_info
        }
        
    except Exception as e:
        logger.error(f"Error getting account info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get account info: {str(e)}",
        )


@app.get("/config")
async def get_bot_config(current_user: User = Depends(get_current_active_user)):
    """
    Get the current bot configuration
    """
    global bot_controller
    
    if bot_controller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot controller not initialized",
        )
    
    try:
        # Get configuration from bot controller
        config = bot_controller.get_config()
        
        # Format the response
        risk_config = config.get('risk_management', {})
        trading_config = config.get('trading', {})
        strategy_config = config.get('strategies', {})
        session_config = config.get('sessions', {})
        
        response = {
            "risk_per_trade": risk_config.get('max_risk_per_trade', 0.02),
            "max_daily_risk": risk_config.get('max_daily_risk', 0.05),
            "allowed_symbols": trading_config.get('instruments', []),
            "active_strategies": strategy_config.get('active', []),
            "trading_hours": session_config.get('trading_hours', {})
        }
        
        return {
            "status": "success",
            "config": response
        }
        
    except Exception as e:
        logger.error(f"Error getting bot config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bot config: {str(e)}",
        )


@app.post("/config")
async def update_bot_config(
    config: BotConfig, current_user: User = Depends(get_current_active_user)
):
    """
    Update the bot configuration
    """
    global bot_controller
    
    if bot_controller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot controller not initialized",
        )
    
    try:
        # Build configuration updates
        updates = {
            "risk_management": {
                "max_risk_per_trade": config.risk_per_trade,
                "max_daily_risk": config.max_daily_risk
            },
            "trading": {
                "instruments": config.allowed_symbols
            },
            "strategies": {
                "active": config.active_strategies
            },
            "sessions": {
                "trading_hours": config.trading_hours
            }
        }
        
        # Update configuration
        success = bot_controller.update_config(updates)
        
        if success:
            # Notify all connected websockets
            await manager.broadcast_json({
                "event": "config_updated",
                "timestamp": datetime.now().isoformat(),
                "data": updates
            })
            
            return {
                "status": "success",
                "message": "Configuration updated successfully",
                "config": updates
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update configuration"
            )
        
    except Exception as e:
        logger.error(f"Error updating config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update config: {str(e)}",
        )


@app.post("/trades/{trade_id}/close")
async def close_trade(
    trade_id: int, current_user: User = Depends(get_current_active_user)
):
    """
    Close a specific trade
    """
    global bot_controller
    
    if bot_controller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot controller not initialized",
        )
    
    try:
        # Close the trade
        success = bot_controller.close_trade(trade_id)
        
        if success:
            # Notify all connected websockets
            await manager.broadcast_json({
                "event": "trade_closed",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "trade_id": trade_id
                }
            })
            
            return {
                "status": "success",
                "message": f"Trade {trade_id} closed successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed to close trade {trade_id}, trade not found or already closed"
            )
        
    except Exception as e:
        logger.error(f"Error closing trade {trade_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close trade {trade_id}: {str(e)}",
        )


@app.post("/trades/{trade_id}/modify")
async def modify_trade(
    trade_id: int,
    sl: Optional[float] = None,
    tp: Optional[float] = None,
    current_user: User = Depends(get_current_active_user),
):
    """
    Modify a specific trade's stop loss and/or take profit
    """
    global bot_controller
    
    if bot_controller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot controller not initialized",
        )
    
    try:
        # Modify the trade
        success = bot_controller.modify_trade(trade_id, sl=sl, tp=tp)
        
        if success:
            # Notify all connected websockets
            await manager.broadcast_json({
                "event": "trade_modified",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "trade_id": trade_id,
                    "stop_loss": sl,
                    "take_profit": tp
                }
            })
            
            return {
                "status": "success",
                "message": f"Trade {trade_id} modified successfully",
                "data": {
                    "trade_id": trade_id,
                    "stop_loss": sl,
                    "take_profit": tp
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed to modify trade {trade_id}, trade not found"
            )
        
    except Exception as e:
        logger.error(f"Error modifying trade {trade_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to modify trade {trade_id}: {str(e)}",
        )


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({"status": "connected"})
        
        while True:
            # Just keep connection alive and wait for server-side broadcasts
            data = await websocket.receive_text()
            # Echo back any received messages (optional)
            await websocket.send_text(f"Echo: {data}")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Monitoring websocket - continuously sends status updates
@app.websocket("/ws/monitor")
async def monitor_websocket(websocket: WebSocket):
    """
    WebSocket endpoint that continuously sends bot status updates
    """
    global bot_controller
    
    await manager.connect(websocket)
    
    try:
        # Send initial status
        if bot_controller:
            status = bot_controller.get_status()
            await websocket.send_json({
                "event": "status_update",
                "timestamp": datetime.now().isoformat(),
                "data": status
            })
        
        # Send updates at regular intervals
        interval = 5  # seconds
        
        while True:
            await asyncio.sleep(interval)
            
            if bot_controller:
                # Get fresh status
                status = bot_controller.get_status()
                
                # Get active trades
                positions = status.get('positions', [])
                trades = []
                for position in positions:
                    trade = {
                        "id": position.get('ticket', 0),
                        "symbol": position.get('symbol', 'unknown'),
                        "type": position.get('type', 'unknown').lower(),
                        "profit": position.get('profit', 0.0),
                        "pips": position.get('pips', 0.0)
                    }
                    trades.append(trade)
                
                # Get account info
                account = status.get('account', {})
                
                # Build update message
                update = {
                    "is_running": bot_controller.is_running(),
                    "account": {
                        "balance": account.get('balance', 0.0),
                        "equity": account.get('equity', 0.0)
                    },
                    "trades": trades,
                    "signals": status.get('recent_signals', [])[:5]
                }
                
                # Send update
                await websocket.send_json({
                    "event": "status_update",
                    "timestamp": datetime.now().isoformat(),
                    "data": update
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in monitor websocket: {str(e)}")
        try:
            manager.disconnect(websocket)
        except:
            pass


# Main function to run the server
def run_server():
    """
    Run the FastAPI server
    """
    # Start the server
    uvicorn.run(
        "src.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()
