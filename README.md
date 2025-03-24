# BioChat

BioChat is a specialized API for interacting with biological databases through natural language. It allows researchers to query multiple biological databases simultaneously using conversational language and synthesizes the results into comprehensive, research-grade responses.

## Features

- **Natural Language Processing**: Query complex biological databases using plain English
- **Multi-Database Integration**: Automatically routes queries to the most appropriate biological databases
- **Intelligent Query Analysis**: Uses a knowledge graph approach to understand entity relationships
- **Comprehensive Response Synthesis**: Combines data from multiple sources with proper citations
- **API Connectivity**: Integrates with numerous biological databases:
  - NCBI PubMed (literature)
  - UniProt (protein information)
  - Reactome (pathways)
  - STRING-DB (protein interactions)
  - BioGRID (molecular interactions)
  - ChEMBL (chemical compounds)
  - Open Targets (drug targets)
  - IntAct (molecular interactions)
  - PharmGKB (pharmacogenomics)
  - Ensembl (genetic variants)
  - GWAS Catalog (genetic associations)

## Installation

### Prerequisites

- Python 3.8 or higher
- API keys for the following services:
  - OpenAI (for GPT-4)
  - NCBI E-utilities
  - BioGRID (optional)

### Install from PyPI

```bash
pip install biochat
```

### Install from Source

```bash
git clone https://github.com/yourusername/biochat.git
cd biochat
pip install -e .
```

### Set up Environment Variables

Create a `.env` file in your project root:

```
OPENAI_API_KEY=your_openai_api_key
NCBI_API_KEY=your_ncbi_api_key
CONTACT_EMAIL=your_email@example.com
BIOGRID_ACCESS_KEY=your_biogrid_api_key  # Optional
```

## Quick Start

```python
import asyncio
import os
from dotenv import load_dotenv
from biochat import BioChatOrchestrator

# Load environment variables
load_dotenv()

async def main():
    # Initialize the orchestrator
    orchestrator = BioChatOrchestrator(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        ncbi_api_key=os.getenv("NCBI_API_KEY"),
        biogrid_access_key=os.getenv("BIOGRID_ACCESS_KEY"),
        tool_name="YourAppName",
        email=os.getenv("CONTACT_EMAIL")
    )
    
    # Process a query
    response = await orchestrator.process_query(
        "What is the role of TP53 in cancer development?"
    )
    
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced Usage

### Knowledge Graph Queries

For more sophisticated queries that benefit from knowledge graph analysis:

```python
# Using knowledge graph approach for complex queries
result = await orchestrator.process_knowledge_graph_query(
    "How does CD47 regulate macrophage phagocytosis in cancer?"
)

print(result["synthesis"])  # Print the synthesized response
```

### Customizing Database Selection

```python
from biochat.utils.query_analyzer import QueryAnalyzer

# Create a custom query analyzer
analyzer = QueryAnalyzer(openai_client)

# Analyze a query to determine optimal database sequence
analysis = await analyzer.analyze_query("What proteins interact with BRCA1?")
db_sequence = analyzer.get_optimal_database_sequence(analysis)

print(f"Optimal database sequence: {db_sequence}")
```

## Integration with Web Frameworks

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from typing import Dict

app = FastAPI()

class Query(BaseModel):
    text: str

def get_orchestrator():
    return BioChatOrchestrator(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        ncbi_api_key=os.getenv("NCBI_API_KEY"),
        biogrid_access_key=os.getenv("BIOGRID_ACCESS_KEY"),
        tool_name="BioChatAPI",
        email=os.getenv("CONTACT_EMAIL")
    )

@app.post("/query")
async def process_query(query: Query, orchestrator=Depends(get_orchestrator)):
    response = await orchestrator.process_query(query.text)
    return {"response": response}
```

### Django Integration

See the `examples/django_app` directory for a complete Django integration example.

## Architecture

BioChat consists of several key components:

1. **Orchestrator**: Manages query processing and database selection
2. **Query Analyzer**: Analyzes queries using knowledge graph principles
3. **Tool Executor**: Handles API calls to biological databases
4. **API Hub**: Contains client classes for various biological database APIs
5. **Response Summarizer**: Filters and condenses API responses
6. **Schema Definitions**: Pydantic models for request/response validation

## API References

For detailed information about the APIs used in BioChat, see:

- [NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25500/)
- [Reactome Content Service](https://reactome.org/ContentService/)
- [IntAct Web Service](https://www.ebi.ac.uk/intact/ws/interaction/v2/api-docs)
- [BioGRID REST API](https://wiki.thebiogrid.org/doku.php/biogridrest)
- [UniProt API](https://www.uniprot.org/help/api)
- [ChEMBL API](https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services)
- [Open Targets Platform API](https://platform-docs.opentargets.org/api-documentation)
- [Ensembl REST API](https://rest.ensembl.org/)

## Testing

Run tests using the provided script:

```bash
# Run all tests
python run_tests.py

# Run only unit tests
python run_tests.py --unit

# Run only integration tests
python run_tests.py --integration

# Generate coverage report
python run_tests.py --coverage
```

## License

[MIT License](LICENSE)

## Citation

If you use BioChat in your research, please cite:

```
Your Name et al. (2025). BioChat: A Natural Language Interface for Biological Databases. 
```

## Acknowledgments

BioChat leverages several open-source biological databases and APIs. We gratefully acknowledge the providers of these resources for making their data accessible.