# Quantum Computing API Software Requirements Document

## 1. Overview

This document outlines the requirements for a REST API service that provides a unified interface to execute quantum circuits across multiple quantum simulators and hardware platforms.

## 2. Functional Requirements

### 2.1 Core Functionality

- Create a FastAPI-based web service that exposes RESTful endpoints
- Allow users to submit OpenQASM circuit files for execution
- Support execution on multiple quantum simulators (Qiskit, Braket, Cirq)
- Support execution on quantum hardware providers (AWS, IBM, Google)
- Provide both synchronous and asynchronous execution modes
- Allow job status checking and result retrieval

### 2.2 API Endpoints

#### 2.2.1 Circuit Execution Endpoint

```
POST /api/v1/circuits/execute
```

**Request Body:**
- `circuit_file`: OpenQASM circuit file (required)
- `shots`: Number of execution shots (default: 1024)
- `backend_type`: "simulator" or "hardware" (required)
- `backend_provider`: "qiskit", "braket", "cirq" for simulators; "aws", "ibm", "google" for hardware (required)
- `backend_name`: Specific backend name if applicable (optional)
- `async_mode`: Boolean flag for asynchronous execution (default: false)
- `parameters`: Dictionary of circuit parameters if the circuit is parameterized (optional)

**Response (Synchronous Mode):**
- Status code: 200 OK
- Body: 
```json
{
  "status": "success",
  "data": {
    "counts": {"00": 0.25, "01": 0.25, "10": 0.25, "11": 0.25},
    "execution_time": "0.52s",
    "metadata": {...}
  },
  "error": null
}
```

**Response (Asynchronous Mode):**
- Status code: 202 Accepted
- Body:
```json
{
  "status": "success",
  "data": {
    "job_id": "job-12345-abcde",
    "status": "QUEUED",
    "estimated_completion_time": "2025-04-09T15:10:00+05:30"
  },
  "error": null
}
```

#### 2.2.2 Job Status Endpoint

```
GET /api/v1/jobs/{job_id}
```

**Path Parameters:**
- `job_id`: Job ID returned from async execution (required)

**Response:**
- Status code: 200 OK
- Body:
```json
{
  "status": "success",
  "data": {
    "job_id": "job-12345-abcde",
    "status": "COMPLETED", // QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED
    "backend_type": "simulator",
    "backend_provider": "qiskit",
    "backend_name": "qasm_simulator",
    "created_at": "2025-04-09T14:55:00+05:30",
    "completed_at": "2025-04-09T14:56:00+05:30",
    "result": {
      "counts": {"00": 0.25, "01": 0.25, "10": 0.25, "11": 0.25}
    },
    "error": null
  },
  "error": null
}
```

#### 2.2.3 Job Cancellation Endpoint

```
DELETE /api/v1/jobs/{job_id}
```

**Path Parameters:**
- `job_id`: Job ID to cancel (required)

**Response:**
- Status code: 200 OK
- Body:
```json
{
  "status": "success",
  "data": {
    "job_id": "job-12345-abcde",
    "status": "CANCELLED"
  },
  "error": null
}
```

## 3. Technical Requirements

### 3.1 Dependencies
- Python 3.10+
- FastAPI framework
- Qiskit, Amazon Braket, and Cirq libraries
- Local files for job persistence
- Local files for circuit persistence

### 3.2 Error Handling
- Consistent error response format
- Detailed error codes and messages

### 3.3 Logging and Monitoring
- Structured logging of all API requests
- Performance metrics collection
- Error rate monitoring

## 4 API Response Format

All API responses will follow a consistent format:

```json
{
  "status": "success|error",
  "data": {...} | null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message"
  } | null
}
```

This software requirements document provides a comprehensive foundation for implementing a quantum computing API that supports multiple simulators and hardware providers with both synchronous and asynchronous execution modes.


## 5. Environment Variables


- `IBM_QUANTUM_TOKEN` - IBM Quantum token
- `AWS_ACCESS_KEY_ID` - AWS access key ID
- `AWS_SECRET_ACCESS_KEY` - AWS secret access key
- `AWS_REGION` - AWS region
- `TOGETHER_API_KEY` - Togethers API key



## 6. Comprehensive Testing

### 6.1 Testing Coverage
- Maintain minimum 80% test coverage for all API endpoints
- Track code coverage using tools like pytest-cov
- Generate coverage reports as part of the CI/CD pipeline

### 6.2 Unit Testing
- Test individual components and services in isolation
- Mock external dependencies (quantum backends, file systems)
- Test all utility functions and helper methods
- Validate input parsing and transformation logic

### 6.3 Integration Testing
- Test the interaction between components
- Validate the proper integration with simulator libraries (Qiskit, Braket, Cirq)
- Test database/storage interactions for job persistence
- Validate environment variable configuration and loading

### 6.4 API Testing
- Test all API endpoints using automated test cases
- Validate request validation and response formatting
- Test the happy path for each endpoint
- Test with various input combinations and parameter sets



