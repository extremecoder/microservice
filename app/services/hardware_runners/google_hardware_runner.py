"""
Google Quantum Hardware Runner for executing quantum circuits on Google Quantum hardware.
"""

import os
import time
import tempfile
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def run_on_google_hardware(qasm_file: str, device_id: str = 'rainbow', 
                           shots: int = 1000, wait_for_results: bool = True,
                           poll_timeout_seconds: int = 3600, auth_file: Optional[str] = None, 
                           project_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Run a QASM file on Google Quantum hardware.
    
    Args:
        qasm_file: Path to the QASM file
        device_id: Google Quantum processor name ('rainbow', 'weber', etc.)
        shots: Number of shots to run (repetitions)
        wait_for_results: Whether to wait for results (True) or return immediately (False)
        poll_timeout_seconds: Maximum time to wait for results, in seconds
        auth_file: Path to Google authentication file (optional)
        project_id: Google Cloud project ID (optional)
        **kwargs: Additional arguments
        
    Returns:
        Dict[str, Any]: Dictionary containing counts and metadata
    """
    try:
        # Try to import cirq - if not available, this will fail early
        try:
            import cirq
            import cirq_google
            from cirq.contrib.qasm_import import circuit_from_qasm
        except ImportError:
            logger.error("Cirq or cirq_google not installed. Please install cirq and cirq_google to use Google hardware.")
            return {"counts": {"error": 1}, "metadata": {
                'platform': 'google',
                'device_id': device_id,
                'error': "Cirq or cirq_google not installed. Please install cirq and cirq_google to use Google hardware."
            }}
        
        # Determine if we should use simulator fallback
        use_simulator = False
        simulator_reason = None
        
        # Check for authentication file path
        google_auth_file = auth_file
        
        # Check environment variables for auth file if not provided
        if not google_auth_file:
            for env_var in ['GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_AUTH_FILE']:
                if env_var in os.environ and os.environ[env_var]:
                    google_auth_file = os.environ[env_var]
                    logger.info(f"Using Google auth file from environment variable: {env_var}")
                    break
        
        # Validate auth file
        if not google_auth_file or not os.path.exists(google_auth_file):
            use_simulator = True
            simulator_reason = f"Google authentication file not found or invalid"
            logger.warning(f"{simulator_reason}. Falling back to simulator.")
        
        # Validate project ID
        google_project_id = project_id
        if not google_project_id:
            if 'GOOGLE_CLOUD_PROJECT' in os.environ:
                google_project_id = os.environ['GOOGLE_CLOUD_PROJECT']
                logger.info(f"Using Google Cloud project from environment: {google_project_id}")
            elif not use_simulator:
                use_simulator = True
                simulator_reason = "Google Cloud project ID not provided"
                logger.warning(f"{simulator_reason}. Falling back to simulator.")
        
        # If using simulator, run with cirq simulator
        if use_simulator:
            logger.info(f"Using Cirq simulator due to: {simulator_reason}")
            
            # Read QASM file
            with open(qasm_file, 'r') as f:
                qasm_str = f.read()
            
            # Import QASM into a Cirq circuit
            try:
                circuit = circuit_from_qasm(qasm_str)
            except Exception as e:
                logger.error(f"Error importing QASM to Cirq: {e}")
                return {"counts": {"error": 1}, "metadata": {
                    'platform': 'google',
                    'device_id': 'simulator',
                    'error': f"Failed to parse QASM file: {str(e)}"
                }}
            
            # Run on simulator
            simulator = cirq.Simulator()
            result = simulator.run(circuit, repetitions=shots)
            
            # Process results
            counts = {}
            for key, value_array in result.measurements.items():
                # Convert bit array to string
                for bits in value_array:
                    bit_string = ''.join(str(bit) for bit in bits)
                    counts[bit_string] = counts.get(bit_string, 0) + 1
            
            return {"counts": counts, "metadata": {
                'platform': 'google',
                'device': 'cirq_simulator',
                'device_id': 'simulator',
                'simulator_fallback': True,
                'simulator_fallback_reason': simulator_reason
            }}
        
        # Hardware execution path
        # Read QASM file
        with open(qasm_file, 'r') as f:
            qasm_str = f.read()
        
        # Import QASM into a Cirq circuit
        try:
            circuit = circuit_from_qasm(qasm_str)
        except Exception as e:
            logger.error(f"Error importing QASM directly: {e}")
            logger.info("Attempting alternative conversion...")
            
            # If direct import fails, use a temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.qasm', delete=False).name
            with open(temp_file, 'w') as f:
                f.write(qasm_str)
            
            try:
                circuit = circuit_from_qasm(temp_file)
            except Exception as e2:
                logger.error(f"Failed to import QASM with alternative method: {e2}")
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return {"counts": {"error": 1}, "metadata": {
                    'platform': 'google',
                    'device_id': device_id,
                    'error': f"Failed to parse QASM file: {str(e2)}"
                }}
            
            try:
                os.remove(temp_file)
            except:
                pass
        
        # Set environment variable for authentication
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_auth_file
        
        # Create the quantum engine service
        try:
            engine = cirq_google.Engine(
                project_id=google_project_id,
                processor_id=device_id
            )
            
            # Check processor availability
            processors = engine.list_processors()
            processor_ids = [p.processor_id for p in processors]
            
            if device_id not in processor_ids:
                available_processors = ", ".join(processor_ids)
                logger.warning(f"Processor '{device_id}' not found. Available processors: {available_processors}")
                
                if processors:
                    # Use the first available processor
                    device_id = processors[0].processor_id
                    logger.info(f"Using available processor: {device_id}")
                else:
                    # Fall back to simulator if no processors are available
                    use_simulator = True
                    simulator_reason = "No Google Quantum processors available"
                    logger.warning(f"{simulator_reason}. Falling back to simulator.")
                    
                    # Run on simulator (similar to above)
                    simulator = cirq.Simulator()
                    result = simulator.run(circuit, repetitions=shots)
                    
                    # Process results
                    counts = {}
                    for key, value_array in result.measurements.items():
                        for bits in value_array:
                            bit_string = ''.join(str(bit) for bit in bits)
                            counts[bit_string] = counts.get(bit_string, 0) + 1
                    
                    return {"counts": counts, "metadata": {
                        'platform': 'google',
                        'device': 'cirq_simulator',
                        'device_id': 'simulator',
                        'simulator_fallback': True,
                        'simulator_fallback_reason': simulator_reason
                    }}
            
            # Get the processor
            processor = engine.get_processor(device_id)
            
            # Get the device for validation
            device = processor.get_device()
            
            # Validate the circuit for the device
            if not cirq.is_valid_circuit_for_device(circuit, device):
                logger.warning("Circuit contains operations not supported by the device. Attempting to convert...")
                
                # Try to convert the circuit to be compatible
                try:
                    from cirq.optimizers import convert_to_cz_and_single_gates
                    circuit = convert_to_cz_and_single_gates(circuit)
                    
                    if not cirq.is_valid_circuit_for_device(circuit, device):
                        simulator_reason = f"Circuit cannot be made compatible with {device_id}"
                        logger.warning(f"{simulator_reason}. Falling back to simulator.")
                        
                        # Run on simulator (similar to above)
                        simulator = cirq.Simulator()
                        result = simulator.run(circuit, repetitions=shots)
                        
                        # Process results
                        counts = {}
                        for key, value_array in result.measurements.items():
                            for bits in value_array:
                                bit_string = ''.join(str(bit) for bit in bits)
                                counts[bit_string] = counts.get(bit_string, 0) + 1
                        
                        return {"counts": counts, "metadata": {
                            'platform': 'google',
                            'device': 'cirq_simulator',
                            'device_id': 'simulator',
                            'simulator_fallback': True,
                            'simulator_fallback_reason': simulator_reason
                        }}
                except Exception as e:
                    logger.error(f"Error converting circuit: {e}")
                    return {"counts": {"error": 1}, "metadata": {
                        'platform': 'google',
                        'device_id': device_id,
                        'error': f"Failed to convert circuit: {str(e)}"
                    }}
            
            # Create a program from the circuit
            program = cirq.Circuit(circuit)
            
            # Submit the job
            logger.info(f"Submitting job to Google Quantum processor: {device_id}")
            
            try:
                # Run calibration (or experiment depending on the device)
                try:
                    job = processor.run_calibration(program, repetitions=shots)
                except (AttributeError, NotImplementedError):
                    # Fall back to run method if run_calibration is not available
                    logger.info("run_calibration not available, using run method instead")
                    job = processor.run(program, repetitions=shots)
                
                job_id = job.id()
                logger.info(f"Job submitted. Job ID: {job_id}")
                
                metadata = {
                    'platform': 'google',
                    'provider': 'Google',
                    'device': device_id,
                    'device_id': device_id,
                    'job_id': job_id,
                    'project_id': google_project_id
                }
                
                # Wait for results if requested
                if wait_for_results:
                    logger.info(f"Waiting for job to complete (timeout: {poll_timeout_seconds}s)...")
                    start_time = time.time()
                    
                    # Poll until job completes or timeout
                    while time.time() - start_time < poll_timeout_seconds:
                        # Check job status
                        status = job.status()
                        logger.info(f"Current status: {status}")
                        
                        if status in ['READY', 'SUCCESS', 'FAILURE', 'CANCELLED']:
                            break
                        
                        time.sleep(30)  # Sleep for 30 seconds between polls
                    
                    # Check if job completed successfully
                    if job.status() == 'SUCCESS':
                        logger.info("Job completed successfully!")
                        
                        # Retrieve and process results
                        result_dict = job.results()
                        
                        # Convert results to counts dictionary
                        counts = _process_google_results(result_dict)
                        
                        # Create result object
                        return {"counts": counts, "metadata": metadata}
                    else:
                        error_msg = f"Job failed or timed out. Final status: {job.status()}"
                        logger.error(error_msg)
                        return {"counts": {"error": 1}, "metadata": {
                            **metadata,
                            'error': error_msg
                        }}
                else:
                    # Return a placeholder result with job information
                    return {"counts": {"pending": shots}, "metadata": {
                        **metadata,
                        'status': job.status(),
                        'message': 'Job submitted but not waiting for results'
                    }}
            except Exception as e:
                error_msg = f"Failed to submit job: {str(e)}"
                logger.error(error_msg)
                return {"counts": {"error": 1}, "metadata": {
                    'platform': 'google',
                    'device_id': device_id,
                    'error': error_msg
                }}
                
        except Exception as e:
            error_msg = f"Failed to connect to Google Quantum: {str(e)}"
            logger.error(error_msg)
            return {"counts": {"error": 1}, "metadata": {
                'platform': 'google',
                'device_id': device_id,
                'error': error_msg
            }}
            
    except Exception as e:
        error_msg = f"Error in run_on_google_hardware: {str(e)}"
        logger.error(error_msg)
        return {"counts": {"error": 1}, "metadata": {
            'platform': 'google',
            'error': error_msg
        }}
        
def _process_google_results(result_dict) -> Dict[str, int]:
    """
    Process Google Quantum results into a counts dictionary.
    
    Args:
        result_dict: Results from Google Quantum job
        
    Returns:
        Dict[str, int]: Counts dictionary in format {'bit_string': count}
    """
    counts = {}
    
    try:
        # Try to process as a measurement dictionary
        for key, value in result_dict.items():
            # Convert key to binary string
            bit_string = ''.join(map(str, key))
            counts[bit_string] = value
    except Exception:
        try:
            # Try to process as a result object with measurement key
            measurements = result_dict.measurements
            for key, values in measurements.items():
                for value in values:
                    bit_string = ''.join(map(str, value))
                    counts[bit_string] = counts.get(bit_string, 0) + 1
        except Exception:
            # If all else fails, return raw data
            counts = {"raw_data": json.dumps(str(result_dict))}
    
    return counts