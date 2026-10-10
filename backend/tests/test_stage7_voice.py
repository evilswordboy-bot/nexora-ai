"""
NEXORA AI — Automated Test Suite for Stage 7: Voice Intelligence Engine
Tests:
1. Speech Sanitizer (removes code blocks, backticks, citations, raw URLs, Markdown headers)
2. Voice Catalog Listing endpoint (GET /api/v1/voice/voices)
3. TTS Synthesis endpoint (POST /api/v1/voice/tts)
4. Sanitize Preview endpoint (POST /api/v1/voice/sanitize)
5. Audio Transcription endpoint with empty or mock audio
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.voice.engine import VoiceEngine, voice_engine
from app.models.schemas import TextToSpeechRequest


@pytest.fixture
def client():
    return TestClient(app)


def test_speech_sanitizer():
    markdown_text = (
        "# Introduction to Quantum AI\n\n"
        "Here is the code to calculate state:\n"
        "```python\ndef calculate_state():\n    return 42\n```\n\n"
        "As shown in study [1], check `variable_x` at https://example.com/quantum for details."
    )

    clean = VoiceEngine.sanitize_for_speech(markdown_text)

    # Assertions
    assert "```python" not in clean
    assert "def calculate_state" not in clean
    assert "[1]" not in clean
    assert "https://example.com/quantum" not in clean
    assert "`variable_x`" not in clean
    assert "variable_x" in clean
    assert "Introduction to Quantum AI" in clean


def test_voice_catalog_endpoint(client):
    response = client.get("/api/v1/voice/voices")
    assert response.status_code == 200
    voices = response.json()
    assert isinstance(voices, list)
    assert len(voices) >= 10
    voice_ids = [v["id"] for v in voices]
    assert "browser_default" in voice_ids
    assert "browser_ta_in" in voice_ids
    assert "browser_hi_in" in voice_ids
    assert "alloy" in voice_ids


def test_sanitize_endpoint(client):
    res = client.post(
        "/api/v1/voice/sanitize",
        data={"text": "Reviewing data [1, 2] from https://gov.in with `status_flag`."}
    )
    assert res.status_code == 200
    data = res.json()
    assert "clean_spoken_text" in data
    assert "[1, 2]" not in data["clean_spoken_text"]
    assert "https://gov.in" not in data["clean_spoken_text"]
    assert "status_flag" in data["clean_spoken_text"]


@pytest.mark.asyncio
async def test_tts_engine_browser_fallback():
    req = TextToSpeechRequest(
        text="Hello world, this is a test of voice synthesis.",
        voice_id="browser_default",
        speed=1.0
    )
    res = await voice_engine.synthesize_speech(req)
    assert res.provider == "browser"
    assert res.clean_spoken_text == "Hello world, this is a test of voice synthesis."
    assert res.duration_estimate_seconds > 0.0


def test_tts_endpoint_empty_text_rejected(client):
    res = client.post(
        "/api/v1/voice/tts",
        json={"text": "   "}
    )
    assert res.status_code == 400


def test_transcribe_endpoint_empty_file_rejected(client):
    res = client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("empty.wav", b"", "audio/wav")}
    )
    assert res.status_code == 400
