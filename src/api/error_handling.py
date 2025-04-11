"""
API Error Handling Module

This module provides standardized error handling for the API, ensuring
consistent error responses with detailed information to help clients
troubleshoot issues.
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Dict, Any, Optional, List, Union
import logging
import traceback
import uuid
import time

# Set up logger
logger = logging.getLogger(__name__)

# Error codes and messages
ERROR_CODES = {
    # Authentication errors (40x)
    "INVALID_CREDENTIALS": {"code": "AUTH_001", "status_code": 401, "message": "Invalid username or password"},
    "EXPIRED_TOKEN": {"code": "AUTH_002", "status_code": 401, "message": "Authentication token has expired"},
    "INVALID_TOKEN": {"code": "AUTH_003", "status_code": 401, "message": "Invalid authentication token"},
    "UNAUTHORIZED": {"code": "AUTH_004", "status_code": 401, "message": "Unauthorized access"},
    "FORBIDDEN": {"code": "AUTH_005", "status_code": 403, "message": "Access forbidden"},
    
    # Validation errors (40x)
    "VALIDATION_ERROR": {"code": "VAL_001", "status_code": 400, "message": "Request validation failed"},
    "INVALID_REQUEST": {"code": "VAL_002", "status_code": 400, "message": "Invalid request format"},
    "MISSING_PARAMETER": {"code": "VAL_003", "status_code": 400, "message": "Required parameter missing"},
    "INVALID_PARAMETER": {"code": "VAL_004", "status_code": 400, "message": "Invalid parameter value"},
    
    # Resource errors (40x)
    "NOT_FOUND": {"code": "RES_001", "status_code": 404, "message": "Resource not found"},
    "ALREADY_EXISTS": {"code": "RES_002", "status_code": 409, "message": "Resource already exists"},
    
    # Business logic errors (40x)
    "INVALID_COMMAND": {"code": "BIZ_001", "status_code": 400, "message": "Invalid command"},
    "OPERATION_NOT_PERMITTED": {"code": "BIZ_002", "status_code": 400, "message": "Operation not permitted"},
    "INVALID_TRADE_PARAMETERS": {"code": "BIZ_003", "status_code": 400, "message": "Invalid trade parameters"},
    "TRADE_EXECUTION_FAILED": {"code": "BIZ_004", "status_code": 400, "message": "Trade execution failed"},
    "SETTINGS_UPDATE_FAILED": {"code": "BIZ_005", "status_code": 400, "message": "Settings update failed"},
    
    # Server errors (50x)
    "SERVER_ERROR": {"code": "SRV_001", "status_code": 500, "message": "Internal server error"},
    "SERVICE_UNAVAILABLE": {"code": "SRV_002", "status_code": 503, "message": "Service temporarily unavailable"},
    "BOT_NOT_RUNNING": {"code": "SRV_003", "status_code": 503, "message": "Trading bot is not running"},
    "BOT_IS_PAUSED": {"code": "SRV_004", "status_code": 503, "message": "Trading bot is paused"},
    "EXECUTION_ERROR": {"code": "SRV_005", "status_code": 500, "message": "Command execution failed"},
}

class ErrorResponse:
    """Class for generating standardized error responses"""
    
    @staticmethod
    def create(
        error_type: str,
        detail: Optional[str] = None,
        field: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a standardized error response
        
        Args:
            error_type: The type of error from ERROR_CODES
            detail: Detailed error message (overrides default if provided)
            field: Field that caused the error (for validation errors)
            data: Additional data to include in the response
            
        Returns:
            Dict containing the error response
        """
        if error_type not in ERROR_CODES:
            error_type = "SERVER_ERROR"
            
        error_info = ERROR_CODES[error_type]
        status_code = error_info["status_code"]
        
        # Create the error response
        response = {
            "error": {
                "code": error_info["code"],
                "type": error_type,
                "message": detail or error_info["message"],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "request_id": str(uuid.uuid4())
            }
        }
        
        # Add field information for validation errors
        if field:
            response["error"]["field"] = field
            
        # Add additional data if provided
        if data:
            response["error"]["data"] = data
            
        return JSONResponse(status_code=status_code, content=response)

