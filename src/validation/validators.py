"""
Validation classes for the Forex Trading Bot
Provides validation and sanitization of inputs
"""

import re
import json
import yaml
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from pydantic import ValidationError
from loguru import logger

from .schema import (
    ConfigSchema,
    StrategySchema,
    OrderSchema,
    TradeSchema,
    MarketDataSchema
)


class BaseValidator:
    """Base validator with common validation methods"""
    
    @staticmethod
    def is_valid_number(value: Any) -> bool:
        """Check if value is a valid number"""
        if value is None:
            return False
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_valid_integer(value: Any) -> bool:
        """Check if value is a valid integer"""
        if value is None:
            return False
        try:
            int_val = int(float(value))
            return float(int_val) == float(value)
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_valid_datetime(value: str) -> bool:
        """Check if string is a valid datetime"""
        if not value or not isinstance(value, str):
            return False
            
        # Try common datetime formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%d',
            '%Y%m%d%H%M%S'
        ]
        
        for fmt in formats:
            try:
                datetime.strptime(value, fmt)
                return True
            except ValueError:
                continue
                
        return False
    
    @staticmethod
    def sanitize_string(value: str) -> str:
        """Sanitize string input by removing potentially harmful characters"""
        if not value or not isinstance(value, str):
            return ""
            
        # Remove control characters and null bytes
        value = re.sub(r'[\x00-\x1F\x7F]', '', value)
        
        # Basic sanitization to prevent injection attacks
        value = value.replace('<', '&lt;').replace('>', '&gt;')
        
        return value
    
    @staticmethod
    def validate_range(value: float, min_val: float, max_val: float) -> bool:
        """Validate a value is within the specified range"""
        if not BaseValidator.is_valid_number(value):
            return False
            
        return min_val <= float(value) <= max_val


class ConfigValidator(BaseValidator):
    """Validates configuration settings"""
    
    def __init__(self):
        """Initialize config validator"""
        super().__init__()
        
    def validate_config_file(self, file_path: str) -> Tuple[bool, Dict, str]:
        """
        Validate a YAML configuration file
        
        Args:
            file_path: Path to the configuration file
            
        Returns:
            Tuple of (is_valid, config_data, error_message)
        """
        try:
            # Read the file
            with open(file_path, 'r') as f:
                config_data = yaml.safe_load(f)
                
            # Validate using the schema
            return self.validate_config(config_data)
            
        except Exception as e:
            error_msg = f"Error validating config file: {str(e)}"
            logger.error(error_msg)
            return False, {}, error_msg
    
    def validate_config(self, config_data: Dict) -> Tuple[bool, Dict, str]:
        """
        Validate configuration data
        
        Args:
            config_data: Configuration dictionary
            
        Returns:
            Tuple of (is_valid, validated_data, error_message)
        """
        try:
            # Validate against schema
            validated_data = ConfigSchema(**config_data).dict()
            return True, validated_data, ""
            
        except ValidationError as e:
            error_msg = f"Config validation error: {str(e)}"
            logger.error(error_msg)
            return False, config_data, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error in config validation: {str(e)}"
            logger.error(error_msg)
            return False, config_data, error_msg
    
    def validate_mt5_config(self, config_data: Dict) -> Tuple[bool, Dict, str]:
        """
        Validate MT5 specific configuration
        
        Args:
            config_data: MT5 configuration dictionary
            
        Returns:
            Tuple of (is_valid, validated_data, error_message)
        """
        required_fields = ['login', 'password', 'server']
        errors = []
        
        # Check required fields
        for field in required_fields:
            if field not in config_data:
                errors.append(f"Missing required field: {field}")
                
        # Validate login is integer
        if 'login' in config_data and not self.is_valid_integer(config_data['login']):
            errors.append("MT5 login must be an integer")
            
        # Validate server is not empty
        if 'server' in config_data and not config_data['server']:
            errors.append("MT5 server cannot be empty")
            
        # Validate path if provided
        if 'path' in config_data and config_data['path']:
            import os
            if not os.path.exists(config_data['path']):
                errors.append(f"MT5 path does not exist: {config_data['path']}")
                
        if errors:
            error_msg = "; ".join(errors)
            logger.error(f"MT5 config validation error: {error_msg}")
            return False, config_data, error_msg
            
        return True, config_data, ""


