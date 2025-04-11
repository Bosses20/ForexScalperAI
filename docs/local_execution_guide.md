# Local Execution Guide for Forex Trading Bot

This guide explains how to run the Forex trading bot locally on your phone and laptop without requiring a VPS.

## Overview

The local execution setup allows you to:

1. Run the trading bot on your phone or laptop
2. Control the bot through the mobile app
3. Manage system resources to ensure efficient operation
4. Handle network interruptions and reconnections gracefully
5. Save and restore bot state when needed

## Requirements

- Python 3.8+ installed on your device
- MT5 platform installed (for laptop/desktop)
- Required Python packages (see `requirements.txt`)
- Mobile phone with adequate RAM (min 2GB) and battery life

## Setup for Laptop/Desktop

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure your settings**

   Edit the configuration files:
   - `config/mt5_config.yaml` - Trading settings and MT5 connection
   - `config/local_execution.yaml` - Local execution settings

3. **Run the bot**

   ```bash
   python run_local.py
   ```

   This will start both:
   - The trading bot in local execution mode
   - The local API server for mobile app communication

4. **Options**

   Run only the bot without API server:
   ```bash
   python run_local.py --bot-only
   ```

   Run only the API server without the bot:
   ```bash
   python run_local.py --api-only
   ```

   Specify custom config files:
   ```bash
   python run_local.py --config path/to/config.yaml --local-config path/to/local_config.yaml
   ```

## Setup for Android Phone

### Option 1: Using Termux

1. **Install Termux** from Google Play Store or F-Droid

2. **Setup Python environment**

   ```bash
   pkg update
   pkg install python git
   pip install -r requirements.txt
   ```

3. **Run the bot**

   ```bash
   python run_local.py
   ```

4. **Keep running in background**

   To keep the bot running when Termux is closed:
   ```bash
   nohup python run_local.py &
   ```

### Option 2: Using QPython or Similar

1. **Install QPython** or another Python app for Android

2. **Setup the project**
   - Import the project files into QPython
   - Install required packages

3. **Run the script**
   - Open `run_local.py` and execute it

## Connecting Mobile App to Local Bot

When the bot is running with the API server enabled:

1. **Same Device:** 
   - Connect to `http://127.0.0.1:8000` in the mobile app

2. **Different Devices on Same Network:**
   - Change the `host` in `local_execution.yaml` to your device's local IP (e.g., `192.168.1.x`)
   - Connect to `http://192.168.1.x:8000` from the other device

3. **Security Considerations:**
   - The API is currently set to only allow local connections for security
   - If you need remote access, consider implementing a secure tunnel

## Resource Management

The local execution setup includes resource management features:

- **CPU Usage Limitation:** Prevents excessive CPU usage
- **Memory Management:** Keeps memory usage within limits
- **Battery Optimization:** Reduces functionality when battery is low
- **Background Mode:** Allows the bot to run in the background

These settings can be adjusted in `config/local_execution.yaml`.

## Network Handling

The local execution system handles network interruptions:

- **Auto-reconnection:** Attempts to reconnect when disconnected
- **State Persistence:** Saves bot state periodically
- **Graceful Recovery:** Continues trading after connection is restored

## Monitoring and Logs

- Logs are saved to the `logs` directory
- Status updates are shown on the console
- WebSocket endpoint provides real-time updates to the mobile app

## Troubleshooting

1. **Bot crashes or fails to start:**
   - Check logs in the `logs` directory
   - Ensure MT5 is running (for laptop/desktop)
   - Verify that configurations are correct

2. **Mobile app can't connect:**
   - Ensure both devices are on the same network
   - Check if the host/port in config is correct
   - Verify firewall settings aren't blocking the connection

3. **Performance issues:**
   - Adjust resource limits in `local_execution.yaml`
   - Reduce the number of currency pairs being monitored
   - Increase polling intervals to reduce CPU/network usage

## Important Notes

1. **Battery Usage:** Running the bot continuously on a mobile device will consume significant battery power. It's recommended to keep the device plugged in.

2. **Data Usage:** The bot will consume data when running on mobile networks. Use WiFi when possible.

3. **Security:** The local API isn't secured with HTTPS by default. Do not expose it to public networks without proper security measures.

4. **Sleep Mode:** Configure your device to prevent sleep while the bot is running.
