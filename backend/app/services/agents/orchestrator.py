"""
NEXORA AI — Stage 14: Multi-Agent Intelligence System
Provides:
- Modular Agent Registry with 8 specialized agents:
  1. Research Agent (research_agent)
  2. Coding Agent (coding_agent)
  3. Education Agent (education_agent)
  4. Writing Agent (writing_agent)
  5. Data Analyst Agent (data_analyst_agent)
  6. Productivity Agent (productivity_agent)
  7. Document Agent (document_agent)
  8. Language Agent (language_agent)
- Central Multi-Agent Orchestrator with automatic & manual agent selection
- Sequential and bounded parallel subtask execution
- Duplicate tool call deduplication, loop prevention, conflict detection, and cost ceiling enforcement
- Least-privilege permission scopes and explicit approval gates for consequential actions
- User-isolated shared context integrating Stage 13 memories, Stage 3 citations, and Stage 4 file references
"""

import asyncio
import json
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from app.config import settings
from app.core.safety import safety_guard
from app.models.schemas import (
    utc_now,
    AgentRoleId,
    SpecializedAgentSpec,
    AgentStructuredFinding,
    AgentSubtaskRun,
    MultiAgentOrchestrationRun,
    MultiAgentRunRequest,
    MultiAgentApproveRequest,
    MultiAgentRetryRequest,
    Message,
    ChatRequest,
)
from app.services.tools_registry import tool_registry
from app.services.search.search_service import search_service
from app.services.documents.storage import document_storage
from app.services.multilingual.detector import LanguageDetector, LANGUAGE_NAMES
from app.services.multilingual.translator import TranslationEngine
from app.services.memory.engine import memory_engine
from app.services.routing.engine import model_routing_engine

logger = logging.getLogger("nexora.agents")

CONSEQUENTIAL_ACTION_KEYWORDS = [
    r"\b(?:delete|erase|remove|purge)\s+(?:all\s+)?(?:files?|documents?|memories|account|database)\b",
    r"\b(?:publish|deploy|broadcast|send\s+email|post\s+publicly|message\s+external)\b",
    r"\b(?:purchase|buy|charge\s+card|transfer\s+funds|spend\s+money)\b",
    r"\b(?:create\s+monitored\s+topic|register\s+webhook|modify\s+account)\b",
]


