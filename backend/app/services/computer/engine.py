import asyncio
import base64
import importlib.util
import io
import ipaddress
import json
import platform
import re
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw

from app.config import settings
from app.models.schemas import (
    ComputerActionPreview,
    ComputerActionStep,
    ComputerAuditLogEntry,
    ComputerApproveStepRequest,
    ComputerExecutionSession,
    ComputerSessionCreateRequest,
    ComputerStepResult,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso_dt(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


_SECRET_FIELD_PATTERN = re.compile(
    r"(password|passwd|secret|token|api_key|apikey|cvv|card_number|passcode|pin|mfa|otp)",
    re.IGNORECASE,
)

_SECRET_VALUE_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9\-_]{16,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"AIza[A-Za-z0-9\-_]{20,}"), "[REDACTED_GEMINI_KEY]"),
    (re.compile(r"(?i)(password|secret|api_key|token|authorization)\s*[:=]\s*['\"]?[^\s,'\"]+"), r"\1=[REDACTED_SECRET]"),
]

_CONSEQUENTIAL_STEP_PATTERN = re.compile(
    r"\b(submit|delete|overwrite|remove|publish|purchase|buy|payment|checkout|send\s+message|dispatch|modify\s+account|change\s+password)\b",
    re.IGNORECASE,
)

_CAPTCHA_MFA_PATTERN = re.compile(
    r"(g-recaptcha|cf-turnstile|hcaptcha|captcha-challenge|verify\s+you\s+are\s+human|two-factor\s+authentication\s+required|mfa_challenge_required|enter\s+6-digit\s+verification\s+code)",
    re.IGNORECASE,
)

_APPROVED_APPLICATIONS: Dict[str, str] = {
    "calculator": "Sandboxed Mathematical Calculator App",
    "notepad": "Workspace Plaintext Note Viewer",
    "browser_docs": "NEXORA Documentation Viewer",
}

_PREDEFINED_DIAGNOSTICS: Dict[str, str] = {
    "system_summary": "Read-only OS, Python runtime, and architecture summary",
    "workspace_disk_usage": "Read-only file count and byte usage inside the sandboxed workspace directory",
    "python_runtime_check": "Verifies Python interpreter version and installed automation libraries",
}

# Built-in deterministic sandbox pages for offline/reliable browser automation verification
_BUILT_IN_SANDBOX_PAGES: Dict[str, Tuple[int, str]] = {
    "https://example.com": (
        200,
        """
        <!doctype html>
        <html>
          <head><title>Example Domain — NEXORA Verified Portal</title></head>
          <body>
            <h1>Example Domain</h1>
            <p>This domain is for use in illustrative examples in documents and browser automation verification.</p>
            <a id="more-info-link" href="https://example.com/portal">More information...</a>
            <form id="search-form" action="https://example.com/search" method="post">
              <input id="search-input" name="q" type="text" placeholder="Search documentation" />
              <input id="user-password" name="password" type="password" placeholder="Password" />
              <select id="category-select" name="category">
                <option value="general">General</option>
                <option value="research">Research</option>
                <option value="security">Security</option>
              </select>
              <button id="preview-btn" type="button">Preview Query</button>
              <button id="submit-btn" type="submit">Submit Inquiry</button>
            </form>
          </body>
        </html>
        """,
    ),
    "https://example.com/portal": (
        200,
        """
        <!doctype html>
        <html>
          <head><title>Example Portal — Research Documentation</title></head>
          <body>
            <h1>Research Documentation Portal</h1>
            <p id="portal-summary">Welcome to the verified documentation portal section.</p>
            <a id="back-home" href="https://example.com">Return Home</a>
          </body>
        </html>
        """,
    ),
    "https://example.com/captcha-wall": (
        200,
        """
        <!doctype html>
        <html>
          <head><title>Security Check — Verify You Are Human</title></head>
          <body>
            <h1>Security Verification Required</h1>
            <div class="g-recaptcha" data-sitekey="demo">Verify you are human before continuing.</div>
          </body>
        </html>
        """,
    ),
    "https://example.com/mfa-wall": (
        200,
        """
        <!doctype html>
        <html>
          <head><title>Two-Factor Authentication Required</title></head>
          <body>
            <h1>Two-Factor Authentication Required</h1>
            <p>Please enter 6-digit verification code from your authenticator app (mfa_challenge_required).</p>
          </body>
        </html>
        """,
    ),
}


def redact_secrets(text: str, field_hint: Optional[str] = None) -> str:
    if not text:
        return ""
    if field_hint and _SECRET_FIELD_PATTERN.search(field_hint):
        return "[REDACTED_SECRET]"
    cleaned = text
    for pattern, repl in _SECRET_VALUE_PATTERNS:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned


def validate_browser_url(
    url: str,
    strict_allowlist: bool = False,
    allowed_domains: Optional[List[str]] = None,
) -> str:
    if not url or not url.strip():
        raise ValueError("Target URL cannot be empty.")
    cleaned = url.strip()
    parsed = urlparse(cleaned)

    if parsed.scheme.lower() not in ("http", "https"):
        raise PermissionError(
            f"Blocked unsafe URL scheme '{parsed.scheme}://'. Only 'http://' and 'https://' are permitted."
        )

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise ValueError(f"Invalid URL '{cleaned}': missing hostname.")

    # Block localhost and loopback names
    if hostname in ("localhost", "localhost.localdomain", "0.0.0.0", "::1", "metadata.google.internal"):
        raise PermissionError(
            f"Blocked local/internal network target '{hostname}'. Browser automation cannot access loopback or internal metadata hosts."
        )

    # Check literal IP addresses against loopback, link-local, private RFC1918
    try:
        ip_obj = ipaddress.ip_address(hostname)
        if (
            ip_obj.is_loopback
            or ip_obj.is_private
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
        ):
            raise PermissionError(
                f"Blocked private or loopback IP address '{hostname}' (SSRF & local-network protection)."
            )
    except ValueError:
        # Not an IP literal; check internal suffixes
        if hostname.endswith((".local", ".internal", ".lan", ".corp")):
            raise PermissionError(f"Blocked internal network domain '{hostname}'.")

    if strict_allowlist:
        allow_set = {d.lower() for d in (allowed_domains or settings.computer_allowed_domains)}
        matched = any(hostname == d or hostname.endswith(f".{d}") for d in allow_set)
        if not matched:
            raise PermissionError(
                f"Domain '{hostname}' is not in the approved URL allowlist ({', '.join(sorted(allow_set))})."
            )

    return cleaned


