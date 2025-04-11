"""
Risk Management module for forex trading
Implements advanced risk control algorithms to protect trading capital
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from loguru import logger
import math

class RiskManager:
    """
    Risk management system that controls position sizing, 
    maximum exposure, and implements circuit breakers
    """
    
    def __init__(self, risk_config: dict):
        """
        Initialize the risk management system
        
        Args:
            risk_config: Dictionary with risk management parameters
        """
        self.config = risk_config
        self.max_risk_per_trade = risk_config.get('max_risk_per_trade', 0.01)  # Default 1%
        self.max_daily_risk = risk_config.get('max_daily_risk', 0.05)  # Default 5%
        self.max_drawdown_percent = risk_config.get('max_drawdown_percent', 0.15)  # Default 15%
        
        # Account-based position sizing tiers
        self.account_tiers = {
            'nano': {'min_balance': 0, 'max_balance': 100, 'max_lot': 0.01, 'risk_percent': 0.01, 'max_trades': 1},
            'micro': {'min_balance': 101, 'max_balance': 500, 'max_lot': 0.01, 'risk_percent': 0.02, 'max_trades': 3},
            'mini': {'min_balance': 501, 'max_balance': 2000, 'max_lot': 0.05, 'risk_percent': 0.015, 'max_trades': 5},
            'standard': {'min_balance': 2001, 'max_balance': 10000, 'max_lot': 0.2, 'risk_percent': 0.01, 'max_trades': 7},
            'professional': {'min_balance': 10001, 'max_balance': float('inf'), 'max_lot': 1.0, 'risk_percent': 0.005, 'max_trades': 10}
        }
        
        # Minimum lot size requirements by instrument type
        self.min_lot_sizes = {
            # Standard forex pairs
            'forex': 0.01,
            
            # Deriv synthetic indices
            'synthetic': {
                'default': 0.01,
                'volatility': 0.05,  # Volatility indices
                'crash_boom': {
                    'default': 0.2,  # Default for Crash/Boom indices
                    'boom_300': 1.0,
                    'crash_300': 0.5,
                    'boom_500': 0.2,
                    'crash_500': 0.2,
                    'boom_1000': 0.2,
                    'crash_1000': 0.2
                },
                'jump': {
                    'default': 0.01,
                    'jump_10': 0.01,
                    'jump_25': 0.01,
                    'jump_50': 0.01,
                    'jump_75': 0.01,
                    'jump_100': 0.01
                }
            }
        }
        
        # Risk control parameters
        self.max_correlation_exposure = risk_config.get('max_correlation_exposure', 2)  # Max trades in correlated pairs
        self.max_spread_multiplier = risk_config.get('max_spread_multiplier', 1.5)  # Max spread as multiplier of average
        self.max_slippage_pips = risk_config.get('max_slippage_pips', 2)  # Max allowed slippage in pips
        self.position_aging_hours = risk_config.get('position_aging_hours', 2)  # Close trades after this many hours
        
        # Track active trades and performance metrics
        self.active_trades = {}
        self.trading_disabled = False
        self.trading_disabled_reason = None
        
        # Performance tracking
        self.starting_balance = None
        self.current_balance = None
        self.highest_balance = None
        self.daily_pnl = {}
        self.trade_history = []
        
        # Track average spreads for each pair
        self.average_spreads = {}
        
        # Track correlated pairs
        self.correlated_pairs = {
            'EUR/USD': ['EUR/GBP', 'EUR/JPY', 'EUR/CHF', 'EUR/AUD'],
            'GBP/USD': ['GBP/JPY', 'GBP/CHF', 'EUR/GBP'],
            'USD/JPY': ['EUR/JPY', 'GBP/JPY', 'AUD/JPY', 'CHF/JPY'],
            'AUD/USD': ['AUD/JPY', 'AUD/NZD', 'AUD/CAD', 'EUR/AUD'],
            'USD/CHF': ['EUR/CHF', 'GBP/CHF', 'CHF/JPY'],
            'USD/CAD': ['CAD/JPY', 'AUD/CAD', 'NZD/CAD'],
            'NZD/USD': ['AUD/NZD', 'NZD/JPY', 'NZD/CAD']
        }
        
        logger.info(f"Risk manager initialized with max risk per trade: {self.max_risk_per_trade*100}%")
    
    def _get_account_tier(self, balance: float) -> dict:
        """
        Determine the account tier based on balance
        
        Args:
            balance: Current account balance
            
        Returns:
            Dictionary with tier parameters
        """
        for tier_name, tier_params in self.account_tiers.items():
            if tier_params['min_balance'] <= balance <= tier_params['max_balance']:
                logger.info(f"Account classified as {tier_name} tier (balance: {balance})")
                return tier_params
        
        # If no tier matches (unlikely with the infinity upper bound), use the professional tier
        return self.account_tiers['professional']
    
    def update_account_balance(self, balance: float):
        """
        Update the current account balance
        
        Args:
            balance: Current account balance
        """
        if self.starting_balance is None:
            self.starting_balance = balance
            self.highest_balance = balance
        
        self.current_balance = balance
        
        if balance > self.highest_balance:
            self.highest_balance = balance
        
        # Check for drawdown circuit breaker
        self._check_drawdown()
    
    def calculate_position_size(self, signal: Dict, account_balance: Optional[float] = None) -> float:
        """
        Calculate the appropriate position size based on risk parameters
        
        Args:
            signal: Signal dictionary with pair, price, stop_loss, etc.
            account_balance: Current account balance (optional)
            
        Returns:
            Position size in standard lots (1.0 = 100,000 units)
        """
        if self.trading_disabled:
            logger.warning(f"Trading disabled: {self.trading_disabled_reason}")
            return 0.0
        
        # Use provided balance or current balance
        balance = account_balance if account_balance is not None else self.current_balance
        
        if balance is None:
            logger.error("Cannot calculate position size: account balance not set")
            return 0.0
        
        # Check if risk limit reached
        if self._daily_risk_limit_reached():
            logger.warning("Daily risk limit reached, reducing position to zero")
            return 0.0
        
        # Extract values from signal
        pair = signal['pair']
        entry_price = signal['price']
        stop_loss = signal['stop_loss']
        instrument_type = signal.get('instrument_type', 'forex')  # Default to forex if not specified
        
        # Calculate risk amount
        risk_amount = balance * self.max_risk_per_trade
        
        # Calculate pip value based on pair
        is_jpy_pair = 'JPY' in pair
        pip_value = 0.01 if is_jpy_pair else 0.0001
        
        # Calculate stop loss distance in pips
        stop_distance_raw = abs(entry_price - stop_loss)
        stop_distance_pips = stop_distance_raw / pip_value
        
        # Calculate pip value for standard lot
        # This is a simplified calculation and would need to be adjusted for different currency pairs
        # and account currency
        standard_lot_size = 100000  # 1 standard lot = 100,000 units
        
        # For a standard account in USD, approximate pip values:
        # - Most pairs: ~$10 per pip per standard lot
        # - JPY pairs: ~$10 per pip per standard lot
        pip_value_per_standard_lot = 10  # $10 per pip for a standard lot
        
        # Calculate position size in standard lots
        position_size = risk_amount / (stop_distance_pips * pip_value_per_standard_lot)
        
        # Get the minimum lot size for this instrument
        min_lot = self._get_min_lot_size(pair, instrument_type)
        
        # Apply minimum and maximum constraints
        max_lot = self._get_account_tier(balance)['max_lot']
        
        position_size = max(min_lot, min(position_size, max_lot))
        position_size = round(position_size, 2)  # Round to 2 decimal places
        
        logger.info(f"Calculated position size for {pair}: {position_size} lots, "
                   f"risking {self.max_risk_per_trade*100:.1f}% of balance ({risk_amount:.2f})")
        
        return position_size
    
    def _get_min_lot_size(self, pair: str, instrument_type: str) -> float:
        """
        Get the minimum lot size for a specific instrument
        
        Args:
            pair: Trading pair or instrument name
            instrument_type: Type of instrument (forex, synthetic, etc)
            
        Returns:
            Minimum lot size for the instrument
        """
        # Handle standard forex pairs
        if instrument_type == 'forex':
            return self.min_lot_sizes['forex']
        
        # Handle synthetic indices
        if instrument_type == 'synthetic':
            # Process pair name to identify the specific synthetic index
            pair_lower = pair.lower()
            
            # Check if it's a volatility index
            if 'volatility' in pair_lower or 'vol' in pair_lower:
                return self.min_lot_sizes['synthetic']['volatility']
            
            # Check if it's a crash index
            if 'crash' in pair_lower:
                # Check specific crash index
                if '300' in pair_lower:
                    return self.min_lot_sizes['synthetic']['crash_boom']['crash_300']
                elif '500' in pair_lower:
                    return self.min_lot_sizes['synthetic']['crash_boom']['crash_500']
                elif '1000' in pair_lower:
                    return self.min_lot_sizes['synthetic']['crash_boom']['crash_1000']
                else:
                    return self.min_lot_sizes['synthetic']['crash_boom']['default']
            
            # Check if it's a boom index
            if 'boom' in pair_lower:
                # Check specific boom index
                if '300' in pair_lower:
                    return self.min_lot_sizes['synthetic']['crash_boom']['boom_300']
                elif '500' in pair_lower:
                    return self.min_lot_sizes['synthetic']['crash_boom']['boom_500']
                elif '1000' in pair_lower:
                    return self.min_lot_sizes['synthetic']['crash_boom']['boom_1000']
                else:
                    return self.min_lot_sizes['synthetic']['crash_boom']['default']
            
            # Check if it's a jump index
            if 'jump' in pair_lower:
                # Extract the jump number if present
                for key in self.min_lot_sizes['synthetic']['jump']:
                    if key in pair_lower:
                        return self.min_lot_sizes['synthetic']['jump'][key]
                return self.min_lot_sizes['synthetic']['jump']['default']
            
            # Default for other synthetic indices
            return self.min_lot_sizes['synthetic']['default']
        
        # Default for unknown instrument types
        logger.warning(f"Unknown instrument type: {instrument_type}, using forex minimum lot size")
        return self.min_lot_sizes['forex']

    def get_account_tier(self, balance: float) -> str:
        """
        Get the current account tier name based on balance
        
        Args:
            balance: Account balance
            
        Returns:
            Account tier name
        """
        for tier_name, tier_params in self.account_tiers.items():
            if tier_params['min_balance'] <= balance <= tier_params['max_balance']:
                return tier_name
        
        return 'professional'  # Default to professional if no match found
    
    def validate_trade(self, signal: Dict, position_size: float) -> bool:
        """
        Validate if a trade should be executed based on risk parameters
        
        Args:
            signal: Signal dictionary
            position_size: Calculated position size
            
        Returns:
            True if trade should be executed
        """
        if self.trading_disabled:
            logger.warning(f"Trade rejected: trading disabled - {self.trading_disabled_reason}")
            return False
        
        # Check position size
        if position_size <= 0:
            logger.warning("Trade rejected: position size too small")
            return False
        
        # Check if we can accept more trades
        pair = signal['pair']
        if pair in self.active_trades:
            logger.warning(f"Trade rejected: already have active trade for {pair}")
            return False
        
        # Check maximum open positions based on account tier
        if self.current_balance:
            account_tier = self._get_account_tier(self.current_balance)
            max_open_positions = account_tier['max_trades']
            if len(self.active_trades) >= max_open_positions:
                logger.warning(f"Trade rejected: maximum number of positions reached ({max_open_positions})")
                return False
        
        # Check spread if available
        if 'spread' in signal:
            current_spread = signal['spread']
            avg_spread = self.average_spreads.get(pair)
            
            if avg_spread and current_spread > (avg_spread * self.max_spread_multiplier):
                logger.warning(f"Trade rejected: current spread ({current_spread}) exceeds {self.max_spread_multiplier}x average ({avg_spread})")
                return False
        
        # Check correlation control - limit exposure to correlated pairs
        if pair in self.correlated_pairs:
            correlated_group = [pair] + self.correlated_pairs[pair]
            active_correlated = [p for p in self.active_trades.keys() if p in correlated_group]
            
            if len(active_correlated) >= self.max_correlation_exposure:
                logger.warning(f"Trade rejected: maximum correlated exposure reached for {pair} group")
                return False
        
        # Check slippage tolerance if entry mode is 'market'
        if signal.get('entry_type') == 'market' and 'max_slippage' not in signal:
            signal['max_slippage'] = self.max_slippage_pips
        
        return True
    
    def update_spread_data(self, pair: str, current_spread: float):
        """
        Update the average spread data for a pair
        
        Args:
            pair: Currency pair
            current_spread: Current spread in pips
        """
        if pair not in self.average_spreads:
            self.average_spreads[pair] = current_spread
        else:
            # Exponential moving average with 0.95 weight to previous value
            self.average_spreads[pair] = (0.95 * self.average_spreads[pair]) + (0.05 * current_spread)
    
    def register_trade(self, trade: Dict):
        """
        Register a new trade in the risk management system
        
        Args:
            trade: Dictionary with trade details
        """
        pair = trade['pair']
        
        if pair in self.active_trades:
            logger.warning(f"Trade already exists for {pair}, updating")
        
        # Ensure trade has entry time
        if 'entry_time' not in trade:
            trade['entry_time'] = datetime.now()
            
        # Add trade aging information
        trade['expiry_time'] = trade['entry_time'] + timedelta(hours=self.position_aging_hours)
        
        # Initialize trailing stop if not present
        if 'trailing_stop_enabled' not in trade:
            trade['trailing_stop_enabled'] = False
            
        self.active_trades[pair] = trade
        logger.info(f"Registered new trade for {pair} at {trade['entry_price']}")
        
    def apply_stop_loss_strategy(self, signal: Dict, stop_loss_strategy: str = 'fixed', atr_value: Optional[float] = None) -> float:
        """
        Calculate stop loss level based on the chosen strategy
        
        Args:
            signal: Signal dictionary with pair, price, direction
            stop_loss_strategy: Strategy to use ('fixed', 'atr', 'structure')
            atr_value: ATR value if using ATR-based stop loss
            
        Returns:
            Stop loss price
        """
        pair = signal['pair']
        entry_price = signal['price']
        direction = 1 if signal['direction'] == 'buy' else -1
        
        # Get pip value for this pair
        is_jpy_pair = 'JPY' in pair
        pip_value = 0.01 if is_jpy_pair else 0.0001
        
        if stop_loss_strategy == 'fixed':
            # Fixed stop loss - default 15 pips
            fixed_sl_pips = signal.get('fixed_sl_pips', 15)
            stop_loss = entry_price - (direction * fixed_sl_pips * pip_value)
            
        elif stop_loss_strategy == 'atr' and atr_value:
            # ATR-based stop loss - default 1.5 * ATR
            atr_multiplier = signal.get('atr_multiplier', 1.5)
            stop_loss = entry_price - (direction * atr_multiplier * atr_value)
            
        elif stop_loss_strategy == 'structure' and 'structure_level' in signal:
            # Support/Resistance based stop loss
            stop_loss = signal['structure_level']
            # Add small buffer to avoid exact level
            buffer_pips = 3
            buffer_amount = buffer_pips * pip_value
            # Adjust buffer direction based on trade direction
            if direction == 1:  # Buy
                stop_loss -= buffer_amount
            else:  # Sell
                stop_loss += buffer_amount
        else:
            # Default to fixed stop loss if strategy invalid or missing parameters
            default_sl_pips = 15
            stop_loss = entry_price - (direction * default_sl_pips * pip_value)
            logger.warning(f"Using default fixed stop loss for {pair} due to invalid strategy or missing parameters")
            
        logger.info(f"Calculated stop loss for {pair} using {stop_loss_strategy} strategy: {stop_loss}")
        return stop_loss
        
    def apply_take_profit_strategy(self, signal: Dict, take_profit_strategy: str = 'fixed', risk_reward_ratio: float = 2.0) -> Dict:
        """
        Calculate take profit level(s) based on the chosen strategy
        
        Args:
            signal: Signal dictionary with pair, price, direction, stop_loss
            take_profit_strategy: Strategy to use ('fixed', 'multiple', 'trailing')
            risk_reward_ratio: Reward to risk ratio for fixed TP
            
        Returns:
            Dictionary with take profit levels and settings
        """
        pair = signal['pair']
        entry_price = signal['price']
        direction = 1 if signal['direction'] == 'buy' else -1
        stop_loss = signal['stop_loss']
        
        # Get pip value for this pair
        is_jpy_pair = 'JPY' in pair
        pip_value = 0.01 if is_jpy_pair else 0.0001
        
        # Calculate risk in price terms
        risk_distance = abs(entry_price - stop_loss)
        
        result = {}
        
        if take_profit_strategy == 'fixed':
            # Fixed risk-reward ratio
            reward_distance = risk_distance * risk_reward_ratio
            take_profit = entry_price + (direction * reward_distance)
            
            result['take_profit'] = take_profit
            result['tp_strategy'] = 'fixed'
            
        elif take_profit_strategy == 'multiple':
            # Multiple take profit levels - default 50% at 1:1, 50% at 2:1
            tp1_ratio = signal.get('tp1_ratio', 1.0)
            tp2_ratio = signal.get('tp2_ratio', 2.0)
            tp1_size = signal.get('tp1_size', 0.5)  # 50% of position
            
            tp1 = entry_price + (direction * risk_distance * tp1_ratio)
            tp2 = entry_price + (direction * risk_distance * tp2_ratio)
            
            result['take_profit_1'] = tp1
            result['take_profit_2'] = tp2
            result['tp1_size'] = tp1_size
            result['tp_strategy'] = 'multiple'
            
        elif take_profit_strategy == 'trailing':
            # Trailing stop - activate after price moves in favor by activation_ratio
            activation_ratio = signal.get('trailing_activation_ratio', 1.0)
            trailing_distance_pips = signal.get('trailing_distance_pips', 20)
            
            # Initial take profit to activate trailing
            activation_distance = risk_distance * activation_ratio
            activation_level = entry_price + (direction * activation_distance)
            
            result['take_profit'] = activation_level
            result['trailing_stop_enabled'] = True
            result['trailing_activation_level'] = activation_level
            result['trailing_stop_distance'] = trailing_distance_pips
            result['tp_strategy'] = 'trailing'
            
        else:
            # Default to fixed risk-reward
            reward_distance = risk_distance * 1.5  # Default 1.5:1
            take_profit = entry_price + (direction * reward_distance)
            
            result['take_profit'] = take_profit
            result['tp_strategy'] = 'fixed'
            logger.warning(f"Using default fixed take profit for {pair} due to invalid strategy")
            
        logger.info(f"Calculated take profit for {pair} using {take_profit_strategy} strategy")
        return result
        
    def check_aged_positions(self) -> List[str]:
        """
        Check for positions that have reached their aging limit
        
        Returns:
            List of pairs that should be closed due to age
        """
        current_time = datetime.now()
        aged_positions = []
        
        for pair, trade in list(self.active_trades.items()):
            if 'expiry_time' in trade and current_time >= trade['expiry_time']:
                logger.warning(f"Position {pair} has reached age limit ({self.position_aging_hours} hours)")
                aged_positions.append(pair)
                
        return aged_positions
        
    def re_evaluate_position(self, pair: str, current_price: float, market_data: Optional[Dict] = None):
        """
        Re-evaluate a position after it's been open for some time
        
        Args:
            pair: Currency pair
            current_price: Current market price
            market_data: Optional additional market data for analysis
            
        Returns:
            Action recommendation ('hold', 'adjust_tp', 'adjust_sl', 'close')
        """
        if pair not in self.active_trades:
            return None
            
        trade = self.active_trades[pair]
        entry_time = trade['entry_time']
        current_time = datetime.now()
        
        # Check if position has been open for at least 30 minutes
        if (current_time - entry_time).total_seconds() < 1800:  # 30 minutes
            return 'hold'
            
        entry_price = trade['entry_price']
        direction = 1 if trade['direction'] == 'buy' else -1
        stop_loss = trade['stop_loss']
        
        # Calculate current profit/loss in pips
        pip_value = 0.01 if 'JPY' in pair else 0.0001
        price_diff = (current_price - entry_price) * direction
        pips_profit = price_diff / pip_value
        
        # Decision logic
        if pips_profit <= -5:
            # In loss territory - consider closing if momentum is against
            return 'close'
            
        elif 0 <= pips_profit < 10:
            # Small profit - tighten stop loss to breakeven
            return 'adjust_sl'
            
        elif pips_profit >= 10:
            # Good profit - adjust to trailing stop if not already
            if not trade.get('trailing_stop_enabled', False):
                return 'adjust_tp'
                
        # Default action
        return 'hold'
    
    def update_trade(self, pair: str, current_price: float):
        """
        Update trade metrics based on current price
        
        Args:
            pair: Currency pair
            current_price: Current market price
        """
        if pair not in self.active_trades:
            return
        
        trade = self.active_trades[pair]
        entry_price = trade['entry_price']
        position_size = trade['position_size']
        direction = 1 if trade['direction'] == 'buy' else -1
        
        # Calculate pip value
        pip_value = 0.01 if 'JPY' in pair else 0.0001
        
        # Calculate profit/loss in pips
        price_difference = (current_price - entry_price) * direction
        pips = price_difference / pip_value
        
        # Calculate profit/loss in money
        # For simplicity, assuming USD account and $10 per pip per standard lot
        pip_value_in_money = 10  # $10 per pip for a standard lot
        pnl = pips * position_size * pip_value_in_money
        
        # Update trade with current metrics
        trade['current_price'] = current_price
        trade['current_pnl_pips'] = pips
        trade['current_pnl_money'] = pnl
        
        # Adjust trailing stop if enabled
        if trade.get('trailing_stop_enabled', False):
            self._adjust_trailing_stop(pair, current_price)
    
    def close_trade(self, pair: str, exit_price: float, exit_reason: str):
        """
        Close a trade and record performance
        
        Args:
            pair: Currency pair
            exit_price: Exit price
            exit_reason: Reason for closing (take profit, stop loss, etc.)
            
        Returns:
            Closed trade details
        """
        if pair not in self.active_trades:
            logger.warning(f"Cannot close trade: no active trade for {pair}")
            return None
        
        trade = self.active_trades[pair]
        entry_price = trade['entry_price']
        position_size = trade['position_size']
        direction = 1 if trade['direction'] == 'buy' else -1
        entry_time = trade['entry_time']
        
        # Calculate pip value
        pip_value = 0.01 if 'JPY' in pair else 0.0001
        
        # Calculate profit/loss in pips
        price_difference = (exit_price - entry_price) * direction
        pips = price_difference / pip_value
        
        # Calculate profit/loss in money
        pip_value_in_money = 10  # $10 per pip for a standard lot
        pnl = pips * position_size * pip_value_in_money
        
        # Calculate duration
        exit_time = datetime.now()
        duration = exit_time - entry_time
        
        # Create closed trade record
        closed_trade = {
            'pair': pair,
            'direction': trade['direction'],
            'entry_price': entry_price,
            'exit_price': exit_price,
            'position_size': position_size,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'duration': duration,
            'pnl_pips': pips,
            'pnl_money': pnl,
            'exit_reason': exit_reason
        }
        
        # Add to trade history
        self.trade_history.append(closed_trade)
        
        # Update daily PnL
        date_key = exit_time.strftime('%Y-%m-%d')
        if date_key not in self.daily_pnl:
            self.daily_pnl[date_key] = 0
        
        self.daily_pnl[date_key] += pnl
        
        # Remove from active trades
        del self.active_trades[pair]
        
        logger.info(f"Closed trade for {pair}: {pnl:.2f} profit, {pips:.1f} pips, reason: {exit_reason}")
        
        return closed_trade
    
    def _adjust_trailing_stop(self, pair: str, current_price: float):
        """
        Adjust trailing stop for a trade
        
        Args:
            pair: Currency pair
            current_price: Current market price
        """
        if pair not in self.active_trades:
            return
        
        trade = self.active_trades[pair]
        
        if not trade.get('trailing_stop_enabled', False):
            return
        
        direction = 1 if trade['direction'] == 'buy' else -1
        stop_loss = trade['stop_loss']
        
        # For buy orders, move stop loss up as price increases
        if direction == 1 and current_price > trade.get('trailing_stop_trigger', current_price):
            # Calculate new stop loss
            pip_value = 0.01 if 'JPY' in pair else 0.0001
            trailing_distance = trade.get('trailing_stop_distance', 20) * pip_value
            new_stop_loss = current_price - trailing_distance
            
            # Only move stop loss up, never down
            if new_stop_loss > stop_loss:
                trade['stop_loss'] = new_stop_loss
                trade['trailing_stop_trigger'] = current_price
                logger.info(f"Adjusted trailing stop for {pair} to {new_stop_loss}")
        
        # For sell orders, move stop loss down as price decreases
        elif direction == -1 and current_price < trade.get('trailing_stop_trigger', current_price):
            # Calculate new stop loss
            pip_value = 0.01 if 'JPY' in pair else 0.0001
            trailing_distance = trade.get('trailing_stop_distance', 20) * pip_value
            new_stop_loss = current_price + trailing_distance
            
            # Only move stop loss down, never up
            if new_stop_loss < stop_loss:
                trade['stop_loss'] = new_stop_loss
                trade['trailing_stop_trigger'] = current_price
                logger.info(f"Adjusted trailing stop for {pair} to {new_stop_loss}")
    
    def _check_drawdown(self):
        """
        Check if drawdown circuit breaker should be triggered
        """
        if self.current_balance is None or self.highest_balance is None:
            return
        
        # Calculate current drawdown
        drawdown = 1 - (self.current_balance / self.highest_balance)
        
        # Check if drawdown exceeds maximum allowed
        if drawdown >= self.max_drawdown_percent:
            if not self.trading_disabled:
                self.trading_disabled = True
                self.trading_disabled_reason = f"Max drawdown reached: {drawdown*100:.1f}% (limit: {self.max_drawdown_percent*100:.1f}%)"
                logger.warning(f"TRADING DISABLED: {self.trading_disabled_reason}")
        
    def _daily_risk_limit_reached(self) -> bool:
        """
        Check if daily risk limit has been reached
        
        Returns:
            True if limit reached
        """
        if self.current_balance is None:
            return False
        
        # Calculate today's losses
        today = datetime.now().strftime('%Y-%m-%d')
        today_pnl = self.daily_pnl.get(today, 0)
        
        # If already profitable today, no need to limit
        if today_pnl >= 0:
            return False
        
        # Calculate absolute loss
        loss = abs(today_pnl)
        
        # Calculate maximum allowed daily loss
        max_daily_loss = self.current_balance * self.max_daily_risk
        
        # Check if loss exceeds limit
        if loss >= max_daily_loss:
            logger.warning(f"Daily risk limit reached: {loss:.2f} (limit: {max_daily_loss:.2f})")
            return True
        
        return False
    
    def get_performance_metrics(self) -> Dict:
        """
        Calculate performance metrics
        
        Returns:
            Dictionary with performance metrics
        """
        metrics = {}
        
        # Basic account metrics
        metrics['starting_balance'] = self.starting_balance
        metrics['current_balance'] = self.current_balance
        metrics['absolute_pnl'] = 0 if self.starting_balance is None else (self.current_balance - self.starting_balance)
        metrics['percent_pnl'] = 0 if self.starting_balance is None else ((self.current_balance / self.starting_balance) - 1) * 100
        metrics['max_drawdown'] = 0 if self.highest_balance is None else (1 - (self.current_balance / self.highest_balance)) * 100
        
        # Trading metrics
        total_trades = len(self.trade_history)
        metrics['total_trades'] = total_trades
        
        if total_trades > 0:
            # Win rate
            winning_trades = sum(1 for trade in self.trade_history if trade['pnl_money'] > 0)
            metrics['win_rate'] = (winning_trades / total_trades) * 100
            
            # Average profit/loss
            avg_pnl_money = sum(trade['pnl_money'] for trade in self.trade_history) / total_trades
            avg_pnl_pips = sum(trade['pnl_pips'] for trade in self.trade_history) / total_trades
            metrics['avg_pnl_money'] = avg_pnl_money
            metrics['avg_pnl_pips'] = avg_pnl_pips
            
            # Profit factor
            gross_profit = sum(trade['pnl_money'] for trade in self.trade_history if trade['pnl_money'] > 0)
            gross_loss = abs(sum(trade['pnl_money'] for trade in self.trade_history if trade['pnl_money'] < 0))
            metrics['profit_factor'] = 0 if gross_loss == 0 else gross_profit / gross_loss
            
            # Average holding time
            avg_duration = sum((trade['exit_time'] - trade['entry_time']).total_seconds() for trade in self.trade_history) / total_trades
            metrics['avg_duration_seconds'] = avg_duration
            
            # Profitable vs unprofitable duration
            if winning_trades > 0 and winning_trades < total_trades:
                avg_winning_duration = sum((trade['exit_time'] - trade['entry_time']).total_seconds() 
                                         for trade in self.trade_history if trade['pnl_money'] > 0) / winning_trades
                avg_losing_duration = sum((trade['exit_time'] - trade['entry_time']).total_seconds() 
                                        for trade in self.trade_history if trade['pnl_money'] <= 0) / (total_trades - winning_trades)
                metrics['avg_winning_duration_seconds'] = avg_winning_duration
                metrics['avg_losing_duration_seconds'] = avg_losing_duration
        
        return metrics
    
    def reset_trading_disabled(self):
        """
        Reset the trading disabled flag
        """
        if self.trading_disabled:
            self.trading_disabled = False
            self.trading_disabled_reason = None
            logger.info("Trading restrictions have been reset")
            
    def get_active_trades(self) -> Dict:
        """
        Get all active trades
        
        Returns:
            Dictionary with active trades
        """
        return self.active_trades
