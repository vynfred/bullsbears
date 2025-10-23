"""
Tests for the main FastAPI application.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "Options Trading Analyzer" in data["message"]


def test_health_check():
    """Test the basic health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
    assert "service" in data


@patch('app.main.redis_client')
@patch('app.main.engine')
def test_detailed_health_check(mock_engine, mock_redis):
    """Test the detailed health check endpoint."""
    # Mock Redis ping
    mock_redis.client.ping = AsyncMock()
    
    # Mock database connection
    mock_conn = AsyncMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = None
    
    response = client.get("/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "dependencies" in data
    assert "redis" in data["dependencies"]
    assert "database" in data["dependencies"]


def test_cors_headers():
    """Test that CORS headers are properly set."""
    response = client.options("/health")
    assert response.status_code == 200


def test_process_time_header():
    """Test that process time header is added."""
    response = client.get("/health")
    assert "X-Process-Time" in response.headers
    assert float(response.headers["X-Process-Time"]) >= 0
