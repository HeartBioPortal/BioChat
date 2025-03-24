# BioChat Development Guide

## Build/Test Commands
- Install dev dependencies: `pip install -r requirements-dev.txt`
- Install package in dev mode: `pip install -e .`
- Run all tests: `python run_tests.py` or `pytest`
- Run unit tests only: `python run_tests.py --unit` or `pytest -m unit`
- Run integration tests: `python run_tests.py --integration` or `pytest -m integration` 
- Run specific test: `pytest tests/path_to_test.py::TestClass::test_function`
- Run with coverage: `python run_tests.py --coverage`
- Run with verbose output: `pytest -v`

## API Dependencies
- OpenAI API (`OPENAI_API_KEY` env var) - used for query analysis and response generation
- NCBI E-utilities (`NCBI_API_KEY` env var) - required for literature searches
- Optional: BioGRID (`BIOGRID_ACCESS_KEY` env var) - for protein interactions

## Error Handling
- Add timeouts to OpenAI API calls to prevent tests from hanging
- Use try/except blocks around API calls with proper fallbacks
- For SSL certificate errors with OpenTargets API, use curated fallback data

## Code Style
- Formatting: `black biochat tests`
- Sort imports: `isort biochat tests` 
- Linting: `flake8 biochat tests`
- Type checking: `mypy biochat`

## Conventions
- Follow PEP 8 style guidelines
- Use clear, descriptive variable and function names
- Add docstrings to all modules, classes, and functions
- Include type hints for all functions
- Use async/await for I/O operations
- Implement proper error handling with specific exceptions
- Write tests for all new functionality (unit tests at minimum)
- Update documentation when adding features