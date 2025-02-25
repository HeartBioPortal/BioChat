#!/usr/bin/env python
"""
Script to run a knowledge graph query through the BioChatOrchestrator.
This script demonstrates the full knowledge graph approach for biological queries.

Usage:
    python run_kg_query.py "What are the functions of the BRCA1 gene in breast cancer?"
"""

import os
import sys
import json
import asyncio
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.orchestrator import BioChatOrchestrator

# Sample queries to test if none provided
SAMPLE_QUERIES = [
    "What are the key functions of the TP53 gene?",
    "How does metformin affect insulin signaling pathways?",
    "What proteins interact with ACE2 receptor?",
    "What genetic variants are associated with Alzheimer's disease?",
    "Compare the mechanisms of action between statins and PCSK9 inhibitors",
    "How do SGLT2 inhibitors work in diabetes treatment?"
]

async def run_knowledge_graph_query(query: str):
    """Run a query using the knowledge graph approach"""
    print(f"\n{'-'*80}")
    print(f"Running knowledge graph query: \"{query}\"")
    print(f"{'-'*80}\n")
    
    # Load environment variables
    load_dotenv()
    
    # Initialize OpenAI client
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    ncbi_api_key = os.environ.get("NCBI_API_KEY")
    contact_email = os.environ.get("CONTACT_EMAIL", "test@example.com")
    biogrid_key = os.environ.get("BIOGRID_ACCESS_KEY", "")
    
    if not openai_api_key or not ncbi_api_key:
        print("Error: Required API keys not found in environment variables")
        return
    
    # Create orchestrator
    orchestrator = BioChatOrchestrator(
        openai_api_key=openai_api_key,
        ncbi_api_key=ncbi_api_key,
        biogrid_access_key=biogrid_key,
        tool_name="BioChat",
        email=contact_email
    )
    
    try:
        print("Processing query with knowledge graph approach...")
        result = await orchestrator.process_knowledge_graph_query(query)
        
        # Check if query was successful
        if "error" in result:
            print(f"Error processing query: {result['error']}")
            return
            
        # Print analysis summary
        print("\nQUERY ANALYSIS:")
        print(f"Intent: {result['analysis'].get('primary_intent', 'unknown')}")
        print(f"Relationship: {result['analysis'].get('relationship_type', 'unknown')}")
        
        # Print entity summary
        print("\nENTITIES DETECTED:")
        for entity_type, entities in result['analysis'].get('entities', {}).items():
            print(f"  - {entity_type}: {', '.join(entities)}")
        
        # Print database sequence
        print("\nDATABASE SEQUENCE:")
        for i, db in enumerate(result['database_sequence'][:5]):
            print(f"  {i+1}. {db}")
        if len(result['database_sequence']) > 5:
            print(f"  ... and {len(result['database_sequence']) - 5} more")
        
        # Print API responses summary
        print("\nAPI RESPONSES:")
        if not result['api_responses']:
            print("  No API responses collected")
        else:
            for api, response in result['api_responses'].items():
                print(f"  - {api}: Response received")
        
        # Print full synthesis
        print("\nSYNTHESIS:")
        print(f"{result['synthesis']}")
        
        # Print file location
        print(f"\nFull response saved to api_results/kg_response_{result['timestamp']}.json")
        
    except Exception as e:
        print(f"Error: {str(e)}")

async def main():
    # Get query from command line or use samples
    if len(sys.argv) > 1:
        query = sys.argv[1]
        await run_knowledge_graph_query(query)
    else:
        print("No query provided. Choose a sample query:")
        for i, query in enumerate(SAMPLE_QUERIES):
            print(f"{i+1}. {query}")
        
        try:
            choice = int(input("\nEnter number (1-6): "))
            if 1 <= choice <= len(SAMPLE_QUERIES):
                await run_knowledge_graph_query(SAMPLE_QUERIES[choice-1])
            else:
                print("Invalid choice")
        except ValueError:
            print("Invalid input")

if __name__ == "__main__":
    asyncio.run(main())