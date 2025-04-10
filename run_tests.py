#!/usr/bin/env python3
"""
Test runner script for the Quantum Computing API.

This script runs pytest with coverage reporting and provides a summary
of test results and coverage metrics.
"""
import os
import sys
import subprocess
from typing import List, Optional

# Minimum required coverage percentage from PRD
MIN_COVERAGE = 80


def run_tests(args: Optional[List[str]] = None) -> int:
    """
    Run pytest with coverage reporting.
    
    Args:
        args: Additional command line arguments to pass to pytest
        
    Returns:
        Exit code from pytest
    """
    if args is None:
        args = []
    
    # Ensure the circuits and results directories exist
    os.makedirs("circuits", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    
    # Base command with coverage
    cmd = [
        "python", "-m", "pytest",
        "--cov=app",
        "--cov-report=term",
        "--cov-report=html:coverage_report",
        "--html=test_report.html",
        "--self-contained-html",
        "-v"
]
    
    # Add any additional arguments
    if args:
        cmd.extend(args)
    
    # Run the tests
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    print("\n🧪 Running Quantum Computing API tests with coverage reporting...\n")
    
    # Get command line args, excluding script name
    args = sys.argv[1:]
    
    # Run tests and get exit code
    exit_code = run_tests(args)
    
    # Print summary
    if exit_code == 0:
        print("\n✅ All tests passed!")
        
        try:
            # Check if we met the coverage threshold
            with open(".coverage", "r") as f:
                if f.read().find(f"\"percent_covered\": {MIN_COVERAGE}") >= 0:
                    print(f"✅ Coverage meets minimum requirement of {MIN_COVERAGE}%")
                else:
                    print(f"⚠️ Coverage might be below the minimum requirement of {MIN_COVERAGE}%")
                    print("   Check the full coverage report for details")
        except:
            print("⚠️ Could not determine coverage percentage from report")
        
        print("\nCoverage report generated in: ./coverage_report/index.html")
    else:
        print("\n❌ Some tests failed!")
    
    sys.exit(exit_code)
