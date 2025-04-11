"""
Circuit execution schemas for the Quantum Computing API.

This module contains the request and response schemas for circuit execution.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class BackendType(str, Enum):
    """Enum for backend types."""
    SIMULATOR = "simulator"
    HARDWARE = "hardware"


class SimulatorProvider(str, Enum):
    """Enum for simulator providers."""
    QISKIT = "qiskit"
    BRAKET = "braket"
    CIRQ = "cirq"


class HardwareProvider(str, Enum):
    """Enum for hardware providers."""
    AWS = "aws"
    IBM = "ibm"
    GOOGLE = "google"


class CircuitExecutionRequest(BaseModel):
    """
    Request model for circuit execution.
    
    Attributes:
        circuit_file: OpenQASM circuit file content
        shots: Number of execution shots
        backend_type: "simulator" or "hardware"
        backend_provider: Provider name (qiskit, braket, cirq, aws, ibm, google)
        backend_name: Specific backend name if applicable
        async_mode: Boolean flag for asynchronous execution
        parameters: Dictionary of circuit parameters if the circuit is parameterized
    """
    circuit_file: Optional[str] = Field(None, description="OpenQASM circuit file content")
    shots: int = Field(1024, description="Number of execution shots")
    backend_type: BackendType = Field(..., description="Backend type (simulator or hardware)")
    backend_provider: str = Field(..., description="Provider name")
    backend_name: Optional[str] = Field(None, description="Specific backend name if applicable")
    async_mode: bool = Field(False, description="Flag for asynchronous execution")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Circuit parameters")


class JobMetadata(BaseModel):
    """
    Job metadata model.
    
    Attributes:
        backend_type: Backend type (simulator or hardware)
        backend_provider: Provider name (qiskit, braket, cirq, aws, ibm, google)
        backend_name: Specific backend name if applicable
        shots: Number of execution shots
    """
    backend_type: str = Field(..., description="Backend type (simulator or hardware)")
    backend_provider: str = Field(..., description="Provider name")
    backend_name: Optional[str] = Field(None, description="Specific backend name")
    shots: int = Field(..., description="Number of execution shots")


class JobStatus(str, Enum):
    """Enum for job status."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CircuitExecutionResponse(BaseModel):
    """
    Unified response model for both synchronous and asynchronous circuit execution.
    
    Attributes:
        job_id: Job ID
        status: Job status (COMPLETED for sync, QUEUED for async)
        execution_mode: Indicator of whether this was a synchronous or asynchronous execution
        counts: Measurement counts (present for sync execution, null for async)
        execution_time: Execution time in seconds (present for sync execution, null for async)
        estimated_completion_time: Estimated completion time (only for async execution)
        provider_job_id: ID of the job/task in the provider's system (for cross-referencing)
        provider_job_status: Status of the job as reported by the provider
        metadata: Additional metadata about the execution or job
    """
    job_id: str = Field(..., description="Job ID")
    status: JobStatus = Field(..., description="Job status")
    execution_mode: str = Field(..., description="Execution mode: 'sync' or 'async'")
    counts: Optional[Dict[str, float]] = Field(None, description="Measurement counts (sync only)")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds (sync only)")
    estimated_completion_time: Optional[datetime] = Field(
        None, description="Estimated completion time (async only)"
    )
    provider_job_id: Optional[str] = Field(None, description="Provider-specific job/task ID")
    provider_job_status: Optional[str] = Field(None, description="Provider-specific job status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional execution metadata")


# Keep these for backward compatibility temporarily, but mark as deprecated
class CircuitExecutionResult(BaseModel):
    """
    @deprecated: Use CircuitExecutionResponse instead.
    Result model for synchronous circuit execution.
    """
    counts: Dict[str, float] = Field(..., description="Measurement counts")
    execution_time: float = Field(..., description="Execution time in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AsyncJobCreationResponse(BaseModel):
    """
    @deprecated: Use CircuitExecutionResponse instead.
    Response model for asynchronous job creation.
    """
    job_id: str = Field(..., description="Job ID")
    status: JobStatus = Field(..., description="Job status")
    estimated_completion_time: Optional[datetime] = Field(
        None, description="Estimated completion time"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional job metadata")


class JobDetailsResponse(BaseModel):
    """
    Response model for job details.
    
    Attributes:
        job_id: Job ID
        status: Job status
        backend_type: Backend type
        backend_provider: Provider name
        backend_name: Specific backend name if applicable
        provider_job_id: ID of the job/task in the provider's system (for cross-referencing)
        provider_job_status: Status of the job as reported by the provider
        created_at: Job creation time
        completed_at: Job completion time
        result: Job result if completed
        error: Error message if failed
    """
    job_id: str = Field(..., description="Job ID")
    status: JobStatus = Field(..., description="Job status")
    backend_type: str = Field(..., description="Backend type")
    backend_provider: str = Field(..., description="Provider name")
    backend_name: Optional[str] = Field(None, description="Specific backend name")
    provider_job_id: Optional[str] = Field(None, description="Provider-specific job/task ID")
    provider_job_status: Optional[str] = Field(None, description="Provider-specific job status")
    created_at: datetime = Field(..., description="Job creation time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    result: Optional[Dict[str, Any]] = Field(None, description="Job result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")


class JobCancellationResponse(BaseModel):
    """
    Response model for job cancellation.
    
    Attributes:
        job_id: Job ID
        status: Job status
    """
    job_id: str = Field(..., description="Job ID")
    status: JobStatus = Field(..., description="Job status")
