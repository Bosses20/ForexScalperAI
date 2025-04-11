"""
UPnP Helper for automatic port forwarding

This module provides utility functions to set up automatic port forwarding
using UPnP, making the API server accessible from external networks.
"""

import socket
import threading
import time
import miniupnpc
from loguru import logger
from typing import Optional, Tuple, List, Dict, Any

class UPnPHelper:
    """
    Helper class for UPnP port forwarding
    """
    
    def __init__(self, service_name: str = "Forex Trading Bot"):
        """
        Initialize the UPnP helper
        
        Args:
            service_name: Name to use for port mapping description
        """
        self.upnp = miniupnpc.UPnP()
        self.service_name = service_name
        self.mapped_ports: Dict[int, str] = {}  # port -> protocol
        self.local_ip = None
        self.external_ip = None
        self.is_available = False
        self._setup_lock = threading.Lock()
        
        # Start monitoring thread
        self._stop_monitor = threading.Event()
        self._monitor_thread = None

    def discover(self) -> bool:
        """
        Discover UPnP devices on the network
        
        Returns:
            True if UPnP is available, False otherwise
        """
        try:
            logger.info("Discovering UPnP devices...")
            
            # Discover UPnP devices
            self.upnp.discoverdelay = 200  # milliseconds
            discover_result = self.upnp.discover()
            
            if discover_result > 0:
                # Select the first IGD (Internet Gateway Device)
                self.upnp.selectigd()
                
                # Get the external IP address
                self.external_ip = self.upnp.externalipaddress()
                
                # Get the local IP address
                self.local_ip = self._get_local_ip()
                
                logger.info(f"UPnP device found: {self.upnp.statusinfo()}")
                logger.info(f"External IP: {self.external_ip}")
                logger.info(f"Local IP: {self.local_ip}")
                
                self.is_available = True
                return True
            else:
                logger.warning("No UPnP devices found")
                self.is_available = False
                return False
                
        except Exception as e:
            logger.error(f"Error discovering UPnP devices: {str(e)}")
            self.is_available = False
            return False

    def add_port_mapping(self, 
                         external_port: int, 
                         internal_port: int,

                         protocol: str = "TCP",
                         lease_duration: int = 0,  # 0 = permanent
                         description: Optional[str] = None) -> bool:
        """
        Add a port mapping to the UPnP router
        
        Args:
            external_port: External port to open
            internal_port: Internal port to forward to
            protocol: Protocol (TCP or UDP)
            lease_duration: Lease duration in seconds (0 for permanent)
            description: Description of the port mapping
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available:
            if not self.discover():
                return False
        
        try:
            # Ensure local IP is set
            if not self.local_ip:
                self.local_ip = self._get_local_ip()
                if not self.local_ip:
                    logger.error("Failed to get local IP address")
                    return False
            
            # Create description if not provided
            if description is None:
                description = f"{self.service_name} - {protocol} Port {external_port}"
            
            # Add port mapping
            result = self.upnp.addportmapping(
                external_port=external_port,
                protocol=protocol,
                internal_port=internal_port,
                internal_client=self.local_ip,
                description=description,
                duration=lease_duration
            )
            
            if result:
                logger.info(f"Port mapping added: {external_port} -> {self.local_ip}:{internal_port} ({protocol})")
                self.mapped_ports[external_port] = protocol
                return True
            else:
                logger.error(f"Failed to add port mapping: {external_port} -> {self.local_ip}:{internal_port}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding port mapping: {str(e)}")
            return False

    def remove_port_mapping(self, external_port: int, protocol: str = "TCP") -> bool:
        """
        Remove a port mapping from the UPnP router
        
        Args:
            external_port: External port to close
            protocol: Protocol (TCP or UDP)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available:
            return False
        
        try:
            # Remove port mapping
            result = self.upnp.deleteportmapping(
                external_port=external_port,
                protocol=protocol
            )
            
            if result:
                logger.info(f"Port mapping removed: {external_port} ({protocol})")
                if external_port in self.mapped_ports:
                    del self.mapped_ports[external_port]
                return True
            else:
                logger.error(f"Failed to remove port mapping: {external_port} ({protocol})")
                return False
                
        except Exception as e:
            logger.error(f"Error removing port mapping: {str(e)}")
            return False

    def setup_api_ports(self, http_port: int, ws_port: Optional[int] = None) -> bool:
        """
        Set up port mappings for the API server
        
        Args:
            http_port: HTTP API port
            ws_port: WebSocket port (if different from HTTP port)
            
        Returns:
            True if at least the HTTP port was mapped, False otherwise
        """
        with self._setup_lock:
            # Try to discover UPnP devices if not already done
            if not self.is_available:
                if not self.discover():
                    logger.warning("UPnP is not available, skipping port mapping")
                    return False
            
            # Add HTTP port mapping
            http_result = self.add_port_mapping(
                external_port=http_port,
                internal_port=http_port,
                protocol="TCP",
                description=f"{self.service_name} - HTTP API"
            )
            
            # Add WebSocket port mapping if provided and different from HTTP port
            ws_result = True
            if ws_port is not None and ws_port != http_port:
                ws_result = self.add_port_mapping(
                    external_port=ws_port,
                    internal_port=ws_port,
                    protocol="TCP",
                    description=f"{self.service_name} - WebSocket"
                )
            
            # Start monitoring thread if not already running
            if (http_result or ws_result) and not self._monitor_thread:
                self._start_monitoring()
            
            return http_result

    def remove_all_mappings(self) -> None:
        """
        Remove all port mappings created by this helper
        """
        if not self.is_available:
            return
        
        # Create a copy to avoid modification during iteration
        ports_to_remove = dict(self.mapped_ports)
        
        for port, protocol in ports_to_remove.items():
            self.remove_port_mapping(port, protocol)
        
        logger.info("All port mappings removed")

    def _get_local_ip(self) -> Optional[str]:
        """
        Get the local IP address of this machine
        
        Returns:
            Local IP address or None if not found
        """
        try:
            # Create a temporary socket to determine the local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # This doesn't actually establish a connection
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception as e:
            logger.error(f"Error getting local IP: {str(e)}")
            
            # Fall back to hostname resolution
            try:
                hostname = socket.gethostname()
                return socket.gethostbyname(hostname)
            except Exception as e2:
                logger.error(f"Error getting IP from hostname: {str(e2)}")
                return None

    def _start_monitoring(self) -> None:
        """
        Start a monitoring thread to keep port mappings alive
        """
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        
        self._stop_monitor.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_port_mappings,
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("Port mapping monitor started")

    def _monitor_port_mappings(self) -> None:
        """
        Monitor thread to keep port mappings alive
        """
        check_interval = 300  # 5 minutes
        
        while not self._stop_monitor.is_set():
            try:
                # Sleep for the interval, but check for stop event
                for _ in range(check_interval):
                    if self._stop_monitor.is_set():
                        break
                    time.sleep(1)
                
                if self._stop_monitor.is_set():
                    break
                
                # Check UPnP availability
                if not self.is_available:
                    self.discover()
                    continue
                
                # Verify and refresh port mappings
                ports_to_refresh = dict(self.mapped_ports)
                
                for port, protocol in ports_to_refresh.items():
                    # Try to get the current mapping
                    try:
                        internal_ip, internal_port = self.upnp.getspecificportmapping(
                            port, protocol)
                        
                        # Check if the mapping points to our local IP
                        if internal_ip == self.local_ip:
                            logger.debug(f"Port mapping {port} ({protocol}) is still active")
                            continue
                    except Exception:
                        # Mapping not found or error occurred, try to recreate it
                        pass
                    
                    # Recreate the mapping
                    logger.info(f"Refreshing port mapping for {port} ({protocol})")
                    self.add_port_mapping(
                        external_port=port,
                        internal_port=port,
                        protocol=protocol
                    )
                
            except Exception as e:
                logger.error(f"Error in port mapping monitor: {str(e)}")

    def stop(self) -> None:
        """
        Stop the UPnP helper and clean up
        """
        # Stop the monitoring thread
        if self._monitor_thread:
            self._stop_monitor.set()
            if self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=5)
        
        # Remove all port mappings
        self.remove_all_mappings()
        
        logger.info("UPnP helper stopped")


# Singleton instance
_upnp_helper = None

def get_upnp_helper() -> UPnPHelper:
    """
    Get the UPnP helper singleton instance
    
    Returns:
        UPnP helper instance
    """
    global _upnp_helper
    
    if _upnp_helper is None:
        _upnp_helper = UPnPHelper()
    
    return _upnp_helper


def setup_port_forwarding(http_port: int, ws_port: Optional[int] = None) -> bool:
    """
    Set up UPnP port forwarding for the API server
    
    Args:
        http_port: HTTP API port
        ws_port: WebSocket port (if different from HTTP port)
        
    Returns:
        True if port forwarding was set up, False otherwise
    """
    helper = get_upnp_helper()
    return helper.setup_api_ports(http_port, ws_port)


def cleanup_port_forwarding() -> None:
    """
    Clean up UPnP port forwarding
    """
    if _upnp_helper is not None:
        _upnp_helper.stop()
