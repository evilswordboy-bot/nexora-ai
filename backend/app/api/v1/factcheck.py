"""
NEXORA AI — Fact Check API Endpoints
Provides:
- POST /api/v1/factcheck: Comprehensive fact-checking over raw text, URLs, or document excerpts.
"""

from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import FactCheckRequest, FactCheckResponse
from app.services.factcheck.engine import fact_check_engine
from app.core.rate_limiter import rate_limiter

router = APIRouter(prefix="/factcheck", tags=["Fact Check"])


@router.post("", response_model=FactCheckResponse)
async def verify_claims(request: FactCheckRequest):
    """
    Evaluates factual claims using real web search, retrieved evidence, and configured AI models.
    Returns classified verdicts: Supported, Contradicted, Mixed, Insufficient Evidence, or Opinion.
    """
    if not (request.text or request.url or request.document_ids):
        raise HTTPException(
            status_code=400,
            detail="At least one of 'text', 'url', or 'document_ids' is required for fact-checking."
        )

    try:
        response = await fact_check_engine.verify_statement(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fact check verification failed: {str(e)}")