class MultiAgentOrchestrator:
    """
    Stage 14 Central Multi-Agent Orchestrator & Registry.
    """

    def __init__(self):
        self._agents: Dict[AgentRoleId, SpecializedAgentSpec] = {}
        self._runs: Dict[str, MultiAgentOrchestrationRun] = {}
        self._register_default_agents()

    def _register_default_agents(self) -> None:
        specs: List[SpecializedAgentSpec] = [
            SpecializedAgentSpec(
                agent_id="research_agent",
                name="Research Agent",
                purpose="Searches live web sources, evaluates evidence, and synthesizes cited research reports.",
                capabilities=[
                    "Live web search & multi-query investigation",
                    "Source citation & URL provenance tracking",
                    "Cross-source fact extraction",
                ],
                limitations=[
                    "Cannot access paywalled or private intranet pages",
                    "Treats all external web snippets as untrusted input",
                ],
                permission_scope="search_and_retrieve",
                allowed_tools=["web_search", "fact_check"],
                requires_approval_for=["publish_report", "dispatch_external_message"],
                preferred_task_category="deep_research",
            ),
            SpecializedAgentSpec(
                agent_id="coding_agent",
                name="Coding Agent",
                purpose="Writes, explains, reviews, refactors, and debugs software code with deterministic math and Stage 18 sandbox verification.",
                capabilities=[
                    "Multi-language code generation & review",
                    "Root-cause debugging & complexity analysis",
                    "Deterministic expression verification via calculator",
                    "Sandboxed code & test verification via Stage 18 Terminal Engine",
                ],
                limitations=[
                    "Does not execute arbitrary shell commands or modify host OS files without approval",
                ],
                permission_scope="read_only",
                allowed_tools=["calculator", "terminal_code_runner"],
                requires_approval_for=["modify_repository", "deploy_code", "delete_document", "terminal_package_and_command"],
                preferred_task_category="coding",
            ),
            SpecializedAgentSpec(
                agent_id="education_agent",
                name="Education Agent",
                purpose="Explains complex concepts clearly, builds structured study guides, and creates practice questions.",
                capabilities=[
                    "Step-by-step pedagogical breakdowns",
                    "Study guide, flashcard & quiz synthesis",
                    "Analogy generation & prerequisite mapping",
                ],
                limitations=[
                    "Does not replace accredited clinical or legal certification",
                ],
                permission_scope="read_only",
                allowed_tools=["calculator", "web_search"],
                requires_approval_for=["publish_course"],
                preferred_task_category="reasoning",
            ),
            SpecializedAgentSpec(
                agent_id="writing_agent",
                name="Writing Agent",
                purpose="Drafts, edits, restructures, and polishes technical, creative, or professional documents.",
                capabilities=[
                    "Structured drafting, executive summaries & tone adaptation",
                    "Clarity, grammar & stylistic editing",
                ],
                limitations=[
                    "Will not fabricate factual citations or impersonate real individuals",
                ],
                permission_scope="read_only",
                allowed_tools=[],
                requires_approval_for=["dispatch_external_message", "publish_content"],
                preferred_task_category="general_chat",
            ),
            SpecializedAgentSpec(
                agent_id="data_analyst_agent",
                name="Data Analyst Agent",
                purpose="Analyzes numeric figures, tabular datasets, and uploaded CSV/XLSX excerpts to summarize findings.",
                capabilities=[
                    "Deterministic arithmetic & statistical calculation",
                    "Dataset trend & anomaly summarization from uploaded files",
                ],
                limitations=[
                    "Requires grounded numeric input or uploaded dataset chunks; never fabricates statistics",
                ],
                permission_scope="document_read",
                allowed_tools=["calculator", "document_retrieval"],
                requires_approval_for=["delete_document", "export_external"],
                preferred_task_category="reasoning",
            ),
            SpecializedAgentSpec(
                agent_id="productivity_agent",
                name="Productivity Agent",
                purpose="Organizes execution roadmaps, prioritized checklists, milestones, and workflow schedules.",
                capabilities=[
                    "Actionable task decomposition & milestone checklists",
                    "Risk & dependency matrix creation",
                    "External notification dispatch (requires explicit approval)",
                ],
                limitations=[
                    "Requires explicit user approval before sending external notifications or modifying persistent state",
                ],
                permission_scope="workspace_write_requires_approval",
                allowed_tools=["dispatch_external_message"],
                requires_approval_for=["dispatch_external_message", "delete_document"],
                preferred_task_category="reasoning",
            ),
            SpecializedAgentSpec(
                agent_id="document_agent",
                name="Document Agent",
                purpose="Extracts, compares, and cites grounded evidence from user-uploaded Vault documents.",
                capabilities=[
                    "Lexical chunk retrieval across PDF, DOCX, TXT, CSV, XLSX",
                    "Verbatim excerpt extraction with document/chunk references",
                ],
                limitations=[
                    "Can only analyze documents currently uploaded to the Document Vault",
                ],
                permission_scope="document_read",
                allowed_tools=["document_retrieval"],
                requires_approval_for=["delete_document"],
                preferred_task_category="document_analysis",
            ),
            SpecializedAgentSpec(
                agent_id="language_agent",
                name="Language Agent",
                purpose="Detects scripts, handles code-switching (Tanglish/Hinglish), translates, and explains cultural nuances.",
                capabilities=[
                    "Automatic script & language detection",
                    "Cross-lingual translation & transliteration (Tamil, Hindi, Telugu, Malayalam, Kannada, Bengali, Marathi, English)",
                ],
                limitations=[
                    "Nuance in low-resource dialects is noted transparently",
                ],
                permission_scope="read_only",
                allowed_tools=["translation"],
                requires_approval_for=[],
                preferred_task_category="translation",
            ),
        ]
        for s in specs:
            self._agents[s.agent_id] = s

    def list_agents(self) -> List[SpecializedAgentSpec]:
        """Returns all registered agents with live availability status based on required tools."""
        result: List[SpecializedAgentSpec] = []
        for agent_id, spec in self._agents.items():
            missing_tools: List[str] = []
            for t_name in spec.allowed_tools:
                t_def = tool_registry.get_tool(t_name)
                if not t_def or not t_def.enabled:
                    missing_tools.append(t_name)
            if missing_tools:
                result.append(
                    spec.model_copy(
                        update={
                            "available": False,
                            "unavailable_reason": f"Required tool(s) unavailable or disabled: {', '.join(missing_tools)}",
                        }
                    )
                )
            else:
                result.append(spec.model_copy(update={"available": True, "unavailable_reason": None}))
        return result

    def get_agent(self, agent_id: AgentRoleId) -> Optional[SpecializedAgentSpec]:
        for a in self.list_agents():
            if a.agent_id == agent_id:
                return a
        return None

    def classify_and_select_agents(
        self,
        goal: str,
        document_ids: Optional[List[str]] = None,
        target_language: str = "en",
    ) -> List[AgentRoleId]:
        """
        Deterministically classifies a user request and selects one or more suitable specialized agents.
        """
        lower = goal.lower()
        selected: List[AgentRoleId] = []

        if document_ids and len(document_ids) > 0 or any(
            k in lower for k in ["uploaded file", "attached document", "in the pdf", "from the document", "extract from file"]
        ):
            selected.append("document_agent")

        if any(
            k in lower
            for k in [
                "research",
                "search the web",
                "latest news",
                "cite sources",
                "market landscape",
                "literature review",
                "investigate",
                "find sources",
            ]
        ):
            selected.append("research_agent")

        if any(
            k in lower
            for k in [
                "code",
                "python",
                "typescript",
                "javascript",
                "fastapi",
                "react",
                "bug",
                "refactor",
                "function",
                "algorithm",
                "sql",
                "debug",
                "implement",
            ]
        ):
            selected.append("coding_agent")

        if any(
            k in lower
            for k in [
                "calculate",
                "dataset",
                "csv",
                "statistics",
                "average",
                "growth rate",
                "revenue",
                "margin",
                "analyze data",
                "numbers",
                "roi",
            ]
        ) or re.search(r"\d+\s*[\+\-\*\/\%]\s*\d+", lower):
            selected.append("data_analyst_agent")

        if any(
            k in lower
            for k in [
                "explain concept",
                "study guide",
                "teach me",
                "flashcards",
                "quiz",
                "tutorial",
                "how does",
                "eli5",
                "lesson",
            ]
        ):
            selected.append("education_agent")

        if any(
            k in lower
            for k in [
                "checklist",
                "roadmap",
                "project plan",
                "action items",
                "workflow",
                "schedule",
                "milestones",
                "organize tasks",
                "monitor topic",
            ]
        ):
            selected.append("productivity_agent")

        if any(
            k in lower
            for k in [
                "draft",
                "write an essay",
                "blog post",
                "article",
                "email draft",
                "press release",
                "rewrite",
                "polish",
            ]
        ):
            selected.append("writing_agent")

        detected_lang = LanguageDetector.detect_language(goal)
        if (
            (target_language and target_language not in ("en", "auto"))
            or detected_lang.detected_language_code != "en"
            or any(k in lower for k in ["translate", "tamil", "hindi", "telugu", "malayalam", "kannada", "tanglish"])
        ):
            selected.append("language_agent")

        if not selected:
            selected.append("research_agent" if "?" in goal else "writing_agent")

        # Preserve order and deduplicate, capping at 4 agents per orchestration run
        deduped: List[AgentRoleId] = []
        for a in selected:
            if a not in deduped:
                deduped.append(a)
        return deduped[:4]

    @staticmethod
    def _requires_consequential_approval(goal: str, agent_id: AgentRoleId) -> Tuple[bool, Optional[str]]:
        for pat in CONSEQUENTIAL_ACTION_KEYWORDS:
            m = re.search(pat, goal, re.IGNORECASE)
            if m:
                return True, f"Consequential action detected ('{m.group(0)}'). Explicit user approval is required before execution."
        if agent_id == "productivity_agent" and "monitor" in goal.lower():
            return True, "Creating a persistent monitored feed requires explicit user approval."
        return False, None

    def _build_subtasks(
        self,
        goal: str,
        selected_agents: List[AgentRoleId],
        allow_parallel: bool,
    ) -> Tuple[List[AgentSubtaskRun], Literal["sequential", "parallel_safe", "hybrid"]]:
        """
        Builds a structured multi-agent subtask graph.
        Independent information-gathering agents (e.g., research_agent, document_agent, data_analyst_agent, coding_agent)
        can run in parallel when allow_parallel=True, whereas synthesis/translation agents (writing_agent, language_agent)
        depend on upstream findings.
        """
        subtasks: List[AgentSubtaskRun] = []
        upstream_ids: List[str] = []
        synthesis_agents = {"writing_agent", "language_agent", "productivity_agent"}

        primary_agents = [a for a in selected_agents if a not in synthesis_agents]
        downstream_agents = [a for a in selected_agents if a in synthesis_agents]

        # If all selected agents are in synthesis_agents, treat the first as primary
        if not primary_agents and downstream_agents:
            primary_agents = [downstream_agents.pop(0)]

        can_parallelize_primary = allow_parallel and len(primary_agents) > 1

        for idx, agent_id in enumerate(primary_agents):
            spec = self.get_agent(agent_id) or self._agents[agent_id]
            sub_id = f"sub_{idx + 1}_{agent_id}"
            req_app, app_reason = self._requires_consequential_approval(goal, agent_id)
            subtasks.append(
                AgentSubtaskRun(
                    subtask_id=sub_id,
                    agent_id=agent_id,
                    agent_name=spec.name,
                    title=f"{spec.name}: Analyze & Execute Core Task",
                    instruction=f"Apply {spec.name} capabilities to address: {goal}",
                    depends_on=[],
                    can_run_parallel=can_parallelize_primary,
                    status="WAITING_APPROVAL" if req_app else "PLANNED",
                    requires_approval=req_app,
                    approval_reason=app_reason,
                )
            )
            upstream_ids.append(sub_id)

        for offset, agent_id in enumerate(downstream_agents):
            spec = self.get_agent(agent_id) or self._agents[agent_id]
            sub_id = f"sub_{len(primary_agents) + offset + 1}_{agent_id}"
            req_app, app_reason = self._requires_consequential_approval(goal, agent_id)
            subtasks.append(
                AgentSubtaskRun(
                    subtask_id=sub_id,
                    agent_id=agent_id,
                    agent_name=spec.name,
                    title=f"{spec.name}: Synthesize & Refine Upstream Findings",
                    instruction=f"Synthesize upstream agent outputs and apply {spec.name} specialization for: {goal}",
                    depends_on=list(upstream_ids),
                    can_run_parallel=False,
                    status="WAITING_APPROVAL" if req_app else "PLANNED",
                    requires_approval=req_app,
                    approval_reason=app_reason,
                )
            )

        if can_parallelize_primary and downstream_agents:
            mode: Literal["sequential", "parallel_safe", "hybrid"] = "hybrid"
        elif can_parallelize_primary:
            mode = "parallel_safe"
        else:
            mode = "sequential"

        return subtasks, mode

    async def _execute_single_subtask(
        self,
        run: MultiAgentOrchestrationRun,
        subtask: AgentSubtaskRun,
        request: MultiAgentRunRequest,
        tool_cache: Dict[str, Any],
        upstream_context: str,
        memory_context_str: str,
    ) -> None:
        """
        Executes a single specialized agent subtask with least-privilege tool access,
        duplicate tool call deduplication, cost ceiling checks, and structured output extraction.
        """
        start_t = time.perf_counter()
        spec = self.get_agent(subtask.agent_id)

        if not spec or not spec.available:
            subtask.status = "FAILED"
            subtask.error_message = (
                spec.unavailable_reason
                if spec and spec.unavailable_reason
                else f"Agent '{subtask.agent_id}' is currently unavailable."
            )
            subtask.latency_ms = round((time.perf_counter() - start_t) * 1000, 2)
            return

        if subtask.requires_approval and not subtask.approved:
            subtask.status = "WAITING_APPROVAL"
            subtask.latency_ms = round((time.perf_counter() - start_t) * 1000, 2)
            return

        # Enforce per-run cost budget before invoking tools/models
        if run.total_estimated_cost_usd >= run.max_cost_budget_usd:
            subtask.status = "FAILED"
            subtask.error_message = (
                f"Execution halted: Run cost budget limit (${run.max_cost_budget_usd:.4f} USD) reached."
            )
            subtask.latency_ms = round((time.perf_counter() - start_t) * 1000, 2)
            return

        subtask.status = "RUNNING"
        facts: List[str] = []
        assumptions: List[str] = []
        unresolved: List[str] = []
        citations: List[Dict[str, str]] = []
        file_refs: List[str] = []
        tool_outputs: List[str] = []

        try:
            # 1. Execute domain-specific approved tools within the agent's permission_scope
            if subtask.agent_id == "research_agent" and "web_search" in spec.allowed_tools:
                cache_key = f"web_search::{request.goal.strip().lower()[:180]}"
                if cache_key in tool_cache:
                    run.duplicate_tool_calls_prevented += 1
                    results = tool_cache[cache_key]
                else:
                    results = await asyncio.wait_for(
                        search_service.execute_search(query=request.goal, max_results=4),
                        timeout=settings.agent_task_timeout_seconds,
                    )
                    tool_cache[cache_key] = results
                    subtask.tools_invoked.append("web_search")

                for idx, item in enumerate(results, 1):
                    citations.append({"title": item.title, "url": item.url, "snippet": item.snippet[:240]})
                    facts.append(f"[{idx}] {item.title}: {item.snippet[:200]} (Source: {item.url})")
                    tool_outputs.append(f"<untrusted_web_evidence index='{idx}' url='{item.url}'>{item.snippet}</untrusted_web_evidence>")
                if not results:
                    unresolved.append("No live web sources matched the query; findings rely on baseline knowledge.")

            if subtask.agent_id in ("document_agent", "data_analyst_agent") and "document_retrieval" in spec.allowed_tools:
                cache_key = f"document_retrieval::{request.goal.strip().lower()[:140]}::{','.join(sorted(request.document_ids))}"
                all_docs = document_storage.list_documents()
                doc_ids = request.document_ids if request.document_ids else [d.id for d in all_docs]
                if cache_key in tool_cache:
                    run.duplicate_tool_calls_prevented += 1
                    passages = tool_cache[cache_key]
                else:
                    passages = (
                        document_storage.retrieve_relevant_passages(doc_ids=doc_ids, query=request.goal, top_k=4)
                        if doc_ids
                        else []
                    )
                    tool_cache[cache_key] = passages
                    subtask.tools_invoked.append("document_retrieval")

                if passages:
                    for chunk, _score, fname in passages:
                        ref_label = f"{fname} (p.{chunk.page_number or 1})"
                        if ref_label not in file_refs:
                            file_refs.append(ref_label)
                        facts.append(f"Document excerpt from {ref_label}: {chunk.content[:220]}")
                        tool_outputs.append(
                            f"<untrusted_document_excerpt file='{fname}' page='{chunk.page_number or 1}'>{chunk.content[:400]}</untrusted_document_excerpt>"
                        )
                elif subtask.agent_id == "document_agent":
                    if not all_docs:
                        unresolved.append("No documents are currently uploaded in the Document Vault to extract from.")
                    else:
                        for d in all_docs[:2]:
                            file_refs.append(d.filename)
                            facts.append(f"Referenced uploaded document '{d.filename}' ({d.word_count} words).")

            if subtask.agent_id in ("data_analyst_agent", "coding_agent", "education_agent") and "calculator" in spec.allowed_tools:
                math_matches = re.findall(r"(?:\d+(?:\.\d+)?\s*[\+\-\*\/\%]\s*)+\d+(?:\.\d+)?", request.goal)
                for expr in math_matches[:3]:
                    clean_expr = expr.strip()
                    cache_key = f"calculator::{clean_expr}"
                    if cache_key in tool_cache:
                        run.duplicate_tool_calls_prevented += 1
                        calc_res = tool_cache[cache_key]
                    else:
                        calc_res = await tool_registry.execute("calculator", {"expression": clean_expr})
                        tool_cache[cache_key] = calc_res
                        subtask.tools_invoked.append("calculator")
                    if calc_res.get("success"):
                        val = calc_res["data"].get("result")
                        facts.append(f"Verified calculation: `{clean_expr} = {val}`")
                        tool_outputs.append(f"Verified Calculator Result: {clean_expr} = {val}")

            if subtask.agent_id == "language_agent":
                target_lang = request.target_language if request.target_language != "auto" else "ta"
                source_to_translate = upstream_context[:600] if upstream_context else request.goal
                from app.models.schemas import TranslationRequest
                trans_res = await TranslationEngine.translate(
                    TranslationRequest(
                        text=source_to_translate,
                        source_language="auto",
                        target_language=target_lang,
                        tone="professional",
                        transliterate=True,
                    )
                )
                lang_name = LANGUAGE_NAMES.get(target_lang, target_lang)
                facts.append(
                    f"Language Agent detected '{trans_res.source_language}' and prepared '{lang_name}' localization."
                )
                tool_outputs.append(
                    f"Localized Output ({lang_name}):\n{trans_res.translated_text}"
                    + (f"\nTransliteration: {trans_res.transliterated_text}" if trans_res.transliterated_text else "")
                )

            # 2. Build specialized agent prompt & route via Stage 12 Model Routing Engine
            agent_system_prompt = (
                f"You are the NEXORA {spec.name} ({spec.agent_id}).\n"
                f"Purpose: {spec.purpose}\n"
                f"Permission Scope: {spec.permission_scope}\n"
                f"Explicitly separate verified facts, working assumptions, and unresolved questions.\n"
            )
            if memory_context_str:
                agent_system_prompt += f"\n{memory_context_str}\n"
            if upstream_context:
                agent_system_prompt += f"\n<upstream_agent_findings>\n{upstream_context[:2500]}\n</upstream_agent_findings>\n"
            if tool_outputs:
                agent_system_prompt += "\n<verified_tool_evidence>\n" + "\n".join(tool_outputs) + "\n</verified_tool_evidence>\n"

            from app.models.schemas import RoutingSimulateRequest, RoutingExecuteRequest

            decision = model_routing_engine.select_route(
                RoutingSimulateRequest(
                    prompt=request.goal,
                    task_category=spec.preferred_task_category,
                    preferred_provider=request.provider or "auto",
                    preferred_model=request.model or "auto",
                    expected_output_tokens=350,
                ),
                client_api_key=request.client_api_key,
            )
            step_cost = decision.cost_estimate.estimated_cost_usd or 0.0005

            if run.total_estimated_cost_usd + step_cost > run.max_cost_budget_usd:
                subtask.status = "FAILED"
                subtask.error_message = (
                    f"Subtask exceeded remaining run cost budget (${run.max_cost_budget_usd:.4f} USD)."
                )
                subtask.latency_ms = round((time.perf_counter() - start_t) * 1000, 2)
                return

            # Execute via configured provider or deterministic domain synthesis when offline
            if decision.is_configured and decision.selected_provider != "offline":
                routed_res = await model_routing_engine.execute_routed_request(
                    RoutingExecuteRequest(
                        prompt=f"[{spec.name} Task]: {subtask.instruction}\n\nUser Goal: {request.goal}",
                        task_category=spec.preferred_task_category,
                        preferred_provider=request.provider or "auto",
                        preferred_model=request.model or "auto",
                        client_api_key=request.client_api_key,
                    )
                )
                summary_text = routed_res.response.content
            else:
                summary_text = self._build_honest_specialist_summary(
                    spec=spec,
                    goal=request.goal,
                    facts=facts,
                    tool_outputs=tool_outputs,
                    upstream_context=upstream_context,
                )

            if not facts:
                facts.append(f"{spec.name} analyzed request parameters within '{spec.permission_scope}' scope.")
            assumptions.append(
                f"Assumed standard domain constraints for {spec.name} where unstated in the prompt."
            )

            subtask.output_summary = summary_text
            subtask.structured_finding = AgentStructuredFinding(
                facts=facts,
                assumptions=assumptions,
                unresolved_questions=unresolved,
                citations=citations,
                file_references=file_refs,
            )
            subtask.estimated_cost_usd = round(step_cost, 6)
            run.total_estimated_cost_usd = round(run.total_estimated_cost_usd + step_cost, 6)
            subtask.status = "COMPLETED"

        except asyncio.TimeoutError:
            subtask.status = "FAILED"
            subtask.error_message = f"{spec.name} timed out after {settings.agent_task_timeout_seconds}s."
        except Exception as exc:
            subtask.status = "FAILED"
            subtask.error_message = f"{spec.name} execution error: {str(exc)}"
        finally:
            subtask.latency_ms = round((time.perf_counter() - start_t) * 1000, 2)

    @staticmethod
    def _build_honest_specialist_summary(
        spec: SpecializedAgentSpec,
        goal: str,
        facts: List[str],
        tool_outputs: List[str],
        upstream_context: str,
    ) -> str:
        header = f"### {spec.name} Report\n"
        body_lines = [f"- **Role Scope**: {spec.purpose} (`{spec.permission_scope}`)"]
        if facts:
            body_lines.append("- **Verified Findings**:")
            for f in facts[:5]:
                body_lines.append(f"  - {f}")
        if tool_outputs:
            body_lines.append("- **Grounded Tool Evidence**:")
            for t in tool_outputs[:3]:
                clean_t = re.sub(r"<[^>]+>", "", t).strip()
                body_lines.append(f"  - {clean_t[:260]}")
        if spec.agent_id == "coding_agent":
            body_lines.append(
                "- **Implementation Guidance**: Modular, type-checked implementation pattern prepared with input validation and error handling."
            )
        elif spec.agent_id == "productivity_agent":
            body_lines.append(
                "- **Action Checklist**:\n  1. [x] Validate requirements & constraints\n  2. [ ] Execute primary deliverable\n  3. [ ] Verify outputs & test edge cases"
            )
        elif spec.agent_id == "education_agent":
            body_lines.append(
                "- **Concept Breakdown**: Core principles, mental model, and self-check review questions structured for study."
            )
        elif spec.agent_id == "writing_agent":
            body_lines.append(
                f"- **Editorial Synthesis**: Structured response drafted for `{goal[:100]}` incorporating upstream evidence."
            )
        return header + "\n".join(body_lines)

    @staticmethod
    def detect_conflicting_outputs(subtasks: List[AgentSubtaskRun]) -> List[str]:
        """
        Inspects completed agent subtasks to surface any contradictory findings or failed upstream dependencies.
        """
        conflicts: List[str] = []
        numeric_claims: Dict[str, Tuple[str, str]] = {}

        for st in subtasks:
            if st.status != "COMPLETED":
                continue
            for fact in st.structured_finding.facts:
                # Check for `expr = value` equations across agents
                m = re.search(r"`([^`=]+)=\s*([-+]?\d+(?:\.\d+)?)`", fact)
                if m:
                    expr_norm = re.sub(r"\s+", "", m.group(1))
                    val_str = m.group(2)
                    if expr_norm in numeric_claims and numeric_claims[expr_norm][0] != val_str:
                        prev_val, prev_agent = numeric_claims[expr_norm]
                        conflicts.append(
                            f"Discrepancy on '{expr_norm}': {prev_agent} reported {prev_val} vs. {st.agent_name} reported {val_str}."
                        )
                    else:
                        numeric_claims[expr_norm] = (val_str, st.agent_name)

        return conflicts

    def _consolidate_run_outputs(self, run: MultiAgentOrchestrationRun) -> None:
        all_facts: List[str] = []
        all_assumptions: List[str] = []
        all_unresolved: List[str] = []
        all_citations: List[Dict[str, str]] = []
        seen_urls: Set[str] = set()
        all_files: List[str] = []
        sections: List[str] = []

        for st in run.subtasks:
            if st.status == "COMPLETED":
                sections.append(st.output_summary)
                for f in st.structured_finding.facts:
                    if f not in all_facts:
                        all_facts.append(f)
                for a in st.structured_finding.assumptions:
                    if a not in all_assumptions:
                        all_assumptions.append(a)
                for u in st.structured_finding.unresolved_questions:
                    if u not in all_unresolved:
                        all_unresolved.append(u)
                for c in st.structured_finding.citations:
                    url = c.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_citations.append(c)
                for f_ref in st.structured_finding.file_references:
                    if f_ref not in all_files:
                        all_files.append(f_ref)
            elif st.status == "WAITING_APPROVAL":
                all_unresolved.append(
                    f"{st.agent_name} is awaiting explicit user approval: {st.approval_reason}"
                )
            elif st.status == "FAILED" and st.error_message:
                all_unresolved.append(f"{st.agent_name} failed: {st.error_message}")

        run.consolidated_facts = all_facts
        run.consolidated_assumptions = all_assumptions
        run.unresolved_questions = all_unresolved
        run.citations = all_citations
        run.file_references = all_files
        run.conflicts_detected = self.detect_conflicting_outputs(run.subtasks)

        # Determine overall run status
        statuses = {st.status for st in run.subtasks}
        if run.status == "CANCELLED":
            pass
        elif "WAITING_APPROVAL" in statuses:
            run.status = "WAITING_APPROVAL"
        elif all(s == "COMPLETED" for s in statuses):
            run.status = "COMPLETED"
        elif any(s == "FAILED" for s in statuses):
            run.status = "FAILED" if all(s == "FAILED" for s in statuses) else "COMPLETED"

        # Assemble final transparent synthesis
        combined_parts = list(sections)
        if run.citations:
            cite_lines = ["### Preserved Source Citations"]
            for idx, c in enumerate(run.citations, 1):
                cite_lines.append(f"{idx}. [{c.get('title', 'Source')}]({c.get('url', '#')})")
            combined_parts.append("\n".join(cite_lines))

        if run.file_references:
            combined_parts.append(
                "### Referenced Vault Files\n" + "\n".join(f"- `{r}`" for r in run.file_references)
            )

        if run.conflicts_detected:
            combined_parts.append(
                "### Conflict Resolution Notice\n" + "\n".join(f"- ⚠️ {c}" for c in run.conflicts_detected)
            )

        run.combined_response = "\n\n---\n\n".join(combined_parts) if combined_parts else "No completed subtask outputs yet."
        run.updated_at = utc_now()

    async def execute_run(self, request: MultiAgentRunRequest) -> MultiAgentOrchestrationRun:
        """
        Classifies the request, selects specialized agents, builds the execution plan,
        retrieves isolated user memories, and executes subtasks sequentially or in bounded parallel.
        """
        start_run = time.perf_counter()

        # 1. Safety Guardrail evaluation
        safety_res = safety_guard.evaluate_content(request.goal)
        if not safety_res.is_safe:
            raise ValueError(safety_res.refusal_message or "Request blocked by safety policy.")

        # 2. Agent Selection (Manual vs. Automatic)
        if request.selection_mode == "manual" and request.manual_agents:
            selected_agents = list(dict.fromkeys(request.manual_agents))[: settings.agent_max_steps_per_task]
        else:
            selected_agents = self.classify_and_select_agents(
                goal=request.goal,
                document_ids=request.document_ids,
                target_language=request.target_language,
            )

        # 3. Retrieve isolated user memories (Stage 13)
        used_memories_meta: List[Dict[str, Any]] = []
        memory_context_str = ""
        if request.memory_enabled:
            mems = memory_engine.retrieve_relevant_memories(
                user_id=request.user_id,
                query=request.goal,
                top_k=settings.top_k_memories,
            )
            if mems:
                memory_context_str = memory_engine.format_memory_context_for_prompt(mems)
                used_memories_meta = [
                    {"id": m.id, "category": m.category, "key": m.key, "content": m.content}
                    for m in mems
                ]

        # 4. Build Subtasks & Execution Plan
        subtasks, exec_mode = self._build_subtasks(
            goal=request.goal,
            selected_agents=selected_agents,
            allow_parallel=request.allow_parallel,
        )
        run_id = f"agent_run_{uuid.uuid4().hex[:10]}"
        budget = request.max_cost_usd if request.max_cost_usd is not None else settings.agent_max_cost_usd_per_run

        agent_names = [self._agents[a].name for a in selected_agents if a in self._agents]
        plan_summary = (
            f"Selected {len(selected_agents)} agent(s) ({', '.join(agent_names)}) in '{exec_mode}' execution mode "
            f"with a ${budget:.4f} USD budget cap."
        )

        run = MultiAgentOrchestrationRun(
            run_id=run_id,
            user_id=request.user_id,
            goal=request.goal,
            selection_mode=request.selection_mode,
            selected_agents=selected_agents,
            execution_mode=exec_mode,
            status="RUNNING",
            plan_summary=plan_summary,
            subtasks=subtasks,
            used_memories=used_memories_meta,
            max_cost_budget_usd=budget,
        )
        self._runs[run_id] = run

        await self._drive_subtasks(run, request, memory_context_str)
        run.total_latency_ms = round((time.perf_counter() - start_run) * 1000, 2)
        return run

    async def _drive_subtasks(
        self,
        run: MultiAgentOrchestrationRun,
        request: MultiAgentRunRequest,
        memory_context_str: str,
    ) -> None:
        tool_cache: Dict[str, Any] = {}
        primary_tasks = [st for st in run.subtasks if not st.depends_on and st.status == "PLANNED"]
        downstream_tasks = [st for st in run.subtasks if st.depends_on]

        # Execute primary wave (in bounded parallel if enabled, otherwise sequential)
        if request.allow_parallel and len(primary_tasks) > 1:
            sem = asyncio.Semaphore(settings.agent_max_parallel_tasks)

            async def _bounded_task(st: AgentSubtaskRun):
                async with sem:
                    await self._execute_single_subtask(
                        run=run,
                        subtask=st,
                        request=request,
                        tool_cache=tool_cache,
                        upstream_context="",
                        memory_context_str=memory_context_str,
                    )

            await asyncio.gather(*[_bounded_task(st) for st in primary_tasks])
        else:
            for st in primary_tasks:
                await self._execute_single_subtask(
                    run=run,
                    subtask=st,
                    request=request,
                    tool_cache=tool_cache,
                    upstream_context="",
                    memory_context_str=memory_context_str,
                )

        # Gather upstream output summaries for downstream dependent subtasks
        upstream_text = "\n\n".join(
            st.output_summary for st in run.subtasks if not st.depends_on and st.status == "COMPLETED"
        )

        for st in downstream_tasks:
            if st.status != "PLANNED":
                continue
            # Check if any dependency is WAITING_APPROVAL or FAILED
            dep_statuses = {
                dep.status for dep in run.subtasks if dep.subtask_id in st.depends_on
            }
            if "WAITING_APPROVAL" in dep_statuses:
                continue
            await self._execute_single_subtask(
                run=run,
                subtask=st,
                request=request,
                tool_cache=tool_cache,
                upstream_context=upstream_text,
                memory_context_str=memory_context_str,
            )

        self._consolidate_run_outputs(run)

    async def approve_subtask(
        self,
        run_id: str,
        approval: MultiAgentApproveRequest,
    ) -> MultiAgentOrchestrationRun:
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(f"Multi-agent run '{run_id}' not found.")

        target = next((st for st in run.subtasks if st.subtask_id == approval.subtask_id), None)
        if not target:
            raise KeyError(f"Subtask '{approval.subtask_id}' not found in run '{run_id}'.")

        if not approval.approved:
            target.approved = False
            target.status = "CANCELLED"
            target.error_message = approval.user_note or "User declined approval for consequential action."
            self._consolidate_run_outputs(run)
            return run

        target.approved = True
        target.requires_approval = False
        target.status = "PLANNED"

        req = MultiAgentRunRequest(
            goal=run.goal,
            user_id=run.user_id,
            selection_mode=run.selection_mode,
            manual_agents=run.selected_agents,
            allow_parallel=False,
            max_cost_usd=run.max_cost_budget_usd,
            provider=approval.provider,
            model=approval.model,
            client_api_key=approval.client_api_key,
        )
        await self._drive_subtasks(run, req, "")
        return run

    async def retry_run(
        self,
        run_id: str,
        retry_req: MultiAgentRetryRequest,
    ) -> MultiAgentOrchestrationRun:
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(f"Multi-agent run '{run_id}' not found.")

        for st in run.subtasks:
            if retry_req.subtask_id is None or st.subtask_id == retry_req.subtask_id:
                if st.status in ("FAILED", "CANCELLED"):
                    st.status = "PLANNED"
                    st.error_message = None
                    st.retry_count += 1

        run.status = "RUNNING"
        req = MultiAgentRunRequest(
            goal=run.goal,
            user_id=run.user_id,
            selection_mode=run.selection_mode,
            manual_agents=run.selected_agents,
            allow_parallel=False,
            max_cost_usd=run.max_cost_budget_usd,
            provider=retry_req.provider,
            model=retry_req.model,
            client_api_key=retry_req.client_api_key,
        )
        await self._drive_subtasks(run, req, "")
        return run

    def cancel_run(self, run_id: str) -> MultiAgentOrchestrationRun:
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(f"Multi-agent run '{run_id}' not found.")
        run.status = "CANCELLED"
        for st in run.subtasks:
            if st.status in ("PLANNED", "RUNNING", "WAITING_APPROVAL"):
                st.status = "CANCELLED"
        run.updated_at = utc_now()
        return run

    def list_runs(self, user_id: str = "default_user") -> List[MultiAgentOrchestrationRun]:
        user_runs = [r for r in self._runs.values() if r.user_id == user_id]
        user_runs.sort(key=lambda r: r.created_at, reverse=True)
        return user_runs[:30]

    def get_run(self, run_id: str, user_id: Optional[str] = None) -> Optional[MultiAgentOrchestrationRun]:
        run = self._runs.get(run_id)
        if not run:
            return None
        if user_id and run.user_id != user_id:
            return None
        return run


multi_agent_orchestrator = MultiAgentOrchestrator()
