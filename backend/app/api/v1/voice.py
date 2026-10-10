"""
NEXORA AI — Voice Intelligence API Endpoints
Provides:
- GET /api/v1/voice/voices: Catalog of honest supported voices & languages
- POST /api/v1/voice/tts: Text-to-speech audio synthesis & speech sanitizer
- POST /api/v1/voice/transcribe: Audio transcription (Whisper API / fallback)
- POST /api/v1/voice/sanitize: Speech sanitizer preview
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import Optional, List
from app.models.schemas import (
    TextToSpeechRequest,
    TextToSpeechResponse,
    VoiceInfo,
    AudioTranscriptionResponse
)
from app.services.voice.engine import voice_engine

router = APIRouter(prefix="/voice", tags=["Voice Intelligence Engine"])


@router.get("/voices", response_model=List[VoiceInfo])
async def list_voices():
    """Returns catalog of supported voices and speech synthesis engines."""
    return voice_engine.get_supported_voices()


@router.post("/tts", response_model=TextToSpeechResponse)
async def synthesize_text_to_speech(request: TextToSpeechRequest):
    """Synthesizes text into speech with Markdown/code sanitation and provider routing."""
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text to synthesize cannot be empty.")
    try:
        return await voice_engine.synthesize_speech(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")


@router.post("/sanitize")
async def sanitize_text_preview(text: str = Form(...)):
    """Returns preview of cleaned speech text without code blocks, Markdown, or raw URLs."""
    clean = voice_engine.sanitize_for_speech(text)
    return {"original": text, "clean_spoken_text": clean}


@router.post("/transcribe", response_model=AudioTranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form("auto"),
    client_api_key: Optional[str] = Form(None)
):
    """Converts recorded audio to text using configured Whisper API or fallback."""
    if not file:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Audio file is empty.")

    res = await voice_engine.transcribe_audio(
        audio_bytes=content,
        filename=file.filename or "recording.wav",
        language=language,
        client_api_key=client_api_key
    )
    return res
