# FastAPI Server Mobile Enhancement Guide

This guide outlines the necessary enhancements to the existing FastAPI server to support mobile connectivity and provide real-time data via WebSockets.

## 1. Authentication Enhancements

### 1.1 MT5 Credential Handling

Modify the authentication system to accept and validate MT5 credentials:

```python
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional

# JWT configuration
SECRET_KEY = "YOUR_SECRET_KEY"  # Replace with a secure secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Models
class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    username: Optional[str] = None
    
class MT5Credentials(BaseModel):
    account: str
    password: str
    server: str
    
class User(BaseModel):
    username: str
    disabled: Optional[bool] = None

# Password context for hashing (if storing local users)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# JWT token creation
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# MT5 authentication function (integrate with your MT5 controller)
async def authenticate_mt5(credentials: MT5Credentials):
    # Here, call your MT5 connection logic to verify credentials
    # This is a placeholder - implement actual MT5 authentication
    is_valid = await bot_controller.verify_mt5_credentials(
        credentials.account, 
        credentials.password,
        credentials.server
    )
    
    if not is_valid:
        return False
    
    return True

# Token endpoint for mobile app
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # For OAuth2 compatibility, translate form_data to MT5 format
    # In real usage, you'd create a dedicated MT5 login endpoint
    credentials = MT5Credentials(
        account=form_data.username,
        password=form_data.password,
        server=form_data.scopes[0] if form_data.scopes else "default"
    )
    
    user_authenticated = await authenticate_mt5(credentials)
    if not user_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect MT5 credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create and return JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": credentials.account, "server": credentials.server},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# MT5-specific login endpoint (better for mobile apps)
@app.post("/mt5_login", response_model=Token)
async def mt5_login(credentials: MT5Credentials):
    user_authenticated = await authenticate_mt5(credentials)
    if not user_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect MT5 credentials"
        )
    
    # Create and return JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": credentials.account, "server": credentials.server},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# Token verification and user extraction
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
    except JWTError:
        raise credentials_exception
    
    # Here you would typically load user from a database
    # For MT5 integration, we just create a user object from token data
    user = User(username=token_data.username)
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
```

## 2. WebSocket Implementation

### 2.1 WebSocket Connection Manager

Create a WebSocket connection manager to handle multiple clients:

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set

class ConnectionManager:
    def __init__(self):
        # Active connections: {account_id: {connection_id: WebSocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Map of connection IDs to account IDs for quick lookups
        self.connection_to_account: Dict[str, str] = {}
        # Counter for generating unique connection IDs
        self.connection_counter = 0
    
    def _get_connection_id(self) -> str:
        """Generate a unique connection ID"""
        self.connection_counter += 1
        return f"conn_{self.connection_counter}"
    
    async def connect(self, websocket: WebSocket, account_id: str) -> str:
        """Connect a new client and return connection ID"""
        await websocket.accept()
        
        # Generate a unique connection ID
        connection_id = self._get_connection_id()
        
        # Initialize account entry if not exists
        if account_id not in self.active_connections:
            self.active_connections[account_id] = {}
        
        # Add the connection to both mappings
        self.active_connections[account_id][connection_id] = websocket
        self.connection_to_account[connection_id] = account_id
        
        return connection_id
    
    def disconnect(self, connection_id: str) -> None:
        """Remove a disconnected client"""
        if connection_id not in self.connection_to_account:
            return
            
        account_id = self.connection_to_account[connection_id]
        
        # Remove from account's connections
        if account_id in self.active_connections and connection_id in self.active_connections[account_id]:
            del self.active_connections[account_id][connection_id]
            
            # Remove account entry if no connections left
            if not self.active_connections[account_id]:
                del self.active_connections[account_id]
        
        # Remove from connection mapping
        del self.connection_to_account[connection_id]
    
    async def send_personal_message(self, message: dict, connection_id: str) -> bool:
        """Send a message to a specific connection"""
        if connection_id not in self.connection_to_account:
            return False
            
        account_id = self.connection_to_account[connection_id]
        
        if account_id not in self.active_connections or connection_id not in self.active_connections[account_id]:
            return False
            
        websocket = self.active_connections[account_id][connection_id]
        await websocket.send_json(message)
        return True
    
    async def broadcast_to_account(self, message: dict, account_id: str) -> int:
        """Send a message to all connections for an account"""
        if account_id not in self.active_connections:
            return 0
            
        count = 0
        for websocket in self.active_connections[account_id].values():
            await websocket.send_json(message)
            count += 1
            
        return count
    
    async def broadcast(self, message: dict) -> int:
        """Send a message to all connected clients"""
        count = 0
        for account_connections in self.active_connections.values():
            for websocket in account_connections.values():
                await websocket.send_json(message)
                count += 1
                
        return count
    
    def get_account_connection_count(self, account_id: str) -> int:
        """Get number of active connections for an account"""
        if account_id not in self.active_connections:
            return 0
        return len(self.active_connections[account_id])
    
    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return len(self.connection_to_account)

