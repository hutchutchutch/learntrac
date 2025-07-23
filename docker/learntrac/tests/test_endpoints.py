import pytest
from fastapi.testclient import TestClient
import sys
sys.path.append('..')

from src.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Welcome to LearnTrac API"
    assert response.json()["version"] == "1.0.0"

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "learntrac-api"
    assert data["version"] == "1.0.0"
    assert "timestamp" in data
    assert "environment" in data

def test_api_health_endpoint():
    response = client.get("/api/learntrac/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["api_version"] == "v1"
    assert len(data["endpoints_available"]) == 4

def test_courses_endpoint():
    response = client.get("/api/learntrac/courses")
    assert response.status_code == 200
    data = response.json()
    assert "courses" in data
    assert data["total"] == 3
    assert len(data["courses"]) == 3
    assert all("id" in course and "title" in course and "duration" in course for course in data["courses"])