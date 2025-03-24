"""
Basic tests for BioChat to verify OpenAI client setup.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json
from biochat import BioChatOrchestrator
import os
from openai import AsyncOpenAI

# Skip test if environment variables are missing
required_vars = ["OPENAI_API_KEY", "NCBI_API_KEY", "CONTACT_EMAIL"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

@pytest.mark.asyncio
class TestBasicFunctionality:
    """Basic functionality tests with mocks."""
    
    @pytest.mark.skipif(missing_vars, reason=f"Missing required environment variables: {missing_vars}")
    async def test_openai_client_initialization(self):
        """Test that the OpenAI client initializes properly."""
        # Create the client directly
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        assert client is not None
        
    @pytest.mark.skipif(missing_vars, reason=f"Missing required environment variables: {missing_vars}")
    @patch("openai.resources.chat.completions.AsyncCompletions.create")
    async def test_orchestrator_with_mock(self, mock_completions):
        """Test the orchestrator with a mocked OpenAI client."""
        # Configure the mock
        mock_response = AsyncMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="This is a mock response"))
        ]
        mock_completions.return_value = mock_response
        
        # Create orchestrator
        orchestrator = BioChatOrchestrator(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            ncbi_api_key=os.getenv("NCBI_API_KEY"),
            tool_name="BioChat_Test_Mock",
            email=os.getenv("CONTACT_EMAIL")
        )
        
        # We're not actually testing the API, just that the initialization works
        assert orchestrator is not None