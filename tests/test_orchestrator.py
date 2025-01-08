import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.orchestrator import BioChatOrchestrator

@pytest.mark.asyncio
async def test_process_simple_query(mock_orchestrator):
    """Test processing a query that doesn't require tool calls"""
    # Set up mock executor
    mock_orchestrator.tool_executor = Mock()
    mock_orchestrator.tool_executor.execute_tool = AsyncMock()
    
    query = "What is a gene?"
    response = await mock_orchestrator.process_query(query)
    
    assert isinstance(response, str)
    assert len(mock_orchestrator.conversation_history) == 2
    assert mock_orchestrator.client.chat.completions.create.called
    assert not mock_orchestrator.tool_executor.execute_tool.called

@pytest.mark.asyncio
async def test_process_query_with_tool_call(mock_orchestrator):
    """Test processing a query that requires tool calls"""
    # Set up mock responses
    mock_orchestrator.client.chat.completions.create = AsyncMock(side_effect=[
        Mock(
            choices=[Mock(
                message=Mock(
                    tool_calls=[Mock(
                        id="call_1",
                        function=Mock(
                            name="search_literature",
                            arguments='{"genes": ["DSP"], "phenotypes": ["myocardial infarction"], "max_results": 5}'
                        )
                    )],
                    content=None
                ),
                finish_reason="tool_calls"
            )]
        ),
        Mock(
            choices=[Mock(
                message=Mock(
                    content="Final response after tool call",
                ),
                finish_reason="stop"
            )]
        )
    ])
    
    # Set up mock executor
    mock_orchestrator.tool_executor = Mock()
    mock_orchestrator.tool_executor.execute_tool = AsyncMock(return_value={"result": "mock data"})
    
    query = "Find research papers about DSP and myocardial infarction"
    response = await mock_orchestrator.process_query(query)
    
    assert isinstance(response, str)
    assert response == "Final response after tool call"
    assert len(mock_orchestrator.conversation_history) >= 3
    assert mock_orchestrator.tool_executor.execute_tool.called

@pytest.mark.asyncio
async def test_conversation_history_management(mock_orchestrator):
    """Test conversation history management"""
    mock_orchestrator.clear_conversation_history()
    assert len(mock_orchestrator.conversation_history) == 0
    
    query = "What is DNA?"
    await mock_orchestrator.process_query(query)
    
    history = mock_orchestrator.get_conversation_history()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == query

@pytest.mark.asyncio
async def test_error_handling(mock_orchestrator):
    """Test error handling in query processing"""
    mock_orchestrator.client.chat.completions.create.side_effect = Exception("API Error")
    
    query = "What is a protein?"
    response = await mock_orchestrator.process_query(query)
    
    assert "error" in response.lower()
    assert len(mock_orchestrator.conversation_history) == 2

@pytest.mark.asyncio
async def test_system_message_content(mock_orchestrator):
    """Test that system message is properly included"""
    query = "What are genes?"
    await mock_orchestrator.process_query(query)
    
    # Check the first call to create completions
    call_args = mock_orchestrator.client.chat.completions.create.call_args_list[0]
    messages = call_args[1]["messages"]
    
    assert messages[0]["role"] == "system"
    assert "BioChat" in messages[0]["content"]

@pytest.mark.asyncio
async def test_multiple_tool_calls(mock_orchestrator):
    """Test handling multiple tool calls in sequence"""
    # Set up mock responses
    mock_orchestrator.client.chat.completions.create = AsyncMock(side_effect=[
        Mock(
            choices=[Mock(
                message=Mock(
                    tool_calls=[
                        Mock(
                            id="call_1",
                            function=Mock(
                                name="search_literature",
                                arguments='{"genes": ["DSP"], "phenotypes": ["Cancer"], "max_results": 5}'
                            )
                        ),
                        Mock(
                            id="call_2",
                            function=Mock(
                                name="get_protein_info",
                                arguments='{"protein_id": "DSP", "include_features": true}'
                            )
                        )
                    ],
                    content=None
                ),
                finish_reason="tool_calls"
            )]
        ),
        Mock(
            choices=[Mock(
                message=Mock(
                    content="Final response after multiple tools",
                ),
                finish_reason="stop"
            )]
        )
    ])
    
    # Set up mock executor
    mock_orchestrator.tool_executor = Mock()
    mock_orchestrator.tool_executor.execute_tool = AsyncMock(return_value={"result": "mock data"})
    
    query = "Tell me about DSP research and protein structure"
    response = await mock_orchestrator.process_query(query)
    
    assert isinstance(response, str)
    assert response == "Final response after multiple tools"
    assert mock_orchestrator.tool_executor.execute_tool.call_count == 2
    assert len(mock_orchestrator.conversation_history) >= 4  # User, tool calls, tool responses, final response