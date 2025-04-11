"""
Execution Engine module for automated forex trading
Handles order execution, position management, and exchange API interactions
"""

import time
import ccxt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime
from loguru import logger
import json
import traceback
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Local imports
from src.risk.risk_manager import RiskManager

class ExecutionEngine:
    """
    Execution engine that handles trade execution, order management,
    and interaction with exchange APIs
    """
    
    def __init__(self, execution_config: dict, risk_manager: RiskManager):
        """
        Initialize the execution engine
        
        Args:
            execution_config: Dictionary with execution parameters
            risk_manager: Risk management system instance
        """
        self.config = execution_config
        self.risk_manager = risk_manager
        self.exchange = None
        self.simulation_mode = execution_config.get('simulation_mode', True)
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # Track orders and executions
        self.pending_orders = {}
        self.active_positions = {}
        self.execution_stats = {
            'orders_placed': 0,
            'orders_filled': 0,
            'orders_canceled': 0,
            'orders_rejected': 0,
            'slippage_total_pips': 0,
            'execution_latency_ms': []
        }
        
        # Initialize exchange
        self._initialize_exchange()
        
        logger.info(f"Execution engine initialized, simulation mode: {self.simulation_mode}")
    
    def _initialize_exchange(self):
        """
        Initialize the connection to the specified exchange
        """
        exchange_id = self.config.get('exchange_id')
        
        if not exchange_id:
            raise ValueError("Exchange ID not specified in configuration")
        
        # Handle simulation mode
        if self.simulation_mode:
            logger.info("Running in simulation mode, no actual trades will be executed")
            return
        
        # Supported exchanges via ccxt
        if exchange_id in ccxt.exchanges:
            api_key = self.config.get('api_key')
            api_secret = self.config.get('api_secret')
            
            if not api_key or not api_secret:
                raise ValueError("API credentials not provided for exchange")
            
            # Initialize the exchange
            exchange_class = getattr(ccxt, exchange_id)
            self.exchange = exchange_class({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': self.config.get('exchange_options', {})
            })
            
            # Load markets
            self.exchange.load_markets()
            logger.info(f"Initialized {exchange_id} exchange with {len(self.exchange.markets)} markets")
            
        # Custom exchange implementations
        elif exchange_id == 'deriv':
            try:
                from src.execution.deriv_api import DerivAPI
                
                app_id = self.config.get('app_id')
                api_token = self.config.get('api_token')
                
                if not app_id or not api_token:
                    raise ValueError("API credentials not provided for Deriv")
                
                self.exchange = DerivAPI(app_id, api_token)
                logger.info("Initialized Deriv exchange")
                
            except ImportError:
                raise ImportError("Deriv API module not found. Please install it first.")
        
        else:
            raise ValueError(f"Unsupported exchange: {exchange_id}")
    
    async def execute_signal(self, signal: Dict) -> Dict:
        """
        Execute a trade signal
        
        Args:
            signal: Trading signal dictionary
            
        Returns:
            Dictionary with execution results
        """
        # Validate signal format
        required_fields = ['pair', 'direction', 'price', 'stop_loss', 'take_profit']
        for field in required_fields:
            if field not in signal:
                logger.error(f"Invalid signal format, missing {field}")
                return {
                    'status': 'error',
                    'message': f"Invalid signal format, missing {field}",
                    'signal': signal
                }
        
        # Extract signal details
        pair = signal['pair']
        direction = signal['direction']
        price = signal['price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        
        # Calculate position size using risk manager
        position_size = self.risk_manager.calculate_position_size(signal)
        
        if position_size <= 0:
            logger.warning(f"Position size too small, skipping trade for {pair}")
            return {
                'status': 'skipped',
                'message': "Position size too small",
                'signal': signal
            }
        
        # Validate trade with risk manager
        if not self.risk_manager.validate_trade(signal, position_size):
            logger.warning(f"Trade validation failed for {pair}")
            return {
                'status': 'rejected',
                'message': "Trade validation failed",
                'signal': signal
            }
        
        # Execute the trade
        execution_start = time.time()
        
        try:
            # Simulate or real execution
            if self.simulation_mode:
                execution_result = self._simulate_execution(pair, direction, price, position_size, stop_loss, take_profit)
            else:
                execution_result = await self._execute_real_trade(pair, direction, price, position_size, stop_loss, take_profit)
            
            # Calculate execution time
            execution_time_ms = (time.time() - execution_start) * 1000
            self.execution_stats['execution_latency_ms'].append(execution_time_ms)
            
            # If successful, register the trade with risk manager
            if execution_result['status'] == 'filled':
                trade_details = {
                    'pair': pair,
                    'direction': direction,
                    'entry_price': execution_result['executed_price'],
                    'position_size': position_size,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_time': datetime.now(),
                    'order_id': execution_result.get('order_id'),
                    'trailing_stop_enabled': signal.get('trailing_stop_enabled', False),
                    'trailing_stop_distance': signal.get('trailing_stop_distance', 20)  # default 20 pips
                }
                
                self.risk_manager.register_trade(trade_details)
                self.active_positions[pair] = trade_details
                
                # Log execution
                logger.info(f"Executed {direction} order for {pair}: {position_size} lots at {execution_result['executed_price']}")
                
                # Calculate slippage
                if 'slippage_pips' in execution_result:
                    self.execution_stats['slippage_total_pips'] += execution_result['slippage_pips']
            
            return {
                **execution_result,
                'position_size': position_size,
                'execution_time_ms': execution_time_ms,
                'signal': signal
            }
            
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            logger.error(traceback.format_exc())
            
            return {
                'status': 'error',
                'message': str(e),
                'signal': signal
            }
    
    def _simulate_execution(self, pair: str, direction: str, price: float, position_size: float, 
                           stop_loss: float, take_profit: float) -> Dict:
        """
        Simulate order execution for testing
        
        Args:
            pair: Currency pair
            direction: 'buy' or 'sell'
            price: Entry price
            position_size: Position size in lots
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Dictionary with execution results
        """
        # Simulate some execution delay
        delay = np.random.normal(0.3, 0.1)  # 300ms average with 100ms standard deviation
        time.sleep(max(0.1, delay))  # At least 100ms
        
        # Simulate slippage
        slippage_pips = np.random.normal(0, 0.5)  # Zero mean, 0.5 pips standard deviation
        
        # Convert to price slippage
        pip_value = 0.01 if 'JPY' in pair else 0.0001
        price_slippage = slippage_pips * pip_value
        
        # Apply slippage
        executed_price = price + (price_slippage if direction == 'buy' else -price_slippage)
        
        # Generate fake order ID
        order_id = f"sim_{int(time.time())}_{np.random.randint(10000, 99999)}"
        
        # Update execution stats
        self.execution_stats['orders_placed'] += 1
        self.execution_stats['orders_filled'] += 1
        
        return {
            'status': 'filled',
            'order_id': order_id,
            'requested_price': price,
            'executed_price': executed_price,
            'slippage_pips': abs(slippage_pips),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _execute_real_trade(self, pair: str, direction: str, price: float, position_size: float, 
                                 stop_loss: float, take_profit: float) -> Dict:
        """
        Execute a real trade on the exchange
        
        Args:
            pair: Currency pair
            direction: 'buy' or 'sell'
            price: Entry price
            position_size: Position size in lots
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Dictionary with execution results
        """
        # Make sure exchange is initialized
        if self.exchange is None:
            raise ValueError("Exchange not initialized or in simulation mode")
        
        exchange_id = self.config.get('exchange_id')
        
        # Execute with CCXT
        if exchange_id in ccxt.exchanges:
            # Prepare order parameters
            side = direction.lower()
            order_type = 'limit'  # or 'market' if immediate execution is preferred
            
            # Convert position size from standard lots to units
            # 1 standard lot = 100,000 units
            amount = position_size * 100000
            
            try:
                # Normalize symbol according to exchange requirements
                symbol = self._normalize_pair(pair)
                
                # Create order
                self.execution_stats['orders_placed'] += 1
                
                # Place the order
                order = self.exchange.create_order(
                    symbol=symbol,
                    type=order_type,
                    side=side,
                    amount=amount,
                    price=price
                )
                
                # Check if we need to place stop loss and take profit
                if self.exchange.has['createOrder']:
                    # Place stop loss
                    if stop_loss:
                        sl_side = 'sell' if direction == 'buy' else 'buy'
                        self.exchange.create_order(
                            symbol=symbol,
                            type='stop-loss',
                            side=sl_side,
                            amount=amount,
                            price=stop_loss,
                            params={'stopPrice': stop_loss, 'reduceOnly': True}
                        )
                    
                    # Place take profit
                    if take_profit:
                        tp_side = 'sell' if direction == 'buy' else 'buy'
                        self.exchange.create_order(
                            symbol=symbol,
                            type='take-profit',
                            side=tp_side,
                            amount=amount,
                            price=take_profit,
                            params={'stopPrice': take_profit, 'reduceOnly': True}
                        )
                
                # Update execution stats
                self.execution_stats['orders_filled'] += 1
                
                # Calculate slippage if applicable
                slippage_pips = 0
                executed_price = price
                if 'price' in order and order['price'] != price:
                    executed_price = order['price']
                    pip_value = 0.01 if 'JPY' in pair else 0.0001
                    price_diff = abs(executed_price - price)
                    slippage_pips = price_diff / pip_value
                    self.execution_stats['slippage_total_pips'] += slippage_pips
                
                return {
                    'status': 'filled',
                    'order_id': order['id'],
                    'requested_price': price,
                    'executed_price': executed_price,
                    'slippage_pips': slippage_pips,
                    'timestamp': datetime.now().isoformat(),
                    'exchange_response': order
                }
                
            except Exception as e:
                self.execution_stats['orders_rejected'] += 1
                raise Exception(f"CCXT order execution error: {str(e)}")
        
        # Execute with Deriv API
        elif exchange_id == 'deriv':
            try:
                # Prepare parameters for Deriv API
                contract_type = 'CALL' if direction == 'buy' else 'PUT'
                
                # Create the trade
                self.execution_stats['orders_placed'] += 1
                
                # Place the order using Deriv API
                order = await self.exchange.buy_contract(
                    symbol=pair.replace('/', ''),
                    contract_type=contract_type,
                    amount=position_size,
                    barrier=take_profit if direction == 'buy' else stop_loss,
                    barrier2=stop_loss if direction == 'buy' else take_profit
                )
                
                # Update execution stats
                self.execution_stats['orders_filled'] += 1
                
                return {
                    'status': 'filled',
                    'order_id': order['contract_id'],
                    'requested_price': price,
                    'executed_price': order.get('entry_spot', price),
                    'timestamp': datetime.now().isoformat(),
                    'exchange_response': order
                }
                
            except Exception as e:
                self.execution_stats['orders_rejected'] += 1
                raise Exception(f"Deriv API order execution error: {str(e)}")
        
        else:
            raise ValueError(f"Unsupported exchange: {exchange_id}")
    
    def _normalize_pair(self, pair: str) -> str:
        """
        Normalize currency pair to exchange format
        
        Args:
            pair: Currency pair in standard format (e.g., 'EUR/USD')
            
        Returns:
            Currency pair in exchange format
        """
        if self.exchange is None:
            return pair
        
        # CCXT exchanges often use different formats
        if pair in self.exchange.markets:
            return pair
        
        # Try common formats
        alternatives = [
            pair.replace('/', ''),  # EURUSD
            pair.replace('/', '_'),  # EUR_USD
            pair.lower().replace('/', ''),  # eurusd
            pair.upper(),  # EUR/USD
        ]
        
        for alt in alternatives:
            if alt in self.exchange.markets:
                return alt
        
        # If no match found, return original and let the exchange handle it
        return pair
    
    async def close_position(self, pair: str, reason: str = 'manual') -> Dict:
        """
        Close an active position
        
        Args:
            pair: Currency pair
            reason: Reason for closing the position
            
        Returns:
            Dictionary with closure results
        """
        if pair not in self.active_positions:
            logger.warning(f"No active position for {pair}")
            return {
                'status': 'error',
                'message': f"No active position for {pair}",
                'pair': pair
            }
        
        position = self.active_positions[pair]
        
        try:
            # Get current market price
            if self.simulation_mode:
                # In simulation, we'd get the price from our market data module
                # For now, just use a slight improvement from the entry
                direction = position['direction']
                entry_price = position['entry_price']
                pip_value = 0.01 if 'JPY' in pair else 0.0001
                price_change = np.random.normal(5, 2) * pip_value  # Average 5 pips profit with 2 pips std dev
                current_price = entry_price + price_change if direction == 'buy' else entry_price - price_change
            else:
                # Get real market price from exchange
                current_price = await self._get_market_price(pair)
            
            # Close the position
            if self.simulation_mode:
                close_result = {
                    'status': 'closed',
                    'pair': pair,
                    'close_price': current_price,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # Execute the closing order (sell if bought, buy if sold)
                close_direction = 'sell' if position['direction'] == 'buy' else 'buy'
                close_order = await self._execute_real_trade(
                    pair=pair,
                    direction=close_direction,
                    price=current_price,
                    position_size=position['position_size'],
                    stop_loss=None,
                    take_profit=None
                )
                close_result = {
                    'status': 'closed',
                    'pair': pair,
                    'close_price': close_order['executed_price'],
                    'order_id': close_order['order_id'],
                    'timestamp': datetime.now().isoformat(),
                    'exchange_response': close_order.get('exchange_response')
                }
            
            # Notify risk manager
            self.risk_manager.close_trade(pair, close_result['close_price'], reason)
            
            # Remove from active positions
            del self.active_positions[pair]
            
            logger.info(f"Closed position for {pair} at {close_result['close_price']}, reason: {reason}")
            
            return close_result
            
        except Exception as e:
            logger.error(f"Error closing position for {pair}: {str(e)}")
            logger.error(traceback.format_exc())
            
            return {
                'status': 'error',
                'message': str(e),
                'pair': pair
            }
    
    async def _get_market_price(self, pair: str) -> float:
        """
        Get current market price for a pair
        
        Args:
            pair: Currency pair
            
        Returns:
            Current market price
        """
        if self.exchange is None:
            raise ValueError("Exchange not initialized")
        
        symbol = self._normalize_pair(pair)
        
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            raise Exception(f"Error fetching market price: {str(e)}")
    
    async def update_positions(self, market_data: Dict[str, pd.DataFrame]):
        """
        Update all active positions with current market data
        Check for stop loss/take profit conditions
        
        Args:
            market_data: Dictionary with market data for pairs
        """
        if not self.active_positions:
            return []
        
        closure_results = []
        positions_to_close = []
        
        # Update each position
        for pair, position in self.active_positions.items():
            # Skip if no market data for this pair
            if pair not in market_data:
                continue
            
            # Get latest price data
            data = market_data[pair]
            if data.empty:
                continue
            
            # Get current price
            current_price = data.iloc[-1]['close']
            
            # Update risk manager with current price
            self.risk_manager.update_trade(pair, current_price)
            
            # Check for stop loss/take profit conditions
            direction = position['direction']
            stop_loss = position['stop_loss']
            take_profit = position['take_profit']
            
            # For buy positions
            if direction == 'buy':
                # Check stop loss
                if current_price <= stop_loss:
                    logger.info(f"Stop loss triggered for {pair} at {current_price}")
                    positions_to_close.append((pair, 'stop_loss'))
                # Check take profit
                elif current_price >= take_profit:
                    logger.info(f"Take profit triggered for {pair} at {current_price}")
                    positions_to_close.append((pair, 'take_profit'))
            
            # For sell positions
            else:
                # Check stop loss
                if current_price >= stop_loss:
                    logger.info(f"Stop loss triggered for {pair} at {current_price}")
                    positions_to_close.append((pair, 'stop_loss'))
                # Check take profit
                elif current_price <= take_profit:
                    logger.info(f"Take profit triggered for {pair} at {current_price}")
                    positions_to_close.append((pair, 'take_profit'))
        
        # Close positions in parallel
        if positions_to_close:
            futures = []
            for pair, reason in positions_to_close:
                # Use ThreadPoolExecutor to close positions concurrently
                future = self.executor.submit(
                    asyncio.run, self.close_position(pair, reason)
                )
                futures.append(future)
            
            # Wait for all closures to complete
            for future in futures:
                try:
                    result = future.result()
                    closure_results.append(result)
                except Exception as e:
                    logger.error(f"Error in position closure task: {str(e)}")
        
        return closure_results
    
    def get_active_positions(self) -> Dict:
        """
        Get all active positions
        
        Returns:
            Dictionary with active positions
        """
        return self.active_positions
    
    def get_execution_stats(self) -> Dict:
        """
        Get execution statistics
        
        Returns:
            Dictionary with execution statistics
        """
        stats = dict(self.execution_stats)
        
        # Calculate average latency
        if stats['execution_latency_ms']:
            stats['avg_execution_latency_ms'] = sum(stats['execution_latency_ms']) / len(stats['execution_latency_ms'])
            stats['max_execution_latency_ms'] = max(stats['execution_latency_ms'])
            stats['min_execution_latency_ms'] = min(stats['execution_latency_ms'])
        
        # Calculate average slippage
        if stats['orders_filled'] > 0:
            stats['avg_slippage_pips'] = stats['slippage_total_pips'] / stats['orders_filled']
        
        return stats
