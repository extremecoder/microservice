#!/usr/bin/env python3
"""
Debug script for IBM Quantum hardware execution.
"""
import os
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Path to the test circuit
QASM_FILE = "test_circuit.qasm"

def debug_ibm_quantum():
    """Debug IBM Quantum execution with direct API access."""
    try:
        # Import required modules
        from qiskit import QuantumCircuit, transpile
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
        
        # Load the QASM circuit
        logger.info(f"Loading circuit from {QASM_FILE}")
        circuit = QuantumCircuit.from_qasm_file(QASM_FILE)
        logger.info(f"Circuit loaded: {circuit.name}")
        logger.info(f"Number of qubits: {circuit.num_qubits}")
        logger.info(f"Classical registers: {circuit.cregs}")
        
        # Print circuit details
        logger.info(f"Circuit drawing:\n{circuit.draw()}")
        
        # Get IBM Quantum credentials from environment
        ibm_api_token = os.environ.get('IBM_QUANTUM_TOKEN')
        if not ibm_api_token:
            logger.error("IBM_QUANTUM_TOKEN environment variable not set")
            return
            
        # Initialize the QiskitRuntimeService
        logger.info("Initializing QiskitRuntimeService")
        service = QiskitRuntimeService(channel="ibm_quantum", token=ibm_api_token)
        
        # Get available backends
        backends = service.backends(operational=True)
        logger.info(f"Available backends: {[b.name for b in backends]}")
        
        # Try to find a simulator first
        backend = None
        for b in backends:
            if 'simulator' in b.name.lower():
                backend = b
                break
                
        if not backend:
            # Use least busy device
            backend = min(backends, key=lambda b: b.status().pending_jobs)
            
        logger.info(f"Using backend: {backend.name}")
        
        # Transpile the circuit for the backend
        logger.info(f"Transpiling circuit for {backend.name}")
        transpiled_circuit = transpile(circuit, backend=backend)
        logger.info(f"Transpiled circuit:\n{transpiled_circuit.draw()}")
        
        # Set options for the sampler
        options = {"default_shots": 1024}
        
        # Initialize SamplerV2
        logger.info("Initializing SamplerV2")
        sampler = SamplerV2(mode=backend, options=options)
        
        # Submit job
        logger.info(f"Submitting job to {backend.name}")
        job = sampler.run([transpiled_circuit])
        job_id = job.job_id()
        logger.info(f"Job ID: {job_id}")
        logger.info(f"Monitor at: https://quantum.ibm.com/jobs/{job_id}")
        
        # Wait for job to complete
        logger.info("Waiting for job to complete...")
        job_status = job.status()
        while job_status not in ["DONE", "ERROR", "CANCELLED"]:
            time.sleep(5)
            job_status = job.status()
            logger.info(f"Current status: {job_status}")
            
        if job_status == "DONE":
            logger.info("Job completed successfully!")
            
            # Get the result
            result = job.result()
            logger.info(f"Result type: {type(result)}")
            logger.info(f"Result attributes: {dir(result)}")
            
            # Try to extract counts using the pattern from the example
            if hasattr(result, '_pub_results') and result._pub_results:
                logger.info(f"_pub_results length: {len(result._pub_results)}")
                
                if len(result._pub_results) > 0:
                    pub_result = result._pub_results[0]
                    logger.info(f"pub_result type: {type(pub_result)}")
                    logger.info(f"pub_result attributes: {dir(pub_result)}")
                    
                    # Get classical register name
                    creg_name = None
                    if circuit.cregs:
                        creg_name = circuit.cregs[0].name
                        
                    logger.info(f"Classical register name: {creg_name}")
                    
                    # Try to extract counts as shown in the example
                    if hasattr(pub_result, 'data'):
                        logger.info(f"pub_result.data attributes: {dir(pub_result.data)}")
                        
                        # Check if data has the classical register
                        if hasattr(pub_result.data, creg_name):
                            creg_data = getattr(pub_result.data, creg_name)
                            logger.info(f"creg_data type: {type(creg_data)}")
                            logger.info(f"creg_data attributes: {dir(creg_data)}")
                            
                            # Try to get counts
                            if hasattr(creg_data, 'get_counts'):
                                counts = creg_data.get_counts()
                                logger.info(f"Counts extracted: {counts}")
                            else:
                                logger.error("creg_data has no get_counts method")
                        else:
                            logger.error(f"pub_result.data has no attribute named {creg_name}")
                            
                            # List all available attributes
                            for attr in dir(pub_result.data):
                                if not attr.startswith('__'):
                                    logger.info(f"Available attribute: {attr}")
                                    
                                    # Try to access this attribute
                                    attr_value = getattr(pub_result.data, attr)
                                    logger.info(f"Attribute value type: {type(attr_value)}")
                                    
                                    # If it's something that might contain our data, inspect it
                                    if not callable(attr_value):
                                        if hasattr(attr_value, 'get_counts'):
                                            try:
                                                counts = attr_value.get_counts()
                                                logger.info(f"Found counts in {attr}: {counts}")
                                            except Exception as e:
                                                logger.error(f"Error getting counts from {attr}: {e}")
                    else:
                        logger.error("pub_result has no data attribute")
            else:
                logger.error("result has no _pub_results attribute or it's empty")
                
        else:
            logger.error(f"Job failed with status: {job_status}")
    
    except Exception as e:
        logger.error(f"Error in debug_ibm_quantum: {e}", exc_info=True)

if __name__ == "__main__":
    debug_ibm_quantum() 