from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Union
import json
import logging
import os
import uuid
from datetime import datetime
import asyncio
import time


# Import quantum backends
try:
    import qiskit
    from qiskit import QuantumCircuit, Aer, execute
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False

try:
    import cirq
    import cirq_qasm
    CIRQ_AVAILABLE = True
except ImportError:
    CIRQ_AVAILABLE = False

try:
    import braket
    from braket.circuits import Circuit
    from braket.devices import LocalSimulator
    BRAKET_AVAILABLE = True
except ImportError:
    BRAKET_AVAILABLE = False


# Create FastAPI app
app = FastAPI(
    title="${app_name}",
    description="${app_description}",
    version="${app_version}"
)

# Models
class CircuitRequest(BaseModel):
    circuit: str
    parameters: Optional[Dict[str, Any]] = None
    shots: int = 1024
    simulator: str = "qiskit"
    blocking: bool = False
    
class JobStatus(BaseModel):
    job_id: str
    status: str
    created_at: str
    simulator: str
    shots: int
    
class ResultsResponse(BaseModel):
    job_id: str
    status: str
    counts: Optional[Dict[str, int]] = None
    execution_time: Optional[float] = None
    error: Optional[str] = None

# In-memory job store (in production, use a database)
jobs = {}

# Circuit store
os.makedirs("circuits", exist_ok=True)
os.makedirs("results", exist_ok=True)

# Routes
@app.get("/")
async def root():
    return {
        "message": "Quantum Microservice API",
        "name": "${app_name}",
        "version": "${app_version}"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "simulators": {
            "qiskit": QISKIT_AVAILABLE,
            "cirq": CIRQ_AVAILABLE,
            "braket": BRAKET_AVAILABLE
        },
        "uptime": "unknown"  # In a real service, track uptime
    }

@app.post("/run")
async def run_circuit(request: CircuitRequest, background_tasks: BackgroundTasks):
    # Validate simulator
    if request.simulator not in ["qiskit", "cirq", "braket"]:
        raise HTTPException(status_code=400, detail="Invalid simulator. Must be one of: qiskit, cirq, braket")
    
    # Check if simulator is available
    if request.simulator == "qiskit" and not QISKIT_AVAILABLE:
        raise HTTPException(status_code=400, detail="Qiskit simulator not available")
    elif request.simulator == "cirq" and not CIRQ_AVAILABLE:
        raise HTTPException(status_code=400, detail="Cirq simulator not available")
    elif request.simulator == "braket" and not BRAKET_AVAILABLE:
        raise HTTPException(status_code=400, detail="Braket simulator not available")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save circuit to file
    circuit_path = f"circuits/{job_id}.qasm"
    with open(circuit_path, "w") as f:
        f.write(request.circuit)
    
    # Create job record
    job = {
        "job_id": job_id,
        "status": "QUEUED",
        "created_at": datetime.now().isoformat(),
        "circuit_path": circuit_path,
        "parameters": request.parameters,
        "shots": request.shots,
        "simulator": request.simulator
    }
    jobs[job_id] = job
    
    # Determine execution mode
    if request.blocking:
        # Execute synchronously
        await execute_circuit(job_id)
        
        # Get results
        job = jobs[job_id]
        result_path = f"results/{job_id}.json"
        
        if job["status"] == "COMPLETED" and os.path.exists(result_path):
            with open(result_path, "r") as f:
                result = json.load(f)
                
            return {
                "job_id": job_id,
                "status": job["status"],
                "counts": result.get("counts"),
                "execution_time": result.get("execution_time")
            }
        else:
            return {
                "job_id": job_id,
                "status": job["status"],
                "error": "Failed to execute circuit"
            }
    else:
        # Run in background
        background_tasks.add_task(execute_circuit, job_id)
        
        return JobStatus(
            job_id=job_id,
            status="QUEUED",
            created_at=job["created_at"],
            simulator=request.simulator,
            shots=request.shots
        )

@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        created_at=job["created_at"],
        simulator=job["simulator"],
        shots=job["shots"]
    )

@app.get("/jobs/{job_id}/results", response_model=ResultsResponse)
async def get_job_results(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] == "QUEUED" or job["status"] == "RUNNING":
        return ResultsResponse(
            job_id=job_id,
            status=job["status"]
        )
    
    result_path = f"results/{job_id}.json"
    if not os.path.exists(result_path):
        return ResultsResponse(
            job_id=job_id,
            status=job["status"],
            error="Results file not found"
        )
    
    with open(result_path, "r") as f:
        result = json.load(f)
    
    return ResultsResponse(
        job_id=job_id,
        status=job["status"],
        counts=result.get("counts"),
        execution_time=result.get("execution_time"),
        error=result.get("error")
    )

