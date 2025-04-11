"""
Session Manager
Manages trading sessions and instrument rotation based on time of day
"""

from datetime import datetime, time, timedelta
import pytz
from typing import Dict, List, Set, Tuple, Optional
from loguru import logger

class SessionManager:
    """
    Manages trading sessions and instrument rotation based on market hours
    Enables intelligent switching between forex and synthetic indices
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize the session manager
        
        Args:
            config: Configuration dictionary with session settings
        """
        self.config = config or {}
        
        # Default trading sessions
        self.default_sessions = {
            'sydney': {
                'start': time(22, 0),  # 22:00 UTC
                'end': time(7, 0),     # 07:00 UTC
                'timezone': 'UTC'
            },
            'tokyo': {
                'start': time(0, 0),   # 00:00 UTC
                'end': time(9, 0),     # 09:00 UTC
                'timezone': 'UTC'
            },
            'london': {
                'start': time(8, 0),   # 08:00 UTC
                'end': time(17, 0),    # 17:00 UTC
                'timezone': 'UTC'
            },
            'newyork': {
                'start': time(13, 0),  # 13:00 UTC
                'end': time(22, 0),    # 22:00 UTC
                'timezone': 'UTC'
            }
        }
        
        # Load sessions from config
        self.sessions = self.config.get('trading_sessions', self.default_sessions)
        
        # Session overlaps (high liquidity periods)
        self.session_overlaps = {
            'tokyo_london': {
                'start': time(8, 0),   # 08:00 UTC
                'end': time(9, 0),     # 09:00 UTC
                'timezone': 'UTC'
            },
            'london_newyork': {
                'start': time(13, 0),  # 13:00 UTC
                'end': time(17, 0),    # 17:00 UTC
                'timezone': 'UTC'
            }
        }
        
        # Load rotation settings
        self.rotation_settings = self.config.get('rotation_settings', {
            'enabled': True,
            'prefer_forex_in_session_overlaps': True,
            'prefer_synthetics_in_low_liquidity': True,
            'low_liquidity_periods': [
                {'start': time(22, 0), 'end': time(0, 0)},  # Between NY close and Tokyo open
                {'start': time(9, 0), 'end': time(13, 0)}   # Between Tokyo close and NY open
            ],
            # Liquidity score weights for decision making
            'weights': {
                'session_activity': 0.7,      # Weight for session activity
                'volatility': 0.15,           # Weight for current volatility
                'spread': 0.15                # Weight for current spread
            },
            # Threshold for switching from forex to synthetic
            'liquidity_threshold': 0.4
        })
        
        # Initialize session status
        self.current_active_sessions = set()
        self.current_overlaps = set()
        self.is_low_liquidity_period = False
        self.last_update_time = None
        
        # Initialize forex pairs by session preference
        self.forex_by_session = {
            'sydney': ['AUDUSD', 'NZDUSD', 'AUDJPY', 'EURAUD', 'AUDCAD'],
            'tokyo': ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY', 'CADJPY'],
            'london': ['EURUSD', 'GBPUSD', 'EURGBP', 'USDCHF', 'EURJPY'],
            'newyork': ['EURUSD', 'GBPUSD', 'USDCAD', 'USDCHF', 'USDJPY']
        }
        
        # Synthetic indices always active
        self.synthetic_indices = {
            'volatility': ['Volatility 10 Index', 'Volatility 25 Index', 'Volatility 50 Index', 
                         'Volatility 75 Index', 'Volatility 100 Index'],
            'crash_boom': ['Crash 300 Index', 'Crash 500 Index', 'Crash 1000 Index',
                         'Boom 300 Index', 'Boom 500 Index', 'Boom 1000 Index'],
            'step': ['Step Index'],
            'jump': ['Jump 10 Index', 'Jump 25 Index', 'Jump 50 Index', 'Jump 75 Index', 'Jump 100 Index']
        }
        
        # Update to current session status
        self.update_session_status()
        
        logger.info("Session Manager initialized")
    
    def update_session_status(self, current_time: datetime = None) -> None:
        """
        Update the current session status based on time
        
        Args:
            current_time: Current time (default: datetime.now(pytz.UTC))
        """
        if current_time is None:
            current_time = datetime.now(pytz.UTC)
        
        # Extract current time components
        current_time_utc = current_time.time()
        
        # Check which sessions are active
        active_sessions = set()
        for session_name, session_times in self.sessions.items():
            session_start = session_times['start']
            session_end = session_times['end']
            
            # Handle sessions that span midnight
            if session_start > session_end:
                is_active = current_time_utc >= session_start or current_time_utc < session_end
            else:
                is_active = session_start <= current_time_utc < session_end
            
            if is_active:
                active_sessions.add(session_name)
        
        # Check for session overlaps
        active_overlaps = set()
        for overlap_name, overlap_times in self.session_overlaps.items():
            overlap_start = overlap_times['start']
            overlap_end = overlap_times['end']
            
            # Handle overlaps that span midnight
            if overlap_start > overlap_end:
                is_active = current_time_utc >= overlap_start or current_time_utc < overlap_end
            else:
                is_active = overlap_start <= current_time_utc < overlap_end
            
            if is_active:
                active_overlaps.add(overlap_name)
        
        # Check for low liquidity periods
        is_low_liquidity = False
        for period in self.rotation_settings['low_liquidity_periods']:
            period_start = period['start']
            period_end = period['end']
            
            # Handle periods that span midnight
            if period_start > period_end:
                is_active = current_time_utc >= period_start or current_time_utc < period_end
            else:
                is_active = period_start <= current_time_utc < period_end
            
            if is_active:
                is_low_liquidity = True
                break
        
        # Update status
        self.current_active_sessions = active_sessions
        self.current_overlaps = active_overlaps
        self.is_low_liquidity_period = is_low_liquidity
        self.last_update_time = current_time
        
        session_str = ", ".join(active_sessions) if active_sessions else "None"
        overlap_str = ", ".join(active_overlaps) if active_overlaps else "None"
        
        logger.debug(f"Session status updated - Active sessions: {session_str}, " +
                    f"Overlaps: {overlap_str}, Low liquidity: {is_low_liquidity}")
    
    def get_active_instruments(self, 
                             market_data: Dict = None, 
                             account_balance: float = None) -> Dict[str, List[str]]:
        """
        Get the active instruments based on current session and market conditions
        
        Args:
            market_data: Optional dictionary with market data for liquidity scoring
            account_balance: Optional account balance for balance-based decisions
            
        Returns:
            Dictionary with 'forex' and 'synthetic' keys containing lists of active instruments
        """
        # Update session status if needed
        if self.last_update_time is None or (datetime.now(pytz.UTC) - self.last_update_time).seconds > 300:
            self.update_session_status()
        
        # Decide which instruments to activate based on session
        # Always include synthetic indices
        all_synthetic = []
        for indices in self.synthetic_indices.values():
            all_synthetic.extend(indices)
        
        # Get session appropriate forex pairs
        forex_pairs = set()
        if self.current_active_sessions:
            for session in self.current_active_sessions:
                pairs = self.forex_by_session.get(session, [])
                forex_pairs.update(pairs)
        
        # Session-based liquidity score (0-1)
        forex_liquidity_score = 0.0
        
        # Boost score for session overlaps (high liquidity)
        if self.current_overlaps and self.rotation_settings['prefer_forex_in_session_overlaps']:
            forex_liquidity_score = 0.8  # High liquidity during overlaps
        
        # Reduce score during low liquidity periods
        elif self.is_low_liquidity_period and self.rotation_settings['prefer_synthetics_in_low_liquidity']:
            forex_liquidity_score = 0.2  # Low liquidity
        
        # Normal session without overlap
        elif self.current_active_sessions:
            forex_liquidity_score = 0.6  # Medium liquidity during normal sessions
        
        # No active session
        else:
            forex_liquidity_score = 0.3  # Low-medium liquidity outside sessions
        
        # Additional market data based adjustments
        if market_data:
            # TODO: Adjust liquidity score based on spreads, volatility, etc.
            pass
        
        # Decision: which instruments to trade based on liquidity
        threshold = self.rotation_settings['liquidity_threshold']
        
        if forex_liquidity_score >= threshold:
            # Good forex liquidity - trade both but more forex
            synthetic_ratio = 1.0 - forex_liquidity_score
            
            # Determine how many synthetic indices to include based on ratio
            synthetic_count = max(1, int(len(all_synthetic) * synthetic_ratio))
            selected_synthetic = all_synthetic[:synthetic_count]
            
            return {
                'forex': list(forex_pairs),
                'synthetic': selected_synthetic
            }
        else:
            # Poor forex liquidity - trade more synthetic indices
            forex_ratio = forex_liquidity_score / threshold
            
            # Determine how many forex pairs to include based on ratio
            forex_count = max(1, int(len(forex_pairs) * forex_ratio))
            selected_forex = list(forex_pairs)[:forex_count]
            
            return {
                'forex': selected_forex,
                'synthetic': all_synthetic
            }
    
    def get_best_trading_hours(self, symbol: str) -> List[Dict]:
        """
        Get the best trading hours for a specific instrument
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            List of dictionaries with 'start' and 'end' times in UTC
        """
        # Synthetic indices can be traded 24/7
        for category, symbols in self.synthetic_indices.items():
            if symbol in symbols:
                return [{'start': time(0, 0), 'end': time(23, 59)}]
        
        # For forex pairs, determine the best sessions
        best_sessions = []
        
        # Find which sessions this pair is active in
        active_sessions = []
        for session, pairs in self.forex_by_session.items():
            if symbol in pairs:
                active_sessions.append(session)
        
        # If no specific sessions, use major sessions
        if not active_sessions:
            active_sessions = ['london', 'newyork']
        
        # Get session times
        for session in active_sessions:
            if session in self.sessions:
                best_sessions.append({
                    'start': self.sessions[session]['start'],
                    'end': self.sessions[session]['end']
                })
        
        # Also add overlap periods
        for overlap, times in self.session_overlaps.items():
            best_sessions.append({
                'start': times['start'],
                'end': times['end']
            })
        
        return best_sessions
    
    def get_session_summary(self) -> Dict:
        """
        Get summary of current session status
        
        Returns:
            Dictionary with session information
        """
        current_time = datetime.now(pytz.UTC)
        
        # Update if needed
        if self.last_update_time is None or (current_time - self.last_update_time).seconds > 300:
            self.update_session_status(current_time)
        
        # Format status information
        active_sessions = list(self.current_active_sessions)
        active_overlaps = list(self.current_overlaps)
        
        # Time until next session starts/ends
        next_session_change = self._calculate_next_session_change(current_time)
        
        # Get recommended instrument types for current session
        recommended_instruments = self.get_active_instruments()
        
        return {
            'current_time_utc': current_time.strftime('%H:%M:%S UTC'),
            'active_sessions': active_sessions,
            'active_overlaps': active_overlaps,
            'is_low_liquidity': self.is_low_liquidity_period,
            'next_session_change': next_session_change,
            'forex_pairs_count': len(recommended_instruments['forex']),
            'synthetic_indices_count': len(recommended_instruments['synthetic']),
            'trading_focus': 'Forex' if len(recommended_instruments['forex']) > len(recommended_instruments['synthetic']) 
                            else 'Synthetic Indices'
        }
    
    def _calculate_next_session_change(self, current_time: datetime) -> Dict:
        """Calculate time until next session start/end"""
        current_time_utc = current_time.time()
        
        # Collect all session transition times
        transitions = []
        
        for session_name, session_times in self.sessions.items():
            start = session_times['start']
            end = session_times['end']
            
            # Add session start and end to transitions
            transitions.append(('start', session_name, start))
            transitions.append(('end', session_name, end))
        
        # Find next transition
        next_transition = None
        min_time_delta = timedelta(days=1)
        
        for transition_type, session_name, transition_time in transitions:
            # Convert current time and transition time to datetime for comparison
            current_dt = datetime.combine(current_time.date(), current_time_utc)
            transition_dt = datetime.combine(current_time.date(), transition_time)
            
            # If transition is in the past, add a day
            if transition_dt <= current_dt:
                transition_dt += timedelta(days=1)
            
            # Calculate time until transition
            time_until = transition_dt - current_dt
            
            # Update if this is the next transition
            if time_until < min_time_delta:
                min_time_delta = time_until
                next_transition = {
                    'type': transition_type,
                    'session': session_name,
                    'time': transition_time.strftime('%H:%M UTC'),
                    'minutes_until': int(time_until.total_seconds() / 60)
                }
        
        return next_transition
