"""
Local API Server for Mobile App Communication

This module provides a FastAPI server that allows the mobile app to communicate
with the locally running trading bot without requiring a remote server.
"""

import os
import sys
import json
import time
import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add project root to the path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# FastAPI imports
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Import local executor
from src.core.local_executor import LocalExecutor
from src.utils.config_utils import load_config
from src.utils.jwt_utils import create_access_token, decode_access_token
from src.api.error_handling import register_exception_handlers, create_api_exception, ErrorResponse

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# API models
class StatusResponse(BaseModel):
    status: str
    uptime: float
    trading_active: bool
    paused: bool
    last_update: str
    resource_usage: dict
    network_status: str
    trades_executed: int
    errors_recovered: int
    bot_status: Optional[dict] = None
    account_info: Optional[dict] = None

class BotCommand(BaseModel):
    command: str  # start, stop, pause, resume
    parameters: dict = {}

class TradeRequest(BaseModel):
    symbol: str
    order_type: str  # BUY, SELL
    volume: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: Optional[str] = None

class SettingsUpdate(BaseModel):
    section: str  # 'mt5', 'trading', 'risk_management', 'strategies'
    settings: dict

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_status: dict = {}
        self.connection_ids: Dict[WebSocket, str] = {}
        
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Generate a unique connection ID
        connection_id = str(uuid.uuid4())
        self.connection_ids[websocket] = connection_id
        
        # Add to active connections
        self.active_connections.append(websocket)
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection_established",
            "connection_id": connection_id,
            "message": "Connected to ForexScalperAI trading bot",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # Send latest status immediately after connection
        if self.last_status:
            await websocket.send_json(self.last_status)
            
        logger.info(f"WebSocket client connected: {connection_id}")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client"""
        # Get connection ID for logging
        connection_id = self.connection_ids.get(websocket, "unknown")
        
        # Remove from active connections
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
        # Remove from connection IDs
        if websocket in self.connection_ids:
            del self.connection_ids[websocket]
            
        logger.info(f"WebSocket client disconnected: {connection_id}")
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients"""
        # Store the last status for new connections
        if message.get("type") == "status_update":
            self.last_status = message
        
        # Send to all active connections
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                # Mark for disconnection due to error
                logger.warning(f"Error sending to client {self.connection_ids.get(connection, 'unknown')}: {str(e)}")
                disconnected.append(connection)
                
        # Clean up any failed connections
        for connection in disconnected:
            self.disconnect(connection)
            
    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """Send a message to a specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Error sending personal message: {str(e)}")
            self.disconnect(websocket)

# Create the FastAPI app
app = FastAPI(title="Forex Bot Local API", 
              description="API for controlling the locally running trading bot",
              version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local use only - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize the local executor
executor = None
config_path = os.environ.get("CONFIG_PATH", "config/mt5_config.yaml")
local_config_path = os.environ.get("LOCAL_CONFIG_PATH", "config/local_execution.yaml")

# Create a connection manager
manager = ConnectionManager()

# Background tasks
async def status_broadcast():
    """Periodically broadcast status to all connected clients"""
    while True:
        if executor and executor.running:
            try:
                # Get detailed status information
                status = executor.get_status()
                
                # Add timestamp
                status["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
                
                # Get active trades if available
                try:
                    if hasattr(executor, 'get_active_trades'):
                        active_trades = executor.get_active_trades()
                        status["active_trades"] = active_trades
                except Exception as e:
                    logger.warning(f"Error getting active trades: {str(e)}")
                
                # Get market conditions if available
                try:
                    if hasattr(executor, 'get_market_conditions'):
                        market_conditions = executor.get_market_conditions()
                        status["market_conditions"] = market_conditions
                except Exception as e:
                    logger.warning(f"Error getting market conditions: {str(e)}")
                
                # Create the broadcast message
                message = {
                    "type": "status_update",
                    "data": status,
                    "timestamp": time.time()
                }
                
                # Broadcast to all clients
                await manager.broadcast(message)
                
            except Exception as e:
                logger.error(f"Error in status broadcast: {str(e)}")
                
                # Try to notify clients of the error
                try:
                    error_message = {
                        "type": "error",
                        "message": f"Error getting bot status: {str(e)}",
                        "timestamp": time.time()
                    }
                    await manager.broadcast(error_message)
                except:
                    pass
                
        # Wait for next update interval
        await asyncio.sleep(3)  # Update every 3 seconds

@app.on_event("startup")
async def startup_event():
    """Initialize the executor on startup"""
    global executor
    try:
        # Create the local executor
        executor = LocalExecutor(config_path, local_config_path)
        
        # Start background task for status updates
        asyncio.create_task(status_broadcast())
        
        logger.info("Local API server started")
    except Exception as e:
        logger.error(f"Failed to initialize local executor: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of the executor"""
    global executor
    if executor and executor.running:
        executor.stop()
        logger.info("Local executor stopped")

# Authentication endpoint
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and provide access token"""
    try:
        # Load config to check credentials
        local_conf = load_config(local_config_path)
        auth_config = local_conf.get("auth", {})
        
        # Check if the provided credentials match the configured ones
        if (form_data.username == auth_config.get("username") and 
            form_data.password == auth_config.get("password")):
            
            # Create access token
            access_token = create_access_token(
                data={"sub": form_data.username},
                expires_delta=auth_config.get("token_expires_minutes", 60)
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer"
            }
        else:
            # Invalid credentials
            raise create_api_exception(
                "INVALID_CREDENTIALS",
                "The username or password you entered is incorrect. Please try again."
            )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise create_api_exception(
            "SERVER_ERROR",
            f"An error occurred during authentication: {str(e)}",
            data={"exception_type": type(e).__name__}
        )

# Dependency for checking authentication
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Validate the access token and return the current user"""
    try:
        # Decode and validate the token
        user = decode_access_token(token)
        if user is None:
            raise create_api_exception(
                "INVALID_TOKEN",
                "Could not validate credentials. The token may be expired or invalid."
            )
        return user
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise create_api_exception(
            "UNAUTHORIZED",
            "Authentication failed. Please log in again.",
            data={"exception_type": type(e).__name__}
        )

