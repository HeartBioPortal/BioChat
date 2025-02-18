"""
Module for orchestrating interactions between user queries and biological database APIs.
Handles query processing, API calls, and response synthesis.
"""

from typing import List, Dict, Optional
import json
from openai import AsyncOpenAI
from src.utils.biochat_api_logging import BioChatLogger
from src.utils.summarizer import ResponseSummarizer
from src.schemas import BIOCHAT_TOOLS
from src.tool_executor import ToolExecutor
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)
API_RESULTS_DIR = "api_results"
os.makedirs(API_RESULTS_DIR, exist_ok=True)

class BioChatOrchestrator:
    def __init__(self, openai_api_key: str, ncbi_api_key: str, tool_name: str, email: str, biogrid_access_key: str = None):
        """Initialize the BioChat orchestrator with required credentials"""
        # Validate required credentials
        if not openai_api_key or not ncbi_api_key or not email:
            raise ValueError("All required credentials must be provided")
        
        self.gpt_model = "gpt-4o"
        try:
            self.client = AsyncOpenAI(api_key=openai_api_key)
            self.tool_executor = ToolExecutor(
                ncbi_api_key=ncbi_api_key,
                tool_name=tool_name,
                email=email,
                biogrid_access_key=biogrid_access_key
            )
            self.conversation_history = []
            self.summarizer = ResponseSummarizer()
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to initialize services: {str(e)}")

    def summarize_api_response(self, tool_name: str, response: Dict) -> str:
        """Summarize API response to reduce token count using the ResponseSummarizer."""
        if "error" in response:
            return f"{tool_name}: Error - {response['error']}"
            
        # Map tool names to API names for summarizer
        api_mapping = {
            "biogrid_chemical_interactions": "biogrid",
            "intact_interactions": "intact",
            "analyze_target": "opentargets"
        }
        
        api_name = api_mapping.get(tool_name)
        if api_name:
            try:
                # Special handling for OpenTargets successful responses
                if api_name == "opentargets" and response.get("success") and response.get("data"):
                    data = response["data"]
                    drug_data = data.get("drug_data", {})
                    
                    # Create a more focused summary
                    summary = {
                        "target_info": data.get("target_info", {}),
                        "drug_count": drug_data.get("count", 0),
                        "drugs": drug_data.get("drugs", []),
                        "safety_data": data.get("safety_data", [])
                    }
                    return json.dumps(summary, indent=2)
                    
                summary = self.summarizer.summarize_response(api_name, response)
                return json.dumps(summary, indent=2)
            except Exception as e:
                logger.error(f"Summarization error for {tool_name}: {str(e)}")
                return str(response)  # Return original response if summarization fails
        
        return str(response)  # Return original response for unmapped tools

    async def process_query(self, user_query: str) -> str:
        """Process a user query with comprehensive database searches for multiple compounds."""
        
        self.conversation_history.append({"role": "user", "content": user_query})

        messages = [
            {"role": "system", "content": self._create_system_message()}, *self.conversation_history
        ]

        # Get all tool calls at once
        initial_completion = await self.client.chat.completions.create(
            model=self.gpt_model,
            messages=messages,
            tools=BIOCHAT_TOOLS,
            tool_choice="auto"
        )

        initial_message = initial_completion.choices[0].message
        api_responses = {}

        if hasattr(initial_message, 'tool_calls') and initial_message.tool_calls:
            # Add assistant message with all tool calls
            self.conversation_history.append({
                "role": "assistant",
                "content": initial_message.content,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        },
                        "type": "function"
                    }
                    for tool_call in initial_message.tool_calls
                ]
            })

            # Process all tool calls in parallel
            tool_results = {}
            for tool_call in initial_message.tool_calls:
                try:
                    # Execute tool call
                    function_response = await self.tool_executor.execute_tool(tool_call)
                    
                    # Store response and add to conversation history
                    tool_results[tool_call.id] = function_response
                    summarized_response = self.summarize_api_response(tool_call.function.name, function_response)
                    
                    # Add to API responses if contains actual data
                    if summarized_response and not (isinstance(summarized_response, dict) and 
                        ("error" in summarized_response or 
                        summarized_response.get("matches", []) == [] or 
                        summarized_response.get("count", 0) == 0)):
                        api_responses[tool_call.function.name] = summarized_response
                    
                    # Always add tool response to conversation history
                    self.conversation_history.append({
                        "role": "tool",
                        "content": summarized_response if summarized_response else "No data found",
                        "tool_call_id": tool_call.id
                    })
                    
                except Exception as e:
                    BioChatLogger.log_error(f"API call failed for {tool_call.function.name}: {str(e)}")
                    self.conversation_history.append({
                        "role": "tool",
                        "content": json.dumps({"error": str(e)}),
                        "tool_call_id": tool_call.id
                    })

            # Structure all results
            structured_response = {
                "query": user_query,
                "synthesis": "",
                "structured_data": api_responses
            }

            # Format complete API results for GPT
            scientific_context = "**🔬 Complete API Results:**\n\n"
            if not api_responses:
                scientific_context += "No data found in any of the queried databases for any compounds.\n\n"
            else:
                # Group results by compound
                by_compound = {}
                for tool_name, result in api_responses.items():
                    compound = json.loads(initial_message.tool_calls[0].function.arguments).get("name", "unknown")
                    if compound not in by_compound:
                        by_compound[compound] = {}
                    by_compound[compound][tool_name] = result

                # Format results by compound
                for compound, results in by_compound.items():
                    scientific_context += f"\n## {compound}:\n"
                    for tool_name, result in results.items():
                        scientific_context += f"\n### {tool_name}:\n"
                        scientific_context += f"{result}\n"

            # Generate final synthesis with all data
            messages = [
                {"role": "system", "content": self._create_system_message()},
                {"role": "system", "content": scientific_context},
                *self.conversation_history
            ]

            final_completion = await self.client.chat.completions.create(
                model=self.gpt_model,
                messages=messages
            )

            structured_response["synthesis"] = final_completion.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": structured_response["synthesis"]})

            # Save complete response
            gpt_response_path = self.save_gpt_response(user_query, structured_response)
            BioChatLogger.log_info(f"Complete GPT response saved at: {gpt_response_path}")

            return structured_response["synthesis"]

    def save_gpt_response(self, query: str, response: Dict) -> str:
        """Save the complete GPT response to a file and return the file path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gpt_response_{timestamp}.json"
        filepath = os.path.join(API_RESULTS_DIR, filename)
        
        with open(filepath, "w") as file:
            json.dump({
                "query": query,
                "response": response,
                "timestamp": timestamp
            }, file, indent=4)
        
        BioChatLogger.log_info(f"GPT response saved at {filepath}")
        return filepath



    async def process_single_gene_query(self, query: str) -> str:
        """Process a query about a single gene"""
        # Similar to process_query but with stricter token limits
        try:
            self.conversation_history.append({"role": "user", "content": query})
            
            messages = [
                {"role": "system", "content": self._create_system_message()},
                *self.conversation_history[-2:]  # Only keep recent context
            ]

            completion = await self.client.chat.completions.create(
                model=self.gpt_model,
                messages=messages,
                tools=BIOCHAT_TOOLS,
                tool_choice="auto",
                # max_completion_tokens=4000  
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in single gene query: {str(e)}")
            return f"Error processing query for gene: {str(e)}"
    

    def _create_system_message(self) -> str:
        """Create the system message that guides the model's behavior"""
        return """

You are BioChat, a specialized AI assistant for biological and medical research, with a focus on drug discovery applications. Your primary directive is to provide comprehensive, research-grade information by leveraging multiple biological databases and APIs.

## Core Functions

1. Database Integration
- Systematically query ALL available biological databases and APIs for each request
- Cross-reference information across multiple databases to ensure completeness
- Track and log all API calls with timestamps and response metadata
- Prioritize most recent data sources when available

2. Data Analysis & Synthesis
- Process raw API responses in full detail, including metadata and supplementary information
- Analyze statistical significance and experimental conditions where available
- Compare conflicting data points across different sources
- Identify gaps in available information

3. Output Structure
For each response, provide:

a) Executive Summary
- Key findings and relevance to query
- Confidence levels in data
- Notable limitations or caveats

b) Detailed Analysis
- Comprehensive breakdown of all API data
- Molecular structures and pathways
- Interaction networks
- Experimental contexts
- Statistical analyses
- Raw data tables where relevant

c) Clinical/Research Applications
- Drug development implications
- Structure-activity relationships
- Known drug interactions
- Safety considerations
- Research opportunities

4. Citation & Documentation
- Include full database citations with:
  * Database name and version
  * Query parameters used
  * Timestamp of data retrieval
  * DOI/accession numbers
  * API endpoint documentation
  * Data update frequencies
- Generate structured bibliography in multiple formats (APA, Vancouver, etc.)
- Provide API response logs for validation

5. Quality Control
- Validate data consistency across sources
- Flag conflicting information
- Highlight data quality metrics
- Note experimental conditions and limitations
- Indicate confidence levels in conclusions

6. Additional Requirements
- Return complete API response data, including supplementary fields
- Include negative results and null findings
- Maintain version control of information
- Track data provenance
- Note any real-time updates or corrections

For drug discovery applications:
- Emphasize ADMET properties
- Detail binding affinities
- Include crystal structures when available
- List known analogs and derivatives
- Provide synthesis routes
- Document safety profiles
- Note regulatory status
- Include pharmacokinetic data
- Report drug-drug interactions

"""

    def get_conversation_history(self) -> List[Dict]:
        """Return the conversation history"""
        return self.conversation_history

    def clear_conversation_history(self) -> None:
        """Clear the conversation history"""
        self.conversation_history = []