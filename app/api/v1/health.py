"""
Health check API endpoint.

This module contains the health check endpoint for the API.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends

from app.core.config import settings
from app.schemas.base import ResponseBase


# Try to import the quantum libraries
try:
    import qiskit
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False

try:
    import cirq
    CIRQ_AVAILABLE = True
except ImportError:
    CIRQ_AVAILABLE = False

try:
    import braket
    BRAKET_AVAILABLE = True
except ImportError:
    BRAKET_AVAILABLE = False


router = APIRouter()


@router.get("/health", response_model=ResponseBase[Dict[str, Any]])
async def health_check() -> ResponseBase[Dict[str, Any]]:
    """
    Health check endpoint.
    
    Returns information about the API's health, available simulators, and
    potential hardware connections.
    
    Returns:
        Response with health status information
    """
    health_data = {
        "status": "healthy",
        "api_version": settings.PROJECT_VERSION,
        "simulators": {
            "qiskit": QISKIT_AVAILABLE,
            "cirq": CIRQ_AVAILABLE,
            "braket": BRAKET_AVAILABLE
        },
        "hardware_connections": {
            "ibm": bool(settings.IBM_QUANTUM_TOKEN),
            "aws": bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY),
            "google": False  # Google requires additional setup
        }
    }
    
    return ResponseBase.success(health_data)