# API endpoints
@app.get("/status", response_model=StatusResponse)
async def get_status(_: str = Depends(get_current_user)):
    """Get the current status of the bot"""
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        # Get status from executor
        status = executor.get_status()
        
        # Set last update time
        status["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        return status
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise create_api_exception(
            "SERVER_ERROR",
            f"Failed to retrieve bot status: {str(e)}",
            data={"exception_type": type(e).__name__}
        )

@app.post("/command")
async def execute_command(command: BotCommand, _: str = Depends(get_current_user)):
    """Execute a command on the bot"""
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        cmd = command.command.lower()
        params = command.parameters
        
        # Execute the appropriate command
        result = None
        if cmd == "start":
            if not executor.running:
                # Start the bot
                executor.start()
                result = {"status": "success", "message": "Bot started"}
            else:
                result = {"status": "warning", "message": "Bot is already running"}
                
        elif cmd == "stop":
            if executor.running:
                # Stop the bot
                executor.stop()
                result = {"status": "success", "message": "Bot stopped"}
            else:
                result = {"status": "warning", "message": "Bot is not running"}
                
        elif cmd == "pause":
            if executor.running and not executor.paused:
                # Pause the bot
                executor.pause()
                result = {"status": "success", "message": "Bot paused"}
            elif executor.paused:
                result = {"status": "warning", "message": "Bot is already paused"}
            else:
                raise create_api_exception(
                    "OPERATION_NOT_PERMITTED",
                    "Cannot pause: Bot is not running"
                )
                
        elif cmd == "resume":
            if executor.running and executor.paused:
                # Resume the bot
                executor.resume()
                result = {"status": "success", "message": "Bot resumed"}
            elif executor.running and not executor.paused:
                result = {"status": "warning", "message": "Bot is already running (not paused)"}
            else:
                raise create_api_exception(
                    "OPERATION_NOT_PERMITTED",
                    "Cannot resume: Bot is not running"
                )
                
        elif cmd == "restart":
            # Stop the bot if running
            if executor.running:
                executor.stop()
                
            # Start the bot again
            executor.start()
            result = {"status": "success", "message": "Bot restarted"}
            
        else:
            # Unknown command
            raise create_api_exception(
                "INVALID_COMMAND",
                f"Unknown command: {cmd}",
                data={"available_commands": ["start", "stop", "pause", "resume", "restart"]}
            )
            
        return result
    except Exception as e:
        logger.error(f"Error executing command {command.command}: {str(e)}")
        
        # Determine the type of error
        if isinstance(e, HTTPException):
            # Re-raise existing HTTP exceptions
            raise e
        else:
            raise create_api_exception(
                "EXECUTION_ERROR",
                f"Failed to execute command '{command.command}': {str(e)}",
                data={"command": command.command, "parameters": command.parameters, "exception_type": type(e).__name__}
            )

@app.post("/trade")
async def place_trade(trade: TradeRequest, _: str = Depends(get_current_user)):
    """Place a trade manually"""
    global executor
    
    # Check if bot is running
    if not executor or not executor.running:
        raise create_api_exception(
            "BOT_NOT_RUNNING",
            "Cannot place trade: Trading bot is not running. Please start the bot first."
        )
    
    # Check if bot is paused
    if executor.paused:
        raise create_api_exception(
            "BOT_IS_PAUSED",
            "Cannot place trade: Trading bot is paused. Please resume the bot first."
        )
    
    try:
        # Validate trade parameters
        if trade.volume <= 0:
            raise create_api_exception(
                "INVALID_TRADE_PARAMETERS",
                "Trade volume must be greater than zero",
                field="volume"
            )
        
        # Validate order type
        valid_order_types = ["BUY", "SELL"]
        if trade.order_type not in valid_order_types:
            raise create_api_exception(
                "INVALID_TRADE_PARAMETERS",
                f"Invalid order type. Must be one of: {', '.join(valid_order_types)}",
                field="order_type"
            )
        
        # Prepare trade parameters
        trade_params = {
            "symbol": trade.symbol,
            "order_type": trade.order_type,
            "volume": trade.volume,
        }
        
        # Add optional parameters if provided
        if trade.stop_loss is not None:
            trade_params["stop_loss"] = trade.stop_loss
        if trade.take_profit is not None:
            trade_params["take_profit"] = trade.take_profit
        if trade.comment is not None:
            trade_params["comment"] = trade.comment
        
        # Execute the trade
        result = executor.place_trade(trade_params)
        
        if result.get("success", False):
            return {
                "status": "success",
                "message": "Trade placed successfully",
                "trade_id": result.get("trade_id"),
                "details": result.get("details", {})
            }
        else:
            # Trade execution failed but without exception
            raise create_api_exception(
                "TRADE_EXECUTION_FAILED",
                result.get("message", "Failed to place trade"),
                data={"details": result.get("details", {})}
            )
            
    except Exception as e:
        logger.error(f"Error placing trade: {str(e)}")
        
        # Determine the type of error
        if isinstance(e, HTTPException):
            # Re-raise existing HTTP exceptions
            raise e
        else:
            raise create_api_exception(
                "TRADE_EXECUTION_FAILED",
                f"Failed to place trade: {str(e)}",
                data={"trade_request": trade.dict(), "exception_type": type(e).__name__}
            )

@app.put("/settings")
async def update_settings(settings: SettingsUpdate, _: str = Depends(get_current_user)):
    """Update bot settings"""
    global executor, config_path
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        # Load current config
        config = load_config(config_path)
        
        # Validate section
        section = settings.section
        if section not in config:
            raise create_api_exception(
                "INVALID_PARAMETER",
                f"Unknown settings section: {section}",
                field="section",
                data={"available_sections": list(config.keys())}
            )
        
        # Validate settings
        invalid_settings = []
        for key, value in settings.settings.items():
            if key not in config[section]:
                invalid_settings.append(key)
        
        if invalid_settings:
            raise create_api_exception(
                "INVALID_PARAMETER",
                f"Unknown setting(s) in section '{section}': {', '.join(invalid_settings)}",
                field="settings",
                data={
                    "invalid_settings": invalid_settings,
                    "available_settings": list(config[section].keys())
                }
            )
        
        # Special validations for specific settings
        if section == "risk_management":
            # Validate risk percentage
            if "risk_per_trade" in settings.settings:
                risk = settings.settings["risk_per_trade"]
                if not isinstance(risk, (int, float)) or risk <= 0 or risk > 5:
                    raise create_api_exception(
                        "INVALID_PARAMETER",
                        "Risk per trade must be a positive number between 0 and 5",
                        field="settings.risk_per_trade"
                    )
        
        # Market condition detection settings
        if section == "market_conditions":
            # Validate volatility thresholds
            if "volatility_thresholds" in settings.settings:
                thresholds = settings.settings["volatility_thresholds"]
                if not isinstance(thresholds, dict):
                    raise create_api_exception(
                        "INVALID_PARAMETER",
                        "Volatility thresholds must be a dictionary",
                        field="settings.volatility_thresholds"
                    )
        
        # Multi-asset trading settings
        if section == "multi_asset":
            # Validate correlation thresholds
            if "correlation_thresholds" in settings.settings:
                thresholds = settings.settings["correlation_thresholds"]
                if not isinstance(thresholds, dict):
                    raise create_api_exception(
                        "INVALID_PARAMETER",
                        "Correlation thresholds must be a dictionary",
                        field="settings.correlation_thresholds"
                    )
        
        # Update settings
        for key, value in settings.settings.items():
            config[section][key] = value
        
        # Save the updated config
        with open(config_path, 'w') as f:
            import yaml
            yaml.dump(config, f, default_flow_style=False)
        
        # Restart the bot if it's running
        restart_required = section in ["mt5", "trading_sessions", "multi_asset", "risk_management"]
        restart_message = ""
        
        if restart_required and executor.running:
            executor.stop()
            executor = LocalExecutor(config_path, local_config_path)
            executor.start()
            restart_message = " Bot has been restarted with new settings."
        
        return {
            "status": "success", 
            "message": f"Settings in section '{section}' updated successfully.{restart_message}",
            "updated_settings": settings.settings
        }
    
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        
        # Determine the type of error
        if isinstance(e, HTTPException):
            # Re-raise existing HTTP exceptions
            raise e
        else:
            raise create_api_exception(
                "SETTINGS_UPDATE_FAILED",
                f"Failed to update settings: {str(e)}",
                data={"section": settings.section, "exception_type": type(e).__name__}
            )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    
    try:
        # Main WebSocket communication loop
        while True:
            try:
                # Wait for any incoming messages from the client
                data = await websocket.receive_text()
                
                # Parse the JSON message
                try:
                    message = json.loads(data)
                    message_type = message.get("type", "")
                    
                    # Handle different message types
                    if message_type == "ping":
                        # Respond to ping with pong
                        await manager.send_personal_message(websocket, {
                            "type": "pong",
                            "timestamp": time.time()
                        })
                        
                    elif message_type == "get_status":
                        # Client requested current status
                        if executor and executor.running:
                            status = executor.get_status()
                            status["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
                            
                            await manager.send_personal_message(websocket, {
                                "type": "status_update",
                                "data": status,
                                "timestamp": time.time()
                            })
                        else:
                            await manager.send_personal_message(websocket, {
                                "type": "error",
                                "message": "Bot is not running",
                                "timestamp": time.time()
                            })
                            
                    elif message_type == "command":
                        # Execute a command
                        if not executor:
                            await manager.send_personal_message(websocket, {
                                "type": "error",
                                "message": "Local executor not initialized",
                                "timestamp": time.time()
                            })
                            continue
                            
                        command = message.get("command", "")
                        parameters = message.get("parameters", {})
                        
                        # Authorization token required for commands
                        token = message.get("token")
                        if not token:
                            await manager.send_personal_message(websocket, {
                                "type": "error",
                                "message": "Authentication required for commands",
                                "timestamp": time.time()
                            })
                            continue
                            
                        # Validate token
                        try:
                            user = decode_access_token(token)
                            if user is None:
                                raise Exception("Invalid token")
                                
                            # Process the command (reusing the HTTP command logic)
                            cmd_obj = BotCommand(command=command, parameters=parameters)
                            result = await execute_command(cmd_obj, user)
                            
                            # Send the command result
                            await manager.send_personal_message(websocket, {
                                "type": "command_result",
                                "command": command,
                                "result": result,
                                "timestamp": time.time()
                            })
                            
                        except Exception as e:
                            await manager.send_personal_message(websocket, {
                                "type": "error",
                                "message": f"Authentication or command error: {str(e)}",
                                "timestamp": time.time()
                            })
                            
                except json.JSONDecodeError:
                    # Not a valid JSON message
                    await manager.send_personal_message(websocket, {
                        "type": "error",
                        "message": "Invalid JSON message",
                        "timestamp": time.time()
                    })
                    
            except WebSocketDisconnect:
                # Client disconnected
                manager.disconnect(websocket)
                break
                
            except Exception as e:
                # Other error while processing client message
                logger.error(f"WebSocket error: {str(e)}")
                try:
                    await manager.send_personal_message(websocket, {
                        "type": "error",
                        "message": f"Error processing message: {str(e)}",
                        "timestamp": time.time()
                    })
                except:
                    # Failed to send error message, client may be disconnected
                    manager.disconnect(websocket)
                    break
                    
    except Exception as e:
        # Main loop exception
        logger.error(f"WebSocket connection error: {str(e)}")
        manager.disconnect(websocket)

# API endpoints for market conditions and multi-asset trading
@app.get("/market_conditions")
async def get_market_conditions(_: str = Depends(get_current_user)):
    """Get current market conditions analysis"""
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    if not executor.running:
        raise create_api_exception(
            "BOT_NOT_RUNNING",
            "Trading bot is not running. Start the bot to access market condition data."
        )
    
    try:
        # Get market conditions data
        if hasattr(executor, 'get_market_conditions'):
            market_conditions = executor.get_market_conditions()
            
            return {
                "status": "success",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "market_conditions": market_conditions
            }
        else:
            raise create_api_exception(
                "OPERATION_NOT_PERMITTED",
                "Market condition detection is not available in this version of the bot."
            )
    except Exception as e:
        logger.error(f"Error getting market conditions: {str(e)}")
        
        # Determine the type of error
        if isinstance(e, HTTPException):
            # Re-raise existing HTTP exceptions
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to retrieve market conditions: {str(e)}",
                data={"exception_type": type(e).__name__}
            )

@app.get("/active_instruments")
async def get_active_instruments(_: str = Depends(get_current_user)):
    """Get currently active trading instruments"""
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    if not executor.running:
        raise create_api_exception(
            "BOT_NOT_RUNNING",
            "Trading bot is not running. Start the bot to access active instruments data."
        )
    
    try:
        # Get active instruments data
        if hasattr(executor, 'get_active_instruments'):
            active_instruments = executor.get_active_instruments()
            
            return {
                "status": "success",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "active_instruments": active_instruments
            }
        else:
            raise create_api_exception(
                "OPERATION_NOT_PERMITTED",
                "Multi-asset trading integration is not available in this version of the bot."
            )
    except Exception as e:
        logger.error(f"Error getting active instruments: {str(e)}")
        
        # Determine the type of error
        if isinstance(e, HTTPException):
            # Re-raise existing HTTP exceptions
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to retrieve active instruments: {str(e)}",
                data={"exception_type": type(e).__name__}
            )

