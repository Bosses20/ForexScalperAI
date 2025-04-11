"""
API Key Manager for secure API authentication
Handles generation, validation, and management of API keys
"""

import os
import uuid
import json
import time
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger

from .encryption import EncryptionService


class APIKeyManager:
    """
    Manages API key creation, validation, and revocation
    Implements secure key storage with encryption
    """
    
    def __init__(self, config: dict, encryption_service: Optional['EncryptionService'] = None):
        """
        Initialize API Key Manager
        
        Args:
            config: Configuration dictionary with API key settings
            encryption_service: Optional encryption service for key storage
        """
        self.config = config
        self.keys_file = config.get('api_keys_path', 'config/api_keys.json')
        self.api_keys = self._load_keys()
        self.default_expiry_days = config.get('api_key_expiry_days', 90)
        self.key_prefix = config.get('api_key_prefix', 'ftb_')
        self.allowed_scopes = config.get('api_key_scopes', [
            'read', 'write', 'trade', 'admin', 'system', 'report'
        ])
        self.encryption_service = encryption_service
        
        logger.info("API Key Manager initialized")
    
    def _load_keys(self) -> Dict:
        """
        Load API keys from keys file
        
        Returns:
            Dictionary of API keys
        """
        if not os.path.exists(self.keys_file):
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.keys_file), exist_ok=True)
            # Create empty keys file
            with open(self.keys_file, 'w') as f:
                json.dump({}, f)
            logger.info(f"Created new API keys file at {self.keys_file}")
            return {}
        
        try:
            with open(self.keys_file, 'r') as f:
                keys_data = json.load(f)
            logger.debug(f"Loaded {len(keys_data)} API keys")
            return keys_data
        except Exception as e:
            logger.error(f"Error loading API keys: {str(e)}")
            return {}
    
    def _save_keys(self) -> bool:
        """
        Save API keys to keys file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.keys_file), exist_ok=True)
            
            with open(self.keys_file, 'w') as f:
                json.dump(self.api_keys, f, indent=2)
            logger.debug(f"Saved {len(self.api_keys)} API keys")
            return True
        except Exception as e:
            logger.error(f"Error saving API keys: {str(e)}")
            return False
    
    def create_key(self, user_id: str, description: str = "", scopes: List[str] = None, 
                   expires_in_days: int = None) -> Tuple[str, str]:
        """
        Create a new API key for a user
        
        Args:
            user_id: User ID to create key for
            description: Description of the key purpose
            scopes: List of permission scopes for this key
            expires_in_days: Days until key expiration
            
        Returns:
            Tuple of (key_id, api_key)
        """
        # Generate a unique key ID
        key_id = str(uuid.uuid4())
        
        # Generate API key (prefix + 32 random bytes base64 encoded)
        api_key_bytes = os.urandom(32)
        api_key = self.key_prefix + base64.urlsafe_b64encode(api_key_bytes).decode('utf-8').rstrip('=')
        
        # Generate key hash for storage
        key_hash = self._hash_key(api_key)
        
        # Set default scopes if none provided
        if scopes is None:
            scopes = ['read']  # Default minimal scope
            
        # Validate scopes
        for scope in scopes:
            if scope not in self.allowed_scopes:
                raise ValueError(f"Invalid scope: {scope}. Allowed scopes: {self.allowed_scopes}")
        
        # Set expiration
        if expires_in_days is None:
            expires_in_days = self.default_expiry_days
            
        expiry_date = (datetime.now() + timedelta(days=expires_in_days)).isoformat()
        
        # Create key record
        key_data = {
            'key_hash': key_hash,
            'user_id': user_id,
            'description': description,
            'scopes': scopes,
            'created_at': datetime.now().isoformat(),
            'expires_at': expiry_date,
            'last_used': None,
            'is_active': True
        }
        
        # Encrypt sensitive data if encryption service available
        if self.encryption_service:
            # Encrypt the user_id field
            key_data['user_id'] = self.encryption_service.encrypt_text(user_id)
            # Mark as encrypted
            key_data['encrypted'] = True
        
        # Store key in database
        self.api_keys[key_id] = key_data
        self._save_keys()
        
        logger.info(f"Created new API key for user {user_id} with scopes {scopes}")
        
        # Return the key ID and API key
        # Note: The API key is only returned once at creation
        return key_id, api_key
    
    def _hash_key(self, api_key: str) -> str:
        """
        Create a secure hash of an API key for storage
        
        Args:
            api_key: API key to hash
            
        Returns:
            Secure hash of the API key
        """
        # Use SHA-256 for hashing
        # In a production environment, consider using a specialized password
        # hashing algorithm like bcrypt, Argon2, or PBKDF2
        return hashlib.sha256(api_key.encode('utf-8')).hexdigest()
    
    def validate_key(self, api_key: str) -> Tuple[bool, Optional[Dict]]:
        """
        Validate an API key
        
        Args:
            api_key: API key to validate
            
        Returns:
            Tuple of (is_valid, key_data)
        """
        if not api_key:
            logger.warning("Empty API key provided")
            return False, None
        
        # Check key format (starts with correct prefix)
        if not api_key.startswith(self.key_prefix):
            logger.warning(f"Invalid API key format: doesn't start with {self.key_prefix}")
            return False, None
            
        # Calculate hash of provided key
        key_hash = self._hash_key(api_key)
        
        # Look up key by hash
        key_id = None
        key_data = None
        
        for k_id, k_data in self.api_keys.items():
            if k_data.get('key_hash') == key_hash:
                key_id = k_id
                key_data = k_data.copy()
                break
                
        if not key_data:
            logger.warning("API key not found")
            return False, None
            
        # Check if key is active
        if not key_data.get('is_active', False):
            logger.warning(f"API key {key_id} is inactive")
            return False, None
            
        # Check if key has expired
        expires_at = datetime.fromisoformat(key_data.get('expires_at'))
        if expires_at < datetime.now():
            logger.warning(f"API key {key_id} has expired")
            
            # Automatically deactivate expired keys
            self.api_keys[key_id]['is_active'] = False
            self._save_keys()
            
            return False, None
            
        # Decrypt fields if needed and encryption service is available
        if key_data.get('encrypted', False) and self.encryption_service:
            user_id = key_data.get('user_id', '')
            try:
                key_data['user_id'] = self.encryption_service.decrypt_text(user_id)
            except Exception as e:
                logger.error(f"Error decrypting user_id for API key {key_id}: {str(e)}")
        
        # Remove sensitive fields from returned data
        if 'key_hash' in key_data:
            del key_data['key_hash']
        if 'encrypted' in key_data:
            del key_data['encrypted']
            
        # Update last used timestamp
        self.api_keys[key_id]['last_used'] = datetime.now().isoformat()
        self._save_keys()
        
        logger.debug(f"API key {key_id} validated successfully")
        
        # Return success and key data
        return True, key_data
    
    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke an API key
        
        Args:
            key_id: ID of the key to revoke
            
        Returns:
            True if key was revoked, False otherwise
        """
        if key_id not in self.api_keys:
            logger.warning(f"API key {key_id} not found")
            return False
            
        self.api_keys[key_id]['is_active'] = False
        self._save_keys()
        
        logger.info(f"API key {key_id} revoked")
        return True
    
    def list_keys(self, user_id: Optional[str] = None) -> List[Dict]:
        """
        List API keys, optionally filtered by user
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of API key data dictionaries
        """
        result = []
        
        for key_id, key_data in self.api_keys.items():
            # Create a copy of the key data
            key_info = key_data.copy()
            
            # Decrypt user_id if needed
            stored_user_id = key_info.get('user_id', '')
            if key_info.get('encrypted', False) and self.encryption_service:
                try:
                    stored_user_id = self.encryption_service.decrypt_text(stored_user_id)
                except Exception as e:
                    logger.error(f"Error decrypting user_id for API key {key_id}: {str(e)}")
            
            # Filter by user_id if provided
            if user_id and stored_user_id != user_id:
                continue
                
            # Add key_id to the data
            key_info['key_id'] = key_id
            
            # Remove sensitive fields
            if 'key_hash' in key_info:
                del key_info['key_hash']
            if 'encrypted' in key_info:
                del key_info['encrypted']
                
            result.append(key_info)
            
        logger.debug(f"Listed {len(result)} API keys")
        return result
    
    def update_key(self, key_id: str, description: Optional[str] = None, 
                  scopes: Optional[List[str]] = None, 
                  is_active: Optional[bool] = None) -> bool:
        """
        Update API key information
        
        Args:
            key_id: ID of the key to update
            description: New description (optional)
            scopes: New scopes (optional)
            is_active: New active status (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if key_id not in self.api_keys:
            logger.warning(f"API key {key_id} not found")
            return False
            
        # Update description if provided
        if description is not None:
            self.api_keys[key_id]['description'] = description
            
        # Update scopes if provided
        if scopes is not None:
            # Validate scopes
            for scope in scopes:
                if scope not in self.allowed_scopes:
                    raise ValueError(f"Invalid scope: {scope}. Allowed scopes: {self.allowed_scopes}")
                    
            self.api_keys[key_id]['scopes'] = scopes
            
        # Update active status if provided
        if is_active is not None:
            self.api_keys[key_id]['is_active'] = is_active
            
        self._save_keys()
        
        logger.info(f"Updated API key {key_id}")
        return True
    
    def rotate_key(self, key_id: str) -> Tuple[bool, Optional[str]]:
        """
        Rotate an API key (create new key with same settings and revoke old one)
        
        Args:
            key_id: ID of the key to rotate
            
        Returns:
            Tuple of (success, new_api_key)
        """
        if key_id not in self.api_keys:
            logger.warning(f"API key {key_id} not found")
            return False, None
            
        # Get original key data
        key_data = self.api_keys[key_id]
        
        # Decrypt user_id if needed
        user_id = key_data.get('user_id', '')
        if key_data.get('encrypted', False) and self.encryption_service:
            try:
                user_id = self.encryption_service.decrypt_text(user_id)
            except Exception as e:
                logger.error(f"Error decrypting user_id for API key {key_id}: {str(e)}")
                return False, None
        
        # Get expiry information
        expires_at = datetime.fromisoformat(key_data.get('expires_at'))
        days_remaining = (expires_at - datetime.now()).days
        expires_in_days = max(1, days_remaining)  # At least 1 day
        
        # Create new key with same settings
        new_key_id, new_api_key = self.create_key(
            user_id=user_id,
            description=f"{key_data.get('description', '')} (rotated)",
            scopes=key_data.get('scopes', ['read']),
            expires_in_days=expires_in_days
        )
        
        # Revoke old key
        self.revoke_key(key_id)
        
        logger.info(f"Rotated API key {key_id} to new key {new_key_id}")
        
        return True, new_api_key
    
    def extend_expiry(self, key_id: str, additional_days: int) -> bool:
        """
        Extend the expiry of an API key
        
        Args:
            key_id: ID of the key to extend
            additional_days: Number of days to extend by
            
        Returns:
            True if successful, False otherwise
        """
        if key_id not in self.api_keys:
            logger.warning(f"API key {key_id} not found")
            return False
            
        if additional_days <= 0:
            logger.warning(f"Additional days must be positive: {additional_days}")
            return False
            
        # Get current expiry
        expires_at = datetime.fromisoformat(self.api_keys[key_id]['expires_at'])
        
        # Calculate new expiry
        new_expiry = expires_at + timedelta(days=additional_days)
        
        # Update expiry
        self.api_keys[key_id]['expires_at'] = new_expiry.isoformat()
        
        self._save_keys()
        
        logger.info(f"Extended API key {key_id} expiry by {additional_days} days to {new_expiry}")
        return True
    
    def generate_signature(self, api_key: str, data: str, timestamp: Optional[int] = None) -> Tuple[str, int]:
        """
        Generate an HMAC signature for authenticating requests
        
        Args:
            api_key: API key to use for signing
            data: Data to sign (typically request body or query string)
            timestamp: Optional timestamp (current time if not provided)
            
        Returns:
            Tuple of (signature, timestamp)
        """
        if timestamp is None:
            timestamp = int(time.time())
            
        # Validate key and get key data
        is_valid, key_data = self.validate_key(api_key)
        if not is_valid or not key_data:
            raise ValueError("Invalid API key")
            
        # Prepare string to sign
        string_to_sign = f"{timestamp}{data}"
        
        # Sign with HMAC-SHA256 using API key as secret
        signature = hmac.new(
            api_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature, timestamp
    
    def verify_signature(self, api_key: str, data: str, signature: str, timestamp: int, 
                        max_age_seconds: int = 300) -> bool:
        """
        Verify an HMAC signature for request authentication
        
        Args:
            api_key: API key used for signing
            data: Data that was signed
            signature: Signature to verify
            timestamp: Timestamp used in signature
            max_age_seconds: Maximum age of signature in seconds
            
        Returns:
            True if signature is valid, False otherwise
        """
        # Check timestamp age
        current_time = int(time.time())
        if current_time - timestamp > max_age_seconds:
            logger.warning(f"Signature expired: {current_time - timestamp} seconds old")
            return False
            
        # Generate expected signature
        expected_signature, _ = self.generate_signature(api_key, data, timestamp)
        
        # Compare signatures (constant-time comparison to prevent timing attacks)
        return hmac.compare_digest(signature, expected_signature)
