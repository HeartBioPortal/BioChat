import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
from src.api import app, get_orchestrator
from datetime import datetime

@pytest.fixture
def test_client():
    """Create a test client for the FastAPI application"""
    return TestClient(app)

@pytest.fixture
def mock_env_vars():
    """Mock environment variables required for the API"""
    with patch.dict('os.environ', {
        'OPENAI_API_KEY': 'mock_openai_key',
        'NCBI_API_KEY': 'mock_ncbi_key',
        'CONTACT_EMAIL': 'test@example.com'
    }):
        yield

@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator with predefined responses"""
    mock = Mock()
    mock.process_query = AsyncMock(return_value="Mock response")
    mock.get_conversation_history = Mock(return_value=[
        {"role": "user", "content": "Test query", "timestamp": datetime.now().isoformat()},
        {"role": "assistant", "content": "Test response", "timestamp": datetime.now().isoformat()}
    ])
    mock.clear_conversation_history = Mock()
    return mock

def test_health_check(test_client, mock_env_vars):
    """Test the health check endpoint"""
    response = test_client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
    assert "services" in data

def test_health_check_missing_env_vars(test_client):
    """Test health check when environment variables are missing"""
    with patch.dict('os.environ', {}, clear=True):
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "unhealthy"

@pytest.mark.asyncio
async def test_query_endpoint_success(test_client, mock_env_vars, mock_orchestrator):
    """Test successful query processing"""
    with patch('src.api.get_orchestrator', return_value=mock_orchestrator):
        response = test_client.post(
            "/query",
            json={"text": "What is DNA?"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "timestamp" in data
        mock_orchestrator.process_query.assert_called_once_with("What is DNA?")

def test_query_endpoint_validation(test_client, mock_env_vars):
    """Test input validation for query endpoint"""
    # Test missing required field
    response = test_client.post(
        "/query",
        json={"invalid_field": "test"}
    )
    assert response.status_code == 422
    
    # Test empty text
    response = test_client.post(
        "/query",
        json={"text": ""}
    )
    assert response.status_code == 422
    
    # Test invalid JSON
    response = test_client.post(
        "/query",
        data="invalid json"
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_query_endpoint_error(test_client, mock_env_vars, mock_orchestrator):
    """Test error handling in query endpoint"""
    mock_orchestrator.process_query.side_effect = Exception("Test error")
    
    with patch('src.api.get_orchestrator', return_value=mock_orchestrator):
        response = test_client.post(
            "/query",
            json={"text": "What is DNA?"}
        )
        
        assert response.status_code == 500
        assert "error" in response.json()

def test_conversation_history_endpoint(test_client, mock_env_vars, mock_orchestrator):
    """Test retrieving conversation history"""
    with patch('src.api.get_orchestrator', return_value=mock_orchestrator):
        response = test_client.get("/history")
        
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) == 2
        
        # Verify message structure
        message = data["messages"][0]
        assert "role" in message
        assert "content" in message
        assert "timestamp" in message

def test_conversation_history_error(test_client, mock_env_vars, mock_orchestrator):
    """Test error handling in history endpoint"""
    mock_orchestrator.get_conversation_history.side_effect = Exception("Test error")
    
    with patch('src.api.get_orchestrator', return_value=mock_orchestrator):
        response = test_client.get("/history")
        
        assert response.status_code == 500
        assert "error" in response.json()

def test_clear_history_endpoint(test_client, mock_env_vars, mock_orchestrator):
    """Test clearing conversation history"""
    with patch('src.api.get_orchestrator', return_value=mock_orchestrator):
        response = test_client.post("/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "timestamp" in data
        mock_orchestrator.clear_conversation_history.assert_called_once()

def test_clear_history_error(test_client, mock_env_vars, mock_orchestrator):
    """Test error handling in clear history endpoint"""
    mock_orchestrator.clear_conversation_history.side_effect = Exception("Test error")
    
    with patch('src.api.get_orchestrator', return_value=mock_orchestrator):
        response = test_client.post("/clear")
        
        assert response.status_code == 500
        assert "error" in response.json()

def test_missing_environment_variables(test_client):
    """Test API behavior when environment variables are missing"""
    with patch.dict('os.environ', {}, clear=True):
        response = test_client.post(
            "/query",
            json={"text": "Test query"}
        )
        assert response.status_code == 500
        assert "Missing required environment variables" in response.json()["detail"]

@pytest.mark.asyncio
async def test_orchestrator_initialization_error(test_client, mock_env_vars):
    """Test handling of orchestrator initialization errors"""
    with patch('src.api.BioChatOrchestrator', side_effect=Exception("Initialization error")):
        response = test_client.post(
            "/query",
            json={"text": "Test query"}
        )
        assert response.status_code == 500
        assert "Failed to initialize BioChat service" in response.json()["detail"]

def test_cors_headers(test_client, mock_env_vars):
    """Test CORS headers in responses"""
    response = test_client.options(
        "/query",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        }
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers
    assert "access-control-allow-headers" in response.headers