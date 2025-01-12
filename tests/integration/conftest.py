import pytest
import os
import logging
from dotenv import load_dotenv
from src.orchestrator import BioChatOrchestrator
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('integration_tests.log')
    ]
)
logger = logging.getLogger(__name__)

def log_conversation(test_name: str, query: str, response: str):
    """Log the conversation exchange with clear formatting"""
    logger.info(f"\n{'='*80}\nTest: {test_name}\n{'='*80}")
    logger.info(f"Query: {query}")
    logger.info(f"Response: {response}")
    logger.info(f"{'='*80}\n")

@pytest.fixture(scope="session")
def integration_orchestrator():
    """Create a shared orchestrator instance for integration tests"""
    logger.info("Initializing integration test orchestrator")
    load_dotenv(".env.integration")
    
    orchestrator = BioChatOrchestrator(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        ncbi_api_key=os.getenv("NCBI_API_KEY"),
        tool_name="biochat_integration_tests",
        email=os.getenv("CONTACT_EMAIL")
    )
    
    logger.info("Orchestrator initialized successfully")
    return orchestrator

@pytest.fixture(autouse=True)
def clear_conversation_history(integration_orchestrator):
    """Clear conversation history before and after each test"""
    integration_orchestrator.clear_conversation_history()
    yield
    integration_orchestrator.clear_conversation_history()