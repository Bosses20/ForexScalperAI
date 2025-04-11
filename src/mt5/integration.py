"""
MT5 Integration module
Connects the MT5 framework with the main trading bot system
"""

import os
import json
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any
from loguru import logger

# Local imports
from src.mt5.controller import MT5Controller
from src.bot_controller import BotController
from src.api.api_server import APIServer
from src.risk.risk_manager import RiskManager

class MT5Integration:
    """
    Integration class that connects the MT5 framework with the main bot system.
    Acts as a bridge between the MT5-specific components and the rest of the system.
    """
    
    def __init__(self, bot_controller: BotController, config_path: str = "config/mt5_config.yaml"):
        """
        Initialize the MT5 integration
        
        Args:
            bot_controller: Main bot controller instance
            config_path: Path to MT5 configuration file
        """
        self.bot_controller = bot_controller
        self.config_path = config_path
        self.mt5_controller = None
        self.sync_interval = 5  # seconds
        self.sync_thread = None
        self.stop_event = threading.Event()
        self.is_running = False
        self.api_routes_registered = False
        
        # State tracking
        self.last_sync_time = None
        self.last_status = {}
        
        logger.info("MT5 integration initialized")
    
    def initialize(self) -> bool:
        """
        Initialize the MT5 integration
        
        Returns:
            True if initialized successfully
        """
        try:
            # Initialize MT5 controller
            self.mt5_controller = MT5Controller(self.config_path)
            
            if not self.mt5_controller.initialize():
                logger.error("Failed to initialize MT5 controller")
                return False
            
            # Register API endpoints
            if hasattr(self.bot_controller, 'api_server') and isinstance(self.bot_controller.api_server, APIServer):
                self._register_api_routes(self.bot_controller.api_server)
            
            logger.info("MT5 integration initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing MT5 integration: {str(e)}")
            return False
    
    def _register_api_routes(self, api_server: APIServer) -> None:
        """
        Register MT5-specific API routes
        
        Args:
            api_server: API server instance
        """
        if self.api_routes_registered:
            return
            
        try:
            # Get FastAPI app
            app = api_server.app
            
            # Import FastAPI dependencies
            from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
            
            # Create router
            mt5_router = APIRouter(
                prefix="/mt5",
                tags=["mt5"],
                responses={404: {"description": "Not found"}},
            )
            
            # Define API endpoints
            @mt5_router.get("/status")
            async def get_mt5_status():
                """Get MT5 status"""
                if not self.mt5_controller:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MT5 controller not initialized"
                    )
                
                return self.mt5_controller.get_status()
            
            @mt5_router.post("/start")
            async def start_mt5():
                """Start MT5 trading"""
                if not self.mt5_controller:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MT5 controller not initialized"
                    )
                
                success = self.start()
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to start MT5 trading"
                    )
                
                return {"status": "started"}
            
            @mt5_router.post("/stop")
            async def stop_mt5():
                """Stop MT5 trading"""
                if not self.mt5_controller:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MT5 controller not initialized"
                    )
                
                success = self.stop()
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to stop MT5 trading"
                    )
                
                return {"status": "stopped"}
            
            @mt5_router.post("/pause")
            async def pause_mt5():
                """Pause MT5 trading"""
                if not self.mt5_controller:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MT5 controller not initialized"
                    )
                
                success = self.mt5_controller.pause()
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to pause MT5 trading"
                    )
                
                return {"status": "paused"}
            
            @mt5_router.post("/resume")
            async def resume_mt5():
                """Resume MT5 trading"""
                if not self.mt5_controller:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MT5 controller not initialized"
                    )
                
                success = self.mt5_controller.resume()
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to resume MT5 trading"
                    )
                
                return {"status": "resumed"}
            
            @mt5_router.get("/positions")
            async def get_positions():
                """Get open positions"""
                if not self.mt5_controller:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MT5 controller not initialized"
                    )
                
                if not self.mt5_controller.executor:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MT5 executor not initialized"
                    )
                
                positions = self.mt5_controller.executor.get_all_positions()
                return {"positions": positions}
            
            @mt5_router.get("/account")
            async def get_account_info():
                """Get account information"""
                if not self.mt5_controller:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MT5 controller not initialized"
                    )
                
                if not self.mt5_controller.connector:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MT5 connector not initialized"
                    )
                
                account_info = self.mt5_controller.connector.get_account_info()
                return account_info
            
            @mt5_router.get("/strategies")
            async def get_strategies():
                """Get strategy information"""
                if not self.mt5_controller:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MT5 controller not initialized"
                    )
                
                strategies = {
                    name: {
                        "name": strategy.name,
                        "timeframe": strategy.timeframe,
                        "symbols": strategy.symbols,
                        "enabled": True,
                        "performance": strategy.performance
                    }
                    for name, strategy in self.mt5_controller.strategies.items()
                }
                
                return {"strategies": strategies}
            
            @mt5_router.get("/symbols")
            async def get_symbols():
                """Get available symbols"""
                if not self.mt5_controller:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MT5 controller not initialized"
                    )
                
                if not self.mt5_controller.connector:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MT5 connector not initialized"
                    )
                
                symbols = self.mt5_controller.connector.get_symbols()
                return {"symbols": symbols}
            
            @mt5_router.post("/close_position/{symbol}")
            async def close_position(symbol: str):
                """Close position for a symbol"""
                if not self.mt5_controller:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MT5 controller not initialized"
                    )
                
                if not self.mt5_controller.executor:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MT5 executor not initialized"
                    )
                
                result = self.mt5_controller.executor.close_position(symbol)
                if not result.get('success', False):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to close position: {result.get('error', 'Unknown error')}"
                    )
                
                return result
            
            # Register router with app
            app.include_router(mt5_router)
            self.api_routes_registered = True
            
            logger.info("MT5 API routes registered")
            
        except Exception as e:
            logger.error(f"Error registering MT5 API routes: {str(e)}")
    
    def start(self) -> bool:
        """
        Start the MT5 integration
        
        Returns:
            True if started successfully
        """
        if self.is_running:
            logger.warning("MT5 integration is already running")
            return True
        
        if not self.mt5_controller:
            logger.error("MT5 controller not initialized")
            return False
        
        # Start MT5 controller
        if not self.mt5_controller.start():
            logger.error("Failed to start MT5 controller")
            return False
        
        # Start sync thread
        self.stop_event.clear()
        self.sync_thread = threading.Thread(target=self._sync_loop)
        self.sync_thread.daemon = True
        self.sync_thread.start()
        
        self.is_running = True
        logger.info("MT5 integration started")
        return True
    
    def stop(self) -> bool:
        """
        Stop the MT5 integration
        
        Returns:
            True if stopped successfully
        """
        if not self.is_running:
            logger.warning("MT5 integration is not running")
            return True
        
        # Stop sync thread
        self.stop_event.set()
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=10)
        
        # Stop MT5 controller
        if self.mt5_controller:
            self.mt5_controller.stop()
        
        self.is_running = False
        logger.info("MT5 integration stopped")
        return True
    
    def _sync_loop(self) -> None:
        """Synchronization loop between MT5 and main system"""
        logger.info("Starting MT5 sync loop")
        
        while not self.stop_event.is_set():
            try:
                # Synchronize data between MT5 and main system
                self._sync_data()
                
                # Update last sync time
                self.last_sync_time = datetime.now()
                
                # Sleep for sync interval
                for _ in range(self.sync_interval):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in MT5 sync loop: {str(e)}")
                time.sleep(5)  # Wait before retrying
    
    def _sync_data(self) -> None:
        """Synchronize data between MT5 and main system"""
        if not self.mt5_controller:
            return
        
        # Get MT5 status
        mt5_status = self.mt5_controller.get_status()
        
        # Update last status
        self.last_status = mt5_status
        
        # Sync active trades with main system
        if hasattr(self.bot_controller, 'active_trades'):
            mt5_active_trades = mt5_status.get('active_trades', [])
            # Convert to format expected by main system
            formatted_trades = []
            for trade in mt5_active_trades:
                formatted_trade = {
                    'id': trade.get('order_id', 0),
                    'symbol': trade.get('symbol', ''),
                    'type': trade.get('direction', ''),
                    'volume': trade.get('volume', 0),
                    'open_price': trade.get('entry_price', 0),
                    'open_time': trade.get('open_time', ''),
                    'sl': trade.get('stop_loss', 0),
                    'tp': trade.get('take_profit', 0),
                    'profit': 0,  # Will be updated from positions
                    'platform': 'mt5'
                }
                formatted_trades.append(formatted_trade)
            
            # Get current positions for profit information
            if self.mt5_controller.executor:
                positions = self.mt5_controller.executor.get_all_positions()
                for position in positions:
                    for trade in formatted_trades:
                        if trade['symbol'] == position['symbol']:
                            trade['profit'] = position.get('profit', 0)
            
            # Update main system's active trades
            self.bot_controller.active_trades = {
                trade['id']: trade for trade in formatted_trades
            }
        
        # Sync account information
        if hasattr(self.bot_controller, 'account_info'):
            account_info = self.mt5_controller.connector.get_account_info() if self.mt5_controller.connector else {}
            self.bot_controller.account_info = {
                'balance': account_info.get('balance', 0),
                'equity': account_info.get('equity', 0),
                'margin': account_info.get('margin', 0),
                'free_margin': account_info.get('margin_free', 0),
                'margin_level': account_info.get('margin_level', 0),
                'profit': self.mt5_controller.session_stats.get('total_profit', 0)
            }
    
    def get_status(self) -> Dict:
        """
        Get current integration status
        
        Returns:
            Dictionary with status information
        """
        return {
            'running': self.is_running,
            'mt5_controller_status': self.mt5_controller.get_status() if self.mt5_controller else {},
            'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'api_routes_registered': self.api_routes_registered
        }