# Initialize the connection manager
manager = ConnectionManager()
```

### 2.2 WebSocket Endpoints

Implement WebSocket endpoints for real-time data:

```python
from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
import json
import asyncio
from typing import Optional

# JWT authentication for WebSockets
async def get_token_from_query(
    token: Optional[str] = Query(None)
) -> Optional[str]:
    return token

async def get_ws_user(
    token: Optional[str] = Depends(get_token_from_query)
) -> User:
    if not token:
        raise WebSocketDisconnect(code=1008)  # Policy violation
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise WebSocketDisconnect(code=1008)
        
        # Create user from token data
        user = User(username=username)
        return user
    except JWTError:
        raise WebSocketDisconnect(code=1008)

# Main WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user: User = Depends(get_ws_user)):
    connection_id = await manager.connect(websocket, user.username)
    
    try:
        # Send initial data upon connection
        bot_status = bot_controller.get_status()
        await manager.send_personal_message(
            {
                "type": "status_update",
                "data": bot_status
            },
            connection_id
        )
        
        # Main WebSocket message loop
        while True:
            try:
                # Wait for client messages
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                message_type = message.get("type", "")
                
                if message_type == "ping":
                    # Respond to ping with pong
                    await manager.send_personal_message({"type": "pong"}, connection_id)
                    
                elif message_type == "command":
                    # Handle bot commands
                    command = message.get("command", "")
                    params = message.get("params", {})
                    
                    if command == "start":
                        success = bot_controller.start(**params)
                        await manager.send_personal_message(
                            {
                                "type": "command_response",
                                "command": "start",
                                "success": success
                            },
                            connection_id
                        )
                        
                    elif command == "stop":
                        success = bot_controller.stop()
                        await manager.send_personal_message(
                            {
                                "type": "command_response",
                                "command": "stop",
                                "success": success
                            },
                            connection_id
                        )
                        
                    elif command == "update_parameters":
                        success = bot_controller.update_parameters(**params)
                        await manager.send_personal_message(
                            {
                                "type": "command_response",
                                "command": "update_parameters",
                                "success": success
                            },
                            connection_id
                        )
                
                elif message_type == "subscribe":
                    # Handle subscription requests (e.g., market conditions)
                    topics = message.get("topics", [])
                    # Store subscription preferences (implementation omitted)
                    await manager.send_personal_message(
                        {
                            "type": "subscription_confirmed",
                            "topics": topics
                        },
                        connection_id
                    )
                    
            except json.JSONDecodeError:
                # Invalid JSON received
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": "Invalid JSON format"
                    },
                    connection_id
                )
                
    except WebSocketDisconnect:
        manager.disconnect(connection_id)

# Specialized WebSocket for market conditions
@app.websocket("/ws/market_conditions")
async def market_conditions_websocket(
    websocket: WebSocket, 
    user: User = Depends(get_ws_user)
):
    connection_id = await manager.connect(websocket, user.username)
    
    try:
        # Initial market condition data
        market_conditions = await get_current_market_conditions()
        await manager.send_personal_message(
            {
                "type": "market_conditions",
                "data": market_conditions
            },
            connection_id
        )
        
        # Message handling loop
        while True:
            try:
                data = await websocket.receive_text()
                # Process client messages if needed
            except WebSocketDisconnect:
                break
                
    finally:
        manager.disconnect(connection_id)