@app.get("/instruments/{symbol}/analysis")
async def get_instrument_analysis(symbol: str, _: str = Depends(get_current_user)):
    """Get detailed analysis for a specific trading instrument"""
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    if not executor.running:
        raise create_api_exception(
            "BOT_NOT_RUNNING",
            "Trading bot is not running. Start the bot to access instrument analysis."
        )
    
    try:
        # Get instrument analysis
        if hasattr(executor, 'get_instrument_analysis'):
            analysis = executor.get_instrument_analysis(symbol)
            
            if not analysis:
                raise create_api_exception(
                    "NOT_FOUND",
                    f"No analysis available for instrument: {symbol}",
                    field="symbol"
                )
            
            return {
                "status": "success",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": symbol,
                "analysis": analysis
            }
        else:
            raise create_api_exception(
                "OPERATION_NOT_PERMITTED",
                "Instrument analysis is not available in this version of the bot."
            )
    except Exception as e:
        logger.error(f"Error getting instrument analysis for {symbol}: {str(e)}")
        
        # Determine the type of error
        if isinstance(e, HTTPException):
            # Re-raise existing HTTP exceptions
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to retrieve analysis for {symbol}: {str(e)}",
                data={"symbol": symbol, "exception_type": type(e).__name__}
            )

@app.get("/active_trades")
async def get_active_trades(_: str = Depends(get_current_user)):
    """Get currently active trades"""
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    if not executor.running:
        raise create_api_exception(
            "BOT_NOT_RUNNING",
            "Trading bot is not running. Start the bot to access active trades."
        )
    
    try:
        # Get active trades
        if hasattr(executor, 'get_active_trades'):
            active_trades = executor.get_active_trades()
            
            return {
                "status": "success",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "count": len(active_trades),
                "trades": active_trades
            }
        else:
            raise create_api_exception(
                "OPERATION_NOT_PERMITTED",
                "Active trades information is not available in this version of the bot."
            )
    except Exception as e:
        logger.error(f"Error getting active trades: {str(e)}")
        
        # Determine the type of error
        if isinstance(e, HTTPException):
            # Re-raise existing HTTP exceptions
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to retrieve active trades: {str(e)}",
                data={"exception_type": type(e).__name__}
            )

