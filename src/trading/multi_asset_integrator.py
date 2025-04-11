"""
Multi-Asset Integrator
Integrates and coordinates all components for multi-asset trading across
Forex and Synthetic Indices
"""

from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
import pandas as pd
from loguru import logger
import logging
import time
import numpy as np

# Import component classes
from src.mt5.instrument_manager import InstrumentManager
from src.risk.correlation_manager import CorrelationManager
from src.trading.session_manager import SessionManager
from src.portfolio.portfolio_optimizer import PortfolioOptimizer
from src.strategies.strategy_selector import StrategySelector
from src.analysis.price_action import PriceActionAnalyzer
from src.analysis.market_condition_detector import MarketConditionDetector


class MultiAssetIntegrator:
    """
    Integrates multi-asset trading capabilities with market condition analysis 
    for optimized trading across Forex and Synthetic Indices.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the multi-asset integrator
        
        Args:
            config: Configuration dictionary containing all settings
        """
        self.logger = logging.getLogger(__name__)
        
        # Store configuration
        self.config = config
        self.correlation_config = config.get('correlation', {})
        self.session_config = config.get('sessions', {})
        self.portfolio_config = config.get('portfolio', {})
        
        # Initialize sub-components
        self.correlation_manager = None
        self.session_manager = None
        self.portfolio_optimizer = None
        self.market_condition_detector = None
        
        # Initialize internal state
        self.active_instruments = {}  # Dict of symbol -> market data
        self.market_conditions = {}   # Dict of symbol -> market condition
        self.positions = []           # List of current positions
        self.account_info = {}        # Current account information
        self.performance_metrics = {} # Performance by symbol and strategy
        
        # Initialize managers if provided in config
        self._initialize_managers()
        
        self.logger.info("MultiAssetIntegrator initialized")
    
    def _initialize_managers(self):
        """Initialize all required managers for multi-asset trading"""
        # Initialize correlation manager
        if self.correlation_config:
            self.correlation_manager = CorrelationManager(self.correlation_config)
            self.logger.info("Correlation manager initialized")
            
        # Initialize session manager
        if self.session_config:
            self.session_manager = SessionManager(self.session_config)
            self.logger.info("Session manager initialized")
            
        # Initialize portfolio optimizer
        if self.portfolio_config:
            self.portfolio_optimizer = PortfolioOptimizer(self.portfolio_config)
            self.logger.info("Portfolio optimizer initialized")
            
    def set_market_condition_detector(self, detector) -> None:
        """
        Connect to market condition detector for enhanced signal validation
        
        Args:
            detector: MarketConditionDetector instance
        """
        self.market_condition_detector = detector
        self.logger.info("Connected to MarketConditionDetector")
    
    def update_market_data(self, symbol: str, data: pd.DataFrame) -> None:
        """
        Update market data for a specific symbol
        
        Args:
            symbol: Trading symbol
            data: DataFrame with market data
        """
        if data is None or data.empty:
            return
            
        # Store updated data
        self.active_instruments[symbol] = data
        
        # If we have a market condition detector, analyze the latest data
        if self.market_condition_detector and hasattr(self.market_condition_detector, 'detect_market_condition'):
            try:
                # Get market condition for this symbol
                condition = self.market_condition_detector.detect_market_condition(symbol, data)
                
                if condition:
                    # Update internal market conditions
                    self.market_conditions[symbol] = condition
                    
                    # Update performance metrics
                    self._update_instrument_performance(symbol, condition)
                    
            except Exception as e:
                self.logger.error(f"Error analyzing market condition for {symbol}: {str(e)}")
                
        self.logger.debug(f"Updated market data for {symbol}")
    
    def update_market_conditions(self, conditions: Dict[str, Dict]) -> None:
        """
        Update market conditions for all symbols
        
        Args:
            conditions: Dictionary of symbol -> condition
        """
        if not conditions:
            return
            
        # Update internal market conditions
        self.market_conditions.update(conditions)
        
        # Update trading candidates based on new conditions
        self._refresh_trading_candidates()
        
        self.logger.debug(f"Updated market conditions for {len(conditions)} symbols")
    
    def update_positions(self, positions: List[Dict]) -> None:
        """
        Update current positions
        
        Args:
            positions: List of position dictionaries
        """
        self.positions = positions
        
        # Update correlation exposure if we have a correlation manager
        if self.correlation_manager:
            self.correlation_manager.update_positions(positions)
            
        # Update portfolio allocation if we have a portfolio optimizer
        if self.portfolio_optimizer:
            self.portfolio_optimizer.update_positions(positions)
            
        self.logger.debug(f"Updated {len(positions)} active positions")
    
    def update_account_info(self, account_info: Dict) -> None:
        """
        Update account information
        
        Args:
            account_info: Dictionary with account details
        """
        self.account_info = account_info
        
        # Update portfolio optimizer with account balance
        if self.portfolio_optimizer and 'balance' in account_info:
            self.portfolio_optimizer.update_account_balance(account_info['balance'])
            
        self.logger.debug("Updated account information")
    
    def _update_instrument_performance(self, symbol: str, condition: Dict) -> None:
        """
        Update performance metrics for an instrument based on market conditions
        
        Args:
            symbol: Trading symbol
            condition: Market condition dictionary
        """
        if symbol not in self.performance_metrics:
            self.performance_metrics[symbol] = {
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'favorable_count': 0,
                'unfavorable_count': 0,
                'volatility_history': [],
                'trend_history': [],
                'confidence_history': []
            }
            
        # Update performance metrics
        metrics = self.performance_metrics[symbol]
        
        # Track condition history
        if 'volatility' in condition:
            metrics['volatility_history'].append(condition['volatility'])
            # Keep history limited to last 20 values
            metrics['volatility_history'] = metrics['volatility_history'][-20:]
            
        if 'trend' in condition:
            metrics['trend_history'].append(condition['trend'])
            # Keep history limited to last 20 values
            metrics['trend_history'] = metrics['trend_history'][-20:]
            
        if 'confidence' in condition:
            metrics['confidence_history'].append(condition['confidence'])
            # Keep history limited to last 20 values
            metrics['confidence_history'] = metrics['confidence_history'][-20:]
            
        # Track favorability
        if condition.get('should_trade', False):
            metrics['favorable_count'] += 1
        else:
            metrics['unfavorable_count'] += 1
    
    def get_trading_candidates(self) -> List[str]:
        """
        Get optimal symbols to trade based on current market conditions,
        session times, correlation constraints, and portfolio allocation.
        
        Returns:
            List of symbol strings to consider for trading
        """
        candidates = []
        now = datetime.now()
        
        # Filter by active session if we have a session manager
        active_session_symbols = self._get_active_session_symbols(now)
        
        # Start with all symbols with favorable market conditions
        for symbol, condition in self.market_conditions.items():
            # Skip if not in active session
            if active_session_symbols and symbol not in active_session_symbols:
                continue
                
            # Check if conditions are favorable for trading
            confidence = condition.get('confidence', 0)
            should_trade = condition.get('should_trade', False)
            
            # Determine if we should include this symbol
            min_confidence = self.config.get('trading', {}).get('min_confidence', 0.6)
            
            if should_trade and confidence >= min_confidence:
                candidates.append(symbol)
                
        # Filter out symbols with high correlation to existing positions
        if self.correlation_manager and self.positions:
            # Get symbols from existing positions
            position_symbols = [p.get('symbol') for p in self.positions]
            
            # Filter candidates by correlation constraints
            candidates = self.correlation_manager.filter_by_correlation(
                candidates, 
                position_symbols
            )
            
        # Limit number of candidates based on config
        max_candidates = self.config.get('trading', {}).get('max_trading_candidates', 5)
        
        # If we have more candidates than allowed, prioritize by market confidence
        if len(candidates) > max_candidates:
            # Sort by confidence (highest first)
            candidates_with_confidence = [(s, self.market_conditions.get(s, {}).get('confidence', 0))
                                          for s in candidates]
            candidates_with_confidence.sort(key=lambda x: x[1], reverse=True)
            
            # Take top N candidates
            candidates = [c[0] for c in candidates_with_confidence[:max_candidates]]
            
        # Log the selected candidates
        self.logger.info(f"Selected {len(candidates)} trading candidates: {candidates}")
        
        return candidates
    
    def _get_active_session_symbols(self, current_time: datetime) -> List[str]:
        """
        Get symbols that are active in the current trading session
        
        Args:
            current_time: Current datetime
            
        Returns:
            List of symbols active in current session
        """
        if not self.session_manager:
            return []
            
        # Get active trading sessions
        active_sessions = self.session_manager.get_active_sessions(current_time)
        
        if not active_sessions:
            return []
            
        # Get symbols for active sessions
        session_symbols = []
        for session_name in active_sessions:
            symbols = self.session_manager.get_session_symbols(session_name)
            session_symbols.extend(symbols)
            
        return list(set(session_symbols))  # Remove duplicates
    
    def _refresh_trading_candidates(self) -> None:
        """
        Refresh the internal list of trading candidates based on current conditions
        """
        # This method can be used to update cache or notify other components
        # about changes in trading candidates
        pass
    
    def select_strategy(self, symbol: str) -> str:
        """
        Select the optimal trading strategy based on current market conditions
        and instrument type (forex vs synthetic).
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Strategy name string
        """
        # Get market conditions for this symbol
        conditions = self.market_conditions.get(symbol, {})
        
        # Default strategy (fallback)
        default_strategy = 'ScalpingStrategy'
        
        # If no conditions available, return default
        if not conditions:
            return default_strategy
            
        # Determine instrument type (forex vs synthetic)
        is_synthetic = 'SYNTH' in symbol or 'R_' in symbol or 'BOOM' in symbol or 'CRASH' in symbol
        
        # Get relevant market factors
        trend = conditions.get('trend', 'unknown')
        volatility = conditions.get('volatility', 'unknown')
        liquidity = conditions.get('liquidity', 'unknown')
        
        # Strategy weights from configuration
        strategy_weights = {}
        
        if is_synthetic:
            strategy_weights = self.config.get('strategies', {}).get('synthetic_weights', {})
        else:
            strategy_weights = self.config.get('strategies', {}).get('forex_weights', {})
            
        # If no weights defined, use default strategy
        if not strategy_weights:
            return default_strategy
            
        # Calculate scores for each strategy based on market conditions
        strategy_scores = {}
        
        for strategy_name, weights in strategy_weights.items():
            # Initialize score
            score = 0
            
            # Add trend score
            if trend != 'unknown' and 'trend' in weights:
                trend_weights = weights['trend']
                if trend in trend_weights:
                    score += trend_weights[trend]
                    
            # Add volatility score
            if volatility != 'unknown' and 'volatility' in weights:
                volatility_weights = weights['volatility']
                if volatility in volatility_weights:
                    score += volatility_weights[volatility]
                    
            # Add liquidity score
            if liquidity != 'unknown' and 'liquidity' in weights:
                liquidity_weights = weights['liquidity']
                if liquidity in liquidity_weights:
                    score += liquidity_weights[liquidity]
                    
            # Store final score
            strategy_scores[strategy_name] = score
            
        # If we have scores, select the strategy with highest score
        if strategy_scores:
            best_strategy = max(strategy_scores.items(), key=lambda x: x[1])
            
            # Only return if score is positive
            if best_strategy[1] > 0:
                return best_strategy[0]
                
        # If no strategy found or all have zero/negative scores, return default
        return default_strategy
    
    def validate_new_position(self, symbol: str, direction: str, size: float) -> Tuple[bool, str]:
        """
        Validate a new position against correlation constraints, session times,
        and market conditions.
        
        Args:
            symbol: Trading symbol
            direction: Trade direction ('BUY' or 'SELL')
            size: Position size
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        # Check if we have market conditions for this symbol
        if symbol not in self.market_conditions:
            return False, "No market conditions available for this symbol"
            
        # Get market conditions
        conditions = self.market_conditions[symbol]
        
        # Check market confidence
        confidence = conditions.get('confidence', 0)
        min_confidence = self.config.get('trading', {}).get('min_confidence', 0.6)
        
        if confidence < min_confidence:
            return False, f"Market confidence too low: {confidence:.2f} < {min_confidence:.2f}"
            
        # Check if direction aligns with market trend
        trend = conditions.get('trend', 'unknown')
        
        if trend != 'unknown':
            if direction == 'BUY' and trend in ['bearish', 'strong_bearish']:
                return False, f"Direction {direction} conflicts with {trend} trend"
                
            if direction == 'SELL' and trend in ['bullish', 'strong_bullish']:
                return False, f"Direction {direction} conflicts with {trend} trend"
                
        # Check session constraints
        if self.session_manager:
            now = datetime.now()
            active_sessions = self.session_manager.get_active_sessions(now)
            
            # Get symbols allowed in current session
            allowed_symbols = []
            for session in active_sessions:
                allowed_symbols.extend(self.session_manager.get_session_symbols(session))
                
            if symbol not in allowed_symbols:
                return False, f"Symbol {symbol} not allowed in current session"
                
        # Check correlation constraints
        if self.correlation_manager and self.positions:
            # Get existing position symbols and directions
            existing_positions = []
            for pos in self.positions:
                existing_positions.append({
                    'symbol': pos.get('symbol', ''),
                    'direction': pos.get('direction', '')
                })
                
            # Check if new position violates correlation constraints
            correlation_valid, reason = self.correlation_manager.validate_new_position(
                symbol, direction, existing_positions
            )
            
            if not correlation_valid:
                return False, reason
                
        # Check portfolio allocation
        if self.portfolio_optimizer:
            # Get current allocation for this symbol
            current_allocation = self.portfolio_optimizer.get_symbol_allocation(symbol)
            
            # Calculate the new allocation with this position
            new_allocation = current_allocation + size
            
            # Check if it exceeds the maximum allocation
            max_allocation = self.portfolio_optimizer.get_max_allocation(symbol)
            
            if new_allocation > max_allocation:
                return False, f"Position would exceed maximum allocation for {symbol}"
                
        # All checks passed
        return True, ""
    
    def get_position_allocation(self, symbol: str) -> float:
        """
        Get position size allocation multiplier based on market conditions,
        portfolio allocation, and correlation constraints.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Allocation multiplier (0-1) to apply to base position size
        """
        # Default allocation (100%)
        allocation = 1.0
        
        # Adjust based on market conditions
        conditions = self.market_conditions.get(symbol, {})
        
        if conditions:
            # Adjust by market confidence
            confidence = conditions.get('confidence', 0.5)
            allocation *= min(1.0, confidence + 0.2)  # Apply confidence with slight boost
            
            # Adjust by volatility
            volatility = conditions.get('volatility', 'medium')
            volatility_factor = {
                'low': 0.8,
                'medium': 1.0,
                'high': 0.7  # Reduce position size in high volatility
            }.get(volatility, 1.0)
            
            allocation *= volatility_factor
            
        # Adjust based on portfolio allocation if available
        if self.portfolio_optimizer:
            portfolio_factor = self.portfolio_optimizer.get_allocation_factor(symbol)
            allocation *= portfolio_factor
            
        # Ensure allocation is between 0.1 and 1.0
        allocation = max(0.1, min(1.0, allocation))
        
        self.logger.debug(f"Position allocation for {symbol}: {allocation:.2f}")
        
        return allocation
    
    def process_trade_result(self, result: Dict) -> None:
        """
        Process a trade result to update performance metrics
        
        Args:
            result: Dictionary with trade result data
        """
        if not result:
            return
            
        # Extract trade data
        symbol = result.get('symbol')
        is_win = result.get('is_win', False)
        pnl = result.get('pnl', 0)
        
        if not symbol:
            return
            
        # Update symbol performance metrics
        if symbol not in self.performance_metrics:
            self.performance_metrics[symbol] = {
                'trades': 0,
                'wins': 0,
                'losses': 0
            }
            
        metrics = self.performance_metrics[symbol]
        metrics['trades'] += 1
        
        if is_win:
            metrics['wins'] += 1
        else:
            metrics['losses'] += 1
            
        # Update strategy performance if available
        strategy = result.get('strategy')
        
        if strategy:
            if 'strategies' not in self.performance_metrics:
                self.performance_metrics['strategies'] = {}
                
            if strategy not in self.performance_metrics['strategies']:
                self.performance_metrics['strategies'][strategy] = {
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'pnl': 0
                }
                
            # Update strategy metrics
            strategy_metrics = self.performance_metrics['strategies'][strategy]
            strategy_metrics['trades'] += 1
            
            if is_win:
                strategy_metrics['wins'] += 1
            else:
                strategy_metrics['losses'] += 1
                
            strategy_metrics['pnl'] += pnl
            
        self.logger.debug(f"Processed trade result for {symbol} (win: {is_win}, pnl: {pnl})")
    
    def get_performance_summary(self) -> Dict:
        """
        Get summary of trading performance across all symbols and strategies
        
        Returns:
            Dictionary with performance metrics
        """
        # Overall metrics
        total_trades = 0
        total_wins = 0
        total_losses = 0
        total_pnl = 0
        
        # Calculate symbol metrics
        for symbol, metrics in self.performance_metrics.items():
            if symbol == 'strategies':
                continue
                
            total_trades += metrics.get('trades', 0)
            total_wins += metrics.get('wins', 0)
            total_losses += metrics.get('losses', 0)
            
        # Calculate strategy metrics
        strategy_performance = {}
        
        if 'strategies' in self.performance_metrics:
            for strategy, metrics in self.performance_metrics['strategies'].items():
                strategy_trades = metrics.get('trades', 0)
                strategy_wins = metrics.get('wins', 0)
                strategy_pnl = metrics.get('pnl', 0)
                
                if strategy_trades > 0:
                    win_rate = strategy_wins / strategy_trades
                else:
                    win_rate = 0
                    
                strategy_performance[strategy] = {
                    'trades': strategy_trades,
                    'win_rate': win_rate,
                    'pnl': strategy_pnl
                }
                
                total_pnl += strategy_pnl
        
        # Calculate overall win rate
        win_rate = total_wins / total_trades if total_trades > 0 else 0
        
        # Prepare summary
        summary = {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'strategies': strategy_performance,
            'timestamp': datetime.now().isoformat()
        }
        
        return summary
        
    def get_favorable_market_conditions(self) -> Dict[str, Dict]:
        """
        Get symbols with favorable market conditions for trading
        
        Returns:
            Dictionary of symbols with their market conditions
        """
        favorable_conditions = {}
        
        for symbol, conditions in self.market_conditions.items():
            # Check if conditions are favorable for trading
            confidence = conditions.get('confidence', 0)
            should_trade = conditions.get('should_trade', False)
            
            min_confidence = self.config.get('trading', {}).get('min_confidence', 0.6)
            
            if should_trade and confidence >= min_confidence:
                favorable_conditions[symbol] = conditions
                
        return favorable_conditions
    
    def get_active_positions_summary(self) -> Dict:
        """
        Get a summary of currently active positions
        
        Returns:
            Dictionary with position summary data
        """
        # Count positions by direction
        buy_positions = 0
        sell_positions = 0
        total_exposure = 0
        
        # Group by symbol
        symbols = {}
        
        for position in self.positions:
            symbol = position.get('symbol', '')
            direction = position.get('direction', '')
            volume = position.get('volume', 0)
            profit = position.get('profit', 0)
            
            # Count by direction
            if direction == 'BUY':
                buy_positions += 1
            elif direction == 'SELL':
                sell_positions += 1
                
            # Add to exposure
            total_exposure += volume
            
            # Add to symbols
            if symbol not in symbols:
                symbols[symbol] = {
                    'count': 0,
                    'volume': 0,
                    'profit': 0,
                    'buy_count': 0,
                    'sell_count': 0
                }
                
            symbols[symbol]['count'] += 1
            symbols[symbol]['volume'] += volume
            symbols[symbol]['profit'] += profit
            
            if direction == 'BUY':
                symbols[symbol]['buy_count'] += 1
            elif direction == 'SELL':
                symbols[symbol]['sell_count'] += 1
                
        # Create summary
        summary = {
            'total_positions': len(self.positions),
            'buy_positions': buy_positions,
            'sell_positions': sell_positions,
            'total_exposure': total_exposure,
            'symbols': symbols,
            'timestamp': datetime.now().isoformat()
        }
        
        return summary
    
    def get_trading_opportunities(self) -> List[Dict]:
        """
        Get potential trading opportunities based on current market conditions
        
        Returns:
            List of trading opportunity dictionaries
        """
        opportunities = []
        
        # Get trading candidates
        candidates = self.get_trading_candidates()
        
        for symbol in candidates:
            # Skip if we don't have market conditions
            if symbol not in self.market_conditions:
                continue
                
            conditions = self.market_conditions[symbol]
            
            # Determine potential direction based on trend
            trend = conditions.get('trend', 'unknown')
            potential_direction = None
            
            if trend in ['bullish', 'strong_bullish']:
                potential_direction = 'BUY'
            elif trend in ['bearish', 'strong_bearish']:
                potential_direction = 'SELL'
                
            # Skip if no clear direction
            if not potential_direction:
                continue
                
            # Get optimal strategy
            strategy = self.select_strategy(symbol)
            
            # Get allocation factor
            allocation = self.get_position_allocation(symbol)
            
            # Create opportunity
            opportunity = {
                'symbol': symbol,
                'direction': potential_direction,
                'confidence': conditions.get('confidence', 0),
                'strategy': strategy,
                'allocation_factor': allocation,
                'market_conditions': {
                    'trend': trend,
                    'volatility': conditions.get('volatility', 'unknown'),
                    'liquidity': conditions.get('liquidity', 'unknown')
                }
            }
            
            opportunities.append(opportunity)
            
        # Sort by confidence (highest first)
        opportunities.sort(key=lambda x: x['confidence'], reverse=True)
        
        return opportunities
    
    def get_portfolio_allocation(self) -> Dict:
        """
        Get current portfolio allocation across symbols
        
        Returns:
            Dictionary with portfolio allocation data
        """
        allocation = {}
        
        # If we have a portfolio optimizer, use it
        if self.portfolio_optimizer:
            allocation = self.portfolio_optimizer.get_current_allocation()
        else:
            # Calculate basic allocation based on positions
            total_volume = sum(p.get('volume', 0) for p in self.positions)
            
            if total_volume > 0:
                # Group by symbol
                for position in self.positions:
                    symbol = position.get('symbol', '')
                    volume = position.get('volume', 0)
                    
                    if symbol not in allocation:
                        allocation[symbol] = 0
                        
                    allocation[symbol] += volume / total_volume
                    
        return {
            'allocation': allocation,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_network_status_data(self) -> Dict:
        """
        Get data to be shared with network clients about the current trading status
        
        Returns:
            Dictionary with trading status data for network sharing
        """
        # Get performance summary
        performance = self.get_performance_summary()
        
        # Get market conditions
        favorable_conditions = self.get_favorable_market_conditions()
        
        # Get position summary
        positions = self.get_active_positions_summary()
        
        # Get trading opportunities
        opportunities = self.get_trading_opportunities()
        
        # Get portfolio allocation
        allocation = self.get_portfolio_allocation()
        
        # Compile network status data
        status_data = {
            'performance': performance,
            'market_conditions': {
                'count': len(favorable_conditions),
                'symbols': list(favorable_conditions.keys())
            },
            'positions': positions,
            'opportunities': {
                'count': len(opportunities),
                'symbols': [o['symbol'] for o in opportunities[:5]]  # Top 5 opportunities
            },
            'portfolio': allocation,
            'timestamp': datetime.now().isoformat()
        }
        
        return status_data
        
    def refresh_all_data(self) -> Dict:
        """
        Refresh all internal data and return a comprehensive state summary.
        This method is useful for synchronizing with network clients.
        
        Returns:
            Dictionary with complete trading state
        """
        # Get trading candidates
        candidates = self.get_trading_candidates()
        
        # Get performance metrics
        performance = self.get_performance_summary()
        
        # Get favorable market conditions
        market_conditions = self.get_favorable_market_conditions()
        
        # Get position summary
        positions = self.get_active_positions_summary()
        
        # Get trading opportunities
        opportunities = self.get_trading_opportunities()
        
        # Create state summary
        state = {
            'trading_candidates': candidates,
            'performance': performance,
            'market_conditions': market_conditions,
            'positions': positions,
            'opportunities': opportunities,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info("Refreshed all trading data")
        
        return state
