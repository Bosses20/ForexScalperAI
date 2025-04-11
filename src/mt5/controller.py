"""
MT5 Controller module
Coordinates all MetaTrader 5 trading operations, integrating data feed, strategy execution,
and risk management components for the forex scalping bot.
"""

import time
import asyncio
import threading
import os
import yaml
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from loguru import logger
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# Local imports
from src.mt5.connector import MT5Connector
from src.mt5.data_feed import MT5DataFeed
from src.mt5.executor import MT5Executor
from src.mt5.strategies import create_strategy, ScalpingStrategy
from src.risk.risk_manager import RiskManager

class MT5Controller:
    """
    Master controller for MetaTrader 5 trading operations.
    Coordinates all components of the MT5 integration framework.
    """
    
    def __init__(self, config_path: str = "config/mt5_config.yaml"):
        """
        Initialize the MT5 controller
        
        Args:
            config_path: Path to MT5-specific configuration file
        """
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        # Core components
        self.connector = None
        self.data_feed = None
        self.executor = None
        self.risk_manager = None
        self.strategies = {}
        
        # Control flags
        self.running = False
        self.paused = False
        self.stop_event = threading.Event()
        
        # Session data
        self.trading_symbols = self.config.get('trading', {}).get('symbols', [])
        self.trading_timeframes = self.config.get('trading', {}).get('timeframes', ['M1', 'M5', 'M15'])
        self.strategy_timeframe = self.config.get('trading', {}).get('strategy_timeframe', 'M5')
        self.update_interval = self.config.get('trading', {}).get('update_interval', 1)  # seconds
        self.trade_session_hours = self.config.get('trading', {}).get('trade_session_hours', None)
        
        # State tracking
        self.last_data_update = {}
        self.last_signal_check = {}
        self.active_trades = {}
        self.pending_signals = {}
        
        # Performance tracking
        self.session_stats = {
            'start_time': None,
            'end_time': None,
            'trades_executed': 0,
            'profitable_trades': 0,
            'lost_trades': 0,
            'total_profit': 0,
            'max_drawdown': 0,
            'win_rate': 0,
            'current_drawdown': 0,
            'peak_balance': 0
        }
        
        # Initialize executor
        self.executor_thread = None
        
        logger.info("MT5 controller initialized")
    
    def _load_config(self, config_path: str) -> Dict:
        """
        Load configuration from YAML file
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Dictionary with configuration
        """
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as file:
                    config = yaml.safe_load(file)
                logger.info(f"Loaded configuration from {config_path}")
                return config
            else:
                logger.warning(f"Configuration file {config_path} not found, using default settings")
                # Return default configuration
                return {
                    'mt5': {
                        'login': 0,
                        'password': '',
                        'server': '',
                        'path': '',
                        'max_retries': 3,
                        'retry_delay': 5
                    },
                    'data_feed': {
                        'max_bars': 1000,
                        'update_interval': 1,
                        'store_history': True,
                        'include_indicators': True
                    },
                    'trading': {
                        'symbols': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD'],
                        'timeframes': ['M1', 'M5', 'M15'],
                        'strategy_timeframe': 'M5',
                        'update_interval': 1,
                        'trade_session_hours': [[0, 24]]  # 24/7 trading
                    },
                    'risk': {
                        'max_risk_per_trade': 0.01,  # 1% per trade
                        'max_daily_risk': 0.05,      # 5% per day
                        'max_positions': 5,
                        'max_positions_per_symbol': 1,
                        'max_daily_loss': 0.05       # 5% max daily loss
                    },
                    'strategies': {
                        'moving_average_cross': {
                            'enabled': True,
                            'fast_ma_period': 5,
                            'slow_ma_period': 20,
                            'ma_type': 'ema',
                            'take_profit_pips': 10,
                            'stop_loss_pips': 5
                        },
                        'bollinger_breakout': {
                            'enabled': True,
                            'bb_period': 20,
                            'bb_std': 2.0,
                            'rsi_period': 14,
                            'rsi_overbought': 70,
                            'rsi_oversold': 30,
                            'use_rsi_filter': True,
                            'take_profit_pips': 15,
                            'stop_loss_pips': 8
                        }
                    },
                    'logging': {
                        'level': 'INFO',
                        'file': 'logs/mt5_controller.log',
                        'max_size': '10 MB',
                        'backup_count': 5
                    }
                }
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            return {}
    
    def _setup_logging(self) -> None:
        """Configure logging based on settings"""
        log_config = self.config.get('logging', {})
        log_level = log_config.get('level', 'INFO')
        log_file = log_config.get('file', 'logs/mt5_controller.log')
        max_size = log_config.get('max_size', '10 MB')
        backup_count = log_config.get('backup_count', 5)
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Configure logger
        logger.add(
            log_file,
            level=log_level,
            rotation=max_size,
            compression="zip",
            retention=backup_count,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
    
    def initialize(self) -> bool:
        """
        Initialize all MT5 components
        
        Returns:
            True if initialized successfully
        """
        try:
            # Initialize risk manager
            risk_config = self.config.get('risk', {})
            self.risk_manager = RiskManager(risk_config)
            logger.info("Risk manager initialized")
            
            # Initialize MT5 connector
            mt5_config = self.config.get('mt5', {})
            self.connector = MT5Connector(mt5_config)
            if not self.connector.connect():
                logger.error("Failed to connect to MT5, initialization failed")
                return False
            logger.info("MT5 connector initialized and connected")
            
            # Initialize data feed
            data_feed_config = self.config.get('data_feed', {})
            data_feed_config['trading_pairs'] = self.trading_symbols
            data_feed_config['timeframes'] = self.trading_timeframes
            self.data_feed = MT5DataFeed(data_feed_config, self.connector)
            if not self.data_feed.initialize():
                logger.error("Failed to initialize data feed")
                return False
            logger.info("MT5 data feed initialized")
            
            # Initialize executor
            executor_config = self.config.get('executor', {})
            self.executor = MT5Executor(executor_config, self.risk_manager, self.connector)
            logger.info("MT5 executor initialized")
            
            # Initialize strategies
            self._initialize_strategies()
            
            # Initialize session stats
            self.session_stats['start_time'] = datetime.now().isoformat()
            self.session_stats['peak_balance'] = self._get_account_balance()
            
            # Initial data update
            self._update_market_data()
            
            logger.info("MT5 controller initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during initialization: {str(e)}")
            return False
    
    def _initialize_strategies(self) -> None:
        """Initialize trading strategies based on configuration"""
        strategy_configs = self.config.get('strategies', {})
        
        for strategy_name, strategy_config in strategy_configs.items():
            if strategy_config.get('enabled', True):
                # Add common configuration
                full_config = strategy_config.copy()
                full_config['symbols'] = self.trading_symbols
                full_config['timeframe'] = self.strategy_timeframe
                full_config['name'] = strategy_name
                
                # Create strategy instance
                try:
                    strategy = create_strategy(strategy_name, full_config)
                    if strategy.initialize():
                        self.strategies[strategy_name] = strategy
                        logger.info(f"Strategy initialized: {strategy_name}")
                    else:
                        logger.error(f"Failed to initialize strategy: {strategy_name}")
                except Exception as e:
                    logger.error(f"Error creating strategy {strategy_name}: {str(e)}")
    
    def start(self) -> bool:
        """
        Start the trading controller
        
        Returns:
            True if started successfully
        """
        if self.running:
            logger.warning("Controller is already running")
            return True
        
        if not self.connector or not self.connector.connected:
            if not self.initialize():
                logger.error("Failed to initialize before starting")
                return False
        
        # Reset stop event
        self.stop_event.clear()
        self.running = True
        self.paused = False
        
        # Start the main execution thread
        self.executor_thread = threading.Thread(target=self._execution_loop)
        self.executor_thread.daemon = True
        self.executor_thread.start()
        
        logger.info("MT5 controller started")
        return True
    
    def stop(self) -> bool:
        """
        Stop the trading controller
        
        Returns:
            True if stopped successfully
        """
        if not self.running:
            logger.warning("Controller is not running")
            return True
        
        # Signal the execution thread to stop
        self.stop_event.set()
        self.running = False
        
        # Wait for execution thread to finish
        if self.executor_thread and self.executor_thread.is_alive():
            self.executor_thread.join(timeout=10)
        
        # Update session stats
        self.session_stats['end_time'] = datetime.now().isoformat()
        if self.session_stats['trades_executed'] > 0:
            self.session_stats['win_rate'] = (
                self.session_stats['profitable_trades'] / self.session_stats['trades_executed']
            )
        
        # Disconnect from MT5
        if self.connector:
            self.connector.disconnect()
        
        logger.info("MT5 controller stopped")
        return True
    
    def pause(self) -> bool:
        """
        Pause trading operations
        
        Returns:
            True if paused successfully
        """
        if not self.running:
            logger.warning("Cannot pause: controller is not running")
            return False
        
        self.paused = True
        logger.info("MT5 controller paused")
        return True
    
    def resume(self) -> bool:
        """
        Resume trading operations
        
        Returns:
            True if resumed successfully
        """
        if not self.running:
            logger.warning("Cannot resume: controller is not running")
            return False
        
        self.paused = False
        logger.info("MT5 controller resumed")
        return True
    
    def _execution_loop(self) -> None:
        """Main execution loop for trading operations"""
        logger.info("Starting execution loop")
        
        while not self.stop_event.is_set():
            try:
                # Skip processing if paused
                if self.paused:
                    time.sleep(1)
                    continue
                
                # Check connection, reconnect if needed
                if not self.connector.connected:
                    logger.warning("Connection lost, attempting to reconnect")
                    if not self.connector.reconnect():
                        logger.error("Failed to reconnect, pausing execution")
                        self.paused = True
                        continue
                
                # Update market data
                self._update_market_data()
                
                # Process strategy signals
                self._process_strategy_signals()
                
                # Monitor open positions
                self._monitor_positions()
                
                # Update performance metrics
                self._update_performance_metrics()
                
                # Sleep for update interval
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in execution loop: {str(e)}")
                time.sleep(5)  # Wait before retrying
    
    def _update_market_data(self) -> None:
        """Update market data for all symbols and timeframes"""
        try:
            # Get latest tick data
            tick_data = self.data_feed.get_latest_ticks()
            
            # Get OHLC data for strategy timeframe
            ohlc_data = self.data_feed.get_ohlc_data(
                timeframes=[self.strategy_timeframe]
            )
            
            # Update last data timestamp
            now = datetime.now()
            for symbol in self.trading_symbols:
                self.last_data_update[symbol] = now
                
        except Exception as e:
            logger.error(f"Error updating market data: {str(e)}")
    
    def _process_strategy_signals(self) -> None:
        """Process trading signals from all active strategies"""
        try:
            now = datetime.now()
            
            # Check if we're in the allowed trading hours
            if not self._is_trading_allowed():
                return
            
            # Get current account information for position sizing
            account_info = self.connector.get_account_info()
            
            # Process each symbol
            for symbol in self.trading_symbols:
                # Skip if we already have an active position for this symbol
                if self._has_active_position(symbol):
                    continue
                
                # Get OHLC data for this symbol and the strategy timeframe
                ohlc_data = self.data_feed.ohlc_data.get(symbol, {}).get(self.strategy_timeframe)
                if ohlc_data is None or len(ohlc_data) < 100:  # Need enough data for analysis
                    continue
                
                # Analyze with each strategy
                combined_signal = self._get_combined_signal(symbol, ohlc_data)
                
                # Process signal if valid
                if combined_signal and combined_signal['signal'] != 'none':
                    self._execute_trading_signal(combined_signal, account_info)
                
                # Update last signal check time
                self.last_signal_check[symbol] = now
                
        except Exception as e:
            logger.error(f"Error processing strategy signals: {str(e)}")
    
    def _get_combined_signal(self, symbol: str, ohlc_data: pd.DataFrame) -> Optional[Dict]:
        """
        Get combined signal from all strategies
        
        Args:
            symbol: Trading symbol
            ohlc_data: OHLC data for analysis
            
        Returns:
            Combined signal dictionary or None
        """
        if not self.strategies:
            return None
        
        # Collect signals from all strategies
        strategy_signals = []
        
        for strategy_name, strategy in self.strategies.items():
            # Check if strategy should trade
            if not strategy.should_trade(symbol, ohlc_data):
                continue
                
            # Get signal
            signal = strategy.analyze(symbol, ohlc_data)
            
            if signal and signal['signal'] != 'none':
                strategy_signals.append({
                    'name': strategy_name,
                    'signal': signal
                })
        
        # No valid signals
        if not strategy_signals:
            return None
        
        # If only one signal, return it
        if len(strategy_signals) == 1:
            return strategy_signals[0]['signal']
        
        # Multiple signals - check for consensus
        buy_signals = [s for s in strategy_signals if s['signal']['signal'] == 'buy']
        sell_signals = [s for s in strategy_signals if s['signal']['signal'] == 'sell']
        
        # If all signals agree, use the strongest signal
        if buy_signals and not sell_signals:
            strongest = max(buy_signals, key=lambda s: s['signal']['signal_strength'])
            return strongest['signal']
        elif sell_signals and not buy_signals:
            strongest = max(sell_signals, key=lambda s: s['signal']['signal_strength'])
            return strongest['signal']
        
        # Conflicting signals, no consensus
        return None
    
    def _execute_trading_signal(self, signal: Dict, account_info: Dict) -> bool:
        """
        Execute a trading signal
        
        Args:
            signal: Signal dictionary with trading information
            account_info: Account information for position sizing
            
        Returns:
            True if order execution successful
        """
        symbol = signal['symbol']
        direction = signal['signal']
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        
        # Calculate position size based on risk
        volume = 0.01  # Default minimal size
        
        # If we have a valid risk manager and stop loss, calculate proper size
        if self.risk_manager and stop_loss > 0:
            # Get risk parameters
            risk_percent = self.config.get('risk', {}).get('max_risk_per_trade', 0.01)
            
            # Calculate position size for the strategies
            for strategy_name, strategy in self.strategies.items():
                if strategy.name in signal.get('strategy_name', ''):
                    volume = strategy.calculate_position_size(
                        symbol, account_info, entry_price, stop_loss
                    )
                    break
        
        # Verify with risk manager
        if self.risk_manager:
            # Check if trade is allowed
            risk_check = self.risk_manager.check_trade(
                symbol=symbol,
                direction=direction,
                volume=volume,
                entry_price=entry_price,
                stop_loss=stop_loss,
                account_info=account_info
            )
            
            if not risk_check['allowed']:
                logger.warning(f"Trade rejected by risk manager: {risk_check['reason']}")
                return False
            
            # Adjust volume if needed
            if risk_check['adjusted_volume'] < volume:
                logger.info(f"Volume adjusted by risk manager: {volume} -> {risk_check['adjusted_volume']}")
                volume = risk_check['adjusted_volume']
        
        # Prepare stop loss and take profit in points
        symbol_info = self.connector.get_symbol_info(symbol)
        if not symbol_info:
            logger.error(f"Cannot get symbol info for {symbol}")
            return False
        
        point = symbol_info.get('point', 0.0001)
        
        # Calculate SL/TP in points
        if direction == 'buy':
            sl_points = int((entry_price - stop_loss) / point) if stop_loss else None
            tp_points = int((take_profit - entry_price) / point) if take_profit else None
        else:  # sell
            sl_points = int((stop_loss - entry_price) / point) if stop_loss else None
            tp_points = int((entry_price - take_profit) / point) if take_profit else None
        
        # Execute the order
        order_result = self.executor.market_order(
            symbol=symbol,
            order_type=direction,
            volume=volume,
            sl_points=sl_points,
            tp_points=tp_points,
            comment=f"MT5Bot {direction.upper()}"
        )
        
        # Process result
        if order_result['success']:
            logger.info(f"Order executed: {symbol} {direction} {volume} lots at {entry_price}")
            
            # Update active trades
            self.active_trades[order_result['order_id']] = {
                'symbol': symbol,
                'direction': direction,
                'volume': volume,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'open_time': datetime.now().isoformat(),
                'order_id': order_result['order_id']
            }
            
            # Update session stats
            self.session_stats['trades_executed'] += 1
            
            return True
        else:
            logger.error(f"Order execution failed: {order_result.get('error', 'Unknown error')}")
            return False
    
    def _monitor_positions(self) -> None:
        """Monitor and manage open positions"""
        try:
            # Get all positions
            positions = self.executor.get_all_positions()
            
            # Update active trades
            for position in positions:
                # Check if we need to trail stop loss
                if self._should_trail_stop_loss(position):
                    self._trail_stop_loss(position)
            
            # Check for closed positions
            closed_positions = []
            
            for order_id, trade in self.active_trades.items():
                symbol = trade['symbol']
                
                # Find matching position
                matching = [p for p in positions if p['symbol'] == symbol]
                
                if not matching:
                    # Position was closed
                    closed_positions.append(order_id)
                    
                    # Get trade history to determine profit
                    profit = self._get_closed_trade_profit(order_id, symbol)
                    
                    # Update session stats
                    if profit > 0:
                        self.session_stats['profitable_trades'] += 1
                        self.session_stats['total_profit'] += profit
                    else:
                        self.session_stats['lost_trades'] += 1
                        self.session_stats['total_profit'] += profit
                    
                    logger.info(f"Position closed: {symbol} with profit {profit}")
            
            # Remove closed positions from active trades
            for order_id in closed_positions:
                if order_id in self.active_trades:
                    del self.active_trades[order_id]
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {str(e)}")
    
    def _should_trail_stop_loss(self, position: Dict) -> bool:
        """
        Check if stop loss should be trailed for a position
        
        Args:
            position: Position information
            
        Returns:
            True if stop loss should be trailed
        """
        # Get trailing stop settings
        trailing_enabled = self.config.get('risk', {}).get('trailing_stop', {}).get('enabled', False)
        if not trailing_enabled:
            return False
            
        # Get trailing parameters
        activation_pips = self.config.get('risk', {}).get('trailing_stop', {}).get('activation_pips', 10)
        trail_step_pips = self.config.get('risk', {}).get('trailing_stop', {}).get('trail_step_pips', 5)
        
        # Check position profit
        profit_pips = position.get('profit_pips', 0)
        
        # If profit exceeds activation threshold, trail the stop
        return profit_pips >= activation_pips
    
    def _trail_stop_loss(self, position: Dict) -> None:
        """
        Trail stop loss for a position
        
        Args:
            position: Position information
        """
        # Get trailing parameters
        trail_step_pips = self.config.get('risk', {}).get('trailing_stop', {}).get('trail_step_pips', 5)
        
        symbol = position['symbol']
        current_sl = position['sl']
        current_price = position['current_price']
        position_type = position['type']
        
        # Get symbol info for pip value
        symbol_info = self.connector.get_symbol_info(symbol)
        if not symbol_info:
            logger.error(f"Cannot get symbol info for {symbol}")
            return
            
        point = symbol_info.get('point', 0.0001)
        pip_value = point * 10  # 1 pip = 10 points
        
        # Calculate new stop loss
        new_sl = current_sl
        
        if position_type == 'buy':
            # For buy positions, move stop loss up
            trail_distance = trail_step_pips * pip_value
            target_sl = current_price - trail_distance
            
            # Only move stop loss up, never down
            if target_sl > current_sl:
                new_sl = target_sl
        else:
            # For sell positions, move stop loss down
            trail_distance = trail_step_pips * pip_value
            target_sl = current_price + trail_distance
            
            # Only move stop loss down, never up
            if target_sl < current_sl or current_sl == 0:
                new_sl = target_sl
        
        # If stop loss position changed, update it
        if new_sl != current_sl:
            result = self.executor.modify_position(
                symbol=symbol,
                sl=new_sl
            )
            
            if result['success']:
                logger.info(f"Trailed stop loss for {symbol}: {current_sl} -> {new_sl}")
            else:
                logger.error(f"Failed to trail stop loss for {symbol}: {result.get('error', 'Unknown error')}")
    
    def _get_closed_trade_profit(self, order_id: int, symbol: str) -> float:
        """
        Get profit for a closed trade
        
        Args:
            order_id: Order identifier
            symbol: Trading symbol
            
        Returns:
            Profit amount
        """
        # In a real implementation, this would query trade history
        # For now, estimate from session stats
        account_info = self.connector.get_account_info()
        current_balance = account_info.get('balance', 0)
        
        # Calculate profit change
        profit = 0
        if self.session_stats.get('peak_balance', 0) > 0:
            profit = current_balance - self.session_stats.get('peak_balance', 0)
            
            # Update peak balance if higher
            if current_balance > self.session_stats.get('peak_balance', 0):
                self.session_stats['peak_balance'] = current_balance
        
        return profit
    
    def _update_performance_metrics(self) -> None:
        """Update performance metrics based on current account status"""
        try:
            current_balance = self._get_account_balance()
            
            # Update peak balance
            if current_balance > self.session_stats.get('peak_balance', 0):
                self.session_stats['peak_balance'] = current_balance
            
            # Calculate current drawdown
            peak = self.session_stats.get('peak_balance', current_balance)
            if peak > 0:
                current_drawdown = (peak - current_balance) / peak
                self.session_stats['current_drawdown'] = current_drawdown
                
                # Update max drawdown
                if current_drawdown > self.session_stats.get('max_drawdown', 0):
                    self.session_stats['max_drawdown'] = current_drawdown
        
        except Exception as e:
            logger.error(f"Error updating performance metrics: {str(e)}")
    
    def _get_account_balance(self) -> float:
        """
        Get current account balance
        
        Returns:
            Account balance
        """
        account_info = self.connector.get_account_info()
        return account_info.get('balance', 0)
    
    def _is_trading_allowed(self) -> bool:
        """
        Check if trading is allowed based on session hours and risk limits
        
        Returns:
            True if trading is allowed
        """
        # Check trading session hours
        if self.trade_session_hours:
            now = datetime.now()
            current_hour = now.hour
            
            allowed_hours = []
            for session in self.trade_session_hours:
                if isinstance(session, list) and len(session) == 2:
                    start, end = session
                    if end < start:  # Overnight session
                        allowed_hours.extend(list(range(start, 24)) + list(range(0, end + 1)))
                    else:
                        allowed_hours.extend(list(range(start, end + 1)))
            
            if current_hour not in allowed_hours:
                return False
        
        # Check if daily loss limit is reached
        max_daily_loss = self.config.get('risk', {}).get('max_daily_loss', 0.05)
        if self.session_stats.get('current_drawdown', 0) >= max_daily_loss:
            logger.warning(f"Daily loss limit reached: {self.session_stats['current_drawdown']:.2%} >= {max_daily_loss:.2%}")
            return False
        
        return True
    
    def _has_active_position(self, symbol: str) -> bool:
        """
        Check if there's an active position for a symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if there's an active position
        """
        for trade in self.active_trades.values():
            if trade['symbol'] == symbol:
                return True
                
        return False
    
    def get_status(self) -> Dict:
        """
        Get current controller status
        
        Returns:
            Dictionary with status information
        """
        return {
            'running': self.running,
            'paused': self.paused,
            'connected': self.connector.connected if self.connector else False,
            'session_stats': self.session_stats,
            'active_trades': list(self.active_trades.values()),
            'symbols_data': {
                symbol: {
                    'last_update': self.last_data_update.get(symbol, None),
                    'last_signal_check': self.last_signal_check.get(symbol, None)
                }
                for symbol in self.trading_symbols
            }
        }
    
    def get_strategy_performance(self) -> Dict[str, Dict]:
        """
        Get performance metrics for all strategies
        
        Returns:
            Dictionary with strategy performance data
        """
        return {strategy_name: strategy.performance for strategy_name, strategy in self.strategies.items()}
