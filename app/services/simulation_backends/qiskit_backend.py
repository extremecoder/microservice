"""
Backend for running simulations using Qiskit Aer.
"""

import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Using existing CircuitExecutionResult model instead of creating SimulationResult
from ...schemas.circuit import CircuitExecutionResponse


# Set up logging for this module
logger = logging.getLogger(__name__)


def run_qiskit_simulation(qasm_file: str, shots: int = 1024, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Runs an OpenQASM 2.0 circuit file using the Qiskit Aer simulator.

    Args:
        qasm_file (str): Path to the OpenQASM 2.0 file.
        shots (int): Number of simulation shots.
        **kwargs: Additional options (e.g., noise model parameters - TBD).

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing the simulation results, or None on failure.

    Raises:
        FileNotFoundError: If the QASM file does not exist.
        ImportError: If qiskit or qiskit_aer is not installed.
        Exception: For errors during circuit loading or simulation.
    """
    logger.info(f"Attempting Qiskit simulation for: {qasm_file} with {shots} shots.")

    try:
        from qiskit import QuantumCircuit
        from qiskit_aer import AerSimulator
    except ImportError:
        logger.error("Qiskit or Qiskit Aer is not installed. Please install them to run simulations.")
        print("Error: Qiskit/Qiskit Aer not found. Run 'pip install qiskit qiskit-aer'", file=sys.stderr)
        raise # Re-raise the ImportError

    qasm_path = Path(qasm_file)
    if not qasm_path.is_file():
        logger.error(f"QASM file not found: {qasm_file}")
        raise FileNotFoundError(f"QASM file not found: {qasm_file}")

    try:
        # Load circuit from QASM file
        circuit = QuantumCircuit.from_qasm_file(str(qasm_path))
        logger.debug(f"Successfully loaded QASM file: {qasm_file}")
        logger.debug(f"Circuit details: {circuit.num_qubits} qubits, {circuit.num_clbits} classical bits, depth {circuit.depth()}")

        # Set up the simulator
        # TODO: Add noise model support based on kwargs
        simulator = AerSimulator()
        logger.debug("AerSimulator initialized.")

        # Run the simulation
        logger.info(f"Running simulation job...")
        job = simulator.run(circuit, shots=shots)
        result = job.result()
        counts = result.get_counts(circuit)
        logger.info(f"Simulation job completed successfully. Status: {result.status}")
        logger.debug(f"Raw counts: {counts}")

        # Format results
        # Qiskit counts are { '00': N, '11': M }, convert to standardized format if needed
        # For now, we'll keep Qiskit's format.

        sim_result = {
            "counts": counts,
            "execution_time": 0.0,
            "metadata": {"status": result.status}
        }
        logger.info("Simulation result object created.")
        return sim_result

    except FileNotFoundError as e: # Should be caught earlier, but handle again just in case
        logger.error(f"File not found error during simulation: {e}")
        raise
    except Exception as e:
        logger.error(f"An error occurred during Qiskit simulation: {e}", exc_info=True)
        print(f"Error during simulation: {e}", file=sys.stderr)
        raise # Re-raise the exception after logging 