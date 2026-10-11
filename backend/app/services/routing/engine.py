"""
NEXORA AI — Stage 12: Intelligent Model Routing Engine
Provides:
- Modular Provider & Model Registry with capabilities, context limits, pricing metadata, timeouts, and honest availability
- Task Category Classification (general_chat, coding, deep_research, document_analysis, image_understanding, translation, voice, reasoning)
- Multi-Preference Intelligent Selection (quality_first, balanced, speed_first)
- Bounded Fallback & Reliability (rate-limit, timeout, and outage recovery without infinite loops)
- Cost & Token Estimation, Spending Limits, and Privacy-Preserving Telemetry
- Prompt-Injection Routing Override Defense
"""

import asyncio
import logging
import re
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any

from app.config import settings
from app.models.schemas import (
    utc_now,
    RoutingTaskCategory,
    RoutingPreference,
    ProviderAvailabilityStatus,
    ModelRegistryEntry,
    TokenCostEstimate,
    RoutingFallbackAttempt,
    RoutingDecision,
    RoutingPolicyConfig,
    RoutingTelemetryEntry,
    RoutingUsageSummary,
    RoutingSimulateRequest,
    RoutingExecuteRequest,
    RoutingExecuteResponse,
    ChatRequest,
    ChatResponse,
    Message,
)
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.openai_provider import OpenAIProvider
from app.services.providers.anthropic_provider import AnthropicProvider
from app.services.providers.offline_provider import OfflineHonestProvider

logger = logging.getLogger("nexora.routing")

ALL_CAPABILITIES: List[RoutingTaskCategory] = [
    "general_chat",
    "coding",
    "deep_research",
    "document_analysis",
    "image_understanding",
    "translation",
    "voice",
    "reasoning",
]

TEXT_ONLY_CAPABILITIES: List[RoutingTaskCategory] = [
    "general_chat",
    "coding",
    "deep_research",
    "document_analysis",
    "translation",
    "reasoning",
]


