"""
Error handling utilities for the Quantum Computing API.

This module contains functions and classes for standardized error handling.
"""
from typing import Dict, Any, Type
from fastapi import HTTPException, status

from app.schemas.base import ResponseBase, ErrorModel


class APIError(Exception):
    """
    Base API error class.
    
    Attributes:
        code: Error code
        message: Error message
        status_code: HTTP status code
    """
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ResourceNotFoundError(APIError):
    """Error raised when a requested resource is not found."""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=f"{resource_type} with ID {resource_id} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class ValidationError(APIError):
    """Error raised when request validation fails."""
    def __init__(self, message: str):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class ExecutionError(APIError):
    """Error raised when circuit execution fails."""
    def __init__(self, message: str):
        super().__init__(
            code="EXECUTION_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def api_error_to_response(error: APIError) -> ResponseBase[None]:
    """
    Convert an API error to a standard response.
    
    Args:
        error: API error
        
    Returns:
        Standard error response
    """
    return ResponseBase.error(error.code, error.message)


ERROR_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: {"model": ResponseBase},
    status.HTTP_404_NOT_FOUND: {"model": ResponseBase},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ResponseBase},
}
