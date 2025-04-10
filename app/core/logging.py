"""
Logging configuration for the Quantum Computing API.

This module sets up structured logging for the application with appropriate
log levels and handlers.
"""
import logging
import sys
from typing import Dict, Any

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure logging for the application.
    
    Sets up structured logging with appropriate log levels and handlers
    based on the application configuration.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Setup basic configuration
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("quantum_api.log")
        ]
    )
    
    # Reduce verbosity of some loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
    
    # Log some basic application info
    logger = logging.getLogger("app")
    logger.info("Logging configured")
    
    # Log available quantum backends
    try:
        import qiskit
        logger.info(f"Qiskit version {qiskit.__version__} available")
    except ImportError:
        logger.warning("Qiskit not available")
    
    try:
        import cirq
        logger.info(f"Cirq version {cirq.__version__} available")
    except ImportError:
        logger.warning("Cirq not available")
    
    try:
        import braket
        logger.info("Braket package available")
    except ImportError:
        logger.warning("Braket not available")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    Args:
        name: Name of the logger
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_request(logger: logging.Logger, endpoint: str, request_data: Dict[str, Any]) -> None:
    """
    Log an API request.
    
    Args:
        logger: Logger instance
        endpoint: API endpoint path
        request_data: Request data (may be sanitized)
    """
    logger.info(f"Request to {endpoint}: {request_data}")


def log_response(logger: logging.Logger, endpoint: str, status_code: int, 
                response_time: float) -> None:
    """
    Log an API response.
    
    Args:
        logger: Logger instance
        endpoint: API endpoint path
        status_code: HTTP status code
        response_time: Response time in seconds
    """
    logger.info(f"Response from {endpoint}: {status_code} in {response_time:.4f}s")
