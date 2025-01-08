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
            messages = [
                {"role": "system", "content": self._create_system_message()},
                {"role": "user", "content": user_query}
            ]

            # Get initial response from ChatGPT
            completion = await self.client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=messages,
                tools=BIOCHAT_TOOLS,
                tool_choice="auto"
            )

            assistant_message = completion.choices[0].message

            # Add assistant's message to conversation history
            self.conversation_history.append({"role": "user", "content": user_query})
            
            # Handle tool calls if present
            if assistant_message.tool_calls:
                # Add assistant's message with tool calls
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "function": {"name": tool_call.function.name, "arguments": tool_call.function.arguments},
                            "type": "function"
                        }
                        for tool_call in assistant_message.tool_calls
                    ]
                })

                # Execute each tool call and add responses
                for tool_call in assistant_message.tool_calls:
                    function_response = await self.tool_executor.execute_tool(tool_call)
                    self.conversation_history.append({
                        "role": "tool",
                        "content": json.dumps(function_response),
                        "tool_call_id": tool_call.id
                    })

                # Get final response
                messages.extend(self.conversation_history[-3:])  # Add tool interaction messages
                final_completion = await self.client.chat.completions.create(
                    model="gpt-4-0125-preview",
                    messages=messages
                )

                final_message = final_completion.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": final_message})
                return final_message

            # If no tool calls, return direct response
            direct_response = assistant_message.content
            self.conversation_history.append({"role": "assistant", "content": direct_response})
            return direct_response

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            error_message = f"An error occurred: {str(e)}"
            self.conversation_history.append({"role": "assistant", "content": error_message})
            return error_message

    def get_conversation_history(self) -> List[Dict]:
        """Return the conversation history"""
        return self.conversation_history

    def clear_conversation_history(self) -> None:
        """Clear the conversation history"""
        self.conversation_history = []