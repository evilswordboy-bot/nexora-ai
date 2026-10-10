from fastapi import APIRouter, Request, HTTPException, status
from app.models.schemas import SearchRequest, SearchResponse
from app.services.search.search_service import search_service
from app.core.rate_limiter import rate_limiter

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=SearchResponse)
async def perform_search(request: SearchRequest, req: Request):
    """
    Direct web search endpoint returning real, verified search results.
    """
    client_ip = req.client.host if req.client else "127.0.0.1"

    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before sending another query.",
        )

    results = await search_service.execute_search(
        query=request.query,
        max_results=request.max_results or 5,
        engine_preference=request.engine or "auto",
        client_key=request.client_search_key,
    )

    resolved_engine, _ = search_service.resolve_engine_and_key(
        request.engine or "auto", request.client_search_key
    )

    return SearchResponse(
        query=request.query,
        engine=resolved_engine,
        results=results,
        count=len(results),
    )
