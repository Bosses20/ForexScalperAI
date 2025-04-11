"""
Rate limiting middleware for API protection
Prevents abuse by limiting the number of requests per client
"""

import time
from typing import Dict, List, Tuple, Optional, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class RateLimiter(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI
    Limits requests based on client IP or other identifier
    """
    
    def __init__(
        self, 
        app, 
        rate_limit_per_minute: int = 60,
        whitelist_ips: List[str] = None,
        whitelist_paths: List[str] = None,
        identifier_extractor: Optional[Callable[[Request], str]] = None
    ):
        """
        Initialize rate limiter
        
        Args:
            app: FastAPI application
            rate_limit_per_minute: Maximum requests per minute
            whitelist_ips: List of IPs exempt from rate limiting
            whitelist_paths: List of API paths exempt from rate limiting
            identifier_extractor: Optional function to extract client identifier
        """
        super().__init__(app)
        self.rate_limit = rate_limit_per_minute
        self.window_size = 60  # seconds
        self.request_history: Dict[str, List[float]] = {}
        self.whitelist_ips = whitelist_ips or ["127.0.0.1", "::1", "localhost"]
        self.whitelist_paths = whitelist_paths or ["/health", "/discover", "/connection-qrcode"]
        self.identifier_extractor = identifier_extractor
        
        logger.info(f"Rate limiter initialized: {rate_limit_per_minute} requests per minute")
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting
        
        Args:
            request: FastAPI request
            call_next: Next middleware in chain
            
        Returns:
            Response or rate limit exceeded error
        """
        # Skip rate limiting for whitelisted paths
        path = request.url.path
        if any(path.startswith(wl_path) for wl_path in self.whitelist_paths):
            return await call_next(request)
        
        # Get client identifier (IP address by default)
        if self.identifier_extractor:
            client_id = self.identifier_extractor(request)
        else:
            client_id = self._get_client_ip(request)
        
        # Skip rate limiting for whitelisted IPs
        if client_id in self.whitelist_ips:
            return await call_next(request)
        
        # Check rate limit
        current_time = time.time()
        
        # Initialize history for new clients
        if client_id not in self.request_history:
            self.request_history[client_id] = []
        
        # Clean up old requests outside the window
        self.request_history[client_id] = [
            t for t in self.request_history[client_id] 
            if current_time - t < self.window_size
        ]
        
        # Check if rate limit exceeded
        if len(self.request_history[client_id]) >= self.rate_limit:
            logger.warning(f"Rate limit exceeded for {client_id}: {len(self.request_history[client_id])} requests")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "detail": f"Rate limit of {self.rate_limit} requests per minute exceeded"
                }
            )
        
        # Add current request to history
        self.request_history[client_id].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        remaining = self.rate_limit - len(self.request_history[client_id])
        
        # Cast response to appropriate type if needed
        if hasattr(response, "headers"):
            response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_size))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request
        
        Args:
            request: FastAPI request
            
        Returns:
            Client IP address
        """
        # First check X-Forwarded-For header (for proxied requests)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to direct client
        client_host = request.client.host if request.client else "unknown"
        return client_host
