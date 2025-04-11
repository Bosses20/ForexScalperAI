"""
Instrument Manager for MT5 Trading Bot
Manages trading instruments including forex pairs and synthetic indices
Handles instrument-specific properties, trading hours, and characteristics
"""

import re
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, time
import pytz
from loguru import logger
import pandas as pd


class InstrumentManager:
    """
    Manages trading instruments, their properties, and schedule
    Provides specialized handling for different instrument types
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the instrument manager with configuration
        
        Args:
            config: Configuration dictionary containing instrument settings
        """
        self.config = config
        self.trading_config = config.get('trading', {})
        
        # Initialize instrument collections
        self.forex_instruments = []
        self.synthetic_instruments = []
        self.all_instruments = []
        
        # Load instruments from config
        self._load_instruments()
        
        # Initialize trading sessions
        self.trading_sessions = self.trading_config.get('trade_session_hours', {})
        
        logger.info(f"Instrument Manager initialized with {len(self.all_instruments)} instruments")

    def _load_instruments(self):
        """Load and validate instruments from configuration"""
        symbols_config = self.trading_config.get('symbols', {})
        
        # Load forex instruments
        if 'forex' in symbols_config:
            for instrument in symbols_config['forex']:
                self.forex_instruments.append(instrument)
                self.all_instruments.append(instrument)
                logger.debug(f"Loaded forex instrument: {instrument['name']}")
        
        # Load synthetic instruments
        if 'synthetic' in symbols_config:
            for instrument in symbols_config['synthetic']:
                self.synthetic_instruments.append(instrument)
                self.all_instruments.append(instrument)
                logger.debug(f"Loaded synthetic instrument: {instrument['name']}")
    
    def get_instrument_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific instrument
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            Dictionary with instrument details or None if not found
        """
        for instrument in self.all_instruments:
            if instrument['name'] == symbol:
                return instrument
        return None
    
    def get_instrument_type(self, symbol: str) -> str:
        """
        Determine the type of instrument (forex, synthetic)
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            Instrument type as string
        """
        instrument = self.get_instrument_details(symbol)
        if instrument:
            return instrument.get('type', 'unknown')
        
        # If not found in our configuration, try to detect type from name
        if any(pair in symbol for pair in ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD']):
            return 'forex'
        elif any(term in symbol for term in ['Volatility', 'Crash', 'Boom', 'Step', 'Jump']):
            return 'synthetic'
        
        return 'unknown'
    
    def get_synthetic_subtype(self, symbol: str) -> Optional[str]:
        """
        For synthetic indices, determine the specific subtype
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            Subtype as string or None if not applicable
        """
        instrument = self.get_instrument_details(symbol)
        if instrument and instrument.get('type') == 'synthetic':
            return instrument.get('sub_type')
        
        # If not found in our configuration, try to detect from name
        symbol_lower = symbol.lower()
        
        if 'volatility' in symbol_lower or 'vol' in symbol_lower:
            return 'volatility'
        elif 'crash' in symbol_lower:
            return 'crash_boom'
        elif 'boom' in symbol_lower:
            return 'crash_boom'
        elif 'step' in symbol_lower:
            return 'step'
        elif 'jump' in symbol_lower:
            return 'jump'
            
        return None
    
    def is_trading_active(self, symbol: str) -> bool:
        """
        Check if trading should be active for this instrument based on current time
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            Boolean indicating if trading is active
        """
        instrument_type = self.get_instrument_type(symbol)
        
        # Synthetic indices can be traded 24/7
        if instrument_type == 'synthetic':
            return True
        
        # For forex, check if current time is within trading sessions
        if instrument_type == 'forex':
            current_hour = datetime.now(pytz.UTC).hour
            
            # Get forex trading sessions
            forex_sessions = self.trading_sessions.get('forex', [])
            
            # Check if current time falls within any active session
            for session in forex_sessions:
                start_hour, end_hour = session.get('hours', [0, 24])
                if start_hour <= current_hour < end_hour:
                    return True
            
            return False
        
        # Default to active if unknown
        return True
    
    def get_all_active_instruments(self) -> List[Dict[str, Any]]:
        """
        Get all instruments that are currently active for trading
        
        Returns:
            List of active instrument details
        """
        active_instruments = []
        
        for instrument in self.all_instruments:
            symbol = instrument['name']
            if self.is_trading_active(symbol):
                active_instruments.append(instrument)
        
        return active_instruments
    
    def get_all_forex_pairs(self) -> List[str]:
        """Get list of all forex pair symbols"""
        return [instrument['name'] for instrument in self.forex_instruments]
    
    def get_all_synthetic_indices(self) -> List[str]:
        """Get list of all synthetic index symbols"""
        return [instrument['name'] for instrument in self.synthetic_instruments]
    
    def get_min_lot_size(self, symbol: str) -> float:
        """
        Get minimum lot size for an instrument
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            Minimum lot size as float
        """
        instrument_type = self.get_instrument_type(symbol)
        
        if instrument_type == 'forex':
            return 0.01  # Standard minimum lot size for forex
        
        if instrument_type == 'synthetic':
            sub_type = self.get_synthetic_subtype(symbol)
            
            if sub_type == 'volatility':
                return 0.05
            elif sub_type == 'crash_boom':
                if 'crash_300' in symbol.lower():
                    return 0.5
                elif 'boom_300' in symbol.lower():
                    return 1.0
                else:
                    return 0.2  # Default for other crash/boom indices
            elif sub_type == 'step':
                return 0.01
            elif sub_type == 'jump':
                return 0.01
                
            # Default for unknown synthetic index
            return 0.01
            
        # Default fallback
        return 0.01
