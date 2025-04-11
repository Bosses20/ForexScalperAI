"""
QR Code Service for the Forex Trading Bot

This service generates and parses QR codes for easy connection to the trading bot.
It helps mobile app users to quickly establish a connection to their bot servers.
"""

import io
import json
import logging
import base64
import qrcode
from typing import Dict, Any, Optional
from pyzbar.pyzbar import decode
from PIL import Image

logger = logging.getLogger(__name__)

# Singleton instance
_instance = None

class QrCodeService:
    """Service for generating and parsing QR codes for trading bot connections"""
    
    def __init__(self):
        """Initialize the QR code service"""
        self._connection_url_format = "tradingbot://{host}:{port}?name={name}&auth={auth}&version={version}"
    
    def generate_qr_code_data(self, 
                              host: str, 
                              port: int, 
                              name: str = "Trading Bot", 
                              requires_auth: bool = True, 
                              version: str = "1.0.0",
                              extra_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate data for a QR code that can be used to connect to the bot
        
        Args:
            host: The host/IP address of the bot
            port: The port number
            name: The name of the bot
            requires_auth: Whether authentication is required
            version: The bot version
            extra_data: Additional data to include in the QR code
            
        Returns:
            String data to be encoded in the QR code
        """
        try:
            # Create base URL with main connection parameters
            url = self._connection_url_format.format(
                host=host,
                port=port,
                name=name.replace(" ", "%20"),
                auth=str(requires_auth).lower(),
                version=version
            )
            
            # Add extra data as URL parameters if provided
            if extra_data:
                for key, value in extra_data.items():
                    # Skip None values
                    if value is None:
                        continue
                    
                    # Convert value to string if it's not already
                    if not isinstance(value, str):
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value)
                        else:
                            value = str(value)
                    
                    # URL encode the value and append to URL
                    encoded_value = value.replace(" ", "%20")
                    url += f"&{key}={encoded_value}"
            
            return url
        except Exception as e:
            logger.error(f"Error generating QR code data: {str(e)}")
            return f"tradingbot://{host}:{port}"
    
    def generate_qr_code(self, 
                         data: str, 
                         box_size: int = 10, 
                         border: int = 4,
                         fill_color: str = "black",
                         back_color: str = "white") -> Image.Image:
        """
        Generate a QR code image from the data
        
        Args:
            data: The data to encode in the QR code
            box_size: Size of each box in the QR code
            border: Border size around the QR code
            fill_color: Color of the QR code
            back_color: Background color
            
        Returns:
            PIL Image of the QR code
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=box_size,
                border=border,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color=fill_color, back_color=back_color)
            return img
        except Exception as e:
            logger.error(f"Error generating QR code image: {str(e)}")
            # Create a simple error QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=box_size,
                border=border,
            )
            qr.add_data("error")
            qr.make(fit=True)
            return qr.make_image(fill_color=fill_color, back_color=back_color)
    
    def generate_qr_code_base64(self, 
                                data: str, 
                                image_format: str = "PNG") -> str:
        """
        Generate a base64 encoded string of the QR code
        
        Args:
            data: The data to encode in the QR code
            image_format: Format of the image (PNG, JPEG, etc.)
            
        Returns:
            Base64 encoded string of the QR code image
        """
        try:
            img = self.generate_qr_code(data)
            buffered = io.BytesIO()
            img.save(buffered, format=image_format)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/{image_format.lower()};base64,{img_str}"
        except Exception as e:
            logger.error(f"Error generating base64 QR code: {str(e)}")
            return ""
    
    def generate_connection_qr_base64(self, 
                                     host: str, 
                                     port: int, 
                                     name: str = "Trading Bot", 
                                     requires_auth: bool = True, 
                                     version: str = "1.0.0",
                                     extra_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a base64 encoded QR code for connecting to the bot
        
        Args:
            host: The host/IP address of the bot
            port: The port number
            name: The name of the bot
            requires_auth: Whether authentication is required
            version: The bot version
            extra_data: Additional data to include in the QR code
            
        Returns:
            Base64 encoded string of the QR code image
        """
        try:
            data = self.generate_qr_code_data(host, port, name, requires_auth, version, extra_data)
            return self.generate_qr_code_base64(data)
        except Exception as e:
            logger.error(f"Error generating connection QR code: {str(e)}")
            return ""
    
    def parse_qr_code(self, image: bytes) -> Optional[str]:
        """
        Parse a QR code from an image
        
        Args:
            image: Image data containing a QR code
            
        Returns:
            Decoded QR code data or None if parsing failed
        """
        try:
            # Create PIL image from bytes
            img = Image.open(io.BytesIO(image))
            
            # Decode QR codes in the image
            decoded_objects = decode(img)
            
            if not decoded_objects:
                logger.warning("No QR codes found in the image")
                return None
            
            # Return the data from the first QR code
            return decoded_objects[0].data.decode('utf-8')
        except Exception as e:
            logger.error(f"Error parsing QR code: {str(e)}")
            return None
    
    def parse_connection_data(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse a connection URL to extract connection information
        
        Args:
            url: URL containing connection information
            
        Returns:
            Dictionary with connection parameters or None if parsing failed
        """
        try:
            # Check if it's a valid trading bot URL
            if not url.startswith("tradingbot://"):
                raise ValueError("Not a valid trading bot URL")
            
            # Extract host and port from the URL
            url_without_scheme = url[len("tradingbot://"):]
            host_port, params_str = url_without_scheme.split("?", 1) if "?" in url_without_scheme else (url_without_scheme, "")
            
            if ":" in host_port:
                host, port_str = host_port.split(":", 1)
                port = int(port_str)
            else:
                host = host_port
                port = 8000  # Default port
            
            # Parse URL parameters
            params = {}
            if params_str:
                param_pairs = params_str.split("&")
                for pair in param_pairs:
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        params[key] = value.replace("%20", " ")
            
            # Build result
            result = {
                "host": host,
                "port": port,
                "name": params.get("name", "Trading Bot"),
                "requires_auth": params.get("auth", "true").lower() == "true",
                "version": params.get("version", "1.0.0"),
            }
            
            # Add any other parameters
            for key, value in params.items():
                if key not in ["name", "auth", "version"]:
                    result[key] = value
            
            return result
        except Exception as e:
            logger.error(f"Error parsing connection URL: {str(e)}")
            return None


def get_qr_code_service() -> QrCodeService:
    """
    Get the QR code service singleton instance
    
    Returns:
        QR code service instance
    """
    global _instance
    
    if _instance is None:
        _instance = QrCodeService()
    
    return _instance
