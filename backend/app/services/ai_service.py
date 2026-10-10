import json
import uuid
import logging
from typing import AsyncGenerator, Optional, Tuple

from app.config import settings
from app.models.schemas import ChatRequest, ChatResponse, Message
from app.core.safety import safety_guard
from app.services.providers.base import BaseAIProvider
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.openai_provider import OpenAIProvider
from app.services.providers.anthropic_provider import AnthropicProvider
from app.services.providers.offline_provider import OfflineHonestProvider

logger = logging.getLogger("nexora.ai_service")


class AIService:
    """
    Unified AI Service for NEXORA AI.
    Dispatches generation and streaming across Gemini, OpenAI, Anthropic, and Offline providers.
    Enforces the zero-fake-response policy and adult-content safety guardrail.
    """

    def __init__(self):
        self.providers: dict[str, BaseAIProvider] = {
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "offline": OfflineHonestProvider(),
        }

    def resolve_provider_and_key(self, request: ChatRequest) -> Tuple[str, Optional[str]]:
        requested_provider = (request.provider or settings.default_provider or "auto").lower()
        client_key = request.client_api_key.strip() if request.client_api_key else None

        # Check Gemini
        if requested_provider in ("gemini", "auto"):
            if client_key and (requested_provider == "gemini" or client_key.startswith("AIza")):
                return "gemini", client_key
            if settings.gemini_api_key and settings.gemini_api_key.strip():
                return "gemini", settings.gemini_api_key

        # Check OpenAI
        if requested_provider in ("openai", "auto"):
            if client_key and (requested_provider == "openai" or client_key.startswith("sk-")):
                return "openai", client_key
            if settings.openai_api_key and settings.openai_api_key.strip():
                return "openai", settings.openai_api_key

        # Check Anthropic
        if requested_provider in ("anthropic", "auto"):
            if client_key and (requested_provider == "anthropic" or client_key.startswith("sk-ant-")):
                return "anthropic", client_key
            if settings.anthropic_api_key and settings.anthropic_api_key.strip():
                return "anthropic", settings.anthropic_api_key

        # Unconfigured / Fallback to honest offline provider
        return "offline", None

    async def generate_response(self, request: ChatRequest) -> ChatResponse:
        # 1. Content Safety Verification
        latest_user_message = next(
            (m.content for m in reversed(request.messages) if m.role == "user"), ""
        )

        if settings.enable_safety_guardrails:
            safety_result = safety_guard.evaluate_content(latest_user_message)
            if not safety_result.is_safe:
                return ChatResponse(
                    id=f"safety-{uuid.uuid4().hex[:8]}",
                    conversation_id=request.conversation_id,
                    role="assistant",
                    content=(
                        f"🛡️ **Safety Guardrail Notification**\n\n"
                        f"{safety_result.reason}\n\n"
                        f"*Category: `{safety_result.category}`*"
                    ),
                    model=request.model or "guardrail",
                    provider="nexora-safety",
                    finish_reason="safety_violation",
                )

        provider_name, api_key = self.resolve_provider_and_key(request)
        provider = self.providers.get(provider_name, self.providers["offline"])
        logger.info(f"Dispatching synchronous completion to provider: {provider_name}")
        return await provider.generate(request, api_key or "")

    async def stream_response(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Yields raw Server-Sent Event (SSE) strings formatted as 'data: <json>\n\n'.
        """
        latest_user_message = next(
            (m.content for m in reversed(request.messages) if m.role == "user"), ""
        )

        # 1. Content Safety Verification
        if settings.enable_safety_guardrails:
            safety_result = safety_guard.evaluate_content(latest_user_message)
            if not safety_result.is_safe:
                res_id = f"safety-{uuid.uuid4().hex[:8]}"
                yield f"data: {json.dumps({'type': 'start', 'id': res_id, 'model': 'guardrail', 'provider': 'nexora-safety'})}\n\n"
                safety_text = (
                    f"🛡️ **Safety Guardrail Notification**\n\n"
                    f"{safety_result.reason}\n\n"
                    f"*Category: `{safety_result.category}`*"
                )
                yield f"data: {json.dumps({'type': 'chunk', 'content': safety_text})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'id': res_id, 'finish_reason': 'safety_violation'})}\n\n"
                return

        provider_name, api_key = self.resolve_provider_and_key(request)
        provider = self.providers.get(provider_name, self.providers["offline"])
        logger.info(f"Dispatching streaming completion to provider: {provider_name}")

        async for chunk in provider.stream(request, api_key or ""):
            yield f"data: {json.dumps(chunk)}\n\n"

    async def generate_smart_title(
        self,
        user_prompt: str,
        assistant_response: Optional[str] = None,
        client_key: Optional[str] = None,
        provider: Optional[str] = "auto",
    ) -> str:
        """
        Generates a concise 3-6 word title for the conversation based on user content.
        Uses fast model inference if credentials exist, or intelligent syntactic extraction if offline.
        """
        clean_prompt = user_prompt.strip().replace("\n", " ")

        # If key is available, attempt fast title generation via provider
        provider_name, api_key = self.resolve_provider_and_key(
            ChatRequest(
                messages=[Message(id="m1", role="user", content=user_prompt)],
                client_api_key=client_key,
                provider=provider,
            )
        )

        if api_key and provider_name in ("gemini", "openai"):
            prompt_for_title = (
                f"Summarize the following user inquiry into a concise, professional 3 to 5 word title. "
                f"Return ONLY the title without quotes or punctuation: '{clean_prompt[:200]}'"
            )
            req = ChatRequest(
                messages=[Message(id="t1", role="user", content=prompt_for_title)],
                temperature=0.3,
                max_tokens=20,
                model="gemini-1.5-flash" if provider_name == "gemini" else "gpt-4o-mini",
            )
            try:
                res = await self.providers[provider_name].generate(req, api_key)
                suggested = res.content.strip().strip('"').strip("'")
                if suggested and len(suggested) < 50:
                    return suggested
            except Exception:
                pass

        # Smart deterministic extraction fallback
        words = clean_prompt.split()
        if len(words) <= 5:
            return " ".join(words).title()
        return " ".join(words[:5]).title() + "..."


ai_service = AIService()
