# BioChat Integration Tests

This directory contains integration tests for BioChat's components, focusing on real-world interactions with external APIs and complete system functionality.

## Test Categories

### Query Analyzer Tests

- **test_query_analyzer_full.py** - Tests for the query analyzer component with the orchestrator

### Biological Database Tests

- **test_gwas.py** - Tests for GWAS Catalog interactions
- **test_literature.py** - Tests for literature search via PubMed
- **test_protein.py** - Tests for protein information retrieval
- **test_variants.py** - Tests for genetic variant information

## Running Tests

### Prerequisites

For these tests to run successfully, you need to set the following environment variables:

```bash
export OPENAI_API_KEY=your_openai_api_key
export NCBI_API_KEY=your_ncbi_api_key
export CONTACT_EMAIL=your_email@example.com
export BIOGRID_ACCESS_KEY=your_biogrid_key  # Optional
```

### Running All Integration Tests

```bash
pytest tests/integration/
```

### Running Specific Test Categories

```bash
# Run only query analyzer tests
pytest tests/integration/test_query_analyzer_full.py

# Run only biological database tests
pytest tests/integration/test_gwas.py tests/integration/test_literature.py tests/integration/test_protein.py tests/integration/test_variants.py
```

### Running Tests with Markers

Some tests are marked with specific markers to indicate their characteristics:

```bash
# Run only slow tests (those making real external API calls)
pytest -m slow tests/integration/

# Skip slow tests
pytest -m "not slow" tests/integration/
```

## Understanding Test Failures

The integration tests interact with real external APIs which may:

1. Rate limit requests
2. Return different results based on the latest database updates
3. Experience temporary outages

If tests fail, check:

1. **API Rate Limits** - You may need to wait before running the tests again
2. **API Changes** - The external API may have changed its response format
3. **Network Issues** - Ensure you have a stable internet connection

## Manual Testing Script

For quick manual testing of the query analyzer, use the script in the scripts directory:

```bash
python scripts/test_query_analyzer.py "What genes are involved in Alzheimer's disease?"
```

## Adding New Tests

When adding new integration tests:

1. Create a clear, descriptive test name
2. Add appropriate markers (`@pytest.mark.slow` for slow tests)
3. Include fallback mechanisms for API failures
4. Use parametrization to test with multiple queries/inputs
5. Minimize API calls by keeping tests focused