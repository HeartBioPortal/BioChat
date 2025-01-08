#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install test requirements
pip install -r test_requirements.txt

# Run tests with coverage
pytest --cov=src --cov-report=html --cov-report=term-missing

# Open coverage report in browser (MacOS)
# Uncomment the appropriate line for your operating system

# MacOS
# open htmlcov/index.html

# Linux
# xdg-open htmlcov/index.html

# Windows
# start htmlcov/index.html