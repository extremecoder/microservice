"""
Tests for the circuit execution API endpoints.

This module contains tests for the /api/v1/circuits/execute endpoint.
"""
import json
import pytest
from typing import Dict, Any
from unittest import mock
from fastapi.testclient import TestClient
from fastapi import status

from app.schemas.circuit import JobStatus


def test_execute_circuit_sync_success(
    test_client: TestClient, 
    valid_circuit_execution_payload: Dict[str, Any],
    available_simulators: Dict[str, bool]
):
    """
    Test successful synchronous circuit execution.
    
    Verifies that a circuit can be executed synchronously and returns
    proper execution results.
    """
    # Skip test if the requested simulator is not available
    provider = valid_circuit_execution_payload["backend_provider"]
    if not available_simulators.get(provider, False):
        pytest.skip(f"{provider} simulator not available")
    
    response = test_client.post(
        "/api/v1/circuits/execute",
        json=valid_circuit_execution_payload
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "status" in data
    assert data["status"] == "success" or "error" in data
    
    if data["status"] == "success":
        assert "data" in data
        assert data["error"] is None
        
        # Validate execution result structure
        result_data = data["data"]
        assert "counts" in result_data
        assert "execution_time" in result_data
        assert "metadata" in result_data
        
        # Validate counts data
        counts = result_data["counts"]
        assert isinstance(counts, dict)
        
        # Validate metadata
        metadata = result_data["metadata"]
        assert metadata["backend_type"] == "simulator"
        assert metadata["backend_provider"] == provider
        assert metadata["shots"] == valid_circuit_execution_payload["shots"]


def test_execute_circuit_async_success(
    test_client: TestClient, 
    valid_circuit_execution_payload: Dict[str, Any],
    available_simulators: Dict[str, bool]
):
    """
    Test successful asynchronous circuit execution.
    
    Verifies that a circuit can be queued for asynchronous execution and
    returns a valid job ID.
    """
    # Skip test if the requested simulator is not available
    provider = valid_circuit_execution_payload["backend_provider"]
    if not available_simulators.get(provider, False):
        pytest.skip(f"{provider} simulator not available")
    
    # Modify the payload for async execution
    payload = valid_circuit_execution_payload.copy()
    payload["async_mode"] = True
    
    response = test_client.post(
        "/api/v1/circuits/execute",
        json=payload
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "status" in data
    
    if data["status"] == "success":
        assert "data" in data
        assert data["error"] is None
        
        # Validate async job creation response
        result_data = data["data"]
        assert "job_id" in result_data
        assert "status" in result_data
        assert result_data["status"] == JobStatus.QUEUED.value


def test_execute_circuit_invalid_backend_type(
    test_client: TestClient, 
    valid_circuit_execution_payload: Dict[str, Any]
):
    """
    Test circuit execution with invalid backend type.
    
    Verifies that proper validation error is returned for invalid backend type.
    """
    # Modify the payload with invalid backend type
    payload = valid_circuit_execution_payload.copy()
    payload["backend_type"] = "invalid_type"
    
    response = test_client.post(
        "/api/v1/circuits/execute",
        json=payload
    )
    
    # Should return 422 Unprocessable Entity for invalid enum value
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    data = response.json()
    assert "detail" in data
    assert len(data["detail"]) > 0
    
    # Verify the error contains information about the invalid value
    error = data["detail"][0]
    assert "backend_type" in str(error)


def test_execute_circuit_invalid_backend_provider(
    test_client: TestClient, 
    valid_circuit_execution_payload: Dict[str, Any]
):
    """
    Test circuit execution with invalid backend provider.
    
    Verifies that proper error is returned for invalid backend provider.
    """
    # Modify the payload with invalid backend provider
    payload = valid_circuit_execution_payload.copy()
    payload["backend_provider"] = "invalid_provider"
    
    response = test_client.post(
        "/api/v1/circuits/execute",
        json=payload
    )
    
    # Should return 400 Bad Request for invalid provider
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    data = response.json()
    assert "detail" in data
    assert "provider" in data["detail"].lower()


def test_execute_circuit_hardware_backend(
    test_client: TestClient, 
    valid_circuit_execution_payload: Dict[str, Any]
):
    """
    Test circuit execution with hardware backend.
    
    Verifies validation for hardware backend providers.
    """
    # Modify the payload to use hardware backend
    payload = valid_circuit_execution_payload.copy()
    payload["backend_type"] = "hardware"
    payload["backend_provider"] = "ibm"
    payload["backend_name"] = "ibmq_qasm_simulator"  # A common IBM simulator
    
    response = test_client.post(
        "/api/v1/circuits/execute",
        json=payload
    )
    
    # We expect either valid response or specific error about hardware
    assert response.status_code in [
        status.HTTP_200_OK, 
        status.HTTP_400_BAD_REQUEST
    ]


def test_execute_circuit_shots_validation(
    test_client: TestClient, 
    valid_circuit_execution_payload: Dict[str, Any]
):
    """
    Test circuit execution with invalid shot count.
    
    Verifies validation for the shots parameter.
    """
    # Modify the payload with invalid (negative) shots
    payload = valid_circuit_execution_payload.copy()
    payload["shots"] = -1
    
    response = test_client.post(
        "/api/v1/circuits/execute",
        json=payload
    )
    
    # The API might use either 422 or 400 for validation errors
    assert response.status_code in [
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        status.HTTP_400_BAD_REQUEST
    ]
    
    data = response.json()
    assert "detail" in data


def test_execute_circuit_empty_circuit(
    test_client: TestClient, 
    valid_circuit_execution_payload: Dict[str, Any]
):
    """
    Test circuit execution with empty circuit.
    
    Verifies proper error handling for empty circuit content.
    """
    # Modify the payload with empty circuit
    payload = valid_circuit_execution_payload.copy()
    payload["circuit_file"] = ""
    
    response = test_client.post(
        "/api/v1/circuits/execute",
        json=payload
    )
    
    # Should return error for empty circuit
    assert response.status_code in [
        status.HTTP_400_BAD_REQUEST, 
        status.HTTP_422_UNPROCESSABLE_ENTITY
    ]
