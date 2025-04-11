# Forex Trading Bot System Architecture

This document provides a detailed overview of the Forex Trading Bot system architecture, including component relationships, data flows, and technical implementation details.

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Components](#core-components)
3. [Component Interactions](#component-interactions)
4. [Database Schema](#database-schema)
5. [API Architecture](#api-architecture)
6. [Infrastructure Design](#infrastructure-design)
7. [Security Architecture](#security-architecture)
8. [Scalability Design](#scalability-design)
9. [Monitoring and Observability](#monitoring-and-observability)
10. [Deployment Architecture](#deployment-architecture)

## System Overview

The Forex Trading Bot is a comprehensive automated trading system that connects to the MetaTrader 5 platform to execute forex and synthetic indices trades based on various technical strategies. The system is designed with a modular architecture to maximize flexibility, reliability, and performance.

### High-Level Architecture Diagram

```
┌─────────────────────────┐      ┌─────────────────────┐
│                         │      │                     │
│   MetaTrader 5          │◄────►│  MT5 Connector      │
│   Trading Platform      │      │                     │
│                         │      └──────────┬──────────┘
└─────────────────────────┘                 │
                                           │
                                           ▼
┌─────────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│                         │      │                     │      │                     │
│   Mobile App            │◄────►│  API Server         │◄────►│  Trading Engine     │
│   (Flutter)             │      │  (Flask/FastAPI)    │      │                     │
│                         │      │                     │      └──────────┬──────────┘
└─────────────────────────┘      └──────────┬──────────┘                 │
                                           │                            │
                                           ▼                            ▼
                                  ┌─────────────────────┐      ┌─────────────────────┐
                                  │                     │      │                     │
                                  │  Database           │◄────►│  Strategy Engine    │
                                  │  (PostgreSQL)       │      │                     │
                                  │                     │      └──────────┬──────────┘
                                  └─────────────────────┘                 │
                                                                         │
┌─────────────────────────┐      ┌─────────────────────┐                 │
│                         │      │                     │                 │
│  Monitoring Stack       │◄────►│  Market Condition   │◄────────────────┘
│  (Prometheus/Grafana)   │      │  Detector           │
│                         │      │                     │
└─────────────────────────┘      └─────────────────────┘
```

### System Requirements

- **Performance**: Sub-second decision-making for scalping strategies
- **Reliability**: 99.9% uptime with failure detection and recovery
- **Security**: Encrypted communications, secure authentication, and API key management
- **Scalability**: Ability to handle multiple currency pairs and synthetic indices simultaneously
- **Observability**: Comprehensive monitoring and alerting capabilities

## Core Components

### 1. MT5 Connector

**Purpose**: Provides a bridge between the Trading Engine and the MetaTrader 5 platform.

**Key Responsibilities**:
- Establish and maintain connection to MT5 platform
- Retrieve market data (price quotes, indicators)
- Execute trading orders (market/limit/stop orders)
- Monitor open positions and account status

**Technologies**:
- Python MetaTrader 5 package
- ZeroMQ for interprocess communication
- Connection pooling for reliability

**Code Structure**:
```
src/
  connectors/
    mt5_connector.py   # Main connector implementation
    mt5_data_types.py  # Data models for MT5 communication
    connection_pool.py # Connection management
```

### 2. Trading Engine

**Purpose**: Core component that coordinates trading activities, risk management, and strategy execution.

**Key Responsibilities**:
- Orchestrate the trading workflow
- Implement position management
- Apply risk management rules
- Track and record trading performance
- Coordinate with Strategy Engine for signal generation

**Technologies**:
- Python asyncio for concurrent operations
- Event-driven architecture
- State machine for trading lifecycle

**Code Structure**:
```
src/
  engine/
    trading_engine.py       # Main engine implementation
    position_manager.py     # Position and order management 
    risk_manager.py         # Risk calculations and limits
    execution_manager.py    # Order execution details
    event_dispatcher.py     # Trading event handling
```

### 3. Strategy Engine

**Purpose**: Implements and executes various trading strategies to generate entry and exit signals.

**Key Responsibilities**:
- Analyze market data
- Apply technical indicators
- Generate trading signals
- Optimize strategy parameters
- Recommend optimal position sizing

**Technologies**:
- NumPy and Pandas for data analysis
- TA-Lib for technical indicators
- Vectorized operations for performance

**Code Structure**:
```
src/
  strategies/
    base_strategy.py            # Strategy interface
    ma_rsi_strategy.py          # Moving Average + RSI strategy
    stochastic_cross_strategy.py # Stochastic oscillator strategy
    break_and_retest_strategy.py # Price action strategy
    jhook_pattern_strategy.py    # J-Hook pattern strategy
    strategy_manager.py          # Strategy orchestration
```

### 4. Market Condition Detector

**Purpose**: Analyzes market conditions to determine optimal trading environments and strategy selection.

**Key Responsibilities**:
- Detect market trends (bullish, bearish, ranging)
- Measure volatility levels
- Identify liquidity conditions
- Calculate trading session activity
- Determine favorable trading conditions

**Technologies**:
- Statistical analysis libraries
- Pattern recognition algorithms
- Time series analysis

**Code Structure**:
```
src/
  market_condition/
    market_condition_detector.py  # Core detection logic
    trend_analyzer.py             # Trend analysis components
    volatility_analyzer.py        # Volatility measurements
    liquidity_analyzer.py         # Liquidity assessments
    session_analyzer.py           # Trading session analysis
```

### 5. API Server

**Purpose**: Provides HTTP and WebSocket interfaces for external communication with the trading system.

**Key Responsibilities**:
- Expose REST endpoints for system control
- Stream real-time data via WebSockets
- Handle authentication and authorization
- Implement rate limiting and security measures

**Technologies**:
- Flask/FastAPI for REST endpoints
- Socket.IO for real-time communication
- JWT for authentication
- OpenAPI for documentation

**Code Structure**:
```
src/
  api/
    app.py                # Main application entry point
    routes/
      auth_routes.py      # Authentication endpoints
      trade_routes.py     # Trading-related endpoints
      system_routes.py    # System configuration endpoints
      data_routes.py      # Market data endpoints
    middleware/
      auth_middleware.py  # Authentication middleware
      rate_limiter.py     # API rate limiting
    websockets/
      socket_manager.py   # WebSocket implementation
```

### 6. Database

**Purpose**: Persistent storage for trading data, configuration, and performance metrics.

**Key Responsibilities**:
- Store trading history and performance
- Maintain system configuration
- Track user preferences
- Record audit logs
- Store market data for analysis

**Technologies**:
- PostgreSQL for relational data
- SQLAlchemy for ORM
- Alembic for migrations
- Connection pooling for performance

**Code Structure**:
```
src/
  database/
    models/
      trade.py          # Trade data models
      strategy.py       # Strategy configuration models
      performance.py    # Performance metrics models
      user.py           # User data models
    database.py         # Database connection management
    repositories/
      trade_repo.py     # Trade data access
      strategy_repo.py  # Strategy data access
    migrations/         # Alembic migration scripts
```

### 7. Mobile App

**Purpose**: Provides a user interface for monitoring and controlling the trading system.

**Key Responsibilities**:
- Display real-time trading activity
- Show performance metrics and statistics
- Allow strategy configuration
- Provide alert notifications
- Display market analysis

**Technologies**:
- Flutter for cross-platform development
- Provider pattern for state management
- HTTP and WebSocket for API communication

**Code Structure**:
```
mobile/
  lib/
    screens/
      dashboard_screen.dart   # Main dashboard
      trades_screen.dart      # Trade history and details
      settings_screen.dart    # System configuration
      analysis_screen.dart    # Market analysis
    services/
      api_service.dart        # API communication
      auth_service.dart       # Authentication
      websocket_service.dart  # Real-time data
    models/
      trade_model.dart        # Data models
      performance_model.dart  # Performance data
    widgets/
      chart_widgets.dart      # Charting components
      trade_widgets.dart      # Trade display components
```

### 8. Monitoring Stack

**Purpose**: Provides system monitoring, alerting, and performance tracking.

**Key Responsibilities**:
- Track system health metrics
- Monitor trading performance
- Alert on system anomalies
- Visualize performance data
- Record system logs

**Technologies**:
- Prometheus for metrics collection
- Grafana for visualization
- Alertmanager for alerting
- ELK stack for log management

**Configuration Structure**:
```
config/
  prometheus.yml         # Prometheus configuration
  alertmanager.yml       # Alertmanager configuration
  forex_trading_bot_rules.yml # Alert rules
  grafana/
    dashboards/
      system_dashboard.json   # System monitoring
      trading_dashboard.json  # Trading performance
```

## Component Interactions

### Trading Workflow

1. **Market Data Flow**:
   ```
   MT5 Platform → MT5 Connector → Trading Engine → Strategy Engine → Signal Generation
   ```

2. **Order Execution Flow**:
   ```
   Strategy Engine → Trading Engine → MT5 Connector → MT5 Platform
   ```

3. **Market Condition Analysis Flow**:
   ```
   MT5 Connector → Market Condition Detector → Trading Engine → Strategy Selection
   ```

4. **API Request Flow**:
   ```
   Mobile App → API Server → Trading Engine → Database
   ```

5. **Real-time Updates Flow**:
   ```
   Trading Engine → API Server (WebSockets) → Mobile App
   ```

### Communication Methods

1. **Internal Component Communication**:
   - Message queues for asynchronous communication
   - Event-driven architecture for real-time responses
   - Direct function calls for synchronous operations

2. **External API Communication**:
   - RESTful HTTP endpoints with JSON payloads
   - WebSockets for real-time data streaming
   - JWT tokens for authentication

3. **Data Persistence**:
   - Database transactions for ACID compliance
   - Connection pooling for efficient database access
   - Repository pattern for data access abstraction

## Database Schema

### Core Tables

1. **Trades Table**:
   ```sql
   CREATE TABLE trades (
       trade_id SERIAL PRIMARY KEY,
       symbol VARCHAR(20) NOT NULL,
       direction VARCHAR(10) NOT NULL,  -- 'buy' or 'sell'
       open_time TIMESTAMP NOT NULL,
       close_time TIMESTAMP,
       open_price DECIMAL(10, 5) NOT NULL,
       close_price DECIMAL(10, 5),
       volume DECIMAL(10, 2) NOT NULL,
       sl_price DECIMAL(10, 5),
       tp_price DECIMAL(10, 5),
       profit DECIMAL(10, 2),
       status VARCHAR(10) NOT NULL,  -- 'open', 'closed', 'cancelled'
       strategy VARCHAR(50) NOT NULL,
       market_condition JSON,
       execution_details JSON,
       notes TEXT
   );
   
   CREATE INDEX idx_trades_symbol ON trades(symbol);
   CREATE INDEX idx_trades_open_time ON trades(open_time);
   CREATE INDEX idx_trades_strategy ON trades(strategy);
   CREATE INDEX idx_trades_status ON trades(status);
   ```

2. **Performance Metrics Table**:
   ```sql
   CREATE TABLE performance_metrics (
       metric_id SERIAL PRIMARY KEY,
       timestamp TIMESTAMP NOT NULL,
       strategy VARCHAR(50),
       symbol VARCHAR(20),
       win_count INTEGER,
       loss_count INTEGER,
       profit_sum DECIMAL(10, 2),
       loss_sum DECIMAL(10, 2),
       win_rate DECIMAL(5, 2),
       profit_factor DECIMAL(5, 2),
       expectancy DECIMAL(5, 2),
       drawdown_percent DECIMAL(5, 2),
       sharpe_ratio DECIMAL(5, 2),
       period VARCHAR(20)  -- 'daily', 'weekly', 'monthly'
   );
   
   CREATE INDEX idx_perf_timestamp ON performance_metrics(timestamp);
   CREATE INDEX idx_perf_strategy ON performance_metrics(strategy);
   CREATE INDEX idx_perf_symbol ON performance_metrics(symbol);
   ```

3. **Market Data Table**:
   ```sql
   CREATE TABLE market_data (
       data_id SERIAL PRIMARY KEY,
       symbol VARCHAR(20) NOT NULL,
       timestamp TIMESTAMP NOT NULL,
       timeframe VARCHAR(10) NOT NULL,
       open DECIMAL(10, 5) NOT NULL,
       high DECIMAL(10, 5) NOT NULL,
       low DECIMAL(10, 5) NOT NULL,
       close DECIMAL(10, 5) NOT NULL,
       volume DECIMAL(10, 2) NOT NULL,
       spread DECIMAL(5, 1),
       indicators JSON
   );
   
   CREATE INDEX idx_market_data_symbol_time ON market_data(symbol, timestamp);
   CREATE INDEX idx_market_data_timeframe ON market_data(timeframe);
   ```

4. **System Configuration Table**:
   ```sql
   CREATE TABLE system_config (
       config_id SERIAL PRIMARY KEY,
       config_name VARCHAR(50) UNIQUE NOT NULL,
       config_value JSON NOT NULL,
       last_updated TIMESTAMP NOT NULL,
       updated_by VARCHAR(50),
       description TEXT
   );
   ```

5. **Strategies Configuration Table**:
   ```sql
   CREATE TABLE strategy_config (
       strategy_id SERIAL PRIMARY KEY,
       strategy_name VARCHAR(50) NOT NULL,
       is_active BOOLEAN NOT NULL DEFAULT TRUE,
       parameters JSON NOT NULL,
       symbols JSON NOT NULL,
       timeframes JSON NOT NULL,
       risk_multiplier DECIMAL(3, 2) NOT NULL DEFAULT 1.0,
       last_updated TIMESTAMP NOT NULL,
       notes TEXT
   );
   
   CREATE UNIQUE INDEX idx_strategy_name ON strategy_config(strategy_name);
   ```

6. **System Logs Table**:
   ```sql
   CREATE TABLE system_logs (
       log_id SERIAL PRIMARY KEY,
       timestamp TIMESTAMP NOT NULL,
       level VARCHAR(10) NOT NULL,
       component VARCHAR(50) NOT NULL,
       message TEXT NOT NULL,
       details JSON
   );
   
   CREATE INDEX idx_logs_timestamp ON system_logs(timestamp);
   CREATE INDEX idx_logs_level ON system_logs(level);
   CREATE INDEX idx_logs_component ON system_logs(component);
   ```

7. **Users Table**:
   ```sql
   CREATE TABLE users (
       user_id SERIAL PRIMARY KEY,
       username VARCHAR(50) UNIQUE NOT NULL,
       password_hash VARCHAR(128) NOT NULL,
       email VARCHAR(100) UNIQUE NOT NULL,
       is_active BOOLEAN NOT NULL DEFAULT TRUE,
       role VARCHAR(20) NOT NULL DEFAULT 'user',
       last_login TIMESTAMP,
       created_at TIMESTAMP NOT NULL,
       preferences JSON
   );
   ```

## API Architecture

### Authentication

- **JWT-based authentication**
- **Refresh token pattern** for extended sessions
- **API key authentication** for programmatic access

### HTTP Endpoints

#### Authentication API
```
POST   /api/auth/login              # User login
POST   /api/auth/logout             # User logout
POST   /api/auth/refresh            # Refresh token
POST   /api/auth/reset-password     # Password reset
```

#### Trading API
```
GET    /api/trades                  # List trades
GET    /api/trades/:id              # Get trade details
POST   /api/trades                  # Create manual trade
PUT    /api/trades/:id              # Update trade
DELETE /api/trades/:id              # Close/delete trade

GET    /api/positions               # Current positions
PUT    /api/positions/:id/sl        # Update stop loss
PUT    /api/positions/:id/tp        # Update take profit
POST   /api/positions/:id/close     # Close position
```

#### System API
```
GET    /api/system/status           # System status
GET    /api/system/performance      # Performance metrics
PUT    /api/system/settings         # Update settings
POST   /api/system/restart          # Restart system
POST   /api/system/backup           # Trigger backup
```

#### Strategies API
```
GET    /api/strategies              # List strategies
GET    /api/strategies/:id          # Strategy details
PUT    /api/strategies/:id          # Update strategy
PUT    /api/strategies/:id/toggle   # Enable/disable strategy
POST   /api/strategies/:id/test     # Backtest strategy
```

#### Market Data API
```
GET    /api/market/symbols          # Available symbols
GET    /api/market/data/:symbol     # Historical data
GET    /api/market/quote/:symbol    # Current quote
GET    /api/market/analysis/:symbol # Technical analysis
GET    /api/market/conditions       # Current market conditions
```

### WebSocket API

#### Real-time Data Channels
```
/ws/quotes                # Real-time price quotes
/ws/trades                # Trade updates
/ws/performance           # Performance metrics updates
/ws/system                # System status updates
/ws/signals               # Strategy signals
```

#### WebSocket Message Format
```json
{
  "channel": "quotes",
  "data": {
    "symbol": "EURUSD",
    "bid": 1.10325,
    "ask": 1.10342,
    "time": "2025-04-17T12:34:56.789Z"
  }
}
```

## Infrastructure Design

### Production Server Specifications

- **VPS Requirements**:
  - 4+ CPU cores
  - 8GB+ RAM
  - 80GB+ SSD storage
  - 99.9% uptime guarantee
  - Low-latency network connection to broker servers

- **Operating System**:
  - Ubuntu Server 22.04 LTS

- **Network Requirements**:
  - Static IP address
  - Firewall configuration
  - VPN access for management

### Service Architecture

- **Containerization**:
  - Docker containers for component isolation
  - Docker Compose for service orchestration

```yaml
# docker-compose.yml structure
version: '3.8'
services:
  trading-engine:
    build: ./src
    depends_on:
      - database
      - redis
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    env_file: .env
    restart: always
    
  api-server:
    build: ./api
    ports:
      - "5000:5000"
    depends_on:
      - trading-engine
      - database
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    env_file: .env
    restart: always
    
  database:
    image: postgres:14
    volumes:
      - postgres-data:/var/lib/postgresql/data
    env_file: .env.db
    restart: always
    
  redis:
    image: redis:6
    volumes:
      - redis-data:/data
    restart: always
    
  prometheus:
    image: prom/prometheus
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    restart: always
    
  grafana:
    image: grafana/grafana
    depends_on:
      - prometheus
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    restart: always
    
  alertmanager:
    image: prom/alertmanager
    volumes:
      - ./config/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    ports:
      - "9093:9093"
    restart: always

volumes:
  postgres-data:
  redis-data:
  prometheus-data:
  grafana-data:
```

### File System Structure

```
/opt/forex-trading-bot/
  ├── src/                  # Source code
  ├── api/                  # API server
  ├── config/               # Configuration files
  │   ├── mt5_config.yaml   # MT5 connection settings
  │   ├── strategies.yaml   # Strategy parameters
  │   ├── risk_config.yaml  # Risk management settings
  │   ├── prometheus.yml    # Monitoring configuration
  │   └── alertmanager.yml  # Alert configuration
  ├── logs/                 # Application logs
  ├── data/                 # Data storage
  │   ├── backups/          # Database backups
  │   └── market_data/      # Historical market data
  ├── scripts/              # Utility scripts
  │   ├── backup.sh         # Backup script
  │   ├── setup_vps.sh      # VPS setup script
  │   └── security_hardening.sh # Security script
  ├── docs/                 # Documentation
  ├── .env                  # Environment variables
  ├── docker-compose.yml    # Service orchestration
  └── README.md             # Project documentation
```

## Security Architecture

### Authentication & Authorization

- **Multi-factor authentication** for admin access
- **Role-based access control** for API endpoints
- **JWT token expiration** and rotation

### Network Security

- **TLS encryption** for all API communications
- **IP whitelisting** for admin access
- **Firewall rules** to restrict access

```bash
# Firewall configuration
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 5000/tcp  # API server
ufw allow 3000/tcp  # Grafana (restricted to admin network)
ufw allow 9090/tcp  # Prometheus (restricted to admin network)
```

### Data Security

- **Database encryption** for sensitive fields
- **API key rotation** policy
- **Secure credential storage**

### Security Monitoring

- **Failed login attempt monitoring**
- **Unusual access pattern detection**
- **Real-time security alerting**

## Scalability Design

### Horizontal Scaling

- **Component separation** for independent scaling
- **Load balancing** for API servers
- **Database read replicas** for query scaling

### Performance Optimization

- **Connection pooling** for database and MT5 connections
- **Caching layer** for frequent data accesses
- **Optimized database queries** with proper indexing

### Resource Management

- **Background jobs** for non-time-critical tasks
- **Rate limiting** to prevent API abuse
- **Graceful degradation** under heavy load

## Monitoring and Observability

### Metrics Collection

- **System metrics**: CPU, memory, disk, network
- **Application metrics**: Request latency, error rates, throughput
- **Trading metrics**: Execution time, slippage, win/loss ratio

### Dashboard Visualizations

- **System health dashboard**
- **Trading performance dashboard**
- **Market conditions dashboard**

### Alerting Configuration

- **Critical system alerts** (SMS, email)
- **Performance degradation alerts**
- **Security incident alerts**
- **Trading anomaly alerts**

## Deployment Architecture

### Deployment Process

1. **Build and Test**:
   - Run CI/CD pipeline
   - Execute unit and integration tests
   - Generate test coverage reports

2. **Deployment Preparation**:
   - Create database backup
   - Verify configuration files
   - Check system dependencies

3. **Deployment**:
   - Deploy updated components
   - Run database migrations
   - Verify service health

4. **Post-Deployment**:
   - Execute smoke tests
   - Monitor system for anomalies
   - Update documentation if needed

### Rollback Procedure

1. **Triggering Rollback**:
   - Automated rollback on deployment failure
   - Manual rollback option for detected issues

2. **Rollback Process**:
   - Restore previous version from repository
   - Revert database migrations if necessary
   - Restart affected services

3. **Verification**:
   - Verify system functionality after rollback
   - Investigate root cause of deployment failure

### Deployment Environments

- **Development**: Local development environment
- **Testing**: Dedicated testing environment with simulated MT5 connection
- **Staging**: Pre-production environment with demo MT5 account
- **Production**: Live trading environment with real MT5 account

---

This architecture document is subject to regular reviews and updates as the system evolves.
