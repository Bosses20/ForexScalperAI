"""
Price Action Analysis Module

This module contains functions for analyzing price action patterns in market data,
identifying key candlestick patterns and market structures that can be used for trading decisions.
"""

import numpy as np
import pandas as pd
from loguru import logger
from typing import Dict, List, Tuple, Optional


class PriceActionAnalyzer:
    """
    Analyzes price action patterns in market data to identify potential trading opportunities.
    """

    def __init__(self, config: dict):
        """
        Initialize the PriceActionAnalyzer with configuration parameters.
        
        Args:
            config (dict): Configuration dictionary containing parameters for price action analysis
        """
        self.config = config
        self.pattern_config = config.get('price_action', {})
        self.min_body_to_wick_ratio = self.pattern_config.get('min_body_to_wick_ratio', 2.0)
        self.strong_candle_threshold = self.pattern_config.get('strong_candle_threshold', 0.7)
        self.pin_bar_threshold = self.pattern_config.get('pin_bar_threshold', 3.0)
        self.engulfing_threshold = self.pattern_config.get('engulfing_threshold', 1.2)
        
        logger.info("Price Action Analyzer initialized")
    
    def identify_market_condition(self, data: pd.DataFrame, lookback: int = 50) -> str:
        """
        Identifies the current market condition: bullish, bearish, ranging, or choppy.
        
        Args:
            data (pd.DataFrame): Market data with OHLC prices
            lookback (int): Number of periods to look back for analysis
            
        Returns:
            str: Market condition ('bullish', 'bearish', 'ranging', or 'choppy')
        """
        if len(data) < lookback:
            return "insufficient_data"
        
        # Get the relevant data subset
        recent_data = data.iloc[-lookback:].copy()
        
        # Calculate basic metrics
        price_change = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]
        volatility = recent_data['high'].max() - recent_data['low'].min()
        avg_range = (recent_data['high'] - recent_data['low']).mean()
        
        # Calculate linear regression to determine trend
        x = np.arange(len(recent_data))
        y = recent_data['close'].values
        slope, _ = np.polyfit(x, y, 1)
        
        # Calculate R-squared to determine trend strength
        y_pred = slope * x + _
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        ss_res = np.sum((y - y_pred) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Calculate choppiness
        atr_sum = (recent_data['high'] - recent_data['low']).sum()
        price_distance = abs(recent_data['close'].iloc[-1] - recent_data['close'].iloc[0])
        choppiness = 1 - (price_distance / atr_sum) if atr_sum != 0 else 0
        
        # Determine market condition
        if r_squared > 0.7:  # Strong trend
            if slope > 0:
                return "bullish"
            else:
                return "bearish"
        elif r_squared > 0.3:  # Moderate trend
            if slope > 0:
                return "weak_bullish"
            else:
                return "weak_bearish"
        elif choppiness > 0.7:  # Choppy market
            return "choppy"
        else:  # Ranging market
            return "ranging"
    
    def identify_key_levels(self, data: pd.DataFrame, lookback: int = 200) -> Dict[str, List[float]]:
        """
        Identifies key support and resistance levels from historical price data.
        
        Args:
            data (pd.DataFrame): Market data with OHLC prices
            lookback (int): Number of periods to look back for analysis
            
        Returns:
            Dict[str, List[float]]: Dictionary containing support and resistance levels
        """
        if len(data) < lookback:
            return {"support": [], "resistance": []}
        
        # Get the relevant data subset
        recent_data = data.iloc[-lookback:].copy()
        
        # Find swing highs and lows
        swings = self._find_swing_points(recent_data)
        
        # Cluster similar price levels
        supports = self._cluster_price_levels(swings['lows'])
        resistances = self._cluster_price_levels(swings['highs'])
        
        # Filter for stronger levels (more touches)
        strong_supports = [level for level, count in supports.items() if count >= 2]
        strong_resistances = [level for level, count in resistances.items() if count >= 2]
        
        return {
            "support": strong_supports,
            "resistance": strong_resistances
        }
    
    def _find_swing_points(self, data: pd.DataFrame, window: int = 5) -> Dict[str, List[float]]:
        """
        Finds swing high and low points in the price data.
        
        Args:
            data (pd.DataFrame): Market data
            window (int): Window size for identifying swing points
            
        Returns:
            Dict[str, List[float]]: Dictionary with swing highs and lows
        """
        highs = []
        lows = []
        
        for i in range(window, len(data) - window):
            # Check for swing high
            if all(data['high'].iloc[i] > data['high'].iloc[i-j] for j in range(1, window+1)) and \
               all(data['high'].iloc[i] > data['high'].iloc[i+j] for j in range(1, window+1)):
                highs.append(data['high'].iloc[i])
            
            # Check for swing low
            if all(data['low'].iloc[i] < data['low'].iloc[i-j] for j in range(1, window+1)) and \
               all(data['low'].iloc[i] < data['low'].iloc[i+j] for j in range(1, window+1)):
                lows.append(data['low'].iloc[i])
        
        return {"highs": highs, "lows": lows}
    
    def _cluster_price_levels(self, price_points: List[float], threshold_pct: float = 0.001) -> Dict[float, int]:
        """
        Clusters similar price levels together.
        
        Args:
            price_points (List[float]): List of price points
            threshold_pct (float): Percentage threshold for clustering
            
        Returns:
            Dict[float, int]: Dictionary with clustered price levels and their counts
        """
        if not price_points:
            return {}
        
        clusters = {}
        price_points = sorted(price_points)
        
        for price in price_points:
            # Check if price belongs to an existing cluster
            found_cluster = False
            for cluster_price in list(clusters.keys()):
                if abs(price - cluster_price) / cluster_price < threshold_pct:
                    # Update cluster with average price and increase count
                    count = clusters[cluster_price]
                    new_avg = (cluster_price * count + price) / (count + 1)
                    del clusters[cluster_price]
                    clusters[new_avg] = count + 1
                    found_cluster = True
                    break
            
            if not found_cluster:
                clusters[price] = 1
        
        return clusters
    
    def identify_candlestick_patterns(self, data: pd.DataFrame) -> Dict[str, List[int]]:
        """
        Identifies common candlestick patterns in the price data.
        
        Args:
            data (pd.DataFrame): Market data with OHLC prices
            
        Returns:
            Dict[str, List[int]]: Dictionary mapping pattern names to indices where they appear
        """
        if len(data) < 3:
            return {}
        
        patterns = {
            "bullish_engulfing": [],
            "bearish_engulfing": [],
            "bullish_pin_bar": [],
            "bearish_pin_bar": [],
            "doji": [],
            "hammer": [],
            "shooting_star": [],
            "morning_star": [],
            "evening_star": []
        }
        
        for i in range(1, len(data)):
            current = data.iloc[i]
            previous = data.iloc[i-1]
            
            # Calculate candle properties
            current_body_size = abs(current['close'] - current['open'])
            current_total_size = current['high'] - current['low']
            current_upper_wick = current['high'] - max(current['open'], current['close'])
            current_lower_wick = min(current['open'], current['close']) - current['low']
            
            previous_body_size = abs(previous['close'] - previous['open'])
            
            # Bullish engulfing
            if (previous['close'] < previous['open'] and  # Previous candle is bearish
                current['close'] > current['open'] and    # Current candle is bullish
                current['open'] < previous['close'] and   # Current open below previous close
                current['close'] > previous['open'] and   # Current close above previous open
                current_body_size > previous_body_size * self.engulfing_threshold):
                patterns["bullish_engulfing"].append(i)
            
            # Bearish engulfing
            elif (previous['close'] > previous['open'] and  # Previous candle is bullish
                  current['close'] < current['open'] and    # Current candle is bearish
                  current['open'] > previous['close'] and   # Current open above previous close
                  current['close'] < previous['open'] and   # Current close below previous open
                  current_body_size > previous_body_size * self.engulfing_threshold):
                patterns["bearish_engulfing"].append(i)
            
            # Bullish pin bar (hammer)
            elif (current_lower_wick > current_body_size * self.pin_bar_threshold and
                  current_upper_wick < current_body_size and
                  current['close'] > current['open']):
                patterns["bullish_pin_bar"].append(i)
                patterns["hammer"].append(i)
            
            # Bearish pin bar (shooting star)
            elif (current_upper_wick > current_body_size * self.pin_bar_threshold and
                  current_lower_wick < current_body_size and
                  current['close'] < current['open']):
                patterns["bearish_pin_bar"].append(i)
                patterns["shooting_star"].append(i)
            
            # Doji
            elif current_body_size / current_total_size < 0.1 and current_total_size > 0:
                patterns["doji"].append(i)
            
            # Morning and evening star patterns require 3 candles
            if i >= 2:
                prev_prev = data.iloc[i-2]
                
                # Morning star (bullish reversal)
                if (prev_prev['close'] < prev_prev['open'] and  # First candle bearish
                    abs(previous['close'] - previous['open']) / (previous['high'] - previous['low']) < 0.3 and  # Middle candle small
                    current['close'] > current['open'] and  # Last candle bullish
                    current['close'] > (prev_prev['open'] + prev_prev['close']) / 2):  # Closed above midpoint of first candle
                    patterns["morning_star"].append(i)
                
                # Evening star (bearish reversal)
                elif (prev_prev['close'] > prev_prev['open'] and  # First candle bullish
                      abs(previous['close'] - previous['open']) / (previous['high'] - previous['low']) < 0.3 and  # Middle candle small
                      current['close'] < current['open'] and  # Last candle bearish
                      current['close'] < (prev_prev['open'] + prev_prev['close']) / 2):  # Closed below midpoint of first candle
                    patterns["evening_star"].append(i)
        
        return patterns
    
    def calculate_candle_strength(self, candle: pd.Series) -> float:
        """
        Calculates the strength of a candle based on its body-to-wick ratio and position.
        
        Args:
            candle (pd.Series): Candle data with 'open', 'high', 'low', 'close'
            
        Returns:
            float: Strength score between -1 (strong bearish) and 1 (strong bullish)
        """
        body_size = abs(candle['close'] - candle['open'])
        total_size = candle['high'] - candle['low']
        
        if total_size == 0:
            return 0
        
        body_ratio = body_size / total_size
        is_bullish = candle['close'] > candle['open']
        
        # Calculate relative position of close within the range
        close_position = (candle['close'] - candle['low']) / total_size
        
        # Strong bullish candle: big body, closed near high
        if is_bullish and body_ratio > self.strong_candle_threshold and close_position > 0.8:
            return 1.0
        # Strong bearish candle: big body, closed near low
        elif not is_bullish and body_ratio > self.strong_candle_threshold and close_position < 0.2:
            return -1.0
        # Calculate strength based on body ratio and direction
        else:
            direction = 1 if is_bullish else -1
            return direction * body_ratio
    
    def find_rejection_zones(self, data: pd.DataFrame, key_levels: Dict[str, List[float]]) -> Dict[str, List[Tuple[int, float]]]:
        """
        Identifies zones where price has rejected from key support or resistance levels.
        
        Args:
            data (pd.DataFrame): Market data with OHLC prices
            key_levels (Dict[str, List[float]]): Dictionary with support and resistance levels
            
        Returns:
            Dict[str, List[Tuple[int, float]]]: Dictionary with rejection points (index, level)
        """
        rejections = {
            "support_rejections": [],
            "resistance_rejections": []
        }
        
        threshold = 0.0005  # 5 pips for typical forex pairs
        
        for i in range(1, len(data)):
            candle = data.iloc[i]
            
            # Check for resistance rejections (upper wick)
            upper_wick = candle['high'] - max(candle['open'], candle['close'])
            if upper_wick > 0:
                for level in key_levels["resistance"]:
                    if abs(candle['high'] - level) / level < threshold:
                        # Significant rejection if upper wick is large and close is far from high
                        if upper_wick > abs(candle['close'] - candle['open']):
                            rejections["resistance_rejections"].append((i, level))
            
            # Check for support rejections (lower wick)
            lower_wick = min(candle['open'], candle['close']) - candle['low']
            if lower_wick > 0:
                for level in key_levels["support"]:
                    if abs(candle['low'] - level) / level < threshold:
                        # Significant rejection if lower wick is large and close is far from low
                        if lower_wick > abs(candle['close'] - candle['open']):
                            rejections["support_rejections"].append((i, level))
        
        return rejections
    
    def analyze_price_action(self, data: pd.DataFrame) -> Dict[str, any]:
        """
        Performs comprehensive price action analysis on the given data.
        
        Args:
            data (pd.DataFrame): Market data with OHLC prices
            
        Returns:
            Dict[str, any]: Dictionary with comprehensive price action analysis
        """
        result = {}
        
        # Analyze market condition
        result["market_condition"] = self.identify_market_condition(data)
        
        # Identify key levels
        result["key_levels"] = self.identify_key_levels(data)
        
        # Find candlestick patterns
        result["candlestick_patterns"] = self.identify_candlestick_patterns(data)
        
        # Calculate candle strength for the most recent candles
        result["recent_candle_strength"] = [
            self.calculate_candle_strength(data.iloc[i]) 
            for i in range(max(0, len(data)-5), len(data))
        ]
        
        # Find rejection zones
        result["rejections"] = self.find_rejection_zones(data, result["key_levels"])
        
        return result
    
    def get_trading_bias(self, analysis_result: Dict[str, any]) -> Tuple[str, float]:
        """
        Determines trading bias (bullish, bearish, neutral) based on price action analysis.
        
        Args:
            analysis_result (Dict[str, any]): Result from analyze_price_action method
            
        Returns:
            Tuple[str, float]: Trading bias ('bullish', 'bearish', 'neutral') and confidence score (0-1)
        """
        # Initialize score components
        market_condition_score = 0
        pattern_score = 0
        rejection_score = 0
        candle_strength_score = 0
        
        # Market condition contribution
        condition = analysis_result["market_condition"]
        if condition == "bullish":
            market_condition_score = 0.8
        elif condition == "weak_bullish":
            market_condition_score = 0.4
        elif condition == "bearish":
            market_condition_score = -0.8
        elif condition == "weak_bearish":
            market_condition_score = -0.4
        elif condition == "ranging":
            market_condition_score = 0
        else:  # choppy or insufficient data
            market_condition_score = 0
        
        # Pattern contribution
        patterns = analysis_result["candlestick_patterns"]
        recent_patterns = {k: [idx for idx in v if idx >= len(analysis_result["recent_candle_strength"]) - 3] 
                          for k, v in patterns.items()}
        
        bullish_patterns = len(recent_patterns.get("bullish_engulfing", [])) + \
                          len(recent_patterns.get("bullish_pin_bar", [])) + \
                          len(recent_patterns.get("hammer", [])) + \
                          len(recent_patterns.get("morning_star", []))
        
        bearish_patterns = len(recent_patterns.get("bearish_engulfing", [])) + \
                          len(recent_patterns.get("bearish_pin_bar", [])) + \
                          len(recent_patterns.get("shooting_star", [])) + \
                          len(recent_patterns.get("evening_star", []))
        
        pattern_score = 0.2 * (bullish_patterns - bearish_patterns)
        pattern_score = max(min(pattern_score, 0.6), -0.6)  # Cap between -0.6 and 0.6
        
        # Rejection contribution
        support_rejections = len(analysis_result["rejections"]["support_rejections"])
        resistance_rejections = len(analysis_result["rejections"]["resistance_rejections"])
        
        rejection_score = 0.1 * (support_rejections - resistance_rejections)
        rejection_score = max(min(rejection_score, 0.4), -0.4)  # Cap between -0.4 and 0.4
        
        # Recent candle strength contribution
        if analysis_result["recent_candle_strength"]:
            candle_strength_score = sum(analysis_result["recent_candle_strength"]) / len(analysis_result["recent_candle_strength"])
            candle_strength_score = max(min(candle_strength_score * 0.5, 0.5), -0.5)  # Scale and cap
        
        # Combine scores
        total_score = market_condition_score + pattern_score + rejection_score + candle_strength_score
        
        # Determine bias and confidence
        if total_score > 0.3:
            bias = "bullish"
            confidence = min(abs(total_score), 1.0)
        elif total_score < -0.3:
            bias = "bearish"
            confidence = min(abs(total_score), 1.0)
        else:
            bias = "neutral"
            confidence = 1.0 - abs(total_score) * 2  # Higher confidence for scores closer to 0
        
        return bias, confidence
