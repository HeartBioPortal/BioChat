from typing import List, Dict, Optional
import json
from openai import AsyncOpenAI
from src.schemas import BIOCHAT_TOOLS
from src.tool_executor import ToolExecutor
import logging

logger = logging.getLogger(__name__)

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

    async def process_query(self, user_query: str) -> str:
        """Process a user query through the ChatGPT model and execute necessary database queries"""
        try:
            # Break down complex queries if needed
            if self._is_complex_gene_query(user_query):
                return await self._handle_complex_gene_query(user_query)
                
            # Original process_query logic for simple queries...
            self.conversation_history.append({"role": "user", "content": user_query})
            
            messages = [
                {"role": "system", "content": self._create_system_message()},
                *self.conversation_history
            ]

            try:
                initial_completion = await self.client.chat.completions.create(
                    model="gpt-4-0125-preview",
                    messages=messages,
                    tools=BIOCHAT_TOOLS,
                    tool_choice="auto",
                    max_tokens=4096  # Add token limit
                )

                initial_message = initial_completion.choices[0].message
            except:
                raise

            # Handle tool calls if present
            if hasattr(initial_message, 'tool_calls') and initial_message.tool_calls:
                # Add assistant's message with tool calls to conversation history
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

                # Execute each tool call
                for tool_call in initial_message.tool_calls:
                    try:
                        function_response = await self.tool_executor.execute_tool(tool_call)
                        self.conversation_history.append({
                            "role": "tool",
                            "content": json.dumps(function_response),
                            "tool_call_id": tool_call.id
                        })
                    except Exception as e:
                        logger.error(f"Tool execution error: {str(e)}", exc_info=True)
                        # Add error message as tool response
                        self.conversation_history.append({
                            "role": "tool",
                            "content": json.dumps({"error": str(e)}),
                            "tool_call_id": tool_call.id
                        })

                # Get final response with updated conversation history
                messages = [
                    {"role": "system", "content": self._create_system_message()},
                    *self.conversation_history
                ]
                
                final_completion = await self.client.chat.completions.create(
                    model="gpt-4-0125-preview",  # Fixed model name
                    messages=messages
                )

                final_message = final_completion.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": final_message})
                return final_message

            else:
                # Handle case where no tool calls are made
                direct_response = initial_message.content or "I apologize, but I couldn't generate a response. Please try rephrasing your question."
                self.conversation_history.append({"role": "assistant", "content": direct_response})
                return direct_response

        except Exception as e:
            logger.error(f"Query processing error: {str(e)}", exc_info=True)
            error_message = f"An error occurred: {str(e)}"
            self.conversation_history.append({"role": "assistant", "content": error_message})
            return error_message
    
    def _is_complex_gene_query(self, query: str) -> bool:
            """Check if query involves multiple genes"""
            # Simple heuristic - count gene symbols
            common_genes = ["BRCA1", "BRCA2", "TP53", "DSP", "PCSK9"]
            mentioned_genes = [gene for gene in common_genes if gene in query]
            return len(mentioned_genes) > 2

    async def _handle_complex_gene_query(self, query: str) -> str:
        """Handle queries involving multiple genes by breaking them down"""
        common_genes = ["BRCA1", "BRCA2", "TP53", "DSP", "PCSK9"]
        mentioned_genes = [gene for gene in common_genes if gene in query]
        
        responses = []
        for gene in mentioned_genes:
            # Process each gene separately
            sub_query = f"What is known about {gene} in the context of {query}?"
            response = await self.process_single_gene_query(sub_query)
            responses.append(response)
            
        # Synthesize responses
        combined = "Analysis of multiple genes:\n\n"
        for gene, response in zip(mentioned_genes, responses):
            combined += f"\n### {gene}:\n{response}\n"
            
        return combined

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
                model="gpt-4-0125-preview",
                messages=messages,
                tools=BIOCHAT_TOOLS,
                tool_choice="auto",
                max_tokens=2048  # Smaller token limit for sub-queries
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in single gene query: {str(e)}")
            return f"Error processing query for gene: {str(e)}"
    

    def _create_system_message(self) -> str:
        """Create the system message that guides the model's behavior"""
        return """You are BioChat, an AI assistant specialized in biological and medical research. Your role is to:
1. Understand user queries about biological/medical topics
2. Use the appropriate database APIs to fetch relevant information
3. Synthesize and explain the information in a clear, scientific manner
4. give precise citations based on the API's you use for any information you provide

Always aim to provide accurate, up-to-date scientific information with appropriate citations.
When using tools, analyze the results carefully and provide comprehensive, well-structured responses."""

    def get_conversation_history(self) -> List[Dict]:
        """Return the conversation history"""
        return self.conversation_history

    def clear_conversation_history(self) -> None:
        """Clear the conversation history"""
        self.conversation_history = []