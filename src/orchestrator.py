from typing import List, Dict, Optional
import json
from openai import AsyncOpenAI
from src.utils.biochat_api_logging import BioChatLogger
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
            
        try:
            self.client = AsyncOpenAI(api_key=openai_api_key)
            self.tool_executor = ToolExecutor(
                ncbi_api_key=ncbi_api_key,
                tool_name=tool_name,
                email=email,
                biogrid_access_key=biogrid_access_key
            )
            self.conversation_history = []
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to initialize services: {str(e)}")

    def save_gpt_response(self, query: str, response: str) -> str:
        """Save the final GPT response to a file and return the file path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gpt_response_{timestamp}.json"
        filepath = os.path.join(API_RESULTS_DIR, filename)
        
        with open(filepath, "w") as file:
            json.dump({"query": query, "response": response}, file, indent=4)
        
        logger.info(f"Final GPT response saved at {filepath}")
        return filepath

    async def process_query(self, user_query: str) -> str:
        """Process a user query and return GPT synthesis as a string."""
        try:
            self.conversation_history.append({"role": "user", "content": user_query})

            messages = [
                {"role": "system", "content": self._create_system_message()},
                *self.conversation_history
            ]

            # Step 1: Initial request to ChatGPT
            initial_completion = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=BIOCHAT_TOOLS,
                tool_choice="auto"
            )

            initial_message = initial_completion.choices[0].message

            # Step 2: Collect API responses
            api_responses = {}

            if hasattr(initial_message, 'tool_calls') and initial_message.tool_calls:
                tool_call_responses = []
                for tool_call in initial_message.tool_calls:
                    try:
                        function_response = await self.tool_executor.execute_tool(tool_call)

                        # ✅ Store API results properly
                        api_responses[tool_call.function.name] = function_response  

                        tool_call_responses.append({
                            "role": "tool",
                            "content": json.dumps(function_response),
                            "tool_call_id": tool_call.id
                        })
                    except Exception as e:
                        api_responses[tool_call.function.name] = {"error": str(e)}
                        tool_call_responses.append({
                            "role": "tool",
                            "content": json.dumps({"error": str(e)}),
                            "tool_call_id": tool_call.id
                        })

                if tool_call_responses:
                    self.conversation_history.extend(tool_call_responses)


            # Step 3: Convert API responses to structured JSON format
            structured_response = {
                "query": user_query,
                "synthesis": "",  # Will be filled after ChatGPT processes it
                "structured_data": api_responses  # Stores API results in JSON format
            }

            # Step 4: Format API results into a system prompt for ChatGPT
            scientific_context = "**🔬 API Results (Filtered & Relevant):**\n\n"
            for tool_name, result in api_responses.items():
                if tool_name == "get_biogrid_interactions" or tool_name == "get_string_interactions":
                    scientific_context += f"**🔗 {tool_name} (Top Interactions):**\n"
                    scientific_context += json.dumps(result["top_interactions"], indent=4) + "\n\n"
                    scientific_context += f"📂 Full data available at: {result['download_url']}\n\n"
                else:
                    scientific_context += f"**🔗 {tool_name} API Response:**\n{json.dumps(result, indent=4)}\n\n"

            # ✅ Add explicit GPT instructions
            scientific_context += (
                "\n🔬 **GPT Instructions:**\n"
                "- Use the API results to generate a scientific summary.\n"
                "- Reference API sources explicitly.\n"
                "- If a tool provided a download link, mention that full data is available."
            )

            # Step 5: Augment conversation history with API data
            messages = [
                {"role": "system", "content": self._create_system_message()},
                {"role": "system", "content": scientific_context},  # Include structured API results
                *self.conversation_history
            ]
            # 🚨 Remove empty tool messages to prevent OpenAI API errors
            messages = [msg for msg in messages if msg.get("role") != "tool" or "tool_call_id" in msg]

            # Step 6: Generate final ChatGPT synthesis
            final_completion = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )

            structured_response["synthesis"] = final_completion.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": structured_response["synthesis"]})

            gpt_response_path = self.save_gpt_response(user_query, structured_response["synthesis"])
            logger.info(f"GPT response saved at: {gpt_response_path}")

            # ✅ Return GPT response as a string (fixes test case)
            return structured_response["synthesis"]

        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            return error_message





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
                model="gpt-4o",
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