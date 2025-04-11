"""
Authentication middleware for securing API endpoints
Provides JWT and API key authentication for web APIs
"""

import jwt
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from functools import wraps
from loguru import logger

class JWTAuthMiddleware:
    """
    JWT-based authentication middleware for API endpoints
    Provides token generation, validation, and role-based access control
    """
    
    def __init__(self, config: dict):
        """
        Initialize JWT authentication middleware
        
        Args:
            config: Configuration dictionary with JWT settings
        """
        self.config = config
        self.secret_key = config.get('jwt_secret_key', 'your-jwt-secret-key')
        self.token_expiry = config.get('jwt_token_expiry', 24)  # hours
        self.refresh_token_expiry = config.get('jwt_refresh_expiry', 7)  # days
        self.algorithm = config.get('jwt_algorithm', 'HS256')
        self.issuer = config.get('jwt_issuer', 'forex-trading-bot')
        
        logger.info("JWT Authentication middleware initialized")
    
    def generate_tokens(self, user_id: str, username: str, 
                       roles: List[str] = None) -> Dict[str, str]:
        """
        Generate JWT access and refresh tokens
        
        Args:
            user_id: Unique user identifier
            username: Username for token payload
            roles: List of user roles for permissions
            
        Returns:
            Dictionary with access_token and refresh_token
        """
        if roles is None:
            roles = ['user']
            
        # Current timestamp
        now = datetime.utcnow()
        
        # Access token payload
        access_payload = {
            'sub': user_id,
            'username': username,
            'roles': roles,
            'iat': now,
            'exp': now + timedelta(hours=self.token_expiry),
            'iss': self.issuer,
            'type': 'access'
        }
        
        # Refresh token payload
        refresh_payload = {
            'sub': user_id,
            'iat': now,
            'exp': now + timedelta(days=self.refresh_token_expiry),
            'iss': self.issuer,
            'type': 'refresh'
        }
        
        # Generate tokens
        access_token = jwt.encode(
            access_payload,
            self.secret_key,
            algorithm=self.algorithm
        )
        
        refresh_token = jwt.encode(
            refresh_payload,
            self.secret_key,
            algorithm=self.algorithm
        )
        
        logger.debug(f"Generated JWT tokens for user {username}")
        
        # Return as dictionary
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': self.token_expiry * 3600  # in seconds
        }
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Generate a new access token using a refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Dictionary with new access_token
        """
        try:
            # Decode and validate refresh token
            payload = jwt.decode(
                refresh_token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={'verify_signature': True}
            )
            
            # Check token type
            if payload.get('type') != 'refresh':
                raise ValueError("Invalid token type")
                
            # Get user_id from token
            user_id = payload.get('sub')
            if not user_id:
                raise ValueError("Invalid token payload")
                
            # TODO: In a real implementation, fetch user data from database
            # For now, use limited information from the token
            
            # Generate new access token
            now = datetime.utcnow()
            access_payload = {
                'sub': user_id,
                'iat': now,
                'exp': now + timedelta(hours=self.token_expiry),
                'iss': self.issuer,
                'type': 'access'
            }
            
            access_token = jwt.encode(
                access_payload,
                self.secret_key,
                algorithm=self.algorithm
            )
            
            logger.debug(f"Refreshed access token for user {user_id}")
            
            return {
                'access_token': access_token,
                'expires_in': self.token_expiry * 3600  # in seconds
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token has expired")
            raise ValueError("Refresh token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {str(e)}")
            raise ValueError("Invalid refresh token")
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise
    
    def validate_token(self, token: str) -> Dict:
        """
        Validate a JWT token
        
        Args:
            token: JWT token to validate
            
        Returns:
            Token payload if valid
            
        Raises:
            ValueError: If token is invalid or expired
        """
        try:
            # Decode and validate token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={'verify_signature': True}
            )
            
            logger.debug(f"Validated JWT token for user {payload.get('sub')}")
            
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            raise ValueError("Token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            raise ValueError("Invalid token")
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            raise
    
    def require_auth(self, roles: List[str] = None):
        """
        Decorator for requiring JWT authentication
        
        Args:
            roles: List of required roles for access
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract request object (framework-specific)
                # This example assumes Flask-like request
                from flask import request
                
                # Get token from Authorization header
                auth_header = request.headers.get('Authorization')
                if not auth_header or not auth_header.startswith('Bearer '):
                    return {"error": "Authentication required"}, 401
                
                token = auth_header.split(' ')[1]
                
                try:
                    # Validate token
                    payload = self.validate_token(token)
                    
                    # Check token type
                    if payload.get('type') != 'access':
                        return {"error": "Invalid token type"}, 401
                    
                    # Check roles if required
                    if roles:
                        user_roles = payload.get('roles', [])
                        has_role = any(role in user_roles for role in roles)
                        if not has_role:
                            return {"error": "Insufficient permissions"}, 403
                    
                    # Add user info to request
                    request.user = payload
                    
                    # Call original function
                    return func(*args, **kwargs)
                    
                except ValueError as e:
                    return {"error": str(e)}, 401
                    
            return wrapper
        return decorator


