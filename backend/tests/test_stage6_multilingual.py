"""
NEXORA AI — Automated Test Suite for Stage 6: Universal Multilingual Intelligence Engine
Tests:
1. Script & Language Detection (Tamil, Hindi, Telugu, Arabic, English)
2. Code-Switching Detection (Tanglish, Hinglish)
3. Multilingual Translation API with tone control & sentence pairs
4. Language list endpoint
5. Chat with multilingual target language directives
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.multilingual.detector import LanguageDetector
from app.services.multilingual.translator import translation_engine
from app.models.schemas import TranslationRequest


@pytest.fixture
def client():
    return TestClient(app)


def test_native_indic_script_detection():
    # Tamil
    ta_res = LanguageDetector.detect_language("வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?")
    assert ta_res.detected_language_code == "ta"
    assert ta_res.detected_language_name == "Tamil"
    assert ta_res.script == "Tamil"

    # Hindi (Devanagari)
    hi_res = LanguageDetector.detect_language("नमस्ते, आप कैसे हैं? भारत एक महान देश है।")
    assert hi_res.detected_language_code == "hi"
    assert hi_res.script == "Devanagari"

    # Telugu
    te_res = LanguageDetector.detect_language("నమస్కారం, మీరు ఎలా ఉన్నారు?")
    assert te_res.detected_language_code == "te"
    assert te_res.script == "Telugu"

    # Arabic (RTL)
    ar_res = LanguageDetector.detect_language("مرحبا كيف حالك اليوم؟")
    assert ar_res.detected_language_code == "ar"
    assert ar_res.script == "Arabic"


def test_code_switching_tanglish_and_hinglish():
    # Tanglish in Latin characters
    tanglish = "Vanakkam nanba, epdi irukinga? Nalla irukkeenga nu ninaikiren."
    t_res = LanguageDetector.detect_language(tanglish)
    assert t_res.detected_language_code == "ta"
    assert t_res.is_mixed_or_code_switched is True
    assert "Tanglish" in t_res.detected_language_name

    # Hinglish in Latin characters
    hinglish = "Namaste bhai, kya kar rahe ho? Sab theek hai na?"
    h_res = LanguageDetector.detect_language(hinglish)
    assert h_res.detected_language_code == "hi"
    assert h_res.is_mixed_or_code_switched is True
    assert "Hinglish" in h_res.detected_language_name


def test_languages_catalog_endpoint(client):
    response = client.get("/api/v1/multilingual/languages")
    assert response.status_code == 200
    data = response.json()
    assert "supported_languages" in data
    codes = [l["code"] for l in data["supported_languages"]]
    assert "ta" in codes
    assert "hi" in codes
    assert "te" in codes
    assert "en" in codes


def test_detect_endpoint(client):
    res = client.post(
        "/api/v1/multilingual/detect",
        json={"text": "Bonjour, comment ça va aujourd'hui?"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_language_code"] in ["fr", "en"]


@pytest.mark.asyncio
async def test_translation_engine():
    req = TranslationRequest(
        text="The artificial intelligence assistant analyzes documents efficiently.",
        source_language="en",
        target_language="ta",
        tone="formal"
    )
    res = await translation_engine.translate(req)
    assert res.target_language in ["Tamil", "TA"]
    assert res.tone == "formal"
    assert len(res.translated_text) > 0


def test_chat_with_multilingual_target(client):
    response = client.post(
        "/api/v1/chat",
        json={
            "messages": [{"id": "m1", "role": "user", "content": "Tell me about quantum computing"}],
            "target_language": "ta"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "assistant"
