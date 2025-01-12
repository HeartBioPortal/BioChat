from typing import List, Dict, Optional
import json
from openai import AsyncOpenAI
from src.schemas import BIOCHAT_TOOLS
from src.tool_executor import ToolExecutor
import logging

logger = logging.getLogger(__name__)

class BioChatOrchestrator:
    def __init__(self, openai_api_key: str, ncbi_api_key: str, tool_name: str, email: str):
        """Initialize the BioChat orchestrator with required credentials"""
        if not openai_api_key or not ncbi_api_key or not email:
            raise ValueError("All required credentials must be provided")
            
        try:
            self.client = AsyncOpenAI(api_key=openai_api_key)
            self.tool_executor = ToolExecutor(
                ncbi_api_key=ncbi_api_key,
                tool_name=tool_name,
                email=email
            )
            self.conversation_history = []
        except Exception as e:
            raise ValueError(f"Failed to initialize services: {str(e)}")

    def _create_system_message(self) -> str:
        """Create the system message that guides the model's behavior"""
        return """You are BioChat, an AI assistant specialized in biological and medical research. Your role is to:
1. Understand user queries about biological/medical topics
2. Use the appropriate database APIs to fetch relevant information
3. Synthesize and explain the information in a clear, scientific manner

Guidelines for using tools:
- Use search_literature when users ask about research papers, studies, or scientific findings
- Use search_variants for questions about genetic variations or mutations
- Use search_gwas when users ask about genetic associations with diseases
- Use get_protein_info for queries about protein structure and function

Always provide accurate scientific information and cite sources when possible."""

    async def process_query(self, user_query: str) -> str:
        """Process a user query through the ChatGPT model and execute necessary database queries"""
        try:
            # Format the query for tool calls
            if "treatment" in user_query.lower() or "therapy" in user_query.lower():
                search_params = {
                    "genes": [],
                    "phenotypes": [p for p in ["myocardial infarction", "heart attack"] if p in user_query.lower()],
                    "additional_terms": ["treatment", "therapy", "management"],
                    "max_results": 5
                }
            else:
                search_params = None
                
            # Get initial response from ChatGPT
            completion = await self.client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=[
                    {"role": "system", "content": self._create_system_message()},
                    {"role": "user", "content": user_query}
                ],
                tools=BIOCHAT_TOOLS if search_params else None,
                tool_choice="auto" if search_params else None
            )

            # Process response and tool calls
            response_message = completion.choices[0].message
            
            if response_message.tool_calls:
                # Execute tool calls with properly formatted parameters
                function_responses = []
                for tool_call in response_message.tool_calls:
                    try:
                        function_response = await self.tool_executor.execute_tool(tool_call)
                        function_responses.append({
                            "role": "tool",
                            "content": json.dumps(function_response),
                            "tool_call_id": tool_call.id
                        })
                    except Exception as e:
                        logger.error(f"Tool execution error: {str(e)}")
                        continue

                if function_responses:
                    self.conversation_history.extend(function_responses)
                    final_completion = await self.client.chat.completions.create(
                        model="gpt-4-0125-preview",
                        messages=[
                            {"role": "system", "content": self._create_system_message()},
                            *self.conversation_history
                        ]
                    )
                    final_message = final_completion.choices[0].message.content
                    self.conversation_history.append({"role": "assistant", "content": final_message})
                    return final_message

            # Return direct response if no tool calls or if all tool calls failed
            direct_response = response_message.content
            self.conversation_history.append({"role": "assistant", "content": direct_response})
            return direct_response

        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            self.conversation_history.append({"role": "assistant", "content": error_message})
            return error_message

    def get_conversation_history(self) -> List[Dict]:
        """Return the conversation history"""
        return self.conversation_history

    def clear_conversation_history(self) -> None:
        """Clear the conversation history"""
        self.conversation_history = []