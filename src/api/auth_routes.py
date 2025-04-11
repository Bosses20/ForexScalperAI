"""
Authentication routes for the API server
Provides login, refresh token, and user management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from loguru import logger

from src.security.api_key_manager import APIKeyManager
from src.api.middlewares.jwt_auth import create_access_token, JWTBearer


# Request and response models
class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str
    expires_in: int
    scopes: List[str]


class UserCredentials(BaseModel):
    """User credentials model"""
    username: str
    password: str


class APIKeyResponse(BaseModel):
    """API key response model"""
    key_id: str
    api_key: str
    description: str
    scopes: List[str]
    expires_at: str


def create_auth_router(api_key_manager: APIKeyManager, user_manager, config: dict):
    """
    Create authentication router
    
    Args:
        api_key_manager: API key manager instance
        user_manager: User manager instance
        config: Authentication configuration
        
    Returns:
        FastAPI router with authentication routes
    """
    router = APIRouter(prefix="/auth", tags=["authentication"])
    
    jwt_expires_minutes = config.get("jwt_expires_minutes", 30)
    admin_bearer = JWTBearer(scopes=["admin"])
    
    @router.post("/login", response_model=TokenResponse)
    async def login(form_data: OAuth2PasswordRequestForm = Depends()):
        """
        Login endpoint
        """
        # Validate user credentials
        user = await user_manager.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        token_data = {
            "sub": user.get("id"),
            "username": user.get("username"),
            "scopes": user.get("scopes", ["read"])
        }
        
        expires_delta = timedelta(minutes=jwt_expires_minutes)
        access_token = create_access_token(token_data, expires_delta)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": jwt_expires_minutes * 60,
            "scopes": user.get("scopes", ["read"])
        }
    
    @router.post("/token", response_model=TokenResponse)
    async def create_token(credentials: UserCredentials):
        """
        Create access token from username/password
        """
        # Validate user credentials
        user = await user_manager.authenticate_user(credentials.username, credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        token_data = {
            "sub": user.get("id"),
            "username": user.get("username"),
            "scopes": user.get("scopes", ["read"])
        }
        
        expires_delta = timedelta(minutes=jwt_expires_minutes)
        access_token = create_access_token(token_data, expires_delta)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": jwt_expires_minutes * 60,
            "scopes": user.get("scopes", ["read"])
        }
    
    @router.get("/api-keys", dependencies=[Depends(admin_bearer)])
    async def list_api_keys(user = Depends(admin_bearer)):
        """
        List API keys for the authenticated user
        """
        user_id = user.get("sub")
        api_keys = api_key_manager.list_keys(user_id)
        
        # Don't return sensitive info
        for key in api_keys:
            if "key_hash" in key:
                del key["key_hash"]
        
        return api_keys
    
    @router.post("/api-keys", response_model=APIKeyResponse, dependencies=[Depends(admin_bearer)])
    async def create_api_key(
        description: str = "",
        scopes: Optional[List[str]] = None,
        user = Depends(admin_bearer)
    ):
        """
        Create a new API key for the authenticated user
        """
        user_id = user.get("sub")
        scopes = scopes or ["read"]
        
        key_id, api_key = api_key_manager.create_key(
            user_id=user_id,
            description=description,
            scopes=scopes
        )
        
        key_data = api_key_manager.list_keys(user_id)
        key_info = next((k for k in key_data if k.get("key_id") == key_id), {})
        
        return {
            "key_id": key_id,
            "api_key": api_key,  # Important: this is the only time the key is returned
            "description": key_info.get("description", description),
            "scopes": key_info.get("scopes", scopes),
            "expires_at": key_info.get("expires_at", "")
        }
    
    @router.delete("/api-keys/{key_id}", dependencies=[Depends(admin_bearer)])
    async def revoke_api_key(key_id: str, user = Depends(admin_bearer)):
        """
        Revoke an API key
        """
        # Only allow users to revoke their own keys
        user_id = user.get("sub")
        keys = api_key_manager.list_keys(user_id)
        
        if not any(k.get("key_id") == key_id for k in keys):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        success = api_key_manager.revoke_key(key_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to revoke API key"
            )
        
        return {"message": "API key revoked successfully"}
    
    return router