```

## 3. Real-Time Data Broadcasting

Implement a background task to broadcast trading updates:

```python
import asyncio
from fastapi import BackgroundTasks
import time

# Start background tasks when app starts
@app.on_event("startup")
async def startup_event():
    # Start the background task for updating trading data
    background_tasks.add_task(broadcast_trading_updates)
    # Start the background task for market condition updates
    background_tasks.add_task(broadcast_market_conditions)

# Background task for trading updates
async def broadcast_trading_updates():
    """Background task that broadcasts trading updates to connected clients"""
    last_update = {}
    
    while True:
        try:
            # Get current trading status
            current_status = bot_controller.get_status()
            
            # Calculate and include meaningful differences from last update
            if last_update:
                # Add changes only, to reduce payload size
                changes = {}
                for key, value in current_status.items():
                    if key not in last_update or last_update[key] != value:
                        changes[key] = value
                
                # Include a timestamp
                changes["timestamp"] = time.time()
                
                # Broadcast if there are any changes
                if len(changes) > 1:  # More than just the timestamp
                    await manager.broadcast(
                        {
                            "type": "status_update",
                            "data": changes
                        }
                    )
            else:
                # First update, send full status
                current_status["timestamp"] = time.time()
                await manager.broadcast(
                    {
                        "type": "status_update",
                        "data": current_status
                    }
                )
            
            # Update the last known state
            last_update = current_status
            
        except Exception as e:
            print(f"Error in trading updates broadcast: {e}")
            
        # Sleep for a short period before next update
        # The frequency can be adjusted based on your needs
        await asyncio.sleep(1)  # 1 second update frequency

# Background task for market condition updates
async def broadcast_market_conditions():
    """Background task for broadcasting market condition updates"""
    last_conditions = {}
    
    while True:
        try:
            # Get current market conditions from your market condition detector
            current_conditions = await get_current_market_conditions()
            
            # Check if conditions have changed
            if current_conditions != last_conditions:
                # Broadcast updated conditions to all clients
                await manager.broadcast(
                    {
                        "type": "market_conditions",
                        "data": current_conditions,
                        "timestamp": time.time()
                    }
                )
                
                # Update last known conditions
                last_conditions = current_conditions
                
        except Exception as e:
            print(f"Error in market conditions broadcast: {e}")
            
        # Market conditions typically change less frequently
        await asyncio.sleep(5)  # 5 seconds update frequency
```

## 4. Enhanced API Endpoints for Mobile

Add specialized endpoints for mobile app needs:

```python
# Additional models for mobile app interactions
class MarketConditionResponse(BaseModel):
    market_trend: str  # bullish, bearish, ranging, choppy
    volatility: str  # low, medium, high
    liquidity: str  # low, medium, high
    optimal_strategies: List[str]
    trading_favorable: bool
    confidence_score: float
    timestamp: float

class MultiAssetStatusResponse(BaseModel):
    active_instruments: List[str]
    correlation_groups: Dict[str, List[str]]
    session_status: Dict[str, bool]
    portfolio_allocation: Dict[str, float]
    strategy_mapping: Dict[str, str]

# Mobile-focused endpoints
@app.get("/mobile/dashboard", response_model=dict)
async def get_mobile_dashboard(current_user: User = Depends(get_current_active_user)):
    """
    Aggregated endpoint that returns all data needed for the mobile dashboard
    This reduces the number of API calls needed from the mobile app
    """
    try:
        # Get bot status
        bot_status = bot_controller.get_status()
        
        # Get trading history (last 10 trades)
        trading_history = bot_controller.get_trading_history(limit=10)
        
        # Get market conditions
        market_conditions = await get_current_market_conditions()
        
        # Get multi-asset status
        multi_asset_status = get_multi_asset_status()
        
        # Return all data in a single response
        return {
            "bot_status": bot_status,
            "trading_history": trading_history,
            "market_conditions": market_conditions,
            "multi_asset_status": multi_asset_status,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard data: {str(e)}"
        )

@app.get("/mobile/market_conditions", response_model=MarketConditionResponse)
async def get_market_conditions(current_user: User = Depends(get_current_active_user)):
    """Get current market conditions for all monitored assets"""
    try:
        conditions = await get_current_market_conditions()
        return conditions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get market conditions: {str(e)}"
        )

