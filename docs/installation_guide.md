# Forex Trading Bot Installation Guide

## System Requirements

### Hardware Requirements
- **CPU**: Intel Core i5 (8th gen or newer) or AMD Ryzen 5 (3000 series or newer)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB of free space
- **Network**: Stable internet connection (minimum 5 Mbps)

### Software Requirements
- **Operating System**: Windows 10/11 (64-bit)
- **MT5 Platform**: Latest version of MetaTrader 5
- **Mobile Device**: Android 8.0+ or iOS 13.0+ for mobile app

## Installation Steps

### Step 1: Install MetaTrader 5
1. Download MetaTrader 5 from your broker's website
2. Install and set up your MT5 terminal with your trading account
3. Verify that you can log in and access market data

### Step 2: Install the Forex Trading Bot

#### Automatic Installation (Recommended)
1. Download the Forex Trading Bot installer from the official website
2. Right-click the installer and select "Run as administrator"
3. Follow the on-screen instructions
4. When prompted, provide your MT5 installation directory
5. Choose installation options:
   - Install as a service (recommended for 24/7 operation)
   - Configure Windows Firewall
   - Enable UPnP for automatic port forwarding
   - Start with Windows

#### Manual Installation (Advanced Users)
1. Download the Forex Trading Bot package
2. Extract the contents to a directory of your choice
3. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Configure the bot by editing `config/mt5_config.yaml`
5. Create a shortcut to `run_bot.bat` in your startup folder for automatic startup

### Step 3: Configure the Bot

1. Launch the configuration wizard from the Start menu or desktop shortcut
2. Enter your MT5 account credentials:
   - Login
   - Password
   - Server
3. Configure trading parameters:
   - Risk per trade (recommended: 1-2%)
   - Maximum daily drawdown (recommended: 5%)
   - Trading instruments (select based on your trading strategy)
   - Trading sessions
4. Set up network settings:
   - Choose a port for the API server (default: 8000)
   - Enable UPnP for automatic port forwarding
   - Configure advanced network settings if needed

### Step 4: Install the Mobile App

1. Download the Forex Trading Bot mobile app from:
   - **Android**: Google Play Store
   - **iOS**: Apple App Store
2. Install the app on your mobile device
3. Launch the app and follow the onboarding process

### Step 5: Connect Mobile App to Trading Bot

#### Using QR Code (Recommended)
1. On your PC, open the Trading Bot dashboard
2. Click "Generate Connection QR Code"
3. On your mobile device, tap "Scan QR Code"
4. Point your camera at the QR code on your PC screen
5. The app will automatically connect to your trading bot

#### Using Network Discovery
1. Ensure your mobile device is on the same network as your PC
2. Open the mobile app and tap "Find Servers"
3. The app will scan the network and display available trading bots
4. Select your trading bot from the list
5. Enter API key if prompted

#### Using Manual Connection
1. On your PC, note the IP address and port of your trading bot
2. Open the mobile app and tap "Manual Connection"
3. Enter the IP address and port
4. Enter API key if prompted

## Configuring for Profitability

### Market Condition Detection
The Forex Trading Bot includes a sophisticated market condition detection system that helps ensure profitability:

1. Navigate to "Settings > Market Conditions"
2. Configure the following parameters:
   - **Trend Detection Sensitivity**: Recommended setting is medium (5)
   - **Volatility Thresholds**: Configure based on your trading style
     - Conservative: Low volatility only (0.2-0.5%)
     - Moderate: Low to medium volatility (0.2-1.0%)
     - Aggressive: All volatility conditions (0.2-2.0%+)
   - **Liquidity Requirements**: Enable for major pairs, disable for exotics
   - **Minimum Confidence Score**: Recommended 65% for beginners, 50% for experienced traders

### Multi-Asset Trading Configuration
For optimal profitability, configure the multi-asset trading features:

1. Navigate to "Settings > Multi-Asset Trading"
2. Configure correlation management:
   - Set correlation threshold to 0.7 (recommended)
   - Enable smart position sizing
   - Configure predefined correlation groups or use automatic detection
3. Set up session management:
   - Enable trading during major session overlaps for best results
   - Configure instrument rotation based on session activity
