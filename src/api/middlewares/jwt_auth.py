"""
JWT Authentication middleware for API security
Provides JWT-based authentication for secure API access
"""

import time
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from loguru import logger


# JWT Configuration
JWT_SECRET_KEY = "your-secret-key-placeholder"  # Will be replaced with a secure key from config
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Data to encode in token
        expires_delta: Optional expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token
    
    Args:
        token: JWT token to decode
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


class JWTBearer(HTTPBearer):
    """
    JWT Bearer token authentication dependency for FastAPI
    """
    
    def __init__(
        self, 
        auto_error: bool = True,
        scopes: Optional[List[str]] = None
    ):
        """
        Initialize JWT bearer authentication
        
        Args:
            auto_error: Whether to auto-raise exceptions
            scopes: Required scopes for this endpoint
        """
        super(JWTBearer, self).__init__(auto_error=auto_error)
        self.scopes = scopes or []
    
    async def __call__(self, request: Request) -> dict:
        """
        Validate and process JWT token
        
        Args:
            request: FastAPI request
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid
        """
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": "Bearer"},
                )
                
            payload = decode_token(credentials.credentials)
            
            # Check scopes if required
            if self.scopes:
                token_scopes = payload.get("scopes", [])
                if not any(scope in token_scopes for scope in self.scopes):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Insufficient permissions. Required scopes: {', '.join(self.scopes)}",
                    )
            
            return payload
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    JWT Authentication middleware for FastAPI
    Validates JWT tokens in request headers
    """
    
    def __init__(
        self, 
        app,
        secret_key: str,
        algorithm: str = JWT_ALGORITHM,
        exclude_paths: List[str] = None,
    ):
        """
        Initialize JWT authentication middleware
        
        Args:
            app: FastAPI application
            secret_key: Secret key for JWT signing
            algorithm: JWT algorithm to use
            exclude_paths: List of paths to exclude from authentication
        """
        super().__init__(app)
        global JWT_SECRET_KEY
        JWT_SECRET_KEY = secret_key
        global JWT_ALGORITHM
        JWT_ALGORITHM = algorithm
        self.exclude_paths = exclude_paths or [
            "/health", 
            "/discover", 
            "/api-docs", 
            "/openapi.json",
            "/connection-qrcode",
            "/auth/login"
        ]
        
        logger.info("JWT Authentication middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with JWT authentication
        
        Args:
            request: FastAPI request
            call_next: Next middleware in chain
            
        Returns:
            Response or authentication error
        """
        # Skip authentication for excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return Response(
                status_code=401,
                content="Unauthorized: Missing authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check Bearer scheme
        parts = auth_header.split()
        if parts[0].lower() != "bearer" or len(parts) < 2:
            return Response(
                status_code=401,
                content="Unauthorized: Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = parts[1]
        
        # Validate token
        try:
            payload = decode_token(token)
            
            # Add user info to request state
            request.state.user = payload
            
            # Process request
            return await call_next(request)
            
        except HTTPException as exc:
            return Response(
                status_code=exc.status_code,
                content=exc.detail,
                headers=exc.headers or {"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"JWT authentication error: {str(e)}")
            return Response(
                status_code=401,
                content="Unauthorized: Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
