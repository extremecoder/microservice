"""
Test configuration and fixtures for the quantum computing API test suite.

This module contains pytest fixtures and configuration for testing the API.
"""
import os
import sys
import pytest
from fastapi.testclient import TestClient
from typing import Dict, Generator, Any

# Add the project root to the Python path to ensure imports work properly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.services.circuit_executor import (
    check_provider_availability
)


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """
    Create a FastAPI TestClient for API testing.
    
    Returns:
        TestClient: A TestClient instance for the FastAPI app
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_qasm_circuit() -> str:
    """
    Load the sample Shor's algorithm QASM circuit.
    
    Returns:
        str: The QASM circuit content
    """
    circuit_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "circuits",
        "shors_factoring_15_compatible.qasm"
    )
    
    with open(circuit_path, "r") as f:
        return f.read()


@pytest.fixture
def available_simulators() -> Dict[str, bool]:
    """
    Get a dictionary of available quantum simulators.
    
    Returns:
        Dict[str, bool]: Dictionary with simulator availability
    """
    return {
        "qiskit": check_provider_availability("qiskit"),
        "cirq": check_provider_availability("cirq"),
        "braket": check_provider_availability("braket")
    }


@pytest.fixture
def valid_circuit_execution_payload(sample_qasm_circuit: str) -> Dict[str, Any]:
    """
    Generate a valid circuit execution payload.
    
    Args:
        sample_qasm_circuit: The QASM circuit content
    
    Returns:
        Dict[str, Any]: A valid circuit execution request
    """
    return {
        "circuit_file": sample_qasm_circuit,
        "shots": 1024,
        "backend_type": "simulator",
        "backend_provider": "qiskit",
        "backend_name": None,
        "async_mode": False,
        "parameters": {}
    }