4. Adjust portfolio optimization:
   - Set maximum allocation per instrument (recommended: 20%)
   - Configure rebalancing frequency (recommended: daily)
   - Set diversity requirements (recommended: minimum 4 instruments)

## Troubleshooting

### Connection Issues
- **Problem**: Mobile app cannot find the trading bot
  - **Solution**: Ensure both devices are on the same network, check firewall settings, verify UPnP is enabled

- **Problem**: Cannot connect from outside home network
  - **Solution**: Configure port forwarding on your router or enable UPnP

- **Problem**: "Connection refused" error
  - **Solution**: Verify the trading bot is running, check the configured port, ensure firewall allows connections

### MT5 Connection Issues
- **Problem**: "MT5 not connected" error
  - **Solution**: Verify MT5 is running, check credentials in config file, restart MT5 and the trading bot

- **Problem**: Cannot retrieve market data
  - **Solution**: Check internet connection, verify your MT5 account has access to required symbols, contact your broker

### Trading Issues
- **Problem**: Bot is not taking trades
  - **Solution**: Check market condition settings, verify trading hours configuration, ensure risk parameters are not too restrictive

- **Problem**: Excessive losing trades
  - **Solution**: Adjust market condition detection sensitivity, enable "Conservative Mode", verify strategy performance in current market conditions

## Network Configuration Guide

### Firewall Configuration
The Forex Trading Bot requires the following ports to be open:
- **TCP 8000**: API server (default, configurable)
- **TCP 8001**: WebSocket server (default, configurable)

#### Windows Firewall
1. Open Windows Defender Firewall with Advanced Security
2. Select "Inbound Rules" and click "New Rule..."
3. Select "Port" and click "Next"
4. Select "TCP" and enter the ports (e.g., "8000,8001")
5. Select "Allow the connection" and click "Next"
6. Select all network types and click "Next"
7. Name the rule "Forex Trading Bot" and click "Finish"

### Router Configuration

#### UPnP (Recommended)
1. Enable UPnP on your router
2. Enable UPnP in the Forex Trading Bot settings
3. The bot will automatically configure port forwarding

#### Manual Port Forwarding
1. Access your router's admin interface (typically http://192.168.1.1 or http://192.168.0.1)
2. Navigate to port forwarding section
3. Create a new port forwarding rule:
   - External Port: 8000
   - Internal Port: 8000
   - Protocol: TCP
   - Internal IP: IP address of your PC
   - Description: "Forex Trading Bot API"
4. Create a second rule for WebSocket port if needed

## Advanced Configuration

For advanced users, the `mt5_config.yaml` file contains comprehensive configuration options:

```yaml
# Example of optimized configuration
api:
  port: 8000
  ws_port: 8001
  enable_upnp: true
  api_keys: ["your-secure-api-key"]

mt5:
  account: 12345678
  password: "your-password"
  server: "YourBroker-Live"
  symbols:
    - EURUSD
    - GBPUSD
    - USDJPY
    - AUDUSD
    - USDCAD
    - USDCHF

trading:
  risk_per_trade: 1.5
  max_daily_drawdown: 5.0
  position_sizing: "dynamic"
  use_market_conditions: true
  trading_sessions:
    - "london_open"
    - "new_york_open"
    - "london_new_york_overlap"

market_conditions:
  trend_sensitivity: 5
  volatility_threshold_low: 0.2
  volatility_threshold_high: 1.0
  liquidity_requirement: true
  min_confidence: 65

multi_asset:
  correlation_threshold: 0.7
  max_correlated_positions: 2
  rebalance_frequency: "daily"
  max_allocation_per_instrument: 20
```

## Getting Help

If you encounter any issues with installation or configuration:

1. Check the troubleshooting section in this guide
2. Visit our online documentation at [forextradingbot.com/docs](https://forextradingbot.com/docs)
3. Contact support at support@forextradingbot.com

## Next Steps

After successful installation, continue to the [Quick Start Guide](quick_start_guide.md) to learn how to:
- Configure your first trading strategy
- Monitor performance via the mobile app
- Set up custom alerts and notifications
- Optimize your trading parameters for maximum profitability
