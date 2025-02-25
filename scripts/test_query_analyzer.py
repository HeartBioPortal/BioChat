#!/usr/bin/env python
"""
Manual testing script for the query analyzer.
This script allows testing of the query analyzer with different biological queries
and displays the analysis results, database sequence, and domain-specific prompt.

Usage:
    python test_query_analyzer.py "What genes are involved in Alzheimer's disease?"
"""

import os
import sys
import json
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.query_analyzer import QueryAnalyzer
from src.orchestrator import BioChatOrchestrator

# Load environment variables
load_dotenv()

# Sample queries to test if none provided
SAMPLE_QUERIES = [
    "What are the functions of the TP53 gene?",
    "How does metformin affect insulin signaling?",
    "What proteins interact with ACE2 receptor?",
    "What genetic variants are associated with Alzheimer's disease?",
    "Compare the mechanisms of action between statins and PCSK9 inhibitors",
    "What pathways are dysregulated in breast cancer?",
    "How do SGLT2 inhibitors work in diabetes treatment?",
    "What is the role of inflammation in cardiovascular disease?",
    "Which genes are involved in cholesterol metabolism?",
    "How does the APOE4 variant contribute to Alzheimer's disease risk?"
]

async def test_query(query: str):
    """Test a query with the QueryAnalyzer"""
    print(f"\n{'='*80}")
    print(f"Testing query: \"{query}\"")
    print(f"{'='*80}")
    
    # Initialize OpenAI client
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    client = AsyncOpenAI(api_key=openai_api_key)
    query_analyzer = QueryAnalyzer(client)
    
    # Analyze query
    print("\nAnalyzing query...")
    try:
        analysis = await query_analyzer.analyze_query(query)
        
        # Print analysis results
        print("\n## Analysis Results:")
        print(f"Primary Intent: {analysis.get('primary_intent', 'unknown')}")
        print(f"Relationship Type: {analysis.get('relationship_type', 'unknown')}")
        print(f"Confidence: {analysis.get('confidence', 0.0)}")
        
        print("\nEntities:")
        for entity_type, entities in analysis.get("entities", {}).items():
            print(f"  - {entity_type}: {', '.join(entities)}")
        
        # Get database sequence
        db_sequence = query_analyzer.get_optimal_database_sequence(analysis)
        print("\n## Optimal Database Sequence:")
        for i, db in enumerate(db_sequence[:10]):  # Limit to top 10
            print(f"  {i+1}. {db}")
        
        # Generate domain-specific prompt
        prompt = query_analyzer.create_domain_specific_prompt(analysis)
        print("\n## Domain-Specific Prompt Preview:")
        # Print first 300 chars
        print(f"{prompt[:300]}...\n[truncated]")
        
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

async def test_with_orchestrator(query: str):
    """Test a query using the BioChatOrchestrator's test method"""
    print("\n## Testing with Orchestrator")
    
    # Initialize credentials
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    ncbi_api_key = os.environ.get("NCBI_API_KEY")
    contact_email = os.environ.get("CONTACT_EMAIL", "test@example.com")
    biogrid_key = os.environ.get("BIOGRID_ACCESS_KEY", "")
    
    if not openai_api_key or not ncbi_api_key:
        print("Error: Missing required credentials")
        return False
    
    try:
        # Create orchestrator
        orchestrator = BioChatOrchestrator(
            openai_api_key=openai_api_key,
            ncbi_api_key=ncbi_api_key,
            biogrid_access_key=biogrid_key,
            tool_name="BioChat",
            email=contact_email
        )
        
        # Test query analyzer
        result = await orchestrator.test_query_analyzer(query)
        
        if result["success"]:
            print("Orchestrator test successful!")
            print(f"Database sequence: {', '.join(result['database_sequence'][:5])}...")
        else:
            print(f"Orchestrator test failed: {result.get('error', 'Unknown error')}")
        
    except Exception as e:
        print(f"Orchestrator error: {str(e)}")
        return False
    
    return True

async def main():
    # Get query from command line or use samples
    if len(sys.argv) > 1:
        query = sys.argv[1]
        await test_query(query)
        await test_with_orchestrator(query)
    else:
        print("No query provided. Testing with sample queries...")
        for i, query in enumerate(SAMPLE_QUERIES):
            print(f"\nSample query {i+1}/{len(SAMPLE_QUERIES)}")
            await test_query(query)
            # Skip orchestrator test for samples to reduce API calls
            if i == 0:  # Only test first sample with orchestrator
                await test_with_orchestrator(query)

if __name__ == "__main__":
    asyncio.run(main())