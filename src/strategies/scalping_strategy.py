"""
Scalping Strategy module for generating trading signals
Implements advanced technical indicators and price action analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union
from loguru import logger
import ta
from datetime import datetime, timedelta

class ScalpingStrategy:
    """
    Implements a scalping strategy for forex markets
    Uses a combination of technical indicators and ML predictions
    """
    
    def __init__(self, strategy_config: dict, prediction_model=None):
        """
        Initialize the scalping strategy
        
        Args:
            strategy_config: Dictionary with strategy configuration
            prediction_model: ML model for price prediction (optional)
        """
        self.config = strategy_config
        self.prediction_model = prediction_model
        self.timeframe = strategy_config.get('timeframe', '1m')
        
        # Configure indicators
        self.indicator_config = strategy_config.get('indicators', {})
        
        # Configure entry/exit parameters
        self.entry_config = strategy_config.get('entry', {})
        self.exit_config = strategy_config.get('exit', {})
        
        # Initialize signal history
        self.signal_history = {}
        
        logger.info(f"Scalping strategy initialized with {self.timeframe} timeframe")
    
    def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """
        Generate trading signals based on market data
        
        Args:
            market_data: Dictionary with pair as key and DataFrame as value
            
        Returns:
            List of signal dictionaries with action (buy/sell), pair, etc.
        """
        signals = []
        
        for pair, data in market_data.items():
            if len(data) < 50:  # Need enough data for indicators
                logger.warning(f"Not enough data for {pair}, skipping signal generation")
                continue
            
            # Calculate technical indicators
            df = self._calculate_indicators(pair, data)
            
            # Check for entry signals
            entry_signal = self._check_entry_conditions(pair, df)
            if entry_signal:
                signals.append(entry_signal)
            
            # Check for exit signals for existing positions
            exit_signal = self._check_exit_conditions(pair, df)
            if exit_signal:
                signals.append(exit_signal)
        
        if signals:
            logger.info(f"Generated {len(signals)} trading signals")
        
        return signals
    
    def _calculate_indicators(self, pair: str, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators for a given pair
        
        Args:
            pair: Currency pair
            data: OHLCV DataFrame
            
        Returns:
            DataFrame with added indicator columns
        """
        df = data.copy()
        
        # Ensure DataFrame has required columns
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Calculate EMA indicators
        if 'ema' in self.indicator_config:
            ema_config = self.indicator_config['ema']
            fast_period = ema_config.get('fast_period', 5)
            slow_period = ema_config.get('slow_period', 8)
            
            df[f'ema_{fast_period}'] = ta.trend.ema_indicator(df['close'], window=fast_period)
            df[f'ema_{slow_period}'] = ta.trend.ema_indicator(df['close'], window=slow_period)
        
        # Calculate RSI
        if 'rsi' in self.indicator_config:
            rsi_config = self.indicator_config['rsi']
            rsi_period = rsi_config.get('period', 5)
            df['rsi'] = ta.momentum.rsi(df['close'], window=rsi_period)
        
        # Calculate Bollinger Bands
        if 'bollinger' in self.indicator_config:
            bb_config = self.indicator_config['bollinger']
            bb_period = bb_config.get('period', 20)
            bb_std = bb_config.get('std_dev', 2.0)
            
            indicator_bb = ta.volatility.BollingerBands(
                close=df['close'], window=bb_period, window_dev=bb_std
            )
            df['bb_upper'] = indicator_bb.bollinger_hband()
            df['bb_lower'] = indicator_bb.bollinger_lband()
            df['bb_middle'] = indicator_bb.bollinger_mavg()
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Add price action patterns
        self._add_price_action_patterns(df)
        
        # Add ML predictions if model is available
        if self.prediction_model and hasattr(self.prediction_model, 'predict'):
            df = self._add_model_predictions(pair, df)
        
        return df
    
    def _add_price_action_patterns(self, df: pd.DataFrame):
        """
        Add price action pattern indicators to the DataFrame
        
        Args:
            df: OHLCV DataFrame
        """
        # Calculate candle body and shadow sizes
        df['body_size'] = abs(df['close'] - df['open'])
        df['upper_shadow'] = df.apply(
            lambda x: x['high'] - max(x['open'], x['close']), axis=1
        )
        df['lower_shadow'] = df.apply(
            lambda x: min(x['open'], x['close']) - x['low'], axis=1
        )
        
        # Identify pin bars (price rejection)
        df['pin_bar'] = (
            (df['body_size'] < df['body_size'].rolling(10).mean() * 0.5) &
            ((df['upper_shadow'] > df['body_size'] * 2) | 
             (df['lower_shadow'] > df['body_size'] * 2))
        )
        
        # Identify inside bars
        df['inside_bar'] = (
            (df['high'] < df['high'].shift(1)) &
            (df['low'] > df['low'].shift(1))
        )
        
        # Identify breakouts
        df['breakout_up'] = (
            (df['close'] > df['high'].rolling(5).max().shift(1)) &
            (df['close'] > df['open'])
        )
        
        df['breakout_down'] = (
            (df['close'] < df['low'].rolling(5).min().shift(1)) &
            (df['close'] < df['open'])
        )
    
    def _add_model_predictions(self, pair: str, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add ML model predictions to the DataFrame
        
        Args:
            pair: Currency pair
            df: OHLCV DataFrame
            
        Returns:
            DataFrame with added prediction columns
        """
        try:
            # Prepare features for prediction
            most_recent = df.iloc[-1].copy()
            
            # Make prediction using the model
            prediction = self.prediction_model.predict(pair, df)
            
            # Add prediction to DataFrame (last row only since we predict future)
            df.loc[df.index[-1], 'ml_prediction'] = prediction['direction']
            df.loc[df.index[-1], 'ml_confidence'] = prediction['confidence']
            
            return df
        except Exception as e:
            logger.error(f"Error making model prediction: {e}")
            return df
    
    def _check_entry_conditions(self, pair: str, df: pd.DataFrame) -> Optional[Dict]:
        """
        Check if entry conditions are met
        
        Args:
            pair: Currency pair
            df: DataFrame with indicators
            
        Returns:
            Signal dictionary or None
        """
        if len(df) < 2:
            return None
        
        # Get the most recent candle
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Default signal strength starts at 0
        signal_strength = 0
        signal_reasons = []
        
        # Check EMA crossover
        if 'ema' in self.indicator_config:
            ema_config = self.indicator_config['ema']
            fast_period = ema_config.get('fast_period', 5)
            slow_period = ema_config.get('slow_period', 8)
            
            # Bullish EMA crossover
            if (previous[f'ema_{fast_period}'] <= previous[f'ema_{slow_period}'] and 
                current[f'ema_{fast_period}'] > current[f'ema_{slow_period}']):
                signal_strength += 0.3
                signal_reasons.append(f"Bullish EMA{fast_period}-EMA{slow_period} crossover")
            
            # Bearish EMA crossover
            elif (previous[f'ema_{fast_period}'] >= previous[f'ema_{slow_period}'] and 
                  current[f'ema_{fast_period}'] < current[f'ema_{slow_period}']):
                signal_strength -= 0.3
                signal_reasons.append(f"Bearish EMA{fast_period}-EMA{slow_period} crossover")
        
        # Check RSI conditions
        if 'rsi' in self.indicator_config:
            rsi_config = self.indicator_config['rsi']
            oversold = rsi_config.get('oversold', 30)
            overbought = rsi_config.get('overbought', 70)
            
            # Oversold condition (potential buy)
            if current['rsi'] < oversold and previous['rsi'] < oversold:
                signal_strength += 0.25
                signal_reasons.append(f"RSI oversold: {current['rsi']:.2f}")
            
            # Overbought condition (potential sell)
            elif current['rsi'] > overbought and previous['rsi'] > overbought:
                signal_strength -= 0.25
                signal_reasons.append(f"RSI overbought: {current['rsi']:.2f}")
            
            # RSI divergence (advanced signal)
            if len(df) > 5:
                # Bullish divergence: price making lower lows but RSI making higher lows
                if (df['close'].iloc[-3] > df['close'].iloc[-1] and 
                    df['rsi'].iloc[-3] < df['rsi'].iloc[-1]):
                    signal_strength += 0.2
                    signal_reasons.append("Bullish RSI divergence")
                
                # Bearish divergence: price making higher highs but RSI making lower highs
                elif (df['close'].iloc[-3] < df['close'].iloc[-1] and 
                      df['rsi'].iloc[-3] > df['rsi'].iloc[-1]):
                    signal_strength -= 0.2
                    signal_reasons.append("Bearish RSI divergence")
        
        # Check Bollinger Bands
        if 'bollinger' in self.indicator_config:
            # Price near lower band (potential buy)
            if current['close'] < current['bb_lower'] * 1.001:
                signal_strength += 0.2
                signal_reasons.append("Price at lower Bollinger Band")
            
            # Price near upper band (potential sell)
            elif current['close'] > current['bb_upper'] * 0.999:
                signal_strength -= 0.2
                signal_reasons.append("Price at upper Bollinger Band")
            
            # Volatility contraction (prepare for breakout)
            if current['bb_width'] < df['bb_width'].rolling(20).mean() * 0.6:
                # Direction depends on other indicators
                if signal_strength > 0:
                    signal_strength += 0.15
                    signal_reasons.append("Volatility contraction (bullish bias)")
                elif signal_strength < 0:
                    signal_strength -= 0.15
                    signal_reasons.append("Volatility contraction (bearish bias)")
        
        # Check price action patterns
        if current['pin_bar']:
            # Determine direction of pin bar
            if current['upper_shadow'] > current['lower_shadow'] * 2:
                signal_strength -= 0.3
                signal_reasons.append("Bearish pin bar rejection")
            elif current['lower_shadow'] > current['upper_shadow'] * 2:
                signal_strength += 0.3
                signal_reasons.append("Bullish pin bar rejection")
        
        if current['breakout_up']:
            signal_strength += 0.35
            signal_reasons.append("Bullish breakout detected")
        elif current['breakout_down']:
            signal_strength -= 0.35
            signal_reasons.append("Bearish breakout detected")
        
        # Include ML prediction if available
        if 'ml_prediction' in current and 'ml_confidence' in current:
            confidence_threshold = self.entry_config.get('min_signal_strength', 0.65)
            
            if current['ml_confidence'] >= confidence_threshold:
                if current['ml_prediction'] > 0:  # Bullish prediction
                    signal_strength += 0.4
                    signal_reasons.append(f"ML predicts up move ({current['ml_confidence']:.2f} confidence)")
                elif current['ml_prediction'] < 0:  # Bearish prediction
                    signal_strength -= 0.4
                    signal_reasons.append(f"ML predicts down move ({current['ml_confidence']:.2f} confidence)")
        
        # Check if signal strength meets the threshold
        min_signal_strength = self.entry_config.get('min_signal_strength', 0.7)
        
        # Determine action based on signal strength
        action = None
        if signal_strength >= min_signal_strength:
            action = 'buy'
        elif signal_strength <= -min_signal_strength:
            action = 'sell'
        
        # No valid signal
        if not action:
            return None
        
        # Calculate risk parameters
        stop_loss_pips = self.exit_config.get('stop_loss_pips', 3)
        take_profit_pips = self.exit_config.get('take_profit_pips', 5)
        
        # Convert to absolute values based on current price
        pip_value = 0.0001 if 'JPY' not in pair else 0.01
        current_price = current['close']
        
        stop_loss = current_price - (stop_loss_pips * pip_value) if action == 'buy' else current_price + (stop_loss_pips * pip_value)
        take_profit = current_price + (take_profit_pips * pip_value) if action == 'buy' else current_price - (take_profit_pips * pip_value)
        
        # Create signal
        signal = {
            'timestamp': datetime.now().isoformat(),
            'pair': pair,
            'action': action,
            'price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'strength': abs(signal_strength),
            'reasons': signal_reasons,
            'timeframe': self.timeframe
        }
        
        # Save to signal history
        if pair not in self.signal_history:
            self.signal_history[pair] = []
        
        self.signal_history[pair].append(signal)
        
        # Keep signal history manageable
        max_history = 100
        if len(self.signal_history[pair]) > max_history:
            self.signal_history[pair] = self.signal_history[pair][-max_history:]
        
        return signal
    
    def _check_exit_conditions(self, pair: str, df: pd.DataFrame) -> Optional[Dict]:
        """
        Check if exit conditions are met for existing positions
        
        Args:
            pair: Currency pair
            df: DataFrame with indicators
            
        Returns:
            Signal dictionary or None
        """
        # This would typically check for open positions and determine if they should be closed
        # Since we don't have position tracking in this module, we'll return None
        # In a real implementation, this would check for trailing stop adjustments, etc.
        
        return None
    
    def calculate_position_size(self, signal: Dict, account_balance: float) -> float:
        """
        Calculate appropriate position size based on risk parameters
        
        Args:
            signal: Signal dictionary
            account_balance: Current account balance
            
        Returns:
            Position size in units/lots
        """
        # Default risk per trade is 1% of account balance
        risk_percent = 0.01
        
        # Calculate risk amount
        risk_amount = account_balance * risk_percent
        
        # Calculate pip value
        pip_value = 0.0001 if 'JPY' not in signal['pair'] else 0.01
        
        # Calculate stop loss distance in pips
        stop_loss_distance = abs(signal['price'] - signal['stop_loss']) / pip_value
        
        # Calculate position size in standard lots (100,000 units)
        # Formula: Risk amount / (stop loss distance in pips * pip value in account currency)
        # This is simplified and would need adjustment for different currency pairs
        
        # For simplicity, we'll use a fixed pip value in account currency
        pip_value_in_account = 10  # $10 per pip for 1 standard lot
        
        position_size = risk_amount / (stop_loss_distance * pip_value_in_account)
        
        # Convert to lots (1.0 = 1 standard lot = 100,000 units)
        position_size_lots = position_size
        
        # Ensure minimum and maximum position sizes
        min_lot = 0.01  # Micro lot
        max_lot = 0.5   # To avoid excessive positions
        
        position_size_lots = max(min_lot, min(position_size_lots, max_lot))
        
        return round(position_size_lots, 2)
