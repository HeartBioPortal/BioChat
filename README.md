# BioChat

BioChat is an intelligent conversational interface for biological databases that combines the power of large language models with specialized biological data sources. It enables researchers and professionals to interact with multiple biological databases using natural language queries.


## Supported Databases and APIs

BioChat integrates with multiple biological databases to provide comprehensive analysis capabilities:

## Process FlowChart

![image (4)](https://github.com/user-attachments/assets/0e8681a7-df04-44e0-8ede-fd6354eb080d)


### Core Databases
- **NCBI PubMed (E-utilities)**
  - Literature search and analysis
  - Citation information
  - Article abstracts

- **Open Targets Platform**
  - Target-disease associations
  - Drug information
  - Clinical trials data
  - Safety information
  - Expression data

- **Reactome**
  - Biological pathways
  - Molecular mechanisms
  - Disease pathways

- **Ensembl**
  - Genetic variants
  - Genomic annotations
  - Gene information

### Molecular Interactions and Networks
- **STRING-DB**
  - Protein-protein interactions
  - Interaction networks
  - Functional associations

- **IntAct**
  - Molecular interaction data
  - Experimentally verified interactions
  - Interaction networks

- **BioGRID**
  - Protein-protein interactions
  - Genetic interactions
  - Chemical associations

### Disease and Drug Resources
- **GWAS Catalog**
  - Genetic associations
  - Trait information
  - Study metadata

- **PharmGKB**
  - Drug-gene relationships
  - Clinical annotations
  - Pharmacogenomic data

### Protein and Pathway Information
- **UniProt**
  - Protein sequences
  - Protein structure
  - Function annotations

- **BioCyc**
  - Metabolic pathways
  - Biochemical reactions
  - Regulatory networks

### Integration Features
Each database provides specific capabilities:
- Literature mining and evidence synthesis (PubMed)
- Drug-target interactions and clinical relevance (Open Targets, PharmGKB)
- Molecular interaction networks (STRING-DB, IntAct, BioGRID)
- Pathway analysis and mechanisms (Reactome, BioCyc)
- Genetic variation and genomic features (Ensembl)
- Disease associations and pharmacogenomics (GWAS Catalog, PharmGKB)
- Protein information and annotations (UniProt)



## Project Structure

```
biochat/

├── LICENSE
├── README.md
├── commitss.sh
├── config.py
├── htmlcov
│   ├── status.json
│   └── style_cb_8e611ae1.css
├── requirements.txt
├── run_tests.sh
├── setup.py
├── src
│   ├── APIHub.py
│   ├── __init__.py
│   ├── __pycache__
│   ├── api.py
│   ├── orchestrator.py
│   ├── schemas.py
│   └── tool_executor.py
└── tests
    ├── __init__.py
    ├── __pycache__
    ├── conftest.py
    ├── integration
    │   ├── __init__.py
    │   ├── __pycache__
    │   ├── conftest.py
    │   ├── test_gwas.py
    │   ├── test_literature.py
    │   ├── test_protein.py
    │   └── test_variants.py
    ├── logs
    ├── pytest.ini
    ├── test_api.py
    ├── test_logger.py
    ├── test_orchestrator.py
    ├── test_requirements.txt
    ├── test_tool_executor.py
    └── utils
        ├── __init__.py
        ├── __pycache__
        └── logger.py
```

## Prerequisites

- Python 3.9 or higher
- OpenAI API key
- NCBI API key
- Valid email address for API access

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/biochat.git
cd biochat
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root with the following variables:

```env
OPENAI_API_KEY=your_openai_api_key
NCBI_API_KEY=your_ncbi_api_key
CONTACT_EMAIL=your_email@example.com
PORT=8000
HOST=0.0.0.0
```

## Running the Application

Start the FastAPI server from the project root:

```bash
python -m src.api
```

The API will be available at `http://localhost:8000`. Access the interactive API documentation at `http://localhost:8000/docs`.

## API Endpoints

The following endpoints are available:

- `POST /query`: Process a natural language query about biological topics
- `GET /history`: Retrieve the conversation history
- `POST /clear`: Clear the conversation history
- `GET /health`: Check the API's health status

## Example Usage

Here's an example of how to use the API:

```python
import requests

# Send a query
response = requests.post(
    "http://localhost:8000/query",
    json={"text": "What are the known genetic variants associated with cystic fibrosis?"}
)

print(response.json())
```

## Development Guidelines

When developing new features:

1. Place all source code in the `src` directory
2. Add test files in the `tests` directory
3. Follow the package structure for imports:
   ```python
   from src.schemas import LiteratureSearchParams
   from src.tool_executor import ToolExecutor
   ```
4. Update requirements.txt when adding new dependencies
5. Maintain consistent error handling and logging practices
6. Follow the established code style and documentation standards

## Error Handling

The API implements comprehensive error handling:

- Input validation errors return 422 status code
- Authentication errors return 401 status code
- Server errors return 500 status code
- All errors include detailed error messages and timestamps

## Testing

To run the test suite:

```bash
pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the GNU AFFERO License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.
