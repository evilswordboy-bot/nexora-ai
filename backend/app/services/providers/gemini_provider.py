import json
import uuid
import logging
from typing import AsyncGenerator, Dict, Any, List
import httpx

from app.services.providers.base import BaseAIProvider
from app.models.schemas import ChatRequest, ChatResponse
from app.config import settings

logger = logging.getLogger("nexora.provider.gemini")


class GeminiProvider(BaseAIProvider):
    """
    Google Gemini Provider for NEXORA AI.
    Implements standard completions and true SSE streaming via streamGenerateContent.
    """

    def _build_payload(self, request: ChatRequest) -> Dict[str, Any]:
        context_messages = self.prepare_context_messages(request.messages)
        contents = []

        for idx, m in enumerate(context_messages):
            if m.role in ("user", "assistant"):
                role_name = "user" if m.role == "user" else "model"
                parts: List[Dict[str, Any]] = [{"text": m.content}]
                
                # Check for image attachments on the message or request
                attached_images = getattr(m, "images", None)
                if not attached_images and idx == len(context_messages) - 1 and request.images:
                    attached_images = request.images

                if attached_images and role_name == "user":
                    for img_str in attached_images:
                        try:
                            # Parse mime and base64 string
                            if "base64," in img_str:
                                header, b64_clean = img_str.split("base64,", 1)
                                mime = "image/png"
                                if "image/" in header:
                                    mime = header.split("data:")[1].split(";")[0].strip()
                            else:
                                mime = "image/png"
                                b64_clean = img_str
                            
                            parts.append({
                                "inline_data": {
                                    "mime_type": mime,
                                    "data": b64_clean.strip(),
                                }
                            })
                        except Exception as e:
                            logger.warning(f"Failed to attach image to Gemini payload: {e}")

                contents.append({"role": role_name, "parts": parts})

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

        return payload

    def _get_model(self, request: ChatRequest) -> str:
        model = request.model or settings.default_model
        return model if "gemini" in model else "gemini-1.5-flash"

    async def generate(self, request: ChatRequest, api_key: str) -> ChatResponse:
        model = self._get_model(request)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = self._build_payload(request)

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    err_text = res.text
                    try:
                        err_text = res.json().get("error", {}).get("message", res.text)
                    except Exception:
                        pass
                    logger.error(f"Gemini API returned error code {res.status_code}")
                    return ChatResponse(
                        id=f"err-{uuid.uuid4().hex[:8]}",
                        conversation_id=request.conversation_id,
                        role="assistant",
                        content=f"❌ **Gemini API Error ({res.status_code})**: {err_text}",
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
        except httpx.TimeoutException:
            logger.error("Gemini API request timed out")
            return ChatResponse(
                id=f"err-{uuid.uuid4().hex[:8]}",
                conversation_id=request.conversation_id,
                role="assistant",
                content="❌ **Request Timeout**: Gemini did not respond within the allocated timeout window.",
                model=model,
                provider="gemini",
                finish_reason="timeout",
            )
        except Exception as e:
            logger.error(f"Gemini unexpected exception: {type(e).__name__}")
            return ChatResponse(
                id=f"err-{uuid.uuid4().hex[:8]}",
                conversation_id=request.conversation_id,
                role="assistant",
                content=f"❌ **Connection Error with Gemini**: {str(e)}",
                model=model,
                provider="gemini",
                finish_reason="network_error",
            )

    async def stream(self, request: ChatRequest, api_key: str) -> AsyncGenerator[dict, None]:
        model = self._get_model(request)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={api_key}"
        payload = self._build_payload(request)
        response_id = f"gemini-{uuid.uuid4().hex[:8]}"

        yield {
            "type": "start",
            "id": response_id,
            "model": model,
            "provider": "gemini",
        }

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        err_msg = error_body.decode(errors="ignore")
                        try:
                            err_msg = json.loads(err_msg).get("error", {}).get("message", err_msg)
                        except Exception:
                            pass
                        yield {
                            "type": "error",
                            "message": f"Gemini API Error ({response.status_code}): {err_msg}",
                        }
                        return

                    buffer = ""
                    async for chunk in response.aiter_text():
                        buffer += chunk
                        while "\n\n" in buffer:
                            event_text, buffer = buffer.split("\n\n", 1)
                            for line in event_text.splitlines():
                                if line.startswith("data: "):
                                    raw_data = line[6:].strip()
                                    if not raw_data:
                                        continue
                                    try:
                                        data = json.loads(raw_data)
                                        candidate = data.get("candidates", [{}])[0]
                                        parts = candidate.get("content", {}).get("parts", [])
                                        for part in parts:
                                            text_chunk = part.get("text", "")
                                            if text_chunk:
                                                yield {
                                                    "type": "chunk",
                                                    "content": text_chunk,
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
                "message": "Connection to Gemini timed out during streaming.",
            }
        except Exception as e:
            logger.error(f"Gemini streaming exception: {type(e).__name__}")
            yield {
                "type": "error",
                "message": f"Streaming connection error: {str(e)}",
            }