class ProviderModelRegistry:
    """
    Modular registry of AI providers and models.
    Supports adding or removing providers/models at runtime without rewriting the application.
    Never exposes API keys or secrets.
    """

    def __init__(self):
        self._models: Dict[str, ModelRegistryEntry] = {}
        self._provider_health_overrides: Dict[str, ProviderAvailabilityStatus] = {}
        self._register_default_catalog()

    def _register_default_catalog(self):
        default_models = [
            ModelRegistryEntry(
                model_id="gemini-1.5-flash",
                provider="gemini",
                display_name="Gemini 1.5 Flash",
                supported_capabilities=list(ALL_CAPABILITIES),
                context_window_tokens=1000000,
                max_output_tokens=8192,
                pricing_per_1k_input_usd=0.000075,
                pricing_per_1k_output_usd=0.00030,
                quality_tier="fast",
                typical_latency_ms=420,
                timeout_seconds=30.0,
                is_default=True,
            ),
            ModelRegistryEntry(
                model_id="gemini-2.0-flash",
                provider="gemini",
                display_name="Gemini 2.0 Flash",
                supported_capabilities=list(ALL_CAPABILITIES),
                context_window_tokens=1000000,
                max_output_tokens=8192,
                pricing_per_1k_input_usd=0.00010,
                pricing_per_1k_output_usd=0.00040,
                quality_tier="balanced",
                typical_latency_ms=480,
                timeout_seconds=30.0,
            ),
            ModelRegistryEntry(
                model_id="gemini-1.5-pro",
                provider="gemini",
                display_name="Gemini 1.5 Pro",
                supported_capabilities=list(ALL_CAPABILITIES),
                context_window_tokens=2000000,
                max_output_tokens=8192,
                pricing_per_1k_input_usd=0.00125,
                pricing_per_1k_output_usd=0.00500,
                quality_tier="frontier",
                typical_latency_ms=1150,
                timeout_seconds=45.0,
            ),
            ModelRegistryEntry(
                model_id="gpt-4o",
                provider="openai",
                display_name="OpenAI GPT-4o",
                supported_capabilities=list(ALL_CAPABILITIES),
                context_window_tokens=128000,
                max_output_tokens=16384,
                pricing_per_1k_input_usd=0.00250,
                pricing_per_1k_output_usd=0.01000,
                quality_tier="frontier",
                typical_latency_ms=980,
                timeout_seconds=45.0,
            ),
            ModelRegistryEntry(
                model_id="gpt-4o-mini",
                provider="openai",
                display_name="OpenAI GPT-4o Mini",
                supported_capabilities=list(ALL_CAPABILITIES),
                context_window_tokens=128000,
                max_output_tokens=16384,
                pricing_per_1k_input_usd=0.00015,
                pricing_per_1k_output_usd=0.00060,
                quality_tier="fast",
                typical_latency_ms=460,
                timeout_seconds=30.0,
            ),
            ModelRegistryEntry(
                model_id="o3-mini",
                provider="openai",
                display_name="OpenAI o3-mini (Reasoning & Coding)",
                supported_capabilities=["general_chat", "coding", "deep_research", "document_analysis", "reasoning"],
                context_window_tokens=200000,
                max_output_tokens=32768,
                pricing_per_1k_input_usd=0.00110,
                pricing_per_1k_output_usd=0.00440,
                quality_tier="frontier",
                typical_latency_ms=1350,
                timeout_seconds=60.0,
            ),
            ModelRegistryEntry(
                model_id="claude-3-5-sonnet-20241022",
                provider="anthropic",
                display_name="Claude 3.5 Sonnet",
                supported_capabilities=[
                    "general_chat",
                    "coding",
                    "deep_research",
                    "document_analysis",
                    "image_understanding",
                    "translation",
                    "reasoning",
                ],
                context_window_tokens=200000,
                max_output_tokens=8192,
                pricing_per_1k_input_usd=0.00300,
                pricing_per_1k_output_usd=0.01500,
                quality_tier="frontier",
                typical_latency_ms=1050,
                timeout_seconds=45.0,
            ),
            ModelRegistryEntry(
                model_id="claude-3-5-haiku-20241022",
                provider="anthropic",
                display_name="Claude 3.5 Haiku",
                supported_capabilities=list(TEXT_ONLY_CAPABILITIES),
                context_window_tokens=200000,
                max_output_tokens=8192,
                pricing_per_1k_input_usd=0.00080,
                pricing_per_1k_output_usd=0.00400,
                quality_tier="fast",
                typical_latency_ms=520,
                timeout_seconds=30.0,
            ),
        ]
        for entry in default_models:
            self._models[entry.model_id] = entry

    def register_model(self, entry: ModelRegistryEntry) -> ModelRegistryEntry:
        """Dynamically adds or updates a model in the registry."""
        self._models[entry.model_id] = entry
        return self.get_model(entry.model_id)  # type: ignore[return-value]

    def unregister_model(self, model_id: str) -> bool:
        """Dynamically removes a model from the registry."""
        if model_id in self._models:
            del self._models[model_id]
            return True
        return False

    def set_provider_health(self, provider: str, status: Optional[ProviderAvailabilityStatus]) -> None:
        """Sets or clears a runtime availability status override (e.g. rate_limited, outage, degraded)."""
        prov = provider.lower().strip()
        if status is None:
            self._provider_health_overrides.pop(prov, None)
        else:
            self._provider_health_overrides[prov] = status

    def is_provider_configured(self, provider: str, client_api_key: Optional[str] = None) -> bool:
        """Checks whether a provider has verified backend credentials (or valid transient client key)."""
        prov = provider.lower().strip()
        if client_api_key and client_api_key.strip():
            key = client_api_key.strip()
            if prov == "gemini" and key.startswith("AIza"):
                return True
            if prov == "openai" and key.startswith("sk-") and not key.startswith("sk-ant-"):
                return True
            if prov == "anthropic" and key.startswith("sk-ant-"):
                return True
        configured_env = settings.get_configured_providers()
        return prov in configured_env

    def get_provider_api_key(self, provider: str, client_api_key: Optional[str] = None) -> Optional[str]:
        """Retrieves the provider credential strictly for internal backend dispatch. Never serialized."""
        prov = provider.lower().strip()
        if client_api_key and client_api_key.strip():
            key = client_api_key.strip()
            if prov == "gemini" and key.startswith("AIza"):
                return key
            if prov == "openai" and key.startswith("sk-") and not key.startswith("sk-ant-"):
                return key
            if prov == "anthropic" and key.startswith("sk-ant-"):
                return key
        if prov == "gemini" and settings.gemini_api_key.strip():
            return settings.gemini_api_key.strip()
        if prov == "openai" and settings.openai_api_key.strip():
            return settings.openai_api_key.strip()
        if prov == "anthropic" and settings.anthropic_api_key.strip():
            return settings.anthropic_api_key.strip()
        return None

    def _enrich_availability(
        self, entry: ModelRegistryEntry, client_api_key: Optional[str] = None
    ) -> ModelRegistryEntry:
        is_conf = self.is_provider_configured(entry.provider, client_api_key=client_api_key)
        override = self._provider_health_overrides.get(entry.provider.lower())
        if not is_conf:
            status: ProviderAvailabilityStatus = "unconfigured"
        elif override:
            status = override
        else:
            status = "available"
        return entry.model_copy(
            update={
                "configured": is_conf,
                "availability_status": status,
                "is_default": entry.model_id == settings.default_model,
            }
        )

    def list_models(self, client_api_key: Optional[str] = None) -> List[ModelRegistryEntry]:
        return [self._enrich_availability(m, client_api_key=client_api_key) for m in self._models.values()]

    def get_model(self, model_id: str, client_api_key: Optional[str] = None) -> Optional[ModelRegistryEntry]:
        m = self._models.get(model_id)
        if not m:
            return None
        return self._enrich_availability(m, client_api_key=client_api_key)


