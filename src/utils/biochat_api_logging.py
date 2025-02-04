import logging
import json
from datetime import datetime

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("biochat_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BioChatLogger")

class BioChatLogger:
    @staticmethod
    def log_api_request(endpoint: str, params: dict):
        logger.info(json.dumps({
            "event": "API Request",
            "endpoint": endpoint,
            "params": params,
            "timestamp": datetime.now().isoformat()
        }, indent=4))

    @staticmethod
    def log_api_response(endpoint: str, response: dict, success: bool):
        logger.info(json.dumps({
            "event": "API Response",
            "endpoint": endpoint,
            "success": success,
            "response_summary": json.dumps(response, indent=4)[:500] if response else "N/A",
            "timestamp": datetime.now().isoformat()
        }, indent=4))

    @staticmethod
    def log_error(message: str, exception: Exception):
        logger.error(json.dumps({
            "event": "Error",
            "message": message,
            "exception": str(exception),
            "timestamp": datetime.now().isoformat()
        }, indent=4))

    @staticmethod
    def log_tool_execution(tool_name: str, arguments: dict, success: bool, response: dict = None):
        logger.info(json.dumps({
            "event": "Tool Execution",
            "tool_name": tool_name,
            "arguments": arguments,
            "success": success,
            "response_summary": json.dumps(response, indent=4)[:500] if response else "N/A",
            "timestamp": datetime.now().isoformat()
        }, indent=4))

    @staticmethod
    def log_test_case(test_name: str, query: str, response: str, history: list):
        logger.info(json.dumps({
            "event": "Test Case Execution",
            "test_name": test_name,
            "query": query,
            "response": response[:500],
            "history_length": len(history),
            "timestamp": datetime.now().isoformat()
        }, indent=4))

    @staticmethod
    def log_info(message: str):
        """Logs a simple info message."""
        logger.info(json.dumps({
            "event": "Info",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }, indent=4))
