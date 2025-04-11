"""
Correlation Manager
Tracks and manages correlations between different trading instruments
to prevent overexposure to correlated market movements
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime, timedelta
from loguru import logger
import json
import os

class CorrelationManager:
    """
    Manages correlations between instruments to control portfolio risk
    by preventing overexposure to highly correlated assets
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize the correlation manager
        
        Args:
            config: Configuration dictionary with correlation settings
        """
        self.config = config or {}
        
        # Configuration
        self.high_correlation_threshold = self.config.get('high_correlation_threshold', 0.7)
        self.medium_correlation_threshold = self.config.get('medium_correlation_threshold', 0.5)
        self.data_lookback_days = self.config.get('data_lookback_days', 30)
        self.correlation_update_hours = self.config.get('correlation_update_hours', 12)
        self.max_correlated_exposure = self.config.get('max_correlated_exposure', 0.15)
        self.max_same_direction_exposure = self.config.get('max_same_direction_exposure', 0.25)
        
        # Known correlation groups
        self.predefined_groups = self.config.get('predefined_correlation_groups', {
            'major_usd_pairs': ['EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD'],
            'jpy_pairs': ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY'],
            'volatility_indices': ['Volatility 10 Index', 'Volatility 25 Index', 'Volatility 50 Index', 'Volatility 75 Index', 'Volatility 100 Index'],
            'crash_indices': ['Crash 300 Index', 'Crash 500 Index', 'Crash 1000 Index'],
            'boom_indices': ['Boom 300 Index', 'Boom 500 Index', 'Boom 1000 Index'],
            'step_indices': ['Step Index'],
            'jump_indices': ['Jump 10 Index', 'Jump 25 Index', 'Jump 50 Index', 'Jump 75 Index', 'Jump 100 Index']
        })
        
        # Initialize correlation matrix
        self.correlation_matrix = pd.DataFrame()
        self.last_correlation_update = None
        self.symbol_price_data = {}
        self.correlation_cache_file = os.path.join(
            self.config.get('data_dir', 'data'), 
            'correlation_matrix.json'
        )
        
        # Load cached correlation data if available
        self._load_cached_correlations()
        
        logger.info("Correlation Manager initialized")
    
    def update_price_data(self, symbol: str, price_data: pd.DataFrame) -> None:
        """
        Update price data for correlation calculations
        
        Args:
            symbol: Instrument symbol
            price_data: DataFrame with price data (must have 'close' column)
        """
        if 'close' not in price_data.columns:
            logger.warning(f"Price data for {symbol} does not have 'close' column")
            return
        
        # Store only closing prices for correlation calculation
        self.symbol_price_data[symbol] = price_data['close'].copy()
        
        # Check if we need to update correlation matrix
        if self._should_update_correlations():
            self._update_correlation_matrix()
    
    def get_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        Get correlation coefficient between two symbols
        
        Args:
            symbol1: First symbol
            symbol2: Second symbol
            
        Returns:
            Correlation coefficient (-1 to 1)
        """
        # Check if both symbols are in correlation matrix
        if (symbol1 not in self.correlation_matrix.index or 
            symbol2 not in self.correlation_matrix.columns):
            # Check if symbols are in the same predefined group
            for group, symbols in self.predefined_groups.items():
                if symbol1 in symbols and symbol2 in symbols:
                    # Return high correlation for symbols in the same group
                    return self.high_correlation_threshold
            
            # Default to zero if no data
            return 0.0
        
        return self.correlation_matrix.loc[symbol1, symbol2]
    
    def get_correlated_symbols(self, symbol: str, threshold: float = None) -> Dict[str, float]:
        """
        Get all symbols correlated with the given symbol above the threshold
        
        Args:
            symbol: Target symbol
            threshold: Correlation threshold (default: use high_correlation_threshold)
            
        Returns:
            Dictionary of {symbol: correlation} for correlated symbols
        """
        if threshold is None:
            threshold = self.high_correlation_threshold
        
        # Check if in correlation matrix
        if symbol not in self.correlation_matrix.index:
            # Check predefined groups
            correlated_symbols = {}
            for group, symbols in self.predefined_groups.items():
                if symbol in symbols:
                    # All symbols in same group are considered correlated
                    for s in symbols:
                        if s != symbol:
                            correlated_symbols[s] = self.high_correlation_threshold
            
            return correlated_symbols
        
        # Get correlations from matrix
        correlations = self.correlation_matrix[symbol].to_dict()
        
        # Filter by threshold
        return {s: corr for s, corr in correlations.items() 
                if s != symbol and abs(corr) >= threshold}
    
    def check_correlation_exposure(self, 
                                 active_positions: List[Dict], 
                                 new_position: Dict) -> Tuple[bool, str]:
        """
        Check if a new position would exceed correlation exposure limits
        
        Args:
            active_positions: List of active position dictionaries
            new_position: New position dictionary
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        if not active_positions:
            return True, ""
        
        new_symbol = new_position['symbol']
        new_direction = new_position['type']  # 'BUY' or 'SELL'
        new_size = new_position.get('volume', 1.0)
        
        # 1. Check exposure to the same instrument
        same_symbol_positions = [p for p in active_positions if p['symbol'] == new_symbol]
        if same_symbol_positions:
            same_direction_positions = [p for p in same_symbol_positions 
                                       if p['type'] == new_direction]
            if same_direction_positions:
                return False, f"Already have position in {new_symbol} in same direction"
        
        # 2. Check exposure to correlated instruments
        correlated_symbols = self.get_correlated_symbols(new_symbol)
        if not correlated_symbols:
            return True, ""
        
        # Track exposure by correlation level and direction
        total_correlated_exposure = 0
        same_direction_exposure = 0
        opposite_direction_exposure = 0
        
        for position in active_positions:
            pos_symbol = position['symbol']
            pos_direction = position['type']
            pos_size = position.get('volume', 1.0)
            
            # Skip if it's the same symbol (already checked)
            if pos_symbol == new_symbol:
                continue
            
            # Check if correlated
            correlation = self.get_correlation(new_symbol, pos_symbol)
            if abs(correlation) >= self.high_correlation_threshold:
                # Adjust exposure based on correlation direction and position direction
                if correlation > 0:  # Positive correlation
                    total_correlated_exposure += pos_size
                    if pos_direction == new_direction:
                        same_direction_exposure += pos_size
                    else:
                        opposite_direction_exposure += pos_size
                else:  # Negative correlation
                    total_correlated_exposure += pos_size
                    if pos_direction != new_direction:
                        same_direction_exposure += pos_size
                    else:
                        opposite_direction_exposure += pos_size
        
        # Check if adding new position would exceed limits
        if (total_correlated_exposure + new_size) > self.max_correlated_exposure:
            return False, f"Adding {new_symbol} would exceed maximum correlated exposure"
            
        if (same_direction_exposure + new_size) > self.max_same_direction_exposure:
            return False, f"Adding {new_symbol} would exceed maximum same-direction exposure"
        
        return True, ""
    
    def get_correlation_groups(self) -> Dict[str, List[str]]:
        """
        Get groups of correlated instruments based on current correlation matrix
        
        Returns:
            Dictionary of {group_name: [symbols]}
        """
        # Start with predefined groups
        groups = self.predefined_groups.copy()
        
        # Skip if correlation matrix is empty
        if self.correlation_matrix.empty:
            return groups
        
        # Find additional correlation groups
        threshold = self.high_correlation_threshold
        remaining_symbols = set(self.correlation_matrix.index)
        
        while remaining_symbols:
            symbol = next(iter(remaining_symbols))
            correlated = self.get_correlated_symbols(symbol, threshold)
            
            if correlated:
                # Create new group
                group_name = f"corr_group_{symbol}"
                group_symbols = [symbol] + list(correlated.keys())
                groups[group_name] = group_symbols
                
                # Remove these symbols from remaining set
                remaining_symbols -= set(group_symbols)
            else:
                # No correlations for this symbol
                remaining_symbols.remove(symbol)
        
        return groups
    
    def _should_update_correlations(self) -> bool:
        """Check if correlation matrix should be updated"""
        # Always update if correlation matrix is empty
        if self.correlation_matrix.empty:
            return True
        
        # Update if more than correlation_update_hours have passed
        if self.last_correlation_update is None:
            return True
            
        hours_since_update = (datetime.now() - self.last_correlation_update).total_seconds() / 3600
        return hours_since_update >= self.correlation_update_hours
    
    def _update_correlation_matrix(self) -> None:
        """Update the correlation matrix using current price data"""
        # Need at least 2 symbols with price data
        if len(self.symbol_price_data) < 2:
            logger.debug("Not enough symbols for correlation calculation")
            return
        
        # Create DataFrame with all price data
        try:
            prices_df = pd.DataFrame(self.symbol_price_data)
            
            # Calculate correlation matrix
            self.correlation_matrix = prices_df.corr(method='pearson')
            self.last_correlation_update = datetime.now()
            
            # Log correlation update
            logger.info(f"Updated correlation matrix for {len(self.correlation_matrix)} symbols")
            
            # Save to cache
            self._save_cached_correlations()
            
        except Exception as e:
            logger.error(f"Error updating correlation matrix: {e}")
    
    def _save_cached_correlations(self) -> None:
        """Save correlation matrix to cache file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.correlation_cache_file), exist_ok=True)
            
            # Convert to JSON-serializable format
            correlation_data = {
                'timestamp': self.last_correlation_update.isoformat(),
                'matrix': self.correlation_matrix.to_dict(),
                'symbols': list(self.correlation_matrix.index)
            }
            
            with open(self.correlation_cache_file, 'w') as f:
                json.dump(correlation_data, f)
                
            logger.debug(f"Saved correlation data to {self.correlation_cache_file}")
            
        except Exception as e:
            logger.error(f"Error saving correlation cache: {e}")
    
    def _load_cached_correlations(self) -> None:
        """Load correlation matrix from cache file"""
        if not os.path.exists(self.correlation_cache_file):
            logger.debug("No correlation cache file found")
            return
            
        try:
            with open(self.correlation_cache_file, 'r') as f:
                correlation_data = json.load(f)
            
            # Parse timestamp
            timestamp_str = correlation_data.get('timestamp')
            if timestamp_str:
                self.last_correlation_update = datetime.fromisoformat(timestamp_str)
                
                # Check if cache is too old
                hours_since_update = (datetime.now() - self.last_correlation_update).total_seconds() / 3600
                if hours_since_update > self.correlation_update_hours:
                    logger.debug("Correlation cache is outdated")
                    return
            
            # Convert dict to DataFrame
            matrix_dict = correlation_data.get('matrix', {})
            self.correlation_matrix = pd.DataFrame(matrix_dict)
            
            logger.info(f"Loaded correlation data for {len(self.correlation_matrix)} symbols from cache")
            
        except Exception as e:
            logger.error(f"Error loading correlation cache: {e}")
    
    def get_correlation_heatmap_data(self) -> Dict:
        """
        Get correlation data formatted for heatmap visualization
        
        Returns:
            Dictionary with correlation data
        """
        if self.correlation_matrix.empty:
            return {'symbols': [], 'correlations': []}
        
        symbols = list(self.correlation_matrix.index)
        correlations = []
        
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                correlations.append({
                    'x': i,
                    'y': j,
                    'value': self.correlation_matrix.loc[symbol1, symbol2]
                })
        
        return {
            'symbols': symbols,
            'correlations': correlations,
            'update_time': self.last_correlation_update.isoformat() if self.last_correlation_update else None
        }
