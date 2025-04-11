# Multi-Instrument Trading System

## Overview

This document explains how the trading bot handles multiple instrument types, specifically:
- Traditional Forex currency pairs 
- Deriv synthetic indices

The system is designed to seamlessly adapt its trading strategies, risk management, and execution approach based on the specific characteristics of each instrument type.

## Instrument Types

### Forex Currency Pairs

Traditional forex pairs like EUR/USD, GBP/USD, and USD/JPY have specific trading characteristics:
- Follow market hours with varying liquidity
- Affected by economic news and geopolitical events
- Typically lower volatility compared to synthetic indices
- Session-based trading patterns (Asian, European, US sessions)

### Deriv Synthetic Indices

Synthetic indices are algorithm-generated instruments with unique properties:
- Available for trading 24/7
- Not affected by real-world economic events
- Programmatically generated price movements
- Specifically designed volatility patterns

#### Subtypes of Synthetic Indices:

1. **Volatility Indices** (e.g., Volatility 10, Volatility 75, Volatility 100)
   - Constant volatility with price simulating a continuous liquid market
   - Higher implied volatility levels for higher index numbers

2. **Crash/Boom Indices** (e.g., Crash 500, Crash 1000, Boom 500, Boom 1000)
   - Periodic price spikes (crashes or booms)
   - Number indicates average frequency of spikes (e.g., 1000 = spike every ~1000 ticks)
   - Crash indices have downward spikes, Boom indices have upward spikes

3. **Step Indices** (e.g., Step Index)
   - Price changes at regular intervals
   - Moves in uniform amounts

4. **Jump Indices** (e.g., Jump 10, Jump 25, Jump 50, Jump 75, Jump 100)
   - Unpredictable jumps in price with varying magnitudes
   - Number indicates volatility level and jump frequency

## System Components for Multi-Instrument Trading

### 1. Instrument Manager

The `InstrumentManager` class handles all aspects of instrument identification and properties:

- Distinguishes between forex and synthetic indices
- Identifies specific subtypes of synthetic indices
- Manages trading sessions for each instrument type
- Determines appropriate lot sizes and risk parameters
- Controls when each instrument type is available for trading

### 2. Strategy Selector

The `StrategySelector` uses different strategy scoring methods based on instrument type:

- Forex instruments use traditional technical analysis
- Synthetic indices use specialized strategy strengths
- Different strategy weights for different synthetic index subtypes
- Adaptive market condition analysis based on instrument characteristics

### 3. Risk Manager

Risk management is customized for each instrument type:

- Adjusted lot size calculations for synthetic indices
- Specialized stop loss distance calculations
- Volatility-based position sizing for synthetic indices
- Correlation management between similar instrument types

### 4. Bot Controller

The main bot controller handles multi-instrument trading by:

- Loading appropriate instruments based on current trading session
- Managing data feeds for both instrument types
- Applying instrument-specific trading parameters
- Routing signals to appropriate execution logic

## Trading Session Management

Different instruments have different optimal trading times:

- **Forex Pairs**: Trade during peak liquidity sessions (overlap of major markets)
- **Synthetic Indices**: Available 24/7, but the bot can be configured to trade them:
  - During specific times
  - When forex market volatility is low
  - Based on account balance management rules

## Implementation Examples

See the examples directory for demonstrations:

- `examples/multi_instrument_trading_example.py` - Shows how the system trades both forex and synthetic indices simultaneously

## Configuration

The `mt5_config.yaml` file contains all settings for multi-instrument trading:

```yaml
trading:
  instruments:
    forex:
      - name: "EURUSD"
        enabled: true
        sessions: ["european", "american"]
      - name: "GBPUSD"
        enabled: true
        sessions: ["european", "american"]
      # ... more forex pairs
      
    synthetic:
      - name: "Volatility 75 Index"
        type: "volatility"
        enabled: true
        sessions: ["all"]
      - name: "Crash 1000 Index"
        type: "crash_boom"
        enabled: true
        sessions: ["all"]
      # ... more synthetic indices
```

## Best Practices

1. **Instrument Selection**:
   - Focus on high-liquidity forex pairs with low spreads
   - Select synthetic indices that complement your forex trading

2. **Risk Management**:
   - Consider using lower risk percentages for volatile synthetic indices
   - Monitor correlation between similar synthetic indices

3. **Strategy Optimization**:
   - Different strategies work better for different instrument types
   - Use the strategy scoring system to select optimal approaches

4. **Testing**:
   - Backtest strategies separately for forex and synthetic indices
   - Forward test with small lot sizes before scaling up

## Conclusion

The multi-instrument trading system provides a comprehensive framework for trading both traditional forex pairs and synthetic indices. By adapting strategies, risk management, and execution logic to each instrument's unique characteristics, the system aims to optimize trading performance across all market conditions.
