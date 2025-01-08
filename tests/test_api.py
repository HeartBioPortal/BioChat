import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
from src.api import app, get_orchestrator

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def mock_env_vars():
    with patch.dict('os.environ', {
        'OPENAI_API_KEY': 'mock_openai_key',
        'NCBI_API_KEY': 'mock_ncbi_key',
        'CONTACT_EMAIL': 'test@example.com'
    }):
        yield

@pytest.fixture
def mocked_dependencies(mock_orchestrator, mock_env_vars):
    """Combine all mocked dependencies"""
    with patch('src.api.get_orchestrator', return_value=mock_orchestrator):
        yield

def test_health_check(test_client, mocked_dependencies):
    """Test the health check endpoint"""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "services" in data

@pytest.mark.asyncio
async def test_query_endpoint_success(test_client, mocked_dependencies):
    """Test successful query processing"""
    response = test_client.post(
        "/query",
        json={"text": "What is DNA?"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "timestamp" in data

def test_query_endpoint_validation(test_client, mocked_dependencies):
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

@pytest.mark.asyncio
async def test_query_endpoint_error(test_client, mocked_dependencies, mock_orchestrator):
    """Test error handling in query endpoint"""
    mock_orchestrator.process_query = AsyncMock(side_effect=Exception("Test error"))
    
    response = test_client.post(
        "/query",
        json={"text": "What is DNA?"}
    )
    
    assert response.status_code == 500
    data = response.json()
    assert "error" in str(data["detail"])

def test_conversation_history_endpoint(test_client, mocked_dependencies):
    """Test retrieving conversation history"""
    response = test_client.get("/history")
    
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data

def test_conversation_history_error(test_client, mocked_dependencies, mock_orchestrator):
    """Test error handling in history endpoint"""
    mock_orchestrator.get_conversation_history = Mock(side_effect=Exception("Test error"))
    
    response = test_client.get("/history")
    
    assert response.status_code == 500
    assert "error" in str(response.json()["detail"])

def test_clear_history_endpoint(test_client, mocked_dependencies):
    """Test clearing conversation history"""
    response = test_client.post("/clear")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "timestamp" in data

def test_clear_history_error(test_client, mocked_dependencies, mock_orchestrator):
    """Test error handling in clear history endpoint"""
    mock_orchestrator.clear_conversation_history = Mock(side_effect=Exception("Test error"))
    
    response = test_client.post("/clear")
    
    assert response.status_code == 500
    assert "error" in str(response.json()["detail"])

def test_missing_environment_variables(test_client):
    """Test API behavior when environment variables are missing"""
    with patch.dict('os.environ', {}, clear=True):
        response = test_client.post(
            "/query",
            json={"text": "Test query"}
        )
        assert response.status_code == 500
        assert "Missing required environment variables" in str(response.json()["detail"])

def test_cors_headers(test_client, mocked_dependencies):
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