class APIKeyAuthMiddleware:
    """
    API key authentication middleware for API endpoints
    Integrates with APIKeyManager for validation
    """
    
    def __init__(self, config: dict, api_key_manager):
        """
        Initialize API key authentication middleware
        
        Args:
            config: Configuration dictionary with API key settings
            api_key_manager: Instance of APIKeyManager
        """
        self.config = config
        self.api_key_manager = api_key_manager
        self.header_name = config.get('api_key_header', 'X-API-Key')
        
        logger.info("API Key authentication middleware initialized")
    
    def require_api_key(self, scopes: List[str] = None):
        """
        Decorator for requiring API key authentication
        
        Args:
            scopes: List of required scopes for access
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract request object (framework-specific)
                # This example assumes Flask-like request
                from flask import request
                
                # Get API key from header
                api_key = request.headers.get(self.header_name)
                if not api_key:
                    return {"error": "API key required"}, 401
                
                try:
                    # Validate API key
                    is_valid, key_data = self.api_key_manager.validate_key(api_key)
                    
                    if not is_valid or not key_data:
                        return {"error": "Invalid API key"}, 401
                    
                    # Check scopes if required
                    if scopes:
                        key_scopes = key_data.get('scopes', [])
                        has_scope = any(scope in key_scopes for scope in scopes)
                        if not has_scope:
                            return {"error": "Insufficient permissions"}, 403
                    
                    # Add API key info to request
                    request.api_key_data = key_data
                    
                    # Call original function
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    logger.error(f"API key authentication error: {str(e)}")
                    return {"error": "Authentication failed"}, 401
                    
            return wrapper
        return decorator
    
    def verify_hmac_signature(self, max_age_seconds: int = 300):
        """
        Decorator for verifying HMAC signatures of API requests
        
        Args:
            max_age_seconds: Maximum age of signature in seconds
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract request object (framework-specific)
                # This example assumes Flask-like request
                from flask import request
                
                # Get required headers
                api_key = request.headers.get(self.header_name)
                signature = request.headers.get('X-Signature')
                timestamp = request.headers.get('X-Timestamp')
                
                if not all([api_key, signature, timestamp]):
                    return {"error": "Missing authentication headers"}, 401
                
                try:
                    # Convert timestamp to int
                    timestamp = int(timestamp)
                    
                    # Get request body or query string
                    if request.is_json:
                        data = json.dumps(request.json)
                    else:
                        data = request.query_string.decode('utf-8')
                    
                    # Verify signature
                    is_valid = self.api_key_manager.verify_signature(
                        api_key, data, signature, timestamp, max_age_seconds
                    )
                    
                    if not is_valid:
                        return {"error": "Invalid signature"}, 401
                    
                    # Call original function
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    logger.error(f"Signature verification error: {str(e)}")
                    return {"error": "Authentication failed"}, 401
                    
            return wrapper
        return decorator