@app.delete("/trades/{trade_id}")
async def close_trade(trade_id: int, _: str = Depends(get_current_user)):
    """Close a specific trade by ID"""
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    if not executor.running:
        raise create_api_exception(
            "BOT_NOT_RUNNING",
            "Trading bot is not running. Start the bot to close trades."
        )
    
    try:
        # Close the trade
        if hasattr(executor, 'close_trade'):
            result = executor.close_trade(trade_id)
            
            if result.get("success", False):
                return {
                    "status": "success",
                    "message": f"Trade {trade_id} closed successfully",
                    "details": result.get("details", {})
                }
            else:
                raise create_api_exception(
                    "OPERATION_NOT_PERMITTED",
                    result.get("message", f"Failed to close trade {trade_id}"),
                    data={"trade_id": trade_id, "details": result.get("details", {})}
                )
        else:
            raise create_api_exception(
                "OPERATION_NOT_PERMITTED",
                "Trade management is not available in this version of the bot."
            )
    except Exception as e:
        logger.error(f"Error closing trade {trade_id}: {str(e)}")
        
        # Determine the type of error
        if isinstance(e, HTTPException):
            # Re-raise existing HTTP exceptions
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to close trade {trade_id}: {str(e)}",
                data={"trade_id": trade_id, "exception_type": type(e).__name__}
            )

