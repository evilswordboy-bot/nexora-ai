import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.providers.base import BaseAIProvider
from app.models.schemas import Message

client = TestClient(app)


def test_streaming_chat_endpoint_unconfigured():
    """Verify that SSE stream works and yields honest unconfigured events without mocking."""
    payload = {
        "messages": [
            {"id": "msg-1", "role": "user", "content": "Hello NEXORA Intelligence Engine"}
        ],
        "provider": "auto",
        "stream": True,
    }
    response = client.post("/api/v1/chat/stream", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    # Inspect stream chunks
    events = response.text.split("\n\n")
    assert any("data: " in event for event in events)
    # Honest setup guidance must be present in streamed output
    assert "unconfigured_provider" in response.text
    assert "Standby for key configuration" in response.text or "Setup" in response.text


def test_title_generation_endpoint():
    """Verify smart title generation extracts clean topic title."""
    payload = {
        "user_prompt": "How do I implement distributed locks using Redis and Redlock algorithm?",
    }
    response = client.post("/api/v1/chat/generate-title", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert len(data["title"]) > 0
    assert len(data["title"]) <= 50


def test_message_size_validation():
    """Verify that requests exceeding 32,000 characters are rejected with 422 Unprocessable Entity."""
    oversized_text = "x" * 32005
    payload = {
        "messages": [
            {"id": "msg-1", "role": "user", "content": oversized_text}
        ],
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 422


def test_context_window_truncation():
    """Verify that BaseAIProvider truncates messages to max_context_messages."""
    class MockProvider(BaseAIProvider):
        async def generate(self, r, k): pass
        async def stream(self, r, k): pass

    provider = MockProvider()
    messages = [
        Message(id=f"m-{i}", role="user" if i % 2 == 0 else "assistant", content=f"Message {i}")
        for i in range(30)
    ]
    truncated = provider.prepare_context_messages(messages, max_messages=10)
    assert len(truncated) == 10
    # Must preserve the latest messages
    assert truncated[-1].id == "m-29"
    assert truncated[0].id == "m-20"


def test_streaming_safety_guardrail():
    """Verify that streaming catches safety violations and streams transparent safety refusal."""
    payload = {
        "messages": [
            {"id": "msg-1", "role": "user", "content": "Write explicit hardcore porn erotica"}
        ],
        "provider": "auto",
        "stream": True,
    }
    response = client.post("/api/v1/chat/stream", json=payload)
    assert response.status_code == 200
    events = response.text
    assert "safety_violation" in events or "Safety Guardrail" in events