@app.get("/mobile/multi_asset_status", response_model=MultiAssetStatusResponse)
async def get_multi_asset_status_endpoint(current_user: User = Depends(get_current_active_user)):
    """Get status of multi-asset trading system"""
    try:
        status = get_multi_asset_status()
        return status
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get multi-asset status: {str(e)}"
        )

@app.post("/mobile/toggle_instrument")
async def toggle_instrument(
    instrument: str, 
    active: bool, 
    current_user: User = Depends(get_current_active_user)
):
    """Toggle an instrument active/inactive"""
    try:
        success = bot_controller.toggle_instrument(instrument, active)
        return {"success": success}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle instrument: {str(e)}"
        )

@app.post("/mobile/update_strategy_strength")
async def update_strategy_strength(
    strategy_id: str,
    instrument: str,
    strength: float,
    current_user: User = Depends(get_current_active_user)
):
    """Update the strength of a strategy for a specific instrument"""
    try:
        success = bot_controller.update_strategy_strength(
            strategy_id=strategy_id,
            instrument=instrument,
            strength=strength
        )
        return {"success": success}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update strategy strength: {str(e)}"
        )
```

## 5. Network Discovery for Mobile App

Implement UPnP for automatic port forwarding and network discovery:

```python
import upnpclient
import socket
import netifaces
import threading
import json
from fastapi import APIRouter

discovery_router = APIRouter()

# Get the server's local IP address
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# UPnP port forwarding setup
def setup_upnp_port_forwarding(port=8000):
    try:
        # Discover UPnP devices on the network
        devices = upnpclient.discover()
        
        if not devices:
            print("No UPnP devices found")
            return None
            
        # Get the first IGD (Internet Gateway Device)
        device = devices[0]
        
        # Get the local IP address
        local_ip = get_local_ip()
        
        # Add port mapping
        device.WANIPConn1.AddPortMapping(
            NewRemoteHost='',
            NewExternalPort=port,
            NewProtocol='TCP',
            NewInternalPort=port,
            NewInternalClient=local_ip,
            NewEnabled='1',
            NewPortMappingDescription='ForexTradingBot',
            NewLeaseDuration=0
        )
        
        # Get the external IP address
        external_ip = device.WANIPConn1.GetExternalIPAddress()['NewExternalIPAddress']
        
        print(f"UPnP port forwarding set up: {external_ip}:{port} -> {local_ip}:{port}")
        return {
            "external_ip": external_ip,
            "external_port": port,
            "local_ip": local_ip,
            "local_port": port
        }
    except Exception as e:
        print(f"Error setting up UPnP port forwarding: {e}")
        return None

# Network discovery broadcast
def start_discovery_broadcast(port=8000):
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    # Get the local IP address
    local_ip = get_local_ip()
    
    # Prepare the discovery message
    discovery_info = {
        "service": "forex_trading_bot",
        "api_url": f"http://{local_ip}:{port}",
        "websocket_url": f"ws://{local_ip}:{port}/ws"
    }
    
    discovery_message = json.dumps(discovery_info).encode()
    
    def broadcast_thread():
        while True:
            try:
                # Broadcast to subnet
                for interface in netifaces.interfaces():
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in addrs:
                        for addr in addrs[netifaces.AF_INET]:
                            if 'broadcast' in addr:
                                sock.sendto(discovery_message, (addr['broadcast'], 5555))
            except Exception as e:
                print(f"Error in discovery broadcast: {e}")
            
            # Sleep for 5 seconds between broadcasts
            time.sleep(5)
    
    # Start the broadcast thread
    thread = threading.Thread(target=broadcast_thread, daemon=True)
    thread.start()
    
    return thread

# Discovery endpoint for direct connection
@discovery_router.get("/discovery")
async def get_discovery_info(port: int = 8000):
    """
    Endpoint that returns server connection info for mobile apps
    This is used when the app already knows the server address
    """
    local_ip = get_local_ip()
    
    return {
        "service": "forex_trading_bot",
        "api_url": f"http://{local_ip}:{port}",
        "websocket_url": f"ws://{local_ip}:{port}/ws",
        "version": "1.0.0"
    }

