from fastapi import APIRouter, Request, HTTPException, status
from app.models.schemas import ChatRequest, ChatResponse, Message
from app.services.ai_service import ai_service
from app.services.conversation_service import conversation_service
from app.core.rate_limiter import rate_limiter

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def send_chat_message(request: ChatRequest, req: Request):
    client_ip = req.client.host if req.client else "127.0.0.1"

    # Enforce rate limiting
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

    # Generate response via AIService (handles honest unconfigured check + real provider dispatch)
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
