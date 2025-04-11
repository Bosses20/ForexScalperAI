# Forex Trading Bot Quick Start Guide

## Introduction

This quick start guide will help you get your Forex Trading Bot up and running for profitable trading in the shortest time possible. Follow these steps to quickly set up and start using your trading bot with the mobile app for one-tap trading.

## Getting Started in 5 Minutes

### Step 1: Launch the Trading Bot (PC)

1. After installation, double-click the Forex Trading Bot icon on your desktop
2. The system will automatically:
   - Connect to MetaTrader 5
   - Start the local API server
   - Configure network settings (UPnP)
   - Begin market condition analysis
3. Wait for the dashboard to show "System Ready"

### Step 2: Connect Mobile App (One-Tap Setup)

1. Launch the mobile app on your smartphone
2. Tap "Scan QR Code" on the welcome screen
3. On your PC, click "Generate QR Code" in the dashboard
4. Scan the QR code with your mobile app
5. The app will automatically connect to your trading bot

### Step 3: Start Trading

1. On the mobile app home screen, review the current market conditions
   - Check the market trend (bullish/bearish/ranging)
   - Review volatility levels
   - Confirm favorable trading conditions
2. Tap the "Start Trading" button
3. Select your risk level (Conservative/Moderate/Aggressive)
4. The bot will now automatically trade according to your settings

## Understanding the Dashboard

### PC Dashboard

![PC Dashboard](https://example.com/dashboard.png)

1. **System Status**: Shows the overall status of your trading bot
2. **MT5 Connection**: Indicates whether MetaTrader 5 is connected
3. **Market Conditions**: Displays current market analysis
4. **Active Trades**: Shows currently open positions
5. **Performance Metrics**: Displays daily/weekly/monthly performance
6. **QR Code**: Button to generate connection QR code

### Mobile Dashboard

![Mobile Dashboard](https://example.com/mobile_dashboard.png)

1. **Server Status**: Shows connection status to your trading bot
2. **Market Summary**: Quick overview of current market conditions
3. **Active Trades**: Displays currently open positions
4. **Quick Actions**: One-tap controls for the trading bot
   - Start/Stop Trading
   - Close All Positions
   - Change Risk Level
5. **Performance Card**: Shows current session performance

## Common Tasks

### Changing Trading Parameters

1. On the mobile app, tap the gear icon in the top-right corner
2. Select "Trading Parameters"
3. Adjust settings:
   - Risk per trade (1-5%)
   - Maximum open positions (1-10)
   - Trading session preferences
4. Tap "Save" to apply changes

### Monitoring Performance

1. On the mobile app, tap "Performance" on the bottom navigation bar
2. View performance metrics:
   - Today's P&L
   - Weekly/Monthly performance
   - Win/loss ratio
   - Average trade duration
3. Use the filter options to analyze performance by:
   - Instrument
   - Strategy
   - Time period

### Managing Active Trades

1. On the mobile app, tap "Trades" on the bottom navigation bar
2. View all active trades with real-time P&L updates
3. Tap any trade to:
   - View detailed entry information
   - Modify take profit/stop loss
   - Close the position manually

### Using Market Condition Analysis

1. On the mobile app, tap "Market" on the bottom navigation bar
2. View detailed market condition analysis:
   - Trend strength and direction
   - Volatility measurements
   - Liquidity indicators
   - Session activity
3. Use this information to:
   - Decide optimal times to enable trading
   - Adjust risk parameters based on conditions
   - Understand why the bot may be inactive

## Optimizing for Profitability

### Quick Optimization Tips

1. **Trade During Major Sessions**: Enable trading during London and New York sessions for best liquidity
2. **Adjust Risk Based on Volatility**: Use lower risk during high volatility periods
3. **Focus on Strong Trends**: Set higher confidence thresholds during ranging markets
4. **Diversify Across Currencies**: Enable multi-asset trading with at least 4-6 currency pairs
5. **Monitor Correlation**: Avoid too many similar positions (e.g., EURUSD and GBPUSD)

### Recommended Settings for Beginners

```yaml
trading:
  risk_per_trade: 1.0
  max_daily_drawdown: 3.0
  position_sizing: "fixed"
  use_market_conditions: true
  trading_sessions:
    - "london_new_york_overlap"

market_conditions:
  trend_sensitivity: 7
  volatility_threshold_low: 0.3
  volatility_threshold_high: 0.8
  liquidity_requirement: true
  min_confidence: 70
```

### Recommended Settings for Experienced Traders

```yaml
trading:
  risk_per_trade: 2.0
  max_daily_drawdown: 5.0
  position_sizing: "dynamic"
  use_market_conditions: true
  trading_sessions:
    - "asian_close"
    - "london_open"
    - "london_new_york_overlap"
    - "new_york_close"

market_conditions:
  trend_sensitivity: 5
  volatility_threshold_low: 0.2
  volatility_threshold_high: 1.2
  liquidity_requirement: false
  min_confidence: 60
```

## Troubleshooting Common Issues

### "No Trading Opportunities Found"

This usually means the current market conditions don't meet your criteria.

**Solutions**:
- Lower the minimum confidence threshold
- Adjust trend sensitivity
- Add more trading instruments
- Enable more trading sessions

### "Connection Lost to Trading Bot"

This indicates a network issue between your mobile app and PC.

**Solutions**:
- Ensure both devices are on the same network
- Check if the PC is running the trading bot
- Verify firewall settings
- Try using the "Reconnect" button

### "MT5 Connection Error"

This means the bot cannot connect to your MetaTrader 5 terminal.

**Solutions**:
- Ensure MT5 is running
- Check MT5 credentials in the configuration
- Restart MT5 and the trading bot
- Make sure MT5 is not in "Strategy Tester" mode

## Next Steps

After you've become familiar with the basic operation of your trading bot, we recommend:

1. **Explore Advanced Features**: Dive into correlation management, portfolio optimization, and custom strategy configuration
2. **Set Up Notifications**: Configure alerts for important events like new trades, significant market changes, or connection issues
3. **Implement a Journal System**: Track your bot's performance and market conditions to refine your strategy
4. **Schedule Regular Reviews**: Set aside time weekly to review performance and adjust parameters

For detailed information on any feature, refer to the [Full Documentation](full_documentation.md) or contact our support team with any questions.

Happy trading!