def create_api_exception(
    error_type: str,
    detail: Optional[str] = None,
    field: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """
    Create an HTTPException with standardized error details
    
    Args:
        error_type: The type of error from ERROR_CODES
        detail: Detailed error message (overrides default if provided)
        field: Field that caused the error (for validation errors)
        data: Additional data to include in the response
        
    Returns:
        HTTPException with appropriate status code and detail
    """
    if error_type not in ERROR_CODES:
        error_type = "SERVER_ERROR"
        
    error_info = ERROR_CODES[error_type]
    status_code = error_info["status_code"]
    
    # Create the error detail
    error_detail = {
        "code": error_info["code"],
        "type": error_type,
        "message": detail or error_info["message"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "request_id": str(uuid.uuid4())
    }
    
    # Add field information for validation errors
    if field:
        error_detail["field"] = field
        
    # Add additional data if provided
    if data:
        error_detail["data"] = data
    
    return HTTPException(status_code=status_code, detail=error_detail)

async def http_exception_handler(request: Request, exc: Union[HTTPException, StarletteHTTPException]) -> JSONResponse:
    """
    Handle HTTPExceptions and convert to standardized format
    
    Args:
        request: The request that caused the exception
        exc: The HTTPException that was raised
        
    Returns:
        JSONResponse with standardized error format
    """
    # Check if this is already a standardized error
    if hasattr(exc, "detail") and isinstance(exc.detail, dict) and "code" in exc.detail:
        # This is already a standardized error
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail}
        )
    
    # Map status code to error type
    status_code = exc.status_code
    error_type = "SERVER_ERROR"
    
    # Map common status codes to error types
    status_code_mapping = {
        400: "INVALID_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "ALREADY_EXISTS",
        500: "SERVER_ERROR",
        503: "SERVICE_UNAVAILABLE"
    }
    
    if status_code in status_code_mapping:
        error_type = status_code_mapping[status_code]
    
    # Get error details
    detail = str(exc.detail) if hasattr(exc, "detail") else "An error occurred"
    
    # Log the error
    logger.error(f"HTTP Exception: {status_code} - {detail}")
    
    # Create and return the error response
    return ErrorResponse.create(error_type, detail)

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle validation exceptions and convert to standardized format
    
    Args:
        request: The request that caused the exception
        exc: The RequestValidationError that was raised
        
    Returns:
        JSONResponse with standardized error format
    """
    errors = []
    
    # Extract validation errors
    for error in exc.errors():
        field = ".".join([str(loc) for loc in error["loc"] if loc != "body"])
        message = error["msg"]
        
        errors.append({
            "field": field,
            "message": message,
            "type": error["type"]
        })
    
    # Log the errors
    logger.error(f"Validation Error: {str(errors)}")
    
    # Create and return the error response
    return ErrorResponse.create(
        "VALIDATION_ERROR",
        "Request validation failed",
        data={"errors": errors}
    )

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle any unhandled exceptions
    
    Args:
        request: The request that caused the exception
        exc: The Exception that was raised
        
    Returns:
        JSONResponse with standardized error format
    """
    # Get exception details
    error_message = str(exc)
    error_traceback = traceback.format_exc()
    
    # Generate request ID for tracking
    request_id = str(uuid.uuid4())
    
    # Log the error with request ID
    logger.error(
        f"Unhandled Exception (ID: {request_id}): {error_message}\n{error_traceback}"
    )
    
    # Create and return the error response
    return ErrorResponse.create(
        "SERVER_ERROR",
        f"An unexpected error occurred. Reference ID: {request_id}",
        data={"request_id": request_id}
    )

def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app
    
    Args:
        app: The FastAPI application instance
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Registered API exception handlers")
