import json
import uuid
import logging
from typing import AsyncGenerator, Optional, Tuple, List

from app.config import settings
from app.models.schemas import ChatRequest, ChatResponse, Message, SearchResultItem
from app.core.safety import safety_guard
from app.services.providers.base import BaseAIProvider
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.openai_provider import OpenAIProvider
from app.services.providers.anthropic_provider import AnthropicProvider
from app.services.providers.offline_provider import OfflineHonestProvider
from app.services.search.search_service import search_service
from app.services.search.deep_research import deep_research_engine

logger = logging.getLogger("nexora.ai_service")


class AIService:
    """
    Unified AI Service for NEXORA AI.
    Integrates Multi-Provider LLMs with Universal Web Search & Deep Research Engine.
    Enforces honest answers, zero mock citations, and prompt injection defense.
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
        latest_user_message = next(
            (m.content for m in reversed(request.messages) if m.role == "user"), ""
        )

        # 1. Content Safety Verification
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
                    search_mode=request.search_mode,
                )

        provider_name, api_key = self.resolve_provider_and_key(request)
        provider = self.providers.get(provider_name, self.providers["offline"])

        # 2. Stage 3 Search & Deep Research Preparation
        sources: List[SearchResultItem] = []
        research_queries: List[str] = []
        active_request = request

        # Stage 6 Multilingual Intelligence Instruction
        from app.services.multilingual.detector import LanguageDetector, LANGUAGE_NAMES
        detected = LanguageDetector.detect_language(latest_user_message)
        lang_target = request.target_language if (request.target_language and request.target_language != "auto") else detected.detected_language_code
        lang_name = LANGUAGE_NAMES.get(lang_target, lang_target)

        multilingual_directive = (
            f"User input detected script/language: {detected.detected_language_name} ({detected.detected_language_code}). "
            f"Respond fluently in {lang_name} ({lang_target}) while maintaining technical precision, names, numbers, and code blocks intact."
        )

        existing_prompt = request.system_prompt or ""
        combined_system = f"{existing_prompt}\n\n{multilingual_directive}".strip()
        active_request = active_request.model_copy(update={"system_prompt": combined_system})

        if request.search_mode == "web_search":
            sources = await search_service.execute_search(
                query=latest_user_message,
                max_results=settings.max_search_results,
                engine_preference=request.search_engine or "auto",
                client_key=request.client_search_key,
            )
            evidence_prompt = search_service.format_evidence_prompt(sources)
            system_instruction = (
                f"{request.system_prompt or ''}\n\n"
                f"You are responding using live web search. Ground your answer with inline citations like [1], [2] "
                f"referencing the following retrieved evidence:\n\n{evidence_prompt}"
            )
            active_request = request.model_copy(update={"system_prompt": system_instruction})

        elif request.search_mode == "deep_research":
            research_queries = deep_research_engine.decompose_query(latest_user_message)
            sources = await deep_research_engine.gather_sources(
                queries=research_queries,
                engine_preference=request.search_engine or "auto",
                client_search_key=request.client_search_key,
                max_total_sources=settings.max_research_sources,
            )
            await deep_research_engine.extract_deep_contents(sources, max_to_scrape=3)
            system_instruction = deep_research_engine.build_research_synthesis_prompt(
                user_prompt=latest_user_message,
                sources=sources,
                queries=research_queries,
            )
            active_request = request.model_copy(update={"system_prompt": system_instruction})

        # Stage 9 Vision Intelligence Context Augmentation
        has_images = bool(request.images) or any(bool(getattr(m, "images", None)) for m in request.messages)
        if has_images:
            from app.services.vision.engine import vision_engine
            img_list = request.images or []
            if not img_list:
                for m in reversed(request.messages):
                    if getattr(m, "images", None):
                        img_list = m.images
                        break
            
            ocr_texts = []
            img_metas = []
            for b64 in img_list:
                try:
                    raw_b, _ = vision_engine.parse_base64_image(b64)
                    meta = vision_engine.extract_image_metadata(raw_b)
                    img_metas.append(meta)
                    ocr_t, has_t, _ = vision_engine.perform_ocr(raw_b)
                    if ocr_t:
                        ocr_texts.append(ocr_t)
                except Exception as ve:
                    logger.warning(f"Vision pre-processing notice: {ve}")

            if ocr_texts:
                vision_context = "\n".join([vision_engine.quarantine_untrusted_text(t) for t in ocr_texts])
                current_sys = active_request.system_prompt or ""
                active_request = active_request.model_copy(update={
                    "system_prompt": f"{current_sys}\n\n### Machine OCR Context from Attached Images:\n{vision_context}".strip()
                })

        # 3. Provider Generation
        response = await provider.generate(active_request, api_key or "")
        response.sources = sources if sources else None
        response.search_mode = request.search_mode
        response.research_queries = research_queries if research_queries else None
        return response

    async def stream_response(self, request: ChatRequest) -> AsyncGenerator[str, None]:
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

        # 2. Stage 3 Search & Deep Research Streaming Pipeline
        sources: List[SearchResultItem] = []
        research_queries: List[str] = []
        active_request = request

        # Stage 6 Multilingual Intelligence Directive
        from app.services.multilingual.detector import LanguageDetector, LANGUAGE_NAMES
        detected = LanguageDetector.detect_language(latest_user_message)
        lang_target = request.target_language if (request.target_language and request.target_language != "auto") else detected.detected_language_code
        lang_name = LANGUAGE_NAMES.get(lang_target, lang_target)

        multilingual_directive = (
            f"User input detected script/language: {detected.detected_language_name} ({detected.detected_language_code}). "
            f"Respond fluently in {lang_name} ({lang_target}) while maintaining technical precision, names, numbers, and code blocks intact."
        )

        existing_prompt = request.system_prompt or ""
        combined_system = f"{existing_prompt}\n\n{multilingual_directive}".strip()
        active_request = active_request.model_copy(update={"system_prompt": combined_system})

        if request.search_mode == "web_search":
            yield f"data: {json.dumps({'type': 'research_progress', 'step': 'searching', 'message': 'Searching live web index...'})}\n\n"
            sources = await search_service.execute_search(
                query=latest_user_message,
                max_results=settings.max_search_results,
                engine_preference=request.search_engine or "auto",
                client_key=request.client_search_key,
            )
            yield f"data: {json.dumps({'type': 'research_sources', 'sources': [s.model_dump() for s in sources]})}\n\n"
            evidence_prompt = search_service.format_evidence_prompt(sources)
            system_instruction = (
                f"{request.system_prompt or ''}\n\n"
                f"You are responding using live web search. Ground your answer with inline citations like [1], [2] "
                f"referencing the following retrieved evidence:\n\n{evidence_prompt}"
            )
            active_request = request.model_copy(update={"system_prompt": system_instruction})

        elif request.search_mode == "deep_research":
            yield f"data: {json.dumps({'type': 'research_progress', 'step': 'decomposing', 'message': 'Decomposing research inquiry into investigation vectors...'})}\n\n"
            research_queries = deep_research_engine.decompose_query(latest_user_message)
            yield f"data: {json.dumps({'type': 'research_progress', 'step': 'searching', 'message': f'Searching {len(research_queries)} web query vectors...', 'queries': research_queries})}\n\n"
            sources = await deep_research_engine.gather_sources(
                queries=research_queries,
                engine_preference=request.search_engine or "auto",
                client_search_key=request.client_search_key,
                max_total_sources=settings.max_research_sources,
            )
            yield f"data: {json.dumps({'type': 'research_progress', 'step': 'reading', 'message': f'Found {len(sources)} sources. Reading and extracting deep page contents...'})}\n\n"
            await deep_research_engine.extract_deep_contents(sources, max_to_scrape=3)
            yield f"data: {json.dumps({'type': 'research_sources', 'sources': [s.model_dump() for s in sources]})}\n\n"
            yield f"data: {json.dumps({'type': 'research_progress', 'step': 'synthesizing', 'message': 'Synthesizing evidence-grounded research report...'})}\n\n"
            system_instruction = deep_research_engine.build_research_synthesis_prompt(
                user_prompt=latest_user_message,
                sources=sources,
                queries=research_queries,
            )
            active_request = request.model_copy(update={"system_prompt": system_instruction})

        # Stage 9 Vision Intelligence Context Augmentation
        has_images = bool(request.images) or any(bool(getattr(m, "images", None)) for m in request.messages)
        if has_images:
            from app.services.vision.engine import vision_engine
            img_list = request.images or []
            if not img_list:
                for m in reversed(request.messages):
                    if getattr(m, "images", None):
                        img_list = m.images
                        break
            
            ocr_texts = []
            for b64 in img_list:
                try:
                    raw_b, _ = vision_engine.parse_base64_image(b64)
                    ocr_t, _, _ = vision_engine.perform_ocr(raw_b)
                    if ocr_t:
                        ocr_texts.append(ocr_t)
                except Exception as ve:
                    logger.warning(f"Vision streaming pre-processing notice: {ve}")

            if ocr_texts:
                vision_context = "\n".join([vision_engine.quarantine_untrusted_text(t) for t in ocr_texts])
                current_sys = active_request.system_prompt or ""
                active_request = active_request.model_copy(update={
                    "system_prompt": f"{current_sys}\n\n### Machine OCR Context from Attached Images:\n{vision_context}".strip()
                })

        # 3. Stream from Chosen Provider
        async for chunk in provider.stream(active_request, api_key or ""):
            yield f"data: {json.dumps(chunk)}\n\n"

    async def generate_smart_title(
        self,
        user_prompt: str,
        assistant_response: Optional[str] = None,
        client_key: Optional[str] = None,
        provider: Optional[str] = "auto",
    ) -> str:
        clean_prompt = user_prompt.strip().replace("\n", " ")

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

        words = clean_prompt.split()
        if len(words) <= 5:
            return " ".join(words).title()
        return " ".join(words[:5]).title() + "..."


ai_service = AIService()
