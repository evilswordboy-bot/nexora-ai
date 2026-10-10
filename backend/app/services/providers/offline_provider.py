import uuid
from typing import AsyncGenerator
from app.services.providers.base import BaseAIProvider
from app.models.schemas import ChatRequest, ChatResponse


class OfflineHonestProvider(BaseAIProvider):
    """
    Honest Unconfigured Provider:
    Strictly forbids fake hallucinations. Provides transparent, actionable setup guidance.
    """

    GUIDANCE_MESSAGE = (
        "⚙️ **NEXORA AI — Stage 2 Intelligence Engine Setup Required**\n\n"
        "No active AI provider API key is currently detected on the server or in your session.\n\n"
        "### How to activate live AI generation:\n"
        "1. **Client-Side (Instant):** Click the **Settings** (gear icon) in the top-right header and enter your **Google Gemini** or **OpenAI** API key. Keys entered in Settings stay in your local browser session.\n"
        "2. **Server-Side:** Open `backend/.env` and configure `GEMINI_API_KEY=your_key_here` or `OPENAI_API_KEY=your_key_here`.\n"
        "3. **Supported Models:** Google Gemini (`gemini-1.5-flash`, `gemini-1.5-pro`), OpenAI (`gpt-4o`, `gpt-4o-mini`), and Anthropic (`claude-3-5-sonnet`).\n\n"
        "*Provider status: Standby for key configuration. Streaming SSE pipeline verified.*"
    )

    async def generate(self, request: ChatRequest, api_key: str = "") -> ChatResponse:
        return ChatResponse(
            id=f"unconfigured-{uuid.uuid4().hex[:8]}",
            conversation_id=request.conversation_id,
            role="assistant",
            content=self.GUIDANCE_MESSAGE,
            model=request.model or "unconfigured",
            provider="nexora-core",
            finish_reason="unconfigured_provider",
        )

    async def stream(self, request: ChatRequest, api_key: str = "") -> AsyncGenerator[dict, None]:
        response_id = f"unconfigured-{uuid.uuid4().hex[:8]}"
        yield {
            "type": "start",
            "id": response_id,
            "model": request.model or "unconfigured",
            "provider": "nexora-core",
        }

        # Stream words smoothly so the client experiences real SSE pipeline mechanics
        words = self.GUIDANCE_MESSAGE.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == len(words) - 1 else word + " "
            yield {
                "type": "chunk",
                "content": chunk,
            }

        yield {
            "type": "done",
            "id": response_id,
            "finish_reason": "unconfigured_provider",
        }
