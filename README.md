# ForexScalperAI - Professional MT5 Trading System

An enterprise-grade automated forex and synthetic indices trading system that integrates with MetaTrader 5 to implement professional scalping strategies with advanced risk management, market condition detection, and AI-enhanced decision making.

## Features

- **MetaTrader 5 Integration**: Seamless connection with MT5 platform for reliable trade execution
- **Professional Scalping Strategies**: Implements proven profitable strategies used by institutional traders
- **Real-time Market Analysis**: Processes tick-by-tick data for ultra-short-term trading opportunities
- **AI-Enhanced Decision Making**: Validates trades using AI models trained on historical data
- **Market Condition Detection**: Automatically identifies favorable market conditions and adapts strategies accordingly
- **Multi-Asset Trading**: Trades both Forex and Synthetic Indices with specialized strategies for each
- **Advanced Technical Indicators**: Implements optimized indicators for scalping (EMA, RSI, Bollinger Bands)
- **Institutional-Grade Risk Management**: Enforces strict position sizing, correlation controls, and circuit breakers
- **Performance Analytics**: Tracks and analyzes trading performance with professional metrics
- **Mobile Interface**: Monitor and control your trading from anywhere with offline capabilities

## Development Plan

A comprehensive development plan is available in the [DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md) file, which includes:

- Detailed implementation phases
- Project architecture
- Strategy specifications
- Risk management rules
- Testing methodologies
- Deployment guidelines

Please refer to this document for a complete roadmap of the project.

## Getting Started

### Prerequisites

- Python 3.8+
- MetaTrader 5 platform installed
- MT5 account with a broker (demo or live)
- Windows OS (for MT5 integration)

### Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Configure your MT5 credentials in `.env` file:
   ```
   MT5_LOGIN=your_login
   MT5_PASSWORD=your_password
   MT5_SERVER=your_broker_server
   MT5_PATH=C:\Path\to\terminal64.exe
   ```
4. Run the application:
   ```
   python run.py
   ```

## Configuration

Edit the `config.yaml` file to customize:
- Trading pairs
- Risk parameters (max risk per trade, daily limits)
- Strategy selection and parameters
- Technical indicator settings
- Model parameters

## Project Structure

- `src/`: Core source code
  - `mt5/`: MetaTrader 5 integration components
  - `data/`: Data handling and preprocessing
  - `models/`: ML models for prediction
  - `strategies/`: Trading strategies including scalping implementation
  - `risk/`: Risk management components with circuit breakers
  - `analysis/`: Market condition detection and analysis
  - `trading/`: Multi-asset trading integration
  - `execution/`: Order execution logic
  - `api/`: API server for mobile access with offline support
  - `utils/`: Utility functions including security components
- `config/`: Configuration files
- `tests/`: Test suites
- `mobile_app/`: Flutter-based mobile application
- `tools/`: Utility scripts
- `docs/`: Documentation
- `data/`: Storage for AI models and historical data

## Risk Management

The bot implements institutional-grade risk management techniques including:

- Dynamic position sizing based on account balance and tier
- Maximum daily loss limits and drawdown controls
- Trading circuit breakers that halt operations during unfavorable conditions
- Correlation control for multi-asset exposure management
- Volatility-adjusted stop losses and take profits
- Account tier-based risk limits

## Backtesting and Optimization

The system includes comprehensive backtesting capabilities:

- Historical data analysis across 5+ years
- Multi-strategy comparative testing
- Stress testing under extreme market conditions
- Monte Carlo simulations for statistical significance
- Benchmark comparisons (Buy & Hold, Random)
- Performance metrics calculation with detailed visual reports

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with the MetaTrader 5 Python API
- Inspired by professional trading systems used in hedge funds

## Disclaimer

Trading forex involves significant risk. This software is for educational purposes only. Always use proper risk management and consult financial advisors before trading with real capital.