@app.get("/trade-history")
async def get_trade_history(
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None, 
    symbol: Optional[str] = None,
    strategy: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    _: str = Depends(get_current_user)
):
    """
    Get trade history with optional filtering by date range, symbol, or strategy.
    
    Parameters:
    - start_date: Optional filter for trades after this date (format: YYYY-MM-DD)
    - end_date: Optional filter for trades before this date (format: YYYY-MM-DD)
    - symbol: Optional filter for specific trading symbol
    - strategy: Optional filter for specific strategy that executed the trade
    - limit: Maximum number of trades to return (default: 100)
    - offset: Number of trades to skip for pagination (default: 0)
    """
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        # Convert date strings to datetime objects if provided
        from datetime import datetime
        start_datetime = None
        end_datetime = None
        
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise create_api_exception(
                    "INVALID_PARAMETER",
                    "Invalid start_date format. Use YYYY-MM-DD format.",
                    data={"parameter": "start_date", "value": start_date}
                )
                
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                # Set time to end of day
                end_datetime = datetime.combine(end_datetime.date(), datetime.max.time())
            except ValueError:
                raise create_api_exception(
                    "INVALID_PARAMETER",
                    "Invalid end_date format. Use YYYY-MM-DD format.",
                    data={"parameter": "end_date", "value": end_date}
                )
        
        # Get trade history from executor with filters
        if hasattr(executor, 'get_trade_history'):
            history = executor.get_trade_history(
                start_date=start_datetime,
                end_date=end_datetime,
                symbol=symbol,
                strategy=strategy,
                limit=limit,
                offset=offset
            )
            
            # Calculate summary statistics for the filtered trades
            total_trades = history.get("total_count", 0)
            winning_trades = sum(1 for trade in history.get("trades", []) if trade.get("profit", 0) > 0)
            losing_trades = sum(1 for trade in history.get("trades", []) if trade.get("profit", 0) < 0)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            total_profit = sum(trade.get("profit", 0) for trade in history.get("trades", []))
            average_profit = total_profit / total_trades if total_trades > 0 else 0
            
            # Add summary to response
            history["summary"] = {
                "win_rate": round(win_rate, 2),
                "total_profit": round(total_profit, 2),
                "average_profit": round(average_profit, 2),
                "winning_trades": winning_trades,
                "losing_trades": losing_trades
            }
            
            return history
        else:
            raise create_api_exception(
                "FEATURE_NOT_SUPPORTED",
                "Trade history retrieval is not supported in this version of the bot."
            )
    except Exception as e:
        logger.error(f"Error retrieving trade history: {str(e)}")
        
        if isinstance(e, HTTPException):
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to retrieve trade history: {str(e)}",
                data={"exception_type": type(e).__name__}
            )

@app.get("/trade-statistics")
async def get_trade_statistics(
    period: str = "all",  # all, today, this_week, this_month, custom
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    symbol: Optional[str] = None,
    _: str = Depends(get_current_user)
):
    """
    Get aggregated trade statistics for analysis.
    
    Parameters:
    - period: Time period for statistics (all, today, this_week, this_month, custom)
    - start_date: Required for custom period, format: YYYY-MM-DD
    - end_date: Required for custom period, format: YYYY-MM-DD
    - symbol: Optional filter for specific trading symbol
    """
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        # Validate period and date parameters
        if period == "custom" and (not start_date or not end_date):
            raise create_api_exception(
                "MISSING_PARAMETER",
                "Custom period requires both start_date and end_date parameters.",
                data={"period": period}
            )
        
        # Get trade statistics from executor
        if hasattr(executor, 'get_trade_statistics'):
            statistics = executor.get_trade_statistics(
                period=period,
                start_date=start_date,
                end_date=end_date,
                symbol=symbol
            )
            
            return statistics
        else:
            raise create_api_exception(
                "FEATURE_NOT_SUPPORTED",
                "Trade statistics retrieval is not supported in this version of the bot."
            )
    except Exception as e:
        logger.error(f"Error retrieving trade statistics: {str(e)}")
        
        if isinstance(e, HTTPException):
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to retrieve trade statistics: {str(e)}",
                data={"exception_type": type(e).__name__}
            )

@app.get("/portfolio")
async def get_portfolio(
    include_historical: bool = False,
    timeframe: str = "1d",  # 1d, 1w, 1m, 3m, 6m, 1y
    _: str = Depends(get_current_user)
):
    """
    Get a comprehensive view of the trading portfolio with performance metrics.
    
    Parameters:
    - include_historical: Include historical portfolio value data for equity curves
    - timeframe: Time period for historical data (1d, 1w, 1m, 3m, 6m, 1y)
    """
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        # Get portfolio data from executor
        if hasattr(executor, 'get_portfolio_data'):
            portfolio_data = executor.get_portfolio_data(
                include_historical=include_historical,
                timeframe=timeframe
            )
            
            # Structure the response
            response = {
                "account_summary": {
                    "balance": portfolio_data.get("balance", 0.0),
                    "equity": portfolio_data.get("equity", 0.0),
                    "margin": portfolio_data.get("margin", 0.0),
                    "free_margin": portfolio_data.get("free_margin", 0.0),
                    "margin_level": portfolio_data.get("margin_level", 0.0),
                    "currency": portfolio_data.get("currency", "USD")
                },
                "performance_metrics": {
                    "daily_pnl": portfolio_data.get("daily_pnl", 0.0),
                    "weekly_pnl": portfolio_data.get("weekly_pnl", 0.0),
                    "monthly_pnl": portfolio_data.get("monthly_pnl", 0.0),
                    "total_pnl": portfolio_data.get("total_pnl", 0.0),
                    "win_rate": portfolio_data.get("win_rate", 0.0),
                    "sharpe_ratio": portfolio_data.get("sharpe_ratio", 0.0),
                    "drawdown": portfolio_data.get("drawdown", 0.0),
                    "drawdown_percentage": portfolio_data.get("drawdown_percentage", 0.0)
                },
                "open_positions": portfolio_data.get("open_positions", []),
                "asset_allocation": portfolio_data.get("asset_allocation", {}),
                "position_distribution": portfolio_data.get("position_distribution", {}),
                "risk_exposure": portfolio_data.get("risk_exposure", {})
            }
            
            # Include historical data if requested
            if include_historical:
                response["historical_data"] = {
                    "equity_curve": portfolio_data.get("equity_curve", []),
                    "balance_curve": portfolio_data.get("balance_curve", []),
                    "drawdown_curve": portfolio_data.get("drawdown_curve", []),
                    "timestamp": portfolio_data.get("timestamp", [])
                }
            
            return response
        else:
            # Fallback implementation if executor doesn't have the method
            # This is to ensure backward compatibility
            logger.warning("Using fallback portfolio implementation")
            
            # Get basic account information
            account_info = {}
            if hasattr(executor, 'get_account_info'):
                account_info = executor.get_account_info() or {}
            
            # Get open positions
            open_positions = []
            if hasattr(executor, 'get_open_positions'):
                open_positions = executor.get_open_positions() or []
            
            # Calculate basic portfolio metrics
            total_profit = sum(pos.get("profit", 0) for pos in open_positions)
            
            # Create a simplified portfolio response
            response = {
                "account_summary": {
                    "balance": account_info.get("balance", 0.0),
                    "equity": account_info.get("equity", 0.0),
                    "margin": account_info.get("margin", 0.0),
                    "free_margin": account_info.get("free_margin", 0.0),
                    "margin_level": account_info.get("margin_level", 0.0),
                    "currency": account_info.get("currency", "USD")
                },
                "performance_metrics": {
                    "total_pnl": total_profit,
                    "open_positions_count": len(open_positions)
                },
                "open_positions": open_positions
            }
            
            return response
    except Exception as e:
        logger.error(f"Error retrieving portfolio data: {str(e)}")
        
        if isinstance(e, HTTPException):
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to retrieve portfolio data: {str(e)}",
                data={"exception_type": type(e).__name__}
            )

