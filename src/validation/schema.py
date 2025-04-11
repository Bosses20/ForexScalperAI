"""
Schema definitions for data validation
Uses Pydantic models to define and validate data structures
"""

from typing import Dict, List, Optional, Union, Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator


class OrderType(str, Enum):
    """Order type enumeration"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class TradeDirection(str, Enum):
    """Trade direction enumeration"""
    BUY = "BUY"
    SELL = "SELL"


class TimeFrame(str, Enum):
    """Timeframe enumeration"""
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    H12 = "H12"
    D1 = "D1"
    W1 = "W1"
    MN1 = "MN1"


class DatabaseConfigSchema(BaseModel):
    """Database configuration schema"""
    host: str = Field(..., min_length=1)
    port: int = Field(..., gt=0)
    user: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    database: str = Field(..., min_length=1)
    ssl_mode: Optional[str] = None
    connection_timeout: int = Field(30, ge=5)
    pool_size: int = Field(5, gt=0)
    
    class Config:
        extra = "allow"


class MT5ConfigSchema(BaseModel):
    """MT5 configuration schema"""
    login: int = Field(..., gt=0)
    password: str = Field(..., min_length=1)
    server: str = Field(..., min_length=1)
    path: Optional[str] = None
    timeout: int = Field(60000, ge=1000)
    max_retries: int = Field(3, ge=1)
    retry_delay: int = Field(5, ge=1)
    
    class Config:
        extra = "allow"


class LoggingConfigSchema(BaseModel):
    """Logging configuration schema"""
    level: str = Field("INFO", regex=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    file_path: Optional[str] = None
    rotation: Optional[str] = None
    format: Optional[str] = None
    
    class Config:
        extra = "allow"


class StrategyConfigSchema(BaseModel):
    """Strategy configuration schema"""
    name: str = Field(..., min_length=1)
    class_path: str = Field(..., min_length=1)
    enabled: bool = True
    params: Dict[str, Any] = Field(default_factory=dict)
    symbols: List[str] = Field(default_factory=list)
    timeframes: List[str] = Field(default_factory=list)
    
    @validator('timeframes')
    def validate_timeframes(cls, v):
        """Validate timeframes are valid"""
        valid_timeframes = [tf.value for tf in TimeFrame]
        for tf in v:
            if tf not in valid_timeframes:
                raise ValueError(f"Invalid timeframe: {tf}")
        return v
    
    class Config:
        extra = "allow"


class ConfigSchema(BaseModel):
    """Main configuration schema"""
    app_name: str = Field("Forex Trading Bot", min_length=1)
    version: str = Field("1.0.0", min_length=1)
    environment: str = Field("development", regex=r"^(development|testing|production)$")
    debug: bool = False
    
    database: Optional[DatabaseConfigSchema] = None
    mt5: Optional[MT5ConfigSchema] = None
    logging: LoggingConfigSchema = Field(default_factory=LoggingConfigSchema)
    
    strategies: List[StrategyConfigSchema] = Field(default_factory=list)
    
    risk_management: Dict[str, Any] = Field(default_factory=dict)
    api: Dict[str, Any] = Field(default_factory=dict)
    security: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        extra = "allow"


class OrderSchema(BaseModel):
    """Trading order schema"""
    symbol: str = Field(..., min_length=1, max_length=20)
    order_type: OrderType
    direction: TradeDirection
    volume: float = Field(..., gt=0)
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: Optional[str] = Field(None, max_length=100)
    magic: Optional[int] = None
    expiration: Optional[datetime] = None
    
    @root_validator
    def check_price_for_pending_orders(cls, values):
        """Validate price is set for non-market orders"""
        order_type = values.get('order_type')
        price = values.get('price')
        
        if order_type != OrderType.MARKET and (price is None or price <= 0):
            raise ValueError(f"Price must be set for {order_type} orders")
            
        return values
    
    @validator('stop_loss', 'take_profit')
    def validate_sl_tp_positive(cls, v):
        """Validate stop loss and take profit are positive if set"""
        if v is not None and v <= 0:
            raise ValueError("Stop loss and take profit must be positive values")
        return v
    
    class Config:
        extra = "allow"


class TradeSchema(BaseModel):
    """Trade or position schema"""
    ticket: int = Field(..., gt=0)
    symbol: str = Field(..., min_length=1, max_length=20)
    order_type: OrderType
    direction: TradeDirection
    volume: float = Field(..., gt=0)
    open_price: float = Field(..., gt=0)
    open_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    close_price: Optional[float] = None
    close_time: Optional[datetime] = None
    profit: Optional[float] = None
    commission: Optional[float] = 0
    swap: Optional[float] = 0
    comment: Optional[str] = None
    magic: Optional[int] = None
    
    class Config:
        extra = "allow"


class MarketDataSchema(BaseModel):
    """Market data schema for OHLCV data"""
    symbol: str = Field(..., min_length=1, max_length=20)
    timeframe: str = Field(..., regex=r"^(M1|M5|M15|M30|H1|H4|D1|W1|MN1)$")
    time: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: float = Field(..., ge=0)
    spread: Optional[float] = None
    
    @root_validator
    def check_prices(cls, values):
        """Validate price relationships"""
        high = values.get('high')
        low = values.get('low')
        open_price = values.get('open')
        close = values.get('close')
        
        if high < low:
            raise ValueError("High price cannot be less than low price")
            
        if open_price < low or open_price > high:
            raise ValueError("Open price must be between low and high")
            
        if close < low or close > high:
            raise ValueError("Close price must be between low and high")
            
        return values
    
    class Config:
        extra = "allow"


class UserSchema(BaseModel):
    """User authentication schema"""
    username: str = Field(..., min_length=3, max_length=50, regex=r"^[a-zA-Z0-9_-]+$")
    email: str = Field(..., regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    password_hash: str = Field(..., min_length=6)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: List[str] = Field(default_factory=lambda: ["user"])
    is_active: bool = True
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        extra = "allow"


class APIKeySchema(BaseModel):
    """API key schema"""
    key_id: str = Field(..., min_length=10)
    user_id: str = Field(..., min_length=1)
    description: Optional[str] = None
    scopes: List[str] = Field(default_factory=lambda: ["read"])
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True
    
    @validator('expires_at')
    def validate_expiry(cls, v):
        """Validate expiry date is in the future"""
        if v <= datetime.now():
            raise ValueError("Expiry date must be in the future")
        return v
    
    class Config:
        extra = "allow"
