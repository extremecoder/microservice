"""
Backend for running simulations using AWS Braket (via qiskit-braket-provider).
"""

import sys
import logging
import time
from pathlib import Path
from typing import Optional, Union, Dict, Any
import os # Import os module
import inspect # Import inspect module
import re # Import re for include replacement

# Using existing CircuitExecutionResult model instead of creating SimulationResult
# from ...schemas.circuit import CircuitExecutionResponse

# Set up logging for this module
logger = logging.getLogger(__name__)

def run_braket_simulation(qasm_file: str, shots: int = 1024, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Runs an OpenQASM 2.0 circuit file using the AWS Braket local simulator via the qiskit-braket-provider.
    QASM 3.0 is explicitly not supported by this backend due to parsing limitations.

    Args:
        qasm_file (str): Path to the OpenQASM 2.0 file.
        shots (int): Number of simulation shots.
        **kwargs: Additional backend-specific options (currently unused for Braket).

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing the simulation results, or None on failure.

    Raises:
        FileNotFoundError: If the QASM file does not exist.
        ImportError: If amazon-braket-sdk or qiskit-braket-provider is not installed.
        Exception: For errors during circuit loading or simulation.
    """
    logger.info(f"Attempting Braket simulation for: {qasm_file} with {shots} shots.")
    logger.info("Using qiskit-braket-provider for circuit conversion.")
    start_time = time.time()

    try:
        # Import necessary components
        from braket.devices import LocalSimulator
        from braket.circuits import Circuit as BraketCircuit
        from qiskit import QuantumCircuit
        from qiskit.qasm2.exceptions import QASM2ParseError
        from qiskit_braket_provider.providers.adapter import convert_qiskit_to_braket_circuit

    except ImportError as e:
        logger.error(f"Braket SDK or Qiskit/Provider dependencies not installed: {e}")
        print(f"Error: Missing library for Braket/Qiskit. Run 'pip install amazon-braket-sdk amazon-braket-default-simulator qiskit qiskit-braket-provider'. Details: {e}", file=sys.stderr)
        raise

    qasm_path = Path(qasm_file)
    if not qasm_path.is_file():
        logger.error(f"QASM file not found: {qasm_file}")
        raise FileNotFoundError(f"QASM file not found: {qasm_file}")

    try:
        with open(qasm_path, 'r') as f:
            qasm_str = f.read()
        logger.debug(f"Read QASM content from {qasm_file}")
        
        braket_circuit: Optional[BraketCircuit] = None

        # Check for QASM3 and reject if found
        if qasm_str.strip().startswith("OPENQASM 3"):
            logger.error("Detected OpenQASM 3.0 input, which is not supported by the Braket backend's current Qiskit conversion path.")
            print("Error: OpenQASM 3.0 input is not supported for the 'braket' backend with this implementation.", file=sys.stderr)
            return None # Indicate failure for QASM3

        # Proceed assuming QASM 2.0
        logger.info("Assuming OpenQASM 2.0 input. Attempting Qiskit parsing + provider conversion.")
        try:
            qiskit_circuit = QuantumCircuit.from_qasm_str(qasm_str)
            braket_circuit = convert_qiskit_to_braket_circuit(qiskit_circuit)
            logger.info("Successfully processed via Qiskit QASM2 + provider.")
        except QASM2ParseError as q2_error:
            logger.error(f"OpenQASM 2.0 parsing failed: {q2_error}", exc_info=True)
            print(f"Error: Failed to parse OpenQASM 2.0 file: {q2_error}", file=sys.stderr)
            return None
        except Exception as qiskit_conv_error:
            logger.error(f"Qiskit QASM2 processing/conversion failed: {qiskit_conv_error}", exc_info=True)
            print(f"Error: Failed processing via Qiskit QASM2 path: {qiskit_conv_error}", file=sys.stderr)
            return None
        
        # If we reach here, braket_circuit should be valid
        if braket_circuit is None:
            # This case should be unlikely if the above try/except blocks are correct
            logger.error("Failed to obtain a runnable Braket Circuit from the QASM 2.0 input after processing.")
            print("Error: Could not process QASM 2.0 into a runnable format for Braket.", file=sys.stderr)
            return None

        logger.debug(f"Running on Braket. Target type: BraketCircuit")
        # logger.debug(f"Target details: {braket_circuit}") # Can be very verbose

        # Run the simulation on Braket Local Simulator
        simulator = LocalSimulator()
        logger.info(f"Running Braket simulation job on {simulator.name}...")

        # Braket returns different result types based on shots
        if shots > 0:
            task = simulator.run(braket_circuit, shots=shots)
            result = task.result()
            # Measurement counts are directly available
            raw_counts = result.measurement_counts
            logger.info(f"Braket simulation completed. Status: {result.task_metadata.status}")
            logger.debug(f"Raw counts: {raw_counts}")
            counts = {k: int(v) for k, v in raw_counts.items()}
            metadata = { "status": result.task_metadata.status, "backend": simulator.name }
        else:
            # If shots=0, Braket calculates state vector or probabilities for Circuits
            logger.info("Shots=0, requesting probabilities from Braket simulator for Circuit input.")
            from braket.circuits import ResultType
            
            # Add the probability result type request to the circuit
            braket_circuit.probability() # Modifies the circuit in-place
            task = simulator.run(braket_circuit, shots=0)

            result = task.result()
            if not result.result_types:
                 logger.error("Braket simulation with shots=0 did not produce any result types.")
                 print("Error: Braket simulation for probabilities failed to return results.", file=sys.stderr)
                 return None

            probabilities = result.result_types[0].value 
            num_qubits = braket_circuit.qubit_count
            counts = {format(i, f'0{num_qubits}b'): prob for i, prob in enumerate(probabilities)}
            logger.info(f"Braket probability calculation completed. Status: {result.task_metadata.status}")
            logger.debug(f"Probabilities: {counts}")
            metadata = { "status": result.task_metadata.status, "backend": simulator.name, "result_type": "probabilities" }

        sim_result = {
            "counts": counts, 
            "execution_time": 0.0,
            "metadata": metadata
        }
        logger.info("Braket simulation result object created.")
        return sim_result

    except FileNotFoundError as fnf_error:
        # Should be caught earlier, but log and re-raise if it occurs here
        logger.error(f"FileNotFoundError caught during Braket simulation for {qasm_file}", exc_info=True)
        raise fnf_error 
    except ImportError as imp_error: # Catch specific import errors from this block if any
        logger.error(f"ImportError during Braket simulation execution: {imp_error}", exc_info=True)
        print(f"Error: A required library for Braket/Qiskit was not found during execution. {imp_error}", file=sys.stderr)
        return None
    except Exception as e:
        logger.error(f"An error occurred during Braket simulation: {e}", exc_info=True)
        print(f"An error occurred during Braket simulation: {e}", file=sys.stderr)
        return None # Indicate failure 