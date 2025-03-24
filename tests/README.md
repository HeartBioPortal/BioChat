# BioChat Tests

This directory contains tests for the BioChat package.

## Test Structure

- **test_orchestrator.py**: Tests for the main `BioChatOrchestrator` class
- **test_integration.py**: End-to-end integration tests
- **test_api_hub/**: Tests for the API client modules
- **test_utils/**: Tests for utility modules

## Prerequisites

- Python 3.8 or higher
- pytest and pytest-asyncio
- An OpenAI API key
- An NCBI API key
- A contact email
- A BioGRID API key (optional)

## Environment Setup

Create a `.env` file in the root directory with the following content:

```
OPENAI_API_KEY=your_openai_api_key
NCBI_API_KEY=your_ncbi_api_key
CONTACT_EMAIL=your_email@example.com
BIOGRID_ACCESS_KEY=your_biogrid_api_key  # Optional
```

## Running Tests

You can run the tests using the provided `run_tests.py` script:

```bash
# Run all tests
python run_tests.py

# Run only unit tests
python run_tests.py --unit

# Run only integration tests
python run_tests.py --integration

# Run with verbose output
python run_tests.py -v

# Generate coverage report
python run_tests.py --coverage
```

Alternatively, you can use pytest directly:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_orchestrator.py

# Run specific test class
pytest tests/test_orchestrator.py::TestBioChatOrchestrator

# Run specific test function
pytest tests/test_orchestrator.py::TestBioChatOrchestrator::test_process_query
```

## Test Categories

The tests are categorized using pytest markers:

- **unit**: Unit tests that don't require external services
- **integration**: Integration tests that require external services
- **slow**: Tests that take a long time to run

You can run tests with specific markers:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run all except slow tests
pytest -m "not slow"
```

## Test Results and Coverage

After running tests with the `--coverage` flag, you can view the HTML coverage report:

```bash
# Open the coverage report in your browser
open htmlcov/index.html  # On macOS
xdg-open htmlcov/index.html  # On Linux
```

## Troubleshooting

### Missing API Keys

If your tests are failing due to missing API keys, make sure you have set the required environment variables. You can check if they are properly loaded with:

```python
import os
print(os.getenv("OPENAI_API_KEY"))
print(os.getenv("NCBI_API_KEY"))
print(os.getenv("CONTACT_EMAIL"))
```

### API Rate Limits

Some tests might fail due to API rate limits. If this happens, try:

1. Running the tests with a delay between them
2. Running only specific test files or classes
3. Reducing the number of API calls in the tests

### Installation Issues

Make sure the package is installed in development mode:

```bash
pip install -e .
```

This ensures that your tests use the local version of the package.