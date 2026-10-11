import asyncio
import json
import re
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from app.config import settings
from app.models.schemas import (
    MultiAgentRunRequest,
    WorkflowApproveStepRequest,
    WorkflowCreateRequest,
    WorkflowDefinition,
    WorkflowExecutionRun,
    WorkflowNotificationConfig,
    WorkflowNotificationItem,
    WorkflowRetryRunRequest,
    WorkflowRunStatus,
    WorkflowScheduleConfig,
    WorkflowStatus,
    WorkflowStepDefinition,
    WorkflowStepExecutionResult,
    WorkflowTriggerRunRequest,
    WorkflowUpdateRequest,
    WorkflowValidationIssue,
    WorkflowValidationResult,
)
from app.services.agents.orchestrator import multi_agent_orchestrator
from app.services.tools_registry import tool_registry


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


# Built-in fallback offsets for common IANA timezones in case Windows lacks OS tzdata
_IANA_FALLBACK_OFFSETS: Dict[str, timezone] = {
    "UTC": timezone.utc,
    "Etc/UTC": timezone.utc,
    "GMT": timezone.utc,
    "Asia/Kolkata": timezone(timedelta(hours=5, minutes=30), "IST"),
    "Asia/Calcutta": timezone(timedelta(hours=5, minutes=30), "IST"),
    "Asia/Tokyo": timezone(timedelta(hours=9), "JST"),
    "Asia/Singapore": timezone(timedelta(hours=8), "SGT"),
    "Asia/Dubai": timezone(timedelta(hours=4), "GST"),
    "Europe/London": timezone.utc,
    "Europe/Berlin": timezone(timedelta(hours=1), "CET"),
    "Europe/Paris": timezone(timedelta(hours=1), "CET"),
    "America/New_York": timezone(timedelta(hours=-5), "EST"),
    "America/Chicago": timezone(timedelta(hours=-6), "CST"),
    "America/Denver": timezone(timedelta(hours=-7), "MST"),
    "America/Los_Angeles": timezone(timedelta(hours=-8), "PST"),
    "Australia/Sydney": timezone(timedelta(hours=10), "AEST"),
}

_CONSEQUENTIAL_KEYWORDS = re.compile(
    r"\b(delete|remove\s+file|drop\s+table|publish|send\s+email|dispatch|spend\s+money|purchase|payment|billing|modify\s+account|delete_document|dispatch_external_message)\b",
    re.IGNORECASE,
)

_SENSITIVE_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9\-_]{16,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"AIza[A-Za-z0-9\-_]{20,}"), "[REDACTED_GEMINI_KEY]"),
    (re.compile(r"(?i)(password|secret|api_key|token|authorization)\s*[:=]\s*['\"]?[^\s,'\"]+"), r"\1=[REDACTED]"),
]


def redact_sensitive_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text
    for pattern, replacement in _SENSITIVE_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


def resolve_timezone(tz_name: str) -> tzinfo:
    if not tz_name or not tz_name.strip():
        raise ValueError("Timezone name cannot be empty.")
    cleaned = tz_name.strip()
    if cleaned in _IANA_FALLBACK_OFFSETS:
        try:
            return ZoneInfo(cleaned)
        except ZoneInfoNotFoundError:
            return _IANA_FALLBACK_OFFSETS[cleaned]
    # Support explicit UTC+HH:MM or UTC-HH:MM
    m = re.match(r"^UTC([+-])(\d{1,2})(?::(\d{2}))?$", cleaned, re.IGNORECASE)
    if m:
        sign = 1 if m.group(1) == "+" else -1
        hours = int(m.group(2))
        mins = int(m.group(3) or "0")
        if hours > 14 or mins >= 60:
            raise ValueError(f"Invalid UTC offset: {cleaned}")
        return timezone(sign * timedelta(hours=hours, minutes=mins), cleaned)
    try:
        return ZoneInfo(cleaned)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unsupported or unknown timezone '{cleaned}'.") from exc


