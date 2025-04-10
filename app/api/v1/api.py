"""
API router for version 1 endpoints.

This module combines all version 1 API endpoints into a single router.
"""
from fastapi import APIRouter

from app.api.v1 import health, circuits

api_router = APIRouter()

# Include all API endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(circuits.router, prefix="/circuits", tags=["circuits"])

# Job management routers will be added in subsequent tasks
