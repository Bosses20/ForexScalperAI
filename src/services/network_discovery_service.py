"""
Network Discovery Service for the Forex Trading Bot

This service enables the trading bot to be discovered by the mobile app on the local network.
It broadcasts the bot's availability using mDNS (Zeroconf/Bonjour) and provides
a simple API endpoint for connection verification.
"""

import json
import logging
import os
import socket
import threading
import time
import uuid
from typing import Dict, Optional, Tuple, Any, List, Union

import netifaces
import qrcode
import io
import base64
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from zeroconf import IPVersion, ServiceInfo, Zeroconf

# Local imports
try:
    from src.api.upnp_helper import get_upnp_helper
except ImportError:
    get_upnp_helper = None

logger = logging.getLogger(__name__)


class NetworkDiscoveryService:
    """
    Service that enables the trading bot to be discovered on the local network
    and integrates with market condition detection and multi-asset trading for
    improved connectivity and trading coordination.
    """
    
    def __init__(self, config: Dict[str, any]):
        """
        Initialize the network discovery service with configuration settings.
        
        Args:
            config: Application configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.network_config = config.get('network', {})
        
        # Service properties
        self.service_name = self.network_config.get('service_name', f'TradingBot-{socket.gethostname()}')
        self.api_port = self.network_config.get('api_port', 8000)
        self.service_type = '_tradingbot._tcp.local.'
        self.external_ip = None
        self.local_ip = self._get_local_ip()
        self.upnp_enabled = self.network_config.get('enable_upnp', True)
        self.auth_enabled = self.network_config.get('auth_enabled', True)
        self.service_properties = {}
        
        # Zeroconf and UPnP setup
        self.zeroconf = None
        self.upnp = None
        
        # QR code for easy connection
        self.qr_connection_data = {}
        
        # Component integrations
        self.market_condition_detector = None
        self.multi_asset_integrator = None
        
        # Performance tracking
        self.connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'last_connection_time': None,
            'client_ips': set()
        }
        
        # Initialize default properties
        self._initialize_service_properties()
        
        self.logger.info("NetworkDiscoveryService initialized")
        
    def set_market_condition_detector(self, detector) -> None:
        """
        Connect to market condition detector for enhanced signal validation and sharing
        
        Args:
            detector: MarketConditionDetector instance
        """
        self.market_condition_detector = detector
        self.logger.info("Connected to MarketConditionDetector")
        
    def set_multi_asset_integrator(self, integrator) -> None:
        """
        Connect to multi-asset integrator for coordinated trading
        
        Args:
            integrator: MultiAssetIntegrator instance
        """
        self.multi_asset_integrator = integrator
        self.logger.info("Connected to MultiAssetIntegrator")
        
    def _get_local_ip(self) -> str:
        """
        Get the local IP address of the machine.
        
        Returns:
            Local IP address
        """
        try:
            # Create a socket to determine local IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            self.logger.error(f"Error getting local IP: {str(e)}")
            return "127.0.0.1"
            
    def _initialize_service_properties(self) -> None:
        """
        Initialize the service properties for network discovery.
        """
        self.service_properties = {
            'version': self.config.get('version', '1.0.0'),
            'bot_name': self.config.get('bot_name', 'TradingBot'),
            'api_port': str(self.api_port),
            'supports_secure': 'true' if self.network_config.get('secure', True) else 'false',
            'supports_auth': 'true' if self.auth_enabled else 'false',
            'active_trading': 'true' if self.config.get('trading', {}).get('enabled', True) else 'false',
            'market_conditions': 'unknown',
            'active_positions': '0',
            'trading_opportunities': '0'
        }
        
    def _setup_upnp(self) -> bool:
        """
        Set up UPnP for port forwarding if enabled.
        
        Returns:
            Success status
        """
        if not self.upnp_enabled:
            self.logger.info("UPnP is disabled")
            return False
            
        try:
            self.logger.info("Setting up UPnP port forwarding...")
            
            # Initialize UPnP
            self.upnp = miniupnpc.UPnP()
            self.upnp.discoverdelay = 200
            
            # Discover UPnP devices
            discover_result = self.upnp.discover()
            self.logger.info(f"UPnP discover found {discover_result} devices")
            
            if discover_result > 0:
                try:
                    # Select the IGD (Internet Gateway Device)
                    self.upnp.selectigd()
                    
                    # Get the external IP address
                    self.external_ip = self.upnp.externalipaddress()
                    self.logger.info(f"External IP: {self.external_ip}")
                    
                    # Try to create the port mapping
                    result = self.upnp.addportmapping(
                        self.api_port,                 # External port
                        'TCP',                          # Protocol
                        self.local_ip,                  # Internal host
                        self.api_port,                 # Internal port
                        f'TradingBot API on {self.local_ip}',  # Description
                        ''                              # Remote host (empty string for wildcard)
                    )
                    
                    if result:
                        self.logger.info(f"UPnP port mapping successful: {self.external_ip}:{self.api_port} -> {self.local_ip}:{self.api_port}")
                        return True
                    else:
                        self.logger.error("UPnP port mapping failed")
                        return False
                        
                except Exception as e:
                    self.logger.error(f"Error during UPnP setup: {str(e)}")
                    return False
            else:
                self.logger.warning("No UPnP devices found")
                return False
                
        except Exception as e:
            self.logger.error(f"Error setting up UPnP: {str(e)}")
            return False
            
    def _generate_qr_connection_data(self) -> str:
        """
        Generate QR code data for easy connection to the trading bot.
        
        Returns:
            QR code data string
        """
        # Determine the best IP to use
        connect_ip = self.external_ip if self.external_ip else self.local_ip
        
        # Create connection data
        connection_data = {
            'name': self.service_name,
            'ip': connect_ip,
            'port': self.api_port,
            'secure': self.network_config.get('secure', True),
            'auth_required': self.auth_enabled,
            'api_version': self.config.get('api_version', '1.0'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Save connection data
        self.qr_connection_data = connection_data
        
        # Convert to JSON string
        return json.dumps(connection_data)
        
    def generate_qr_code(self, filename: str = None) -> Optional[str]:
        """
        Generate a QR code for easy connection to the trading bot.
        
        Args:
            filename: Optional filename to save the QR code image
            
        Returns:
            Path to the saved QR code or None if failed
        """
        try:
            # Generate connection data
            connection_data = self._generate_qr_connection_data()
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            
            qr.add_data(connection_data)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # If filename provided, save the image
            if filename:
                img.save(filename)
                self.logger.info(f"QR code saved to {filename}")
                return filename
                
            # Generate temp file if no filename specified
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            img.save(temp_file.name)
            self.logger.info(f"QR code saved to temporary file {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            self.logger.error(f"Error generating QR code: {str(e)}")
            return None
            
    def update_market_conditions(self, market_conditions: Dict[str, Any]) -> None:
        """
        Update the service properties with current market conditions.
        
        Args:
            market_conditions: Dictionary of market conditions
        """
        if not market_conditions:
            return
            
        # Count favorable trading conditions
        favorable_count = 0
        active_symbols = []
        
        for symbol, condition in market_conditions.items():
            if condition.get('should_trade', False) and condition.get('confidence', 0) >= 0.6:
                favorable_count += 1
                active_symbols.append(symbol)
                
        # Update service properties
        self.service_properties['market_conditions'] = f"{favorable_count} favorable"
        
        if active_symbols:
            self.service_properties['active_symbols'] = ','.join(active_symbols[:5])  # Just the first 5
            
        self.logger.debug(f"Updated market conditions in service properties: {favorable_count} favorable")
        
        # If we have a running Zeroconf service, update the properties
        if self.zeroconf:
            self._update_service_properties()
            
    def update_active_positions(self, positions: List[Dict]) -> None:
        """
        Update the service properties with active position information.
        
        Args:
            positions: List of active positions
        """
        if positions is None:
            return
            
        # Count positions
        position_count = len(positions)
        
        # Group by direction
        buy_count = len([p for p in positions if p.get('direction') == 'BUY'])
        sell_count = len([p for p in positions if p.get('direction') == 'SELL'])
        
        # Update service properties
        self.service_properties['active_positions'] = str(position_count)
        self.service_properties['buy_positions'] = str(buy_count)
        self.service_properties['sell_positions'] = str(sell_count)
        
        self.logger.debug(f"Updated active positions in service properties: {position_count} positions")
        
        # If we have a running Zeroconf service, update the properties
        if self.zeroconf:
            self._update_service_properties()
            
    def update_trading_opportunities(self, opportunities: List[Dict]) -> None:
        """
        Update the service properties with current trading opportunities.
        
        Args:
            opportunities: List of trading opportunities
        """
        if opportunities is None:
            return
            
        # Count opportunities
        opportunity_count = len(opportunities)
        
        # Get top opportunities
        top_opportunities = []
        
        for opp in opportunities[:3]:  # Just the top 3
            symbol = opp.get('symbol', '')
            direction = opp.get('direction', '')
            confidence = opp.get('confidence', 0)
            
            if symbol and direction:
                top_opportunities.append(f"{symbol}:{direction}:{confidence:.2f}")
                
        # Update service properties
        self.service_properties['trading_opportunities'] = str(opportunity_count)
        
        if top_opportunities:
            self.service_properties['top_opportunities'] = ','.join(top_opportunities)
            
        self.logger.debug(f"Updated trading opportunities in service properties: {opportunity_count} opportunities")
        
        # If we have a running Zeroconf service, update the properties
        if self.zeroconf:
            self._update_service_properties()
            
    def update_service_status(self, status: Dict[str, Any]) -> None:
        """
        Update the service properties with the current status of the trading bot.
        
        Args:
            status: Dictionary with status information
        """
        if not status:
            return
            
        # Update service properties with status info
        for key, value in status.items():
            # Skip complex objects, only include simple types
            if isinstance(value, (str, int, float, bool)):
                self.service_properties[key] = str(value)
                
        self.logger.debug("Updated service status in service properties")
        
        # If we have a running Zeroconf service, update the properties
        if self.zeroconf:
            self._update_service_properties()
            
    def _update_service_properties(self) -> None:
        """
        Update the Zeroconf service properties.
        """
        try:
            if not self.zeroconf:
                return
                
            # Convert all properties to strings (required by Zeroconf)
            properties = {k: str(v).encode('utf-8') for k, v in self.service_properties.items()}
            
            # Update the service info
            service_info = ServiceInfo(
                self.service_type,
                f"{self.service_name}.{self.service_type}",
                addresses=[socket.inet_aton(self.local_ip)],
                port=self.api_port,
                properties=properties
            )
            
            # Update the service
            self.zeroconf.update_service(service_info)
            
            self.logger.debug("Zeroconf service properties updated")
            
        except Exception as e:
            self.logger.error(f"Error updating Zeroconf service properties: {str(e)}")
            
    def start(self) -> bool:
        """
        Start the network discovery service.
        
        Returns:
            Success status
        """
        try:
            self.logger.info("Starting NetworkDiscoveryService...")
            
            # Set up UPnP if enabled
            if self.upnp_enabled:
                upnp_success = self._setup_upnp()
                self.logger.info(f"UPnP setup {'successful' if upnp_success else 'failed'}")
                
            # Initialize Zeroconf
            self.zeroconf = Zeroconf()
            
            # Convert all properties to strings (required by Zeroconf)
            properties = {k: str(v).encode('utf-8') for k, v in self.service_properties.items()}
            
            # Create service info
            service_info = ServiceInfo(
                self.service_type,
                f"{self.service_name}.{self.service_type}",
                addresses=[socket.inet_aton(self.local_ip)],
                port=self.api_port,
                properties=properties
            )
            
            # Register the service
            self.zeroconf.register_service(service_info)
            
            self.logger.info(f"Zeroconf service registered: {self.service_name} on {self.local_ip}:{self.api_port}")
            
            # Generate QR code for easy connection
            qr_file = self.generate_qr_code(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'connection_qr.png'))
            if qr_file:
                self.logger.info(f"Connection QR code generated: {qr_file}")
                
            # If we have integrated components, initialize with current data
            self._sync_integrated_components()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting network discovery service: {str(e)}")
            return False
            
    def _sync_integrated_components(self) -> None:
        """
        Synchronize with integrated components to get current state.
        """
        # Sync with market condition detector
        if self.market_condition_detector:
            # Get current market conditions if available
            if hasattr(self.market_condition_detector, 'get_all_market_conditions'):
                try:
                    conditions = self.market_condition_detector.get_all_market_conditions()
                    self.update_market_conditions(conditions)
                except Exception as e:
                    self.logger.error(f"Error syncing with MarketConditionDetector: {str(e)}")
                    
        # Sync with multi-asset integrator
        if self.multi_asset_integrator:
            try:
                # Get network status data if available
                if hasattr(self.multi_asset_integrator, 'get_network_status_data'):
                    status_data = self.multi_asset_integrator.get_network_status_data()
                    
                    # Update service with relevant data
                    if 'positions' in status_data:
                        self.update_active_positions(status_data['positions'].get('total_positions', 0))
                        
                    if 'opportunities' in status_data:
                        opportunities = []
                        # Convert summary data to opportunity format for service properties
                        for symbol in status_data['opportunities'].get('symbols', []):
                            opportunities.append({'symbol': symbol})
                            
                        self.update_trading_opportunities(opportunities)
                        
                # Alternatively, try individual methods
                else:
                    # Get active positions if available
                    if hasattr(self.multi_asset_integrator, 'positions'):
                        self.update_active_positions(self.multi_asset_integrator.positions)
                        
                    # Get trading opportunities if available
                    if hasattr(self.multi_asset_integrator, 'get_trading_opportunities'):
                        opportunities = self.multi_asset_integrator.get_trading_opportunities()
                        self.update_trading_opportunities(opportunities)
                        
            except Exception as e:
                self.logger.error(f"Error syncing with MultiAssetIntegrator: {str(e)}")
                
    def stop(self) -> None:
        """
        Stop the network discovery service.
        """
        try:
            self.logger.info("Stopping NetworkDiscoveryService...")
            
            # Unregister Zeroconf service
            if self.zeroconf:
                self.zeroconf.unregister_all_services()
                self.zeroconf.close()
                self.zeroconf = None
                self.logger.info("Zeroconf service unregistered")
                
            # Remove UPnP port forwarding
            if self.upnp and self.upnp_enabled:
                try:
                    self.upnp.deleteportmapping(self.api_port, 'TCP')
                    self.logger.info(f"UPnP port mapping removed for port {self.api_port}")
                except Exception as e:
                    self.logger.error(f"Error removing UPnP port mapping: {str(e)}")
                    
            self.logger.info("NetworkDiscoveryService stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping network discovery service: {str(e)}")
            
    def get_connection_info(self) -> Dict[str, any]:
        """
        Get information about how to connect to the trading bot.
        
        Returns:
            Dictionary with connection information
        """
        # Determine the best IP to use
        connect_ip = self.external_ip if self.external_ip else self.local_ip
        
        # Create connection info
        connection_info = {
            'service_name': self.service_name,
            'local_ip': self.local_ip,
            'external_ip': self.external_ip,
            'connect_ip': connect_ip,
            'api_port': self.api_port,
            'secure': self.network_config.get('secure', True),
            'auth_required': self.auth_enabled,
            'upnp_enabled': self.upnp_enabled,
            'upnp_status': 'active' if self.external_ip else 'inactive',
            'qr_connection_data': self.qr_connection_data,
            'api_url': f"http{'s' if self.network_config.get('secure', True) else ''}://{connect_ip}:{self.api_port}"
        }
        
        return connection_info
        
    def get_service_status(self) -> Dict[str, any]:
        """
        Get the current status of the network discovery service.
        
        Returns:
            Dictionary with service status
        """
        status = {
            'service_name': self.service_name,
            'service_type': self.service_type,
            'local_ip': self.local_ip,
            'external_ip': self.external_ip,
            'api_port': self.api_port,
            'upnp_enabled': self.upnp_enabled,
            'upnp_status': 'active' if self.external_ip else 'inactive',
            'zeroconf_active': self.zeroconf is not None,
            'auth_enabled': self.auth_enabled,
            'service_properties': self.service_properties,
            'connection_stats': {
                'total_connections': self.connection_stats['total_connections'],
                'active_connections': self.connection_stats['active_connections'],
                'last_connection_time': self.connection_stats['last_connection_time'],
                'unique_clients': len(self.connection_stats['client_ips'])
            }
        }
        
        return status
        
    def register_connection(self, client_ip: str) -> None:
        """
        Register a new client connection for statistics tracking.
        
        Args:
            client_ip: IP address of the client
        """
        # Update connection stats
        self.connection_stats['total_connections'] += 1
        self.connection_stats['active_connections'] += 1
        self.connection_stats['last_connection_time'] = datetime.now()
        self.connection_stats['client_ips'].add(client_ip)
        
        self.logger.info(f"New client connection from {client_ip}")
        
    def unregister_connection(self, client_ip: str) -> None:
        """
        Unregister a client connection.
        
        Args:
            client_ip: IP address of the client
        """
        # Update connection stats
        if self.connection_stats['active_connections'] > 0:
            self.connection_stats['active_connections'] -= 1
            
        self.logger.info(f"Client disconnected: {client_ip}")
        
    def get_trading_state_for_client(self) -> Dict[str, any]:
        """
        Get the current trading state to share with a client connection.
        This integrates data from MarketConditionDetector and MultiAssetIntegrator.
        
        Returns:
            Dictionary with trading state information
        """
        trading_state = {
            'timestamp': datetime.now().isoformat(),
            'market_conditions': {},
            'active_positions': {},
            'trading_opportunities': [],
            'performance': {}
        }
        
        # Get market conditions if available
        if self.market_condition_detector:
            if hasattr(self.market_condition_detector, 'get_all_market_conditions'):
                trading_state['market_conditions'] = self.market_condition_detector.get_all_market_conditions()
                
        # Get trading state from multi-asset integrator if available
        if self.multi_asset_integrator:
            # Try to get comprehensive state data
            if hasattr(self.multi_asset_integrator, 'refresh_all_data'):
                integrator_state = self.multi_asset_integrator.refresh_all_data()
                
                # Update trading state with integrator data
                if 'positions' in integrator_state:
                    trading_state['active_positions'] = integrator_state['positions']
                    
                if 'opportunities' in integrator_state:
                    trading_state['trading_opportunities'] = integrator_state['opportunities']
                    
                if 'performance' in integrator_state:
                    trading_state['performance'] = integrator_state['performance']
                    
            # Alternatively, try to get data from individual methods
            else:
                # Get active positions summary
                if hasattr(self.multi_asset_integrator, 'get_active_positions_summary'):
                    trading_state['active_positions'] = self.multi_asset_integrator.get_active_positions_summary()
                    
                # Get trading opportunities
                if hasattr(self.multi_asset_integrator, 'get_trading_opportunities'):
                    trading_state['trading_opportunities'] = self.multi_asset_integrator.get_trading_opportunities()
                    
                # Get performance summary
                if hasattr(self.multi_asset_integrator, 'get_performance_summary'):
                    trading_state['performance'] = self.multi_asset_integrator.get_performance_summary()
                    
        # Add system information
        trading_state['system_info'] = {
            'host': socket.gethostname(),
            'version': self.config.get('version', '1.0.0'),
            'uptime': time.time() - psutil.boot_time() if 'psutil' in sys.modules else 0,
            'client_connections': self.connection_stats['active_connections']
        }
        
        return trading_state
        
    def broadcast_trading_update(self, update_type: str, data: Dict[str, any]) -> bool:
        """
        Broadcast a trading update to all connected clients.
        This method would typically integrate with a WebSocket server.
        
        Args:
            update_type: Type of update (e.g., market_condition, new_position)
            data: Update data to broadcast
            
        Returns:
            Success status
        """
        try:
            # This is a placeholder for integration with a WebSocket server
            # In a real implementation, this would send the update to all connected clients
            
            # Update service properties with this data
            if update_type == 'market_condition':
                self.update_market_conditions(data)
            elif update_type == 'position':
                self.update_active_positions([data])
            elif update_type == 'opportunity':
                self.update_trading_opportunities([data])
                
            # Log the broadcast
            self.logger.debug(f"Broadcasting {update_type} update to {self.connection_stats['active_connections']} clients")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error broadcasting trading update: {str(e)}")
            return False
