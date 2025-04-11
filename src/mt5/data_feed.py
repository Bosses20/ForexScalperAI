"""
MT5 Data Feed module
Handles fetching and processing market data from MetaTrader 5
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from loguru import logger
import asyncio
from concurrent.futures import ThreadPoolExecutor
import ta  # Technical Analysis library

# Import local modules
from src.mt5.connector import MT5Connector

# Import the MetaTrader5 module
try:
    import MetaTrader5 as mt5
except ImportError:
    logger.error("MetaTrader5 package not found. Please install: pip install MetaTrader5")
    mt5 = None

class MT5DataFeed:
    """
    Class for fetching and processing market data from MetaTrader 5
    """
    
    def __init__(self, config: dict, mt5_connector: Optional[MT5Connector] = None):
        """
        Initialize the MT5 data feed
        
        Args:
            config: Dictionary with data feed configuration
            mt5_connector: Optional existing MT5 connector instance
        """
        self.config = config
        self.trading_pairs = config.get('trading_pairs', [])
        self.timeframes = config.get('timeframes', ['M1', 'M5', 'M15'])
        self.max_bars = config.get('max_bars', 1000)
        self.update_interval = config.get('update_interval', 1)  # seconds
        self.store_history = config.get('store_history', True)
        self.history_limit = config.get('history_limit', 10000)  # Max bars to store
        self.include_indicators = config.get('include_indicators', True)
        
        # MT5 connector
        if mt5_connector:
            self.connector = mt5_connector
        else:
            mt5_config = config.get('mt5_connector', {})
            self.connector = MT5Connector(mt5_config)
        
        # Data storage
        self.latest_ticks = {}  # Latest tick data by symbol
        self.ohlc_data = {}     # OHLC data by symbol and timeframe
        self.market_depth = {}  # Order book data by symbol
        
        # Thread executor for parallel data fetching
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Map MT5 timeframes to standard format
        self.timeframe_map = {
            'M1': mt5.TIMEFRAME_M1 if mt5 else 1,
            'M5': mt5.TIMEFRAME_M5 if mt5 else 5,
            'M15': mt5.TIMEFRAME_M15 if mt5 else 15,
            'M30': mt5.TIMEFRAME_M30 if mt5 else 30,
            'H1': mt5.TIMEFRAME_H1 if mt5 else 60,
            'H4': mt5.TIMEFRAME_H4 if mt5 else 240,
            'D1': mt5.TIMEFRAME_D1 if mt5 else 1440,
            'W1': mt5.TIMEFRAME_W1 if mt5 else 10080,
            'MN1': mt5.TIMEFRAME_MN1 if mt5 else 43200
        }
        
        # Technical indicators to calculate if enabled
        self.indicators = config.get('indicators', {
            'sma': [5, 10, 20, 50, 100],
            'ema': [9, 21, 55, 200],
            'rsi': [14],
            'macd': [[12, 26, 9]],
            'bollinger': [[20, 2]],
            'atr': [14]
        })
        
        logger.info(f"MT5 data feed initialized for {len(self.trading_pairs)} pairs")
    
    def initialize(self) -> bool:
        """
        Initialize the data feed
        
        Returns:
            True if initialized successfully, False otherwise
        """
        # Ensure connection to MT5
        if not self.connector.connected:
            if not self.connector.connect():
                logger.error("Failed to connect to MT5, data feed initialization failed")
                return False
        
        # Validate symbols
        available_symbols = self.connector.get_symbols()
        invalid_symbols = [s for s in self.trading_pairs if s not in available_symbols]
        if invalid_symbols:
            logger.warning(f"Invalid symbols: {invalid_symbols}. These will be ignored.")
            self.trading_pairs = [s for s in self.trading_pairs if s not in invalid_symbols]
        
        # Initialize data structures for each pair and timeframe
        for pair in self.trading_pairs:
            self.latest_ticks[pair] = None
            self.market_depth[pair] = None
            self.ohlc_data[pair] = {}
            
            for tf in self.timeframes:
                self.ohlc_data[pair][tf] = None
        
        logger.info("MT5 data feed initialized successfully")
        return True
    
    def get_latest_ticks(self, symbols: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        """
        Get latest tick data for specified symbols
        
        Args:
            symbols: List of symbols to get data for, or None for all
        
        Returns:
            Dictionary with symbol as key and tick data DataFrame as value
        """
        if not symbols:
            symbols = self.trading_pairs
        
        if not self.connector.connected:
            if not self.connector.connect():
                logger.error("Failed to connect to MT5, cannot get tick data")
                return {}
        
        result = {}
        
        for symbol in symbols:
            try:
                # Get the last N ticks
                num_ticks = 100  # Get last 100 ticks
                ticks = mt5.copy_ticks_from(symbol, datetime.now() - timedelta(minutes=5),
                                           num_ticks, mt5.COPY_TICKS_ALL)
                
                if ticks is None or len(ticks) == 0:
                    logger.warning(f"No tick data received for {symbol}")
                    continue
                
                # Convert to DataFrame
                ticks_df = pd.DataFrame(ticks)
                
                # Convert time_msc to datetime
                ticks_df['time'] = pd.to_datetime(ticks_df['time_msc'], unit='ms')
                
                # Store and return the result
                self.latest_ticks[symbol] = ticks_df
                result[symbol] = ticks_df
                
            except Exception as e:
                logger.error(f"Error getting tick data for {symbol}: {str(e)}")
        
        return result
    
    def get_ohlc_data(self, 
                    symbols: Optional[List[str]] = None, 
                    timeframes: Optional[List[str]] = None, 
                    num_bars: int = None) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Get OHLC data for specified symbols and timeframes
        
        Args:
            symbols: List of symbols to get data for, or None for all
            timeframes: List of timeframes to get data for, or None for all
            num_bars: Number of bars to fetch, or None for config default
        
        Returns:
            Nested dictionary with symbol and timeframe as keys and OHLC DataFrame as value
        """
        if not symbols:
            symbols = self.trading_pairs
        
        if not timeframes:
            timeframes = self.timeframes
        
        if num_bars is None:
            num_bars = self.max_bars
        
        if not self.connector.connected:
            if not self.connector.connect():
                logger.error("Failed to connect to MT5, cannot get OHLC data")
                return {}
        
        result = {}
        
        # Use ThreadPoolExecutor for parallel fetching
        futures = {}
        
        for symbol in symbols:
            result[symbol] = {}
            
            for tf in timeframes:
                # Skip invalid timeframes
                if tf not in self.timeframe_map:
                    logger.warning(f"Invalid timeframe: {tf}")
                    continue
                
                # Submit task to executor
                future = self.executor.submit(
                    self._fetch_ohlc_data,
                    symbol,
                    tf,
                    num_bars
                )
                
                futures[(symbol, tf)] = future
        
        # Collect results
        for (symbol, tf), future in futures.items():
            try:
                ohlc_df = future.result()
                
                if ohlc_df is not None:
                    result[symbol][tf] = ohlc_df
                    # Store in cache
                    self.ohlc_data[symbol][tf] = ohlc_df
            except Exception as e:
                logger.error(f"Error collecting OHLC data for {symbol} {tf}: {str(e)}")
        
        return result
    
    def _fetch_ohlc_data(self, symbol: str, timeframe: str, num_bars: int) -> Optional[pd.DataFrame]:
        """
        Fetch OHLC data for a single symbol and timeframe
        
        Args:
            symbol: Symbol to fetch data for
            timeframe: Timeframe to fetch data for
            num_bars: Number of bars to fetch
        
        Returns:
            DataFrame with OHLC data or None if error
        """
        try:
            mt5_timeframe = self.timeframe_map.get(timeframe)
            if mt5_timeframe is None:
                logger.warning(f"Unsupported timeframe: {timeframe}")
                return None
            
            # Fetch the OHLCV data
            rates = mt5.copy_rates_from_pos(
                symbol,
                mt5_timeframe,
                0,  # From current position
                num_bars
            )
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No OHLC data received for {symbol} {timeframe}")
                return None
            
            # Convert to DataFrame
            rates_df = pd.DataFrame(rates)
            
            # Convert time to datetime
            rates_df['time'] = pd.to_datetime(rates_df['time'], unit='s')
            
            # Calculate technical indicators if enabled
            if self.include_indicators:
                self._add_indicators(rates_df)
            
            return rates_df
            
        except Exception as e:
            logger.error(f"Error fetching OHLC data for {symbol} {timeframe}: {str(e)}")
            return None
    
    def _add_indicators(self, df: pd.DataFrame) -> None:
        """
        Add technical indicators to DataFrame
        
        Args:
            df: DataFrame with OHLC data
        """
        if len(df) < 250:  # Need enough data for indicators
            return
        
        # Simple Moving Averages
        for period in self.indicators.get('sma', []):
            if len(df) > period:
                df[f'sma_{period}'] = ta.trend.sma_indicator(df['close'], window=period)
        
        # Exponential Moving Averages
        for period in self.indicators.get('ema', []):
            if len(df) > period:
                df[f'ema_{period}'] = ta.trend.ema_indicator(df['close'], window=period)
        
        # RSI
        for period in self.indicators.get('rsi', []):
            if len(df) > period:
                df[f'rsi_{period}'] = ta.momentum.rsi(df['close'], window=period)
        
        # MACD
        for params in self.indicators.get('macd', []):
            if len(params) == 3 and len(df) > max(params):
                fast, slow, signal = params
                macd = ta.trend.MACD(df['close'], window_fast=fast, window_slow=slow, window_sign=signal)
                df[f'macd_line_{fast}_{slow}_{signal}'] = macd.macd()
                df[f'macd_signal_{fast}_{slow}_{signal}'] = macd.macd_signal()
                df[f'macd_hist_{fast}_{slow}_{signal}'] = macd.macd_diff()
        
        # Bollinger Bands
        for params in self.indicators.get('bollinger', []):
            if len(params) == 2 and len(df) > params[0]:
                window, std = params
                bollinger = ta.volatility.BollingerBands(df['close'], window=window, window_dev=std)
                df[f'bb_upper_{window}_{std}'] = bollinger.bollinger_hband()
                df[f'bb_middle_{window}_{std}'] = bollinger.bollinger_mavg()
                df[f'bb_lower_{window}_{std}'] = bollinger.bollinger_lband()
        
        # ATR
        for period in self.indicators.get('atr', []):
            if len(df) > period:
                df[f'atr_{period}'] = ta.volatility.average_true_range(
                    df['high'], df['low'], df['close'], window=period
                )
    
    def get_market_depth(self, symbols: Optional[List[str]] = None, max_depth: int = 10) -> Dict[str, Dict]:
        """
        Get order book data (market depth) for specified symbols
        
        Args:
            symbols: List of symbols to get data for, or None for all
            max_depth: Maximum depth of order book
        
        Returns:
            Dictionary with symbol as key and order book data as value
        """
        if not symbols:
            symbols = self.trading_pairs
        
        if not self.connector.connected:
            if not self.connector.connect():
                logger.error("Failed to connect to MT5, cannot get market depth")
                return {}
        
        result = {}
        
        for symbol in symbols:
            try:
                # Get the order book
                depth = mt5.market_book_get(symbol)
                
                if depth is None or len(depth) == 0:
                    logger.warning(f"No market depth data received for {symbol}")
                    continue
                
                # Process order book data
                bids = []
                asks = []
                
                for item in depth:
                    # Convert named tuple to dict
                    order = item._asdict()
                    
                    if order['type'] in [0, 1]:  # Bid
                        bids.append({
                            'price': order['price'],
                            'volume': order['volume'],
                            'type': 'bid'
                        })
                    elif order['type'] in [2, 3]:  # Ask
                        asks.append({
                            'price': order['price'],
                            'volume': order['volume'],
                            'type': 'ask'
                        })
                
                # Sort and limit depth
                bids = sorted(bids, key=lambda x: x['price'], reverse=True)[:max_depth]
                asks = sorted(asks, key=lambda x: x['price'])[:max_depth]
                
                # Calculate spread
                if asks and bids:
                    spread = asks[0]['price'] - bids[0]['price']
                    spread_pips = round(spread * 10000, 1)  # Assuming 4 decimal places
                else:
                    spread = 0
                    spread_pips = 0
                
                # Store result
                depth_data = {
                    'bids': bids,
                    'asks': asks,
                    'spread': spread,
                    'spread_pips': spread_pips,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.market_depth[symbol] = depth_data
                result[symbol] = depth_data
                
            except Exception as e:
                logger.error(f"Error getting market depth for {symbol}: {str(e)}")
        
        return result
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """
        Get detailed information about a trading symbol
        
        Args:
            symbol: Symbol to get info for
        
        Returns:
            Dictionary with symbol information or None if error
        """
        if not self.connector.connected:
            if not self.connector.connect():
                logger.error("Failed to connect to MT5, cannot get symbol info")
                return None
        
        try:
            # Get symbol information
            symbol_info = mt5.symbol_info(symbol)
            
            if symbol_info is None:
                logger.warning(f"No information received for symbol {symbol}")
                return None
            
            # Convert named tuple to dict
            info_dict = symbol_info._asdict()
            
            # Add computed fields
            info_dict['point_value'] = info_dict.get('point', 0) * info_dict.get('trade_contract_size', 1)
            info_dict['pip_value'] = info_dict.get('point_value', 0) * 10
            
            return info_dict
            
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {str(e)}")
            return None
    
    def update_all_data(self) -> Dict:
        """
        Update all data (ticks, OHLC, market depth) for all symbols
        
        Returns:
            Dictionary with update results
        """
        tick_data = self.get_latest_ticks()
        ohlc_data = self.get_ohlc_data()
        depth_data = self.get_market_depth()
        
        return {
            'tick_data': {symbol: len(df) for symbol, df in tick_data.items()},
            'ohlc_data': {
                symbol: {tf: len(df) for tf, df in timeframes.items()}
                for symbol, timeframes in ohlc_data.items()
            },
            'depth_data': {symbol: (len(data['bids']), len(data['asks'])) for symbol, data in depth_data.items()}
        }
    
    def get_current_prices(self) -> Dict[str, Dict[str, float]]:
        """
        Get current bid/ask prices for all symbols
        
        Returns:
            Dictionary with symbol as key and price information as value
        """
        if not self.connector.connected:
            if not self.connector.connect():
                logger.error("Failed to connect to MT5, cannot get current prices")
                return {}
        
        result = {}
        
        for symbol in self.trading_pairs:
            try:
                # Get the last tick
                tick = mt5.symbol_info_tick(symbol)
                
                if tick is None:
                    logger.warning(f"No tick data received for {symbol}")
                    continue
                
                # Convert named tuple to dict
                tick_dict = tick._asdict()
                
                # Extract prices
                result[symbol] = {
                    'bid': tick_dict.get('bid', 0),
                    'ask': tick_dict.get('ask', 0),
                    'spread': tick_dict.get('ask', 0) - tick_dict.get('bid', 0),
                    'time': datetime.fromtimestamp(tick_dict.get('time', 0)).isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error getting current price for {symbol}: {str(e)}")
        
        return result
