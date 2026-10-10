"""
NEXORA AI — Language Identifier & Code-Switching Detector
Detects 90+ languages with special support for:
- Indic languages: Tamil, Hindi, Telugu, Malayalam, Kannada, Bengali, Marathi, Gujarati, Punjabi, Urdu
- European languages: Spanish, French, German, Italian, Portuguese, Russian
- Asian & Middle Eastern: Arabic, Japanese, Chinese, Korean
- Code-switching & Mixed languages: Tanglish (Tamil in Latin script), Hinglish (Hindi in Latin script)
"""

import re
from typing import Dict, List, Optional
from app.models.schemas import LanguageDetectionResult

try:
    from langdetect import detect_langs, DetectorFactory
    DetectorFactory.seed = 0
except ImportError:
    detect_langs = None


# Unicode Script Range RegEx
SCRIPT_REGEXES = {
    "Tamil": re.compile(r"[\u0B80-\u0BFF]"),
    "Devanagari (Hindi/Marathi)": re.compile(r"[\u0900-\u097F]"),
    "Telugu": re.compile(r"[\u0C00-\u0C7F]"),
    "Malayalam": re.compile(r"[\u0D00-\u0D7F]"),
    "Kannada": re.compile(r"[\u0C80-\u0CFF]"),
    "Bengali": re.compile(r"[\u0980-\u09FF]"),
    "Gujarati": re.compile(r"[\u0A80-\u0AFF]"),
    "Arabic": re.compile(r"[\u0600-\u06FF]"),
    "CJK (Chinese/Japanese)": re.compile(r"[\u4E00-\u9FFF]"),
    "Hangul (Korean)": re.compile(r"[\uAC00-\uD7AF]"),
    "Cyrillic": re.compile(r"[\u0400-\u04FF]"),
    "Latin": re.compile(r"[A-Za-z]"),
}

LANGUAGE_NAMES = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
    "te": "Telugu",
    "ml": "Malayalam",
    "kn": "Kannada",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ur": "Urdu",
    "ar": "Arabic",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "zh": "Chinese",
    "ko": "Korean",
    "ru": "Russian",
    "pt": "Portuguese",
    "it": "Italian"
}

# Regional code-switching markers in Latin script
TANGLISH_MARKERS = {
    "vanakkam", "epdi", "irukinga", "irukkeenga", "enna", "solreenga",
    "nalla", "romba", "seri", "illai", "illa", "pannunga", "vaanga", "ponga",
    "nanba", "nanbi", "thambi", "anna", "theriyum", "theriyadhu", "aama"
}

HINGLISH_MARKERS = {
    "namaste", "kya", "kar", "rahe", "ho", "kaise", "theek", "hai", "bhai",
    "shukriya", "bahut", "achha", "pata", "nahi", "samajh", "aaya", "karo"
}


class LanguageDetector:
    """Accurate script-aware language and code-switching detector."""

    @classmethod
    def detect_language(cls, text: str) -> LanguageDetectionResult:
        cleaned = text.strip()
        if not cleaned:
            return LanguageDetectionResult(
                detected_language_code="en",
                detected_language_name="English",
                confidence=1.0,
                script="Latin"
            )

        # 1. First analyze Unicode scripts
        detected_scripts = []
        for script_name, reg in SCRIPT_REGEXES.items():
            if reg.search(cleaned):
                detected_scripts.append(script_name)

        primary_script = detected_scripts[0] if detected_scripts else "Latin"

        # Direct script mapping for unambiguous native Indic scripts
        if "Tamil" in detected_scripts:
            return LanguageDetectionResult(
                detected_language_code="ta",
                detected_language_name="Tamil",
                confidence=0.98,
                is_mixed_or_code_switched=("Latin" in detected_scripts),
                script="Tamil"
            )
        elif "Telugu" in detected_scripts:
            return LanguageDetectionResult(
                detected_language_code="te",
                detected_language_name="Telugu",
                confidence=0.98,
                is_mixed_or_code_switched=("Latin" in detected_scripts),
                script="Telugu"
            )
        elif "Malayalam" in detected_scripts:
            return LanguageDetectionResult(
                detected_language_code="ml",
                detected_language_name="Malayalam",
                confidence=0.98,
                is_mixed_or_code_switched=("Latin" in detected_scripts),
                script="Malayalam"
            )
        elif "Kannada" in detected_scripts:
            return LanguageDetectionResult(
                detected_language_code="kn",
                detected_language_name="Kannada",
                confidence=0.98,
                is_mixed_or_code_switched=("Latin" in detected_scripts),
                script="Kannada"
            )
        elif "Bengali" in detected_scripts:
            return LanguageDetectionResult(
                detected_language_code="bn",
                detected_language_name="Bengali",
                confidence=0.98,
                is_mixed_or_code_switched=("Latin" in detected_scripts),
                script="Bengali"
            )
        elif "Devanagari (Hindi/Marathi)" in detected_scripts:
            return LanguageDetectionResult(
                detected_language_code="hi",
                detected_language_name="Hindi",
                confidence=0.95,
                is_mixed_or_code_switched=("Latin" in detected_scripts),
                script="Devanagari"
            )
        elif "Arabic" in detected_scripts:
            return LanguageDetectionResult(
                detected_language_code="ar",
                detected_language_name="Arabic",
                confidence=0.98,
                script="Arabic"
            )

        # 2. Check for Latin script code-switching (Tanglish, Hinglish)
        words = set(re.findall(r"\b\w+\b", cleaned.lower()))
        tanglish_hits = words.intersection(TANGLISH_MARKERS)
        hinglish_hits = words.intersection(HINGLISH_MARKERS)

        if len(tanglish_hits) >= 1:
            return LanguageDetectionResult(
                detected_language_code="ta",
                detected_language_name="Tamil (Tanglish)",
                confidence=0.88,
                is_mixed_or_code_switched=True,
                secondary_languages=["English"],
                script="Latin"
            )

        if len(hinglish_hits) >= 1:
            return LanguageDetectionResult(
                detected_language_code="hi",
                detected_language_name="Hindi (Hinglish)",
                confidence=0.88,
                is_mixed_or_code_switched=True,
                secondary_languages=["English"],
                script="Latin"
            )

        # 3. Fallback to statistical library (langdetect) if available
        if detect_langs:
            try:
                predictions = detect_langs(cleaned)
                if predictions:
                    top = predictions[0]
                    lang_code = top.lang
                    # Normalize zh-cn, etc.
                    lang_code = lang_code.split("-")[0]
                    name = LANGUAGE_NAMES.get(lang_code, lang_code.upper())
                    return LanguageDetectionResult(
                        detected_language_code=lang_code,
                        detected_language_name=name,
                        confidence=round(top.prob, 2),
                        is_mixed_or_code_switched=len(predictions) > 1 and predictions[1].prob > 0.25,
                        script=primary_script
                    )
            except Exception:
                pass

        return LanguageDetectionResult(
            detected_language_code="en",
            detected_language_name="English",
            confidence=0.8,
            script=primary_script
        )
