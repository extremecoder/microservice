"""
Configuration module for the Quantum Computing API.

This module contains configuration settings and environment variables for the application.
"""
import os
from typing import Dict, Any, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Settings for the Quantum Computing API.
    
    Attributes:
        API_V1_STR: API version prefix
        PROJECT_NAME: Name of the project
        PROJECT_DESCRIPTION: Description of the project
        PROJECT_VERSION: Version of the project
        DEBUG: Debug mode flag
        LOG_LEVEL: Logging level
        IBM_QUANTUM_TOKEN: IBM Quantum token
        AWS_ACCESS_KEY_ID: AWS access key ID
        AWS_SECRET_ACCESS_KEY: AWS secret access key
        AWS_REGION: AWS region
        TOGETHER_API_KEY: Together API key
    """
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Quantum Computing API"
    PROJECT_DESCRIPTION: str = "A unified interface to execute quantum circuits on multiple simulators and hardware platforms"
    PROJECT_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Quantum provider credentials
    IBM_QUANTUM_TOKEN: Optional[str] = Field(None, env="IBM_QUANTUM_TOKEN")
    AWS_ACCESS_KEY_ID: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: Optional[str] = Field(None, env="AWS_REGION")
    TOGETHER_API_KEY: Optional[str] = Field(None, env="TOGETHER_API_KEY")
    
    # Paths for storing circuits and results
    CIRCUITS_DIR: str = "circuits"
    RESULTS_DIR: str = "results"
    
    class Config:
        """Pydantic Config class."""
        env_file = ".env"
        case_sensitive = True


# Create an instance of the settings
settings = Settings()

# Create directories if they don't exist
os.makedirs(settings.CIRCUITS_DIR, exist_ok=True)
os.makedirs(settings.RESULTS_DIR, exist_ok=True)
