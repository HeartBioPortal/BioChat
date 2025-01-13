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
                email=email,
                api_keys={}
            )
            self.conversation_history = []
        except Exception as e:
            raise ValueError(f"Failed to initialize services: {str(e)}")

    async def process_query(self, user_query: str) -> str:
        """Process a user query through the ChatGPT model and execute necessary database queries"""
        try:
            # Add user query to conversation history
            self.conversation_history.append({"role": "user", "content": user_query})
            
            # Initial message list includes system and user messages
            messages = [
                {"role": "system", "content": self._create_system_message()},
                {"role": "user", "content": user_query}
            ]

            # Get initial response from ChatGPT
            initial_completion = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=BIOCHAT_TOOLS,
                tool_choice="auto"
            )

            initial_message = initial_completion.choices[0].message
            self.conversation_history.append({
                "role": "assistant",
                "content": initial_message.content or "",
                "tool_calls": initial_message.tool_calls or []
            })

            # Process tool calls if present
            if initial_message.tool_calls:
                tool_messages = []
                
                # Execute each tool call
                for tool_call in initial_message.tool_calls:
                    try:
                        function_response = await self.tool_executor.execute_tool(tool_call)
                        tool_messages.append({
                            "role": "tool",
                            "content": json.dumps(function_response),
                            "tool_call_id": tool_call.id
                        })
                    except Exception as e:
                        logger.error(f"Tool execution error: {str(e)}")
                
                if tool_messages:
                    # Add tool messages to both conversation history and messages for next completion
                    self.conversation_history.extend(tool_messages)
                    messages.extend([self.conversation_history[-2]])  # Add assistant message with tool calls
                    messages.extend(tool_messages)

                    # Get final response
                    final_completion = await self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages
                    )

                    final_message = final_completion.choices[0].message.content
                    self.conversation_history.append({"role": "assistant", "content": final_message})
                    return final_message

            # Return initial response if no tool calls were made
            return initial_message.content or "I apologize, but I couldn't generate a response. Please try rephrasing your question."

        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            self.conversation_history.append({"role": "assistant", "content": error_message})
            return error_message

    def _create_system_message(self) -> str:
        """Create the system message that guides the model's behavior"""
        return """You are BioChat, an AI assistant specialized in biological and medical research. Your role is to:
1. Understand user queries about biological/medical topics
2. Use the appropriate database APIs to fetch relevant information
3. Synthesize and explain the information in a clear, scientific manner

Always aim to provide accurate, up-to-date scientific information with appropriate citations.
When using tools, analyze the results carefully and provide comprehensive, well-structured responses."""

    def get_conversation_history(self) -> List[Dict]:
        """Return the conversation history"""
        return self.conversation_history

    def clear_conversation_history(self) -> None:
        """Clear the conversation history"""
        self.conversation_history = []