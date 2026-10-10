import json
import uuid
import logging
from typing import AsyncGenerator, Dict, Any
import httpx

from app.services.providers.base import BaseAIProvider
from app.models.schemas import ChatRequest, ChatResponse
from app.config import settings

logger = logging.getLogger("nexora.provider.anthropic")


class AnthropicProvider(BaseAIProvider):
    """
    Anthropic Claude Provider for NEXORA AI.
    Implements standard completions and SSE streaming via stream=true.
    """

    def _build_payload(self, request: ChatRequest, stream: bool = False) -> Dict[str, Any]:
        context_messages = self.prepare_context_messages(request.messages)
        messages = [
            {"role": m.role, "content": m.content}
            for m in context_messages
            if m.role in ("user", "assistant")
        ]

        model = request.model or "claude-3-5-sonnet-20241022"
        if "claude" not in model:
            model = "claude-3-5-sonnet-20241022"

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": stream,
        }

        if request.system_prompt:
            payload["system"] = request.system_prompt

        return payload

    async def generate(self, request: ChatRequest, api_key: str) -> ChatResponse:
        url = "https://api.anthropic.com/v1/messages"
        payload = self._build_payload(request, stream=False)
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code != 200:
                    err_text = res.text
                    try:
                        err_text = res.json().get("error", {}).get("message", res.text)
                    except Exception:
                        pass
                    logger.error(f"Anthropic API returned error code {res.status_code}")
                    return ChatResponse(
                        id=f"err-{uuid.uuid4().hex[:8]}",
                        conversation_id=request.conversation_id,
                        role="assistant",
                        content=f"❌ **Anthropic API Error ({res.status_code})**: {err_text}",
                        model=payload["model"],
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
                    model=payload["model"],
                    provider="anthropic",
                    finish_reason=data.get("stop_reason", "stop"),
                )
        except httpx.TimeoutException:
            logger.error("Anthropic API request timed out")
            return ChatResponse(
                id=f"err-{uuid.uuid4().hex[:8]}",
                conversation_id=request.conversation_id,
                role="assistant",
                content="❌ **Request Timeout**: Anthropic did not respond within the allocated timeout window.",
                model=payload["model"],
                provider="anthropic",
                finish_reason="timeout",
            )
        except Exception as e:
            logger.error(f"Anthropic unexpected exception: {type(e).__name__}")
            return ChatResponse(
                id=f"err-{uuid.uuid4().hex[:8]}",
                conversation_id=request.conversation_id,
                role="assistant",
                content=f"❌ **Connection Error with Anthropic**: {str(e)}",
                model=payload["model"],
                provider="anthropic",
                finish_reason="network_error",
            )

    async def stream(self, request: ChatRequest, api_key: str) -> AsyncGenerator[dict, None]:
        url = "https://api.anthropic.com/v1/messages"
        payload = self._build_payload(request, stream=True)
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        response_id = f"claude-{uuid.uuid4().hex[:8]}"

        yield {
            "type": "start",
            "id": response_id,
            "model": payload["model"],
            "provider": "anthropic",
        }

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        err_msg = error_body.decode(errors="ignore")
                        try:
                            err_msg = json.loads(err_msg).get("error", {}).get("message", err_msg)
                        except Exception:
                            pass
                        yield {
                            "type": "error",
                            "message": f"Anthropic API Error ({response.status_code}): {err_msg}",
                        }
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            try:
                                event_data = json.loads(data_str)
                                if event_data.get("type") == "content_block_delta":
                                    delta = event_data.get("delta", {})
                                    if delta.get("type") == "text_delta":
                                        yield {
                                            "type": "chunk",
                                            "content": delta.get("text", ""),
                                        }
                            except Exception:
                                continue

            yield {
                "type": "done",
                "id": response_id,
                "finish_reason": "stop",
            }
        except httpx.TimeoutException:
            yield {
                "type": "error",
                "message": "Connection to Anthropic timed out during streaming.",
            }
        except Exception as e:
            logger.error(f"Anthropic streaming exception: {type(e).__name__}")
            yield {
                "type": "error",
                "message": f"Streaming connection error: {str(e)}",
            }