class InputValidator(BaseValidator):
    """Validates user and API inputs"""
    
    def __init__(self):
        """Initialize input validator"""
        super().__init__()
        
    def validate_symbol(self, symbol: str) -> Tuple[bool, str, str]:
        """
        Validate a trading symbol
        
        Args:
            symbol: Trading symbol to validate
            
        Returns:
            Tuple of (is_valid, sanitized_symbol, error_message)
        """
        if not symbol or not isinstance(symbol, str):
            return False, "", "Symbol must be a non-empty string"
            
        # Sanitize symbol
        sanitized = self.sanitize_string(symbol.strip().upper())
        
        # Check pattern (alphanumeric with optional dots)
        if not re.match(r'^[A-Z0-9\.]+$', sanitized):
            return False, sanitized, "Symbol contains invalid characters"
            
        # Check length
        if len(sanitized) < 2 or len(sanitized) > 20:
            return False, sanitized, "Symbol length must be between 2 and 20 characters"
            
        return True, sanitized, ""
    
    def validate_timeframe(self, timeframe: str) -> Tuple[bool, str, str]:
        """
        Validate a timeframe string
        
        Args:
            timeframe: Timeframe string to validate (e.g., M1, H4, D1)
            
        Returns:
            Tuple of (is_valid, sanitized_timeframe, error_message)
        """
        if not timeframe or not isinstance(timeframe, str):
            return False, "", "Timeframe must be a non-empty string"
            
        # Sanitize timeframe
        sanitized = self.sanitize_string(timeframe.strip().upper())
        
        # Valid timeframes
        valid_timeframes = [
            'M1', 'M5', 'M15', 'M30',
            'H1', 'H4', 'H12',
            'D1', 'W1', 'MN1'
        ]
        
        if sanitized not in valid_timeframes:
            return False, sanitized, f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}"
            
        return True, sanitized, ""
    
    def validate_api_request(self, request_data: Dict, required_fields: List[str],
                           field_validators: Dict = None) -> Tuple[bool, Dict, str]:
        """
        Validate API request data
        
        Args:
            request_data: Request data dictionary
            required_fields: List of required field names
            field_validators: Dictionary of field-specific validators
            
        Returns:
            Tuple of (is_valid, validated_data, error_message)
        """
        if not isinstance(request_data, dict):
            return False, {}, "Request data must be a dictionary"
            
        errors = []
        validated_data = {}
        
        # Check required fields
        for field in required_fields:
            if field not in request_data:
                errors.append(f"Missing required field: {field}")
                
        # Apply field-specific validators
        if field_validators:
            for field, validator in field_validators.items():
                if field in request_data:
                    try:
                        is_valid, value, error = validator(request_data[field])
                        if not is_valid:
                            errors.append(f"Field '{field}': {error}")
                        else:
                            validated_data[field] = value
                    except Exception as e:
                        errors.append(f"Error validating field '{field}': {str(e)}")
                        
        # Copy remaining fields
        for field, value in request_data.items():
            if field not in validated_data:
                # Basic sanitization for string values
                if isinstance(value, str):
                    validated_data[field] = self.sanitize_string(value)
                else:
                    validated_data[field] = value
                    
        if errors:
            error_msg = "; ".join(errors)
            logger.error(f"API request validation error: {error_msg}")
            return False, validated_data, error_msg
            
        return True, validated_data, ""


