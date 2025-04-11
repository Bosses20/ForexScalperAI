"""
Encryption Service for the Forex Trading Bot
Provides secure encryption and decryption of sensitive data
"""

import os
import base64
import json
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger


class EncryptionService:
    """
    Provides encryption and decryption services using Fernet (AES-128-CBC)
    Handles key generation, rotation, and secure storage
    """
    
    def __init__(self, config: dict):
        """
        Initialize encryption service
        
        Args:
            config: Configuration dictionary with encryption settings
        """
        self.config = config
        self.key_file = config.get('encryption_key_path', 'config/encryption_keys.json')
        self.active_key_id = None
        self.keys = self._load_keys()
        
        # Create a new key if none exist
        if not self.keys:
            self._generate_new_key()
            
        logger.info("Encryption service initialized")
    
    def _load_keys(self) -> Dict:
        """
        Load encryption keys from key file
        
        Returns:
            Dictionary of encryption keys
        """
        if not os.path.exists(self.key_file):
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
            # Create empty keys file
            with open(self.key_file, 'w') as f:
                json.dump({"keys": {}, "active_key_id": None}, f)
            logger.info(f"Created new encryption keys file at {self.key_file}")
            return {"keys": {}, "active_key_id": None}
        
        try:
            with open(self.key_file, 'r') as f:
                keys_data = json.load(f)
            
            # Set active key
            self.active_key_id = keys_data.get('active_key_id')
            
            logger.debug(f"Loaded {len(keys_data.get('keys', {}))} encryption keys")
            return keys_data
        except Exception as e:
            logger.error(f"Error loading encryption keys: {str(e)}")
            return {"keys": {}, "active_key_id": None}
    
    def _save_keys(self) -> bool:
        """
        Save encryption keys to key file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
            
            # Update active key ID
            self.keys['active_key_id'] = self.active_key_id
            
            with open(self.key_file, 'w') as f:
                json.dump(self.keys, f, indent=2)
            logger.debug(f"Saved {len(self.keys.get('keys', {}))} encryption keys")
            return True
        except Exception as e:
            logger.error(f"Error saving encryption keys: {str(e)}")
            return False
    
    def _generate_new_key(self) -> str:
        """
        Generate a new encryption key
        
        Returns:
            ID of the generated key
        """
        # Generate a unique key ID
        key_id = base64.urlsafe_b64encode(os.urandom(9)).decode('utf-8')
        
        # Generate a new Fernet key
        key = Fernet.generate_key().decode('utf-8')
        
        # Store the key
        if 'keys' not in self.keys:
            self.keys['keys'] = {}
            
        self.keys['keys'][key_id] = {
            'key': key,
            'created_at': self._get_timestamp(),
            'rotated': False
        }
        
        # Set as active key
        self.active_key_id = key_id
        
        # Save keys
        self._save_keys()
        
        logger.info(f"Generated new encryption key {key_id}")
        return key_id
    
    def _get_timestamp(self) -> str:
        """
        Get current timestamp in ISO format
        
        Returns:
            ISO timestamp string
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _get_active_key(self) -> Optional[bytes]:
        """
        Get the currently active encryption key
        
        Returns:
            Active encryption key or None if no key is available
        """
        if not self.active_key_id or not self.keys.get('keys', {}):
            logger.warning("No active encryption key found")
            return None
            
        key_data = self.keys.get('keys', {}).get(self.active_key_id)
        if not key_data:
            logger.warning(f"Active key {self.active_key_id} not found in key store")
            return None
            
        return key_data.get('key').encode('utf-8')
    
    def rotate_key(self) -> bool:
        """
        Rotate encryption key (generate new key and set as active)
        
        Returns:
            True if successful, False otherwise
        """
        # Mark existing key as rotated
        if self.active_key_id and self.active_key_id in self.keys.get('keys', {}):
            self.keys['keys'][self.active_key_id]['rotated'] = True
            
        # Generate new key
        self._generate_new_key()
        
        logger.info("Encryption key rotated successfully")
        return True
    
    def encrypt_text(self, plaintext: str) -> str:
        """
        Encrypt a text string
        
        Args:
            plaintext: Text to encrypt
            
        Returns:
            Base64-encoded encrypted text
        """
        if not plaintext:
            return ""
            
        key = self._get_active_key()
        if not key:
            raise ValueError("No encryption key available")
            
        fernet = Fernet(key)
        
        try:
            # Add key ID to encrypted data for later decryption
            key_id_bytes = self.active_key_id.encode('utf-8')
            plaintext_bytes = plaintext.encode('utf-8')
            
            # Encrypt the plaintext
            encrypted_bytes = fernet.encrypt(plaintext_bytes)
            
            # Combine key ID and encrypted data
            combined = key_id_bytes + b':' + encrypted_bytes
            
            # Return as base64 string
            return base64.urlsafe_b64encode(combined).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            raise
    
    def decrypt_text(self, encrypted_text: str) -> str:
        """
        Decrypt an encrypted text string
        
        Args:
            encrypted_text: Base64-encoded encrypted text
            
        Returns:
            Decrypted plaintext
        """
        if not encrypted_text:
            return ""
            
        try:
            # Decode the combined data
            combined = base64.urlsafe_b64decode(encrypted_text.encode('utf-8'))
            
            # Split into key ID and encrypted data
            parts = combined.split(b':', 1)
            if len(parts) != 2:
                raise ValueError("Invalid encrypted data format")
                
            key_id = parts[0].decode('utf-8')
            encrypted_bytes = parts[1]
            
            # Get the key for this encrypted data
            if key_id not in self.keys.get('keys', {}):
                raise ValueError(f"Encryption key {key_id} not found")
                
            key = self.keys['keys'][key_id]['key'].encode('utf-8')
            
            # Decrypt the data
            fernet = Fernet(key)
            plaintext_bytes = fernet.decrypt(encrypted_bytes)
            
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            raise
    
    def encrypt_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in a dictionary
        
        Args:
            data: Dictionary with data to encrypt
            
        Returns:
            Dictionary with encrypted sensitive fields
        """
        # Define sensitive field names (customize as needed)
        sensitive_fields = [
            'password', 'secret', 'key', 'token', 'api_key', 'access_token',
            'refresh_token', 'private_key', 'mt5_password', 'mt5_login'
        ]
        
        encrypted_data = data.copy()
        
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                if isinstance(encrypted_data[field], str):
                    encrypted_data[field] = self.encrypt_text(encrypted_data[field])
                    
        return encrypted_data
    
    def decrypt_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt sensitive fields in a dictionary
        
        Args:
            data: Dictionary with encrypted data
            
        Returns:
            Dictionary with decrypted sensitive fields
        """
        # Define sensitive field names (customize as needed)
        sensitive_fields = [
            'password', 'secret', 'key', 'token', 'api_key', 'access_token',
            'refresh_token', 'private_key', 'mt5_password', 'mt5_login'
        ]
        
        decrypted_data = data.copy()
        
        for field in sensitive_fields:
            if field in decrypted_data and decrypted_data[field]:
                if isinstance(decrypted_data[field], str):
                    try:
                        decrypted_data[field] = self.decrypt_text(decrypted_data[field])
                    except Exception as e:
                        # If decryption fails, it might not be encrypted
                        logger.warning(f"Failed to decrypt field {field}: {str(e)}")
                    
        return decrypted_data
    
    def derive_key_from_password(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """
        Derive an encryption key from a password using PBKDF2
        
        Args:
            password: Password to derive key from
            salt: Optional salt for key derivation
            
        Returns:
            Derived key bytes
        """
        if salt is None:
            salt = os.urandom(16)
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
