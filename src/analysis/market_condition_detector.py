"""
Market Condition Detector Module

This module is responsible for detecting and classifying different market conditions
and suggesting optimal trading approaches for each condition. It integrates with
the price action analyzer and other indicators to provide a comprehensive assessment
of current market states.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from loguru import logger

from src.analysis.price_action import PriceActionAnalyzer


class MarketConditionDetector:
    """
    Detects and classifies different market conditions to optimize trading strategy selection.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the MarketConditionDetector with configuration parameters.
        
        Args:
            config (dict): Configuration dictionary containing parameters for market condition detection
        """
        self.config = config
        self.detector_config = config.get('market_condition_detector', {})
        
        # Initialize price action analyzer
        self.price_action_analyzer = PriceActionAnalyzer(config)
        
        # Parameters for market condition detection
        self.trend_lookback = self.detector_config.get('trend_lookback', 100)
        self.volatility_window = self.detector_config.get('volatility_window', 20)
        self.liquidity_threshold = self.detector_config.get('liquidity_threshold', 0.4)
        self.trend_strength_threshold = self.detector_config.get('trend_strength_threshold', 0.6)
        self.volatility_categories = self.detector_config.get('volatility_categories', {
            'low': 0.4,
            'medium': 0.8,
            'high': float('inf')
        })
        
        # Cache for market conditions to avoid recalculation
        self.market_condition_cache = {}
        self.cache_expiry_seconds = self.detector_config.get('cache_expiry_seconds', 300)  # 5 minutes default
        
        logger.info("Market Condition Detector initialized")
    
    def detect_market_condition(self, symbol: str, data: pd.DataFrame, force_refresh: bool = False) -> Dict[str, any]:
        """
        Detects the current market condition for a given symbol.
        
        Args:
            symbol (str): Trading symbol to analyze
            data (pd.DataFrame): Market data with OHLC prices
            force_refresh (bool): Whether to force recalculation even if cached data exists
            
        Returns:
            Dict[str, any]: Market condition details including trend, volatility, liquidity, etc.
        """
        current_time = datetime.now()
        
        # Check if we have a recent cached result
        if not force_refresh and symbol in self.market_condition_cache:
            cache_entry = self.market_condition_cache[symbol]
            cache_age = (current_time - cache_entry['timestamp']).total_seconds()
            
            if cache_age < self.cache_expiry_seconds:
                return cache_entry['condition']
        
        # Not cached or expired, calculate market condition
        if len(data) < self.trend_lookback:
            logger.warning(f"Insufficient data for {symbol} to detect market condition")
            return {
                'trend': 'unknown',
                'volatility': 'unknown',
                'liquidity': 'unknown',
                'recommended_strategies': [],
                'condition_details': {},
                'confidence': 0.0
            }
        
        # Get price action analysis
        price_action_analysis = self.price_action_analyzer.analyze_price_action(data)
        
        # Determine trend
        trend = price_action_analysis['market_condition']
        
        # Calculate volatility
        volatility = self._calculate_volatility(data)
        
        # Determine liquidity based on volume and spread if available
        liquidity = self._estimate_liquidity(data)
        
        # Calculate strength of the current trend
        trend_strength = self._calculate_trend_strength(data)
        
        # Get optimal strategies for current conditions
        recommended_strategies = self._get_recommended_strategies(
            trend, volatility, liquidity, trend_strength, symbol
        )
        
        # Determine overall market condition
        market_condition = {
            'trend': trend,
            'volatility': volatility,
            'liquidity': liquidity,
            'trend_strength': trend_strength,
            'recommended_strategies': recommended_strategies,
            'condition_details': {
                'price_action': price_action_analysis,
                'atr': self._calculate_atr(data, 14),
                'volume_trend': self._analyze_volume_trend(data) if 'volume' in data.columns else None,
            },
            'confidence': self._calculate_condition_confidence(trend, volatility, liquidity, trend_strength)
        }
        
        # Cache the result
        self.market_condition_cache[symbol] = {
            'timestamp': current_time,
            'condition': market_condition
        }
        
        return market_condition
    
    def _calculate_volatility(self, data: pd.DataFrame) -> str:
        """
        Calculates the current market volatility.
        
        Args:
            data (pd.DataFrame): Market data with OHLC prices
            
        Returns:
            str: Volatility category ('low', 'medium', 'high')
        """
        # Calculate ATR as a percentage of price
        if len(data) < self.volatility_window:
            return 'unknown'
        
        recent_data = data.iloc[-self.volatility_window:]
        
        # Calculate Average True Range
        true_ranges = []
        for i in range(1, len(recent_data)):
            high = recent_data['high'].iloc[i]
            low = recent_data['low'].iloc[i]
            prev_close = recent_data['close'].iloc[i-1]
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_ranges.append(max(tr1, tr2, tr3))
        
        if not true_ranges:
            return 'unknown'
        
        atr = sum(true_ranges) / len(true_ranges)
        
        # Normalize ATR as percentage of price
        avg_price = recent_data['close'].mean()
        normalized_atr = atr / avg_price if avg_price > 0 else 0
        
        # Categorize volatility
        if normalized_atr < self.volatility_categories['low']:
            return 'low'
        elif normalized_atr < self.volatility_categories['medium']:
            return 'medium'
        else:
            return 'high'
    
    def _estimate_liquidity(self, data: pd.DataFrame) -> str:
        """
        Estimates the current market liquidity based on available data.
        
        Args:
            data (pd.DataFrame): Market data with OHLC prices and volume if available
            
        Returns:
            str: Liquidity category ('low', 'medium', 'high')
        """
        # If we have volume data, use it to estimate liquidity
        if 'volume' in data.columns:
            recent_volume = data['volume'].iloc[-self.volatility_window:].mean()
            historical_volume = data['volume'].mean()
            
            if historical_volume == 0:
                return 'medium'  # Default if no historical context
            
            volume_ratio = recent_volume / historical_volume
            
            if volume_ratio < self.liquidity_threshold:
                return 'low'
            elif volume_ratio < 1.0:
                return 'medium'
            else:
                return 'high'
        
        # If no volume data, estimate based on spread and time of day
        # Since we don't have spread data directly in this function, 
        # we'll use a simpler approach based on expected market hours
        else:
            # Default to medium liquidity if we can't determine
            return 'medium'
    
    def _calculate_trend_strength(self, data: pd.DataFrame) -> float:
        """
        Calculates the strength of the current market trend.
        
        Args:
            data (pd.DataFrame): Market data with OHLC prices
            
        Returns:
            float: Trend strength (0-1)
        """
        # Use linear regression to determine trend strength
        if len(data) < self.trend_lookback:
            return 0.0
        
        recent_data = data.iloc[-self.trend_lookback:].copy()
        
        x = np.arange(len(recent_data))
        y = recent_data['close'].values
        
        # Calculate linear regression
        slope, intercept = np.polyfit(x, y, 1)
        
        # Calculate R-squared (coefficient of determination)
        y_pred = slope * x + intercept
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        ss_res = np.sum((y - y_pred) ** 2)
        
        if ss_tot == 0:
            return 0.0
        
        r_squared = 1 - (ss_res / ss_tot)
        
        # Normalize to 0-1 range
        return min(max(r_squared, 0.0), 1.0)
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """
        Calculates the Average True Range (ATR) for the given data.
        
        Args:
            data (pd.DataFrame): Market data with OHLC prices
            period (int): ATR period
            
        Returns:
            float: ATR value
        """
        if len(data) < period + 1:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(data)):
            high = data['high'].iloc[i]
            low = data['low'].iloc[i]
            prev_close = data['close'].iloc[i-1]
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_ranges.append(max(tr1, tr2, tr3))
        
        # Simple average for first ATR
        atr = sum(true_ranges[-period:]) / period
        
        return atr
    
    def _analyze_volume_trend(self, data: pd.DataFrame) -> Dict[str, any]:
        """
        Analyzes volume trend to identify potential breakouts or reversals.
        
        Args:
            data (pd.DataFrame): Market data with OHLC prices and volume
            
        Returns:
            Dict[str, any]: Volume analysis results
        """
        if 'volume' not in data.columns or len(data) < 20:
            return {'trend': 'unknown'}
        
        recent_data = data.iloc[-20:].copy()
        
        # Calculate volume moving averages
        recent_data['volume_sma5'] = recent_data['volume'].rolling(window=5).mean()
        
        # Detect increasing or decreasing volume trend
        recent_volume = recent_data['volume'].iloc[-5:].mean()
        prev_volume = recent_data['volume'].iloc[-10:-5].mean()
        
        if recent_volume > prev_volume * 1.2:
            volume_trend = 'increasing'
        elif recent_volume < prev_volume * 0.8:
            volume_trend = 'decreasing'
        else:
            volume_trend = 'stable'
        
        # Detect volume spikes
        volume_mean = recent_data['volume'].mean()
        volume_std = recent_data['volume'].std()
        
        has_recent_spike = False
        if len(recent_data) > 0:
            last_volume = recent_data['volume'].iloc[-1]
            if last_volume > volume_mean + 2 * volume_std:
                has_recent_spike = True
        
        return {
            'trend': volume_trend,
            'has_recent_spike': has_recent_spike,
            'recent_avg': recent_volume,
            'previous_avg': prev_volume
        }
    
    def _get_recommended_strategies(self, trend: str, volatility: str, 
                                   liquidity: str, trend_strength: float, 
                                   symbol: str) -> List[str]:
        """
        Determines the recommended trading strategies for the current market condition.
        
        Args:
            trend (str): Current market trend
            volatility (str): Current market volatility
            liquidity (str): Current market liquidity
            trend_strength (float): Strength of the current trend
            symbol (str): Trading symbol
            
        Returns:
            List[str]: List of recommended strategy names
        """
        symbol_type = 'forex'
        symbol_subtype = None
        
        # Determine symbol type and subtype from trading configuration
        trading_config = self.config.get('trading', {}).get('symbols', {})
        
        for category, symbols in trading_config.items():
            for symbol_info in symbols:
                if symbol_info.get('name') == symbol:
                    symbol_type = symbol_info.get('type', 'forex')
                    symbol_subtype = symbol_info.get('sub_type')
                    break
        
        recommended = []
        
        # Get strategy strengths from configuration
        strategy_strengths = self.config.get('multi_asset', {}).get('strategy_strengths', {})
        
        # Get strategies for the symbol type
        type_strategies = strategy_strengths.get(symbol_type, {})
        
        # For synthetic indices, we might have subtype-specific strategies
        if symbol_type == 'synthetic' and symbol_subtype and symbol_subtype in strategy_strengths.get('synthetic', {}):
            type_strategies = strategy_strengths['synthetic'][symbol_subtype]
        
        # Sort strategies by strength for this symbol type
        sorted_strategies = sorted(type_strategies.items(), key=lambda x: x[1], reverse=True)
        
        # Recommend strategies based on market conditions
        if trend in ['bullish', 'weak_bullish']:
            if volatility == 'high':
                # For high volatility uptrends, breakout strategies work well
                for strategy, _ in sorted_strategies:
                    if 'breakout' in strategy or 'momentum' in strategy:
                        recommended.append(strategy)
                    if len(recommended) >= 2:
                        break
            elif volatility == 'medium' and trend_strength > self.trend_strength_threshold:
                # For medium volatility strong uptrends, trend-following strategies work well
                for strategy, _ in sorted_strategies:
                    if 'trend' in strategy or 'moving_average' in strategy:
                        recommended.append(strategy)
                    if len(recommended) >= 2:
                        break
            else:
                # For low volatility or weak uptrends, reversion strategies might work
                for strategy, _ in sorted_strategies:
                    if 'value_gap' in strategy or 'retest' in strategy:
                        recommended.append(strategy)
                    if len(recommended) >= 2:
                        break
                
        elif trend in ['bearish', 'weak_bearish']:
            if volatility == 'high':
                # For high volatility downtrends, breakout strategies work well
                for strategy, _ in sorted_strategies:
                    if 'breakout' in strategy or 'structure' in strategy:
                        recommended.append(strategy)
                    if len(recommended) >= 2:
                        break
            elif volatility == 'medium' and trend_strength > self.trend_strength_threshold:
                # For medium volatility strong downtrends, trend-following strategies work well
                for strategy, _ in sorted_strategies:
                    if 'trend' in strategy or 'moving_average' in strategy:
                        recommended.append(strategy)
                    if len(recommended) >= 2:
                        break
            else:
                # For low volatility or weak downtrends, reversion strategies might work
                for strategy, _ in sorted_strategies:
                    if 'value_gap' in strategy or 'retest' in strategy:
                        recommended.append(strategy)
                    if len(recommended) >= 2:
                        break
        
        elif trend == 'ranging':
            # For ranging markets, range trading strategies work well
            for strategy, _ in sorted_strategies:
                if 'bollinger' in strategy or 'value_gap' in strategy:
                    recommended.append(strategy)
                if len(recommended) >= 2:
                    break
        
        else:  # choppy or unknown
            # For choppy markets, it's better to be conservative
            # Recommend the highest-rated strategy for this symbol type
            if sorted_strategies:
                recommended.append(sorted_strategies[0][0])
        
        # If we couldn't find specific recommendations, just use the top strategies
        if not recommended and sorted_strategies:
            recommended = [strategy for strategy, _ in sorted_strategies[:2]]
        
        return recommended
    
    def _calculate_condition_confidence(self, trend: str, volatility: str, 
                                       liquidity: str, trend_strength: float) -> float:
        """
        Calculates confidence level in the market condition assessment.
        
        Args:
            trend (str): Current market trend
            volatility (str): Current market volatility
            liquidity (str): Current market liquidity
            trend_strength (float): Strength of the current trend
            
        Returns:
            float: Confidence level (0-1)
        """
        # Base confidence
        confidence = 0.5
        
        # Adjust based on trend clarity
        if trend in ['bullish', 'bearish']:
            confidence += 0.2
        elif trend in ['weak_bullish', 'weak_bearish']:
            confidence += 0.1
        elif trend == 'ranging':
            confidence += 0.15
        elif trend == 'choppy':
            confidence -= 0.1
        
        # Adjust based on trend strength
        confidence += trend_strength * 0.2
        
        # Adjust based on data quality
        if volatility != 'unknown':
            confidence += 0.05
        if liquidity != 'unknown':
            confidence += 0.05
        
        # Ensure confidence is in range [0, 1]
        return min(max(confidence, 0.0), 1.0)
    
    def get_optimal_strategy(self, symbol: str, data: pd.DataFrame) -> Tuple[str, float]:
        """
        Determines the optimal trading strategy for the current market conditions.
        
        Args:
            symbol (str): Trading symbol to analyze
            data (pd.DataFrame): Market data with OHLC prices
            
        Returns:
            Tuple[str, float]: Optimal strategy name and confidence score
        """
        market_condition = self.detect_market_condition(symbol, data)
        recommended_strategies = market_condition['recommended_strategies']
        
        if not recommended_strategies:
            # Default to the most versatile strategy if no recommendations
            return "moving_average_cross", 0.5
        
        # Return the top recommended strategy with confidence
        return recommended_strategies[0], market_condition['confidence']
    
    def should_trade_now(self, symbol: str, data: pd.DataFrame, min_confidence: float = 0.6) -> bool:
        """
        Determines if current market conditions are favorable for trading.
        
        Args:
            symbol (str): Trading symbol to analyze
            data (pd.DataFrame): Market data with OHLC prices
            min_confidence (float): Minimum confidence threshold
            
        Returns:
            bool: Whether trading is recommended
        """
        market_condition = self.detect_market_condition(symbol, data)
        
        # Don't trade in choppy or unknown markets
        if market_condition['trend'] in ['choppy', 'unknown']:
            return False
        
        # Don't trade if confidence is too low
        if market_condition['confidence'] < min_confidence:
            return False
        
        # Don't trade if liquidity is too low
        if market_condition['liquidity'] == 'low':
            return False
        
        # All checks passed, trading is recommended
        return True
