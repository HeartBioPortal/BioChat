from typing import List, Dict, Optional
import json
from openai import OpenAI
from src.schemas import BIOCHAT_TOOLS
from src.tool_executor import ToolExecutor

class BioChatOrchestrator:
    def __init__(self, openai_api_key: str, ncbi_api_key: str, tool_name: str, email: str):
        """Initialize BioChat with necessary components"""
        self.client = OpenAI(api_key=openai_api_key)
        self.tool_executor = ToolExecutor(ncbi_api_key, tool_name, email)
        self.conversation_history = []

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

Always provide accurate scientific information and cite sources when possible.
When using tools, analyze the results and provide a clear, comprehensive explanation to the user."""

    async def process_query(self, user_query: str) -> str:
        """Process a user query through the ChatGPT model and execute necessary database queries"""
        # Add user query to conversation history
        self.conversation_history.append({"role": "user", "content": user_query})

        try:
            # Get initial response from ChatGPT
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": self._create_system_message()},
                    *self.conversation_history
                ],
                tools=BIOCHAT_TOOLS,
                tool_choice="auto"
            )

            message = response.choices[0].message

            # Check if the model wants to call functions
            if message.tool_calls:
                # Execute each tool call
                for tool_call in message.tool_calls:
                    function_response = await self.tool_executor.execute_tool(tool_call)

                    # Add function response to conversation history
                    self.conversation_history.append({
                        "role": "tool",
                        "content": json.dumps(function_response),
                        "tool_call_id": tool_call.id
                    })

                # Get final response from ChatGPT
                final_response = await self.client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": self._create_system_message()},
                        *self.conversation_history
                    ]
                )

                final_message = final_response.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": final_message})
                return final_message

            # If no function call needed, return the direct response
            self.conversation_history.append({"role": "assistant", "content": message.content})
            return message.content

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