class OrderValidator(BaseValidator):
    """Validates trading orders"""
    
    def __init__(self):
        """Initialize order validator"""
        super().__init__()
        
    def validate_order(self, order_data: Dict) -> Tuple[bool, Dict, str]:
        """
        Validate a trading order
        
        Args:
            order_data: Order data dictionary
            
        Returns:
            Tuple of (is_valid, validated_data, error_message)
        """
        try:
            # Validate against schema
            validated_data = OrderSchema(**order_data).dict()
            
            # Additional custom validations
            errors = []
            
            # Validate symbol
            symbol = validated_data.get('symbol', '')
            if not re.match(r'^[A-Z0-9\.]+$', symbol):
                errors.append("Symbol contains invalid characters")
                
            # Validate order type
            order_type = validated_data.get('order_type', '')
            valid_types = ['MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT']
            if order_type not in valid_types:
                errors.append(f"Invalid order type. Must be one of: {', '.join(valid_types)}")
                
            # Validate volume
            volume = validated_data.get('volume', 0)
            if volume <= 0:
                errors.append("Volume must be greater than zero")
                
            # Validate price for non-market orders
            if order_type != 'MARKET':
                price = validated_data.get('price', 0)
                if price <= 0:
                    errors.append("Price must be greater than zero for non-market orders")
                    
            if errors:
                error_msg = "; ".join(errors)
                logger.error(f"Order validation error: {error_msg}")
                return False, validated_data, error_msg
                
            return True, validated_data, ""
            
        except ValidationError as e:
            error_msg = f"Order validation error: {str(e)}"
            logger.error(error_msg)
            return False, order_data, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error in order validation: {str(e)}"
            logger.error(error_msg)
            return False, order_data, error_msg
    
    def validate_sl_tp(self, price: float, sl: Optional[float], tp: Optional[float], 
                     order_type: str, direction: str) -> str:
        """
        Validate stop loss and take profit
        
        Args:
            price: Order price
            sl: Stop loss price
            tp: Take profit price
            order_type: Order type
            direction: Order direction (BUY/SELL)
            
        Returns:
            Error message or empty string if valid
        """
        if not price or price <= 0:
            return "Invalid price value"
            
        # Validate stop loss
        if sl is not None:
            if not self.is_valid_number(sl) or sl <= 0:
                return "Invalid stop loss value"
                
            # Check SL is below price for BUY orders
            if direction == 'BUY' and sl >= price:
                return "Stop loss must be below entry price for BUY orders"
                
            # Check SL is above price for SELL orders
            if direction == 'SELL' and sl <= price:
                return "Stop loss must be above entry price for SELL orders"
                
        # Validate take profit
        if tp is not None:
            if not self.is_valid_number(tp) or tp <= 0:
                return "Invalid take profit value"
                
            # Check TP is above price for BUY orders
            if direction == 'BUY' and tp <= price:
                return "Take profit must be above entry price for BUY orders"
                
            # Check TP is below price for SELL orders
            if direction == 'SELL' and tp >= price:
                return "Take profit must be below entry price for SELL orders"
                
        return ""


class TradeValidator(BaseValidator):
    """Validates trades and positions"""
    
    def __init__(self):
        """Initialize trade validator"""
        super().__init__()
        
    def validate_trade(self, trade_data: Dict) -> Tuple[bool, Dict, str]:
        """
        Validate trade data
        
        Args:
            trade_data: Trade data dictionary
            
        Returns:
            Tuple of (is_valid, validated_data, error_message)
        """
        try:
            # Validate against schema
            validated_data = TradeSchema(**trade_data).dict()
            return True, validated_data, ""
            
        except ValidationError as e:
            error_msg = f"Trade validation error: {str(e)}"
            logger.error(error_msg)
            return False, trade_data, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error in trade validation: {str(e)}"
            logger.error(error_msg)
            return False, trade_data, error_msg
    
    def validate_risk_limits(self, account_balance: float, 
                           risk_per_trade: float, 
                           max_risk_per_day: float,
                           current_daily_risk: float) -> Tuple[bool, str]:
        """
        Validate risk management limits
        
        Args:
            account_balance: Current account balance
            risk_per_trade: Risk amount for this trade
            max_risk_per_day: Maximum allowed daily risk
            current_daily_risk: Current risk exposure for the day
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate account balance
        if not self.is_valid_number(account_balance) or account_balance <= 0:
            return False, "Invalid account balance"
            
        # Validate risk per trade
        if not self.is_valid_number(risk_per_trade) or risk_per_trade <= 0:
            return False, "Invalid risk per trade"
            
        # Check risk per trade as percentage of balance
        risk_percent = (risk_per_trade / account_balance) * 100
        if risk_percent > 2:  # Example limit: 2%
            return False, f"Risk per trade ({risk_percent:.2f}%) exceeds maximum allowed (2%)"
            
        # Check daily risk limit
        new_daily_risk = current_daily_risk + risk_per_trade
        if new_daily_risk > max_risk_per_day:
            return False, f"This trade would exceed your daily risk limit of {max_risk_per_day}"
            
        return True, ""
    
    def validate_margin_requirements(self, account_equity: float, 
                                   margin_required: float,
                                   free_margin: float) -> Tuple[bool, str]:
        """
        Validate margin requirements for a trade
        
        Args:
            account_equity: Current account equity
            margin_required: Margin required for the trade
            free_margin: Available free margin
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if we have sufficient free margin
        if margin_required > free_margin:
            return False, f"Insufficient free margin: {free_margin} available, {margin_required} required"
            
        # Check margin/equity ratio
        margin_equity_ratio = margin_required / account_equity
        if margin_equity_ratio > 0.2:  # Example limit: 20%
            return False, f"Margin required ({margin_equity_ratio:.2f}%) exceeds maximum allowed ratio (20%)"
            
        return True, ""
