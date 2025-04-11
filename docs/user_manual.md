# Forex Trading Bot User Manual

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
   - [System Requirements](#system-requirements)
   - [Installation](#installation)
   - [Initial Configuration](#initial-configuration)
3. [Dashboard Overview](#dashboard-overview)
4. [Trading Strategies](#trading-strategies)
   - [MA + RSI Combo Strategy](#ma--rsi-combo-strategy)
   - [Stochastic Cross Strategy](#stochastic-cross-strategy)
   - [Break and Retest Strategy](#break-and-retest-strategy)
   - [JHook Pattern Strategy](#jhook-pattern-strategy)
5. [Market Condition Detection](#market-condition-detection)
6. [Multi-Asset Trading](#multi-asset-trading)
7. [Risk Management](#risk-management)
8. [Monitoring and Alerts](#monitoring-and-alerts)
9. [Performance Analysis](#performance-analysis)
10. [Backup and Recovery](#backup-and-recovery)
11. [Troubleshooting](#troubleshooting)
12. [API Integration](#api-integration)
13. [FAQ](#faq)
14. [Support and Contact](#support-and-contact)

## Introduction

The Forex Trading Bot is an automated trading system designed for the foreign exchange market. It employs sophisticated algorithmic strategies to identify trading opportunities, execute trades, and manage risk across multiple currency pairs and synthetic indices.

This user manual provides comprehensive information on how to set up, configure, operate, and maintain the trading bot for optimal performance.

## Getting Started

### System Requirements

**Minimum Requirements:**
- Operating System: Windows 10/11, Ubuntu 20.04/22.04, or macOS 12+
- Processor: Intel Core i5 (8th gen or newer) or AMD Ryzen 5
- Memory: 8GB RAM
- Storage: 50GB free space
- Internet: Stable connection, 10+ Mbps
- MetaTrader 5 terminal installed

**Recommended Specifications:**
- Processor: Intel Core i7/i9 or AMD Ryzen 7/9
- Memory: 16GB RAM or higher
- Storage: 100GB+ SSD
- Internet: Dedicated connection, 50+ Mbps

### Installation

#### Local Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-repository/forex-trading-bot.git
   cd forex-trading-bot
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install MetaTrader 5 Python package:**
   ```bash
   pip install MetaTrader5
   ```

5. **Configure your MetaTrader 5 credentials in the configuration file:**
   Edit `config/mt5_config.yaml` with your account details.

#### VPS Installation

For production environments, we recommend using a Virtual Private Server (VPS). The repository includes a setup script for automated deployment:

1. **SSH into your VPS**

2. **Clone the repository:**
   ```bash
   git clone https://github.com/your-repository/forex-trading-bot.git
   cd forex-trading-bot
   ```

3. **Run the setup script:**
   ```bash
   chmod +x scripts/setup_vps.sh
   ./scripts/setup_vps.sh
   ```

The script will install all required dependencies, set up a dedicated user, configure Supervisor for process management, and set up NGINX as a reverse proxy.

### Initial Configuration

1. **Open the configuration directory:**
   ```
   config/
   ├── mt5_config.yaml          # MetaTrader 5 connection and account settings
   ├── trading_config.yaml      # Strategy parameters and risk management
   ├── market_conditions.yaml   # Market condition detection settings
   ├── multi_asset_config.yaml  # Multi-asset trading configuration
   ├── monitoring_config.yaml   # Monitoring and alert settings
   └── api_config.yaml          # API server configuration
   ```

2. **Edit `mt5_config.yaml` with your MT5 credentials:**
   ```yaml
   connection:
     server: "YourBrokerServer"
     login: 12345678
     password: "YourPassword"
     timeout: 60000
   
   symbols:
     - name: "EURUSD"
       enabled: true
       timeframes: ["M5", "M15", "H1"]
     - name: "GBPUSD"
       enabled: true
       timeframes: ["M5", "M15", "H1"]
     # Add more symbols as needed
   ```

3. **Configure risk management in `trading_config.yaml`:**
   ```yaml
   risk_management:
     max_risk_per_trade: 0.01  # 1% of account balance
     max_daily_risk: 0.05      # 5% of account balance
     max_open_trades: 5
     max_trades_per_symbol: 2
     stop_loss_pips: 30
     use_trailing_stop: true
   ```

4. **Start the trading bot:**
   ```bash
   python run_bot.py
   ```

## Dashboard Overview

The trading bot provides a web-based dashboard accessible at `http://localhost:8000` (or your server's IP address). The dashboard is divided into several sections:

### Main Dashboard
![Dashboard](images/dashboard.png)

1. **Account Summary**: Displays account balance, equity, margin, and daily P&L
2. **Open Positions**: Lists all open trades with essential details
3. **Performance Charts**: Visual representation of trading performance
4. **Strategy Performance**: Comparison of different strategies' results
5. **Market Overview**: Quick view of monitored symbols and their trend status

### Navigation Menu

- **Dashboard**: Main overview screen
- **Trades**: Detailed history of all trades
- **Strategies**: Configure and monitor individual strategies
- **Market Analysis**: In-depth market condition analysis
- **Performance**: Detailed performance metrics and reports
- **Settings**: System configuration options
- **Logs**: System and trading logs

## Trading Strategies

The bot includes four primary trading strategies, each with its own strengths and optimal market conditions.

### MA + RSI Combo Strategy

This strategy combines Moving Averages (MA) and the Relative Strength Index (RSI) to identify trend direction and potential entry points.

#### How It Works

1. Uses two Moving Averages (fast and slow) to determine trend direction
2. RSI is used to identify overbought/oversold conditions
3. Generates buy signals when:
   - Fast MA crosses above Slow MA (uptrend)
   - RSI recovers from oversold territory
4. Generates sell signals when:
   - Fast MA crosses below Slow MA (downtrend)
   - RSI recovers from overbought territory

#### Configuration

In `trading_config.yaml`:

```yaml
strategies:
  ma_rsi:
    enabled: true
    timeframes: ["M15", "H1"]
    symbols: ["EURUSD", "GBPUSD", "USDJPY"]
    parameters:
      fast_ma_period: 9
      fast_ma_type: "EMA"
      slow_ma_period: 21
      slow_ma_type: "EMA"
      rsi_period: 14
      rsi_overbought: 70
      rsi_oversold: 30
```

#### Optimal Market Conditions

- Trending markets with clear directional movement
- Medium volatility environments
- Best during London and New York trading sessions

### Stochastic Cross Strategy

Uses the Stochastic oscillator to identify potential reversal points in the market.

#### How It Works

1. Monitors the crossovers of the Stochastic %K and %D lines
2. Generates buy signals when:
   - %K crosses above %D
   - Both lines are below the oversold threshold
3. Generates sell signals when:
   - %K crosses below %D
   - Both lines are above the overbought threshold

#### Configuration

```yaml
strategies:
  stochastic_cross:
    enabled: true
    timeframes: ["M5", "M15"]
    symbols: ["EURUSD", "GBPUSD", "AUDUSD"]
    parameters:
      k_period: 5
      d_period: 3
      slowing: 3
      overbought: 80
      oversold: 20
```

#### Optimal Market Conditions

- Ranging markets with clear support and resistance levels
- Low to medium volatility environments
- Works well during Asian trading session

### Break and Retest Strategy

This strategy capitalizes on breakouts from key support and resistance levels, entering trades after a price retest of the broken level.

#### How It Works

1. Identifies key support and resistance levels using recent swing highs/lows
2. Detects when price breaks through these levels
3. Waits for a retest of the broken level
4. Enters the trade in the direction of the breakout if the retest holds

#### Configuration

```yaml
strategies:
  break_and_retest:
    enabled: true
    timeframes: ["H1", "H4"]
    symbols: ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
    parameters:
      swing_lookback: 20
      min_level_touches: 2
      retest_zone_pips: 10
      minimum_pip_range: 30
```

#### Optimal Market Conditions

- Markets with clear support/resistance levels
- Medium to high volatility
- News-driven breakouts
- Major session opens (London/New York)

### JHook Pattern Strategy

The JHook pattern is a reversal pattern that forms after a strong trend move, signaling a potential trend reversal.

#### How It Works

1. Identifies a strong trend move (J-shape)
2. Looks for a retracement that forms a hook pattern
3. Enters in the direction of the expected new trend when price action confirms the reversal

#### Configuration

```yaml
strategies:
  jhook_pattern:
    enabled: true
    timeframes: ["H1", "H4", "D1"]
    symbols: ["EURUSD", "GBPUSD", "USDJPY"]
    parameters:
      trend_strength_threshold: 0.7
      min_trend_bars: 10
      hook_depth_ratio: 0.38
      confirmation_candles: 2
```

#### Optimal Market Conditions

- After extended trends
- During major fundamental shifts
- Higher timeframes (H1, H4, D1)
- Medium to high volatility

## Market Condition Detection

The trading bot includes an advanced market condition detection system that analyzes current market conditions and selects the most appropriate trading strategy.

### Key Features

- Trend analysis (bullish, bearish, ranging, choppy)
- Volatility measurement (low, medium, high)
- Liquidity condition estimation
- Session overlap detection
- Strategy recommendation based on current conditions

### How It's Used

1. The system continuously monitors market conditions for all configured symbols
2. Based on the detected conditions, it:
   - Activates appropriate strategies
   - Adjusts position sizing based on volatility
   - Filters out unfavorable trading environments
   - Provides confidence scores for potential trades

### Configuration

In `market_conditions.yaml`:

```yaml
market_condition_detector:
  update_interval_minutes: 15
  
  trend_analysis:
    ema_periods: [20, 50, 100]
    adx_period: 14
    adx_threshold: 25
    
  volatility_analysis:
    atr_period: 14
    low_volatility_percentile: 30
    high_volatility_percentile: 70
    
  liquidity_analysis:
    volume_lookback_periods: 20
    tick_volume_threshold: 500
    
  confidence_thresholds:
    minimum_trade_confidence: 0.65
    high_confidence_level: 0.85
```

## Multi-Asset Trading

The bot supports trading across multiple asset classes, including Forex pairs and synthetic indices, with correlation management to prevent over-exposure.

### Features

- Trading across multiple currency pairs
- Support for synthetic indices
- Correlation analysis to prevent similar trades
- Session-aware trading (Asian, London, New York)
- Portfolio optimization and position sizing

### Configuration

In `multi_asset_config.yaml`:

```yaml
correlation_management:
  max_correlation_threshold: 0.7
  update_interval_hours: 24
  correlation_window_days: 30
  predefined_groups:
    - name: "USD Group"
      symbols: ["EURUSD", "GBPUSD", "AUDUSD", "USDJPY"]
    - name: "EUR Group"
      symbols: ["EURUSD", "EURGBP", "EURJPY", "EURAUD"]

session_management:
  sessions:
    asian:
      start: "22:00"
      end: "08:00"
      timezone: "UTC"
    london:
      start: "08:00"
      end: "16:00"
      timezone: "UTC"
    new_york:
      start: "13:00"
      end: "22:00"
      timezone: "UTC"
  
  session_preferences:
    ma_rsi:
      - "london"
      - "new_york"
    stochastic_cross:
      - "asian"
      - "london"
    break_and_retest:
      - "london"
      - "new_york"
    jhook_pattern:
      - "all"
```

## Risk Management

The bot includes comprehensive risk management features to protect your capital.

### Features

1. **Position Sizing**: Automatically calculates position size based on:
   - Account balance
   - Maximum risk per trade
   - Stop loss distance
   - Current market volatility

2. **Risk Limits**:
   - Maximum risk per trade (% of balance)
   - Maximum daily risk limit
   - Maximum drawdown protection
   - Maximum open trades
   - Maximum correlated exposure

3. **Stop Loss Management**:
   - Fixed stop loss
   - Volatility-based stop loss (ATR)
   - Trailing stops
   - Break-even automation

4. **Circuit Breakers**:
   - Daily loss limit
   - Consecutive loss counter
   - Unusual market condition detection
   - News event avoidance

### Configuration

In `trading_config.yaml`:

```yaml
risk_management:
  position_sizing:
    method: "percent_risk"  # Options: fixed_lot, percent_risk, volatility_adjusted
    risk_per_trade: 0.01    # 1% of account balance
    min_lot: 0.01
    max_lot: 5.0
    
  risk_limits:
    max_daily_risk: 0.05    # 5% of account balance
    max_drawdown_percent: 0.15  # 15% drawdown
    max_open_trades: 5
    max_trades_per_symbol: 2
    
  stop_loss:
    default_type: "fixed"   # Options: fixed, atr, support_resistance
    fixed_pip_value: 30
    atr_multiplier: 2.0
    atr_period: 14
    trailing_stop: true
    trailing_activation_pips: 15
    break_even_pips: 20
    
  circuit_breakers:
    daily_loss_limit_percent: 0.03  # Stop trading after 3% daily loss
    max_consecutive_losses: 5
    pause_minutes_after_hits: 240  # 4 hours pause
```

## Monitoring and Alerts

The trading bot includes a comprehensive monitoring system that keeps you informed about its operation and performance.

### Monitoring Features

1. **System Monitoring**:
   - CPU and memory usage
   - Disk space
   - Network connectivity
   - Service status

2. **Trading Monitoring**:
   - Account balance and equity
   - Open positions
   - Pending orders
   - Daily P&L
   - Strategy performance

3. **Market Monitoring**:
   - Price movements
   - Volatility changes
   - Liquidity conditions
   - Unusual market activity

### Alert Types

1. **Email Alerts**: Receive important notifications via email
2. **Mobile Push Notifications**: Get alerts on your mobile device
3. **Telegram Notifications**: Real-time updates via Telegram
4. **Dashboard Alerts**: Visual notifications in the web dashboard
5. **SMS Alerts**: Text message notifications for critical events

### Alert Configuration

In `monitoring_config.yaml`:

```yaml
alerts:
  email:
    enabled: true
    server: "smtp.example.com"
    port: 587
    username: "alerts@yourdomin.com"
    password: "your_password"
    recipient: "your-email@example.com"
    
  telegram:
    enabled: true
    token: "your_telegram_bot_token"
    chat_id: "your_chat_id"
    
  mobile_push:
    enabled: true
    service: "pushover" # Options: pushover, pushbullet
    api_key: "your_api_key"
    user_key: "your_user_key"
    
  sms:
    enabled: false
    service: "twilio"
    account_sid: "your_twilio_account_sid"
    auth_token: "your_twilio_auth_token"
    from_number: "+1234567890"
    to_number: "+1234567890"

alert_triggers:
  trade_opened:
    channels: ["telegram", "dashboard"]
    
  trade_closed:
    channels: ["telegram", "dashboard", "email"]
    include_details: true
    
  daily_summary:
    channels: ["email", "telegram"]
    time: "22:00"
    timezone: "UTC"
    
  system_warnings:
    channels: ["telegram", "email", "sms"]
    
  critical_errors:
    channels: ["telegram", "email", "sms", "mobile_push"]
    repeat_interval_minutes: 30
```

## Performance Analysis

The bot includes comprehensive tools for analyzing trading performance and optimizing strategies.

### Performance Metrics

1. **Profitability Metrics**:
   - Total profit/loss
   - Win rate (%)
   - Profit factor
   - Average win/loss
   - Return on investment (ROI)

2. **Risk Metrics**:
   - Maximum drawdown
   - Sharpe ratio
   - Sortino ratio
   - Risk-reward ratio
   - Value at Risk (VaR)

3. **Strategy Metrics**:
   - Performance by strategy
   - Performance by symbol
   - Performance by time of day/session
   - Performance by market condition

### Analysis Tools

The dashboard provides various analysis tools:

1. **Performance Dashboard**: Overview of key metrics
2. **Equity Curve**: Visual representation of account growth
3. **Drawdown Chart**: Visualization of drawdowns over time
4. **Trade Distribution**: Analysis of trade distribution
5. **Strategy Comparison**: Compare performance across strategies
6. **Timeframe Analysis**: Performance across different timeframes
7. **Optimization Tools**: Parameter optimization for strategies

### Reports

The system generates various reports:

1. **Daily Summary**: End-of-day trading summary
2. **Weekly Report**: Comprehensive weekly performance analysis
3. **Monthly Report**: Monthly performance review
4. **Strategy Report**: Detailed analysis of strategy performance
5. **Custom Reports**: Create custom reports based on specific criteria

## Backup and Recovery

The trading bot includes comprehensive backup and recovery procedures to ensure data integrity and business continuity.

### Backup Features

1. **Automatic Backups**:
   - Daily configuration backups
   - Trading database backups
   - Performance metrics backups
   - System logs backups

2. **Backup Storage**:
   - Local storage
   - Remote storage (optional)
   - Cloud storage (optional)

3. **Backup Verification**:
   - Automatic integrity checking
   - Restoration testing

### Recovery Procedures

Detailed recovery procedures are provided in the `docs/disaster_recovery.md` document, covering:

1. **Server Failure Recovery**
2. **Database Corruption Recovery**
3. **MT5 Connection Loss Recovery**
4. **API Service Failure Recovery**
5. **Data Breach Recovery**

## Troubleshooting

### Common Issues

#### Connection Problems

**Issue**: The bot cannot connect to the MetaTrader 5 terminal.

**Solution**:
1. Ensure MT5 is running and logged in
2. Verify the credentials in `mt5_config.yaml`
3. Check for any firewall blocking the connection
4. Restart the MT5 terminal
5. Check the connection logs at `logs/mt5_connector.log`

#### Trading Issues

**Issue**: The bot identifies signals but doesn't execute trades.

**Solution**:
1. Check if trading is enabled in the dashboard
2. Verify that risk management limits are not being exceeded
3. Check if there are any active circuit breakers
4. Verify sufficient margin in your trading account
5. Check the trading logs at `logs/trading.log`

#### Performance Issues

**Issue**: The bot is running slowly or using excessive system resources.

**Solution**:
1. Reduce the number of monitored symbols
2. Increase the timeframe analysis interval
3. Disable unused strategies
4. Check for and kill any orphaned processes
5. Verify system meets minimum requirements

#### API Issues

**Issue**: Cannot connect to the bot's API server.

**Solution**:
1. Verify the API server is running (`systemctl status forex-api-server`)
2. Check API logs at `logs/api_server.log`
3. Verify firewall settings allow connections to the API port
4. Check for correct API keys and authentication
5. Restart the API server

### Logs

The system maintains several log files to help with troubleshooting:

1. **Main Bot Log**: `logs/forex_trading_bot.log`
2. **MT5 Connector Log**: `logs/mt5_connector.log`
3. **Trading Log**: `logs/trading.log`
4. **API Server Log**: `logs/api_server.log`
5. **Error Log**: `logs/error.log`

### Support Resources

For additional troubleshooting help:

1. Consult the [Troubleshooting Guide](docs/troubleshooting_guide.md)
2. Check the [FAQ Section](#faq)
3. Contact [Technical Support](#support-and-contact)

## API Integration

The trading bot provides a comprehensive API for integration with external systems. See the [API Documentation](docs/api_documentation.md) for details.

### Key API Features

1. **Account Management**: Access account information and trading history
2. **Trading Operations**: Place, modify, and close trades
3. **Market Data**: Access price data and market conditions
4. **Bot Management**: Control and configure the trading bot
5. **Performance Monitoring**: Access performance metrics and logs

### Integration Examples

The API documentation includes integration examples for various programming languages:

1. **Python**: Example scripts for common operations
2. **JavaScript**: Node.js integration examples
3. **Java**: Java integration examples
4. **C#**: .NET integration examples

## FAQ

### General Questions

#### Q: Can the bot run without an internet connection?
**A**: No, the bot requires a stable internet connection to communicate with the MT5 terminal and execute trades.

#### Q: Does the bot work with MetaTrader 4?
**A**: No, the bot is designed specifically for MetaTrader 5. There are no plans for MT4 support.

#### Q: Can I run the bot on a cloud server?
**A**: Yes, we recommend running the bot on a VPS for 24/7 operation. The setup script included in the repository automates the deployment process.

### Trading Questions

#### Q: How many currency pairs can the bot trade simultaneously?
**A**: The bot can monitor and trade as many currency pairs as configured. However, for optimal performance, we recommend limiting to 5-10 major pairs.

#### Q: Can I use my existing trading strategies with the bot?
**A**: Currently, the bot supports four built-in strategies. Custom strategy integration is planned for a future release.

#### Q: Does the bot work in all market conditions?
**A**: The bot includes a market condition detection system that adapts to different market conditions by selecting appropriate strategies and adjusting risk parameters.

### Performance Questions

#### Q: What kind of returns can I expect?
**A**: Trading performance depends on many factors including market conditions, risk settings, and strategy configuration. The bot is designed to provide consistent, risk-managed trading, not guaranteed returns.

#### Q: How often does the bot trade?
**A**: The trading frequency depends on the configured strategies, timeframes, and market conditions. It can range from several trades per day to a few trades per week.

### Security Questions

#### Q: Is my trading account information secure?
**A**: Yes, your account credentials are stored locally in encrypted configuration files. The bot does not transmit your credentials to any external servers.

#### Q: Can I limit the bot's ability to trade?
**A**: Yes, you can configure maximum position sizes, risk limits, and circuit breakers to control the bot's trading activity.

## Support and Contact

For additional support:

- **Email**: support@forextradingbot.com
- **Website**: https://www.forextradingbot.com/support
- **Documentation**: https://docs.forextradingbot.com
- **GitHub Issues**: https://github.com/your-repository/forex-trading-bot/issues

---

**Last Updated**: YYYY-MM-DD  
**Version**: 1.0.0  
**Author**: Your Company Name
