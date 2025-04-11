"""
Connection Monitor for the Forex Trading Bot
Monitors and verifies connectivity with critical endpoints
"""

import socket
import time
import threading
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
import ssl

from .logger import get_logger

logger = get_logger("ConnectionMonitor")


class ConnectionMonitor:
    """
    Monitors connection status to critical endpoints like MT5 server, broker APIs,
    and other external services
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the connection monitor
        
        Args:
            config: Configuration dictionary with connection monitoring settings
        """
        self.config = config
        self.enabled = config.get('connection_monitoring_enabled', True)
        self.check_interval = config.get('check_interval_seconds', 60)
        self.history_size = config.get('history_size', 100)
        self.timeout = config.get('connection_timeout_seconds', 5)
        
        # Configure endpoints to monitor
        self.endpoints = config.get('endpoints', {})
        if not self.endpoints:
            self.endpoints = self._get_default_endpoints()
            
        # Initialize status history
        self.status_history = {}
        for endpoint_id in self.endpoints:
            self.status_history[endpoint_id] = deque(maxlen=self.history_size)
            
        # Track current status
        self.current_status = {}
        
        # Track downtime
        self.downtime_start = {}
        
        # Set up alert manager
        self.alert_manager = None
        
        # Start monitoring
        if self.enabled:
            self._start_monitoring()
            
        logger.info(f"Connection monitor initialized with {len(self.endpoints)} endpoints")
    
    def _get_default_endpoints(self) -> Dict[str, Dict[str, Any]]:
        """
        Get default endpoints to monitor
        
        Returns:
            Dictionary of default endpoints
        """
        return {
            "mt5_server": {
                "name": "MT5 Trading Server",
                "type": "tcp",
                "host": "127.0.0.1",  # Replace with actual MT5 server
                "port": 443,
                "critical": True
            },
            "broker_api": {
                "name": "Broker API",
                "type": "http",
                "url": "https://api.broker.com/status",  # Replace with actual broker API
                "method": "GET",
                "expected_status": 200,
                "critical": True
            },
            "market_data_api": {
                "name": "Market Data API",
                "type": "http",
                "url": "https://api.marketdata.com/health",  # Replace with actual data API
                "method": "GET",
                "expected_status": 200,
                "critical": True
            },
            "dns_resolver": {
                "name": "DNS Resolver",
                "type": "dns",
                "host": "8.8.8.8",
                "critical": False
            },
            "internet_connectivity": {
                "name": "Internet Connectivity",
                "type": "http",
                "url": "https://www.google.com",
                "method": "HEAD",
                "expected_status": 200,
                "critical": False
            }
        }
    
    def set_alert_manager(self, alert_manager: Any) -> None:
        """
        Set the alert manager for sending connectivity alerts
        
        Args:
            alert_manager: Alert manager instance
        """
        self.alert_manager = alert_manager
        logger.debug("Alert manager registered with connection monitor")
    
    def _start_monitoring(self) -> None:
        """
        Start the connection monitoring thread
        """
        def monitor_task():
            while self.enabled:
                try:
                    # Check all endpoints
                    self.check_all_endpoints()
                    
                    # Sleep for the check interval
                    time.sleep(self.check_interval)
                    
                except Exception as e:
                    logger.error(f"Error in connection monitoring: {str(e)}")
                    time.sleep(self.check_interval)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=monitor_task,
            daemon=True,
            name="ConnectionMonitoring"
        )
        monitor_thread.start()
        logger.debug("Connection monitoring thread started")
    
    def check_all_endpoints(self) -> Dict[str, Dict[str, Any]]:
        """
        Check all configured endpoints and update status
        
        Returns:
            Dictionary with status for all endpoints
        """
        status = {}
        
        for endpoint_id, endpoint_config in self.endpoints.items():
            endpoint_status = self.check_endpoint(endpoint_id)
            status[endpoint_id] = endpoint_status
            
        # Update current status
        self.current_status = status
        
        return status
    
    def check_endpoint(self, endpoint_id: str) -> Dict[str, Any]:
        """
        Check a specific endpoint
        
        Args:
            endpoint_id: ID of the endpoint to check
            
        Returns:
            Status dictionary for the endpoint
        """
        if endpoint_id not in self.endpoints:
            logger.warning(f"Unknown endpoint: {endpoint_id}")
            return {"status": "unknown", "error": "Unknown endpoint"}
            
        endpoint_config = self.endpoints[endpoint_id]
        endpoint_type = endpoint_config.get("type", "http")
        
        # Initialize status
        status = {
            "id": endpoint_id,
            "name": endpoint_config.get("name", endpoint_id),
            "timestamp": datetime.now().isoformat(),
            "type": endpoint_type,
            "status": "unknown",
            "latency_ms": 0,
            "error": None
        }
        
        # Check endpoint based on type
        try:
            start_time = time.time()
            
            if endpoint_type == "http":
                self._check_http_endpoint(endpoint_config, status)
            elif endpoint_type == "tcp":
                self._check_tcp_endpoint(endpoint_config, status)
            elif endpoint_type == "dns":
                self._check_dns_endpoint(endpoint_config, status)
            else:
                status["status"] = "error"
                status["error"] = f"Unsupported endpoint type: {endpoint_type}"
                
            # Calculate latency
            status["latency_ms"] = int((time.time() - start_time) * 1000)
            
        except Exception as e:
            status["status"] = "error"
            status["error"] = str(e)
            
        # Update status history
        if endpoint_id in self.status_history:
            self.status_history[endpoint_id].append(status)
            
        # Track downtime
        if status["status"] != "ok":
            if endpoint_id not in self.downtime_start:
                self.downtime_start[endpoint_id] = datetime.now()
                
            # Send alert if critical and alert manager is available
            if endpoint_config.get("critical", False) and self.alert_manager:
                try:
                    # Only alert if this is a new error
                    previous_status = None
                    if endpoint_id in self.current_status:
                        previous_status = self.current_status[endpoint_id]["status"]
                        
                    if previous_status in ["ok", "unknown"]:
                        self.alert_manager.send_alert(
                            level="error",
                            title=f"Connection Lost: {status['name']}",
                            message=f"Lost connection to {status['name']}. Error: {status['error']}",
                            source="connection_monitor",
                            data={
                                "endpoint_id": endpoint_id,
                                "endpoint_type": endpoint_type,
                                "status": status["status"],
                                "timestamp": status["timestamp"]
                            }
                        )
                except Exception as e:
                    logger.error(f"Error sending connection alert: {str(e)}")
        else:
            # If status is OK and was previously down, send recovery alert
            if endpoint_id in self.downtime_start:
                downtime_duration = datetime.now() - self.downtime_start[endpoint_id]
                
                # Send recovery alert if critical and alert manager is available
                if endpoint_config.get("critical", False) and self.alert_manager:
                    try:
                        # Check if previous status was an error
                        previous_status = None
                        if endpoint_id in self.current_status:
                            previous_status = self.current_status[endpoint_id]["status"]
                            
                        if previous_status not in ["ok", "unknown"]:
                            self.alert_manager.send_alert(
                                level="info",
                                title=f"Connection Restored: {status['name']}",
                                message=f"Connection to {status['name']} restored after {downtime_duration.total_seconds():.1f} seconds",
                                source="connection_monitor",
                                data={
                                    "endpoint_id": endpoint_id,
                                    "endpoint_type": endpoint_type,
                                    "downtime_seconds": downtime_duration.total_seconds(),
                                    "timestamp": status["timestamp"]
                                }
                            )
                    except Exception as e:
                        logger.error(f"Error sending connection recovery alert: {str(e)}")
                
                # Clear downtime tracking
                del self.downtime_start[endpoint_id]
                
        return status
    
    def _check_http_endpoint(self, endpoint_config: Dict[str, Any], status: Dict[str, Any]) -> None:
        """
        Check an HTTP endpoint
        
        Args:
            endpoint_config: Endpoint configuration
            status: Status dictionary to update
        """
        url = endpoint_config.get("url")
        method = endpoint_config.get("method", "GET")
        headers = endpoint_config.get("headers", {})
        expected_status = endpoint_config.get("expected_status", 200)
        
        if not url:
            status["status"] = "error"
            status["error"] = "No URL configured"
            return
            
        # Make request
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=self.timeout, verify=endpoint_config.get("verify_ssl", True))
        elif method.upper() == "HEAD":
            response = requests.head(url, headers=headers, timeout=self.timeout, verify=endpoint_config.get("verify_ssl", True))
        elif method.upper() == "POST":
            data = endpoint_config.get("data", {})
            response = requests.post(url, json=data, headers=headers, timeout=self.timeout, verify=endpoint_config.get("verify_ssl", True))
        else:
            status["status"] = "error"
            status["error"] = f"Unsupported HTTP method: {method}"
            return
            
        # Check response
        if response.status_code == expected_status:
            status["status"] = "ok"
        else:
            status["status"] = "error"
            status["error"] = f"Unexpected status code: {response.status_code}, expected: {expected_status}"
            
        # Add additional info
        status["http_status"] = response.status_code
    
    def _check_tcp_endpoint(self, endpoint_config: Dict[str, Any], status: Dict[str, Any]) -> None:
        """
        Check a TCP endpoint
        
        Args:
            endpoint_config: Endpoint configuration
            status: Status dictionary to update
        """
        host = endpoint_config.get("host")
        port = endpoint_config.get("port")
        
        if not host or not port:
            status["status"] = "error"
            status["error"] = "No host or port configured"
            return
            
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        
        # Connect
        try:
            sock.connect((host, port))
            
            # If SSL, try to establish SSL connection
            if endpoint_config.get("ssl", False):
                context = ssl.create_default_context()
                if not endpoint_config.get("verify_ssl", True):
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    
                ssl_sock = context.wrap_socket(sock, server_hostname=host)
                ssl_sock.close()
            else:
                sock.close()
                
            status["status"] = "ok"
            
        except socket.timeout:
            status["status"] = "error"
            status["error"] = "Connection timed out"
        except socket.error as e:
            status["status"] = "error"
            status["error"] = f"Socket error: {str(e)}"
        except ssl.SSLError as e:
            status["status"] = "error"
            status["error"] = f"SSL error: {str(e)}"
        finally:
            try:
                sock.close()
            except:
                pass
    
    def _check_dns_endpoint(self, endpoint_config: Dict[str, Any], status: Dict[str, Any]) -> None:
        """
        Check a DNS endpoint
        
        Args:
            endpoint_config: Endpoint configuration
            status: Status dictionary to update
        """
        host = endpoint_config.get("host")
        
        if not host:
            status["status"] = "error"
            status["error"] = "No host configured"
            return
            
        try:
            # Try to resolve a domain
            socket.gethostbyname("google.com")
            status["status"] = "ok"
        except socket.error as e:
            status["status"] = "error"
            status["error"] = f"DNS resolution error: {str(e)}"
    
    def get_status(self, endpoint_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current status for endpoints
        
        Args:
            endpoint_id: Optional endpoint ID to get status for
            
        Returns:
            Status dictionary
        """
        if not self.enabled:
            return {"enabled": False}
            
        if endpoint_id:
            if endpoint_id in self.current_status:
                return self.current_status[endpoint_id]
            else:
                return {"error": f"Unknown endpoint: {endpoint_id}"}
                
        return self.current_status
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current status
        
        Returns:
            Status summary dictionary
        """
        if not self.enabled:
            return {"enabled": False}
            
        # Count status types
        status_counts = {"ok": 0, "error": 0, "unknown": 0}
        critical_status = "ok"
        non_critical_status = "ok"
        
        for endpoint_id, status in self.current_status.items():
            current_status = status.get("status", "unknown")
            if current_status in status_counts:
                status_counts[current_status] += 1
                
            # Update critical status
            if self.endpoints[endpoint_id].get("critical", False):
                if current_status != "ok":
                    critical_status = "error"
            else:
                if current_status != "ok":
                    non_critical_status = "error"
                    
        # Overall status
        overall_status = "ok"
        if critical_status != "ok":
            overall_status = "error"
        elif non_critical_status != "ok":
            overall_status = "warning"
            
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "critical_status": critical_status,
            "non_critical_status": non_critical_status,
            "status_counts": status_counts,
            "endpoints_count": len(self.current_status)
        }
    
    def get_history(self, endpoint_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get status history for an endpoint
        
        Args:
            endpoint_id: Endpoint ID
            limit: Maximum number of history entries to return
            
        Returns:
            List of status dictionaries
        """
        if not self.enabled:
            return []
            
        if endpoint_id not in self.status_history:
            return []
            
        # Convert deque to list and apply limit
        history = list(self.status_history[endpoint_id])
        return history[-limit:]
    
    def get_uptime_percentage(self, endpoint_id: str, hours: int = 24) -> float:
        """
        Calculate uptime percentage for an endpoint
        
        Args:
            endpoint_id: Endpoint ID
            hours: Number of hours to calculate uptime for
            
        Returns:
            Uptime percentage (0-100)
        """
        if not self.enabled or endpoint_id not in self.status_history:
            return 0.0
            
        # Get history for the endpoint
        history = list(self.status_history[endpoint_id])
        
        # Filter by time range
        cutoff_time = datetime.now() - timedelta(hours=hours)
        filtered_history = []
        
        for entry in history:
            try:
                entry_time = datetime.fromisoformat(entry["timestamp"])
                if entry_time >= cutoff_time:
                    filtered_history.append(entry)
            except:
                pass
                
        # If no history in time range
        if not filtered_history:
            return 0.0
            
        # Count success entries
        success_count = sum(1 for entry in filtered_history if entry["status"] == "ok")
        
        # Calculate percentage
        return (success_count / len(filtered_history)) * 100.0
    
    def add_endpoint(self, endpoint_id: str, endpoint_config: Dict[str, Any]) -> bool:
        """
        Add a new endpoint to monitor
        
        Args:
            endpoint_id: Endpoint ID
            endpoint_config: Endpoint configuration
            
        Returns:
            True if added successfully, False otherwise
        """
        if endpoint_id in self.endpoints:
            logger.warning(f"Endpoint already exists: {endpoint_id}")
            return False
            
        # Validate config
        endpoint_type = endpoint_config.get("type")
        if not endpoint_type:
            logger.warning(f"No endpoint type specified for {endpoint_id}")
            return False
            
        if endpoint_type == "http" and not endpoint_config.get("url"):
            logger.warning(f"No URL specified for HTTP endpoint {endpoint_id}")
            return False
            
        if endpoint_type == "tcp" and (not endpoint_config.get("host") or not endpoint_config.get("port")):
            logger.warning(f"No host or port specified for TCP endpoint {endpoint_id}")
            return False
            
        if endpoint_type == "dns" and not endpoint_config.get("host"):
            logger.warning(f"No host specified for DNS endpoint {endpoint_id}")
            return False
            
        # Add endpoint
        self.endpoints[endpoint_id] = endpoint_config
        self.status_history[endpoint_id] = deque(maxlen=self.history_size)
        
        # Check endpoint immediately
        self.check_endpoint(endpoint_id)
        
        logger.info(f"Added new endpoint: {endpoint_id}")
        return True
    
    def remove_endpoint(self, endpoint_id: str) -> bool:
        """
        Remove an endpoint from monitoring
        
        Args:
            endpoint_id: Endpoint ID
            
        Returns:
            True if removed successfully, False otherwise
        """
        if endpoint_id not in self.endpoints:
            logger.warning(f"Unknown endpoint: {endpoint_id}")
            return False
            
        # Remove endpoint
        del self.endpoints[endpoint_id]
        
        # Remove from status history
        if endpoint_id in self.status_history:
            del self.status_history[endpoint_id]
            
        # Remove from current status
        if endpoint_id in self.current_status:
            del self.current_status[endpoint_id]
            
        # Remove from downtime tracking
        if endpoint_id in self.downtime_start:
            del self.downtime_start[endpoint_id]
            
        logger.info(f"Removed endpoint: {endpoint_id}")
        return True
