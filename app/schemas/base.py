"""
Base schemas for the Quantum Computing API.

This module contains the base response schemas used throughout the API.
"""
from typing import Generic, TypeVar, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


T = TypeVar('T')


class ErrorModel(BaseModel):
    """
    Standard error response model.
    
    Attributes:
        code: Error code
        message: Human readable error message
    """
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human readable error message")


class ResponseBase(BaseModel, Generic[T]):
    """
    Base response model for all API endpoints.
    
    Attributes:
        status: Response status ('success' or 'error')
        data: Response data (type depends on the endpoint)
        error: Error information if status is 'error'
    """
    status: str = Field(..., description="Response status ('success' or 'error')")
    data: Optional[T] = Field(None, description="Response data")
    error: Optional[ErrorModel] = Field(None, description="Error information if status is 'error'")
    
    @classmethod
    def success(cls, data: T) -> "ResponseBase[T]":
        """
        Create a success response.
        
        Args:
            data: Response data
            
        Returns:
            Success response
        """
        return cls(status="success", data=data, error=None)
    
    @classmethod
    def error(cls, code: str, message: str) -> "ResponseBase[None]":
        """
        Create an error response.
        
        Args:
            code: Error code
            message: Error message
            
        Returns:
            Error response
        """
        return cls(
            status="error", 
            data=None, 
            error=ErrorModel(code=code, message=message)
        )
