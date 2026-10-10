from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "NEXORA AI"
    assert data["stage"] == 1


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "configured_providers" in data


def test_providers_status_honest_state():
    response = client.get("/api/v1/providers/status")
    assert response.status_code == 200
    data = response.json()
    assert "available_providers" in data
    assert isinstance(data["available_providers"], list)
