"""
NEXORA AI — Multilingual API Endpoints
Provides:
- POST /api/v1/multilingual/detect: Real-time script & language detection
- POST /api/v1/multilingual/translate: Full-text translation with sentence alignment and tone settings
- GET /api/v1/multilingual/languages: List supported language catalog
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List
from app.models.schemas import (
    LanguageDetectionResult,
    TranslationRequest,
    TranslationResponse
)
from app.services.multilingual.detector import LanguageDetector, LANGUAGE_NAMES
from app.services.multilingual.translator import translation_engine

router = APIRouter(prefix="/multilingual", tags=["Multilingual Intelligence"])


class DetectionRequest(BaseModel):
    text: str


@router.post("/detect", response_model=LanguageDetectionResult)
async def detect_language(request: DetectionRequest):
    """Detects text language, script, code-switching, and Tanglish/Hinglish patterns."""
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    return LanguageDetector.detect_language(request.text)


@router.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """Faithfully translates text with tone control, transliteration, and parallel sentence alignment."""
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text to translate cannot be empty.")
    try:
        return await translation_engine.translate(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@router.get("/languages")
async def list_languages():
    """Returns catalog of supported languages and codes."""
    return {
        "supported_languages": [
            {"code": k, "name": v} for k, v in LANGUAGE_NAMES.items()
        ]
    }