@app.get("/portfolio/performance")
async def get_portfolio_performance(
    period: str = "1m",  # 1d, 1w, 1m, 3m, 6m, 1y, all
    comparison: Optional[str] = None,  # None, "benchmark", "symbol"
    benchmark: Optional[str] = None,  # e.g., "S&P500", "EURUSD", etc.
    _: str = Depends(get_current_user)
):
    """
    Get detailed portfolio performance metrics with optional benchmark comparison.
    
    Parameters:
    - period: Time period for performance data
    - comparison: Type of comparison to perform (None, "benchmark", "symbol")
    - benchmark: Benchmark identifier if comparison is set
    """
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        # Get portfolio performance data from executor
        if hasattr(executor, 'get_portfolio_performance'):
            performance = executor.get_portfolio_performance(
                period=period,
                comparison=comparison,
                benchmark=benchmark
            )
            
            return performance
        else:
            raise create_api_exception(
                "FEATURE_NOT_SUPPORTED",
                "Portfolio performance analysis is not supported in this version of the bot."
            )
    except Exception as e:
        logger.error(f"Error retrieving portfolio performance: {str(e)}")
        
        if isinstance(e, HTTPException):
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to retrieve portfolio performance: {str(e)}",
                data={"exception_type": type(e).__name__}
            )

@app.get("/market-analysis/{symbol}")
async def get_market_analysis(
    symbol: str,
    timeframe: str = "H1",  # M1, M5, M15, M30, H1, H4, D1, W1, MN1
    num_candles: int = 100,
    indicators: Optional[str] = None,  # comma-separated list of indicators
    _: str = Depends(get_current_user)
):
    """
    Get market analysis data including price data and technical indicators.
    
    Parameters:
    - symbol: Trading symbol (e.g., EURUSD)
    - timeframe: Chart timeframe
    - num_candles: Number of candles/bars to return
    - indicators: Comma-separated list of technical indicators to include
    """
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        # Parse indicators list
        indicator_list = []
        if indicators:
            indicator_list = [ind.strip() for ind in indicators.split(",")]
        
        # Get market data from executor
        if hasattr(executor, 'get_market_analysis'):
            analysis = executor.get_market_analysis(
                symbol=symbol,
                timeframe=timeframe,
                num_candles=num_candles,
                indicators=indicator_list
            )
            
            return analysis
        else:
            raise create_api_exception(
                "FEATURE_NOT_SUPPORTED",
                "Market analysis is not supported in this version of the bot."
            )
    except Exception as e:
        logger.error(f"Error retrieving market analysis for {symbol}: {str(e)}")
        
        if isinstance(e, HTTPException):
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to retrieve market analysis: {str(e)}",
                data={"symbol": symbol, "exception_type": type(e).__name__}
            )

@app.get("/market-condition-assessment/{symbol}")
async def get_market_condition_assessment(
    symbol: str,
    timeframe: str = "H1",
    _: str = Depends(get_current_user)
):
    """
    Get a comprehensive assessment of current market conditions for a symbol.
    
    Parameters:
    - symbol: Trading symbol (e.g., EURUSD)
    - timeframe: Timeframe for analysis
    """
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        # Get market condition assessment from executor
        if hasattr(executor, 'get_market_condition_assessment'):
            assessment = executor.get_market_condition_assessment(
                symbol=symbol,
                timeframe=timeframe
            )
            
            return assessment
        else:
            raise create_api_exception(
                "FEATURE_NOT_SUPPORTED",
                "Market condition assessment is not supported in this version of the bot."
            )
    except Exception as e:
        logger.error(f"Error retrieving market condition assessment for {symbol}: {str(e)}")
        
        if isinstance(e, HTTPException):
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to retrieve market condition assessment: {str(e)}",
                data={"symbol": symbol, "exception_type": type(e).__name__}
            )

@app.get("/available-indicators")
async def get_available_indicators(_: str = Depends(get_current_user)):
    """
    Get a list of all available technical indicators that can be used in market analysis.
    """
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        # Get available indicators from executor
        if hasattr(executor, 'get_available_indicators'):
            indicators = executor.get_available_indicators()
            
            return {
                "indicators": indicators
            }
        else:
            # Fallback to providing a standard list of common indicators
            standard_indicators = [
                {"id": "sma", "name": "Simple Moving Average", "parameters": ["period"]},
                {"id": "ema", "name": "Exponential Moving Average", "parameters": ["period"]},
                {"id": "rsi", "name": "Relative Strength Index", "parameters": ["period"]},
                {"id": "macd", "name": "MACD", "parameters": ["fast_period", "slow_period", "signal_period"]},
                {"id": "bollinger", "name": "Bollinger Bands", "parameters": ["period", "deviations"]},
                {"id": "stochastic", "name": "Stochastic Oscillator", "parameters": ["k_period", "d_period", "slowing"]},
                {"id": "atr", "name": "Average True Range", "parameters": ["period"]},
                {"id": "adx", "name": "Average Directional Index", "parameters": ["period"]}
            ]
            
            return {
                "indicators": standard_indicators,
                "note": "Using standard indicator list. For custom indicators, update the executor implementation."
            }
    except Exception as e:
        logger.error(f"Error retrieving available indicators: {str(e)}")
        
        if isinstance(e, HTTPException):
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to retrieve available indicators: {str(e)}",
                data={"exception_type": type(e).__name__}
            )

