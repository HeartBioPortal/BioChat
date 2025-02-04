import logging
import os
from datetime import datetime
from typing import Dict, List

class TestLogger:
    def __init__(self):
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

        # Set up file logger
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicate logging
        self.logger.handlers = []

        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(logs_dir, f"test_conversation_{timestamp}.log")
        
        # Configure file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def log_conversation(self, test_name: str, query: str, response: str, conversation_history: List[Dict]):
        """Log a complete test conversation with formatting"""
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"Test: {test_name}")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Query: {query}")
        # self.logger.info(f"Response: {response}")
        self.logger.info("\nFull Conversation History:")
        
        for msg in conversation_history:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            tool_calls = msg.get('tool_calls', [])
            
            if role == 'tool':
                self.logger.info(f"\nTool Response:")
                self.logger.info(f"{content}")
            elif tool_calls:
                self.logger.info(f"\n{role.capitalize()} (with tool calls):")
                self.logger.info(f"Message: {content}")
                for tool_call in tool_calls:
                    self.logger.info(f"Tool Call: {tool_call}")
            else:
                self.logger.info(f"\n{role.capitalize()}:")
                self.logger.info(f"{content}")
        
        self.logger.info(f"\n{'='*80}\n")

# Create a singleton instance
test_logger = TestLogger()