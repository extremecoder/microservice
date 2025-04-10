#!/usr/bin/env python3
"""
Test script for all supported quantum simulators.
"""
import requests
import json
import time
from typing import Dict, Any

API_URL = "http://localhost:8889/api/v1/circuits/execute"

def test_simulator(provider: str) -> Dict[str, Any]:
    """
    Test a specific quantum simulator.
    
    Args:
        provider: The simulator provider (qiskit, cirq, braket)
        
    Returns:
        API response
    """
    print(f"\n===== Testing {provider} simulator =====")
    
    # Read the QASM file
    with open("test_circuit.qasm", "r") as f:
        circuit = f.read()
    
    # Create the payload
    payload = {
        "circuit_file": circuit,
        "shots": 1024,
        "backend_type": "simulator",
        "backend_provider": provider,
        "async_mode": False
    }
    
    # Make the API call
    print(f"Sending request to {provider} simulator...")
    response = requests.post(
        API_URL,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    # Print response
    result = response.json()
    print(json.dumps(result, indent=2))
    
    print(f"===== {provider} test complete =====\n")
    return result

def main():
    """Test all supported simulators."""
    # Test each supported simulator
    providers = ["qiskit", "cirq", "braket"]
    
    for provider in providers:
        result = test_simulator(provider)
        # Add a small delay between requests
        time.sleep(1)
    
    print("All simulator tests completed!")

if __name__ == "__main__":
    main()
