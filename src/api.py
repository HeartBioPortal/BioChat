from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from src.orchestrator import BioChatOrchestrator
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="BioChat API",
    description="API for interacting with biological databases through natural language",
    version="1.0.0"
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
    text: str = Field(..., min_length=1, description="The user's query text")

class Message(BaseModel):
    role: str
    content: str
    tool_call_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ConversationHistory(BaseModel):
    messages: List[Message]

# Global orchestrator instance
orchestrator: Optional[BioChatOrchestrator] = None

def get_orchestrator() -> BioChatOrchestrator:
    """Dependency to get or create the BioChatOrchestrator instance"""
    global orchestrator
    if orchestrator is None:
        required_env_vars = {
            "OPENAI_API_KEY": "OpenAI API key",
            "NCBI_API_KEY": "NCBI API key",
            "CONTACT_EMAIL": "Contact email"
        }
        
        missing_vars = {
            var: desc for var, desc in required_env_vars.items() 
            if not os.getenv(var)
        }
        
        if missing_vars:
            raise HTTPException(
                status_code=500, 
                detail=f"Missing required environment variables: {', '.join(missing_vars.keys())}"
            )
            
        try:
            orchestrator = BioChatOrchestrator(
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                ncbi_api_key=os.getenv("NCBI_API_KEY"),
                tool_name="BioChat",
                email=os.getenv("CONTACT_EMAIL")
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return orchestrator

@app.post("/query")
async def process_query(
    query: Query,
    orchestrator: BioChatOrchestrator = Depends(get_orchestrator)
) -> Dict:
    """Process a natural language query"""
    try:
        if not query.text.strip():
            raise HTTPException(status_code=422, detail="Query text cannot be empty")
            
        response = await orchestrator.process_query(query.text)
        return {"response": response, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history(
    orchestrator: BioChatOrchestrator = Depends(get_orchestrator)
) -> ConversationHistory:
    """Get conversation history"""
    try:
        history = orchestrator.get_conversation_history()
        return ConversationHistory(messages=[Message(**msg) for msg in history])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear")
async def clear_history(
    orchestrator: BioChatOrchestrator = Depends(get_orchestrator)
) -> Dict:
    """Clear conversation history"""
    try:
        orchestrator.clear_conversation_history()
        return {"status": "success", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check() -> Dict:
    """Check API health status"""
    try:
        # Attempt to initialize orchestrator to verify all components
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
        log_level="info"
    )