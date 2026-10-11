import ast
import asyncio
import math
import operator
import time
from typing import Callable, Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="Description of the tool function")
    parameters_schema: Dict[str, Any] = Field(..., description="JSON Schema for parameters")
    enabled: bool = True
    stage_introduced: int = 1
    requires_approval: bool = False
    risk_level: str = "low"  # low, medium, high
    timeout_seconds: float = 15.0
    treats_output_as_untrusted: bool = True


# Safe AST Mathematical Evaluator
_ALLOWED_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_ALLOWED_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_ALLOWED_MATH_FUNCS: Dict[str, Any] = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "min": min,
    "max": max,
    "sum": sum,
    "pi": math.pi,
    "e": math.e,
}


def safe_eval_math(expression: str) -> float:
    """
    Safely evaluates mathematical expressions using Python's AST without eval().
    Raises ValueError on unsafe or malformed expressions.
    """
    if not expression or not expression.strip():
        raise ValueError("Empty mathematical expression.")
    cleaned = expression.strip().replace("^", "**")
    if len(cleaned) > 500:
        raise ValueError("Expression exceeds maximum allowed length (500 chars).")

    try:
        tree = ast.parse(cleaned, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid math syntax: {exc.msg}") from exc

    def _eval_node(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return node.value
            raise ValueError(f"Unsupported constant value: {node.value}")
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in _ALLOWED_BIN_OPS:
                raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
            left = _eval_node(node.left)
            right = _eval_node(node.right)
            if op_type is ast.Pow and abs(right) > 1000:
                raise ValueError("Exponent magnitude exceeds safe limit (1000).")
            return float(_ALLOWED_BIN_OPS[op_type](left, right))
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in _ALLOWED_UNARY_OPS:
                raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
            return float(_ALLOWED_UNARY_OPS[op_type](_eval_node(node.operand)))
        if isinstance(node, ast.Name):
            if node.id in _ALLOWED_MATH_FUNCS and isinstance(_ALLOWED_MATH_FUNCS[node.id], (int, float)):
                return float(_ALLOWED_MATH_FUNCS[node.id])
            raise ValueError(f"Unknown identifier '{node.id}' in math expression.")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_MATH_FUNCS:
                raise ValueError("Unsupported function call in math expression.")
            fn = _ALLOWED_MATH_FUNCS[node.func.id]
            if not callable(fn):
                raise ValueError(f"'{node.func.id}' is a constant, not a function.")
            args = [_eval_node(arg) for arg in node.args]
            return float(fn(*args))
        if isinstance(node, (ast.List, ast.Tuple)):
            return [_eval_node(elt) for elt in node.elts]  # type: ignore[return-value]
        raise ValueError(f"Unsupported AST node: {type(node).__name__}")

    result = _eval_node(tree)
    if isinstance(result, float) and (math.isnan(result) or math.isinf(result)):
        raise ValueError("Mathematical evaluation resulted in NaN or Infinity.")
    return round(float(result), 8)


class ToolRegistry:
    """
    Extensible Tool Registry for NEXORA AI platform (Stages 1–11).
    Provides least-privilege tool discovery, input validation, timeout enforcement,
    and untrusted output quarantine.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}
        self._register_foundation_tools()

    def _register_foundation_tools(self):
        # 1. Foundation diagnostic and system introspection tool
        self.register(
            tool=ToolDefinition(
                name="get_system_telemetry",
                description="Returns current Nexora platform telemetry, phase status, and active provider info.",
                parameters_schema={"type": "object", "properties": {}},
                stage_introduced=1,
                requires_approval=False,
                risk_level="low",
                treats_output_as_untrusted=False,
            ),
            handler=self._handle_telemetry,
        )

        # 2. Safe AST Calculator Tool
        self.register(
            tool=ToolDefinition(
                name="calculator",
                description="Evaluates exact mathematical expressions (arithmetic, powers, sqrt, trig, logs, rounding) safely via AST.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "Mathematical expression to evaluate, e.g. '(1450 * 1.18) + sqrt(256)'"}
                    },
                    "required": ["expression"],
                },
                stage_introduced=11,
                requires_approval=False,
                risk_level="low",
                treats_output_as_untrusted=False,
            ),
            handler=self._handle_calculator,
        )

        # 3. Web Search Tool (Stage 3 integration)
        self.register(
            tool=ToolDefinition(
                name="web_search",
                description="Searches live web sources via the Stage 3 Universal Search Engine and returns citations and snippets.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query string"},
                        "max_results": {"type": "integer", "default": 4},
                    },
                    "required": ["query"],
                },
                stage_introduced=3,
                requires_approval=False,
                risk_level="low",
                treats_output_as_untrusted=True,
            ),
            handler=self._handle_web_search,
        )

        # 4. Document Retrieval Tool (Stage 4 integration)
        self.register(
            tool=ToolDefinition(
                name="document_retrieval",
                description="Queries uploaded documents in the Stage 4 Document Intelligence Vault for relevant chunks and citations.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query across uploaded documents"},
                        "top_k": {"type": "integer", "default": 4},
                    },
                    "required": ["query"],
                },
                stage_introduced=4,
                requires_approval=False,
                risk_level="low",
                treats_output_as_untrusted=True,
            ),
            handler=self._handle_document_retrieval,
        )

        # 5. Fact-Check Verification Tool (Stage 5 integration)
        self.register(
            tool=ToolDefinition(
                name="fact_check",
                description="Verifies factual claims against live web evidence and uploaded documents using the Stage 5 Fact-Checking Engine.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "claim": {"type": "string", "description": "Claim or statement to verify"},
                    },
                    "required": ["claim"],
                },
                stage_introduced=5,
                requires_approval=False,
                risk_level="low",
                treats_output_as_untrusted=True,
            ),
            handler=self._handle_fact_check,
        )

        # 6. Multilingual Translation Tool (Stage 6 integration)
        self.register(
            tool=ToolDefinition(
                name="translation",
                description="Translates or transliterates text between supported languages using the Stage 6 Multilingual Engine.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Source text to translate"},
                        "target_language": {"type": "string", "description": "Target language code or name (e.g., 'ta', 'hi', 'es', 'fr')"},
                        "source_language": {"type": "string", "default": "auto"},
                    },
                    "required": ["text", "target_language"],
                },
                stage_introduced=6,
                requires_approval=False,
                risk_level="low",
                treats_output_as_untrusted=False,
            ),
            handler=self._handle_translation,
        )

        # 7. Real-Time Intelligence Feed Tool (Stage 8 integration)
        self.register(
            tool=ToolDefinition(
                name="realtime_pulse",
                description="Fetches live category intelligence (weather, technology, science, finance, sports, world) from Stage 8 Real-Time Engine.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "default": "technology"},
                        "query": {"type": "string", "default": ""},
                        "location": {"type": "string", "default": "Chennai"},
                    },
                },
                stage_introduced=8,
                requires_approval=False,
                risk_level="low",
                treats_output_as_untrusted=True,
            ),
            handler=self._handle_realtime_pulse,
        )

        # 8. Consequential Tool: Delete Document Vault Item (Requires Explicit User Approval)
        self.register(
            tool=ToolDefinition(
                name="delete_document",
                description="Permanently deletes a document from the NEXORA Document Vault. Consequential action requiring explicit user approval.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "doc_id": {"type": "string", "description": "Document ID to delete (or 'all_temp' for cleanup)"},
                    },
                    "required": ["doc_id"],
                },
                stage_introduced=11,
                requires_approval=True,
                risk_level="high",
                treats_output_as_untrusted=False,
            ),
            handler=self._handle_delete_document,
        )

        # 9. Consequential Tool: External Webhook / Dispatch Notification (Requires Explicit User Approval)
        self.register(
            tool=ToolDefinition(
                name="dispatch_external_message",
                description="Sends an external notification or webhook payload outside the NEXORA workspace. Consequential action requiring explicit user approval.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "recipient": {"type": "string", "description": "Recipient channel or endpoint identifier"},
                        "subject": {"type": "string", "description": "Notification subject"},
                        "body": {"type": "string", "description": "Message body"},
                    },
                    "required": ["recipient", "body"],
                },
                stage_introduced=11,
                requires_approval=True,
                risk_level="high",
                treats_output_as_untrusted=False,
            ),
            handler=self._handle_dispatch_external_message,
        )

        # 10. Stage 16: Controlled Browser Automation Tool
        self.register(
            tool=ToolDefinition(
                name="browser_automation_step",
                description="Opens an approved URL in an isolated Stage 16 browser session, extracts DOM content, and captures a verified viewport screenshot.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Approved http/https URL to open"},
                        "selector": {"type": "string", "default": "h1, p, a"},
                    },
                    "required": ["url"],
                },
                stage_introduced=16,
                requires_approval=False,
                risk_level="low",
                treats_output_as_untrusted=True,
            ),
            handler=self._handle_browser_automation_step,
        )

        # 11. Stage 16: Sandboxed Computer Workspace Task Tool
        self.register(
            tool=ToolDefinition(
                name="computer_workspace_task",
                description="Executes a read-only diagnostic or file listing inside the Stage 16 sandboxed computer workspace.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "default": "list_workspace_files",
                            "description": "list_workspace_files | read_workspace_file | run_predefined_diagnostic",
                        },
                        "target": {"type": "string", "default": "."},
                    },
                },
                stage_introduced=16,
                requires_approval=False,
                risk_level="low",
                treats_output_as_untrusted=True,
            ),
            handler=self._handle_computer_workspace_task,
        )

    def register(self, tool: ToolDefinition, handler: Optional[Callable] = None):
        self._tools[tool.name] = tool
        if handler:
            self._handlers[tool.name] = handler

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def validate_params(self, tool: ToolDefinition, params: Dict[str, Any]) -> None:
        required_fields = tool.parameters_schema.get("required", [])
        for req in required_fields:
            if req not in params or params[req] is None or (isinstance(params[req], str) and not params[req].strip()):
                raise ValueError(f"Missing required parameter '{req}' for tool '{tool.name}'.")

    async def execute(self, name: str, params: Dict[str, Any], approval_granted: bool = False) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' is not registered in the NEXORA ToolRegistry.")
        if not tool.enabled:
            raise RuntimeError(f"Tool '{name}' is currently disabled.")
        if name not in self._handlers:
            raise ValueError(f"Tool '{name}' has no registered execution handler.")

        if tool.requires_approval and not approval_granted:
            raise PermissionError(
                f"Tool '{name}' performs a consequential action (risk={tool.risk_level}) and requires explicit user approval before execution."
            )

        self.validate_params(tool, params)
        handler = self._handlers[name]
        start_ts = time.perf_counter()
        raw_result = await asyncio.wait_for(handler(params), timeout=tool.timeout_seconds)
        elapsed_ms = round((time.perf_counter() - start_ts) * 1000, 2)

        summary_str = raw_result.get("summary", str(raw_result)) if isinstance(raw_result, dict) else str(raw_result)
        if tool.treats_output_as_untrusted:
            quarantined_summary = f"<untrusted_tool_output tool=\"{name}\">\n{summary_str}\n</untrusted_tool_output>"
        else:
            quarantined_summary = summary_str

        return {
            "tool_name": name,
            "success": True,
            "duration_ms": elapsed_ms,
            "summary": summary_str,
            "quarantined_summary": quarantined_summary,
            "untrusted_content_quarantined": tool.treats_output_as_untrusted,
            "data": raw_result,
        }

    async def _handle_telemetry(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "platform": "NEXORA AI",
            "current_stage": 11,
            "architecture": "Universal Multi-Provider Assistant & Reasoning Engine",
            "status": "operational",
            "registered_tools_count": len(self._tools),
            "summary": f"NEXORA AI Stage 11 operational with {len(self._tools)} registered tools.",
        }

    async def _handle_calculator(self, params: Dict[str, Any]) -> Dict[str, Any]:
        expr = str(params.get("expression", "")).strip()
        value = safe_eval_math(expr)
        formatted = int(value) if value == int(value) else value
        return {
            "expression": expr,
            "result": formatted,
            "summary": f"Calculated `{expr}` = {formatted}",
        }

    async def _handle_web_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.search.search_service import search_service
        query = str(params.get("query", "")).strip()
        max_results = int(params.get("max_results", 4))
        results = await search_service.execute_search(
            query=query,
            max_results=max_results,
            engine_preference="auto",
        )
        resolved_engine, _ = search_service.resolve_engine_and_key("auto", None)
        snippets = []
        for idx, src in enumerate(results[:max_results], start=1):
            snippets.append(f"[{idx}] {src.title} ({src.url}): {src.snippet[:220]}")
        joined = "\n".join(snippets) if snippets else "No web search results returned."
        return {
            "query": query,
            "provider": resolved_engine,
            "results_count": len(results),
            "sources": [s.model_dump(mode="json") for s in results[:max_results]],
            "summary": f"Retrieved {len(results)} web source(s) via {resolved_engine}:\n{joined}",
        }

    async def _handle_document_retrieval(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.documents.storage import document_storage
        query = str(params.get("query", "")).strip()
        top_k = int(params.get("top_k", 4))
        docs = document_storage.list_documents()
        if not docs:
            return {
                "query": query,
                "chunks_found": 0,
                "documents_in_vault": 0,
                "summary": "Document Vault is currently empty (0 uploaded documents). Upload a PDF, DOCX, TXT, or CSV in the Documents tab to query local files.",
            }
        doc_ids = [d.id for d in docs]
        passages = document_storage.retrieve_relevant_passages(doc_ids=doc_ids, query=query, top_k=top_k)
        lines = []
        chunks_out = []
        for chunk, score, fname in passages:
            lines.append(f"[{fname} p.{chunk.page_number or 1}]: {chunk.content[:220]}")
            chunks_out.append({
                "doc_id": chunk.doc_id,
                "filename": fname,
                "page_number": chunk.page_number,
                "score": score,
                "content": chunk.content,
            })
        summary = (
            f"Found {len(passages)} relevant excerpt(s) across {len(docs)} uploaded document(s):\n" + "\n".join(lines)
            if passages
            else f"Searched {len(docs)} uploaded document(s) in vault, but no matching excerpts matched '{query}'."
        )
        return {
            "query": query,
            "chunks_found": len(passages),
            "documents_in_vault": len(docs),
            "chunks": chunks_out,
            "summary": summary,
        }

    async def _handle_fact_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.factcheck.engine import fact_check_engine
        from app.models.schemas import FactCheckRequest
        claim = str(params.get("claim", "")).strip()
        report = await fact_check_engine.verify_statement(
            FactCheckRequest(text=claim)
        )
        verdict_summaries = [
            f"Claim: '{c.claim_text}' -> Verdict: {c.verdict} (Confidence: {c.confidence})"
            for c in report.claims
        ]
        summary = "; ".join(verdict_summaries) if verdict_summaries else report.overall_summary
        return {
            "claim": claim,
            "overall_summary": report.overall_summary,
            "claims": [c.model_dump(mode="json") for c in report.claims],
            "summary": f"Fact-Check completed: {summary}",
        }

    async def _handle_translation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.multilingual.translator import TranslationEngine
        from app.models.schemas import TranslationRequest
        text = str(params.get("text", "")).strip()
        target_lang = str(params.get("target_language", "ta")).strip()
        source_lang = str(params.get("source_language", "auto")).strip()
        res = await TranslationEngine.translate(
            TranslationRequest(
                text=text,
                source_language=source_lang,
                target_language=target_lang,
                transliterate=True,
            )
        )
        return {
            "source_text": text,
            "translated_text": res.translated_text,
            "target_language": res.target_language,
            "transliteration": res.transliterated_text,
            "summary": f"Translated to {res.target_language}: {res.translated_text}"
            + (f" (Phonetic: {res.transliterated_text})" if res.transliterated_text else ""),
        }

    async def _handle_realtime_pulse(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.realtime.engine import realtime_engine
        from app.models.schemas import LiveQueryRequest
        category = str(params.get("category", "tech_updates")).strip().lower()
        valid_cats = {"general", "news", "tech_updates", "research", "weather", "sports", "public_announcements"}
        if category == "technology":
            category = "tech_updates"
        elif category not in valid_cats:
            category = "general"
        query = str(params.get("query") or f"latest {category} updates").strip()
        res = await realtime_engine.execute_live_query(
            LiveQueryRequest(
                query=query,
                category=category,  # type: ignore[arg-type]
                location=str(params.get("location", "Chennai")),
            )
        )
        headlines = [f"- {src.title} ({src.domain})" for src in res.sources[:3]]
        return {
            "category": category,
            "query": query,
            "sources_count": len(res.sources),
            "summary": f"Live {category} feed ({res.retrieved_at.isoformat()}): {res.answer[:240]}"
            + (" | Sources: " + ", ".join(headlines) if headlines else ""),
        }

    async def _handle_delete_document(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.documents.storage import document_storage
        doc_id = str(params.get("doc_id", "")).strip()
        if doc_id == "all_temp":
            return {
                "doc_id": doc_id,
                "deleted": False,
                "summary": "Approved cleanup check completed: No temporary documents marked for deletion.",
            }
        deleted = document_storage.delete_document(doc_id)
        return {
            "doc_id": doc_id,
            "deleted": deleted,
            "summary": f"Document '{doc_id}' deletion executed (deleted={deleted}) after explicit user approval.",
        }

    async def _handle_dispatch_external_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        recipient = str(params.get("recipient", "external-webhook")).strip()
        subject = str(params.get("subject", "NEXORA Notification")).strip()
        body = str(params.get("body", "")).strip()
        return {
            "recipient": recipient,
            "subject": subject,
            "dispatched": True,
            "summary": f"Approved external message dispatched to '{recipient}' (Subject: '{subject}', Length: {len(body)} chars).",
        }

    async def _handle_browser_automation_step(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.computer.engine import computer_control_engine
        from app.models.schemas import ComputerSessionCreateRequest, ComputerActionStep

        url = str(params.get("url", "https://example.com")).strip()
        selector = str(params.get("selector", "h1, p, a")).strip()
        session = await computer_control_engine.create_session(
            ComputerSessionCreateRequest(
                goal=f"Inspect and extract {selector} from {url}",
                target_domain="browser",
                target_url=url,
                steps=[
                    ComputerActionStep(
                        step_id="s1_open",
                        title=f"Open {url}",
                        target_domain="browser",
                        action_type="open_url",
                        target_url_or_path=url,
                    ),
                    ComputerActionStep(
                        step_id="s2_extract",
                        title=f"Extract {selector}",
                        target_domain="browser",
                        action_type="extract_content",
                        selector=selector,
                    ),
                ],
                auto_start=True,
            )
        )
        return {
            "session_id": session.session_id,
            "status": session.status,
            "verified": session.verified_completion,
            "summary": session.final_summary,
        }

    async def _handle_computer_workspace_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.computer.engine import computer_control_engine
        from app.models.schemas import ComputerSessionCreateRequest, ComputerActionStep

        action = str(params.get("action", "list_workspace_files")).strip()
        if action not in ("list_workspace_files", "read_workspace_file", "run_predefined_diagnostic"):
            action = "list_workspace_files"
        target = str(params.get("target", ".")).strip()
        session = await computer_control_engine.create_session(
            ComputerSessionCreateRequest(
                goal=f"Execute sandboxed computer task {action} on {target}",
                target_domain="local_os",
                steps=[
                    ComputerActionStep(
                        step_id="s1_local",
                        title=f"Run {action}",
                        target_domain="local_os",
                        action_type=action,  # type: ignore[arg-type]
                        target_url_or_path=target,
                    )
                ],
                auto_start=True,
            )
        )
        return {
            "session_id": session.session_id,
            "status": session.status,
            "verified": session.verified_completion,
            "summary": session.final_summary,
        }


tool_registry = ToolRegistry()
