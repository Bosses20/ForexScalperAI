"""
Metrics collector for the Forex Trading Bot
Aggregates metrics from different system components
"""

import os
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np

from .logger import get_logger

logger = get_logger("MetricsCollector")


class MetricsCollector:
    """
    Collects, aggregates, and manages metrics from various bot components
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the metrics collector
        
        Args:
            config: Configuration dictionary with metrics collection settings
        """
        self.config = config
        self.enabled = config.get('metrics_collection_enabled', True)
        self.collection_interval = config.get('collection_interval_seconds', 300)  # 5 minutes
        self.storage_dir = config.get('metrics_storage_dir', 'data/metrics')
        self.max_history_days = config.get('max_history_days', 30)
        
        # Create metrics directory
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Initialize metrics stores
        self.trading_metrics = {}
        self.performance_metrics = {}
        self.system_metrics = {}
        self.api_metrics = {}
        
        # Initialize components
        self.performance_tracker = None
        self.system_monitor = None
        self.api_monitor = None
        
        # Start collection thread if enabled
        if self.enabled:
            self._start_collection()
            
        logger.info("Metrics collector initialized")
    
    def register_component(self, component_type: str, component: Any) -> None:
        """
        Register a component for metrics collection
        
        Args:
            component_type: Type of component (performance, system, api, etc.)
            component: Component instance
        """
        if component_type == 'performance':
            self.performance_tracker = component
            logger.info("Registered performance tracker")
        elif component_type == 'system':
            self.system_monitor = component
            logger.info("Registered system monitor")
        elif component_type == 'api':
            self.api_monitor = component
            logger.info("Registered API monitor")
        else:
            logger.warning(f"Unknown component type: {component_type}")
    
    def _start_collection(self) -> None:
        """
        Start the background metrics collection thread
        """
        def collect_task():
            while self.enabled:
                try:
                    # Collect metrics from all registered components
                    self.collect_all_metrics()
                    
                    # Save metrics
                    self.save_metrics()
                    
                    # Clean up old metrics
                    self.cleanup_old_metrics()
                    
                    # Sleep for the collection interval
                    time.sleep(self.collection_interval)
                    
                except Exception as e:
                    logger.error(f"Error in metrics collection: {str(e)}")
                    time.sleep(self.collection_interval)
        
        # Start collection thread
        collection_thread = threading.Thread(
            target=collect_task,
            daemon=True,
            name="MetricsCollection"
        )
        collection_thread.start()
        logger.debug("Metrics collection thread started")
    
    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        Collect metrics from all registered components
        
        Returns:
            Dictionary with collected metrics
        """
        timestamp = datetime.now().isoformat()
        all_metrics = {
            'timestamp': timestamp,
            'trading': self.collect_trading_metrics(),
            'performance': self.collect_performance_metrics(),
            'system': self.collect_system_metrics(),
            'api': self.collect_api_metrics()
        }
        
        logger.debug(f"Collected metrics from all components")
        return all_metrics
    
    def collect_trading_metrics(self) -> Dict[str, Any]:
        """
        Collect trading metrics
        
        Returns:
            Dictionary with trading metrics
        """
        # This would typically be collected from the trading engine
        # For now, we return an empty dict as this will be implemented later
        return {}
    
    def collect_performance_metrics(self) -> Dict[str, Any]:
        """
        Collect performance metrics
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.performance_tracker:
            return {}
            
        try:
            # Get performance metrics
            metrics = {
                'resource_usage': self.performance_tracker.get_resource_statistics(hours=1),
                'functions': self.performance_tracker.get_function_statistics(),
                'strategies': self.performance_tracker.get_strategy_statistics(),
                'api_endpoints': self.performance_tracker.get_api_statistics(),
                'queues': self.performance_tracker.get_queue_statistics()
            }
            
            # Store metrics
            self.performance_metrics = metrics
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting performance metrics: {str(e)}")
            return {}
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """
        Collect system metrics
        
        Returns:
            Dictionary with system metrics
        """
        if not self.system_monitor:
            return {}
            
        try:
            # Get system metrics
            metrics = {
                'system_info': self.system_monitor.get_system_info(),
                'health_check': self.system_monitor.health_check(),
                'connectivity': self.system_monitor.get_connectivity_status(),
                'disk_status': self.system_monitor.get_disk_status(),
                'process_status': self.system_monitor.get_process_status()
            }
            
            # Store metrics
            self.system_metrics = metrics
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            return {}
    
    def collect_api_metrics(self) -> Dict[str, Any]:
        """
        Collect API metrics
        
        Returns:
            Dictionary with API metrics
        """
        if not self.api_monitor:
            return {}
            
        try:
            # Get API metrics
            metrics = {
                'api_statistics': self.api_monitor.get_api_statistics(),
                'rate_limits': {},
                'errors': self.api_monitor.get_errors(limit=20)
            }
            
            # Get rate limits for each API
            for api_name in metrics['api_statistics'].keys():
                metrics['rate_limits'][api_name] = self.api_monitor.check_rate_limit(api_name)
                
            # Store metrics
            self.api_metrics = metrics
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting API metrics: {str(e)}")
            return {}
    
    def get_metrics(self, metric_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get collected metrics
        
        Args:
            metric_type: Optional type of metrics to get (trading, performance, system, api)
            
        Returns:
            Dictionary with requested metrics
        """
        if not self.enabled:
            return {}
            
        # Return specific metric type if requested
        if metric_type:
            if metric_type == 'trading':
                return self.trading_metrics
            elif metric_type == 'performance':
                return self.performance_metrics
            elif metric_type == 'system':
                return self.system_metrics
            elif metric_type == 'api':
                return self.api_metrics
            else:
                logger.warning(f"Unknown metric type: {metric_type}")
                return {}
                
        # Return all metrics
        return {
            'timestamp': datetime.now().isoformat(),
            'trading': self.trading_metrics,
            'performance': self.performance_metrics,
            'system': self.system_metrics,
            'api': self.api_metrics
        }
    
    def save_metrics(self) -> bool:
        """
        Save collected metrics to file
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
            
        try:
            # Current timestamp
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            
            # Create metrics file
            metrics_file = os.path.join(
                self.storage_dir,
                f'metrics_{timestamp}.json'
            )
            
            # Get all metrics
            metrics_data = self.get_metrics()
            
            # Write to file
            with open(metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
                
            logger.debug(f"Saved metrics to {metrics_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving metrics: {str(e)}")
            return False
    
    def cleanup_old_metrics(self) -> int:
        """
        Clean up old metrics files beyond the max history days
        
        Returns:
            Number of files cleaned up
        """
        if not self.enabled:
            return 0
            
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=self.max_history_days)
            
            # Get all metrics files
            files = [f for f in os.listdir(self.storage_dir) if f.startswith('metrics_') and f.endswith('.json')]
            
            # Count deleted files
            deleted_count = 0
            
            # Check each file
            for file in files:
                try:
                    # Extract date from filename (format: metrics_YYYYMMDD-HHMMSS.json)
                    date_str = file.split('_')[1].split('.')[0]
                    file_date = datetime.strptime(date_str, "%Y%m%d-%H%M%S")
                    
                    # Delete if older than cutoff
                    if file_date < cutoff_date:
                        os.remove(os.path.join(self.storage_dir, file))
                        deleted_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error processing file {file}: {str(e)}")
                    
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old metrics files")
                
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {str(e)}")
            return 0
    
    def get_metrics_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        Generate a comprehensive metrics report for the specified time range
        
        Args:
            hours: Number of hours to include in the report
            
        Returns:
            Dictionary with metrics report
        """
        if not self.enabled:
            return {'enabled': False}
            
        try:
            # Get metrics files from the past N hours
            cutoff_date = datetime.now() - timedelta(hours=hours)
            
            # Get all metrics files
            files = [f for f in os.listdir(self.storage_dir) if f.startswith('metrics_') and f.endswith('.json')]
            
            # Filter files by date
            filtered_files = []
            for file in files:
                try:
                    # Extract date from filename
                    date_str = file.split('_')[1].split('.')[0]
                    file_date = datetime.strptime(date_str, "%Y%m%d-%H%M%S")
                    
                    # Add if newer than cutoff
                    if file_date >= cutoff_date:
                        filtered_files.append((file_date, file))
                        
                except Exception:
                    pass
                    
            # Sort by date (newest first)
            filtered_files.sort(reverse=True)
            
            # Load metrics data
            all_metrics = []
            for _, file in filtered_files:
                try:
                    with open(os.path.join(self.storage_dir, file), 'r') as f:
                        metrics = json.load(f)
                        all_metrics.append(metrics)
                except Exception:
                    pass
                    
            # If no metrics found
            if not all_metrics:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'timeframe': f'last {hours} hours',
                    'status': 'no_data',
                    'metrics_files': len(filtered_files)
                }
                
            # Generate report
            report = {
                'timestamp': datetime.now().isoformat(),
                'timeframe': f'last {hours} hours',
                'status': 'success',
                'metrics_files': len(filtered_files),
                'latest': all_metrics[0],
                'summary': self._generate_metrics_summary(all_metrics)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating metrics report: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'timeframe': f'last {hours} hours',
                'status': 'error',
                'error': str(e)
            }
    
    def _generate_metrics_summary(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of metrics over time
        
        Args:
            metrics_list: List of metrics dictionaries
            
        Returns:
            Dictionary with metrics summary
        """
        # Initialize summary
        summary = {
            'system': {},
            'performance': {},
            'api': {}
        }
        
        # Extract system metrics
        system_cpu = []
        system_memory = []
        system_disk = {}
        
        # Extract performance metrics
        perf_cpu = []
        perf_memory = []
        
        # Extract API metrics
        api_calls = {}
        api_errors = 0
        
        # Process each metrics snapshot
        for metrics in metrics_list:
            # Process system metrics
            if 'system' in metrics and metrics['system']:
                system = metrics['system']
                
                # Process health check
                if 'health_check' in system and system['health_check']:
                    health = system['health_check']
                    
                    # Get CPU and memory metrics
                    if 'metrics' in health:
                        if 'cpu_percent' in health['metrics']:
                            system_cpu.append(health['metrics']['cpu_percent'])
                        if 'memory_percent' in health['metrics']:
                            system_memory.append(health['metrics']['memory_percent'])
                            
                # Process disk status
                if 'disk_status' in system and system['disk_status']:
                    for mount, disk in system['disk_status'].items():
                        if mount not in system_disk:
                            system_disk[mount] = []
                        system_disk[mount].append(disk.get('percent', 0))
                        
            # Process performance metrics
            if 'performance' in metrics and metrics['performance']:
                perf = metrics['performance']
                
                # Process resource usage
                if 'resource_usage' in perf and perf['resource_usage']:
                    resource = perf['resource_usage']
                    
                    # Get CPU metrics
                    if 'cpu_percent' in resource and 'mean' in resource['cpu_percent']:
                        perf_cpu.append(resource['cpu_percent']['mean'])
                        
                    # Get memory metrics
                    if 'memory_percent' in resource and 'mean' in resource['memory_percent']:
                        perf_memory.append(resource['memory_percent']['mean'])
                        
            # Process API metrics
            if 'api' in metrics and metrics['api']:
                api = metrics['api']
                
                # Process API statistics
                if 'api_statistics' in api and api['api_statistics']:
                    for api_name, endpoints in api['api_statistics'].items():
                        for endpoint, stats in endpoints.items():
                            key = f"{api_name}_{endpoint}"
                            if key not in api_calls:
                                api_calls[key] = []
                            api_calls[key].append(stats.get('count', 0))
                            
                # Count API errors
                if 'errors' in api and api['errors']:
                    api_errors += len(api['errors'])
                    
        # Calculate system summary
        if system_cpu:
            summary['system']['cpu_percent'] = {
                'mean': np.mean(system_cpu),
                'max': max(system_cpu),
                'min': min(system_cpu)
            }
            
        if system_memory:
            summary['system']['memory_percent'] = {
                'mean': np.mean(system_memory),
                'max': max(system_memory),
                'min': min(system_memory)
            }
            
        summary['system']['disk_percent'] = {}
        for mount, percents in system_disk.items():
            if percents:
                summary['system']['disk_percent'][mount] = {
                    'mean': np.mean(percents),
                    'max': max(percents),
                    'min': min(percents)
                }
                
        # Calculate performance summary
        if perf_cpu:
            summary['performance']['cpu_percent'] = {
                'mean': np.mean(perf_cpu),
                'max': max(perf_cpu),
                'min': min(perf_cpu)
            }
            
        if perf_memory:
            summary['performance']['memory_percent'] = {
                'mean': np.mean(perf_memory),
                'max': max(perf_memory),
                'min': min(perf_memory)
            }
            
        # Calculate API summary
        summary['api']['endpoints'] = {}
        for endpoint, counts in api_calls.items():
            if counts:
                summary['api']['endpoints'][endpoint] = {
                    'mean': np.mean(counts),
                    'max': max(counts),
                    'min': min(counts),
                    'total': sum(counts)
                }
                
        summary['api']['total_errors'] = api_errors
        
        return summary