class IntelligentModelRouter:
    """
    Stage 12 Intelligent Model Routing Engine.
    Selects eligible models based on task classification, required capabilities, availability,
    routing preference (quality_first, balanced, speed_first), and cost budgets.
    Implements bounded fallback on rate limits, timeouts, and outages.
    """

    def __init__(self):
        self.registry = ProviderModelRegistry()
        self.policy = RoutingPolicyConfig(
            routing_preference=settings.default_routing_mode if settings.default_routing_mode in ("quality_first", "balanced", "speed_first") else "balanced",  # type: ignore[arg-type]
            default_provider=settings.default_provider,
            default_model=settings.default_model,
            max_fallbacks=settings.max_routing_fallbacks,
            daily_spending_limit_usd=settings.daily_spending_limit_usd,
            per_request_max_cost_usd=settings.per_request_max_cost_usd,
            timeout_seconds=settings.routing_timeout_seconds,
        )
        self._providers = {
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "offline": OfflineHonestProvider(),
        }
        self._telemetry: List[RoutingTelemetryEntry] = []
        self._lock = asyncio.Lock()

    def get_policy(self) -> RoutingPolicyConfig:
        return self.policy

    def update_policy(self, new_policy: RoutingPolicyConfig) -> RoutingPolicyConfig:
        self.policy = new_policy
        return self.policy

    @staticmethod
    def detect_routing_policy_injection(prompt: str) -> bool:
        """
        Detects attempts in user input or retrieved untrusted web content to override
        routing security policies, spending limits, or model authorization rules.
        """
        lower = prompt.lower()
        injection_patterns = [
            r"ignore\s+(all\s+)?routing\s+(rules|policies|limits)",
            r"bypass\s+(the\s+)?(spending|budget|cost)\s+limit",
            r"override\s+(system\s+)?routing\s+policy",
            r"force\s+paid\s+frontier\s+model\s+without\s+budget",
            r"disable\s+routing\s+security",
        ]
        return any(re.search(pat, lower) for pat in injection_patterns)

    @staticmethod
    def classify_task_category(
        prompt: str,
        explicit_category: Optional[RoutingTaskCategory] = None,
        has_images: bool = False,
        has_documents: bool = False,
    ) -> Tuple[RoutingTaskCategory, List[RoutingTaskCategory]]:
        """
        Classifies an incoming request into a task category and identifies required model capabilities.
        """
        required: List[RoutingTaskCategory] = []
        if has_images:
            required.append("image_understanding")
        if has_documents:
            required.append("document_analysis")

        if explicit_category:
            if explicit_category not in required:
                required.insert(0, explicit_category)
            return explicit_category, required

        lower = prompt.lower()
        if has_images or any(k in lower for k in ["analyze this image", "in this screenshot", "diagram", "ocr", "visual diff"]):
            cat: RoutingTaskCategory = "image_understanding"
        elif any(k in lower for k in ["def ", "function ", "typescript", "python", "refactor", "compile", "sql query", "bug in", "stack trace", "algorithm", "code"]):
            cat = "coding"
        elif has_documents or any(k in lower for k in ["uploaded pdf", "in the document", "summarize the file", "contract clause"]):
            cat = "document_analysis"
        elif any(k in lower for k in ["translate", "transliterate", "in tamil", "in hindi", "in spanish", "in french"]):
            cat = "translation"
        elif any(k in lower for k in ["deep research", "literature review", "compare sources", "comprehensive report"]):
            cat = "deep_research"
        elif any(k in lower for k in ["step by step", "prove that", "multi-step", "logical deduction", "calculate"]):
            cat = "reasoning"
        elif any(k in lower for k in ["speak this", "voice mode", "audio transcript", "dictate"]):
            cat = "voice"
        else:
            cat = "general_chat"

        if cat not in required:
            required.insert(0, cat)
        return cat, required

    @staticmethod
    def estimate_tokens_and_cost(
        prompt: str,
        expected_output_tokens: int,
        model: Optional[ModelRegistryEntry],
    ) -> TokenCostEstimate:
        """
        Estimates prompt and completion token usage and calculates estimated USD cost
        when reliable pricing metadata is available on the model registry entry.
        """
        est_prompt_tokens = max(1, len(prompt) // 4)
        est_completion_tokens = max(10, expected_output_tokens)
        est_total = est_prompt_tokens + est_completion_tokens

        if not model or model.pricing_per_1k_input_usd is None or model.pricing_per_1k_output_usd is None:
            return TokenCostEstimate(
                estimated_prompt_tokens=est_prompt_tokens,
                estimated_completion_tokens=est_completion_tokens,
                estimated_total_tokens=est_total,
                estimated_cost_usd=None,
                is_exact_cost=False,
                pricing_available=False,
                cost_note="Pricing metadata unavailable for this provider/offline mode; exact cost cannot be calculated.",
            )

        input_cost = (est_prompt_tokens / 1000.0) * model.pricing_per_1k_input_usd
        output_cost = (est_completion_tokens / 1000.0) * model.pricing_per_1k_output_usd
        total_cost = round(input_cost + output_cost, 6)

        return TokenCostEstimate(
            estimated_prompt_tokens=est_prompt_tokens,
            estimated_completion_tokens=est_completion_tokens,
            estimated_total_tokens=est_total,
            estimated_cost_usd=total_cost,
            is_exact_cost=False,
            pricing_available=True,
            cost_note="Estimated using ~4 chars/token heuristic and published per-1K token rates (not an exact billing invoice).",
        )

    def _score_model(
        self,
        model: ModelRegistryEntry,
        category: RoutingTaskCategory,
        preference: RoutingPreference,
    ) -> float:
        """Scores an eligible model based on routing preference, task affinity, latency, and cost."""
        score = 50.0

        # Quality tier weights
        tier_scores = {"frontier": 40.0, "balanced": 25.0, "fast": 15.0}
        speed_scores = {"fast": 40.0, "balanced": 28.0, "frontier": 10.0}
        balanced_scores = {"balanced": 35.0, "fast": 30.0, "frontier": 25.0}

        if preference == "quality_first":
            score += tier_scores.get(model.quality_tier, 20.0)
        elif preference == "speed_first":
            score += speed_scores.get(model.quality_tier, 20.0)
            score += max(0.0, (1500 - model.typical_latency_ms) / 50.0)
        else:  # balanced
            score += balanced_scores.get(model.quality_tier, 25.0)
            score += max(0.0, (1200 - model.typical_latency_ms) / 80.0)

        # Task-specific affinity bonuses
        if category in ("coding", "reasoning") and model.model_id in ("claude-3-5-sonnet-20241022", "o3-mini", "gpt-4o", "gemini-1.5-pro"):
            score += 12.0 if preference != "speed_first" else 4.0
        if category in ("document_analysis", "deep_research") and model.context_window_tokens >= 500000:
            score += 10.0
        if category == "image_understanding" and model.model_id in ("gemini-1.5-pro", "gpt-4o", "gemini-2.0-flash", "gemini-1.5-flash"):
            score += 8.0

        # Degraded health penalty
        if model.availability_status == "degraded":
            score -= 25.0

        # Explicit default model slight tie-breaker bonus in balanced mode
        if preference == "balanced" and model.model_id == self.policy.default_model:
            score += 5.0

        return round(score, 2)

    def select_route(
        self,
        request: RoutingSimulateRequest,
        client_api_key: Optional[str] = None,
        allow_unconfigured_preview: bool = False,
    ) -> RoutingDecision:
        """
        Selects the optimal eligible model and builds a bounded fallback chain.
        Never claims an unconfigured model is available for live execution.
        """
        decision_id = f"route_{uuid.uuid4().hex[:10]}"
        injection_blocked = self.detect_routing_policy_injection(request.prompt)

        category, required_caps = self.classify_task_category(
            prompt=request.prompt,
            explicit_category=request.task_category,
            has_images=request.has_images,
            has_documents=request.has_documents,
        )
        for extra_cap in request.required_capabilities:
            if extra_cap not in required_caps:
                required_caps.append(extra_cap)

        preference: RoutingPreference = (
            self.policy.routing_preference
            if injection_blocked
            else (request.routing_preference or self.policy.routing_preference)
        )

        est_prompt_tokens = max(1, len(request.prompt) // 4)
        all_models = self.registry.list_models(client_api_key=client_api_key)

        # 1. Filter by capability & context window
        capable_models: List[ModelRegistryEntry] = []
        for m in all_models:
            if not all(req_cap in m.supported_capabilities for req_cap in required_caps):
                continue
            if est_prompt_tokens + request.expected_output_tokens > m.context_window_tokens:
                continue
            if not self.policy.allow_paid_frontier_models and m.quality_tier == "frontier":
                continue
            capable_models.append(m)

        if not capable_models:
            return RoutingDecision(
                id=decision_id,
                task_category=category,
                required_capabilities=required_caps,
                routing_preference=preference,
                selected_provider="offline",
                selected_model="unconfigured",
                selection_rationale=(
                    f"No registered model supports the required capabilities {required_caps} "
                    f"within context/policy constraints."
                ),
                fallback_chain=[],
                is_configured=False,
                cost_estimate=self.estimate_tokens_and_cost(request.prompt, request.expected_output_tokens, None),
                budget_allowed=True,
                prompt_injection_override_blocked=injection_blocked,
            )

        # 2. Filter by verified configuration and operational availability
        available_models = [
            m
            for m in capable_models
            if m.configured and m.availability_status in ("available", "degraded")
        ]

        # Check current cumulative spend against daily budget
        current_spend = sum(t.estimated_cost_usd for t in self._telemetry if t.success)
        remaining_daily = max(0.0, self.policy.daily_spending_limit_usd - current_spend)

        # If no provider is configured, explain honestly (or rank capable models if previewing in simulator)
        candidate_pool = available_models if available_models else (capable_models if allow_unconfigured_preview else [])

        if not candidate_pool:
            return RoutingDecision(
                id=decision_id,
                task_category=category,
                required_capabilities=required_caps,
                routing_preference=preference,
                selected_provider="offline",
                selected_model="offline-honest-guide",
                selection_rationale=(
                    f"Task classified as '{category}' requiring {required_caps}. "
                    f"No configured & available provider currently satisfies these requirements. "
                    f"Configure GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY in backend/.env."
                ),
                fallback_chain=[],
                is_configured=False,
                cost_estimate=self.estimate_tokens_and_cost(request.prompt, request.expected_output_tokens, None),
                budget_allowed=True,
                prompt_injection_override_blocked=injection_blocked,
            )

        # 3. Score & sort candidates
        scored_candidates: List[Tuple[float, ModelRegistryEntry]] = []
        for m in candidate_pool:
            s = self._score_model(m, category, preference)
            # Honor explicit user preferred provider/model if valid, capable, and not a prompt injection
            if not injection_blocked:
                if request.preferred_model and request.preferred_model != "auto" and m.model_id == request.preferred_model:
                    s += 100.0
                elif request.preferred_provider and request.preferred_provider != "auto" and m.provider == request.preferred_provider:
                    s += 30.0
            scored_candidates.append((s, m))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # 4. Enforce per-request and daily spending limits
        selected_entry = scored_candidates[0][1]
        selected_cost = self.estimate_tokens_and_cost(request.prompt, request.expected_output_tokens, selected_entry)
        budget_allowed = True
        budget_warning: Optional[str] = None

        if selected_cost.estimated_cost_usd is not None:
            if (
                selected_cost.estimated_cost_usd > self.policy.per_request_max_cost_usd
                or selected_cost.estimated_cost_usd > remaining_daily
            ):
                # Try to find a more affordable candidate within budget
                affordable_found = False
                for _, cand in scored_candidates[1:]:
                    cand_cost = self.estimate_tokens_and_cost(request.prompt, request.expected_output_tokens, cand)
                    if (
                        cand_cost.estimated_cost_usd is not None
                        and cand_cost.estimated_cost_usd <= self.policy.per_request_max_cost_usd
                        and cand_cost.estimated_cost_usd <= remaining_daily
                    ):
                        budget_warning = (
                            f"Downgraded from '{selected_entry.model_id}' (${selected_cost.estimated_cost_usd:.5f}) "
                            f"to '{cand.model_id}' (${cand_cost.estimated_cost_usd:.5f}) to stay within configured budget limits."
                        )
                        selected_entry = cand
                        selected_cost = cand_cost
                        affordable_found = True
                        break
                if not affordable_found:
                    budget_allowed = False
                    budget_warning = (
                        f"Estimated request cost (${selected_cost.estimated_cost_usd:.5f}) exceeds configured budget limit "
                        f"(per-request max: ${self.policy.per_request_max_cost_usd:.4f}, remaining daily: ${remaining_daily:.4f})."
                    )

        fallback_models = [
            cand.model_id
            for _, cand in scored_candidates
            if cand.model_id != selected_entry.model_id
        ][: self.policy.max_fallbacks]

        rationale = (
            f"Selected '{selected_entry.display_name}' ({selected_entry.provider}/{selected_entry.model_id}) "
            f"for task category '{category}' under '{preference}' routing preference "
            f"(tier={selected_entry.quality_tier}, typical_latency={selected_entry.typical_latency_ms}ms, "
            f"configured={selected_entry.configured})."
        )
        if injection_blocked:
            rationale += " [Security Alert: Prompt attempt to override routing policy was blocked.]"

        return RoutingDecision(
            id=decision_id,
            task_category=category,
            required_capabilities=required_caps,
            routing_preference=preference,
            selected_provider=selected_entry.provider,
            selected_model=selected_entry.model_id,
            selection_rationale=rationale,
            fallback_chain=fallback_models,
            is_configured=selected_entry.configured,
            cost_estimate=selected_cost,
            budget_allowed=budget_allowed,
            budget_warning=budget_warning,
            security_policy_enforced=True,
            prompt_injection_override_blocked=injection_blocked,
        )

    async def execute_routed_request(self, request: RoutingExecuteRequest) -> RoutingExecuteResponse:
        """
        Executes a request using Intelligent Model Routing with bounded fallback recovery,
        spending limit enforcement, error normalization, and telemetry logging.
        """
        start_ts = time.perf_counter()
        sim_req = RoutingSimulateRequest(
            prompt=request.prompt,
            task_category=request.task_category,
            required_capabilities=request.required_capabilities,
            routing_preference=request.routing_preference,
            preferred_provider=request.preferred_provider,
            preferred_model=request.preferred_model,
            has_images=request.has_images,
            has_documents=request.has_documents,
            expected_output_tokens=request.expected_output_tokens,
        )
        decision = self.select_route(sim_req, client_api_key=request.client_api_key, allow_unconfigured_preview=False)

        if not decision.budget_allowed:
            elapsed = round((time.perf_counter() - start_ts) * 1000, 2)
            await self._record_telemetry(
                decision=decision,
                success=False,
                error_category="budget_exceeded",
                latency_ms=elapsed,
            )
            raise ValueError(decision.budget_warning or "Request blocked by configured spending limit.")

        # Build candidate execution sequence: [selected_model] + bounded fallback_chain
        execution_chain = [decision.selected_model] + list(decision.fallback_chain[: self.policy.max_fallbacks])
        visited_models: set[str] = set()
        final_response: Optional[ChatResponse] = None
        last_error: Optional[str] = None

        for idx, model_id in enumerate(execution_chain):
            if model_id in visited_models:
                continue
            visited_models.add(model_id)

            if model_id in ("unconfigured", "offline-honest-guide"):
                offline_req = ChatRequest(
                    messages=[Message(id="r_msg_1", role="user", content=request.prompt)],
                    provider="offline",
                    model="unconfigured",
                )
                final_response = await self._providers["offline"].generate(offline_req, "")
                break

            model_entry = self.registry.get_model(model_id, client_api_key=request.client_api_key)
            if not model_entry or not model_entry.configured:
                continue

            api_key = self.registry.get_provider_api_key(model_entry.provider, client_api_key=request.client_api_key)
            provider_impl = self._providers.get(model_entry.provider)
            if not provider_impl or not api_key:
                continue

            step_start = time.perf_counter()
            try:
                chat_req = ChatRequest(
                    messages=[Message(id="r_msg_1", role="user", content=request.prompt)],
                    provider=model_entry.provider,
                    model=model_entry.model_id,
                    max_tokens=request.expected_output_tokens,
                )
                timeout_s = min(model_entry.timeout_seconds, self.policy.timeout_seconds)
                res = await asyncio.wait_for(provider_impl.generate(chat_req, api_key), timeout=timeout_s)

                # Check if provider returned an error finish_reason (e.g., 429 rate limit, 503 outage, or invalid response)
                if res.finish_reason == "error" or res.content.startswith("⚠️"):
                    raise RuntimeError(res.content[:200])

                final_response = res
                if idx > 0:
                    decision.used_fallback = True
                    decision.selected_provider = model_entry.provider
                    decision.selected_model = model_entry.model_id
                    decision.cost_estimate = self.estimate_tokens_and_cost(
                        request.prompt, request.expected_output_tokens, model_entry
                    )
                break
            except Exception as exc:
                step_ms = round((time.perf_counter() - step_start) * 1000, 2)
                norm_err, err_code = self._normalize_error(exc)
                last_error = norm_err
                decision.fallback_attempts.append(
                    RoutingFallbackAttempt(
                        provider=model_entry.provider,
                        model_id=model_entry.model_id,
                        reason=norm_err,
                        error_code=err_code,
                        latency_ms=step_ms,
                    )
                )
                logger.warning(
                    f"Routing attempt failed for {model_entry.provider}/{model_entry.model_id}: {norm_err} (code={err_code})"
                )

        total_ms = round((time.perf_counter() - start_ts) * 1000, 2)

        if final_response is None:
            # All configured candidates failed; return clear, normalized explanation without crashing
            error_explanation = (
                f"⚠️ **Model Routing Fallback Exhausted**\n\n"
                f"Attempted {len(decision.fallback_attempts)} configured model(s) "
                f"({', '.join(a.model_id for a in decision.fallback_attempts)}), "
                f"but all failed or timed out.\n\n"
                f"**Last Error:** {last_error or 'Provider unavailable'}"
            )
            final_response = ChatResponse(
                id=f"route-err-{uuid.uuid4().hex[:8]}",
                role="assistant",
                content=error_explanation,
                model=decision.selected_model,
                provider=decision.selected_provider,
                finish_reason="error",
            )
            await self._record_telemetry(
                decision=decision,
                success=False,
                error_category="all_providers_failed",
                latency_ms=total_ms,
            )
        else:
            await self._record_telemetry(
                decision=decision,
                success=True,
                error_category=None,
                latency_ms=total_ms,
            )

        return RoutingExecuteResponse(
            decision=decision,
            response=final_response,
            latency_ms=total_ms,
        )

    @staticmethod
    def _normalize_error(exc: Exception) -> Tuple[str, str]:
        msg = str(exc)
        lower = msg.lower()
        if isinstance(exc, asyncio.TimeoutError) or "timeout" in lower or "timed out" in lower:
            return "Provider request timed out.", "timeout"
        if "429" in lower or "rate limit" in lower or "quota" in lower:
            return "Provider rate limit or quota exceeded (HTTP 429).", "rate_limit"
        if "401" in lower or "403" in lower or "unauthorized" in lower or "invalid api key" in lower:
            return "Provider authentication failed (check API key configuration).", "auth_error"
        if "500" in lower or "502" in lower or "503" in lower or "overloaded" in lower or "outage" in lower:
            return "Upstream provider service outage or overload.", "provider_outage"
        # Scrub any potential key patterns just in case
        scrubbed = re.sub(r"(AIza[0-9A-Za-z\-_]+|sk-[0-9A-Za-z\-_]+)", "[REDACTED_KEY]", msg)
        return scrubbed[:180], "provider_error"

    async def _record_telemetry(
        self,
        decision: RoutingDecision,
        success: bool,
        error_category: Optional[str],
        latency_ms: float,
    ) -> None:
        async with self._lock:
            entry = RoutingTelemetryEntry(
                id=f"tel_{uuid.uuid4().hex[:10]}",
                task_category=decision.task_category,
                routing_preference=decision.routing_preference,
                selected_provider=decision.selected_provider,
                selected_model=decision.selected_model,
                used_fallback=decision.used_fallback,
                fallback_count=len(decision.fallback_attempts),
                success=success,
                error_category=error_category,
                latency_ms=latency_ms,
                estimated_tokens=decision.cost_estimate.estimated_total_tokens,
                estimated_cost_usd=decision.cost_estimate.estimated_cost_usd or 0.0,
            )
            self._telemetry.append(entry)
            if len(self._telemetry) > 200:
                self._telemetry = self._telemetry[-200:]

    def get_usage_summary(self) -> RoutingUsageSummary:
        total = len(self._telemetry)
        succ = sum(1 for t in self._telemetry if t.success)
        failed = total - succ
        fallbacks = sum(1 for t in self._telemetry if t.used_fallback)
        tokens = sum(t.estimated_tokens for t in self._telemetry if t.success)
        cost = round(sum(t.estimated_cost_usd for t in self._telemetry if t.success), 6)
        avg_lat = (
            round(sum(t.latency_ms for t in self._telemetry) / total, 2)
            if total > 0
            else 0.0
        )

        by_prov: Dict[str, int] = {}
        by_cat: Dict[str, int] = {}
        by_mod: Dict[str, int] = {}
        for t in self._telemetry:
            by_prov[t.selected_provider] = by_prov.get(t.selected_provider, 0) + 1
            by_cat[t.task_category] = by_cat.get(t.task_category, 0) + 1
            by_mod[t.selected_model] = by_mod.get(t.selected_model, 0) + 1

        remaining = round(max(0.0, self.policy.daily_spending_limit_usd - cost), 6)
        recent = list(reversed(self._telemetry[-25:]))

        return RoutingUsageSummary(
            total_requests=total,
            successful_requests=succ,
            failed_requests=failed,
            fallback_triggered_count=fallbacks,
            total_estimated_tokens=tokens,
            total_estimated_cost_usd=cost,
            daily_spending_limit_usd=self.policy.daily_spending_limit_usd,
            remaining_daily_budget_usd=remaining,
            average_latency_ms=avg_lat,
            by_provider=by_prov,
            by_category=by_cat,
            by_model=by_mod,
            recent_telemetry=recent,
        )

    def clear_telemetry(self) -> None:
        self._telemetry.clear()


model_routing_engine = IntelligentModelRouter()
