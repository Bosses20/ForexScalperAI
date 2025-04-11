"""
Market data module for fetching real-time forex data
"""

import time
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
import ccxt
import websockets
import json
from typing import Dict, List, Optional, Union

class MarketDataFeed:
    """
    Class for fetching and processing market data from various sources
    Supports both REST API and WebSocket connections for real-time data
    """
    
    def __init__(self, api_config: dict, data_config: dict, trading_pairs: List[str]):
        """
        Initialize the market data feed
        
        Args:
            api_config: Dictionary with API configuration
            data_config: Dictionary with data collection configuration
            trading_pairs: List of currency pairs to monitor
        """
        self.api_config = api_config
        self.data_config = data_config
        self.trading_pairs = trading_pairs
        self.exchange_name = api_config.get('exchange', 'deriv').lower()
        self.demo_mode = api_config.get('demo_mode', True)
        
        # Initialize data storage
        self.latest_ticks = {}
        self.price_history = {}
        self.orderbook_data = {}
        
        # WebSocket connections
        self.ws_connections = {}
        self.is_connected = False
        
        # Initialize exchange connection
        self._initialize_exchange()
        
        logger.info(f"Market data feed initialized for {len(trading_pairs)} pairs on {self.exchange_name}")
    
    def _initialize_exchange(self):
        """Initialize connection to the exchange"""
        try:
            if self.exchange_name in ccxt.exchanges:
                # Use CCXT for standard exchanges
                exchange_class = getattr(ccxt, self.exchange_name)
                
                exchange_params = {
                    'apiKey': self.api_config.get('api_key', ''),
                    'secret': self.api_config.get('api_secret', ''),
                    'enableRateLimit': True,
                }
                
                # Add demo/paper trading if supported and enabled
                if self.demo_mode:
                    if 'options' not in exchange_params:
                        exchange_params['options'] = {}
                    if self.exchange_name == 'binance':
                        exchange_params['options']['defaultType'] = 'future'
                        exchange_params['options']['testnet'] = True
                    elif self.exchange_name == 'oanda':
                        exchange_params['options']['practice'] = True
                
                self.exchange = exchange_class(exchange_params)
                logger.debug(f"Connected to {self.exchange_name} using CCXT")
            
            elif self.exchange_name == 'deriv':
                # Custom implementation for Deriv
                self.exchange = DerivAPI(
                    api_key=self.api_config.get('api_key', ''),
                    demo_mode=self.demo_mode
                )
                logger.debug("Connected to Deriv API")
            
            else:
                raise ValueError(f"Unsupported exchange: {self.exchange_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            raise
    
    async def _connect_websocket(self, pair: str):
        """
        Establish WebSocket connection for real-time data
        
        Args:
            pair: Currency pair to subscribe to
        """
        if self.exchange_name == 'deriv':
            # Deriv-specific WebSocket implementation
            ws_url = "wss://ws.derivws.com/websockets/v3"
            self.ws_connections[pair] = await websockets.connect(ws_url)
            
            # Subscribe to tick data
            subscription_msg = {
                "ticks": pair.replace('/', ''),
                "subscribe": 1
            }
            await self.ws_connections[pair].send(json.dumps(subscription_msg))
            logger.debug(f"Subscribed to {pair} tick data on Deriv")
            
        else:
            # Generic CCXT WebSocket implementation (if supported)
            if hasattr(self.exchange, 'websocket_url'):
                ws_url = self.exchange.websocket_url
                self.ws_connections[pair] = await websockets.connect(ws_url)
                
                # Format subscription message based on exchange
                if self.exchange_name == 'binance':
                    subscription_msg = {
                        "method": "SUBSCRIBE",
                        "params": [f"{pair.lower().replace('/', '')}@ticker"],
                        "id": int(time.time())
                    }
                elif self.exchange_name == 'oanda':
                    subscription_msg = {
                        "type": "SUBSCRIBE",
                        "instruments": [pair.replace('/', '_')]
                    }
                else:
                    subscription_msg = {"subscribe": pair}
                
                await self.ws_connections[pair].send(json.dumps(subscription_msg))
                logger.debug(f"Subscribed to {pair} on {self.exchange_name}")
            else:
                logger.warning(f"WebSocket not supported for {self.exchange_name}")
    
    async def _process_websocket_messages(self):
        """Process incoming WebSocket messages"""
        while self.is_connected:
            for pair, ws in self.ws_connections.items():
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=0.1)
                    data = json.loads(message)
                    
                    # Parse data based on exchange format
                    if self.exchange_name == 'deriv':
                        if 'tick' in data:
                            tick_data = data['tick']
                            self.latest_ticks[pair] = {
                                'timestamp': tick_data['epoch'],
                                'bid': tick_data['bid'],
                                'ask': tick_data['ask'],
                                'last': tick_data['quote'],
                                'volume': 0  # Deriv doesn't provide volume
                            }
                    elif self.exchange_name == 'binance':
                        self.latest_ticks[pair] = {
                            'timestamp': int(time.time()),
                            'bid': float(data['b']),
                            'ask': float(data['a']),
                            'last': float(data['c']),
                            'volume': float(data['v'])
                        }
                    # Add other exchange formats as needed
                    
                    # Update price history
                    self._update_price_history(pair)
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error processing WebSocket message for {pair}: {e}")
    
    def _update_price_history(self, pair: str):
        """
        Update price history for a pair
        
        Args:
            pair: Currency pair to update
        """
        if pair not in self.price_history:
            self.price_history[pair] = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        if pair in self.latest_ticks:
            tick = self.latest_ticks[pair]
            mid_price = (tick['bid'] + tick['ask']) / 2
            
            # Add to price history (simplified, in real implementation would aggregate by timeframe)
            new_row = pd.DataFrame([{
                'timestamp': pd.to_datetime(tick['timestamp'], unit='s'),
                'open': mid_price,
                'high': mid_price,
                'low': mid_price,
                'close': mid_price,
                'volume': tick.get('volume', 0)
            }])
            
            self.price_history[pair] = pd.concat([self.price_history[pair], new_row], ignore_index=True)
            
            # Limit history size
            max_rows = 10000  # Adjust based on memory requirements
            if len(self.price_history[pair]) > max_rows:
                self.price_history[pair] = self.price_history[pair].iloc[-max_rows:]
    
    def connect(self):
        """Connect to data feeds"""
        self.is_connected = True
        
        # Start WebSocket connections if data_config specifies tick_data
        if self.data_config.get('tick_data', False):
            for pair in self.trading_pairs:
                # Start WebSocket in background
                asyncio.create_task(self._connect_websocket(pair))
            
            # Start message processing in background
            asyncio.create_task(self._process_websocket_messages())
            
            logger.info(f"Connected to WebSocket feeds for {len(self.trading_pairs)} pairs")
        
        # Initial data fetch for all pairs
        for pair in self.trading_pairs:
            self._fetch_historical_data(pair)
    
    def disconnect(self):
        """Disconnect from data feeds"""
        self.is_connected = False
        
        # Close all WebSocket connections
        for pair, ws in self.ws_connections.items():
            asyncio.create_task(ws.close())
        
        self.ws_connections = {}
        logger.info("Disconnected from all data feeds")
    
    def _fetch_historical_data(self, pair: str, timeframe: str = '1m', limit: int = 1000):
        """
        Fetch historical OHLCV data for a pair
        
        Args:
            pair: Currency pair
            timeframe: Timeframe for data (1m, 5m, etc.)
            limit: Number of candles to fetch
        """
        try:
            # Convert pair format if needed (some exchanges use different formats)
            formatted_pair = pair
            if self.exchange_name == 'oanda':
                formatted_pair = pair.replace('/', '_')
            
            # Fetch OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(formatted_pair, timeframe, limit=limit)
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Store in price history
            self.price_history[pair] = df
            
            logger.debug(f"Fetched historical data for {pair}: {len(df)} candles")
            
        except Exception as e:
            logger.error(f"Failed to fetch historical data for {pair}: {e}")
    
    def get_latest_data(self) -> Dict[str, pd.DataFrame]:
        """
        Get the latest market data for all pairs
        
        Returns:
            Dictionary with pair as key and DataFrame as value
        """
        # Update data if not using WebSockets
        if not self.data_config.get('tick_data', False):
            for pair in self.trading_pairs:
                self._fetch_historical_data(pair)
        
        return self.price_history
    
    def get_orderbook(self, pair: str, depth: int = 10) -> Dict:
        """
        Get order book data for a specific pair
        
        Args:
            pair: Currency pair
            depth: Depth of the order book
            
        Returns:
            Dictionary with bids and asks
        """
        try:
            orderbook = self.exchange.fetch_order_book(pair, depth)
            self.orderbook_data[pair] = {
                'timestamp': int(time.time()),
                'bids': orderbook['bids'],
                'asks': orderbook['asks']
            }
            return self.orderbook_data[pair]
        except Exception as e:
            logger.error(f"Failed to fetch order book for {pair}: {e}")
            return {}


