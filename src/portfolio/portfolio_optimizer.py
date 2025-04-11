"""
Portfolio Optimizer
Optimizes trading portfolio across both Forex and synthetic indices
based on correlation data, session timing, and performance metrics.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime, timedelta
from loguru import logger
from collections import defaultdict
import json
import os

class PortfolioOptimizer:
    """
    Optimizes trading portfolio by managing instrument allocation,
    position sizing, and risk distribution across different asset classes.
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize the portfolio optimizer
        
        Args:
            config: Configuration dictionary with portfolio settings
        """
        self.config = config or {}
        
        # Portfolio configuration
        self.max_active_instruments = self.config.get('max_active_instruments', 10)
        self.max_same_category = self.config.get('max_same_category', 5)
        self.max_position_per_instrument = self.config.get('max_position_per_instrument', 2)
        self.base_allocation = self.config.get('base_allocation', {
            'forex': 0.6,
            'synthetic': 0.4
        })
        
        # Current portfolio status
        self.instrument_metrics = {}
        self.current_allocation = {
            'forex': [],
            'synthetic': []
        }
        
        # Performance tracking
        self.instrument_performance = defaultdict(lambda: {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'profit': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'win_rate': 0.0,
            'expectancy': 0.0,
            'sharpe': 0.0,
            'score': 50.0  # Neutral starting score
        })
        
        # Allocation adjustment periods
        self.rebalance_frequency_hours = self.config.get('rebalance_frequency_hours', 24)
        self.performance_decay_factor = self.config.get('performance_decay_factor', 0.95)
        self.last_rebalance_time = None
        
        # Performance data file path
        self.performance_data_file = os.path.join(
            self.config.get('data_dir', 'data'), 
            'instrument_performance.json'
        )
        
        # Load performance data if available
        self._load_performance_data()
        
        logger.info("Portfolio Optimizer initialized")
    
    def update_instrument_metrics(self, 
                                symbol: str, 
                                category: str, 
                                metrics: Dict) -> None:
        """
        Update metrics for a specific instrument
        
        Args:
            symbol: Instrument symbol
            category: Instrument category ('forex' or 'synthetic')
            metrics: Dictionary of metrics including volatility, spread, etc.
        """
        if symbol not in self.instrument_metrics:
            self.instrument_metrics[symbol] = {
                'category': category,
                'volatility': 0.0,
                'spread': 0.0,
                'volume': 0.0,
                'trend_strength': 0.0,
                'score': 50.0  # Neutral starting score
            }
        
        # Update metrics
        metrics_obj = self.instrument_metrics[symbol]
        for key, value in metrics.items():
            if key in metrics_obj:
                metrics_obj[key] = value
        
        # Recalculate instrument score
        self._calculate_instrument_score(symbol)
    
    def update_trade_result(self, 
                          trade_data: Dict) -> None:
        """
        Update performance data based on a completed trade
        
        Args:
            trade_data: Dictionary with trade result information
        """
        symbol = trade_data.get('symbol')
        if not symbol:
            logger.warning("Trade data missing symbol")
            return
        
        profit = trade_data.get('profit', 0.0)
        
        # Get existing performance data
        perf = self.instrument_performance[symbol]
        
        # Update trade counts
        perf['trades'] += 1
        if profit > 0:
            perf['wins'] += 1
            # Update average win
            perf['avg_win'] = ((perf['avg_win'] * (perf['wins'] - 1)) + profit) / perf['wins']
        else:
            perf['losses'] += 1
            # Update average loss (store as positive value)
            perf['avg_loss'] = ((perf['avg_loss'] * (perf['losses'] - 1)) + abs(profit)) / perf['losses']
        
        # Update profit
        perf['profit'] += profit
        
        # Recalculate metrics
        if perf['trades'] > 0:
            perf['win_rate'] = perf['wins'] / perf['trades']
            
            # Calculate expectancy
            if perf['losses'] > 0:
                perf['expectancy'] = (perf['win_rate'] * perf['avg_win']) - ((1 - perf['win_rate']) * perf['avg_loss'])
            
            # Update score
            self._calculate_performance_score(symbol)
        
        # Save updated performance data
        self._save_performance_data()
    
    def optimize_portfolio(self,
                         session_manager,
                         correlation_manager,
                         active_positions: List[Dict] = None,
                         account_balance: float = None,
                         market_data: Dict = None) -> Dict:
        """
        Optimize portfolio allocation based on session, correlation, and performance data
        
        Args:
            session_manager: Session manager instance
            correlation_manager: Correlation manager instance
            active_positions: List of currently active trading positions
            account_balance: Current account balance
            market_data: Current market data
            
        Returns:
            Dictionary with optimized portfolio allocation
        """
        active_positions = active_positions or []
        
        # Check if rebalance is needed
        current_time = datetime.now()
        if self.last_rebalance_time is None:
            should_rebalance = True
        else:
            hours_since_rebalance = (current_time - self.last_rebalance_time).total_seconds() / 3600
            should_rebalance = hours_since_rebalance >= self.rebalance_frequency_hours
        
        # Get active instruments from session manager
        session_instruments = session_manager.get_active_instruments(market_data, account_balance)
        
        if should_rebalance:
            # Perform full rebalance
            self._decay_performance_scores()
            optimized_allocation = self._rebalance_portfolio(
                session_instruments, 
                correlation_manager,
                active_positions
            )
            self.last_rebalance_time = current_time
            
            # Update current allocation
            self.current_allocation = optimized_allocation
            
            logger.info("Portfolio rebalanced")
            return optimized_allocation
        else:
            # Make incremental adjustments
            optimized_allocation = self._adjust_current_allocation(
                session_instruments,
                correlation_manager,
                active_positions
            )
            return optimized_allocation
    
    def get_instrument_allocations(self) -> Dict[str, float]:
        """
        Get recommended position size allocations for each instrument
        
        Returns:
            Dictionary mapping instrument symbols to allocation percentages
        """
        allocations = {}
        
        # Flatten current allocations
        all_instruments = []
        for category, instruments in self.current_allocation.items():
            all_instruments.extend(instruments)
        
        # Equal allocation if no instruments
        if not all_instruments:
            return allocations
        
        # Base allocation per instrument
        base_per_instrument = 1.0 / len(all_instruments)
        
        # Adjust based on performance scores
        total_score = 0
        for symbol in all_instruments:
            # Get performance score (default 50 if not available)
            perf_score = self.instrument_performance[symbol].get('score', 50.0)
            total_score += perf_score
        
        # Calculate allocations proportional to scores
        if total_score > 0:
            for symbol in all_instruments:
                perf_score = self.instrument_performance[symbol].get('score', 50.0)
                allocations[symbol] = (perf_score / total_score) 
        else:
            # Equal allocation if no score data
            for symbol in all_instruments:
                allocations[symbol] = base_per_instrument
        
        return allocations
    
    def get_top_performing_instruments(self, category: str = None, limit: int = 5) -> List[Dict]:
        """
        Get the top performing instruments
        
        Args:
            category: Optional category filter ('forex' or 'synthetic')
            limit: Maximum number of instruments to return
            
        Returns:
            List of dictionaries with performance data
        """
        # Filter by category if specified
        instruments = []
        for symbol, perf in self.instrument_performance.items():
            # Skip if trades count is too low
            if perf['trades'] < 5:
                continue
                
            # Skip if category doesn't match
            if category and symbol in self.instrument_metrics:
                if self.instrument_metrics[symbol]['category'] != category:
                    continue
            
            instruments.append({
                'symbol': symbol,
                'win_rate': perf['win_rate'],
                'expectancy': perf['expectancy'],
                'profit': perf['profit'],
                'trades': perf['trades'],
                'score': perf['score']
            })
        
        # Sort by score (descending)
        instruments.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top N instruments
        return instruments[:limit]
    
    def get_portfolio_summary(self) -> Dict:
        """
        Get summary of current portfolio allocation and performance
        
        Returns:
            Dictionary with portfolio summary information
        """
        # Count allocations by category
        forex_count = len(self.current_allocation['forex'])
        synthetic_count = len(self.current_allocation['synthetic'])
        total_instruments = forex_count + synthetic_count
        
        # Calculate category percentages
        forex_pct = 0
        synthetic_pct = 0
        if total_instruments > 0:
            forex_pct = (forex_count / total_instruments) * 100
            synthetic_pct = (synthetic_count / total_instruments) * 100
        
        # Get top instruments
        top_forex = self.get_top_performing_instruments('forex', 3)
        top_synthetic = self.get_top_performing_instruments('synthetic', 3)
        
        return {
            'total_instruments': total_instruments,
            'forex_count': forex_count,
            'synthetic_count': synthetic_count,
            'forex_percent': forex_pct,
            'synthetic_percent': synthetic_pct,
            'portfolio_balance': 'Balanced' if abs(forex_pct - synthetic_pct) < 20 else (
                'Forex-Focused' if forex_pct > synthetic_pct else 'Synthetic-Focused'
            ),
            'top_forex': top_forex,
            'top_synthetic': top_synthetic,
            'last_rebalance': self.last_rebalance_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_rebalance_time else 'Never'
        }
    
    def _calculate_instrument_score(self, symbol: str) -> float:
        """
        Calculate a score for an instrument based on its metrics
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            Score value (0-100)
        """
        if symbol not in self.instrument_metrics:
            return 50.0  # Neutral score
        
        metrics = self.instrument_metrics[symbol]
        
        # Basic score calculation
        # - Lower spread is better (0-1 normalized and inverted)
        # - Higher volume is better (0-1 normalized)
        # - Moderate volatility is best (peak at 0.5)
        # - Stronger trends are better (0-1 normalized)
        
        spread_score = max(0, 1 - (metrics.get('spread', 0) / 0.0005))  # 0.0005 = 5 pips
        volume_score = min(1, metrics.get('volume', 0) / 1000)
        
        # Volatility score peaks at moderate volatility (0.5)
        vol = metrics.get('volatility', 0.5)
        volatility_score = 1 - abs(vol - 0.5) * 2
        
        trend_score = metrics.get('trend_strength', 0.5)
        
        # Combine scores with weights
        weights = {
            'spread': 0.3,
            'volume': 0.2,
            'volatility': 0.2,
            'trend': 0.3
        }
        
        combined_score = (
            spread_score * weights['spread'] +
            volume_score * weights['volume'] +
            volatility_score * weights['volatility'] +
            trend_score * weights['trend']
        )
        
        # Scale to 0-100
        final_score = combined_score * 100
        
        # Store the score
        metrics['score'] = final_score
        
        return final_score
    
    def _calculate_performance_score(self, symbol: str) -> float:
        """
        Calculate performance score for an instrument
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            Performance score (0-100)
        """
        if symbol not in self.instrument_performance:
            return 50.0
        
        perf = self.instrument_performance[symbol]
        
        # Need minimum number of trades for reliable scoring
        if perf['trades'] < 5:
            return 50.0
        
        # Scoring components
        # - Win rate (higher is better)
        # - Expectancy (higher is better)
        # - Risk-adjusted return (higher is better)
        
        win_rate_score = perf['win_rate'] * 100
        
        # Expectancy score (normalize around reasonable expectancy values)
        # 0.5 R expectancy would be a score of 50
        expectancy_score = min(100, max(0, perf['expectancy'] * 100))
        
        # Risk-adjusted return (simple Sharpe-like measure)
        if perf['avg_loss'] > 0:
            risk_adjusted = perf['avg_win'] / perf['avg_loss']
            risk_score = min(100, risk_adjusted * 50)
        else:
            risk_score = 100
        
        # Combine with weights
        weights = {
            'win_rate': 0.3,
            'expectancy': 0.5,
            'risk_adjusted': 0.2
        }
        
        combined_score = (
            win_rate_score * weights['win_rate'] +
            expectancy_score * weights['expectancy'] +
            risk_score * weights['risk_adjusted']
        )
        
        # Store the score
        perf['score'] = combined_score
        
        return combined_score
    
    def _decay_performance_scores(self) -> None:
        """Decay performance scores over time to favor recent results"""
        for symbol, perf in self.instrument_performance.items():
            # Apply decay factor to score
            if 'score' in perf and perf['score'] != 50.0:
                # Move score toward neutral (50)
                current = perf['score']
                distance_to_neutral = current - 50.0
                perf['score'] = current - (distance_to_neutral * (1 - self.performance_decay_factor))
    
    def _rebalance_portfolio(self,
                           session_instruments: Dict[str, List[str]],
                           correlation_manager,
                           active_positions: List[Dict]) -> Dict:
        """
        Perform full portfolio rebalance
        
        Args:
            session_instruments: Dictionary of active instruments by category
            correlation_manager: Correlation manager instance
            active_positions: List of active positions
            
        Returns:
            Dictionary with optimized allocations by category
        """
        # Extract active symbols from positions
        active_symbols = {pos['symbol'] for pos in active_positions}
        
        # Candidate instruments with their scores
        candidates = {
            'forex': [],
            'synthetic': []
        }
        
        # Process forex instruments
        for symbol in session_instruments.get('forex', []):
            # Calculate score based on performance and metrics
            perf_score = self.instrument_performance[symbol].get('score', 50.0)
            metric_score = 50.0
            if symbol in self.instrument_metrics:
                metric_score = self.instrument_metrics[symbol].get('score', 50.0)
            
            # Combined score (70% performance, 30% metrics)
            combined_score = (perf_score * 0.7) + (metric_score * 0.3)
            
            candidates['forex'].append((symbol, combined_score))
        
        # Process synthetic instruments
        for symbol in session_instruments.get('synthetic', []):
            # Calculate score based on performance and metrics
            perf_score = self.instrument_performance[symbol].get('score', 50.0)
            metric_score = 50.0
            if symbol in self.instrument_metrics:
                metric_score = self.instrument_metrics[symbol].get('score', 50.0)
            
            # Combined score (70% performance, 30% metrics)
            combined_score = (perf_score * 0.7) + (metric_score * 0.3)
            
            candidates['synthetic'].append((symbol, combined_score))
        
        # Sort candidates by score
        for category in candidates:
            candidates[category].sort(key=lambda x: x[1], reverse=True)
        
        # Determine allocation counts
        forex_allocation = int(self.base_allocation['forex'] * self.max_active_instruments)
        synthetic_allocation = int(self.base_allocation['synthetic'] * self.max_active_instruments)
        
        # Ensure at least one of each category
        forex_allocation = max(1, forex_allocation)
        synthetic_allocation = max(1, synthetic_allocation)
        
        # Adjust to ensure total does not exceed max
        total_allocation = forex_allocation + synthetic_allocation
        if total_allocation > self.max_active_instruments:
            # Scale back proportionally
            scaling_factor = self.max_active_instruments / total_allocation
            forex_allocation = max(1, int(forex_allocation * scaling_factor))
            synthetic_allocation = max(1, int(synthetic_allocation * scaling_factor))
        
        # Select top instruments while avoiding high correlations
        selected_forex = self._select_uncorrelated_instruments(
            candidates['forex'],
            correlation_manager,
            forex_allocation,
            active_symbols
        )
        
        selected_synthetic = self._select_uncorrelated_instruments(
            candidates['synthetic'],
            correlation_manager,
            synthetic_allocation,
            active_symbols
        )
        
        # Ensure active symbols stay in portfolio
        for symbol in active_symbols:
            # Check if it's a forex pair
            is_forex = any(symbol in session_instruments['forex'])
            is_synthetic = any(symbol in session_instruments['synthetic'])
            
            if is_forex and symbol not in selected_forex:
                # Add to forex, possibly removing lowest-scored instrument
                if len(selected_forex) >= forex_allocation:
                    selected_forex.pop()
                selected_forex.append(symbol)
            
            elif is_synthetic and symbol not in selected_synthetic:
                # Add to synthetic, possibly removing lowest-scored instrument
                if len(selected_synthetic) >= synthetic_allocation:
                    selected_synthetic.pop()
                selected_synthetic.append(symbol)
        
        return {
            'forex': selected_forex,
            'synthetic': selected_synthetic
        }
    
    def _select_uncorrelated_instruments(self,
                                       candidates: List[Tuple[str, float]],
                                       correlation_manager,
                                       max_count: int,
                                       must_include: Set[str] = None) -> List[str]:
        """
        Select instruments while minimizing correlation
        
        Args:
            candidates: List of (symbol, score) tuples
            correlation_manager: Correlation manager instance
            max_count: Maximum instruments to select
            must_include: Set of symbols that must be included
            
        Returns:
            List of selected symbols
        """
        must_include = must_include or set()
        
        # Start with empty selection
        selected = []
        
        # First add all must-include symbols
        for symbol in must_include:
            if len(selected) < max_count:
                selected.append(symbol)
        
        # If selection is already full, return
        if len(selected) >= max_count:
            return selected
        
        # Track symbols we've already considered
        considered = set(selected)
        
        # For each candidate
        for symbol, score in candidates:
            # Skip if already considered
            if symbol in considered:
                continue
            
            # Check if correlated with any selected symbol
            is_correlated = False
            for selected_symbol in selected:
                correlation = abs(correlation_manager.get_correlation(symbol, selected_symbol))
                if correlation >= correlation_manager.high_correlation_threshold:
                    is_correlated = True
                    break
            
            # Add if not correlated
            if not is_correlated:
                selected.append(symbol)
                considered.add(symbol)
            
            # Stop if we've reached the limit
            if len(selected) >= max_count:
                break
        
        # If we still need more symbols, add highest-scoring remaining candidates
        # even if they have some correlation
        if len(selected) < max_count:
            for symbol, score in candidates:
                if symbol not in considered:
                    selected.append(symbol)
                    considered.add(symbol)
                    
                    if len(selected) >= max_count:
                        break
        
        return selected
    
    def _adjust_current_allocation(self,
                                 session_instruments: Dict[str, List[str]],
                                 correlation_manager,
                                 active_positions: List[Dict]) -> Dict:
        """
        Make incremental adjustments to current allocation
        
        Args:
            session_instruments: Dictionary of active instruments by category
            correlation_manager: Correlation manager instance
            active_positions: List of active positions
            
        Returns:
            Dictionary with adjusted allocations by category
        """
        # Extract active symbols from positions
        active_symbols = {pos['symbol'] for pos in active_positions}
        
        # Start with current allocation
        adjusted = {
            'forex': self.current_allocation['forex'].copy(),
            'synthetic': self.current_allocation['synthetic'].copy()
        }
        
        # Remove any instruments no longer in session
        for category in adjusted:
            session_set = set(session_instruments.get(category, []))
            adjusted[category] = [s for s in adjusted[category] if s in session_set or s in active_symbols]
        
        # Add any missing active symbols
        for symbol in active_symbols:
            # Check which category it belongs to
            is_forex = symbol in session_instruments.get('forex', [])
            is_synthetic = symbol in session_instruments.get('synthetic', [])
            
            if is_forex and symbol not in adjusted['forex']:
                adjusted['forex'].append(symbol)
            elif is_synthetic and symbol not in adjusted['synthetic']:
                adjusted['synthetic'].append(symbol)
        
        # Add high-scoring instruments from session list
        for category in adjusted:
            # Skip if we already have enough
            if len(adjusted[category]) >= self.max_same_category:
                continue
            
            # Create candidates list
            candidates = []
            for symbol in session_instruments.get(category, []):
                if symbol not in adjusted[category] and symbol not in active_symbols:
                    # Get instrument score
                    perf_score = self.instrument_performance[symbol].get('score', 50.0)
                    candidates.append((symbol, perf_score))
            
            # Sort candidates by score
            candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Add top candidates until we reach the limit
            for symbol, score in candidates:
                # Check correlation with existing instruments
                is_correlated = False
                for existing in adjusted[category]:
                    correlation = abs(correlation_manager.get_correlation(symbol, existing))
                    if correlation >= correlation_manager.high_correlation_threshold:
                        is_correlated = True
                        break
                
                # Add if not correlated
                if not is_correlated:
                    adjusted[category].append(symbol)
                    
                    # Stop if we've reached the limit
                    if len(adjusted[category]) >= self.max_same_category:
                        break
        
        return adjusted
    
    def _load_performance_data(self) -> None:
        """Load instrument performance data from file"""
        if not os.path.exists(self.performance_data_file):
            logger.debug("No performance data file found")
            return
            
        try:
            with open(self.performance_data_file, 'r') as f:
                performance_data = json.load(f)
            
            # Convert to defaultdict structure
            for symbol, data in performance_data.items():
                self.instrument_performance[symbol] = data
            
            logger.info(f"Loaded performance data for {len(performance_data)} instruments")
            
        except Exception as e:
            logger.error(f"Error loading performance data: {e}")
    
    def _save_performance_data(self) -> None:
        """Save instrument performance data to file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.performance_data_file), exist_ok=True)
            
            # Convert defaultdict to regular dict for serialization
            performance_data = dict(self.instrument_performance)
            
            with open(self.performance_data_file, 'w') as f:
                json.dump(performance_data, f, indent=2)
                
            logger.debug(f"Saved performance data to {self.performance_data_file}")
            
        except Exception as e:
            logger.error(f"Error saving performance data: {e}")
