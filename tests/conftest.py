import pytest
from unittest.mock import Mock, AsyncMock
from src.orchestrator import BioChatOrchestrator
from src.tool_executor import ToolExecutor
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionMessageToolCall,
    Function
)

@pytest.fixture
def mock_openai_client():
    """Provides a mock OpenAI client with predefined responses"""
    mock_client = Mock()
    
    # Create mock chat completion responses
    async def mock_create(*args, **kwargs):
        # Basic response without tool calls
        if 'tools' not in kwargs:
            return ChatCompletion(
                id="mock_completion",
                choices=[
                    Mock(
                        message=ChatCompletionMessage(
                            role="assistant",
                            content="This is a mock response",
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
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id="call_123",
                                type="function",
                                function=Function(
                                    name="search_literature",
                                    arguments='{"genes": ["BRCA1"], "phenotypes": ["Breast Cancer"]}'
                                )
                            )
                        ]
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
def mock_tool_executor():
    """Provides a mock ToolExecutor with predefined responses"""
    mock_executor = Mock(spec=ToolExecutor)
    
    async def mock_execute_tool(tool_call):
        return {
            "status": "success",
            "data": {
                "articles": [
                    {
                        "title": "Mock Article Title",
                        "abstract": "Mock article abstract for testing purposes.",
                        "authors": ["Author One", "Author Two"],
                        "journal": "Mock Journal",
                        "pubdate": "2024"
                    }
                ]
            }
        }
    
    mock_executor.execute_tool = AsyncMock(side_effect=mock_execute_tool)
    return mock_executor

@pytest.fixture
def mock_orchestrator(mock_openai_client, mock_tool_executor):
    """Provides a mock BioChatOrchestrator with mocked dependencies"""
    orchestrator = BioChatOrchestrator(
        openai_api_key="mock_key",
        ncbi_api_key="mock_key",
        tool_name="test_tool",
        email="test@example.com"
    )
    orchestrator.client = mock_openai_client
    orchestrator.tool_executor = mock_tool_executor
    return orchestrator