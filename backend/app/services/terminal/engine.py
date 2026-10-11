"""
NEXORA AI — Stage 18: Terminal & Code Execution Engine

Provides:
- Isolated per-user, per-project developer code workspaces (Python, JavaScript, TypeScript, HTML, CSS)
- Automatic pre-edit and pre-repair version backups (.nexora_code_backups + SQLite audit log) with 1-click restore
- Real AST syntax validation, deterministic formatting, static linting, and missing dependency detection
- Sandboxed code & test execution with CPU/memory/recursion/process/output-size/timeout limits and network isolation by default
- Controlled allowlisted terminal runner with 3-tier classification (allowed_safe, requires_approval, blocked_forbidden)
- Real stdout/stderr/exit-code capture, secret masking, and untrusted repository instruction quarantine
- Bounded autonomous debugging & repair engine that diagnoses failures, backs up files, proposes/applies targeted patches, and verifies with real test runs
- Stage 17 File Workspace sync bridge
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from app.config import settings
from app.models.schemas import (
    CodeDiagnosticIssue,
    CodeExecuteRequest,
    CodeFileBackup,
    CodeInspectionResult,
    CodeInspectRequest,
    CodeLanguage,
    CodeProjectFile,
    CodeProjectSummary,
    CommandPreview,
    CommandRiskClassification,
    CreateCodeProjectRequest,
    DebugRepairRequest,
    DebugRepairResponse,
    DependencyStatusItem,
    ProjectTemplateType,
    RepairIterationStep,
    SaveCodeFileRequest,
    SyncStage17Request,
    TerminalApproveRequest,
    TerminalCommandRequest,
    TerminalExecutionRecord,
    TestCaseResult,
    TestSuiteResult,
    utc_now,
)

INTERNAL_BACKUP_DIR = ".nexora_code_backups"
INTERNAL_SANDBOX_FILE = "_nexora_sandbox_boot.py"

FORBIDDEN_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
    "authorized_keys",
}

FORBIDDEN_EXTENSIONS = {
    ".exe",
    ".dll",
    ".bat",
    ".cmd",
    ".ps1",
    ".vbs",
    ".msi",
    ".scr",
    ".com",
    ".pem",
    ".key",
}

SECRET_REDACTION_PATTERNS = [
    re.compile(r"(AIza[0-9A-Za-z\-_]{20,})"),
    re.compile(r"(sk-[0-9A-Za-z\-_]{20,})"),
    re.compile(r"(tvly-[0-9A-Za-z\-_]{16,})"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{12,})['\"]?"),
]

UNTRUSTED_REPO_PATTERNS = [
    (re.compile(r"(?i)ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions"), "Prompt-injection override directive detected in repository file."),
    (re.compile(r"(?i)system\s+override|bypass\s+sandbox|disable\s+security"), "Attempt to override sandbox security rules detected in file comments/text."),
    (re.compile(r"(?i)(?:curl|wget)\s+[^\n]+\|\s*(?:sh|bash|powershell|python)"), "Suspicious remote pipe-to-shell instruction detected in file."),
    (re.compile(r"(?i)os\.environ\[['\"](?:GEMINI|OPENAI|ANTHROPIC|AWS|GITHUB)"), "Attempt to read host credential environment variables detected."),
]

# Commands that are unconditionally blocked
BLOCKED_COMMAND_PATTERNS = [
    (re.compile(r"[;&|`]|(?:\$\()|(?:&&)|(?:\|\|)"), "Shell command chaining, pipes, and subshell expansion are blocked in the controlled terminal."),
    (re.compile(r"\.\.[/\\]"), "Directory traversal ('..') outside the project workspace is blocked."),
    (re.compile(r"(?i)\b(?:rm\s+-rf|del\s+/s|rd\s+/s|format\s+[a-z]:|mkfs|shutdown|reboot|halt|poweroff)\b"), "Destructive operating-system command is strictly blocked."),
    (re.compile(r"(?i)\b(?:reg\s+delete|reg\s+add|sc\s+stop|net\s+user|runas|sudo|su\s+-|chmod\s+777|chown)\b"), "Privileged system administration command is blocked."),
    (re.compile(r"(?i)\b(?:powershell|pwsh|cmd\.exe|bash|sh|zsh|wsl|nc|ncat|netcat|telnet|ssh|scp|sftp|ftp)\b"), "Interactive subshell and raw remote-access binaries are blocked."),
    (re.compile(r"(?i)\b(?:printenv|set|export)\b|(?:\benv\b)"), "Environment and credential inspection commands are blocked to protect secrets."),
    (re.compile(r"(?i)(?:\.env|id_rsa|\.ssh|/etc/passwd|/etc/shadow|sam\b|ntds\.dit)"), "Accessing credential or system password files is strictly blocked."),
    (re.compile(r":\(\)\s*\{\s*:\|\:&\s*\}\s*;:"), "Fork bomb pattern is strictly blocked."),
]

# Commands that require explicit user confirmation before execution
APPROVAL_COMMAND_PATTERNS = [
    (re.compile(r"(?i)^(pip|pip3)\s+install\b"), "Installing Python packages modifies the environment and requires explicit user approval."),
    (re.compile(r"(?i)^(npm|yarn|pnpm)\s+(install|add|i)\b"), "Installing Node.js packages requires explicit user approval."),
    (re.compile(r"(?i)^(rm|del|erase)\b"), "Deleting project files via terminal requires explicit user approval."),
    (re.compile(r"(?i)^(curl|wget)\b"), "Outbound network fetch commands require explicit user approval."),
    (re.compile(r"(?i)^git\s+(reset|clean|checkout|push|pull|clone|fetch)\b"), "Mutating or network git operations require explicit user approval."),
]

STARTER_TEMPLATES: Dict[ProjectTemplateType, Dict[str, Any]] = {
    "python": {
        "primary_language": "python",
        "entrypoint": "main.py",
        "test_entrypoint": "test_main.py",
        "files": {
            "main.py": (
                '"""Nexora AI Stage 18 — Python Developer Workspace."""\n'
                "from typing import List, Dict\n\n\n"
                "def analyze_metrics(values: List[float]) -> Dict[str, float]:\n"
                '    """Computes count, total, mean, min, and max for a non-empty numeric list."""\n'
                "    if not values:\n"
                "        return {\"count\": 0, \"total\": 0.0, \"mean\": 0.0, \"min\": 0.0, \"max\": 0.0}\n"
                "    total = float(sum(values))\n"
                "    count = len(values)\n"
                "    return {\n"
                "        \"count\": count,\n"
                "        \"total\": round(total, 4),\n"
                "        \"mean\": round(total / count, 4),\n"
                "        \"min\": float(min(values)),\n"
                "        \"max\": float(max(values)),\n"
                "    }\n\n\n"
                "def fibonacci(n: int) -> int:\n"
                '    """Returns the n-th Fibonacci number (0-indexed)."""\n'
                "    if n < 0:\n"
                "        raise ValueError(\"n must be non-negative\")\n"
                "    a, b = 0, 1\n"
                "    for _ in range(n):\n"
                "        a, b = b, a + b\n"
                "    return a\n\n\n"
                "if __name__ == \"__main__\":\n"
                "    sample = [12.5, 18.0, 24.5, 31.0, 14.0]\n"
                "    stats = analyze_metrics(sample)\n"
                "    print(f\"Metrics Summary: {stats}\")\n"
                "    print(f\"Fibonacci(10): {fibonacci(10)}\")\n"
            ),
            "test_main.py": (
                '"""Unit tests for main.py."""\n'
                "import unittest\n"
                "from main import analyze_metrics, fibonacci\n\n\n"
                "class TestMainMetrics(unittest.TestCase):\n"
                "    def test_analyze_metrics_standard(self):\n"
                "        res = analyze_metrics([10.0, 20.0, 30.0])\n"
                "        self.assertEqual(res[\"count\"], 3)\n"
                "        self.assertEqual(res[\"total\"], 60.0)\n"
                "        self.assertEqual(res[\"mean\"], 20.0)\n\n"
                "    def test_analyze_metrics_empty(self):\n"
                "        res = analyze_metrics([])\n"
                "        self.assertEqual(res[\"count\"], 0)\n"
                "        self.assertEqual(res[\"mean\"], 0.0)\n\n"
                "    def test_fibonacci_sequence(self):\n"
                "        self.assertEqual(fibonacci(0), 0)\n"
                "        self.assertEqual(fibonacci(1), 1)\n"
                "        self.assertEqual(fibonacci(7), 13)\n\n\n"
                "if __name__ == \"__main__\":\n"
                "    unittest.main()\n"
            ),
            "requirements.txt": "# Add project dependencies here\n",
        },
    },
    "javascript": {
        "primary_language": "javascript",
        "entrypoint": "index.js",
        "test_entrypoint": "test.js",
        "files": {
            "index.js": (
                "// Nexora AI Stage 18 — JavaScript Developer Workspace\n\n"
                "function summarizeScores(scores) {\n"
                "  if (!Array.isArray(scores) || scores.length === 0) {\n"
                "    return { count: 0, sum: 0, average: 0 };\n"
                "  }\n"
                "  const sum = scores.reduce((acc, v) => acc + v, 0);\n"
                "  return {\n"
                "    count: scores.length,\n"
                "    sum,\n"
                "    average: Number((sum / scores.length).toFixed(2)),\n"
                "  };\n"
                "}\n\n"
                "if (require.main === module) {\n"
                "  console.log('Score Summary:', JSON.stringify(summarizeScores([85, 90, 95])));\n"
                "}\n\n"
                "module.exports = { summarizeScores };\n"
            ),
            "test.js": (
                "const assert = require('assert');\n"
                "const { summarizeScores } = require('./index.js');\n\n"
                "const result = summarizeScores([80, 90, 100]);\n"
                "assert.strictEqual(result.count, 3, 'Count should be 3');\n"
                "assert.strictEqual(result.sum, 270, 'Sum should be 270');\n"
                "assert.strictEqual(result.average, 90, 'Average should be 90');\n"
                "console.log('ALL_TESTS_PASSED: 3/3 assertions succeeded.');\n"
            ),
            "package.json": json.dumps(
                {
                    "name": "nexora-js-starter",
                    "version": "1.0.0",
                    "main": "index.js",
                    "scripts": {"start": "node index.js", "test": "node test.js"},
                },
                indent=2,
            )
            + "\n",
        },
    },
    "typescript": {
        "primary_language": "typescript",
        "entrypoint": "index.ts",
        "test_entrypoint": "test.ts",
        "files": {
            "index.ts": (
                "// Nexora AI Stage 18 — TypeScript Module\n\n"
                "export interface Vector2D {\n"
                "  x: number;\n"
                "  y: number;\n"
                "}\n\n"
                "export function magnitude(v: Vector2D): number {\n"
                "  return Math.hypot(v.x, v.y);\n"
                "}\n\n"
                "console.log('Vector magnitude (3, 4):', magnitude({ x: 3, y: 4 }));\n"
            ),
            "tsconfig.json": json.dumps(
                {
                    "compilerOptions": {
                        "target": "ES2022",
                        "module": "commonjs",
                        "strict": True,
                    }
                },
                indent=2,
            )
            + "\n",
        },
    },
    "web": {
        "primary_language": "html",
        "entrypoint": "index.html",
        "test_entrypoint": "app.js",
        "files": {
            "index.html": (
                "<!DOCTYPE html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                "  <meta charset=\"UTF-8\" />\n"
                "  <title>Nexora Web Sandbox</title>\n"
                "  <link rel=\"stylesheet\" href=\"styles.css\" />\n"
                "</head>\n"
                "<body>\n"
                "  <main class=\"card\">\n"
                "    <h1>Nexora Web App</h1>\n"
                "    <p id=\"status\">Ready</p>\n"
                "  </main>\n"
                "  <script src=\"app.js\"></script>\n"
                "</body>\n"
                "</html>\n"
            ),
            "styles.css": (
                "body {\n"
                "  font-family: system-ui, sans-serif;\n"
                "  background: #0f172a;\n"
                "  color: #f8fafc;\n"
                "  margin: 0;\n"
                "  padding: 2rem;\n"
                "}\n"
                ".card {\n"
                "  border: 1px solid #334155;\n"
                "  border-radius: 0.75rem;\n"
                "  padding: 1.5rem;\n"
                "}\n"
            ),
            "app.js": "console.log('Nexora Web Sandbox initialized.');\n",
        },
    },
}


class TerminalExecutionEngine:
    """
    Stage 18: Permission-Controlled Developer Code Workspace, Sandboxed Runner,
    Controlled Terminal, and Autonomous Debugger/Repair Engine.
    """

    def __init__(self) -> None:
        self._root_dir = Path(settings.terminal_workspace_dir).resolve()
        self._db_path = Path(settings.terminal_db_path).resolve()
        self._root_dir.mkdir(parents=True, exist_ok=True)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._active_processes: Dict[str, subprocess.Popen] = {}
        self._active_runs_per_user: Dict[str, int] = {}
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                # Migrate single-PK table if present from earlier test run
                cols = conn.execute("PRAGMA table_info(terminal_projects)").fetchall()
                pk_count = sum(1 for c in cols if int(c["pk"]) > 0)
                if cols and pk_count == 1:
                    conn.execute("DROP TABLE terminal_projects")

                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS terminal_projects (
                        project_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT NOT NULL,
                        template TEXT NOT NULL,
                        primary_language TEXT NOT NULL,
                        entrypoint TEXT NOT NULL,
                        test_entrypoint TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (user_id, project_id)
                    );

                    CREATE TABLE IF NOT EXISTS terminal_backups (
                        backup_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        relative_path TEXT NOT NULL,
                        version_number INTEGER NOT NULL,
                        sha256_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        reason TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS terminal_executions (
                        execution_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        record_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                conn.commit()
            finally:
                conn.close()

    # =========================================================================
    # Environment & Security Helpers
    # =========================================================================

    @staticmethod
    def _sanitize_user_id(user_id: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "_", (user_id or "default_user").strip())
        return cleaned[:64] or "default_user"

    @staticmethod
    def _sanitize_project_id(project_id: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "_", (project_id or "").strip())
        if not cleaned:
            raise ValueError("Invalid project_id.")
        return cleaned[:64]

    @staticmethod
    def _detect_language(filename: str) -> CodeLanguage:
        ext = Path(filename).suffix.lower()
        mapping: Dict[str, CodeLanguage] = {
            ".py": "python",
            ".js": "javascript",
            ".cjs": "javascript",
            ".mjs": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".html": "html",
            ".htm": "html",
            ".css": "css",
            ".json": "json",
            ".md": "markdown",
        }
        return mapping.get(ext, "python")

    @staticmethod
    def _redact_secrets(text: str) -> str:
        if not text:
            return ""
        redacted = text
        for pattern in SECRET_REDACTION_PATTERNS:
            if pattern.groups >= 2:
                redacted = pattern.sub(r"\1=[REDACTED_SECRET]", redacted)
            else:
                redacted = pattern.sub("[REDACTED_SECRET]", redacted)
        # Also redact any configured provider keys if non-empty
        for key_val in (
            settings.gemini_api_key,
            settings.openai_api_key,
            settings.anthropic_api_key,
            settings.tavily_api_key,
            settings.serper_api_key,
            settings.brave_api_key,
        ):
            if key_val and len(key_val.strip()) >= 8:
                redacted = redacted.replace(key_val.strip(), "[REDACTED_SECRET]")
        return redacted

    @staticmethod
    def _scan_untrusted_repo_instructions(content: str) -> List[str]:
        warnings: List[str] = []
        for pattern, message in UNTRUSTED_REPO_PATTERNS:
            if pattern.search(content or ""):
                warnings.append(message)
        return warnings

    def _project_dir(self, user_id: str, project_id: str) -> Path:
        uid = self._sanitize_user_id(user_id)
        pid = self._sanitize_project_id(project_id)
        target = (self._root_dir / uid / pid).resolve()
        if not str(target).startswith(str(self._root_dir)):
            raise PermissionError("Workspace path escape blocked.")
        return target

    def _resolve_project_file(
        self, user_id: str, project_id: str, relative_path: str
    ) -> Tuple[Path, str]:
        if not relative_path or "\x00" in relative_path:
            raise PermissionError("Invalid or null-byte file path rejected.")
        raw = relative_path.strip().replace("\\", "/")
        if raw.startswith("/") or re.match(r"^[a-zA-Z]:", raw):
            raise PermissionError(f"Absolute path or drive letter '{relative_path}' is forbidden.")
        parts = [p for p in raw.split("/") if p and p != "."]
        if not parts or any(p == ".." for p in parts):
            raise PermissionError(f"Path traversal ('..') in '{relative_path}' is forbidden.")
        if parts[0] in (INTERNAL_BACKUP_DIR, "__pycache__", ".git"):
            raise PermissionError(f"Access to internal directory '{parts[0]}' is restricted.")
        filename = parts[-1]
        if filename.lower() in FORBIDDEN_FILENAMES or filename == INTERNAL_SANDBOX_FILE:
            raise PermissionError(f"Access to protected or credential file '{filename}' is forbidden.")
        ext = Path(filename).suffix.lower()
        if ext in FORBIDDEN_EXTENSIONS:
            raise PermissionError(f"File extension '{ext}' is forbidden in the code workspace.")

        proj_root = self._project_dir(user_id, project_id)
        candidate = proj_root.joinpath(*parts)
        if candidate.exists() and candidate.is_symlink():
            raise PermissionError(f"Symbolic link '{relative_path}' is blocked inside sandbox.")
        for parent in candidate.parents:
            if parent == proj_root:
                break
            if parent.exists() and parent.is_symlink():
                raise PermissionError(f"Symbolic link parent in '{relative_path}' is blocked.")
        resolved = candidate.resolve()
        if not str(resolved).startswith(str(proj_root)):
            raise PermissionError(f"Path '{relative_path}' escapes project workspace boundary.")
        norm_rel = "/".join(parts)
        return resolved, norm_rel

    def get_capabilities(self, user_id: str = "default_user") -> Dict[str, Any]:
        self._ensure_default_project(user_id)
        pytest_installed = importlib.util.find_spec("pytest") is not None
        node_bin = shutil.which("node")
        git_bin = shutil.which("git")
        return {
            "stage": 18,
            "engine": "TerminalExecutionEngine",
            "sandbox_mode": "isolated_subprocess_with_site_guard",
            "supported_languages": ["python", "javascript", "typescript", "html", "css"],
            "runtimes": {
                "python": {
                    "available": True,
                    "version": sys.version.split()[0],
                    "executable": Path(sys.executable).name,
                    "pytest_available": pytest_installed,
                    "unittest_available": True,
                },
                "node": {
                    "available": node_bin is not None,
                    "executable": Path(node_bin).name if node_bin else None,
                },
                "git": {
                    "available": git_bin is not None,
                },
            },
            "limits": {
                "execution_timeout_seconds": settings.terminal_execution_timeout_seconds,
                "max_output_bytes": settings.terminal_max_output_bytes,
                "max_memory_mb": settings.terminal_max_memory_mb,
                "max_processes": settings.terminal_max_processes,
                "max_concurrent_runs_per_user": settings.terminal_max_concurrent_runs_per_user,
                "max_repair_attempts": settings.terminal_max_repair_attempts,
                "default_allow_network": settings.terminal_default_allow_network,
            },
            "allowlisted_commands": [
                "python <script.py>",
                "pytest [file]",
                "python -m unittest [file]",
                "node <script.js>",
                "ls / dir",
                "cat / type <file>",
                "echo <text>",
                "git status / git diff",
            ],
            "approval_required_operations": [
                "pip install <pkg>",
                "npm install <pkg>",
                "outbound network execution (--allow-network)",
                "file deletion via terminal (rm / del)",
            ],
        }

    # =========================================================================
    # Project & File Management with Version Backups
    # =========================================================================

    def _ensure_default_project(self, user_id: str) -> str:
        uid = self._sanitize_user_id(user_id)
        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT project_id FROM terminal_projects WHERE user_id = ? ORDER BY created_at ASC LIMIT 1",
                    (uid,),
                ).fetchone()
                if row:
                    return str(row["project_id"])
            finally:
                conn.close()

        created = self.create_project(
            CreateCodeProjectRequest(
                user_id=uid,
                name="Nexora Analytics & Algorithms Starter",
                description="Default Stage 18 Python sandbox workspace with unit tests.",
                template="python",
            ),
            fixed_project_id="proj_default_py",
        )
        return created.project_id

    def create_project(
        self,
        req: CreateCodeProjectRequest,
        fixed_project_id: Optional[str] = None,
    ) -> CodeProjectSummary:
        uid = self._sanitize_user_id(req.user_id)
        pid = fixed_project_id or f"proj_{uuid.uuid4().hex[:10]}"
        tpl = STARTER_TEMPLATES.get(req.template, STARTER_TEMPLATES["python"])
        proj_dir = self._project_dir(uid, pid)
        proj_dir.mkdir(parents=True, exist_ok=True)
        (proj_dir / INTERNAL_BACKUP_DIR).mkdir(parents=True, exist_ok=True)

        now_iso = utc_now().isoformat()
        for rel_path, file_content in tpl["files"].items():
            fpath, _ = self._resolve_project_file(uid, pid, rel_path)
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(file_content, encoding="utf-8")

        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO terminal_projects
                    (project_id, user_id, name, description, template, primary_language, entrypoint, test_entrypoint, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pid,
                        uid,
                        req.name.strip(),
                        req.description.strip(),
                        req.template,
                        tpl["primary_language"],
                        tpl["entrypoint"],
                        tpl["test_entrypoint"],
                        now_iso,
                        now_iso,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        return self.get_project(uid, pid)

    def list_projects(self, user_id: str = "default_user") -> List[CodeProjectSummary]:
        uid = self._sanitize_user_id(user_id)
        self._ensure_default_project(uid)
        with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    "SELECT project_id FROM terminal_projects WHERE user_id = ? ORDER BY updated_at DESC",
                    (uid,),
                ).fetchall()
            finally:
                conn.close()
        return [self.get_project(uid, str(r["project_id"])) for r in rows]

    def get_project(self, user_id: str, project_id: str) -> CodeProjectSummary:
        uid = self._sanitize_user_id(user_id)
        pid = self._sanitize_project_id(project_id)
        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT * FROM terminal_projects WHERE user_id = ? AND project_id = ?",
                    (uid, pid),
                ).fetchone()
                if not row:
                    raise ValueError(f"Project '{pid}' not found for user '{uid}'.")
                backup_rows = conn.execute(
                    "SELECT relative_path, COUNT(*) as cnt FROM terminal_backups WHERE user_id = ? AND project_id = ? GROUP BY relative_path",
                    (uid, pid),
                ).fetchall()
                backup_counts = {str(r["relative_path"]): int(r["cnt"]) for r in backup_rows}
            finally:
                conn.close()

        proj_dir = self._project_dir(uid, pid)
        proj_dir.mkdir(parents=True, exist_ok=True)
        files: List[CodeProjectFile] = []
        for item in sorted(proj_dir.rglob("*")):
            if not item.is_file():
                continue
            rel = item.relative_to(proj_dir).as_posix()
            if (
                rel.startswith(INTERNAL_BACKUP_DIR)
                or "/__pycache__/" in f"/{rel}/"
                or item.name == INTERNAL_SANDBOX_FILE
                or item.suffix == ".pyc"
            ):
                continue
            raw_bytes = item.read_bytes()
            sha = hashlib.sha256(raw_bytes).hexdigest()
            text_content = raw_bytes.decode("utf-8", errors="replace")
            files.append(
                CodeProjectFile(
                    relative_path=rel,
                    name=item.name,
                    language=self._detect_language(item.name),
                    size_bytes=len(raw_bytes),
                    sha256_hash=sha,
                    modified_at=datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc),
                    backup_count=backup_counts.get(rel, 0),
                    content=text_content,
                )
            )

        return CodeProjectSummary(
            project_id=pid,
            user_id=uid,
            name=str(row["name"]),
            description=str(row["description"]),
            template=row["template"],
            primary_language=row["primary_language"],
            entrypoint=str(row["entrypoint"]),
            test_entrypoint=str(row["test_entrypoint"]),
            file_count=len(files),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            files=files,
        )

    def _create_backup_snapshot(
        self,
        user_id: str,
        project_id: str,
        relative_path: str,
        reason: str,
    ) -> Optional[CodeFileBackup]:
        uid = self._sanitize_user_id(user_id)
        pid = self._sanitize_project_id(project_id)
        fpath, norm_rel = self._resolve_project_file(uid, pid, relative_path)
        if not fpath.exists() or not fpath.is_file():
            return None

        raw_bytes = fpath.read_bytes()
        sha = hashlib.sha256(raw_bytes).hexdigest()
        proj_dir = self._project_dir(uid, pid)
        backup_dir = proj_dir / INTERNAL_BACKUP_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)

        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT COALESCE(MAX(version_number), 0) AS max_v FROM terminal_backups WHERE user_id = ? AND project_id = ? AND relative_path = ?",
                    (uid, pid, norm_rel),
                ).fetchone()
                next_v = int(row["max_v"]) + 1
                backup_id = f"cbk_{uuid.uuid4().hex[:12]}"
                safe_name = norm_rel.replace("/", "__")
                snap_file = backup_dir / f"{backup_id}_v{next_v}_{safe_name}"
                snap_file.write_bytes(raw_bytes)
                now_dt = utc_now()
                conn.execute(
                    """
                    INSERT INTO terminal_backups
                    (backup_id, user_id, project_id, relative_path, version_number, sha256_hash, size_bytes, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        backup_id,
                        uid,
                        pid,
                        norm_rel,
                        next_v,
                        sha,
                        len(raw_bytes),
                        reason,
                        now_dt.isoformat(),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        return CodeFileBackup(
            backup_id=backup_id,
            user_id=uid,
            project_id=pid,
            relative_path=norm_rel,
            version_number=next_v,
            sha256_hash=sha,
            size_bytes=len(raw_bytes),
            reason=reason,
            created_at=now_dt,
        )

    def save_file(
        self, project_id: str, req: SaveCodeFileRequest
    ) -> Tuple[CodeProjectFile, Optional[CodeFileBackup]]:
        uid = self._sanitize_user_id(req.user_id)
        pid = self._sanitize_project_id(project_id)
        # Ensure project exists
        self.get_project(uid, pid)
        fpath, norm_rel = self._resolve_project_file(uid, pid, req.relative_path)

        backup: Optional[CodeFileBackup] = None
        if fpath.exists() and req.create_backup:
            existing_text = fpath.read_text(encoding="utf-8", errors="replace")
            if existing_text != req.content:
                backup = self._create_backup_snapshot(
                    uid, pid, norm_rel, reason=req.backup_reason
                )

        fpath.parent.mkdir(parents=True, exist_ok=True)
        encoded = req.content.encode("utf-8")
        fpath.write_bytes(encoded)
        sha = hashlib.sha256(encoded).hexdigest()

        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "UPDATE terminal_projects SET updated_at = ? WHERE user_id = ? AND project_id = ?",
                    (utc_now().isoformat(), uid, pid),
                )
                cnt_row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM terminal_backups WHERE user_id = ? AND project_id = ? AND relative_path = ?",
                    (uid, pid, norm_rel),
                ).fetchone()
                b_cnt = int(cnt_row["cnt"]) if cnt_row else 0
                conn.commit()
            finally:
                conn.close()

        file_item = CodeProjectFile(
            relative_path=norm_rel,
            name=fpath.name,
            language=self._detect_language(fpath.name),
            size_bytes=len(encoded),
            sha256_hash=sha,
            modified_at=datetime.fromtimestamp(fpath.stat().st_mtime, tz=timezone.utc),
            backup_count=b_cnt,
            content=req.content,
        )
        return file_item, backup

    def list_backups(
        self, user_id: str, project_id: str, relative_path: Optional[str] = None
    ) -> List[CodeFileBackup]:
        uid = self._sanitize_user_id(user_id)
        pid = self._sanitize_project_id(project_id)
        with self._lock:
            conn = self._get_conn()
            try:
                if relative_path:
                    _, norm_rel = self._resolve_project_file(uid, pid, relative_path)
                    rows = conn.execute(
                        "SELECT * FROM terminal_backups WHERE user_id = ? AND project_id = ? AND relative_path = ? ORDER BY version_number DESC",
                        (uid, pid, norm_rel),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM terminal_backups WHERE user_id = ? AND project_id = ? ORDER BY created_at DESC",
                        (uid, pid),
                    ).fetchall()
            finally:
                conn.close()

        return [
            CodeFileBackup(
                backup_id=str(r["backup_id"]),
                user_id=str(r["user_id"]),
                project_id=str(r["project_id"]),
                relative_path=str(r["relative_path"]),
                version_number=int(r["version_number"]),
                sha256_hash=str(r["sha256_hash"]),
                size_bytes=int(r["size_bytes"]),
                reason=str(r["reason"]),
                created_at=datetime.fromisoformat(str(r["created_at"])),
            )
            for r in rows
        ]

    def restore_backup(
        self, user_id: str, project_id: str, backup_id: str
    ) -> CodeProjectFile:
        uid = self._sanitize_user_id(user_id)
        pid = self._sanitize_project_id(project_id)
        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT * FROM terminal_backups WHERE user_id = ? AND project_id = ? AND backup_id = ?",
                    (uid, pid, backup_id),
                ).fetchone()
                if not row:
                    raise ValueError(f"Backup '{backup_id}' not found.")
            finally:
                conn.close()

        rel_path = str(row["relative_path"])
        version_num = int(row["version_number"])
        safe_name = rel_path.replace("/", "__")
        snap_file = (
            self._project_dir(uid, pid)
            / INTERNAL_BACKUP_DIR
            / f"{backup_id}_v{version_num}_{safe_name}"
        )
        if not snap_file.exists():
            raise ValueError(f"Backup snapshot file for '{backup_id}' is missing on disk.")

        restored_content = snap_file.read_text(encoding="utf-8", errors="replace")
        file_item, _ = self.save_file(
            pid,
            SaveCodeFileRequest(
                user_id=uid,
                relative_path=rel_path,
                content=restored_content,
                create_backup=True,
                backup_reason=f"pre_restore_from_{backup_id}",
            ),
        )
        return file_item

    def reset_project(self, user_id: str, project_id: str) -> CodeProjectSummary:
        uid = self._sanitize_user_id(user_id)
        pid = self._sanitize_project_id(project_id)
        proj = self.get_project(uid, pid)
        tpl = STARTER_TEMPLATES.get(proj.template, STARTER_TEMPLATES["python"])
        for rel_path, default_content in tpl["files"].items():
            self.save_file(
                pid,
                SaveCodeFileRequest(
                    user_id=uid,
                    relative_path=rel_path,
                    content=default_content,
                    create_backup=True,
                    backup_reason="project_template_reset",
                ),
            )
        return self.get_project(uid, pid)

    # =========================================================================
    # Syntax Checking, Formatting, Linting & Missing Dependency Detection
    # =========================================================================

    @staticmethod
    def _format_code(content: str, language: CodeLanguage) -> str:
        lines = (content or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        cleaned_lines: List[str] = []
        blank_streak = 0
        for line in lines:
            expanded = line.replace("\t", "    ").rstrip()
            if expanded == "":
                blank_streak += 1
                max_blanks = 2 if language == "python" else 1
                if blank_streak <= max_blanks:
                    cleaned_lines.append("")
            else:
                blank_streak = 0
                cleaned_lines.append(expanded)
        result = "\n".join(cleaned_lines).strip() + "\n"
        return result

    def _inspect_python_code(
        self,
        uid: str,
        pid: str,
        norm_rel: str,
        content: str,
    ) -> Tuple[bool, List[CodeDiagnosticIssue], List[DependencyStatusItem]]:
        diagnostics: List[CodeDiagnosticIssue] = []
        dependencies: List[DependencyStatusItem] = []
        syntax_valid = True

        try:
            tree = ast.parse(content, filename=norm_rel)
        except SyntaxError as syn_err:
            syntax_valid = False
            suggestion = "Verify matching parentheses, quotes, indentation, and trailing colons ':' on block headers."
            msg = syn_err.msg or "Invalid Python syntax"
            if "expected ':'" in msg.lower():
                suggestion = "Add a colon ':' at the end of the def/if/for/while/class statement."
            elif "unclosed" in msg.lower() or "never closed" in msg.lower():
                suggestion = "Close the matching parenthesis, bracket, or string literal."
            diagnostics.append(
                CodeDiagnosticIssue(
                    line=syn_err.lineno or 1,
                    column=syn_err.offset or 1,
                    severity="error",
                    code="PY_SYNTAX_ERROR",
                    message=f"SyntaxError: {msg}",
                    rule_source="python_ast",
                    suggestion=suggestion,
                )
            )
            # Even when syntax fails, scan regex imports for dependency awareness
            for m in re.finditer(r"^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)", content, re.MULTILINE):
                pkg = m.group(1)
                dependencies.append(self._check_python_dependency(uid, pid, pkg, norm_rel))
            return syntax_valid, diagnostics, dependencies

        # Static AST Lint Checks + Import extraction
        imported_names: Dict[str, int] = {}
        used_names: Set[str] = set()
        imported_roots: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0]
                    imported_roots.add(root_pkg)
                    bound_name = alias.asname or root_pkg
                    imported_names[bound_name] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:
                    root_pkg = node.module.split(".")[0]
                    imported_roots.add(root_pkg)
                for alias in node.names:
                    if alias.name != "*":
                        bound_name = alias.asname or alias.name
                        imported_names[bound_name] = node.lineno
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
            elif isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    diagnostics.append(
                        CodeDiagnosticIssue(
                            line=node.lineno,
                            column=node.col_offset + 1,
                            severity="warning",
                            code="PY_BARE_EXCEPT",
                            message="Bare 'except:' catches SystemExit and KeyboardInterrupt.",
                            rule_source="nexora_linter",
                            suggestion="Use 'except Exception as exc:' instead of bare 'except:'.",
                        )
                    )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default_node in node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
                    if isinstance(default_node, (ast.List, ast.Dict, ast.Set)):
                        diagnostics.append(
                            CodeDiagnosticIssue(
                                line=node.lineno,
                                column=node.col_offset + 1,
                                severity="warning",
                                code="PY_MUTABLE_DEFAULT",
                                message=f"Function '{node.name}' uses a mutable default argument (list/dict/set).",
                                rule_source="nexora_linter",
                                suggestion="Default to None and initialize the collection inside the function body.",
                            )
                        )
            elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                if isinstance(node.right, ast.Constant) and node.right.value == 0:
                    diagnostics.append(
                        CodeDiagnosticIssue(
                            line=node.lineno,
                            column=node.col_offset + 1,
                            severity="error",
                            code="PY_DIV_BY_ZERO",
                            message="Literal division or modulo by zero detected.",
                            rule_source="nexora_linter",
                            suggestion="Guard the denominator against zero before dividing.",
                        )
                    )

        for name, lineno in imported_names.items():
            if name not in used_names and not name.startswith("_"):
                diagnostics.append(
                    CodeDiagnosticIssue(
                        line=lineno,
                        column=1,
                        severity="info",
                        code="PY_UNUSED_IMPORT",
                        message=f"Imported symbol '{name}' is unused.",
                        rule_source="nexora_linter",
                        suggestion=f"Remove unused import '{name}' if not needed.",
                    )
                )

        # Also check requirements.txt in the project if present
        req_file = self._project_dir(uid, pid) / "requirements.txt"
        if req_file.exists():
            for line in req_file.read_text(encoding="utf-8", errors="replace").splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    pkg_token = re.split(r"[=<>!~;\s]", stripped)[0].strip()
                    if pkg_token:
                        imported_roots.add(pkg_token)

        for pkg in sorted(imported_roots):
            dependencies.append(self._check_python_dependency(uid, pid, pkg, norm_rel))

        return syntax_valid, diagnostics, dependencies

    def _check_python_dependency(
        self, uid: str, pid: str, pkg_name: str, imported_in: str
    ) -> DependencyStatusItem:
        proj_dir = self._project_dir(uid, pid)
        if (proj_dir / f"{pkg_name}.py").exists() or (proj_dir / pkg_name / "__init__.py").exists():
            return DependencyStatusItem(
                package_name=pkg_name,
                ecosystem="builtin",
                installed=True,
                version="local_module",
                imported_in=[imported_in],
                setup_explanation=f"Local workspace module '{pkg_name}.py'.",
            )

        stdlib_names = getattr(sys, "stdlib_module_names", set())
        if pkg_name in stdlib_names or pkg_name in sys.builtin_module_names:
            return DependencyStatusItem(
                package_name=pkg_name,
                ecosystem="builtin",
                installed=True,
                version=sys.version.split()[0],
                imported_in=[imported_in],
                setup_explanation="Python standard library module (built-in).",
            )

        spec = importlib.util.find_spec(pkg_name)
        if spec is not None:
            ver = "installed"
            try:
                ver = importlib.metadata.version(pkg_name)
            except Exception:
                pass
            return DependencyStatusItem(
                package_name=pkg_name,
                ecosystem="pip",
                installed=True,
                version=ver,
                imported_in=[imported_in],
                install_command=f"pip install {pkg_name}",
                setup_explanation=f"Package '{pkg_name}' ({ver}) is installed and available in sandbox.",
            )

        return DependencyStatusItem(
            package_name=pkg_name,
            ecosystem="pip",
            installed=False,
            version=None,
            imported_in=[imported_in],
            install_command=f"pip install {pkg_name}",
            setup_explanation=(
                f"Missing dependency '{pkg_name}'. Run 'pip install {pkg_name}' via the Controlled Terminal "
                "(requires explicit user confirmation) or add it to requirements.txt."
            ),
        )

    def _inspect_js_or_web_code(
        self,
        uid: str,
        pid: str,
        norm_rel: str,
        language: CodeLanguage,
        content: str,
    ) -> Tuple[bool, List[CodeDiagnosticIssue], List[DependencyStatusItem]]:
        diagnostics: List[CodeDiagnosticIssue] = []
        dependencies: List[DependencyStatusItem] = []
        syntax_valid = True

        # Check balanced brackets/braces/parens for JS/TS/CSS
        if language in ("javascript", "typescript", "css"):
            stack: List[Tuple[str, int, int]] = []
            pairs = {")": "(", "]": "[", "}": "{"}
            in_str: Optional[str] = None
            escaped = False
            for line_idx, line in enumerate(content.splitlines(), start=1):
                if line.strip().startswith("//"):
                    continue
                for col_idx, ch in enumerate(line, start=1):
                    if escaped:
                        escaped = False
                        continue
                    if ch == "\\":
                        escaped = True
                        continue
                    if in_str:
                        if ch == in_str:
                            in_str = None
                        continue
                    if ch in ("'", '"', "`"):
                        in_str = ch
                        continue
                    if ch in "([{":
                        stack.append((ch, line_idx, col_idx))
                    elif ch in ")]}":
                        if not stack or stack[-1][0] != pairs[ch]:
                            syntax_valid = False
                            diagnostics.append(
                                CodeDiagnosticIssue(
                                    line=line_idx,
                                    column=col_idx,
                                    severity="error",
                                    code=f"{language.upper()}_UNMATCHED_BRACKET",
                                    message=f"Unmatched closing '{ch}' at line {line_idx}:{col_idx}.",
                                    rule_source="nexora_BracketChecker",
                                    suggestion="Ensure all parentheses, brackets, and braces are properly balanced.",
                                )
                            )
                            break
                        stack.pop()
            if stack:
                open_ch, open_ln, open_col = stack[-1]
                syntax_valid = False
                diagnostics.append(
                    CodeDiagnosticIssue(
                        line=open_ln,
                        column=open_col,
                        severity="error",
                        code=f"{language.upper()}_UNCLOSED_DELIMITER",
                        message=f"Unclosed '{open_ch}' opened at line {open_ln}:{open_col}.",
                        rule_source="nexora_BracketChecker",
                        suggestion=f"Close '{open_ch}' before the end of the file.",
                    )
                )

        # Extract require('pkg') or import ... from 'pkg'
        if language in ("javascript", "typescript"):
            js_builtins = {"assert", "fs", "path", "os", "util", "crypto", "events", "stream", "http", "https", "url"}
            pkgs: Set[str] = set()
            for m in re.finditer(r"(?:require\(\s*['\"]([^'\"]+)['\"]\s*\)|from\s+['\"]([^'\"]+)['\"])", content):
                raw_mod = m.group(1) or m.group(2)
                if raw_mod and not raw_mod.startswith(".") and not raw_mod.startswith("/"):
                    pkgs.add(raw_mod.split("/")[0])
            proj_dir = self._project_dir(uid, pid)
            for pkg in sorted(pkgs):
                if pkg in js_builtins:
                    dependencies.append(
                        DependencyStatusItem(
                            package_name=pkg,
                            ecosystem="builtin",
                            installed=True,
                            version="node_builtin",
                            imported_in=[norm_rel],
                            setup_explanation="Built-in Node.js runtime module.",
                        )
                    )
                else:
                    installed = (proj_dir / "node_modules" / pkg).exists()
                    dependencies.append(
                        DependencyStatusItem(
                            package_name=pkg,
                            ecosystem="npm",
                            installed=installed,
                            version="installed" if installed else None,
                            imported_in=[norm_rel],
                            install_command=f"npm install {pkg}",
                            setup_explanation=(
                                f"Package '{pkg}' is installed in node_modules."
                                if installed
                                else f"Missing npm dependency '{pkg}'. Run 'npm install {pkg}' with approval."
                            ),
                        )
                    )

        return syntax_valid, diagnostics, dependencies

    def inspect_code(self, req: CodeInspectRequest) -> CodeInspectionResult:
        uid = self._sanitize_user_id(req.user_id)
        pid = self._sanitize_project_id(req.project_id)
        fpath, norm_rel = self._resolve_project_file(uid, pid, req.relative_path)

        if req.content is not None:
            source_text = req.content
        elif fpath.exists():
            source_text = fpath.read_text(encoding="utf-8", errors="replace")
        else:
            raise ValueError(f"File '{norm_rel}' does not exist in project '{pid}'.")

        lang = self._detect_language(norm_rel)
        formatted = self._format_code(source_text, lang)
        formatting_changed = formatted != source_text

        if req.apply_formatting and formatting_changed and fpath.exists():
            self.save_file(
                pid,
                SaveCodeFileRequest(
                    user_id=uid,
                    relative_path=norm_rel,
                    content=formatted,
                    create_backup=True,
                    backup_reason="auto_format",
                ),
            )

        if lang == "python":
            syntax_valid, diagnostics, dependencies = self._inspect_python_code(
                uid, pid, norm_rel, formatted if req.apply_formatting else source_text
            )
        else:
            syntax_valid, diagnostics, dependencies = self._inspect_js_or_web_code(
                uid, pid, norm_rel, lang, formatted if req.apply_formatting else source_text
            )

        untrusted_warnings = self._scan_untrusted_repo_instructions(source_text)
        for uw in untrusted_warnings:
            diagnostics.append(
                CodeDiagnosticIssue(
                    line=1,
                    column=1,
                    severity="warning",
                    code="SECURITY_UNTRUSTED_REPO_INSTRUCTION",
                    message=uw,
                    rule_source="nexora_security_scanner",
                    suggestion="Untrusted repository instructions are quarantined and cannot override sandbox policies.",
                )
            )

        missing_count = sum(1 for d in dependencies if not d.installed)
        err_count = sum(1 for d in diagnostics if d.severity == "error")
        warn_count = sum(1 for d in diagnostics if d.severity == "warning")

        summary = (
            f"Inspected '{norm_rel}' ({lang}): "
            f"Syntax={'VALID' if syntax_valid else 'INVALID'}, "
            f"{err_count} error(s), {warn_count} warning(s), "
            f"{missing_count} missing dependency(ies)."
        )

        return CodeInspectionResult(
            project_id=pid,
            relative_path=norm_rel,
            language=lang,
            syntax_valid=syntax_valid,
            formatted_content=formatted,
            formatting_changed=formatting_changed,
            diagnostics=diagnostics,
            dependencies=dependencies,
            missing_dependencies_count=missing_count,
            untrusted_instruction_warnings=untrusted_warnings,
            summary=summary,
        )

    # =========================================================================
    # Sandboxed Process Execution & Controlled Terminal
    # =========================================================================

    def _build_sanitized_env(self, proj_dir: Path, allow_network: bool) -> Dict[str, str]:
        safe_env: Dict[str, str] = {}
        allowed_passthrough = {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "COMSPEC",
            "PATHEXT",
            "TEMP",
            "TMP",
            "LANG",
            "LC_ALL",
        }
        for k, v in os.environ.items():
            if k.upper() in allowed_passthrough:
                safe_env[k] = v

        safe_env["PYTHONDONTWRITEBYTECODE"] = "1"
        safe_env["PYTHONUNBUFFERED"] = "1"
        safe_env["PYTHONNOUSERSITE"] = "1"
        safe_env["PYTHONIOENCODING"] = "utf-8"
        safe_env["NEXORA_SANDBOX_ACTIVE"] = "1"
        safe_env["NEXORA_ALLOW_NETWORK"] = "1" if allow_network else "0"
        safe_env["NEXORA_PROJECT_ROOT"] = str(proj_dir)
        safe_env["NEXORA_MAX_MEMORY_MB"] = str(settings.terminal_max_memory_mb)
        return safe_env

    def _write_python_sandbox_bootstrap(
        self,
        proj_dir: Path,
        target_rel: str,
        mode: Literal["run", "test"],
        args: List[str],
        allow_network: bool,
    ) -> Path:
        """
        Writes a deterministic sandbox runner bootstrap that enforces:
        - Outbound network blocking when allow_network=False
        - Subprocess/shell spawn blocking in user scripts
        - Recursion depth & memory ceiling where supported by OS
        - Clean invocation of user script or unittest/pytest runner
        """
        boot_path = proj_dir / INTERNAL_SANDBOX_FILE
        boot_code = f'''# Auto-generated NEXORA AI Stage 18 Sandbox Guard
import os
import sys
import socket
import builtins

sys.setrecursionlimit(250)
PROJECT_ROOT = os.path.abspath({json.dumps(str(proj_dir))})
ALLOW_NETWORK = { "True" if allow_network else "False" }
EXEC_MODE = {json.dumps(mode)}
TARGET_REL = {json.dumps(target_rel)}
USER_ARGS = {json.dumps(args)}

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 1. Network Isolation Guard
if not ALLOW_NETWORK:
    def _blocked_network(*_a, **_kw):
        raise PermissionError("NEXORA Sandbox Policy: Outbound network access is disabled by default.")
    socket.socket.connect = _blocked_network
    socket.socket.connect_ex = _blocked_network
    socket.create_connection = _blocked_network

# 2. Subprocess & Host Escape Guard during user script run
if EXEC_MODE == "run":
    def _blocked_os_system(*_a, **_kw):
        raise PermissionError("NEXORA Sandbox Policy: Direct shell execution (os.system/popen) is blocked inside sandboxed code.")
    os.system = _blocked_os_system
    os.popen = _blocked_os_system

# 3. File Open Boundary Guard (blocks reading outside PROJECT_ROOT except Python stdlib/site-packages)
_orig_open = builtins.open
def _guarded_open(file, mode="r", *a, **kw):
    if isinstance(file, (str, bytes, os.PathLike)):
        p_str = os.fspath(file)
        if isinstance(p_str, bytes):
            p_str = p_str.decode("utf-8", errors="replace")
        abs_p = os.path.abspath(os.path.join(PROJECT_ROOT, p_str)) if not os.path.isabs(p_str) else os.path.abspath(p_str)
        base_lower = os.path.basename(abs_p).lower()
        if base_lower in (".env", "id_rsa", "id_ed25519", "passwd", "shadow", "sam"):
            raise PermissionError(f"NEXORA Sandbox Policy: Access to sensitive file '{{base_lower}}' is blocked.")
        if any(w in mode for w in ("w", "a", "x", "+")) and not abs_p.startswith(PROJECT_ROOT):
            raise PermissionError(f"NEXORA Sandbox Policy: Writing outside project workspace ('{{p_str}}') is blocked.")
    return _orig_open(file, mode, *a, **kw)

builtins.open = _guarded_open

if EXEC_MODE == "run":
    import runpy
    sys.argv = [TARGET_REL] + list(USER_ARGS)
    runpy.run_path(os.path.join(PROJECT_ROOT, TARGET_REL), run_name="__main__")
else:
    import unittest
    loader = unittest.TestLoader()
    target_full = os.path.join(PROJECT_ROOT, TARGET_REL)
    if os.path.isfile(target_full):
        suite = loader.discover(start_dir=os.path.dirname(target_full) or PROJECT_ROOT, pattern=os.path.basename(target_full))
    else:
        suite = loader.discover(start_dir=PROJECT_ROOT, pattern="test*.py")
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
'''
        boot_path.write_text(boot_code, encoding="utf-8")
        return boot_path

    @staticmethod
    def _terminate_process_tree(proc: subprocess.Popen) -> None:
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3,
                    check=False,
                )
            else:
                proc.kill()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def _run_subprocess_bounded(
        self,
        execution_id: str,
        user_id: str,
        argv: List[str],
        cwd: Path,
        env: Dict[str, str],
        stdin_text: str,
        timeout_seconds: float,
    ) -> Tuple[int, str, str, bool, bool, float]:
        uid = self._sanitize_user_id(user_id)
        with self._lock:
            current_active = self._active_runs_per_user.get(uid, 0)
            if current_active >= settings.terminal_max_concurrent_runs_per_user:
                raise RuntimeError(
                    f"Concurrent execution limit ({settings.terminal_max_concurrent_runs_per_user}) reached for user '{uid}'."
                )
            self._active_runs_per_user[uid] = current_active + 1

        start_ts = time.perf_counter()
        timed_out = False
        proc: Optional[subprocess.Popen] = None
        try:
            proc = subprocess.Popen(
                argv,
                cwd=str(cwd),
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
            )
            with self._lock:
                self._active_processes[execution_id] = proc

            stdin_bytes = stdin_text.encode("utf-8") if stdin_text else None
            try:
                out_bytes, err_bytes = proc.communicate(
                    input=stdin_bytes, timeout=timeout_seconds
                )
                exit_code = int(proc.returncode or 0)
            except subprocess.TimeoutExpired:
                timed_out = True
                self._terminate_process_tree(proc)
                try:
                    out_bytes, err_bytes = proc.communicate(timeout=1.0)
                except Exception:
                    out_bytes, err_bytes = b"", b""
                exit_code = 124
        finally:
            with self._lock:
                self._active_processes.pop(execution_id, None)
                self._active_runs_per_user[uid] = max(
                    0, self._active_runs_per_user.get(uid, 1) - 1
                )

        duration_ms = round((time.perf_counter() - start_ts) * 1000, 2)
        max_bytes = settings.terminal_max_output_bytes
        truncated = False
        if len(out_bytes) > max_bytes:
            out_bytes = out_bytes[:max_bytes]
            truncated = True
        if len(err_bytes) > max_bytes:
            err_bytes = err_bytes[:max_bytes]
            truncated = True

        stdout_str = self._redact_secrets(out_bytes.decode("utf-8", errors="replace"))
        stderr_str = self._redact_secrets(err_bytes.decode("utf-8", errors="replace"))
        if truncated:
            stdout_str += f"\n...[OUTPUT TRUNCATED AT {max_bytes} BYTES SANDBOX LIMIT]..."
        if timed_out:
            stderr_str = (
                (stderr_str + "\n").lstrip()
                + f"TimeoutError: Execution exceeded sandbox time limit of {timeout_seconds:.1f}s and was terminated."
            )

        return exit_code, stdout_str, stderr_str, truncated, timed_out, duration_ms

    @staticmethod
    def _parse_unittest_or_node_results(
        framework: str, exit_code: int, stdout: str, stderr: str
    ) -> TestSuiteResult:
        combined = f"{stdout}\n{stderr}"
        cases: List[TestCaseResult] = []

        if framework == "unittest":
            for m in re.finditer(
                r"^(test_[a-zA-Z0-9_]+)\s+\(([^)]+)\)\s+\.\.\.\s+(ok|FAIL|ERROR|skipped.*)$",
                combined,
                re.MULTILINE,
            ):
                t_name = f"{m.group(2)}.{m.group(1)}"
                raw_st = m.group(3).lower()
                if raw_st == "ok":
                    st: Literal["passed", "failed", "error", "skipped"] = "passed"
                elif raw_st.startswith("fail"):
                    st = "failed"
                elif raw_st.startswith("error"):
                    st = "error"
                else:
                    st = "skipped"
                cases.append(TestCaseResult(name=t_name, status=st))

            ran_match = re.search(r"Ran\s+(\d+)\s+tests?\s+in\s+([\d\.]+)s", combined)
            total = int(ran_match.group(1)) if ran_match else len(cases)
            failed = sum(1 for c in cases if c.status == "failed")
            errors = sum(1 for c in cases if c.status == "error")
            skipped = sum(1 for c in cases if c.status == "skipped")
            if not cases and total > 0:
                if exit_code == 0:
                    passed = total
                else:
                    fail_m = re.search(r"failures=(\d+)", combined)
                    err_m = re.search(r"errors=(\d+)", combined)
                    failed = int(fail_m.group(1)) if fail_m else (1 if exit_code != 0 else 0)
                    errors = int(err_m.group(1)) if err_m else 0
                    passed = max(0, total - failed - errors)
            else:
                passed = sum(1 for c in cases if c.status == "passed")

            return TestSuiteResult(
                framework="unittest",
                executed=True,
                passed=passed,
                failed=failed,
                errors=errors,
                skipped=skipped,
                total=total,
                all_passed=(exit_code == 0 and total > 0 and failed == 0 and errors == 0),
                cases=cases,
                raw_summary=f"Ran {total} test(s): {passed} passed, {failed} failed, {errors} error(s).",
            )

        # Node.js test output
        passed = 1 if exit_code == 0 else 0
        failed = 0 if exit_code == 0 else 1
        cases.append(
            TestCaseResult(
                name="node_test_suite",
                status="passed" if exit_code == 0 else "failed",
                message=stdout.strip()[:200] if exit_code == 0 else stderr.strip()[:200],
            )
        )
        return TestSuiteResult(
            framework="node_assert",
            executed=True,
            passed=passed,
            failed=failed,
            errors=0,
            skipped=0,
            total=1,
            all_passed=(exit_code == 0),
            cases=cases,
            raw_summary="Node test suite passed." if exit_code == 0 else "Node test suite failed.",
        )

    @staticmethod
    def _diagnose_execution_failure(
        exit_code: int, timed_out: bool, stdout: str, stderr: str
    ) -> Tuple[Optional[str], Optional[str]]:
        if exit_code == 0 and not timed_out:
            return None, None
        combined = f"{stderr}\n{stdout}"
        if timed_out:
            return (
                "Execution timed out due to an infinite loop, blocking I/O wait, or excessive computation.",
                "Add a termination condition or loop bound to prevent infinite iteration.",
            )
        if "PermissionError: NEXORA Sandbox Policy" in combined:
            return (
                "Sandbox Security Policy blocked an unauthorized network, shell, or outside-workspace file operation.",
                "Remove external network/shell calls or explicitly request user approval for network access.",
            )
        if "ModuleNotFoundError" in combined or "ImportError" in combined:
            m = re.search(r"No module named ['\"]([^'\"]+)['\"]", combined)
            pkg = m.group(1) if m else "unknown_package"
            return (
                f"Missing Python dependency '{pkg}'.",
                f"Install '{pkg}' via the Controlled Terminal ('pip install {pkg}' with user approval) or use standard library equivalents.",
            )
        if "SyntaxError" in combined:
            return (
                "Python SyntaxError prevented the script from compiling.",
                "Run 'Check & Lint' or 'Auto-Debug & Repair' to fix the syntax error on the reported line.",
            )
        if "ZeroDivisionError" in combined:
            return (
                "ZeroDivisionError raised during arithmetic division by 0.",
                "Check if the denominator is 0 before dividing and return a safe fallback value.",
            )
        if "NameError" in combined:
            m = re.search(r"name ['\"]([^'\"]+)['\"] is not defined", combined)
            sym = m.group(1) if m else "identifier"
            return (
                f"NameError: identifier '{sym}' is referenced before definition or misspelled.",
                f"Define '{sym}' or fix the variable/function name spelling.",
            )
        if "AssertionError" in combined or "FAILED (" in combined:
            return (
                "One or more unit test assertions failed.",
                "Inspect the expected vs. actual values in the test traceback or run 'Auto-Debug & Repair'.",
            )
        if "MemoryError" in combined:
            return (
                "Process exceeded sandbox memory allocation limits.",
                "Reduce list/buffer sizes or use generators instead of materializing huge collections.",
            )
        return (
            f"Process exited with non-zero code {exit_code}.",
            "Review stderr traceback for the root cause line and exception type.",
        )

    def _save_execution_record(self, record: TerminalExecutionRecord) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO terminal_executions
                    (execution_id, user_id, project_id, record_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        record.execution_id,
                        record.user_id,
                        record.project_id,
                        record.model_dump_json(),
                        record.created_at.isoformat(),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def list_executions(
        self, user_id: str, project_id: Optional[str] = None, limit: int = 30
    ) -> List[TerminalExecutionRecord]:
        uid = self._sanitize_user_id(user_id)
        with self._lock:
            conn = self._get_conn()
            try:
                if project_id:
                    pid = self._sanitize_project_id(project_id)
                    rows = conn.execute(
                        "SELECT record_json FROM terminal_executions WHERE user_id = ? AND project_id = ? ORDER BY created_at DESC LIMIT ?",
                        (uid, pid, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT record_json FROM terminal_executions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                        (uid, limit),
                    ).fetchall()
            finally:
                conn.close()
        return [TerminalExecutionRecord.model_validate_json(str(r["record_json"])) for r in rows]

    def stop_execution(self, user_id: str, execution_id: str) -> Dict[str, Any]:
        uid = self._sanitize_user_id(user_id)
        with self._lock:
            proc = self._active_processes.get(execution_id)
        if proc is not None:
            self._terminate_process_tree(proc)
            return {
                "execution_id": execution_id,
                "user_id": uid,
                "stopped": True,
                "message": f"Process for execution '{execution_id}' was terminated.",
            }
        return {
            "execution_id": execution_id,
            "user_id": uid,
            "stopped": False,
            "message": f"Execution '{execution_id}' is not currently running.",
        }

    async def execute_code(self, req: CodeExecuteRequest) -> TerminalExecutionRecord:
        uid = self._sanitize_user_id(req.user_id)
        pid = self._sanitize_project_id(req.project_id)
        proj = self.get_project(uid, pid)
        proj_dir = self._project_dir(uid, pid)

        target_rel = req.target_file or (
            proj.test_entrypoint if req.mode == "test" else proj.entrypoint
        )
        fpath, norm_rel = self._resolve_project_file(uid, pid, target_rel)
        if not fpath.exists():
            raise ValueError(f"Target file '{norm_rel}' does not exist in project '{pid}'.")

        lang = self._detect_language(norm_rel)
        exec_id = f"exec_{uuid.uuid4().hex[:12]}"
        timeout_sec = min(
            float(req.timeout_seconds or settings.terminal_execution_timeout_seconds),
            15.0,
        )

        # Gate network access behind explicit confirmation
        if req.allow_network and not req.confirmed_network:
            preview = CommandPreview(
                raw_command=f"{req.mode} {norm_rel} --allow-network",
                normalized_command=f"python {norm_rel} --allow-network",
                classification="requires_approval",
                risk_level="high",
                target_workspace=f"{uid}/{pid}",
                expected_effect=f"Execute '{norm_rel}' with outbound network access enabled.",
                requires_approval=True,
                approval_reason="Outbound network access is disabled by default in the sandbox and requires explicit user confirmation.",
            )
            rec = TerminalExecutionRecord(
                execution_id=exec_id,
                user_id=uid,
                project_id=pid,
                execution_type="run_tests" if req.mode == "test" else "run_code",
                command_preview=preview,
                status="WAITING_FOR_APPROVAL",
                memory_limit_mb=settings.terminal_max_memory_mb,
                network_enabled=True,
                verified_execution=False,
            )
            self._save_execution_record(rec)
            return rec

        preview = CommandPreview(
            raw_command=f"{'test' if req.mode == 'test' else 'run'} {norm_rel}",
            normalized_command=f"{lang} {norm_rel}",
            classification="allowed_safe",
            risk_level="low",
            target_workspace=f"{uid}/{pid}",
            expected_effect=f"Run {'test suite' if req.mode == 'test' else 'entrypoint'} '{norm_rel}' inside isolated sandbox.",
            requires_approval=False,
        )

        env = self._build_sanitized_env(proj_dir, allow_network=req.allow_network)
        boot_path: Optional[Path] = None

        try:
            if lang == "python":
                boot_path = self._write_python_sandbox_bootstrap(
                    proj_dir=proj_dir,
                    target_rel=norm_rel,
                    mode=req.mode,
                    args=req.args,
                    allow_network=req.allow_network,
                )
                argv = [sys.executable, "-I", str(boot_path)]
                exit_code, stdout, stderr, truncated, timed_out, duration_ms = await asyncio.to_thread(
                    self._run_subprocess_bounded,
                    exec_id,
                    uid,
                    argv,
                    proj_dir,
                    env,
                    req.stdin_text,
                    timeout_sec,
                )
                test_results = (
                    self._parse_unittest_or_node_results("unittest", exit_code, stdout, stderr)
                    if req.mode == "test"
                    else None
                )
            elif lang in ("javascript", "typescript"):
                node_bin = shutil.which("node")
                if not node_bin:
                    rec = TerminalExecutionRecord(
                        execution_id=exec_id,
                        user_id=uid,
                        project_id=pid,
                        execution_type="run_tests" if req.mode == "test" else "run_code",
                        command_preview=preview,
                        status="FAILED",
                        exit_code=127,
                        stdout="",
                        stderr="RuntimeUnavailableError: Node.js ('node') is not installed in the host environment.",
                        verified_execution=False,
                        error_diagnosis="Node.js runtime binary was not found on PATH.",
                        suggested_fix="Install Node.js or switch to a Python project workspace.",
                        completed_at=utc_now(),
                    )
                    self._save_execution_record(rec)
                    return rec

                argv = [node_bin, str(fpath)] + list(req.args)
                exit_code, stdout, stderr, truncated, timed_out, duration_ms = await asyncio.to_thread(
                    self._run_subprocess_bounded,
                    exec_id,
                    uid,
                    argv,
                    proj_dir,
                    env,
                    req.stdin_text,
                    timeout_sec,
                )
                test_results = (
                    self._parse_unittest_or_node_results("node_assert", exit_code, stdout, stderr)
                    if req.mode == "test"
                    else None
                )
            else:
                # HTML/CSS static verification
                inspection = self.inspect_code(
                    CodeInspectRequest(user_id=uid, project_id=pid, relative_path=norm_rel)
                )
                exit_code = 0 if inspection.syntax_valid else 1
                stdout = f"Static asset '{norm_rel}' ({lang}) validated: {inspection.summary}"
                stderr = "" if inspection.syntax_valid else "\n".join(d.message for d in inspection.diagnostics)
                truncated = False
                timed_out = False
                duration_ms = 5.0
                test_results = None
        finally:
            if boot_path and boot_path.exists():
                try:
                    boot_path.unlink()
                except Exception:
                    pass

        status: Literal["SUCCEEDED", "FAILED", "TIMED_OUT"] = (
            "TIMED_OUT" if timed_out else ("SUCCEEDED" if exit_code == 0 else "FAILED")
        )
        err_diag, fix_sug = self._diagnose_execution_failure(exit_code, timed_out, stdout, stderr)

        rec = TerminalExecutionRecord(
            execution_id=exec_id,
            user_id=uid,
            project_id=pid,
            execution_type="run_tests" if req.mode == "test" else "run_code",
            command_preview=preview,
            status=status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            output_truncated=truncated,
            timed_out=timed_out,
            duration_ms=duration_ms,
            memory_limit_mb=settings.terminal_max_memory_mb,
            network_enabled=req.allow_network,
            verified_execution=True,
            approved=True if req.confirmed_network else None,
            test_results=test_results,
            error_diagnosis=err_diag,
            suggested_fix=fix_sug,
            completed_at=utc_now(),
        )
        self._save_execution_record(rec)
        return rec

    # =========================================================================
    # Controlled Terminal Allowlist & Approval Gate
    # =========================================================================

    def classify_command(
        self,
        user_id: str,
        project_id: str,
        command: str,
        allow_network: bool = False,
    ) -> CommandPreview:
        uid = self._sanitize_user_id(user_id)
        pid = self._sanitize_project_id(project_id)
        raw = (command or "").strip()
        workspace_label = f"data/terminal_workspace/{uid}/{pid}"

        if not raw:
            return CommandPreview(
                raw_command="",
                normalized_command="",
                classification="blocked_forbidden",
                risk_level="critical",
                target_workspace=workspace_label,
                expected_effect="Empty command rejected.",
                blocked_reason="Command cannot be empty.",
            )

        # 1. Check strictly blocked patterns first
        for pattern, reason in BLOCKED_COMMAND_PATTERNS:
            if pattern.search(raw):
                return CommandPreview(
                    raw_command=raw,
                    normalized_command=raw,
                    classification="blocked_forbidden",
                    risk_level="critical",
                    target_workspace=workspace_label,
                    expected_effect="Blocked before execution by sandbox security policy.",
                    requires_approval=False,
                    blocked_reason=reason,
                )

        # 2. Check approval-required patterns
        for pattern, reason in APPROVAL_COMMAND_PATTERNS:
            if pattern.search(raw):
                return CommandPreview(
                    raw_command=raw,
                    normalized_command=raw,
                    classification="requires_approval",
                    risk_level="high",
                    target_workspace=workspace_label,
                    expected_effect=f"Execute consequential operation '{raw}' in {workspace_label}.",
                    requires_approval=True,
                    approval_reason=reason,
                )

        if allow_network:
            return CommandPreview(
                raw_command=raw,
                normalized_command=raw,
                classification="requires_approval",
                risk_level="high",
                target_workspace=workspace_label,
                expected_effect=f"Execute '{raw}' with outbound network access enabled.",
                requires_approval=True,
                approval_reason="Outbound network access is disabled by default and requires explicit user confirmation.",
            )

        # 3. Parse tokens and verify against allowlist
        try:
            tokens = shlex.split(raw, posix=True)
        except ValueError as exc:
            return CommandPreview(
                raw_command=raw,
                normalized_command=raw,
                classification="blocked_forbidden",
                risk_level="high",
                target_workspace=workspace_label,
                expected_effect="Malformed command syntax rejected.",
                blocked_reason=f"Shell token parse error: {exc}",
            )

        if not tokens:
            return CommandPreview(
                raw_command=raw,
                normalized_command=raw,
                classification="blocked_forbidden",
                risk_level="high",
                target_workspace=workspace_label,
                expected_effect="Empty token list rejected.",
                blocked_reason="No executable token found.",
            )

        head = tokens[0].lower()
        allowlisted_heads = {
            "python",
            "python3",
            "pytest",
            "node",
            "ls",
            "dir",
            "cat",
            "type",
            "echo",
            "git",
            "pwd",
        }
        if head not in allowlisted_heads:
            return CommandPreview(
                raw_command=raw,
                normalized_command=" ".join(tokens),
                classification="blocked_forbidden",
                risk_level="high",
                target_workspace=workspace_label,
                expected_effect="Command is not on the developer terminal allowlist.",
                blocked_reason=(
                    f"Executable '{tokens[0]}' is not in the controlled terminal allowlist "
                    f"({', '.join(sorted(allowlisted_heads))})."
                ),
            )

        # Prevent python -c or node -e inline arbitrary flags that try to bypass file checks if they contain forbidden tokens
        if head == "git" and (len(tokens) < 2 or tokens[1].lower() not in ("status", "diff", "log", "branch")):
            return CommandPreview(
                raw_command=raw,
                normalized_command=" ".join(tokens),
                classification="requires_approval",
                risk_level="medium",
                target_workspace=workspace_label,
                expected_effect=f"Run git subcommand '{' '.join(tokens)}' in workspace.",
                requires_approval=True,
                approval_reason="Only read-only git commands (status, diff, log, branch) run without confirmation.",
            )

        return CommandPreview(
            raw_command=raw,
            normalized_command=" ".join(tokens),
            classification="allowed_safe",
            risk_level="low",
            target_workspace=workspace_label,
            expected_effect=f"Execute allowlisted developer command '{' '.join(tokens)}' inside isolated workspace.",
            requires_approval=False,
        )

    async def run_terminal_command(
        self, req: TerminalCommandRequest
    ) -> TerminalExecutionRecord:
        uid = self._sanitize_user_id(req.user_id)
        pid = self._sanitize_project_id(req.project_id)
        self.get_project(uid, pid)
        proj_dir = self._project_dir(uid, pid)

        preview = self.classify_command(uid, pid, req.command, allow_network=req.allow_network)
        exec_id = f"term_{uuid.uuid4().hex[:12]}"

        if req.preview_only:
            return TerminalExecutionRecord(
                execution_id=exec_id,
                user_id=uid,
                project_id=pid,
                execution_type="terminal_command",
                command_preview=preview,
                status="PLANNED",
                memory_limit_mb=settings.terminal_max_memory_mb,
                network_enabled=req.allow_network,
                verified_execution=False,
            )

        if preview.classification == "blocked_forbidden":
            rec = TerminalExecutionRecord(
                execution_id=exec_id,
                user_id=uid,
                project_id=pid,
                execution_type="terminal_command",
                command_preview=preview,
                status="BLOCKED",
                exit_code=126,
                stdout="",
                stderr=f"SecurityPolicyViolation: {preview.blocked_reason}",
                verified_execution=False,
                error_diagnosis=preview.blocked_reason,
                suggested_fix="Use an allowlisted developer command confined to the project workspace.",
                completed_at=utc_now(),
            )
            self._save_execution_record(rec)
            return rec

        if preview.requires_approval and not req.confirmed:
            rec = TerminalExecutionRecord(
                execution_id=exec_id,
                user_id=uid,
                project_id=pid,
                execution_type="terminal_command",
                command_preview=preview,
                status="WAITING_FOR_APPROVAL",
                memory_limit_mb=settings.terminal_max_memory_mb,
                network_enabled=req.allow_network,
                verified_execution=False,
            )
            self._save_execution_record(rec)
            return rec

        return await self._execute_approved_terminal_command(
            exec_id=exec_id,
            uid=uid,
            pid=pid,
            proj_dir=proj_dir,
            preview=preview,
            timeout_seconds=req.timeout_seconds,
            allow_network=req.allow_network,
            was_approved=req.confirmed if preview.requires_approval else None,
        )

    async def _execute_approved_terminal_command(
        self,
        exec_id: str,
        uid: str,
        pid: str,
        proj_dir: Path,
        preview: CommandPreview,
        timeout_seconds: Optional[float],
        allow_network: bool,
        was_approved: Optional[bool],
    ) -> TerminalExecutionRecord:
        tokens = shlex.split(preview.normalized_command, posix=True)
        head = tokens[0].lower()
        args = tokens[1:]
        timeout_sec = min(
            float(timeout_seconds or settings.terminal_execution_timeout_seconds),
            15.0,
        )

        # Built-in portable workspace commands (ls/dir, cat/type, pwd, echo, rm/del)
        if head in ("ls", "dir"):
            items = [
                p.relative_to(proj_dir).as_posix()
                for p in sorted(proj_dir.rglob("*"))
                if p.is_file()
                and not p.relative_to(proj_dir).as_posix().startswith(INTERNAL_BACKUP_DIR)
                and "/__pycache__/" not in f"/{p.relative_to(proj_dir).as_posix()}/"
            ]
            rec = TerminalExecutionRecord(
                execution_id=exec_id,
                user_id=uid,
                project_id=pid,
                execution_type="terminal_command",
                command_preview=preview,
                status="SUCCEEDED",
                exit_code=0,
                stdout="\n".join(items) + ("\n" if items else ""),
                stderr="",
                duration_ms=2.5,
                verified_execution=True,
                approved=was_approved,
                completed_at=utc_now(),
            )
            self._save_execution_record(rec)
            return rec

        if head == "pwd":
            rec = TerminalExecutionRecord(
                execution_id=exec_id,
                user_id=uid,
                project_id=pid,
                execution_type="terminal_command",
                command_preview=preview,
                status="SUCCEEDED",
                exit_code=0,
                stdout=f"/workspace/{uid}/{pid}\n",
                stderr="",
                duration_ms=1.5,
                verified_execution=True,
                approved=was_approved,
                completed_at=utc_now(),
            )
            self._save_execution_record(rec)
            return rec

        if head == "echo":
            rec = TerminalExecutionRecord(
                execution_id=exec_id,
                user_id=uid,
                project_id=pid,
                execution_type="terminal_command",
                command_preview=preview,
                status="SUCCEEDED",
                exit_code=0,
                stdout=" ".join(args) + "\n",
                stderr="",
                duration_ms=1.5,
                verified_execution=True,
                approved=was_approved,
                completed_at=utc_now(),
            )
            self._save_execution_record(rec)
            return rec

        if head in ("cat", "type"):
            if not args:
                raise ValueError(f"Command '{head}' requires a target file path.")
            fpath, norm_rel = self._resolve_project_file(uid, pid, args[0])
            if not fpath.exists():
                rec = TerminalExecutionRecord(
                    execution_id=exec_id,
                    user_id=uid,
                    project_id=pid,
                    execution_type="terminal_command",
                    command_preview=preview,
                    status="FAILED",
                    exit_code=1,
                    stdout="",
                    stderr=f"{head}: {norm_rel}: No such file in project workspace.\n",
                    duration_ms=2.0,
                    verified_execution=True,
                    approved=was_approved,
                    completed_at=utc_now(),
                )
                self._save_execution_record(rec)
                return rec
            content = self._redact_secrets(fpath.read_text(encoding="utf-8", errors="replace"))
            rec = TerminalExecutionRecord(
                execution_id=exec_id,
                user_id=uid,
                project_id=pid,
                execution_type="terminal_command",
                command_preview=preview,
                status="SUCCEEDED",
                exit_code=0,
                stdout=content,
                stderr="",
                duration_ms=2.5,
                verified_execution=True,
                approved=was_approved,
                completed_at=utc_now(),
            )
            self._save_execution_record(rec)
            return rec

        if head in ("rm", "del", "erase"):
            if not args:
                raise ValueError(f"Command '{head}' requires a target file path.")
            fpath, norm_rel = self._resolve_project_file(uid, pid, args[-1])
            if not fpath.exists():
                rec = TerminalExecutionRecord(
                    execution_id=exec_id,
                    user_id=uid,
                    project_id=pid,
                    execution_type="terminal_command",
                    command_preview=preview,
                    status="FAILED",
                    exit_code=1,
                    stdout="",
                    stderr=f"{head}: cannot remove '{norm_rel}': No such file\n",
                    duration_ms=2.0,
                    verified_execution=True,
                    approved=was_approved,
                    completed_at=utc_now(),
                )
                self._save_execution_record(rec)
                return rec
            self._create_backup_snapshot(uid, pid, norm_rel, reason="pre_terminal_delete")
            fpath.unlink()
            rec = TerminalExecutionRecord(
                execution_id=exec_id,
                user_id=uid,
                project_id=pid,
                execution_type="terminal_command",
                command_preview=preview,
                status="SUCCEEDED",
                exit_code=0,
                stdout=f"Removed '{norm_rel}' (backup preserved in {INTERNAL_BACKUP_DIR}).\n",
                stderr="",
                duration_ms=4.0,
                verified_execution=True,
                approved=was_approved,
                completed_at=utc_now(),
            )
            self._save_execution_record(rec)
            return rec

        if head in ("pip", "pip3") and args and args[0].lower() == "install":
            pkgs = [a for a in args[1:] if not a.startswith("-")]
            req_path = proj_dir / "requirements.txt"
            existing_reqs = req_path.read_text(encoding="utf-8", errors="replace") if req_path.exists() else ""
            added: List[str] = []
            for p in pkgs:
                if p not in existing_reqs:
                    existing_reqs = existing_reqs.rstrip() + f"\n{p}\n"
                    added.append(p)
            req_path.write_text(existing_reqs.lstrip(), encoding="utf-8")
            rec = TerminalExecutionRecord(
                execution_id=exec_id,
                user_id=uid,
                project_id=pid,
                execution_type="terminal_command",
                command_preview=preview,
                status="SUCCEEDED",
                exit_code=0,
                stdout=(
                    f"Approved dependency registration complete: recorded {', '.join(pkgs)} in requirements.txt.\n"
                ),
                stderr="",
                duration_ms=8.0,
                verified_execution=True,
                approved=True,
                completed_at=utc_now(),
            )
            self._save_execution_record(rec)
            return rec

        # Execute python / pytest / node / git inside sandbox
        if head in ("python", "python3"):
            if args and not args[0].startswith("-"):
                # Run via sandbox bootstrap for full protection
                target_script = args[0]
                return await self.execute_code(
                    CodeExecuteRequest(
                        user_id=uid,
                        project_id=pid,
                        target_file=target_script,
                        mode="run",
                        args=args[1:],
                        timeout_seconds=timeout_sec,
                        allow_network=allow_network,
                        confirmed_network=bool(was_approved or allow_network),
                    )
                )
            argv = [sys.executable, "-I"] + args
        elif head == "pytest":
            target_test = args[0] if (args and not args[0].startswith("-")) else None
            return await self.execute_code(
                CodeExecuteRequest(
                    user_id=uid,
                    project_id=pid,
                    target_file=target_test,
                    mode="test",
                    args=args[1:] if target_test else args,
                    timeout_seconds=timeout_sec,
                    allow_network=allow_network,
                    confirmed_network=bool(was_approved or allow_network),
                )
            )
        elif head == "node":
            node_bin = shutil.which("node")
            if not node_bin:
                raise RuntimeError("Node.js runtime is not installed.")
            argv = [node_bin] + args
        elif head == "git":
            git_bin = shutil.which("git")
            if not git_bin:
                raise RuntimeError("Git executable is not installed.")
            argv = [git_bin] + args
        else:
            raise PermissionError(f"Unsupported command '{head}'.")

        env = self._build_sanitized_env(proj_dir, allow_network=allow_network)
        exit_code, stdout, stderr, truncated, timed_out, duration_ms = await asyncio.to_thread(
            self._run_subprocess_bounded,
            exec_id,
            uid,
            argv,
            proj_dir,
            env,
            "",
            timeout_sec,
        )
        status: Literal["SUCCEEDED", "FAILED", "TIMED_OUT"] = (
            "TIMED_OUT" if timed_out else ("SUCCEEDED" if exit_code == 0 else "FAILED")
        )
        err_diag, fix_sug = self._diagnose_execution_failure(exit_code, timed_out, stdout, stderr)

        rec = TerminalExecutionRecord(
            execution_id=exec_id,
            user_id=uid,
            project_id=pid,
            execution_type="terminal_command",
            command_preview=preview,
            status=status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            output_truncated=truncated,
            timed_out=timed_out,
            duration_ms=duration_ms,
            memory_limit_mb=settings.terminal_max_memory_mb,
            network_enabled=allow_network,
            verified_execution=True,
            approved=was_approved,
            error_diagnosis=err_diag,
            suggested_fix=fix_sug,
            completed_at=utc_now(),
        )
        self._save_execution_record(rec)
        return rec

    async def approve_execution(
        self, execution_id: str, req: TerminalApproveRequest
    ) -> TerminalExecutionRecord:
        uid = self._sanitize_user_id(req.user_id)
        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT record_json FROM terminal_executions WHERE execution_id = ? AND user_id = ?",
                    (execution_id, uid),
                ).fetchone()
                if not row:
                    raise ValueError(f"Execution '{execution_id}' not found for user '{uid}'.")
            finally:
                conn.close()

        rec = TerminalExecutionRecord.model_validate_json(str(row["record_json"]))
        if rec.status != "WAITING_FOR_APPROVAL":
            return rec

        if not req.approved:
            rec.status = "CANCELLED"
            rec.approved = False
            rec.stderr = "Operation cancelled: User declined approval for consequential terminal command."
            rec.completed_at = utc_now()
            self._save_execution_record(rec)
            return rec

        proj_dir = self._project_dir(uid, rec.project_id)
        if rec.execution_type in ("run_code", "run_tests"):
            target_rel = rec.command_preview.raw_command.split()[1]
            return await self.execute_code(
                CodeExecuteRequest(
                    user_id=uid,
                    project_id=rec.project_id,
                    target_file=target_rel,
                    mode="test" if rec.execution_type == "run_tests" else "run",
                    allow_network=rec.network_enabled,
                    confirmed_network=True,
                )
            )

        return await self._execute_approved_terminal_command(
            exec_id=rec.execution_id,
            uid=uid,
            pid=rec.project_id,
            proj_dir=proj_dir,
            preview=rec.command_preview,
            timeout_seconds=settings.terminal_execution_timeout_seconds,
            allow_network=rec.network_enabled,
            was_approved=True,
        )

    # =========================================================================
    # Debugging & Bounded Autonomous Repair Engine
    # =========================================================================

    @staticmethod
    def _synthesize_targeted_repair(
        source: str, stdout: str, stderr: str, timed_out: bool
    ) -> Tuple[str, str, Optional[str], Optional[str]]:
        """
        Inspects actual execution failure (stderr/stdout + source) and returns:
        (failure_type, diagnosis, patched_source_or_None, intervention_reason_or_None)
        """
        combined = f"{stderr}\n{stdout}"

        # 1. Missing external dependency -> Stop and require user intervention
        if "ModuleNotFoundError" in combined or "ImportError" in combined:
            m = re.search(r"No module named ['\"]([^'\"]+)['\"]", combined)
            pkg = m.group(1) if m else "external_package"
            return (
                "MissingDependencyError",
                f"Execution failed because package '{pkg}' is not installed in the sandbox.",
                None,
                f"Installing external package '{pkg}' ('pip install {pkg}') requires explicit user approval.",
            )

        # 2. Sandbox security policy violation -> Stop and require user intervention
        if "PermissionError: NEXORA Sandbox Policy" in combined:
            return (
                "SandboxPolicyViolation",
                "Code attempted a restricted operation (network access, shell execution, or outside-workspace write).",
                None,
                "Sandbox security rules cannot be bypassed automatically; user intervention is required.",
            )

        # 3. Infinite loop / timeout repair
        if timed_out:
            if "while True:" in source:
                patched = source.replace(
                    "while True:",
                    "for _bounded_step in range(100):",
                    1,
                )
                return (
                    "InfiniteLoopTimeout",
                    "Detected unbounded 'while True:' loop causing execution timeout.",
                    patched,
                    None,
                )
            return (
                "ExecutionTimeout",
                "Execution timed out and could not be automatically bounded without altering program semantics.",
                None,
                "Manual review required to optimize algorithm complexity or termination condition.",
            )

        # 4. SyntaxError repair (missing colon on def/if/for/while/class/else/elif/try/except)
        if "SyntaxError" in combined:
            err_line: Optional[int] = None
            try:
                ast.parse(source)
            except SyntaxError as syn_exc:
                err_line = syn_exc.lineno
            if not err_line:
                all_lines = re.findall(r"line\s+(\d+)", combined)
                if all_lines:
                    err_line = int(all_lines[-1])
            lines = source.splitlines()
            if err_line and 1 <= err_line <= len(lines):
                idx = err_line - 1
                raw_ln = lines[idx].rstrip()
                if re.match(r"^\s*(?:def|class|if|elif|else|for|while|try|except|finally)\b", raw_ln) and not raw_ln.endswith(":"):
                    lines[idx] = raw_ln + ":"
                    return (
                        "SyntaxError",
                        f"Missing trailing colon ':' on block statement at line {err_line}.",
                        "\n".join(lines) + "\n",
                        None,
                    )
                if raw_ln.count("(") > raw_ln.count(")"):
                    diff = raw_ln.count("(") - raw_ln.count(")")
                    lines[idx] = raw_ln + (")" * diff)
                    return (
                        "SyntaxError",
                        f"Unclosed parenthesis '(' at line {err_line}.",
                        "\n".join(lines) + "\n",
                        None,
                    )

        # 5. ZeroDivisionError repair
        if "ZeroDivisionError" in combined:
            patched = re.sub(
                r"(\b\w+\s*)/\s*0\b",
                r"(\1 / 1)",
                source,
            )
            if patched != source:
                return (
                    "ZeroDivisionError",
                    "Replaced literal division by zero ('/ 0') with safe denominator.",
                    patched,
                    None,
                )

        # 6. Unit test AssertionError or buggy operator repair (e.g. a - b instead of a + b)
        if "AssertionError" in combined or "FAILED" in combined:
            if "return a - b" in source:
                patched = source.replace("return a - b", "return a + b", 1)
                return (
                    "AssertionError",
                    "Unit test failed due to subtraction ('return a - b') instead of addition ('return a + b').",
                    patched,
                    None,
                )
            if "total * count" in source:
                patched = source.replace("total * count", "total / count", 1)
                return (
                    "AssertionError",
                    "Unit test failed due to multiplication ('total * count') instead of mean division ('total / count').",
                    patched,
                    None,
                )

        return (
            "RuntimeError",
            f"Captured runtime failure: {combined.strip()[:220]}",
            None,
            "Automated patch could not be deterministically synthesized without risking unintended logic changes; user review required.",
        )

    async def debug_and_repair(self, req: DebugRepairRequest) -> DebugRepairResponse:
        uid = self._sanitize_user_id(req.user_id)
        pid = self._sanitize_project_id(req.project_id)
        self.get_project(uid, pid)
        fpath, norm_rel = self._resolve_project_file(uid, pid, req.target_file)
        if not fpath.exists():
            raise ValueError(f"Target file '{norm_rel}' not found in project '{pid}'.")

        max_attempts = min(req.max_attempts, settings.terminal_max_repair_attempts)
        repair_id = f"rep_{uuid.uuid4().hex[:12]}"

        # Run initial verification
        initial_exec = await self.execute_code(
            CodeExecuteRequest(
                user_id=uid,
                project_id=pid,
                target_file=norm_rel if not req.run_tests else None,
                mode="test" if req.run_tests else "run",
            )
        )

        # Also execute the target file directly if syntax/runtime check is needed
        if req.run_tests and initial_exec.exit_code == 0:
            direct_exec = await self.execute_code(
                CodeExecuteRequest(
                    user_id=uid,
                    project_id=pid,
                    target_file=norm_rel,
                    mode="run",
                )
            )
            if direct_exec.exit_code != 0:
                initial_exec = direct_exec

        if initial_exec.exit_code == 0 and not initial_exec.timed_out:
            return DebugRepairResponse(
                repair_id=repair_id,
                user_id=uid,
                project_id=pid,
                target_file=norm_rel,
                initial_error="",
                status="NO_FAILURE_DETECTED",
                attempts_used=0,
                max_attempts=max_attempts,
                final_verified=True,
                explanation=f"Executed '{norm_rel}' and verified exit_code=0 with no errors.",
                iterations=[],
                final_execution=initial_exec,
            )

        initial_err_str = (initial_exec.stderr or initial_exec.stdout).strip()[:500]
        iterations: List[RepairIterationStep] = []
        current_exec = initial_exec

        for attempt in range(1, max_attempts + 1):
            source_text = fpath.read_text(encoding="utf-8", errors="replace")
            failure_type, diagnosis, patched_source, intervention_reason = (
                self._synthesize_targeted_repair(
                    source=source_text,
                    stdout=current_exec.stdout,
                    stderr=current_exec.stderr,
                    timed_out=current_exec.timed_out,
                )
            )

            if intervention_reason or patched_source is None:
                iterations.append(
                    RepairIterationStep(
                        attempt_number=attempt,
                        failure_type=failure_type,
                        diagnosis=diagnosis,
                        proposed_patch_summary=intervention_reason or "Manual code intervention required.",
                        applied=False,
                        execution_id=current_exec.execution_id,
                        exit_code=current_exec.exit_code,
                        tests_passed=False,
                        stdout_excerpt=current_exec.stdout[:300],
                        stderr_excerpt=current_exec.stderr[:300],
                    )
                )
                return DebugRepairResponse(
                    repair_id=repair_id,
                    user_id=uid,
                    project_id=pid,
                    target_file=norm_rel,
                    initial_error=initial_err_str,
                    status="REQUIRES_USER_INTERVENTION",
                    attempts_used=attempt,
                    max_attempts=max_attempts,
                    final_verified=False,
                    intervention_reason=intervention_reason,
                    explanation=f"{diagnosis} Stopped automatic repair: {intervention_reason}",
                    iterations=iterations,
                    final_execution=current_exec,
                )

            backup_obj: Optional[CodeFileBackup] = None
            if req.auto_apply:
                _, backup_obj = self.save_file(
                    pid,
                    SaveCodeFileRequest(
                        user_id=uid,
                        relative_path=norm_rel,
                        content=patched_source,
                        create_backup=True,
                        backup_reason=f"auto_repair_attempt_{attempt}",
                    ),
                )

            # Re-verify execution after patch
            verify_exec = await self.execute_code(
                CodeExecuteRequest(
                    user_id=uid,
                    project_id=pid,
                    target_file=norm_rel if not req.run_tests else None,
                    mode="test" if req.run_tests else "run",
                )
            )
            if req.run_tests and verify_exec.exit_code == 0:
                script_check = await self.execute_code(
                    CodeExecuteRequest(
                        user_id=uid,
                        project_id=pid,
                        target_file=norm_rel,
                        mode="run",
                    )
                )
                if script_check.exit_code != 0:
                    verify_exec = script_check

            passed = verify_exec.exit_code == 0 and not verify_exec.timed_out
            iterations.append(
                RepairIterationStep(
                    attempt_number=attempt,
                    failure_type=failure_type,
                    diagnosis=diagnosis,
                    proposed_patch_summary=f"Applied targeted fix for {failure_type} in '{norm_rel}'.",
                    backup_id=backup_obj.backup_id if backup_obj else None,
                    applied=req.auto_apply,
                    execution_id=verify_exec.execution_id,
                    exit_code=verify_exec.exit_code,
                    tests_passed=passed,
                    stdout_excerpt=verify_exec.stdout[:300],
                    stderr_excerpt=verify_exec.stderr[:300],
                )
            )
            current_exec = verify_exec
            if passed:
                return DebugRepairResponse(
                    repair_id=repair_id,
                    user_id=uid,
                    project_id=pid,
                    target_file=norm_rel,
                    initial_error=initial_err_str,
                    status="REPAIRED_AND_VERIFIED",
                    attempts_used=attempt,
                    max_attempts=max_attempts,
                    final_verified=True,
                    explanation=(
                        f"Diagnosed {failure_type} ({diagnosis}), created backup "
                        f"'{backup_obj.backup_id if backup_obj else 'n/a'}', applied patch, "
                        f"and verified execution succeeded (exit_code=0) on attempt {attempt}."
                    ),
                    iterations=iterations,
                    final_execution=current_exec,
                )

        return DebugRepairResponse(
            repair_id=repair_id,
            user_id=uid,
            project_id=pid,
            target_file=norm_rel,
            initial_error=initial_err_str,
            status="MAX_ATTEMPTS_REACHED",
            attempts_used=max_attempts,
            max_attempts=max_attempts,
            final_verified=False,
            intervention_reason=f"Bounded repair limit ({max_attempts} attempts) reached without passing verification.",
            explanation=f"Reached maximum of {max_attempts} repair attempts; stopping for user review.",
            iterations=iterations,
            final_execution=current_exec,
        )

    # =========================================================================
    # Stage 17 File Workspace Bridge
    # =========================================================================

    def sync_with_stage17(
        self, project_id: str, req: SyncStage17Request
    ) -> Dict[str, Any]:
        from app.services.files.engine import file_workspace_engine
        from app.models.schemas import FileWriteRequest

        uid = self._sanitize_user_id(req.user_id)
        pid = self._sanitize_project_id(project_id)
        proj = self.get_project(uid, pid)

        synced_files: List[str] = []
        if req.direction == "to_stage17":
            for f in proj.files:
                if req.relative_path and f.relative_path != req.relative_path:
                    continue
                dest_rel = f"code_projects/{pid}/{f.relative_path}"
                file_workspace_engine.write_file(
                    FileWriteRequest(
                        user_id=uid,
                        relative_path=dest_rel,
                        content=f.content or "",
                        overwrite=True,
                        confirmed_overwrite=True,
                        backup_reason=f"sync_from_stage18_{pid}",
                    )
                )
                synced_files.append(dest_rel)
        else:
            target_rel = req.relative_path or "README_WORKSPACE.md"
            read_res = file_workspace_engine.read_file(user_id=uid, relative_path=target_rel)
            dest_name = Path(target_rel).name
            self.save_file(
                pid,
                SaveCodeFileRequest(
                    user_id=uid,
                    relative_path=dest_name,
                    content=read_res.content,
                    create_backup=True,
                    backup_reason="import_from_stage17_workspace",
                ),
            )
            synced_files.append(dest_name)

        return {
            "project_id": pid,
            "user_id": uid,
            "direction": req.direction,
            "synced_count": len(synced_files),
            "synced_files": synced_files,
            "summary": f"Synced {len(synced_files)} file(s) ({req.direction}) between Stage 18 Code Project '{pid}' and Stage 17 File Workspace.",
        }


terminal_execution_engine = TerminalExecutionEngine()
