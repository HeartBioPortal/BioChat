# BioChat

BioChat is an intelligent conversational interface for biological databases that combines the power of large language models with specialized biological data sources. It enables researchers and professionals to interact with multiple biological databases using natural language queries.

## Features

BioChat provides seamless access to multiple biological databases through a unified interface:

- NCBI PubMed literature search and analysis
- Ensembl genetic variant information
- GWAS Catalog for genetic associations
- UniProt protein information
- Natural language understanding of biological queries
- Comprehensive result synthesis and explanation

## Project Structure

```
biochat/
├── src/
│   ├── __init__.py
│   ├── APIHub.py          # Biological database API integrations
│   ├── schemas.py         # Data models and function definitions
│   ├── tool_executor.py   # Database interaction logic
│   ├── orchestrator.py    # Main orchestration logic
│   └── api.py            # FastAPI application
├── tests/                # Test files
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_orchestrator.py
│   └── test_tool_executor.py
├── docs/                 # Documentation files
├── .env                 # Environment variables
├── .gitignore          # Git ignore file
├── requirements.txt    # Project dependencies
├── LICENSE            # License file
└── README.md         # Project documentation
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