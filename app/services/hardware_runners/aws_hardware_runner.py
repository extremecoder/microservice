"""
AWS Braket Hardware Runner for executing quantum circuits on AWS Quantum hardware.
"""

import os
import time
import tempfile
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def run_on_aws_hardware(qasm_file: str, device_id: str = None, shots: int = 1000,
                      wait_for_results: bool = True, poll_timeout_seconds: int = 3600,
                      access_key: Optional[str] = None, secret_key: Optional[str] = None,
                      region: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Run a QASM file on AWS Braket hardware.
    
    Args:
        qasm_file: Path to the QASM file
        device_id: AWS Braket device ARN or name
        shots: Number of shots to run
        wait_for_results: Whether to wait for results (True) or return immediately (False)
        poll_timeout_seconds: Maximum time to wait for results, in seconds
        access_key: AWS access key (optional)
        secret_key: AWS secret key (optional)
        region: AWS region (optional)
        **kwargs: Additional arguments
        
    Returns:
        Dict[str, Any]: Dictionary containing counts and metadata
    """
    try:
        # Try to import Braket - if not available, this will fail early
        try:
            from braket.aws import AwsDevice
            from braket.circuits import Circuit
            from braket.ir.openqasm import Program as OpenQasmProgram
        except ImportError:
            logger.error("Amazon Braket SDK not installed. Please install amazon-braket-sdk to use AWS hardware.")
            return {"error": 1, 'platform': 'aws', 'device_id': device_id, 'error': "Amazon Braket SDK not installed. Please install amazon-braket-sdk to use AWS hardware."}
        
        # Get AWS credentials
        aws_access_key = access_key
        aws_secret_key = secret_key
        aws_region = region if region else 'us-east-1'  # Default region
        
        # Check environment variables if not provided
        if not aws_access_key or not aws_secret_key:
            if 'AWS_ACCESS_KEY_ID' in os.environ and 'AWS_SECRET_ACCESS_KEY' in os.environ:
                aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
                aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
                logger.info("Using AWS credentials from environment variables.")
                
                if not aws_region and 'AWS_REGION' in os.environ:
                    aws_region = os.environ.get('AWS_REGION')
                elif not aws_region and 'AWS_DEFAULT_REGION' in os.environ:
                    aws_region = os.environ.get('AWS_DEFAULT_REGION')
        
        # Check if we have credentials
        if not aws_access_key or not aws_secret_key:
            # Try to use default credentials (from ~/.aws/credentials)
            logger.info("No explicit AWS credentials provided, using default credentials.")
        else:
            # Set environment variables for credentials
            os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key
            os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_key
            os.environ['AWS_REGION'] = aws_region
        
        # Read QASM file
        with open(qasm_file, 'r') as f:
            qasm_str = f.read()
        
        # Adapt QASM for Braket compatibility if needed
        # This is a placeholder - you might need specific conversion for Braket
        if qasm_str.startswith('OPENQASM 2.0'):
            logger.info("Converting OpenQASM 2.0 to OpenQASM 3.0 (Braket compatible)")
            # Simple header conversion (might need more sophisticated conversion)
            qasm_str = qasm_str.replace('OPENQASM 2.0', 'OPENQASM 3.0')
        
        # Create a QASM program for Braket
        try:
            # Try direct OpenQASM 3 support
            logger.info("Creating OpenQASM program for Braket...")
            qasm_program = OpenQasmProgram(source=qasm_str)
            
            # If device_id is not specified or is not an ARN, use a default device or look up by name
            if not device_id:
                # List available devices
                from braket.aws import AwsDevice
                
                # Get all QPU devices
                devices = AwsDevice.get_devices(provider_names=['IonQ', 'Rigetti', 'Oxford', 'IQM'], statuses=['ONLINE'])
                
                if not devices:
                    logger.warning("No quantum hardware devices available. Using simulator.")
                    # Use the SV1 simulator
                    device_id = "arn:aws:braket:::device/quantum-simulator/amazon/sv1"
                else:
                    # Use the first available device
                    device_id = devices[0].arn
                    logger.info(f"No device specified, using available device: {device_id}")
            elif not device_id.startswith('arn:'):
                # If device_id is not an ARN, try to find by name
                dev_mappings = {
                    'sv1': 'arn:aws:braket:::device/quantum-simulator/amazon/sv1',
                    'dm1': 'arn:aws:braket:::device/quantum-simulator/amazon/dm1',
                    'tn1': 'arn:aws:braket:::device/quantum-simulator/amazon/tn1',
                    'ionq': 'arn:aws:braket:::device/qpu/ionq/ionQdevice',
                    'aria-1': 'arn:aws:braket:us-east-1::device/qpu/ionq/Aria-1',
                    'aria-2': 'arn:aws:braket:us-east-1::device/qpu/ionq/Aria-2',
                    'rigetti': 'arn:aws:braket:us-west-1::device/qpu/rigetti/Aspen-M-3',
                    'aspen-m-3': 'arn:aws:braket:us-west-1::device/qpu/rigetti/Aspen-M-3'
                }
                
                if device_id.lower() in dev_mappings:
                    device_id = dev_mappings[device_id.lower()]
                    logger.info(f"Using device ARN for {device_id}")
                else:
                    logger.warning(f"Device '{device_id}' not recognized, using SV1 simulator.")
                    device_id = "arn:aws:braket:::device/quantum-simulator/amazon/sv1"
            
            # Connect to the device
            device = AwsDevice(device_id)
            logger.info(f"Connected to AWS device: {device.name}")
            
            # Create the task
            logger.info(f"Submitting task to AWS Braket ({device.name})...")
            task = device.run(qasm_program, shots=shots)
            
            # Get task ID
            task_id = task.id
            logger.info(f"Task submitted. Task ID: {task_id}")
            
            metadata = {
                'platform': 'aws',
                'provider': device.provider_name,
                'device': device.name,
                'device_id': device_id,
                'task_id': task_id
            }
            
            # Wait for results if requested
            if wait_for_results:
                logger.info(f"Waiting for task to complete (timeout: {poll_timeout_seconds}s)...")
                start_time = time.time()
                
                # Poll until task completes or timeout
                while time.time() - start_time < poll_timeout_seconds:
                    task_status = task.state()
                    logger.info(f"Current status: {task_status}")
                    
                    if task_status in ['COMPLETED', 'FAILED', 'CANCELLED']:
                        break
                    
                    time.sleep(10)  # Sleep for 10 seconds between polls
                
                # Check if task completed successfully
                if task.state() == 'COMPLETED':
                    logger.info("Task completed successfully!")
                    
                    # Retrieve and process results
                    result = task.result()
                    
                    # Get measurement counts
                    counts = result.measurement_counts
                    
                    if not counts:
                        # If no measurement_counts available, try to reconstruct from measurement_probabilities
                        logger.info("No measurement counts available, trying measurement probabilities.")
                        probs = result.measurement_probabilities
                        if probs:
                            # Convert top probabilities to counts by scaling with shots
                            counts = {state: int(prob * shots + 0.5) for state, prob in probs.items()}
                        else:
                            logger.warning("No measurement data available. Creating empty result.")
                            counts = {"0": shots}  # Fallback
                    
                    # Create result dictionary
                    return {'counts': counts, 'metadata': metadata}
                else:
                    error_msg = f"Task failed or timed out. Final status: {task.state()}"
                    logger.error(error_msg)
                    return {"error": 1, **metadata, 'error': error_msg}
            else:
                # Return a placeholder result with task information
                return {'counts': {"pending": shots}, 'metadata': {**metadata, 'status': 'QUEUED', 'message': 'Task submitted but not waiting for results'}}
        
        except Exception as e:
            # Fall back to Qiskit conversion if direct OpenQASM 3 fails
            logger.warning(f"Direct Braket OpenQASM failed: {e}")
            logger.info("Falling back to Qiskit conversion...")
            
            try:
                from qiskit import QuantumCircuit
                from qiskit_braket_provider.providers import to_braket
                
                # Convert via Qiskit
                temp_file = tempfile.NamedTemporaryFile(suffix='.qasm', delete=False).name
                with open(temp_file, 'w') as f:
                    f.write(qasm_str)
                
                # First convert QASM to Qiskit circuit
                qiskit_circuit = QuantumCircuit.from_qasm_file(temp_file)
                
                # Then convert Qiskit circuit to Braket circuit
                braket_circuit = to_braket(qiskit_circuit)
                
                try:
                    os.remove(temp_file)
                except:
                    pass
                
                # Handle device selection same as above
                if not device_id:
                    # Use simulator
                    device_id = "arn:aws:braket:::device/quantum-simulator/amazon/sv1"
                    logger.info(f"No device specified, using simulator: {device_id}")
                elif not device_id.startswith('arn:'):
                    # If device_id is not an ARN, try to find by name
                    dev_mappings = {
                        'sv1': 'arn:aws:braket:::device/quantum-simulator/amazon/sv1',
                        'dm1': 'arn:aws:braket:::device/quantum-simulator/amazon/dm1',
                        'tn1': 'arn:aws:braket:::device/quantum-simulator/amazon/tn1',
                        'ionq': 'arn:aws:braket:::device/qpu/ionq/ionQdevice',
                        'aria-1': 'arn:aws:braket:us-east-1::device/qpu/ionq/Aria-1',
                        'aria-2': 'arn:aws:braket:us-east-1::device/qpu/ionq/Aria-2',
                        'rigetti': 'arn:aws:braket:us-west-1::device/qpu/rigetti/Aspen-M-3',
                        'aspen-m-3': 'arn:aws:braket:us-west-1::device/qpu/rigetti/Aspen-M-3'
                    }
                    
                    if device_id.lower() in dev_mappings:
                        device_id = dev_mappings[device_id.lower()]
                    else:
                        logger.warning(f"Device '{device_id}' not recognized, using SV1 simulator.")
                        device_id = "arn:aws:braket:::device/quantum-simulator/amazon/sv1"
                
                # Connect to the device
                device = AwsDevice(device_id)
                logger.info(f"Connected to AWS device: {device.name}")
                
                # Create the task
                logger.info(f"Submitting task to AWS Braket ({device.name})...")
                task = device.run(braket_circuit, shots=shots)
                
                # Get task ID
                task_id = task.id
                logger.info(f"Task submitted. Task ID: {task_id}")
                
                metadata = {
                    'platform': 'aws',
                    'provider': device.provider_name,
                    'device': device.name,
                    'device_id': device_id,
                    'task_id': task_id
                }
                
                # Wait for results if requested (similar to above)
                if wait_for_results:
                    logger.info(f"Waiting for task to complete (timeout: {poll_timeout_seconds}s)...")
                    start_time = time.time()
                    
                    # Poll until task completes or timeout
                    while time.time() - start_time < poll_timeout_seconds:
                        task_status = task.state()
                        logger.info(f"Current status: {task_status}")
                        
                        if task_status in ['COMPLETED', 'FAILED', 'CANCELLED']:
                            break
                        
                        time.sleep(10)  # Sleep for 10 seconds between polls
                    
                    # Check if task completed successfully
                    if task.state() == 'COMPLETED':
                        logger.info("Task completed successfully!")
                        
                        # Retrieve and process results
                        result = task.result()
                        
                        # Get measurement counts
                        counts = result.measurement_counts
                        
                        if not counts:
                            # Try with probabilities if counts not available
                            probs = result.measurement_probabilities
                            if probs:
                                counts = {state: int(prob * shots + 0.5) for state, prob in probs.items()}
                            else:
                                counts = {"0": shots}  # Fallback
                        
                        # Create result dictionary
                        return {'counts': counts, 'metadata': metadata}
                    else:
                        error_msg = f"Task failed or timed out. Final status: {task.state()}"
                        logger.error(error_msg)
                        return {"error": 1, **metadata, 'error': error_msg}
                else:
                    # Return a placeholder result with task information
                    return {'counts': {"pending": shots}, 'metadata': {**metadata, 'status': 'QUEUED', 'message': 'Task submitted but not waiting for results'}}
            
            except Exception as inner_e:
                error_msg = f"Failed to submit circuit to AWS Braket: {inner_e}"
                logger.error(error_msg)
                return {"error": 1, 'platform': 'aws', 'device_id': device_id, 'error': error_msg}
    
    except Exception as e:
        error_msg = f"Error in run_on_aws_hardware: {str(e)}"
        logger.error(error_msg)
        return {"error": 1, 'platform': 'aws', 'error': error_msg} 