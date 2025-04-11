"""
MT5 Executor module
Handles order execution and position management for MetaTrader 5
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from loguru import logger

# Import the MetaTrader5 module
try:
    import MetaTrader5 as mt5
except ImportError:
    logger.error("MetaTrader5 package not found. Please install: pip install MetaTrader5")
    mt5 = None

# Local imports
from src.mt5.connector import MT5Connector
from src.risk.risk_manager import RiskManager

class MT5Executor:
    """
    Executor class for MetaTrader 5 trading operations
    """
    
    def __init__(self, config: dict, risk_manager: RiskManager, mt5_connector: Optional[MT5Connector] = None):
        """
        Initialize MT5 executor
        
        Args:
            config: Dictionary with executor configuration
            risk_manager: Risk management system instance
            mt5_connector: Optional existing MT5 connector instance
        """
        self.config = config
        self.risk_manager = risk_manager
        
        # MT5 connector
        if mt5_connector:
            self.connector = mt5_connector
        else:
            mt5_config = config.get('mt5_connector', {})
            self.connector = MT5Connector(mt5_config)
        
        # Execution settings
        self.max_slippage_pips = config.get('max_slippage_pips', 3)
        self.default_deviation = config.get('default_deviation', 20)  # Price deviation in points
        self.async_execution = config.get('async_execution', True)
        self.retry_attempts = config.get('retry_attempts', 3)
        self.retry_delay = config.get('retry_delay', 1)  # seconds
        
        # Order tracking
        self.pending_orders = {}
        self.active_positions = {}
        self.order_history = []
        
        # Execution statistics
        self.execution_stats = {
            'orders_placed': 0,
            'orders_filled': 0,
            'orders_canceled': 0,
            'orders_rejected': 0,
            'slippage_total_pips': 0,
            'execution_latency_ms': []
        }
        
        logger.info("MT5 executor initialized")
    
    def market_order(self, symbol: str, order_type: str, volume: float, 
                   sl_points: Optional[int] = None, tp_points: Optional[int] = None,
                   comment: str = "", deviation: Optional[int] = None) -> Dict:
        """
        Place a market order
        
        Args:
            symbol: Trading symbol
            order_type: 'buy' or 'sell'
            volume: Trade volume in lots
            sl_points: Stop loss in points (optional)
            tp_points: Take profit in points (optional)
            comment: Order comment
            deviation: Maximum price deviation in points
            
        Returns:
            Dictionary with order result
        """
        if not self.connector.connected:
            if not self.connector.connect():
                logger.error("Failed to connect to MT5, cannot place market order")
                return {"success": False, "error": "Not connected to MT5"}
        
        # Validate order type
        mt5_order_type = mt5.ORDER_TYPE_BUY if order_type.lower() == 'buy' else mt5.ORDER_TYPE_SELL
        if order_type.lower() not in ['buy', 'sell']:
            logger.error(f"Invalid order type: {order_type}")
            return {"success": False, "error": f"Invalid order type: {order_type}"}
        
        # Get current market price
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.error(f"Symbol {symbol} not found")
            return {"success": False, "error": f"Symbol {symbol} not found"}
        
        symbol_info_dict = symbol_info._asdict()
        
        # Get price based on order type
        if mt5_order_type == mt5.ORDER_TYPE_BUY:
            price = symbol_info_dict["ask"]
        else:
            price = symbol_info_dict["bid"]
        
        # Set deviation
        if deviation is None:
            deviation = self.default_deviation
        
        # Calculate stop loss and take profit levels
        sl = 0
        tp = 0
        
        if sl_points is not None and sl_points > 0:
            if mt5_order_type == mt5.ORDER_TYPE_BUY:
                sl = price - sl_points * symbol_info_dict["point"]
            else:
                sl = price + sl_points * symbol_info_dict["point"]
        
        if tp_points is not None and tp_points > 0:
            if mt5_order_type == mt5.ORDER_TYPE_BUY:
                tp = price + tp_points * symbol_info_dict["point"]
            else:
                tp = price - tp_points * symbol_info_dict["point"]
        
        # Prepare trade request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5_order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": deviation,
            "magic": 123456,  # Magic number to identify bot orders
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK
        }
        
        # Send the order
        start_time = time.time()
        result = mt5.order_send(request)
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Update execution stats
        self.execution_stats["execution_latency_ms"].append(execution_time_ms)
        
        # Process result
        if result is None:
            error_code = mt5.last_error()
            error_message = f"Error sending order: {error_code}"
            logger.error(error_message)
            self.execution_stats["orders_rejected"] += 1
            return {"success": False, "error": error_message}
        
        result_dict = result._asdict()
        
        if result_dict["retcode"] != mt5.TRADE_RETCODE_DONE:
            error_message = f"Order failed with retcode {result_dict['retcode']}"
            logger.error(error_message)
            self.execution_stats["orders_rejected"] += 1
            return {"success": False, "error": error_message, "retcode": result_dict["retcode"]}
        
        # Order successful
        logger.info(f"Market order placed successfully: {symbol} {order_type} {volume} lots")
        self.execution_stats["orders_placed"] += 1
        self.execution_stats["orders_filled"] += 1
        
        # Calculate slippage
        if "price" in result_dict and abs(result_dict["price"] - price) > 0:
            slippage = abs(result_dict["price"] - price) / symbol_info_dict["point"]
            self.execution_stats["slippage_total_pips"] += slippage
        
        # Add to active positions
        position_info = self.get_position(symbol)
        if position_info:
            self.active_positions[symbol] = position_info
        
        return {
            "success": True, 
            "order_id": result_dict["order"],
            "volume": volume,
            "price": result_dict["price"],
            "symbol": symbol,
            "type": order_type,
            "sl": sl,
            "tp": tp,
            "execution_time_ms": execution_time_ms
        }
    
    def limit_order(self, symbol: str, order_type: str, volume: float, price: float,
                  sl_points: Optional[int] = None, tp_points: Optional[int] = None,
                  comment: str = "", expiration: Optional[datetime] = None) -> Dict:
        """
        Place a limit order
        
        Args:
            symbol: Trading symbol
            order_type: 'buy_limit' or 'sell_limit'
            volume: Trade volume in lots
            price: Order price
            sl_points: Stop loss in points (optional)
            tp_points: Take profit in points (optional)
            comment: Order comment
            expiration: Order expiration time (optional)
            
        Returns:
            Dictionary with order result
        """
        if not self.connector.connected:
            if not self.connector.connect():
                logger.error("Failed to connect to MT5, cannot place limit order")
                return {"success": False, "error": "Not connected to MT5"}
        
        # Validate order type
        if order_type.lower() == 'buy_limit':
            mt5_order_type = mt5.ORDER_TYPE_BUY_LIMIT
        elif order_type.lower() == 'sell_limit':
            mt5_order_type = mt5.ORDER_TYPE_SELL_LIMIT
        else:
            logger.error(f"Invalid order type: {order_type}")
            return {"success": False, "error": f"Invalid order type: {order_type}"}
        
        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.error(f"Symbol {symbol} not found")
            return {"success": False, "error": f"Symbol {symbol} not found"}
        
        symbol_info_dict = symbol_info._asdict()
        
        # Calculate stop loss and take profit levels
        sl = 0
        tp = 0
        
        if sl_points is not None and sl_points > 0:
            if mt5_order_type == mt5.ORDER_TYPE_BUY_LIMIT:
                sl = price - sl_points * symbol_info_dict["point"]
            else:
                sl = price + sl_points * symbol_info_dict["point"]
        
        if tp_points is not None and tp_points > 0:
            if mt5_order_type == mt5.ORDER_TYPE_BUY_LIMIT:
                tp = price + tp_points * symbol_info_dict["point"]
            else:
                tp = price - tp_points * symbol_info_dict["point"]
        
        # Set expiration
        type_time = mt5.ORDER_TIME_GTC
        expiration_time = 0
        
        if expiration:
            type_time = mt5.ORDER_TIME_SPECIFIED
            expiration_time = int(expiration.timestamp())
        
        # Prepare trade request
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": volume,
            "type": mt5_order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": self.default_deviation,
            "magic": 123456,  # Magic number to identify bot orders
            "comment": comment,
            "type_time": type_time,
            "expiration": expiration_time,
            "type_filling": mt5.ORDER_FILLING_FOK
        }
        
        # Send the order
        start_time = time.time()
        result = mt5.order_send(request)
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Update execution stats
        self.execution_stats["execution_latency_ms"].append(execution_time_ms)
        
        # Process result
        if result is None:
            error_code = mt5.last_error()
            error_message = f"Error sending limit order: {error_code}"
            logger.error(error_message)
            self.execution_stats["orders_rejected"] += 1
            return {"success": False, "error": error_message}
        
        result_dict = result._asdict()
        
        if result_dict["retcode"] != mt5.TRADE_RETCODE_DONE:
            error_message = f"Limit order failed with retcode {result_dict['retcode']}"
            logger.error(error_message)
            self.execution_stats["orders_rejected"] += 1
            return {"success": False, "error": error_message, "retcode": result_dict["retcode"]}
        
        # Order successful
        logger.info(f"Limit order placed successfully: {symbol} {order_type} {volume} lots at {price}")
        self.execution_stats["orders_placed"] += 1
        
        # Add to pending orders
        self.pending_orders[result_dict["order"]] = {
            "order_id": result_dict["order"],
            "symbol": symbol,
            "type": order_type,
            "volume": volume,
            "price": price,
            "sl": sl,
            "tp": tp,
            "time": datetime.now().isoformat()
        }
        
        return {
            "success": True, 
            "order_id": result_dict["order"],
            "volume": volume,
            "price": price,
            "symbol": symbol,
            "type": order_type,
            "sl": sl,
            "tp": tp,
            "execution_time_ms": execution_time_ms
        }
    
    def close_position(self, symbol: str, volume: Optional[float] = None, comment: str = "") -> Dict:
        """
        Close an open position
        
        Args:
            symbol: Trading symbol
            volume: Volume to close (None for full position)
            comment: Order comment
            
        Returns:
            Dictionary with close result
        """
        if not self.connector.connected:
            if not self.connector.connect():
                logger.error("Failed to connect to MT5, cannot close position")
                return {"success": False, "error": "Not connected to MT5"}
        
        # Get position info
        position = mt5.positions_get(symbol=symbol)
        if position is None or len(position) == 0:
            logger.warning(f"No open position found for {symbol}")
            return {"success": False, "error": f"No open position found for {symbol}"}
        
        position_dict = position[0]._asdict()
        
        # Determine volume to close
        close_volume = position_dict["volume"] if volume is None else min(volume, position_dict["volume"])
        
        # Determine order type (opposite of position)
        if position_dict["type"] == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(symbol).ask
        
        # Prepare close request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": close_volume,
            "type": order_type,
            "position": position_dict["ticket"],
            "price": price,
            "deviation": self.default_deviation,
            "magic": 123456,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK
        }
        
        # Send the order
        start_time = time.time()
        result = mt5.order_send(request)
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Process result
        if result is None:
            error_code = mt5.last_error()
            error_message = f"Error closing position: {error_code}"
            logger.error(error_message)
            return {"success": False, "error": error_message}
        
        result_dict = result._asdict()
        
        if result_dict["retcode"] != mt5.TRADE_RETCODE_DONE:
            error_message = f"Position close failed with retcode {result_dict['retcode']}"
            logger.error(error_message)
            return {"success": False, "error": error_message, "retcode": result_dict["retcode"]}
        
        # Close successful
        logger.info(f"Position closed successfully: {symbol} {close_volume} lots")
        
        # Update active positions
        if volume is None or abs(close_volume - position_dict["volume"]) < 0.0001:
            if symbol in self.active_positions:
                del self.active_positions[symbol]
        else:
            # Position partially closed, update
            position_info = self.get_position(symbol)
            if position_info:
                self.active_positions[symbol] = position_info
        
        return {
            "success": True, 
            "order_id": result_dict["order"],
            "volume": close_volume,
            "price": result_dict["price"],
            "symbol": symbol,
            "execution_time_ms": execution_time_ms
        }
    
    def modify_position(self, symbol: str, sl: Optional[float] = None, 
                      tp: Optional[float] = None) -> Dict:
        """
        Modify stop loss and take profit for an open position
        
        Args:
            symbol: Trading symbol
            sl: New stop loss price (None to keep current)
            tp: New take profit price (None to keep current)
            
        Returns:
            Dictionary with modification result
        """
        if not self.connector.connected:
            if not self.connector.connect():
                logger.error("Failed to connect to MT5, cannot modify position")
                return {"success": False, "error": "Not connected to MT5"}
        
        # Get position info
        position = mt5.positions_get(symbol=symbol)
        if position is None or len(position) == 0:
            logger.warning(f"No open position found for {symbol}")
            return {"success": False, "error": f"No open position found for {symbol}"}
        
        position_dict = position[0]._asdict()
        
        # Use current values if not specified
        if sl is None:
            sl = position_dict["sl"]
        if tp is None:
            tp = position_dict["tp"]
        
        # Prepare modification request
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "sl": sl,
            "tp": tp,
            "position": position_dict["ticket"]
        }
        
        # Send the modification
        result = mt5.order_send(request)
        
        # Process result
        if result is None:
            error_code = mt5.last_error()
            error_message = f"Error modifying position: {error_code}"
            logger.error(error_message)
            return {"success": False, "error": error_message}
        
        result_dict = result._asdict()
        
        if result_dict["retcode"] != mt5.TRADE_RETCODE_DONE:
            error_message = f"Position modification failed with retcode {result_dict['retcode']}"
            logger.error(error_message)
            return {"success": False, "error": error_message, "retcode": result_dict["retcode"]}
        
        # Modification successful
        logger.info(f"Position modified successfully: {symbol} SL={sl} TP={tp}")
        
        # Update active positions
        position_info = self.get_position(symbol)
        if position_info:
            self.active_positions[symbol] = position_info
        
        return {
            "success": True, 
            "symbol": symbol,
            "sl": sl,
            "tp": tp
        }
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get information about an open position
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with position information or None if no position
        """
        if not self.connector.connected:
            if not self.connector.connect():
                logger.error("Failed to connect to MT5, cannot get position")
                return None
        
        # Get position info
        position = mt5.positions_get(symbol=symbol)
        if position is None or len(position) == 0:
            return None
        
        # Convert to dict
        position_dict = position[0]._asdict()
        
        # Get symbol info for point value
        symbol_info = mt5.symbol_info(symbol)
        point = symbol_info.point if symbol_info else 0.0001
        
        # Format position info
        return {
            "ticket": position_dict["ticket"],
            "symbol": position_dict["symbol"],
            "volume": position_dict["volume"],
            "type": "buy" if position_dict["type"] == mt5.POSITION_TYPE_BUY else "sell",
            "open_price": position_dict["price_open"],
            "current_price": position_dict["price_current"],
            "sl": position_dict["sl"],
            "tp": position_dict["tp"],
            "profit": position_dict["profit"],
            "profit_pips": round((position_dict["price_current"] - position_dict["price_open"]) / point, 1)
                          if position_dict["type"] == mt5.POSITION_TYPE_BUY
                          else round((position_dict["price_open"] - position_dict["price_current"]) / point, 1),
            "swap": position_dict["swap"],
            "open_time": datetime.fromtimestamp(position_dict["time"]).isoformat()
        }
    
    def get_all_positions(self) -> List[Dict]:
        """
        Get all open positions
        
        Returns:
            List of dictionaries with position information
        """
        if not self.connector.connected:
            if not self.connector.connect():
                logger.error("Failed to connect to MT5, cannot get positions")
                return []
        
        # Get all positions
        positions = mt5.positions_get()
        if positions is None or len(positions) == 0:
            return []
        
        result = []
        
        for pos in positions:
            # Convert to dict
            position_dict = pos._asdict()
            symbol = position_dict["symbol"]
            
            # Get symbol info for point value
            symbol_info = mt5.symbol_info(symbol)
            point = symbol_info.point if symbol_info else 0.0001
            
            # Format position info
            position_info = {
                "ticket": position_dict["ticket"],
                "symbol": symbol,
                "volume": position_dict["volume"],
                "type": "buy" if position_dict["type"] == mt5.POSITION_TYPE_BUY else "sell",
                "open_price": position_dict["price_open"],
                "current_price": position_dict["price_current"],
                "sl": position_dict["sl"],
                "tp": position_dict["tp"],
                "profit": position_dict["profit"],
                "profit_pips": round((position_dict["price_current"] - position_dict["price_open"]) / point, 1)
                              if position_dict["type"] == mt5.POSITION_TYPE_BUY
                              else round((position_dict["price_open"] - position_dict["price_current"]) / point, 1),
                "swap": position_dict["swap"],
                "open_time": datetime.fromtimestamp(position_dict["time"]).isoformat()
            }
            
            result.append(position_info)
            
            # Update active positions cache
            self.active_positions[symbol] = position_info
        
        return result
    
    def get_account_info(self) -> Dict:
        """
        Get trading account information
        
        Returns:
            Dictionary with account details
        """
        return self.connector.get_account_info()
    
    def get_execution_stats(self) -> Dict:
        """
        Get execution statistics
        
        Returns:
            Dictionary with execution stats
        """
        stats = self.execution_stats.copy()
        
        # Calculate average latency
        latencies = stats.get("execution_latency_ms", [])
        if latencies:
            stats["avg_execution_latency_ms"] = sum(latencies) / len(latencies)
        
        return stats
