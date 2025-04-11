"""
Multi-Factor Authentication module for the Forex Trading Bot
Provides 2FA authentication using time-based one-time passwords (TOTP)
"""

import base64
import hmac
import time
import hashlib
import secrets
import qrcode
from io import BytesIO
import os
from typing import Dict, Tuple, Optional
from datetime import datetime
import json
from loguru import logger


class MFAAuthenticator:
    """
    Implements Time-Based One-Time Password (TOTP) authentication
    Compatible with Google Authenticator, Authy, and other TOTP apps
    """
    
    def __init__(self, config: dict):
        """
        Initialize the MFA authenticator
        
        Args:
            config: Configuration dictionary with MFA settings
        """
        self.config = config
        self.secrets_file = config.get('mfa_secrets_path', 'config/mfa_secrets.json')
        self.issuer = config.get('mfa_issuer', 'Forex Trading Bot')
        self.digit_length = config.get('mfa_digits', 6)
        self.period = config.get('mfa_period', 30)  # Default 30-second period
        self.algorithm = config.get('mfa_algorithm', 'SHA1')
        self.user_secrets = self._load_secrets()
        
        logger.info("MFA Authenticator initialized")
    
    def _load_secrets(self) -> Dict:
        """
        Load MFA secrets from the secrets file
        
        Returns:
            Dictionary of user MFA secrets
        """
        if not os.path.exists(self.secrets_file):
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.secrets_file), exist_ok=True)
            # Create empty secrets file
            with open(self.secrets_file, 'w') as f:
                json.dump({}, f)
            logger.info(f"Created new MFA secrets file at {self.secrets_file}")
            return {}
        
        try:
            with open(self.secrets_file, 'r') as f:
                secrets_data = json.load(f)
            logger.debug(f"Loaded MFA secrets for {len(secrets_data)} users")
            return secrets_data
        except Exception as e:
            logger.error(f"Error loading MFA secrets: {str(e)}")
            return {}
    
    def _save_secrets(self) -> bool:
        """
        Save MFA secrets to the secrets file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.secrets_file), exist_ok=True)
            
            # Save with pretty formatting for readability
            with open(self.secrets_file, 'w') as f:
                json.dump(self.user_secrets, f, indent=2)
            logger.debug(f"Saved MFA secrets for {len(self.user_secrets)} users")
            return True
        except Exception as e:
            logger.error(f"Error saving MFA secrets: {str(e)}")
            return False
    
    def generate_secret(self) -> str:
        """
        Generate a new random secret key for TOTP
        
        Returns:
            Base32 encoded secret key
        """
        # Generate 32 bytes of random data
        random_bytes = secrets.token_bytes(32)
        # Convert to base32 encoding (required for TOTP)
        return base64.b32encode(random_bytes).decode('utf-8')
    
    def setup_mfa(self, username: str) -> Tuple[str, str, BytesIO]:
        """
        Set up MFA for a user
        
        Args:
            username: Username to set up MFA for
            
        Returns:
            Tuple of (secret_key, provisioning_uri, qr_code_image)
        """
        # Generate a new secret
        secret_key = self.generate_secret()
        
        # Save to user secrets
        self.user_secrets[username] = {
            'secret': secret_key,
            'enabled': True,
            'created_at': datetime.now().isoformat(),
            'last_used': None
        }
        self._save_secrets()
        
        # Create provisioning URI (for QR code)
        provisioning_uri = self._get_provisioning_uri(username, secret_key)
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = BytesIO()
        img.save(img_buffer)
        img_buffer.seek(0)
        
        logger.info(f"MFA setup completed for user {username}")
        return secret_key, provisioning_uri, img_buffer
    
    def _get_provisioning_uri(self, username: str, secret_key: str) -> str:
        """
        Generate the provisioning URI for TOTP apps
        
        Args:
            username: User identifier
            secret_key: TOTP secret key
            
        Returns:
            URI for QR code generation
        """
        return (f"otpauth://totp/{self.issuer}:{username}?"
                f"secret={secret_key}&issuer={self.issuer}"
                f"&algorithm={self.algorithm}&digits={self.digit_length}"
                f"&period={self.period}")
    
    def verify_code(self, username: str, code: str) -> bool:
        """
        Verify a TOTP code
        
        Args:
            username: Username to verify code for
            code: TOTP code to verify
            
        Returns:
            True if code is valid, False otherwise
        """
        if username not in self.user_secrets or not self.user_secrets[username]['enabled']:
            logger.warning(f"MFA verification failed: User {username} not found or MFA not enabled")
            return False
        
        secret_key = self.user_secrets[username]['secret']
        
        # Get current timestamp and calculate counter
        now = int(time.time())
        
        # Check current and adjacent time windows
        for offset in [-1, 0, 1]:
            counter = (now // self.period) + offset
            if self._generate_code(secret_key, counter) == code:
                # Update last used timestamp
                self.user_secrets[username]['last_used'] = datetime.now().isoformat()
                self._save_secrets()
                logger.debug(f"MFA code verified for user {username}")
                return True
        
        logger.warning(f"Invalid MFA code provided by user {username}")
        return False
    
    def _generate_code(self, secret_key: str, counter: int) -> str:
        """
        Generate a TOTP code
        
        Args:
            secret_key: Base32 encoded secret key
            counter: Time counter
            
        Returns:
            TOTP code
        """
        # Decode the base32 secret
        key = base64.b32decode(secret_key, True)
        
        # Convert counter to bytes (8 bytes, big-endian)
        counter_bytes = counter.to_bytes(8, byteorder='big')
        
        # Compute HMAC
        if self.algorithm == 'SHA1':
            hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        elif self.algorithm == 'SHA256':
            hmac_hash = hmac.new(key, counter_bytes, hashlib.sha256).digest()
        elif self.algorithm == 'SHA512':
            hmac_hash = hmac.new(key, counter_bytes, hashlib.sha512).digest()
        else:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")
        
        # Dynamic truncation
        offset = hmac_hash[-1] & 0x0F
        code = ((hmac_hash[offset] & 0x7F) << 24 |
                (hmac_hash[offset + 1] & 0xFF) << 16 |
                (hmac_hash[offset + 2] & 0xFF) << 8 |
                (hmac_hash[offset + 3] & 0xFF))
        
        # Modulo to get the specified number of digits
        code = code % (10 ** self.digit_length)
        
        # Left-pad with zeroes if necessary
        return str(code).zfill(self.digit_length)
    
    def disable_mfa(self, username: str) -> bool:
        """
        Disable MFA for a user
        
        Args:
            username: Username to disable MFA for
            
        Returns:
            True if successful, False otherwise
        """
        if username not in self.user_secrets:
            logger.warning(f"Cannot disable MFA: User {username} not found")
            return False
        
        self.user_secrets[username]['enabled'] = False
        self._save_secrets()
        logger.info(f"MFA disabled for user {username}")
        return True
    
    def enable_mfa(self, username: str) -> bool:
        """
        Enable MFA for a user if previously disabled
        
        Args:
            username: Username to enable MFA for
            
        Returns:
            True if successful, False otherwise
        """
        if username not in self.user_secrets:
            logger.warning(f"Cannot enable MFA: User {username} not found")
            return False
        
        self.user_secrets[username]['enabled'] = True
        self._save_secrets()
        logger.info(f"MFA enabled for user {username}")
        return True
    
    def get_mfa_status(self, username: str) -> Optional[Dict]:
        """
        Get MFA status for a user
        
        Args:
            username: Username to get status for
            
        Returns:
            Dictionary with MFA status or None if user not found
        """
        if username not in self.user_secrets:
            return None
        
        user_data = self.user_secrets[username].copy()
        # Remove the secret key from the response
        if 'secret' in user_data:
            del user_data['secret']
            
        return user_data