@app.get("/jobs")
async def list_jobs():
    return {
        "jobs": [
            {
                "job_id": job_id,
                "status": job["status"],
                "created_at": job["created_at"],
                "simulator": job["simulator"]
            } for job_id, job in jobs.items()
        ]
    }

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete job files
    try:
        if os.path.exists(f"circuits/{job_id}.qasm"):
            os.remove(f"circuits/{job_id}.qasm")
        if os.path.exists(f"results/{job_id}.json"):
            os.remove(f"results/{job_id}.json")
    except Exception as e:
        logger.error(f"Error deleting job files: {e}")
    
    # Remove from job store
    del jobs[job_id]
    
    return {"message": f"Job {job_id} deleted"}

# Background task for circuit execution
async def execute_circuit(job_id: str):
    if job_id not in jobs:
        logger.error(f"Job {job_id} not found")
        return
    
    job = jobs[job_id]
    job["status"] = "RUNNING"
    
    try:
        # Get circuit and parameters
        circuit_path = job["circuit_path"]
        parameters = job["parameters"] or {}
        shots = job["shots"]
        simulator = job["simulator"]
        
        if simulator == "qiskit":
            result = await execute_with_qiskit(circuit_path, parameters, shots)
        elif simulator == "cirq":
            result = await execute_with_cirq(circuit_path, parameters, shots)
        elif simulator == "braket":
            result = await execute_with_braket(circuit_path, parameters, shots)
        else:
            raise ValueError(f"Unsupported simulator: {simulator}")
        
        # Save results
        result_path = f"results/{job_id}.json"
        with open(result_path, "w") as f:
            json.dump(result, f, indent=2)
        
        job["status"] = "COMPLETED"
        logger.info(f"Job {job_id} completed")
        
    except Exception as e:
        logger.error(f"Error executing job {job_id}: {e}")
        job["status"] = "FAILED"
        
        # Save error
        result_path = f"results/{job_id}.json"
        with open(result_path, "w") as f:
            json.dump({"error": str(e)}, f, indent=2)

# Qiskit execution
async def execute_with_qiskit(circuit_path, parameters, shots):
    import time
    start_time = time.time()
    
    # Load circuit from file
    with open(circuit_path, "r") as f:
        qasm = f.read()
    
    # Replace parameters in QASM
    for param_name, param_value in parameters.items():
        qasm = qasm.replace(f"parameter {param_name}", str(param_value))
    
    # Create circuit from QASM
    circuit = QuantumCircuit.from_qasm_str(qasm)
    
    # Add measurements if not present
    if not circuit.clbits:
        circuit.measure_all()
    
    # Run simulation
    simulator = Aer.get_backend('qasm_simulator')
    job = execute(circuit, simulator, shots=shots)
    result = job.result()
    
    # Process results
    counts = result.get_counts()
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return {
        "counts": counts,
        "execution_time": execution_time,
        "success": True
    }

# Cirq execution
async def execute_with_cirq(circuit_path, parameters, shots):
    import time
    start_time = time.time()
    
    # Load circuit from file
    with open(circuit_path, "r") as f:
        qasm = f.read()
    
    # Replace parameters in QASM
    for param_name, param_value in parameters.items():
        qasm = qasm.replace(f"parameter {param_name}", str(param_value))
    
    # Create circuit from QASM
    parser = cirq_qasm.QasmParser()
    circuit = parser.parse(qasm)
    
    # Run simulation
    simulator = cirq.Simulator()
    result = simulator.run(circuit, repetitions=shots)
    
    # Process results
    measurements = result.measurements
    if not measurements:
        # For circuits without explicit measurements
        counts = {"0": shots}
    else:
        # Convert measurements to counts
        key = list(measurements.keys())[0]
        bitstrings = []
        for bits in measurements[key]:
            bitstring = ''.join(str(int(b)) for b in bits)
            bitstrings.append(bitstring)
        
        # Count unique bitstrings
        counts = {}
        for bitstring in bitstrings:
            if bitstring not in counts:
                counts[bitstring] = 0
            counts[bitstring] += 1
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return {
        "counts": counts,
        "execution_time": execution_time,
        "success": True
    }

# Braket execution
async def execute_with_braket(circuit_path, parameters, shots):
    import time
    start_time = time.time()
    
    # Load circuit from file
    with open(circuit_path, "r") as f:
        qasm = f.read()
    
    # Replace parameters in QASM
    for param_name, param_value in parameters.items():
        qasm = qasm.replace(f"parameter {param_name}", str(param_value))
    
    # Create circuit from QASM
    # Note: In production, use a proper QASM to Braket converter
    circuit = Circuit.from_openqasm(qasm)
    
    # Run simulation
    device = LocalSimulator()
    task = device.run(circuit, shots=shots)
    result = task.result()
    
    # Process results
    counts = result.measurement_counts
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return {
        "counts": counts,
        "execution_time": execution_time,
        "success": True
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
