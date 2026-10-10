"""
NEXORA AI — Claim Extractor & Classifier
Dissects statements, articles, and text excerpts into individual checkable claims.
Classifies whether each statement is an objective factual claim, opinion, prediction, or satire.
"""

import re
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel
from app.models.schemas import VerdictClassification


class ExtractedClaim(BaseModel):
    claim_id: int
    text: str
    is_factual: bool
    category: str # "statistic", "event", "quote", "scientific", "opinion", "prediction"


class ClaimExtractor:
    """Extracts verifiable claims from unstructured narrative."""

    OPINION_MARKERS = [
        "i think", "i believe", "in my opinion", "arguably", "probably",
        "feels like", "best in the world", "worst ever", "beautiful",
        "should", "must", "ought to"
    ]

    PREDICTION_MARKERS = [
        "will happen", "will become", "by 2030", "by 2040", "by 2050",
        "projected to", "expected to reach", "forecasted"
    ]

    @classmethod
    def extract_claims_from_text(cls, text: str) -> List[ExtractedClaim]:
        cleaned = text.strip()
        if not cleaned:
            return []

        # Split into sentences using punctuation boundaries
        raw_sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 10]

        if not sentences:
            sentences = [cleaned]

        extracted: List[ExtractedClaim] = []
        for idx, sentence in enumerate(sentences[:10]): # Limit to top 10 claims per batch
            lower = sentence.lower()

            # Check if prediction
            is_prediction = any(p in lower for p in cls.PREDICTION_MARKERS)
            # Check if subjective opinion
            is_opinion = any(o in lower for o in cls.OPINION_MARKERS)

            # Check if statistic / numerical claim
            has_numbers = bool(re.search(r"\b\d+(\.\d+)?%?\b", sentence))
            has_dates = bool(re.search(r"\b(19\d\d|20\d\d)\b", sentence))

            if is_prediction:
                category = "prediction"
                is_factual = False
            elif is_opinion:
                category = "opinion"
                is_factual = False
            elif has_numbers or "%" in sentence or "$" in sentence:
                category = "statistic"
                is_factual = True
            elif has_dates or "in " in lower or "on " in lower:
                category = "event"
                is_factual = True
            else:
                category = "factual_assertion"
                is_factual = True

            extracted.append(ExtractedClaim(
                claim_id=idx + 1,
                text=sentence,
                is_factual=is_factual,
                category=category
            ))

        return extracted
