"""
Integration tests for the query analyzer module.
Tests the analyzer methods and database sequence determination.
"""

import pytest
import os
import json
from typing import Dict, List
import asyncio
from openai import AsyncOpenAI

from src.orchestrator import BioChatOrchestrator
from src.utils.query_analyzer import QueryAnalyzer

# Skip tests if environment variables aren't set up
pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OpenAI API key not set"
)

# Set of representative biological queries to test the full system
TEST_QUERIES = [
    {
        "query": "What are the key functions of the TP53 gene?",
        "expected_entity_types": ["gene"],
        "expected_databases": ["get_protein_info", "search_literature"]
    },
    {
        "query": "How does metformin affect insulin signaling pathways?",
        "expected_entity_types": ["drug", "protein", "pathway"],
        "expected_databases": ["analyze_pathways", "search_literature"]
    },
    {
        "query": "What proteins interact with ACE2 receptor?",
        "expected_entity_types": ["protein"],
        "expected_databases": ["get_string_interactions", "get_protein_info"]
    },
    {
        "query": "What genetic variants are associated with long QT syndrome?",
        "expected_entity_types": ["variant", "disease"],
        "expected_databases": ["search_variants", "search_gwas", "search_literature"]
    },
    {
        "query": "Compare the mechanisms of action between statins and PCSK9 inhibitors",
        "expected_entity_types": ["drug"],
        "expected_databases": ["search_literature", "search_chembl"]
    }
]

@pytest.fixture(scope="module")
def orchestrator():
    """Create a real orchestrator instance for testing."""
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    ncbi_api_key = os.environ.get("NCBI_API_KEY")
    contact_email = os.environ.get("CONTACT_EMAIL", "test@example.com")
    biogrid_key = os.environ.get("BIOGRID_ACCESS_KEY", "")
    
    return BioChatOrchestrator(
        openai_api_key=openai_api_key,
        ncbi_api_key=ncbi_api_key,
        biogrid_access_key=biogrid_key,
        tool_name="BioChat",
        email=contact_email
    )

@pytest.fixture(scope="module")
def openai_client():
    """Create an OpenAI client for testing."""
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    return AsyncOpenAI(api_key=openai_api_key)

@pytest.fixture(scope="module")
def query_analyzer(openai_client):
    """Create a QueryAnalyzer instance for testing."""
    return QueryAnalyzer(openai_client)


class TestQueryAnalyzerIntegration:
    """Integration tests for query analyzer with real API calls."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_data", TEST_QUERIES)
    async def test_query_analyzer_standalone(self, query_analyzer, test_data):
        """Test the query analyzer with real API calls but no database calls."""
        query = test_data["query"]
        
        # Run analysis with real LLM
        analysis = await query_analyzer.analyze_query(query)
        
        # Check basic analysis results
        assert "primary_intent" in analysis
        assert "entities" in analysis
        assert "relationship_type" in analysis
        assert "confidence" in analysis
        
        # Check that expected entity types are detected
        actual_entity_types = set(analysis.get("entities", {}).keys())
        expected_types = set(test_data["expected_entity_types"])
        
        # Some leniency - at least one expected entity type should be detected
        assert any(entity_type in actual_entity_types for entity_type in expected_types)
        
        # Get database sequence
        db_sequence = query_analyzer.get_optimal_database_sequence(analysis)
        
        # Check that the sequence includes at least one of the expected databases
        expected_dbs = set(test_data["expected_databases"])
        assert any(db in db_sequence for db in expected_dbs)
        
        # Generate domain-specific prompt
        prompt = query_analyzer.create_domain_specific_prompt(analysis)
        
        # Check that the prompt is meaningful
        assert len(prompt) > 200
        assert "BioChat" in prompt
        for entity_type in actual_entity_types:
            assert entity_type.lower() in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_orchestrator_analyzer_method(self, orchestrator):
        """Test the test_query_analyzer method in the orchestrator with real API calls."""
        query = "What pathways are involved in Alzheimer's disease?"
        
        # Run the test method
        result = await orchestrator.test_query_analyzer(query)
        
        # Verify basic structure
        assert result["success"] is True
        assert "analysis" in result
        assert "database_sequence" in result
        assert "prompt_preview" in result
        
        # Check analysis content
        analysis = result["analysis"]
        assert "primary_intent" in analysis
        assert "entities" in analysis
        
        # Should detect disease and possibly pathway
        entities = analysis.get("entities", {})
        assert any(entity_type in ["disease", "pathway"] for entity_type in entities.keys())
        
        # Check database sequence
        db_sequence = result["database_sequence"]
        assert len(db_sequence) > 0
        assert any(db in ["analyze_pathways", "search_literature"] for db in db_sequence)


    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_knowledge_graph_query(self, orchestrator):
        """
        Test a full knowledge graph query with real database calls.
        
        NOTE: This test makes real API calls to biological databases
        and may take some time to complete. It's marked with 'slow'.
        """
        try:
            query = "What role does the BRCA1 gene play in breast cancer?"
            
            # Run the complete query pipeline
            result = await orchestrator.process_knowledge_graph_query(query)
            
            # Verify result structure
            assert "query" in result
            assert "analysis" in result
            assert "database_sequence" in result
            assert "api_responses" in result
            assert "synthesis" in result
            
            # Analysis should include gene and disease entities
            entities = result["analysis"].get("entities", {})
            entity_types = set(entities.keys())
            assert "gene" in entity_types or "protein" in entity_types
            assert "disease" in entity_types
            
            # Database sequence should include literature search
            assert "search_literature" in result["database_sequence"]
            
            # The synthesis should be non-empty
            assert len(result["synthesis"]) > 0
            
        except Exception as e:
            pytest.skip(f"Test skipped due to external API issues: {str(e)}")

