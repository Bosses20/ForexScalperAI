"""
MT5 Backtesting Module
Provides comprehensive backtesting capabilities for MT5 trading strategies
"""

import os
import time
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from loguru import logger
import MetaTrader5 as mt5

# Local imports
from src.mt5.connector import MT5Connector
from src.mt5.data_feed import MT5DataFeed
from src.mt5.strategies import BaseStrategy

class MT5Backtester:
    """
    Backtesting engine for MT5 strategies
    Allows for historical simulation of strategy performance
    """
    
    def __init__(self, config: Dict = None, config_path: str = None):
        """
        Initialize the backtester
        
        Args:
            config: Configuration dictionary
            config_path: Path to configuration file
        """
        if config_path and not config:
            # Load config from file
            import yaml
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
        
        self.config = config or {}
        self.connector = None
        self.data_feed = None
        self.strategies = {}
        self.results = {}
        self.current_balance = self.config.get('initial_balance', 10000)
        
        # Set up logging
        log_config = self.config.get('logging', {})
        log_level = log_config.get('level', 'INFO')
        log_file = log_config.get('file', 'logs/backtester.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        logger.add(log_file, rotation="10 MB", level=log_level)
        
        logger.info("MT5 Backtester initialized")
    
    def initialize(self) -> bool:
        """
        Initialize the backtester
        
        Returns:
            True if initialized successfully
        """
        try:
            # Initialize MT5 connector
            self.connector = MT5Connector(self.config.get('mt5', {}))
            if not self.connector.connect():
                logger.error("Failed to connect to MT5")
                return False
            
            # Initialize data feed
            self.data_feed = MT5DataFeed(self.connector, self.config.get('data_feed', {}))
            
            logger.info("MT5 Backtester initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing MT5 Backtester: {str(e)}")
            return False
    
    def add_strategy(self, strategy: BaseStrategy) -> None:
        """
        Add a strategy to the backtester
        
        Args:
            strategy: Strategy instance to add
        """
        self.strategies[strategy.name] = strategy
        logger.info(f"Added strategy: {strategy.name}")
    
    def run_backtest(self, 
                     symbol: str, 
                     timeframe: str, 
                     strategy_name: str, 
                     start_date: datetime, 
                     end_date: datetime,
                     initial_balance: float = 10000,
                     commission: float = 0.0,
                     slippage_pips: float = 0.0,
                     spread_pips: Optional[float] = None) -> Dict:
        """
        Run backtest for a strategy
        
        Args:
            symbol: Symbol to backtest on
            timeframe: Timeframe to use
            strategy_name: Name of strategy to backtest
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_balance: Initial account balance
            commission: Commission per trade in account currency
            slippage_pips: Slippage in pips
            spread_pips: Custom spread in pips (None to use historical)
            
        Returns:
            Dictionary with backtest results
        """
        if strategy_name not in self.strategies:
            logger.error(f"Strategy {strategy_name} not found")
            return {"success": False, "error": f"Strategy {strategy_name} not found"}
        
        try:
            logger.info(f"Starting backtest for {strategy_name} on {symbol} {timeframe} from {start_date} to {end_date}")
            
            # Get historical data
            logger.info(f"Fetching historical data for {symbol} {timeframe}")
            data = self.data_feed.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            if data is None or len(data) == 0:
                logger.error(f"No historical data found for {symbol} {timeframe}")
                return {"success": False, "error": "No historical data found"}
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Apply spread if provided
            if spread_pips is not None:
                symbol_info = self.connector.get_symbol_info(symbol)
                if symbol_info:
                    point = symbol_info.point
                    df['ask'] = df['close'] + (spread_pips * 10 * point)
                    df['bid'] = df['close']
                else:
                    # Fallback if symbol info not available
                    df['ask'] = df['close'] + (spread_pips * 0.0001)
                    df['bid'] = df['close']
            else:
                # Use historical spread
                df['ask'] = df['close']
                df['bid'] = df['close']
            
            # Initialize state
            self.current_balance = initial_balance
            trades = []
            positions = {}
            equity_curve = []
            
            # Get strategy instance
            strategy = self.strategies[strategy_name]
            
            # Prepare initial state
            strategy.prepare_indicators(df)
            
            # Run backtest
            logger.info(f"Running backtest simulation on {len(df)} candles")
            
            for i in range(100, len(df)):  # Skip first 100 bars for indicators to warm up
                current_time = df.iloc[i]['time']
                current_bar = df.iloc[i-100:i+1].copy()
                
                # Calculate account metrics
                unrealized_pnl = 0
                for pos_symbol, position in positions.items():
                    if position['type'] == 'buy':
                        unrealized_pnl += position['volume'] * (df.iloc[i]['bid'] - position['entry_price']) / 0.0001
                    else:
                        unrealized_pnl += position['volume'] * (position['entry_price'] - df.iloc[i]['ask']) / 0.0001
                
                equity = self.current_balance + unrealized_pnl
                equity_curve.append({
                    'time': current_time,
                    'balance': self.current_balance,
                    'equity': equity,
                    'open_positions': len(positions)
                })
                
                # Close completed trades
                positions_to_remove = []
                for pos_symbol, position in positions.items():
                    # Check take profit
                    if position['type'] == 'buy' and df.iloc[i]['high'] >= position['take_profit']:
                        profit = position['volume'] * (position['take_profit'] - position['entry_price']) / 0.0001
                        profit -= commission  # Apply commission
                        
                        self.current_balance += profit
                        positions_to_remove.append(pos_symbol)
                        
                        trades.append({
                            'symbol': position['symbol'],
                            'type': position['type'],
                            'entry_time': position['entry_time'],
                            'entry_price': position['entry_price'],
                            'exit_time': current_time,
                            'exit_price': position['take_profit'],
                            'volume': position['volume'],
                            'profit': profit,
                            'pips': (position['take_profit'] - position['entry_price']) / 0.0001,
                            'exit_reason': 'take_profit'
                        })
                        
                    # Check stop loss
                    elif position['type'] == 'buy' and df.iloc[i]['low'] <= position['stop_loss']:
                        loss = position['volume'] * (position['stop_loss'] - position['entry_price']) / 0.0001
                        loss -= commission  # Apply commission
                        
                        self.current_balance += loss
                        positions_to_remove.append(pos_symbol)
                        
                        trades.append({
                            'symbol': position['symbol'],
                            'type': position['type'],
                            'entry_time': position['entry_time'],
                            'entry_price': position['entry_price'],
                            'exit_time': current_time,
                            'exit_price': position['stop_loss'],
                            'volume': position['volume'],
                            'profit': loss,
                            'pips': (position['stop_loss'] - position['entry_price']) / 0.0001,
                            'exit_reason': 'stop_loss'
                        })
                    
                    # Check take profit for sell positions
                    elif position['type'] == 'sell' and df.iloc[i]['low'] <= position['take_profit']:
                        profit = position['volume'] * (position['entry_price'] - position['take_profit']) / 0.0001
                        profit -= commission  # Apply commission
                        
                        self.current_balance += profit
                        positions_to_remove.append(pos_symbol)
                        
                        trades.append({
                            'symbol': position['symbol'],
                            'type': position['type'],
                            'entry_time': position['entry_time'],
                            'entry_price': position['entry_price'],
                            'exit_time': current_time,
                            'exit_price': position['take_profit'],
                            'volume': position['volume'],
                            'profit': profit,
                            'pips': (position['entry_price'] - position['take_profit']) / 0.0001,
                            'exit_reason': 'take_profit'
                        })
                    
                    # Check stop loss for sell positions
                    elif position['type'] == 'sell' and df.iloc[i]['high'] >= position['stop_loss']:
                        loss = position['volume'] * (position['entry_price'] - position['stop_loss']) / 0.0001
                        loss -= commission  # Apply commission
                        
                        self.current_balance += loss
                        positions_to_remove.append(pos_symbol)
                        
                        trades.append({
                            'symbol': position['symbol'],
                            'type': position['type'],
                            'entry_time': position['entry_time'],
                            'entry_price': position['entry_price'],
                            'exit_time': current_time,
                            'exit_price': position['stop_loss'],
                            'volume': position['volume'],
                            'profit': loss,
                            'pips': (position['entry_price'] - position['stop_loss']) / 0.0001,
                            'exit_reason': 'stop_loss'
                        })
                
                # Remove closed positions
                for pos_symbol in positions_to_remove:
                    del positions[pos_symbol]
                
                # Get strategy signals
                signals = strategy.generate_signals(current_bar, symbol, timeframe)
                
                # Process signals
                for signal in signals:
                    # Check if we already have a position for this symbol
                    if f"{symbol}_{signal['direction']}" in positions:
                        continue
                        
                    # Calculate position size based on risk
                    risk_amount = self.current_balance * signal.get('risk_percent', 0.01)
                    price = df.iloc[i]['ask'] if signal['direction'] == 'buy' else df.iloc[i]['bid']
                    stop_loss = signal.get('stop_loss', price * 0.99 if signal['direction'] == 'buy' else price * 1.01)
                    
                    risk_per_pip = risk_amount / abs((price - stop_loss) / 0.0001)
                    volume = round(risk_per_pip / 10, 2)  # Standard lot size calculation
                    
                    if volume < 0.01:  # Minimum lot size
                        volume = 0.01
                    
                    # Create position
                    position = {
                        'symbol': symbol,
                        'type': signal['direction'],
                        'entry_time': current_time,
                        'entry_price': price + (slippage_pips * 0.0001) if signal['direction'] == 'buy' else price - (slippage_pips * 0.0001),
                        'stop_loss': stop_loss,
                        'take_profit': signal.get('take_profit', price * 1.01 if signal['direction'] == 'buy' else price * 0.99),
                        'volume': volume
                    }
                    
                    positions[f"{symbol}_{signal['direction']}"] = position
            
            # Close any remaining positions at the last price
            for pos_symbol, position in positions.items():
                last_price = df.iloc[-1]['bid'] if position['type'] == 'buy' else df.iloc[-1]['ask']
                
                if position['type'] == 'buy':
                    profit = position['volume'] * (last_price - position['entry_price']) / 0.0001
                else:
                    profit = position['volume'] * (position['entry_price'] - last_price) / 0.0001
                
                profit -= commission  # Apply commission
                self.current_balance += profit
                
                trades.append({
                    'symbol': position['symbol'],
                    'type': position['type'],
                    'entry_time': position['entry_time'],
                    'entry_price': position['entry_price'],
                    'exit_time': df.iloc[-1]['time'],
                    'exit_price': last_price,
                    'volume': position['volume'],
                    'profit': profit,
                    'pips': (last_price - position['entry_price']) / 0.0001 if position['type'] == 'buy' else (position['entry_price'] - last_price) / 0.0001,
                    'exit_reason': 'end_of_test'
                })
            
            # Convert equity curve to DataFrame
            equity_df = pd.DataFrame(equity_curve)
            
            # Calculate performance metrics
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['profit'] > 0])
            losing_trades = len([t for t in trades if t['profit'] <= 0])
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            total_profit = sum(t['profit'] for t in trades)
            total_pips = sum(t['pips'] for t in trades)
            
            if winning_trades > 0:
                avg_win = sum(t['profit'] for t in trades if t['profit'] > 0) / winning_trades
            else:
                avg_win = 0
                
            if losing_trades > 0:
                avg_loss = sum(t['profit'] for t in trades if t['profit'] <= 0) / losing_trades
            else:
                avg_loss = 0
            
            profit_factor = abs(sum(t['profit'] for t in trades if t['profit'] > 0) / sum(t['profit'] for t in trades if t['profit'] <= 0)) if sum(t['profit'] for t in trades if t['profit'] <= 0) != 0 else float('inf')
            
            # Calculate drawdown
            max_balance = initial_balance
            max_drawdown = 0
            max_drawdown_pct = 0
            
            for i in range(len(equity_df)):
                if equity_df.iloc[i]['equity'] > max_balance:
                    max_balance = equity_df.iloc[i]['equity']
                
                drawdown = max_balance - equity_df.iloc[i]['equity']
                drawdown_pct = drawdown / max_balance
                
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                
                if drawdown_pct > max_drawdown_pct:
                    max_drawdown_pct = drawdown_pct
            
            # Calculate Sharpe ratio
            if len(equity_df) > 1:
                equity_returns = equity_df['equity'].pct_change().dropna()
                sharpe_ratio = (equity_returns.mean() * 252) / (equity_returns.std() * np.sqrt(252)) if equity_returns.std() > 0 else 0
            else:
                sharpe_ratio = 0
                
            # Save results
            results = {
                'success': True,
                'strategy': strategy_name,
                'symbol': symbol,
                'timeframe': timeframe,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'initial_balance': initial_balance,
                'final_balance': self.current_balance,
                'total_profit': total_profit,
                'total_profit_pct': (total_profit / initial_balance) * 100,
                'total_pips': total_pips,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'max_drawdown_pct': max_drawdown_pct,
                'sharpe_ratio': sharpe_ratio,
                'trades': trades,
                'equity_curve': equity_df.to_dict(orient='records')
            }
            
            self.results[f"{strategy_name}_{symbol}_{timeframe}"] = results
            
            logger.info(f"Backtest completed: {total_trades} trades, Win rate: {win_rate:.2%}, Profit: {total_profit:.2f}")
            return results
            
        except Exception as e:
            logger.exception(f"Error in backtest: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def generate_report(self, result_key: str, output_dir: str = "reports") -> str:
        """
        Generate HTML report for a backtest result
        
        Args:
            result_key: Key of the result to generate report for
            output_dir: Directory to save report
            
        Returns:
            Path to the generated report
        """
        if result_key not in self.results:
            logger.error(f"Result {result_key} not found")
            return ""
        
        try:
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            result = self.results[result_key]
            
            # Convert trades to DataFrame
            trades_df = pd.DataFrame(result['trades'])
            
            # Convert equity curve to DataFrame
            equity_df = pd.DataFrame(result['equity_curve'])
            
            # Create report file
            report_path = f"{output_dir}/{result_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            
            # Generate HTML report
            with open(report_path, 'w') as f:
                f.write(f'''
                <html>
                <head>
                    <title>Backtest Report: {result_key}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        h1, h2, h3 {{ color: #333; }}
                        .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                        .chart {{ margin-bottom: 30px; }}
                        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                        th {{ background-color: #f2f2f2; }}
                        tr:nth-child(even) {{ background-color: #f9f9f9; }}
                        .win {{ color: green; }}
                        .loss {{ color: red; }}
                    </style>
                </head>
                <body>
                    <h1>Backtest Report: {result['strategy']} on {result['symbol']} {result['timeframe']}</h1>
                    
                    <div class="summary">
                        <h2>Summary</h2>
                        <p><strong>Period:</strong> {result['start_date']} to {result['end_date']}</p>
                        <p><strong>Initial Balance:</strong> ${result['initial_balance']:.2f}</p>
                        <p><strong>Final Balance:</strong> ${result['final_balance']:.2f}</p>
                        <p><strong>Total Profit:</strong> ${result['total_profit']:.2f} ({result['total_profit_pct']:.2f}%)</p>
                        <p><strong>Total Pips:</strong> {result['total_pips']:.2f}</p>
                        <p><strong>Total Trades:</strong> {result['total_trades']}</p>
                        <p><strong>Win Rate:</strong> {result['win_rate']*100:.2f}% ({result['winning_trades']} wins, {result['losing_trades']} losses)</p>
                        <p><strong>Average Win:</strong> ${result['avg_win']:.2f}</p>
                        <p><strong>Average Loss:</strong> ${result['avg_loss']:.2f}</p>
                        <p><strong>Profit Factor:</strong> {result['profit_factor']:.2f}</p>
                        <p><strong>Maximum Drawdown:</strong> ${result['max_drawdown']:.2f} ({result['max_drawdown_pct']*100:.2f}%)</p>
                        <p><strong>Sharpe Ratio:</strong> {result['sharpe_ratio']:.2f}</p>
                    </div>
                    
                    <div class="chart">
                        <h2>Equity Curve</h2>
                        <img src="data:image/png;base64,{self._generate_equity_chart(equity_df)}" width="100%">
                    </div>
                    
                    <div class="chart">
                        <h2>Monthly Returns</h2>
                        <img src="data:image/png;base64,{self._generate_monthly_returns_chart(equity_df)}" width="100%">
                    </div>
                    
                    <h2>Trade List</h2>
                    <table>
                        <tr>
                            <th>#</th>
                            <th>Symbol</th>
                            <th>Type</th>
                            <th>Entry Time</th>
                            <th>Entry Price</th>
                            <th>Exit Time</th>
                            <th>Exit Price</th>
                            <th>Volume</th>
                            <th>Profit</th>
                            <th>Pips</th>
                            <th>Exit Reason</th>
                        </tr>
                ''')
                
                # Add trade rows
                for i, trade in enumerate(result['trades']):
                    profit_class = "win" if trade['profit'] > 0 else "loss"
                    f.write(f'''
                        <tr>
                            <td>{i+1}</td>
                            <td>{trade['symbol']}</td>
                            <td>{trade['type']}</td>
                            <td>{trade['entry_time']}</td>
                            <td>{trade['entry_price']:.5f}</td>
                            <td>{trade['exit_time']}</td>
                            <td>{trade['exit_price']:.5f}</td>
                            <td>{trade['volume']:.2f}</td>
                            <td class="{profit_class}">${trade['profit']:.2f}</td>
                            <td class="{profit_class}">{trade['pips']:.1f}</td>
                            <td>{trade['exit_reason']}</td>
                        </tr>
                    ''')
                
                f.write('''
                    </table>
                </body>
                </html>
                ''')
            
            logger.info(f"Report generated: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return ""
    
    def _generate_equity_chart(self, equity_df: pd.DataFrame) -> str:
        """
        Generate base64-encoded equity chart
        
        Args:
            equity_df: DataFrame with equity data
            
        Returns:
            Base64-encoded image
        """
        import io
        import base64
        
        # Create figure
        plt.figure(figsize=(12, 6))
        plt.plot(equity_df['time'], equity_df['balance'], label='Balance')
        plt.plot(equity_df['time'], equity_df['equity'], label='Equity')
        plt.title('Equity Curve')
        plt.xlabel('Time')
        plt.ylabel('Value')
        plt.legend()
        plt.grid(True)
        
        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return base64.b64encode(buf.read()).decode('utf-8')
    
    def _generate_monthly_returns_chart(self, equity_df: pd.DataFrame) -> str:
        """
        Generate base64-encoded monthly returns chart
        
        Args:
            equity_df: DataFrame with equity data
            
        Returns:
            Base64-encoded image
        """
        import io
        import base64
        
        # Convert time to datetime
        equity_df['time'] = pd.to_datetime(equity_df['time'])
        
        # Extract month and year
        equity_df['year_month'] = equity_df['time'].dt.strftime('%Y-%m')
        
        # Group by month and calculate returns
        monthly_returns = []
        
        for month, group in equity_df.groupby('year_month'):
            start_equity = group.iloc[0]['equity']
            end_equity = group.iloc[-1]['equity']
            return_pct = (end_equity - start_equity) / start_equity * 100
            monthly_returns.append({'month': month, 'return': return_pct})
        
        monthly_df = pd.DataFrame(monthly_returns)
        
        # Create figure
        plt.figure(figsize=(12, 6))
        bars = plt.bar(monthly_df['month'], monthly_df['return'])
        
        # Color bars based on return
        for i, bar in enumerate(bars):
            if monthly_df.iloc[i]['return'] >= 0:
                bar.set_color('green')
            else:
                bar.set_color('red')
        
        plt.title('Monthly Returns (%)')
        plt.xlabel('Month')
        plt.ylabel('Return (%)')
        plt.xticks(rotation=45)
        plt.grid(True, axis='y')
        plt.tight_layout()
        
        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return base64.b64encode(buf.read()).decode('utf-8')
    
    def cleanup(self) -> None:
        """Clean up resources"""
        if self.connector:
            self.connector.disconnect()
            
        logger.info("MT5 Backtester cleaned up")
