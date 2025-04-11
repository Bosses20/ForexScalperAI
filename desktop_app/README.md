# ForexScalperAI Desktop Application

This desktop application provides a convenient wrapper around the ForexScalperAI trading bot, allowing you to control and monitor your Forex trading operations with ease.

## Features

- **One-Click Trading**: Start and stop your trading bot with a single click
- **System Tray Integration**: Access bot controls quickly from the system tray
- **Auto-Start Capability**: Configure the bot to start automatically with Windows
- **Real-Time Status Monitoring**: View current trading status, active pairs, and profits
- **Mobile App Integration**: Quick access to the mobile app interface

## Installation

### Prerequisites
- Python 3.8 or higher
- Windows operating system
- ForexScalperAI bot installed and configured

### Setup Instructions

1. **Install Required Packages**

   The setup.py script will handle this for you, but you can also install them manually:
   ```
   pip install PyQt5 pywin32 requests
   ```

2. **Run the Setup Script**

   ```
   python setup.py
   ```

   This will:
   - Install required dependencies
   - Create desktop and start menu shortcuts
   - Optionally configure auto-start on Windows boot

3. **Launch the Application**

   After setup, you can launch the application using:
   - The desktop shortcut
   - The start menu entry
   - Running `python main.py` from the desktop_app directory

## Usage

### Starting the Bot

1. Launch the ForexScalperAI desktop application
2. Click the "Start Bot" button on the dashboard
3. The application will start the bot and begin trading according to your configured strategies

### Monitoring Status

The dashboard provides real-time information about:
- Bot running status
- Current uptime
- Active trading pairs
- Number of open trades
- Current profit/loss

### System Tray Access

When minimized, the application continues running in the system tray:
- Double-click the tray icon to show/hide the main window
- Right-click for quick access to start/stop functionality
- The icon color indicates the current bot status

### Auto-Start Configuration

To configure auto-start settings:
1. Go to the "Settings" tab
2. Check "Start bot automatically when application launches" to have the bot start immediately when you open the application
3. Check "Launch application on Windows startup" to have the application start when Windows boots

## Troubleshooting

### Bot Fails to Start

If the bot fails to start:
1. Check that the main ForexScalperAI bot is properly installed
2. Ensure all required Python packages are installed
3. Check the log file at `desktop_app.log` for error details

### Connection Issues

If the application cannot connect to the bot API:
1. Make sure the API server is running
2. Check that the API URL is correctly configured (default: http://localhost:8000)
3. Verify that no firewall is blocking the connection

## No VPS Required

This application is designed to run directly on your local PC, eliminating the need for a VPS service:

- Run the application on your personal computer
- Control trading from your mobile device
- Keep your PC on while trading
- The desktop app ensures reliable operation on your local hardware

## Support

For support and additional information, refer to the main ForexScalperAI documentation.
