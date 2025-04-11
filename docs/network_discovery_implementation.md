# Network Discovery Implementation

## Overview

The network discovery feature allows the mobile trading app to automatically discover and connect to the trading bot running on a PC within the same local network. This document outlines the implementation details, architecture, and usage of this feature.

## Architecture

The network discovery system uses a combination of technologies to provide a seamless connection experience:

```
📱 Mobile App (Flutter)                   💻 PC/Trading Bot (Python)
┌─────────────────────────┐              ┌─────────────────────────┐
│                         │              │                         │
│  NetworkDiscoveryBloc   │◄─── mDNS ────►   NetworkDiscoveryServ- │
│         +               │              │       ice               │
│  NetworkDiscoveryServ-  │◄─── HTTP ────►                         │
│       ice               │              │                         │
│                         │◄─── QR ──────►                         │
└─────────────────────────┘              └─────────────────────────┘
```

### Key Components

#### Mobile App (Flutter)

1. **NetworkDiscoveryService**: Service class that handles scanning local networks for trading bot servers using:
   - mDNS (Multicast DNS) for zero-configuration discovery
   - IP range scanning for networks where mDNS might be blocked
   - Connection validation and testing

2. **BotServer Model**: Data model representing discovered trading bot servers, containing:
   - Server name, host, port
   - Authentication requirements
   - Version information
   - Connection history and status

3. **NetworkDiscoveryBloc**: State management that handles:
   - Loading cached servers
   - Starting network scans
   - Adding/removing/favoriting servers
   - Connecting to servers

4. **Server Discovery UI**:
   - ServerDiscoveryScreen for displaying and managing servers
   - AddServerDialog for manually adding servers
   - QrScannerScreen for scanning QR codes to add servers

5. **Utility Components**:
   - Logger for consistent logging
   - Formatters for user-friendly display of server information

#### PC/Trading Bot (Python)

1. **NetworkDiscoveryService**: Service that:
   - Broadcasts the trading bot's presence using mDNS
   - Provides API endpoints for connection verification
   - Generates QR codes for easy mobile connections
   - Automatically refreshes when network changes occur

2. **API Endpoints**:
   - `/api/info`: Returns connection details for the trading bot
   - `/api/qr`: Provides a QR code data URI for easy connections

## Implementation Details

### Mobile App Discovery Process

1. **Server Discovery Flow**:
   ```
   User opens app → Load cached servers → Start mDNS & IP scanning → 
   Display discovered servers → User selects server → Connect & authenticate
   ```

2. **Multiple Discovery Methods**:
   - **Automatic Discovery**: Using mDNS and IP scanning
   - **Manual Entry**: User can manually enter server details
   - **QR Code Scanning**: User can scan QR code displayed by the PC app

3. **Server Management**:
   - **Favorites**: Frequently used servers can be marked as favorites
   - **History**: Connection history is maintained for easy reconnection
   - **Auto-Connect**: Option to automatically connect to last used server

### PC-side Broadcasting

1. **Service Advertising**:
   - Trading bot advertises itself as a `_forexbot._tcp.local.` service via mDNS
   - Service includes metadata (name, version, auth requirements)

2. **Connection Details**:
   - API endpoint provides current connection information
   - QR code contains all necessary details for instant connection

3. **Network Change Handling**:
   - Service periodically checks for IP changes
   - Automatically updates mDNS broadcasting if network changes

## Recent Enhancements

### BotServer Model Enhancements

The `BotServer` model has been enhanced with additional capabilities to improve network discovery integration:

1. **Connection History**: The model now tracks `lastSeen` and `lastConnected` timestamps to provide better insight into server availability and usage history.

2. **URL Management**: Added helper methods for accessing different server endpoints:
   - `baseUrl`: HTTP URL for API requests
   - `wsUrl`: WebSocket URL for real-time updates
   - `qrCodeUrl`: URL for QR code generation
   - `getUrl()`: Method for getting the full URL

3. **Reachability Assessment**: Added `isLikelyReachable` property that evaluates if a server has been seen recently (within the last 10 minutes) and is likely still available on the network.

4. **Factory Methods**:
   - `BotServer.fromDiscoveredService()`: Creates a server entry from network discovery results
   - `BotServer.manual()`: Creates a manually configured server entry
   - `BotServer.fromJson()`: Creates a server from JSON for storage/retrieval
   
5. **URL Matching**: Added `matchesUrl()` method to identify if a given URL matches this server's address.

### API and WebSocket Integration

The network discovery system has been integrated with both the API and WebSocket services:

1. **ApiService Integration**:
   - `getServerInfo()`: Connects to a server and retrieves its version, features, and configuration
   - `setActiveServer()`: Sets and persists the active server for API requests
   - `getActiveServer()` and `hasActiveServer()`: Methods to check current server status

2. **WebSocketService Integration**:
   - Updated to accept `BotServer` objects directly for connection setup
   - Improved reconnection logic with proper error handling
   - Server state persistence for continuous operation

### Market Condition Integration

The network discovery feature now integrates with the trading bot's market condition detection system:

1. **Server Discovery and Market Context**: When connecting to a trading bot server, the app retrieves information about current market conditions to enhance the trading experience.

2. **Market-Informed Connection Management**: The app prioritizes connections to servers that are actively analyzing favorable market conditions.

3. **Market Condition Visualization**:
   - Upon connection, the app displays the current analysis of market trends (bullish, bearish, ranging, choppy)
   - Shows volatility assessments (low, medium, high)
   - Displays liquidity conditions
   - Indicates the trading bot's confidence in current market conditions

4. **Multi-Asset Strategy Selection**: The connection system integrates with the multi-asset trading capabilities to display active instruments and selected strategies based on current market conditions.

## Enhanced User Experience

The network discovery process has been improved with several UX enhancements:

1. **Server Reachability Indicators**: Servers are visually indicated as "Likely Available" or "May be Offline" based on their last seen timestamps.

2. **Favorite Servers**: Users can now mark servers as favorites for quick access.

3. **Connection History**: The app displays when a server was last connected to, providing users with useful context.

4. **Automatic Reconnection**: The app will attempt to reconnect to the last used server when launched, prioritizing favorite servers if multiple are available.

5. **Market Condition Preview**: Before establishing a full connection, users can see a preview of current market conditions to determine if trading is favorable.

## Security Considerations

1. **Authentication**:
   - All connections require authentication with JWT tokens
   - Connection details are encrypted in the mobile app's secure storage

2. **QR Code Security**:
   - QR codes contain only connection info, not credentials
   - QR codes can be regenerated as needed for security

3. **Network Isolation**:
   - Discovery works only on local networks
   - External connections require explicit configuration

## Usage Examples

### Connecting via Automatic Discovery

1. Open the mobile app
2. Navigate to the "Connect" or "Servers" section
3. Wait for automatic discovery to find available trading bots
4. Select the desired server from the list
5. Enter credentials if prompted

### Connecting via QR Code

1. Open the PC trading bot application
2. Navigate to the connection info section to display the QR code
3. Open the mobile app and navigate to the "Scan QR" section
4. Scan the displayed QR code
5. Enter credentials if prompted

### Manually Adding a Server

1. Open the mobile app
2. Navigate to the "Connect" or "Servers" section
3. Tap the "+" button to add a server manually
4. Enter the server's IP address, port, and name
5. Save the server details
6. Connect to the server and enter credentials if prompted

## Troubleshooting

### Common Issues and Solutions

1. **Server Not Found**:
   - Ensure the PC and mobile device are on the same network
   - Check if any firewall is blocking mDNS (port 5353) or the trading bot port
   - Try manually entering the server IP address

2. **Connection Failed**:
   - Verify the server is running
   - Check network connectivity
   - Ensure the entered credentials are correct

3. **QR Code Scan Failed**:
   - Ensure adequate lighting for the QR code
   - Hold the camera steady and at an appropriate distance
   - Make sure the entire QR code is visible in the scanner

## Future Enhancements

1. **Connection Resilience**:
   - Improved reconnection logic for unstable networks
   - Background reconnection attempts

2. **Enhanced Security**:
   - Certificate-based authentication option
   - Encrypted communication channels
   - Two-factor authentication

3. **Multi-Server Management**:
   - Ability to connect to multiple servers simultaneously
   - Server grouping and organization

---

## Technical Reference

### Mobile App Dependencies

```yaml
dependencies:
  network_info_plus: ^4.0.0
  multicast_dns: ^0.3.2
  connectivity_plus: ^4.0.2
  mobile_scanner: ^3.0.0
```

### PC-side Dependencies

```
zeroconf
fastapi
netifaces
qrcode
```

### QR Code Format

The QR code uses the following URI format:
```
forexbot://<host>:<port>?name=<encoded_name>&version=<version>
```

### mDNS Service Properties

```
Service Type: _forexbot._tcp.local.
Service Name: ForexTradingBot
Properties:
  - name: "Forex Trading Bot"
  - version: "<bot_version>"
  - auth: "true"
```
