"""
Main application module for the Quantum Computing API.

This module initializes the FastAPI application with all routes, middleware,
and configuration.
"""
import time
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import setup_logging, get_logger


logger = get_logger(__name__)


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    # Initialize logging
    setup_logging()
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.PROJECT_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )
    
    # Set up CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # For development; restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add API router with version prefix
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Add request timing middleware
    @app.middleware("http")
    async def add_timing_header(request: Request, call_next: Callable) -> Response:
        """Add timing information to response headers."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Root endpoint for basic application info
    @app.get("/")
    async def root():
        """Root endpoint with basic API information."""
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.PROJECT_VERSION,
            "description": settings.PROJECT_DESCRIPTION,
            "docs": "/docs",
        }
    
    # Custom OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=settings.PROJECT_NAME,
            version=settings.PROJECT_VERSION,
            description=settings.PROJECT_DESCRIPTION,
            routes=app.routes,
        )
        
        # Add API documentation enhancements here as needed
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    logger.info(f"Application initialized: {settings.PROJECT_NAME} {settings.PROJECT_VERSION}")
    return app


app = create_application()
