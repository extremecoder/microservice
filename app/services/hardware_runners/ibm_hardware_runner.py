"""
IBM Quantum Hardware Runner for executing quantum circuits on IBM Quantum hardware.
"""

import os
import time
import tempfile
import json
import logging
from typing import Dict, Any, Optional

# Import JobStatus here
from qiskit.providers.jobstatus import JobStatus

logger = logging.getLogger(__name__)

def run_on_ibm_hardware(qasm_file: str, device_id: str = None, shots: int = 1024,
                      wait_for_results: bool = True, poll_timeout_seconds: int = 3600,
                      optimization_level: int = 1, api_token: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Run a QASM file on IBM Quantum hardware.
    
    Args:
        qasm_file: Path to the QASM file
        device_id: IBM Quantum backend name
        shots: Number of shots to run
        wait_for_results: Whether to wait for results (True) or return immediately (False)
        poll_timeout_seconds: Maximum time to wait for results, in seconds
        optimization_level: Transpiler optimization level (0-3)
        api_token: IBM Quantum API token (optional)
        **kwargs: Additional arguments
        
    Returns:
        Dict[str, Any]: Dictionary containing counts and metadata
    """
    # Initialize counts at the beginning of the function
    counts = {"error": 1}
    metadata = {
        'platform': 'ibm',
        'device_id': device_id or 'unknown',
    }
    
    try:
        # Try to import Qiskit - if not available, this will fail early
        try:
            from qiskit import QuantumCircuit
        except ImportError:
            logger.error("Qiskit not installed. Please install qiskit to use IBM hardware.")
            return {"counts": {"error": 1}, "metadata": {
                'platform': 'ibm',
                'device_id': device_id,
                'error': "Qiskit not installed. Please install qiskit to use IBM hardware."
            }}
        
        # Get IBM credentials - either from config or from args
        ibm_api_token = None
        
        # First check if token is provided as an argument
        if api_token:
            ibm_api_token = api_token
            logger.info("Using IBM Quantum API token provided in arguments.")
        
        # Check environment variables
        if not ibm_api_token:
            # Try multiple possible environment variable names
            for env_var in ['QISKIT_IBM_TOKEN', 'IBM_QUANTUM_TOKEN', 'IBM_API_TOKEN']:
                if env_var in os.environ and os.environ[env_var]:
                    ibm_api_token = os.environ[env_var]
                    logger.info(f"Using IBM Quantum API token from environment variable: {env_var}")
                    break
        
        # Try to get from Qiskit saved credentials
        if not ibm_api_token:
            try:
                from qiskit_ibm_provider import IBMProvider
                # This uses credentials saved via IBMProvider.save_account()
                provider = IBMProvider()
                logger.info("Using IBM Quantum credentials from Qiskit saved account.")
                ibm_api_token = "USING_SAVED_ACCOUNT"  # Placeholder to indicate we're using saved credentials
            except Exception as e:
                logger.warning(f"Error accessing saved IBM credentials: {e}")
        
        if not ibm_api_token:
            error_msg = "IBM Quantum API token not found. Please provide it using --api-token or set it as an environment variable (QISKIT_IBM_TOKEN, IBM_QUANTUM_TOKEN)."
            logger.error(error_msg)
            return {"counts": {"error": 1}, "metadata": {
                'platform': 'ibm',
                'device_id': device_id,
                'error': error_msg
            }}
        
        # Read QASM file
        with open(qasm_file, 'r') as f:
            qasm_str = f.read()
        
        # Load the QASM into a Qiskit circuit
        temp_file = tempfile.NamedTemporaryFile(suffix='.qasm', delete=False).name
        with open(temp_file, 'w') as f:
            f.write(qasm_str)
        
        # Parse the circuit
        circuit = QuantumCircuit.from_qasm_file(temp_file)
        
        try:
            os.remove(temp_file)
        except:
            pass
        
        # Initialize IBM Quantum services based on API version
        try:
            try:
                # First try with Qiskit IBM Runtime (newer API)
                from qiskit_ibm_runtime import QiskitRuntimeService, Sampler
                
                # Initialize the QiskitRuntimeService
                if ibm_api_token == "USING_SAVED_ACCOUNT":
                    service = QiskitRuntimeService()
                else:
                    service = QiskitRuntimeService(channel="ibm_quantum", token=ibm_api_token)
                
                logger.info("Using QiskitRuntimeService API")
                
                if not service.active_account():
                    raise RuntimeError("IBM Quantum credentials invalid or expired")
                
                # Get available hardware backends
                backends = service.backends(operational=True, simulator=False)
                if not backends:
                    raise RuntimeError("No IBM Quantum devices available")
                
                # Select backend
                if device_id and any(b.name == device_id for b in backends):
                    device = next(b for b in backends if b.name == device_id)
                    logger.info(f"Using specified device: {device.name}")
                else:
                    if device_id:
                        logger.warning(f"Specified device {device_id} not found or not available")
                    
                    # Get least busy device
                    device = min(backends, key=lambda b: b.status().pending_jobs)
                    logger.info(f"Using least busy device: {device.name}")
                
                # Print device info
                logger.info(f"Device: {device.name}, Qubits: {device.num_qubits}")
                
                # Transpile circuit for the target device
                from qiskit import transpile
                transpiled = transpile(circuit, backend=device, optimization_level=optimization_level)
                
                # Submit the job using Runtime API
                logger.info(f"Submitting job to {device.name} using Runtime API")
                
                # Try different Sampler initialization approaches
                try:
                    # First try SamplerV2 (newer API)
                    from qiskit_ibm_runtime import SamplerV2
                    logger.info("Attempting to initialize SamplerV2")
                    
                    # Set options for shots
                    options = {"default_shots": shots}
                    
                    # Initialize SamplerV2
                    sampler = SamplerV2(mode=device, options=options)
                    
                    # Submit job
                    job = sampler.run([transpiled])
                    logger.info("Successfully submitted job using SamplerV2")
                except (ImportError, Exception) as e:
                    logger.warning(f"Error with SamplerV2 initialization: {str(e)}")
                    
                    # Fall back to regular Sampler
                    logger.info("Falling back to regular Sampler")
                    sampler = Sampler(backend=device)
                    job = sampler.run([transpiled], shots=shots)
                    logger.info("Successfully submitted job using Sampler")
                
                # Get job ID
                job_id = job.job_id()
                logger.info(f"Job ID: {job_id}")
                logger.info(f"Monitor at: https://quantum.ibm.com/jobs/{job_id}")
            
            except (ImportError, Exception) as e:
                # Fall back to IBMProvider (older API)
                logger.warning(f"Runtime API failed: {str(e)}")
                logger.info("Falling back to IBMProvider API")
                
                from qiskit_ibm_provider import IBMProvider
                
                # Initialize provider
                if ibm_api_token == "USING_SAVED_ACCOUNT":
                    provider = IBMProvider()
                else:
                    provider = IBMProvider(token=ibm_api_token)
                
                # Get available backends
                backends = provider.backends(operational=True, simulator=False)
                
                # Select backend
                if device_id and any(b.name == device_id for b in backends):
                    device = provider.get_backend(device_id)
                    logger.info(f"Using specified device: {device.name}")
                else:
                    if device_id:
                        logger.warning(f"Specified device {device_id} not found or not available")
                    
                    # Get least busy backend
                    device = provider.backend.least_busy(backends)
                    logger.info(f"Using least busy device: {device.name}")
                
                # Print device info
                logger.info(f"Device: {device.name}, Qubits: {device.configuration().n_qubits}")
                
                # Transpile circuit for the target device
                from qiskit import transpile
                transpiled = transpile(circuit, backend=device, optimization_level=optimization_level)
                
                # Submit the job
                logger.info(f"Submitting job to {device.name}")
                job = device.run(transpiled, shots=shots)
                job_id = job.job_id()
                logger.info(f"Job ID: {job_id}")
            
            # Set up metadata
            metadata = {
                'platform': 'ibm',
                'provider': 'IBM',
                'device': device.name if hasattr(device, 'name') else str(device),
                'device_id': device_id,
                'provider_job_id': job_id,
                'optimization_level': optimization_level
            }
            
            # Wait for results if requested
            if wait_for_results:
                logger.info(f"Waiting for job to complete (timeout: {poll_timeout_seconds}s)...")
                start_time = time.time()
                
                # Poll until job completes or timeout
                while time.time() - start_time < poll_timeout_seconds:
                    job_status = job.status()
                    logger.info(f"Current status: {job_status}")
                    
                    # Check if job completed or failed
                    if isinstance(job_status, str):
                        # For newer API, status is a string
                        if job_status in ["DONE", "ERROR", "CANCELLED"]:
                            break
                    else:
                        # For older API, status is an enum
                        if job_status in [JobStatus.DONE, JobStatus.ERROR, JobStatus.CANCELLED]:
                            break
                    
                    time.sleep(30)  # Sleep for 30 seconds between polls
                
                # Check if job completed successfully
                job_final_status = job.status()
                logger.info(f"Final job status check. Type: {type(job_final_status)}, Value: {job_final_status}")
                
                # Modify the condition to check for both enum and string "DONE"
                if job and wait_for_results and (job_final_status == JobStatus.DONE or str(job_final_status).upper() == "DONE"):
                    logger.info("Job completed successfully!")
                    
                    # Process the job result
                    status_str = job_final_status.name if hasattr(job_final_status, 'name') else str(job_final_status)
                    metadata.update({
                        'shots': shots,
                        'status': status_str,
                        'execution_time': time.time() - start_time
                    })
                    
                    try:
                        # Get the result object
                        result = job.result()
                        logger.info(f"Result object type: {type(result)}")
                        logger.debug(f"Result object attributes: {dir(result)}")
                        
                        # Default counts from initialization - explicitly set to None
                        result_counts = None
                        
                        # Check different result formats and try to extract counts
                        # Standard Qiskit result format
                        if hasattr(result, 'get_counts'):
                            try:
                                result_counts = result.get_counts(0)
                                logger.info(f"Successfully extracted counts from get_counts()")
                            except Exception as e:
                                logger.warning(f"Failed to extract counts using get_counts(): {str(e)}")
                        
                        # Try to extract from data attribute if available
                        elif hasattr(result, 'data'):
                            if hasattr(result.data, 'counts'):
                                result_counts = result.data.counts
                                logger.info("Successfully extracted counts from data.counts")
                        
                        # PrimitiveResult format (IBM Qiskit Runtime)
                        elif hasattr(result, '_pub_results') and result._pub_results:
                            logger.info("Processing PrimitiveResult format (SamplerV2)")
                            logger.info(f"_pub_results length: {len(result._pub_results)}")

                            if len(result._pub_results) > 0:
                                pub_result = result._pub_results[0]
                                logger.info(f"pub_result type: {type(pub_result)}")
                                logger.debug(f"pub_result attributes: {dir(pub_result)}")

                                # Get classical register name
                                creg_name = None
                                if hasattr(circuit, 'cregs') and circuit.cregs:
                                    # Assuming the first classical register is the one used for measurements
                                    creg_name = circuit.cregs[0].name
                                    logger.info(f"Found classical register name from circuit: {creg_name}")
                                else:
                                    # Fallback if no cregs found (might happen with transpiled circuits)
                                    # We can try a common default or inspect data attributes later
                                    logger.warning("Could not find classical register name in circuit object. Will try common names or inspect data.")
                                    # Defaulting to 'c' as seen in test_circuit.qasm
                                    creg_name = "c" 

                                # Try to extract counts as shown in the successful debug script
                                if hasattr(pub_result, 'data'):
                                    logger.debug(f"pub_result.data type: {type(pub_result.data)}")
                                    logger.debug(f"pub_result.data attributes: {dir(pub_result.data)}")

                                    # Function to attempt extraction with a given register name
                                    def attempt_extraction(reg_name):
                                        if reg_name and hasattr(pub_result.data, reg_name):
                                            creg_data = getattr(pub_result.data, reg_name)
                                            logger.info(f"Attempting extraction with register name: {reg_name}")
                                            logger.debug(f"creg_data type: {type(creg_data)}")
                                            logger.debug(f"creg_data attributes: {dir(creg_data)}")

                                            if hasattr(creg_data, 'get_counts'):
                                                try:
                                                    counts = creg_data.get_counts()
                                                    logger.info(f"Counts extracted successfully using register '{reg_name}': {counts}")
                                                    return counts
                                                except Exception as e:
                                                    logger.warning(f"Error calling get_counts on register '{reg_name}': {e}")
                                            else:
                                                logger.warning(f"Register data for '{reg_name}' has no get_counts method.")
                                        else:
                                            logger.debug(f"pub_result.data has no attribute named '{reg_name}'")
                                        return None

                                    # Try with the determined or default classical register name first
                                    extracted_counts = attempt_extraction(creg_name)

                                    # If failed, try common default names or inspect other attributes
                                    if extracted_counts is None:
                                        logger.info("Primary extraction failed. Trying common register names or inspecting attributes.")
                                        common_names = ['c', 'meas', 'measurement'] # Add other potential names if needed
                                        if creg_name in common_names: # Avoid re-trying the same name
                                            common_names.remove(creg_name)
                                            
                                        for name in common_names:
                                            extracted_counts = attempt_extraction(name)
                                            if extracted_counts is not None:
                                                break # Stop if successful

                                    # If still None, inspect all attributes of pub_result.data
                                    if extracted_counts is None:
                                        logger.warning("Could not extract counts using known/common register names. Inspecting all data attributes.")
                                        for attr in dir(pub_result.data):
                                            if not attr.startswith('_'):
                                                logger.debug(f"Inspecting attribute: {attr}")
                                                attr_value = getattr(pub_result.data, attr)
                                                if hasattr(attr_value, 'get_counts'):
                                                    logger.info(f"Found get_counts method on attribute: {attr}. Attempting extraction.")
                                                    extracted_counts = attempt_extraction(attr)
                                                    if extracted_counts is not None:
                                                        break # Stop if successful
                                                        
                                    # Assign to result_counts if extraction was successful
                                    if extracted_counts is not None:
                                        result_counts = extracted_counts
                                    else:
                                        logger.error("Failed to extract counts from pub_result.data using all known methods.")

                                else:
                                    logger.error("pub_result has no data attribute")
                            else:
                                logger.error("result has no _pub_results attribute or it's empty")
                        
                        # If we found valid counts, use them
                        if result_counts is not None:
                            counts = result_counts
                            logger.info(f"Using extracted counts: {counts}")
                        else:
                            # If no counts found, create default counts
                            logger.warning("No counts could be extracted, using default")
                            counts = {"error_extracting_counts": 1}
                            
                        # Return dictionary with counts and metadata
                        return {"counts": counts, "metadata": metadata}
                        
                    except Exception as e:
                        error_msg = f"Failed to process result: {str(e)}"
                        logger.error(error_msg)
                        return {"counts": {"error": 1}, "metadata": {
                            **metadata,
                            'error': error_msg
                        }}
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
                    'status': 'QUEUED',
                    'message': 'Job submitted but not waiting for results'
                }}
                
        except Exception as e:
            error_msg = f"Failed to submit circuit to IBM Quantum: {str(e)}"
            logger.error(error_msg)
            
            # Special handling for unbound local error for counts
            if isinstance(e, UnboundLocalError) and "local variable 'counts' referenced before assignment" in str(e):
                logger.error("Caught counts variable reference error, using default value")
                return {"counts": {"error_unbound_counts": 1}, "metadata": {
                    'platform': 'ibm',
                    'device_id': device_id,
                    'error': "Failed to process result: counts variable was not properly assigned"
                }}
            
            return {"counts": {"error": 1}, "metadata": {
                'platform': 'ibm',
                'device_id': device_id,
                'error': error_msg
            }}
            
    except Exception as e:
        error_msg = f"Error in run_on_ibm_hardware: {str(e)}"
        logger.error(error_msg)
        return {"counts": {"error": 1}, "metadata": {
            'platform': 'ibm',
            'error': error_msg
        }} 