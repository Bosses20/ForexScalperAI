"""
MT5 Strategies module
Implements various scalping strategies for MetaTrader 5
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
from loguru import logger
from datetime import datetime
import time

# Technical analysis library
import ta
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.others import DailyReturnIndicator, CumulativeReturnIndicator

# Import our newly implemented strategy classes
from src.strategies.ma_rsi_strategy import MaRsiStrategy
from src.strategies.stochastic_cross_strategy import StochasticCrossStrategy
from src.strategies.break_and_retest_strategy import BreakAndRetestStrategy
from src.strategies.jhook_pattern_strategy import JHookPatternStrategy

class ScalpingStrategy:
    """Base class for all scalping strategies"""
    
    def __init__(self, config: dict):
        """
        Initialize the scalping strategy with configuration
        
        Args:
            config: Strategy configuration parameters
        """
        self.config = config
        self.name = config.get('name', self.__class__.__name__)
        self.timeframe = config.get('timeframe', 'M1')
        self.symbols = config.get('symbols', [])
        self.risk_per_trade = config.get('risk_per_trade', 0.01)  # 1% risk per trade
        self.take_profit_pips = config.get('take_profit_pips', 10)
        self.stop_loss_pips = config.get('stop_loss_pips', 5)
        self.max_spread_pips = config.get('max_spread_pips', 2)
        self.min_volume = config.get('min_volume', 0.01)
        self.max_volume = config.get('max_volume', 1.0)
        self.trade_session_hours = config.get('trade_session_hours', None)
        self.warmup_bars = config.get('warmup_bars', 100)
        
        # Strategy state
        self.is_initialized = False
        self.signals = {}
        self.last_signal_time = {}
        
        # Performance metrics
        self.performance = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'profit_factor': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'max_drawdown': 0,
            'expectancy': 0
        }
        
        logger.info(f"Initialized strategy: {self.name}")
    
    def initialize(self) -> bool:
        """
        Initialize strategy with any required setup
        
        Returns:
            True if initialized successfully
        """
        self.is_initialized = True
        return True
    
    def analyze(self, symbol: str, data: pd.DataFrame) -> Dict:
        """
        Analyze market data and generate trading signals
        
        Args:
            symbol: Trading symbol
            data: OHLCV data as pandas DataFrame
            
        Returns:
            Dict with signal information
        """
        # Base implementation that should be overridden by subclasses
        logger.warning(f"Base analyze method called for {symbol} in {self.name}")
        return {
            'symbol': symbol,
            'signal': 'none',
            'signal_strength': 0,
            'entry_price': 0,
            'stop_loss': 0,
            'take_profit': 0,
            'timestamp': datetime.now().isoformat()
        }
    
    def should_trade(self, symbol: str, data: pd.DataFrame) -> bool:
        """
        Determine if we should trade based on current conditions
        
        Args:
            symbol: Trading symbol
            data: OHLCV data as pandas DataFrame
            
        Returns:
            True if trading conditions are met
        """
        # Check if we have enough data
        if len(data) < self.warmup_bars:
            logger.debug(f"Not enough data for {symbol}, need {self.warmup_bars} bars")
            return False
        
        # Check if we're in the allowed trading hours
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
                logger.debug(f"Outside trading hours for {symbol}, current hour: {current_hour}")
                return False
        
        # Check spread
        if 'spread' in data.columns and len(data) > 0:
            current_spread = data['spread'].iloc[-1]
            max_spread = self.max_spread_pips * 0.0001  # Convert pips to price
            
            if current_spread > max_spread:
                logger.debug(f"Spread too high for {symbol}: {current_spread} > {max_spread}")
                return False
        
        return True
    
    def calculate_position_size(self, symbol: str, account_info: Dict, 
                              entry_price: float, stop_loss_price: float) -> float:
        """
        Calculate appropriate position size based on risk parameters
        
        Args:
            symbol: Trading symbol
            account_info: Account information
            entry_price: Entry price
            stop_loss_price: Stop loss price
            
        Returns:
            Position size in lots
        """
        # Get account balance
        balance = account_info.get('balance', 0)
        
        # Calculate risk amount based on risk percentage
        risk_amount = balance * self.risk_per_trade
        
        # Calculate pip value for this symbol (assuming standard 10,000 units per lot)
        # For USD-based accounts and major pairs
        point_value = 0.0001  # Standard point value for 4-digit brokers
        contract_size = 100000  # Standard lot = 100,000 units
        
        # Adjust for JPY pairs
        if symbol.endswith('JPY'):
            point_value = 0.01
        
        # Calculate pip value (for 1 lot)
        pip_value = point_value * 10 * contract_size  # 1 pip = 10 points
        
        # Calculate stop loss in pips
        stop_loss_pips = abs(entry_price - stop_loss_price) / point_value
        
        # Calculate position size
        if stop_loss_pips > 0 and pip_value > 0:
            position_size = risk_amount / (stop_loss_pips * pip_value)
        else:
            logger.warning(f"Invalid stop loss or pip value for {symbol}")
            position_size = self.min_volume
        
        # Ensure within limits
        position_size = max(min(position_size, self.max_volume), self.min_volume)
        
        # Round to broker's lot step
        lot_step = 0.01  # Standard lot step
        position_size = round(position_size / lot_step) * lot_step
        
        logger.debug(f"Calculated position size for {symbol}: {position_size} lots")
        return position_size
    
    def update_performance(self, trade_result: Dict) -> None:
        """
        Update strategy performance metrics
        
        Args:
            trade_result: Dictionary with trade result information
        """
        # Update total trades
        self.performance['total_trades'] += 1
        
        # Update wins/losses
        profit = trade_result.get('profit', 0)
        
        if profit > 0:
            self.performance['winning_trades'] += 1
            self.performance['avg_win'] = (
                (self.performance['avg_win'] * (self.performance['winning_trades'] - 1) + profit)
                / self.performance['winning_trades']
            )
        elif profit < 0:
            self.performance['losing_trades'] += 1
            self.performance['avg_loss'] = (
                (self.performance['avg_loss'] * (self.performance['losing_trades'] - 1) + profit)
                / self.performance['losing_trades']
            )
        
        # Calculate win rate
        if self.performance['total_trades'] > 0:
            self.performance['win_rate'] = self.performance['winning_trades'] / self.performance['total_trades']
        
        # Calculate profit factor
        total_losses = self.performance['losing_trades'] * abs(self.performance['avg_loss'])
        total_wins = self.performance['winning_trades'] * self.performance['avg_win']
        
        if total_losses > 0:
            self.performance['profit_factor'] = total_wins / total_losses
        
        # Calculate expectancy
        if self.performance['total_trades'] > 0:
            win_rate = self.performance['win_rate']
            reward_risk_ratio = (
                abs(self.performance['avg_win'] / self.performance['avg_loss'])
                if self.performance['avg_loss'] != 0 else 0
            )
            self.performance['expectancy'] = (win_rate * reward_risk_ratio) - (1 - win_rate)


class MovingAverageCross(ScalpingStrategy):
    """Moving Average Crossover Scalping Strategy"""
    
    def __init__(self, config: dict):
        """
        Initialize the Moving Average Crossover strategy
        
        Args:
            config: Strategy configuration
        """
        super().__init__(config)
        
        # Strategy-specific parameters
        self.fast_ma_period = config.get('fast_ma_period', 5)
        self.slow_ma_period = config.get('slow_ma_period', 20)
        self.ma_type = config.get('ma_type', 'ema').lower()  # 'sma' or 'ema'
        self.signal_threshold = config.get('signal_threshold', 0.0001)
        self.use_confirmation = config.get('use_confirmation', True)
        
        # Initialization requires more data for the slow MA
        self.warmup_bars = max(self.slow_ma_period * 3, self.warmup_bars)
    
    def analyze(self, symbol: str, data: pd.DataFrame) -> Dict:
        """
        Analyze market data with Moving Average Crossover strategy
        
        Args:
            symbol: Trading symbol
            data: OHLCV data as pandas DataFrame
            
        Returns:
            Dict with signal information
        """
        # Ensure we have enough data
        if len(data) < self.warmup_bars:
            return {
                'symbol': symbol,
                'signal': 'none',
                'signal_strength': 0,
                'entry_price': 0,
                'stop_loss': 0,
                'take_profit': 0,
                'timestamp': datetime.now().isoformat()
            }
        
        # Calculate moving averages
        if self.ma_type == 'sma':
            fast_ma = SMAIndicator(close=data['close'], window=self.fast_ma_period).sma_indicator()
            slow_ma = SMAIndicator(close=data['close'], window=self.slow_ma_period).sma_indicator()
        else:  # EMA default
            fast_ma = EMAIndicator(close=data['close'], window=self.fast_ma_period).ema_indicator()
            slow_ma = EMAIndicator(close=data['close'], window=self.slow_ma_period).ema_indicator()
        
        # Calculate crossovers
        data['fast_ma'] = fast_ma
        data['slow_ma'] = slow_ma
        data['ma_diff'] = data['fast_ma'] - data['slow_ma']
        
        # Check for crossover signals
        signal = 'none'
        signal_strength = 0
        entry_price = data['close'].iloc[-1]
        current_ma_diff = data['ma_diff'].iloc[-1]
        prev_ma_diff = data['ma_diff'].iloc[-2] if len(data) > 2 else 0
        
        # Determine signal direction
        if prev_ma_diff < 0 and current_ma_diff > 0:
            # Bullish crossover (fast MA crosses above slow MA)
            signal = 'buy'
            signal_strength = abs(current_ma_diff) / entry_price
        elif prev_ma_diff > 0 and current_ma_diff < 0:
            # Bearish crossover (fast MA crosses below slow MA)
            signal = 'sell'
            signal_strength = abs(current_ma_diff) / entry_price
        
        # Price confirmation - only trade if price is on the correct side of both MAs
        if self.use_confirmation:
            if signal == 'buy' and entry_price < data['fast_ma'].iloc[-1]:
                signal = 'none'  # Invalidate buy signal if price below fast MA
            elif signal == 'sell' and entry_price > data['fast_ma'].iloc[-1]:
                signal = 'none'  # Invalidate sell signal if price above fast MA
        
        # Check signal threshold
        if signal_strength < self.signal_threshold:
            signal = 'none'
        
        # Calculate stop loss and take profit levels
        point = 0.0001  # Standard point value for 4-digit brokers
        if symbol.endswith('JPY'):
            point = 0.01
        
        stop_loss = 0
        take_profit = 0
        
        if signal == 'buy':
            stop_loss = entry_price - (self.stop_loss_pips * point)
            take_profit = entry_price + (self.take_profit_pips * point)
        elif signal == 'sell':
            stop_loss = entry_price + (self.stop_loss_pips * point)
            take_profit = entry_price - (self.take_profit_pips * point)
        
        # Record signal time
        if signal != 'none':
            self.last_signal_time[symbol] = datetime.now()
        
        # Construct signal result
        signal_result = {
            'symbol': symbol,
            'signal': signal,
            'signal_strength': signal_strength,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'fast_ma': data['fast_ma'].iloc[-1],
            'slow_ma': data['slow_ma'].iloc[-1],
            'ma_diff': current_ma_diff,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store signal
        self.signals[symbol] = signal_result
        
        return signal_result


class BollingerBreakout(ScalpingStrategy):
    """Bollinger Bands Breakout Scalping Strategy"""
    
    def __init__(self, config: dict):
        """
        Initialize the Bollinger Bands Breakout strategy
        
        Args:
            config: Strategy configuration
        """
        super().__init__(config)
        
        # Strategy-specific parameters
        self.bb_period = config.get('bb_period', 20)
        self.bb_std = config.get('bb_std', 2.0)
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.use_rsi_filter = config.get('use_rsi_filter', True)
        self.entry_atr_multiplier = config.get('entry_atr_multiplier', 0.5)
        self.atr_period = config.get('atr_period', 14)
        
        # Initialization requires more data
        self.warmup_bars = max(self.bb_period * 3, self.warmup_bars)
    
    def analyze(self, symbol: str, data: pd.DataFrame) -> Dict:
        """
        Analyze market data with Bollinger Bands Breakout strategy
        
        Args:
            symbol: Trading symbol
            data: OHLCV data as pandas DataFrame
            
        Returns:
            Dict with signal information
        """
        # Ensure we have enough data
        if len(data) < self.warmup_bars:
            return {
                'symbol': symbol,
                'signal': 'none',
                'signal_strength': 0,
                'entry_price': 0,
                'stop_loss': 0,
                'take_profit': 0,
                'timestamp': datetime.now().isoformat()
            }
        
        # Calculate Bollinger Bands
        bb = BollingerBands(close=data['close'], window=self.bb_period, window_dev=self.bb_std)
        data['bb_upper'] = bb.bollinger_hband()
        data['bb_middle'] = bb.bollinger_mavg()
        data['bb_lower'] = bb.bollinger_lband()
        
        # Calculate RSI if using RSI filter
        if self.use_rsi_filter:
            rsi = RSIIndicator(close=data['close'], window=self.rsi_period)
            data['rsi'] = rsi.rsi()
        
        # Calculate ATR for stop loss
        atr = AverageTrueRange(high=data['high'], low=data['low'], close=data['close'], window=self.atr_period)
        data['atr'] = atr.average_true_range()
        
        # Get current values
        current_close = data['close'].iloc[-1]
        current_bb_upper = data['bb_upper'].iloc[-1]
        current_bb_lower = data['bb_lower'].iloc[-1]
        current_bb_middle = data['bb_middle'].iloc[-1]
        
        prev_close = data['close'].iloc[-2]
        prev_bb_upper = data['bb_upper'].iloc[-2]
        prev_bb_lower = data['bb_lower'].iloc[-2]
        
        current_atr = data['atr'].iloc[-1]
        
        # Initialize signal
        signal = 'none'
        signal_strength = 0
        entry_price = current_close
        
        # Check for breakout patterns
        breakout_up = prev_close <= prev_bb_upper and current_close > current_bb_upper
        breakout_down = prev_close >= prev_bb_lower and current_close < current_bb_lower
        
        # Apply RSI filter if enabled
        if self.use_rsi_filter:
            current_rsi = data['rsi'].iloc[-1]
            
            if breakout_up and current_rsi < self.rsi_overbought:
                signal = 'buy'
                signal_strength = (current_close - current_bb_middle) / current_atr
            elif breakout_down and current_rsi > self.rsi_oversold:
                signal = 'sell'
                signal_strength = (current_bb_middle - current_close) / current_atr
        else:
            # No RSI filter
            if breakout_up:
                signal = 'buy'
                signal_strength = (current_close - current_bb_middle) / current_atr
            elif breakout_down:
                signal = 'sell'
                signal_strength = (current_bb_middle - current_close) / current_atr
        
        # Calculate stop loss and take profit levels
        point = 0.0001  # Standard point value for 4-digit brokers
        if symbol.endswith('JPY'):
            point = 0.01
        
        stop_loss = 0
        take_profit = 0
        
        if signal == 'buy':
            # ATR-based stop loss below entry
            stop_loss = entry_price - (current_atr * self.entry_atr_multiplier)
            take_profit = entry_price + (self.take_profit_pips * point)
        elif signal == 'sell':
            # ATR-based stop loss above entry
            stop_loss = entry_price + (current_atr * self.entry_atr_multiplier)
            take_profit = entry_price - (self.take_profit_pips * point)
        
        # Record signal time
        if signal != 'none':
            self.last_signal_time[symbol] = datetime.now()
        
        # Construct signal result
        signal_result = {
            'symbol': symbol,
            'signal': signal,
            'signal_strength': signal_strength,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'bb_upper': current_bb_upper,
            'bb_middle': current_bb_middle,
            'bb_lower': current_bb_lower,
            'atr': current_atr,
            'rsi': data['rsi'].iloc[-1] if self.use_rsi_filter else None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store signal
        self.signals[symbol] = signal_result
        
        return signal_result


class BreakAndRetest(ScalpingStrategy):
    """Break and Retest Strategy for MT5
    
    This strategy identifies key support and resistance levels,
    detects valid breakouts with volume confirmation, and enters
    trades when price returns to retest the broken level.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the Break and Retest strategy
        
        Args:
            config: Strategy configuration
        """
        super().__init__(config)
        
        # Strategy-specific parameters
        self.sr_lookback_periods = config.get('sr_lookback_periods', 50)
        self.sr_touchpoints = config.get('sr_touchpoints', 2)  # Minimum touches to confirm S/R
        self.zone_size_pips = config.get('zone_size_pips', 5)  # Size of S/R zones in pips
        self.min_breakout_pips = config.get('min_breakout_pips', 10)  # Min pips for valid breakout
        self.retest_max_pips = config.get('retest_max_pips', 5)  # Max pips from level for valid retest
        self.confirmation_candles = config.get('confirmation_candles', 2)  # Candles to confirm breakout
        self.volume_confirmation = config.get('volume_confirmation', True)  # Use volume for confirmation
        self.min_volume_increase = config.get('min_volume_increase', 1.5)  # Min volume multiplier for breakout
        self.atr_period = config.get('atr_period', 14)  # ATR period for volatility filtering
        self.atr_multiplier = config.get('atr_multiplier', 0.5)  # ATR multiplier for stop loss
        self.risk_reward_ratio = config.get('risk_reward_ratio', 2.0)  # Risk-reward ratio for take profit
        
        # Initialization requires more data for S/R identification
        self.warmup_bars = max(self.sr_lookback_periods + 20, self.warmup_bars)
        
        # Store identified levels
        self.support_levels = {}
        self.resistance_levels = {}
        self.breakouts = {}
        self.retests = {}
        
        logger.info(f"Break and Retest strategy initialized with lookback: {self.sr_lookback_periods}")
    
    def analyze(self, symbol: str, data: pd.DataFrame) -> Dict:
        """
        Analyze market data with Break and Retest strategy
        
        Args:
            symbol: Trading symbol
            data: OHLCV data as pandas DataFrame
            
        Returns:
            Dict with signal information
        """
        # Ensure we have enough data
        if len(data) < self.warmup_bars:
            return {
                'symbol': symbol,
                'signal': 'none',
                'signal_strength': 0,
                'entry_price': 0,
                'stop_loss': 0,
                'take_profit': 0,
                'timestamp': datetime.now().isoformat()
            }
        
        # Identify support and resistance levels
        self._identify_sr_levels(symbol, data)
        
        # Detect breakouts
        self._detect_breakouts(symbol, data)
        
        # Check for retests
        retest_signal = self._detect_retests(symbol, data)
        
        # If we have a valid retest signal, prepare trade parameters
        if retest_signal and retest_signal['signal'] != 'none':
            return retest_signal
        
        # No signal found
        return {
            'symbol': symbol,
            'signal': 'none',
            'signal_strength': 0,
            'entry_price': 0,
            'stop_loss': 0,
            'take_profit': 0,
            'timestamp': datetime.now().isoformat()
        }
    
    def _identify_sr_levels(self, symbol: str, data: pd.DataFrame) -> None:
        """
        Identify support and resistance levels
        
        Args:
            symbol: Trading symbol
            data: OHLCV data as pandas DataFrame
        """
        # Use only a portion of the data for S/R calculation
        df = data.iloc[-self.sr_lookback_periods:].copy()
        
        # Calculate swings (pivot points)
        highs = []
        lows = []
        
        # Find pivot highs
        for i in range(2, len(df)-2):
            if (df['high'].iloc[i] > df['high'].iloc[i-1] and 
                df['high'].iloc[i] > df['high'].iloc[i-2] and
                df['high'].iloc[i] > df['high'].iloc[i+1] and
                df['high'].iloc[i] > df['high'].iloc[i+2]):
                highs.append((i, df['high'].iloc[i]))
        
        # Find pivot lows
        for i in range(2, len(df)-2):
            if (df['low'].iloc[i] < df['low'].iloc[i-1] and 
                df['low'].iloc[i] < df['low'].iloc[i-2] and
                df['low'].iloc[i] < df['low'].iloc[i+1] and
                df['low'].iloc[i] < df['low'].iloc[i+2]):
                lows.append((i, df['low'].iloc[i]))
        
        # Group nearby levels to create zones
        support_zones = self._group_levels(lows, 'support')
        resistance_zones = self._group_levels(highs, 'resistance')
        
        # Store significant levels (those with enough touchpoints)
        self.support_levels[symbol] = [level for level in support_zones 
                                     if level['touchpoints'] >= self.sr_touchpoints]
        self.resistance_levels[symbol] = [level for level in resistance_zones 
                                        if level['touchpoints'] >= self.sr_touchpoints]
        
        logger.debug(f"Identified {len(self.support_levels[symbol])} support and "
                   f"{len(self.resistance_levels[symbol])} resistance zones for {symbol}")
    
    def _group_levels(self, pivot_points: List[Tuple[int, float]], level_type: str) -> List[Dict]:
        """
        Group nearby pivot points into zones
        
        Args:
            pivot_points: List of pivot points (index, price)
            level_type: Type of level ('support' or 'resistance')
            
        Returns:
            List of level dictionaries
        """
        if not pivot_points:
            return []
        
        # Sort pivot points by price
        pivot_points.sort(key=lambda x: x[1])
        
        # Calculate pip value (approximate)
        pip_value = 0.0001  # For most forex pairs
        if pivot_points[0][1] > 100:
            pip_value = 0.01  # For JPY pairs
        
        zone_size = self.zone_size_pips * pip_value
        
        # Group nearby levels
        zones = []
        current_zone = {
            'pivot_points': [pivot_points[0]],
            'price': pivot_points[0][1],
            'touchpoints': 1,
            'type': level_type
        }
        
        for i in range(1, len(pivot_points)):
            idx, price = pivot_points[i]
            
            # If the price is within the zone, add to current zone
            if abs(price - current_zone['price']) <= zone_size:
                current_zone['pivot_points'].append((idx, price))
                current_zone['touchpoints'] += 1
                # Update zone price to the average
                current_zone['price'] = sum(p[1] for p in current_zone['pivot_points']) / len(current_zone['pivot_points'])
            else:
                # Add completed zone to zones list
                zones.append(current_zone)
                # Start a new zone
                current_zone = {
                    'pivot_points': [(idx, price)],
                    'price': price,
                    'touchpoints': 1,
                    'type': level_type
                }
        
        # Add the last zone
        zones.append(current_zone)
        
        return zones
    
    def _detect_breakouts(self, symbol: str, data: pd.DataFrame) -> None:
        """
        Detect breakouts of support and resistance levels
        
        Args:
            symbol: Trading symbol
            data: OHLCV data as pandas DataFrame
        """
        if symbol not in self.support_levels or symbol not in self.resistance_levels:
            return
        
        # Calculate pip value (approximate)
        pip_value = 0.0001  # For most pairs
        if data['close'].iloc[-1] > 100:
            pip_value = 0.01  # For JPY pairs
        
        min_breakout_distance = self.min_breakout_pips * pip_value
        
        # Calculate ATR for volatility filtering
        atr = AverageTrueRange(high=data['high'], low=data['low'], close=data['close'], 
                              window=self.atr_period).average_true_range()
        current_atr = atr.iloc[-1]
        
        # Calculate average volume
        avg_volume = data['volume'].iloc[-10:].mean()
        
        # Initialize breakouts dict if not exists
        if symbol not in self.breakouts:
            self.breakouts[symbol] = []
        
        # Check for resistance breakouts (bullish)
        for level in self.resistance_levels[symbol]:
            # Get the last close and previous close
            last_close = data['close'].iloc[-1]
            last_high = data['high'].iloc[-1]
            
            # Check if we've broken above resistance
            if (last_close > level['price'] and 
                # Ensure we've broken above the zone
                last_close - level['price'] > min_breakout_distance):
                
                # Check for volume confirmation if enabled
                volume_confirmed = True
                if self.volume_confirmation:
                    last_volume = data['volume'].iloc[-1]
                    volume_confirmed = last_volume > avg_volume * self.min_volume_increase
                
                # Add to breakouts if not already tracked
                if not any(b['level'] == level['price'] and b['type'] == 'bullish' 
                          for b in self.breakouts[symbol]):
                    
                    # Record the breakout
                    self.breakouts[symbol].append({
                        'level': level['price'],
                        'type': 'bullish',
                        'price': last_close,
                        'time': data.index[-1],
                        'volume_confirmed': volume_confirmed,
                        'atr': current_atr,
                        'retested': False
                    })
                    
                    logger.info(f"Detected bullish breakout for {symbol} at {level['price']}")
        
        # Check for support breakouts (bearish)
        for level in self.support_levels[symbol]:
            # Get the last close and previous close
            last_close = data['close'].iloc[-1]
            last_low = data['low'].iloc[-1]
            
            # Check if we've broken below support
            if (last_close < level['price'] and 
                # Ensure we've broken below the zone
                level['price'] - last_close > min_breakout_distance):
                
                # Check for volume confirmation if enabled
                volume_confirmed = True
                if self.volume_confirmation:
                    last_volume = data['volume'].iloc[-1]
                    volume_confirmed = last_volume > avg_volume * self.min_volume_increase
                
                # Add to breakouts if not already tracked
                if not any(b['level'] == level['price'] and b['type'] == 'bearish' 
                          for b in self.breakouts[symbol]):
                    
                    # Record the breakout
                    self.breakouts[symbol].append({
                        'level': level['price'],
                        'type': 'bearish',
                        'price': last_close,
                        'time': data.index[-1],
                        'volume_confirmed': volume_confirmed,
                        'atr': current_atr,
                        'retested': False
                    })
                    
                    logger.info(f"Detected bearish breakout for {symbol} at {level['price']}")
    
    def _detect_retests(self, symbol: str, data: pd.DataFrame) -> Optional[Dict]:
        """
        Detect retests of broken levels
        
        Args:
            symbol: Trading symbol
            data: OHLCV data as pandas DataFrame
            
        Returns:
            Signal dictionary if retest found, None otherwise
        """
        if symbol not in self.breakouts or not self.breakouts[symbol]:
            return None
        
        # Calculate pip value (approximate)
        pip_value = 0.0001  # For most pairs
        if data['close'].iloc[-1] > 100:
            pip_value = 0.01  # For JPY pairs
        
        retest_max_distance = self.retest_max_pips * pip_value
        
        # Calculate ATR for stop loss and take profit
        atr = AverageTrueRange(high=data['high'], low=data['low'], close=data['close'], 
                              window=self.atr_period).average_true_range()
        current_atr = atr.iloc[-1]
        
        # Get current price
        current_price = data['close'].iloc[-1]
        current_time = data.index[-1] if isinstance(data.index, pd.DatetimeIndex) else datetime.now()
        
        # Check for pending retests
        for breakout in self.breakouts[symbol]:
            # Skip if already retested or not volume confirmed
            if breakout['retested'] or (self.volume_confirmation and not breakout['volume_confirmed']):
                continue
            
            # Check if we're back near the breakout level
            if breakout['type'] == 'bullish':
                # For bullish breakouts, price should come back down to the resistance level (now support)
                if (abs(current_price - breakout['level']) < retest_max_distance and 
                    current_price > breakout['level']):
                    
                    # Found a bullish retest
                    stop_loss = current_price - current_atr * self.atr_multiplier
                    take_profit = current_price + ((current_price - stop_loss) * self.risk_reward_ratio)
                    
                    # Mark as retested
                    breakout['retested'] = True
                    
                    logger.info(f"Detected bullish retest for {symbol} at {breakout['level']}")
                    
                    # Return the signal if volume filter passed or not required
                    if not self.volume_filter or breakout['volume_confirmed']:
                        return {
                            'symbol': symbol,
                            'signal': 'buy',
                            'signal_strength': 0.8,  # High confidence
                            'entry_price': current_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'timestamp': current_time.isoformat() if hasattr(current_time, 'isoformat') else str(current_time)
                        }
                
            elif breakout['type'] == 'bearish':
                # For bearish breakouts, price should come back up to the support level (now resistance)
                if (abs(current_price - breakout['level']) < retest_max_distance and 
                    current_price < breakout['level']):
                    
                    # Found a bearish retest
                    stop_loss = current_price + current_atr * self.atr_multiplier
                    take_profit = current_price - (stop_loss - current_price) * self.risk_reward_ratio
                    
                    # Mark as retested
                    breakout['retested'] = True
                    
                    logger.info(f"Detected bearish retest for {symbol} at {breakout['level']}")
                    
                    # Return the signal if volume filter passed or not required
                    if not self.volume_filter or breakout['volume_confirmed']:
                        return {
                            'symbol': symbol,
                            'signal': 'sell',
                            'signal_strength': 0.8,  # High confidence
                            'entry_price': current_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'timestamp': current_time.isoformat() if hasattr(current_time, 'isoformat') else str(current_time)
                        }
        
        return None


class BreakOfStructure(ScalpingStrategy):
    """Break of Structure (BOS) Strategy for MT5
    
    This strategy identifies points where price breaks previous structure,
    indicating a likely continuation of the trend. BOS is a key part of 
    the Smart Money Concept (SMC) approach to trading.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the Break of Structure strategy
        
        Args:
            config: Strategy configuration
        """
        super().__init__(config)
        
        # Strategy-specific parameters
        self.lookback_periods = config.get('lookback_periods', 20)  # How far back to look for swing points
        self.min_swing_size_pips = config.get('min_swing_size_pips', 5)  # Minimum size for valid swing
        self.break_confirmation_bars = config.get('break_confirmation_bars', 1)  # Bars to confirm break
        self.use_trend_filter = config.get('use_trend_filter', True)  # Use longer-term trend filter
        self.trend_ema_period = config.get('trend_ema_period', 50)  # EMA period for trend filter
        self.volume_filter = config.get('volume_filter', True)  # Filter for volume confirmation
        self.volume_threshold = config.get('volume_threshold', 1.3)  # Volume increase threshold
        self.atr_period = config.get('atr_period', 14)  # ATR period for stop loss
        self.atr_multiplier = config.get('atr_multiplier', 1.0)  # ATR multiplier for stop loss
        self.risk_reward_ratio = config.get('risk_reward_ratio', 1.5)  # Risk-reward ratio
        
        # Initialization requires more bars for swing point detection
        self.warmup_bars = max(self.lookback_periods + 20, self.warmup_bars)
        
        # Track identified swing points and BOS signals
        self.swing_highs = {}
        self.swing_lows = {}
        self.bos_signals = {}
        
        logger.info(f"Break of Structure strategy initialized with lookback: {self.lookback_periods}")
    
    def analyze(self, symbol: str, data: pd.DataFrame) -> Dict:
        """
        Analyze market data with Break of Structure strategy
        
        Args:
            symbol: Trading symbol
            data: OHLCV data as pandas DataFrame
            
        Returns:
            Dict with signal information
        """
        # Ensure we have enough data
        if len(data) < self.warmup_bars:
            return {
                'symbol': symbol,
                'signal': 'none',
                'signal_strength': 0,
                'entry_price': 0,
                'stop_loss': 0,
                'take_profit': 0,
                'timestamp': datetime.now().isoformat()
            }
        
        # Find swing points
        self._find_swing_points(symbol, data)
        
        # Identify trends
        trend = self._identify_trend(data)
        
        # Detect break of structure
        bos_signal = self._detect_bos(symbol, data, trend)
        
        # If we have a valid BOS signal, return it
        if bos_signal and bos_signal['signal'] != 'none':
            return bos_signal
        
        # No signal found
        return {
            'symbol': symbol,
            'signal': 'none',
            'signal_strength': 0,
            'entry_price': 0,
            'stop_loss': 0,
            'take_profit': 0,
            'timestamp': datetime.now().isoformat()
        }
    
    def _find_swing_points(self, symbol: str, data: pd.DataFrame) -> None:
        """
        Find swing high and low points in the price data
        
        Args:
            symbol: Trading symbol
            data: OHLCV data
        """
        # Calculate pip value (approximate)
        pip_value = 0.0001  # For most pairs
        if data['close'].iloc[-1] > 100:
            pip_value = 0.01  # For JPY pairs
        
        min_swing_size = self.min_swing_size_pips * pip_value
        
        # Initialize swing points storage for this symbol if not exists
        if symbol not in self.swing_highs:
            self.swing_highs[symbol] = []
        if symbol not in self.swing_lows:
            self.swing_lows[symbol] = []
        
        # Use only a portion of the data for swing point detection
        df = data.iloc[-self.lookback_periods:].copy()
        
        # Find swing highs - a point is a swing high if:
        # 1. Higher than X bars before and after it
        # 2. The price difference is significant (min_swing_size)
        swing_highs = []
        for i in range(2, len(df) - 2):
            if (df['high'].iloc[i] > df['high'].iloc[i-1] and 
                df['high'].iloc[i] > df['high'].iloc[i-2] and
                df['high'].iloc[i] > df['high'].iloc[i+1] and
                df['high'].iloc[i] > df['high'].iloc[i+2]):
                
                # Check if the swing is significant enough
                left_diff = df['high'].iloc[i] - max(df['high'].iloc[i-2:i])
                right_diff = df['high'].iloc[i] - max(df['high'].iloc[i+1:i+3])
                
                if left_diff > min_swing_size and right_diff > min_swing_size:
                    swing_highs.append({
                        'index': i,
                        'price': df['high'].iloc[i],
                        'timestamp': df.index[i] if isinstance(df.index, pd.DatetimeIndex) else i
                    })
        
        # Find swing lows
        swing_lows = []
        for i in range(2, len(df) - 2):
            if (df['low'].iloc[i] < df['low'].iloc[i-1] and 
                df['low'].iloc[i] < df['low'].iloc[i-2] and
                df['low'].iloc[i] < df['low'].iloc[i+1] and
                df['low'].iloc[i] < df['low'].iloc[i+2]):
                
                # Check if the swing is significant enough
                left_diff = min(df['low'].iloc[i-2:i]) - df['low'].iloc[i]
                right_diff = min(df['low'].iloc[i+1:i+3]) - df['low'].iloc[i]
                
                if left_diff > min_swing_size and right_diff > min_swing_size:
                    swing_lows.append({
                        'index': i,
                        'price': df['low'].iloc[i],
                        'timestamp': df.index[i] if isinstance(df.index, pd.DatetimeIndex) else i
                    })
        
        # Store the new swing points
        self.swing_highs[symbol] = swing_highs
        self.swing_lows[symbol] = swing_lows
        
        logger.debug(f"Found {len(swing_highs)} swing highs and {len(swing_lows)} swing lows for {symbol}")
    
    def _identify_trend(self, data: pd.DataFrame) -> str:
        """
        Identify the current market trend
        
        Args:
            data: OHLCV data
            
        Returns:
            Trend direction as string ('bullish', 'bearish', or 'sideways')
        """
        if not self.use_trend_filter:
            return 'none'  # No trend filter applied
        
        # Calculate EMA for trend identification
        ema = EMAIndicator(close=data['close'], window=self.trend_ema_period).ema_indicator()
        
        # Get the current price and EMA value
        current_price = data['close'].iloc[-1]
        current_ema = ema.iloc[-1]
        
        # Calculate the EMA slope over the last few periods
        ema_slope = (ema.iloc[-1] - ema.iloc[-5]) / 5
        
        # Determine trend based on price relation to EMA and EMA slope
        if current_price > current_ema and ema_slope > 0:
            return 'bullish'
        elif current_price < current_ema and ema_slope < 0:
            return 'bearish'
        else:
            return 'sideways'
    
    def _detect_bos(self, symbol: str, data: pd.DataFrame, trend: str) -> Optional[Dict]:
        """
        Detect break of structure signals
        
        Args:
            symbol: Trading symbol
            data: OHLCV data
            trend: Current market trend
            
        Returns:
            Signal dictionary if BOS found, None otherwise
        """
        if symbol not in self.swing_highs or symbol not in self.swing_lows:
            return None
        
        # Calculate ATR for stop loss and take profit
        atr = AverageTrueRange(high=data['high'], low=data['low'], close=data['close'], 
                              window=self.atr_period).average_true_range()
        current_atr = atr.iloc[-1]
        
        # Get current price
        current_price = data['close'].iloc[-1]
        current_time = data.index[-1] if isinstance(data.index, pd.DatetimeIndex) else datetime.now()
        
        # Calculate volume confirmation if needed
        volume_confirmed = True
        if self.volume_filter:
            # Calculate average volume over last 10 bars
            avg_volume = data['volume'].iloc[-11:-1].mean()
            current_volume = data['volume'].iloc[-1]
            
            volume_confirmed = current_volume > (avg_volume * self.volume_threshold)
        
        # Initialize BOS signals dict if not exists
        if symbol not in self.bos_signals:
            self.bos_signals[symbol] = []
        
        # Check for bullish BOS (if trend is bullish or no trend filter)
        if trend == 'bullish' or trend == 'none':
            # Sort swing highs by recency
            recent_swing_highs = sorted(self.swing_highs[symbol], key=lambda x: x['index'], reverse=True)
            
            if len(recent_swing_highs) >= 2:
                # Get most recent swing high
                latest_swing_high = recent_swing_highs[0]
                prev_swing_high = recent_swing_highs[1]
                
                # Check if price has broken above previous swing high
                if (current_price > prev_swing_high['price'] and 
                    # Make sure this is a new break, not one we've already signaled
                    not any(b['swing_point'] == prev_swing_high['price'] and b['type'] == 'bullish_bos' 
                           for b in self.bos_signals[symbol])):
                    
                    # BOS confirmation - wait for n bars after the break
                    # We would typically check if a certain number of bars have closed above the swing high
                    
                    # For a more sophisticated implementation, you might check:
                    # 1. If price has closed above the swing high for X consecutive bars
                    # 2. If the current bar has closed with strong momentum
                    # For this example, we'll keep it simple
                    
                    # Generate bullish BOS signal
                    stop_loss = current_price - current_atr * self.atr_multiplier
                    take_profit = current_price + ((current_price - stop_loss) * self.risk_reward_ratio)
                    
                    # Mark as retested
                    breakout['retested'] = True
                    
                    logger.info(f"Detected bullish BOS for {symbol} at {current_price}")
                    
                    # Return the signal if volume filter passed or not required
                    if not self.volume_filter or volume_confirmed:
                        return {
                            'symbol': symbol,
                            'signal': 'buy',
                            'signal_strength': 0.75,  # Good confidence
                            'entry_price': current_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'timestamp': current_time.isoformat() if hasattr(current_time, 'isoformat') else str(current_time)
                        }
        
        # Check for bearish BOS (if trend is bearish or no trend filter)
        if trend == 'bearish' or trend == 'none':
            # Sort swing lows by recency
            recent_swing_lows = sorted(self.swing_lows[symbol], key=lambda x: x['index'], reverse=True)
            
            if len(recent_swing_lows) >= 2:
                # Get most recent swing low
                latest_swing_low = recent_swing_lows[0]
                prev_swing_low = recent_swing_lows[1]
                
                # Check if price has broken below previous swing low
                if (current_price < prev_swing_low['price'] and 
                    # Make sure this is a new break, not one we've already signaled
                    not any(b['swing_point'] == prev_swing_low['price'] and b['type'] == 'bearish_bos' 
                           for b in self.bos_signals[symbol])):
                    
                    # Generate bearish BOS signal
                    stop_loss = current_price + current_atr * self.atr_multiplier
                    take_profit = current_price - ((stop_loss - current_price) * self.risk_reward_ratio)
                    
                    # Mark as retested
                    breakout['retested'] = True
                    
                    logger.info(f"Detected bearish BOS for {symbol} at {current_price}")
                    
                    # Return the signal if volume filter passed or not required
                    if not self.volume_filter or volume_confirmed:
                        return {
                            'symbol': symbol,
                            'signal': 'sell',
                            'signal_strength': 0.75,  # Good confidence
                            'entry_price': current_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'timestamp': current_time.isoformat() if hasattr(current_time, 'isoformat') else str(current_time)
                        }
        
        return None


class FairValueGap(ScalpingStrategy):
    """Fair Value Gap (FVG) Strategy for MT5
    
    This strategy identifies price gaps or imbalances in the market where minimal
    or no trading activity has occurred, resulting from rapid price movements.
    These gaps often indicate areas where the market may retrace to "fill" the gap
    before continuing its original trend.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the Fair Value Gap strategy
        
        Args:
            config: Strategy configuration
        """
        super().__init__(config)
        
        # Strategy-specific parameters
        self.lookback_period = config.get('lookback_period', 100)  # Bars to lookback for FVG detection
        self.min_gap_size_pips = config.get('min_gap_size_pips', 5)  # Minimum size for valid FVG in pips
        self.max_gap_size_pips = config.get('max_gap_size_pips', 30)  # Maximum size for valid FVG in pips
        self.use_trend_filter = config.get('use_trend_filter', True)  # Whether to use trend filter
        self.trend_ema_period = config.get('trend_ema_period', 50)  # EMA period for trend filter
        self.volume_confirmation = config.get('volume_confirmation', True)  # Use volume confirmation
        self.volume_threshold = config.get('volume_threshold', 1.5)  # Volume increase threshold
        self.gap_validity_periods = config.get('gap_validity_periods', 50)  # How long FVGs remain valid
        self.mitigation_threshold = config.get('mitigation_threshold', 0.5)  # How much of gap must be filled (0-1)
        self.atr_period = config.get('atr_period', 14)  # ATR period for stop loss
        self.atr_multiplier = config.get('atr_multiplier', 1.0)  # ATR multiplier for stop loss
        self.risk_reward_ratio = config.get('risk_reward_ratio', 2.0)  # Risk-reward ratio
        
        # Initialization requires more bars to detect FVGs
        self.warmup_bars = max(self.lookback_period + 20, self.warmup_bars)
        
        # Track identified FVGs
        self.bullish_fvgs = {}  # Symbol -> list of bullish FVGs
        self.bearish_fvgs = {}  # Symbol -> list of bearish FVGs
        
        logger.info(f"Fair Value Gap strategy initialized with lookback: {self.lookback_period}")
    
    def analyze(self, symbol: str, data: pd.DataFrame) -> Dict:
        """
        Analyze market data with Fair Value Gap strategy
        
        Args:
            symbol: Trading symbol
            data: OHLCV data as pandas DataFrame
            
        Returns:
            Dict with signal information
        """
        # Ensure we have enough data
        if len(data) < self.warmup_bars:
            return {
                'symbol': symbol,
                'signal': 'none',
                'signal_strength': 0,
                'entry_price': 0,
                'stop_loss': 0,
                'take_profit': 0,
                'timestamp': datetime.now().isoformat()
            }
        
        # Calculate pip value (approximate)
        pip_value = 0.0001  # For most pairs
        if data['close'].iloc[-1] > 100:
            pip_value = 0.01  # For JPY pairs
        
        # Calculate ATR for stop loss and take profit
        atr = AverageTrueRange(high=data['high'], low=data['low'], close=data['close'], 
                              window=self.atr_period).average_true_range()
        current_atr = atr.iloc[-1]
        
        # Get current price and time
        current_price = data['close'].iloc[-1]
        current_time = data.index[-1] if isinstance(data.index, pd.DatetimeIndex) else datetime.now()
        
        # Identify trend if using filter
        trend = self._identify_trend(data)
        
        # Detect Fair Value Gaps
        self._detect_fvgs(symbol, data, pip_value)
        
        # Update existing FVGs (remove expired/mitigated)
        self._update_fvgs(symbol, data)
        
        # Check for trading opportunities
        fvg_signal = self._check_for_signals(symbol, data, trend, current_price, current_atr, current_time)
        
        # If we have a valid FVG signal, return it
        if fvg_signal and fvg_signal['signal'] != 'none':
            return fvg_signal
        
        # No signal found
        return {
            'symbol': symbol,
            'signal': 'none',
            'signal_strength': 0,
            'entry_price': 0,
            'stop_loss': 0,
            'take_profit': 0,
            'timestamp': datetime.now().isoformat()
        }
    
    def _identify_trend(self, data: pd.DataFrame) -> str:
        """
        Identify the current market trend
        
        Args:
            data: OHLCV data
            
        Returns:
            Trend direction as string ('bullish', 'bearish', or 'sideways')
        """
        if not self.use_trend_filter:
            return 'none'  # No trend filter applied
        
        # Calculate EMA for trend identification
        ema = EMAIndicator(close=data['close'], window=self.trend_ema_period).ema_indicator()
        
        # Get the current price and EMA value
        current_price = data['close'].iloc[-1]
        current_ema = ema.iloc[-1]
        
        # Calculate the EMA slope over the last few periods
        ema_slope = (ema.iloc[-1] - ema.iloc[-5]) / 5
        
        # Determine trend based on price relation to EMA and EMA slope
        if current_price > current_ema and ema_slope > 0:
            return 'bullish'
        elif current_price < current_ema and ema_slope < 0:
            return 'bearish'
        else:
            return 'sideways'
    
    def _detect_fvgs(self, symbol: str, data: pd.DataFrame, pip_value: float) -> None:
        """
        Detect Fair Value Gaps in the price data
        
        Args:
            symbol: Trading symbol
            data: OHLCV data
            pip_value: Value of one pip for the symbol
        """
        # Initialize FVG storage for this symbol if not exists
        if symbol not in self.bullish_fvgs:
            self.bullish_fvgs[symbol] = []
        if symbol not in self.bearish_fvgs:
            self.bearish_fvgs[symbol] = []
        
        # Calculate minimum and maximum gap sizes in price terms
        min_gap_size = self.min_gap_size_pips * pip_value
        max_gap_size = self.max_gap_size_pips * pip_value
        
        # We need at least 3 candles to detect an FVG
        if len(data) < 3:
            return
        
        # Use only a portion of the data for FVG detection
        df = data.iloc[-self.lookback_period:].copy()
        
        # Check volume confirmation
        volume_confirmed = True
        if self.volume_confirmation:
            # We'll check volume when detecting individual FVGs
            pass
        
        # Loop through data to find FVGs
        # We start from index 2 since we need to look at 3 consecutive candles
        # And we stop one before the end to avoid accessing beyond the array
        for i in range(2, len(df)-1):
            # Extract the three candles for FVG detection
            candle1 = {
                'open': df['open'].iloc[i-2],
                'high': df['high'].iloc[i-2],
                'low': df['low'].iloc[i-2],
                'close': df['close'].iloc[i-2],
                'volume': df['volume'].iloc[i-2],
                'index': i-2,
                'time': df.index[i-2] if isinstance(df.index, pd.DatetimeIndex) else i-2
            }
            
            candle2 = {
                'open': df['open'].iloc[i-1],
                'high': df['high'].iloc[i-1],
                'low': df['low'].iloc[i-1],
                'close': df['close'].iloc[i-1],
                'volume': df['volume'].iloc[i-1],
                'index': i-1,
                'time': df.index[i-1] if isinstance(df.index, pd.DatetimeIndex) else i-1
            }
            
            candle3 = {
                'open': df['open'].iloc[i],
                'high': df['high'].iloc[i],
                'low': df['low'].iloc[i],
                'close': df['close'].iloc[i],
                'volume': df['volume'].iloc[i],
                'index': i,
                'time': df.index[i] if isinstance(df.index, pd.DatetimeIndex) else i
            }
            
            # Check for bullish FVG
            # A bullish FVG forms when the low of candle3 is higher than the high of candle1
            if candle3['low'] > candle1['high']:
                # Calculate gap size
                gap_size = candle3['low'] - candle1['high']
                
                # Validate gap size
                if min_gap_size <= gap_size <= max_gap_size:
                    # Volume confirmation if required
                    volume_confirmed = True
                    if self.volume_confirmation:
                        # Compare volume of middle candle to average
                        avg_volume = df['volume'].iloc[max(0, i-5):i-1].mean()
                        volume_confirmed = candle2['volume'] > (avg_volume * self.volume_threshold)
                    
                    # Add to bullish FVGs if not already detected
                    # Check if this FVG overlaps with any existing one
                    overlap = False
                    for fvg in self.bullish_fvgs[symbol]:
                        if (candle1['high'] <= fvg['upper'] and candle3['low'] >= fvg['lower']) or \
                           (candle1['high'] >= fvg['lower'] and candle3['low'] <= fvg['upper']):
                            overlap = True
                            break
                    
                    if not overlap:
                        # Create FVG object
                        fvg = {
                            'type': 'bullish',
                            'upper': candle3['low'],
                            'lower': candle1['high'],
                            'middle': (candle3['low'] + candle1['high']) / 2,
                            'size': gap_size,
                            'created_at': candle3['time'],
                            'created_index': candle3['index'],
                            'expires_at': candle3['index'] + self.gap_validity_periods,
                            'mitigated': False,
                            'volume_confirmed': volume_confirmed
                        }
                        
                        self.bullish_fvgs[symbol].append(fvg)
                        logger.debug(f"Detected bullish FVG for {symbol} from {fvg['lower']:.5f} to {fvg['upper']:.5f}")
            
            # Check for bearish FVG
            # A bearish FVG forms when the high of candle3 is lower than the low of candle1
            if candle3['high'] < candle1['low']:
                # Calculate gap size
                gap_size = candle1['low'] - candle3['high']
                
                # Validate gap size
                if min_gap_size <= gap_size <= max_gap_size:
                    # Volume confirmation if required
                    volume_confirmed = True
                    if self.volume_confirmation:
                        # Compare volume of middle candle to average
                        avg_volume = df['volume'].iloc[max(0, i-5):i-1].mean()
                        volume_confirmed = candle2['volume'] > (avg_volume * self.volume_threshold)
                    
                    # Add to bearish FVGs if not already detected
                    # Check if this FVG overlaps with any existing one
                    overlap = False
                    for fvg in self.bearish_fvgs[symbol]:
                        if (candle1['low'] >= fvg['upper'] and candle3['high'] <= fvg['lower']) or \
                           (candle1['low'] <= fvg['lower'] and candle3['high'] >= fvg['upper']):
                            overlap = True
                            break
                    
                    if not overlap:
                        # Create FVG object
                        fvg = {
                            'type': 'bearish',
                            'upper': candle1['low'],
                            'lower': candle3['high'],
                            'middle': (candle1['low'] + candle3['high']) / 2,
                            'size': gap_size,
                            'created_at': candle3['time'],
                            'created_index': candle3['index'],
                            'expires_at': candle3['index'] + self.gap_validity_periods,
                            'mitigated': False,
                            'volume_confirmed': volume_confirmed
                        }
                        
                        self.bearish_fvgs[symbol].append(fvg)
                        logger.debug(f"Detected bearish FVG for {symbol} from {fvg['lower']:.5f} to {fvg['upper']:.5f}")
    
    def _update_fvgs(self, symbol: str, data: pd.DataFrame) -> None:
        """
        Update the status of existing FVGs and remove expired/mitigated ones
        
        Args:
            symbol: Trading symbol
            data: OHLCV data
        """
        if symbol not in self.bullish_fvgs or symbol not in self.bearish_fvgs:
            return
        
        # Get the current index
        current_index = len(data) - 1
        
        # Update bullish FVGs
        updated_bullish = []
        for fvg in self.bullish_fvgs[symbol]:
            # Skip already mitigated FVGs
            if fvg['mitigated']:
                continue
            
            # Check if FVG has expired
            if fvg['expires_at'] < current_index:
                logger.debug(f"Bullish FVG for {symbol} expired at {fvg['upper']:.5f}-{fvg['lower']:.5f}")
                continue
            
            # Check if price has mitigated the FVG (price went back into the gap)
            # We consider a gap mitigated if price has retraced at least X% into the gap
            high_after_fvg = data['high'].iloc[fvg['created_index']:current_index+1].max()
            low_after_fvg = data['low'].iloc[fvg['created_index']:current_index+1].min()
            
            mitigation_level = fvg['upper'] - (fvg['size'] * self.mitigation_threshold)
            
            # If the low price after FVG formation is lower than the mitigation level,
            # then the FVG is considered mitigated
            if low_after_fvg <= mitigation_level:
                fvg['mitigated'] = True
                logger.debug(f"Bullish FVG for {symbol} mitigated at {fvg['upper']:.5f}-{fvg['lower']:.5f}")
                continue
            
            # Keep this FVG
            updated_bullish.append(fvg)
        
        # Update bearish FVGs
        updated_bearish = []
        for fvg in self.bearish_fvgs[symbol]:
            # Skip already mitigated FVGs
            if fvg['mitigated']:
                continue
            
            # Check if FVG has expired
            if fvg['expires_at'] < current_index:
                logger.debug(f"Bearish FVG for {symbol} expired at {fvg['upper']:.5f}-{fvg['lower']:.5f}")
                continue
            
            # Check if price has mitigated the FVG
            high_after_fvg = data['high'].iloc[fvg['created_index']:current_index+1].max()
            low_after_fvg = data['low'].iloc[fvg['created_index']:current_index+1].min()
            
            mitigation_level = fvg['lower'] + (fvg['size'] * self.mitigation_threshold)
            
            # If the high price after FVG formation is higher than the mitigation level,
            # then the FVG is considered mitigated
            if high_after_fvg >= mitigation_level:
                fvg['mitigated'] = True
                logger.debug(f"Bearish FVG for {symbol} mitigated at {fvg['upper']:.5f}-{fvg['lower']:.5f}")
                continue
            
            # Keep this FVG
            updated_bearish.append(fvg)
        
        # Update the FVG lists
        self.bullish_fvgs[symbol] = updated_bullish
        self.bearish_fvgs[symbol] = updated_bearish
    
    def _check_for_signals(self, symbol: str, data: pd.DataFrame, trend: str, 
                           current_price: float, current_atr: float, current_time) -> Optional[Dict]:
        """
        Check for trading signals based on FVGs
        
        Args:
            symbol: Trading symbol
            data: OHLCV data
            trend: Current market trend
            current_price: Current price
            current_atr: Current ATR value
            current_time: Current timestamp
            
        Returns:
            Signal dictionary if trading opportunity found, None otherwise
        """
        if symbol not in self.bullish_fvgs or symbol not in self.bearish_fvgs:
            return None
        
        # For bullish trend or no trend filter, check bearish FVGs (for long entries)
        if trend == 'bullish' or trend == 'none':
            # Sort bearish FVGs by distance from current price
            nearby_bearish_fvgs = sorted(
                [fvg for fvg in self.bearish_fvgs[symbol] if not fvg['mitigated']],
                key=lambda x: abs(current_price - x['middle'])
            )
            
            # Check if price is approaching a bearish FVG
            for fvg in nearby_bearish_fvgs:
                # Skip if volume not confirmed and we require it
                if self.volume_confirmation and not fvg['volume_confirmed']:
                    continue
                
                # Check if price is close to the lower bound of the bearish FVG
                # This would be a potential long entry as price approaches the gap
                if current_price <= fvg['lower'] * 1.001:  # Within 0.1% of lower bound
                    # Generate long signal
                    stop_loss = current_price - (current_atr * self.atr_multiplier)
                    # Target is upper bound of the FVG
                    take_profit = fvg['upper']
                    
                    # Check risk-reward ratio
                    if (take_profit - current_price) < (current_price - stop_loss) * self.risk_reward_ratio:
                        # Skip if risk-reward is not favorable
                        continue
                    
                    logger.info(f"Generated buy signal based on bearish FVG for {symbol} at {current_price:.5f}")
                    return {
                        'symbol': symbol,
                        'signal': 'buy',
                        'signal_strength': 0.7,  # Moderate confidence
                        'entry_price': current_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'timestamp': current_time.isoformat() if hasattr(current_time, 'isoformat') else str(current_time),
                        'fvg': fvg
                    }
        
        # For bearish trend or no trend filter, check bullish FVGs (for short entries)
        if trend == 'bearish' or trend == 'none':
            # Sort bullish FVGs by distance from current price
            nearby_bullish_fvgs = sorted(
                [fvg for fvg in self.bullish_fvgs[symbol] if not fvg['mitigated']],
                key=lambda x: abs(current_price - x['middle'])
            )
            
            # Check if price is approaching a bullish FVG
            for fvg in nearby_bullish_fvgs:
                # Skip if volume not confirmed and we require it
                if self.volume_confirmation and not fvg['volume_confirmed']:
                    continue
                
                # Check if price is close to the upper bound of the bullish FVG
                # This would be a potential short entry as price approaches the gap
                if current_price >= fvg['upper'] * 0.999:  # Within 0.1% of upper bound
                    # Generate short signal
                    stop_loss = current_price + (current_atr * self.atr_multiplier)
                    # Target is lower bound of the FVG
                    take_profit = fvg['lower']
                    
                    # Check risk-reward ratio
                    if (current_price - take_profit) < (stop_loss - current_price) * self.risk_reward_ratio:
                        # Skip if risk-reward is not favorable
                        continue
                    
                    logger.info(f"Generated sell signal based on bullish FVG for {symbol} at {current_price:.5f}")
                    return {
                        'symbol': symbol,
                        'signal': 'sell',
                        'signal_strength': 0.7,  # Moderate confidence
                        'entry_price': current_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'timestamp': current_time.isoformat() if hasattr(current_time, 'isoformat') else str(current_time),
                        'fvg': fvg
                    }
        
        return None


class JHookPattern(ScalpingStrategy):
    """
    JHook Pattern Strategy

    The JHook pattern identifies institutional liquidity zones and strong resumption of trend.
    It consists of:
    1. Initial trend move
    2. Retracement phase (forming the hook)
    3. Consolidation period
    4. Breakout in the direction of the original trend

    This strategy aims to capture the continuation of trends after a temporary retracement.
    """

    def __init__(self, config: dict):
        """
        Initialize the JHook Pattern strategy.

        Args:
            config (dict): Strategy configuration parameters
        """
        super().__init__(config)
        self.name = config.get('name', 'JHook Pattern')
        self.lookback_period = config.get('lookback_period', 50)
        self.trend_strength = config.get('trend_strength', 10)  # Minimum pips for initial trend
        self.retracement_threshold = config.get('retracement_threshold', 0.382)  # Fib retracement level
        self.consolidation_periods = config.get('consolidation_periods', 5)  # Min bars in consolidation
        self.breakout_threshold = config.get('breakout_threshold', 0.5)  # % of initial move
        self.volume_confirmation = config.get('volume_confirmation', True)
        self.volume_threshold = config.get('volume_threshold', 1.5)  # Minimum volume increase
        self.atr_period = config.get('atr_period', 14)
        self.atr_multiplier = config.get('atr_multiplier', 1.0)
        self.risk_reward_ratio = config.get('risk_reward_ratio', 2.0)
        
        # Initialize pattern storage
        self.patterns = {}
        self.logger.info(f"JHook Pattern strategy initialized with: trend_strength={self.trend_strength}, "
                         f"retracement_threshold={self.retracement_threshold}, "
                         f"consolidation_periods={self.consolidation_periods}")

    def analyze(self, symbol: str, data: pd.DataFrame) -> Dict:
        """
        Analyze market data to identify JHook patterns and generate trading signals.

        Args:
            symbol (str): Trading symbol
            data (pd.DataFrame): Price data with OHLCV

        Returns:
            Dict: Trading signal with entry, stop loss, and take profit levels
        """
        # Calculate pip value for this symbol
        pip_value = self._calculate_pip_value(symbol)
        if pip_value is None:
            self.logger.error(f"Unable to calculate pip value for {symbol}")
            return self._create_neutral_signal()
        
        # Ensure we have enough data
        if len(data) < self.lookback_period:
            self.logger.warning(f"Not enough data for {symbol} JHook analysis. Need {self.lookback_period}, got {len(data)}.")
            return self._create_neutral_signal()
        
        # Calculate ATR for stop loss
        data['atr'] = self._calculate_atr(data, self.atr_period)
        
        # Identify JHook patterns
        self._identify_jhook_patterns(symbol, data, pip_value)
        
        # Check for valid trade signals
        signal = self._check_for_signals(symbol, data)
        
        # Log results
        if signal['signal'] != 'none':
            self.logger.info(f"JHook Pattern signal for {symbol}: {signal['signal']} at {signal['entry_price']}")
        
        return signal

    def _identify_jhook_patterns(self, symbol: str, data: pd.DataFrame, pip_value: float) -> None:
        """
        Identify potential JHook patterns in the price data.

        Args:
            symbol (str): Trading symbol
            data (pd.DataFrame): Price data
            pip_value (float): Value of one pip for the symbol
        """
        # Reset patterns for this symbol
        if symbol not in self.patterns:
            self.patterns[symbol] = {
                'bullish': [],
                'bearish': []
            }
        
        # Use recent data for analysis
        recent_data = data.tail(self.lookback_period).copy()
        
        # Calculate swing highs and lows
        swings = self._calculate_swings(recent_data)
        
        # Check for bullish JHook patterns
        self._identify_bullish_jhooks(symbol, recent_data, swings, pip_value)
        
        # Check for bearish JHook patterns
        self._identify_bearish_jhooks(symbol, recent_data, swings, pip_value)
        
        # Clean up expired patterns
        self._clean_expired_patterns(symbol, data.index[-1])

    def _calculate_swings(self, data: pd.DataFrame) -> Dict:
        """
        Calculate swing highs and lows in the price data.

        Args:
            data (pd.DataFrame): Price data

        Returns:
            Dict: Dictionary containing swing highs and lows with their indices
        """
        swings = {
            'highs': [],
            'lows': []
        }
        
        # Simple swing detection using local maxima/minima
        for i in range(2, len(data) - 2):
            # Check for swing high
            if (data['high'].iloc[i] > data['high'].iloc[i-1] and 
                data['high'].iloc[i] > data['high'].iloc[i-2] and
                data['high'].iloc[i] > data['high'].iloc[i+1] and
                data['high'].iloc[i] > data['high'].iloc[i+2]):
                swings['highs'].append((i, data.index[i], data['high'].iloc[i]))
            
            # Check for swing low
            if (data['low'].iloc[i] < data['low'].iloc[i-1] and 
                data['low'].iloc[i] < data['low'].iloc[i-2] and
                data['low'].iloc[i] < data['low'].iloc[i+1] and
                data['low'].iloc[i] < data['low'].iloc[i+2]):
                swings['lows'].append((i, data.index[i], data['low'].iloc[i]))
        
        return swings

    def _identify_bullish_jhooks(self, symbol: str, data: pd.DataFrame, swings: Dict, pip_value: float) -> None:
        """
        Identify bullish JHook patterns.

        Args:
            symbol (str): Trading symbol
            data (pd.DataFrame): Price data
            swings (Dict): Dictionary of swing highs and lows
            pip_value (float): Value of one pip
        """
        # Need at least 3 swing points to form a JHook
        if len(swings['lows']) < 3 or len(swings['highs']) < 2:
            return
        
        for i in range(len(swings['lows']) - 2):
            # Get three consecutive swing lows to check for JHook
            low1_idx, low1_date, low1_price = swings['lows'][i]
            low2_idx, low2_date, low2_price = swings['lows'][i+1]
            low3_idx, low3_date, low3_price = swings['lows'][i+2]
            
            # Find high between low1 and low2
            interim_highs = [h for h in swings['highs'] if h[0] > low1_idx and h[0] < low2_idx]
            if not interim_highs:
                continue
            
            high1_idx, high1_date, high1_price = max(interim_highs, key=lambda x: x[2])
            
            # Calculate the initial trend move (low1 to high1)
            initial_move = (high1_price - low1_price) / pip_value
            
            # Check if initial move is significant
            if initial_move < self.trend_strength:
                continue
            
            # Calculate retracement (high1 to low2)
            retracement = (high1_price - low2_price) / (high1_price - low1_price)
            
            # Check if retracement meets threshold (typical Fibonacci levels)
            if retracement < self.retracement_threshold or retracement > 0.786:
                continue
            
            # Check for consolidation phase and breakout
            consolidation_range = self._check_consolidation(data, low2_idx, low3_idx)
            if not consolidation_range:
                continue
            
            # Check for breakout in direction of original trend
            breakout_level = min(consolidation_range[0], low2_price)
            current_price = data['close'].iloc[-1]
            
            # Mark pattern as valid if price breaks above consolidation
            if current_price > consolidation_range[1]:
                # Calculate breakout strength
                breakout_strength = (current_price - consolidation_range[1]) / pip_value
                
                # Verify volume if required
                volume_confirmed = True
                if self.volume_confirmation:
                    volume_confirmed = self._check_volume_confirmation(data, low3_idx)
                
                if volume_confirmed and breakout_strength > self.breakout_threshold * initial_move:
                    # Add bullish JHook to patterns
                    self.patterns[symbol]['bullish'].append({
                        'start_date': low1_date,
                        'high_date': high1_date,
                        'retracement_date': low2_date,
                        'consolidation_date': low3_date,
                        'start_price': low1_price,
                        'high_price': high1_price,
                        'retracement_price': low2_price,
                        'consolidation_low': consolidation_range[0],
                        'consolidation_high': consolidation_range[1],
                        'initial_move': initial_move,
                        'retracement': retracement,
                        'entry_price': current_price,
                        'stop_loss': low3_price - self.atr_multiplier * data['atr'].iloc[-1],
                        'detection_date': data.index[-1],
                        'valid_until': self._calculate_expiry(data.index[-1])
                    })
                    self.logger.info(f"Bullish JHook detected on {symbol} at {data.index[-1]}")

    def _identify_bearish_jhooks(self, symbol: str, data: pd.DataFrame, swings: Dict, pip_value: float) -> None:
        """
        Identify bearish JHook patterns.

        Args:
            symbol (str): Trading symbol
            data (pd.DataFrame): Price data
            swings (Dict): Dictionary of swing highs and lows
            pip_value (float): Value of one pip
        """
        # Need at least 3 swing points to form a JHook
        if len(swings['highs']) < 3 or len(swings['lows']) < 2:
            return
        
        for i in range(len(swings['highs']) - 2):
            # Get three consecutive swing highs to check for JHook
            high1_idx, high1_date, high1_price = swings['highs'][i]
            high2_idx, high2_date, high2_price = swings['highs'][i+1]
            high3_idx, high3_date, high3_price = swings['highs'][i+2]
            
            # Find low between high1 and high2
            interim_lows = [l for l in swings['lows'] if l[0] > high1_idx and l[0] < high2_idx]
            if not interim_lows:
                continue
            
            low1_idx, low1_date, low1_price = min(interim_lows, key=lambda x: x[2])
            
            # Calculate the initial trend move (high1 to low1)
            initial_move = (high1_price - low1_price) / pip_value
            
            # Check if initial move is significant
            if initial_move < self.trend_strength:
                continue
            
            # Calculate retracement (low1 to high2)
            retracement = (high2_price - low1_price) / (high1_price - low1_price)
            
            # Check if retracement meets threshold (typical Fibonacci levels)
            if retracement < self.retracement_threshold or retracement > 0.786:
                continue
            
            # Check for consolidation phase and breakout
            consolidation_range = self._check_consolidation(data, high2_idx, high3_idx)
            if not consolidation_range:
                continue
            
            # Check for breakout in direction of original trend
            breakout_level = max(consolidation_range[1], high2_price)
            current_price = data['close'].iloc[-1]
            
            # Mark pattern as valid if price breaks below consolidation
            if current_price < consolidation_range[0]:
                # Calculate breakout strength
                breakout_strength = (consolidation_range[0] - current_price) / pip_value
                
                # Verify volume if required
                volume_confirmed = True
                if self.volume_confirmation:
                    volume_confirmed = self._check_volume_confirmation(data, high3_idx)
                
                if volume_confirmed and breakout_strength > self.breakout_threshold * initial_move:
                    # Add bearish JHook to patterns
                    self.patterns[symbol]['bearish'].append({
                        'start_date': high1_date,
                        'low_date': low1_date,
                        'retracement_date': high2_date,
                        'consolidation_date': high3_date,
                        'start_price': high1_price,
                        'low_price': low1_price,
                        'retracement_price': high2_price,
                        'consolidation_low': consolidation_range[0],
                        'consolidation_high': consolidation_range[1],
                        'initial_move': initial_move,
                        'retracement': retracement,
                        'entry_price': current_price,
                        'stop_loss': high3_price + self.atr_multiplier * data['atr'].iloc[-1],
                        'detection_date': data.index[-1],
                        'valid_until': self._calculate_expiry(data.index[-1])
                    })
                    self.logger.info(f"Bearish JHook detected on {symbol} at {data.index[-1]}")

    def _check_consolidation(self, data: pd.DataFrame, start_idx: int, end_idx: int) -> Optional[Tuple[float, float]]:
        """
        Check if there's a consolidation phase between two indices.

        Args:
            data (pd.DataFrame): Price data
            start_idx (int): Starting index of potential consolidation
            end_idx (int): Ending index of potential consolidation

        Returns:
            Optional[Tuple[float, float]]: Range of consolidation (low, high) or None if no valid consolidation
        """
        # Need minimum bars for consolidation
        if end_idx - start_idx < self.consolidation_periods:
            return None
        
        # Get price range during consolidation
        consolidation_data = data.iloc[start_idx:end_idx+1]
        consolidation_low = consolidation_data['low'].min()
        consolidation_high = consolidation_data['high'].max()
        
        # Calculate range as percentage of ATR
        consolidation_range = consolidation_high - consolidation_low
        avg_atr = data['atr'].iloc[start_idx:end_idx+1].mean()
        
        # Valid consolidation should have a tight range
        if consolidation_range > 2.0 * avg_atr:
            return None
        
        return (consolidation_low, consolidation_high)

    def _check_volume_confirmation(self, data: pd.DataFrame, breakout_idx: int) -> bool:
        """
        Check if breakout is confirmed by increased volume.

        Args:
            data (pd.DataFrame): Price data
            breakout_idx (int): Index of breakout bar

        Returns:
            bool: True if volume confirms breakout, False otherwise
        """
        # Need volume data
        if 'tick_volume' not in data.columns:
            return True
        
        # Get average volume before breakout
        pre_breakout_volume = data['tick_volume'].iloc[max(0, breakout_idx-5):breakout_idx].mean()
        
        # Get volume at breakout
        breakout_volume = data['tick_volume'].iloc[breakout_idx]
        
        # Check if breakout volume exceeds threshold
        return breakout_volume > self.volume_threshold * pre_breakout_volume

    def _check_for_signals(self, symbol: str, data: pd.DataFrame) -> Dict:
        """
        Check for valid trading signals based on identified JHook patterns.

        Args:
            symbol (str): Trading symbol
            data (pd.DataFrame): Price data

        Returns:
            Dict: Trading signal with entry, stop loss, and take profit levels
        """
        if symbol not in self.patterns:
            return self._create_neutral_signal()
        
        current_price = data['close'].iloc[-1]
        current_time = data.index[-1]
        atr = data['atr'].iloc[-1]
        
        # Check bullish patterns first
        for pattern in self.patterns[symbol]['bullish']:
            # Skip expired patterns
            if pattern['valid_until'] < current_time:
                continue
            
            # Entry should be after consolidation breakout
            if current_price > pattern['consolidation_high']:
                entry_price = current_price
                stop_loss = pattern['stop_loss']
                
                # Calculate take profit based on risk-reward ratio
                risk = entry_price - stop_loss
                take_profit = entry_price + (risk * self.risk_reward_ratio)
                
                return {
                    'signal': 'buy',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'pattern': 'jhook_bullish',
                    'pattern_details': pattern
                }
        
        # Check bearish patterns
        for pattern in self.patterns[symbol]['bearish']:
            # Skip expired patterns
            if pattern['valid_until'] < current_time:
                continue
            
            # Entry should be after consolidation breakout
            if current_price < pattern['consolidation_low']:
                entry_price = current_price
                stop_loss = pattern['stop_loss']
                
                # Calculate take profit based on risk-reward ratio
                risk = stop_loss - entry_price
                take_profit = entry_price - (risk * self.risk_reward_ratio)
                
                return {
                    'signal': 'sell',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'pattern': 'jhook_bearish',
                    'pattern_details': pattern
                }
        
        # No valid signals
        return self._create_neutral_signal()

    def _clean_expired_patterns(self, symbol: str, current_time) -> None:
        """
        Remove expired JHook patterns from storage.

        Args:
            symbol (str): Trading symbol
            current_time: Current timestamp
        """
        if symbol not in self.patterns:
            return
        
        # Filter out expired bullish patterns
        self.patterns[symbol]['bullish'] = [
            pattern for pattern in self.patterns[symbol]['bullish']
            if pattern['valid_until'] >= current_time
        ]
        
        # Filter out expired bearish patterns
        self.patterns[symbol]['bearish'] = [
            pattern for pattern in self.patterns[symbol]['bearish']
            if pattern['valid_until'] >= current_time
        ]

    def _calculate_expiry(self, detection_time) -> any:
        """
        Calculate expiry time for a pattern.

        Args:
            detection_time: Time when pattern was detected

        Returns:
            Expiry timestamp
        """
        # Patterns are valid for 24 hours by default
        # This should be adjusted based on timeframe and strategy requirements
        if isinstance(detection_time, pd.Timestamp):
            return detection_time + pd.Timedelta(hours=24)
        else:
            # Handle datetime or similar objects
            try:
                from datetime import timedelta
                return detection_time + timedelta(hours=24)
            except (TypeError, ImportError):
                # Fallback to returning a timestamp far in the future
                return detection_time


# Update the strategy registry with the new JHookPattern class
STRATEGY_REGISTRY = {
    'moving_average_cross': MovingAverageCross,
    'bollinger_breakout': BollingerBreakout,
    'break_and_retest': BreakAndRetest,
    'break_of_structure': BreakOfStructure,
    'fair_value_gap': FairValueGap,
    'jhook_pattern': JHookPattern,
    # New strategies
    'ma_rsi_combo': MaRsiStrategy,
    'stochastic_cross': StochasticCrossStrategy,
    'bnr_strategy': BreakAndRetestStrategy,
    'jhook_strategy': JHookPatternStrategy
}

# Factory function to create strategy instances
def create_strategy(strategy_type: str, config: dict) -> ScalpingStrategy:
    """
    Factory function to create strategy instances
    
    Args:
        strategy_type: Type of strategy to create
        config: Strategy configuration
        
    Returns:
        Strategy instance
    """
    if strategy_type not in STRATEGY_REGISTRY:
        logger.error(f"Unknown strategy type: {strategy_type}")
        raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    strategy_class = STRATEGY_REGISTRY[strategy_type]
    return strategy_class(config)