class DerivAPI:
    """
    Custom implementation for Deriv API
    """
    
    def __init__(self, api_key: str = '', demo_mode: bool = True):
        """
        Initialize Deriv API connection
        
        Args:
            api_key: API key for Deriv
            demo_mode: If True, use demo account
        """
        self.api_key = api_key
        self.demo_mode = demo_mode
        self.app_id = 1089  # Example app ID, replace with your own
        
        logger.debug(f"Initialized Deriv API in {'demo' if demo_mode else 'live'} mode")
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 1000) -> List:
        """
        Fetch historical OHLCV data
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            limit: Number of candles
            
        Returns:
            List of OHLCV data
        """
        # This would typically make an API call to Deriv
        # For now, we'll return simulated data
        
        end_time = int(time.time())
        
        # Map timeframe to seconds
        timeframe_seconds = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }
        
        interval = timeframe_seconds.get(timeframe, 60)
        start_time = end_time - (interval * limit)
        
        # Generate simulated data
        ohlcv_data = []
        for i in range(limit):
            timestamp = (start_time + i * interval) * 1000  # Convert to milliseconds
            
            # Generate random but realistic price data
            base_price = 1.1000 + np.random.normal(0, 0.0005)  # For EUR/USD example
            open_price = base_price
            high_price = base_price * (1 + abs(np.random.normal(0, 0.0003)))
            low_price = base_price * (1 - abs(np.random.normal(0, 0.0003)))
            close_price = base_price * (1 + np.random.normal(0, 0.0002))
            volume = np.random.randint(50, 200)
            
            ohlcv_data.append([timestamp, open_price, high_price, low_price, close_price, volume])
        
        return ohlcv_data
    
    def fetch_order_book(self, symbol: str, limit: int = 10) -> Dict:
        """
        Fetch order book data
        
        Args:
            symbol: Trading symbol
            limit: Depth of the order book
            
        Returns:
            Dictionary with bids and asks
        """
        # Simulated order book data for testing
        base_price = 1.1000  # Example for EUR/USD
        
        # Generate random but realistic bids and asks
        bids = []
        asks = []
        
        for i in range(limit):
            bid_price = base_price - (i * 0.0001) - np.random.uniform(0, 0.00005)
            bid_volume = np.random.uniform(0.5, 5.0)
            bids.append([bid_price, bid_volume])
            
            ask_price = base_price + (i * 0.0001) + np.random.uniform(0, 0.00005)
            ask_volume = np.random.uniform(0.5, 5.0)
            asks.append([ask_price, ask_volume])
        
        return {
            'bids': bids,
            'asks': asks,
            'timestamp': int(time.time() * 1000),
            'datetime': datetime.utcnow().isoformat(),
            'symbol': symbol
        }
