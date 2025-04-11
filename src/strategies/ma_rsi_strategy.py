"""
MA + RSI Combo Strategy for Forex Trading
Implements a trend-following strategy with momentum confirmation
Uses 50 EMA for trend direction and RSI(14) for entry conditions
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union
from loguru import logger
import ta
from datetime import datetime, timedelta

class MaRsiStrategy:
    """
    MA + RSI Combo Strategy 
    Follows the trend using a moving average while confirming entries with RSI
    """
    
    def __init__(self, strategy_config: dict):
        """
        Initialize the MA + RSI strategy
        
        Args:
            strategy_config: Dictionary with strategy configuration
        """
        self.config = strategy_config
        self.name = "ma_rsi_combo"
        
        # Get timeframe from config or use default
        self.timeframe = strategy_config.get('timeframe', 'M5')  # Default to 5-minute chart
        
        # Configure EMA parameters
        self.ema_config = strategy_config.get('ema', {})
        self.ema_period = self.ema_config.get('period', 50)  # Default 50 EMA
        
        # Configure RSI parameters
        self.rsi_config = strategy_config.get('rsi', {})
        self.rsi_period = self.rsi_config.get('period', 14)  # Default 14 RSI
        self.rsi_overbought = self.rsi_config.get('overbought', 70)
        self.rsi_oversold = self.rsi_config.get('oversold', 30)
        
        # Entry/exit parameters
        self.entry_config = strategy_config.get('entry', {})
        self.exit_config = strategy_config.get('exit', {})
        
        # Risk settings
        self.risk_per_trade = strategy_config.get('risk_per_trade', 0.01)  # 1% risk per trade by default
        
        # Signal tracking
        self.signals = {}
        self.last_signal_time = {}
        
        logger.info(f"MA + RSI Combo strategy initialized with {self.timeframe} timeframe")
    
    def generate_signal(self, symbol: str, data: pd.DataFrame) -> Dict:
        """
        Generate trading signal based on MA + RSI strategy
        
        Args:
            symbol: Trading symbol/pair
            data: OHLCV DataFrame with price data
            
        Returns:
            Signal dictionary with trading action and parameters
        """
        if len(data) < max(self.ema_period, self.rsi_period) + 10:
            logger.warning(f"Not enough data for {symbol} to generate signals")
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
        Calculate EMA and RSI indicators
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            DataFrame with added indicator columns
        """
        df = data.copy()
        
        # Calculate EMA
        ema_indicator = ta.trend.EMAIndicator(df['close'], window=self.ema_period, fillna=True)
        df[f'ema_{self.ema_period}'] = ema_indicator.ema_indicator()
        
        # Calculate RSI
        rsi_indicator = ta.momentum.RSIIndicator(df['close'], window=self.rsi_period, fillna=True)
        df['rsi'] = rsi_indicator.rsi()
        
        # Calculate price direction
        df['price_above_ema'] = df['close'] > df[f'ema_{self.ema_period}']
        
        # Calculate EMA direction (slope)
        df['ema_direction'] = df[f'ema_{self.ema_period}'].diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
        
        # Add RSI momentum indicators
        df['rsi_bullish'] = (df['rsi'] < self.rsi_overbought) & (df['rsi'] > 45)
        df['rsi_bearish'] = (df['rsi'] > self.rsi_oversold) & (df['rsi'] < 55)
        
        # Add RSI divergence (simple implementation)
        df['rsi_higher'] = df['rsi'].diff(3) > 0
        df['price_higher'] = df['close'].diff(3) > 0
        df['bullish_divergence'] = (~df['rsi_higher']) & (df['price_higher'])
        df['bearish_divergence'] = (df['rsi_higher']) & (~df['price_higher'])
        
        return df
    
    def _check_signal_conditions(self, symbol: str, df: pd.DataFrame) -> Optional[Dict]:
        """
        Check for trading signal conditions
        
        Args:
            symbol: Trading symbol
            df: DataFrame with indicators
            
        Returns:
            Signal dictionary or None
        """
        # Get the most recent candle and the previous one
        if len(df) < 3:
            return None
            
        current = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]
        
        # Initialize signal variables
        action = "NONE"
        signal_reasons = []
        signal_strength = 0.0
        
        # Check for bullish signal
        bullish_conditions = [
            # Condition 1: Price above EMA and EMA sloping up
            current['price_above_ema'] and current['ema_direction'] > 0,
            
            # Condition 2: RSI is showing bullish momentum
            current['rsi_bullish'],
            
            # Condition 3: RSI moving up from middle zone
            current['rsi'] > prev['rsi'] and prev['rsi'] > 45 and prev['rsi'] < 65,
        ]
        
        # Check for bearish signal
        bearish_conditions = [
            # Condition 1: Price below EMA and EMA sloping down
            not current['price_above_ema'] and current['ema_direction'] < 0,
            
            # Condition 2: RSI is showing bearish momentum
            current['rsi_bearish'],
            
            # Condition 3: RSI moving down from middle zone
            current['rsi'] < prev['rsi'] and prev['rsi'] < 55 and prev['rsi'] > 35,
        ]
        
        # Additional divergence conditions
        divergence_conditions = {
            'bullish': current['bullish_divergence'],  # RSI making lower lows while price making higher lows
            'bearish': current['bearish_divergence'],  # RSI making higher highs while price making lower highs
        }
        
        # Buy signal
        if sum(bullish_conditions) >= 2:
            action = "BUY"
            signal_strength = 0.5 + (sum(bullish_conditions) / len(bullish_conditions)) * 0.5
            
            signal_reasons.append(f"Price above {self.ema_period} EMA")
            signal_reasons.append(f"RSI({self.rsi_period}) showing bullish momentum at {current['rsi']:.1f}")
            
            if divergence_conditions['bullish']:
                signal_reasons.append("Bullish divergence detected")
                signal_strength += 0.2
        
        # Sell signal
        elif sum(bearish_conditions) >= 2:
            action = "SELL"
            signal_strength = 0.5 + (sum(bearish_conditions) / len(bearish_conditions)) * 0.5
            
            signal_reasons.append(f"Price below {self.ema_period} EMA")
            signal_reasons.append(f"RSI({self.rsi_period}) showing bearish momentum at {current['rsi']:.1f}")
            
            if divergence_conditions['bearish']:
                signal_reasons.append("Bearish divergence detected")
                signal_strength += 0.2
        
        # No valid signal
        if action == "NONE" or not signal_reasons:
            return {'action': 'NONE', 'symbol': symbol}
        
        # Prevent trading too frequently
        min_time_between_signals = timedelta(minutes=30)
        if symbol in self.last_signal_time:
            time_since_last = datetime.now() - self.last_signal_time[symbol]
            if time_since_last < min_time_between_signals:
                return {'action': 'NONE', 'symbol': symbol, 'reason': 'Too soon after previous signal'}
        
        # Calculate stop loss and take profit levels
        current_price = current['close']
        atr_value = df['high'].rolling(14).max() - df['low'].rolling(14).min()
        atr = atr_value.iloc[-1] if not pd.isna(atr_value.iloc[-1]) else current_price * 0.001
        
        # Dynamic stop loss based on ATR
        stop_loss_multiplier = self.exit_config.get('sl_atr_multiplier', 1.5)
        take_profit_multiplier = self.exit_config.get('tp_atr_multiplier', 2.0)
        
        if action == "BUY":
            stop_loss = current_price - (atr * stop_loss_multiplier)
            take_profit = current_price + (atr * take_profit_multiplier)
        else:  # SELL
            stop_loss = current_price + (atr * stop_loss_multiplier)
            take_profit = current_price - (atr * take_profit_multiplier)
        
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
            'strength': signal_strength,
            'strategy': 'MA_RSI_COMBO',
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
        if 'ema_50' not in data.columns or 'rsi' not in data.columns:
            df = self._calculate_indicators(data)
        else:
            df = data
            
        current_price = df['close'].iloc[-1]
        
        # Get ATR for dynamic stop loss
        atr_value = df['high'].rolling(14).max() - df['low'].rolling(14).min()
        atr = atr_value.iloc[-1] if not pd.isna(atr_value.iloc[-1]) else current_price * 0.001
        
        # Calculate stop loss distance
        stop_loss_multiplier = self.exit_config.get('sl_atr_multiplier', 1.5)
        stop_loss_distance = atr * stop_loss_multiplier
        
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
        
        # MA+RSI works best in trending markets with moderate volatility
        if trend == 'ranging' and action != 'NONE':
            logger.info(f"MA+RSI signal rejected: {symbol} is in ranging market")
            return False
            
        # Avoid low liquidity conditions
        if liquidity == 'low':
            logger.info(f"MA+RSI signal rejected: {symbol} has low liquidity")
            return False
            
        # Adjust for high volatility
        if volatility == 'high' and signal.get('strength', 0) < 0.7:
            logger.info(f"MA+RSI signal rejected: {symbol} has high volatility with insufficient signal strength")
            return False
            
        return True
