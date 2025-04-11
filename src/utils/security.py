"""
Security utilities for the Forex Trading Bot

Handles security-related functions including token generation,
encryption/decryption, and QR code generation.
"""

import base64
import logging
import os
from datetime import datetime, timedelta
from io import BytesIO
from typing import Dict, Optional, Tuple, Union

import jwt
import qrcode
import qrcode.image.svg
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config.settings import get_settings

logger = logging.getLogger(__name__)

def generate_jwt_token(user_data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a JWT token for authentication
    
    Args:
        user_data: The user data to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        str: The encoded JWT token
    """
    settings = get_settings()
    
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        
    expire = datetime.utcnow() + expires_delta
    to_encode = user_data.copy()
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.secret_key, 
        algorithm=settings.algorithm
    )
    
    return encoded_jwt

def verify_jwt_token(token: str) -> Dict:
    """
    Verify a JWT token and return the decoded payload
    
    Args:
        token: The JWT token to verify
        
    Returns:
        Dict: The decoded token payload
        
    Raises:
        jwt.PyJWTError: If the token is invalid
    """
    settings = get_settings()
    return jwt.decode(
        token, 
        settings.secret_key, 
        algorithms=[settings.algorithm]
    )

def generate_encryption_key(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Generate an encryption key from a password using PBKDF2
    
    Args:
        password: The password to derive the key from
        salt: Optional salt for key derivation, generated if not provided
        
    Returns:
        Tuple[bytes, bytes]: The derived key and the salt used
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
    return key, salt

def encrypt_data(data: Union[str, bytes], key: bytes) -> bytes:
    """
    Encrypt data using Fernet symmetric encryption
    
    Args:
        data: The data to encrypt (string or bytes)
        key: The encryption key
        
    Returns:
        bytes: The encrypted data
    """
    if isinstance(data, str):
        data = data.encode()
        
    f = Fernet(key)
    return f.encrypt(data)

def decrypt_data(encrypted_data: bytes, key: bytes) -> bytes:
    """
    Decrypt data using Fernet symmetric encryption
    
    Args:
        encrypted_data: The encrypted data
        key: The encryption key
        
    Returns:
        bytes: The decrypted data
        
    Raises:
        cryptography.fernet.InvalidToken: If the data cannot be decrypted
    """
    f = Fernet(key)
    return f.decrypt(encrypted_data)

def generate_qr_code(data: str) -> str:
    """
    Generate a QR code as SVG for the provided data
    
    Args:
        data: The data to encode in the QR code
        
    Returns:
        str: The QR code as an SVG data URI
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create an SVG image
    factory = qrcode.image.svg.SvgPathImage
    img = qr.make_image(fill_color="black", back_color="white", image_factory=factory)
    
    # Convert to string
    buffer = BytesIO()
    img.save(buffer)
    svg_str = buffer.getvalue().decode('utf-8')
    
    return svg_str

def secure_hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Create a secure hash of a password
    
    Args:
        password: The password to hash
        salt: Optional salt for the hash, generated if not provided
        
    Returns:
        Tuple[bytes, bytes]: The password hash and salt
    """
    if salt is None:
        salt = os.urandom(16)
        
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    password_hash = kdf.derive(password.encode())
    return password_hash, salt

def verify_password(password: str, password_hash: bytes, salt: bytes) -> bool:
    """
    Verify a password against a hash
    
    Args:
        password: The password to verify
        password_hash: The stored password hash
        salt: The salt used for hashing
        
    Returns:
        bool: True if the password matches, False otherwise
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    try:
        kdf.verify(password.encode(), password_hash)
        return True
    except Exception:
        return False
