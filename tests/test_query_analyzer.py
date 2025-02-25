"""
Unit tests for the query analyzer module.
Tests entity extraction, query classification, and database prioritization.
"""

import pytest
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch
from src.utils.query_analyzer import (
    QueryAnalyzer, QueryIntent, EntityType, 
    RelationshipType, DatabasePriority, ENTITY_DB_MAPPING
)

# Setup test data
TEST_QUERIES = [
    {
        "query": "What are the known functions of the BRCA1 gene?",
        "expected_intent": "explanation",
        "expected_entities": {"gene": ["BRCA1"]},
        "expected_relationship": "functional"
    },
    {
        "query": "How does metformin interact with AMPK protein?",
        "expected_intent": "mechanism",
        "expected_entities": {"drug": ["metformin"], "protein": ["AMPK"]},
        "expected_relationship": "regulatory"
    },
    {
        "query": "What pathways are involved in insulin resistance?",
        "expected_intent": "explanation",
        "expected_entities": {"protein": ["insulin"], "phenotype": ["resistance"]},
        "expected_relationship": "associative"
    },
    {
        "query": "Can you predict how a mutation in the TP53 gene might affect cancer risk?",
        "expected_intent": "prediction",
        "expected_entities": {"gene": ["TP53"], "disease": ["cancer"]},
        "expected_relationship": "causal"
    },
    {
        "query": "Compare the efficacy of statins versus PCSK9 inhibitors for lowering cholesterol.",
        "expected_intent": "comparison",
        "expected_entities": {"drug": ["statins", "PCSK9 inhibitors"], "chemical": ["cholesterol"]},
        "expected_relationship": "functional"
    }
]


class TestQueryAnalyzer:
    """Test suite for the QueryAnalyzer class."""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        return mock_client
    
    @pytest.fixture
    def query_analyzer(self, mock_openai_client):
        """Create a QueryAnalyzer instance with a mock client."""
        return QueryAnalyzer(mock_openai_client)
    
    async def test_analyze_query(self, query_analyzer, mock_openai_client):
        """Test that analyze_query correctly processes queries."""
        # Setup mock response
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "primary_intent": "explanation",
            "entities": {"gene": ["BRCA1"]},
            "relationship_type": "functional",
            "confidence": 0.9
        })
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Call the method
        result = await query_analyzer.analyze_query("What are the functions of BRCA1?")
        
        # Verify results
        assert result["primary_intent"] == "explanation"
        assert "gene" in result["entities"]
        assert "BRCA1" in result["entities"]["gene"]
        assert result["relationship_type"] == "functional"
        assert result["confidence"] == 0.9
        
        # Verify the appropriate API call was made
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args[1]
        assert call_args["model"] == "gpt-4o"
        assert len(call_args["messages"]) == 2
        assert call_args["messages"][0]["role"] == "system"
        assert call_args["messages"][1]["role"] == "user"
        assert call_args["response_format"]["type"] == "json_object"
    
    def test_get_optimal_database_sequence(self, query_analyzer):
        """Test database sequence generation based on entities and relationships."""
        # Test case 1: Gene and disease
        analysis1 = {
            "primary_intent": "explanation",
            "entities": {"gene": ["BRCA1"], "disease": ["breast cancer"]},
            "relationship_type": "causal"
        }
        
        db_sequence1 = query_analyzer.get_optimal_database_sequence(analysis1)
        assert len(db_sequence1) > 0
        assert "search_literature" in db_sequence1  # Literature should be included
        
        # Test case 2: Protein interaction query
        analysis2 = {
            "primary_intent": "mechanism",
            "entities": {"protein": ["insulin receptor", "IRS1"]},
            "relationship_type": "regulatory"
        }
        
        db_sequence2 = query_analyzer.get_optimal_database_sequence(analysis2)
        assert len(db_sequence2) > 0
        assert "get_string_interactions" in db_sequence2  # STRING should be included
        
        # Test case 3: Empty analysis fallback
        analysis3 = {
            "primary_intent": "unknown",
            "entities": {},
            "relationship_type": "unknown"
        }
        
        db_sequence3 = query_analyzer.get_optimal_database_sequence(analysis3)
        assert len(db_sequence3) > 0
        assert "search_literature" in db_sequence3  # Default fallback
    
    def test_create_domain_specific_prompt(self, query_analyzer):
        """Test domain-specific prompt generation."""
        # Test for explanation intent
        analysis1 = {
            "primary_intent": "explanation",
            "entities": {"gene": ["BRCA1"], "protein": ["p53"]},
            "relationship_type": "regulatory"
        }
        
        prompt1 = query_analyzer.create_domain_specific_prompt(analysis1)
        assert "BioChat" in prompt1
        assert "explanation" in prompt1.lower()
        assert "gene" in prompt1.lower() and "protein" in prompt1.lower()
        assert "regulatory" in prompt1.lower()
        
        # Test for treatment intent
        analysis2 = {
            "primary_intent": "treatment",
            "entities": {"drug": ["metformin"], "disease": ["diabetes"]},
            "relationship_type": "associative"
        }
        
        prompt2 = query_analyzer.create_domain_specific_prompt(analysis2)
        assert "BioChat" in prompt2
        assert "treatment" in prompt2.lower()
        assert "drug" in prompt2.lower() and "disease" in prompt2.lower()
        
        # Test error handling
        analysis3 = {"invalid_key": "value"}
        prompt3 = query_analyzer.create_domain_specific_prompt(analysis3)
        assert "BioChat" in prompt3  # Should return default prompt
    
    @pytest.mark.parametrize("test_data", TEST_QUERIES)
    async def test_query_analysis_integration(self, query_analyzer, mock_openai_client, test_data):
        """Test full analysis pipeline with parametrized test cases."""
        # Setup mock response
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "primary_intent": test_data["expected_intent"],
            "entities": test_data["expected_entities"],
            "relationship_type": test_data["expected_relationship"],
            "confidence": 0.85
        })
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Execute analysis
        result = await query_analyzer.analyze_query(test_data["query"])
        
        # Get database sequence
        db_sequence = query_analyzer.get_optimal_database_sequence(result)
        
        # Generate domain-specific prompt
        prompt = query_analyzer.create_domain_specific_prompt(result)
        
        # Verify results
        assert result["primary_intent"] == test_data["expected_intent"]
        assert set(result["entities"].keys()).issuperset(set(test_data["expected_entities"].keys()))
        assert result["relationship_type"] == test_data["expected_relationship"]
        assert len(db_sequence) > 0
        assert len(prompt) > 0
        assert test_data["expected_intent"] in prompt.lower()