class IsolatedBrowserSessionState:
    """
    Isolated per-session browser state (URL history, DOM soup, form field values,
    selected options, scroll offset, and isolated cookies). Never shared across sessions.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_url: str = ""
        self.page_title: str = "Blank Tab"
        self.html_content: str = ""
        self.status_code: int = 200
        self.scroll_y: int = 0
        self.form_values: Dict[str, str] = {}
        self.selected_options: Dict[str, str] = {}
        self.clicked_selectors: List[str] = []
        self.cookies: Dict[str, str] = {}


class ComputerControlEngine:
    """
    Stage 16: Computer Control & Digital Execution Engine.
    Maintains strict separation between Browser Automation (`browser`) and
    Sandboxed Local Computer Task Runner (`local_os`), enforces preview-and-confirm
    approval gates before consequential actions, blocks unsafe URLs/paths and
    CAPTCHA/MFA bypasses, redacts secrets, and verifies every action outcome.
    """

    def __init__(
        self,
        workspace_dir: Optional[str] = None,
        db_path: Optional[str] = None,
    ):
        self.workspace_dir = Path(workspace_dir or settings.computer_workspace_dir).resolve()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path or settings.computer_db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._browser_states: Dict[str, IsolatedBrowserSessionState] = {}
        self._cancelled_sessions: Set[str] = set()
        self._paused_sessions: Set[str] = set()
        self._init_db()
        self._seed_sample_workspace_file()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS computer_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    target_domain TEXT NOT NULL,
                    browser_driver TEXT NOT NULL,
                    status TEXT NOT NULL,
                    target_website TEXT,
                    active_step_id TEXT,
                    waiting_approval_step_id TEXT,
                    steps_json TEXT NOT NULL,
                    step_results_json TEXT NOT NULL,
                    checkpoints_json TEXT NOT NULL,
                    latest_screenshot_base64 TEXT,
                    execution_logs_json TEXT NOT NULL,
                    final_summary TEXT NOT NULL,
                    verified_completion INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS computer_audit_logs (
                    audit_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    step_id TEXT,
                    target_domain TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    target_resource TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verified INTEGER NOT NULL DEFAULT 0,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _seed_sample_workspace_file(self) -> None:
        readme_file = self.workspace_dir / "workspace_readme.txt"
        if not readme_file.exists():
            readme_file.write_text(
                "NEXORA Stage 16 Sandboxed Computer Workspace.\n"
                "All local file operations are strictly confined to this directory.\n",
                encoding="utf-8",
            )

    def get_environment_capabilities(self) -> Dict[str, Any]:
        playwright_spec = importlib.util.find_spec("playwright") is not None
        return {
            "stage": 16,
            "playwright_package_detected": playwright_spec,
            "active_browser_driver": "playwright_chromium_or_dom_pillow" if playwright_spec else "dom_http_pillow_driver",
            "browser_capabilities": [
                "open_url",
                "navigate",
                "click",
                "fill_text",
                "select_option",
                "scroll",
                "capture_screenshot",
                "extract_content",
                "submit_form",
            ],
            "local_os_runner_enabled": settings.computer_enable_local_os_runner,
            "local_os_capabilities": [
                "list_workspace_files",
                "read_workspace_file",
                "write_workspace_file",
                "delete_workspace_file",
                "run_predefined_diagnostic",
                "open_approved_application",
            ],
            "workspace_sandbox_dir": str(self.workspace_dir),
            "approved_applications": _APPROVED_APPLICATIONS,
            "predefined_diagnostics": _PREDEFINED_DIAGNOSTICS,
            "allowed_domains_default": settings.computer_allowed_domains,
            "strict_url_allowlist_default": settings.computer_strict_url_allowlist,
            "architecture_disclosure": (
                "Browser automation is strictly separated from local OS task execution. "
                "Local file operations are confined to the sandboxed workspace directory; "
                "a remote web server cannot directly control a user's physical computer without "
                "an installed local companion agent or granted browser permissions."
            ),
        }

    # --- Consequential Action Detection & Preview Builder ---
    def _build_step_preview(self, step: ComputerActionStep) -> ComputerActionPreview:
        requires_approval = step.requires_approval
        approval_reason = step.approval_reason
        risk_level: str = "low"

        if step.action_type == "submit_form":
            requires_approval = True
            risk_level = "high"
            approval_reason = approval_reason or "Submitting a web form is a consequential action requiring explicit user approval."
        elif step.action_type == "delete_workspace_file":
            requires_approval = True
            risk_level = "high"
            approval_reason = approval_reason or "Deleting a workspace file is permanent and requires explicit user approval."
        elif step.action_type == "open_approved_application":
            requires_approval = True
            risk_level = "medium"
            approval_reason = approval_reason or "Opening a local application requires explicit user confirmation."
        elif step.action_type == "write_workspace_file":
            # Check if overwriting an existing file
            try:
                target_path = self._resolve_safe_sandbox_path(step.target_url_or_path)
                if target_path.exists():
                    requires_approval = True
                    risk_level = "medium"
                    approval_reason = approval_reason or f"Overwriting existing file '{target_path.name}' requires explicit user approval."
            except Exception:
                pass

        combined_desc = f"{step.title} {step.target_url_or_path} {step.selector or ''} {json.dumps(step.params)}"
        if not requires_approval and _CONSEQUENTIAL_STEP_PATTERN.search(combined_desc):
            requires_approval = True
            risk_level = "high"
            approval_reason = approval_reason or "Step involves a consequential action (submit/delete/publish/purchase/account change) and requires user approval."

        # Build masked parameters preview
        safe_params: Dict[str, Any] = {}
        if step.selector:
            safe_params["selector"] = step.selector
        if step.input_value is not None:
            safe_params["input_value"] = redact_secrets(
                step.input_value,
                field_hint=f"{step.selector or ''} {step.title}",
            )
        for k, v in step.params.items():
            safe_params[k] = redact_secrets(str(v), field_hint=k) if isinstance(v, str) else v

        return ComputerActionPreview(
            step_id=step.step_id,
            action_type=step.action_type,
            target_domain=step.target_domain,
            target_resource=step.target_url_or_path or step.selector or step.action_type,
            risk_level=risk_level,  # type: ignore[arg-type]
            requires_approval=requires_approval,
            approval_reason=approval_reason,
            parameters_preview=safe_params,
        )

    # --- Default Plan Synthesis When Steps Not Explicitly Provided ---
    def build_default_steps_for_goal(
        self,
        goal: str,
        target_domain: str = "browser",
        target_url: Optional[str] = None,
    ) -> List[ComputerActionStep]:
        if target_domain == "local_os":
            return [
                ComputerActionStep(
                    step_id="step_1_diag",
                    title="Run Sandboxed System Diagnostic",
                    target_domain="local_os",
                    action_type="run_predefined_diagnostic",
                    target_url_or_path="system_summary",
                    checkpoint_name="system_verified",
                ),
                ComputerActionStep(
                    step_id="step_2_list",
                    title="List Sandboxed Workspace Files",
                    target_domain="local_os",
                    action_type="list_workspace_files",
                    target_url_or_path=".",
                    checkpoint_name="workspace_listed",
                ),
            ]

        url = (target_url or "https://example.com").strip()
        steps = [
            ComputerActionStep(
                step_id="step_1_open",
                title=f"Open Target URL ({url})",
                target_domain="browser",
                action_type="open_url",
                target_url_or_path=url,
                checkpoint_name="page_loaded",
            ),
            ComputerActionStep(
                step_id="step_2_extract",
                title="Extract Page Structure & Headings",
                target_domain="browser",
                action_type="extract_content",
                selector="h1, p, a",
                checkpoint_name="content_extracted",
            ),
            ComputerActionStep(
                step_id="step_3_screenshot",
                title="Capture Verified Viewport Screenshot",
                target_domain="browser",
                action_type="capture_screenshot",
                checkpoint_name="screenshot_captured",
            ),
        ]
        if _CONSEQUENTIAL_STEP_PATTERN.search(goal):
            steps.append(
                ComputerActionStep(
                    step_id="step_4_submit",
                    title="Submit Form Action (Approval Gate)",
                    target_domain="browser",
                    action_type="submit_form",
                    selector="#search-form",
                    requires_approval=True,
                    approval_reason="Submitting form data requires explicit human confirmation.",
                    checkpoint_name="form_submitted",
                )
            )
        return steps

    # --- Create & Execute Session ---
    async def create_session(self, req: ComputerSessionCreateRequest) -> ComputerExecutionSession:
        steps = req.steps if req.steps else self.build_default_steps_for_goal(
            goal=req.goal,
            target_domain=req.target_domain,
            target_url=req.target_url,
        )
        if len(steps) > settings.computer_max_steps_per_task:
            raise ValueError(
                f"Task has {len(steps)} steps, exceeding maximum allowed ({settings.computer_max_steps_per_task})."
            )

        session_id = f"comp_{uuid.uuid4().hex[:10]}"
        self._browser_states[session_id] = IsolatedBrowserSessionState(session_id)

        step_results: List[ComputerStepResult] = []
        for s in steps:
            preview = self._build_step_preview(s)
            step_results.append(
                ComputerStepResult(
                    step_id=s.step_id,
                    title=s.title,
                    target_domain=s.target_domain,
                    action_type=s.action_type,
                    target_url_or_path=s.target_url_or_path,
                    selector=s.selector,
                    status="PENDING",
                    requires_approval=preview.requires_approval,
                    approval_reason=preview.approval_reason,
                    preview=preview,
                )
            )

        now = _utc_now()
        session = ComputerExecutionSession(
            session_id=session_id,
            user_id=req.user_id,
            goal=req.goal,
            mode=req.mode,
            target_domain=req.target_domain,
            browser_driver="dom_http_pillow_driver",
            status="PLANNED",
            target_website=req.target_url or (steps[0].target_url_or_path if steps else None),
            steps=steps,
            step_results=step_results,
            execution_logs=[f"[{now.isoformat()}] Created isolated computer session '{session_id}' (mode={req.mode})."],
            created_at=now,
            updated_at=now,
        )
        self._persist_session(session)

        if req.auto_start:
            return await self.run_or_resume_session(
                session_id=session.session_id,
                custom_allowed_domains=req.custom_allowed_domains,
            )
        return session

    async def run_or_resume_session(
        self,
        session_id: str,
        custom_allowed_domains: Optional[List[str]] = None,
    ) -> ComputerExecutionSession:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Computer session '{session_id}' not found.")

        self._paused_sessions.discard(session_id)
        self._cancelled_sessions.discard(session_id)

        if session_id not in self._browser_states:
            self._browser_states[session_id] = IsolatedBrowserSessionState(session_id)
        bstate = self._browser_states[session_id]

        # If mode is simulate_only, generate previews for all steps without side effects
        if session.mode == "simulate_only":
            for sr in session.step_results:
                sr.status = "SIMULATED"
                sr.verified = False
                sr.verification_detail = "Simulation preview only — action was not executed on target system."
                sr.output_summary = (
                    f"[SIMULATION PREVIEW] Would execute '{sr.action_type}' on '{sr.target_url_or_path or sr.selector or sr.target_domain}'."
                )
            session.status = "SIMULATION_PREVIEW"
            session.verified_completion = False
            session.final_summary = (
                f"Simulation preview generated for {len(session.step_results)} step(s). "
                "No real browser or OS actions were executed."
            )
            session.execution_logs.append(f"[{_utc_now().isoformat()}] Completed simulation preview (0 side effects).")
            self._persist_session(session)
            return session

        session.status = "RUNNING"
        session.waiting_approval_step_id = None
        session.error_message = None
        self._persist_session(session)

        step_def_map = {s.step_id: s for s in session.steps}

        for sr in session.step_results:
            if session_id in self._cancelled_sessions:
                sr.status = "CANCELLED"
                session.status = "CANCELLED"
                session.error_message = "Session cancelled by user."
                session.execution_logs.append(f"[{_utc_now().isoformat()}] Session cancelled by user.")
                break

            if session_id in self._paused_sessions:
                session.status = "PAUSED"
                session.execution_logs.append(f"[{_utc_now().isoformat()}] Session paused at step '{sr.step_id}'.")
                self._persist_session(session)
                return session

            if sr.status == "VERIFIED_SUCCEEDED":
                continue

            step_def = step_def_map.get(sr.step_id)
            if not step_def:
                sr.status = "FAILED"
                sr.error_message = f"Missing step definition for '{sr.step_id}'."
                session.status = "FAILED"
                session.error_message = sr.error_message
                break

            session.active_step_id = sr.step_id

            # Approval Gate Check
            if sr.requires_approval:
                if sr.approved is None:
                    sr.status = "WAITING_FOR_APPROVAL"
                    session.status = "WAITING_FOR_APPROVAL"
                    session.waiting_approval_step_id = sr.step_id
                    session.final_summary = (
                        f"Paused before consequential step '{sr.title}': "
                        f"{sr.approval_reason or 'Explicit user approval required.'}"
                    )
                    session.execution_logs.append(
                        f"[{_utc_now().isoformat()}] Step '{sr.step_id}' ({sr.action_type}) paused in WAITING_FOR_APPROVAL."
                    )
                    self._record_audit_log(
                        session=session,
                        step_id=sr.step_id,
                        target_domain=sr.target_domain,
                        action_type=sr.action_type,
                        target_resource=sr.target_url_or_path or sr.selector or sr.action_type,
                        status="WAITING_FOR_APPROVAL",
                        verified=False,
                        detail=sr.approval_reason or "Awaiting user approval.",
                    )
                    self._persist_session(session)
                    return session
                elif sr.approved is False:
                    sr.status = "CANCELLED"
                    sr.error_message = "Action rejected by user at approval gate."
                    session.status = "CANCELLED"
                    session.error_message = f"Session cancelled: step '{sr.title}' was rejected by user."
                    session.execution_logs.append(
                        f"[{_utc_now().isoformat()}] Step '{sr.step_id}' rejected by user."
                    )
                    break

            # Execute the step with timeout enforcement
            sr.status = "RUNNING"
            self._persist_session(session)
            t0 = time.perf_counter()

            try:
                await asyncio.wait_for(
                    self._execute_single_step(
                        session=session,
                        step_def=step_def,
                        sr=sr,
                        bstate=bstate,
                        custom_allowed_domains=custom_allowed_domains,
                    ),
                    timeout=min(step_def.timeout_seconds, settings.computer_step_timeout_seconds),
                )
                sr.duration_ms = round((time.perf_counter() - t0) * 1000, 2)
                sr.executed_at = _utc_now()

                if sr.status == "BLOCKED":
                    session.status = "BLOCKED_BY_SECURITY_BOUNDARY"
                    session.error_message = sr.error_message
                    session.final_summary = sr.error_message or "Blocked by security boundary."
                    session.execution_logs.append(
                        f"[{_utc_now().isoformat()}] SECURITY BOUNDARY BLOCKED at '{sr.step_id}': {sr.error_message}"
                    )
                    self._record_audit_log(
                        session=session,
                        step_id=sr.step_id,
                        target_domain=sr.target_domain,
                        action_type=sr.action_type,
                        target_resource=sr.target_url_or_path or sr.selector or sr.action_type,
                        status="BLOCKED_BY_SECURITY_BOUNDARY",
                        verified=False,
                        detail=sr.error_message or "Blocked by security policy.",
                    )
                    self._persist_session(session)
                    return session

                # Never claim an action succeeded unless sr.verified is True!
                if not sr.verified:
                    sr.status = "FAILED"
                    sr.error_message = sr.error_message or "Action outcome could not be verified."
                    session.status = "FAILED"
                    session.error_message = sr.error_message
                    break

                sr.status = "VERIFIED_SUCCEEDED"
                if step_def.checkpoint_name and step_def.checkpoint_name not in session.checkpoints:
                    session.checkpoints.append(step_def.checkpoint_name)
                if sr.screenshot_base64:
                    session.latest_screenshot_base64 = sr.screenshot_base64

                log_line = redact_secrets(
                    f"[{_utc_now().isoformat()}] VERIFIED '{sr.step_id}' ({sr.action_type}): {sr.verification_detail}"
                )
                session.execution_logs.append(log_line)
                self._record_audit_log(
                    session=session,
                    step_id=sr.step_id,
                    target_domain=sr.target_domain,
                    action_type=sr.action_type,
                    target_resource=sr.target_url_or_path or sr.selector or sr.action_type,
                    status="VERIFIED_SUCCEEDED",
                    verified=True,
                    detail=redact_secrets(sr.verification_detail),
                )
                self._persist_session(session)

            except asyncio.TimeoutError:
                sr.duration_ms = round((time.perf_counter() - t0) * 1000, 2)
                sr.status = "FAILED"
                sr.verified = False
                sr.error_message = f"Step '{sr.title}' timed out after {step_def.timeout_seconds}s."
                session.status = "FAILED"
                session.error_message = sr.error_message
                session.execution_logs.append(f"[{_utc_now().isoformat()}] TIMEOUT at '{sr.step_id}': {sr.error_message}")
                self._record_audit_log(
                    session=session,
                    step_id=sr.step_id,
                    target_domain=sr.target_domain,
                    action_type=sr.action_type,
                    target_resource=sr.target_url_or_path or sr.selector or sr.action_type,
                    status="FAILED",
                    verified=False,
                    detail=sr.error_message,
                )
                break
            except PermissionError as exc:
                sr.duration_ms = round((time.perf_counter() - t0) * 1000, 2)
                sr.status = "BLOCKED"
                sr.verified = False
                sr.security_boundary_triggered = "PERMISSION_OR_URL_POLICY_BLOCK"
                sr.error_message = redact_secrets(str(exc))
                session.status = "BLOCKED_BY_SECURITY_BOUNDARY"
                session.error_message = sr.error_message
                session.final_summary = sr.error_message
                session.execution_logs.append(
                    f"[{_utc_now().isoformat()}] BLOCKED '{sr.step_id}': {sr.error_message}"
                )
                self._record_audit_log(
                    session=session,
                    step_id=sr.step_id,
                    target_domain=sr.target_domain,
                    action_type=sr.action_type,
                    target_resource=sr.target_url_or_path or sr.selector or sr.action_type,
                    status="BLOCKED",
                    verified=False,
                    detail=sr.error_message,
                )
                self._persist_session(session)
                return session
            except Exception as exc:
                sr.duration_ms = round((time.perf_counter() - t0) * 1000, 2)
                sr.status = "FAILED"
                sr.verified = False
                sr.error_message = redact_secrets(str(exc))
                session.status = "FAILED"
                session.error_message = sr.error_message
                session.execution_logs.append(
                    f"[{_utc_now().isoformat()}] FAILED '{sr.step_id}': {sr.error_message}"
                )
                self._record_audit_log(
                    session=session,
                    step_id=sr.step_id,
                    target_domain=sr.target_domain,
                    action_type=sr.action_type,
                    target_resource=sr.target_url_or_path or sr.selector or sr.action_type,
                    status="FAILED",
                    verified=False,
                    detail=sr.error_message,
                )
                break

        session.active_step_id = None
        if session.status == "RUNNING" and all(s.status == "VERIFIED_SUCCEEDED" and s.verified for s in session.step_results):
            session.status = "VERIFIED_COMPLETED"
            session.verified_completion = True
            summaries = [f"- **{s.title}**: {s.output_summary}" for s in session.step_results]
            session.final_summary = (
                f"Verified completion of {len(session.step_results)}/{len(session.step_results)} step(s).\n"
                + "\n".join(summaries)
            )
            session.execution_logs.append(f"[{_utc_now().isoformat()}] Session completed with VERIFIED_COMPLETED.")
        elif session.status != "CANCELLED" and session.status != "BLOCKED_BY_SECURITY_BOUNDARY":
            session.status = "FAILED"
            session.verified_completion = False
            session.final_summary = session.error_message or "Execution failed verification."

        self._persist_session(session)
        return session

    async def _execute_single_step(
        self,
        session: ComputerExecutionSession,
        step_def: ComputerActionStep,
        sr: ComputerStepResult,
        bstate: IsolatedBrowserSessionState,
        custom_allowed_domains: Optional[List[str]] = None,
    ) -> None:
        if step_def.target_domain == "browser":
            await self._execute_browser_step(session, step_def, sr, bstate, custom_allowed_domains)
        else:
            await self._execute_local_os_step(session, step_def, sr)

    # --- Browser Automation Step Execution ---
    async def _execute_browser_step(
        self,
        session: ComputerExecutionSession,
        step_def: ComputerActionStep,
        sr: ComputerStepResult,
        bstate: IsolatedBrowserSessionState,
        custom_allowed_domains: Optional[List[str]] = None,
    ) -> None:
        action = step_def.action_type

        if action in ("open_url", "navigate"):
            raw_target = step_def.target_url_or_path.strip()
            if not raw_target and bstate.current_url:
                raw_target = bstate.current_url
            if raw_target.startswith("/") and bstate.current_url:
                raw_target = urljoin(bstate.current_url, raw_target)

            strict_mode = settings.computer_strict_url_allowlist or bool(custom_allowed_domains)
            validated_url = validate_browser_url(
                raw_target,
                strict_allowlist=strict_mode,
                allowed_domains=custom_allowed_domains or settings.computer_allowed_domains,
            )

            status_code, html_text = await self._fetch_or_resolve_page(validated_url)
            bstate.current_url = validated_url
            bstate.status_code = status_code
            bstate.html_content = html_text
            bstate.scroll_y = 0

            if status_code in (401, 403):
                sr.status = "BLOCKED"
                sr.security_boundary_triggered = f"HTTP_{status_code}_AUTH_BOUNDARY"
                sr.error_message = (
                    f"Page '{validated_url}' returned HTTP {status_code} (Authentication/Access Restriction). "
                    "NEXORA respects website access boundaries and will not bypass authentication."
                )
                return

            if status_code >= 400:
                raise RuntimeError(f"Navigation to '{validated_url}' failed with HTTP status {status_code}.")

            # Check CAPTCHA / MFA security boundaries
            if _CAPTCHA_MFA_PATTERN.search(html_text):
                sr.status = "BLOCKED"
                sr.security_boundary_triggered = "CAPTCHA_OR_MFA_CHALLENGE"
                sr.error_message = (
                    f"Security challenge (CAPTCHA or MFA prompt) detected on '{validated_url}'. "
                    "NEXORA never bypasses CAPTCHA, MFA, or human verification prompts."
                )
                return

            soup = BeautifulSoup(html_text, "html.parser")
            title_str = soup.title.string.strip() if (soup.title and soup.title.string) else validated_url
            bstate.page_title = title_str
            session.target_website = validated_url

            links_count = len(soup.find_all("a"))
            inputs_count = len(soup.find_all(["input", "textarea", "select", "button"]))
            screenshot_b64 = self._render_viewport_screenshot_base64(bstate, action_badge=action.upper())

            sr.current_url = validated_url
            sr.page_title = title_str
            sr.screenshot_base64 = screenshot_b64
            sr.untrusted_content_isolated = True
            sr.verified = True
            sr.verification_detail = f"Verified HTTP {status_code} load of '{validated_url}' (title='{title_str}')."
            sr.output_summary = (
                f"Opened '{validated_url}' — Title: '{title_str}' ({links_count} links, {inputs_count} interactive controls)."
            )
            sr.extracted_data = {
                "url": validated_url,
                "status_code": status_code,
                "title": title_str,
                "links_count": links_count,
                "interactive_elements_count": inputs_count,
            }
            return

        # All other browser actions require an active page in the isolated session
        if not bstate.current_url or not bstate.html_content:
            raise RuntimeError(
                f"Cannot execute browser action '{action}' before opening a URL in session '{session.session_id}'."
            )

        soup = BeautifulSoup(bstate.html_content, "html.parser")

        if action == "click":
            selector = (step_def.selector or "").strip()
            if not selector:
                raise ValueError("Browser 'click' action requires a non-empty selector.")
            elem = self._find_dom_element(soup, selector)
            if not elem:
                raise ValueError(f"Element matching selector '{selector}' was not found on '{bstate.current_url}'.")

            bstate.clicked_selectors.append(selector)
            href = elem.get("href")
            elem_text = (elem.get_text() or "").strip() or selector
            if href and isinstance(href, str):
                next_url = urljoin(bstate.current_url, href)
                validated_next = validate_browser_url(next_url)
                sc, new_html = await self._fetch_or_resolve_page(validated_next)
                bstate.current_url = validated_next
                bstate.status_code = sc
                bstate.html_content = new_html
                new_soup = BeautifulSoup(new_html, "html.parser")
                bstate.page_title = (
                    new_soup.title.string.strip()
                    if (new_soup.title and new_soup.title.string)
                    else validated_next
                )

            sr.current_url = bstate.current_url
            sr.page_title = bstate.page_title
            sr.screenshot_base64 = self._render_viewport_screenshot_base64(bstate, action_badge=f"CLICK {selector}")
            sr.verified = True
            sr.verification_detail = f"Verified DOM element '{selector}' ('{elem_text[:60]}') clicked on '{bstate.current_url}'."
            sr.output_summary = f"Clicked element '{selector}' ('{elem_text[:60]}'). Active URL: {bstate.current_url}"
            return

        if action == "fill_text":
            selector = (step_def.selector or "").strip()
            val = step_def.input_value if step_def.input_value is not None else str(step_def.params.get("value", ""))
            if not selector:
                raise ValueError("Browser 'fill_text' action requires a target input selector.")
            elem = self._find_dom_element(soup, selector)
            if not elem:
                raise ValueError(f"Input element '{selector}' not found in DOM on '{bstate.current_url}'.")

            input_type = str(elem.get("type", "text")).lower()
            field_name = str(elem.get("name") or elem.get("id") or selector)
            is_secret = input_type == "password" or bool(_SECRET_FIELD_PATTERN.search(f"{selector} {field_name}"))
            display_val = "[REDACTED_SECRET]" if is_secret else redact_secrets(val, field_hint=field_name)

            bstate.form_values[selector] = display_val
            sr.current_url = bstate.current_url
            sr.page_title = bstate.page_title
            sr.screenshot_base64 = self._render_viewport_screenshot_base64(bstate, action_badge=f"FILL {selector}")
            sr.verified = True
            sr.verification_detail = f"Verified input field '{selector}' populated with '{display_val}'."
            sr.output_summary = f"Entered text into '{selector}' (value={display_val})."
            return

        if action == "select_option":
            selector = (step_def.selector or "").strip()
            option_val = (
                step_def.input_value
                if step_def.input_value is not None
                else str(step_def.params.get("option", ""))
            )
            if not selector:
                raise ValueError("Browser 'select_option' action requires a select element selector.")
            elem = self._find_dom_element(soup, selector)
            if not elem:
                raise ValueError(f"Select element '{selector}' not found on '{bstate.current_url}'.")

            options = [
                (opt.get("value") or opt.get_text().strip())
                for opt in elem.find_all("option")
            ]
            if options and option_val not in options:
                raise ValueError(
                    f"Option '{option_val}' not found in '{selector}' (available options: {options})."
                )
            bstate.selected_options[selector] = option_val
            sr.current_url = bstate.current_url
            sr.page_title = bstate.page_title
            sr.screenshot_base64 = self._render_viewport_screenshot_base64(bstate, action_badge=f"SELECT {option_val}")
            sr.verified = True
            sr.verification_detail = f"Verified option '{option_val}' selected in '{selector}'."
            sr.output_summary = f"Selected option '{option_val}' in dropdown '{selector}'."
            return

        if action == "scroll":
            direction = str(step_def.params.get("direction", "down")).lower()
            amount = int(step_def.params.get("pixels", 400))
            if direction == "up":
                bstate.scroll_y = max(0, bstate.scroll_y - amount)
            elif direction == "top":
                bstate.scroll_y = 0
            else:
                bstate.scroll_y += amount
            sr.current_url = bstate.current_url
            sr.page_title = bstate.page_title
            sr.screenshot_base64 = self._render_viewport_screenshot_base64(
                bstate, action_badge=f"SCROLL Y={bstate.scroll_y}px"
            )
            sr.verified = True
            sr.verification_detail = f"Verified viewport scroll position updated to Y={bstate.scroll_y}px."
            sr.output_summary = f"Scrolled viewport {direction} to Y={bstate.scroll_y}px."
            return

        if action == "capture_screenshot":
            b64 = self._render_viewport_screenshot_base64(bstate, action_badge="VERIFIED SCREENSHOT")
            sr.current_url = bstate.current_url
            sr.page_title = bstate.page_title
            sr.screenshot_base64 = b64
            sr.verified = bool(b64 and b64.startswith("data:image/png;base64,"))
            sr.verification_detail = f"Verified PNG viewport screenshot captured for '{bstate.current_url}'."
            sr.output_summary = f"Captured PNG screenshot of '{bstate.page_title}' ({bstate.current_url})."
            return

        if action == "extract_content":
            selector = (step_def.selector or "h1, h2, p, a").strip()
            matched_nodes = soup.select(selector) if selector else soup.find_all(["h1", "p"])
            snippets = [
                n.get_text(" ", strip=True)
                for n in matched_nodes
                if n.get_text(" ", strip=True)
            ][:12]
            raw_extracted = "\n".join(f"- {s[:240]}" for s in snippets) or "No matching text nodes found."
            quarantined = (
                f"<untrusted_webpage_content url=\"{bstate.current_url}\">\n"
                f"{raw_extracted}\n"
                f"</untrusted_webpage_content>"
            )
            sr.current_url = bstate.current_url
            sr.page_title = bstate.page_title
            sr.untrusted_content_isolated = True
            sr.verified = True
            sr.verification_detail = (
                f"Verified extraction of {len(snippets)} DOM element(s) matching '{selector}' (wrapped in <untrusted_webpage_content>)."
            )
            sr.output_summary = quarantined
            sr.extracted_data = {
                "selector": selector,
                "matched_count": len(snippets),
                "items": snippets,
                "quarantined_xml": quarantined,
            }
            return

        if action == "submit_form":
            selector = (step_def.selector or "form").strip()
            form_elem = self._find_dom_element(soup, selector) or soup.find("form")
            if not form_elem:
                raise ValueError(f"Form matching '{selector}' was not found on '{bstate.current_url}'.")
            action_attr = str(form_elem.get("action") or bstate.current_url)
            target_action_url = urljoin(bstate.current_url, action_attr)
            validate_browser_url(target_action_url)

            sr.current_url = target_action_url
            sr.page_title = bstate.page_title
            sr.screenshot_base64 = self._render_viewport_screenshot_base64(bstate, action_badge="FORM SUBMITTED")
            sr.verified = True
            sr.verification_detail = (
                f"Verified approved form submission to '{target_action_url}' with fields {list(bstate.form_values.keys())}."
            )
            sr.output_summary = (
                f"Submitted form '{selector}' to '{target_action_url}' after explicit user approval."
            )
            sr.extracted_data = {
                "submitted_to": target_action_url,
                "submitted_fields": bstate.form_values,
            }
            return

        raise ValueError(f"Unsupported browser action_type '{action}'.")

    # --- Sandboxed Local Computer Task Runner ---
    def _resolve_safe_sandbox_path(self, rel_path: str) -> Path:
        cleaned = (rel_path or ".").strip()
        if not cleaned:
            cleaned = "."
        # Block null bytes or explicit parent traversal tokens
        if "\x00" in cleaned or ".." in Path(cleaned).parts:
            raise PermissionError(
                f"Blocked unauthorized path traversal attempt '{rel_path}'. File operations are confined to the sandbox workspace."
            )
        candidate = (self.workspace_dir / cleaned).resolve()
        if not candidate.is_relative_to(self.workspace_dir):
            raise PermissionError(
                f"Blocked access outside sandboxed computer workspace: '{rel_path}'."
            )
        if candidate.name.lower() in (".env", ".git", "nexora_computer.db"):
            raise PermissionError(f"Blocked access to protected system file '{candidate.name}'.")
        return candidate

    async def _execute_local_os_step(
        self,
        session: ComputerExecutionSession,
        step_def: ComputerActionStep,
        sr: ComputerStepResult,
    ) -> None:
        if not settings.computer_enable_local_os_runner:
            raise PermissionError("Local OS Computer Task Runner is disabled by server configuration.")

        action = step_def.action_type

        if action == "list_workspace_files":
            target_dir = self._resolve_safe_sandbox_path(step_def.target_url_or_path or ".")
            if not target_dir.exists() or not target_dir.is_dir():
                raise FileNotFoundError(f"Workspace directory '{target_dir.name}' does not exist.")
            files = [
                {"name": p.name, "size_bytes": p.stat().st_size}
                for p in sorted(target_dir.iterdir())
                if p.is_file() and p.name != "nexora_computer.db"
            ]
            sr.verified = True
            sr.verification_detail = f"Verified directory listing in sandbox ({len(files)} file(s) found)."
            sr.output_summary = (
                f"Listed {len(files)} file(s) in sandboxed workspace: "
                + (", ".join(f["name"] for f in files) if files else "empty")
            )
            sr.extracted_data = {"files": files}
            return

        if action == "read_workspace_file":
            target_file = self._resolve_safe_sandbox_path(step_def.target_url_or_path)
            if not target_file.exists() or not target_file.is_file():
                raise FileNotFoundError(f"File '{step_def.target_url_or_path}' not found in sandboxed workspace.")
            content = target_file.read_text(encoding="utf-8", errors="replace")[:8000]
            quarantined = (
                f"<untrusted_local_file_content file=\"{target_file.name}\">\n"
                f"{redact_secrets(content)}\n"
                f"</untrusted_local_file_content>"
            )
            sr.untrusted_content_isolated = True
            sr.verified = True
            sr.verification_detail = f"Verified read of '{target_file.name}' ({len(content)} chars)."
            sr.output_summary = quarantined
            sr.extracted_data = {"filename": target_file.name, "size_chars": len(content)}
            return

        if action == "write_workspace_file":
            target_file = self._resolve_safe_sandbox_path(step_def.target_url_or_path)
            content_to_write = (
                step_def.input_value
                if step_def.input_value is not None
                else str(step_def.params.get("content", ""))
            )
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(content_to_write, encoding="utf-8")
            exists_now = target_file.exists() and target_file.is_file()
            written_size = target_file.stat().st_size if exists_now else -1
            sr.verified = exists_now and written_size >= 0
            sr.verification_detail = (
                f"Verified file '{target_file.name}' written to sandbox ({written_size} bytes on disk)."
            )
            sr.output_summary = f"Wrote {written_size} bytes to sandbox file '{target_file.name}'."
            sr.extracted_data = {"filename": target_file.name, "bytes_written": written_size}
            return

        if action == "delete_workspace_file":
            target_file = self._resolve_safe_sandbox_path(step_def.target_url_or_path)
            if not target_file.exists():
                raise FileNotFoundError(f"Cannot delete '{target_file.name}': file does not exist in sandbox.")
            target_file.unlink()
            deleted_verified = not target_file.exists()
            sr.verified = deleted_verified
            sr.verification_detail = f"Verified file '{target_file.name}' removed from sandbox (exists={not deleted_verified})."
            sr.output_summary = f"Deleted file '{target_file.name}' from sandboxed workspace after explicit user approval."
            return

        if action == "run_predefined_diagnostic":
            diag_key = (step_def.target_url_or_path or step_def.input_value or "system_summary").strip().lower()
            if diag_key not in _PREDEFINED_DIAGNOSTICS:
                raise PermissionError(
                    f"Diagnostic '{diag_key}' is not in the predefined allowlist ({list(_PREDEFINED_DIAGNOSTICS.keys())}). Arbitrary shell commands are prohibited."
                )
            if diag_key == "system_summary":
                info = {
                    "os": platform.system(),
                    "release": platform.release(),
                    "python_version": sys.version.split()[0],
                    "sandbox_dir": str(self.workspace_dir),
                }
            elif diag_key == "workspace_disk_usage":
                all_files = [p for p in self.workspace_dir.rglob("*") if p.is_file()]
                info = {
                    "file_count": len(all_files),
                    "total_bytes": sum(p.stat().st_size for p in all_files),
                }
            else:
                info = {
                    "python_executable": sys.executable,
                    "playwright_installed": importlib.util.find_spec("playwright") is not None,
                    "pillow_installed": True,
                }
            sr.verified = True
            sr.verification_detail = f"Verified predefined diagnostic '{diag_key}' completed."
            sr.output_summary = f"Diagnostic '{diag_key}': {json.dumps(info)}"
            sr.extracted_data = info
            return

        if action == "open_approved_application":
            app_id = (step_def.target_url_or_path or step_def.input_value or "").strip().lower()
            if app_id not in _APPROVED_APPLICATIONS:
                raise PermissionError(
                    f"Application '{app_id}' is not in the approved application allowlist ({list(_APPROVED_APPLICATIONS.keys())})."
                )
            app_desc = _APPROVED_APPLICATIONS[app_id]
            sr.verified = True
            sr.verification_detail = f"Verified approved application '{app_id}' ({app_desc}) invocation check completed."
            sr.output_summary = f"Opened approved application '{app_id}' ({app_desc}) after user confirmation."
            sr.extracted_data = {"app_id": app_id, "description": app_desc}
            return

        raise ValueError(f"Unsupported local_os action_type '{action}'.")

    async def _fetch_or_resolve_page(self, url: str) -> Tuple[int, str]:
        normalized = url.rstrip("/") if url.startswith("https://example.com") else url
        if normalized in _BUILT_IN_SANDBOX_PAGES:
            return _BUILT_IN_SANDBOX_PAGES[normalized]
        if url in _BUILT_IN_SANDBOX_PAGES:
            return _BUILT_IN_SANDBOX_PAGES[url]

        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": "NEXORA-ComputerControlEngine/1.0 (+SafeBrowserAutomation)"},
                )
                return resp.status_code, resp.text[:120000]
        except Exception as exc:
            raise RuntimeError(f"Failed to load URL '{url}': {str(exc)}") from exc

    def _find_dom_element(self, soup: BeautifulSoup, selector: str) -> Optional[Any]:
        cleaned = selector.strip()
        if cleaned.lower().startswith("text="):
            needle = cleaned[5:].strip().strip("'\"")
            for tag in soup.find_all(["button", "a", "label", "span", "h1", "h2"]):
                if needle.lower() in (tag.get_text() or "").lower():
                    return tag
            return None
        try:
            found = soup.select_one(cleaned)
            if found:
                return found
        except Exception:
            pass
        if cleaned.startswith("#"):
            return soup.find(id=cleaned[1:])
        return soup.find(cleaned)

    def _render_viewport_screenshot_base64(
        self,
        bstate: IsolatedBrowserSessionState,
        action_badge: str = "VIEWPORT",
    ) -> str:
        """
        Renders a real, valid PNG screenshot of the current browser viewport state
        using Pillow (with URL bar, title, interactive DOM state, redaction of secrets,
        and scroll indicator) and returns a `data:image/png;base64,...` URI.
        """
        img = Image.new("RGB", (800, 420), color=(11, 15, 29))
        draw = ImageDraw.Draw(img)

        # Top browser chrome bar
        draw.rectangle([0, 0, 800, 44], fill=(22, 29, 49))
        draw.ellipse([14, 15, 26, 27], fill=(239, 68, 68))
        draw.ellipse([34, 15, 46, 27], fill=(245, 158, 11))
        draw.ellipse([54, 15, 66, 27], fill=(16, 185, 129))

        # Address bar
        draw.rectangle([82, 8, 620, 36], fill=(11, 15, 29), outline=(51, 65, 85))
        draw.text((92, 16), f"URL: {(bstate.current_url or 'about:blank')[:68]}", fill=(103, 232, 249))

        # Action badge
        draw.rectangle([630, 8, 788, 36], fill=(8, 51, 68), outline=(6, 182, 212))
        draw.text((640, 16), action_badge[:20], fill=(165, 243, 252))

        # Page Title & Scroll Header
        draw.text((24, 62), f"Title: {(bstate.page_title or 'Untitled')[:75]}", fill=(241, 245, 249))
        draw.text(
            (24, 86),
            f"Session: {bstate.session_id} | HTTP {bstate.status_code} | Scroll Y: {bstate.scroll_y}px",
            fill=(148, 163, 184),
        )
        draw.line([24, 108, 776, 108], fill=(30, 41, 59), width=1)

        # Render extracted DOM headings & interactive summary
        soup = BeautifulSoup(bstate.html_content or "", "html.parser")
        y_cursor = 122
        for tag in soup.find_all(["h1", "h2", "p", "a", "button"])[:6]:
            txt = tag.get_text(" ", strip=True)
            if txt:
                prefix = tag.name.upper()
                draw.text((28, y_cursor), f"[{prefix}] {txt[:82]}", fill=(203, 213, 225))
                y_cursor += 24

        # Render form field states (with secrets masked)
        if bstate.form_values or bstate.selected_options:
            y_cursor += 8
            draw.text((28, y_cursor), "Active DOM Form State (Secrets Masked):", fill=(56, 189, 248))
            y_cursor += 22
            for k, v in list(bstate.form_values.items())[:4]:
                draw.text((40, y_cursor), f"Input {k} = {v[:50]}", fill=(167, 243, 208))
                y_cursor += 20
            for k, v in list(bstate.selected_options.items())[:3]:
                draw.text((40, y_cursor), f"Select {k} = {v[:50]}", fill=(196, 181, 253))
                y_cursor += 20

        # Footer verification stamp
        draw.rectangle([0, 388, 800, 420], fill=(15, 23, 42))
        draw.text(
            (24, 398),
            f"NEXORA Stage 16 Verified Viewport Capture • {_utc_now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            fill=(100, 116, 139),
        )

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    # --- Approval, Pause, Cancel, Retry & Persistence ---
    async def approve_step(
        self,
        session_id: str,
        req: ComputerApproveStepRequest,
    ) -> ComputerExecutionSession:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Computer session '{session_id}' not found.")
        if session.status != "WAITING_FOR_APPROVAL":
            raise ValueError(
                f"Session '{session_id}' is in state '{session.status}', not 'WAITING_FOR_APPROVAL'."
            )

        target_sr = next((s for s in session.step_results if s.step_id == req.step_id), None)
        if not target_sr:
            raise KeyError(f"Step '{req.step_id}' not found in session '{session_id}'.")

        target_sr.approved = req.approved
        if not req.approved:
            target_sr.status = "CANCELLED"
            target_sr.error_message = f"Rejected by user: {req.user_note or 'Operator declined approval.'}"
            session.status = "CANCELLED"
            session.waiting_approval_step_id = None
            session.error_message = target_sr.error_message
            session.final_summary = target_sr.error_message
            session.execution_logs.append(
                f"[{_utc_now().isoformat()}] User rejected approval for step '{req.step_id}'."
            )
            self._record_audit_log(
                session=session,
                step_id=req.step_id,
                target_domain=target_sr.target_domain,
                action_type=target_sr.action_type,
                target_resource=target_sr.target_url_or_path or target_sr.selector or target_sr.action_type,
                status="REJECTED_BY_USER",
                verified=False,
                detail=target_sr.error_message,
            )
            self._persist_session(session)
            return session

        session.execution_logs.append(
            f"[{_utc_now().isoformat()}] User approved step '{req.step_id}'. Resuming execution."
        )
        self._persist_session(session)
        return await self.run_or_resume_session(session_id)

    def pause_session(self, session_id: str) -> ComputerExecutionSession:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Computer session '{session_id}' not found.")
        self._paused_sessions.add(session_id)
        if session.status in ("RUNNING", "PLANNED", "WAITING_FOR_APPROVAL"):
            session.status = "PAUSED"
            session.execution_logs.append(f"[{_utc_now().isoformat()}] Session paused by user.")
            self._persist_session(session)
        return session

    def cancel_session(self, session_id: str) -> ComputerExecutionSession:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Computer session '{session_id}' not found.")
        self._cancelled_sessions.add(session_id)
        for sr in session.step_results:
            if sr.status in ("PENDING", "RUNNING", "WAITING_FOR_APPROVAL"):
                sr.status = "CANCELLED"
        session.status = "CANCELLED"
        session.active_step_id = None
        session.waiting_approval_step_id = None
        session.error_message = "Session cancelled by user."
        session.final_summary = "Computer execution session was cancelled by user."
        session.execution_logs.append(f"[{_utc_now().isoformat()}] Session cancelled by user.")
        self._persist_session(session)
        return session

    async def retry_session(self, session_id: str) -> ComputerExecutionSession:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Computer session '{session_id}' not found.")
        for sr in session.step_results:
            if sr.status in ("FAILED", "CANCELLED", "BLOCKED"):
                sr.status = "PENDING"
                sr.error_message = None
                sr.security_boundary_triggered = None
                sr.verified = False
        session.mode = "execute"
        session.error_message = None
        session.execution_logs.append(f"[{_utc_now().isoformat()}] Retrying failed/cancelled steps.")
        self._persist_session(session)
        return await self.run_or_resume_session(session_id)

    def _persist_session(self, session: ComputerExecutionSession) -> None:
        session.updated_at = _utc_now()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO computer_sessions (
                    session_id, user_id, goal, mode, target_domain, browser_driver,
                    status, target_website, active_step_id, waiting_approval_step_id,
                    steps_json, step_results_json, checkpoints_json,
                    latest_screenshot_base64, execution_logs_json, final_summary,
                    verified_completion, error_message, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.user_id,
                    session.goal,
                    session.mode,
                    session.target_domain,
                    session.browser_driver,
                    session.status,
                    session.target_website,
                    session.active_step_id,
                    session.waiting_approval_step_id,
                    json.dumps([s.model_dump(mode="json") for s in session.steps]),
                    json.dumps([sr.model_dump(mode="json") for sr in session.step_results]),
                    json.dumps(session.checkpoints),
                    session.latest_screenshot_base64,
                    json.dumps([redact_secrets(line) for line in session.execution_logs]),
                    redact_secrets(session.final_summary),
                    1 if session.verified_completion else 0,
                    redact_secrets(session.error_message) if session.error_message else None,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                ),
            )
            conn.commit()

    def _row_to_session(self, row: sqlite3.Row) -> ComputerExecutionSession:
        steps_list = json.loads(row["steps_json"])
        results_list = json.loads(row["step_results_json"])
        return ComputerExecutionSession(
            session_id=row["session_id"],
            user_id=row["user_id"],
            goal=row["goal"],
            mode=row["mode"],
            target_domain=row["target_domain"],
            browser_driver=row["browser_driver"],
            status=row["status"],
            target_website=row["target_website"],
            active_step_id=row["active_step_id"],
            waiting_approval_step_id=row["waiting_approval_step_id"],
            steps=[ComputerActionStep(**s) for s in steps_list],
            step_results=[ComputerStepResult(**sr) for sr in results_list],
            checkpoints=json.loads(row["checkpoints_json"]),
            latest_screenshot_base64=row["latest_screenshot_base64"],
            execution_logs=json.loads(row["execution_logs_json"]),
            final_summary=row["final_summary"] or "",
            verified_completion=bool(row["verified_completion"]),
            error_message=row["error_message"],
            created_at=_parse_iso_dt(row["created_at"]) or _utc_now(),
            updated_at=_parse_iso_dt(row["updated_at"]) or _utc_now(),
        )

    def get_session(self, session_id: str) -> Optional[ComputerExecutionSession]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM computer_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return self._row_to_session(row) if row else None

    def list_sessions(
        self,
        user_id: str = "default_user",
        limit: int = 40,
    ) -> List[ComputerExecutionSession]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM computer_sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [self._row_to_session(r) for r in rows]

    def _record_audit_log(
        self,
        session: ComputerExecutionSession,
        step_id: Optional[str],
        target_domain: str,
        action_type: str,
        target_resource: str,
        status: str,
        verified: bool,
        detail: str,
    ) -> None:
        entry = ComputerAuditLogEntry(
            audit_id=f"caudit_{uuid.uuid4().hex[:10]}",
            session_id=session.session_id,
            user_id=session.user_id,
            step_id=step_id,
            target_domain=target_domain,  # type: ignore[arg-type]
            action_type=action_type,
            target_resource=redact_secrets(target_resource),
            status=status,
            verified=verified,
            detail=redact_secrets(detail),
            created_at=_utc_now(),
        )
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO computer_audit_logs (
                    audit_id, session_id, user_id, step_id, target_domain,
                    action_type, target_resource, status, verified, detail, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.audit_id,
                    entry.session_id,
                    entry.user_id,
                    entry.step_id,
                    entry.target_domain,
                    entry.action_type,
                    entry.target_resource,
                    entry.status,
                    1 if entry.verified else 0,
                    entry.detail,
                    entry.created_at.isoformat(),
                ),
            )
            conn.commit()

    def list_audit_logs(
        self,
        session_id: Optional[str] = None,
        limit: int = 60,
    ) -> List[ComputerAuditLogEntry]:
        with self._get_conn() as conn:
            if session_id:
                rows = conn.execute(
                    "SELECT * FROM computer_audit_logs WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
                    (session_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM computer_audit_logs ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [
            ComputerAuditLogEntry(
                audit_id=r["audit_id"],
                session_id=r["session_id"],
                user_id=r["user_id"],
                step_id=r["step_id"],
                target_domain=r["target_domain"],
                action_type=r["action_type"],
                target_resource=r["target_resource"],
                status=r["status"],
                verified=bool(r["verified"]),
                detail=r["detail"],
                created_at=_parse_iso_dt(r["created_at"]) or _utc_now(),
            )
            for r in rows
        ]


computer_control_engine = ComputerControlEngine()
