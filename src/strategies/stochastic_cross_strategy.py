"""
Stochastic Cross Strategy for Forex Trading
Implements a strategy that trades crossovers in oversold/overbought regions
Uses Stochastic (5,3,3) for precise entry and exit timing
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union
from loguru import logger
import ta
from datetime import datetime, timedelta

class StochasticCrossStrategy:
    """
    Stochastic Cross Strategy
    Trades crossovers in oversold/overbought regions using Stochastic oscillator
    Effective for scalping in M1 and M5 timeframes
    """
    
    def __init__(self, strategy_config: dict):
        """
        Initialize the Stochastic Cross strategy
        
        Args:
            strategy_config: Dictionary with strategy configuration
        """
        self.config = strategy_config
        self.name = "stochastic_cross"
        
        # Get timeframe from config or use default
        self.timeframe = strategy_config.get('timeframe', 'M1')  # Default to 1-minute chart for faster scalping
        
        # Stochastic oscillator parameters (default 5,3,3 for fast scalping)
        self.stoch_config = strategy_config.get('stochastic', {})
        self.stoch_k_period = self.stoch_config.get('k_period', 5)  # %K period 
        self.stoch_d_period = self.stoch_config.get('d_period', 3)  # %D period
        self.stoch_smooth = self.stoch_config.get('smooth', 3)      # Smoothing
        
        # Threshold levels
        self.overbought_level = self.stoch_config.get('overbought_level', 80)
        self.oversold_level = self.stoch_config.get('oversold_level', 20)
        self.middle_zone_upper = self.stoch_config.get('middle_zone_upper', 60)
        self.middle_zone_lower = self.stoch_config.get('middle_zone_lower', 40)
        
        # Additional filter indicators
        self.use_ema_filter = strategy_config.get('use_ema_filter', True)
        self.ema_period = strategy_config.get('ema_period', 50)
        
        # Entry/exit parameters
        self.entry_config = strategy_config.get('entry', {})
        self.exit_config = strategy_config.get('exit', {})
        
        # Risk settings
        self.risk_per_trade = strategy_config.get('risk_per_trade', 0.01)  # 1% risk per trade by default
        
        # Signal tracking
        self.signals = {}
        self.last_signal_time = {}
        
        logger.info(f"Stochastic Cross strategy initialized with {self.timeframe} timeframe")
    
    def generate_signal(self, symbol: str, data: pd.DataFrame) -> Dict:
        """
        Generate trading signal based on Stochastic Cross strategy
        
        Args:
            symbol: Trading symbol/pair
            data: OHLCV DataFrame with price data
            
        Returns:
            Signal dictionary with trading action and parameters
        """
        if len(data) < max(self.stoch_k_period + self.stoch_d_period + self.stoch_smooth, self.ema_period) + 5:
            logger.warning(f"Not enough data for {symbol} to generate Stochastic signals")
            return {'action': 'NONE', 'symbol': symbol}
        
        # Calculate indicators
        df = self._calculate_indicators(data)
        
        # Check for valid signal
        signal = self._check_signal_conditions(symbol, df)
        
        # Store signal in history
        if symbol not in self.signals:
            self.signals[symbol] = []
        
        if signal and signal.get('action') != 'NONE':
            self.signals[symbol].append(signal)
            self.last_signal_time[symbol] = datetime.now()
            
            # Limit history to last 100 signals
            if len(self.signals[symbol]) > 100:
                self.signals[symbol] = self.signals[symbol][-100:]
        
        return signal or {'action': 'NONE', 'symbol': symbol}
    
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Stochastic and other indicators
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            DataFrame with added indicator columns
        """
        df = data.copy()
        
        # Calculate Stochastic Oscillator
        stoch = ta.momentum.StochasticOscillator(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=self.stoch_k_period,
            smooth_window=self.stoch_smooth,
            fillna=True
        )
        
        # Add %K and %D lines
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        
        # Calculate cross conditions
        df['k_above_d'] = df['stoch_k'] > df['stoch_d']
        
        # Identify crossovers
        df['k_cross_above_d'] = (df['k_above_d'] != df['k_above_d'].shift(1)) & df['k_above_d']
        df['k_cross_below_d'] = (df['k_above_d'] != df['k_above_d'].shift(1)) & ~df['k_above_d']
        
        # Identify overbought and oversold conditions
        df['overbought'] = df['stoch_k'] > self.overbought_level
        df['oversold'] = df['stoch_k'] < self.oversold_level
        
        # Identify stochastic zones (useful for determining signal context)
        df['stoch_zone'] = 'middle'
        df.loc[df['stoch_k'] > self.overbought_level, 'stoch_zone'] = 'overbought'
        df.loc[df['stoch_k'] < self.oversold_level, 'stoch_zone'] = 'oversold'
        df.loc[(df['stoch_k'] > self.middle_zone_upper) & (df['stoch_k'] <= self.overbought_level), 'stoch_zone'] = 'high_middle'
        df.loc[(df['stoch_k'] < self.middle_zone_lower) & (df['stoch_k'] >= self.oversold_level), 'stoch_zone'] = 'low_middle'
        
        # Calculate trend indicator if EMA filter is enabled
        if self.use_ema_filter:
            ema_indicator = ta.trend.EMAIndicator(df['close'], window=self.ema_period, fillna=True)
            df[f'ema_{self.ema_period}'] = ema_indicator.ema_indicator()
            df['price_above_ema'] = df['close'] > df[f'ema_{self.ema_period}']
        
        # Add ATR for stop loss calculation
        atr_indicator = ta.volatility.AverageTrueRange(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=14,
            fillna=True
        )
        df['atr'] = atr_indicator.average_true_range()
        
        return df
    
    def _check_signal_conditions(self, symbol: str, df: pd.DataFrame) -> Optional[Dict]:
        """
        Check for trading signal conditions using Stochastic crossovers
        
        Args:
            symbol: Trading symbol
            df: DataFrame with indicators
            
        Returns:
            Signal dictionary or None
        """
        # Get the most recent candles
        if len(df) < 5:  # Need at least a few candles to analyze
            return None
            
        current = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]
        
        # Initialize signal variables
        action = "NONE"
        signal_reasons = []
        signal_strength = 0.0
        
        # Check for bullish signal (Stochastic %K crosses above %D in oversold region)
        bullish_conditions = [
            # Primary condition: K crossing above D
            current['k_cross_above_d'],
            
            # Condition 2: In or coming from oversold zone
            prev['stoch_zone'] == 'oversold' or current['stoch_zone'] == 'oversold' or prev['stoch_zone'] == 'low_middle',
            
            # Condition 3: Stochastic values are low but increasing
            current['stoch_k'] > prev['stoch_k'] and current['stoch_k'] < 40
        ]
        
        # EMA filter for bull setup (optional)
        if self.use_ema_filter:
            ema_bull_condition = current['price_above_ema'] or (not prev['price_above_ema'] and current['price_above_ema'])
            bullish_conditions.append(ema_bull_condition)
        
        # Check for bearish signal (Stochastic %K crosses below %D in overbought region)
        bearish_conditions = [
            # Primary condition: K crossing below D
            current['k_cross_below_d'],
            
            # Condition 2: In or coming from overbought zone
            prev['stoch_zone'] == 'overbought' or current['stoch_zone'] == 'overbought' or prev['stoch_zone'] == 'high_middle',
            
            # Condition 3: Stochastic values are high but decreasing
            current['stoch_k'] < prev['stoch_k'] and current['stoch_k'] > 60
        ]
        
        # EMA filter for bear setup (optional)
        if self.use_ema_filter:
            ema_bear_condition = not current['price_above_ema'] or (prev['price_above_ema'] and not current['price_above_ema'])
            bearish_conditions.append(ema_bear_condition)
        
        # Calculate signal strength based on condition count
        bull_score = sum(bullish_conditions) / len(bullish_conditions) if bullish_conditions else 0
        bear_score = sum(bearish_conditions) / len(bearish_conditions) if bearish_conditions else 0
        
        # Buy signal - K crosses above D in oversold region
        if bull_score >= 0.7:  # At least 70% of conditions match
            action = "BUY"
            signal_strength = bull_score
            
            signal_reasons.append(f"Stochastic %K crossed above %D")
            signal_reasons.append(f"Stochastic value: {current['stoch_k']:.1f}")
            
            if 'stoch_zone' in current and current['stoch_zone'] == 'oversold':
                signal_reasons.append("Signal from oversold region")
                signal_strength += 0.1
                
            if self.use_ema_filter and current['price_above_ema']:
                signal_reasons.append(f"Price above {self.ema_period} EMA")
                signal_strength += 0.1
        
        # Sell signal - K crosses below D in overbought region
        elif bear_score >= 0.7:  # At least 70% of conditions match
            action = "SELL"
            signal_strength = bear_score
            
            signal_reasons.append(f"Stochastic %K crossed below %D")
            signal_reasons.append(f"Stochastic value: {current['stoch_k']:.1f}")
            
            if 'stoch_zone' in current and current['stoch_zone'] == 'overbought':
                signal_reasons.append("Signal from overbought region")
                signal_strength += 0.1
                
            if self.use_ema_filter and not current['price_above_ema']:
                signal_reasons.append(f"Price below {self.ema_period} EMA")
                signal_strength += 0.1
        
        # No valid signal
        if action == "NONE" or not signal_reasons:
            return {'action': 'NONE', 'symbol': symbol}
        
        # Prevent trading too frequently
        min_time_between_signals = timedelta(minutes=15)  # Adjust for fast scalping
        if symbol in self.last_signal_time:
            time_since_last = datetime.now() - self.last_signal_time[symbol]
            if time_since_last < min_time_between_signals:
                return {'action': 'NONE', 'symbol': symbol, 'reason': 'Too soon after previous signal'}
        
        # Calculate stop loss and take profit levels
        current_price = current['close']
        atr = current['atr'] if not pd.isna(current['atr']) else current_price * 0.001
        
        # Dynamic stop loss based on ATR and timeframe-appropriate multipliers
        # For faster timeframes like M1, use smaller multipliers
        if self.timeframe == 'M1':
            sl_multiplier = 1.0
            tp_multiplier = 1.5
        else:  # M5, etc.
            sl_multiplier = 1.5
            tp_multiplier = 2.0
            
        # Apply configuration overrides if present
        sl_multiplier = self.exit_config.get('sl_atr_multiplier', sl_multiplier)
        tp_multiplier = self.exit_config.get('tp_atr_multiplier', tp_multiplier)
        
        if action == "BUY":
            stop_loss = current_price - (atr * sl_multiplier)
            take_profit = current_price + (atr * tp_multiplier)
        else:  # SELL
            stop_loss = current_price + (atr * sl_multiplier)
            take_profit = current_price - (atr * tp_multiplier)
        
        # Create signal dictionary
        signal = {
            'symbol': symbol,
            'action': action,
            'direction': action,  # For compatibility with some systems
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': datetime.now().isoformat(),
            'reasons': signal_reasons,
            'strength': min(1.0, signal_strength),
            'strategy': 'STOCHASTIC_CROSS',
            'timeframe': self.timeframe
        }
        
        return signal
    
    def calculate_position_size(self, symbol: str, direction: str, data: pd.DataFrame, account_balance: float) -> float:
        """
        Calculate position size based on risk parameters
        
        Args:
            symbol: Trading symbol
            direction: Trade direction (BUY/SELL)
            data: Market data DataFrame
            account_balance: Current account balance
            
        Returns:
            Position size in lots
        """
        # Check for valid data
        if len(data) < 20:
            logger.warning(f"Not enough data to calculate position size for {symbol}")
            return 0.01  # Minimum position size
        
        # Calculate indicators if not already done
        if 'stoch_k' not in data.columns or 'atr' not in data.columns:
            df = self._calculate_indicators(data)
        else:
            df = data
            
        current_price = df['close'].iloc[-1]
        
        # Get ATR for dynamic stop loss
        atr = df['atr'].iloc[-1] if not pd.isna(df['atr'].iloc[-1]) else current_price * 0.001
        
        # Calculate stop loss distance based on timeframe
        if self.timeframe == 'M1':
            sl_multiplier = 1.0
        else:  # M5, etc.
            sl_multiplier = 1.5
            
        sl_multiplier = self.exit_config.get('sl_atr_multiplier', sl_multiplier)
        stop_loss_distance = atr * sl_multiplier
        
        # Risk amount is risk_per_trade% of account balance
        risk_amount = account_balance * self.risk_per_trade
        
        # Adjust for forex pair pip value (simplified)
        pip_value = 0.0001 if 'JPY' not in symbol else 0.01
        pip_distance = stop_loss_distance / pip_value
        
        # Approximate pip value (would need to be adjusted for different account currencies)
        pip_value_per_lot = 10  # $10 per pip for 1 standard lot
        
        # Calculate position size in lots
        if pip_distance == 0:
            logger.warning(f"Zero pip distance for {symbol}, using default position size")
            return 0.01
            
        position_size_lots = risk_amount / (pip_distance * pip_value_per_lot)
        
        # Apply position size limits - for faster scalping, use smaller positions
        min_lot = 0.01  # Micro lot
        max_lot = 0.3 if self.timeframe == 'M1' else 0.5  # Lower max size for M1 timeframe
        
        position_size_lots = max(min_lot, min(position_size_lots, max_lot))
        
        return round(position_size_lots, 2)
    
    def validate_signal(self, symbol: str, signal: Dict, market_condition: Dict) -> bool:
        """
        Validate signal against current market conditions
        
        Args:
            symbol: Trading symbol
            signal: Signal dictionary
            market_condition: Dictionary with market condition information
            
        Returns:
            True if signal is valid, False otherwise
        """
        # Skip validation if market condition info is missing
        if not market_condition:
            return True
            
        action = signal.get('action')
        
        # Get market condition factors
        volatility = market_condition.get('volatility', 'medium')
        trend = market_condition.get('trend', 'ranging')
        liquidity = market_condition.get('liquidity', 'normal')
        
        # Stochastic works well in ranging markets
        if trend in ['strong_bullish', 'strong_bearish'] and action != 'NONE':
            if action == 'BUY' and trend == 'strong_bearish':
                logger.info(f"Stochastic signal rejected: {symbol} is in strong bearish trend, avoiding counter-trend buy")
                return False
            elif action == 'SELL' and trend == 'strong_bullish':
                logger.info(f"Stochastic signal rejected: {symbol} is in strong bullish trend, avoiding counter-trend sell")
                return False
            
        # Avoid low liquidity conditions
        if liquidity == 'low':
            logger.info(f"Stochastic signal rejected: {symbol} has low liquidity")
            return False
            
        # Stochastic often works better in low-medium volatility
        if volatility == 'high' and self.timeframe in ['M1', 'M5']:
            logger.info(f"Stochastic signal caution: {symbol} has high volatility in fast timeframe")
            # Don't reject outright but could adjust settings
            
        return True
