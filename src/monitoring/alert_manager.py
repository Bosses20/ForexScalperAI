"""
Alert manager for the Forex Trading Bot
Handles alerting for critical issues and notifications
"""

import os
import time
import json
import threading
import smtplib
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from collections import deque
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .logger import get_logger

logger = get_logger("AlertManager")


class AlertManager:
    """
    Manages alerts and notifications for critical trading and system issues
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the alert manager
        
        Args:
            config: Configuration dictionary with alert settings
        """
        self.config = config
        self.enabled = config.get('alerts_enabled', True)
        self.alert_levels = ['info', 'warning', 'error', 'critical']
        self.min_alert_level = config.get('min_alert_level', 'warning')
        
        # Set up notification methods
        self.email_config = config.get('email', {})
        self.sms_config = config.get('sms', {})
        self.telegram_config = config.get('telegram', {})
        self.webhook_config = config.get('webhook', {})
        
        # Configure alert throttling
        self.throttle_seconds = config.get('throttle_seconds', 300)  # 5 minutes
        self.alert_history = deque(maxlen=config.get('max_history', 100))
        self.last_alerts = {}  # For throttling
        
        # Set up alert log
        self.log_file = config.get('alert_log_file', 'data/logs/alerts.log')
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Set up alert handlers
        self.alert_handlers = {
            'email': self._send_email_alert,
            'sms': self._send_sms_alert,
            'telegram': self._send_telegram_alert,
            'webhook': self._send_webhook_alert,
            'log': self._log_alert
        }
        
        # Configure which channels to use for each alert level
        self.alert_channels = config.get('alert_channels', {
            'info': ['log'],
            'warning': ['log'],
            'error': ['log', 'email'],
            'critical': ['log', 'email', 'sms', 'telegram']
        })
        
        # Check if we have custom alert handlers
        self.custom_handlers = {}
        
        logger.info("Alert manager initialized")
    
    def register_custom_handler(self, name: str, handler: Callable) -> bool:
        """
        Register a custom alert handler function
        
        Args:
            name: Name for the handler
            handler: Handler function taking alert data and returning success boolean
            
        Returns:
            True if registered successfully, False otherwise
        """
        if name in self.alert_handlers:
            logger.warning(f"Alert handler '{name}' already exists")
            return False
            
        self.custom_handlers[name] = handler
        self.alert_handlers[name] = handler
        
        logger.info(f"Registered custom alert handler: {name}")
        return True
    
    def send_alert(self, level: str, title: str, message: str, 
                source: str = 'system', data: Optional[Dict] = None,
                channels: Optional[List[str]] = None) -> bool:
        """
        Send an alert via configured channels
        
        Args:
            level: Alert level (info, warning, error, critical)
            title: Alert title
            message: Alert message
            source: Source of the alert
            data: Optional data to include with the alert
            channels: Optional override of channels to use
            
        Returns:
            True if alert was sent successfully, False otherwise
        """
        if not self.enabled:
            return False
            
        # Validate alert level
        level = level.lower()
        if level not in self.alert_levels:
            logger.warning(f"Invalid alert level: {level}")
            level = 'info'
            
        # Check if we should send this alert based on min_alert_level
        if self.alert_levels.index(level) < self.alert_levels.index(self.min_alert_level):
            logger.debug(f"Alert level {level} below minimum {self.min_alert_level}, not sending")
            return False
            
        # Check throttling
        alert_key = f"{level}_{source}_{title}"
        if alert_key in self.last_alerts:
            last_time = self.last_alerts[alert_key]
            if datetime.now() - last_time < timedelta(seconds=self.throttle_seconds):
                logger.debug(f"Alert throttled: {alert_key}")
                return False
                
        # Update last alert time
        self.last_alerts[alert_key] = datetime.now()
        
        # Create alert data
        alert_data = {
            'id': f"{int(time.time())}_{level}_{source}",
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'title': title,
            'message': message,
            'source': source
        }
        
        # Add additional data if provided
        if data:
            alert_data['data'] = data
            
        # Add to history
        self.alert_history.append(alert_data)
        
        # Determine which channels to use
        if channels is None:
            channels = self.alert_channels.get(level, ['log'])
            
        # Send to each channel
        success = True
        for channel in channels:
            if channel in self.alert_handlers:
                try:
                    result = self.alert_handlers[channel](alert_data)
                    if not result:
                        success = False
                        logger.warning(f"Failed to send alert via {channel}")
                except Exception as e:
                    success = False
                    logger.error(f"Error sending alert via {channel}: {str(e)}")
            else:
                logger.warning(f"Unknown alert channel: {channel}")
                
        return success
    
    def _log_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Log an alert to the alert log file
        
        Args:
            alert_data: Alert data dictionary
            
        Returns:
            True if logged successfully, False otherwise
        """
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(alert_data) + '\n')
                
            # Also log to the application logger
            log_level = alert_data['level'].lower()
            log_message = f"[{alert_data['source']}] {alert_data['title']}: {alert_data['message']}"
            
            if log_level == 'critical':
                logger.critical(log_message)
            elif log_level == 'error':
                logger.error(log_message)
            elif log_level == 'warning':
                logger.warning(log_message)
            else:
                logger.info(log_message)
                
            return True
            
        except Exception as e:
            logger.error(f"Error logging alert: {str(e)}")
            return False
    
    def _send_email_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send an alert via email
        
        Args:
            alert_data: Alert data dictionary
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.email_config or not self.email_config.get('enabled', False):
            return False
            
        try:
            # Get email config
            smtp_server = self.email_config.get('smtp_server')
            smtp_port = self.email_config.get('smtp_port', 587)
            username = self.email_config.get('username')
            password = self.email_config.get('password')
            sender = self.email_config.get('sender')
            recipients = self.email_config.get('recipients', [])
            
            # Check if required config is present
            if not smtp_server or not username or not password or not sender or not recipients:
                logger.warning("Incomplete email configuration")
                return False
                
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"[{alert_data['level'].upper()}] {alert_data['title']}"
            
            # Create HTML body
            html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .alert-critical {{ background-color: #f8d7da; color: #721c24; padding: 10px; border: 1px solid #f5c6cb; border-radius: 4px; }}
                    .alert-error {{ background-color: #f8d7da; color: #721c24; padding: 10px; border: 1px solid #f5c6cb; border-radius: 4px; }}
                    .alert-warning {{ background-color: #fff3cd; color: #856404; padding: 10px; border: 1px solid #ffeeba; border-radius: 4px; }}
                    .alert-info {{ background-color: #d1ecf1; color: #0c5460; padding: 10px; border: 1px solid #bee5eb; border-radius: 4px; }}
                </style>
            </head>
            <body>
                <div class="alert-{alert_data['level']}">
                    <h2>{alert_data['title']}</h2>
                    <p><strong>Level:</strong> {alert_data['level'].upper()}</p>
                    <p><strong>Source:</strong> {alert_data['source']}</p>
                    <p><strong>Time:</strong> {alert_data['timestamp']}</p>
                    <p><strong>Message:</strong> {alert_data['message']}</p>
                </div>
            """
            
            # Add data if present
            if 'data' in alert_data:
                html += "<h3>Additional Data:</h3><pre>"
                if isinstance(alert_data['data'], dict):
                    for key, value in alert_data['data'].items():
                        html += f"{key}: {value}<br>"
                else:
                    html += f"{str(alert_data['data'])}"
                html += "</pre>"
                
            html += """
            </body>
            </html>
            """
            
            # Attach HTML content
            msg.attach(MIMEText(html, 'html'))
            
            # Connect to server and send
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.ehlo()
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email alert sent: {alert_data['title']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email alert: {str(e)}")
            return False
    
    def _send_sms_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send an alert via SMS
        
        Args:
            alert_data: Alert data dictionary
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.sms_config or not self.sms_config.get('enabled', False):
            return False
            
        try:
            # Get SMS config
            provider = self.sms_config.get('provider', 'twilio')
            
            # Format SMS message
            level = alert_data['level'].upper()
            message = f"[{level}] {alert_data['title']}: {alert_data['message']}"
            
            # Send via appropriate provider
            if provider == 'twilio':
                return self._send_twilio_sms(message, alert_data)
            else:
                logger.warning(f"Unknown SMS provider: {provider}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending SMS alert: {str(e)}")
            return False
    
    def _send_twilio_sms(self, message: str, alert_data: Dict[str, Any]) -> bool:
        """
        Send SMS via Twilio
        
        Args:
            message: SMS message
            alert_data: Alert data dictionary
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Get Twilio config
            account_sid = self.sms_config.get('twilio_account_sid')
            auth_token = self.sms_config.get('twilio_auth_token')
            from_number = self.sms_config.get('from_number')
            to_numbers = self.sms_config.get('to_numbers', [])
            
            # Check if required config is present
            if not account_sid or not auth_token or not from_number or not to_numbers:
                logger.warning("Incomplete Twilio configuration")
                return False
                
            # Try to import Twilio client
            try:
                from twilio.rest import Client
                client = Client(account_sid, auth_token)
            except ImportError:
                # Fallback to HTTP API if Twilio library not available
                for to_number in to_numbers:
                    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
                    auth = (account_sid, auth_token)
                    data = {
                        'From': from_number,
                        'To': to_number,
                        'Body': message
                    }
                    response = requests.post(url, auth=auth, data=data)
                    if response.status_code != 201:
                        logger.warning(f"Failed to send SMS to {to_number}: {response.text}")
                        return False
                        
                logger.info(f"SMS alert sent to {len(to_numbers)} recipients")
                return True
                
            # Send message to each recipient
            for to_number in to_numbers:
                client.messages.create(
                    body=message,
                    from_=from_number,
                    to=to_number
                )
                
            logger.info(f"SMS alert sent to {len(to_numbers)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Twilio SMS: {str(e)}")
            return False
    
    def _send_telegram_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send an alert via Telegram
        
        Args:
            alert_data: Alert data dictionary
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.telegram_config or not self.telegram_config.get('enabled', False):
            return False
            
        try:
            # Get Telegram config
            bot_token = self.telegram_config.get('bot_token')
            chat_ids = self.telegram_config.get('chat_ids', [])
            
            # Check if required config is present
            if not bot_token or not chat_ids:
                logger.warning("Incomplete Telegram configuration")
                return False
                
            # Format message
            level = alert_data['level'].upper()
            message = f"*[{level}] {alert_data['title']}*\n\n{alert_data['message']}"
            
            # Add source and timestamp
            message += f"\n\nSource: {alert_data['source']}"
            message += f"\nTime: {alert_data['timestamp']}"
            
            # Add data if present
            if 'data' in alert_data:
                message += "\n\nAdditional Data:"
                if isinstance(alert_data['data'], dict):
                    for key, value in alert_data['data'].items():
                        message += f"\n- {key}: {value}"
                else:
                    message += f"\n{str(alert_data['data'])}"
                    
            # Send to each chat
            for chat_id in chat_ids:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                params = {
                    'chat_id': chat_id,
                    'text': message,
                    'parse_mode': 'Markdown'
                }
                response = requests.post(url, json=params)
                if response.status_code != 200:
                    logger.warning(f"Failed to send Telegram message to {chat_id}: {response.text}")
                    return False
                    
            logger.info(f"Telegram alert sent to {len(chat_ids)} chats")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {str(e)}")
            return False
    
    def _send_webhook_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send an alert via webhook
        
        Args:
            alert_data: Alert data dictionary
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.webhook_config or not self.webhook_config.get('enabled', False):
            return False
            
        try:
            # Get webhook config
            url = self.webhook_config.get('url')
            method = self.webhook_config.get('method', 'POST')
            headers = self.webhook_config.get('headers', {})
            
            # Check if required config is present
            if not url:
                logger.warning("Incomplete webhook configuration")
                return False
                
            # Send request
            if method.upper() == 'POST':
                response = requests.post(url, json=alert_data, headers=headers)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=alert_data, headers=headers)
            else:
                logger.warning(f"Unsupported webhook method: {method}")
                return False
                
            # Check response
            if response.status_code < 200 or response.status_code >= 300:
                logger.warning(f"Webhook returned non-success status: {response.status_code}")
                return False
                
            logger.info(f"Webhook alert sent: {alert_data['title']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending webhook alert: {str(e)}")
            return False
    
    def get_alerts(self, level: Optional[str] = None, 
                source: Optional[str] = None, 
                limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get alerts from history
        
        Args:
            level: Optional filter by alert level
            source: Optional filter by alert source
            limit: Maximum number of alerts to return
            
        Returns:
            List of alert dictionaries
        """
        if not self.enabled:
            return []
            
        # Convert history to list for filtering
        alerts = list(self.alert_history)
        
        # Apply filters
        if level:
            alerts = [a for a in alerts if a['level'] == level]
            
        if source:
            alerts = [a for a in alerts if a['source'] == source]
            
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda a: a['timestamp'], reverse=True)
        
        # Apply limit
        return alerts[:limit]
    
    def get_alert_counts(self) -> Dict[str, int]:
        """
        Get counts of alerts by level
        
        Returns:
            Dictionary with alert counts
        """
        if not self.enabled:
            return {}
            
        counts = {level: 0 for level in self.alert_levels}
        
        # Count alerts by level
        for alert in self.alert_history:
            level = alert['level']
            if level in counts:
                counts[level] += 1
                
        return counts
    
    def clear_alerts(self) -> int:
        """
        Clear all alerts from history
        
        Returns:
            Number of alerts cleared
        """
        count = len(self.alert_history)
        self.alert_history.clear()
        return count
