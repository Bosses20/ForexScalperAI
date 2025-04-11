"""
Performance tracking for the Forex Trading Bot
Monitors execution speed, resource usage, and trading performance
"""

import time
import os
import psutil
import threading
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple, Any
from collections import deque
from loguru import logger


class PerformanceTracker:
    """
    Tracks trading system performance metrics
    Includes execution timing, resource usage, and trading statistics
    """
    
    def __init__(self, config: dict):
        """
        Initialize the performance tracker
        
        Args:
            config: Configuration dictionary with performance settings
        """
        self.config = config
        self.metrics_file = config.get('metrics_file', 'data/performance/metrics.csv')
        self.max_history = config.get('max_history_items', 1000)
        self.save_interval = config.get('save_interval_seconds', 300)  # 5 minutes
        self.enabled = config.get('performance_tracking_enabled', True)
        
        # Initialize metrics storage
        self.function_timings = {}
        self.resource_usage = deque(maxlen=self.max_history)
        self.strategy_timings = {}
        self.api_response_times = {}
        self.execution_queue_lengths = deque(maxlen=self.max_history)
        
        # Initialize process monitor
        self.process = psutil.Process(os.getpid())
        
        # Initialize metrics saving
        self.last_save_time = time.time()
        
        # Create metrics directory
        os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
        
        # Start background monitoring if enabled
        if self.enabled:
            self._start_resource_monitoring()
            
        logger.info("Performance tracker initialized")
    
    def _start_resource_monitoring(self, interval: int = 60) -> None:
        """
        Start background thread to monitor system resources
        
        Args:
            interval: Monitoring interval in seconds
        """
        def monitor_resources():
            while self.enabled:
                try:
                    # Collect resource metrics
                    self.record_resource_usage()
                    
                    # Save metrics if interval elapsed
                    current_time = time.time()
                    if current_time - self.last_save_time >= self.save_interval:
                        self.save_metrics()
                        self.last_save_time = current_time
                    
                    # Sleep for the specified interval
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"Error in resource monitoring: {str(e)}")
        
        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=monitor_resources,
            daemon=True,
            name="ResourceMonitor"
        )
        monitor_thread.start()
        logger.debug("Resource monitoring thread started")
    
    def record_function_time(self, function_name: str, execution_time: float,
                          module: str = None, category: str = None) -> None:
        """
        Record execution time for a function
        
        Args:
            function_name: Name of the function
            execution_time: Execution time in milliseconds
            module: Module containing the function
            category: Category for grouping functions
        """
        if not self.enabled:
            return
            
        # Create key for the function
        key = f"{module}.{function_name}" if module else function_name
        
        # Add category if provided
        if category:
            key = f"{category}:{key}"
            
        # Initialize function record if not exists
        if key not in self.function_timings:
            self.function_timings[key] = {
                'count': 0,
                'total_time': 0,
                'min_time': float('inf'),
                'max_time': 0,
                'times': deque(maxlen=100),  # Keep last 100 times for percentiles
                'last_call': datetime.now().isoformat()
            }
            
        # Update metrics
        self.function_timings[key]['count'] += 1
        self.function_timings[key]['total_time'] += execution_time
        self.function_timings[key]['min_time'] = min(
            self.function_timings[key]['min_time'], execution_time
        )
        self.function_timings[key]['max_time'] = max(
            self.function_timings[key]['max_time'], execution_time
        )
        self.function_timings[key]['times'].append(execution_time)
        self.function_timings[key]['last_call'] = datetime.now().isoformat()
    
    def record_strategy_time(self, strategy_name: str, symbol: str, timeframe: str, 
                          execution_time: float) -> None:
        """
        Record execution time for a strategy
        
        Args:
            strategy_name: Name of the strategy
            symbol: Trading symbol analyzed
            timeframe: Timeframe analyzed
            execution_time: Execution time in milliseconds
        """
        if not self.enabled:
            return
            
        # Create key for the strategy
        key = f"{strategy_name}_{symbol}_{timeframe}"
        
        # Initialize strategy record if not exists
        if key not in self.strategy_timings:
            self.strategy_timings[key] = {
                'count': 0,
                'total_time': 0,
                'min_time': float('inf'),
                'max_time': 0,
                'times': deque(maxlen=100),  # Keep last 100 times for percentiles
                'last_call': datetime.now().isoformat()
            }
            
        # Update metrics
        self.strategy_timings[key]['count'] += 1
        self.strategy_timings[key]['total_time'] += execution_time
        self.strategy_timings[key]['min_time'] = min(
            self.strategy_timings[key]['min_time'], execution_time
        )
        self.strategy_timings[key]['max_time'] = max(
            self.strategy_timings[key]['max_time'], execution_time
        )
        self.strategy_timings[key]['times'].append(execution_time)
        self.strategy_timings[key]['last_call'] = datetime.now().isoformat()
    
    def record_api_response_time(self, endpoint: str, method: str, 
                              status_code: int, execution_time: float) -> None:
        """
        Record API response time
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            status_code: Response status code
            execution_time: Execution time in milliseconds
        """
        if not self.enabled:
            return
            
        # Create key for the API endpoint
        key = f"{method}_{endpoint}"
        
        # Initialize API record if not exists
        if key not in self.api_response_times:
            self.api_response_times[key] = {
                'count': 0,
                'total_time': 0,
                'min_time': float('inf'),
                'max_time': 0,
                'status_codes': {},
                'times': deque(maxlen=100),  # Keep last 100 times for percentiles
                'last_call': datetime.now().isoformat()
            }
            
        # Update metrics
        self.api_response_times[key]['count'] += 1
        self.api_response_times[key]['total_time'] += execution_time
        self.api_response_times[key]['min_time'] = min(
            self.api_response_times[key]['min_time'], execution_time
        )
        self.api_response_times[key]['max_time'] = max(
            self.api_response_times[key]['max_time'], execution_time
        )
        self.api_response_times[key]['times'].append(execution_time)
        self.api_response_times[key]['last_call'] = datetime.now().isoformat()
        
        # Update status code counts
        status_code_str = str(status_code)
        if status_code_str not in self.api_response_times[key]['status_codes']:
            self.api_response_times[key]['status_codes'][status_code_str] = 0
        self.api_response_times[key]['status_codes'][status_code_str] += 1
    
    def record_queue_length(self, queue_name: str, length: int) -> None:
        """
        Record execution queue length
        
        Args:
            queue_name: Name of the queue
            length: Current queue length
        """
        if not self.enabled:
            return
            
        timestamp = datetime.now().isoformat()
        
        self.execution_queue_lengths.append({
            'timestamp': timestamp,
            'queue_name': queue_name,
            'length': length
        })
    
    def record_resource_usage(self) -> Dict:
        """
        Record system resource usage
        
        Returns:
            Dictionary with resource usage metrics
        """
        if not self.enabled:
            return {}
            
        try:
            # Get memory usage
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            
            # Get CPU usage
            cpu_percent = self.process.cpu_percent(interval=0.1)
            
            # Get disk I/O
            io_counters = self.process.io_counters()
            
            # Get thread count
            thread_count = len(self.process.threads())
            
            # Create metrics record
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': cpu_percent,
                'memory_rss_mb': memory_info.rss / (1024 * 1024),
                'memory_vms_mb': memory_info.vms / (1024 * 1024),
                'memory_percent': memory_percent,
                'thread_count': thread_count,
                'read_count': io_counters.read_count,
                'write_count': io_counters.write_count,
                'read_bytes': io_counters.read_bytes,
                'write_bytes': io_counters.write_bytes
            }
            
            # Add system-wide metrics
            system_memory = psutil.virtual_memory()
            system_cpu = psutil.cpu_percent(interval=None)
            
            metrics.update({
                'system_cpu_percent': system_cpu,
                'system_memory_percent': system_memory.percent,
                'system_memory_available_mb': system_memory.available / (1024 * 1024)
            })
            
            # Store metrics
            self.resource_usage.append(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error recording resource usage: {str(e)}")
            return {}
    
    def get_function_statistics(self, function_name: Optional[str] = None) -> Dict:
        """
        Get performance statistics for functions
        
        Args:
            function_name: Optional function name filter
            
        Returns:
            Dictionary with function performance statistics
        """
        if not self.enabled:
            return {}
            
        # Return stats for specific function if requested
        if function_name and function_name in self.function_timings:
            stats = self._calculate_timing_stats(self.function_timings[function_name])
            return {function_name: stats}
            
        # Return stats for all functions
        result = {}
        for name, timing in self.function_timings.items():
            if function_name and function_name not in name:
                continue
                
            result[name] = self._calculate_timing_stats(timing)
            
        return result
    
    def get_strategy_statistics(self, strategy_name: Optional[str] = None) -> Dict:
        """
        Get performance statistics for strategies
        
        Args:
            strategy_name: Optional strategy name filter
            
        Returns:
            Dictionary with strategy performance statistics
        """
        if not self.enabled:
            return {}
            
        # Return stats for all strategies
        result = {}
        for name, timing in self.strategy_timings.items():
            if strategy_name and strategy_name not in name:
                continue
                
            result[name] = self._calculate_timing_stats(timing)
            
        return result
    
    def get_api_statistics(self, endpoint: Optional[str] = None) -> Dict:
        """
        Get performance statistics for API endpoints
        
        Args:
            endpoint: Optional endpoint filter
            
        Returns:
            Dictionary with API performance statistics
        """
        if not self.enabled:
            return {}
            
        # Return stats for all API endpoints
        result = {}
        for name, timing in self.api_response_times.items():
            if endpoint and endpoint not in name:
                continue
                
            stats = self._calculate_timing_stats(timing)
            # Add status code distribution
            stats['status_codes'] = timing['status_codes']
            result[name] = stats
            
        return result
    
    def get_resource_statistics(self, hours: int = 1) -> Dict:
        """
        Get resource usage statistics
        
        Args:
            hours: Number of hours to include in statistics
            
        Returns:
            Dictionary with resource usage statistics
        """
        if not self.enabled or not self.resource_usage:
            return {}
            
        # Filter by time if requested
        if hours:
            start_time = datetime.now() - timedelta(hours=hours)
            filtered_data = [
                item for item in self.resource_usage
                if datetime.fromisoformat(item['timestamp']) >= start_time
            ]
        else:
            filtered_data = list(self.resource_usage)
            
        if not filtered_data:
            return {}
            
        # Convert to DataFrame for easier statistics
        df = pd.DataFrame(filtered_data)
        
        # Calculate statistics
        result = {
            'cpu_percent': {
                'mean': df['cpu_percent'].mean(),
                'max': df['cpu_percent'].max(),
                'min': df['cpu_percent'].min(),
                'p95': np.percentile(df['cpu_percent'], 95)
            },
            'memory_rss_mb': {
                'mean': df['memory_rss_mb'].mean(),
                'max': df['memory_rss_mb'].max(),
                'min': df['memory_rss_mb'].min(),
                'p95': np.percentile(df['memory_rss_mb'], 95)
            },
            'memory_percent': {
                'mean': df['memory_percent'].mean(),
                'max': df['memory_percent'].max(),
                'min': df['memory_percent'].min(),
                'p95': np.percentile(df['memory_percent'], 95)
            },
            'thread_count': {
                'mean': df['thread_count'].mean(),
                'max': df['thread_count'].max(),
                'min': df['thread_count'].min()
            },
            'system_cpu_percent': {
                'mean': df['system_cpu_percent'].mean(),
                'max': df['system_cpu_percent'].max(),
                'min': df['system_cpu_percent'].min(),
                'p95': np.percentile(df['system_cpu_percent'], 95)
            },
            'system_memory_percent': {
                'mean': df['system_memory_percent'].mean(),
                'max': df['system_memory_percent'].max(),
                'min': df['system_memory_percent'].min(),
                'p95': np.percentile(df['system_memory_percent'], 95)
            },
            'data_points': len(filtered_data),
            'time_range': {
                'start': filtered_data[0]['timestamp'],
                'end': filtered_data[-1]['timestamp']
            }
        }
        
        return result
    
    def get_queue_statistics(self) -> Dict:
        """
        Get queue length statistics
        
        Returns:
            Dictionary with queue length statistics
        """
        if not self.enabled or not self.execution_queue_lengths:
            return {}
            
        # Group by queue name
        queues = {}
        for item in self.execution_queue_lengths:
            queue_name = item['queue_name']
            if queue_name not in queues:
                queues[queue_name] = []
            queues[queue_name].append(item['length'])
            
        # Calculate statistics for each queue
        result = {}
        for queue_name, lengths in queues.items():
            result[queue_name] = {
                'mean': np.mean(lengths),
                'max': max(lengths),
                'min': min(lengths),
                'p95': np.percentile(lengths, 95) if len(lengths) > 0 else 0,
                'current': lengths[-1] if lengths else 0,
                'data_points': len(lengths)
            }
            
        return result
    
    def _calculate_timing_stats(self, timing_data: Dict) -> Dict:
        """
        Calculate timing statistics from raw timing data
        
        Args:
            timing_data: Raw timing data dictionary
            
        Returns:
            Dictionary with calculated statistics
        """
        count = timing_data['count']
        if count == 0:
            return {
                'count': 0,
                'avg_time': 0,
                'min_time': 0,
                'max_time': 0,
                'p95': 0,
                'p99': 0,
                'last_call': timing_data.get('last_call')
            }
            
        # Calculate statistics
        avg_time = timing_data['total_time'] / count
        
        # Calculate percentiles if there's enough data
        times_list = list(timing_data['times'])
        p95 = np.percentile(times_list, 95) if times_list else 0
        p99 = np.percentile(times_list, 99) if times_list else 0
        
        return {
            'count': count,
            'avg_time': avg_time,
            'min_time': timing_data['min_time'],
            'max_time': timing_data['max_time'],
            'p95': p95,
            'p99': p99,
            'last_call': timing_data.get('last_call')
        }
    
    def save_metrics(self) -> bool:
        """
        Save performance metrics to file
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
            
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
            
            # Save resource usage data
            resource_df = pd.DataFrame(list(self.resource_usage))
            
            # Save to CSV
            resource_df.to_csv(self.metrics_file, index=False)
            
            logger.debug(f"Saved performance metrics to {self.metrics_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving performance metrics: {str(e)}")
            return False
    
    def reset_metrics(self) -> None:
        """
        Reset all performance metrics
        """
        self.function_timings = {}
        self.resource_usage.clear()
        self.strategy_timings = {}
        self.api_response_times = {}
        self.execution_queue_lengths.clear()
        
        logger.info("Performance metrics reset")
    
    def performance_report(self) -> Dict:
        """
        Generate a comprehensive performance report
        
        Returns:
            Dictionary with performance report data
        """
        if not self.enabled:
            return {'enabled': False}
            
        report = {
            'timestamp': datetime.now().isoformat(),
            'enabled': self.enabled,
            'resource_usage': self.get_resource_statistics(hours=24),
            'functions': {
                'count': len(self.function_timings),
                'slowest': [],
                'most_called': []
            },
            'strategies': {
                'count': len(self.strategy_timings),
                'slowest': [],
                'most_called': []
            },
            'api_endpoints': {
                'count': len(self.api_response_times),
                'slowest': [],
                'most_called': []
            },
            'queues': self.get_queue_statistics()
        }
        
        # Find slowest functions
        sorted_funcs = sorted(
            self.get_function_statistics().items(),
            key=lambda x: x[1]['avg_time'],
            reverse=True
        )
        report['functions']['slowest'] = sorted_funcs[:5]
        
        # Find most called functions
        sorted_funcs = sorted(
            self.get_function_statistics().items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        report['functions']['most_called'] = sorted_funcs[:5]
        
        # Find slowest strategies
        sorted_strats = sorted(
            self.get_strategy_statistics().items(),
            key=lambda x: x[1]['avg_time'],
            reverse=True
        )
        report['strategies']['slowest'] = sorted_strats[:5]
        
        # Find most called strategies
        sorted_strats = sorted(
            self.get_strategy_statistics().items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        report['strategies']['most_called'] = sorted_strats[:5]
        
        # Find slowest API endpoints
        sorted_apis = sorted(
            self.get_api_statistics().items(),
            key=lambda x: x[1]['avg_time'],
            reverse=True
        )
        report['api_endpoints']['slowest'] = sorted_apis[:5]
        
        # Find most called API endpoints
        sorted_apis = sorted(
            self.get_api_statistics().items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        report['api_endpoints']['most_called'] = sorted_apis[:5]
        
        return report
