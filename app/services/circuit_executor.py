"""
Circuit execution service.

This module provides functions for executing quantum circuits on various backends.
"""
from typing import Dict, Any, Optional, List
import asyncio
import time
from pathlib import Path
from app.core.logging import get_logger

# Import quantum backends with availability checking
try:
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False

try:
    import cirq
    from cirq.contrib.qasm_import import circuit_from_qasm
    CIRQ_AVAILABLE = True
except ImportError:
    CIRQ_AVAILABLE = False

try:
    from braket.devices import LocalSimulator
    from braket.circuits import Circuit as BraketCircuit
    from qiskit import QuantumCircuit
    from qiskit.qasm2.exceptions import QASM2ParseError
    from qiskit_braket_provider.providers.adapter import convert_qiskit_to_braket_circuit
    BRAKET_AVAILABLE = True
except ImportError:
    BRAKET_AVAILABLE = False

# Import backend simulation functions
from app.services.simulation_backends.qiskit_backend import run_qiskit_simulation
from app.services.simulation_backends.cirq_backend import run_cirq_simulation
from app.services.simulation_backends.braket_backend import run_braket_simulation
from app.schemas.circuit import CircuitExecutionResult

logger = get_logger(__name__)


def check_provider_availability(provider: str) -> bool:
    """
    Check if the specified provider is available.
    
    Args:
        provider: The name of the provider to check
        
    Returns:
        True if the provider is available, False otherwise
    """
    if provider == "qiskit":
        return QISKIT_AVAILABLE
    elif provider == "cirq":
        return CIRQ_AVAILABLE
    elif provider == "braket":
        return BRAKET_AVAILABLE
    elif provider in ["aws", "ibm", "google"]:
        # For hardware providers, we would check credentials and connectivity
        # This is a placeholder for future implementation
        return True
    else:
        return False


async def execute_circuit_with_qiskit(
    circuit_path: str, parameters: Dict[str, Any], shots: int
) -> Dict[str, int]:
    """
    Execute a quantum circuit using Qiskit.
    
    Args:
        circuit_path: Path to the OpenQASM circuit file
        parameters: Dictionary of circuit parameters
        shots: Number of execution shots
    
    Returns:
        Measurement counts
        
    Raises:
        ValueError: If Qiskit is not available or circuit execution fails
    """
    if not QISKIT_AVAILABLE:
        raise ValueError("Qiskit is not available")
    
    # Record start time for execution timing
    start_time = time.time()
    
    try:
        # Call the backend implementation
        result = run_qiskit_simulation(
            qasm_file=circuit_path,
            shots=shots,
            **parameters
        )
        
        if result is None:
            raise ValueError("Qiskit simulation returned no results")
            
        # Update execution time in result
        execution_time = time.time() - start_time
        result["execution_time"] = execution_time
        
        # Return the counts dictionary
        return result["counts"]
    except Exception as e:
        logger.error(f"Error executing circuit with Qiskit: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to execute circuit with Qiskit: {str(e)}")


async def execute_circuit_with_cirq(
    circuit_path: str, parameters: Dict[str, Any], shots: int
) -> Dict[str, int]:
    """
    Execute a quantum circuit using Cirq.
    
    Args:
        circuit_path: Path to the OpenQASM circuit file
        parameters: Dictionary of circuit parameters
        shots: Number of execution shots
    
    Returns:
        Measurement counts
        
    Raises:
        ValueError: If Cirq is not available or circuit execution fails
    """
    if not CIRQ_AVAILABLE:
        raise ValueError("Cirq is not available")
        
    # Record start time for execution timing
    start_time = time.time()
    
    try:
        # Call the backend implementation
        result = run_cirq_simulation(
            qasm_file=circuit_path,
            shots=shots,
            **parameters
        )
        
        if result is None:
            raise ValueError("Cirq simulation returned no results")
            
        # Update execution time in result
        execution_time = time.time() - start_time
        result["execution_time"] = execution_time
        
        # Return the counts dictionary
        return result["counts"]
    except Exception as e:
        logger.error(f"Error executing circuit with Cirq: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to execute circuit with Cirq: {str(e)}")


async def execute_circuit_with_braket(
    circuit_path: str, parameters: Dict[str, Any], shots: int
) -> Dict[str, int]:
    """
    Execute a quantum circuit using Braket.
    
    Args:
        circuit_path: Path to the OpenQASM circuit file
        parameters: Dictionary of circuit parameters
        shots: Number of execution shots
    
    Returns:
        Measurement counts
        
    Raises:
        ValueError: If Braket is not available or circuit execution fails
    """
    if not BRAKET_AVAILABLE:
        raise ValueError("Braket is not available")
        
    # Record start time for execution timing
    start_time = time.time()
    
    try:
        # Call the backend implementation
        result = run_braket_simulation(
            qasm_file=circuit_path,
            shots=shots,
            **parameters
        )
        
        if result is None:
            raise ValueError("Braket simulation returned no results")
            
        # Update execution time in result
        execution_time = time.time() - start_time
        result["execution_time"] = execution_time
        
        # Return the counts dictionary
        return result["counts"]
    except Exception as e:
        logger.error(f"Error executing circuit with Braket: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to execute circuit with Braket: {str(e)}")
