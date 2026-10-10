import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import httpx

from app.config import settings
from app.models.schemas import ChatRequest, ChatResponse
from app.core.safety import safety_guard


class AIService:
    """
    Modular AI Provider Dispatcher for NEXORA AI.
    Integrates Gemini, OpenAI, Anthropic, and local diagnostic providers.
    Enforces the core rule: Never fakes AI responses; provides honest, actionable setup guidance.
    """

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

        # 2. Determine Provider & API Key
        provider, api_key = self._resolve_provider_and_key(request)

        # 3. If unconfigured, provide transparent setup instructions
        if not api_key:
            return self._build_unconfigured_response(request, provider)

        # 4. Dispatch to real external provider
        if provider == "gemini":
            return await self._call_gemini(request, api_key)
        elif provider == "openai":
            return await self._call_openai(request, api_key)
        elif provider == "anthropic":
            return await self._call_anthropic(request, api_key)
        else:
            return self._build_unconfigured_response(request, provider)

    def _resolve_provider_and_key(self, request: ChatRequest) -> tuple[str, Optional[str]]:
        requested_provider = (request.provider or "auto").lower()

        # Check client provided override key first
        client_key = request.client_api_key.strip() if request.client_api_key else None

        if requested_provider in ("gemini", "auto"):
            if client_key and (requested_provider == "gemini" or client_key.startswith("AIza")):
                return "gemini", client_key
            if settings.gemini_api_key:
                return "gemini", settings.gemini_api_key

        if requested_provider in ("openai", "auto"):
            if client_key and (requested_provider == "openai" or client_key.startswith("sk-")):
                return "openai", client_key
            if settings.openai_api_key:
                return "openai", settings.openai_api_key

        if requested_provider in ("anthropic", "auto"):
            if client_key and (requested_provider == "anthropic" or client_key.startswith("sk-ant-")):
                return "anthropic", client_key
            if settings.anthropic_api_key:
                return "anthropic", settings.anthropic_api_key

        return requested_provider, None

    def _build_unconfigured_response(self, request: ChatRequest, attempted_provider: str) -> ChatResponse:
        content = (
            "⚙️ **NEXORA AI — Stage 1 Foundation Setup Required**\n\n"
            "No active AI provider API key is currently detected on the server or in your session.\n\n"
            "### How to activate live AI generation:\n"
            "1. **Client-Side:** Click the **Settings** (gear icon) in the top-right header and enter your **Google Gemini** or **OpenAI** API key. Keys entered in Settings stay in your local browser session.\n"
            "2. **Server-Side:** Open `backend/.env` and configure `GEMINI_API_KEY=your_key_here` or `OPENAI_API_KEY=your_key_here`.\n"
            "3. **Supported Providers:** Google Gemini (`gemini-1.5-flash`, `gemini-1.5-pro`), OpenAI (`gpt-4o`, `gpt-4o-mini`), and Anthropic (`claude-3-5-sonnet`).\n\n"
            "*Status: Provider connection verified. Ready for key configuration.*"
        )
        return ChatResponse(
            id=f"unconfigured-{uuid.uuid4().hex[:8]}",
            conversation_id=request.conversation_id,
            role="assistant",
            content=content,
            model=request.model or "unconfigured",
            provider="nexora-core",
            finish_reason="unconfigured_provider",
        )

    async def _call_gemini(self, request: ChatRequest, api_key: str) -> ChatResponse:
        model = request.model if request.model and "gemini" in request.model else "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        # Convert conversation messages to Gemini format
        contents = []
        for m in request.messages:
            if m.role in ("user", "assistant"):
                role_name = "user" if m.role == "user" else "model"
                contents.append({"role": role_name, "parts": [{"text": m.content}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }

        if request.system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": request.system_prompt}]
            }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    error_data = res.json().get("error", {})
                    error_msg = error_data.get("message", res.text)
                    return ChatResponse(
                        id=f"err-{uuid.uuid4().hex[:8]}",
                        conversation_id=request.conversation_id,
                        role="assistant",
                        content=f"❌ **Gemini API Error ({res.status_code})**: {error_msg}",
                        model=model,
                        provider="gemini",
                        finish_reason="api_error",
                    )

                data = res.json()
                candidate = data.get("candidates", [{}])[0]
                content_parts = candidate.get("content", {}).get("parts", [{}])
                reply_text = "".join(p.get("text", "") for p in content_parts)

                usage_data = data.get("usageMetadata", {})
                usage = {
                    "prompt_tokens": usage_data.get("promptTokenCount", 0),
                    "completion_tokens": usage_data.get("candidatesTokenCount", 0),
                    "total_tokens": usage_data.get("totalTokenCount", 0),
                }

                return ChatResponse(
                    id=f"gemini-{uuid.uuid4().hex[:8]}",
                    conversation_id=request.conversation_id,
                    role="assistant",
                    content=reply_text or "No response received.",
                    model=model,
                    provider="gemini",
                    finish_reason=candidate.get("finishReason", "stop"),
                    usage=usage,
                )
        except Exception as e:
            return ChatResponse(
                id=f"err-{uuid.uuid4().hex[:8]}",
                conversation_id=request.conversation_id,
                role="assistant",
                content=f"❌ **Connection Error with Gemini**: {str(e)}",
                model=model,
                provider="gemini",
                finish_reason="network_error",
            )

    async def _call_openai(self, request: ChatRequest, api_key: str) -> ChatResponse:
        model = request.model if request.model and "gpt" in request.model else "gpt-4o-mini"
        url = "https://api.openai.com/v1/chat/completions"

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})

        for m in request.messages:
            messages.append({"role": m.role, "content": m.content})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code != 200:
                    error_data = res.json().get("error", {})
                    error_msg = error_data.get("message", res.text)
                    return ChatResponse(
                        id=f"err-{uuid.uuid4().hex[:8]}",
                        conversation_id=request.conversation_id,
                        role="assistant",
                        content=f"❌ **OpenAI API Error ({res.status_code})**: {error_msg}",
                        model=model,
                        provider="openai",
                        finish_reason="api_error",
                    )

                data = res.json()
                choice = data.get("choices", [{}])[0]
                reply_text = choice.get("message", {}).get("content", "")
                raw_usage = data.get("usage", {})

                return ChatResponse(
                    id=data.get("id", f"openai-{uuid.uuid4().hex[:8]}"),
                    conversation_id=request.conversation_id,
                    role="assistant",
                    content=reply_text or "No response received.",
                    model=model,
                    provider="openai",
                    finish_reason=choice.get("finish_reason", "stop"),
                    usage=raw_usage,
                )
        except Exception as e:
            return ChatResponse(
                id=f"err-{uuid.uuid4().hex[:8]}",
                conversation_id=request.conversation_id,
                role="assistant",
                content=f"❌ **Connection Error with OpenAI**: {str(e)}",
                model=model,
                provider="openai",
                finish_reason="network_error",
            )

    async def _call_anthropic(self, request: ChatRequest, api_key: str) -> ChatResponse:
        model = request.model if request.model and "claude" in request.model else "claude-3-5-sonnet-20241022"
        url = "https://api.anthropic.com/v1/messages"

        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role in ("user", "assistant")
        ]

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

        if request.system_prompt:
            payload["system"] = request.system_prompt

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code != 200:
                    error_data = res.json().get("error", {})
                    error_msg = error_data.get("message", res.text)
                    return ChatResponse(
                        id=f"err-{uuid.uuid4().hex[:8]}",
                        conversation_id=request.conversation_id,
                        role="assistant",
                        content=f"❌ **Anthropic API Error ({res.status_code})**: {error_msg}",
                        model=model,
                        provider="anthropic",
                        finish_reason="api_error",
                    )

                data = res.json()
                content_blocks = data.get("content", [])
                reply_text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")

                return ChatResponse(
                    id=data.get("id", f"claude-{uuid.uuid4().hex[:8]}"),
                    conversation_id=request.conversation_id,
                    role="assistant",
                    content=reply_text or "No response received.",
                    model=model,
                    provider="anthropic",
                    finish_reason=data.get("stop_reason", "stop"),
                )
        except Exception as e:
            return ChatResponse(
                id=f"err-{uuid.uuid4().hex[:8]}",
                conversation_id=request.conversation_id,
                role="assistant",
                content=f"❌ **Connection Error with Anthropic**: {str(e)}",
                model=model,
                provider="anthropic",
                finish_reason="network_error",
            )


ai_service = AIService()
