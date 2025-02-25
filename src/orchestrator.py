"""
Module for orchestrating interactions between user queries and biological database APIs.
Handles query processing, API calls, and response synthesis.
"""

from typing import List, Dict, Optional, Union, Set, Tuple
import json
from openai import AsyncOpenAI
from src.utils.biochat_api_logging import BioChatLogger
from src.utils.summarizer import ResponseSummarizer, StringInteractionExecutor
from src.schemas import BIOCHAT_TOOLS, EndpointPriority, QueryCategory, ENDPOINT_PRIORITY_MAP
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
            self.string_executor = StringInteractionExecutor(self.client, self.gpt_model)
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

    async def determine_query_categories(self, query: str) -> List[QueryCategory]:
        """
        Use the LLM to determine the categories of the query to prioritize endpoints.
        
        Args:
            query: The user's query string
            
        Returns:
            List of QueryCategory enum values
        """
        try:
            system_prompt = """
            Your task is to categorize a biological or medical research query into one or more categories.
            Analyze the query and return ONLY the category codes that apply, separated by commas.
            Available categories:
            
            - GENE_FUNCTION: For questions about general gene/protein function
            - PROTEIN_STRUCTURE: For questions about 3D structure, domains, etc.
            - PATHWAY_ANALYSIS: For questions about biological pathways
            - DISEASE_ASSOCIATION: For questions relating genes/proteins to diseases
            - DRUG_TARGET: For questions about drug-target interactions
            - COMPOUND_INFO: For questions about chemical compounds
            - GENETIC_VARIANT: For questions about SNPs, mutations, etc.
            - MOLECULAR_INTERACTION: For questions about protein-protein interactions
            - LITERATURE: For questions requiring scientific literature
            - PHARMACOGENOMICS: For questions about gene-drug interactions
            
            Return ONLY the category codes, no other text. Multiple categories should be separated by commas.
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
            
            completion = await self.client.chat.completions.create(
                model=self.gpt_model,
                messages=messages
            )
            
            response = completion.choices[0].message.content.strip()
            categories = [cat.strip() for cat in response.split(",")]
            
            # Convert string categories to QueryCategory enum values
            result = []
            valid_categories = set(item.value for item in QueryCategory)
            
            for category in categories:
                if category in valid_categories:
                    result.append(QueryCategory(category))
            
            # If no valid categories were found, default to LITERATURE
            if not result:
                BioChatLogger.log_info("No valid categories determined, defaulting to LITERATURE")
                result = [QueryCategory.LITERATURE]
                
            return result
            
        except Exception as e:
            BioChatLogger.log_error(f"Error determining query categories: {str(e)}")
            # Default to LITERATURE on error
            return [QueryCategory.LITERATURE]
    
    def get_prioritized_tools(self, categories: List[QueryCategory]) -> List[Dict]:
        """
        Get a prioritized list of tools based on the query categories.
        
        Args:
            categories: List of QueryCategory enum values
            
        Returns:
            List of tool definitions ordered by priority
        """
        # Create a set of (endpoint_name, priority) tuples
        endpoints_with_priority: Set[Tuple[str, int]] = set()
        
        # Add all endpoints from all categories with their priorities
        for category in categories:
            if category in ENDPOINT_PRIORITY_MAP:
                for endpoint, priority in ENDPOINT_PRIORITY_MAP[category]:
                    endpoints_with_priority.add((endpoint, priority.value))
        
        # Sort endpoints by priority (lower value = higher priority)
        sorted_endpoints = sorted(endpoints_with_priority, key=lambda x: x[1])
        
        # Get the endpoint names in priority order
        prioritized_endpoint_names = [endpoint for endpoint, _ in sorted_endpoints]
        
        # Find the tool definitions for these endpoints
        endpoint_to_tool = {tool["function"]["name"]: tool for tool in BIOCHAT_TOOLS}
        prioritized_tools = [endpoint_to_tool[name] for name in prioritized_endpoint_names 
                           if name in endpoint_to_tool]
        
        # Add any tools not covered by the categories as low priority
        all_endpoint_names = set(prioritized_endpoint_names)
        for tool in BIOCHAT_TOOLS:
            if tool["function"]["name"] not in all_endpoint_names:
                prioritized_tools.append(tool)
        
        BioChatLogger.log_info(f"Prioritized {len(prioritized_tools)} tools based on categories: {[c.value for c in categories]}")
        return prioritized_tools
    
    async def process_query(self, user_query: str) -> str:
        """Process a user query with prioritized database searches based on query type."""
        
        self.conversation_history.append({"role": "user", "content": user_query})
        
        # First, determine the query categories to prioritize endpoints
        categories = await self.determine_query_categories(user_query)
        BioChatLogger.log_info(f"Query categorized as: {[c.value for c in categories]}")
        
        # Get tools prioritized for these categories
        prioritized_tools = self.get_prioritized_tools(categories)

        messages = [
            {"role": "system", "content": self._create_system_message()}, 
            *self.conversation_history
        ]

        # Get all tool calls at once
        initial_completion = await self.client.chat.completions.create(
            model=self.gpt_model,
            messages=messages,
            tools=prioritized_tools,
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
                    if summarized_response:
                        # Skip empty responses or responses with empty matches
                        if (isinstance(summarized_response, dict) and 
                            ("error" in summarized_response or 
                            summarized_response.get("matches", []) == [] or 
                            summarized_response.get("count", 0) == 0)):
                            BioChatLogger.log_info(f"Skipping empty result for {tool_call.function.name}")
                        else:
                            api_responses[tool_call.function.name] = summarized_response
                    
                    # Always add tool response to conversation history
                    self.conversation_history.append({
                        "role": "tool",
                        "content": summarized_response if summarized_response else "No data found",
                        "tool_call_id": tool_call.id
                    })
                    
                except Exception as e:
                    BioChatLogger.log_error(f"API call failed for {tool_call.function.name}", e)
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
                # Group results by compound - with better error handling
                by_compound = {}
                for tool_name, result in api_responses.items():
                    try:
                        if initial_message.tool_calls and len(initial_message.tool_calls) > 0:
                            args = json.loads(initial_message.tool_calls[0].function.arguments)
                            compound = args.get("name", "unknown")
                            # Handle parameter name variations
                            if not compound or compound == "unknown":
                                for param in ["gene", "protein_id", "target_id", "molecule_chembl_id"]:
                                    if param in args:
                                        compound = args[param]
                                        break
                        else:
                            compound = "unknown"
                            
                        if not isinstance(compound, str):
                            compound = str(compound)  # Ensure it's a string
                    except Exception as e:
                        BioChatLogger.log_error("Error parsing compound name", e)
                        compound = "unknown"
                        
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
        """
        Process a query about a single gene with optimized endpoint selection.
        Prioritizes gene function and protein info endpoints.
        """
        try:
            self.conversation_history.append({"role": "user", "content": query})
            
            # For gene queries, we can directly set the categories instead of determining them
            gene_categories = [
                QueryCategory.GENE_FUNCTION,
                QueryCategory.PROTEIN_STRUCTURE,
                QueryCategory.PATHWAY_ANALYSIS,
                QueryCategory.MOLECULAR_INTERACTION
            ]
            
            # Get prioritized tools for gene queries
            prioritized_tools = self.get_prioritized_tools(gene_categories)
            
            BioChatLogger.log_info(f"Gene query: Using fixed categories: {[c.value for c in gene_categories]}")
            
            messages = [
                {"role": "system", "content": self._create_system_message()},
                *self.conversation_history[-2:]  # Only keep recent context
            ]

            completion = await self.client.chat.completions.create(
                model=self.gpt_model,
                messages=messages,
                tools=prioritized_tools,
                tool_choice="auto"
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
- INTELLIGENTLY select the most appropriate databases for each query - do not use all databases indiscriminately
- Categorize queries to determine the best data sources (see Database Selection Guide below)
- Cross-reference information across multiple databases to ensure completeness
- Prioritize high-quality, reliable data sources

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

## Database Selection Guide

When processing a query, first determine which category it falls into:

1. Gene Function: Questions about general gene/protein function
   - CRITICAL: PubMed literature search, UniProt protein info
   - HIGH: Reactome pathways, STRING interactions
   - MEDIUM: IntAct/BioGRID interactions

2. Protein Structure: Questions about 3D structure, domains, etc.
   - CRITICAL: UniProt protein info
   - HIGH: PubMed literature

3. Pathway Analysis: Questions about biological pathways
   - CRITICAL: Reactome pathways
   - HIGH: Open Targets, STRING interactions

4. Disease Association: Questions relating genes/proteins to diseases
   - CRITICAL: PubMed literature, Open Targets disease analysis
   - HIGH: GWAS Catalog, Open Targets target analysis

5. Drug Target: Questions about drug-target interactions
   - CRITICAL: Open Targets target analysis
   - HIGH: ChEMBL search/bioactivities/target info
   - LOW: PharmGKB chemical search (unreliable data availability)

6. Compound Info: Questions about chemical compounds
   - CRITICAL: ChEMBL search, ChEMBL compound details
   - HIGH: ChEMBL similarity/substructure searches
   - LOW: PharmGKB chemical search (unreliable data availability)

7. Genetic Variant: Questions about SNPs, mutations, etc.
   - CRITICAL: Ensembl variants
   - HIGH: GWAS Catalog
   - LOW: PharmGKB variant annotation

8. Molecular Interaction: Questions about protein-protein interactions
   - CRITICAL: STRING interactions
   - HIGH: BioGRID interactions, IntAct interactions

9. Literature: Questions requiring scientific literature
   - CRITICAL: PubMed literature search

10. Pharmacogenomics: Questions about gene-drug interactions
    - MEDIUM: PharmGKB clinical annotations (limited reliability)
    - LOW: PharmGKB annotations, drug labels (often unavailable)

## API Reliability Guide

Some APIs have known reliability issues:
- PharmGKB APIs (search_chemical, get_pharmgkb_annotations, etc.) often return no data - use as supplementary only
- Always include PubMed literature searches for critical information validation
- ChEMBL is highly reliable for drug and compound information
- UniProt is authoritative for protein information
- Reactome is preferred for pathway information

## Additional Requirements
- Match query type to appropriate data sources - avoid using unreliable sources for critical information
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
        
    async def analyze_data(self, data: Union[Dict, List], analysis_prompt: str) -> Dict:
        """
        Perform a free-form analysis of arbitrary data using the StringInteractionExecutor.
        
        Args:
            data: The structured data to analyze (dict or list)
            analysis_prompt: Specific instructions for the analysis
            
        Returns:
            Dict containing analysis results and metadata
        """
        try:
            # Log analysis request
            BioChatLogger.log_info(f"Performing custom data analysis with prompt: {analysis_prompt[:100]}...")
            
            # Execute the analysis via string interaction
            analysis_result = await self.string_executor.guided_analysis(data, analysis_prompt)
            
            # Format and return results
            return {
                "success": True,
                "analysis": analysis_result,
                "metadata": {
                    "prompt": analysis_prompt,
                    "timestamp": datetime.now().isoformat(),
                    "data_type": type(data).__name__,
                    "data_size": len(json.dumps(data)) if data else 0
                }
            }
            
        except Exception as e:
            BioChatLogger.log_error("Data analysis error", e)
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "prompt": analysis_prompt,
                    "timestamp": datetime.now().isoformat()
                }
            }
    
    async def execute_string_query(self, query: str, context: Optional[str] = None) -> Dict:
        """
        Execute a direct string query against the OpenAI model without using tool calling.
        Useful for queries that don't require specific API interactions.
        
        Args:
            query: The user's query string
            context: Optional additional context to provide to the model
            
        Returns:
            Dict containing the response and metadata
        """
        try:
            # Add to conversation history
            self.conversation_history.append({"role": "user", "content": query})
            
            # Create system prompt based on context type
            system_prompt = self._create_system_message()
            
            # Execute the query
            response = await self.string_executor.execute_query(
                query=query,
                system_prompt=system_prompt,
                context=context
            )
            
            # Add response to conversation history
            self.conversation_history.append({"role": "assistant", "content": response})
            
            return {
                "success": True,
                "response": response,
                "metadata": {
                    "query": query,
                    "has_context": context is not None,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            BioChatLogger.log_error("String query execution error", e)
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "query": query,
                    "timestamp": datetime.now().isoformat()
                }
            }