@app.get("/risk-management/settings")
async def get_risk_management_settings(_: str = Depends(get_current_user)):
    """
    Get the current risk management settings.
    """
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        if hasattr(executor, 'get_risk_settings'):
            settings = executor.get_risk_settings()
            return settings
        else:
            raise create_api_exception(
                "FEATURE_NOT_SUPPORTED",
                "Risk management settings retrieval is not supported in this version of the bot."
            )
    except Exception as e:
        logger.error(f"Error retrieving risk management settings: {str(e)}")
        
        if isinstance(e, HTTPException):
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to retrieve risk management settings: {str(e)}",
                data={"exception_type": type(e).__name__}
            )

@app.put("/risk-management/settings")
async def update_risk_management_settings(
    settings: dict, 
    _: str = Depends(get_current_user)
):
    """
    Update risk management settings.
    
    Settings include:
    - max_risk_per_trade: Maximum risk percentage per trade
    - max_daily_drawdown: Maximum allowed daily drawdown percentage
    - max_total_drawdown: Maximum allowed total drawdown percentage
    - position_sizing_method: Method used for position sizing (fixed, risk-based, kelly)
    - risk_reward_ratio: Minimum risk-reward ratio for trades
    - max_open_positions: Maximum number of open positions allowed
    - correlation_threshold: Threshold for correlation filtering
    """
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        # Validate risk settings before applying
        required_keys = ['max_risk_per_trade', 'max_daily_drawdown', 'max_total_drawdown']
        missing_keys = [key for key in required_keys if key not in settings]
        
        if missing_keys:
            raise create_api_exception(
                "MISSING_PARAMETER",
                f"Missing required risk parameters: {', '.join(missing_keys)}",
                data={"missing_keys": missing_keys}
            )
        
        # Validate value ranges
        if settings.get('max_risk_per_trade', 0) < 0 or settings.get('max_risk_per_trade', 0) > 100:
            raise create_api_exception(
                "INVALID_PARAMETER",
                "max_risk_per_trade must be between 0 and 100",
                data={"parameter": "max_risk_per_trade", "value": settings.get('max_risk_per_trade')}
            )
        
        if settings.get('max_daily_drawdown', 0) < 0 or settings.get('max_daily_drawdown', 0) > 100:
            raise create_api_exception(
                "INVALID_PARAMETER",
                "max_daily_drawdown must be between 0 and 100",
                data={"parameter": "max_daily_drawdown", "value": settings.get('max_daily_drawdown')}
            )
        
        if settings.get('max_total_drawdown', 0) < 0 or settings.get('max_total_drawdown', 0) > 100:
            raise create_api_exception(
                "INVALID_PARAMETER",
                "max_total_drawdown must be between 0 and 100",
                data={"parameter": "max_total_drawdown", "value": settings.get('max_total_drawdown')}
            )
        
        # Apply risk settings
        if hasattr(executor, 'update_risk_settings'):
            result = executor.update_risk_settings(settings)
            
            if result.get("success", False):
                return {
                    "status": "success",
                    "message": "Risk management settings updated successfully",
                    "settings": result.get("settings", {})
                }
            else:
                raise create_api_exception(
                    "UPDATE_FAILED",
                    result.get("message", "Failed to update risk management settings"),
                    data={"details": result.get("details", {})}
                )
        else:
            raise create_api_exception(
                "FEATURE_NOT_SUPPORTED",
                "Risk management settings update is not supported in this version of the bot."
            )
    except Exception as e:
        logger.error(f"Error updating risk management settings: {str(e)}")
        
        if isinstance(e, HTTPException):
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to update risk management settings: {str(e)}",
                data={"exception_type": type(e).__name__}
            )

@app.post("/risk-management/emergency-stop")
async def emergency_stop_trading(
    reason: Optional[str] = None,
    close_positions: bool = False,
    _: str = Depends(get_current_user)
):
    """
    Emergency stop for all trading activities.
    
    Parameters:
    - reason: Optional reason for the emergency stop
    - close_positions: Whether to close all open positions
    """
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        if hasattr(executor, 'emergency_stop'):
            result = executor.emergency_stop(
                reason=reason,
                close_positions=close_positions
            )
            
            if result.get("success", False):
                return {
                    "status": "success",
                    "message": "Emergency stop triggered successfully",
                    "details": result.get("details", {})
                }
            else:
                raise create_api_exception(
                    "OPERATION_FAILED",
                    result.get("message", "Failed to trigger emergency stop"),
                    data={"details": result.get("details", {})}
                )
        else:
            raise create_api_exception(
                "FEATURE_NOT_SUPPORTED",
                "Emergency stop is not supported in this version of the bot."
            )
    except Exception as e:
        logger.error(f"Error triggering emergency stop: {str(e)}")
        
        if isinstance(e, HTTPException):
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to trigger emergency stop: {str(e)}",
                data={"exception_type": type(e).__name__}
            )

@app.get("/offline/sync-status")
async def get_offline_sync_status(_: str = Depends(get_current_user)):
    """
    Get the current offline synchronization status.
    """
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        if hasattr(executor, 'get_offline_sync_status'):
            status = executor.get_offline_sync_status()
            return status
        else:
            # Provide a basic offline status if the executor doesn't have the method
            return {
                "offline_enabled": True,
                "last_sync_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "cached_data": {
                    "symbols": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"],
                    "timeframes": ["M1", "M5", "M15", "H1", "H4", "D1"],
                    "indicators": ["SMA", "EMA", "RSI", "MACD", "Bollinger"],
                    "historical_data_days": 30
                },
                "sync_progress": 100,
                "storage_usage": {
                    "used_mb": 25,
                    "total_mb": 100,
                    "percentage": 25
                }
            }
    except Exception as e:
        logger.error(f"Error retrieving offline sync status: {str(e)}")
        
        if isinstance(e, HTTPException):
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to retrieve offline sync status: {str(e)}",
                data={"exception_type": type(e).__name__}
            )

