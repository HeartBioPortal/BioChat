#!/usr/bin/env python
"""
Script to run BioChat tests with proper configuration.

Usage:
    python run_tests.py [pytest_args]
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Get the root directory (where setup.py is)
root_dir = Path(__file__).parent
dotenv_path = os.path.join(root_dir, '.env')

# Load environment variables from .env file
load_dotenv(dotenv_path=dotenv_path)

def check_env_vars():
    """Check if required environment variables are set."""
    required_vars = ["OPENAI_API_KEY", "NCBI_API_KEY", "CONTACT_EMAIL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"WARNING: Missing required environment variables: {', '.join(missing_vars)}")
        print("Some tests may be skipped or fail.")
        
        # Ask user if they want to proceed
        response = input("Do you want to proceed with tests anyway? (y/n): ")
        if response.lower() != 'y':
            print("Tests aborted.")
            sys.exit(1)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run BioChat tests")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("args", nargs="*", help="Additional pytest arguments")
    
    return parser.parse_args()

def main():
    """Main function to run the tests."""
    # Check environment variables
    check_env_vars()
    
    # Parse command-line arguments
    args = parse_args()
    
    # Build pytest command
    pytest_args = ["pytest"]
    
    # Add verbosity flag
    if args.verbose:
        pytest_args.append("-v")
    
    # Add test selection flags
    if args.unit:
        pytest_args.append("-m unit")
    elif args.integration:
        pytest_args.append("-m integration")
    elif not args.all:
        # Default: run both unit and integration tests
        pass
    
    # Add coverage if requested
    if args.coverage:
        pytest_args.extend(["--cov=biochat", "--cov-report=term", "--cov-report=html"])
    
    # Add additional arguments
    pytest_args.extend(args.args)
    
    # Run pytest
    print(f"Running: {' '.join(pytest_args)}")
    result = subprocess.run(" ".join(pytest_args), shell=True)
    
    # Return pytest exit code
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()