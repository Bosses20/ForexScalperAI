"""
Strategy Selector module
Analyzes current market conditions and selects the optimal trading strategy
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union
from loguru import logger
from datetime import datetime, timedelta

# Technical analysis libraries
import ta
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.others import DailyReturnIndicator

# Import strategies
from src.mt5.strategies import create_strategy

class StrategySelector:
    """
    Analyzes current market conditions and selects the most appropriate
    trading strategy based on volatility, trend strength, and other factors
    """
    
    def __init__(self, config: dict):
        """
        Initialize the strategy selector
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.strategies_config = config.get('strategies', {})
        self.selection_timeframe = config.get('selection_timeframe', 'H1')
        self.analysis_lookback = config.get('analysis_lookback', 100)
        self.min_data_points = config.get('min_data_points', 50)
        self.market_state_update_interval = config.get('market_state_update_interval', 3600)  # 1 hour
        
        # Market condition thresholds
        self.volatility_thresholds = config.get('volatility_thresholds', {
            'low': 0.0003,    # 0.03% price change per period (low volatility)
            'medium': 0.0007, # 0.07% price change per period (medium volatility)
            'high': 0.0012    # 0.12% price change per period (high volatility)
        })
        
        self.trend_thresholds = config.get('trend_thresholds', {
            'weak': 0.1,      # ADX below 20 indicates weak trend
            'moderate': 0.25, # ADX between 20-40 indicates moderate trend
            'strong': 0.4     # ADX above 40 indicates strong trend
        })
        
        # Strategy strengths for forex instruments
        # Values from 0 (weak) to 10 (strong)
        self.forex_strategy_strengths = {
            'break_and_retest': {
                'range_market': 8,
                'trending_market': 6,
                'high_volatility': 5,
                'low_volatility': 7,
                'overall': 7
            },
            'break_of_structure': {
                'range_market': 4,
                'trending_market': 9,
                'high_volatility': 7,
                'low_volatility': 5,
                'overall': 6
            },
            'fair_value_gap': {
                'range_market': 5,
                'trending_market': 8,
                'high_volatility': 8,
                'low_volatility': 4,
                'overall': 7
            },
            'jhook_pattern': {
                'range_market': 3,
                'trending_market': 9,
                'high_volatility': 6,
                'low_volatility': 6,
                'overall': 6
            },
            'ma_rsi_combo': {
                'range_market': 4,
                'trending_market': 9,
                'high_volatility': 5,
                'low_volatility': 8,
                'overall': 7
            },
            'stochastic_cross': {
                'range_market': 8,
                'trending_market': 4,
                'high_volatility': 6,
                'low_volatility': 7,
                'overall': 6
            },
            'bnr_strategy': {
                'range_market': 9,
                'trending_market': 5,
                'high_volatility': 4,
                'low_volatility': 8,
                'overall': 7
            },
            'jhook_strategy': {
                'range_market': 3,
                'trending_market': 8,
                'high_volatility': 6,
                'low_volatility': 5,
                'overall': 6
            }
        }
        
        # Strategy strengths for synthetic indices
        # Optimized for algorithmic-driven synthetic markets
        self.synthetic_strategy_strengths = {
            # For Volatility indices - focus on quick reversals and range trading
            'volatility': {
                'break_and_retest': {
                    'range_market': 9,
                    'trending_market': 5,
                    'high_volatility': 8,
                    'low_volatility': 6,
                    'overall': 8
                },
                'break_of_structure': {
                    'range_market': 4,
                    'trending_market': 7,
                    'high_volatility': 8,
                    'low_volatility': 3,
                    'overall': 6
                },
                'fair_value_gap': {
                    'range_market': 7,
                    'trending_market': 6,
                    'high_volatility': 9,
                    'low_volatility': 4,
                    'overall': 7
                },
                'jhook_pattern': {
                    'range_market': 3,
                    'trending_market': 6,
                    'high_volatility': 7,
                    'low_volatility': 4,
                    'overall': 5
                },
                'ma_rsi_combo': {
                    'range_market': 3,
                    'trending_market': 8,
                    'high_volatility': 7,
                    'low_volatility': 5,
                    'overall': 6
                },
                'stochastic_cross': {
                    'range_market': 9,
                    'trending_market': 4,
                    'high_volatility': 6,
                    'low_volatility': 8,
                    'overall': 7
                },
                'bnr_strategy': {
                    'range_market': 9,
                    'trending_market': 4,
                    'high_volatility': 5,
                    'low_volatility': 8,
                    'overall': 7
                },
                'jhook_strategy': {
                    'range_market': 3,
                    'trending_market': 7,
                    'high_volatility': 6,
                    'low_volatility': 5,
                    'overall': 5
                }
            },
            # For Crash/Boom indices - focus on momentum and trend following
            'crash_boom': {
                'break_and_retest': {
                    'range_market': 3,
                    'trending_market': 7,
                    'high_volatility': 8,
                    'low_volatility': 2,
                    'overall': 6
                },
                'break_of_structure': {
                    'range_market': 4,
                    'trending_market': 9,
                    'high_volatility': 9,
                    'low_volatility': 3,
                    'overall': 8
                },
                'fair_value_gap': {
                    'range_market': 3,
                    'trending_market': 8,
                    'high_volatility': 9,
                    'low_volatility': 2,
                    'overall': 7
                },
                'jhook_pattern': {
                    'range_market': 2,
                    'trending_market': 9,
                    'high_volatility': 9,
                    'low_volatility': 2,
                    'overall': 7
                },
                'ma_rsi_combo': {
                    'range_market': 3,
                    'trending_market': 8,
                    'high_volatility': 8,
                    'low_volatility': 4,
                    'overall': 6
                },
                'stochastic_cross': {
                    'range_market': 5,
                    'trending_market': 6,
                    'high_volatility': 9,
                    'low_volatility': 3,
                    'overall': 6
                },
                'bnr_strategy': {
                    'range_market': 7,
                    'trending_market': 5,
                    'high_volatility': 8,
                    'low_volatility': 4,
                    'overall': 6
                },
                'jhook_strategy': {
                    'range_market': 2,
                    'trending_market': 7,
                    'high_volatility': 8,
                    'low_volatility': 3,
                    'overall': 5
                }
            },
            # For Step indices - focus on consistent small movements
            'step': {
                'break_and_retest': {
                    'range_market': 9,
                    'trending_market': 4,
                    'high_volatility': 3,
                    'low_volatility': 9,
                    'overall': 7
                },
                'break_of_structure': {
                    'range_market': 3,
                    'trending_market': 6,
                    'high_volatility': 4,
                    'low_volatility': 8,
                    'overall': 5
                },
                'fair_value_gap': {
                    'range_market': 6,
                    'trending_market': 5,
                    'high_volatility': 4,
                    'low_volatility': 8,
                    'overall': 6
                },
                'jhook_pattern': {
                    'range_market': 5,
                    'trending_market': 9,
                    'high_volatility': 5,
                    'low_volatility': 7,
                    'overall': 7
                },
                'ma_rsi_combo': {
                    'range_market': 6,
                    'trending_market': 8,
                    'high_volatility': 6,
                    'low_volatility': 7,
                    'overall': 7
                },
                'stochastic_cross': {
                    'range_market': 8,
                    'trending_market': 5,
                    'high_volatility': 5,
                    'low_volatility': 8,
                    'overall': 7
                },
                'bnr_strategy': {
                    'range_market': 9,
                    'trending_market': 5,
                    'high_volatility': 4,
                    'low_volatility': 9,
                    'overall': 7
                },
                'jhook_strategy': {
                    'range_market': 5,
                    'trending_market': 8,
                    'high_volatility': 5,
                    'low_volatility': 7,
                    'overall': 6
                }
            }
        }
        
        # Default strategy strengths (used when no specific type is matched)
        self.strategy_strengths = self.forex_strategy_strengths
        
        # Strategy instances
        self.strategies = {}
        
        # Cache of market condition analysis
        self.market_conditions = {}
        self.last_analysis_time = {}
        
        # Initialize strategy instances
        self._initialize_strategies()
        
        logger.info("Strategy selector initialized")
        
    def _initialize_strategies(self):
        """Initialize all available strategy instances"""
        for strategy_name, strategy_config in self.strategies_config.items():
            if strategy_config.get('enabled', False):
                logger.info(f"Initializing strategy: {strategy_name}")
                try:
                    self.strategies[strategy_name] = create_strategy(strategy_name, strategy_config)
                except Exception as e:
                    logger.error(f"Error initializing strategy {strategy_name}: {str(e)}")
    
    def select_strategy(self, symbol: str, data: pd.DataFrame) -> Optional[str]:
        """
        Select the best strategy based on current market conditions
        
        Args:
            symbol: Trading symbol
            data: Market data as pandas DataFrame with OHLCV
            
        Returns:
            Name of the best strategy to use
        """
        if len(data) < self.min_data_points:
            logger.warning(f"Insufficient data points for {symbol} strategy selection")
            return None
            
        # Get instrument type from dataframe attributes if available
        instrument_type = data.attrs.get('instrument_type', 'forex')
        instrument_subtype = data.attrs.get('instrument_subtype', None)
        
        logger.debug(f"Selecting strategy for {symbol}, type: {instrument_type}, subtype: {instrument_subtype}")
        
        # Analyze market conditions
        market_condition = self._analyze_market_conditions(symbol, data, instrument_type)
        
        # Rank strategies based on current conditions and instrument type
        strategy_scores = self._rank_strategies(market_condition, instrument_type, instrument_subtype)
        
        # Get the best strategy
        if not strategy_scores:
            logger.warning(f"No suitable strategies found for {symbol}")
            return None
        
        best_strategy = max(strategy_scores.items(), key=lambda x: x[1])[0]
        strategy_score = strategy_scores[best_strategy]
        
        logger.info(f"Selected {best_strategy} for {symbol} ({instrument_type}) with score {strategy_score:.2f}")
        logger.debug(f"Market conditions: {market_condition}")
        
        return best_strategy
    
    def _analyze_market_conditions(self, symbol: str, data: pd.DataFrame, instrument_type: str = 'forex') -> Dict:
        """
        Analyze current market conditions
        
        Args:
            symbol: Trading symbol
            data: Market data
            instrument_type: Type of instrument (forex, synthetic)
            
        Returns:
            Dictionary with market condition analysis
        """
        current_time = datetime.now()
        
        # Check if we have recent analysis
        if (symbol in self.last_analysis_time and 
            (current_time - self.last_analysis_time[symbol]).total_seconds() < self.market_state_update_interval):
            return self.market_conditions.get(symbol, {})
        
        # Calculate indicators
        close = data['close']
        high = data['high']
        low = data['low']
        
        # Volatility indicators
        atr = AverageTrueRange(high=high, low=low, close=close, window=14)
        atr_value = atr.average_true_range().iloc[-1]
        atr_percent = atr_value / close.iloc[-1]
        
        bb = BollingerBands(close=close, window=20, window_dev=2)
        bb_width = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()
        bb_width_value = bb_width.iloc[-1]
        
        # Trend indicators
        ema_fast = EMAIndicator(close=close, window=20)
        ema_slow = EMAIndicator(close=close, window=50)
        ema_fast_value = ema_fast.ema_indicator().iloc[-1]
        ema_slow_value = ema_slow.ema_indicator().iloc[-1]
        
        # Calculate ADX (Average Directional Index)
        # Simplified implementation
        plus_dm = high.diff()
        minus_dm = low.diff(-1)
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr = pd.DataFrame({
            'hl': high - low,
            'hc': (high - close.shift(1)).abs(),
            'lc': (low - close.shift(1)).abs()
        }).max(axis=1)
        
        tr14 = tr.rolling(window=14).mean()
        plus_di14 = 100 * (plus_dm.rolling(window=14).mean() / tr14)
        minus_di14 = 100 * (minus_dm.rolling(window=14).mean() / tr14)
        
        dx = 100 * ((plus_di14 - minus_di14).abs() / (plus_di14 + minus_di14).abs())
        adx = dx.rolling(window=14).mean()
        adx_value = adx.iloc[-1] / 100  # Normalize to 0-1 range
        
        # Momentum indicators
        rsi = RSIIndicator(close=close, window=14)
        rsi_value = rsi.rsi().iloc[-1] / 100  # Normalize to 0-1 range
        
        # Classify market condition
        
        # Adjust volatility thresholds based on instrument type
        volatility_thresholds = self.volatility_thresholds
        if instrument_type == 'synthetic':
            # Synthetic indices generally have higher volatility
            volatility_thresholds = {
                'low': self.volatility_thresholds['low'] * 2,
                'medium': self.volatility_thresholds['medium'] * 2,
                'high': self.volatility_thresholds['high'] * 2
            }
        
        # Determine volatility level
        if atr_percent < volatility_thresholds['low']:
            volatility = 'low'
        elif atr_percent < volatility_thresholds['medium']:
            volatility = 'medium'
        else:
            volatility = 'high'
        
        # Determine trend strength
        if adx_value < self.trend_thresholds['weak']:
            trend_strength = 'weak'
        elif adx_value < self.trend_thresholds['moderate']:
            trend_strength = 'moderate'
        else:
            trend_strength = 'strong'
        
        # Determine trend direction
        trend_direction = 'sideways'
        if ema_fast_value > ema_slow_value:
            trend_direction = 'uptrend'
        elif ema_fast_value < ema_slow_value:
            trend_direction = 'downtrend'
        
        # Determine if market is ranging
        in_range = abs(ema_fast_value - ema_slow_value) / ema_slow_value < 0.001
        
        # Determine overbought/oversold condition
        market_condition = 'neutral'
        if rsi_value > 0.7:
            market_condition = 'overbought'
        elif rsi_value < 0.3:
            market_condition = 'oversold'
        
        # Compile market condition
        result = {
            'volatility': volatility,
            'trend_strength': trend_strength,
            'trend_direction': trend_direction,
            'in_range': in_range,
            'market_condition': market_condition,
            'atr_value': atr_percent,
            'adx_value': adx_value,
            'rsi_value': rsi_value,
            'bb_width': bb_width_value,
            'ema_diff': (ema_fast_value - ema_slow_value) / ema_slow_value,
            'instrument_type': instrument_type
        }
        
        # Cache the result
        self.market_conditions[symbol] = result
        self.last_analysis_time[symbol] = current_time
        
        return result
    
    def _rank_strategies(self, market_condition: Dict, instrument_type: str = 'forex', 
                        instrument_subtype: Optional[str] = None) -> Dict:
        """
        Rank available strategies based on market conditions and instrument type
        
        Args:
            market_condition: Market condition dictionary
            instrument_type: Type of instrument (forex, synthetic)
            instrument_subtype: Subtype of synthetic instrument (volatility, crash_boom, etc.)
            
        Returns:
            Dictionary with strategy scores
        """
        # Choose strategy strengths based on instrument type
        strategy_strengths = self.forex_strategy_strengths
        
        if instrument_type == 'synthetic':
            if instrument_subtype in self.synthetic_strategy_strengths:
                strategy_strengths = self.synthetic_strategy_strengths[instrument_subtype]
            elif instrument_subtype == 'jump':
                # Use crash/boom settings for jump indices
                strategy_strengths = self.synthetic_strategy_strengths['crash_boom']
            else:
                # Default to volatility settings for other synthetic indices
                strategy_strengths = self.synthetic_strategy_strengths['volatility']
        
        # Calculate scores
        scores = {}
        
        # Skip strategies that are not enabled or available
        available_strategies = set(self.strategies.keys())
        
        for strategy_name, strengths in strategy_strengths.items():
            if strategy_name not in available_strategies:
                continue
                
            # Base score from overall rating
            score = strengths['overall'] * 0.4
            
            # Add score based on market conditions
            if market_condition['in_range']:
                score += strengths['range_market'] * 0.2
            elif market_condition['trend_strength'] in ['moderate', 'strong']:
                score += strengths['trending_market'] * 0.2
            
            # Add score based on volatility
            if market_condition['volatility'] == 'high':
                score += strengths['high_volatility'] * 0.2
            elif market_condition['volatility'] == 'low':
                score += strengths['low_volatility'] * 0.2
            else:  # medium volatility
                score += (strengths['high_volatility'] + strengths['low_volatility']) * 0.1
            
            # Apply market-specific adjustments
            if market_condition['market_condition'] == 'overbought' and strategy_name == 'break_of_structure':
                # BoS works well for reversals from overbought
                score += 1.0
            elif market_condition['market_condition'] == 'oversold' and strategy_name == 'jhook_pattern':
                # JHook pattern works well for reversals from oversold
                score += 1.0
            elif market_condition['market_condition'] == 'overbought' and strategy_name == 'stochastic_cross':
                # Stochastic Cross works well for overbought conditions
                score += 1.0
            elif market_condition['market_condition'] == 'oversold' and strategy_name == 'ma_rsi_combo':
                # MA + RSI works well for oversold conditions
                score += 1.0
            
            # Apply instrument-specific adjustments
            if instrument_type == 'synthetic':
                if instrument_subtype == 'volatility' and strategy_name == 'break_and_retest':
                    # Break and retest works well for volatility indices
                    score += 1.0
                elif instrument_subtype == 'crash_boom' and strategy_name == 'break_of_structure':
                    # BoS works well for crash/boom indices to catch the spikes
                    score += 1.5
                elif instrument_subtype == 'step' and strategy_name == 'fair_value_gap':
                    # FVG works well for step indices with predictable movements
                    score += 1.0
            
            scores[strategy_name] = score
        
        return scores
    
    def get_strategy_instance(self, strategy_name: str):
        """
        Get a strategy instance by name
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            Strategy instance or None if not found
        """
        return self.strategies.get(strategy_name)
