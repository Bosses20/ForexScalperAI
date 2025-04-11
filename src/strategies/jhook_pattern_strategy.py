"""
JHook Pattern Strategy for Forex Trading
Implements a strategy that identifies and trades the JHook reversal pattern
Specializes in capturing reversals at the end of trends
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple
from loguru import logger
import ta
from datetime import datetime, timedelta

class JHookPatternStrategy:
    """
    JHook Pattern Strategy
    Identifies and trades the JHook reversal pattern, which occurs after a trend has exhausted
    Particularly effective for catching reversals from oversold/overbought conditions
    """
    
    def __init__(self, strategy_config: dict):
        """
        Initialize the JHook Pattern strategy
        
        Args:
            strategy_config: Dictionary with strategy configuration
        """
        self.config = strategy_config
        self.name = "jhook_pattern"
        
        # Get timeframe from config or use default
        self.timeframe = strategy_config.get('timeframe', 'H1')  # Default to 1-hour chart
        
        # Pattern detection parameters
        self.pattern_config = strategy_config.get('pattern', {})
        self.lookback_periods = self.pattern_config.get('lookback_periods', 50)
        self.trend_length = self.pattern_config.get('min_trend_length', 10)
        self.reversal_strength = self.pattern_config.get('reversal_strength', 30)  # Percent of trend retraced
        self.continuation_strength = self.pattern_config.get('continuation_strength', 20)  # Percent continuation
        
        # Indicators configuration
        self.indicator_config = strategy_config.get('indicators', {})
        
        # RSI settings for confirmation
        self.rsi_config = self.indicator_config.get('rsi', {})
        self.rsi_period = self.rsi_config.get('period', 14)
        self.rsi_overbought = self.rsi_config.get('overbought', 70)
        self.rsi_oversold = self.rsi_config.get('oversold', 30)
        
        # MACD settings for trend confirmation
        self.macd_config = self.indicator_config.get('macd', {})
        self.macd_fast = self.macd_config.get('fast_period', 12)
        self.macd_slow = self.macd_config.get('slow_period', 26)
        self.macd_signal = self.macd_config.get('signal_period', 9)
        
        # Order management
        self.entry_config = strategy_config.get('entry', {})
        self.exit_config = strategy_config.get('exit', {})
        
        # Risk settings
        self.risk_per_trade = strategy_config.get('risk_per_trade', 0.01)  # 1% risk per trade by default
        
        # Signal tracking
        self.signals = {}
        self.last_signal_time = {}
        self.identified_patterns = {}  # Store identified JHook patterns by symbol
        
        logger.info(f"JHook Pattern strategy initialized with {self.timeframe} timeframe")
    
    def generate_signal(self, symbol: str, data: pd.DataFrame) -> Dict:
        """
        Generate trading signal based on JHook Pattern strategy
        
        Args:
            symbol: Trading symbol/pair
            data: OHLCV DataFrame with price data
            
        Returns:
            Signal dictionary with trading action and parameters
        """
        if len(data) < self.lookback_periods + 10:
            logger.warning(f"Not enough data for {symbol} to detect JHook patterns")
            return {'action': 'NONE', 'symbol': symbol}
        
        # Process data
        processed_data = self._calculate_indicators(data.copy())
        
        # Identify JHook patterns
        patterns = self._identify_jhook_patterns(symbol, processed_data)
        
        if patterns:
            self.identified_patterns[symbol] = patterns
            
            # Get most recent pattern for signal generation
            latest_pattern = patterns[-1]
            
            # Check if the pattern is actionable (recent and valid)
            if self._is_pattern_valid(latest_pattern, processed_data):
                signal = self._create_signal_from_pattern(symbol, latest_pattern, processed_data)
                
                # Store signal in history
                if symbol not in self.signals:
                    self.signals[symbol] = []
                
                if signal and signal.get('action') != 'NONE':
                    self.signals[symbol].append(signal)
                    self.last_signal_time[symbol] = datetime.now()
                    
                    # Limit history to last 100 signals
                    if len(self.signals[symbol]) > 100:
                        self.signals[symbol] = self.signals[symbol][-100:]
                        
                    return signal
        
        return {'action': 'NONE', 'symbol': symbol}
    
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators needed for JHook pattern detection
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            DataFrame with added indicator columns
        """
        df = data.copy()
        
        # Calculate RSI
        rsi_indicator = ta.momentum.RSIIndicator(
            close=df['close'],
            window=self.rsi_period,
            fillna=True
        )
        df['rsi'] = rsi_indicator.rsi()
        df['rsi_overbought'] = df['rsi'] > self.rsi_overbought
        df['rsi_oversold'] = df['rsi'] < self.rsi_oversold
        
        # Calculate MACD
        macd = ta.trend.MACD(
            close=df['close'],
            window_slow=self.macd_slow,
            window_fast=self.macd_fast,
            window_sign=self.macd_signal,
            fillna=True
        )
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_histogram'] = macd.macd_diff()
        df['macd_above_signal'] = df['macd'] > df['macd_signal']
        
        # Calculate Bollinger Bands for volatility context
        bollinger = ta.volatility.BollingerBands(
            close=df['close'],
            window=20,
            window_dev=2,
            fillna=True
        )
        df['bb_upper'] = bollinger.bollinger_hband()
        df['bb_lower'] = bollinger.bollinger_lband()
        df['bb_middle'] = bollinger.bollinger_mavg()
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Calculate ATR for stop loss calculation
        atr_indicator = ta.volatility.AverageTrueRange(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=14,
            fillna=True
        )
        df['atr'] = atr_indicator.average_true_range()
        
        # Calculate EMAs for trend context
        df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50, fillna=True)
        df['ema_100'] = ta.trend.ema_indicator(df['close'], window=100, fillna=True)
        df['price_above_ema50'] = df['close'] > df['ema_50']
        df['price_above_ema100'] = df['close'] > df['ema_100']
        
        # Add percentage change column for measuring moves
        df['pct_change'] = df['close'].pct_change()
        
        # Identify swings using a sliding window approach
        self._identify_swings(df)
        
        return df
    
    def _identify_swings(self, df: pd.DataFrame, window: int = 5) -> None:
        """
        Identify price swings (highs and lows) in the data
        
        Args:
            df: OHLCV DataFrame
            window: Window size for detecting swings
        """
        # Initialize swing columns
        df['swing_high'] = False
        df['swing_low'] = False
        df['swing_high_price'] = np.nan
        df['swing_low_price'] = np.nan
        
        # Minimum bars to identify a swing
        for i in range(window, len(df) - window):
            # Check if this is a swing high
            if all(df.iloc[i]['high'] > df.iloc[i-j]['high'] for j in range(1, window+1)) and \
               all(df.iloc[i]['high'] > df.iloc[i+j]['high'] for j in range(1, window+1)):
                df.iloc[i, df.columns.get_loc('swing_high')] = True
                df.iloc[i, df.columns.get_loc('swing_high_price')] = df.iloc[i]['high']
            
            # Check if this is a swing low
            if all(df.iloc[i]['low'] < df.iloc[i-j]['low'] for j in range(1, window+1)) and \
               all(df.iloc[i]['low'] < df.iloc[i+j]['low'] for j in range(1, window+1)):
                df.iloc[i, df.columns.get_loc('swing_low')] = True
                df.iloc[i, df.columns.get_loc('swing_low_price')] = df.iloc[i]['low']
                
        # Fill swing high/low prices forward to make them easier to use
        df['swing_high_price'] = df['swing_high_price'].fillna(method='ffill')
        df['swing_low_price'] = df['swing_low_price'].fillna(method='ffill')
    
    def _identify_jhook_patterns(self, symbol: str, df: pd.DataFrame) -> List[Dict]:
        """
        Identify JHook patterns in the price data
        
        Args:
            symbol: Trading symbol
            df: Processed DataFrame with indicators
            
        Returns:
            List of identified JHook patterns
        """
        patterns = []
        
        # Need at least enough data to identify a trend and reversal
        if len(df) < self.trend_length + 10:
            return patterns
            
        # JHook is typically a reversal pattern after a strong trend
        # We look for a strong trend, followed by a reversal, then continuation in the original direction
        
        # For each potential end point of a pattern (excluding the most recent few bars)
        for i in range(self.trend_length + 10, len(df) - 5):
            # For bullish JHook (after downtrend)
            bullish_jhook = self._check_bullish_jhook(df, i)
            if bullish_jhook:
                patterns.append(bullish_jhook)
                
            # For bearish JHook (after uptrend)
            bearish_jhook = self._check_bearish_jhook(df, i)
            if bearish_jhook:
                patterns.append(bearish_jhook)
        
        # Sort patterns by end index (most recent first)
        patterns.sort(key=lambda x: x['end_index'], reverse=True)
        
        # Return only the most recent patterns
        return patterns[:3]
    
    def _check_bullish_jhook(self, df: pd.DataFrame, end_index: int) -> Optional[Dict]:
        """
        Check for a bullish JHook pattern (reversal from downtrend)
        
        Args:
            df: Processed DataFrame
            end_index: End index of potential pattern
            
        Returns:
            Pattern dictionary if valid, None otherwise
        """
        # Look back from end_index to find a suitable trend start
        max_lookback = min(end_index, self.lookback_periods)
        
        # Find significant swing lows
        swing_lows = []
        for i in range(end_index - max_lookback, end_index + 1):
            if df.iloc[i]['swing_low']:
                swing_lows.append((i, df.iloc[i]['low']))
        
        if len(swing_lows) < 3:
            return None
            
        # Need at least 3 points for a JHook: trend start, reversal point, continuation
        # For bullish JHook: A (low), B (lower low), C (higher low)
        
        # Try to identify the pattern within the swing lows
        for idx in range(len(swing_lows) - 2):
            a_idx, a_price = swing_lows[idx]
            b_idx, b_price = swing_lows[idx + 1]
            c_idx, c_price = swing_lows[idx + 2]
            
            # Check if a valid JHook pattern:
            # 1. Point B should be lower than A (downtrend)
            # 2. Point C should be higher than B (reversal) but lower than A (continuation of original trend)
            # 3. RSI at point B should preferably be oversold (confirmation of exhaustion)
            if b_price < a_price and c_price > b_price and c_price < a_price:
                # Calculate percentage moves
                down_move = (a_price - b_price) / a_price * 100
                reversal_move = (c_price - b_price) / b_price * 100
                
                # Check if the moves are significant enough
                if down_move > 0.5 and reversal_move > 0.3:
                    # Check for RSI confirmation
                    rsi_confirmed = df.iloc[b_idx]['rsi'] < 40  # Preferably oversold or near it
                    
                    # Create pattern
                    pattern = {
                        'type': 'bullish_jhook',
                        'start_index': a_idx,
                        'reversal_index': b_idx,
                        'end_index': c_idx,
                        'start_price': a_price,
                        'reversal_price': b_price,
                        'end_price': c_price,
                        'down_move_percent': down_move,
                        'reversal_percent': reversal_move,
                        'rsi_confirmed': rsi_confirmed,
                        'strength': min(1.0, (down_move * 0.1 + reversal_move * 0.2) / 10),
                        'timestamp': df.index[c_idx] if isinstance(df.index, pd.DatetimeIndex) else c_idx
                    }
                    
                    return pattern
        
        return None
    
    def _check_bearish_jhook(self, df: pd.DataFrame, end_index: int) -> Optional[Dict]:
        """
        Check for a bearish JHook pattern (reversal from uptrend)
        
        Args:
            df: Processed DataFrame
            end_index: End index of potential pattern
            
        Returns:
            Pattern dictionary if valid, None otherwise
        """
        # Look back from end_index to find a suitable trend start
        max_lookback = min(end_index, self.lookback_periods)
        
        # Find significant swing highs
        swing_highs = []
        for i in range(end_index - max_lookback, end_index + 1):
            if df.iloc[i]['swing_high']:
                swing_highs.append((i, df.iloc[i]['high']))
        
        if len(swing_highs) < 3:
            return None
            
        # Need at least 3 points for a JHook: trend start, reversal point, continuation
        # For bearish JHook: A (high), B (higher high), C (lower high)
        
        # Try to identify the pattern within the swing highs
        for idx in range(len(swing_highs) - 2):
            a_idx, a_price = swing_highs[idx]
            b_idx, b_price = swing_highs[idx + 1]
            c_idx, c_price = swing_highs[idx + 2]
            
            # Check if a valid JHook pattern:
            # 1. Point B should be higher than A (uptrend)
            # 2. Point C should be lower than B (reversal) but higher than A (continuation of original trend)
            # 3. RSI at point B should preferably be overbought (confirmation of exhaustion)
            if b_price > a_price and c_price < b_price and c_price > a_price:
                # Calculate percentage moves
                up_move = (b_price - a_price) / a_price * 100
                reversal_move = (b_price - c_price) / b_price * 100
                
                # Check if the moves are significant enough
                if up_move > 0.5 and reversal_move > 0.3:
                    # Check for RSI confirmation
                    rsi_confirmed = df.iloc[b_idx]['rsi'] > 60  # Preferably overbought or near it
                    
                    # Create pattern
                    pattern = {
                        'type': 'bearish_jhook',
                        'start_index': a_idx,
                        'reversal_index': b_idx,
                        'end_index': c_idx,
                        'start_price': a_price,
                        'reversal_price': b_price,
                        'end_price': c_price,
                        'up_move_percent': up_move,
                        'reversal_percent': reversal_move,
                        'rsi_confirmed': rsi_confirmed,
                        'strength': min(1.0, (up_move * 0.1 + reversal_move * 0.2) / 10),
                        'timestamp': df.index[c_idx] if isinstance(df.index, pd.DatetimeIndex) else c_idx
                    }
                    
                    return pattern
        
        return None
    
    def _is_pattern_valid(self, pattern: Dict, df: pd.DataFrame) -> bool:
        """
        Check if a JHook pattern is still valid for trading
        
        Args:
            pattern: Pattern dictionary
            df: Processed DataFrame
            
        Returns:
            True if pattern is valid for trading, False otherwise
        """
        # Pattern should be recent
        max_age = 5  # Maximum number of candles since pattern formed
        
        pattern_end_idx = pattern['end_index']
        current_idx = len(df) - 1
        
        # Check if pattern is recent enough
        if current_idx - pattern_end_idx > max_age:
            return False
            
        # Check that price hasn't moved too far from pattern end
        pattern_end_price = pattern['end_price']
        current_price = df.iloc[-1]['close']
        
        # For bullish pattern, price shouldn't have moved up too much already
        if pattern['type'] == 'bullish_jhook':
            if current_price > pattern_end_price * 1.005:  # More than 0.5% move already
                return False
                
            # Price should be above the pattern end (low)
            if current_price < pattern_end_price:
                return False
                
            # Check for MACD confirmation (bullish crossover or positive histogram)
            if not df.iloc[-1]['macd_above_signal'] and df.iloc[-1]['macd_histogram'] <= 0:
                return False
        
        # For bearish pattern, price shouldn't have moved down too much already
        elif pattern['type'] == 'bearish_jhook':
            if current_price < pattern_end_price * 0.995:  # More than 0.5% move already
                return False
                
            # Price should be below the pattern end (high)
            if current_price > pattern_end_price:
                return False
                
            # Check for MACD confirmation (bearish crossover or negative histogram)
            if df.iloc[-1]['macd_above_signal'] and df.iloc[-1]['macd_histogram'] >= 0:
                return False
        
        return True
    
    def _create_signal_from_pattern(self, symbol: str, pattern: Dict, df: pd.DataFrame) -> Dict:
        """
        Create a trading signal from a valid JHook pattern
        
        Args:
            symbol: Trading symbol
            pattern: Pattern dictionary
            df: Processed DataFrame
            
        Returns:
            Signal dictionary
        """
        current_price = df.iloc[-1]['close']
        action = "NONE"
        signal_reasons = []
        signal_strength = pattern.get('strength', 0.7)
        
        # For bullish JHook, we want to BUY
        if pattern['type'] == 'bullish_jhook':
            action = "BUY"
            signal_reasons.append(f"Bullish JHook pattern detected")
            signal_reasons.append(f"Downtrend of {pattern['down_move_percent']:.2f}% followed by {pattern['reversal_percent']:.2f}% reversal")
            
            if pattern['rsi_confirmed']:
                signal_reasons.append("RSI confirms reversal from oversold conditions")
                signal_strength += 0.1
                
            if df.iloc[-1]['macd_above_signal']:
                signal_reasons.append("MACD confirms bullish momentum")
                signal_strength += 0.1
                
            if df.iloc[-1]['price_above_ema50']:
                signal_reasons.append("Price above 50 EMA indicates bullish bias")
                signal_strength += 0.05
        
        # For bearish JHook, we want to SELL
        elif pattern['type'] == 'bearish_jhook':
            action = "SELL"
            signal_reasons.append(f"Bearish JHook pattern detected")
            signal_reasons.append(f"Uptrend of {pattern['up_move_percent']:.2f}% followed by {pattern['reversal_percent']:.2f}% reversal")
            
            if pattern['rsi_confirmed']:
                signal_reasons.append("RSI confirms reversal from overbought conditions")
                signal_strength += 0.1
                
            if not df.iloc[-1]['macd_above_signal']:
                signal_reasons.append("MACD confirms bearish momentum")
                signal_strength += 0.1
                
            if not df.iloc[-1]['price_above_ema50']:
                signal_reasons.append("Price below 50 EMA indicates bearish bias")
                signal_strength += 0.05
        
        # No valid signal
        if action == "NONE" or not signal_reasons:
            return {'action': 'NONE', 'symbol': symbol}
        
        # Prevent trading too frequently
        min_time_between_signals = timedelta(hours=8)  # JHook is often a longer term pattern
        if symbol in self.last_signal_time:
            time_since_last = datetime.now() - self.last_signal_time[symbol]
            if time_since_last < min_time_between_signals:
                return {'action': 'NONE', 'symbol': symbol, 'reason': 'Too soon after previous signal'}
        
        # Calculate stop loss and take profit levels
        atr = df.iloc[-1]['atr'] if not pd.isna(df.iloc[-1]['atr']) else current_price * 0.001
        
        # For JHook patterns, stop loss is typically placed beyond the reversal point
        if action == "BUY":
            # Place stop below the reversal point (pattern low)
            stop_distance = current_price - pattern['reversal_price']
            
            # If the stop is too small, use ATR-based stop
            if stop_distance < atr:
                stop_loss = current_price - (atr * 1.5)
            else:
                # Add a buffer below the reversal point
                stop_loss = pattern['reversal_price'] - (atr * 0.5)
                
            # Take profit based on risk-reward ratio
            risk = current_price - stop_loss
            take_profit = current_price + (risk * 2)  # 1:2 risk-reward
            
        else:  # SELL
            # Place stop above the reversal point (pattern high)
            stop_distance = pattern['reversal_price'] - current_price
            
            # If the stop is too small, use ATR-based stop
            if stop_distance < atr:
                stop_loss = current_price + (atr * 1.5)
            else:
                # Add a buffer above the reversal point
                stop_loss = pattern['reversal_price'] + (atr * 0.5)
                
            # Take profit based on risk-reward ratio
            risk = stop_loss - current_price
            take_profit = current_price - (risk * 2)  # 1:2 risk-reward
        
        # Create signal dictionary
        signal = {
            'symbol': symbol,
            'action': action,
            'direction': action,  # For compatibility
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': datetime.now().isoformat(),
            'reasons': signal_reasons,
            'strength': min(1.0, signal_strength),
            'strategy': 'JHOOK_PATTERN',
            'timeframe': self.timeframe,
            'pattern_type': pattern['type'],
            'pattern_start_idx': pattern['start_index'],
            'pattern_reversal_idx': pattern['reversal_index'],
            'pattern_end_idx': pattern['end_index']
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
        
        # Use the latest signal for this symbol
        if symbol in self.signals and self.signals[symbol]:
            latest_signal = self.signals[symbol][-1]
            
            current_price = data['close'].iloc[-1]
            stop_loss = latest_signal.get('stop_loss')
            
            if not stop_loss:
                logger.warning(f"No stop loss found for {symbol}, using default position size")
                return 0.01
                
            # Calculate stop loss distance
            stop_loss_distance = abs(current_price - stop_loss)
            
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
            
            # Apply position size limits
            min_lot = 0.01  # Micro lot
            max_lot = 0.5   # Maximum 0.5 lot per trade
            
            position_size_lots = max(min_lot, min(position_size_lots, max_lot))
            
            return round(position_size_lots, 2)
        else:
            # No signal history, use a conservative default
            return 0.01
    
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
        
        # JHook patterns work well at market turning points, so may be counter-trend
        # That's actually the point of these patterns, so we don't reject based on trend
        
        # Avoid low liquidity conditions
        if liquidity == 'low':
            logger.info(f"JHook signal rejected: {symbol} has low liquidity")
            return False
            
        # JHook needs some volatility to work well for the reversal to be meaningful
        if volatility == 'low' and signal.get('strength', 0) < 0.8:
            logger.info(f"JHook signal caution: {symbol} has low volatility")
            # Don't reject but flag as potentially less reliable
            
        return True
