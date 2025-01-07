from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from src.orchestrator import BioChatOrchestrator
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="BioChat API",
    description="API for interacting with biological databases through natural language",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation
class Query(BaseModel):
    text: str = Field(..., description="The user's natural language query")

class Message(BaseModel):
    role: str = Field(..., description="The role of the message sender (user, assistant, or tool)")
    content: str = Field(..., description="The content of the message")
    tool_call_id: Optional[str] = Field(None, description="ID of the tool call if this is a tool response")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the message")

class ConversationHistory(BaseModel):
    messages: List[Message] = Field(..., description="List of conversation messages")

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    timestamp: datetime = Field(default_factory=datetime.now)

# Global orchestrator instance
orchestrator: Optional[BioChatOrchestrator] = None

def get_orchestrator() -> BioChatOrchestrator:
    """
    Dependency to get or create the BioChatOrchestrator instance.
    Ensures environment variables are properly configured.
    """
    global orchestrator
    if orchestrator is None:
        required_env_vars = {
            "OPENAI_API_KEY": "OpenAI API key",
            "NCBI_API_KEY": "NCBI API key",
            "CONTACT_EMAIL": "Contact email for API access"
        }
        
        missing_vars = {
            var: desc for var, desc in required_env_vars.items() 
            if not os.getenv(var)
        }
        
        if missing_vars:
            error_msg = "Missing required environment variables:\n" + \
                       "\n".join([f"- {desc} ({var})" for var, desc in missing_vars.items()])
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
            
        try:
            orchestrator = BioChatOrchestrator(
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                ncbi_api_key=os.getenv("NCBI_API_KEY"),
                tool_name="BioChat",
                email=os.getenv("CONTACT_EMAIL")
            )
            logger.info("BioChatOrchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize BioChatOrchestrator: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize BioChat service"
            )
    
    return orchestrator

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred", "timestamp": datetime.now().isoformat()}
    )

@app.post("/query")
async def process_query(
    query: Query,
    orchestrator: BioChatOrchestrator = Depends(get_orchestrator)
) -> Dict:
    """
    Process a natural language query about biological or medical topics.
    Returns a response generated using various biological databases and AI analysis.
    """
    logger.info(f"Received query: {query.text}")
    try:
        response = await orchestrator.process_query(query.text)
        logger.info("Query processed successfully")
        return {
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

@app.get("/history", response_model=ConversationHistory)
def get_history(
    orchestrator: BioChatOrchestrator = Depends(get_orchestrator)
) -> ConversationHistory:
    """
    Retrieve the current conversation history.
    Returns all messages exchanged in the current session.
    """
    try:
        history = orchestrator.get_conversation_history()
        messages = [
            Message(
                role=msg["role"],
                content=msg["content"],
                tool_call_id=msg.get("tool_call_id"),
                timestamp=msg.get("timestamp", datetime.now())
            )
            for msg in history
        ]
        return ConversationHistory(messages=messages)
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversation history"
        )

@app.post("/clear")
def clear_history(
    orchestrator: BioChatOrchestrator = Depends(get_orchestrator)
) -> Dict:
    """
    Clear the current conversation history.
    Removes all stored messages from the current session.
    """
    try:
        orchestrator.clear_conversation_history()
        logger.info("Conversation history cleared")
        return {
            "status": "success",
            "message": "Conversation history cleared",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing conversation history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to clear conversation history"
        )

@app.get("/health")
async def health_check() -> Dict:
    """
    Check if the API and its dependencies are functioning properly.
    Verifies the availability of required services and configurations.
    """
    try:
        # Check if we can initialize the orchestrator
        orchestrator = get_orchestrator()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": app.version,
            "services": {
                "orchestrator": "available",
                "openai": "configured",
                "ncbi": "configured"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        reload=True  # Enable auto-reload during development
    )