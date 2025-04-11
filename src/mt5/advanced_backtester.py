"""
Advanced MT5 Backtesting Module

Extends the base MT5Backtester with additional features:
- Multi-strategy testing
- Performance benchmarks
- Stress testing
- Edge case scenarios
- Statistical analysis
"""

import os
import time
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any, Set
from loguru import logger
import MetaTrader5 as mt5
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import copy
import random
import scipy.stats as stats

# Local imports
from src.mt5.backtester import MT5Backtester
from src.mt5.connector import MT5Connector
from src.mt5.data_feed import MT5DataFeed
from src.mt5.strategies import BaseStrategy
from src.market.market_condition_detector import MarketConditionDetector

class AdvancedBacktester(MT5Backtester):
    """
    Advanced backtesting engine with extended capabilities
    """
    
    def __init__(self, config: Dict = None, config_path: str = None):
        """
        Initialize the advanced backtester
        
        Args:
            config: Configuration dictionary
            config_path: Path to configuration file
        """
        super().__init__(config, config_path)
        
        # Advanced settings
        self.advanced_config = self.config.get('advanced_backtesting', {})
        self.enable_multi_strategy = self.advanced_config.get('enable_multi_strategy', True)
        self.enable_parallel = self.advanced_config.get('enable_parallel', True)
        self.max_workers = self.advanced_config.get('max_workers', multiprocessing.cpu_count() - 1)
        self.max_workers = max(1, self.max_workers)  # At least 1 worker
        
        # Statistical measures
        self.benchmark_results = {}
        self.stress_test_results = {}
        self.edge_case_results = {}
        self.multi_strategy_results = {}
        
        # Market condition detector
        self.market_detector = None
        if self.advanced_config.get('use_market_conditions', True):
            self.market_detector = MarketConditionDetector(self.config)
            
        logger.info(f"Advanced MT5 Backtester initialized with {self.max_workers} workers")
    
    def run_multi_strategy_backtest(self, 
                                   symbol: str, 
                                   timeframe: str, 
                                   strategy_names: List[str], 
                                   start_date: datetime, 
                                   end_date: datetime,
                                   initial_balance: float = 10000,
                                   commission: float = 0.0,
                                   slippage_pips: float = 0.0,
                                   spread_pips: Optional[float] = None) -> Dict:
        """
        Run backtest for multiple strategies on the same data
        
        Args:
            symbol: Symbol to backtest on
            timeframe: Timeframe to use
            strategy_names: List of strategy names to backtest
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_balance: Initial account balance
            commission: Commission per trade in account currency
            slippage_pips: Slippage in pips
            spread_pips: Custom spread in pips (None to use historical)
            
        Returns:
            Dictionary with backtest results for all strategies
        """
        if not self.enable_multi_strategy:
            logger.warning("Multi-strategy testing is disabled")
            return {}
            
        # Validate strategy names
        valid_strategies = [s for s in strategy_names if s in self.strategies]
        
        if not valid_strategies:
            logger.error("No valid strategies found for multi-strategy backtest")
            return {}
            
        logger.info(f"Running multi-strategy backtest for {len(valid_strategies)} strategies")
        
        # Create a unique key for this multi-strategy test
        key = f"multi_{symbol}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        
        # Fetch data once for all strategies
        mt5_timeframe = self.data_feed.get_mt5_timeframe(timeframe)
        data = self.data_feed.get_historical_data(symbol, mt5_timeframe, start_date, end_date)
        
        if data.empty:
            logger.error(f"No data available for {symbol} on {timeframe}")
            return {}
            
        # Run backtest for each strategy
        results = {}
        
        # Use parallel processing if enabled
        if self.enable_parallel and len(valid_strategies) > 1:
            futures = {}
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                for strategy_name in valid_strategies:
                    future = executor.submit(
                        self._run_strategy_backtest,
                        strategy_name, symbol, timeframe, data.copy(), 
                        start_date, end_date, initial_balance,
                        commission, slippage_pips, spread_pips
                    )
                    futures[future] = strategy_name
                
                for future in concurrent.futures.as_completed(futures):
                    strategy_name = futures[future]
                    try:
                        strategy_result = future.result()
                        results[strategy_name] = strategy_result
                    except Exception as e:
                        logger.error(f"Error in strategy {strategy_name}: {str(e)}")
        else:
            # Run sequentially
            for strategy_name in valid_strategies:
                try:
                    strategy_result = self._run_strategy_backtest(
                        strategy_name, symbol, timeframe, data.copy(), 
                        start_date, end_date, initial_balance,
                        commission, slippage_pips, spread_pips
                    )
                    results[strategy_name] = strategy_result
                except Exception as e:
                    logger.error(f"Error in strategy {strategy_name}: {str(e)}")
        
        # Combine results
        combined_result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "initial_balance": initial_balance,
            "strategies": results,
            "comparison": self._compare_strategy_results(results),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Store result
        self.multi_strategy_results[key] = combined_result
        
        logger.info(f"Multi-strategy backtest completed with key: {key}")
        return combined_result
    
    def _run_strategy_backtest(self, 
                             strategy_name: str, 
                             symbol: str, 
                             timeframe: str, 
                             data: pd.DataFrame, 
                             start_date: datetime, 
                             end_date: datetime,
                             initial_balance: float,
                             commission: float,
                             slippage_pips: float,
                             spread_pips: Optional[float]) -> Dict:
        """
        Run backtest for a single strategy (internal helper)
        """
        logger.debug(f"Running backtest for strategy {strategy_name}")
        
        strategy = self.strategies[strategy_name]
        
        # Configure strategy
        strategy.symbol = symbol
        strategy.timeframe = timeframe
        strategy.reset()
        
        # Processing variables
        current_balance = initial_balance
        current_equity = initial_balance
        open_trades = []
        closed_trades = []
        equity_curve = []
        
        # Track drawdown
        max_equity = initial_balance
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        
        # Track performance
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        break_even_trades = 0
        
        # Track pips and money
        total_pips = 0.0
        total_profit = 0.0
        largest_win = 0.0
        largest_loss = 0.0
        
        # Process data
        for i in range(len(data)):
            candle = data.iloc[i].to_dict()
            current_time = pd.to_datetime(candle['time'])
            
            # Skip data outside of date range
            if current_time < start_date or current_time > end_date:
                continue
                
            # Process open trades
            for trade in open_trades[:]:
                # Calculate current trade values
                if trade['type'] == 'buy':
                    trade['current_price'] = candle['close']
                    trade['current_profit_pips'] = (candle['close'] - trade['entry_price']) * 10000
                    trade['current_profit'] = trade['current_profit_pips'] * trade['pip_value'] * trade['volume']
                else:  # sell
                    trade['current_price'] = candle['close']
                    trade['current_profit_pips'] = (trade['entry_price'] - candle['close']) * 10000
                    trade['current_profit'] = trade['current_profit_pips'] * trade['pip_value'] * trade['volume']
                
                # Apply commission
                trade['current_profit'] -= commission
                
                # Check if SL or TP is hit
                exit_reason = None
                
                if trade['type'] == 'buy':
                    if candle['low'] <= trade['sl_price']:
                        exit_reason = 'sl'
                        exit_price = trade['sl_price']
                        exit_profit_pips = (exit_price - trade['entry_price']) * 10000
                    elif candle['high'] >= trade['tp_price']:
                        exit_reason = 'tp'
                        exit_price = trade['tp_price']
                        exit_profit_pips = (exit_price - trade['entry_price']) * 10000
                else:  # sell
                    if candle['high'] >= trade['sl_price']:
                        exit_reason = 'sl'
                        exit_price = trade['sl_price']
                        exit_profit_pips = (trade['entry_price'] - exit_price) * 10000
                    elif candle['low'] <= trade['tp_price']:
                        exit_reason = 'tp'
                        exit_price = trade['tp_price']
                        exit_profit_pips = (trade['entry_price'] - exit_price) * 10000
                
                # Close trade if needed
                if exit_reason:
                    exit_profit = exit_profit_pips * trade['pip_value'] * trade['volume']
                    
                    trade['exit_time'] = candle['time']
                    trade['exit_price'] = exit_price
                    trade['exit_reason'] = exit_reason
                    trade['profit_pips'] = exit_profit_pips
                    trade['profit'] = exit_profit
                    
                    # Update performance metrics
                    total_trades += 1
                    total_pips += exit_profit_pips
                    total_profit += exit_profit
                    
                    if exit_profit > 0:
                        winning_trades += 1
                        largest_win = max(largest_win, exit_profit)
                    elif exit_profit < 0:
                        losing_trades += 1
                        largest_loss = min(largest_loss, exit_profit)
                    else:
                        break_even_trades += 1
                    
                    # Update balance
                    current_balance += exit_profit
                    
                    # Move to closed trades
                    closed_trades.append(trade)
                    open_trades.remove(trade)
            
            # Update equity
            current_equity = current_balance + sum(t['current_profit'] for t in open_trades)
            
            # Update drawdown
            if current_equity > max_equity:
                max_equity = current_equity
            
            drawdown = max_equity - current_equity
            drawdown_pct = drawdown / max_equity if max_equity > 0 else 0
            
            max_drawdown = max(max_drawdown, drawdown)
            max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)
            
            # Add to equity curve
            equity_curve.append({
                'time': candle['time'],
                'balance': current_balance,
                'equity': current_equity,
                'drawdown': drawdown,
                'drawdown_pct': drawdown_pct
            })
            
            # Get strategy signals
            try:
                # Prepare market data for strategy
                market_data = {
                    'open': data['open'].values[:i+1],
                    'high': data['high'].values[:i+1],
                    'low': data['low'].values[:i+1],
                    'close': data['close'].values[:i+1],
                    'volume': data['tick_volume'].values[:i+1],
                    'time': data['time'].values[:i+1]
                }
                
                signals = strategy.generate_signals(market_data)
                
                # Process signals
                for signal in signals:
                    # Ensure we have valid signal
                    if 'action' not in signal or signal['action'] not in ['buy', 'sell']:
                        continue
                    
                    # Calculate lot size
                    lot_size = 0.01  # Minimum
                    
                    # Calculate pip value
                    if symbol.endswith('JPY'):
                        pip_value = lot_size * 1000  # 1 pip = 0.01 for JPY pairs
                    else:
                        pip_value = lot_size * 10  # 1 pip = 0.0001 for other pairs
                    
                    # Create trade
                    trade = {
                        'symbol': symbol,
                        'type': signal['action'],
                        'entry_time': candle['time'],
                        'entry_price': candle['close'],
                        'volume': lot_size,
                        'pip_value': pip_value,
                        'sl_price': signal.get('sl_price'),
                        'tp_price': signal.get('tp_price'),
                        'current_price': candle['close'],
                        'current_profit_pips': 0.0,
                        'current_profit': 0.0
                    }
                    
                    # If SL/TP not provided, use pips
                    if 'sl_pips' in signal and 'sl_price' not in trade:
                        if trade['type'] == 'buy':
                            trade['sl_price'] = trade['entry_price'] - signal['sl_pips'] / 10000
                        else:
                            trade['sl_price'] = trade['entry_price'] + signal['sl_pips'] / 10000
                    
                    if 'tp_pips' in signal and 'tp_price' not in trade:
                        if trade['type'] == 'buy':
                            trade['tp_price'] = trade['entry_price'] + signal['tp_pips'] / 10000
                        else:
                            trade['tp_price'] = trade['entry_price'] - signal['tp_pips'] / 10000
                    
                    # Add to open trades
                    open_trades.append(trade)
            
            except Exception as e:
                logger.error(f"Error processing strategy signals: {str(e)}")
        
        # Close any remaining open trades at the last price
        last_price = data.iloc[-1]['close']
        for trade in open_trades[:]:
            if trade['type'] == 'buy':
                exit_profit_pips = (last_price - trade['entry_price']) * 10000
            else:  # sell
                exit_profit_pips = (trade['entry_price'] - last_price) * 10000
                
            exit_profit = exit_profit_pips * trade['pip_value'] * trade['volume']
            exit_profit -= commission  # Apply commission
            
            trade['exit_time'] = data.iloc[-1]['time']
            trade['exit_price'] = last_price
            trade['exit_reason'] = 'end_of_test'
            trade['profit_pips'] = exit_profit_pips
            trade['profit'] = exit_profit
            
            # Update performance metrics
            total_trades += 1
            total_pips += exit_profit_pips
            total_profit += exit_profit
            
            if exit_profit > 0:
                winning_trades += 1
                largest_win = max(largest_win, exit_profit)
            elif exit_profit < 0:
                losing_trades += 1
                largest_loss = min(largest_loss, exit_profit)
            else:
                break_even_trades += 1
            
            # Update balance
            current_balance += exit_profit
            
            # Move to closed trades
            closed_trades.append(trade)
        
        # Clear open trades
        open_trades = []
        
        # Calculate final equity
        current_equity = current_balance
        
        # Calculate performance metrics
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        profit_factor = abs(sum(t['profit'] for t in closed_trades if t['profit'] > 0)) / abs(sum(t['profit'] for t in closed_trades if t['profit'] < 0)) if sum(t['profit'] for t in closed_trades if t['profit'] < 0) != 0 else float('inf')
        average_win = sum(t['profit'] for t in closed_trades if t['profit'] > 0) / winning_trades if winning_trades > 0 else 0
        average_loss = sum(t['profit'] for t in closed_trades if t['profit'] < 0) / losing_trades if losing_trades > 0 else 0
        expectancy = (win_rate * average_win) - ((1 - win_rate) * abs(average_loss)) if total_trades > 0 else 0
        
        # Calculate Sharpe ratio
        equity_df = pd.DataFrame(equity_curve)
        equity_df['return'] = equity_df['equity'].pct_change().fillna(0)
        sharpe_ratio = (equity_df['return'].mean() / equity_df['return'].std()) * np.sqrt(252) if equity_df['return'].std() > 0 else 0
        
        # Calculate Sortino ratio
        negative_returns = equity_df['return'][equity_df['return'] < 0]
        sortino_ratio = (equity_df['return'].mean() / negative_returns.std()) * np.sqrt(252) if len(negative_returns) > 0 and negative_returns.std() > 0 else 0
        
        # Calculate CAR and MDD
        years = (end_date - start_date).days / 365.25
        car = ((current_equity / initial_balance) ** (1 / years) - 1) if years > 0 else 0
        mdd = max_drawdown_pct
        
        # Calculate Calmar ratio
        calmar_ratio = car / mdd if mdd > 0 else float('inf')
        
        # Prepare results
        result = {
            "strategy": strategy_name,
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "initial_balance": initial_balance,
            "final_balance": current_balance,
            "net_profit": current_balance - initial_balance,
            "profit_percentage": ((current_balance - initial_balance) / initial_balance) * 100,
            "max_drawdown": max_drawdown,
            "max_drawdown_percentage": max_drawdown_pct * 100,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "break_even_trades": break_even_trades,
            "win_rate": win_rate * 100,
            "profit_factor": profit_factor,
            "average_win": average_win,
            "average_loss": average_loss,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "total_pips": total_pips,
            "expectancy": expectancy,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "car": car * 100,  # Compound Annual Return in percentage
            "calmar_ratio": calmar_ratio,
            "equity_curve": equity_curve,
            "trades": closed_trades
        }
        
        return result

    def _compare_strategy_results(self, strategy_results: Dict) -> Dict:
        """
        Compare results from multiple strategies
        
        Args:
            strategy_results: Dictionary with strategy results
            
        Returns:
            Comparison metrics
        """
        if not strategy_results:
            return {}
            
        # Prepare comparison metrics
        metrics = {
            "net_profit": {},
            "profit_percentage": {},
            "max_drawdown_percentage": {},
            "win_rate": {},
            "profit_factor": {},
            "expectancy": {},
            "sharpe_ratio": {},
            "sortino_ratio": {},
            "car": {},
            "calmar_ratio": {},
        }
        
        # Extract metrics for each strategy
        for strategy_name, result in strategy_results.items():
            for metric in metrics:
                if metric in result:
                    metrics[metric][strategy_name] = result[metric]
        
        # Find best strategy for each metric
        best_strategies = {}
        for metric, values in metrics.items():
            if not values:
                continue
                
            # Determine if higher is better or lower is better
            higher_is_better = True
            if metric in ["max_drawdown_percentage"]:
                higher_is_better = False
                
            if higher_is_better:
                best_strategy = max(values, key=values.get)
                best_value = values[best_strategy]
            else:
                best_strategy = min(values, key=values.get)
                best_value = values[best_strategy]
                
            best_strategies[metric] = {
                "best_strategy": best_strategy,
                "value": best_value
            }
        
        # Calculate correlation between equity curves
        equity_correlation = {}
        for name1, result1 in strategy_results.items():
            equity_correlation[name1] = {}
            for name2, result2 in strategy_results.items():
                if name1 == name2:
                    equity_correlation[name1][name2] = 1.0
                    continue
                    
                # Convert equity curves to DataFrames
                equity1 = pd.DataFrame(result1.get("equity_curve", []))
                equity2 = pd.DataFrame(result2.get("equity_curve", []))
                
                if not equity1.empty and not equity2.empty:
                    # Align time indices
                    equity1.set_index("time", inplace=True)
                    equity2.set_index("time", inplace=True)
                    
                    # Resample to ensure alignment
                    common_index = equity1.index.intersection(equity2.index)
                    if len(common_index) > 1:
                        corr = equity1.loc[common_index, "equity"].corr(equity2.loc[common_index, "equity"])
                        equity_correlation[name1][name2] = corr
                    else:
                        equity_correlation[name1][name2] = None
                else:
                    equity_correlation[name1][name2] = None
        
        # Return comparison
        return {
            "metrics": metrics,
            "best_strategies": best_strategies,
            "equity_correlation": equity_correlation
        }
    
    def run_benchmark_test(self, 
                          symbol: str, 
                          timeframe: str, 
                          strategy_name: str, 
                          start_date: datetime, 
                          end_date: datetime,
                          initial_balance: float = 10000,
                          benchmark_type: str = "buy_and_hold") -> Dict:
        """
        Run a benchmark test to compare strategy against standard benchmarks
        
        Args:
            symbol: Symbol to backtest on
            timeframe: Timeframe to use
            strategy_name: Name of strategy to backtest
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_balance: Initial account balance
            benchmark_type: Type of benchmark (buy_and_hold, random, etc.)
            
        Returns:
            Dictionary with strategy and benchmark results
        """
        logger.info(f"Running benchmark test for {strategy_name} against {benchmark_type}")
        
        # Validate strategy
        if strategy_name not in self.strategies:
            logger.error(f"Strategy {strategy_name} not found")
            return {}
        
        # Create a unique key for this benchmark test
        key = f"bench_{symbol}_{timeframe}_{strategy_name}_{benchmark_type}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        
        # Get strategy result
        strategy_result = self.run_backtest(
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            initial_balance=initial_balance
        )
        
        # Run benchmark backtest
        benchmark_result = {}
        
        if benchmark_type == "buy_and_hold":
            benchmark_result = self._run_buy_and_hold_benchmark(
                symbol, timeframe, start_date, end_date, initial_balance
            )
        elif benchmark_type == "random":
            benchmark_result = self._run_random_benchmark(
                symbol, timeframe, start_date, end_date, initial_balance
            )
        else:
            logger.error(f"Unknown benchmark type: {benchmark_type}")
            return {}
        
        # Compare results
        comparison = self._compare_benchmark_results(strategy_result, benchmark_result)
        
        # Store result
        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "strategy_name": strategy_name,
            "benchmark_type": benchmark_type,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "strategy_result": strategy_result,
            "benchmark_result": benchmark_result,
            "comparison": comparison,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.benchmark_results[key] = result
        
        logger.info(f"Benchmark test completed with key: {key}")
        return result
    
    def _run_buy_and_hold_benchmark(self, 
                                  symbol: str, 
                                  timeframe: str, 
                                  start_date: datetime, 
                                  end_date: datetime,
                                  initial_balance: float) -> Dict:
        """
        Run a buy-and-hold benchmark test
        """
        # Fetch data
        mt5_timeframe = self.data_feed.get_mt5_timeframe(timeframe)
        data = self.data_feed.get_historical_data(symbol, mt5_timeframe, start_date, end_date)
        
        if data.empty:
            logger.error(f"No data available for {symbol} on {timeframe}")
            return {}
        
        # Get start and end prices
        start_price = data.iloc[0]['close']
        end_price = data.iloc[-1]['close']
        
        # Calculate lot size based on initial balance and leverage
        leverage = self.config.get('mt5', {}).get('leverage', 100)
        lot_size = (initial_balance * leverage) / (start_price * 100000)
        lot_size = min(max(lot_size, 0.01), 10.0)  # Limit lot size between 0.01 and 10.0
        
        # Calculate pip value
        if symbol.endswith('JPY'):
            pip_value = lot_size * 1000  # 1 pip = 0.01 for JPY pairs
        else:
            pip_value = lot_size * 10  # 1 pip = 0.0001 for other pairs
        
        # Calculate profit in pips
        profit_pips = (end_price - start_price) * 10000
        if symbol.endswith('JPY'):
            profit_pips = profit_pips / 100  # Adjust for JPY pairs
            
        # Calculate profit in money
        profit = profit_pips * pip_value
        
        # Create equity curve
        equity_curve = []
        
        for i in range(len(data)):
            current_price = data.iloc[i]['close']
            current_profit_pips = (current_price - start_price) * 10000
            if symbol.endswith('JPY'):
                current_profit_pips = current_profit_pips / 100
                
            current_profit = current_profit_pips * pip_value
            current_equity = initial_balance + current_profit
            
            equity_curve.append({
                'time': data.iloc[i]['time'],
                'balance': initial_balance,
                'equity': current_equity,
                'drawdown': max(0, initial_balance - current_equity),
                'drawdown_pct': max(0, (initial_balance - current_equity) / initial_balance)
            })
            
        # Calculate max drawdown
        max_equity = initial_balance
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        
        for point in equity_curve:
            if point['equity'] > max_equity:
                max_equity = point['equity']
            
            drawdown = max_equity - point['equity']
            drawdown_pct = drawdown / max_equity if max_equity > 0 else 0
            
            max_drawdown = max(max_drawdown, drawdown)
            max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)
        
        # Calculate CAR
        years = (end_date - start_date).days / 365.25
        car = ((initial_balance + profit) / initial_balance) ** (1 / years) - 1 if years > 0 else 0
        
        # Calculate Sharpe ratio
        equity_df = pd.DataFrame(equity_curve)
        equity_df['return'] = equity_df['equity'].pct_change().fillna(0)
        sharpe_ratio = (equity_df['return'].mean() / equity_df['return'].std()) * np.sqrt(252) if equity_df['return'].std() > 0 else 0
        
        # Prepare results
        result = {
            "strategy": "buy_and_hold",
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "initial_balance": initial_balance,
            "final_balance": initial_balance + profit,
            "net_profit": profit,
            "profit_percentage": (profit / initial_balance) * 100,
            "max_drawdown": max_drawdown,
            "max_drawdown_percentage": max_drawdown_pct * 100,
            "total_trades": 1,
            "winning_trades": 1 if profit > 0 else 0,
            "losing_trades": 1 if profit < 0 else 0,
            "break_even_trades": 1 if profit == 0 else 0,
            "win_rate": 100 if profit > 0 else 0,
            "profit_factor": float('inf') if profit > 0 else 0,
            "average_win": profit if profit > 0 else 0,
            "average_loss": profit if profit < 0 else 0,
            "largest_win": profit if profit > 0 else 0,
            "largest_loss": profit if profit < 0 else 0,
            "total_pips": profit_pips,
            "expectancy": profit,
            "sharpe_ratio": sharpe_ratio,
            "car": car * 100,  # Compound Annual Return in percentage
            "calmar_ratio": car / max_drawdown_pct if max_drawdown_pct > 0 else float('inf'),
            "equity_curve": equity_curve,
            "trades": [{
                "symbol": symbol,
                "type": "buy",
                "entry_time": data.iloc[0]['time'],
                "entry_price": start_price,
                "exit_time": data.iloc[-1]['time'],
                "exit_price": end_price,
                "volume": lot_size,
                "profit_pips": profit_pips,
                "profit": profit,
                "exit_reason": "end_of_test"
            }]
        }
        
        return result
    
    def _run_random_benchmark(self, 
                            symbol: str, 
                            timeframe: str, 
                            start_date: datetime, 
                            end_date: datetime,
                            initial_balance: float) -> Dict:
        """
        Run a random trading benchmark test
        """
        # Fetch data
        mt5_timeframe = self.data_feed.get_mt5_timeframe(timeframe)
        data = self.data_feed.get_historical_data(symbol, mt5_timeframe, start_date, end_date)
        
        if data.empty:
            logger.error(f"No data available for {symbol} on {timeframe}")
            return {}
        
        # Set random seed for reproducibility
        random.seed(42)
        
        # Processing variables
        current_balance = initial_balance
        current_equity = initial_balance
        open_trades = []
        closed_trades = []
        equity_curve = []
        
        # Track drawdown
        max_equity = initial_balance
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        
        # Track performance
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        break_even_trades = 0
        
        # Track pips and money
        total_pips = 0.0
        total_profit = 0.0
        largest_win = 0.0
        largest_loss = 0.0
        
        # Settings for random trading
        trade_probability = 0.05  # Probability of opening a trade on each candle
        lot_size = 0.01  # Standard lot size
        sl_pips = 20  # Stop loss in pips
        tp_pips = 40  # Take profit in pips
        
        # Calculate pip value
        if symbol.endswith('JPY'):
            pip_value = lot_size * 1000  # 1 pip = 0.01 for JPY pairs
            pip_multiplier = 0.01
        else:
            pip_value = lot_size * 10  # 1 pip = 0.0001 for other pairs
            pip_multiplier = 0.0001
        
        # Process data
        for i in range(len(data)):
            candle = data.iloc[i].to_dict()
            current_time = pd.to_datetime(candle['time'])
            
            # Skip data outside of date range
            if current_time < start_date or current_time > end_date:
                continue
                
            # Process open trades
            for trade in open_trades[:]:
                # Calculate current trade values
                if trade['type'] == 'buy':
                    trade['current_price'] = candle['close']
                    trade['current_profit_pips'] = (candle['close'] - trade['entry_price']) / pip_multiplier
                    trade['current_profit'] = trade['current_profit_pips'] * pip_value * trade['volume']
                else:  # sell
                    trade['current_price'] = candle['close']
                    trade['current_profit_pips'] = (trade['entry_price'] - candle['close']) / pip_multiplier
                    trade['current_profit'] = trade['current_profit_pips'] * pip_value * trade['volume']
                
                # Check if SL or TP is hit
                exit_reason = None
                exit_price = None
                
                if trade['type'] == 'buy':
                    if candle['low'] <= trade['sl_price']:
                        exit_reason = 'sl'
                        exit_price = trade['sl_price']
                    elif candle['high'] >= trade['tp_price']:
                        exit_reason = 'tp'
                        exit_price = trade['tp_price']
                else:  # sell
                    if candle['high'] >= trade['sl_price']:
                        exit_reason = 'sl'
                        exit_price = trade['sl_price']
                    elif candle['low'] <= trade['tp_price']:
                        exit_reason = 'tp'
                        exit_price = trade['tp_price']
                
                # Close trade if needed
                if exit_reason:
                    if trade['type'] == 'buy':
                        exit_profit_pips = (exit_price - trade['entry_price']) / pip_multiplier
                    else:  # sell
                        exit_profit_pips = (trade['entry_price'] - exit_price) / pip_multiplier
                        
                    exit_profit = exit_profit_pips * pip_value * trade['volume']
                    
                    trade['exit_time'] = candle['time']
                    trade['exit_price'] = exit_price
                    trade['exit_reason'] = exit_reason
                    trade['profit_pips'] = exit_profit_pips
                    trade['profit'] = exit_profit
                    
                    # Update performance metrics
                    total_trades += 1
                    total_pips += exit_profit_pips
                    total_profit += exit_profit
                    
                    if exit_profit > 0:
                        winning_trades += 1
                        largest_win = max(largest_win, exit_profit)
                    elif exit_profit < 0:
                        losing_trades += 1
                        largest_loss = min(largest_loss, exit_profit)
                    else:
                        break_even_trades += 1
                    
                    # Update balance
                    current_balance += exit_profit
                    
                    # Move to closed trades
                    closed_trades.append(trade)
                    open_trades.remove(trade)
            
            # Update equity
            current_equity = current_balance + sum(t.get('current_profit', 0) for t in open_trades)
            
            # Update drawdown
            if current_equity > max_equity:
                max_equity = current_equity
            
            drawdown = max_equity - current_equity
            drawdown_pct = drawdown / max_equity if max_equity > 0 else 0
            
            max_drawdown = max(max_drawdown, drawdown)
            max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)
            
            # Add to equity curve
            equity_curve.append({
                'time': candle['time'],
                'balance': current_balance,
                'equity': current_equity,
                'drawdown': drawdown,
                'drawdown_pct': drawdown_pct
            })
            
            # Random trade entry
            if not open_trades and random.random() < trade_probability:
                # Randomly select buy or sell
                trade_type = random.choice(['buy', 'sell'])
                
                # Set SL and TP prices
                if trade_type == 'buy':
                    sl_price = candle['close'] - sl_pips * pip_multiplier
                    tp_price = candle['close'] + tp_pips * pip_multiplier
                else:  # sell
                    sl_price = candle['close'] + sl_pips * pip_multiplier
                    tp_price = candle['close'] - tp_pips * pip_multiplier
                
                # Create trade
                trade = {
                    'symbol': symbol,
                    'type': trade_type,
                    'entry_time': candle['time'],
                    'entry_price': candle['close'],
                    'volume': lot_size,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'current_price': candle['close'],
                    'current_profit_pips': 0.0,
                    'current_profit': 0.0
                }
                
                # Add to open trades
                open_trades.append(trade)
        
        # Close any remaining open trades at the last price
        last_price = data.iloc[-1]['close']
        for trade in open_trades[:]:
            if trade['type'] == 'buy':
                exit_profit_pips = (last_price - trade['entry_price']) / pip_multiplier
            else:  # sell
                exit_profit_pips = (trade['entry_price'] - last_price) / pip_multiplier
                
            exit_profit = exit_profit_pips * pip_value * trade['volume']
            
            trade['exit_time'] = data.iloc[-1]['time']
            trade['exit_price'] = last_price
            trade['exit_reason'] = 'end_of_test'
            trade['profit_pips'] = exit_profit_pips
            trade['profit'] = exit_profit
            
            # Update performance metrics
            total_trades += 1
            total_pips += exit_profit_pips
            total_profit += exit_profit
            
            if exit_profit > 0:
                winning_trades += 1
                largest_win = max(largest_win, exit_profit)
            elif exit_profit < 0:
                losing_trades += 1
                largest_loss = min(largest_loss, exit_profit)
            else:
                break_even_trades += 1
            
            # Update balance
            current_balance += exit_profit
            
            # Move to closed trades
            closed_trades.append(trade)
        
        # Clear open trades
        open_trades = []
        
        # Calculate final equity
        current_equity = current_balance
        
        # Calculate performance metrics
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        profit_factor = abs(sum(t['profit'] for t in closed_trades if t['profit'] > 0)) / abs(sum(t['profit'] for t in closed_trades if t['profit'] < 0)) if sum(t['profit'] for t in closed_trades if t['profit'] < 0) != 0 else float('inf')
        average_win = sum(t['profit'] for t in closed_trades if t['profit'] > 0) / winning_trades if winning_trades > 0 else 0
        average_loss = sum(t['profit'] for t in closed_trades if t['profit'] < 0) / losing_trades if losing_trades > 0 else 0
        expectancy = (win_rate * average_win) - ((1 - win_rate) * abs(average_loss)) if total_trades > 0 else 0
        
        # Calculate Sharpe ratio
        equity_df = pd.DataFrame(equity_curve)
        equity_df['return'] = equity_df['equity'].pct_change().fillna(0)
        sharpe_ratio = (equity_df['return'].mean() / equity_df['return'].std()) * np.sqrt(252) if equity_df['return'].std() > 0 else 0
        
        # Calculate CAR
        years = (end_date - start_date).days / 365.25
        car = ((current_equity / initial_balance) ** (1 / years) - 1) if years > 0 else 0
        
        # Prepare results
        result = {
            "strategy": "random",
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "initial_balance": initial_balance,
            "final_balance": current_balance,
            "net_profit": current_balance - initial_balance,
            "profit_percentage": ((current_balance - initial_balance) / initial_balance) * 100,
            "max_drawdown": max_drawdown,
            "max_drawdown_percentage": max_drawdown_pct * 100,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "break_even_trades": break_even_trades,
            "win_rate": win_rate * 100,
            "profit_factor": profit_factor,
            "average_win": average_win,
            "average_loss": average_loss,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "total_pips": total_pips,
            "expectancy": expectancy,
            "sharpe_ratio": sharpe_ratio,
            "car": car * 100,  # Compound Annual Return in percentage
            "calmar_ratio": car / max_drawdown_pct if max_drawdown_pct > 0 else float('inf'),
            "equity_curve": equity_curve,
            "trades": closed_trades
        }
        
        return result

    def _compare_benchmark_results(self, strategy_result: Dict, benchmark_result: Dict) -> Dict:
        """
        Compare strategy results against benchmark results
        
        Args:
            strategy_result: Strategy backtest results
            benchmark_result: Benchmark backtest results
            
        Returns:
            Comparison metrics
        """
        if not strategy_result or not benchmark_result:
            return {}
            
        # Extract key metrics
        metrics = [
            "net_profit", "profit_percentage", "max_drawdown_percentage",
            "win_rate", "profit_factor", "expectancy", "sharpe_ratio",
            "car", "calmar_ratio"
        ]
        
        comparison = {}
        
        for metric in metrics:
            if metric in strategy_result and metric in benchmark_result:
                strategy_value = strategy_result.get(metric, 0)
                benchmark_value = benchmark_result.get(metric, 0)
                
                # Calculate difference and relative performance
                difference = strategy_value - benchmark_value
                
                # Avoid division by zero
                if benchmark_value != 0:
                    relative_performance = (strategy_value / benchmark_value) - 1
                else:
                    relative_performance = float('inf') if strategy_value > 0 else (0 if strategy_value == 0 else float('-inf'))
                
                # Determine if higher is better
                higher_is_better = True
                if metric in ["max_drawdown_percentage"]:
                    higher_is_better = False
                
                # Determine if strategy outperforms benchmark
                if higher_is_better:
                    outperforms = strategy_value > benchmark_value
                else:
                    outperforms = strategy_value < benchmark_value
                
                comparison[metric] = {
                    "strategy_value": strategy_value,
                    "benchmark_value": benchmark_value,
                    "difference": difference,
                    "relative_performance": relative_performance * 100,  # As percentage
                    "outperforms": outperforms
                }
        
        # Calculate correlation between equity curves
        strategy_equity = pd.DataFrame(strategy_result.get("equity_curve", []))
        benchmark_equity = pd.DataFrame(benchmark_result.get("equity_curve", []))
        
        correlation = None
        
        if not strategy_equity.empty and not benchmark_equity.empty:
            # Align time indices
            strategy_equity.set_index("time", inplace=True)
            benchmark_equity.set_index("time", inplace=True)
            
            # Resample to ensure alignment
            common_index = strategy_equity.index.intersection(benchmark_equity.index)
            if len(common_index) > 1:
                correlation = strategy_equity.loc[common_index, "equity"].corr(benchmark_equity.loc[common_index, "equity"])
        
        # Return comparison
        return {
            "metrics": comparison,
            "equity_correlation": correlation
        }
    
    def run_stress_test(self, 
                       symbol: str, 
                       timeframe: str, 
                       strategy_name: str, 
                       start_date: datetime, 
                       end_date: datetime,
                       stress_type: str = "volatility",
                       stress_level: str = "high",
                       initial_balance: float = 10000) -> Dict:
        """
        Run a stress test for a strategy under extreme market conditions
        
        Args:
            symbol: Symbol to backtest on
            timeframe: Timeframe to use
            strategy_name: Name of strategy to backtest
            start_date: Start date for backtest
            end_date: End date for backtest
            stress_type: Type of stress test (volatility, slippage, spread)
            stress_level: Level of stress (low, medium, high)
            initial_balance: Initial account balance
            
        Returns:
            Dictionary with stress test results
        """
        logger.info(f"Running {stress_level} {stress_type} stress test for {strategy_name}")
        
        # Validate strategy
        if strategy_name not in self.strategies:
            logger.error(f"Strategy {strategy_name} not found")
            return {}
        
        # Create a unique key for this stress test
        key = f"stress_{symbol}_{timeframe}_{strategy_name}_{stress_type}_{stress_level}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        
        # Set stress parameters
        stress_params = {}
        
        if stress_type == "volatility":
            # Simulate increased volatility by modifying price data
            if stress_level == "low":
                stress_params["volatility_multiplier"] = 1.5
            elif stress_level == "medium":
                stress_params["volatility_multiplier"] = 2.0
            else:  # high
                stress_params["volatility_multiplier"] = 3.0
                
        elif stress_type == "slippage":
            # Simulate increased slippage
            if stress_level == "low":
                stress_params["slippage_pips"] = 2.0
            elif stress_level == "medium":
                stress_params["slippage_pips"] = 5.0
            else:  # high
                stress_params["slippage_pips"] = 10.0
                
        elif stress_type == "spread":
            # Simulate increased spread
            if stress_level == "low":
                stress_params["spread_pips"] = 2.0
            elif stress_level == "medium":
                stress_params["spread_pips"] = 5.0
            else:  # high
                stress_params["spread_pips"] = 10.0
                
        else:
            logger.error(f"Unknown stress type: {stress_type}")
            return {}
        
        # Run normal backtest for comparison
        normal_result = self.run_backtest(
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            initial_balance=initial_balance
        )
        
        # Run stressed backtest
        stressed_result = self._run_stressed_backtest(
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_balance=initial_balance,
            stress_type=stress_type,
            stress_params=stress_params
        )
        
        # Compare results
        comparison = self._compare_stress_results(normal_result, stressed_result)
        
        # Store result
        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "strategy_name": strategy_name,
            "stress_type": stress_type,
            "stress_level": stress_level,
            "stress_params": stress_params,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "normal_result": normal_result,
            "stressed_result": stressed_result,
            "comparison": comparison,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.stress_test_results[key] = result
        
        logger.info(f"Stress test completed with key: {key}")
        return result

    def _run_stressed_backtest(self,
                             strategy_name: str,
                             symbol: str,
                             timeframe: str,
                             start_date: datetime,
                             end_date: datetime,
                             initial_balance: float,
                             stress_type: str,
                             stress_params: Dict) -> Dict:
        """
        Run backtest with stressed conditions
        
        Args:
            strategy_name: Name of strategy to backtest
            symbol: Symbol to backtest on
            timeframe: Timeframe to use
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_balance: Initial account balance
            stress_type: Type of stress test
            stress_params: Stress parameters
            
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Running stressed backtest for {strategy_name} with {stress_type} stress")
        
        # Get strategy
        strategy = self.strategies[strategy_name]
        
        # Fetch data
        mt5_timeframe = self.data_feed.get_mt5_timeframe(timeframe)
        data = self.data_feed.get_historical_data(symbol, mt5_timeframe, start_date, end_date)
        
        if data.empty:
            logger.error(f"No data available for {symbol} on {timeframe}")
            return {}
            
        # Apply stress to data if needed
        if stress_type == "volatility":
            data = self._apply_volatility_stress(data, stress_params)
            
        # Configure parameters for backtest
        backtest_params = {
            "symbol": symbol,
            "timeframe": timeframe,
            "strategy_name": strategy_name,
            "start_date": start_date,
            "end_date": end_date,
            "initial_balance": initial_balance
        }
        
        # Add stress parameters
        if stress_type == "slippage":
            backtest_params["slippage_pips"] = stress_params.get("slippage_pips", 0.0)
        elif stress_type == "spread":
            backtest_params["spread_pips"] = stress_params.get("spread_pips", 0.0)
            
        # Run backtest with stressed data
        result = self.run_backtest(**backtest_params)
        
        return result
    
    def _apply_volatility_stress(self, data: pd.DataFrame, stress_params: Dict) -> pd.DataFrame:
        """
        Apply volatility stress to data
        
        Args:
            data: DataFrame with price data
            stress_params: Stress parameters
            
        Returns:
            Stressed DataFrame
        """
        volatility_multiplier = stress_params.get("volatility_multiplier", 1.0)
        
        if volatility_multiplier == 1.0:
            return data
            
        # Create a copy to avoid modifying original data
        stressed_data = data.copy()
        
        # Calculate average true range for each candle
        stressed_data['tr1'] = abs(stressed_data['high'] - stressed_data['low'])
        stressed_data['tr2'] = abs(stressed_data['high'] - stressed_data['close'].shift(1))
        stressed_data['tr3'] = abs(stressed_data['low'] - stressed_data['close'].shift(1))
        stressed_data['true_range'] = stressed_data[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        # Apply volatility multiplier
        for i in range(len(stressed_data)):
            if i == 0:
                continue
                
            # Get base values
            open_price = stressed_data.iloc[i]['open']
            close_price = stressed_data.iloc[i]['close']
            high_price = stressed_data.iloc[i]['high']
            low_price = stressed_data.iloc[i]['low']
            
            # Calculate midpoint
            midpoint = (open_price + close_price) / 2
            
            # Calculate new ranges based on volatility multiplier
            new_high = midpoint + (high_price - midpoint) * volatility_multiplier
            new_low = midpoint - (midpoint - low_price) * volatility_multiplier
            
            # Update values
            stressed_data.at[stressed_data.index[i], 'high'] = new_high
            stressed_data.at[stressed_data.index[i], 'low'] = new_low
            
        # Drop temporary columns
        stressed_data.drop(['tr1', 'tr2', 'tr3', 'true_range'], axis=1, inplace=True)
        
        logger.debug(f"Applied volatility stress with multiplier {volatility_multiplier}")
        return stressed_data
    
    def _compare_stress_results(self, normal_result: Dict, stressed_result: Dict) -> Dict:
        """
        Compare normal and stressed results
        
        Args:
            normal_result: Normal backtest results
            stressed_result: Stressed backtest results
            
        Returns:
            Comparison metrics
        """
        if not normal_result or not stressed_result:
            return {}
            
        # Extract key metrics
        metrics = [
            "net_profit", "profit_percentage", "max_drawdown_percentage",
            "win_rate", "profit_factor", "expectancy", "sharpe_ratio",
            "car", "calmar_ratio"
        ]
        
        comparison = {}
        
        for metric in metrics:
            if metric in normal_result and metric in stressed_result:
                normal_value = normal_result.get(metric, 0)
                stressed_value = stressed_result.get(metric, 0)
                
                # Calculate absolute and percentage changes
                absolute_change = stressed_value - normal_value
                
                # Avoid division by zero
                if normal_value != 0:
                    percentage_change = (stressed_value / normal_value - 1) * 100
                else:
                    percentage_change = float('inf') if stressed_value > 0 else (0 if stressed_value == 0 else float('-inf'))
                
                comparison[metric] = {
                    "normal_value": normal_value,
                    "stressed_value": stressed_value,
                    "absolute_change": absolute_change,
                    "percentage_change": percentage_change
                }
        
        # Calculate stress resistance score
        # For metrics where higher is better, less negative change is better
        # For metrics where lower is better, less positive change is better
        stress_scores = []
        
        for metric, values in comparison.items():
            higher_is_better = True
            if metric in ["max_drawdown_percentage"]:
                higher_is_better = False
                
            percentage_change = values["percentage_change"]
            
            if higher_is_better:
                # For higher is better, 0% change = 100% score, -100% change = 0% score
                score = max(0, 100 + min(0, percentage_change))
            else:
                # For lower is better, 0% change = 100% score, 100% change = 0% score
                score = max(0, 100 - max(0, percentage_change))
                
            stress_scores.append(score)
        
        # Calculate average stress resistance score
        stress_resistance = sum(stress_scores) / len(stress_scores) if stress_scores else 0
        
        return {
            "metrics": comparison,
            "stress_resistance": stress_resistance,
            "summary": f"Strategy has {stress_resistance:.1f}% stress resistance"
        }
    
    def run_edge_case_test(self, 
                         symbol: str, 
                         timeframe: str, 
                         strategy_name: str, 
                         edge_case_type: str = "gap",
                         edge_case_params: Dict = None,
                         initial_balance: float = 10000) -> Dict:
        """
        Run an edge case test for a strategy
        
        Args:
            symbol: Symbol to backtest on
            timeframe: Timeframe to use
            strategy_name: Name of strategy to backtest
            edge_case_type: Type of edge case (gap, flash_crash, etc.)
            edge_case_params: Edge case parameters
            initial_balance: Initial account balance
            
        Returns:
            Dictionary with edge case test results
        """
        logger.info(f"Running {edge_case_type} edge case test for {strategy_name}")
        
        # Validate strategy
        if strategy_name not in self.strategies:
            logger.error(f"Strategy {strategy_name} not found")
            return {}
        
        # Set default parameters if not provided
        if edge_case_params is None:
            edge_case_params = {}
            
        # Set default values for parameters
        if edge_case_type == "gap":
            edge_case_params.setdefault("gap_percentage", 2.0)
            edge_case_params.setdefault("gap_direction", "down")
            edge_case_params.setdefault("test_period", timedelta(days=30))
        elif edge_case_type == "flash_crash":
            edge_case_params.setdefault("crash_percentage", 5.0)
            edge_case_params.setdefault("recovery_percentage", 3.0)
            edge_case_params.setdefault("test_period", timedelta(days=7))
        elif edge_case_type == "high_volatility":
            edge_case_params.setdefault("volatility_multiplier", 3.0)
            edge_case_params.setdefault("test_period", timedelta(days=30))
        else:
            logger.error(f"Unknown edge case type: {edge_case_type}")
            return {}
            
        # Generate date ranges for test
        end_date = datetime.now()
        start_date = end_date - edge_case_params["test_period"]
        
        # Create a unique key for this edge case test
        key = f"edge_{symbol}_{timeframe}_{strategy_name}_{edge_case_type}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        
        # Run edge case test
        result = self._run_edge_case_backtest(
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_balance=initial_balance,
            edge_case_type=edge_case_type,
            edge_case_params=edge_case_params
        )
        
        # Store result
        self.edge_case_results[key] = result
        
        logger.info(f"Edge case test completed with key: {key}")
        return result
    
    def _run_edge_case_backtest(self,
                              strategy_name: str,
                              symbol: str,
                              timeframe: str,
                              start_date: datetime,
                              end_date: datetime,
                              initial_balance: float,
                              edge_case_type: str,
                              edge_case_params: Dict) -> Dict:
        """
        Run backtest with edge case conditions
        
        Args:
            strategy_name: Name of strategy to backtest
            symbol: Symbol to backtest on
            timeframe: Timeframe to use
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_balance: Initial account balance
            edge_case_type: Type of edge case
            edge_case_params: Edge case parameters
            
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Running edge case backtest for {strategy_name} with {edge_case_type} edge case")
        
        # Get strategy
        strategy = self.strategies[strategy_name]
        
        # Fetch data
        mt5_timeframe = self.data_feed.get_mt5_timeframe(timeframe)
        data = self.data_feed.get_historical_data(symbol, mt5_timeframe, start_date, end_date)
        
        if data.empty:
            logger.error(f"No data available for {symbol} on {timeframe}")
            return {}
            
        # Apply edge case to data
        if edge_case_type == "gap":
            data = self._apply_gap_edge_case(data, edge_case_params)
        elif edge_case_type == "flash_crash":
            data = self._apply_flash_crash_edge_case(data, edge_case_params)
        elif edge_case_type == "high_volatility":
            data = self._apply_high_volatility_edge_case(data, edge_case_params)
            
        # Run normal backtest
        normal_result = self.run_backtest(
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            initial_balance=initial_balance
        )
        
        # Process data with edge case
        # Configure strategy
        strategy.symbol = symbol
        strategy.timeframe = timeframe
        strategy.reset()
        
        # Processing variables
        current_balance = initial_balance
        current_equity = initial_balance
        open_trades = []
        closed_trades = []
        equity_curve = []
        
        # Track drawdown
        max_equity = initial_balance
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        
        # Track performance
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        break_even_trades = 0
        
        # Track pips and money
        total_pips = 0.0
        total_profit = 0.0
        largest_win = 0.0
        largest_loss = 0.0
        
        # Process data
        for i in range(len(data)):
            candle = data.iloc[i].to_dict()
            current_time = pd.to_datetime(candle['time'])
            
            # Skip data outside of date range
            if current_time < start_date or current_time > end_date:
                continue
                
            # Process open trades
            for trade in open_trades[:]:
                # Calculate current trade values
                if trade['type'] == 'buy':
                    trade['current_price'] = candle['close']
                    trade['current_profit_pips'] = (candle['close'] - trade['entry_price']) * 10000
                    trade['current_profit'] = trade['current_profit_pips'] * trade['pip_value'] * trade['volume']
                else:  # sell
                    trade['current_price'] = candle['close']
                    trade['current_profit_pips'] = (trade['entry_price'] - candle['close']) * 10000
                    trade['current_profit'] = trade['current_profit_pips'] * trade['pip_value'] * trade['volume']
                
                # Check if SL or TP is hit
                exit_reason = None
                
                if trade['type'] == 'buy':
                    if candle['low'] <= trade['sl_price']:
                        exit_reason = 'sl'
                        exit_price = trade['sl_price']
                        exit_profit_pips = (exit_price - trade['entry_price']) * 10000
                    elif candle['high'] >= trade['tp_price']:
                        exit_reason = 'tp'
                        exit_price = trade['tp_price']
                        exit_profit_pips = (exit_price - trade['entry_price']) * 10000
                else:  # sell
                    if candle['high'] >= trade['sl_price']:
                        exit_reason = 'sl'
                        exit_price = trade['sl_price']
                        exit_profit_pips = (trade['entry_price'] - exit_price) * 10000
                    elif candle['low'] <= trade['tp_price']:
                        exit_reason = 'tp'
                        exit_price = trade['tp_price']
                        exit_profit_pips = (trade['entry_price'] - exit_price) * 10000
                
                # Close trade if needed
                if exit_reason:
                    exit_profit = exit_profit_pips * trade['pip_value'] * trade['volume']
                    
                    trade['exit_time'] = candle['time']
                    trade['exit_price'] = exit_price
                    trade['exit_reason'] = exit_reason
                    trade['profit_pips'] = exit_profit_pips
                    trade['profit'] = exit_profit
                    
                    # Update performance metrics
                    total_trades += 1
                    total_pips += exit_profit_pips
                    total_profit += exit_profit
                    
                    if exit_profit > 0:
                        winning_trades += 1
                        largest_win = max(largest_win, exit_profit)
                    elif exit_profit < 0:
                        losing_trades += 1
                        largest_loss = min(largest_loss, exit_profit)
                    else:
                        break_even_trades += 1
                    
                    # Update balance
                    current_balance += exit_profit
                    
                    # Move to closed trades
                    closed_trades.append(trade)
                    open_trades.remove(trade)
            
            # Update equity
            current_equity = current_balance + sum(t['current_profit'] for t in open_trades)
            
            # Update drawdown
            if current_equity > max_equity:
                max_equity = current_equity
            
            drawdown = max_equity - current_equity
            drawdown_pct = drawdown / max_equity if max_equity > 0 else 0
            
            max_drawdown = max(max_drawdown, drawdown)
            max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)
            
            # Add to equity curve
            equity_curve.append({
                'time': candle['time'],
                'balance': current_balance,
                'equity': current_equity,
                'drawdown': drawdown,
                'drawdown_pct': drawdown_pct
            })
            
            # Get strategy signals
            try:
                # Prepare market data for strategy
                market_data = {
                    'open': data['open'].values[:i+1],
                    'high': data['high'].values[:i+1],
                    'low': data['low'].values[:i+1],
                    'close': data['close'].values[:i+1],
                    'volume': data['tick_volume'].values[:i+1],
                    'time': data['time'].values[:i+1]
                }
                
                signals = strategy.generate_signals(market_data)
                
                # Process signals
                for signal in signals:
                    # Ensure we have valid signal
                    if 'action' not in signal or signal['action'] not in ['buy', 'sell']:
                        continue
                    
                    # Calculate lot size
                    lot_size = 0.01  # Minimum
                    
                    # Calculate pip value
                    if symbol.endswith('JPY'):
                        pip_value = lot_size * 1000  # 1 pip = 0.01 for JPY pairs
                    else:
                        pip_value = lot_size * 10  # 1 pip = 0.0001 for other pairs
                    
                    # Create trade
                    trade = {
                        'symbol': symbol,
                        'type': signal['action'],
                        'entry_time': candle['time'],
                        'entry_price': candle['close'],
                        'volume': lot_size,
                        'pip_value': pip_value,
                        'sl_price': signal.get('sl_price'),
                        'tp_price': signal.get('tp_price'),
                        'current_price': candle['close'],
                        'current_profit_pips': 0.0,
                        'current_profit': 0.0
                    }
                    
                    # If SL/TP not provided, use pips
                    if 'sl_pips' in signal and 'sl_price' not in trade:
                        if trade['type'] == 'buy':
                            trade['sl_price'] = trade['entry_price'] - signal['sl_pips'] / 10000
                        else:
                            trade['sl_price'] = trade['entry_price'] + signal['sl_pips'] / 10000
                    
                    if 'tp_pips' in signal and 'tp_price' not in trade:
                        if trade['type'] == 'buy':
                            trade['tp_price'] = trade['entry_price'] + signal['tp_pips'] / 10000
                        else:
                            trade['tp_price'] = trade['entry_price'] - signal['tp_pips'] / 10000
                    
                    # Add to open trades
                    open_trades.append(trade)
            
            except Exception as e:
                logger.error(f"Error processing strategy signals: {str(e)}")
        
        # Close any remaining open trades at the last price
        last_price = data.iloc[-1]['close']
        for trade in open_trades[:]:
            if trade['type'] == 'buy':
                exit_profit_pips = (last_price - trade['entry_price']) * 10000
            else:  # sell
                exit_profit_pips = (trade['entry_price'] - last_price) * 10000
                
            exit_profit = exit_profit_pips * trade['pip_value'] * trade['volume']
            exit_profit -= 0.0  # Apply commission
            
            trade['exit_time'] = data.iloc[-1]['time']
            trade['exit_price'] = last_price
            trade['exit_reason'] = 'end_of_test'
            trade['profit_pips'] = exit_profit_pips
            trade['profit'] = exit_profit
            
            # Update performance metrics
            total_trades += 1
            total_pips += exit_profit_pips
            total_profit += exit_profit
            
            if exit_profit > 0:
                winning_trades += 1
                largest_win = max(largest_win, exit_profit)
            elif exit_profit < 0:
                losing_trades += 1
                largest_loss = min(largest_loss, exit_profit)
            else:
                break_even_trades += 1
            
            # Update balance
            current_balance += exit_profit
            
            # Move to closed trades
            closed_trades.append(trade)
        
        # Clear open trades
        open_trades = []
        
        # Calculate final equity
        current_equity = current_balance
        
        # Calculate performance metrics
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        profit_factor = abs(sum(t['profit'] for t in closed_trades if t['profit'] > 0)) / abs(sum(t['profit'] for t in closed_trades if t['profit'] < 0)) if sum(t['profit'] for t in closed_trades if t['profit'] < 0) != 0 else float('inf')
        average_win = sum(t['profit'] for t in closed_trades if t['profit'] > 0) / winning_trades if winning_trades > 0 else 0
        average_loss = sum(t['profit'] for t in closed_trades if t['profit'] < 0) / losing_trades if losing_trades > 0 else 0
        expectancy = (win_rate * average_win) - ((1 - win_rate) * abs(average_loss)) if total_trades > 0 else 0
        
        # Calculate Sharpe ratio
        equity_df = pd.DataFrame(equity_curve)
        equity_df['return'] = equity_df['equity'].pct_change().fillna(0)
        sharpe_ratio = (equity_df['return'].mean() / equity_df['return'].std()) * np.sqrt(252) if equity_df['return'].std() > 0 else 0
        
        # Calculate Sortino ratio
        negative_returns = equity_df['return'][equity_df['return'] < 0]
        sortino_ratio = (equity_df['return'].mean() / negative_returns.std()) * np.sqrt(252) if len(negative_returns) > 0 and negative_returns.std() > 0 else 0
        
        # Calculate CAR and MDD
        years = (end_date - start_date).days / 365.25
        car = ((current_equity / initial_balance) ** (1 / years) - 1) if years > 0 else 0
        mdd = max_drawdown_pct
        
        # Calculate Calmar ratio
        calmar_ratio = car / mdd if mdd > 0 else float('inf')
        
        # Prepare results
        result = {
            "strategy": strategy_name,
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "initial_balance": initial_balance,
            "final_balance": current_balance,
            "net_profit": current_balance - initial_balance,
            "profit_percentage": ((current_balance - initial_balance) / initial_balance) * 100,
            "max_drawdown": max_drawdown,
            "max_drawdown_percentage": max_drawdown_pct * 100,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "break_even_trades": break_even_trades,
            "win_rate": win_rate * 100,
            "profit_factor": profit_factor,
            "average_win": average_win,
            "average_loss": average_loss,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "total_pips": total_pips,
            "expectancy": expectancy,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "car": car * 100,  # Compound Annual Return in percentage
            "calmar_ratio": calmar_ratio,
            "equity_curve": equity_curve,
            "trades": closed_trades
        }
        
        return result

    def _apply_gap_edge_case(self, data: pd.DataFrame, edge_case_params: Dict) -> pd.DataFrame:
        """
        Apply a price gap edge case to data
        
        Args:
            data: DataFrame with price data
            edge_case_params: Edge case parameters
            
        Returns:
            Modified DataFrame with a price gap
        """
        gap_percentage = edge_case_params.get("gap_percentage", 2.0)
        gap_direction = edge_case_params.get("gap_direction", "down")
        
        # Create a copy to avoid modifying original data
        modified_data = data.copy()
        
        # Choose a random point in the first 70% of the data to insert the gap
        gap_index = random.randint(int(len(data) * 0.3), int(len(data) * 0.7))
        
        # Calculate gap size based on percentage and current price
        base_price = data.iloc[gap_index]['close']
        gap_size = base_price * (gap_percentage / 100)
        
        # Apply gap
        if gap_direction == "down":
            # For a gap down, adjust all prices from gap_index forward
            modifier = -gap_size
        else:
            # For a gap up, adjust all prices from gap_index forward
            modifier = gap_size
            
        # Apply the gap
        for i in range(gap_index, len(modified_data)):
            modified_data.at[modified_data.index[i], 'open'] += modifier
            modified_data.at[modified_data.index[i], 'high'] += modifier
            modified_data.at[modified_data.index[i], 'low'] += modifier
            modified_data.at[modified_data.index[i], 'close'] += modifier
            
        logger.debug(f"Applied {gap_direction} price gap of {gap_percentage}% at index {gap_index}")
        return modified_data
    
    def _apply_flash_crash_edge_case(self, data: pd.DataFrame, edge_case_params: Dict) -> pd.DataFrame:
        """
        Apply a flash crash edge case to data
        
        Args:
            data: DataFrame with price data
            edge_case_params: Edge case parameters
            
        Returns:
            Modified DataFrame with flash crash
        """
        crash_percentage = edge_case_params.get("crash_percentage", 5.0)
        recovery_percentage = edge_case_params.get("recovery_percentage", 3.0)
        
        # Create a copy to avoid modifying original data
        modified_data = data.copy()
        
        # Choose a point in the middle of the data to insert the flash crash
        crash_index = random.randint(int(len(data) * 0.4), int(len(data) * 0.6))
        
        # Calculate how many bars the crash and recovery should last
        # For flash crash, we'll use a small number of bars
        crash_duration = min(5, int(len(data) * 0.02))
        recovery_duration = min(8, int(len(data) * 0.03))
        
        # Find the base price before the crash
        base_price = data.iloc[crash_index]['close']
        
        # Calculate the crash size and recovery size
        crash_size = base_price * (crash_percentage / 100)
        recovery_size = base_price * (recovery_percentage / 100)
        
        # Apply the crash (steep decline over crash_duration)
        for i in range(crash_duration):
            if crash_index + i >= len(modified_data):
                break
                
            # Calculate this bar's portion of the crash (more at the beginning, less at the end)
            crash_portion = crash_size * (crash_duration - i) / crash_duration
            
            # Apply the drop to this bar
            idx = modified_data.index[crash_index + i]
            modified_data.at[idx, 'open'] = modified_data.at[idx, 'open'] if i == 0 else modified_data.at[modified_data.index[crash_index + i - 1], 'close']
            modified_data.at[idx, 'close'] = modified_data.at[idx, 'open'] - crash_portion
            modified_data.at[idx, 'high'] = max(modified_data.at[idx, 'open'], modified_data.at[idx, 'close'])
            modified_data.at[idx, 'low'] = min(modified_data.at[idx, 'open'], modified_data.at[idx, 'close']) - (crash_portion * 0.2)  # Extra spike down
        
        # Apply the recovery (gradual increase over recovery_duration)
        for i in range(recovery_duration):
            if crash_index + crash_duration + i >= len(modified_data):
                break
                
            # Calculate this bar's portion of the recovery (more at the beginning, less at the end)
            recovery_portion = recovery_size * (recovery_duration - i) / recovery_duration
            
            # Apply the recovery to this bar
            idx = modified_data.index[crash_index + crash_duration + i]
            modified_data.at[idx, 'open'] = modified_data.at[idx, 'open'] if i == 0 else modified_data.at[modified_data.index[crash_index + crash_duration + i - 1], 'close']
            modified_data.at[idx, 'close'] = modified_data.at[idx, 'open'] + recovery_portion
            modified_data.at[idx, 'high'] = max(modified_data.at[idx, 'open'], modified_data.at[idx, 'close']) + (recovery_portion * 0.2)  # Extra spike up
            modified_data.at[idx, 'low'] = min(modified_data.at[idx, 'open'], modified_data.at[idx, 'close'])
        
        logger.debug(f"Applied flash crash of {crash_percentage}% and recovery of {recovery_percentage}% at index {crash_index}")
        return modified_data
    
    def _apply_high_volatility_edge_case(self, data: pd.DataFrame, edge_case_params: Dict) -> pd.DataFrame:
        """
        Apply a high volatility edge case to data
        
        Args:
            data: DataFrame with price data
            edge_case_params: Edge case parameters
            
        Returns:
            Modified DataFrame with high volatility
        """
        volatility_multiplier = edge_case_params.get("volatility_multiplier", 3.0)
        
        if volatility_multiplier <= 1.0:
            return data
            
        # Create a copy to avoid modifying original data
        modified_data = data.copy()
        
        # Choose a segment of the data to apply high volatility
        start_index = random.randint(int(len(data) * 0.3), int(len(data) * 0.6))
        segment_length = min(20, int(len(data) * 0.1))
        end_index = min(start_index + segment_length, len(data) - 1)
        
        # Calculate the average range for the data
        avg_range = (data['high'] - data['low']).mean()
        
        # Apply high volatility to the segment
        for i in range(start_index, end_index + 1):
            # Get the base values
            open_price = modified_data.iloc[i]['open']
            close_price = modified_data.iloc[i]['close']
            
            # Calculate the original range
            orig_range = modified_data.iloc[i]['high'] - modified_data.iloc[i]['low']
            
            # Calculate the new range based on the volatility multiplier
            new_range = orig_range * volatility_multiplier
            
            # Calculate the midpoint of open and close
            midpoint = (open_price + close_price) / 2
            
            # Set new high and low based on increased volatility
            new_high = midpoint + (new_range / 2)
            new_low = midpoint - (new_range / 2)
            
            # Update the values
            modified_data.at[modified_data.index[i], 'high'] = new_high
            modified_data.at[modified_data.index[i], 'low'] = new_low
            
        logger.debug(f"Applied high volatility with multiplier {volatility_multiplier} from index {start_index} to {end_index}")
        return modified_data
        
    def generate_edge_case_report(self, result_key: str, output_dir: str = "reports") -> str:
        """
        Generate an HTML report for an edge case test
        
        Args:
            result_key: Key of the edge case test result
            output_dir: Directory to save the report
            
        Returns:
            Path to the generated report
        """
        if result_key not in self.edge_case_results:
            logger.error(f"Edge case test result with key {result_key} not found")
            return ""
            
        edge_case_result = self.edge_case_results[result_key]
        
        # Ensure output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Create filename
        filename = f"edge_case_{edge_case_result['symbol']}_{edge_case_result['timeframe']}_{edge_case_result['strategy_name']}_{edge_case_result['edge_case_type']}.html"
        filepath = os.path.join(output_dir, filename)
        
        # Generate HTML content
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Edge Case Test Report: {strategy} - {symbol} - {edge_case_type}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .metric {{ margin-bottom: 10px; }}
                .metric span {{ font-weight: bold; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                .chart {{ width: 100%; height: 400px; margin-top: 20px; }}
            </style>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <h1>Edge Case Test Report</h1>
            
            <div class="summary">
                <h2>Test Summary</h2>
                <div class="metric"><span>Strategy:</span> {strategy}</div>
                <div class="metric"><span>Symbol:</span> {symbol}</div>
                <div class="metric"><span>Timeframe:</span> {timeframe}</div>
                <div class="metric"><span>Edge Case Type:</span> {edge_case_type}</div>
                <div class="metric"><span>Edge Case Parameters:</span> {edge_case_params}</div>
                <div class="metric"><span>Test Period:</span> {start_date} to {end_date}</div>
                <div class="metric"><span>Generated:</span> {timestamp}</div>
            </div>
            
            <h2>Performance Summary</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Initial Balance</td>
                    <td>{initial_balance:.2f}</td>
                </tr>
                <tr>
                    <td>Final Balance</td>
                    <td>{final_balance:.2f}</td>
                </tr>
                <tr>
                    <td>Net Profit</td>
                    <td class="{profit_class}">{net_profit:.2f} ({profit_percentage:.2f}%)</td>
                </tr>
                <tr>
                    <td>Max Drawdown</td>
                    <td class="negative">{max_drawdown:.2f} ({max_drawdown_percentage:.2f}%)</td>
                </tr>
                <tr>
                    <td>Total Trades</td>
                    <td>{total_trades}</td>
                </tr>
                <tr>
                    <td>Win Rate</td>
                    <td>{win_rate:.2f}%</td>
                </tr>
                <tr>
                    <td>Profit Factor</td>
                    <td>{profit_factor:.2f}</td>
                </tr>
                <tr>
                    <td>Expectancy</td>
                    <td>{expectancy:.2f}</td>
                </tr>
                <tr>
                    <td>Sharpe Ratio</td>
                    <td>{sharpe_ratio:.2f}</td>
                </tr>
                <tr>
                    <td>CAR</td>
                    <td>{car:.2f}%</td>
                </tr>
                <tr>
                    <td>Calmar Ratio</td>
                    <td>{calmar_ratio:.2f}</td>
                </tr>
            </table>
            
            <div id="equity-chart" class="chart"></div>
            
            <script>
                // Equity curve data
                var equityData = {equity_data};
                
                // Create traces
                var equityTrace = {{
                    x: equityData.map(item => item.time),
                    y: equityData.map(item => item.equity),
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Equity'
                }};
                
                var balanceTrace = {{
                    x: equityData.map(item => item.time),
                    y: equityData.map(item => item.balance),
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Balance'
                }};
                
                var drawdownTrace = {{
                    x: equityData.map(item => item.time),
                    y: equityData.map(item => -item.drawdown_pct * 100),
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Drawdown %',
                    yaxis: 'y2'
                }};
                
                var data = [equityTrace, balanceTrace, drawdownTrace];
                
                var layout = {{
                    title: 'Equity Curve and Drawdown',
                    yaxis: {{
                        title: 'Equity/Balance'
                    }},
                    yaxis2: {{
                        title: 'Drawdown %',
                        overlaying: 'y',
                        side: 'right',
                        showgrid: false,
                        zeroline: false
                    }},
                    legend: {{
                        x: 0,
                        y: 1
                    }}
                }};
                
                Plotly.newPlot('equity-chart', data, layout);
            </script>
        </body>
        </html>
        """
        
        # Get result data
        result = edge_case_result.get("result", {})
        
        # Format data for template
        profit_class = "positive" if result.get("net_profit", 0) >= 0 else "negative"
        edge_case_params_str = ", ".join([f"{k}: {v}" for k, v in edge_case_result.get("edge_case_params", {}).items() if k != "test_period"])
        
        # Convert equity data to JSON for JavaScript
        equity_data = json.dumps(result.get("equity_curve", []))
        
        # Fill template
        html_content = template.format(
            strategy=edge_case_result.get("strategy_name", ""),
            symbol=edge_case_result.get("symbol", ""),
            timeframe=edge_case_result.get("timeframe", ""),
            edge_case_type=edge_case_result.get("edge_case_type", ""),
            edge_case_params=edge_case_params_str,
            start_date=edge_case_result.get("start_date", ""),
            end_date=edge_case_result.get("end_date", ""),
            timestamp=edge_case_result.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            initial_balance=result.get("initial_balance", 0),
            final_balance=result.get("final_balance", 0),
            net_profit=result.get("net_profit", 0),
            profit_percentage=result.get("profit_percentage", 0),
            max_drawdown=result.get("max_drawdown", 0),
            max_drawdown_percentage=result.get("max_drawdown_percentage", 0),
            total_trades=result.get("total_trades", 0),
            win_rate=result.get("win_rate", 0),
            profit_factor=result.get("profit_factor", 0),
            average_win=result.get("average_win", 0),
            average_loss=result.get("average_loss", 0),
            largest_win=result.get("largest_win", 0),
            largest_loss=result.get("largest_loss", 0),
            total_pips=result.get("total_pips", 0),
            expectancy=result.get("expectancy", 0),
            sharpe_ratio=result.get("sharpe_ratio", 0),
            sortino_ratio=result.get("sortino_ratio", 0),
            car=result.get("car", 0),
            calmar_ratio=result.get("calmar_ratio", 0),
            profit_class=profit_class,
            equity_data=equity_data
        )
        
        # Write to file
        with open(filepath, "w") as f:
            f.write(html_content)
            
        logger.info(f"Edge case report generated at {filepath}")
        return filepath

class AdvancedBacktester(MT5Backtester):
    """
    Advanced backtesting class that extends MT5Backtester with additional features:
    
    - Multi-strategy testing and comparison
    - Performance benchmarks (buy-and-hold, random)
    - Stress testing
    - Edge case testing
    - Statistical analysis
    """
    
    def __init__(self, strategies: Dict[str, BaseStrategy], data_feed: MT5DataFeed, config: Dict = None):
        """
        Initialize AdvancedBacktester
        
        Args:
            strategies: Dictionary of strategy instances keyed by name
            data_feed: MT5DataFeed instance to fetch data
            config: Optional configuration dictionary
        """
        super().__init__(strategies, data_feed, config)
        
        # Initialize storage for advanced testing results
        self.multi_strategy_results = {}
        self.benchmark_results = {}
        self.stress_test_results = {}
        self.edge_case_results = {}
        
        # Default configurations
        self.benchmark_config = {
            "buy_and_hold": {
                "enabled": True
            },
            "random": {
                "enabled": True,
                "win_rate": 0.5,
                "risk_reward": 1.0
            }
        }
        
        self.stress_test_config = {
            "volatility": {
                "enabled": True,
                "levels": ["low", "medium", "high"]
            },
            "slippage": {
                "enabled": True,
                "levels": ["low", "medium", "high"]
            },
            "spread": {
                "enabled": True,
                "levels": ["low", "medium", "high"]
            }
        }
        
        self.edge_case_config = {
            "gap": {
                "enabled": True,
                "directions": ["up", "down"]
            },
            "flash_crash": {
                "enabled": True
            },
            "high_volatility": {
                "enabled": True
            }
        }
        
        # Update configuration if provided
        if config:
            self._update_advanced_config(config)
    
    def _update_advanced_config(self, config: Dict):
        """
        Update advanced configuration
        
        Args:
            config: Configuration dictionary
        """
        if "benchmark" in config:
            self.benchmark_config.update(config["benchmark"])
            
        if "stress_test" in config:
            self.stress_test_config.update(config["stress_test"])
            
        if "edge_case" in config:
            self.edge_case_config.update(config["edge_case"])
    
    def compare_strategies(self, 
                         symbol: str, 
                         timeframe: str, 
                         strategy_names: List[str], 
                         start_date: datetime, 
                         end_date: datetime,
                         initial_balance: float = 10000,
                         include_benchmarks: bool = True) -> Dict:
        """
        Compare multiple strategies on the same market data
        
        Args:
            symbol: Symbol to backtest on
            timeframe: Timeframe to use
            strategy_names: List of strategy names to compare
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_balance: Initial account balance
            include_benchmarks: Whether to include benchmark strategies
            
        Returns:
            Dictionary with comparison results
        """
        logger.info(f"Comparing strategies: {strategy_names}")
        
        # Validate strategies
        valid_strategies = []
        for strategy_name in strategy_names:
            if strategy_name in self.strategies:
                valid_strategies.append(strategy_name)
            else:
                logger.warning(f"Strategy {strategy_name} not found and will be skipped")
                
        if not valid_strategies:
            logger.error("No valid strategies to compare")
            return {}
        
        # Create a unique key for this comparison
        key = f"compare_{symbol}_{timeframe}_{'_'.join(valid_strategies)}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        
        # Run backtest for each strategy
        results = {}
        for strategy_name in valid_strategies:
            logger.info(f"Running backtest for {strategy_name}")
            
            result = self.run_backtest(
                symbol=symbol,
                timeframe=timeframe,
                strategy_name=strategy_name,
                start_date=start_date,
                end_date=end_date,
                initial_balance=initial_balance
            )
            
            results[strategy_name] = result
        
        # Add benchmarks if requested
        benchmarks = {}
        if include_benchmarks:
            # Buy and hold benchmark
            if self.benchmark_config["buy_and_hold"]["enabled"]:
                bh_result = self.run_buy_and_hold_benchmark(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    initial_balance=initial_balance
                )
                benchmarks["buy_and_hold"] = bh_result
            
            # Random benchmark
            if self.benchmark_config["random"]["enabled"]:
                rnd_result = self.run_random_benchmark(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    initial_balance=initial_balance,
                    win_rate=self.benchmark_config["random"]["win_rate"],
                    risk_reward=self.benchmark_config["random"]["risk_reward"]
                )
                benchmarks["random"] = rnd_result
        
        # Compare results
        # Create a ranking of strategies based on key metrics
        metrics = [
            {"name": "net_profit", "higher_better": True, "weight": 1.0},
            {"name": "max_drawdown_percentage", "higher_better": False, "weight": 0.8},
            {"name": "win_rate", "higher_better": True, "weight": 0.7},
            {"name": "profit_factor", "higher_better": True, "weight": 0.8},
            {"name": "expectancy", "higher_better": True, "weight": 0.9},
            {"name": "sharpe_ratio", "higher_better": True, "weight": 0.9},
            {"name": "calmar_ratio", "higher_better": True, "weight": 0.8}
        ]
        
        # Calculate scores
        strategy_scores = {}
        
        # Combine all results for ranking
        all_results = {**results}
        if include_benchmarks:
            all_results.update({f"benchmark_{k}": v for k, v in benchmarks.items()})
        
        # Calculate normalized scores for each metric
        for metric in metrics:
            metric_name = metric["name"]
            metric_values = [result.get(metric_name, 0) for result in all_results.values() if metric_name in result]
            
            if not metric_values:
                continue
                
            min_val = min(metric_values)
            max_val = max(metric_values)
            
            # Skip if min and max are the same
            if min_val == max_val:
                continue
                
            # Calculate normalized scores (0-1 range)
            for strategy_name, result in all_results.items():
                if metric_name not in result:
                    continue
                    
                value = result[metric_name]
                
                # Normalize the value between 0 and 1
                if metric["higher_better"]:
                    normalized_score = (value - min_val) / (max_val - min_val)
                else:
                    normalized_score = (max_val - value) / (max_val - min_val)
                
                # Initialize score for this strategy if needed
                if strategy_name not in strategy_scores:
                    strategy_scores[strategy_name] = 0
                
                # Add weighted score
                strategy_scores[strategy_name] += normalized_score * metric["weight"]
        
        # Normalize final scores to percentages
        max_score = sum(metric["weight"] for metric in metrics)
        for strategy_name in strategy_scores:
            strategy_scores[strategy_name] = (strategy_scores[strategy_name] / max_score) * 100
        
        # Rank strategies
        ranked_strategies = sorted(strategy_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Prepare comparison result
        comparison = {
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "strategies": {name: results[name] for name in valid_strategies},
            "benchmarks": benchmarks if include_benchmarks else {},
            "scores": {name: score for name, score in strategy_scores.items()},
            "ranking": [{"strategy": name, "score": score} for name, score in ranked_strategies],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Store result
        self.multi_strategy_results[key] = comparison
        
        logger.info(f"Strategy comparison completed with key: {key}")
        return comparison
    
    def run_comprehensive_test(self,
                             symbol: str,
                             timeframe: str,
                             strategy_names: List[str],
                             start_date: datetime,
                             end_date: datetime,
                             initial_balance: float = 10000,
                             include_benchmarks: bool = True,
                             include_stress_tests: bool = True,
                             include_edge_cases: bool = True,
                             output_dir: str = "reports") -> Dict:
        """
        Run a comprehensive test suite on multiple strategies
        
        Args:
            symbol: Symbol to test on
            timeframe: Timeframe to use
            strategy_names: List of strategy names to test
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_balance: Initial account balance
            include_benchmarks: Whether to include benchmark strategies
            include_stress_tests: Whether to include stress tests
            include_edge_cases: Whether to include edge case tests
            output_dir: Directory to save reports
            
        Returns:
            Dictionary with comprehensive test results
        """
        logger.info(f"Running comprehensive test for strategies: {strategy_names}")
        
        # Create report directory
        test_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = os.path.join(output_dir, f"comprehensive_test_{test_id}")
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
            
        # Initialize result container
        results = {
            "test_id": test_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "strategy_names": strategy_names,
            "backtest_results": {},
            "comparison_result": None,
            "stress_test_results": {},
            "edge_case_results": {},
            "report_dir": report_dir,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Run basic backtests for each strategy
        for strategy_name in strategy_names:
            if strategy_name not in self.strategies:
                logger.warning(f"Strategy {strategy_name} not found and will be skipped")
                continue
                
            logger.info(f"Running backtest for {strategy_name}")
            
            result = self.run_backtest(
                symbol=symbol,
                timeframe=timeframe,
                strategy_name=strategy_name,
                start_date=start_date,
                end_date=end_date,
                initial_balance=initial_balance
            )
            
            results["backtest_results"][strategy_name] = result
            
            # Generate report
            report_path = self.generate_report(
                result_key=f"{symbol}_{timeframe}_{strategy_name}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}",
                output_dir=report_dir
            )
            
            results["backtest_results"][strategy_name]["report_path"] = report_path
            
        # Run strategy comparison
        if len(strategy_names) > 1:
            logger.info("Running strategy comparison")
            
            comparison = self.compare_strategies(
                symbol=symbol,
                timeframe=timeframe,
                strategy_names=strategy_names,
                start_date=start_date,
                end_date=end_date,
                initial_balance=initial_balance,
                include_benchmarks=include_benchmarks
            )
            
            results["comparison_result"] = comparison
            
            # Generate comparison report
            # TODO: Implement comparison report generation
        
        # Run stress tests
        if include_stress_tests:
            logger.info("Running stress tests")
            
            for strategy_name in strategy_names:
                if strategy_name not in self.strategies:
                    continue
                    
                results["stress_test_results"][strategy_name] = {}
                
                # Run volatility stress tests
                if self.stress_test_config["volatility"]["enabled"]:
                    for level in self.stress_test_config["volatility"]["levels"]:
                        stress_result = self.run_stress_test(
                            symbol=symbol,
                            timeframe=timeframe,
                            strategy_name=strategy_name,
                            start_date=start_date,
                            end_date=end_date,
                            stress_type="volatility",
                            stress_level=level,
                            initial_balance=initial_balance
                        )
                        
                        results["stress_test_results"][strategy_name][f"volatility_{level}"] = stress_result
                
                # Run slippage stress tests
                if self.stress_test_config["slippage"]["enabled"]:
                    for level in self.stress_test_config["slippage"]["levels"]:
                        stress_result = self.run_stress_test(
                            symbol=symbol,
                            timeframe=timeframe,
                            strategy_name=strategy_name,
                            start_date=start_date,
                            end_date=end_date,
                            stress_type="slippage",
                            stress_level=level,
                            initial_balance=initial_balance
                        )
                        
                        results["stress_test_results"][strategy_name][f"slippage_{level}"] = stress_result
                
                # Run spread stress tests
                if self.stress_test_config["spread"]["enabled"]:
                    for level in self.stress_test_config["spread"]["levels"]:
                        stress_result = self.run_stress_test(
                            symbol=symbol,
                            timeframe=timeframe,
                            strategy_name=strategy_name,
                            start_date=start_date,
                            end_date=end_date,
                            stress_type="spread",
                            stress_level=level,
                            initial_balance=initial_balance
                        )
                        
                        results["stress_test_results"][strategy_name][f"spread_{level}"] = stress_result
        
        # Run edge case tests
        if include_edge_cases:
            logger.info("Running edge case tests")
            
            for strategy_name in strategy_names:
                if strategy_name not in self.strategies:
                    continue
                    
                results["edge_case_results"][strategy_name] = {}
                
                # Run gap tests
                if self.edge_case_config["gap"]["enabled"]:
                    for direction in self.edge_case_config["gap"]["directions"]:
                        edge_case_result = self.run_edge_case_test(
                            symbol=symbol,
                            timeframe=timeframe,
                            strategy_name=strategy_name,
                            edge_case_type="gap",
                            edge_case_params={"gap_direction": direction},
                            initial_balance=initial_balance
                        )
                        
                        results["edge_case_results"][strategy_name][f"gap_{direction}"] = edge_case_result
                
                # Run flash crash test
                if self.edge_case_config["flash_crash"]["enabled"]:
                    edge_case_result = self.run_edge_case_test(
                        symbol=symbol,
                        timeframe=timeframe,
                        strategy_name=strategy_name,
                        edge_case_type="flash_crash",
                        initial_balance=initial_balance
                    )
                    
                    results["edge_case_results"][strategy_name]["flash_crash"] = edge_case_result
                
                # Run high volatility test
                if self.edge_case_config["high_volatility"]["enabled"]:
                    edge_case_result = self.run_edge_case_test(
                        symbol=symbol,
                        timeframe=timeframe,
                        strategy_name=strategy_name,
                        edge_case_type="high_volatility",
                        initial_balance=initial_balance
                    )
                    
                    results["edge_case_results"][strategy_name]["high_volatility"] = edge_case_result
        
        # Generate comprehensive summary report
        summary_path = self._generate_comprehensive_report(results, report_dir)
        results["summary_report_path"] = summary_path
        
        logger.info(f"Comprehensive test completed, reports saved to {report_dir}")
        return results
    
    def _generate_comprehensive_report(self, results: Dict, output_dir: str) -> str:
        """
        Generate a comprehensive HTML report for all test results
        
        Args:
            results: Comprehensive test results
            output_dir: Directory to save the report
            
        Returns:
            Path to the generated report
        """
        # Create filename
        filename = f"comprehensive_report_{results['test_id']}.html"
        filepath = os.path.join(output_dir, filename)
        
        # Generate HTML content
        # This would be a complex HTML template with sections for each test type
        # and visualizations comparing results
        # For brevity, implementing a minimal version here
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Comprehensive Test Report - {results['symbol']} - {results['timeframe']}</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .metric {{ margin-bottom: 10px; }}
                .metric span {{ font-weight: bold; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                .chart {{ width: 100%; height: 400px; margin-top: 20px; }}
                .section {{ margin-bottom: 30px; }}
            </style>
        </head>
        <body>
            <h1>Comprehensive Trading Strategy Test Report</h1>
            
            <div class="summary">
                <h2>Test Summary</h2>
                <div class="metric"><span>Symbol:</span> {results['symbol']}</div>
                <div class="metric"><span>Timeframe:</span> {results['timeframe']}</div>
                <div class="metric"><span>Test Period:</span> {results['start_date']} to {results['end_date']}</div>
                <div class="metric"><span>Strategies Tested:</span> {', '.join(results['strategy_names'])}</div>
                <div class="metric"><span>Test ID:</span> {results['test_id']}</div>
                <div class="metric"><span>Generated:</span> {results['timestamp']}</div>
            </div>
            
            <div class="section">
                <h2>Backtest Results</h2>
                <table>
                    <tr>
                        <th>Strategy</th>
                        <th>Net Profit</th>
                        <th>Win Rate</th>
                        <th>Sharpe Ratio</th>
                        <th>Max Drawdown</th>
                        <th>Report</th>
                    </tr>
        """
        
        # Add rows for each strategy
        for strategy_name, result in results['backtest_results'].items():
            profit_class = "positive" if result.get("net_profit", 0) >= 0 else "negative"
            report_link = os.path.basename(result.get("report_path", ""))
            
            html_content += f"""
                    <tr>
                        <td>{strategy_name}</td>
                        <td class="{profit_class}">{result.get('net_profit', 0):.2f}</td>
                        <td>{result.get('win_rate', 0):.2f}%</td>
                        <td>{result.get('sharpe_ratio', 0):.2f}</td>
                        <td class="negative">{result.get('max_drawdown_percentage', 0):.2f}%</td>
                        <td><a href="{report_link}">View Report</a></td>
                    </tr>
            """
        
        html_content += """
                </table>
            </div>
        """
        
        # Add strategy comparison section if available
        if results.get("comparison_result"):
            html_content += """
            <div class="section">
                <h2>Strategy Comparison</h2>
                <table>
                    <tr>
                        <th>Rank</th>
                        <th>Strategy</th>
                        <th>Score</th>
                    </tr>
            """
            
            for i, ranking in enumerate(results["comparison_result"].get("ranking", []), 1):
                html_content += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{ranking['strategy']}</td>
                        <td>{ranking['score']:.2f}%</td>
                    </tr>
                """
            
            html_content += """
                </table>
            </div>
            """
        
        # Add stress test summary
        if results.get("stress_test_results"):
            html_content += """
            <div class="section">
                <h2>Stress Test Summary</h2>
                <table>
                    <tr>
                        <th>Strategy</th>
                        <th>Test Type</th>
                        <th>Stress Resistance</th>
                        <th>Impact on Profit</th>
                        <th>Impact on Drawdown</th>
                    </tr>
            """
            
            for strategy_name, stress_tests in results["stress_test_results"].items():
                for test_name, test_result in stress_tests.items():
                    comparison = test_result.get("comparison", {})
                    metrics = comparison.get("metrics", {})
                    
                    profit_impact = metrics.get("net_profit", {}).get("percentage_change", 0)
                    profit_class = "positive" if profit_impact >= 0 else "negative"
                    
                    drawdown_impact = metrics.get("max_drawdown_percentage", {}).get("percentage_change", 0)
                    drawdown_class = "positive" if drawdown_impact <= 0 else "negative"
                    
                    html_content += f"""
                    <tr>
                        <td>{strategy_name}</td>
                        <td>{test_name}</td>
                        <td>{comparison.get("stress_resistance", 0):.2f}%</td>
                        <td class="{profit_class}">{profit_impact:.2f}%</td>
                        <td class="{drawdown_class}">{drawdown_impact:.2f}%</td>
                    </tr>
                    """
            
            html_content += """
                </table>
            </div>
            """
        
        # Add edge case summary
        if results.get("edge_case_results"):
            html_content += """
            <div class="section">
                <h2>Edge Case Test Summary</h2>
                <table>
                    <tr>
                        <th>Strategy</th>
                        <th>Edge Case</th>
                        <th>Net Profit</th>
                        <th>Win Rate</th>
                        <th>Max Drawdown</th>
                    </tr>
            """
            
            for strategy_name, edge_cases in results["edge_case_results"].items():
                for case_name, case_result in edge_cases.items():
                    result = case_result.get("result", {})
                    
                    profit_class = "positive" if result.get("net_profit", 0) >= 0 else "negative"
                    
                    html_content += f"""
                    <tr>
                        <td>{strategy_name}</td>
                        <td>{case_name}</td>
                        <td class="{profit_class}">{result.get('net_profit', 0):.2f} ({result.get('profit_percentage', 0):.2f}%)</td>
                        <td>{result.get('win_rate', 0):.2f}%</td>
                        <td class="negative">{result.get('max_drawdown_percentage', 0):.2f}%</td>
                    </tr>
                    """
            
            html_content += """
                </table>
            </div>
            """
        
        # Close HTML
        html_content += """
        </body>
        </html>
        """
        
        # Write to file
        with open(filepath, "w") as f:
            f.write(html_content)
            
        logger.info(f"Comprehensive report generated at {filepath}")
        return filepath

    def run_statistical_analysis(self, 
                               result_key: str, 
                               monte_carlo_iterations: int = 1000,
                               confidence_level: float = 0.95) -> Dict:
        """
        Run statistical analysis on backtest results
        
        Args:
            result_key: Key to the backtest result to analyze
            monte_carlo_iterations: Number of Monte Carlo simulations to run
            confidence_level: Confidence level for statistics (0-1)
            
        Returns:
            Dictionary with statistical analysis results
        """
        logger.info(f"Running statistical analysis on result: {result_key}")
        
        # Get the backtest result
        if result_key not in self.results:
            logger.error(f"Backtest result with key {result_key} not found")
            return {}
        
        result = self.results[result_key]
        trades = result.get("trades", [])
        
        if not trades:
            logger.error("No trades found in the backtest result")
            return {}
        
        # Extract trade returns
        returns = [trade["profit"] for trade in trades]
        
        # Basic statistics
        total_trades = len(returns)
        winning_trades = sum(1 for r in returns if r > 0)
        losing_trades = sum(1 for r in returns if r <= 0)
        
        win_rate = (winning_trades / total_trades) if total_trades > 0 else 0
        
        # Calculate standard metrics
        mean_return = np.mean(returns) if returns else 0
        median_return = np.median(returns) if returns else 0
        std_return = np.std(returns) if returns else 0
        skew = scipy.stats.skew(returns) if len(returns) > 2 else 0
        kurtosis = scipy.stats.kurtosis(returns) if len(returns) > 2 else 0
        
        # Calculate percentiles
        percentiles = {}
        for percentile in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
            percentiles[str(percentile)] = np.percentile(returns, percentile)
        
        # Run Monte Carlo simulation
        mc_results = self._run_monte_carlo_simulation(
            returns=returns,
            initial_balance=result.get("initial_balance", 10000),
            iterations=monte_carlo_iterations,
            confidence_level=confidence_level
        )
        
        # Prepare analysis results
        analysis = {
            "basic_stats": {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate * 100,
                "mean_return": mean_return,
                "median_return": median_return,
                "std_return": std_return,
                "skew": skew,
                "kurtosis": kurtosis,
                "sharpe_ratio": result.get("sharpe_ratio", 0),
                "profit_factor": result.get("profit_factor", 0),
                "max_drawdown_percentage": result.get("max_drawdown_percentage", 0)
            },
            "percentiles": percentiles,
            "monte_carlo": mc_results,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Calculate advanced metrics
        analysis["advanced_metrics"] = self._calculate_advanced_metrics(returns, result)
        
        # Store analysis results
        key = f"analysis_{result_key}"
        self.results[key] = analysis
        
        logger.info(f"Statistical analysis completed for {result_key}")
        return analysis

    def _run_monte_carlo_simulation(self, 
                                  returns: List[float], 
                                  initial_balance: float = 10000,
                                  iterations: int = 1000,
                                  confidence_level: float = 0.95) -> Dict:
        """
        Run Monte Carlo simulation on trade returns
        
        Args:
            returns: List of trade returns
            initial_balance: Initial account balance
            iterations: Number of iterations to run
            confidence_level: Confidence level for statistics (0-1)
            
        Returns:
            Dictionary with Monte Carlo simulation results
        """
        logger.info(f"Running Monte Carlo simulation with {iterations} iterations")
        
        # If not enough trades, return empty results
        if len(returns) < 10:
            logger.warning("Not enough trades for Monte Carlo simulation")
            return {}
        
        # Generate simulation paths
        equity_curves = []
        final_equities = []
        max_drawdowns = []
        
        # Calculate what percentiles to use based on confidence level
        lower_percentile = ((1 - confidence_level) / 2) * 100
        upper_percentile = 100 - lower_percentile
        
        for _ in range(iterations):
            # Randomly sample returns with replacement
            sampled_returns = np.random.choice(returns, size=len(returns), replace=True)
            
            # Generate equity curve
            equity = [initial_balance]
            for ret in sampled_returns:
                equity.append(equity[-1] + ret)
            
            equity_curves.append(equity)
            final_equities.append(equity[-1])
            
            # Calculate maximum drawdown
            peak = initial_balance
            max_dd = 0
            
            for eq in equity:
                if eq > peak:
                    peak = eq
                
                dd = (peak - eq) / peak * 100 if peak > 0 else 0
                max_dd = max(max_dd, dd)
            
            max_drawdowns.append(max_dd)
        
        # Calculate statistics
        mean_final_equity = np.mean(final_equities)
        median_final_equity = np.median(final_equities)
        std_final_equity = np.std(final_equities)
        
        mean_max_drawdown = np.mean(max_drawdowns)
        median_max_drawdown = np.median(max_drawdowns)
        worst_max_drawdown = np.max(max_drawdowns)
        
        # Calculate percentiles
        final_equity_percentiles = {}
        for percentile in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
            final_equity_percentiles[str(percentile)] = np.percentile(final_equities, percentile)
        
        # Calculate confidence interval
        lower_bound = np.percentile(final_equities, lower_percentile)
        upper_bound = np.percentile(final_equities, upper_percentile)
        
        # Prepare Monte Carlo results
        mc_results = {
            "iterations": iterations,
            "confidence_level": confidence_level * 100,
            "mean_final_equity": mean_final_equity,
            "median_final_equity": median_final_equity,
            "std_final_equity": std_final_equity,
            "confidence_interval": {
                "lower": lower_bound,
                "upper": upper_bound
            },
            "final_equity_percentiles": final_equity_percentiles,
            "drawdown_stats": {
                "mean_max_drawdown": mean_max_drawdown,
                "median_max_drawdown": median_max_drawdown,
                "worst_max_drawdown": worst_max_drawdown
            },
            # Store a subset of equity curves for visualization
            "sample_equity_curves": [curve for curve in equity_curves[:10]]
        }
        
        return mc_results

    def _calculate_advanced_metrics(self, returns: List[float], result: Dict) -> Dict:
        """
        Calculate advanced performance metrics
        
        Args:
            returns: List of trade returns
            result: Backtest result dictionary
            
        Returns:
            Dictionary with advanced metrics
        """
        # Calculate trade statistics
        if not returns:
            return {}
            
        # Convert to numpy array for calculations
        returns_array = np.array(returns)
        
        # Get winning and losing trades
        winning_returns = returns_array[returns_array > 0]
        losing_returns = returns_array[returns_array <= 0]
        
        # Average win and loss
        avg_win = np.mean(winning_returns) if winning_returns.size > 0 else 0
        avg_loss = np.mean(losing_returns) if losing_returns.size > 0 else 0
        
        # Kelly Criterion
        win_probability = winning_returns.size / returns_array.size if returns_array.size > 0 else 0
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        kelly_percentage = (win_probability * win_loss_ratio - (1 - win_probability)) / win_loss_ratio if win_loss_ratio != float('inf') else win_probability
        
        # Calculate risk-adjusted metrics
        risk_free_rate = 0.02  # Assuming 2%
        
        # Extract equity curve
        equity_curve = result.get("equity_curve", [])
        
        # Initialize performance metrics
        total_return = annualized_return = 0
        sharpe_ratio = sortino_ratio = calmar_ratio = r_squared = 0
        
        # Convert equity curve to returns if we have enough data
        if len(equity_curve) > 1:
            equity_returns = np.diff(equity_curve) / equity_curve[:-1]
            
            # Annualized return (assuming 252 trading days per year)
            trading_days_per_year = 252
            
            # Get dates from result
            start_date = result.get("start_date", "")
            end_date = result.get("end_date", "")
            
            # Convert string dates to datetime if needed
            if isinstance(start_date, str) and start_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            if isinstance(end_date, str) and end_date:
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
            
            # Calculate annualized metrics if we have valid dates
            if start_date and end_date and isinstance(start_date, datetime) and isinstance(end_date, datetime):
                days_in_backtest = (end_date - start_date).days
                
                if days_in_backtest > 0:
                    # Calculate total return
                    total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
                    
                    # Calculate annualized return
                    annualized_return = (1 + total_return) ** (trading_days_per_year / days_in_backtest) - 1
                    
                    # Calculate volatility
                    daily_volatility = np.std(equity_returns)
                    annualized_volatility = daily_volatility * np.sqrt(trading_days_per_year)
                    
                    # Calculate Sharpe Ratio
                    if annualized_volatility > 0:
                        sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility
                    
                    # Calculate Sortino Ratio
                    negative_returns = equity_returns[equity_returns < 0]
                    if negative_returns.size > 0:
                        downside_deviation = np.std(negative_returns) * np.sqrt(trading_days_per_year)
                        if downside_deviation > 0:
                            sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation
                    
                    # Calculate Calmar Ratio
                    max_drawdown = result.get("max_drawdown_percentage", 0)
                    if max_drawdown > 0:
                        calmar_ratio = annualized_return / (max_drawdown / 100)
                    
                    # Calculate R-Squared
                    if len(equity_curve) > 2:
                        x = np.arange(len(equity_curve))
                        slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(x, equity_curve)
                        r_squared = r_value ** 2
        
        # Create advanced metrics dictionary
        advanced_metrics = {
            "trade_metrics": {
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "win_loss_ratio": win_loss_ratio if win_loss_ratio != float('inf') else 9999,
                "expectancy": avg_win * win_probability + avg_loss * (1 - win_probability)
            },
            "risk_metrics": {
                "kelly_percentage": kelly_percentage * 100,
                "optimal_f": kelly_percentage / 2 * 100  # Half Kelly is considered safer
            },
            "performance_metrics": {
                "total_return": total_return * 100,
                "annualized_return": annualized_return * 100,
                "sharpe_ratio": sharpe_ratio,
                "sortino_ratio": sortino_ratio,
                "calmar_ratio": calmar_ratio,
                "r_squared": r_squared
            }
        }
        
        return advanced_metrics

    def generate_statistical_report(self, analysis_key: str, output_dir: str = "reports") -> str:
        """
        Generate an HTML report for statistical analysis results
        
        Args:
            analysis_key: Key to the analysis result
            output_dir: Directory to save the report
            
        Returns:
            Path to the generated report
        """
        # Extract the backtest key from the analysis key
        backtest_key = analysis_key.replace("analysis_", "")
        
        if backtest_key not in self.results:
            logger.error(f"Backtest result with key {backtest_key} not found")
            return ""
            
        if analysis_key not in self.results:
            logger.error(f"Analysis result with key {analysis_key} not found")
            return ""
        
        # Get the data
        backtest_result = self.results[backtest_key]
        analysis_result = self.results[analysis_key]
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Create filename
        filename = f"statistical_analysis_{backtest_key}.html"
        filepath = os.path.join(output_dir, filename)
        
        # Generate HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Statistical Analysis - {backtest_result['symbol']} - {backtest_result['strategy']}</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .metric {{ margin-bottom: 10px; }}
                .metric span {{ font-weight: bold; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                .chart {{ width: 100%; height: 400px; margin-top: 20px; }}
                .section {{ margin-bottom: 30px; }}
            </style>
        </head>
        <body>
            <h1>Statistical Analysis Report</h1>
            
            <div class="summary">
                <h2>Backtest Summary</h2>
                <div class="metric"><span>Symbol:</span> {backtest_result['symbol']}</div>
                <div class="metric"><span>Timeframe:</span> {backtest_result['timeframe']}</div>
                <div class="metric"><span>Strategy:</span> {backtest_result['strategy']}</div>
                <div class="metric"><span>Test Period:</span> {backtest_result['start_date']} to {backtest_result['end_date']}</div>
                <div class="metric"><span>Net Profit:</span> {backtest_result['net_profit']:.2f} ({backtest_result['profit_percentage']:.2f}%)</div>
                <div class="metric"><span>Total Trades:</span> {backtest_result['total_trades']}</div>
            </div>
            
            <div class="section">
                <h2>Basic Statistics</h2>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
        """
        
        # Add basic statistics
        basic_stats = analysis_result.get("basic_stats", {})
        for metric, value in basic_stats.items():
            display_name = " ".join(word.capitalize() for word in metric.split("_"))
            
            # Format the value
            if isinstance(value, float):
                formatted_value = f"{value:.2f}"
                if metric in ["win_rate", "max_drawdown_percentage"]:
                    formatted_value += "%"
            else:
                formatted_value = str(value)
            
            # Determine CSS class
            css_class = ""
            if metric == "win_rate" and value > 50:
                css_class = "positive"
            elif metric == "max_drawdown_percentage":
                css_class = "negative"
            elif metric == "sharpe_ratio" and value > 1:
                css_class = "positive"
            elif metric == "profit_factor" and value > 1:
                css_class = "positive"
            
            html_content += f"""
                    <tr>
                        <td>{display_name}</td>
                        <td class="{css_class}">{formatted_value}</td>
                    </tr>
            """
        
        html_content += """
                </table>
            </div>
            
            <div class="section">
                <h2>Advanced Metrics</h2>
                <table>
                    <tr>
                        <th>Category</th>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
        """
        
        # Add advanced metrics
        advanced_metrics = analysis_result.get("advanced_metrics", {})
        for category, metrics in advanced_metrics.items():
            category_display = " ".join(word.capitalize() for word in category.split("_"))
            
            for i, (metric, value) in enumerate(metrics.items()):
                display_name = " ".join(word.capitalize() for word in metric.split("_"))
                
                # Format the value
                if isinstance(value, float):
                    formatted_value = f"{value:.2f}"
                    if metric in ["win_loss_ratio", "kelly_percentage", "optimal_f", "total_return", "annualized_return"]:
                        if metric != "win_loss_ratio":
                            formatted_value += "%"
                else:
                    formatted_value = str(value)
                
                # Determine CSS class
                css_class = ""
                if metric in ["sharpe_ratio", "sortino_ratio", "calmar_ratio"] and value > 1:
                    css_class = "positive"
                elif metric in ["win_loss_ratio"] and value > 1:
                    css_class = "positive"
                elif metric in ["total_return", "annualized_return"] and value > 0:
                    css_class = "positive"
                elif metric in ["total_return", "annualized_return"] and value < 0:
                    css_class = "negative"
                
                html_content += f"""
                    <tr>
                        <td>{category_display if i == 0 else ""}</td>
                        <td>{display_name}</td>
                        <td class="{css_class}">{formatted_value}</td>
                    </tr>
                """
        
        html_content += """
                </table>
            </div>
        """
        
        # Add Monte Carlo simulation results
        mc_results = analysis_result.get("monte_carlo", {})
        if mc_results:
            html_content += f"""
            <div class="section">
                <h2>Monte Carlo Simulation</h2>
                <div class="summary">
                    <div class="metric"><span>Iterations:</span> {mc_results['iterations']}</div>
                    <div class="metric"><span>Confidence Level:</span> {mc_results['confidence_level']:.1f}%</div>
                    <div class="metric"><span>Mean Final Equity:</span> {mc_results['mean_final_equity']:.2f}</div>
                    <div class="metric"><span>Median Final Equity:</span> {mc_results['median_final_equity']:.2f}</div>
                    <div class="metric"><span>Confidence Interval:</span> {mc_results['confidence_interval']['lower']:.2f} to {mc_results['confidence_interval']['upper']:.2f}</div>
                    <div class="metric"><span>Mean Maximum Drawdown:</span> {mc_results['drawdown_stats']['mean_max_drawdown']:.2f}%</div>
                    <div class="metric"><span>Worst Maximum Drawdown:</span> {mc_results['drawdown_stats']['worst_max_drawdown']:.2f}%</div>
                </div>
                
                <h3>Final Equity Distribution</h3>
                <div id="equity-distribution-chart" class="chart"></div>
                
                <h3>Monte Carlo Equity Curves</h3>
                <div id="mc-equity-chart" class="chart"></div>
            </div>
            
            <script>
                // Final Equity Distribution Chart
                var percentiles = {json.dumps(mc_results['final_equity_percentiles'])};
                var percentileValues = Object.values(percentiles);
                var percentileLabels = Object.keys(percentiles).map(p => p + '%');
                
                var trace = {{
                    x: percentileLabels,
                    y: percentileValues,
                    type: 'bar'
                }};
                
                var layout = {{
                    title: 'Final Equity Percentiles',
                    xaxis: {{ title: 'Percentile' }},
                    yaxis: {{ title: 'Equity' }}
                }};
                
                Plotly.newPlot('equity-distribution-chart', [trace], layout);
                
                // Monte Carlo Equity Curves
                var mcTraces = [];
            """
            
            # Add sample equity curves
            for i, curve in enumerate(mc_results.get("sample_equity_curves", [])):
                html_content += f"""
                mcTraces.push({{
                    y: {json.dumps(curve)},
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Simulation {i+1}',
                    opacity: 0.3
                }});
                """
            
            # Add original equity curve
            html_content += f"""
                // Original equity curve
                mcTraces.push({{
                    y: {json.dumps(backtest_result.get('equity_curve', []))},
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Original',
                    line: {{ color: 'red', width: 2 }}
                }});
                
                var mcLayout = {{
                    title: 'Monte Carlo Equity Curves',
                    xaxis: {{ title: 'Trade #' }},
                    yaxis: {{ title: 'Equity' }}
                }};
                
                Plotly.newPlot('mc-equity-chart', mcTraces, mcLayout);
            </script>
            """
        
        # Close HTML
        html_content += """
        </body>
        </html>
        """
        
        # Write to file
        with open(filepath, "w") as f:
            f.write(html_content)
            
        logger.info(f"Statistical analysis report generated at {filepath}")
        return filepath
