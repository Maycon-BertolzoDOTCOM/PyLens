"""
Testes para a API do PyLens.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestAPI:
    """Testes para os endpoints da API."""

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "PyLens API"
        assert "endpoints" in data

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "llm" in data

    def test_analyze_code(self, client):
        response = client.post("/analyze", json={
            "code": """
def add(x, y):
    return x + y
"""
        })
        assert response.status_code == 200
        data = response.json()
        assert "static_analysis" in data
        assert "architectural" in data
        assert "code_structure" in data

    def test_analyze_with_loops(self, client):
        response = client.post("/analyze", json={
            "code": """
for i in range(100):
    for j in range(100):
        pass
"""
        })
        assert response.status_code == 200
        data = response.json()
        assert data["static_analysis"]["loops"] >= 2

    def test_report_generation(self, client):
        response = client.post("/report", json={
            "code": """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
        })
        assert response.status_code == 200
        data = response.json()
        assert "overall" in data
        assert "analyses" in data
        assert "insights" in data
