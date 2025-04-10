"""
Backend for running simulations using Cirq.
"""

import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Using existing CircuitExecutionResult model instead of creating SimulationResult
#from ...schemas.circuit import CircuitExecutionResponse


# Set up logging for this module
logger = logging.getLogger(__name__)

def run_cirq_simulation(qasm_file: str, shots: int = 1024, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Runs an OpenQASM 2.0 circuit file using the Cirq simulator.

    Args:
        qasm_file (str): Path to the OpenQASM 2.0 file.
        shots (int): Number of simulation shots.
        **kwargs: Additional options (currently unused).

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing the simulation results, or None if an error occurs.

    Raises:
        FileNotFoundError: If the QASM file does not exist.
        ImportError: If cirq is not installed.
        Exception: For errors during circuit loading or simulation.
    """
    logger.info(f"Attempting Cirq simulation for: {qasm_file} with {shots} shots.")

    try:
        import cirq
        from cirq.contrib.qasm_import import circuit_from_qasm
    except ImportError:
        logger.error("Cirq is not installed. Please install it to run simulations.")
        print("Error: Cirq not found. Run 'pip install cirq-core'", file=sys.stderr)
        raise

    qasm_path = Path(qasm_file)
    if not qasm_path.is_file():
        logger.error(f"QASM file not found: {qasm_file}")
        raise FileNotFoundError(f"QASM file not found: {qasm_file}")

    try:
        # Load QASM file content
        qasm_content = qasm_path.read_text()
        logger.debug(f"Successfully read QASM file content from: {qasm_file}")

        # Parse QASM into a Cirq circuit
        circuit = circuit_from_qasm(qasm_content)
        logger.debug("Successfully parsed QASM into Cirq circuit.")
        # Note: Cirq QASM import might be limited. More complex circuits might fail.
        # Check if the circuit has measurements, required for simulation runs
        if not circuit.has_measurements():
            logger.error("Cirq circuit has no measurements. Cannot simulate counts.")
            print(f"Error: The circuit loaded from {qasm_file} has no measurement gates, which are required for simulation.", file=sys.stderr)
            return None # Cannot simulate without measurements

        # Set up the simulator
        simulator = cirq.Simulator()
        logger.debug("Cirq Simulator initialized.")

        # Run the simulation
        logger.info(f"Running Cirq simulation job...")
        results = simulator.run(circuit, repetitions=shots)
        # Process results: Cirq results are often by measurement key
        # We need to aggregate them into a format similar to Qiskit counts (bitstrings)
        # Assuming measurements are mapped to classical bits with keys like 'c[0]', 'c[1]', etc.
        # Or a single key like 'meas' if defined differently in QASM

        counts = {}
        if results.measurements:
            # Find the measurement keys used in the QASM (usually related to cregs)
            # QASM typically measures to named classical registers. Cirq maps these to keys.
            # We need to figure out which key(s) hold the measurement outcomes.
            # Let's assume a common case where all measurements are mapped to a single key (often the default).
            
            # Find the key associated with the measurements (often 'm' or specific creg names)
            measurement_key = list(results.measurements.keys())[0] # Simplistic assumption
            logger.debug(f"Using measurement key: '{measurement_key}'")

            # Get the measurement outcomes (shape: (repetitions, num_measured_qubits))
            measurement_data = results.measurements[measurement_key]

            # Convert each measurement outcome (row) into a bitstring
            num_measured_qubits = measurement_data.shape[1]
            for i in range(shots):
                bitstring = "".join(map(str, measurement_data[i]))
                counts[bitstring] = counts.get(bitstring, 0) + 1
        else:
             logger.warning("Cirq simulation ran but no measurements found in the results object.")

        logger.info(f"Cirq simulation job completed.")
        logger.debug(f"Raw counts (aggregated): {counts}")

        sim_result = {
            "counts": counts,
            "execution_time": 0.0,
            "metadata": {"measurement_keys": list(results.measurements.keys())}
        }
        logger.info("Simulation result object created.")
        return sim_result

    except FileNotFoundError as e:
        logger.error(f"File not found error during Cirq simulation: {e}")
        raise
    except ValueError as e:
         logger.error(f"Error parsing QASM for Cirq: {e}", exc_info=True)
         print(f"Error: Could not parse QASM file '{qasm_file}' for Cirq. It might contain unsupported features. Details: {e}", file=sys.stderr)
         return None
    except Exception as e:
        logger.error(f"An error occurred during Cirq simulation: {e}", exc_info=True)
        print(f"Error during Cirq simulation: {e}", file=sys.stderr)
        raise # Re-raise the exception after logging 