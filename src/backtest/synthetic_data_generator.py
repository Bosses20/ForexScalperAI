"""
Synthetic Data Generator for Backtesting
Generates realistic synthetic price data for backtesting with different index types
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import random
from loguru import logger

class SyntheticDataGenerator:
    """
    Generates synthetic price data for various instrument types
    to enable realistic backtesting of trading strategies
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize the synthetic data generator
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Default parameters for different synthetic types
        self.default_params = {
            'volatility': {
                'vol_10': {'base_volatility': 0.0010, 'mean_reversion': 0.05},
                'vol_25': {'base_volatility': 0.0025, 'mean_reversion': 0.04},
                'vol_50': {'base_volatility': 0.0050, 'mean_reversion': 0.03},
                'vol_75': {'base_volatility': 0.0075, 'mean_reversion': 0.02},
                'vol_100': {'base_volatility': 0.0100, 'mean_reversion': 0.01},
            },
            'crash_boom': {
                'crash_300': {'base_volatility': 0.0020, 'spike_frequency': 300, 'spike_magnitude': -0.05, 'mean_reversion': 0.03},
                'crash_500': {'base_volatility': 0.0025, 'spike_frequency': 500, 'spike_magnitude': -0.07, 'mean_reversion': 0.02},
                'crash_1000': {'base_volatility': 0.0030, 'spike_frequency': 1000, 'spike_magnitude': -0.10, 'mean_reversion': 0.01},
                'boom_300': {'base_volatility': 0.0020, 'spike_frequency': 300, 'spike_magnitude': 0.05, 'mean_reversion': 0.03},
                'boom_500': {'base_volatility': 0.0025, 'spike_frequency': 500, 'spike_magnitude': 0.07, 'mean_reversion': 0.02},
                'boom_1000': {'base_volatility': 0.0030, 'spike_frequency': 1000, 'spike_magnitude': 0.10, 'mean_reversion': 0.01},
            },
            'step': {
                'step_index': {'base_volatility': 0.0005, 'step_size': 0.0020, 'step_frequency': 20},
            },
            'jump': {
                'jump_10': {'base_volatility': 0.0010, 'jump_frequency': 50, 'jump_magnitude_range': (0.002, 0.010)},
                'jump_25': {'base_volatility': 0.0015, 'jump_frequency': 40, 'jump_magnitude_range': (0.005, 0.025)},
                'jump_50': {'base_volatility': 0.0020, 'jump_frequency': 30, 'jump_magnitude_range': (0.010, 0.050)},
                'jump_75': {'base_volatility': 0.0025, 'jump_frequency': 25, 'jump_magnitude_range': (0.015, 0.075)},
                'jump_100': {'base_volatility': 0.0030, 'jump_frequency': 20, 'jump_magnitude_range': (0.020, 0.100)},
            }
        }
        
        # Load parameters from config if provided
        if config and 'synthetic_params' in config:
            for category, indices in config['synthetic_params'].items():
                if category in self.default_params:
                    for index, params in indices.items():
                        if index in self.default_params[category]:
                            self.default_params[category][index].update(params)
        
        logger.info("Synthetic Data Generator initialized")
    
    def generate_data(self, 
                      instrument_type: str, 
                      instrument_subtype: str, 
                      start_date: datetime,
                      end_date: datetime,
                      timeframe: str = 'M1',
                      initial_price: float = 1000.0,
                      include_indicators: bool = True) -> pd.DataFrame:
        """
        Generate synthetic price data for backtesting
        
        Args:
            instrument_type: Type of instrument (forex, synthetic)
            instrument_subtype: Subtype of synthetic instrument (vol_75, crash_1000, etc.)
            start_date: Start date for generated data
            end_date: End date for generated data
            timeframe: Timeframe in MT5 format (M1, M5, H1, etc.)
            initial_price: Starting price
            include_indicators: Whether to include indicators in output
            
        Returns:
            DataFrame with OHLCV data
        """
        if instrument_type != 'synthetic':
            raise ValueError("This generator is for synthetic indices only")
        
        # Parse timeframe to minutes
        tf_minutes = self._parse_timeframe_minutes(timeframe)
        
        # Calculate number of bars needed
        delta = end_date - start_date
        total_minutes = delta.days * 24 * 60 + delta.seconds // 60
        num_bars = total_minutes // tf_minutes
        
        # Generate timestamps
        timestamps = [start_date + timedelta(minutes=i * tf_minutes) for i in range(num_bars)]
        
        # Get the right generator based on instrument type
        if instrument_subtype.startswith('vol_'):
            prices = self._generate_volatility_index(
                instrument_subtype, num_bars, initial_price)
        elif instrument_subtype.startswith('crash_') or instrument_subtype.startswith('boom_'):
            prices = self._generate_crash_boom_index(
                instrument_subtype, num_bars, initial_price)
        elif instrument_subtype.startswith('step_'):
            prices = self._generate_step_index(
                instrument_subtype, num_bars, initial_price)
        elif instrument_subtype.startswith('jump_'):
            prices = self._generate_jump_index(
                instrument_subtype, num_bars, initial_price)
        else:
            raise ValueError(f"Unknown synthetic index subtype: {instrument_subtype}")
            
        # Create OHLCV dataframe
        df = self._create_ohlcv_from_prices(prices, timestamps)
        
        # Add technical indicators if requested
        if include_indicators:
            df = self._add_indicators(df)
        
        # Add metadata
        df.attrs['instrument_type'] = instrument_type
        df.attrs['instrument_subtype'] = instrument_subtype
        
        return df
    
    def _parse_timeframe_minutes(self, timeframe: str) -> int:
        """Convert MT5 timeframe to minutes"""
        if timeframe.startswith('M'):
            return int(timeframe[1:])
        elif timeframe.startswith('H'):
            return int(timeframe[1:]) * 60
        elif timeframe.startswith('D'):
            return int(timeframe[1:]) * 60 * 24
        else:
            return 1  # Default to 1 minute
    
    def _generate_volatility_index(self, index_name: str, num_bars: int, initial_price: float) -> np.ndarray:
        """Generate price data for volatility indices"""
        # Get parameters
        category = 'volatility'
        params = self.default_params[category].get(index_name, 
                 self.default_params[category]['vol_75'])  # Default to vol_75 if not found
        
        base_volatility = params['base_volatility']
        mean_reversion = params['mean_reversion']
        
        # Generate price series with geometric brownian motion + mean reversion
        prices = np.zeros(num_bars)
        prices[0] = initial_price
        
        for i in range(1, num_bars):
            # Mean reversion component
            mean_rev = mean_reversion * (initial_price - prices[i-1])
            
            # Random component (volatility)
            random_change = np.random.normal(0, base_volatility * prices[i-1])
            
            # Combine components
            prices[i] = prices[i-1] * (1 + mean_rev + random_change)
            
            # Ensure price doesn't go too low
            prices[i] = max(prices[i], initial_price * 0.01)
            
        return prices
    
    def _generate_crash_boom_index(self, index_name: str, num_bars: int, initial_price: float) -> np.ndarray:
        """Generate price data for crash/boom indices"""
        # Get parameters
        category = 'crash_boom'
        params = self.default_params[category].get(index_name, 
                 self.default_params[category]['crash_1000'])  # Default to crash_1000
        
        base_volatility = params['base_volatility']
        spike_frequency = params['spike_frequency']
        spike_magnitude = params['spike_magnitude']
        mean_reversion = params['mean_reversion']
        
        # Generate price series with spikes
        prices = np.zeros(num_bars)
        prices[0] = initial_price
        
        for i in range(1, num_bars):
            # Mean reversion component
            mean_rev = mean_reversion * (initial_price - prices[i-1])
            
            # Random component (volatility)
            random_change = np.random.normal(0, base_volatility * prices[i-1])
            
            # Spike component
            spike = 0
            if random.random() < (1 / spike_frequency):
                spike = spike_magnitude
            
            # Combine components
            prices[i] = prices[i-1] * (1 + mean_rev + random_change + spike)
            
            # Ensure price doesn't go too low
            prices[i] = max(prices[i], initial_price * 0.01)
            
        return prices
    
    def _generate_step_index(self, index_name: str, num_bars: int, initial_price: float) -> np.ndarray:
        """Generate price data for step indices"""
        # Get parameters
        category = 'step'
        params = self.default_params[category].get(index_name, 
                 self.default_params[category]['step_index'])  # Default to step_index
        
        base_volatility = params['base_volatility']
        step_size = params['step_size']
        step_frequency = params['step_frequency']
        
        # Generate price series with uniform steps
        prices = np.zeros(num_bars)
        prices[0] = initial_price
        
        for i in range(1, num_bars):
            # Random noise component (small)
            noise = np.random.normal(0, base_volatility * prices[i-1])
            
            # Step component
            if i % step_frequency == 0:
                step = np.random.choice([-1, 1]) * step_size * prices[i-1]
            else:
                step = 0
            
            # Combine components
            prices[i] = prices[i-1] * (1 + noise + step)
            
            # Ensure price doesn't go too low
            prices[i] = max(prices[i], initial_price * 0.01)
            
        return prices
    
    def _generate_jump_index(self, index_name: str, num_bars: int, initial_price: float) -> np.ndarray:
        """Generate price data for jump indices"""
        # Get parameters
        category = 'jump'
        params = self.default_params[category].get(index_name, 
                 self.default_params[category]['jump_50'])  # Default to jump_50
        
        base_volatility = params['base_volatility']
        jump_frequency = params['jump_frequency']
        jump_min, jump_max = params['jump_magnitude_range']
        
        # Generate price series with random jumps
        prices = np.zeros(num_bars)
        prices[0] = initial_price
        
        for i in range(1, num_bars):
            # Random component (volatility)
            random_change = np.random.normal(0, base_volatility * prices[i-1])
            
            # Jump component
            jump = 0
            if random.random() < (1 / jump_frequency):
                jump_magnitude = np.random.uniform(jump_min, jump_max)
                jump = np.random.choice([-1, 1]) * jump_magnitude
            
            # Combine components
            prices[i] = prices[i-1] * (1 + random_change + jump)
            
            # Ensure price doesn't go too low
            prices[i] = max(prices[i], initial_price * 0.01)
            
        return prices
    
    def _create_ohlcv_from_prices(self, prices: np.ndarray, timestamps: List[datetime]) -> pd.DataFrame:
        """Convert price array to OHLCV dataframe"""
        # Generate realistic OHLC from close prices
        opens = np.zeros(len(prices))
        highs = np.zeros(len(prices))
        lows = np.zeros(len(prices))
        volumes = np.zeros(len(prices))
        
        # First bar
        opens[0] = prices[0]
        highs[0] = prices[0] * 1.001
        lows[0] = prices[0] * 0.999
        volumes[0] = np.random.randint(100, 1000)
        
        # Subsequent bars
        for i in range(1, len(prices)):
            opens[i] = prices[i-1]  # Open at previous close
            
            # Volatility within the bar
            intrabar_vol = abs(prices[i] - opens[i]) * 0.5
            
            # High and low
            highs[i] = max(opens[i], prices[i]) + np.random.uniform(0, intrabar_vol)
            lows[i] = min(opens[i], prices[i]) - np.random.uniform(0, intrabar_vol)
            
            # Ensure high >= low
            if highs[i] <= lows[i]:
                mean_price = (highs[i] + lows[i]) / 2
                highs[i] = mean_price * 1.001
                lows[i] = mean_price * 0.999
            
            # Random volume (correlated with price change)
            price_change_pct = abs(prices[i] - opens[i]) / opens[i]
            volumes[i] = int(np.random.gamma(1 + price_change_pct * 100, 10))
        
        # Create dataframe
        df = pd.DataFrame({
            'time': timestamps,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': prices,
            'volume': volumes
        })
        
        df.set_index('time', inplace=True)
        return df
    
    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to the dataframe"""
        # Moving averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        
        # Exponential moving averages
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # RSI (14)
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi_14'] = 100 - (100 / (1 + rs))
        
        # ATR (14)
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        df['atr_14'] = tr.rolling(window=14).mean()
        
        # Bollinger Bands (20, 2)
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        
        return df
