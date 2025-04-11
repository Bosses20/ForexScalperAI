"""
Bot Controller module for automated forex trading
Central component that manages all trading bot operations
"""

import asyncio
import yaml
import time
import signal
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
import pandas as pd
import threading
import json

# Local imports
from src.data.market_data import MarketDataFeed
from src.strategies.scalping_strategy import ScalpingStrategy
from src.models.prediction_model import PricePredictionModel
from src.risk.risk_manager import RiskManager
from src.execution.execution_engine import ExecutionEngine
from src.strategies.strategy_selector import StrategySelector
from src.mt5.instrument_manager import InstrumentManager
# Import new multi-asset trading components
from src.risk.correlation_manager import CorrelationManager
from src.trading.session_manager import SessionManager
from src.portfolio.portfolio_optimizer import PortfolioOptimizer
from src.trading.multi_asset_integrator import MultiAssetIntegrator
from src.analysis.market_condition_detector import MarketConditionDetector
# Import network discovery service
from src.services.network_discovery_service import NetworkDiscoveryService

class BotController:
    """
    Central controller for the trading bot that coordinates all components
    and manages the main trading loop. Integrates advanced market condition 
    detection and multi-asset trading capabilities.
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize the bot controller
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Configure logging
        self._setup_logging()
        
        # Flag for controlling the main loop
        self.running = False
        self.paused = False
        
        # Initialize components
        self.market_data = None
        self.strategy = None
        self.prediction_model = None
        self.risk_manager = None
        self.execution_engine = None
        self.strategy_selector = None
        self.instrument_manager = None
        self.correlation_manager = None
        self.session_manager = None
        self.portfolio_optimizer = None
        self.multi_asset_integrator = None
        self.market_condition_detector = None
        self.network_discovery_service = None
        
        # Trading state
        self.last_update_time = None
        self.trade_count = 0
        self.recent_signals = []
        self.recent_executions = []
        self.market_conditions = {}
        self.active_positions = []
        
        # Track performance
        self.performance_metrics = {}
        self.account_balance_history = []
        
        # Initialize executor for background tasks
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        logger.info("Bot controller initialized")
    
    def _load_config(self, config_path: str) -> dict:
        """
        Load configuration from YAML file
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                return config
            
        except Exception as e:
            raise Exception(f"Error loading configuration: {str(e)}")
    
    def _setup_logging(self):
        """
        Configure logging settings
        """
        log_config = self.config.get('logging', {})
        
        # Create logs directory if it doesn't exist
        log_dir = log_config.get('directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Configure loguru
        log_file = os.path.join(log_dir, f"bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        log_level = log_config.get('level', 'INFO')
        
        logger.remove()  # Remove default handler
        logger.add(sys.stderr, level=log_level)  # Add stderr handler
        logger.add(log_file, rotation="10 MB", level=log_level)  # Add file handler
        
        logger.info(f"Logging initialized at level {log_level}")
    
    def initialize_components(self):
        """
        Initialize all bot components
        """
        logger.info("Initializing bot components...")
        
        try:
            # Initialize instrument manager
            self.instrument_manager = InstrumentManager(self.config.get('instruments', {}))
            
            # Initialize market data feed
            self.market_data = MarketDataFeed(self.config.get('data', {}))
            
            # Initialize strategy components
            self.strategy_selector = StrategySelector(self.config.get('strategies', {}))
            
            # Initialize prediction model
            model_config = self.config.get('model', {})
            self.prediction_model = PricePredictionModel(model_config)
            
            # Initialize risk manager
            self.risk_manager = RiskManager(self.config.get('risk_management', {}))
            
            # Initialize execution engine
            self.execution_engine = ExecutionEngine(self.config.get('execution', {}))
            
            # Initialize multi-asset trading components
            self.correlation_manager = CorrelationManager(self.config.get('correlation', {}))
            self.session_manager = SessionManager(self.config.get('sessions', {}))
            self.portfolio_optimizer = PortfolioOptimizer(self.config.get('portfolio', {}))
            
            # Initialize market condition detector
            self.market_condition_detector = MarketConditionDetector(self.config)
            
            # Initialize multi-asset integrator
            self.multi_asset_integrator = MultiAssetIntegrator(self.config)
            
            # Connect components for proper integration
            # Connect MarketConditionDetector to MultiAssetIntegrator
            self.multi_asset_integrator.set_market_condition_detector(self.market_condition_detector)
            
            # Initialize network discovery service
            self.network_discovery_service = NetworkDiscoveryService(self.config)
            
            # Connect components to network discovery service
            self.network_discovery_service.set_market_condition_detector(self.market_condition_detector)
            self.network_discovery_service.set_multi_asset_integrator(self.multi_asset_integrator)
            
            # Ensure proper initialization of market conditions
            self._initialize_market_conditions()
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
            raise

    def _initialize_market_conditions(self):
        """
        Initialize market conditions for all configured symbols
        """
        try:
            # Get all trading symbols
            symbols = self._get_trading_symbols()
            
            if not symbols:
                logger.warning("No trading symbols configured")
                return
                
            logger.info(f"Initializing market conditions for {len(symbols)} symbols")
            
            # Fetch initial market data
            initial_data = {}
            for symbol in symbols:
                data = self.market_data.get_latest_data(symbol)
                if data is not None and not data.empty:
                    initial_data[symbol] = data
                    
            # Analyze initial market conditions
            if self.market_condition_detector and initial_data:
                market_conditions = {}
                for symbol, data in initial_data.items():
                    try:
                        condition = self.market_condition_detector.detect_market_condition(symbol, data)
                        market_conditions[symbol] = condition
                    except Exception as e:
                        logger.error(f"Error analyzing market condition for {symbol}: {str(e)}")
                
                # Update market conditions in components
                self.market_conditions = market_conditions
                
                # Update multi-asset integrator with initial market conditions
                if self.multi_asset_integrator:
                    self.multi_asset_integrator.update_market_conditions(market_conditions)
                    
                # Update network discovery service with initial market conditions
                if self.network_discovery_service:
                    self.network_discovery_service.update_market_conditions(market_conditions)
                    
                logger.info(f"Market conditions initialized for {len(market_conditions)} symbols")
        except Exception as e:
            logger.error(f"Error initializing market conditions: {str(e)}")
    
    def start(self):
        """
        Start the bot
        """
        logger.info("Starting trading bot")
        self.running = True
        self.paused = False
        
        # Start network discovery service
        self.network_discovery_service.start()
        logger.info("Network discovery service started")
        
        # Fetch initial market data
        self.update_market_data()
        
        # Analyze market conditions before starting trading
        self._analyze_global_market_conditions()
        
        # Start the trading thread
        self.trading_thread = threading.Thread(target=self.trading_cycle, daemon=True)
        self.trading_thread.start()
        
        logger.info("Trading bot started")
        
    def _analyze_global_market_conditions(self):
        """
        Analyze market conditions across all instruments to determine optimal trading strategy
        """
        logger.debug("Analyzing global market conditions")
        
        try:
            # Get all symbols configured for trading
            symbols = self._get_trading_symbols()
            
            # Track market conditions for all symbols
            market_conditions = {}
            
            # Analyze each symbol
            for symbol in symbols:
                # Get latest data
                data = self.market_data.get_latest_data(symbol)
                if data is None or data.empty:
                    logger.warning(f"No data available for {symbol}")
                    continue
                
                # Detect market condition using the specialized detector
                condition = self.market_condition_detector.detect_market_condition(symbol, data)
                
                if condition:
                    market_conditions[symbol] = condition
                    
                    # Update the data in multi-asset integrator
                    self.multi_asset_integrator.update_market_data(symbol, data)
            
            # Store market conditions
            self.market_conditions = market_conditions
            
            # Update multi-asset integrator with comprehensive market conditions
            self.multi_asset_integrator.update_market_conditions(market_conditions)
            
            # Update network discovery service with market conditions
            self.network_discovery_service.update_market_conditions(market_conditions)
            
            # Get active positions
            active_positions = self.execution_engine.get_active_positions()
            self.active_positions = active_positions
            
            # Update multi-asset integrator and network discovery with positions
            self.multi_asset_integrator.update_positions(active_positions)
            self.network_discovery_service.update_active_positions(active_positions)
            
            # Get trading opportunities for network discovery
            opportunities = self._get_trading_opportunities()
            self.network_discovery_service.update_trading_opportunities(opportunities)
            
            logger.debug(f"Market conditions analyzed for {len(market_conditions)} symbols")
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {str(e)}")
            raise

    def trading_cycle(self):
        """
        Main trading cycle
        """
        logger.info("Starting trading cycle")
        
        try:
            # Get global market conditions
            try:
                self._analyze_global_market_conditions()
            except Exception as e:
                logger.error(f"Error in analyzing market conditions: {str(e)}")
                # Continue execution as we can still work with existing data
            
            # Get account information and update components
            try:
                account_info = self.execution_engine.get_account_info()
                if account_info:
                    self.multi_asset_integrator.update_account_info(account_info)
                    
                    # Track account balance history
                    self.account_balance_history.append({
                        'timestamp': datetime.now().isoformat(),
                        'balance': account_info.get('balance', 0),
                        'equity': account_info.get('equity', 0)
                    })
            except Exception as e:
                logger.error(f"Error getting account info: {str(e)}")
                account_info = None
            
            # Process existing positions first to manage risk before entering new trades
            try:
                self.process_active_positions()
            except Exception as e:
                logger.error(f"Error processing active positions: {str(e)}")
                # Continue execution to try other operations
            
            # Update portfolio metrics after processing existing positions
            try:
                portfolio_metrics = self.multi_asset_integrator.get_performance_summary()
                self.performance_metrics = portfolio_metrics
            except Exception as e:
                logger.error(f"Error updating portfolio metrics: {str(e)}")
            
            # Skip new trades if we don't have account info
            if not account_info:
                logger.warning("No account info available, skipping new trade entries")
                return
            
            # Get trading candidates from multi-asset integrator - these are the optimal symbols to trade
            try:
                trading_candidates = self.multi_asset_integrator.get_trading_candidates()
            except Exception as e:
                logger.error(f"Error getting trading candidates: {str(e)}")
                trading_candidates = []
            
            # Skip entering new positions if we already have too many open positions or market is too volatile
            active_positions_count = len(self.active_positions)
            max_positions = self.config.get('trading', {}).get('max_concurrent_positions', 5)
            
            if active_positions_count >= max_positions:
                logger.info(f"Already at maximum positions ({active_positions_count}/{max_positions}), skipping new entries")
                return
                
            # Check overall market stress 
            try:
                market_stress_level = self._calculate_market_stress_level()
                if market_stress_level > 0.7:  # High stress
                    logger.warning(f"High market stress level ({market_stress_level:.2f}), being conservative with new positions")
                    # Reduce max positions in high stress market
                    max_positions = max(1, int(max_positions * 0.5))
            except Exception as e:
                logger.error(f"Error calculating market stress level: {str(e)}")
                market_stress_level = 0.5  # Default to medium stress
        
            # Determine how many new positions we can take
            available_position_slots = max_positions - active_positions_count
            if available_position_slots <= 0:
                logger.info("No available position slots, skipping new entries")
                return
                
            logger.info(f"Found {len(trading_candidates)} trading candidates: {', '.join(trading_candidates)}")
            logger.info(f"Available position slots: {available_position_slots}")
            
            # Sort candidates by their opportunity strength
            try:
                sorted_candidates = self._rank_trading_candidates(trading_candidates)
                
                # Limit to available slots
                candidates_to_process = sorted_candidates[:available_position_slots]
            except Exception as e:
                logger.error(f"Error ranking trading candidates: {str(e)}")
                candidates_to_process = trading_candidates[:available_position_slots]
            
            # Process each trading candidate
            for symbol in candidates_to_process:
                try:
                    # Get symbol data
                    data = self.market_data.get_latest_data(symbol)
                    if data is None or data.empty:
                        logger.warning(f"No data available for {symbol}")
                        continue
                    
                    # Check if we should trade this symbol based on market conditions
                    if self.market_condition_detector and not self.market_condition_detector.should_trade_now(
                        symbol, data, min_confidence=0.65):  # Higher confidence threshold for profitability
                        logger.info(f"Market conditions not favorable for {symbol}, skipping")
                        continue
                    
                    # Select optimal strategy using multi-asset integrator
                    strategy_name = self.multi_asset_integrator.select_strategy(symbol)
                    
                    if not strategy_name:
                        logger.warning(f"No suitable strategy found for {symbol}")
                        continue
                    
                    # Create strategy instance
                    strategy = self.strategy_selector.get_strategy(strategy_name)
                    
                    if not strategy:
                        logger.warning(f"Could not initialize strategy {strategy_name}")
                        continue
                    
                    # Generate signals
                    signal = strategy.generate_signal(symbol, data)
                    
                    # Store recent signals for analysis
                    self.recent_signals.append({
                        'timestamp': datetime.now().isoformat(),
                        'symbol': symbol,
                        'strategy': strategy_name,
                        'signal': signal
                    })
                    
                    # Validate signal against market conditions
                    if signal and signal.get('action') != 'NONE':
                        try:
                            # Get current market conditions for this symbol
                            instrument_info = self.market_conditions.get(symbol, {})
                            
                            # Validate signal
                            is_valid = self._validate_signal(signal, instrument_info)
                            
                            if is_valid:
                                # Check for existing position in the same symbol
                                existing_position = next((p for p in self.active_positions if p.get('symbol') == symbol), None)
                                if existing_position:
                                    logger.info(f"Already have an active position for {symbol}, skipping new entry")
                                    continue
                                    
                                # Get position size with risk management
                                position_size = self.risk_manager.calculate_position_size(
                                    symbol, 
                                    signal.get('direction'), 
                                    data, 
                                    account_info.get('balance', 0)
                                )
                                
                                # Apply market-based position sizing adjustment
                                allocation = self.multi_asset_integrator.get_position_allocation(symbol)
                                adjusted_position_size = position_size * allocation
                                
                                # Apply additional market condition adjustment based on confidence
                                market_confidence = instrument_info.get('confidence', 0.5)
                                # Scale position size by confidence (reduce size in uncertain markets)
                                confidence_factor = max(0.5, market_confidence) 
                                final_position_size = adjusted_position_size * confidence_factor
                                
                                # Validate position with multi-asset integrator
                                validation_result = self.multi_asset_integrator.validate_new_position(
                                    symbol, 
                                    signal.get('direction'), 
                                    final_position_size
                                )
                                
                                if validation_result[0]:
                                    # Execute trade with dynamic risk parameters
                                    execution_result = self.execution_engine.execute_trade(
                                        symbol,
                                        signal.get('direction'),
                                        final_position_size,
                                        sl_pips=self._calculate_dynamic_stop_loss(symbol, signal.get('direction'), data, instrument_info),
                                        tp_pips=self._calculate_dynamic_take_profit(symbol, signal.get('direction'), data, instrument_info),
                                        strategy=strategy_name
                                    )
                                    
                                    # Store execution result
                                    self.recent_executions.append({
                                        'timestamp': datetime.now().isoformat(),
                                        'symbol': symbol,
                                        'direction': signal.get('direction'),
                                        'size': final_position_size,
                                        'result': execution_result
                                    })
                                    
                                    # Process trade result in multi-asset integrator
                                    if execution_result and execution_result.get('success'):
                                        trade_data = {
                                            'symbol': symbol,
                                            'strategy': strategy_name,
                                            'direction': signal.get('direction'),
                                            'entry_price': execution_result.get('price'),
                                            'position_size': final_position_size,
                                            'timestamp': datetime.now().isoformat()
                                        }
                                        self.multi_asset_integrator.process_trade_result(trade_data)
                                    
                                    # Increment trade counter
                                    self.trade_count += 1
                                    
                                    logger.info(f"Executed {signal.get('direction')} trade on {symbol} with size {final_position_size}")
                                else:
                                    logger.info(f"Trade validation failed for {symbol}: {validation_result[1]}")
                            else:
                                logger.info(f"Signal validation failed for {symbol}")
                        except Exception as e:
                            logger.error(f"Error validating/executing signal for {symbol}: {str(e)}")
                except Exception as e:
                    logger.error(f"Error processing symbol {symbol}: {str(e)}")
            
            # Update last update time
            self.last_update_time = datetime.now()
            
            # Update trading opportunities for network discovery
            try:
                opportunities = self._get_trading_opportunities()
                self.network_discovery_service.update_trading_opportunities(opportunities)
            except Exception as e:
                logger.error(f"Error updating trading opportunities: {str(e)}")
            
            logger.info("Trading cycle completed")
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {str(e)}")
            raise  # Re-raise the exception for proper error handling at higher level

    def process_active_positions(self):
        """
        Process and manage all active positions:
        - Apply trailing stops
        - Close positions in adverse market conditions
        - Scale out of profitable positions
        - Adjust risk parameters based on performance
        """
        logger.info("Processing active positions")
        
        try:
            # Get all current positions
            try:
                active_positions = self.execution_engine.get_active_positions()
                
                if not active_positions:
                    logger.info("No active positions to process")
                    self.active_positions = []
                    return
                    
                self.active_positions = active_positions
                
                # Update components with current positions
                self.multi_asset_integrator.update_positions(active_positions)
                self.network_discovery_service.update_active_positions(active_positions)
            except Exception as e:
                logger.error(f"Error retrieving active positions: {str(e)}")
                return
            
            # Track position performance metrics
            position_metrics = {
                'total_profit_pips': 0,
                'total_profit_amount': 0,
                'winning_positions': 0,
                'losing_positions': 0,
                'breakeven_positions': 0
            }
            
            # Process each position
            for position in active_positions:
                symbol = position.get('symbol')
                entry_price = position.get('entry_price', 0)
                current_price = position.get('current_price', entry_price)
                direction = position.get('direction', 'BUY')
                position_id = position.get('id', '')
                open_time = position.get('open_time', '')
                profit_pips = position.get('profit_pips', 0)
                profit_amount = position.get('profit_amount', 0)
                
                # Update position metrics
                position_metrics['total_profit_pips'] += profit_pips
                position_metrics['total_profit_amount'] += profit_amount
                
                if profit_pips > 2:  # More than 2 pips profit
                    position_metrics['winning_positions'] += 1
                elif profit_pips < -2:  # More than 2 pips loss
                    position_metrics['losing_positions'] += 1
                else:
                    position_metrics['breakeven_positions'] += 1
                
                try:
                    # Get latest data and market conditions
                    latest_data = self.market_data.get_latest_data(symbol)
                    market_condition = self.market_conditions.get(symbol, {})
                    
                    if latest_data is None or latest_data.empty:
                        logger.warning(f"No market data available for {symbol}, skipping position management")
                        continue
                    
                    # Calculate position age in minutes
                    if open_time:
                        try:
                            open_datetime = datetime.fromisoformat(open_time)
                            position_age_minutes = (datetime.now() - open_datetime).total_seconds() / 60
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid open time format for {symbol} position: {open_time}")
                            position_age_minutes = 0
                    else:
                        position_age_minutes = 0
                    
                    # Get current trend from market conditions
                    current_trend = market_condition.get('trend', 'unknown')
                    
                    # Check if market conditions have become adverse (trend reversed)
                    trend_against_position = (
                        (direction == 'BUY' and current_trend in ['bearish', 'strong_bearish']) or
                        (direction == 'SELL' and current_trend in ['bullish', 'strong_bullish'])
                    )
                    
                    # Check if trend has strengthened in our favor
                    trend_strongly_favoring_position = (
                        (direction == 'BUY' and current_trend == 'strong_bullish') or
                        (direction == 'SELL' and current_trend == 'strong_bearish')
                    )
                    
                    # Advanced scalping logic - move to breakeven quickly
                    should_move_to_breakeven = (
                        profit_pips >= 3 or  # At least 3 pips in profit
                        (position_age_minutes >= 30 and profit_pips >= 2)  # 2+ pips after 30 minutes
                    )
                    
                    if should_move_to_breakeven and not position.get('at_breakeven', False):
                        try:
                            # Update stop loss to breakeven (plus 1 pip buffer)
                            result = self.execution_engine.update_stop_loss(
                                symbol, position_id, entry_price, "Move to breakeven"
                            )
                            
                            if result and result.get('success'):
                                logger.info(f"Moved {symbol} position to breakeven after {position_age_minutes:.1f} minutes")
                                # Mark position as at breakeven in local cache
                                position['at_breakeven'] = True
                        except Exception as e:
                            logger.error(f"Error moving {symbol} position to breakeven: {str(e)}")
                    
                    # Check if we should apply a trailing stop
                    should_trail = (
                        profit_pips >= 5 or  # At least 5 pips in profit
                        position_age_minutes >= 60  # Position open for at least 1 hour
                    )
                    
                    # Apply trailing stop if needed
                    if should_trail:
                        try:
                            # Calculate trailing stop distance based on volatility and profit
                            volatility = market_condition.get('volatility', 'medium')
                            trail_distance_pips = self._calculate_trailing_stop(
                                symbol, direction, profit_pips, volatility, position_age_minutes
                            )
                            
                            # Apply trailing stop
                            self.execution_engine.update_trailing_stop(
                                symbol, position_id, trail_distance_pips
                            )
                            logger.info(f"Applied trailing stop of {trail_distance_pips} pips to {symbol} position")
                        except Exception as e:
                            logger.error(f"Error applying trailing stop to {symbol} position: {str(e)}")
                    
                    # Check if we should scale out (partial close) of a profitable position
                    should_scale_out = (
                        profit_pips >= 15 or  # At least 15 pips in profit
                        (profit_pips >= 10 and trend_against_position) or  # Lock in profits if trend turning
                        (profit_pips >= 8 and position_age_minutes >= 120)  # Lock in smaller profits for older positions
                    )
                    
                    # Only scale out if not already scaled
                    if should_scale_out and not position.get('scaled_out', False):
                        try:
                            # Scale out 50% of the position
                            current_volume = position.get('volume', 0)
                            scale_out_volume = current_volume * 0.5
                            
                            # Partially close position
                            result = self.execution_engine.partially_close_position(
                                symbol, position_id, scale_out_volume
                            )
                            
                            if result and result.get('success'):
                                logger.info(f"Scaled out 50% of position for {symbol} at {profit_pips} pips profit")
                                # Mark position as scaled in local cache
                                position['scaled_out'] = True
                        except Exception as e:
                            logger.error(f"Error scaling out {symbol} position: {str(e)}")
                    
                    # Close position if market conditions are significantly adverse
                    if trend_against_position and position_age_minutes > 30:
                        # Only close if the trend change is confirmed and position is not too new
                        confidence = market_condition.get('confidence', 0)
                        
                        if confidence > 0.7:  # High confidence in adverse trend
                            try:
                                # Close position
                                result = self.execution_engine.close_position(
                                    symbol, position_id, "Adverse market conditions"
                                )
                                
                                if result and result.get('success'):
                                    logger.info(f"Closed position for {symbol} due to adverse market conditions")
                            except Exception as e:
                                logger.error(f"Error closing {symbol} position in adverse market: {str(e)}")
                    
                    # Handle positions that are stuck in a range
                    is_ranging = market_condition.get('trend') == 'ranging'
                    is_stuck = position_age_minutes > 180 and abs(profit_pips) < 5  # 3 hours with less than 5 pips movement
                    
                    if is_stuck and is_ranging:
                        try:
                            # Close positions stuck in ranging markets
                            result = self.execution_engine.close_position(
                                symbol, position_id, "Position stuck in ranging market"
                            )
                            
                            if result and result.get('success'):
                                logger.info(f"Closed stuck position for {symbol} in ranging market")
                        except Exception as e:
                            logger.error(f"Error closing stuck {symbol} position: {str(e)}")
                    
                    # Handle positions that have been open too long (preventing overnight exposure)
                    max_hold_time_minutes = self.config.get('trading', {}).get('max_hold_time_minutes', 480)  # 8 hours default
                    if position_age_minutes > max_hold_time_minutes:
                        try:
                            # Close position that has been open too long
                            result = self.execution_engine.close_position(
                                symbol, position_id, "Max hold time exceeded"
                            )
                            
                            if result and result.get('success'):
                                logger.info(f"Closed {symbol} position after {position_age_minutes:.1f} minutes (max hold time reached)")
                        except Exception as e:
                            logger.error(f"Error closing {symbol} position at max hold time: {str(e)}")
                    
                    # For winning positions in strong trend, pyramiding (adding to position)
                    can_pyramid = (
                        trend_strongly_favoring_position and
                        profit_pips >= 10 and
                        not position.get('pyramided', False) and
                        position_age_minutes < 120  # Only pyramid newer positions
                    )
                    
                    if can_pyramid:
                        try:
                            # Calculate additional position size (half of original)
                            original_volume = position.get('volume', 0)
                            pyramid_volume = original_volume * 0.5
                            
                            # Execute additional trade in the same direction
                            execution_result = self.execution_engine.execute_trade(
                                symbol,
                                direction,
                                pyramid_volume,
                                sl_pips=self._calculate_dynamic_stop_loss(symbol, direction, latest_data, market_condition),
                                tp_pips=self._calculate_dynamic_take_profit(symbol, direction, latest_data, market_condition),
                                strategy=position.get('strategy', 'unknown'),
                                is_pyramid=True
                            )
                            
                            if execution_result and execution_result.get('success'):
                                logger.info(f"Pyramided position for {symbol} with additional {pyramid_volume} volume")
                                # Mark position as pyramided in local cache
                                position['pyramided'] = True
                        except Exception as e:
                            logger.error(f"Error pyramiding {symbol} position: {str(e)}")
                    
                except Exception as e:
                    logger.error(f"Error processing position for {symbol}: {str(e)}")
            
            # Update performance metrics for stats tracking
            try:
                self.multi_asset_integrator.update_position_metrics(position_metrics)
            except Exception as e:
                logger.error(f"Error updating position metrics: {str(e)}")
            
            logger.info(f"Processed {len(active_positions)} active positions")
            
        except Exception as e:
            logger.error(f"Error in process_active_positions: {str(e)}")
            raise  # Re-raise for proper error handling
    
    def _calculate_dynamic_stop_loss(self, symbol, direction, data, market_info):
        """
        Calculate dynamic stop loss based on market volatility and trend
        
        Args:
            symbol: Trading symbol
            direction: Trade direction (BUY/SELL)
            data: Market data DataFrame
            market_info: Market condition information
        
        Returns:
            Stop loss in pips
        """
        # Get volatility from market info
        volatility = market_info.get('volatility', 'medium')
        
        # Base stop loss
        base_sl_pips = 10  # Default 10 pips
        
        # Adjust based on volatility
        if volatility == 'high':
            base_sl_pips = 15
        elif volatility == 'low':
            base_sl_pips = 7
            
        # Calculate ATR if available in the data
        if 'atr' in data.columns:
            atr = data['atr'].iloc[-1]
            # Convert ATR to pips (assuming 4 decimal standard)
            atr_pips = atr * 10000
            
            # Use ATR-based stop loss, but enforce minimum and maximum
            sl_pips = max(base_sl_pips, min(atr_pips * 1.5, 25))
        else:
            sl_pips = base_sl_pips
            
        # Adjust for trading session if available
        if hasattr(self, 'session_manager') and self.session_manager:
            current_session = self.session_manager.get_current_session()
            if current_session == 'london_ny_overlap':
                # Higher volatility during London/NY overlap, increase stop loss
                sl_pips *= 1.2
            elif current_session == 'asian':
                # Lower volatility in Asian session, slightly tighter stop loss
                sl_pips *= 0.9
        
        return round(sl_pips, 1)
    
    def _calculate_dynamic_take_profit(self, symbol, direction, data, market_info):
        """
        Calculate dynamic take profit based on market volatility and trend
        
        Args:
            symbol: Trading symbol
            direction: Trade direction (BUY/SELL)
            data: Market data DataFrame
            market_info: Market condition information
        
        Returns:
            Take profit in pips
        """
        # Get stop loss first (to maintain risk:reward ratio)
        sl_pips = self._calculate_dynamic_stop_loss(symbol, direction, data, market_info)
        
        # Calculate risk:reward ratio based on market trend strength
        trend_strength = market_info.get('trend_strength', 0.5)
        
        # Adjust risk:reward based on trend strength
        if trend_strength > 0.7:  # Strong trend
            risk_reward_ratio = 1.8  # Higher reward for strong trends
        elif trend_strength > 0.4:  # Moderate trend
            risk_reward_ratio = 1.5
        else:  # Weak trend
            risk_reward_ratio = 1.2  # Conservative target
            
        # Calculate take profit
        tp_pips = sl_pips * risk_reward_ratio
        
        # Cap at reasonable maximum
        tp_pips = min(tp_pips, 30)
        
        return round(tp_pips, 1)

    def _calculate_trailing_stop(self, symbol, direction, profit_pips, volatility, position_age_minutes):
        """
        Calculate trailing stop distance based on profit and market conditions
        
        Args:
            symbol: Trading symbol
            direction: Trade direction (BUY/SELL)
            profit_pips: Current profit in pips
            volatility: Market volatility (low, medium, high)
            position_age_minutes: Position age in minutes
        
        Returns:
            Trailing stop distance in pips
        """
        # Base trailing stop
        base_trail = 5
        
        # Adjust based on volatility
        if volatility == 'high':
            base_trail = 8
        elif volatility == 'low':
            base_trail = 3
            
        # Adjust based on profit (trail tighter for higher profits)
        if profit_pips > 20:
            base_trail = base_trail * 0.7  # Tighter trail for big profits
        elif profit_pips > 10:
            base_trail = base_trail * 0.85
            
        # Adjust based on position age (trail tighter for older positions)
        if position_age_minutes > 240:  # 4 hours or older
            base_trail = base_trail * 0.8
        elif position_age_minutes > 120:  # 2-4 hours
            base_trail = base_trail * 0.9
            
        return round(base_trail, 1)

    def _calculate_market_stress_level(self):
        """
        Calculate overall market stress level across all symbols
        
        Returns:
            Market stress level from 0 (low stress) to 1 (high stress)
        """
        if not self.market_conditions:
            return 0.5  # Default middle value if no data
            
        # Count high volatility and adverse conditions
        high_volatility_count = 0
        choppy_count = 0
        total_symbols = len(self.market_conditions)
        
        for symbol, condition in self.market_conditions.items():
            if condition.get('volatility') == 'high':
                high_volatility_count += 1
                
            if condition.get('trend') in ['choppy', 'unknown']:
                choppy_count += 1
                
        # Calculate ratios
        volatility_ratio = high_volatility_count / total_symbols if total_symbols > 0 else 0
        choppy_ratio = choppy_count / total_symbols if total_symbols > 0 else 0
        
        # Combine into overall stress level
        stress_level = (volatility_ratio * 0.6) + (choppy_ratio * 0.4)
        
        return stress_level

    def _rank_trading_candidates(self, candidates):
        """
        Rank trading candidates by opportunity quality
        
        Args:
            candidates: List of trading symbols
        
        Returns:
            Sorted list of symbols by opportunity quality
        """
        if not candidates:
            return []
            
        ranked_candidates = []
        
        for symbol in candidates:
            # Get market conditions for this symbol
            market_condition = self.market_conditions.get(symbol, {})
            
            # Score factors
            trend_score = 0
            volatility_score = 0
            confidence_score = 0
            
            # Score trend
            trend = market_condition.get('trend', 'unknown')
            if trend in ['strong_bullish', 'strong_bearish']:
                trend_score = 1.0
            elif trend in ['bullish', 'bearish']:
                trend_score = 0.8
            elif trend in ['weak_bullish', 'weak_bearish']:
                trend_score = 0.6
            elif trend == 'ranging':
                trend_score = 0.4
            else:
                trend_score = 0.2
                
            # Score volatility - favor medium volatility
            volatility = market_condition.get('volatility', 'medium')
            if volatility == 'medium':
                volatility_score = 1.0
            elif volatility == 'low':
                volatility_score = 0.7
            elif volatility == 'high':
                volatility_score = 0.5
            else:
                volatility_score = 0.3
                
            # Score confidence
            confidence = market_condition.get('confidence', 0.5)
            confidence_score = confidence
            
            # Calculate total score
            total_score = (trend_score * 0.5) + (volatility_score * 0.3) + (confidence_score * 0.2)
            
            ranked_candidates.append((symbol, total_score))
    
        # Sort by score (highest first)
        ranked_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Return just the symbols
        return [symbol for symbol, _ in ranked_candidates]

    def _validate_signal(self, signal, instrument_info):
        """
        Validate a trading signal against current market conditions and risk parameters
        
        Args:
            signal: Trading signal dictionary
            instrument_info: Instrument market condition info
            
        Returns:
            bool: Whether the signal should be executed
        """
        if not signal:
            return False
            
        # Extract signal components
        action = signal.get('action')
        direction = signal.get('direction')
        symbol = signal.get('symbol')
        
        # Skip if no action or symbol
        if not action or not symbol:
            return False
            
        # Only process 'OPEN' actions
        if action != 'OPEN':
            return True  # Other actions (like CLOSE) are always valid
            
        # Check against market conditions
        if instrument_info:
            trend = instrument_info.get('trend', 'unknown')
            volatility = instrument_info.get('volatility', 'unknown')
            confidence = instrument_info.get('confidence', 0)
            liquidity = instrument_info.get('liquidity', 'unknown')
            
            # Reject trades with insufficient confidence
            min_confidence = self.config.get('trading', {}).get('min_confidence', 0.6)
            if confidence < min_confidence:
                logger.debug(f"Signal rejected for {symbol}: Confidence too low ({confidence:.2f} < {min_confidence:.2f})")
                return False
                
            # Check if signal direction aligns with trend
            if trend != 'unknown':
                if (direction == 'BUY' and trend in ['bearish', 'strong_bearish']) or \
                   (direction == 'SELL' and trend in ['bullish', 'strong_bullish']):
                    logger.debug(f"Signal rejected for {symbol}: Direction {direction} conflicts with {trend} trend")
                    return False
                    
            # Check volatility suitability
            max_volatility = self.config.get('risk_management', {}).get('max_volatility', 'high')
            if volatility != 'unknown' and max_volatility != 'any':
                volatility_ranks = {'low': 1, 'medium': 2, 'high': 3}
                if volatility_ranks.get(volatility, 0) > volatility_ranks.get(max_volatility, 3):
                    logger.debug(f"Signal rejected for {symbol}: Volatility too high ({volatility} > {max_volatility})")
                    return False
            
            # Check liquidity
            min_liquidity = self.config.get('trading', {}).get('min_liquidity', 'medium')
            if liquidity != 'unknown' and min_liquidity != 'any':
                liquidity_ranks = {'low': 1, 'medium': 2, 'high': 3}
                if liquidity_ranks.get(liquidity, 0) < liquidity_ranks.get(min_liquidity, 2):
                    logger.debug(f"Signal rejected for {symbol}: Liquidity too low ({liquidity} < {min_liquidity})")
                    return False
        
        # Check risk limits
        max_trades = self.config.get('risk_management', {}).get('max_concurrent_trades', 10)
        if len(self.execution_engine.get_active_positions()) >= max_trades:
            logger.debug(f"Signal rejected for {symbol}: Maximum number of trades ({max_trades}) reached")
            return False
            
        return True
    
    def _get_trading_symbols(self) -> List[str]:
        """
        Get list of symbols to trade.
        
        Returns:
            List of symbol strings
        """
        # Get symbols from configuration
        config_symbols = []
        
        # Extract symbols from forex section
        forex_symbols = self.config.get('trading', {}).get('symbols', {}).get('forex', [])
        for symbol_info in forex_symbols:
            if isinstance(symbol_info, dict) and 'name' in symbol_info:
                config_symbols.append(symbol_info['name'])
            elif isinstance(symbol_info, str):
                config_symbols.append(symbol_info)
                
        # Extract symbols from synthetic section
        synthetic_symbols = self.config.get('trading', {}).get('symbols', {}).get('synthetic', [])
        for symbol_info in synthetic_symbols:
            if isinstance(symbol_info, dict) and 'name' in symbol_info:
                config_symbols.append(symbol_info['name'])
            elif isinstance(symbol_info, str):
                config_symbols.append(symbol_info)
                
        return config_symbols
        
    def _get_trading_opportunities(self) -> List[Dict]:
        """
        Get current trading opportunities based on market conditions.
        
        Returns:
            List of trading opportunity dictionaries
        """
        opportunities = []
        
        # Get trading candidates
        trading_candidates = self.multi_asset_integrator.get_trading_candidates()
        
        for symbol in trading_candidates:
            # Skip if we don't have market conditions
            if symbol not in self.market_conditions:
                continue
                
            # Get market conditions
            conditions = self.market_conditions[symbol]
            
            # Get trend and confidence
            trend = conditions.get('trend', 'unknown')
            confidence = conditions.get('confidence', 0)
            
            # Skip low confidence opportunities
            if confidence < 0.6:
                continue
                
            # Determine direction based on trend
            direction = None
            if trend in ['bullish', 'strong_bullish']:
                direction = 'BUY'
            elif trend in ['bearish', 'strong_bearish']:
                direction = 'SELL'
                
            # Add opportunity if we have a direction
            if direction:
                # Get strategy
                strategy_name = self.multi_asset_integrator.select_strategy(symbol)
                
                # Get estimated position size
                position_size = 0.01  # Default
                account_info = self.execution_engine.get_account_info()
                if account_info:
                    account_balance = account_info.get('balance', 0)
                    position_size = self.risk_manager.calculate_position_size(
                        symbol, 
                        direction, 
                        self.market_data.get_latest_data(symbol), 
                        account_balance
                    )
                    
                    # Apply allocation
                    allocation = self.multi_asset_integrator.get_position_allocation(symbol)
                    position_size *= allocation
                
                opportunities.append({
                    'symbol': symbol,
                    'direction': direction,
                    'confidence': confidence,
                    'strategy': strategy_name,
                    'position_size': position_size,
                    'market_conditions': {
                        'trend': trend,
                        'volatility': conditions.get('volatility', 'unknown')
                    }
                })
        
        # Sort by confidence
        opportunities.sort(key=lambda x: x['confidence'], reverse=True)
        
        return opportunities
    
    def stop(self):
        """
        Stop the bot
        """
        if not self.running:
            return
            
        logger.info("Stopping trading bot")
        self.running = False
        
        # Wait for trading thread to complete
        if self.trading_thread and self.trading_thread.is_alive():
            self.trading_thread.join(timeout=10)
            
        # Close all positions if configured
        if self.config.get('trading', {}).get('close_positions_on_stop', True):
            try:
                active_positions = self.execution_engine.get_active_positions()
                if active_positions:
                    logger.info(f"Closing {len(active_positions)} positions on shutdown")
                    for symbol in active_positions:
                        self.execution_engine.close_position(symbol, "bot_shutdown")
            except Exception as e:
                logger.error(f"Error closing positions on shutdown: {str(e)}")
        
        # Stop network discovery service
        try:
            self.network_discovery_service.stop()
        except Exception as e:
            logger.error(f"Error stopping network discovery service: {str(e)}")
            
        logger.info("Trading bot stopped")
