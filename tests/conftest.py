"""
Test configuration for BioChat.
"""

import os
import pytest
from dotenv import load_dotenv
from biochat import BioChatOrchestrator

# Load environment variables for tests
load_dotenv()

# Check if required environment variables are set
required_vars = ["OPENAI_API_KEY", "NCBI_API_KEY", "CONTACT_EMAIL"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"WARNING: Missing required environment variables for tests: {', '.join(missing_vars)}")
    print("Some tests may be skipped or fail.")

@pytest.fixture
async def orchestrator():
    """Fixture to provide a BioChatOrchestrator instance."""
    # Skip tests if required variables are missing
    if missing_vars:
        pytest.skip(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Create orchestrator with updated parameters
    orch = BioChatOrchestrator(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        ncbi_api_key=os.getenv("NCBI_API_KEY"),
        biogrid_access_key=os.getenv("BIOGRID_ACCESS_KEY"),
        tool_name="BioChat_Test",
        email=os.getenv("CONTACT_EMAIL")
    )
    
    yield orch
    
    # Cleanup
    orch.clear_conversation_history()