import json
import uuid
import logging
from typing import AsyncGenerator, Dict, Any
import httpx

from app.services.providers.base import BaseAIProvider
from app.models.schemas import ChatRequest, ChatResponse
from app.config import settings

logger = logging.getLogger("nexora.provider.openai")


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI Provider for NEXORA AI.
    Implements standard completions and SSE streaming via stream=True.
    """

    def _build_payload(self, request: ChatRequest, stream: bool = False) -> Dict[str, Any]:
        context_messages = self.prepare_context_messages(request.messages)
        messages = []

        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})

        for m in context_messages:
            if m.role in ("user", "assistant"):
                messages.append({"role": m.role, "content": m.content})

        model = request.model or "gpt-4o-mini"
        if not ("gpt" in model or "o3" in model or "o1" in model):
            model = "gpt-4o-mini"

        return {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": stream,
        }

    async def generate(self, request: ChatRequest, api_key: str) -> ChatResponse:
        url = "https://api.openai.com/v1/chat/completions"
        payload = self._build_payload(request, stream=False)
        headers = {
            "Authorization": f"Bearer {api_key}",
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
                    logger.error(f"OpenAI API returned error code {res.status_code}")
                    return ChatResponse(
                        id=f"err-{uuid.uuid4().hex[:8]}",
                        conversation_id=request.conversation_id,
                        role="assistant",
                        content=f"❌ **OpenAI API Error ({res.status_code})**: {err_text}",
                        model=payload["model"],
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
                    model=payload["model"],
                    provider="openai",
                    finish_reason=choice.get("finish_reason", "stop"),
                    usage=raw_usage,
                )
        except httpx.TimeoutException:
            logger.error("OpenAI API request timed out")
            return ChatResponse(
                id=f"err-{uuid.uuid4().hex[:8]}",
                conversation_id=request.conversation_id,
                role="assistant",
                content="❌ **Request Timeout**: OpenAI did not respond within the allocated timeout window.",
                model=payload["model"],
                provider="openai",
                finish_reason="timeout",
            )
        except Exception as e:
            logger.error(f"OpenAI unexpected exception: {type(e).__name__}")
            return ChatResponse(
                id=f"err-{uuid.uuid4().hex[:8]}",
                conversation_id=request.conversation_id,
                role="assistant",
                content=f"❌ **Connection Error with OpenAI**: {str(e)}",
                model=payload["model"],
                provider="openai",
                finish_reason="network_error",
            )

    async def stream(self, request: ChatRequest, api_key: str) -> AsyncGenerator[dict, None]:
        url = "https://api.openai.com/v1/chat/completions"
        payload = self._build_payload(request, stream=True)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        response_id = f"openai-{uuid.uuid4().hex[:8]}"

        yield {
            "type": "start",
            "id": response_id,
            "model": payload["model"],
            "provider": "openai",
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
                            "message": f"OpenAI API Error ({response.status_code}): {err_msg}",
                        }
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk_json = json.loads(data_str)
                                delta = chunk_json.get("choices", [{}])[0].get("delta", {})
                                text_content = delta.get("content", "")
                                if text_content:
                                    yield {
                                        "type": "chunk",
                                        "content": text_content,
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
                "message": "Connection to OpenAI timed out during streaming.",
            }
        except Exception as e:
            logger.error(f"OpenAI streaming exception: {type(e).__name__}")
            yield {
                "type": "error",
                "message": f"Streaming connection error: {str(e)}",
            }
