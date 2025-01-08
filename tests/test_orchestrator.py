import pytest
from unittest.mock import Mock, patch
from src.orchestrator import BioChatOrchestrator

@pytest.mark.asyncio
async def test_process_simple_query(mock_orchestrator):
    """Test processing a query that doesn't require tool calls"""
    query = "What is a gene?"
    
    response = await mock_orchestrator.process_query(query)
    
    assert isinstance(response, str)
    assert len(mock_orchestrator.conversation_history) == 2  # Query and response
    assert mock_orchestrator.client.chat.completions.create.called
    assert not mock_orchestrator.tool_executor.execute_tool.called

@pytest.mark.asyncio
async def test_process_query_with_tool_call(mock_orchestrator):
    """Test processing a query that requires tool calls"""
    query = "Find research papers about BRCA1 and breast cancer"
    
    response = await mock_orchestrator.process_query(query)
    
    assert isinstance(response, str)
    assert len(mock_orchestrator.conversation_history) >= 3  # Query, tool call, and response
    assert mock_orchestrator.client.chat.completions.create.call_count == 2
    assert mock_orchestrator.tool_executor.execute_tool.called

@pytest.mark.asyncio
async def test_conversation_history_management(mock_orchestrator):
    """Test conversation history management"""
    # Clear history
    mock_orchestrator.clear_conversation_history()
    assert len(mock_orchestrator.conversation_history) == 0
    
    # Process a query
    query = "What is DNA?"
    await mock_orchestrator.process_query(query)
    
    # Check history
    history = mock_orchestrator.get_conversation_history()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == query
    assert history[1]["role"] == "assistant"

@pytest.mark.asyncio
async def test_error_handling(mock_orchestrator):
    """Test error handling in query processing"""
    # Make the OpenAI client raise an exception
    mock_orchestrator.client.chat.completions.create.side_effect = Exception("API Error")
    
    query = "What is a protein?"
    response = await mock_orchestrator.process_query(query)
    
    assert "error" in response.lower()
    assert len(mock_orchestrator.conversation_history) == 2  # Query and error response

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
    assert "guidelines" in messages[0]["content"].lower()

@pytest.mark.asyncio
async def test_multiple_tool_calls(mock_orchestrator):
    """Test handling multiple tool calls in sequence"""
    # Configure mock to return multiple tool calls
    mock_orchestrator.client.chat.completions.create.side_effect = [
        Mock(
            choices=[Mock(
                message=Mock(
                    tool_calls=[
                        Mock(
                            id="call_1",
                            function=Mock(
                                name="search_literature",
                                arguments='{"genes": ["BRCA1"], "phenotypes": ["Cancer"]}'
                            )
                        ),
                        Mock(
                            id="call_2",
                            function=Mock(
                                name="get_protein_info",
                                arguments='{"protein_id": "BRCA1"}'
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
                message=Mock(content="Final response"),
                finish_reason="stop"
            )]
        )
    ]
    
    query = "Tell me about BRCA1 research and protein structure"
    response = await mock_orchestrator.process_query(query)
    
    assert mock_orchestrator.tool_executor.execute_tool.call_count == 2
    assert "Final response" in response