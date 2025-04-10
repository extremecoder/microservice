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
    # Validate the circuit content
    if not request.circuit_file or request.circuit_file.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty circuit file provided"
        )
    
    # Validate shots parameter
    if request.shots <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shots must be a positive integer"
        )
    
    # Validate backend provider
    if request.backend_type.value == "simulator":
        valid_providers = ["qiskit", "braket", "cirq"]
        provider_specific_check = request.backend_provider in valid_providers
    else:  # hardware
        valid_providers = ["aws", "ibm", "google"]
        provider_specific_check = request.backend_provider in valid_providers
    
    if not provider_specific_check:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid backend provider for {request.backend_type.value}. "
                  f"Must be one of: {', '.join(valid_providers)}"
        )
    
    # Check if backend provider is available
    if not check_provider_availability(request.backend_provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{request.backend_provider} backend is not available"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save circuit to file
    circuit_path = f"{CIRCUITS_DIR}/{job_id}.qasm"
    with open(circuit_path, "w") as f:
        f.write(request.circuit_file)
    
    # Create job record
    job = {
        "job_id": job_id,
        "status": JobStatus.QUEUED.value,
        "created_at": datetime.now().isoformat(),
        "circuit_path": circuit_path,
        "parameters": request.parameters,
        "shots": request.shots,
        "backend_type": request.backend_type.value,
        "backend_provider": request.backend_provider,
        "backend_name": request.backend_name
    }
    jobs[job_id] = job
    
    # Determine execution mode
    if not request.async_mode:
        # Execute synchronously
        result = await _execute_circuit(job_id)
        
        if result.get("success", False):
            return {
                "status": "success",
                "data": CircuitExecutionResponse(
                    job_id=job_id,
                    status=JobStatus.COMPLETED,
                    execution_mode="sync",
                    counts=result.get("counts", {}),
                    execution_time=result.get("execution_time", 0.0),
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
                "error": result.get("error", "Unknown execution error")
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
        Execution results
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
        if provider == "qiskit":
            result = await execute_circuit_with_qiskit(circuit_path, parameters, shots)
        elif provider == "braket":
            result = await execute_circuit_with_braket(circuit_path, parameters, shots)
        elif provider == "cirq":
            result = await execute_circuit_with_cirq(circuit_path, parameters, shots)
        else:
            # For hardware providers, we would implement the appropriate adapters
            raise ValueError(f"Unsupported provider: {provider}")
        
        execution_time = time.time() - start_time
        
        # Save results
        result_data = {
            "counts": result,
            "execution_time": execution_time,
            "metadata": {
                "circuit_file": os.path.basename(circuit_path),
                "job_id": job_id,
                "backend_type": backend_type,
                "backend_provider": provider,
                "backend_name": backend_name,
                "shots": shots,
                "parameters": parameters,
                "created_at": job["created_at"],
                "completed_at": datetime.now().isoformat()
            },
            "success": True
        }
        
        result_path = f"{RESULTS_DIR}/{job_id}.json"
        with open(result_path, "w") as f:
            json.dump(result_data, f, indent=2)
        
        job["status"] = JobStatus.COMPLETED.value
        logger.info(f"Job {job_id} completed")
        
        return result_data
        
    except Exception as e:
        logger.error(f"Error executing job {job_id}: {e}")
        job["status"] = JobStatus.FAILED.value
        
        # Save error
        error_data = {
            "error": str(e),
            "metadata": {
                "circuit_file": os.path.basename(job["circuit_path"]),
                "job_id": job_id,
                "backend_type": job["backend_type"],
                "backend_provider": job["backend_provider"],
                "backend_name": job["backend_name"],
                "shots": job["shots"],
                "parameters": job["parameters"],
                "created_at": job["created_at"],
                "failed_at": datetime.now().isoformat()
            },
            "success": False
        }
        
        result_path = f"{RESULTS_DIR}/{job_id}.json"
        with open(result_path, "w") as f:
            json.dump(error_data, f, indent=2)
        
        return error_data
