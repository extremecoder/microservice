"""
Script to run the Quantum Computing API.

This script provides a simple way to run the API in development mode.
"""
import uvicorn


if __name__ == "__main__":
    """Run the application with uvicorn."""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8888,
        reload=True
    )
