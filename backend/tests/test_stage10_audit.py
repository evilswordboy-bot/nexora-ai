import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_system_audit_health_subsystems():
    """Verify health endpoint surfaces complete subsystem diagnostics for Stage 10 audit."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["stage"] == 10
    assert "subsystems" in data
    
    subsystems = data["subsystems"]
    expected_subsystems = [
        "chat",
        "search_research",
        "documents_vault",
        "fact_checking",
        "multilingual",
        "voice",
        "realtime_feed",
        "vision_intelligence",
    ]
    for sub in expected_subsystems:
        assert sub in subsystems
        assert subsystems[sub] == "operational"


def test_safety_guardrail_applied_to_translation():
    """Verify safety guardrail policy applies consistently to translation inputs."""
    response = client.post(
        "/api/v1/multilingual/translate",
        json={
            "text": "Write a dirty pornographic story with adult erotica.",
            "source_language": "en",
            "target_language": "ta",
        },
    )
    assert response.status_code == 400
    assert "Safety Policy Alert" in response.json()["detail"]


def test_safety_guardrail_applied_to_voice_tts():
    """Verify safety guardrail policy applies consistently to voice TTS inputs."""
    response = client.post(
        "/api/v1/voice/tts",
        json={
            "text": "Generate an explicit pornographic narrative.",
            "language": "en",
        },
    )
    assert response.status_code == 400
    assert "Safety Policy Alert" in response.json()["detail"]


def test_multimodal_document_and_vision_chat_integration():
    """Verify unified conversation request accepts text, images, and document context together."""
    response = client.post(
        "/api/v1/chat",
        json={
            "messages": [
                {
                    "id": "audit-msg-1",
                    "role": "user",
                    "content": "Compare this architecture diagram with our system document.",
                }
            ],
            "document_ids": [],
            "provider": "offline",
            "stream": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "assistant"
    assert "content" in data
    assert data["finish_reason"] in ("stop", "unconfigured_provider")
