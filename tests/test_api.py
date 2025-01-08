import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
from src.api import app, get_orchestrator
from datetime import datetime

def get_test_orchestrator():
    return Mock()

app.dependency_overrides[get_orchestrator] = get_test_orchestrator

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def mock_orchestrator():
    """Create a fresh mock orchestrator for each test"""
    mock = Mock()
    # Configure default async method for process_query
    mock.process_query = AsyncMock()
    app.dependency_overrides[get_orchestrator] = lambda: mock
    yield mock
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_query_endpoint_success(test_client, mock_orchestrator):
    """Test successful query processing"""
    expected_response = "Test response"
    mock_orchestrator.process_query.return_value = expected_response
    
    response = test_client.post(
        "/query",
        json={"text": "What is DNA?"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["response"] == expected_response
    assert "timestamp" in data

def test_query_endpoint_validation(test_client, mock_orchestrator):
    """Test input validation for query endpoint"""
    response = test_client.post(
        "/query",
        json={"invalid_field": "test"}
    )
    assert response.status_code == 422
    
    response = test_client.post(
        "/query",
        json={"text": ""}
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_query_endpoint_error(test_client, mock_orchestrator):
    """Test error handling in query endpoint"""
    mock_orchestrator.process_query.side_effect = Exception("Test error")
    
    response = test_client.post(
        "/query",
        json={"text": "What is DNA?"}
    )
    
    assert response.status_code == 500
    assert "Test error" in response.json()["detail"]

def test_conversation_history_endpoint(test_client, mock_orchestrator):
    """Test retrieving conversation history"""
    mock_history = [
        {"role": "user", "content": "Test question", "timestamp": datetime.now().isoformat()},
        {"role": "assistant", "content": "Test answer", "timestamp": datetime.now().isoformat()}
    ]
    mock_orchestrator.get_conversation_history.return_value = mock_history
    
    response = test_client.get("/history")
    
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert len(data["messages"]) == len(mock_history)

def test_conversation_history_error(test_client, mock_orchestrator):
    """Test error handling in history endpoint"""
    mock_orchestrator.get_conversation_history.side_effect = Exception("Test error")
    
    response = test_client.get("/history")
    
    assert response.status_code == 500
    assert "Test error" in response.json()["detail"]

def test_clear_history_endpoint(test_client, mock_orchestrator):
    """Test clearing conversation history"""
    response = test_client.post("/clear")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "timestamp" in data
    mock_orchestrator.clear_conversation_history.assert_called_once()

def test_clear_history_error(test_client, mock_orchestrator):
    """Test error handling in clear history endpoint"""
    mock_orchestrator.clear_conversation_history.side_effect = Exception("Test error")
    
    response = test_client.post("/clear")
    
    assert response.status_code == 500
    assert "Test error" in response.json()["detail"]

def test_missing_environment_variables(test_client):
    """Test API behavior when environment variables are missing"""
    def mock_get_orchestrator_with_error():
        orchestrator = Mock()
        orchestrator.process_query = AsyncMock(side_effect=ValueError("Missing required environment variables"))
        return orchestrator

    try:
        app.dependency_overrides[get_orchestrator] = mock_get_orchestrator_with_error
        response = test_client.post(
            "/query",
            json={"text": "Test query"}
        )
        assert response.status_code == 500
        assert "Missing required environment variables" in response.json()["detail"]
    finally:
        app.dependency_overrides = {}

def test_cors_headers(test_client, mock_orchestrator):
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