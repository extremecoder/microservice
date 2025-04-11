"""
Circuit execution API endpoints.

This module contains endpoints for quantum circuit execution.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, status
from typing import Dict, Any, Optional
import uuid
import os
import json
from datetime import datetime
import time

from app.schemas.circuit import (
    CircuitExecutionRequest,
    CircuitExecutionResponse,
    JobStatus,
)
from app.core.logging import get_logger
from app.services.circuit_executor import (
    execute_circuit_with_qiskit,
    execute_circuit_with_braket,
    execute_circuit_with_cirq,
    execute_circuit_with_ibm_hardware,
    execute_circuit_with_aws_hardware,
    execute_circuit_with_google_hardware,
    check_provider_availability,
)

# Setup router
router = APIRouter()

# Setup logger
logger = get_logger(__name__)

# Directory paths for storing circuits and results
CIRCUITS_DIR = "circuits"
RESULTS_DIR = "results"

# Ensure directories exist
os.makedirs(CIRCUITS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# In-memory job store (in production, use a database)
jobs = {}


@router.post(
    "/execute",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Execute a quantum circuit",
    description="Submit a quantum circuit for execution on a selected backend",
)
async def execute_circuit(
    request: CircuitExecutionRequest, background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Execute a quantum circuit on a selected backend.
    
    This endpoint accepts a quantum circuit in OpenQASM format and executes it
    on the specified backend. It supports both synchronous and asynchronous
    execution modes.
    
    Args:
        request: Circuit execution request containing circuit and execution parameters
        background_tasks: FastAPI background tasks handler
        
    Returns:
        Either circuit execution results (synchronous mode) or job creation
        confirmation (asynchronous mode)
        
    Raises:
        HTTPException: If the backend provider is invalid or unavailable
    """
    job_id = str(uuid.uuid4())
    circuit_path = f"{CIRCUITS_DIR}/{job_id}.qasm"
    # If no circuit provided, try reading default circuit
    if request.circuit_file is None:
        default_circuit_dir = os.path.join(CIRCUITS_DIR, "default")
        try:
            # List files in the default directory
            default_files = [f for f in os.listdir(default_circuit_dir) if os.path.isfile(os.path.join(default_circuit_dir, f))]
            if not default_files:
                raise FileNotFoundError("No files found in default circuit directory")

            # Take the first file found
            default_file_path = os.path.join(default_circuit_dir, default_files[0])
            logger.info(f"No circuit provided, using default: {default_file_path}")
            with open(default_file_path, "r") as f:
                request.circuit_file = f.read()
        except FileNotFoundError:
             raise HTTPException(
                status_code=400,
                detail=f"No circuit provided and default circuit directory '{default_circuit_dir}' not found or empty."
            )
        except Exception as e:
            logger.error(f"Error reading default circuit from {default_circuit_dir}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, # Use 500 for unexpected server errors
                detail=f"Error reading default circuit file: {str(e)}"
            )

    # Save circuit
    try:
        with open(circuit_path, "w") as f:
            f.write(request.circuit_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save circuit file: {str(e)}")

    job = {
        "job_id": job_id,
        "status": JobStatus.QUEUED.value,
        "created_at": datetime.now().isoformat(),
        "circuit_path": circuit_path,
        "parameters": request.parameters,
        "shots": request.shots,
        "backend_type": request.backend_type.value,
        "backend_provider": request.backend_provider,
        "backend_name": request.backend_name,
        "provider_job_id": None,  # Initialize provider fields
        "provider_job_status": None,
    }
    jobs[job_id] = job
    
    # Determine execution mode
    if not request.async_mode:
        # Execute synchronously
        exec_result = await _execute_circuit(job_id)
        
        # Refresh job data after execution (it might have been updated with provider info)
        job = jobs.get(job_id, job) 
        
        if exec_result.get("success", False):
            return {
                "status": "success",
                "data": CircuitExecutionResponse(
                    job_id=job_id,
                    status=job.get("status", JobStatus.COMPLETED.value),
                    execution_mode="sync",
                    execution_time=exec_result.get("execution_time"),
                    counts=exec_result.get("counts", {}),
                    provider_job_id=job.get("provider_job_id"),  # Read from updated job record
                    provider_job_status=job.get("provider_job_status"), # Read from updated job record
                    metadata={
                        "backend_type": request.backend_type.value,
                        "backend_provider": request.backend_provider,
                        "backend_name": request.backend_name,
                        "shots": request.shots
                    }
                ).dict(),
                "error": None
            }
        else:
            return {
                "status": "error",
                "data": None,
                "error": exec_result.get("error", "Unknown execution error")
            }
    else:
        # Run in background
        background_tasks.add_task(_execute_circuit, job_id)
        
        return {
            "status": "success",
            "data": CircuitExecutionResponse(
                job_id=job_id,
                status=JobStatus.QUEUED,
                execution_mode="async",
                estimated_completion_time=None,
                provider_job_id=None,  # Initially None, will be updated after execution
                provider_job_status=None,  # Initially None, will be updated after execution
                metadata={
                    "backend_type": request.backend_type.value,
                    "backend_provider": request.backend_provider,
                    "backend_name": request.backend_name,
                    "shots": request.shots,
                    "created_at": job["created_at"]
                }
            ).dict(),
            "error": None
        }


async def _execute_circuit(job_id: str) -> Dict[str, Any]:
    """
    Internal function to execute a circuit asynchronously.
    
    Args:
        job_id: ID of the job to execute
        
    Returns:
        Execution results (including success status, counts/error, metadata)
    """
    if job_id not in jobs:
        logger.error(f"Job {job_id} not found")
        return {"success": False, "error": "Job not found"}
    
    job = jobs[job_id]
    job["status"] = JobStatus.RUNNING.value
    
    try:
        # Get circuit and parameters
        circuit_path = job["circuit_path"]
        parameters = job["parameters"] or {}
        shots = job["shots"]
        provider = job["backend_provider"]
        backend_type = job["backend_type"]
        backend_name = job["backend_name"]
        
        start_time = time.time()
        
        # Execute on appropriate backend
        if backend_type == "simulator":
            if provider == "qiskit":
                exec_result = await execute_circuit_with_qiskit(circuit_path, parameters, shots)
                counts = exec_result.get("counts")
                exec_metadata = exec_result.get("metadata", {})
            elif provider == "braket":
                exec_result = await execute_circuit_with_braket(circuit_path, parameters, shots)
                counts = exec_result.get("counts")
                exec_metadata = exec_result.get("metadata", {})
            elif provider == "cirq":
                exec_result = await execute_circuit_with_cirq(circuit_path, parameters, shots)
                counts = exec_result.get("counts")
                exec_metadata = exec_result.get("metadata", {})
            else:
                raise ValueError(f"Unsupported simulator provider: {provider}")
        elif backend_type == "hardware":
            if provider == "ibm":
                exec_result = await execute_circuit_with_ibm_hardware(circuit_path, parameters, shots, backend_name)
            elif provider == "aws":
                exec_result = await execute_circuit_with_aws_hardware(circuit_path, parameters, shots, backend_name)
            elif provider == "google":
                exec_result = await execute_circuit_with_google_hardware(circuit_path, parameters, shots, backend_name)
            else:
                raise ValueError(f"Unsupported hardware provider: {provider}")
                
            # Extract counts and metadata from the full result
            counts = exec_result.get("counts")
            exec_metadata = exec_result.get("metadata", {})
        else:
            raise ValueError(f"Unsupported backend type: {backend_type}")
        
        execution_time = time.time() - start_time
        
        # Update job record with provider details from metadata
        job["provider_job_id"] = exec_metadata.get("provider_job_id")
        job["provider_job_status"] = exec_metadata.get("status")
        job["status"] = JobStatus.COMPLETED.value
        logger.info(f"Stored provider job ID {job['provider_job_id']} for job {job_id}")
        logger.info(f"Job {job_id} completed")

        # Save results (including updated metadata)
        result_data = {
            "counts": counts,
            "execution_time": execution_time, 
            "metadata": {
                "circuit_file": os.path.basename(circuit_path),
                "job_id": job_id,
                "provider_job_id": job["provider_job_id"],  # Include in saved results
                "provider_job_status": job["provider_job_status"],
                "backend_type": backend_type,
                "backend_provider": provider,
                "backend_name": backend_name,
                "shots": shots,
                "parameters": parameters,
                "created_at": job["created_at"],
                "completed_at": datetime.now().isoformat(),
                **exec_metadata # Include any other metadata from the runner
            },
            "success": True
        }
        
        result_path = f"{RESULTS_DIR}/{job_id}.json"
        with open(result_path, "w") as f:
            json.dump(result_data, f, indent=2)
        
        return result_data # Return the full result data

    except Exception as e:
        error_msg = f"Error executing job {job_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        job["status"] = JobStatus.FAILED.value
        
        # Save error information
        result_data = {"success": False, "error": error_msg, "counts": None, "metadata": {}}
        result_path = f"{RESULTS_DIR}/{job_id}.json"
        try:
            with open(result_path, "w") as f:
                json.dump(result_data, f, indent=2)
        except Exception as write_e:
            logger.error(f"Failed to write error results for job {job_id}: {write_e}")
            
        return result_data
