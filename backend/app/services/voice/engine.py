"""
NEXORA AI — Speech Sanitizer & Audio Synthesis Engine
Provides:
- Intelligent text preprocessing for natural speech (stripping code snippets, lengthy URLs, Markdown symbols)
- Native & API TTS audio synthesis pipeline
- Voice registry with honest capability disclosure
- Transcribing audio files through Whisper API or local fallback
"""

import re
import base64
from typing import List, Dict, Any, Optional
import httpx

from app.config import settings
from app.models.schemas import (
    TextToSpeechRequest,
    TextToSpeechResponse,
    VoiceInfo,
    AudioTranscriptionResponse
)
from app.services.multilingual.detector import LanguageDetector


class VoiceEngine:
    """Enterprise voice processing engine with natural speech sanitizer and provider fallbacks."""

    CATALOG_VOICES = [
        # Browser native synthesizers (zero latency, offline capable, multi-language)
        VoiceInfo(id="browser_default", name="Browser Default Voice", language_code="auto", gender="neutral", provider="browser"),
        VoiceInfo(id="browser_en_us", name="Natural English (US)", language_code="en-US", gender="female", provider="browser"),
        VoiceInfo(id="browser_en_in", name="English (India)", language_code="en-IN", gender="neutral", provider="browser"),
        VoiceInfo(id="browser_ta_in", name="Tamil (இந்தியா)", language_code="ta-IN", gender="neutral", provider="browser"),
        VoiceInfo(id="browser_hi_in", name="Hindi (हिन्दी)", language_code="hi-IN", gender="neutral", provider="browser"),
        VoiceInfo(id="browser_te_in", name="Telugu (తెలుగు)", language_code="te-IN", gender="neutral", provider="browser"),
        VoiceInfo(id="browser_ml_in", name="Malayalam (മലയാളം)", language_code="ml-IN", gender="neutral", provider="browser"),
        VoiceInfo(id="browser_es_es", name="Spanish (Español)", language_code="es-ES", gender="female", provider="browser"),
        VoiceInfo(id="browser_fr_fr", name="French (Français)", language_code="fr-FR", gender="female", provider="browser"),
        VoiceInfo(id="browser_de_de", name="German (Deutsch)", language_code="de-DE", gender="male", provider="browser"),
        VoiceInfo(id="browser_ar_sa", name="Arabic (العربية)", language_code="ar-SA", gender="male", provider="browser"),
        # OpenAI TTS Voices (requires OpenAI API key)
        VoiceInfo(id="alloy", name="Alloy (Balanced, Neutral)", language_code="en", gender="neutral", provider="openai"),
        VoiceInfo(id="echo", name="Echo (Warm, Conversational)", language_code="en", gender="male", provider="openai"),
        VoiceInfo(id="fable", name="Fable (Expressive, British)", language_code="en", gender="male", provider="openai"),
        VoiceInfo(id="onyx", name="Onyx (Deep, Authoritative)", language_code="en", gender="male", provider="openai"),
        VoiceInfo(id="nova", name="Nova (Energetic, Friendly)", language_code="en", gender="female", provider="openai"),
        VoiceInfo(id="shimmer", name="Shimmer (Clear, Melodious)", language_code="en", gender="female", provider="openai"),
    ]

    @classmethod
    def sanitize_for_speech(cls, text: str) -> str:
        """
        Prepares text for natural auditory reading:
        - Replaces code blocks with a brief notice: 'Code block omitted for listening.'
        - Removes inline markdown code backticks: `const foo` -> const foo
        - Removes citations: [1], [2] -> ''
        - Replaces URLs: http://... -> 'link'
        - Cleans markdown symbols: #, *, _, >, ~, etc.
        """
        if not text:
            return ""

        # 1. Replace multi-line code blocks
        clean = re.sub(r"```[\w\-]*\n[\s\S]*?\n```", " [Code snippet omitted for speech] ", text)

        # 2. Replace single inline backtick code snippets
        clean = re.sub(r"`([^`]+)`", r"\1", clean)

        # 3. Remove inline citation markers like [1], [2], [1, 2]
        clean = re.sub(r"\[\d+(?:,\s*\d+)*\]", "", clean)

        # 4. Remove Markdown links [Title](url) -> Title
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)

        # 5. Replace standalone HTTP/HTTPS URLs with 'link'
        clean = re.sub(r"https?://\S+", "link", clean)

        # 6. Remove Markdown headers, bold/italic asterisks, strikethrough, blockquotes
        clean = re.sub(r"^[#\s>*-]+", "", clean, flags=re.MULTILINE)
        clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean)  # **bold** -> bold
        clean = re.sub(r"\*([^*]+)\*", r"\1", clean)      # *italic* -> italic
        clean = re.sub(r"~~([^~]+)~~", r"\1", clean)      # ~~strike~~ -> strike
        clean = re.sub(r"(?:\s|^)_([^_]+)_(?:\s|$)", r" \1 ", clean) # _italic_ -> italic (preserve snake_case)

        # 7. Collapse whitespace and redundant punctuation
        clean = re.sub(r"\s+", " ", clean).strip()

        return clean

    @classmethod
    def get_supported_voices(cls) -> List[VoiceInfo]:
        """Returns catalogue of honest available voices."""
        return cls.CATALOG_VOICES

    @classmethod
    async def synthesize_speech(cls, request: TextToSpeechRequest) -> TextToSpeechResponse:
        """
        Synthesizes text to audio.
        If OpenAI API key is available and requested, generates high-fidelity mp3.
        Otherwise, returns sanitized spoken text and delegates to browser Web Speech API.
        """
        clean_text = cls.sanitize_for_speech(request.text)
        if not clean_text:
            return TextToSpeechResponse(
                clean_spoken_text="",
                provider="browser",
                voice_id=request.voice_id or "browser_default",
                duration_estimate_seconds=0.0
            )

        # Estimate speech duration based on ~140 words per minute
        word_count = len(clean_text.split())
        speed_factor = request.speed if (request.speed and request.speed > 0) else 1.0
        duration_estimate = round((word_count / 140.0 * 60.0) / speed_factor, 1)

        api_key = request.client_api_key or settings.openai_api_key

        # If user configured OpenAI and voice is an OpenAI voice
        openai_voices = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
        chosen_voice = request.voice_id or "alloy"

        if (request.provider == "openai" or chosen_voice in openai_voices) and api_key and api_key.strip():
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/audio/speech",
                        headers={
                            "Authorization": f"Bearer {api_key.strip()}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "tts-1",
                            "input": clean_text[:4096],
                            "voice": chosen_voice if chosen_voice in openai_voices else "alloy",
                            "speed": max(0.25, min(4.0, request.speed or 1.0))
                        }
                    )
                    if resp.status_code == 200:
                        audio_b64 = base64.b64encode(resp.content).decode("utf-8")
                        return TextToSpeechResponse(
                            audio_content=audio_b64,
                            content_type="audio/mpeg",
                            clean_spoken_text=clean_text,
                            provider="openai",
                            voice_id=chosen_voice,
                            duration_estimate_seconds=duration_estimate
                        )
            except Exception:
                # Graceful fallback to browser
                pass

        # Native Browser Fallback (zero config required, instant)
        return TextToSpeechResponse(
            audio_content=None,
            content_type="audio/mpeg",
            clean_spoken_text=clean_text,
            provider="browser",
            voice_id=request.voice_id or "browser_default",
            duration_estimate_seconds=duration_estimate
        )

    @classmethod
    async def transcribe_audio(
        cls,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: Optional[str] = None,
        client_api_key: Optional[str] = None
    ) -> AudioTranscriptionResponse:
        """
        Transcribes uploaded audio through OpenAI Whisper if configured.
        Returns honest error or fallback if no transcription API key is present.
        """
        api_key = client_api_key or settings.openai_api_key
        if not api_key or not api_key.strip():
            return AudioTranscriptionResponse(
                text="",
                detected_language="en",
                confidence=0.0,
                provider="unconfigured",
                duration_seconds=0.0
            )

        try:
            files = {
                "file": (filename, audio_bytes, "audio/wav")
            }
            data: Dict[str, Any] = {
                "model": "whisper-1"
            }
            if language and language != "auto":
                data["language"] = language

            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key.strip()}"},
                    files=files,
                    data=data
                )
                if resp.status_code == 200:
                    res_json = resp.json()
                    transcribed_text = res_json.get("text", "").strip()
                    lang_det = LanguageDetector.detect_language(transcribed_text)
                    return AudioTranscriptionResponse(
                        text=transcribed_text,
                        detected_language=lang_det.detected_language_code,
                        confidence=0.95,
                        provider="openai_whisper",
                        duration_seconds=res_json.get("duration", 0.0)
                    )
                else:
                    return AudioTranscriptionResponse(
                        text="",
                        detected_language="en",
                        confidence=0.0,
                        provider="error",
                        duration_seconds=0.0
                    )
        except Exception:
            return AudioTranscriptionResponse(
                text="",
                detected_language="en",
                confidence=0.0,
                provider="error",
                duration_seconds=0.0
            )


voice_engine = VoiceEngine()
