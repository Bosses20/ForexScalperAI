"""
Low-Latency Execution Module for Forex Trading Bot

This module provides optimized, low-latency trade execution capabilities
for the Forex trading bot, enabling faster trade placement and processing.
"""

import logging
import time
import threading
from queue import Queue, Empty
from typing import Dict, List, Any, Optional, Callable
import json
import os
from datetime import datetime

# Initialize logger
logger = logging.getLogger('low_latency_executor')

class ExecutionOptimizer:
    """
    Optimizes trade execution parameters based on market conditions,
    historical execution data, and current system performance.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the execution optimizer.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config.get('execution_optimizer', {})
        self.enabled = self.config.get('enabled', True)
        self.max_history_size = self.config.get('max_history_size', 1000)
        self.execution_history = []
        
        # Performance thresholds
        self.execution_time_threshold = self.config.get('execution_time_threshold_ms', 150)
        self.slippage_threshold = self.config.get('slippage_threshold_pips', 1.0)
        
        logger.info("Execution Optimizer initialized")
    
    def record_execution(self, execution_data: Dict[str, Any]) -> None:
        """
        Record trade execution data for optimization.
        
        Args:
            execution_data: Dictionary with execution details
        """
        if not self.enabled:
            return
            
        # Add timestamp if not present
        if 'timestamp' not in execution_data:
            execution_data['timestamp'] = time.time()
            
        # Add to execution history
        self.execution_history.append(execution_data)
        
        # Trim history if needed
        if len(self.execution_history) > self.max_history_size:
            self.execution_history = self.execution_history[-self.max_history_size:]
    
    def get_execution_parameters(self, 
                              symbol: str, 
                              order_type: str,
                              market_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get optimized execution parameters based on history and market conditions.
        
        Args:
            symbol: Trading symbol
            order_type: Type of order to execute
            market_conditions: Current market conditions
            
        Returns:
            Dictionary with optimized execution parameters
        """
        if not self.enabled:
            return self._get_default_parameters(order_type)
            
        try:
            # Extract relevant market conditions
            volatility = market_conditions.get('volatility', 'medium')
            liquidity = market_conditions.get('liquidity', 'medium')
            spread = market_conditions.get('spread', 0.0)
            
            # Get symbol-specific execution history
            symbol_history = [entry for entry in self.execution_history 
                            if entry.get('symbol') == symbol]
            
            # Calculate average execution time and slippage for this symbol
            avg_execution_time = 0.0
            avg_slippage = 0.0
            
            if symbol_history:
                execution_times = [entry.get('execution_time_ms', 0) for entry in symbol_history]
                slippages = [entry.get('slippage_pips', 0) for entry in symbol_history]
                
                avg_execution_time = sum(execution_times) / len(execution_times)
                avg_slippage = sum(slippages) / len(slippages)
            
            # Optimize parameters based on conditions
            params = self._get_default_parameters(order_type)
            
            # Adjust timeout based on execution history
            if avg_execution_time > 0:
                # Set timeout to average execution time plus buffer
                buffer_factor = 2.0  # Default buffer
                
                # Increase buffer for high volatility
                if volatility == 'high':
                    buffer_factor = 3.0
                elif volatility == 'low':
                    buffer_factor = 1.5
                    
                params['timeout_ms'] = int(avg_execution_time * buffer_factor)
                
                # Ensure reasonable bounds
                params['timeout_ms'] = max(100, min(5000, params['timeout_ms']))
            
            # Adjust maximum slippage based on history and market conditions
            if avg_slippage > 0:
                # Base max allowed slippage on historical average
                params['max_slippage_pips'] = avg_slippage * 1.5
                
                # Adjust for volatility
                if volatility == 'high':
                    params['max_slippage_pips'] *= 1.5
                elif volatility == 'low':
                    params['max_slippage_pips'] *= 0.8
                    
                # Adjust for liquidity
                if liquidity == 'low':
                    params['max_slippage_pips'] *= 1.3
                elif liquidity == 'high':
                    params['max_slippage_pips'] *= 0.9
                    
                # Ensure reasonable bounds (0.5 - 10 pips)
                params['max_slippage_pips'] = max(0.5, min(10.0, params['max_slippage_pips']))
            
            # Adjust retry settings based on conditions
            if liquidity == 'low' or volatility == 'high':
                params['max_retries'] = self.config.get('high_volatility_max_retries', 3)
                params['retry_delay_ms'] = self.config.get('high_volatility_retry_delay_ms', 100)
            else:
                params['max_retries'] = self.config.get('default_max_retries', 2)
                params['retry_delay_ms'] = self.config.get('default_retry_delay_ms', 50)
            
            # Adjust execution mode based on conditions
            if spread > self.config.get('high_spread_threshold', 3.0):
                params['execution_mode'] = 'conservative'
            elif liquidity == 'high' and volatility == 'low':
                params['execution_mode'] = 'aggressive'
            else:
                params['execution_mode'] = 'balanced'
                
            return params
            
        except Exception as e:
            logger.error(f"Error optimizing execution parameters: {str(e)}")
            return self._get_default_parameters(order_type)
    
    def _get_default_parameters(self, order_type: str) -> Dict[str, Any]:
        """
        Get default execution parameters based on order type.
        
        Args:
            order_type: Type of order to execute
            
        Returns:
            Dictionary with default execution parameters
        """
        # Base parameters
        params = {
            'timeout_ms': self.config.get('default_timeout_ms', 500),
            'max_slippage_pips': self.config.get('default_max_slippage_pips', 1.0),
            'max_retries': self.config.get('default_max_retries', 2),
            'retry_delay_ms': self.config.get('default_retry_delay_ms', 50),
            'execution_mode': 'balanced'  # balanced, aggressive, conservative
        }
        
        # Adjust based on order type
        if order_type == 'market':
            # Market orders need faster execution
            params['timeout_ms'] = self.config.get('market_order_timeout_ms', 300)
            params['max_slippage_pips'] = self.config.get('market_order_max_slippage_pips', 1.5)
        elif order_type == 'limit':
            # Limit orders can have longer timeouts
            params['timeout_ms'] = self.config.get('limit_order_timeout_ms', 800)
            params['max_slippage_pips'] = self.config.get('limit_order_max_slippage_pips', 0.0)
        elif order_type == 'stop':
            # Stop orders
            params['timeout_ms'] = self.config.get('stop_order_timeout_ms', 500)
            params['max_slippage_pips'] = self.config.get('stop_order_max_slippage_pips', 2.0)
            
        return params
    
    def analyze_execution_performance(self) -> Dict[str, Any]:
        """
        Analyze execution performance based on historical data.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.execution_history:
            return {
                "status": "no_data",
                "message": "No execution history available"
            }
            
        try:
            # Calculate overall metrics
            execution_times = [entry.get('execution_time_ms', 0) for entry in self.execution_history]
            slippages = [entry.get('slippage_pips', 0) for entry in self.execution_history]
            success_rate = sum(1 for entry in self.execution_history if entry.get('success', False)) / len(self.execution_history)
            
            # Calculate symbol-specific metrics
            symbols = {}
            for entry in self.execution_history:
                symbol = entry.get('symbol')
                if not symbol:
                    continue
                    
                if symbol not in symbols:
                    symbols[symbol] = {
                        'count': 0,
                        'execution_times': [],
                        'slippages': [],
                        'success_count': 0
                    }
                    
                symbols[symbol]['count'] += 1
                symbols[symbol]['execution_times'].append(entry.get('execution_time_ms', 0))
                symbols[symbol]['slippages'].append(entry.get('slippage_pips', 0))
                if entry.get('success', False):
                    symbols[symbol]['success_count'] += 1
            
            # Prepare symbol metrics
            symbol_metrics = {}
            for symbol, data in symbols.items():
                if data['count'] > 0:
                    avg_execution_time = sum(data['execution_times']) / data['count']
                    avg_slippage = sum(data['slippages']) / data['count']
                    symbol_success_rate = data['success_count'] / data['count']
                    
                    symbol_metrics[symbol] = {
                        'count': data['count'],
                        'avg_execution_time_ms': round(avg_execution_time, 2),
                        'avg_slippage_pips': round(avg_slippage, 3),
                        'success_rate': round(symbol_success_rate, 4),
                        'performance_rating': self._calculate_performance_rating(
                            avg_execution_time, avg_slippage, symbol_success_rate
                        )
                    }
            
            return {
                "status": "success",
                "overall_metrics": {
                    "total_executions": len(self.execution_history),
                    "avg_execution_time_ms": round(sum(execution_times) / len(execution_times), 2),
                    "avg_slippage_pips": round(sum(slippages) / len(slippages), 3),
                    "success_rate": round(success_rate, 4),
                    "executions_above_time_threshold": sum(1 for t in execution_times if t > self.execution_time_threshold),
                    "executions_above_slippage_threshold": sum(1 for s in slippages if s > self.slippage_threshold)
                },
                "symbol_metrics": symbol_metrics,
                "time_period": {
                    "start": datetime.fromtimestamp(min(entry.get('timestamp', time.time()) 
                                                for entry in self.execution_history)).strftime("%Y-%m-%d %H:%M:%S"),
                    "end": datetime.fromtimestamp(max(entry.get('timestamp', time.time()) 
                                              for entry in self.execution_history)).strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing execution performance: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to analyze performance: {str(e)}"
            }
    
    def _calculate_performance_rating(self, 
                                   execution_time: float, 
                                   slippage: float, 
                                   success_rate: float) -> str:
        """
        Calculate a performance rating based on metrics.
        
        Args:
            execution_time: Average execution time in ms
            slippage: Average slippage in pips
            success_rate: Rate of successful executions
            
        Returns:
            Performance rating as string
        """
        # Create a score from 0-100
        time_score = max(0, 100 - (execution_time / self.execution_time_threshold) * 50)
        slippage_score = max(0, 100 - (slippage / self.slippage_threshold) * 50)
        success_score = success_rate * 100
        
        # Weight the scores
        weighted_score = (time_score * 0.3 + slippage_score * 0.3 + success_score * 0.4)
        
        # Convert to rating
        if weighted_score >= 90:
            return "excellent"
        elif weighted_score >= 75:
            return "good"
        elif weighted_score >= 60:
            return "satisfactory"
        elif weighted_score >= 40:
            return "needs_improvement"
        else:
            return "poor"


class LowLatencyExecutor:
    """
    Provides optimized, low-latency trade execution for the Forex trading bot.
    Handles trade queue processing, execution optimization, and performance monitoring.
    """
    
    def __init__(self, config: Dict[str, Any], data_dir: str = 'data'):
        """
        Initialize the low-latency executor.
        
        Args:
            config: Configuration dictionary
            data_dir: Directory for storing execution data
        """
        self.config = config
        self.latency_config = config.get('low_latency_execution', {})
        self.enabled = self.latency_config.get('enabled', True)
        
        # Set up execution queues with priority levels
        self.high_priority_queue = Queue()
        self.normal_priority_queue = Queue()
        self.low_priority_queue = Queue()
        
        # Initialize execution optimizer
        self.optimizer = ExecutionOptimizer(config)
        
        # Set up execution statistics
        self.execution_stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'average_execution_time_ms': 0,
            'min_execution_time_ms': float('inf'),
            'max_execution_time_ms': 0
        }
        
        # Set up data directory
        self.data_dir = data_dir
        self.execution_data_dir = os.path.join(data_dir, 'execution_data')
        os.makedirs(self.execution_data_dir, exist_ok=True)
        
        # Thread management
        self.threads = []
        self.running = False
        self.thread_count = self.latency_config.get('executor_threads', 2)
        
        # Callback registration
        self.execution_callback = None
        
        logger.info(f"Low Latency Executor initialized with {self.thread_count} threads")
    
    def start(self) -> None:
        """Start the low-latency executor threads"""
        if self.running:
            logger.warning("Low Latency Executor is already running")
            return
            
        if not self.enabled:
            logger.info("Low Latency Executor is disabled in configuration")
            return
            
        self.running = True
        
        # Start executor threads
        for i in range(self.thread_count):
            thread = threading.Thread(
                target=self._execution_worker,
                name=f"executor-{i}",
                daemon=True
            )
            thread.start()
            self.threads.append(thread)
            
        logger.info(f"Started {self.thread_count} execution threads")
    
    def stop(self) -> None:
        """Stop the low-latency executor threads"""
        if not self.running:
            return
            
        self.running = False
        
        # Wait for threads to terminate
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=2.0)
                
        self.threads = []
        logger.info("Low Latency Executor stopped")
    
    def register_execution_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback function for execution results.
        
        Args:
            callback: Function to call with execution results
        """
        self.execution_callback = callback
        logger.debug("Execution callback registered")
    
    def queue_execution(self, 
                      execution_request: Dict[str, Any], 
                      priority: str = 'normal') -> str:
        """
        Queue a trade execution request.
        
        Args:
            execution_request: Dictionary with execution details
            priority: Priority level (high, normal, low)
            
        Returns:
            Execution ID
        """
        if not self.enabled:
            logger.warning("Execution request ignored: Low Latency Executor is disabled")
            return ""
            
        try:
            # Generate execution ID
            execution_id = f"exec_{int(time.time())}_{execution_request.get('symbol', 'unknown')}_{execution_request.get('order_type', 'unknown')}"
            
            # Add metadata
            execution_request['execution_id'] = execution_id
            execution_request['timestamp'] = time.time()
            execution_request['status'] = 'queued'
            
            # Select queue based on priority
            if priority == 'high':
                self.high_priority_queue.put(execution_request)
            elif priority == 'low':
                self.low_priority_queue.put(execution_request)
            else:  # 'normal' is default
                self.normal_priority_queue.put(execution_request)
                
            logger.debug(f"Queued execution {execution_id} with {priority} priority")
            return execution_id
            
        except Exception as e:
            logger.error(f"Error queueing execution: {str(e)}")
            return ""
    
    def _execution_worker(self) -> None:
        """Worker thread for processing execution requests"""
        while self.running:
            try:
                # Check queues in priority order
                execution_request = None
                
                try:
                    # Try to get from high priority queue first
                    execution_request = self.high_priority_queue.get(block=False)
                except Empty:
                    try:
                        # Try normal priority queue next
                        execution_request = self.normal_priority_queue.get(block=False)
                    except Empty:
                        try:
                            # Finally, try low priority queue
                            execution_request = self.low_priority_queue.get(block=True, timeout=0.1)
                        except Empty:
                            # No items in any queue, sleep briefly and continue
                            time.sleep(0.01)
                            continue
                
                if execution_request:
                    self._process_execution(execution_request)
                    
            except Exception as e:
                logger.error(f"Error in execution worker: {str(e)}")
                time.sleep(0.1)  # Sleep briefly to avoid tight loop in case of persistent errors
    
    def _process_execution(self, execution_request: Dict[str, Any]) -> None:
        """
        Process an execution request.
        
        Args:
            execution_request: Dictionary with execution details
        """
        execution_id = execution_request.get('execution_id', 'unknown')
        symbol = execution_request.get('symbol', 'unknown')
        order_type = execution_request.get('order_type', 'market')
        
        try:
            # Log the start of execution
            logger.debug(f"Processing execution {execution_id} for {symbol}")
            
            # Update status
            execution_request['status'] = 'processing'
            execution_request['processing_started'] = time.time()
            
            # Get market conditions (if available in the request)
            market_conditions = execution_request.get('market_conditions', {})
            
            # Get optimized execution parameters
            execution_params = self.optimizer.get_execution_parameters(
                symbol, order_type, market_conditions
            )
            execution_request['execution_params'] = execution_params
            
            # Start timing execution
            start_time = time.time()
            
            # *** ACTUAL EXECUTION WOULD HAPPEN HERE ***
            # This would typically involve calls to a trading platform API
            # For simulation purposes, we'll just sleep for a random amount of time
            
            # Simulate execution time based on parameters
            execution_mode = execution_params.get('execution_mode', 'balanced')
            timeout_ms = execution_params.get('timeout_ms', 500)
            
            # Simulate different execution times based on mode
            if execution_mode == 'aggressive':
                execution_time = timeout_ms * 0.3  # 30% of timeout
            elif execution_mode == 'conservative':
                execution_time = timeout_ms * 0.7  # 70% of timeout
            else:  # balanced
                execution_time = timeout_ms * 0.5  # 50% of timeout
                
            # Convert to seconds and sleep
            time.sleep(execution_time / 1000.0)
            
            # Simulate success rate (95% success)
            import random
            success = random.random() < 0.95
            
            # Calculate execution time
            end_time = time.time()
            execution_time_ms = (end_time - start_time) * 1000
            
            # Simulate slippage
            if order_type == 'market':
                slippage_pips = random.uniform(0, execution_params.get('max_slippage_pips', 1.0))
            else:
                slippage_pips = 0.0
                
            # Update execution request with results
            execution_request.update({
                'status': 'completed' if success else 'failed',
                'success': success,
                'execution_time_ms': execution_time_ms,
                'slippage_pips': slippage_pips,
                'completion_time': end_time
            })
            
            # Update execution statistics
            self._update_statistics(execution_time_ms, success)
            
            # Record execution for optimization
            self.optimizer.record_execution({
                'symbol': symbol,
                'order_type': order_type,
                'execution_time_ms': execution_time_ms,
                'slippage_pips': slippage_pips,
                'success': success,
                'timestamp': end_time
            })
            
            # Save execution data
            self._save_execution_data(execution_request)
            
            # Call execution callback if registered
            if self.execution_callback:
                self.execution_callback(execution_request)
                
            logger.debug(f"Execution {execution_id} completed in {execution_time_ms:.2f} ms, success: {success}")
            
        except Exception as e:
            # Update execution request with error
            execution_request.update({
                'status': 'error',
                'success': False,
                'error': str(e),
                'completion_time': time.time()
            })
            
            # Update statistics
            self._update_statistics(0, False)
            
            # Save execution data
            self._save_execution_data(execution_request)
            
            # Call execution callback if registered
            if self.execution_callback:
                self.execution_callback(execution_request)
                
            logger.error(f"Error processing execution {execution_id}: {str(e)}")
    
    def _update_statistics(self, execution_time_ms: float, success: bool) -> None:
        """
        Update execution statistics.
        
        Args:
            execution_time_ms: Execution time in milliseconds
            success: Whether the execution was successful
        """
        self.execution_stats['total_executions'] += 1
        
        if success:
            self.execution_stats['successful_executions'] += 1
        else:
            self.execution_stats['failed_executions'] += 1
            
        if execution_time_ms > 0:
            # Update min/max times
            self.execution_stats['min_execution_time_ms'] = min(
                self.execution_stats['min_execution_time_ms'], 
                execution_time_ms
            )
            self.execution_stats['max_execution_time_ms'] = max(
                self.execution_stats['max_execution_time_ms'], 
                execution_time_ms
            )
            
            # Update average time using rolling average
            current_avg = self.execution_stats['average_execution_time_ms']
            current_count = self.execution_stats['total_executions']
            
            if current_count == 1:
                # First execution
                self.execution_stats['average_execution_time_ms'] = execution_time_ms
            else:
                # Rolling average
                new_avg = current_avg + (execution_time_ms - current_avg) / current_count
                self.execution_stats['average_execution_time_ms'] = new_avg
    
    def _save_execution_data(self, execution_data: Dict[str, Any]) -> None:
        """
        Save execution data to disk.
        
        Args:
            execution_data: Dictionary with execution details
        """
        try:
            # Create a filename with timestamp and execution ID
            timestamp = time.strftime("%Y%m%d")
            execution_id = execution_data.get('execution_id', 'unknown')
            filename = os.path.join(self.execution_data_dir, f"{timestamp}_executions.jsonl")
            
            # Append to file
            with open(filename, 'a') as f:
                f.write(json.dumps(execution_data) + '\n')
                
        except Exception as e:
            logger.error(f"Error saving execution data: {str(e)}")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Get current execution statistics.
        
        Returns:
            Dictionary with execution statistics
        """
        # Copy stats to avoid threading issues
        stats = dict(self.execution_stats)
        
        # Calculate success rate
        total = stats['total_executions']
        if total > 0:
            stats['success_rate'] = stats['successful_executions'] / total
        else:
            stats['success_rate'] = 0.0
            
        # Convert infinite min to 0
        if stats['min_execution_time_ms'] == float('inf'):
            stats['min_execution_time_ms'] = 0
            
        # Round floating point values
        for key in ['average_execution_time_ms', 'min_execution_time_ms', 'max_execution_time_ms', 'success_rate']:
            if key in stats:
                stats[key] = round(stats[key], 2)
                
        # Add queue stats
        stats['queued_executions'] = {
            'high_priority': self.high_priority_queue.qsize(),
            'normal_priority': self.normal_priority_queue.qsize(),
            'low_priority': self.low_priority_queue.qsize(),
            'total': (self.high_priority_queue.qsize() + 
                     self.normal_priority_queue.qsize() + 
                     self.low_priority_queue.qsize())
        }
        
        # Add thread stats
        stats['executor_threads'] = {
            'configured': self.thread_count,
            'active': sum(1 for t in self.threads if t.is_alive())
        }
        
        # Add system stats
        stats['system'] = {
            'enabled': self.enabled,
            'running': self.running
        }
        
        return stats
    
    def get_optimization_analysis(self) -> Dict[str, Any]:
        """
        Get optimization analysis from the execution optimizer.
        
        Returns:
            Dictionary with optimization analysis
        """
        return self.optimizer.analyze_execution_performance()
    
    def reset_statistics(self) -> None:
        """Reset execution statistics"""
        self.execution_stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'average_execution_time_ms': 0,
            'min_execution_time_ms': float('inf'),
            'max_execution_time_ms': 0
        }
        logger.info("Execution statistics reset")
