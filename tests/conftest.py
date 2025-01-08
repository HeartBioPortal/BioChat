from typing import Dict, Optional
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.orchestrator import BioChatOrchestrator
from src.tool_executor import ToolExecutor
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from src.APIHub import BioDatabaseAPI

# Create a mock implementation of BioDatabaseAPI
class MockNCBIEutils(BioDatabaseAPI):
    """Mock implementation of NCBIEutils for testing"""
    
    def __init__(self, api_key: Optional[str] = None, tool: str = "test_tool", email: Optional[str] = None):
        super().__init__(api_key=api_key, tool=tool, email=email)
        self.base_url = "https://mock.ncbi.nlm.nih.gov"

    def search(self, query: str) -> Dict:
        """Mock implementation of the search method"""
        return {
            "esearchresult": {
                "count": "1",
                "idlist": ["12345"],
                "translationset": []
            }
        }

    def search_and_analyze(self, genes, phenotypes, additional_terms=None, max_results=10):
        """Mock implementation of search_and_analyze"""
        return {
            "articles": [
                {
                    "title": "Mock Research Article",
                    "abstract": "This is a mock abstract for testing purposes.",
                    "authors": ["Test Author"],
                    "journal": "Mock Journal of Biology",
                    "pubdate": "2024"
                }
            ],
            "metadata": {
                "query": {
                    "genes": genes,
                    "phenotypes": phenotypes,
                    "additional_terms": additional_terms
                },
                "total_results": 1
            }
        }

@pytest.fixture
def mock_apis():
    """Mock all external API clients"""
    with patch('src.tool_executor.NCBIEutils', MockNCBIEutils), \
         patch('src.tool_executor.EnsemblAPI'), \
         patch('src.tool_executor.GWASCatalog'), \
         patch('src.tool_executor.UniProtAPI'):
        yield

@pytest.fixture
def mock_openai_client():
    """Provides a mock OpenAI client with predefined responses"""
    mock_client = Mock()
    
    async def mock_create(*args, **kwargs):
        # Basic response without tool calls
        if 'tools' not in kwargs:
            return ChatCompletion(
                id="mock_completion",
                choices=[
                    Mock(
                        message=ChatCompletionMessage(
                            role="assistant",
                            content="This is a mock response"
                        ),
                        finish_reason="stop"
                    )
                ],
                created=1234567890,
                model="gpt-4-turbo-preview",
                object="chat.completion"
            )
        
        # Response with tool calls
        return ChatCompletion(
            id="mock_completion",
            choices=[
                Mock(
                    message=ChatCompletionMessage(
                        role="assistant",
                        content=None,
                        tool_calls=[{
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "search_literature",
                                "arguments": '{"genes": ["BRCA1"], "phenotypes": ["Breast Cancer"]}'
                            }
                        }]
                    ),
                    finish_reason="tool_calls"
                )
            ],
            created=1234567890,
            model="gpt-4-turbo-preview",
            object="chat.completion"
        )
    
    mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)
    return mock_client

@pytest.fixture
def mock_orchestrator(mock_openai_client, mock_apis):
    """Provides a mock BioChatOrchestrator with mocked dependencies"""
    orchestrator = BioChatOrchestrator(
        openai_api_key="mock_key",
        ncbi_api_key="mock_key",
        tool_name="test_tool",
        email="test@example.com"
    )
    orchestrator.client = mock_openai_client
    return orchestrator