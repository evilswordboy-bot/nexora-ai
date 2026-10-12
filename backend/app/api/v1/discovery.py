"""
NEXORA AI — Stage 21: Universal Knowledge Discovery Engine API Router
"""

from typing import List
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    DiscoveryMetadataResponse,
    DiscoverySearchRequest,
    DiscoverySearchResponse,
)
from app.services.discovery.engine import discovery_engine

router = APIRouter(prefix="/discovery", tags=["Universal Knowledge Discovery (Stage 21)"])


@router.get("/metadata", response_model=DiscoveryMetadataResponse)
async def get_discovery_metadata():
    """
    Returns Stage 21 registered multi-source connectors, supported search modes,
    query syntax operators, and cache/staleness settings.
    """
    return discovery_engine.get_metadata()


@router.post("/search", response_model=DiscoverySearchResponse)
async def execute_discovery_search(req: DiscoverySearchRequest):
    """
    Executes a unified multi-source discovery search across Web, Academic, News,
    Public Datasets, Official Documentation, and Authorized Local Knowledge Bases.
    Normalizes, deduplicates, verifies source provenance, ranks, and synthesizes findings.
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Discovery search query cannot be empty.")
    return await discovery_engine.execute_discovery(req)


@router.get("/history", response_model=List[DiscoverySearchResponse])
async def list_discovery_history(limit: int = Query(default=15, ge=1, le=30)):
    """Returns recent discovery search & synthesis runs."""
    return discovery_engine.list_recent_discoveries(limit=limit)