class WorkflowAutomationEngine:
    """
    Stage 15: NEXORA AI Workflow Automation Engine.
    Provides durable SQLite storage, DAG step validation, input/output templating,
    branching & bounded retries, consequential approval gates, timezone-aware scheduling,
    duplicate/overlap prevention, worker crash recovery, and verified notifications.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or settings.workflow_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._cancelled_runs: Set[str] = set()
        self._active_run_tasks: Dict[str, asyncio.Task] = {}
        self._rate_limit_buckets: Dict[str, List[float]] = {}
        self._scheduler_task: Optional[asyncio.Task] = None
        self._init_db()
        self._seed_default_templates()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    status TEXT NOT NULL,
                    is_template INTEGER NOT NULL DEFAULT 0,
                    schedule_json TEXT NOT NULL,
                    steps_json TEXT NOT NULL,
                    notification_json TEXT NOT NULL,
                    max_cost_budget_usd REAL NOT NULL DEFAULT 0.50,
                    total_runs INTEGER NOT NULL DEFAULT 0,
                    succeeded_runs INTEGER NOT NULL DEFAULT 0,
                    failed_runs INTEGER NOT NULL DEFAULT 0,
                    last_run_status TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    run_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    workflow_name TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    trigger_source TEXT NOT NULL,
                    idempotency_key TEXT UNIQUE,
                    status TEXT NOT NULL,
                    is_dry_run INTEGER NOT NULL DEFAULT 0,
                    runtime_inputs_json TEXT NOT NULL,
                    step_results_json TEXT NOT NULL,
                    completed_steps INTEGER NOT NULL DEFAULT 0,
                    total_steps INTEGER NOT NULL DEFAULT 0,
                    progress_percent REAL NOT NULL DEFAULT 0.0,
                    current_step_id TEXT,
                    waiting_approval_step_id TEXT,
                    final_summary TEXT NOT NULL DEFAULT '',
                    error_message TEXT,
                    total_estimated_cost_usd REAL NOT NULL DEFAULT 0.0,
                    max_cost_budget_usd REAL NOT NULL DEFAULT 0.50,
                    queued_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    duration_ms REAL NOT NULL DEFAULT 0.0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_notifications (
                    notification_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    workflow_name TEXT NOT NULL,
                    run_id TEXT,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    read INTEGER NOT NULL DEFAULT 0,
                    external_channels_json TEXT NOT NULL,
                    external_delivery_status TEXT NOT NULL,
                    external_delivery_confirmed INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _seed_default_templates(self) -> None:
        templates = [
            WorkflowDefinition(
                workflow_id="tpl_daily_tech_digest",
                user_id="system",
                name="Daily Tech & Research Verification Digest",
                description="Searches live technology & AI updates, verifies key claims with the Fact-Check tool, and synthesizes an executive digest.",
                category="research",
                status="ACTIVE",
                is_template=True,
                schedule=WorkflowScheduleConfig(
                    trigger_type="scheduled",
                    recurrence="daily",
                    interval_minutes=1440,
                    timezone="Asia/Kolkata",
                    allow_concurrent_runs=False,
                ),
                steps=[
                    WorkflowStepDefinition(
                        step_id="step_1_search",
                        name="Fetch Live Tech Pulse",
                        description="Retrieves live technology headlines from Stage 8 Real-Time Engine.",
                        action_type="tool",
                        tool_name="realtime_pulse",
                        tool_params={"category": "technology", "query": "{{workflow.input.topic}}"},
                        output_key="pulse_summary",
                    ),
                    WorkflowStepDefinition(
                        step_id="step_2_factcheck",
                        name="Verify Top Claim",
                        description="Fact-checks the retrieved technology pulse before drafting.",
                        action_type="tool",
                        tool_name="fact_check",
                        tool_params={"claim": "{{steps.step_1_search.output}}"},
                        depends_on=["step_1_search"],
                        condition_expression="previous_succeeded",
                    ),
                    WorkflowStepDefinition(
                        step_id="step_3_briefing",
                        name="Draft Executive Summary",
                        description="Uses the Writing Agent to synthesize verified findings.",
                        action_type="agent",
                        agent_id="writing_agent",
                        prompt_template="Create a concise executive digest from these verified findings:\nPulse: {{steps.step_1_search.output}}\nVerification: {{steps.step_2_factcheck.output}}",
                        depends_on=["step_2_factcheck"],
                        condition_expression="previous_succeeded",
                    ),
                ],
                max_cost_budget_usd=0.25,
            ),
            WorkflowDefinition(
                workflow_id="tpl_document_compliance_audit",
                user_id="system",
                name="Document Vault Fact & Compliance Audit",
                description="Queries uploaded documents in the Stage 4 Vault, analyzes clauses via the Document Agent, and generates a compliance checklist.",
                category="documents",
                status="ACTIVE",
                is_template=True,
                schedule=WorkflowScheduleConfig(trigger_type="manual", timezone="UTC"),
                steps=[
                    WorkflowStepDefinition(
                        step_id="step_1_retrieve",
                        name="Query Document Vault",
                        description="Retrieves relevant passages from uploaded documents.",
                        action_type="tool",
                        tool_name="document_retrieval",
                        tool_params={"query": "{{workflow.input.audit_query}}", "top_k": 4},
                    ),
                    WorkflowStepDefinition(
                        step_id="step_2_analyze",
                        name="Analyze Excerpts & Risks",
                        description="Document Agent inspects retrieved excerpts for risks and missing clauses.",
                        action_type="agent",
                        agent_id="document_agent",
                        prompt_template="Analyze these document excerpts for compliance and key obligations:\n{{steps.step_1_retrieve.output}}",
                        depends_on=["step_1_retrieve"],
                    ),
                    WorkflowStepDefinition(
                        step_id="step_3_checklist",
                        name="Generate Action Checklist",
                        description="Productivity Agent creates an actionable checklist.",
                        action_type="agent",
                        agent_id="productivity_agent",
                        prompt_template="Convert this document analysis into a prioritized action checklist:\n{{steps.step_2_analyze.output}}",
                        depends_on=["step_2_analyze"],
                    ),
                ],
                max_cost_budget_usd=0.25,
            ),
            WorkflowDefinition(
                workflow_id="tpl_multilingual_release_notes",
                user_id="system",
                name="Multilingual Release Notes & Localization Pipeline",
                description="Drafts structured product release notes and translates them into Tamil (or target language) with phonetic transliteration.",
                category="multilingual",
                status="ACTIVE",
                is_template=True,
                schedule=WorkflowScheduleConfig(trigger_type="manual", timezone="UTC"),
                steps=[
                    WorkflowStepDefinition(
                        step_id="step_1_draft",
                        name="Draft Release Notes",
                        description="Writing Agent drafts structured release highlights.",
                        action_type="agent",
                        agent_id="writing_agent",
                        prompt_template="Write concise release notes for: {{workflow.input.feature_summary}}",
                    ),
                    WorkflowStepDefinition(
                        step_id="step_2_translate",
                        name="Translate & Transliterate",
                        description="Translates drafted notes using Stage 6 Multilingual Engine.",
                        action_type="tool",
                        tool_name="translation",
                        tool_params={
                            "text": "{{steps.step_1_draft.output}}",
                            "target_language": "{{workflow.input.target_language}}",
                        },
                        depends_on=["step_1_draft"],
                    ),
                ],
                max_cost_budget_usd=0.20,
            ),
            WorkflowDefinition(
                workflow_id="tpl_approved_external_dispatch",
                user_id="system",
                name="Gated External Incident Dispatch (Approval Required)",
                description="Calculates SLA metrics, prepares an incident report, and pauses at a mandatory human approval gate before dispatching externally.",
                category="operations",
                status="ACTIVE",
                is_template=True,
                schedule=WorkflowScheduleConfig(trigger_type="manual", timezone="UTC"),
                steps=[
                    WorkflowStepDefinition(
                        step_id="step_1_calc",
                        name="Compute SLA Metrics",
                        description="Evaluates mathematical metric expression via AST calculator.",
                        action_type="tool",
                        tool_name="calculator",
                        tool_params={"expression": "{{workflow.input.formula}}"},
                    ),
                    WorkflowStepDefinition(
                        step_id="step_2_dispatch",
                        name="Dispatch External Alert",
                        description="Sends external webhook notification. Always pauses for explicit human approval.",
                        action_type="tool",
                        tool_name="dispatch_external_message",
                        tool_params={
                            "recipient": "{{workflow.input.recipient}}",
                            "subject": "NEXORA Automated SLA Report",
                            "body": "Calculated metric output: {{steps.step_1_calc.output}}",
                        },
                        depends_on=["step_1_calc"],
                        requires_approval=True,
                        approval_reason="Sending an external message/webhook outside NEXORA requires explicit human approval.",
                    ),
                ],
                max_cost_budget_usd=0.15,
            ),
        ]

        with self._get_conn() as conn:
            for tpl in templates:
                existing = conn.execute(
                    "SELECT workflow_id FROM workflows WHERE workflow_id = ?",
                    (tpl.workflow_id,),
                ).fetchone()
                if not existing:
                    self._save_workflow_row(conn, tpl)
            conn.commit()

    def _save_workflow_row(self, conn: sqlite3.Connection, wf: WorkflowDefinition) -> None:
        conn.execute(
            """
            INSERT OR REPLACE INTO workflows (
                workflow_id, user_id, name, description, category, status, is_template,
                schedule_json, steps_json, notification_json, max_cost_budget_usd,
                total_runs, succeeded_runs, failed_runs, last_run_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                wf.workflow_id,
                wf.user_id,
                wf.name,
                wf.description,
                wf.category,
                wf.status,
                1 if wf.is_template else 0,
                json.dumps(wf.schedule.model_dump(mode="json")),
                json.dumps([s.model_dump(mode="json") for s in wf.steps]),
                json.dumps(wf.notification_config.model_dump(mode="json")),
                wf.max_cost_budget_usd,
                wf.total_runs,
                wf.succeeded_runs,
                wf.failed_runs,
                wf.last_run_status,
                wf.created_at.isoformat(),
                wf.updated_at.isoformat(),
            ),
        )

    def _row_to_workflow(self, row: sqlite3.Row) -> WorkflowDefinition:
        sched_dict = json.loads(row["schedule_json"])
        steps_list = json.loads(row["steps_json"])
        notif_dict = json.loads(row["notification_json"])
        return WorkflowDefinition(
            workflow_id=row["workflow_id"],
            user_id=row["user_id"],
            name=row["name"],
            description=row["description"],
            category=row["category"],
            status=row["status"],
            is_template=bool(row["is_template"]),
            schedule=WorkflowScheduleConfig(**sched_dict),
            steps=[WorkflowStepDefinition(**s) for s in steps_list],
            notification_config=WorkflowNotificationConfig(**notif_dict),
            max_cost_budget_usd=float(row["max_cost_budget_usd"]),
            total_runs=int(row["total_runs"]),
            succeeded_runs=int(row["succeeded_runs"]),
            failed_runs=int(row["failed_runs"]),
            last_run_status=row["last_run_status"],
            created_at=_parse_iso_dt(row["created_at"]) or _utc_now(),
            updated_at=_parse_iso_dt(row["updated_at"]) or _utc_now(),
        )

    def _save_run_row(self, conn: sqlite3.Connection, run: WorkflowExecutionRun) -> None:
        conn.execute(
            """
            INSERT OR REPLACE INTO workflow_runs (
                run_id, workflow_id, workflow_name, user_id, trigger_source, idempotency_key,
                status, is_dry_run, runtime_inputs_json, step_results_json,
                completed_steps, total_steps, progress_percent, current_step_id,
                waiting_approval_step_id, final_summary, error_message,
                total_estimated_cost_usd, max_cost_budget_usd,
                queued_at, started_at, completed_at, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.run_id,
                run.workflow_id,
                run.workflow_name,
                run.user_id,
                run.trigger_source,
                run.idempotency_key,
                run.status,
                1 if run.is_dry_run else 0,
                json.dumps(run.runtime_inputs),
                json.dumps([sr.model_dump(mode="json") for sr in run.step_results]),
                run.completed_steps,
                run.total_steps,
                run.progress_percent,
                run.current_step_id,
                run.waiting_approval_step_id,
                redact_sensitive_text(run.final_summary),
                redact_sensitive_text(run.error_message) if run.error_message else None,
                run.total_estimated_cost_usd,
                run.max_cost_budget_usd,
                run.queued_at.isoformat(),
                run.started_at.isoformat() if run.started_at else None,
                run.completed_at.isoformat() if run.completed_at else None,
                run.duration_ms,
            ),
        )

    def _row_to_run(self, row: sqlite3.Row) -> WorkflowExecutionRun:
        steps_data = json.loads(row["step_results_json"])
        return WorkflowExecutionRun(
            run_id=row["run_id"],
            workflow_id=row["workflow_id"],
            workflow_name=row["workflow_name"],
            user_id=row["user_id"],
            trigger_source=row["trigger_source"],
            idempotency_key=row["idempotency_key"],
            status=row["status"],
            is_dry_run=bool(row["is_dry_run"]),
            runtime_inputs=json.loads(row["runtime_inputs_json"]),
            step_results=[WorkflowStepExecutionResult(**s) for s in steps_data],
            completed_steps=int(row["completed_steps"]),
            total_steps=int(row["total_steps"]),
            progress_percent=float(row["progress_percent"]),
            current_step_id=row["current_step_id"],
            waiting_approval_step_id=row["waiting_approval_step_id"],
            final_summary=row["final_summary"] or "",
            error_message=row["error_message"],
            total_estimated_cost_usd=float(row["total_estimated_cost_usd"]),
            max_cost_budget_usd=float(row["max_cost_budget_usd"]),
            queued_at=_parse_iso_dt(row["queued_at"]) or _utc_now(),
            started_at=_parse_iso_dt(row["started_at"]),
            completed_at=_parse_iso_dt(row["completed_at"]),
            duration_ms=float(row["duration_ms"]),
        )

    # --- Scheduling & Timezone Calculation ---
    def calculate_next_run_at(
        self,
        schedule: WorkflowScheduleConfig,
        reference_utc: Optional[datetime] = None,
    ) -> Optional[datetime]:
        if schedule.trigger_type != "scheduled":
            return None
        tz = resolve_timezone(schedule.timezone)
        now_utc = reference_utc or _utc_now()
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)

        now_local = now_utc.astimezone(tz)
        if schedule.start_at:
            start_dt = schedule.start_at
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=tz)
            else:
                start_dt = start_dt.astimezone(tz)
            if start_dt > now_local:
                return start_dt.astimezone(timezone.utc)

        if schedule.recurrence == "once":
            if schedule.last_run_at is not None:
                return None
            if schedule.start_at:
                start_dt = schedule.start_at
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=tz)
                return start_dt.astimezone(timezone.utc)
            return (now_local + timedelta(minutes=1)).astimezone(timezone.utc)

        if schedule.recurrence == "hourly":
            next_local = now_local + timedelta(hours=1)
        elif schedule.recurrence == "daily":
            next_local = now_local + timedelta(days=1)
        elif schedule.recurrence == "weekly":
            next_local = now_local + timedelta(weeks=1)
        else:  # interval
            mins = max(1, schedule.interval_minutes)
            next_local = now_local + timedelta(minutes=mins)

        return next_local.astimezone(timezone.utc)

    # --- Validation & Topological Sorting ---
    def validate_workflow_definition(
        self,
        steps: List[WorkflowStepDefinition],
        schedule: Optional[WorkflowScheduleConfig] = None,
        max_cost_budget_usd: float = 0.50,
    ) -> WorkflowValidationResult:
        issues: List[WorkflowValidationIssue] = []
        requires_approval_steps: List[str] = []

        if schedule:
            try:
                resolve_timezone(schedule.timezone)
            except ValueError as exc:
                issues.append(
                    WorkflowValidationIssue(
                        severity="error",
                        code="INVALID_TIMEZONE",
                        message=str(exc),
                    )
                )

        if not steps:
            issues.append(
                WorkflowValidationIssue(
                    severity="error",
                    code="EMPTY_WORKFLOW",
                    message="Workflow must contain at least one task step.",
                )
            )
            return WorkflowValidationResult(valid=False, issues=issues)

        if len(steps) > settings.workflow_max_steps:
            issues.append(
                WorkflowValidationIssue(
                    severity="error",
                    code="MAX_STEPS_EXCEEDED",
                    message=f"Workflow has {len(steps)} steps, exceeding the maximum allowed ({settings.workflow_max_steps}).",
                )
            )

        step_map: Dict[str, WorkflowStepDefinition] = {}
        step_index_map: Dict[str, int] = {}
        for idx, step in enumerate(steps):
            if step.step_id in step_map:
                issues.append(
                    WorkflowValidationIssue(
                        severity="error",
                        step_id=step.step_id,
                        code="DUPLICATE_STEP_ID",
                        message=f"Duplicate step_id '{step.step_id}' detected.",
                    )
                )
            step_map[step.step_id] = step
            step_index_map[step.step_id] = idx

        available_agents = {a.agent_id for a in multi_agent_orchestrator.list_agents()}
        available_tools = {t.name: t for t in tool_registry.list_tools()}

        for idx, step in enumerate(steps):
            # Validate retries cap
            if step.max_retries > settings.workflow_max_step_retries:
                issues.append(
                    WorkflowValidationIssue(
                        severity="error",
                        step_id=step.step_id,
                        code="MAX_RETRIES_EXCEEDED",
                        message=f"Step '{step.name}' requests {step.max_retries} retries; maximum allowed is {settings.workflow_max_step_retries}.",
                    )
                )

            # Validate action target
            if step.action_type == "agent":
                if not step.agent_id or step.agent_id not in available_agents:
                    issues.append(
                        WorkflowValidationIssue(
                            severity="error",
                            step_id=step.step_id,
                            code="UNKNOWN_AGENT",
                            message=f"Step '{step.name}' references unknown or unconfigured agent '{step.agent_id}'.",
                        )
                    )
                if not step.prompt_template.strip():
                    issues.append(
                        WorkflowValidationIssue(
                            severity="error",
                            step_id=step.step_id,
                            code="EMPTY_AGENT_PROMPT",
                            message=f"Agent step '{step.name}' requires a non-empty prompt_template.",
                        )
                    )
            elif step.action_type == "tool":
                if not step.tool_name or step.tool_name not in available_tools:
                    issues.append(
                        WorkflowValidationIssue(
                            severity="error",
                            step_id=step.step_id,
                            code="UNKNOWN_TOOL",
                            message=f"Step '{step.name}' references unregistered tool '{step.tool_name}'.",
                        )
                    )
                else:
                    tdef = available_tools[step.tool_name]
                    if tdef.requires_approval and step.step_id not in requires_approval_steps:
                        requires_approval_steps.append(step.step_id)

            if self._step_requires_consequential_approval(step) and step.step_id not in requires_approval_steps:
                requires_approval_steps.append(step.step_id)

            # Validate dependencies exist
            for dep in step.depends_on:
                if dep == step.step_id:
                    issues.append(
                        WorkflowValidationIssue(
                            severity="error",
                            step_id=step.step_id,
                            code="SELF_DEPENDENCY",
                            message=f"Step '{step.step_id}' cannot depend on itself.",
                        )
                    )
                elif dep not in step_map:
                    issues.append(
                        WorkflowValidationIssue(
                            severity="error",
                            step_id=step.step_id,
                            code="MISSING_DEPENDENCY",
                            message=f"Step '{step.step_id}' depends on non-existent step '{dep}'.",
                        )
                    )

            # Validate jump target (must jump forward to prevent infinite loops)
            if step.on_condition_false == "jump_to_step":
                if not step.jump_to_step_id or step.jump_to_step_id not in step_index_map:
                    issues.append(
                        WorkflowValidationIssue(
                            severity="error",
                            step_id=step.step_id,
                            code="INVALID_JUMP_TARGET",
                            message=f"Step '{step.step_id}' specifies jump_to_step_id '{step.jump_to_step_id}' which does not exist.",
                        )
                    )
                elif step_index_map[step.jump_to_step_id] <= idx:
                    issues.append(
                        WorkflowValidationIssue(
                            severity="error",
                            step_id=step.step_id,
                            code="BACKWARD_JUMP_LOOP",
                            message=f"Step '{step.step_id}' attempts a backward jump to '{step.jump_to_step_id}', which is prohibited to prevent infinite loops.",
                        )
                    )

        # Cycle detection via Kahn's algorithm
        in_degree: Dict[str, int] = {s.step_id: 0 for s in steps}
        adj: Dict[str, List[str]] = {s.step_id: [] for s in steps}
        for s in steps:
            for dep in s.depends_on:
                if dep in adj and dep != s.step_id:
                    adj[dep].append(s.step_id)
                    in_degree[s.step_id] += 1

        queue = [s.step_id for s in steps if in_degree[s.step_id] == 0]
        execution_order: List[str] = []
        while queue:
            curr = queue.pop(0)
            execution_order.append(curr)
            for nxt in adj.get(curr, []):
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        if len(execution_order) != len(step_map):
            issues.append(
                WorkflowValidationIssue(
                    severity="error",
                    code="DEPENDENCY_CYCLE_DETECTED",
                    message="Circular dependency detected among workflow steps. Workflows must form a valid Directed Acyclic Graph (DAG).",
                )
            )

        estimated_cost = round(sum(0.015 if s.action_type == "agent" else 0.002 for s in steps), 4)
        if estimated_cost > max_cost_budget_usd:
            issues.append(
                WorkflowValidationIssue(
                    severity="warning",
                    code="ESTIMATED_COST_NEAR_BUDGET",
                    message=f"Estimated workflow cost (${estimated_cost:.4f}) exceeds configured budget (${max_cost_budget_usd:.4f}).",
                )
            )

        has_errors = any(i.severity == "error" for i in issues)
        return WorkflowValidationResult(
            valid=not has_errors,
            issues=issues,
            execution_order=execution_order if not has_errors else [],
            estimated_max_cost_usd=estimated_cost,
            requires_approval_steps=requires_approval_steps,
        )

    def _step_requires_consequential_approval(self, step: WorkflowStepDefinition) -> bool:
        if step.requires_approval:
            return True
        if step.action_type == "tool" and step.tool_name:
            tdef = tool_registry.get_tool(step.tool_name)
            if tdef and tdef.requires_approval:
                return True
        combined_text = f"{step.name} {step.description} {step.prompt_template} {json.dumps(step.tool_params)}"
        if _CONSEQUENTIAL_KEYWORDS.search(combined_text):
            return True
        return False

    # --- CRUD & Workflow Management ---
    def list_workflows(
        self,
        user_id: str = "default_user",
        include_templates: bool = False,
        status_filter: Optional[str] = None,
    ) -> List[WorkflowDefinition]:
        with self._get_conn() as conn:
            if include_templates:
                rows = conn.execute(
                    "SELECT * FROM workflows WHERE (user_id = ? OR is_template = 1) ORDER BY is_template ASC, updated_at DESC",
                    (user_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM workflows WHERE user_id = ? AND is_template = 0 ORDER BY updated_at DESC",
                    (user_id,),
                ).fetchall()
        workflows = [self._row_to_workflow(r) for r in rows]
        if status_filter:
            workflows = [w for w in workflows if w.status == status_filter]
        return workflows

    def list_templates(self) -> List[WorkflowDefinition]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM workflows WHERE is_template = 1 ORDER BY name ASC"
            ).fetchall()
        return [self._row_to_workflow(r) for r in rows]

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM workflows WHERE workflow_id = ?",
                (workflow_id,),
            ).fetchone()
        return self._row_to_workflow(row) if row else None

    def create_workflow(self, req: WorkflowCreateRequest) -> WorkflowDefinition:
        validation = self.validate_workflow_definition(
            steps=req.steps,
            schedule=req.schedule,
            max_cost_budget_usd=req.max_cost_budget_usd,
        )
        if not validation.valid:
            err_msgs = "; ".join(i.message for i in validation.issues if i.severity == "error")
            raise ValueError(f"Workflow validation failed: {err_msgs}")

        now = _utc_now()
        schedule = req.schedule.model_copy(deep=True)
        if schedule.trigger_type == "scheduled" and req.status == "ACTIVE":
            schedule.next_run_at = self.calculate_next_run_at(schedule, now)

        wf = WorkflowDefinition(
            workflow_id=f"wf_{uuid.uuid4().hex[:10]}",
            user_id=req.user_id,
            name=req.name.strip(),
            description=req.description.strip(),
            category=req.category.strip() or "general",
            status=req.status,
            is_template=False,
            schedule=schedule,
            steps=req.steps,
            notification_config=req.notification_config,
            max_cost_budget_usd=req.max_cost_budget_usd,
            created_at=now,
            updated_at=now,
        )
        with self._get_conn() as conn:
            self._save_workflow_row(conn, wf)
            conn.commit()
        return wf

    def update_workflow(self, workflow_id: str, req: WorkflowUpdateRequest) -> WorkflowDefinition:
        existing = self.get_workflow(workflow_id)
        if not existing:
            raise KeyError(f"Workflow '{workflow_id}' not found.")
        if existing.is_template:
            raise ValueError("System templates cannot be modified directly; duplicate the template first.")

        new_steps = req.steps if req.steps is not None else existing.steps
        new_schedule = req.schedule if req.schedule is not None else existing.schedule
        new_budget = req.max_cost_budget_usd if req.max_cost_budget_usd is not None else existing.max_cost_budget_usd
        new_status = req.status if req.status is not None else existing.status

        validation = self.validate_workflow_definition(
            steps=new_steps,
            schedule=new_schedule,
            max_cost_budget_usd=new_budget,
        )
        if not validation.valid:
            err_msgs = "; ".join(i.message for i in validation.issues if i.severity == "error")
            raise ValueError(f"Workflow validation failed: {err_msgs}")

        now = _utc_now()
        if new_schedule.trigger_type == "scheduled" and new_status == "ACTIVE":
            new_schedule.next_run_at = self.calculate_next_run_at(new_schedule, now)
        elif new_status in ("PAUSED", "DISABLED", "DRAFT"):
            new_schedule.next_run_at = None

        updated = existing.model_copy(
            update={
                "name": req.name.strip() if req.name else existing.name,
                "description": req.description.strip() if req.description is not None else existing.description,
                "category": req.category if req.category is not None else existing.category,
                "status": new_status,
                "schedule": new_schedule,
                "steps": new_steps,
                "notification_config": req.notification_config or existing.notification_config,
                "max_cost_budget_usd": new_budget,
                "updated_at": now,
            }
        )
        with self._get_conn() as conn:
            self._save_workflow_row(conn, updated)
            conn.commit()
        return updated

    def set_workflow_status(self, workflow_id: str, status: WorkflowStatus) -> WorkflowDefinition:
        existing = self.get_workflow(workflow_id)
        if not existing:
            raise KeyError(f"Workflow '{workflow_id}' not found.")
        now = _utc_now()
        sched = existing.schedule.model_copy(deep=True)
        if status == "ACTIVE" and sched.trigger_type == "scheduled":
            sched.next_run_at = self.calculate_next_run_at(sched, now)
        elif status in ("PAUSED", "DISABLED", "DRAFT"):
            sched.next_run_at = None

        updated = existing.model_copy(
            update={"status": status, "schedule": sched, "updated_at": now}
        )
        with self._get_conn() as conn:
            self._save_workflow_row(conn, updated)
            conn.commit()
        return updated

    def duplicate_workflow(self, workflow_id: str, user_id: str = "default_user") -> WorkflowDefinition:
        source = self.get_workflow(workflow_id)
        if not source:
            raise KeyError(f"Workflow '{workflow_id}' not found.")
        now = _utc_now()
        sched = source.schedule.model_copy(deep=True)
        sched.last_run_at = None
        if sched.trigger_type == "scheduled":
            sched.next_run_at = self.calculate_next_run_at(sched, now)

        cloned = WorkflowDefinition(
            workflow_id=f"wf_{uuid.uuid4().hex[:10]}",
            user_id=user_id,
            name=f"{source.name} (Copy)",
            description=source.description,
            category=source.category,
            status="DRAFT",
            is_template=False,
            schedule=sched,
            steps=[s.model_copy(deep=True) for s in source.steps],
            notification_config=source.notification_config.model_copy(deep=True),
            max_cost_budget_usd=source.max_cost_budget_usd,
            created_at=now,
            updated_at=now,
        )
        with self._get_conn() as conn:
            self._save_workflow_row(conn, cloned)
            conn.commit()
        return cloned

    def delete_workflow(self, workflow_id: str) -> bool:
        existing = self.get_workflow(workflow_id)
        if not existing:
            return False
        if existing.is_template:
            raise ValueError("Built-in system templates cannot be deleted.")
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM workflows WHERE workflow_id = ?", (workflow_id,))
            conn.commit()
            return cur.rowcount > 0

    # --- Rate Limiting & Overlap Prevention ---
    def _enforce_rate_limit(self, user_id: str) -> None:
        now_ts = time.time()
        bucket = self._rate_limit_buckets.get(user_id, [])
        bucket = [t for t in bucket if now_ts - t < 60.0]
        if len(bucket) >= settings.workflow_rate_limit_per_minute:
            raise RuntimeError(
                f"Rate limit exceeded: max {settings.workflow_rate_limit_per_minute} workflow executions per minute for user '{user_id}'."
            )
        bucket.append(now_ts)
        self._rate_limit_buckets[user_id] = bucket

    def get_active_runs_for_workflow(self, workflow_id: str) -> List[WorkflowExecutionRun]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM workflow_runs
                WHERE workflow_id = ? AND status IN ('QUEUED', 'RUNNING', 'RETRYING', 'WAITING_FOR_APPROVAL')
                """,
                (workflow_id,),
            ).fetchall()
        return [self._row_to_run(r) for r in rows]

    # --- Input/Output Templating & Condition Evaluation ---
    def _resolve_template_str(
        self,
        template: str,
        runtime_inputs: Dict[str, Any],
        step_outputs: Dict[str, Dict[str, Any]],
        prev_output: str,
    ) -> str:
        if not template or "{{" not in template:
            return template

        def _replacer(match: re.Match) -> str:
            expr = match.group(1).strip()
            if expr.startswith("workflow.input."):
                key = expr[len("workflow.input."):]
                val = runtime_inputs.get(key, f"[{key}]")
                return str(val)
            if expr == "steps.prev.output":
                return prev_output
            if expr.startswith("steps."):
                parts = expr.split(".")
                if len(parts) >= 3:
                    sid = parts[1]
                    field_key = ".".join(parts[2:])
                    sdata = step_outputs.get(sid, {})
                    if field_key in sdata:
                        return str(sdata[field_key])
                    if field_key == "output" and "output" in sdata:
                        return str(sdata["output"])
            return match.group(0)

        return re.sub(r"\{\{([^{}]+)\}\}", _replacer, template)

    def _resolve_step_inputs(
        self,
        step: WorkflowStepDefinition,
        runtime_inputs: Dict[str, Any],
        step_outputs: Dict[str, Dict[str, Any]],
        prev_output: str,
    ) -> Dict[str, Any]:
        resolved: Dict[str, Any] = {}
        for k, v in step.tool_params.items():
            if isinstance(v, str):
                resolved[k] = self._resolve_template_str(v, runtime_inputs, step_outputs, prev_output)
            else:
                resolved[k] = v
        for k, v in step.input_mapping.items():
            resolved[k] = self._resolve_template_str(v, runtime_inputs, step_outputs, prev_output)
        if step.prompt_template:
            resolved["prompt"] = self._resolve_template_str(
                step.prompt_template, runtime_inputs, step_outputs, prev_output
            )
        return resolved

    def _evaluate_condition(
        self,
        step: WorkflowStepDefinition,
        step_results_by_id: Dict[str, WorkflowStepExecutionResult],
        runtime_inputs: Dict[str, Any],
        prev_output: str,
    ) -> Tuple[bool, str]:
        expr = (step.condition_expression or "always").strip()
        if not expr or expr.lower() == "always":
            return True, "Condition 'always' passed."

        if expr.lower() == "previous_succeeded":
            for dep_id in step.depends_on:
                dep_res = step_results_by_id.get(dep_id)
                if not dep_res or dep_res.status != "SUCCEEDED":
                    return False, f"Dependency '{dep_id}' did not succeed (status={dep_res.status if dep_res else 'MISSING'})."
            return True, "All upstream dependencies succeeded."

        # Gather combined upstream text
        upstream_texts = [prev_output]
        for dep_id in step.depends_on:
            dep_res = step_results_by_id.get(dep_id)
            if dep_res and dep_res.output_summary:
                upstream_texts.append(dep_res.output_summary)
        combined_upstream = "\n".join(t for t in upstream_texts if t)

        if expr.lower().startswith("contains:"):
            needle = expr[len("contains:"):].strip()
            matched = needle.lower() in combined_upstream.lower()
            return matched, f"Checked contains '{needle}' -> {matched}"

        if expr.lower().startswith("not_contains:"):
            needle = expr[len("not_contains:"):].strip()
            matched = needle.lower() not in combined_upstream.lower()
            return matched, f"Checked not_contains '{needle}' -> {matched}"

        if expr.lower().startswith("equals:"):
            pair = expr[len("equals:"):].strip()
            if "=" in pair:
                k, expected = pair.split("=", 1)
                k = k.strip()
                expected = expected.strip()
                actual = str(runtime_inputs.get(k, "")).strip()
                matched = actual.lower() == expected.lower()
                return matched, f"Checked input '{k}' == '{expected}' (actual='{actual}') -> {matched}"

        return True, f"Default condition evaluation passed for '{expr}'."

    # --- Workflow Execution Engine ---
    async def trigger_workflow_run(
        self,
        workflow_id: str,
        req: WorkflowTriggerRunRequest,
    ) -> WorkflowExecutionRun:
        wf = self.get_workflow(workflow_id)
        if not wf:
            raise KeyError(f"Workflow '{workflow_id}' not found.")

        if wf.status == "DISABLED" and not req.is_dry_run:
            raise ValueError(f"Workflow '{wf.name}' is DISABLED and cannot be executed.")

        self._enforce_rate_limit(req.user_id)

        # Idempotency duplicate check
        if req.idempotency_key:
            with self._get_conn() as conn:
                dup_row = conn.execute(
                    "SELECT * FROM workflow_runs WHERE idempotency_key = ?",
                    (req.idempotency_key,),
                ).fetchone()
                if dup_row:
                    return self._row_to_run(dup_row)

        # Overlap prevention check
        if not wf.schedule.allow_concurrent_runs and not req.is_dry_run:
            active_runs = self.get_active_runs_for_workflow(workflow_id)
            if active_runs:
                raise RuntimeError(
                    f"Overlap prevented: Workflow '{wf.name}' already has an active run ({active_runs[0].run_id} in state {active_runs[0].status}) and allow_concurrent_runs is False."
                )

        validation = self.validate_workflow_definition(
            steps=wf.steps,
            schedule=wf.schedule,
            max_cost_budget_usd=wf.max_cost_budget_usd,
        )
        if not validation.valid:
            err_msgs = "; ".join(i.message for i in validation.issues if i.severity == "error")
            raise ValueError(f"Cannot execute invalid workflow: {err_msgs}")

        step_map = {s.step_id: s for s in wf.steps}
        ordered_steps = [step_map[sid] for sid in validation.execution_order]

        initial_step_results = [
            WorkflowStepExecutionResult(
                step_id=s.step_id,
                step_name=s.name,
                action_type=s.action_type,
                agent_id=s.agent_id,
                tool_name=s.tool_name,
                status="PENDING",
                requires_approval=self._step_requires_consequential_approval(s),
                approval_reason=s.approval_reason
                or (
                    f"Step '{s.name}' invokes a consequential action requiring explicit human approval."
                    if self._step_requires_consequential_approval(s)
                    else None
                ),
                max_retries=min(s.max_retries, settings.workflow_max_step_retries),
            )
            for s in ordered_steps
        ]

        now = _utc_now()
        run = WorkflowExecutionRun(
            run_id=f"wfrun_{uuid.uuid4().hex[:10]}",
            workflow_id=wf.workflow_id,
            workflow_name=wf.name,
            user_id=req.user_id,
            trigger_source=req.trigger_source,
            idempotency_key=req.idempotency_key,
            status="QUEUED",
            is_dry_run=req.is_dry_run,
            runtime_inputs=req.runtime_inputs,
            step_results=initial_step_results,
            completed_steps=0,
            total_steps=len(initial_step_results),
            progress_percent=0.0,
            max_cost_budget_usd=wf.max_cost_budget_usd,
            queued_at=now,
        )

        with self._get_conn() as conn:
            self._save_run_row(conn, run)
            conn.commit()

        return await self._execute_or_resume_run(
            run=run,
            wf=wf,
            provider=req.provider,
            model=req.model,
            client_api_key=req.client_api_key,
        )

    async def _execute_or_resume_run(
        self,
        run: WorkflowExecutionRun,
        wf: WorkflowDefinition,
        provider: Optional[str] = "auto",
        model: Optional[str] = "auto",
        client_api_key: Optional[str] = None,
    ) -> WorkflowExecutionRun:
        start_perf = time.perf_counter()
        if not run.started_at:
            run.started_at = _utc_now()
        run.status = "RUNNING"
        run.waiting_approval_step_id = None
        run.error_message = None
        self._persist_run(run)

        step_def_map = {s.step_id: s for s in wf.steps}
        step_results_by_id = {sr.step_id: sr for sr in run.step_results}
        step_outputs: Dict[str, Dict[str, Any]] = {}
        prev_output = ""

        # Populate already-succeeded outputs if resuming
        for sr in run.step_results:
            if sr.status == "SUCCEEDED":
                step_outputs[sr.step_id] = {
                    "output": sr.output_summary,
                    **sr.output_data,
                }
                prev_output = sr.output_summary

        skip_until_step_id: Optional[str] = None

        for sr in run.step_results:
            if run.run_id in self._cancelled_runs:
                sr.status = "CANCELLED"
                run.status = "CANCELLED"
                run.error_message = "Workflow execution cancelled by user."
                break

            if sr.status in ("SUCCEEDED", "SKIPPED"):
                continue

            if skip_until_step_id is not None:
                if sr.step_id != skip_until_step_id:
                    sr.status = "SKIPPED"
                    sr.condition_evaluated = False
                    sr.condition_detail = f"Skipped via branch jump to '{skip_until_step_id}'."
                    self._update_progress(run)
                    self._persist_run(run)
                    continue
                else:
                    skip_until_step_id = None

            step_def = step_def_map.get(sr.step_id)
            if not step_def:
                sr.status = "FAILED"
                sr.error_message = f"Step definition '{sr.step_id}' missing from workflow."
                run.status = "FAILED"
                run.error_message = sr.error_message
                break

            run.current_step_id = sr.step_id

            # Check if any upstream dependency failed
            failed_deps = [
                dep_id
                for dep_id in step_def.depends_on
                if step_results_by_id.get(dep_id) and step_results_by_id[dep_id].status == "FAILED"
            ]
            if failed_deps:
                sr.status = "SKIPPED"
                sr.condition_evaluated = False
                sr.condition_detail = f"Skipped because upstream dependency '{failed_deps[0]}' failed."
                self._update_progress(run)
                self._persist_run(run)
                continue

            # Evaluate condition expression
            cond_ok, cond_detail = self._evaluate_condition(
                step=step_def,
                step_results_by_id=step_results_by_id,
                runtime_inputs=run.runtime_inputs,
                prev_output=prev_output,
            )
            sr.condition_evaluated = cond_ok
            sr.condition_detail = cond_detail

            if not cond_ok:
                if step_def.on_condition_false == "skip":
                    sr.status = "SKIPPED"
                    sr.output_summary = f"Skipped: {cond_detail}"
                    self._update_progress(run)
                    self._persist_run(run)
                    continue
                elif step_def.on_condition_false == "jump_to_step" and step_def.jump_to_step_id:
                    sr.status = "SKIPPED"
                    sr.output_summary = f"Branching jump to '{step_def.jump_to_step_id}': {cond_detail}"
                    skip_until_step_id = step_def.jump_to_step_id
                    self._update_progress(run)
                    self._persist_run(run)
                    continue
                else:
                    sr.status = "FAILED"
                    sr.error_message = f"Condition failed with fail_workflow policy: {cond_detail}"
                    run.status = "FAILED"
                    run.error_message = sr.error_message
                    self._persist_run(run)
                    break

            # Resolve step inputs with template substitution
            resolved_inputs = self._resolve_step_inputs(
                step=step_def,
                runtime_inputs=run.runtime_inputs,
                step_outputs=step_outputs,
                prev_output=prev_output,
            )
            sr.resolved_inputs = resolved_inputs

            # Consequential approval gate check
            if sr.requires_approval and not run.is_dry_run:
                if sr.approved is None:
                    sr.status = "WAITING_FOR_APPROVAL"
                    run.status = "WAITING_FOR_APPROVAL"
                    run.waiting_approval_step_id = sr.step_id
                    run.final_summary = (
                        f"Workflow paused at step '{sr.step_name}' awaiting explicit user approval: "
                        f"{sr.approval_reason or 'Consequential action detected.'}"
                    )
                    self._persist_run(run)
                    await self._create_notification(
                        wf=wf,
                        run=run,
                        event_type="approval_required",
                        severity="warning",
                        title=f"Approval Required: {wf.name}",
                        message=f"Step '{sr.step_name}' requires your explicit approval before execution.",
                    )
                    return run
                elif sr.approved is False:
                    sr.status = "CANCELLED"
                    sr.error_message = "Rejected by user at approval gate."
                    run.status = "CANCELLED"
                    run.error_message = f"Workflow cancelled: step '{sr.step_name}' was rejected by user."
                    self._persist_run(run)
                    break

            # Execute step with bounded retries
            max_attempts = 1 + min(step_def.max_retries, settings.workflow_max_step_retries)
            attempt = 0
            step_succeeded = False

            while attempt < max_attempts:
                if run.run_id in self._cancelled_runs:
                    sr.status = "CANCELLED"
                    run.status = "CANCELLED"
                    run.error_message = "Workflow cancelled by user during step execution."
                    break

                attempt += 1
                sr.attempt_count = attempt
                sr.status = "RUNNING" if attempt == 1 else "RETRYING"
                if attempt > 1:
                    run.status = "RETRYING"
                self._persist_run(run)

                step_t0 = time.perf_counter()
                sr.started_at = sr.started_at or _utc_now()

                try:
                    if run.is_dry_run:
                        out_summary = (
                            f"[DRY-RUN VALIDATED] Step '{sr.step_name}' ({sr.action_type}) "
                            f"inputs resolved cleanly: {json.dumps(resolved_inputs)[:220]}"
                        )
                        out_data = {"dry_run": True, "resolved_inputs": resolved_inputs}
                        est_cost = 0.0
                        untrusted_flag = False
                    else:
                        out_summary, out_data, est_cost, untrusted_flag = await asyncio.wait_for(
                            self._run_single_step_action(
                                step_def=step_def,
                                resolved_inputs=resolved_inputs,
                                approval_granted=bool(sr.approved),
                                user_id=run.user_id,
                                provider=provider,
                                model=model,
                                client_api_key=client_api_key,
                            ),
                            timeout=min(step_def.timeout_seconds, settings.workflow_step_timeout_seconds),
                        )

                    # Enforce workflow cost budget
                    if run.total_estimated_cost_usd + est_cost > run.max_cost_budget_usd:
                        raise RuntimeError(
                            f"Workflow cost budget exceeded (${run.total_estimated_cost_usd + est_cost:.4f} > ${run.max_cost_budget_usd:.4f})."
                        )

                    sr.duration_ms = round((time.perf_counter() - step_t0) * 1000, 2)
                    sr.completed_at = _utc_now()
                    sr.status = "SUCCEEDED"
                    sr.output_summary = redact_sensitive_text(out_summary)
                    sr.output_data = out_data
                    sr.estimated_cost_usd = round(est_cost, 6)
                    sr.untrusted_content_isolated = untrusted_flag
                    sr.error_message = None

                    run.total_estimated_cost_usd = round(run.total_estimated_cost_usd + est_cost, 6)
                    run.status = "RUNNING"
                    step_outputs[sr.step_id] = {
                        "output": sr.output_summary,
                        step_def.output_key: sr.output_summary,
                        **out_data,
                    }
                    prev_output = sr.output_summary
                    step_succeeded = True
                    break

                except asyncio.TimeoutError:
                    sr.duration_ms = round((time.perf_counter() - step_t0) * 1000, 2)
                    sr.error_message = f"Step '{sr.step_name}' timed out after {step_def.timeout_seconds}s (attempt {attempt}/{max_attempts})."
                except Exception as exc:
                    sr.duration_ms = round((time.perf_counter() - step_t0) * 1000, 2)
                    sr.error_message = redact_sensitive_text(
                        f"Step '{sr.step_name}' failed (attempt {attempt}/{max_attempts}): {str(exc)}"
                    )

                if attempt < max_attempts and run.run_id not in self._cancelled_runs:
                    sr.status = "RETRYING"
                    run.status = "RETRYING"
                    self._persist_run(run)
                    await asyncio.sleep(min(step_def.retry_delay_seconds, 2.0))

            if not step_succeeded:
                if run.status != "CANCELLED":
                    sr.status = "FAILED"
                    sr.completed_at = _utc_now()
                    run.status = "FAILED"
                    run.error_message = sr.error_message or f"Step '{sr.step_name}' failed after {attempt} attempt(s)."
                self._update_progress(run)
                self._persist_run(run)
                break

            self._update_progress(run)
            self._persist_run(run)

        # Finalize run state — never mark SUCCEEDED unless all non-skipped steps succeeded
        run.current_step_id = None
        run.completed_at = _utc_now()
        run.duration_ms = round(run.duration_ms + (time.perf_counter() - start_perf) * 1000, 2)

        if run.run_id in self._cancelled_runs or run.status == "CANCELLED":
            run.status = "CANCELLED"
            self._cancelled_runs.discard(run.run_id)
            run.final_summary = run.error_message or "Workflow run was cancelled."
            await self._create_notification(
                wf=wf,
                run=run,
                event_type="run_cancelled",
                severity="info",
                title=f"Workflow Cancelled: {wf.name}",
                message=run.final_summary,
            )
        elif run.status == "FAILED" or any(s.status == "FAILED" for s in run.step_results):
            run.status = "FAILED"
            run.final_summary = run.error_message or "Workflow execution failed."
            await self._create_notification(
                wf=wf,
                run=run,
                event_type="run_failed",
                severity="error",
                title=f"Workflow Failed: {wf.name}",
                message=run.final_summary,
            )
        elif all(s.status in ("SUCCEEDED", "SKIPPED") for s in run.step_results):
            run.status = "SUCCEEDED"
            summaries = [
                f"- **{s.step_name}** ({s.status}): {s.output_summary[:260]}"
                for s in run.step_results
            ]
            run.final_summary = (
                f"Workflow '{wf.name}' completed {run.completed_steps}/{run.total_steps} step(s) successfully.\n"
                + "\n".join(summaries)
            )
            await self._create_notification(
                wf=wf,
                run=run,
                event_type="run_succeeded",
                severity="success",
                title=f"Workflow Succeeded: {wf.name}",
                message=f"Completed {run.completed_steps}/{run.total_steps} steps in {run.duration_ms:.0f}ms.",
            )

        self._update_progress(run)
        self._persist_run(run)
        self._update_workflow_counters(wf.workflow_id, run.status)
        return run

    async def _run_single_step_action(
        self,
        step_def: WorkflowStepDefinition,
        resolved_inputs: Dict[str, Any],
        approval_granted: bool,
        user_id: str,
        provider: Optional[str],
        model: Optional[str],
        client_api_key: Optional[str],
    ) -> Tuple[str, Dict[str, Any], float, bool]:
        if step_def.action_type == "tool":
            tool_name = step_def.tool_name or ""
            tool_params = {k: v for k, v in resolved_inputs.items() if k != "prompt"}
            # Simulate intentional failure if test param requests it
            if str(tool_params.get("__simulate_failure", "")).lower() == "true":
                raise RuntimeError(f"Simulated integration failure in tool '{tool_name}'.")
            res = await tool_registry.execute(
                name=tool_name,
                params=tool_params,
                approval_granted=approval_granted,
            )
            summary = res.get("quarantined_summary") or res.get("summary", "")
            untrusted = bool(res.get("untrusted_content_quarantined", False))
            return summary, res.get("data", {}), 0.001, untrusted

        if step_def.action_type == "agent":
            agent_id = step_def.agent_id or "productivity_agent"
            prompt_text = str(resolved_inputs.get("prompt") or step_def.prompt_template).strip()
            if "__simulate_failure" in prompt_text:
                raise RuntimeError(f"Simulated agent failure in '{agent_id}'.")

            # Isolate any untrusted upstream output passed into the prompt
            orch_run = await multi_agent_orchestrator.execute_run(
                MultiAgentRunRequest(
                    goal=prompt_text,
                    user_id=user_id,
                    selection_mode="manual",
                    manual_agents=[agent_id],
                    allow_parallel=False,
                    provider=provider,
                    model=model,
                    client_api_key=client_api_key,
                )
            )
            if orch_run.status == "FAILED":
                raise RuntimeError(f"Agent '{agent_id}' failed to complete step '{step_def.name}'.")
            sub = orch_run.subtasks[0] if orch_run.subtasks else None
            summary = sub.output_summary if sub else orch_run.combined_response
            quarantined = f"<untrusted_workflow_step_output step=\"{step_def.step_id}\">\n{summary}\n</untrusted_workflow_step_output>"
            return (
                summary,
                {
                    "agent_id": agent_id,
                    "orchestration_run_id": orch_run.run_id,
                    "quarantined_output": quarantined,
                    "facts": orch_run.consolidated_facts,
                },
                orch_run.total_estimated_cost_usd or 0.005,
                True,
            )

        if step_def.action_type == "condition_gate":
            summary = f"Condition gate '{step_def.name}' evaluated true."
            return summary, {"gate_passed": True}, 0.0, False

        # transform action
        transformed = str(resolved_inputs.get("prompt") or json.dumps(resolved_inputs))
        return transformed, {"transformed": transformed}, 0.0, False

    def _update_progress(self, run: WorkflowExecutionRun) -> None:
        done = sum(1 for s in run.step_results if s.status in ("SUCCEEDED", "SKIPPED"))
        run.completed_steps = done
        run.total_steps = len(run.step_results)
        run.progress_percent = round((done / run.total_steps) * 100.0, 1) if run.total_steps > 0 else 0.0

    def _persist_run(self, run: WorkflowExecutionRun) -> None:
        with self._get_conn() as conn:
            self._save_run_row(conn, run)
            conn.commit()

    def _update_workflow_counters(self, workflow_id: str, run_status: WorkflowRunStatus) -> None:
        wf = self.get_workflow(workflow_id)
        if not wf:
            return
        wf.total_runs += 1
        if run_status == "SUCCEEDED":
            wf.succeeded_runs += 1
        elif run_status == "FAILED":
            wf.failed_runs += 1
        wf.last_run_status = run_status
        wf.updated_at = _utc_now()
        with self._get_conn() as conn:
            self._save_workflow_row(conn, wf)
            conn.commit()

    # --- Approval, Retry & Cancellation Controls ---
    async def approve_run_step(
        self,
        run_id: str,
        req: WorkflowApproveStepRequest,
    ) -> WorkflowExecutionRun:
        run = self.get_run(run_id)
        if not run:
            raise KeyError(f"Workflow run '{run_id}' not found.")
        if run.status != "WAITING_FOR_APPROVAL":
            raise ValueError(f"Run '{run_id}' is in state '{run.status}', not 'WAITING_FOR_APPROVAL'.")

        wf = self.get_workflow(run.workflow_id)
        if not wf:
            raise KeyError(f"Workflow '{run.workflow_id}' not found.")

        target_step = next((s for s in run.step_results if s.step_id == req.step_id), None)
        if not target_step:
            raise KeyError(f"Step '{req.step_id}' not found in run '{run_id}'.")

        target_step.approved = req.approved
        if not req.approved:
            target_step.status = "CANCELLED"
            target_step.error_message = f"User rejected approval gate: {req.user_note or 'Rejected by operator.'}"
            run.status = "CANCELLED"
            run.waiting_approval_step_id = None
            run.completed_at = _utc_now()
            run.error_message = target_step.error_message
            run.final_summary = target_step.error_message
            self._persist_run(run)
            self._update_workflow_counters(wf.workflow_id, "CANCELLED")
            await self._create_notification(
                wf=wf,
                run=run,
                event_type="run_cancelled",
                severity="warning",
                title=f"Approval Rejected: {wf.name}",
                message=target_step.error_message,
            )
            return run

        return await self._execute_or_resume_run(
            run=run,
            wf=wf,
            provider=req.provider,
            model=req.model,
            client_api_key=req.client_api_key,
        )

    async def retry_run(
        self,
        run_id: str,
        req: WorkflowRetryRunRequest,
    ) -> WorkflowExecutionRun:
        run = self.get_run(run_id)
        if not run:
            raise KeyError(f"Workflow run '{run_id}' not found.")
        if run.status not in ("FAILED", "CANCELLED"):
            raise ValueError(f"Only FAILED or CANCELLED runs can be retried (current status: {run.status}).")

        wf = self.get_workflow(run.workflow_id)
        if not wf:
            raise KeyError(f"Workflow '{run.workflow_id}' not found.")

        for sr in run.step_results:
            if not req.from_failed_step_only or sr.status in ("FAILED", "CANCELLED", "SKIPPED"):
                sr.status = "PENDING"
                sr.error_message = None
                sr.attempt_count = 0

        run.trigger_source = "retry"
        run.error_message = None
        run.completed_at = None
        self._update_progress(run)
        self._persist_run(run)

        return await self._execute_or_resume_run(
            run=run,
            wf=wf,
            provider=req.provider,
            model=req.model,
            client_api_key=req.client_api_key,
        )

    async def cancel_run(self, run_id: str) -> WorkflowExecutionRun:
        run = self.get_run(run_id)
        if not run:
            raise KeyError(f"Workflow run '{run_id}' not found.")
        if run.status in ("SUCCEEDED", "FAILED", "CANCELLED"):
            return run

        self._cancelled_runs.add(run_id)
        for sr in run.step_results:
            if sr.status in ("PENDING", "RUNNING", "RETRYING", "WAITING_FOR_APPROVAL"):
                sr.status = "CANCELLED"
                sr.completed_at = _utc_now()

        run.status = "CANCELLED"
        run.waiting_approval_step_id = None
        run.current_step_id = None
        run.completed_at = _utc_now()
        run.error_message = "Cancelled by user request."
        run.final_summary = "Workflow execution was cancelled by user."
        self._persist_run(run)

        wf = self.get_workflow(run.workflow_id)
        if wf:
            self._update_workflow_counters(wf.workflow_id, "CANCELLED")
            await self._create_notification(
                wf=wf,
                run=run,
                event_type="run_cancelled",
                severity="info",
                title=f"Workflow Run Cancelled: {wf.name}",
                message=f"Run {run.run_id} was cancelled by user.",
            )
        return run

    def get_run(self, run_id: str) -> Optional[WorkflowExecutionRun]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,)).fetchone()
        return self._row_to_run(row) if row else None

    def list_runs(
        self,
        user_id: str = "default_user",
        workflow_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
    ) -> List[WorkflowExecutionRun]:
        query = "SELECT * FROM workflow_runs WHERE (user_id = ? OR user_id = 'system')"
        params: List[Any] = [user_id]
        if workflow_id:
            query += " AND workflow_id = ?"
            params.append(workflow_id)
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        query += " ORDER BY queued_at DESC LIMIT ?"
        params.append(limit)

        with self._get_conn() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_run(r) for r in rows]

    # --- Persistent Scheduler & Worker Restart Recovery ---
    async def tick_scheduler(self, now_utc: Optional[datetime] = None) -> List[WorkflowExecutionRun]:
        """
        Evaluates all ACTIVE scheduled workflows whose next_run_at <= now_utc,
        dispatches them with deterministic idempotency keys to prevent duplicate runs,
        and updates next_run_at (or pauses one-time schedules).
        """
        current_utc = now_utc or _utc_now()
        if current_utc.tzinfo is None:
            current_utc = current_utc.replace(tzinfo=timezone.utc)

        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM workflows WHERE status = 'ACTIVE' AND is_template = 0"
            ).fetchall()

        triggered_runs: List[WorkflowExecutionRun] = []
        for row in rows:
            wf = self._row_to_workflow(row)
            if wf.schedule.trigger_type != "scheduled":
                continue

            next_run = wf.schedule.next_run_at
            if next_run is None:
                next_run = self.calculate_next_run_at(wf.schedule, current_utc)
                wf.schedule.next_run_at = next_run
                with self._get_conn() as conn:
                    self._save_workflow_row(conn, wf)
                    conn.commit()
                continue

            if next_run <= current_utc:
                slot_key = f"sched:{wf.workflow_id}:{next_run.isoformat()}"
                # Update schedule timestamps before running to prevent re-triggering
                wf.schedule.last_run_at = current_utc
                if wf.schedule.recurrence == "once":
                    wf.schedule.next_run_at = None
                    wf.status = "PAUSED"
                else:
                    wf.schedule.next_run_at = self.calculate_next_run_at(wf.schedule, current_utc)
                wf.updated_at = current_utc
                with self._get_conn() as conn:
                    self._save_workflow_row(conn, wf)
                    conn.commit()

                try:
                    run = await self.trigger_workflow_run(
                        workflow_id=wf.workflow_id,
                        req=WorkflowTriggerRunRequest(
                            user_id=wf.user_id,
                            trigger_source="scheduled",
                            idempotency_key=slot_key,
                        ),
                    )
                    triggered_runs.append(run)
                except Exception as exc:
                    await self._create_notification(
                        wf=wf,
                        run=None,
                        event_type="run_failed",
                        severity="error",
                        title=f"Scheduled Trigger Skipped: {wf.name}",
                        message=str(exc),
                    )

        return triggered_runs

    async def recover_interrupted_runs_on_startup(self) -> List[WorkflowExecutionRun]:
        """
        Detects any runs left in RUNNING, QUEUED, or RETRYING state due to an unexpected
        worker restart, safely marks them FAILED with a clear recovery reason so they can
        be retried without faking completion, and posts a worker_recovery notification.
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM workflow_runs WHERE status IN ('RUNNING', 'QUEUED', 'RETRYING')"
            ).fetchall()

        recovered: List[WorkflowExecutionRun] = []
        for row in rows:
            run = self._row_to_run(row)
            for sr in run.step_results:
                if sr.status in ("RUNNING", "RETRYING"):
                    sr.status = "FAILED"
                    sr.error_message = "Interrupted by worker restart; ready for safe retry."
                    sr.completed_at = _utc_now()
            run.status = "FAILED"
            run.completed_at = _utc_now()
            run.error_message = "Run interrupted by backend worker restart. Use Retry to resume safely."
            run.final_summary = run.error_message
            self._persist_run(run)
            recovered.append(run)

            wf = self.get_workflow(run.workflow_id)
            if wf:
                await self._create_notification(
                    wf=wf,
                    run=run,
                    event_type="worker_recovery",
                    severity="warning",
                    title=f"Worker Restart Recovery: {wf.name}",
                    message=f"Run {run.run_id} was interrupted by a worker restart and safely marked FAILED for retry.",
                )
        return recovered

    # --- Notification Center & Honest External Delivery ---
    async def _create_notification(
        self,
        wf: WorkflowDefinition,
        run: Optional[WorkflowExecutionRun],
        event_type: str,
        severity: str,
        title: str,
        message: str,
    ) -> Optional[WorkflowNotificationItem]:
        cfg = wf.notification_config
        if event_type == "run_succeeded" and not cfg.notify_on_complete:
            return None
        if event_type == "run_failed" and not cfg.notify_on_failure:
            return None
        if event_type == "approval_required" and not cfg.notify_on_approval_required:
            return None

        channels_attempted: List[str] = []
        external_status = "in_app_only"
        external_confirmed = False

        # Check webhook opt-in
        if cfg.webhook_opt_in:
            channels_attempted.append("webhook")
            if not settings.notification_webhook_url.strip():
                external_status = "webhook_not_configured"
                external_confirmed = False
            else:
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.post(
                            settings.notification_webhook_url.strip(),
                            json={
                                "workflow_id": wf.workflow_id,
                                "workflow_name": wf.name,
                                "run_id": run.run_id if run else None,
                                "event_type": event_type,
                                "title": title,
                                "message": redact_sensitive_text(message),
                            },
                        )
                        if 200 <= resp.status_code < 300:
                            external_status = "webhook_delivered_confirmed"
                            external_confirmed = True
                        else:
                            external_status = f"webhook_failed_http_{resp.status_code}"
                            external_confirmed = False
                except Exception as exc:
                    external_status = f"webhook_failed: {str(exc)[:120]}"
                    external_confirmed = False

        # Check email opt-in
        if cfg.email_opt_in:
            channels_attempted.append("email")
            if not settings.smtp_host.strip():
                if external_status == "in_app_only":
                    external_status = "smtp_not_configured"
                else:
                    external_status += "; smtp_not_configured"

        notif = WorkflowNotificationItem(
            notification_id=f"wfnotif_{uuid.uuid4().hex[:10]}",
            user_id=wf.user_id if wf.user_id != "system" else (run.user_id if run else "default_user"),
            workflow_id=wf.workflow_id,
            workflow_name=wf.name,
            run_id=run.run_id if run else None,
            event_type=event_type,  # type: ignore[arg-type]
            severity=severity,  # type: ignore[arg-type]
            title=title,
            message=redact_sensitive_text(message),
            read=False,
            external_channels_attempted=channels_attempted,
            external_delivery_status=external_status,
            external_delivery_confirmed=external_confirmed,
            created_at=_utc_now(),
        )

        if cfg.in_app_enabled:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO workflow_notifications (
                        notification_id, user_id, workflow_id, workflow_name, run_id,
                        event_type, severity, title, message, read,
                        external_channels_json, external_delivery_status,
                        external_delivery_confirmed, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        notif.notification_id,
                        notif.user_id,
                        notif.workflow_id,
                        notif.workflow_name,
                        notif.run_id,
                        notif.event_type,
                        notif.severity,
                        notif.title,
                        notif.message,
                        0,
                        json.dumps(notif.external_channels_attempted),
                        notif.external_delivery_status,
                        1 if notif.external_delivery_confirmed else 0,
                        notif.created_at.isoformat(),
                    ),
                )
                conn.commit()
        return notif

    def list_notifications(
        self,
        user_id: str = "default_user",
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[WorkflowNotificationItem]:
        query = "SELECT * FROM workflow_notifications WHERE (user_id = ? OR user_id = 'default_user')"
        params: List[Any] = [user_id]
        if unread_only:
            query += " AND read = 0"
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._get_conn() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            WorkflowNotificationItem(
                notification_id=r["notification_id"],
                user_id=r["user_id"],
                workflow_id=r["workflow_id"],
                workflow_name=r["workflow_name"],
                run_id=r["run_id"],
                event_type=r["event_type"],
                severity=r["severity"],
                title=r["title"],
                message=r["message"],
                read=bool(r["read"]),
                external_channels_attempted=json.loads(r["external_channels_json"]),
                external_delivery_status=r["external_delivery_status"],
                external_delivery_confirmed=bool(r["external_delivery_confirmed"]),
                created_at=_parse_iso_dt(r["created_at"]) or _utc_now(),
            )
            for r in rows
        ]

    def mark_notification_read(self, notification_id: str, read: bool = True) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE workflow_notifications SET read = ? WHERE notification_id = ?",
                (1 if read else 0, notification_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def mark_all_notifications_read(self, user_id: str = "default_user") -> int:
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE workflow_notifications SET read = 1 WHERE (user_id = ? OR user_id = 'default_user') AND read = 0",
                (user_id,),
            )
            conn.commit()
            return cur.rowcount


workflow_engine = WorkflowAutomationEngine()
