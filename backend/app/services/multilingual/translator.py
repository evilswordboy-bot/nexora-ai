"""
NEXORA AI — Translation & Transliteration Engine
Provides:
- Translation with tone calibration (formal, casual, technical, simplified)
- Sentence-by-sentence parallel alignment
- Transliteration between native scripts and Latin phonetics
- Preserves technical terminology, proper names, and code syntax
"""

import json
import re
from typing import List, Dict, Any, Optional
from app.models.schemas import (
    TranslationRequest,
    TranslationResponse,
    SentencePair,
    Message,
    ChatRequest
)
from app.services.multilingual.detector import LanguageDetector, LANGUAGE_NAMES
from app.services.ai_service import ai_service


class TranslationEngine:
    """Enterprise translation engine with tone adjustment and parallel sentence alignment."""

    @classmethod
    async def translate(cls, request: TranslationRequest) -> TranslationResponse:
        cleaned_text = request.text.strip()
        if not cleaned_text:
            return TranslationResponse(
                original_text="",
                translated_text="",
                detected_source_language="en",
                target_language=request.target_language,
                tone=request.tone or "formal",
                provider=request.provider or "auto",
                model=request.model or "gemini-1.5-flash"
            )

        # 1. Detect source language if set to auto
        detected = LanguageDetector.detect_language(cleaned_text)
        src_lang = request.source_language if (request.source_language and request.source_language != "auto") else detected.detected_language_code
        src_name = LANGUAGE_NAMES.get(src_lang, src_lang.upper())
        tgt_name = LANGUAGE_NAMES.get(request.target_language, request.target_language.upper())

        # 2. Build structured LLM translation prompt
        tone_instructions = {
            "formal": "Use an authoritative, professional, and respectful tone suited for business, academic, and government communication.",
            "casual": "Use natural, colloquial phrasing suited for friendly everyday conversations.",
            "technical": "Preserve exact software, engineering, and scientific terminology without over-translating established industry keywords.",
            "simplification": "Translate into simple, accessible everyday vocabulary for broad general comprehension."
        }
        tone_instruction = tone_instructions.get(request.tone or "formal", tone_instructions["formal"])

        transliteration_clause = (
            "Also provide a phonetic transliteration of the translated text in Latin script (e.g., Romanized script)."
            if request.transliterate else "Do not include transliteration unless requested."
        )

        prompt = (
            f"You are NEXORA AI Universal Translation Specialist.\n\n"
            f"Source Language: {src_name} ({src_lang})\n"
            f"Target Language: {tgt_name} ({request.target_language})\n"
            f"Tone Directive: {tone_instruction}\n"
            f"{transliteration_clause}\n\n"
            f"Text to translate:\n\"\"\"{cleaned_text}\"\"\"\n\n"
            f"Guidelines:\n"
            f"1. Preserve numbers, proper nouns, brands, equations, and Markdown formatting.\n"
            f"2. Never replace the translation with a summary. Translate the full content faithfully.\n"
            f"3. Provide a sentence-by-sentence aligned mapping of source to translated sentences.\n"
            f"4. Add any cultural or contextual nuances if relevant.\n\n"
            f"Return JSON strictly in this format:\n"
            f'{{\n'
            f'  "translated_text": "...",\n'
            f'  "sentence_pairs": [\n'
            f'    {{"source": "Sentence 1", "translated": "Translated 1"}}\n'
            f'  ],\n'
            f'  "transliterated_text": null,\n'
            f'  "cultural_notes": null\n'
            f'}}'
        )

        chat_req = ChatRequest(
            messages=[Message(id="tr_req_1", role="user", content=prompt)],
            provider=request.provider or "auto",
            model=request.model or "gemini-1.5-flash",
            client_api_key=request.client_api_key,
            temperature=0.2,
            search_mode="ai_only"
        )

        try:
            res = await ai_service.generate_response(chat_req)
            raw = res.content.strip()

            if "{" in raw and "}" in raw:
                json_part = raw[raw.find("{"):raw.rfind("}") + 1]
                data = json.loads(json_part)

                pairs = [
                    SentencePair(
                        source_sentence=p.get("source", ""),
                        translated_sentence=p.get("translated", "")
                    )
                    for p in data.get("sentence_pairs", [])
                ]

                return TranslationResponse(
                    original_text=cleaned_text,
                    translated_text=data.get("translated_text", raw),
                    detected_source_language=src_name,
                    target_language=tgt_name,
                    tone=request.tone or "formal",
                    sentence_pairs=pairs,
                    transliterated_text=data.get("transliterated_text"),
                    cultural_notes=data.get("cultural_notes"),
                    provider=res.provider,
                    model=res.model
                )
        except Exception:
            pass

        # Fallback if raw text output
        return TranslationResponse(
            original_text=cleaned_text,
            translated_text=f"[{tgt_name} Translation of: {cleaned_text}]",
            detected_source_language=src_name,
            target_language=tgt_name,
            tone=request.tone or "formal",
            sentence_pairs=[SentencePair(source_sentence=cleaned_text, translated_sentence=cleaned_text)],
            transliterated_text=None,
            cultural_notes=None,
            provider=request.provider or "offline",
            model=request.model or "default"
        )


translation_engine = TranslationEngine()
