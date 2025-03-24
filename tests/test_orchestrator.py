"""
Integration tests for the BioChatOrchestrator class.
"""

import pytest
import re
from unittest.mock import patch, AsyncMock, MagicMock

# Mark all tests as asyncio
pytestmark = pytest.mark.asyncio

class TestBioChatOrchestrator:
    """Test the BioChatOrchestrator class."""
    
    async def test_initialization(self, orchestrator):
        """Test that the orchestrator initializes properly."""
        assert orchestrator is not None
        assert orchestrator.conversation_history == []
    
    async def test_process_query(self, orchestrator):
        """Test processing a simple query."""
        # Use a simple query that doesn't rely on third-party APIs too much
        query = "What is a gene?"
        
        # Process the query
        response = await orchestrator.process_query(query)
        
        # Check that we got a non-empty response
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 100  # Response should be substantial
        
        # Check that the conversation history was updated
        assert len(orchestrator.conversation_history) == 2
        assert orchestrator.conversation_history[0]["role"] == "user"
        assert orchestrator.conversation_history[0]["content"] == query
        assert orchestrator.conversation_history[1]["role"] == "assistant"
        assert orchestrator.conversation_history[1]["content"] == response
    
    async def test_conversation_history(self, orchestrator):
        """Test that conversation history works properly."""
        # Clear conversation history
        orchestrator.clear_conversation_history()
        assert orchestrator.conversation_history == []
        
        # Process two queries
        query1 = "What is DNA?"
        query2 = "How does it store genetic information?"
        
        # First query
        response1 = await orchestrator.process_query(query1)
        assert len(orchestrator.conversation_history) == 2
        
        # Second query should take the first into account
        response2 = await orchestrator.process_query(query2)
        assert len(orchestrator.conversation_history) == 4
        
        # Check that the history contains both interactions
        assert orchestrator.conversation_history[0]["content"] == query1
        assert orchestrator.conversation_history[1]["content"] == response1
        assert orchestrator.conversation_history[2]["content"] == query2
        assert orchestrator.conversation_history[3]["content"] == response2
        
        # Get conversation history
        history = orchestrator.get_conversation_history()
        assert history == orchestrator.conversation_history
        
        # Clear history
        orchestrator.clear_conversation_history()
        assert orchestrator.conversation_history == []