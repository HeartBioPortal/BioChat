# BioChat

BioChat is a specialized API for interacting with biological databases through natural language. It allows researchers to query multiple biological databases simultaneously using conversational language.

## Features

- Natural language processing of biological and medical queries
- Integration with multiple biological databases:
  - NCBI PubMed for literature search
  - UniProt for protein information
  - Reactome for pathway analysis
  - STRING-DB for protein interactions
  - BioGRID for molecular interactions
  - Open Targets for drug target analysis
  - ChEMBL for compound information
  - And many more
- Intelligent query routing to appropriate databases
- Comprehensive response synthesis across multiple data sources

## Installation

```bash
pip install biochat
```

Or install from source:

```bash
git clone https://github.com/yourusername/biochat.git
cd biochat
pip install -e .
```

## Usage

### Basic Usage

```python
from biochat import BioChatOrchestrator
import asyncio

async def main():
    # Initialize with API keys
    orchestrator = BioChatOrchestrator(
        openai_api_key="your-openai-key",
        ncbi_api_key="your-ncbi-key",
        biogrid_access_key="your-biogrid-key",
        tool_name="YourToolName",
        email="your.email@example.com"
    )
    
    # Process a query
    response = await orchestrator.process_query(
        "What is the role of TP53 in cancer development?"
    )
    
    print(response)

# Run the async function
asyncio.run(main())
```

### Integration with FastAPI

```python
from fastapi import FastAPI, Depends
from biochat import BioChatOrchestrator
import os

app = FastAPI()

# Dependency to get orchestrator
def get_orchestrator():
    return BioChatOrchestrator(
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        ncbi_api_key=os.environ.get("NCBI_API_KEY"),
        biogrid_access_key=os.environ.get("BIOGRID_ACCESS_KEY"),
        tool_name="YourApp",
        email=os.environ.get("CONTACT_EMAIL")
    )

@app.post("/query")
async def process_query(
    query: str,
    orchestrator: BioChatOrchestrator = Depends(get_orchestrator)
):
    response = await orchestrator.process_query(query)
    return {"response": response}
```

## Environment Variables

The package requires the following environment variables:

- `OPENAI_API_KEY`: Your OpenAI API key
- `NCBI_API_KEY`: Your NCBI API key
- `CONTACT_EMAIL`: Your contact email for API usage
- `BIOGRID_ACCESS_KEY`: Your BioGRID API key (optional)

## License

[MIT License](LICENSE)