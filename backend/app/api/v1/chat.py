from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import StreamingResponse
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    Message,
    TitleGenerationRequest,
    TitleGenerationResponse,
)
from app.services.ai_service import ai_service
from app.services.conversation_service import conversation_service
from app.core.rate_limiter import rate_limiter

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def send_chat_message(request: ChatRequest, req: Request):
    """
    Standard synchronous chat completion endpoint.
    """
    client_ip = req.client.host if req.client else "127.0.0.1"

    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before sending another message.",
        )

    # Persist the latest user message to conversation history if conversation_id provided
    if request.conversation_id:
        latest_user_msg = next(
            (m for m in reversed(request.messages) if m.role == "user"), None
        )
        if latest_user_msg:
            conversation_service.add_message(request.conversation_id, latest_user_msg)

    response = await ai_service.generate_response(request)

    # Persist assistant response
    if request.conversation_id:
        assistant_msg = Message(
            id=response.id,
            role="assistant",
            content=response.content,
            model=response.model,
            provider=response.provider,
        )
        conversation_service.add_message(request.conversation_id, assistant_msg)

    return response


@router.post("/stream")
async def stream_chat_message(request: ChatRequest, req: Request):
    """
    Server-Sent Events (SSE) streaming chat completion endpoint.
    Streams token-by-token chunks as they arrive from the active LLM provider.
    """
    client_ip = req.client.host if req.client else "127.0.0.1"

    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before sending another message.",
        )

    # Persist the latest user message to conversation history
    if request.conversation_id:
        latest_user_msg = next(
            (m for m in reversed(request.messages) if m.role == "user"), None
        )
        if latest_user_msg:
            conversation_service.add_message(request.conversation_id, latest_user_msg)

    async def event_generator():
        async for sse_event in ai_service.stream_response(request):
            yield sse_event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/generate-title", response_model=TitleGenerationResponse)
async def generate_title(request: TitleGenerationRequest, req: Request):
    """
    Generates a concise 3-5 word conversation title from conversation content.
    """
    title = await ai_service.generate_smart_title(
        user_prompt=request.user_prompt,
        assistant_response=request.assistant_response,
        client_key=request.client_api_key,
        provider=request.provider,
    )
    if request.conversation_id:
        from app.models.schemas import ConversationUpdate
        conversation_service.update(request.conversation_id, ConversationUpdate(title=title))

    return TitleGenerationResponse(title=title)
