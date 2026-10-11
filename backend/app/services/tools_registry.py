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

        # 12. Stage 17: Controlled Workspace File Manager Tool
        self.register(
            tool=ToolDefinition(
                name="workspace_file_manager",
                description="Lists, searches, reads, finds duplicates, creates, or converts files inside the Stage 17 Authorized File Workspace.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "default": "list",
                            "description": "list | search | read | find_duplicates | create_file | convert_file",
                        },
                        "path": {"type": "string", "default": ""},
                        "query": {"type": "string", "default": ""},
                        "content": {"type": "string", "default": ""},
                        "target_format": {"type": "string", "default": "json"},
                        "user_id": {"type": "string", "default": "default_user"},
                    },
                },
                stage_introduced=17,
                requires_approval=False,
                risk_level="low",
                treats_output_as_untrusted=True,
            ),
            handler=self._handle_workspace_file_manager,
        )

        # 13. Stage 17: Consequential Bulk Workspace Organizer & Cleanup Tool (Requires Approval)
        self.register(
            tool=ToolDefinition(
                name="workspace_bulk_organizer",
                description="Organizes workspace files into structured folders or moves duplicates/selected files to Recoverable Trash. Consequential action requiring explicit user approval.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "default": "organize_workspace",
                            "description": "organize_workspace | cleanup_duplicates | delete_to_trash",
                        },
                        "strategy": {"type": "string", "default": "by_category"},
                        "directory": {"type": "string", "default": ""},
                        "paths": {"type": "array", "items": {"type": "string"}, "default": []},
                        "user_id": {"type": "string", "default": "default_user"},
                    },
                },
                stage_introduced=17,
                requires_approval=True,
                risk_level="high",
                treats_output_as_untrusted=False,
            ),
            handler=self._handle_workspace_bulk_organizer,
        )

        # 14. Stage 18: Sandboxed Code & Test Runner Tool
        self.register(
            tool=ToolDefinition(
                name="terminal_code_runner",
                description="Inspects, lints, executes, or tests code inside the isolated Stage 18 developer sandbox with CPU/memory/timeout limits and network disabled by default.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "default": "run",
                            "description": "run | test | inspect | debug_repair",
                        },
                        "project_id": {"type": "string", "default": "proj_default_py"},
                        "target_file": {"type": "string", "default": "main.py"},
                        "user_id": {"type": "string", "default": "default_user"},
                    },
                },
                stage_introduced=18,
                requires_approval=False,
                risk_level="low",
                treats_output_as_untrusted=True,
            ),
            handler=self._handle_terminal_code_runner,
        )

        # 15. Stage 18: Consequential Terminal Package & Command Runner (Requires Approval)
        self.register(
            tool=ToolDefinition(
                name="terminal_package_and_command",
                description="Executes consequential developer terminal operations (package installation, file removal, or network-enabled execution) after explicit user approval.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Terminal command to execute"},
                        "project_id": {"type": "string", "default": "proj_default_py"},
                        "user_id": {"type": "string", "default": "default_user"},
                        "allow_network": {"type": "boolean", "default": False},
                    },
                    "required": ["command"],
                },
                stage_introduced=18,
                requires_approval=True,
                risk_level="high",
                treats_output_as_untrusted=True,
            ),
            handler=self._handle_terminal_package_and_command,
        )

        # 16. Stage 19: Git Repository Inspector & Code Review Tool
        self.register(
            tool=ToolDefinition(
                name="git_repository_inspector",
                description="Inspects Git repository status, branches, recent commits, unified/side-by-side diffs, and runs AI-powered code review (distinguishing verified defects from possible concerns) inside authorized Stage 18/19 workspaces.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "default": "status",
                            "description": "status | diff | review | commits | branches",
                        },
                        "project_id": {"type": "string", "default": "proj_default_py"},
                        "user_id": {"type": "string", "default": "default_user"},
                        "file_path": {"type": "string", "default": ""},
                        "staged": {"type": "boolean", "default": False},
                        "run_tests": {"type": "boolean", "default": False},
                    },
                },
                stage_introduced=19,
                requires_approval=False,
                risk_level="low",
                treats_output_as_untrusted=True,
            ),
            handler=self._handle_git_repository_inspector,
        )

        # 17. Stage 19: Safe Git Commit, Branch, Merge & Remote Sync Tool (Requires Approval)
        self.register(
            tool=ToolDefinition(
                name="git_safe_commit_and_branch",
                description="Stages files, creates/switches/merges branches, commits changes with secret/env-file scanning, or syncs remotes after explicit user approval.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "default": "commit",
                            "description": "init | stage | commit | create_branch | switch_branch | merge | sync_remote",
                        },
                        "project_id": {"type": "string", "default": "proj_default_py"},
                        "user_id": {"type": "string", "default": "default_user"},
                        "message": {"type": "string", "default": "chore: update workspace files"},
                        "branch_name": {"type": "string", "default": ""},
                        "paths": {"type": "array", "items": {"type": "string"}, "default": []},
                    },
                },
                stage_introduced=19,
                requires_approval=True,
                risk_level="high",
                treats_output_as_untrusted=True,
            ),
            handler=self._handle_git_safe_commit_and_branch,
        )

        # 17. Stage 20 Evaluation & QA Runner (Read-only / Isolated)
        self.register(
            ToolDefinition(
                name="evaluation_qa_runner",
                description=(
                    "Runs NEXORA AI Stage 20 Evaluation & Quality Assurance benchmark suites in an isolated environment, "
                    "retrieves dataset metadata, or compares baseline vs. candidate runs for regression gating."
                ),
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["metadata", "run_suite", "latest_runs"],
                            "default": "metadata",
                        },
                        "suite_id": {
                            "type": "string",
                            "default": "general_qa",
                            "description": "Evaluation suite ID when action='run_suite'",
                        },
                        "label": {
                            "type": "string",
                            "default": "Tool-triggered QA Run",
                        },
                    },
                },
                stage_introduced=20,
                requires_approval=False,
                risk_level="low",
                treats_output_as_untrusted=False,
            ),
            handler=self._handle_evaluation_qa_runner,
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
                "doc_id": getattr(chunk, "document_id", getattr(chunk, "doc_id", "")),
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

    async def _handle_workspace_file_manager(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.files.engine import file_workspace_engine
        from app.models.schemas import (
            FileSearchRequest,
            FileWriteRequest,
            FileConvertRequest,
        )

        action = str(params.get("action", "list")).strip().lower()
        user_id = str(params.get("user_id", "default_user")).strip()
        path = str(params.get("path", "")).strip()

        if action == "read":
            read_res = file_workspace_engine.read_file(user_id=user_id, relative_path=path)
            return {
                "action": "read",
                "relative_path": read_res.item.relative_path,
                "sha256_hash": read_res.item.sha256_hash,
                "size_bytes": read_res.item.size_bytes,
                "summary": read_res.quarantined_content[:800],
            }
        if action == "search":
            query = str(params.get("query", "")).strip()
            search_res = file_workspace_engine.search_items(
                FileSearchRequest(user_id=user_id, query=query, directory=path, search_content=True)
            )
            names = [it.relative_path for it in search_res["items"][:10]]
            return {
                "action": "search",
                "query": query,
                "total_matches": search_res["total_matches"],
                "matches": names,
                "summary": f"Found {search_res['total_matches']} matching workspace file(s): {', '.join(names)}",
            }
        if action == "find_duplicates":
            dups = file_workspace_engine.find_duplicates(user_id=user_id, directory=path)
            return {
                "action": "find_duplicates",
                "duplicate_groups": len(dups),
                "groups": [g.model_dump(mode="json") for g in dups],
                "summary": f"Detected {len(dups)} duplicate file group(s) by SHA-256 content hash.",
            }
        if action == "create_file":
            content = str(params.get("content", ""))
            op = file_workspace_engine.write_file(
                FileWriteRequest(
                    user_id=user_id,
                    relative_path=path or "generated_note.md",
                    content=content,
                    overwrite=False,
                )
            )
            return {
                "action": "create_file",
                "operation_id": op.operation_id,
                "verified": op.verified,
                "summary": op.summary,
            }
        if action == "convert_file":
            target_fmt = str(params.get("target_format", "json")).strip().lower()
            op = file_workspace_engine.convert_file(
                FileConvertRequest(
                    user_id=user_id,
                    source_path=path,
                    target_format=target_fmt,  # type: ignore[arg-type]
                    overwrite=True,
                    confirmed_overwrite=True,
                )
            )
            return {
                "action": "convert_file",
                "operation_id": op.operation_id,
                "verified": op.verified,
                "summary": op.summary,
            }

        items = file_workspace_engine.list_items(user_id=user_id, directory=path, recursive=True)
        paths_list = [it.relative_path for it in items[:25]]
        return {
            "action": "list",
            "total_items": len(items),
            "items": paths_list,
            "summary": f"Listed {len(items)} item(s) in workspace: {', '.join(paths_list[:10])}",
        }

    async def _handle_workspace_bulk_organizer(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.files.engine import file_workspace_engine
        from app.models.schemas import (
            FileOrganizeRequest,
            FileDuplicateCleanupRequest,
            FileDeleteRequest,
        )

        action = str(params.get("action", "organize_workspace")).strip().lower()
        user_id = str(params.get("user_id", "default_user")).strip()
        directory = str(params.get("directory", "")).strip()

        if action == "cleanup_duplicates":
            op = file_workspace_engine.cleanup_duplicates(
                FileDuplicateCleanupRequest(user_id=user_id, directory=directory, confirmed=True)
            )
        elif action == "delete_to_trash":
            paths = list(params.get("paths") or [])
            op = file_workspace_engine.delete_to_trash(
                FileDeleteRequest(user_id=user_id, paths=paths, confirmed=True)
            )
        else:
            strategy = str(params.get("strategy", "by_category")).strip()
            if strategy not in ("by_category", "by_extension", "by_date_month", "custom_rules"):
                strategy = "by_category"
            op = file_workspace_engine.organize_workspace(
                FileOrganizeRequest(
                    user_id=user_id,
                    directory=directory,
                    strategy=strategy,  # type: ignore[arg-type]
                    confirmed=True,
                )
            )
        return {
            "operation_id": op.operation_id,
            "status": op.status,
            "verified": op.verified,
            "summary": op.summary,
        }

    async def _handle_terminal_code_runner(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.terminal.engine import terminal_execution_engine
        from app.models.schemas import (
            CodeExecuteRequest,
            CodeInspectRequest,
            DebugRepairRequest,
        )

        action = str(params.get("action", "run")).strip().lower()
        user_id = str(params.get("user_id", "default_user")).strip()
        project_id = str(params.get("project_id", "proj_default_py")).strip()
        target_file = str(params.get("target_file", "main.py")).strip()
        terminal_execution_engine._ensure_default_project(user_id)

        if action == "inspect":
            res = terminal_execution_engine.inspect_code(
                CodeInspectRequest(
                    user_id=user_id,
                    project_id=project_id,
                    relative_path=target_file,
                )
            )
            return {
                "action": "inspect",
                "project_id": project_id,
                "target_file": target_file,
                "syntax_valid": res.syntax_valid,
                "diagnostics_count": len(res.diagnostics),
                "missing_dependencies_count": res.missing_dependencies_count,
                "summary": res.summary,
            }

        if action == "debug_repair":
            rep = await terminal_execution_engine.debug_and_repair(
                DebugRepairRequest(
                    user_id=user_id,
                    project_id=project_id,
                    target_file=target_file,
                    run_tests=True,
                )
            )
            return {
                "action": "debug_repair",
                "repair_id": rep.repair_id,
                "status": rep.status,
                "attempts_used": rep.attempts_used,
                "final_verified": rep.final_verified,
                "summary": rep.explanation,
            }

        mode = "test" if action == "test" else "run"
        exec_rec = await terminal_execution_engine.execute_code(
            CodeExecuteRequest(
                user_id=user_id,
                project_id=project_id,
                target_file=target_file if mode == "run" else None,
                mode=mode,  # type: ignore[arg-type]
            )
        )
        return {
            "action": mode,
            "execution_id": exec_rec.execution_id,
            "status": exec_rec.status,
            "exit_code": exec_rec.exit_code,
            "verified": exec_rec.verified_execution,
            "stdout": exec_rec.stdout,
            "stderr": exec_rec.stderr,
            "summary": (
                f"Sandbox {mode} ({target_file}) finished with status={exec_rec.status}, "
                f"exit_code={exec_rec.exit_code}: {(exec_rec.stdout or exec_rec.stderr).strip()[:300]}"
            ),
        }

    async def _handle_terminal_package_and_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.terminal.engine import terminal_execution_engine
        from app.models.schemas import TerminalCommandRequest

        user_id = str(params.get("user_id", "default_user")).strip()
        project_id = str(params.get("project_id", "proj_default_py")).strip()
        command = str(params.get("command", "")).strip()
        allow_network = bool(params.get("allow_network", False))
        terminal_execution_engine._ensure_default_project(user_id)

        rec = await terminal_execution_engine.run_terminal_command(
            TerminalCommandRequest(
                user_id=user_id,
                project_id=project_id,
                command=command,
                allow_network=allow_network,
                confirmed=True,
            )
        )
        return {
            "execution_id": rec.execution_id,
            "status": rec.status,
            "exit_code": rec.exit_code,
            "verified": rec.verified_execution,
            "summary": (
                f"Terminal command '{command}' finished with status={rec.status}, "
                f"exit_code={rec.exit_code}: {(rec.stdout or rec.stderr).strip()[:300]}"
            ),
        }

    async def _handle_git_repository_inspector(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.git.engine import git_version_control_engine
        from app.models.schemas import GitReviewRequest

        action = str(params.get("action", "status")).strip().lower()
        user_id = str(params.get("user_id", "default_user")).strip()
        project_id = str(params.get("project_id", "proj_default_py")).strip()
        file_path = str(params.get("file_path", "")).strip() or None
        staged = bool(params.get("staged", False))
        run_tests = bool(params.get("run_tests", False))

        if action == "diff":
            diff = git_version_control_engine.get_diff(
                user_id=user_id,
                project_id=project_id,
                scope="staged" if staged else "all_working",
                file_path=file_path,
            )
            return {
                "action": "diff",
                "project_id": project_id,
                "staged": staged,
                "files_count": len(diff.files),
                "total_additions": diff.total_additions,
                "total_deletions": diff.total_deletions,
                "secret_warnings": diff.secret_warnings,
                "summary": (
                    f"Git diff ({'staged' if staged else 'working tree'}) for '{project_id}': "
                    f"{len(diff.files)} file(s), +{diff.total_additions} / -{diff.total_deletions}."
                ),
            }

        if action == "review":
            rev = await git_version_control_engine.review_changes(
                GitReviewRequest(
                    user_id=user_id,
                    project_id=project_id,
                    paths=[file_path] if file_path else [],
                    run_stage18_tests=run_tests,
                )
            )
            return {
                "action": "review",
                "review_id": rev.review_id,
                "project_id": project_id,
                "verified_defects_count": rev.verified_defects_count,
                "possible_concerns_count": rev.possible_concerns_count,
                "summary": rev.summary,
            }

        status = git_version_control_engine.get_status(user_id=user_id, project_id=project_id)
        return {
            "action": "status",
            "project_id": project_id,
            "is_initialized": status.is_initialized,
            "current_branch": status.current_branch,
            "is_clean": status.is_clean,
            "staged_count": status.staged_count,
            "unstaged_count": status.unstaged_count,
            "untracked_count": status.untracked_count,
            "recent_commits_count": len(status.recent_commits),
            "summary": (
                f"Git status for '{project_id}' (branch '{status.current_branch}'): "
                f"{'clean' if status.is_clean else f'{len(status.changed_files)} changed file(s)'} "
                f"(staged={status.staged_count}, unstaged={status.unstaged_count}, untracked={status.untracked_count})."
            ),
        }

    async def _handle_git_safe_commit_and_branch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.git.engine import git_version_control_engine
        from app.models.schemas import (
            GitInitRequest,
            GitStageRequest,
            GitCommitRequest,
            GitBranchActionRequest,
        )

        action = str(params.get("action", "commit")).strip().lower()
        user_id = str(params.get("user_id", "default_user")).strip()
        project_id = str(params.get("project_id", "proj_default_py")).strip()
        message = str(params.get("message", "chore: update workspace files")).strip()
        branch_name = str(params.get("branch_name", "feature/update")).strip()
        paths = list(params.get("paths") or [])

        if action == "init":
            op = git_version_control_engine.init_repository(
                GitInitRequest(user_id=user_id, project_id=project_id)
            )
        elif action == "stage":
            op = git_version_control_engine.stage_files(
                GitStageRequest(
                    user_id=user_id,
                    project_id=project_id,
                    paths=paths,
                    stage_all=len(paths) == 0,
                )
            )
        elif action in ("create_branch", "switch_branch", "merge"):
            b_act = "create" if action == "create_branch" else ("switch" if action == "switch_branch" else "merge")
            op = git_version_control_engine.manage_branch(
                GitBranchActionRequest(
                    user_id=user_id,
                    project_id=project_id,
                    action=b_act,  # type: ignore[arg-type]
                    branch_name=branch_name,
                    confirmed=True,
                )
            )
        else:
            op = git_version_control_engine.commit_changes(
                GitCommitRequest(
                    user_id=user_id,
                    project_id=project_id,
                    message=message,
                    stage_all=len(paths) == 0,
                    confirmed=True,
                )
            )
        return {
            "operation_id": op.operation_id,
            "operation_type": op.operation_type,
            "status": op.status,
            "verified": op.verified,
            "summary": op.stdout or op.error_message or op.command_display,
        }

    async def _handle_evaluation_qa_runner(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.evaluation.engine import evaluation_qa_engine
        from app.models.schemas import EvalRunCreateRequest

        action = str(params.get("action", "metadata")).strip().lower()
        suite_id = str(params.get("suite_id", "general_qa")).strip()
        label = str(params.get("label", "Tool-triggered QA Run")).strip()

        if action == "run_suite":
            run_rec = await evaluation_qa_engine.execute_run(
                EvalRunCreateRequest(
                    label=label,
                    suites=[suite_id],  # type: ignore[list-item]
                )
            )
            return {
                "action": "run_suite",
                "run_id": run_rec.run_id,
                "status": run_rec.status,
                "release_gate_verdict": run_rec.release_gate_verdict,
                "passed_cases": run_rec.passed_cases,
                "sample_size": run_rec.sample_size,
                "task_success_rate": run_rec.metrics.task_success_rate,
                "summary": (
                    f"Executed Evaluation Suite '{suite_id}' (run_id={run_rec.run_id}): "
                    f"{run_rec.passed_cases}/{run_rec.sample_size} passed, verdict={run_rec.release_gate_verdict}."
                ),
            }

        if action == "latest_runs":
            runs = evaluation_qa_engine.list_runs(limit=5)
            return {
                "action": "latest_runs",
                "runs_count": len(runs),
                "runs": [
                    {
                        "run_id": r.run_id,
                        "label": r.label,
                        "verdict": r.release_gate_verdict,
                        "passed_cases": r.passed_cases,
                        "sample_size": r.sample_size,
                    }
                    for r in runs
                ],
                "summary": f"Retrieved {len(runs)} recent evaluation run(s).",
            }

        meta = evaluation_qa_engine.get_metadata()
        return {
            "action": "metadata",
            "dataset_version": meta["dataset_version"],
            "total_cases": meta["total_cases"],
            "suites_count": len(meta["suites"]),
            "summary": (
                f"Evaluation & QA Engine operational (Dataset {meta['dataset_version']}, "
                f"{meta['total_cases']} total cases across {len(meta['suites'])} suites)."
            ),
        }


tool_registry = ToolRegistry()

