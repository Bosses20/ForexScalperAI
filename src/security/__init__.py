"""
Security module for Forex Trading Bot
Implements authentication, encryption, and other security features
"""

from .api_key_manager import APIKeyManager
from .mfa_authenticator import MFAAuthenticator
from .encryption import EncryptionService
from .auth_middleware import JWTAuthMiddleware, APIKeyAuthMiddleware
from .security_hardening import SecurityHardening

__all__ = [
    'APIKeyManager',
    'MFAAuthenticator',
    'EncryptionService',
    'JWTAuthMiddleware',
    'APIKeyAuthMiddleware',
    'SecurityHardening'
]
