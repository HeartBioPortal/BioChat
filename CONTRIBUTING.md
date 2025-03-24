# Contributing to BioChat

Thank you for considering contributing to BioChat! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Documentation](#documentation)

## Code of Conduct

Please be respectful and considerate of others. We aim to foster an inclusive and welcoming community.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork to your local machine
3. Set up the development environment

## Development Environment

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

3. Create a `.env` file with your API keys (see `.env.example` for format)

## Coding Standards

We follow PEP 8 and use the following tools to enforce coding standards:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

You can run these tools as follows:

```bash
# Format code
black biochat tests

# Sort imports
isort biochat tests

# Lint code
flake8 biochat tests

# Type check
mypy biochat
```

Our code conventions:

1. Use clear, descriptive variable and function names
2. Add docstrings to all modules, classes, and functions
3. Include type hints
4. Keep functions small and focused on a single task
5. Use async/await where appropriate

## Testing

All new code should have tests. We use pytest for testing:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=biochat

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

See the [tests/README.md](tests/README.md) for more details on testing.

## Pull Request Process

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them with clear, descriptive commit messages

3. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a pull request to the main repository's `main` branch

5. Ensure all tests pass and the code meets our coding standards

6. Update documentation if necessary

7. Wait for review and address any feedback

## Documentation

Documentation is crucial. Please:

1. Update the README.md if you change functionality
2. Document new functions, classes, and modules with docstrings
3. Add examples for new features
4. Update any relevant documentation files

## Adding New API Clients

When adding a new API client to the `api_hub` directory:

1. Create a new file for your client (e.g., `my_api.py`)
2. Inherit from the `BioDatabaseAPI` base class
3. Implement the required abstract methods
4. Add the client to `api_hub/__init__.py`
5. Add tests for the new client
6. Document the new client and its usage

Example:

```python
from .base import BioDatabaseAPI

class MyAPIClient(BioDatabaseAPI):
    """Client for accessing the MyAPI service."""
    
    def __init__(self, api_key: str = None, tool: str = None, email: str = None):
        super().__init__(api_key=api_key, tool=tool, email=email)
        self.base_url = "https://api.myapi.com"
    
    async def search(self, query: str) -> dict:
        """Search the MyAPI database."""
        params = {"query": query}
        return await self._make_request("search", params)
```

## Questions?

If you have any questions or need help, please open an issue or contact the maintainers.

Thank you for contributing to BioChat!