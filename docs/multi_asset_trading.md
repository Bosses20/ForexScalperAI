# Multi-Asset Trading Documentation

## Overview

The multi-asset trading module enhances the trading bot with advanced capabilities to effectively manage both Forex pairs and Deriv synthetic indices. This system intelligently switches between different instrument types based on market conditions, trading sessions, and historical performance.

## Key Components

### 1. Correlation Manager (`src/risk/correlation_manager.py`)

The Correlation Manager tracks and manages correlations between different trading instruments to prevent overexposure to similar market movements.

**Key Features:**
- Calculates and maintains a correlation matrix between instruments
- Identifies highly correlated instruments to prevent excessive risk
- Prevents opening positions that would create excessive exposure to correlated market movements
- Supports predefined correlation groups for instruments without sufficient price history
- Manages correlation-based risk across both Forex and synthetic indices

### 2. Session Manager (`src/trading/session_manager.py`)

The Session Manager implements time-based instrument rotation, automatically switching between Forex and synthetic indices based on market hours and liquidity conditions.

**Key Features:**
- Tracks global trading sessions (Sydney, Tokyo, London, New York)
- Identifies session overlaps which typically have the highest liquidity
- Recognizes low liquidity periods optimal for synthetic indices
- Recommends instruments based on the current trading session
- Optimizes trading focus throughout the 24-hour cycle

### 3. Portfolio Optimizer (`src/portfolio/portfolio_optimizer.py`)

The Portfolio Optimizer handles optimal asset allocation across different instrument types based on performance metrics and risk parameters.

**Key Features:**
- Calculates optimal instrument allocation based on historical performance
- Rebalances the portfolio periodically to adapt to changing market conditions
- Tracks instrument-specific performance metrics (win rate, expectancy, profit)
- Maintains diversification between Forex and synthetic indices
- Prevents overconcentration in any one instrument or category

### 4. Multi-Asset Integrator (`src/trading/multi_asset_integrator.py`)

The Multi-Asset Integrator serves as the coordination layer that combines all components to provide unified multi-asset trading capabilities.

**Key Features:**
- Coordinates all trading components (correlation, session, portfolio)
- Provides a unified interface for the bot controller to access multi-asset functionality
- Validates new positions based on all risk parameters
- Selects optimal trading strategies based on instrument type
- Monitors and reports on the overall trading status

## Configuration

All multi-asset trading components are configured through the `config/mt5_config.yaml` file in the following sections:

1. **Correlation Management**: `correlation` section
2. **Session Management**: `sessions` section
3. **Portfolio Optimization**: `portfolio` section
4. **Multi-Asset Integration**: `multi_asset` section

## Best Practices

### Forex Trading Optimization

- Focus on major pairs during session overlaps (London/New York overlap is ideal)
- Use tighter stop losses during high-volatility periods
- Monitor spread widening during news events
- Prefer technical strategies when liquidity is high

### Synthetic Indices Optimization

- Use synthetic indices during low Forex liquidity periods
- Apply distinct strategies based on synthetic index type:
  - **Volatility Indices**: MA crossover and Bollinger Band strategies work well
  - **Crash/Boom Indices**: Break of structure and breakout strategies are effective
  - **Step Indices**: Moving average strategies are highly effective
- Adjust position sizes based on the volatility profile of each index

### Combined Trading Approach

1. **Market Hours Strategy**:
   - European/US session overlap: Focus on major Forex pairs
   - Asian session: Include JPY pairs and synthetic indices
   - Off-hours: Primarily trade synthetic indices

2. **Risk Allocation**:
   - Maintain a balanced exposure between Forex and synthetic indices
   - Reduce correlation risk by diversifying across different instrument types
   - Allocate more capital to high-performing instruments while maintaining diversification

3. **Performance Monitoring**:
   - Regularly review the performance of each instrument
   - Adjust allocations based on historical performance
   - Use the portfolio optimizer's recommendations for optimal exposure

## System Integration

The multi-asset trading components are fully integrated with the existing bot controller. The controller now:

1. Initializes all multi-asset components during startup
2. Uses the multi-asset integrator to determine which instruments to trade
3. Validates new positions against correlation rules
4. Selects appropriate strategies based on instrument type
5. Adjusts position sizing based on portfolio allocation
6. Processes trade results to optimize future allocation

## Backtesting with Synthetic Data

For backtesting strategies, especially with synthetic indices, use the `SyntheticDataGenerator` in the `src/backtest` directory. This allows testing strategies against realistic price data for various synthetic index types without requiring historical data.
