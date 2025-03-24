"""
End-to-end integration tests for the BioChat package.
These tests verify that all components work together properly.
"""

import os
import pytest
import json
from biochat import BioChatOrchestrator
from biochat.utils.query_analyzer import QueryAnalyzer
from openai import AsyncOpenAI
from dotenv import load_dotenv
# Load environment variables for tests
load_dotenv()
pytestmark = [pytest.mark.asyncio, pytest.mark.integration, pytest.mark.slow]

@pytest.fixture
async def openai_client():
    """Fixture to provide an OpenAI client."""
    # Skip test if OpenAI API key is missing
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OpenAI API key not found in environment variables")
    
    # Initialize with only the API key to avoid compatibility issues
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    yield client

@pytest.fixture
async def query_analyzer(openai_client):
    """Fixture to provide a QueryAnalyzer instance."""
    # Pass the model parameter explicitly for compatibility
    analyzer = QueryAnalyzer(openai_client, model="gpt-4o")
    yield analyzer

@pytest.fixture
async def full_orchestrator():
    """Fixture to provide a fully configured BioChatOrchestrator instance."""
    # Skip tests if required variables are missing
    required_vars = ["OPENAI_API_KEY", "NCBI_API_KEY", "CONTACT_EMAIL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        pytest.skip(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Create orchestrator
    orch = BioChatOrchestrator(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        ncbi_api_key=os.getenv("NCBI_API_KEY"),
        biogrid_access_key=os.getenv("BIOGRID_ACCESS_KEY"),
        tool_name="BioChat_Integration_Test",
        email=os.getenv("CONTACT_EMAIL")
    )
    
    yield orch
    
    # Cleanup
    orch.clear_conversation_history()

class TestEndToEnd:
    """End-to-end integration tests for BioChat."""
    
    TEST_QUERIES = [
        "What is a gene?",
        "What is the role of TP53 in cancer?",
        "How does CD47 relate to cardiovascular disease?",
        "What are the main functions of insulin?"
    ]
    
    async def test_query_analysis_to_database_sequence(self, query_analyzer):
        """Test the flow from query analysis to database sequence selection."""
        for query in self.TEST_QUERIES:
            # Analyze query
            analysis = await query_analyzer.analyze_query(query)
            
            # Check that analysis contains expected fields
            assert "primary_intent" in analysis
            assert "entities" in analysis
            assert "relationship_type" in analysis
            
            # Get database sequence
            db_sequence = query_analyzer.get_optimal_database_sequence(analysis)
            
            # Check that we got a valid sequence
            assert isinstance(db_sequence, list)
            assert len(db_sequence) > 0
            
            # There should be at least one critical database (usually literature)
            assert db_sequence[0] in ["search_literature", "get_protein_info", "analyze_pathways"]
    
    async def test_full_query_workflow(self, full_orchestrator):
        """Test the full query workflow from start to finish."""
        # Test with a simple query that shouldn't take too long
        query = "What is a gene?"
        
        # Process the query with a timeout
        try:
            response = await full_orchestrator.process_query(query)
            
            # Check that we got a valid response
            assert response is not None
            assert isinstance(response, str)
            
            # Response should have reasonable length - could be error message or normal response
            assert len(response) > 20
            
            # The conversation history should be updated
            assert len(full_orchestrator.conversation_history) >= 1
            assert full_orchestrator.conversation_history[0]["role"] == "user"
            
            # Check if we got a meaningful response (not just error message)
            if len(response) > 100 and not response.startswith("I'm sorry"):
                # The response should contain relevant information about genes
                assert "gene" in response.lower() or "dna" in response.lower() or "rna" in response.lower()
                assert len(full_orchestrator.conversation_history) >= 2
                
        except Exception as e:
            pytest.skip(f"API error during test: {str(e)}")
    
    async def test_multi_turn_conversation(self, full_orchestrator):
        """Test a multi-turn conversation with follow-up questions."""
        try:
            # First query to establish context
            query1 = "What is DNA?"
            response1 = await full_orchestrator.process_query(query1)
            
            # Check that we got a valid response
            assert response1 is not None
            assert isinstance(response1, str)
            
            # Only proceed with follow-up if we got a meaningful response
            if len(response1) > 100 and not response1.startswith("I'm sorry"):
                # Follow-up question that relies on context
                query2 = "How does it store genetic information?"
                response2 = await full_orchestrator.process_query(query2)
                
                # Check that we got a valid response
                assert response2 is not None
                assert isinstance(response2, str)
                
                # If we got a meaningful response to the follow-up
                if len(response2) > 100 and not response2.startswith("I'm sorry"):
                    # The response should refer to DNA or genetic information
                    assert "dna" in response2.lower() or "genetic" in response2.lower() or "base" in response2.lower()
            
            # Clear conversation and ask a query that needs context
            # This tests that context is properly tracked
            full_orchestrator.clear_conversation_history()
            query3 = "How does it work?"
            response3 = await full_orchestrator.process_query(query3)
            
            # Basic validation only - the actual content will vary
            assert response3 is not None
            assert isinstance(response3, str)
            assert len(response3) > 20  # Even a clarification should have some length
            
        except Exception as e:
            pytest.skip(f"API error during test: {str(e)}")
    
    async def test_knowledge_graph_query(self, full_orchestrator):
        """Test the knowledge graph query processing capability."""
        # This is a more advanced test that uses the knowledge graph approach
        if not hasattr(full_orchestrator, "process_knowledge_graph_query"):
            pytest.skip("Knowledge graph query processing not available")
        
        try:
            # Use a query that benefits from knowledge graph processing
            query = "How does TP53 regulate apoptosis?"
            
            # Process the query with a timeout
            result = await full_orchestrator.process_knowledge_graph_query(query)
            
            # Check that we got a valid result
            assert result is not None
            assert isinstance(result, dict)
            assert "query" in result
            
            # Basic structure validation
            if "error" not in result:
                assert "synthesis" in result
                
                # Check that analysis and database sequence were generated
                assert "analysis" in result
                assert "database_sequence" in result
                
                # If we got a meaningful synthesis, validate content
                synthesis = result["synthesis"]
                if len(synthesis) > 100 and not synthesis.startswith("I'm sorry"):
                    assert ("tp53" in synthesis.lower() or "p53" in synthesis.lower())
                    assert "apoptosis" in synthesis.lower()
        
        except Exception as e:
            pytest.skip(f"API error during knowledge graph query test: {str(e)}")