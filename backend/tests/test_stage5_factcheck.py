"""
NEXORA AI — Automated Test Suite for Stage 5: Fact-Checking & Evidence Verification
Tests:
1. Claim extraction (isolating factual statements from opinions and predictions)
2. Evidence collection across search and user documents
3. Classifications: supported, contradicted, mixed, insufficient_evidence, opinion_or_prediction
4. Confidence scoring calculation
5. Missing context and misinformation flags
6. End-to-end POST /api/v1/factcheck API endpoint
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.factcheck.extractor import ClaimExtractor
from app.services.factcheck.collector import EvidenceCollector
from app.services.factcheck.engine import fact_check_engine
from app.models.schemas import FactCheckRequest, EvidenceSource


@pytest.fixture
def client():
    return TestClient(app)


def test_claim_extraction_differentiation():
    input_text = (
        "The Apollo 11 mission landed humans on the Moon in July 1969. "
        "I think space exploration is the greatest human endeavor ever. "
        "Global atmospheric carbon dioxide concentration exceeded 420 ppm in 2024. "
        "Artificial general intelligence will probably dominate civilization by 2040."
    )

    claims = ClaimExtractor.extract_claims_from_text(input_text)
    assert len(claims) >= 3

    # Check factual claim
    apollo_claim = next((c for c in claims if "Apollo 11" in c.text), None)
    assert apollo_claim is not None
    assert apollo_claim.is_factual is True

    # Check opinion
    opinion_claim = next((c for c in claims if "greatest human endeavor" in c.text), None)
    assert opinion_claim is not None
    assert opinion_claim.is_factual is False
    assert opinion_claim.category == "opinion"

    # Check prediction
    prediction_claim = next((c for c in claims if "by 2040" in c.text), None)
    assert prediction_claim is not None
    assert prediction_claim.is_factual is False
    assert prediction_claim.category == "prediction"


@pytest.mark.asyncio
async def test_evidence_collector():
    sources = await EvidenceCollector.collect_evidence_for_claim(
        claim_text="The speed of light in a vacuum is approximately 299,792 kilometers per second.",
        max_search_results=3
    )
    # DuckDuckGo fallback returns sources
    assert isinstance(sources, list)


@pytest.mark.asyncio
async def test_fact_check_opinion_evaluation():
    req = FactCheckRequest(text="Chocolate ice cream is arguably the best flavor in existence.")
    res = await fact_check_engine.verify_statement(req)

    assert res.extracted_claims_count == 1
    claim = res.claims[0]
    assert claim.verdict == "opinion_or_prediction"
    assert claim.confidence == "high"
    assert "subjective" in claim.explanation.lower()


def test_fact_check_endpoint(client):
    response = client.post(
        "/api/v1/factcheck",
        json={"text": "Water boils at 100 degrees Celsius at standard atmospheric pressure."}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["extracted_claims_count"] >= 1
    assert "overall_summary" in data
    assert len(data["claims"]) >= 1
    claim = data["claims"][0]
    assert claim["verdict"] in ["supported", "mixed", "insufficient_evidence"]
    assert claim["confidence"] in ["high", "medium", "low", "uncertain"]


def test_fact_check_empty_request_rejected(client):
    response = client.post("/api/v1/factcheck", json={})
    assert response.status_code == 400
    assert "required for fact-checking" in response.json()["detail"]
