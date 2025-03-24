"""
Basic example of using BioChat for a biological query.
"""

import asyncio
import os
from dotenv import load_dotenv
from biochat import BioChatOrchestrator

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment
openai_api_key = os.getenv("OPENAI_API_KEY")
ncbi_api_key = os.getenv("NCBI_API_KEY")
contact_email = os.getenv("CONTACT_EMAIL")
biogrid_access_key = os.getenv("BIOGRID_ACCESS_KEY")

# Example queries
QUERIES = [
    "What is the role of TP53 in cancer development?",
    "How does CD47 relate to cardiovascular disease?",
    "What are the main pathways involved in insulin signaling?",
]

async def main():
    # Initialize the orchestrator
    orchestrator = BioChatOrchestrator(
        openai_api_key=openai_api_key,
        ncbi_api_key=ncbi_api_key,
        biogrid_access_key=biogrid_access_key,
        tool_name="BioChat_Example",
        email=contact_email
    )
    
    # Process each query
    for query in QUERIES:
        print(f"\n\n=== QUERY: {query} ===\n")
        
        try:
            # Process the query
            response = await orchestrator.process_query(query)
            
            # Print the response
            print("RESPONSE:")
            print(response)
            
        except Exception as e:
            print(f"Error processing query: {str(e)}")
    
    # Clear conversation history
    orchestrator.clear_conversation_history()

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())