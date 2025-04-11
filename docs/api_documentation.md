# Forex Trading Bot API Documentation

This document provides comprehensive information about the Forex Trading Bot API endpoints, authentication, request/response formats, and examples.

## API Overview

The Forex Trading Bot API provides programmatic access to trading functionality, market data, account information, and bot configuration. This RESTful API uses JSON for request and response payloads, and HTTP status codes to indicate the success or failure of requests.

## Base URL

All API endpoints are relative to the base URL:

```
https://api.forextradingbot.com/v1
```

For local development, use:

```
http://localhost:8000/v1
```

## Authentication

### API Key Authentication

All API requests must include the following headers:

- `X-API-Key`: Your API key
- `X-Timestamp`: Current Unix timestamp in seconds
- `X-Signature`: HMAC SHA-256 signature

To generate the signature:

1. Concatenate your API key and timestamp with a colon: `{api_key}:{timestamp}`
2. Sign this string using HMAC SHA-256 with your secret key
3. Convert the signature to a hexadecimal string

Example (Python):

```python
import time
import hmac
import hashlib

api_key = "your_api_key"
secret_key = "your_secret_key"
timestamp = str(int(time.time()))

message = f"{api_key}:{timestamp}"
signature = hmac.new(
    secret_key.encode('utf-8'),
    message.encode('utf-8'),
    hashlib.sha256
).hexdigest()

headers = {
    "X-API-Key": api_key,
    "X-Timestamp": timestamp,
    "X-Signature": signature
}
```

## Rate Limiting

API requests are limited to 60 requests per minute per API key. Rate limit information is included in the response headers:

- `X-Rate-Limit-Limit`: Number of requests allowed per minute
- `X-Rate-Limit-Remaining`: Number of requests remaining in the current window
- `X-Rate-Limit-Reset`: Time at which the rate limit resets (Unix timestamp)

If you exceed the rate limit, you'll receive a `429 Too Many Requests` response.

## Endpoints

### Account Information

#### Get Account Status

```
GET /account/status
```

Returns current account information including balance, equity, open positions, and trading stats.

**Response**:

```json
{
  "account_id": "12345678",
  "balance": 10000.00,
  "equity": 10050.25,
  "margin": 500.15,
  "free_margin": 9550.10,
  "margin_level": 2009.45,
  "currency": "USD",
  "open_positions": 2,
  "floating_pnl": 50.25,
  "daily_pnl": 120.50,
  "weekly_pnl": 345.75,
  "monthly_pnl": 780.30
}
```

#### Get Trading Performance

```
GET /account/performance
```

Returns detailed trading performance metrics.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| period | string | No | Time period for stats (daily, weekly, monthly, yearly, all). Default: monthly |
| start_date | string | No | Start date in YYYY-MM-DD format |
| end_date | string | No | End date in YYYY-MM-DD format |

**Response**:

```json
{
  "period": "monthly",
  "total_trades": 87,
  "win_rate": 68.5,
  "profit_factor": 2.3,
  "net_profit": 780.30,
  "max_drawdown": 210.45,
  "max_drawdown_percentage": 2.1,
  "sharpe_ratio": 1.85,
  "average_win": 25.40,
  "average_loss": 15.20,
  "best_trade": 85.50,
  "worst_trade": -45.30,
  "strategies": [
    {
      "name": "EMA Crossover",
      "trades": 28,
      "win_rate": 71.4,
      "net_profit": 315.60
    },
    {
      "name": "Bollinger Band Breakouts",
      "trades": 32,
      "win_rate": 65.6,
      "net_profit": 275.80
    }
  ]
}
```

### Trading Operations

#### Place Trade

```
POST /trade/place
```

Opens a new trade position.

**Request**:

```json
{
  "symbol": "EURUSD",
  "order_type": "market",
  "direction": "buy",
  "volume": 0.1,
  "stop_loss": 1.0950,
  "take_profit": 1.1050,
  "strategy": "manual",
  "comment": "API trade"
}
```