# Include the discovery router in the main app
app.include_router(discovery_router, tags=["discovery"])

# Start discovery services when app starts
@app.on_event("startup")
async def start_discovery_services():
    # Set up UPnP port forwarding
    upnp_info = setup_upnp_port_forwarding(8000)
    
    # Start discovery broadcast
    broadcast_thread = start_discovery_broadcast(8000)
```

## 6. Helper Functions for Market Condition & Multi-Asset Systems

Functions to integrate with your existing systems:

```python
# Helper function to get current market conditions from your detector
async def get_current_market_conditions():
    """Get current market conditions from the MarketConditionDetector"""
    try:
        # Access your market condition detector 
        detector = bot_controller.get_market_condition_detector()
        
        # Get overall market trend analysis
        market_trend = detector.analyze_market_trend()
        
        # Get volatility level
        volatility = detector.measure_volatility()
        
        # Get liquidity assessment
        liquidity = detector.estimate_liquidity()
        
        # Get recommended strategies
        optimal_strategies = detector.recommend_strategies()
        
        # Get trading favorability assessment
        favorable, confidence = detector.is_trading_favorable()
        
        # Return formatted response
        return {
            "market_trend": market_trend,
            "volatility": volatility,
            "liquidity": liquidity,
            "optimal_strategies": optimal_strategies,
            "trading_favorable": favorable,
            "confidence_score": confidence,
            "timestamp": time.time()
        }
    except Exception as e:
        print(f"Error getting market conditions: {e}")
        # Return default values in case of error
        return {
            "market_trend": "unknown",
            "volatility": "unknown",
            "liquidity": "unknown",
            "optimal_strategies": [],
            "trading_favorable": False,
            "confidence_score": 0.0,
            "timestamp": time.time()
        }

# Helper function to get multi-asset trading system status
def get_multi_asset_status():
    """Get status of the multi-asset trading system"""
    try:
        # Access your multi-asset integrator
        integrator = bot_controller.get_multi_asset_integrator()
        
        # Get active instruments
        active_instruments = integrator.get_active_instruments()
        
        # Get correlation groups
        correlation_groups = integrator.get_correlation_groups()
        
        # Get trading session status
        session_status = integrator.get_session_status()
        
        # Get current portfolio allocation
        portfolio_allocation = integrator.get_portfolio_allocation()
        
        # Get strategy mapping for instruments
        strategy_mapping = integrator.get_strategy_instrument_mapping()
        
        # Return formatted response
        return {
            "active_instruments": active_instruments,
            "correlation_groups": correlation_groups,
            "session_status": session_status,
            "portfolio_allocation": portfolio_allocation,
            "strategy_mapping": strategy_mapping
        }
    except Exception as e:
        print(f"Error getting multi-asset status: {e}")
        # Return empty data in case of error
        return {
            "active_instruments": [],
            "correlation_groups": {},
            "session_status": {},
            "portfolio_allocation": {},
            "strategy_mapping": {}
        }
```

## 7. Implementation Steps

1. **Add dependencies to requirements.txt**:
   ```
   fastapi>=0.95.0
   uvicorn>=0.22.0
   websockets>=11.0.3
   python-jose[cryptography]>=3.3.0
   passlib[bcrypt]>=1.7.4
   python-multipart>=0.0.6
   upnpclient>=0.0.8
   netifaces>=0.11.0
   ```

2. **Modify your FastAPI application**:
   - Update your server.py file with the authentication enhancements
   - Add the WebSocket implementation
   - Implement the background tasks for real-time updates
   - Add the mobile-specific endpoints
   - Add network discovery functionality

3. **Integrate with existing components**:
   - Connect the WebSocket broadcasting to your trading bot's event system
   - Ensure your MarketConditionDetector exposes the required methods
   - Make sure your MultiAssetIntegrator has the necessary interface methods

4. **Test the implementation**:
   - Test authentication with MT5 credentials
   - Verify WebSocket connections and data streaming
   - Check that mobile-specific endpoints return proper data
   - Test the network discovery functionality
   - Ensure UPnP port forwarding works correctly

5. **Document the API**:
   - Update your API documentation with the new endpoints
   - Document the WebSocket message formats
   - Provide examples for mobile app developers
