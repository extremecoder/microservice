"""
Tests for the circuit executor service.

This module contains tests for the circuit execution service functions.
"""
import os
import sys
import pytest
import tempfile
from unittest import mock
from typing import Dict, Any

# Add the project root to the Python path to ensure imports work properly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.circuit_executor import (
    check_provider_availability,
    execute_circuit_with_qiskit,
    execute_circuit_with_cirq,
    execute_circuit_with_braket
)


def test_check_provider_availability():
    """
    Test the provider availability checking function.
    
    Verifies that the function correctly reports availability of providers.
    """
    # Test simulator providers
    assert isinstance(check_provider_availability("qiskit"), bool)
    assert isinstance(check_provider_availability("cirq"), bool)
    assert isinstance(check_provider_availability("braket"), bool)
    
    # Test hardware providers (should return True since they're handled differently)
    assert check_provider_availability("aws") == True
    assert check_provider_availability("ibm") == True
    assert check_provider_availability("google") == True
    
    # Test invalid provider
    assert check_provider_availability("invalid_provider") == False


@pytest.mark.asyncio
async def test_execute_circuit_with_qiskit(sample_qasm_circuit: str):
    """
    Test Qiskit circuit executor.
    
    Verifies that the function can execute a circuit using Qiskit.
    """
    if not check_provider_availability("qiskit"):
        pytest.skip("Qiskit is not available")
    
    # Create temporary file with the circuit
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".qasm", delete=False) as f:
        f.write(sample_qasm_circuit)
        circuit_path = f.name
    
    try:
        # Execute circuit
        parameters = {}
        shots = 1024
        
        result = await execute_circuit_with_qiskit(circuit_path, parameters, shots)
        
        # Validate result
        assert isinstance(result, dict)
        
        # Verify all counts add up to the number of shots (or close to it)
        total_counts = sum(result.values())
        assert abs(total_counts - shots) <= shots * 0.1  # Allow for small variations
    
    finally:
        # Clean up the temporary file
        if os.path.exists(circuit_path):
            os.unlink(circuit_path)


@pytest.mark.asyncio
async def test_execute_circuit_with_cirq(sample_qasm_circuit: str):
    """
    Test Cirq circuit executor.
    
    Verifies that the function can execute a circuit using Cirq.
    """
    if not check_provider_availability("cirq"):
        pytest.skip("Cirq is not available")
    
    # Create temporary file with the circuit
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".qasm", delete=False) as f:
        f.write(sample_qasm_circuit)
        circuit_path = f.name
    
    try:
        # Execute circuit
        parameters = {}
        shots = 1024
        
        result = await execute_circuit_with_cirq(circuit_path, parameters, shots)
        
        # Validate result
        assert isinstance(result, dict)
        
        # Verify all counts add up approximately to the number of shots
        total_counts = sum(result.values())
        assert abs(total_counts - shots) <= shots * 0.1  # Allow for small variations
    
    finally:
        # Clean up the temporary file
        if os.path.exists(circuit_path):
            os.unlink(circuit_path)


@pytest.mark.asyncio
async def test_execute_circuit_with_braket(sample_qasm_circuit: str):
    """
    Test Braket circuit executor.
    
    Verifies that the function can execute a circuit using Braket.
    """
    if not check_provider_availability("braket"):
        pytest.skip("Braket is not available")
    
    # Create temporary file with the circuit
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".qasm", delete=False) as f:
        f.write(sample_qasm_circuit)
        circuit_path = f.name
    
    try:
        # Execute circuit
        parameters = {}
        shots = 1024
        
        result = await execute_circuit_with_braket(circuit_path, parameters, shots)
        
        # Validate result
        assert isinstance(result, dict)
        
        # Verify all counts add up to the number of shots (or close to it)
        total_counts = sum(result.values())
        assert abs(total_counts - shots) <= shots * 0.1  # Allow for small variations
    
    finally:
        # Clean up the temporary file
        if os.path.exists(circuit_path):
            os.unlink(circuit_path)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["qiskit", "cirq", "braket"])
async def test_execute_circuit_invalid_qasm(provider):
    """
    Test circuit executors with invalid QASM.
    
    Verifies that the functions properly handle errors with invalid QASM.
    """
    if not check_provider_availability(provider):
        pytest.skip(f"{provider} is not available")
    
    # Create temporary file with invalid QASM
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".qasm", delete=False) as f:
        f.write("This is not valid QASM")
        circuit_path = f.name
    
    try:
        # Execute circuit and expect an error
        parameters = {}
        shots = 1024
        
        with pytest.raises(Exception):
            if provider == "qiskit":
                await execute_circuit_with_qiskit(circuit_path, parameters, shots)
            elif provider == "cirq":
                await execute_circuit_with_cirq(circuit_path, parameters, shots)
            elif provider == "braket":
                await execute_circuit_with_braket(circuit_path, parameters, shots)
    
    finally:
        # Clean up the temporary file
        if os.path.exists(circuit_path):
            os.unlink(circuit_path)