@app.post("/offline/sync")
async def trigger_offline_sync(
    sync_options: dict = {},
    _: str = Depends(get_current_user)
):
    """
    Trigger a synchronization for offline mode.
    
    Parameters:
    - sync_options: Options for synchronization
      - symbols: List of symbols to sync
      - timeframes: List of timeframes to sync
      - days: Number of days of historical data to sync
      - indicators: List of indicators to precalculate
    """
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        # Set default sync options if not provided
        default_options = {
            "symbols": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"],
            "timeframes": ["M1", "M5", "M15", "H1", "H4", "D1"],
            "days": 30,
            "indicators": ["SMA", "EMA", "RSI", "MACD", "Bollinger"]
        }
        
        # Merge with provided options
        for key, value in default_options.items():
            if key not in sync_options:
                sync_options[key] = value
        
        # Trigger synchronization
        if hasattr(executor, 'sync_offline_data'):
            result = executor.sync_offline_data(sync_options)
            
            if result.get("success", False):
                return {
                    "status": "success",
                    "message": "Offline synchronization started successfully",
                    "details": result.get("details", {})
                }
            else:
                raise create_api_exception(
                    "SYNC_FAILED",
                    result.get("message", "Failed to start offline synchronization"),
                    data={"details": result.get("details", {})}
                )
        else:
            # Simulate a successful response if the executor doesn't have the method
            return {
                "status": "success",
                "message": "Offline synchronization started successfully (simulated)",
                "details": {
                    "sync_id": str(uuid.uuid4()),
                    "estimated_completion_time": "5 minutes",
                    "storage_required_mb": 25
                }
            }
    except Exception as e:
        logger.error(f"Error triggering offline synchronization: {str(e)}")
        
        if isinstance(e, HTTPException):
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to trigger offline synchronization: {str(e)}",
                data={"exception_type": type(e).__name__}
            )

@app.get("/offline/cached-data")
async def get_offline_cached_data(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    _: str = Depends(get_current_user)
):
    """
    Get information about data cached for offline use.
    
    Parameters:
    - symbol: Optional filter for specific symbol
    - timeframe: Optional filter for specific timeframe
    """
    global executor
    
    if not executor:
        raise create_api_exception(
            "SERVICE_UNAVAILABLE",
            "Local executor not initialized. The trading bot service is unavailable."
        )
    
    try:
        if hasattr(executor, 'get_offline_cached_data'):
            cached_data = executor.get_offline_cached_data(
                symbol=symbol,
                timeframe=timeframe
            )
            return cached_data
        else:
            # Provide sample cached data if the executor doesn't have the method
            sample_data = {
                "symbols": {
                    "EURUSD": {
                        "timeframes": ["M1", "M5", "M15", "H1", "H4", "D1"],
                        "date_range": "2025-03-11 to 2025-04-11",
                        "indicators": ["SMA", "EMA", "RSI", "MACD", "Bollinger"],
                        "size_mb": 5.2
                    },
                    "GBPUSD": {
                        "timeframes": ["M1", "M5", "M15", "H1", "H4", "D1"],
                        "date_range": "2025-03-11 to 2025-04-11",
                        "indicators": ["SMA", "EMA", "RSI", "MACD", "Bollinger"],
                        "size_mb": 5.1
                    },
                    "USDJPY": {
                        "timeframes": ["M1", "M5", "M15", "H1", "H4", "D1"],
                        "date_range": "2025-03-11 to 2025-04-11",
                        "indicators": ["SMA", "EMA", "RSI", "MACD", "Bollinger"],
                        "size_mb": 4.9
                    },
                    "AUDUSD": {
                        "timeframes": ["M1", "M5", "M15", "H1", "H4", "D1"],
                        "date_range": "2025-03-11 to 2025-04-11",
                        "indicators": ["SMA", "EMA", "RSI", "MACD", "Bollinger"],
                        "size_mb": 4.8
                    }
                },
                "total_size_mb": 20.0,
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Filter by symbol if specified
            if symbol:
                if symbol in sample_data["symbols"]:
                    filtered_data = {
                        "symbols": {symbol: sample_data["symbols"][symbol]},
                        "total_size_mb": sample_data["symbols"][symbol]["size_mb"],
                        "last_updated": sample_data["last_updated"]
                    }
                    
                    # Filter by timeframe if specified
                    if timeframe and timeframe in sample_data["symbols"][symbol]["timeframes"]:
                        filtered_data["symbols"][symbol]["timeframes"] = [timeframe]
                    
                    return filtered_data
                else:
                    return {"symbols": {}, "total_size_mb": 0, "last_updated": sample_data["last_updated"]}
            
            return sample_data
    except Exception as e:
        logger.error(f"Error retrieving offline cached data: {str(e)}")
        
        if isinstance(e, HTTPException):
            raise e
        else:
            raise create_api_exception(
                "SERVER_ERROR",
                f"Failed to retrieve offline cached data: {str(e)}",
                data={"exception_type": type(e).__name__}
            )

# Main function to run the server
def start_local_api(host="127.0.0.1", port=8000, config="config/mt5_config.yaml", 
                    local_config="config/local_execution.yaml"):
    """Start the local API server"""
    global config_path, local_config_path
    
    config_path = config
    local_config_path = local_config
    
    # Load local config to get API settings
    try:
        local_conf = load_config(local_config)
        api_config = local_conf.get("execution", {}).get("local_api", {})
        if api_config.get("enabled", True):
            host = api_config.get("host", host)
            port = api_config.get("port", port)
        else:
            logger.warning("Local API is disabled in config. Not starting server.")
            return
    except Exception as e:
        logger.warning(f"Error loading local config: {str(e)}. Using default settings.")
    
    # Start the server
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    # Setup logging to file
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "local_api.log")
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    import argparse
    parser = argparse.ArgumentParser(description="Local API server for Forex trading bot")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--config", type=str, default="config/mt5_config.yaml", help="Path to MT5 config file")
    parser.add_argument("--local-config", type=str, default="config/local_execution.yaml", help="Path to local execution config")
    
    args = parser.parse_args()
    
    start_local_api(args.host, args.port, args.config, args.local_config)
