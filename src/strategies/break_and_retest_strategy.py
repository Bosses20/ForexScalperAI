"""
Break and Retest Strategy for Forex Trading
Implements a strategy that trades the retest of broken support/resistance levels
Effectively captures high-probability reversals at key market levels
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple
from loguru import logger
import ta
from datetime import datetime, timedelta

class BreakAndRetestStrategy:
    """
    Break and Retest Strategy
    Identifies key support/resistance levels, waits for breakout and retest
    Particularly effective for range breakouts and trend continuations
    """
    
    def __init__(self, strategy_config: dict):
        """
        Initialize the Break and Retest strategy
        
        Args:
            strategy_config: Dictionary with strategy configuration
        """
        self.config = strategy_config
        self.name = "break_and_retest"
        
        # Get timeframe from config or use default
        self.timeframe = strategy_config.get('timeframe', 'H1')  # Default to 1-hour chart
        
        # Support/Resistance detection parameters
        self.sr_config = strategy_config.get('support_resistance', {})
        self.lookback_periods = self.sr_config.get('lookback_periods', 100)
        self.min_touches = self.sr_config.get('min_touches', 2)
        self.swing_strength = self.sr_config.get('swing_strength', 3)
        self.level_proximity_pips = self.sr_config.get('level_proximity_pips', 10)
        
        # Breakout confirmation parameters
        self.breakout_config = strategy_config.get('breakout', {})
        self.breakout_candles = self.breakout_config.get('confirmation_candles', 3)
        self.volume_confirmation = self.breakout_config.get('volume_confirmation', True)
        self.min_breakout_pips = self.breakout_config.get('min_pips', 10)
        
        # Retest parameters
        self.retest_config = strategy_config.get('retest', {})
        self.max_retest_wait = self.retest_config.get('max_wait_candles', 15)
        self.retest_proximity_pct = self.retest_config.get('proximity_percent', 0.1)
        
        # Order management
        self.entry_config = strategy_config.get('entry', {})
        self.exit_config = strategy_config.get('exit', {})
        
        # Risk settings
        self.risk_per_trade = strategy_config.get('risk_per_trade', 0.01)  # 1% risk per trade by default
        
        # Signal tracking
        self.signals = {}
        self.last_signal_time = {}
        self.identified_levels = {}  # Store identified S/R levels by symbol
        self.confirmed_breakouts = {}  # Store confirmed breakouts awaiting retest
        
        logger.info(f"Break and Retest strategy initialized with {self.timeframe} timeframe")
    
    def generate_signal(self, symbol: str, data: pd.DataFrame) -> Dict:
        """
        Generate trading signal based on Break and Retest strategy
        
        Args:
            symbol: Trading symbol/pair
            data: OHLCV DataFrame with price data
            
        Returns:
            Signal dictionary with trading action and parameters
        """
        if len(data) < self.lookback_periods + 10:
            logger.warning(f"Not enough data for {symbol} to detect support/resistance levels")
            return {'action': 'NONE', 'symbol': symbol}
        
        # Process data
        processed_data = self._process_data(data.copy())
        
        # Identify support and resistance levels if not already done
        if symbol not in self.identified_levels or len(self.identified_levels[symbol]) == 0:
            levels = self._identify_support_resistance(processed_data)
            self.identified_levels[symbol] = levels
            logger.info(f"Identified {len(levels)} S/R levels for {symbol}")
        
        # Check for breakouts of existing levels
        if symbol not in self.confirmed_breakouts:
            self.confirmed_breakouts[symbol] = []
            
        # Update existing breakouts with new data
        self._update_breakout_status(symbol, processed_data)
        
        # Check for new breakouts
        new_breakouts = self._detect_breakouts(symbol, processed_data)
        if new_breakouts:
            for breakout in new_breakouts:
                self.confirmed_breakouts[symbol].append(breakout)
                logger.info(f"New {breakout['direction']} breakout detected for {symbol} at level {breakout['level']:.5f}")
        
        # Check for retest signals
        signal = self._check_retest_signals(symbol, processed_data)
        
        # Store signal in history
        if symbol not in self.signals:
            self.signals[symbol] = []
        
        if signal and signal.get('action') != 'NONE':
            self.signals[symbol].append(signal)
            self.last_signal_time[symbol] = datetime.now()
            
            # Limit history to last 100 signals
            if len(self.signals[symbol]) > 100:
                self.signals[symbol] = self.signals[symbol][-100:]
                
            # Remove the executed breakout from the tracking list
            self._remove_executed_breakout(symbol, signal)
        
        return signal or {'action': 'NONE', 'symbol': symbol}
    
    def _process_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Process and prepare data for analysis
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            Processed DataFrame with additional indicators
        """
        df = data.copy()
        
        # Ensure proper datetime index
        if 'timestamp' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        
        # Calculate basic indicators
        
        # ATR for volatility assessment and stop loss calculation
        atr_indicator = ta.volatility.AverageTrueRange(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=14,
            fillna=True
        )
        df['atr'] = atr_indicator.average_true_range()
        
        # Add EMA for trend direction
        ema_indicator = ta.trend.EMAIndicator(df['close'], window=50, fillna=True)
        df['ema_50'] = ema_indicator.ema_indicator()
        df['price_above_ema'] = df['close'] > df['ema_50']
        
        # Identify local swing highs and lows
        df = self._find_swing_points(df)
        
        # Calculate normalized volume if volume data is available
        if 'volume' in df.columns:
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
        else:
            df['volume_ratio'] = 1.0  # Default if no volume data
            
        return df
    
    def _find_swing_points(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Identify swing high and low points in the price data
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added swing point indicators
        """
        n = self.swing_strength  # Number of candles on each side
        
        # Initialize swing columns
        df['swing_high'] = False
        df['swing_low'] = False
        
        # Find swing highs
        for i in range(n, len(df) - n):
            # Check if the current high is higher than n candles before and after
            is_swing_high = True
            current_high = df.iloc[i]['high']
            
            for j in range(1, n + 1):
                if df.iloc[i - j]['high'] > current_high or df.iloc[i + j]['high'] > current_high:
                    is_swing_high = False
                    break
                    
            df.iloc[i, df.columns.get_loc('swing_high')] = is_swing_high
        
        # Find swing lows
        for i in range(n, len(df) - n):
            # Check if the current low is lower than n candles before and after
            is_swing_low = True
            current_low = df.iloc[i]['low']
            
            for j in range(1, n + 1):
                if df.iloc[i - j]['low'] < current_low or df.iloc[i + j]['low'] < current_low:
                    is_swing_low = False
                    break
                    
            df.iloc[i, df.columns.get_loc('swing_low')] = is_swing_low
            
        return df
    
    def _identify_support_resistance(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify significant support and resistance levels
        
        Args:
            df: Processed DataFrame with price data
            
        Returns:
            List of support/resistance level dictionaries
        """
        levels = []
        
        # Identify levels from swing highs and lows
        for i in range(len(df) - self.swing_strength):
            if df.iloc[i]['swing_high']:
                level = df.iloc[i]['high']
                levels.append({
                    'type': 'resistance',
                    'level': level,
                    'time': df.index[i] if isinstance(df.index, pd.DatetimeIndex) else i,
                    'touches': 1,
                    'broken': False,
                    'broken_index': None,
                    'broken_direction': None
                })
                
            if df.iloc[i]['swing_low']:
                level = df.iloc[i]['low']
                levels.append({
                    'type': 'support',
                    'level': level,
                    'time': df.index[i] if isinstance(df.index, pd.DatetimeIndex) else i,
                    'touches': 1,
                    'broken': False,
                    'broken_index': None,
                    'broken_direction': None
                })
        
        # Cluster similar levels (within a small range)
        clustered_levels = self._cluster_levels(levels, df)
        
        # Filter to keep only significant levels with multiple touches
        filtered_levels = [lvl for lvl in clustered_levels if lvl['touches'] >= self.min_touches]
        
        # Sort by strength (number of touches)
        filtered_levels.sort(key=lambda x: x['touches'], reverse=True)
        
        return filtered_levels[:10]  # Keep only top 10 strongest levels
    
    def _cluster_levels(self, levels: List[Dict], df: pd.DataFrame) -> List[Dict]:
        """
        Cluster similar price levels together
        
        Args:
            levels: List of identified price levels
            df: DataFrame with price data
            
        Returns:
            Clustered list of price levels
        """
        if not levels:
            return []
            
        # Calculate proximity threshold based on ATR
        atr = df['atr'].mean()
        proximity_threshold = atr * 0.5  # Half ATR for clustering
        
        # Sort levels by price
        sorted_levels = sorted(levels, key=lambda x: x['level'])
        clustered = []
        
        current_cluster = [sorted_levels[0]]
        current_level_avg = sorted_levels[0]['level']
        
        for lvl in sorted_levels[1:]:
            # If close to current cluster, add to it
            if abs(lvl['level'] - current_level_avg) < proximity_threshold:
                current_cluster.append(lvl)
                # Update the weighted average level
                weights = [l['touches'] for l in current_cluster]
                levels_array = np.array([l['level'] for l in current_cluster])
                current_level_avg = np.average(levels_array, weights=weights)
            else:
                # Create a new cluster entry from the current cluster
                cluster_type = max(set([l['type'] for l in current_cluster]), 
                                  key=[l['type'] for l in current_cluster].count)
                
                clustered.append({
                    'type': cluster_type,
                    'level': current_level_avg,
                    'time': current_cluster[0]['time'],  # Use time of first occurrence
                    'touches': sum([l['touches'] for l in current_cluster]),
                    'broken': False,
                    'broken_index': None,
                    'broken_direction': None
                })
                
                # Start a new cluster
                current_cluster = [lvl]
                current_level_avg = lvl['level']
        
        # Add the last cluster
        if current_cluster:
            cluster_type = max(set([l['type'] for l in current_cluster]), 
                              key=[l['type'] for l in current_cluster].count)
            
            clustered.append({
                'type': cluster_type,
                'level': current_level_avg,
                'time': current_cluster[0]['time'],
                'touches': sum([l['touches'] for l in current_cluster]),
                'broken': False,
                'broken_index': None,
                'broken_direction': None
            })
        
        return clustered
    
    def _detect_breakouts(self, symbol: str, df: pd.DataFrame) -> List[Dict]:
        """
        Detect breakouts of identified support/resistance levels
        
        Args:
            symbol: Trading symbol
            df: Processed DataFrame
            
        Returns:
            List of newly confirmed breakouts
        """
        if symbol not in self.identified_levels:
            return []
            
        new_breakouts = []
        
        # For each identified level, check if a breakout has occurred
        for level in self.identified_levels[symbol]:
            # Skip already broken levels
            if level['broken']:
                continue
                
            level_price = level['level']
            
            # Get the last few candles for breakout confirmation
            last_candles = df.iloc[-self.breakout_candles:]
            
            # Check for upward breakout of resistance
            if level['type'] == 'resistance':
                # All closing prices must be above the level
                if all(last_candles['close'] > level_price):
                    # Confirm with volume if required
                    if not self.volume_confirmation or (self.volume_confirmation and 
                                                      any(last_candles['volume_ratio'] > 1.2)):
                        # Ensure enough pips movement
                        pip_value = 0.0001 if 'JPY' not in symbol else 0.01
                        min_breakout_distance = self.min_breakout_pips * pip_value
                        
                        if min(last_candles['low']) > level_price + min_breakout_distance:
                            # Mark level as broken
                            level['broken'] = True
                            level['broken_index'] = len(df) - self.breakout_candles
                            level['broken_direction'] = 'up'
                            
                            # Create breakout record
                            breakout = {
                                'symbol': symbol,
                                'level': level_price,
                                'level_type': 'resistance',
                                'direction': 'up',
                                'breakout_time': df.index[-self.breakout_candles] if isinstance(df.index, pd.DatetimeIndex) else len(df) - self.breakout_candles,
                                'breakout_index': len(df) - self.breakout_candles,
                                'breakout_price': last_candles.iloc[0]['close'],
                                'awaiting_retest': True,
                                'retest_found': False,
                                'candles_since_breakout': 0,
                                'retest_complete': False
                            }
                            
                            new_breakouts.append(breakout)
            
            # Check for downward breakout of support
            elif level['type'] == 'support':
                # All closing prices must be below the level
                if all(last_candles['close'] < level_price):
                    # Confirm with volume if required
                    if not self.volume_confirmation or (self.volume_confirmation and 
                                                      any(last_candles['volume_ratio'] > 1.2)):
                        # Ensure enough pips movement
                        pip_value = 0.0001 if 'JPY' not in symbol else 0.01
                        min_breakout_distance = self.min_breakout_pips * pip_value
                        
                        if max(last_candles['high']) < level_price - min_breakout_distance:
                            # Mark level as broken
                            level['broken'] = True
                            level['broken_index'] = len(df) - self.breakout_candles
                            level['broken_direction'] = 'down'
                            
                            # Create breakout record
                            breakout = {
                                'symbol': symbol,
                                'level': level_price,
                                'level_type': 'support',
                                'direction': 'down',
                                'breakout_time': df.index[-self.breakout_candles] if isinstance(df.index, pd.DatetimeIndex) else len(df) - self.breakout_candles,
                                'breakout_index': len(df) - self.breakout_candles,
                                'breakout_price': last_candles.iloc[0]['close'],
                                'awaiting_retest': True,
                                'retest_found': False,
                                'candles_since_breakout': 0,
                                'retest_complete': False
                            }
                            
                            new_breakouts.append(breakout)
                            
        return new_breakouts
    
    def _update_breakout_status(self, symbol: str, df: pd.DataFrame) -> None:
        """
        Update the status of confirmed breakouts waiting for retest
        
        Args:
            symbol: Trading symbol
            df: Processed DataFrame
        """
        if symbol not in self.confirmed_breakouts:
            return
            
        for breakout in self.confirmed_breakouts[symbol]:
            if not breakout['awaiting_retest'] or breakout['retest_complete']:
                continue
                
            # Increment counter of candles since breakout
            breakout['candles_since_breakout'] += 1
            
            # Check if max wait time exceeded
            if breakout['candles_since_breakout'] > self.max_retest_wait:
                breakout['awaiting_retest'] = False
                logger.info(f"Breakout for {symbol} timed out without retest")
                continue
                
            # Check for retest
            if self._check_level_retest(breakout, df):
                breakout['retest_found'] = True
                logger.info(f"Retest found for {symbol} at level {breakout['level']:.5f}")
    
    def _check_level_retest(self, breakout: Dict, df: pd.DataFrame) -> bool:
        """
        Check if a broken level has been retested
        
        Args:
            breakout: Breakout dictionary
            df: Processed DataFrame
            
        Returns:
            True if retest found, False otherwise
        """
        # Get the most recent candle
        latest_candle = df.iloc[-1]
        
        level_price = breakout['level']
        
        # For resistance broken to the upside
        if breakout['level_type'] == 'resistance' and breakout['direction'] == 'up':
            # Price needs to pull back down to the broken resistance, which now acts as support
            proximity_range = level_price * (1 - self.retest_proximity_pct/100)
            
            # Check if price pulled back to retest level
            return latest_candle['low'] <= level_price and latest_candle['low'] >= proximity_range
        
        # For support broken to the downside
        elif breakout['level_type'] == 'support' and breakout['direction'] == 'down':
            # Price needs to pull back up to the broken support, which now acts as resistance
            proximity_range = level_price * (1 + self.retest_proximity_pct/100)
            
            # Check if price pulled back to retest level
            return latest_candle['high'] >= level_price and latest_candle['high'] <= proximity_range
            
        return False
    
    def _check_retest_signals(self, symbol: str, df: pd.DataFrame) -> Optional[Dict]:
        """
        Check for trading signals from retests of broken levels
        
        Args:
            symbol: Trading symbol
            df: Processed DataFrame
            
        Returns:
            Signal dictionary or None
        """
        if symbol not in self.confirmed_breakouts or not self.confirmed_breakouts[symbol]:
            return None
            
        valid_breakouts = [b for b in self.confirmed_breakouts[symbol] 
                           if b['awaiting_retest'] and b['retest_found'] and not b['retest_complete']]
        
        if not valid_breakouts:
            return None
            
        # Get the most recent breakout with retest
        breakout = valid_breakouts[0]
        
        # Generate signal based on the retest
        action = "NONE"
        signal_reasons = []
        signal_strength = 0.0
        
        current_price = df.iloc[-1]['close']
        
        # For resistance broken to the upside, we want to BUY on the retest
        if breakout['level_type'] == 'resistance' and breakout['direction'] == 'up':
            action = "BUY"
            signal_reasons.append(f"Retest of broken resistance at {breakout['level']:.5f}")
            signal_strength = 0.8
            
            # Add more confidence if trend matches direction
            if df.iloc[-1]['price_above_ema']:
                signal_reasons.append("Aligned with bullish trend (price above EMA)")
                signal_strength += 0.1
        
        # For support broken to the downside, we want to SELL on the retest
        elif breakout['level_type'] == 'support' and breakout['direction'] == 'down':
            action = "SELL"
            signal_reasons.append(f"Retest of broken support at {breakout['level']:.5f}")
            signal_strength = 0.8
            
            # Add more confidence if trend matches direction
            if not df.iloc[-1]['price_above_ema']:
                signal_reasons.append("Aligned with bearish trend (price below EMA)")
                signal_strength += 0.1
        
        # No valid signal
        if action == "NONE" or not signal_reasons:
            return {'action': 'NONE', 'symbol': symbol}
        
        # Prevent trading too frequently
        min_time_between_signals = timedelta(hours=4)  # Longer timeframe strategy
        if symbol in self.last_signal_time:
            time_since_last = datetime.now() - self.last_signal_time[symbol]
            if time_since_last < min_time_between_signals:
                return {'action': 'NONE', 'symbol': symbol, 'reason': 'Too soon after previous signal'}
        
        # Calculate stop loss and take profit levels
        atr = df.iloc[-1]['atr'] if not pd.isna(df.iloc[-1]['atr']) else current_price * 0.001
        
        # Dynamic stop loss based on ATR
        sl_multiplier = self.exit_config.get('sl_atr_multiplier', 1.5)
        tp_multiplier = self.exit_config.get('tp_atr_multiplier', 2.5)  # Higher reward-to-risk
        
        if action == "BUY":
            # Place stop below the retest level
            stop_loss = breakout['level'] - (atr * sl_multiplier)
            take_profit = current_price + (current_price - stop_loss) * tp_multiplier
        else:  # SELL
            # Place stop above the retest level
            stop_loss = breakout['level'] + (atr * sl_multiplier)
            take_profit = current_price - (stop_loss - current_price) * tp_multiplier
        
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
            'strategy': 'BREAK_AND_RETEST',
            'timeframe': self.timeframe,
            'breakout_level': breakout['level'],
            'breakout_type': breakout['level_type']
        }
        
        # Mark breakout as complete
        breakout['retest_complete'] = True
        
        return signal
    
    def _remove_executed_breakout(self, symbol: str, signal: Dict) -> None:
        """
        Remove a breakout from tracking after signal execution
        
        Args:
            symbol: Trading symbol
            signal: Executed signal
        """
        if symbol not in self.confirmed_breakouts:
            return
            
        # Find the breakout that was executed
        breakout_level = signal.get('breakout_level')
        if not breakout_level:
            return
            
        # Remove from active tracking
        self.confirmed_breakouts[symbol] = [b for b in self.confirmed_breakouts[symbol] 
                                           if b['level'] != breakout_level or not b['retest_complete']]
    
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
        
        # Break and Retest works well in ranging and moderate trending markets
        if trend in ['strong_bullish', 'strong_bearish']:
            if action == 'BUY' and trend == 'strong_bearish':
                logger.info(f"Break and Retest signal caution: {symbol} is in strong bearish trend for a buy")
                # We don't reject outright as the breakout itself could be signaling a trend change
            elif action == 'SELL' and trend == 'strong_bullish':
                logger.info(f"Break and Retest signal caution: {symbol} is in strong bullish trend for a sell")
                # We don't reject outright as the breakout itself could be signaling a trend change
        
        # Avoid low liquidity conditions
        if liquidity == 'low':
            logger.info(f"Break and Retest signal rejected: {symbol} has low liquidity")
            return False
            
        # Break and Retest needs some volatility to work well
        if volatility == 'low' and signal.get('strength', 0) < 0.8:
            logger.info(f"Break and Retest signal caution: {symbol} has low volatility")
            # Don't reject but flag as potentially less reliable
            
        return True
