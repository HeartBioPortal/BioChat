"""
Integration tests for the QueryAnalyzer utility.
"""

import os
import pytest
from openai import AsyncOpenAI
from biochat.utils.query_analyzer import QueryAnalyzer

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def query_analyzer():
    """Fixture to provide a QueryAnalyzer instance."""
    # Skip test if OpenAI API key is missing
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OpenAI API key not found in environment variables")
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    analyzer = QueryAnalyzer(client)
    
    yield analyzer

class TestQueryAnalyzer:
    """Test the QueryAnalyzer utility."""
    
    async def test_analyze_query(self, query_analyzer):
        """Test query analysis functionality."""
        # Test with a simple query
        query = "What is the role of TP53 in cancer development?"
        analysis = await query_analyzer.analyze_query(query)
        
        # Check analysis structure
        assert analysis is not None
        assert isinstance(analysis, dict)
        assert "primary_intent" in analysis
        assert "entities" in analysis
        assert "relationship_type" in analysis
        
        # Check that we got gene entity
        assert "gene" in analysis["entities"]
        assert "TP53" in analysis["entities"]["gene"]
        
        # Check that we got disease entity
        assert "disease" in analysis["entities"]
        assert any("cancer" in disease.lower() for disease in analysis["entities"]["disease"])
    
    async def test_get_optimal_database_sequence(self, query_analyzer):
        """Test database sequence optimization."""
        # Create a sample analysis
        analysis = {
            "primary_intent": "explanation",
            "entities": {
                "gene": ["TP53"],
                "disease": ["cancer"]
            },
            "relationship_type": "causal"
        }
        
        # Get database sequence
        db_sequence = query_analyzer.get_optimal_database_sequence(analysis)
        
        # Check that we got a valid sequence
        assert db_sequence is not None
        assert isinstance(db_sequence, list)
        assert len(db_sequence) > 0
        
        # For gene-disease queries, we should have literature search
        assert "search_literature" in db_sequence
    
    def test_create_domain_specific_prompt(self, query_analyzer):
        """Test domain-specific prompt creation."""
        # Create a sample analysis
        analysis = {
            "primary_intent": "explanation",
            "entities": {
                "gene": ["TP53"],
                "disease": ["cancer"]
            },
            "relationship_type": "causal"
        }
        
        # Create domain-specific prompt
        prompt = query_analyzer.create_domain_specific_prompt(analysis)
        
        # Check that we got a valid prompt
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        
        # Check that the prompt includes relevant content
        assert "TP53" in prompt or "gene" in prompt
        assert "cancer" in prompt or "disease" in prompt
        assert "causal" in prompt or "cause" in prompt