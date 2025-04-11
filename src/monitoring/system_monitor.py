"""
System monitoring for the Forex Trading Bot
Tracks system health, resource usage, and overall performance
"""

import os
import sys
import time
import threading
import platform
import socket
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
import logging

from .logger import get_logger

logger = get_logger("SystemMonitor")


class SystemMonitor:
    """
    Monitors system resources, network connectivity, and overall health
    of the Forex Trading Bot environment
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the system monitor
        
        Args:
            config: Configuration dictionary with system monitoring settings
        """
        self.config = config
        self.enabled = config.get('system_monitoring_enabled', True)
        self.check_interval = config.get('check_interval_seconds', 60)
        self.log_file = config.get('system_log_file', 'data/logs/system_health.log')
        self.alert_thresholds = config.get('alert_thresholds', {
            'cpu_percent': 80,
            'memory_percent': 80,
            'disk_percent': 85,
            'network_error_rate': 0.05
        })
        
        # Initialize metrics storage
        self.system_metrics = deque(maxlen=config.get('max_history_items', 1000))
        self.network_metrics = deque(maxlen=config.get('max_history_items', 1000))
        self.disk_metrics = deque(maxlen=config.get('max_history_items', 1000))
        self.process_metrics = deque(maxlen=config.get('max_history_items', 1000))
        
        # Initialize connectivity checks
        self.connectivity_endpoints = config.get('connectivity_endpoints', [
            {'name': 'MT5 Server', 'host': 'trader.deriv.com', 'port': 443},
            {'name': 'API Server', 'host': '127.0.0.1', 'port': 8000},
            {'name': 'Internet', 'host': '8.8.8.8', 'port': 53}
        ])
        
        # Store platform info
        self.platform_info = self._get_platform_info()
        
        # Create log directory
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Initialize process object
        self.process = psutil.Process(os.getpid())
        
        # Start monitoring thread if enabled
        if self.enabled:
            self._start_monitoring()
            
        logger.info("System monitor initialized")
    
    def _start_monitoring(self) -> None:
        """
        Start the background monitoring thread
        """
        def monitor_task():
            while self.enabled:
                try:
                    # Collect system metrics
                    self.collect_system_metrics()
                    
                    # Check connectivity
                    self.check_connectivity()
                    
                    # Check disk usage
                    self.check_disk_usage()
                    
                    # Check process health
                    self.check_process_health()
                    
                    # Save metrics periodically (every 10 intervals)
                    if len(self.system_metrics) % 10 == 0:
                        self.save_metrics()
                    
                    # Sleep for the check interval
                    time.sleep(self.check_interval)
                    
                except Exception as e:
                    logger.error(f"Error in system monitoring: {str(e)}")
                    time.sleep(self.check_interval)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=monitor_task,
            daemon=True,
            name="SystemMonitoring"
        )
        monitor_thread.start()
        logger.debug("System monitoring thread started")
    
    def _get_platform_info(self) -> Dict[str, Any]:
        """
        Get information about the platform the bot is running on
        
        Returns:
            Dictionary with platform information
        """
        info = {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'node': platform.node(),
            'hostname': socket.gethostname()
        }
        
        # Add more detailed information based on the platform
        if platform.system() == 'Windows':
            try:
                import wmi
                c = wmi.WMI()
                system_info = c.Win32_ComputerSystem()[0]
                os_info = c.Win32_OperatingSystem()[0]
                
                info.update({
                    'manufacturer': system_info.Manufacturer,
                    'model': system_info.Model,
                    'os_name': os_info.Caption,
                    'installed_ram': round(int(system_info.TotalPhysicalMemory) / (1024**3), 2)
                })
            except Exception:
                # If WMI fails, we'll just use the basic info
                pass
        
        # Get CPU core information
        try:
            info['cpu_cores_physical'] = psutil.cpu_count(logical=False)
            info['cpu_cores_logical'] = psutil.cpu_count(logical=True)
        except Exception:
            pass
            
        # Get memory information
        try:
            memory = psutil.virtual_memory()
            info['total_memory_gb'] = round(memory.total / (1024**3), 2)
        except Exception:
            pass
            
        return info
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """
        Collect and store system-wide performance metrics
        
        Returns:
            Dictionary with collected metrics
        """
        if not self.enabled:
            return {}
            
        try:
            # Get current time
            timestamp = datetime.now()
            
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.5)
            cpu_freq = psutil.cpu_freq()
            cpu_frequency = cpu_freq.current if cpu_freq else None
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = round(memory.used / (1024**3), 2)
            memory_available_gb = round(memory.available / (1024**3), 2)
            
            # Get swap usage
            swap = psutil.swap_memory()
            swap_percent = swap.percent
            
            # Get network stats
            network = psutil.net_io_counters()
            
            # Create metrics record
            metrics = {
                'timestamp': timestamp.isoformat(),
                'cpu_percent': cpu_percent,
                'cpu_frequency': cpu_frequency,
                'memory_percent': memory_percent,
                'memory_used_gb': memory_used_gb,
                'memory_available_gb': memory_available_gb,
                'swap_percent': swap_percent,
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'network_packets_sent': network.packets_sent,
                'network_packets_recv': network.packets_recv,
                'network_errin': network.errin,
                'network_errout': network.errout
            }
            
            # Check if we have previous metrics to calculate rates
            if self.system_metrics:
                prev_metrics = self.system_metrics[-1]
                prev_time = datetime.fromisoformat(prev_metrics['timestamp'])
                time_diff = (timestamp - prev_time).total_seconds()
                
                if time_diff > 0:
                    # Calculate network rates
                    bytes_sent_rate = (network.bytes_sent - prev_metrics['network_bytes_sent']) / time_diff
                    bytes_recv_rate = (network.bytes_recv - prev_metrics['network_bytes_recv']) / time_diff
                    
                    # Add calculated rates
                    metrics['network_bytes_sent_per_sec'] = round(bytes_sent_rate, 2)
                    metrics['network_bytes_recv_per_sec'] = round(bytes_recv_rate, 2)
                    
                    # Calculate error rates
                    errors_in = network.errin - prev_metrics['network_errin']
                    errors_out = network.errout - prev_metrics['network_errout']
                    packets_in = network.packets_recv - prev_metrics['network_packets_recv']
                    packets_out = network.packets_sent - prev_metrics['network_packets_sent']
                    
                    # Avoid division by zero
                    if packets_in > 0:
                        metrics['network_error_rate_in'] = errors_in / packets_in
                    else:
                        metrics['network_error_rate_in'] = 0
                        
                    if packets_out > 0:
                        metrics['network_error_rate_out'] = errors_out / packets_out
                    else:
                        metrics['network_error_rate_out'] = 0
            
            # Store metrics
            self.system_metrics.append(metrics)
            
            # Check for alertable conditions
            self._check_system_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            return {}
    
    def check_connectivity(self) -> List[Dict[str, Any]]:
        """
        Check connectivity to important endpoints
        
        Returns:
            List of dictionaries with connectivity check results
        """
        if not self.enabled:
            return []
            
        results = []
        timestamp = datetime.now().isoformat()
        
        for endpoint in self.connectivity_endpoints:
            try:
                name = endpoint['name']
                host = endpoint['host']
                port = endpoint['port']
                timeout = endpoint.get('timeout', 5)
                
                # Create socket and attempt to connect
                start_time = time.time()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                
                # Attempt connection
                result = sock.connect_ex((host, port))
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                
                # Close socket
                sock.close()
                
                # Determine status
                status = "OK" if result == 0 else "FAIL"
                
                # Create result record
                check_result = {
                    'timestamp': timestamp,
                    'name': name,
                    'host': host,
                    'port': port,
                    'status': status,
                    'response_time_ms': round(response_time, 2) if status == "OK" else None,
                    'error_code': result if result != 0 else None
                }
                
                # Store result
                self.network_metrics.append(check_result)
                results.append(check_result)
                
                # Log result
                if status == "OK":
                    logger.debug(f"Connectivity check: {name} - OK ({round(response_time, 2)} ms)")
                else:
                    logger.warning(f"Connectivity check: {name} - FAILED (Error code: {result})")
                    
            except Exception as e:
                # Create error result
                error_result = {
                    'timestamp': timestamp,
                    'name': endpoint['name'],
                    'host': endpoint['host'],
                    'port': endpoint['port'],
                    'status': "ERROR",
                    'response_time_ms': None,
                    'error': str(e)
                }
                
                # Store and log error
                self.network_metrics.append(error_result)
                results.append(error_result)
                logger.error(f"Connectivity check error ({endpoint['name']}): {str(e)}")
        
        return results
    
    def check_disk_usage(self) -> Dict[str, Dict[str, Any]]:
        """
        Check disk usage on all relevant drives
        
        Returns:
            Dictionary with disk usage information
        """
        if not self.enabled:
            return {}
            
        result = {}
        timestamp = datetime.now().isoformat()
        
        try:
            # Get all mounted disk partitions
            partitions = psutil.disk_partitions()
            
            for partition in partitions:
                # Skip non-fixed drives on Windows
                if platform.system() == "Windows" and "fixed" not in partition.opts:
                    continue
                    
                # Get disk usage
                usage = psutil.disk_usage(partition.mountpoint)
                
                # Create result record
                disk_info = {
                    'timestamp': timestamp,
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'filesystem': partition.fstype,
                    'total_gb': round(usage.total / (1024**3), 2),
                    'used_gb': round(usage.used / (1024**3), 2),
                    'free_gb': round(usage.free / (1024**3), 2),
                    'percent': usage.percent
                }
                
                # Store result
                self.disk_metrics.append(disk_info)
                result[partition.mountpoint] = disk_info
                
                # Check for alert threshold
                if usage.percent >= self.alert_thresholds.get('disk_percent', 85):
                    logger.warning(f"Disk usage alert: {partition.mountpoint} at {usage.percent}% usage")
                    
        except Exception as e:
            logger.error(f"Error checking disk usage: {str(e)}")
            
        return result
    
    def check_process_health(self) -> Dict[str, Any]:
        """
        Check health of the current process
        
        Returns:
            Dictionary with process health information
        """
        if not self.enabled:
            return {}
            
        try:
            timestamp = datetime.now().isoformat()
            
            # Get process info
            process = self.process
            
            # Get CPU and memory usage
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            # Get process status
            status = process.status()
            
            # Get thread count
            thread_count = len(process.threads())
            
            # Get open files
            try:
                open_files = len(process.open_files())
            except Exception:
                open_files = -1
                
            # Get connections
            try:
                connections = len(process.connections())
            except Exception:
                connections = -1
                
            # Create result record
            process_info = {
                'timestamp': timestamp,
                'pid': process.pid,
                'name': process.name(),
                'status': status,
                'cpu_percent': cpu_percent,
                'memory_rss_mb': round(memory_info.rss / (1024**2), 2),
                'memory_vms_mb': round(memory_info.vms / (1024**2), 2),
                'memory_percent': memory_percent,
                'thread_count': thread_count,
                'open_files': open_files,
                'connections': connections,
                'create_time': datetime.fromtimestamp(process.create_time()).isoformat()
            }
            
            # Calculate uptime
            process_info['uptime_seconds'] = (datetime.now() - datetime.fromtimestamp(process.create_time())).total_seconds()
            
            # Store result
            self.process_metrics.append(process_info)
            
            # Check for alert conditions
            if cpu_percent >= self.alert_thresholds.get('cpu_percent', 80):
                logger.warning(f"Process CPU usage alert: {cpu_percent}%")
                
            if memory_percent >= self.alert_thresholds.get('memory_percent', 80):
                logger.warning(f"Process memory usage alert: {memory_percent}%")
                
            return process_info
            
        except Exception as e:
            logger.error(f"Error checking process health: {str(e)}")
            return {}
    
    def _check_system_alerts(self, metrics: Dict[str, Any]) -> None:
        """
        Check for alertable conditions in system metrics
        
        Args:
            metrics: Dictionary with system metrics
        """
        # Check CPU usage
        if metrics.get('cpu_percent', 0) >= self.alert_thresholds.get('cpu_percent', 80):
            logger.warning(f"System CPU usage alert: {metrics['cpu_percent']}%")
            
        # Check memory usage
        if metrics.get('memory_percent', 0) >= self.alert_thresholds.get('memory_percent', 80):
            logger.warning(f"System memory usage alert: {metrics['memory_percent']}%")
            
        # Check swap usage
        if metrics.get('swap_percent', 0) >= self.alert_thresholds.get('swap_percent', 80):
            logger.warning(f"System swap usage alert: {metrics['swap_percent']}%")
            
        # Check network error rates
        error_rate_threshold = self.alert_thresholds.get('network_error_rate', 0.05)
        
        if metrics.get('network_error_rate_in', 0) >= error_rate_threshold:
            logger.warning(f"Network input error rate alert: {metrics['network_error_rate_in']:.4f}")
            
        if metrics.get('network_error_rate_out', 0) >= error_rate_threshold:
            logger.warning(f"Network output error rate alert: {metrics['network_error_rate_out']:.4f}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get comprehensive system information
        
        Returns:
            Dictionary with system information
        """
        info = self.platform_info.copy()
        
        try:
            # Add current boot time
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            info['boot_time'] = boot_time.isoformat()
            info['uptime_seconds'] = (datetime.now() - boot_time).total_seconds()
            
            # Add current performance metrics
            if self.system_metrics:
                latest_metrics = self.system_metrics[-1]
                info['current_cpu_percent'] = latest_metrics.get('cpu_percent')
                info['current_memory_percent'] = latest_metrics.get('memory_percent')
                
            # Add connectivity status
            if self.network_metrics:
                connectivity = {}
                for metric in list(self.network_metrics)[-len(self.connectivity_endpoints):]:
                    if 'name' in metric:
                        connectivity[metric['name']] = {
                            'status': metric.get('status'),
                            'response_time_ms': metric.get('response_time_ms')
                        }
                info['connectivity'] = connectivity
                
            # Add disk information
            if self.disk_metrics:
                disks = {}
                for metric in list(self.disk_metrics)[-10:]:  # Last 10 entries
                    if 'mountpoint' in metric:
                        disks[metric['mountpoint']] = {
                            'total_gb': metric.get('total_gb'),
                            'free_gb': metric.get('free_gb'),
                            'percent': metric.get('percent')
                        }
                info['disks'] = disks
                
            return info
            
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return info
    
    def get_system_metrics(self, hours: int = 1) -> List[Dict[str, Any]]:
        """
        Get system metrics for the specified time range
        
        Args:
            hours: Number of hours to include in metrics
            
        Returns:
            List of system metric dictionaries
        """
        if not self.enabled:
            return []
            
        if not self.system_metrics:
            return []
            
        # Filter metrics by time
        start_time = datetime.now() - timedelta(hours=hours)
        
        filtered_metrics = [
            metric for metric in self.system_metrics
            if datetime.fromisoformat(metric['timestamp']) >= start_time
        ]
        
        return filtered_metrics
    
    def get_connectivity_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the latest connectivity status for all endpoints
        
        Returns:
            Dictionary with connectivity status for each endpoint
        """
        if not self.enabled or not self.network_metrics:
            return {}
            
        result = {}
        
        # Get the latest status for each endpoint
        for endpoint in self.connectivity_endpoints:
            name = endpoint['name']
            latest_status = None
            
            # Find the latest status for this endpoint
            for metric in reversed(list(self.network_metrics)):
                if metric.get('name') == name:
                    latest_status = {
                        'status': metric.get('status'),
                        'timestamp': metric.get('timestamp'),
                        'response_time_ms': metric.get('response_time_ms'),
                        'error': metric.get('error') or metric.get('error_code')
                    }
                    break
                    
            if latest_status:
                result[name] = latest_status
                
        return result
    
    def get_disk_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the latest disk status for all drives
        
        Returns:
            Dictionary with disk status for each drive
        """
        if not self.enabled or not self.disk_metrics:
            return {}
            
        result = {}
        mount_points = set()
        
        # Get all unique mount points
        for metric in self.disk_metrics:
            if 'mountpoint' in metric:
                mount_points.add(metric['mountpoint'])
                
        # Get the latest status for each mount point
        for mount_point in mount_points:
            latest_status = None
            
            # Find the latest status for this mount point
            for metric in reversed(list(self.disk_metrics)):
                if metric.get('mountpoint') == mount_point:
                    latest_status = {
                        'device': metric.get('device'),
                        'filesystem': metric.get('filesystem'),
                        'total_gb': metric.get('total_gb'),
                        'used_gb': metric.get('used_gb'),
                        'free_gb': metric.get('free_gb'),
                        'percent': metric.get('percent'),
                        'timestamp': metric.get('timestamp')
                    }
                    break
                    
            if latest_status:
                result[mount_point] = latest_status
                
        return result
    
    def get_process_status(self) -> Dict[str, Any]:
        """
        Get the latest process status
        
        Returns:
            Dictionary with process status
        """
        if not self.enabled or not self.process_metrics:
            return {}
            
        # Return the most recent process metrics
        return self.process_metrics[-1]
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a comprehensive health check of the system
        
        Returns:
            Dictionary with health check results
        """
        if not self.enabled:
            return {'status': 'disabled'}
            
        # Initialize the result
        result = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'checks': {},
            'metrics': {}
        }
        
        # Check system resources
        system_status = 'healthy'
        system_warnings = []
        
        if self.system_metrics:
            latest_metrics = self.system_metrics[-1]
            
            # CPU check
            cpu_percent = latest_metrics.get('cpu_percent', 0)
            if cpu_percent >= self.alert_thresholds.get('cpu_percent', 80):
                system_status = 'warning'
                system_warnings.append(f"High CPU usage: {cpu_percent}%")
                
            # Memory check
            memory_percent = latest_metrics.get('memory_percent', 0)
            if memory_percent >= self.alert_thresholds.get('memory_percent', 80):
                system_status = 'warning'
                system_warnings.append(f"High memory usage: {memory_percent}%")
                
            # Add metrics
            result['metrics']['cpu_percent'] = cpu_percent
            result['metrics']['memory_percent'] = memory_percent
            result['metrics']['memory_available_gb'] = latest_metrics.get('memory_available_gb')
            
        # Add system check
        result['checks']['system'] = {
            'status': system_status,
            'warnings': system_warnings
        }
        
        # Check connectivity
        connectivity_status = 'healthy'
        connectivity_warnings = []
        connectivity_details = {}
        
        for endpoint_name, status in self.get_connectivity_status().items():
            connectivity_details[endpoint_name] = {
                'status': status.get('status'),
                'response_time_ms': status.get('response_time_ms')
            }
            
            if status.get('status') != 'OK':
                connectivity_status = 'warning'
                connectivity_warnings.append(f"Connection to {endpoint_name} failed")
                
        # Add connectivity check
        result['checks']['connectivity'] = {
            'status': connectivity_status,
            'warnings': connectivity_warnings,
            'details': connectivity_details
        }
        
        # Check disk usage
        disk_status = 'healthy'
        disk_warnings = []
        disk_details = {}
        
        for mount_point, status in self.get_disk_status().items():
            disk_details[mount_point] = {
                'percent': status.get('percent'),
                'free_gb': status.get('free_gb')
            }
            
            if status.get('percent', 0) >= self.alert_thresholds.get('disk_percent', 85):
                disk_status = 'warning'
                disk_warnings.append(f"Disk {mount_point} usage high: {status.get('percent')}%")
                
        # Add disk check
        result['checks']['disk'] = {
            'status': disk_status,
            'warnings': disk_warnings,
            'details': disk_details
        }
        
        # Check process health
        process_status = 'healthy'
        process_warnings = []
        
        if self.process_metrics:
            latest_process = self.process_metrics[-1]
            
            # Process CPU check
            proc_cpu_percent = latest_process.get('cpu_percent', 0)
            if proc_cpu_percent >= self.alert_thresholds.get('cpu_percent', 80):
                process_status = 'warning'
                process_warnings.append(f"Process CPU usage high: {proc_cpu_percent}%")
                
            # Process memory check
            proc_memory_percent = latest_process.get('memory_percent', 0)
            if proc_memory_percent >= self.alert_thresholds.get('memory_percent', 80):
                process_status = 'warning'
                process_warnings.append(f"Process memory usage high: {proc_memory_percent}%")
                
            # Add process metrics
            result['metrics']['process_cpu_percent'] = proc_cpu_percent
            result['metrics']['process_memory_percent'] = proc_memory_percent
            result['metrics']['process_memory_mb'] = latest_process.get('memory_rss_mb')
            result['metrics']['process_threads'] = latest_process.get('thread_count')
            result['metrics']['process_uptime_seconds'] = latest_process.get('uptime_seconds')
            
        # Add process check
        result['checks']['process'] = {
            'status': process_status,
            'warnings': process_warnings
        }
        
        # Set overall status
        for check in result['checks'].values():
            if check['status'] == 'critical':
                result['status'] = 'critical'
                break
            elif check['status'] == 'warning' and result['status'] != 'critical':
                result['status'] = 'warning'
                
        return result
    
    def save_metrics(self) -> bool:
        """
        Save system metrics to file
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
            
        try:
            # Create system logs directory
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            
            # Current timestamp
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            
            # Create metrics file
            metrics_file = os.path.join(
                os.path.dirname(self.log_file),
                f'system_metrics_{timestamp}.json'
            )
            
            # Create metrics data
            metrics_data = {
                'timestamp': datetime.now().isoformat(),
                'platform_info': self.platform_info,
                'system_metrics': list(self.system_metrics),
                'network_metrics': list(self.network_metrics),
                'disk_metrics': list(self.disk_metrics),
                'process_metrics': list(self.process_metrics),
                'health_check': self.health_check()
            }
            
            # Write to file
            with open(metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
                
            logger.debug(f"Saved system metrics to {metrics_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving system metrics: {str(e)}")
            return False