**Response**:

```json
{
  "trade_id": "12345",
  "symbol": "EURUSD",
  "direction": "buy",
  "open_price": 1.1000,
  "volume": 0.1,
  "stop_loss": 1.0950,
  "take_profit": 1.1050,
  "open_time": "2025-04-11T10:15:25Z",
  "status": "open",
  "strategy": "manual",
  "comment": "API trade"
}
```

#### Modify Trade

```
PUT /trade/{trade_id}
```

Modifies an existing trade.

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| trade_id | string | ID of the trade to modify |

**Request**:

```json
{
  "stop_loss": 1.0960,
  "take_profit": 1.1060
}
```

**Response**:

```json
{
  "trade_id": "12345",
  "symbol": "EURUSD",
  "direction": "buy",
  "open_price": 1.1000,
  "volume": 0.1,
  "stop_loss": 1.0960,
  "take_profit": 1.1060,
  "open_time": "2025-04-11T10:15:25Z",
  "status": "open",
  "strategy": "manual",
  "comment": "API trade"
}
```

#### Close Trade

```
DELETE /trade/{trade_id}
```

Closes an open trade.

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| trade_id | string | ID of the trade to close |

**Response**:

```json
{
  "trade_id": "12345",
  "symbol": "EURUSD",
  "direction": "buy",
  "open_price": 1.1000,
  "close_price": 1.1025,
  "volume": 0.1,
  "profit": 25.00,
  "open_time": "2025-04-11T10:15:25Z",
  "close_time": "2025-04-11T14:30:15Z",
  "status": "closed",
  "strategy": "manual",
  "comment": "API trade"
}
```

#### Get Open Trades

```
GET /trades/open
```

Returns all open trades.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| symbol | string | No | Filter by symbol (e.g., EURUSD) |
| strategy | string | No | Filter by strategy |

**Response**:

```json
{
  "total": 2,
  "trades": [
    {
      "trade_id": "12345",
      "symbol": "EURUSD",
      "direction": "buy",
      "open_price": 1.1000,
      "volume": 0.1,
      "stop_loss": 1.0960,
      "take_profit": 1.1060,
      "open_time": "2025-04-11T10:15:25Z",
      "floating_profit": 25.00,
      "status": "open",
      "strategy": "manual"
    },
    {
      "trade_id": "12346",
      "symbol": "GBPUSD",
      "direction": "sell",
      "open_price": 1.2500,
      "volume": 0.2,
      "stop_loss": 1.2550,
      "take_profit": 1.2400,
      "open_time": "2025-04-11T11:05:15Z",
      "floating_profit": 30.25,
      "status": "open",
      "strategy": "EMA Crossover"
    }
  ]
}
```

### Market Data

#### Get Price Data

```
GET /market/prices
```

Returns current price data for specified symbols.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| symbols | string | Yes | Comma-separated list of symbols (e.g., EURUSD,GBPUSD) |

**Response**:

```json
{
  "timestamp": "2025-04-11T13:15:00Z",
  "prices": [
    {
      "symbol": "EURUSD",
      "bid": 1.1025,
      "ask": 1.1027,
      "spread": 0.2
    },
    {
      "symbol": "GBPUSD",
      "bid": 1.2480,
      "ask": 1.2483,
      "spread": 0.3
    }
  ]
}
```

#### Get Historical Data

```
GET /market/history
```

Returns historical OHLC data for a symbol.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| symbol | string | Yes | Symbol (e.g., EURUSD) |
| timeframe | string | Yes | Timeframe (M1, M5, M15, M30, H1, H4, D1, W1, MN) |
| count | integer | No | Number of candles to return. Default: 100 |
| start_time | string | No | Start time in ISO format or Unix timestamp |
| end_time | string | No | End time in ISO format or Unix timestamp |

**Response**:

```json
{
  "symbol": "EURUSD",
  "timeframe": "H1",
  "data": [
    {
      "time": "2025-04-11T12:00:00Z",
      "open": 1.1010,
      "high": 1.1035,
      "low": 1.1005,
      "close": 1.1025,
      "volume": 1250
    },
    {
      "time": "2025-04-11T11:00:00Z",
      "open": 1.1020,
      "high": 1.1025,
      "low": 1.0990,
      "close": 1.1010,
      "volume": 1180
    }
  ]
}
```

#### Get Market Conditions

```
GET /market/conditions
```

Returns current market condition analysis.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| symbol | string | Yes | Symbol (e.g., EURUSD) |

**Response**:

```json
{
  "symbol": "EURUSD",
  "updated_at": "2025-04-11T13:10:00Z",
  "trend": "bullish",
  "strength": 0.75,
  "volatility": "medium",
  "liquidity": "high",
  "suitable_strategies": [
    "EMA Crossover",
    "Break and Retest"
  ],
  "confidence": 0.82,
  "trade_recommendation": true
}
```

### Bot Management

#### Get Bot Status

```
GET /bot/status
```

Returns current bot operational status.

**Response**:

```json
{
  "status": "running",
  "uptime": 259200,
  "active_strategies": [
    "EMA Crossover",
    "Bollinger Band Breakouts",
    "Break and Retest"
  ],
  "monitored_symbols": [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "AUDUSD"
  ],
  "last_trade_time": "2025-04-11T12:45:10Z",
  "cpu_usage": 15.2,
  "memory_usage": 125.4,
  "pending_signals": 2
}
```

#### Update Bot Configuration

```
PUT /bot/config
```

Updates bot configuration parameters.

**Request**:

```json
{
  "risk_per_trade": 0.01,
  "max_daily_trades": 10,
  "active_strategies": [
    "EMA Crossover",
    "Bollinger Band Breakouts",
    "Break and Retest"
  ],
  "trading_hours": {
    "start": "08:00",
    "end": "17:00",
    "timezone": "UTC"
  },
  "max_spread_pips": {
    "EURUSD": 3.0,
    "GBPUSD": 3.5,
    "USDJPY": 4.0,
    "AUDUSD": 3.5
  }
}
```

**Response**:

```json
{
  "success": true,
  "message": "Bot configuration updated successfully",
  "updated_at": "2025-04-11T13:20:15Z",
  "config": {
    "risk_per_trade": 0.01,
    "max_daily_trades": 10,
    "active_strategies": [
      "EMA Crossover",
      "Bollinger Band Breakouts",
      "Break and Retest"
    ],
    "trading_hours": {
      "start": "08:00",
      "end": "17:00",
      "timezone": "UTC"
    },
    "max_spread_pips": {
      "EURUSD": 3.0,
      "GBPUSD": 3.5,
      "USDJPY": 4.0,
      "AUDUSD": 3.5
    }
  }
}
```

#### Start/Stop Trading

```
POST /bot/control
```

Controls the bot's trading operations.

**Request**:

```json
{
  "action": "stop",
  "reason": "Scheduled maintenance"
}
```

**Response**:

```json
{
  "success": true,
  "message": "Bot trading stopped",
  "status": "stopped",
  "timestamp": "2025-04-11T13:25:30Z"
}
```

### Logs and Notifications

#### Get Trading Logs

```
GET /logs/trading
```

Returns trading activity logs.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| start_time | string | No | Start time in ISO format or Unix timestamp |
| end_time | string | No | End time in ISO format or Unix timestamp |
| level | string | No | Log level (info, warning, error, all). Default: all |
| limit | integer | No | Maximum number of logs to return. Default: 100 |

**Response**:

```json
{
  "total": 2,
  "logs": [
    {
      "timestamp": "2025-04-11T12:45:10Z",
      "level": "info",
      "message": "Opened BUY position for EURUSD",
      "details": {
        "trade_id": "12345",
        "symbol": "EURUSD",
        "direction": "buy",
        "volume": 0.1,
        "strategy": "EMA Crossover"
      }
    },
    {
      "timestamp": "2025-04-11T11:30:25Z",
      "level": "warning",
      "message": "Strategy signal rejected due to high spread",
      "details": {
        "symbol": "USDJPY",
        "strategy": "Bollinger Band Breakouts",
        "spread": 5.2,
        "max_allowed": 4.0
      }
    }
  ]
}
```

#### Configure Notifications

```
PUT /notifications/config
```

Updates notification settings.

**Request**:

```json
{
  "email": {
    "enabled": true,
    "address": "trader@example.com",
    "events": ["trade_open", "trade_close", "error"]
  },
  "mobile_push": {
    "enabled": true,
    "device_id": "d8e8fca2dc0f896fd7cb4cb0031ba249",
    "events": ["trade_open", "trade_close", "warning", "error"]
  },
  "telegram": {
    "enabled": true,
    "chat_id": "123456789",
    "events": ["trade_open", "trade_close", "daily_summary"]
  }
}
```

**Response**:

```json
{
  "success": true,
  "message": "Notification settings updated successfully",
  "updated_at": "2025-04-11T13:30:45Z"
}
```

## Error Handling

The API uses standard HTTP status codes to indicate the success or failure of requests:

- `200 OK`: The request was successful
- `201 Created`: The resource was successfully created
- `400 Bad Request`: The request was invalid
- `401 Unauthorized`: Authentication failed
- `403 Forbidden`: The request is forbidden
- `404 Not Found`: The resource was not found
- `422 Unprocessable Entity`: The request was well-formed but contains semantic errors
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: An error occurred on the server

Error responses include a JSON body with details:

```json
{
  "error": {
    "code": "invalid_parameter",
    "message": "Invalid value for parameter 'volume'",
    "details": "Volume must be greater than 0.01 and a multiple of 0.01",
    "request_id": "req_7c89fb27a8d64e9b9f17c69c9476e9c1"
  }
}
```

## Webhook Integration

You can register webhook URLs to receive real-time notifications of trading events.

### Register Webhook

```
POST /webhooks
```

**Request**:

```json
{
  "url": "https://your-server.com/webhook",
  "events": ["trade_open", "trade_close", "trade_modify"],
  "secret": "your_webhook_secret"
}
```

**Response**:

```json
{
  "id": "wh_123456",
  "url": "https://your-server.com/webhook",
  "events": ["trade_open", "trade_close", "trade_modify"],
  "created_at": "2025-04-11T13:35:20Z",
  "status": "active"
}
```

Webhook payloads are signed with your webhook secret using HMAC SHA-256. The signature is included in the `X-Webhook-Signature` header.

## SDK Libraries

Official SDK libraries are available for the following programming languages:

- [Python](https://github.com/forex-trading-bot/python-sdk)
- [JavaScript/Node.js](https://github.com/forex-trading-bot/node-sdk)
- [Java](https://github.com/forex-trading-bot/java-sdk)
- [C#](https://github.com/forex-trading-bot/dotnet-sdk)

## API Changelog

### v1.3.0 (2025-03-15)
- Added market condition analysis endpoint
- Enhanced performance statistics
- Added support for strategy-specific configuration

### v1.2.0 (2025-02-01)
- Added webhook integration
- Improved rate limiting with more detailed headers
- Added multi-asset trading support

### v1.1.0 (2025-01-10)
- Added notification configuration endpoints
- Enhanced authentication with HMAC signatures
- Added detailed trade history filtering

### v1.0.0 (2024-12-15)
- Initial API release

## Support

If you encounter any issues or have questions about the API, please contact:

- Email: api-support@forextradingbot.com
- Support Portal: https://support.forextradingbot.com
- Documentation: https://docs.forextradingbot.com
