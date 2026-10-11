"""
NEXORA AI — Stage 19: Git & Version Control Engine

Provides:
- Genuine Git repository detection, validation, and initialization inside authorized Stage 18 developer workspaces
- Repository status inspection: current branch, local/remote branches, staged/unstaged/untracked files, secret warnings, recommended .gitignore rules, and recent commit log
- Staging, unstaging, diff inspection (both unified patch and structured side-by-side line hunks), and commit history browsing
- Safe Change Management: pre-commit diff preview, secret & .env file blocking, dirty-worktree guard before branch switches, force-push blocking, and explicit user confirmation (WAITING_FOR_APPROVAL) before commits, merges, pushes, or destructive resets
- AI-Powered Code Review: analyzes changed files for bugs, security weaknesses, readability issues, and missing tests; distinguishes 'verified_defect' from 'possible_concern' and integrates with Stage 18 unit test execution
- Collaboration & Remote Integration: branch comparison with conflict detection, configurable remotes (GitHub, GitLab, Bitbucket, Custom), honest separation of local PR drafts (LOCAL_DRAFT_ONLY) from provider-confirmed remote actions
"""

from __future__ import annotations

import ast
import asyncio
import json
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
from urllib.parse import urlparse

from app.config import settings
from app.models.schemas import (
    CodeExecuteRequest,
    GitApproveOperationRequest,
    GitBranchActionRequest,
    GitBranchComparisonResponse,
    GitBranchInfo,
    GitChangedFile,
    GitCodeReviewFinding,
    GitCodeReviewResponse,
    GitCommitEntry,
    GitCommitRequest,
    GitDiffResponse,
    GitFileDiff,
    GitInitRequest,
    GitOperationRecord,
    GitPullRequestCreateRequest,
    GitPullRequestRecord,
    GitRemoteConfig,
    GitRemoteConfigRequest,
    GitRemoteProvider,
    GitRemoteSyncRequest,
    GitRepositoryStatusResponse,
    GitReviewRequest,
    GitSideBySideLine,
    GitStageRequest,
    utc_now,
)
from app.services.terminal.engine import (
    INTERNAL_BACKUP_DIR,
    INTERNAL_SANDBOX_FILE,
    terminal_execution_engine,
)

RECOMMENDED_GITIGNORE_RULES = [
    "# Nexora AI Recommended .gitignore",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_ed25519",
    "__pycache__/",
    "*.py[cod]",
    ".pytest_cache/",
    "node_modules/",
    "dist/",
    f"{INTERNAL_BACKUP_DIR}/",
    INTERNAL_SANDBOX_FILE,
]

SENSITIVE_ENV_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "secrets.yaml",
}

SENSITIVE_EXTENSIONS = {".pem", ".key", ".pfx", ".p12"}

SECRET_SCAN_PATTERNS = [
    (re.compile(r"AIza[0-9A-Za-z\-_]{20,}"), "Google Gemini API key pattern ('AIza...') detected."),
    (re.compile(r"sk-[0-9A-Za-z\-_]{20,}"), "OpenAI/Anthropic secret key pattern ('sk-...') detected."),
    (re.compile(r"gh[pousr]_[0-9A-Za-z]{20,}"), "GitHub Personal Access Token ('ghp_/gho_...') detected."),
    (re.compile(r"glpat-[0-9A-Za-z\-_]{16,}"), "GitLab Personal Access Token ('glpat-...') detected."),
    (re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |PRIVATE )?KEY-----"), "Private cryptographic key block detected."),
    (
        re.compile(r"(?i)(?:api[_-]?key|secret[_-]?key|access[_-]?token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{12,}['\"]"),
        "Hardcoded credential/secret assignment detected.",
    ),
]

VALID_BRANCH_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._/\-]{0,98}$")
VALID_REMOTE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._\-]{0,48}$")


class GitVersionControlEngine:
    """
    Stage 19: Permission-Controlled Git & Version Control Engine.
    Executes real git operations confined to Stage 18 developer workspaces.
    """

    def __init__(self) -> None:
        self._db_path = Path(settings.git_db_path).resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        # Optional override used only by unit tests to verify missing-git behavior
        self._git_binary_override: Optional[str] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS git_operations (
                        operation_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        record_json TEXT NOT NULL,
                        pending_payload_json TEXT,
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS git_pull_requests (
                        pr_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        record_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS git_reviews (
                        review_id TEXT PRIMARY KEY,
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
    # Git Binary & Subprocess Execution Helper
    # =========================================================================

    def _resolve_git_binary(self) -> Optional[str]:
        if self._git_binary_override == "__MISSING__":
            return None
        if self._git_binary_override:
            return self._git_binary_override
        return shutil.which("git")

    def _project_root(self, user_id: str, project_id: str) -> Tuple[str, str, Path]:
        uid = terminal_execution_engine._sanitize_user_id(user_id)
        terminal_execution_engine._ensure_default_project(uid)
        pid = terminal_execution_engine._sanitize_project_id(project_id)
        # Verify project exists for user
        terminal_execution_engine.get_project(uid, pid)
        proj_dir = terminal_execution_engine._project_dir(uid, pid)
        return uid, pid, proj_dir

    def _validate_branch_name(self, branch_name: str) -> str:
        b = (branch_name or "").strip()
        if (
            not b
            or b.startswith("-")
            or ".." in b
            or "//" in b
            or b.endswith(".lock")
            or not VALID_BRANCH_NAME_RE.match(b)
        ):
            raise ValueError(
                f"Invalid Git branch name '{branch_name}'. Branch names must be alphanumeric and cannot start with '-' or contain '..'."
            )
        return b

    def _validate_remote_url(self, url: str) -> Tuple[str, GitRemoteProvider]:
        raw = (url or "").strip()
        if not raw or "\x00" in raw or raw.startswith("-"):
            raise ValueError("Invalid remote URL.")

        # Support SSH format git@github.com:org/repo.git
        ssh_m = re.match(r"^git@([a-zA-Z0-9.\-]+):([a-zA-Z0-9._/\-]+)$", raw)
        if ssh_m:
            host = ssh_m.group(1).lower()
            path_part = ssh_m.group(2)
            if ".." in path_part:
                raise ValueError("Path traversal in remote repository path is forbidden.")
            provider = self._detect_provider_from_host(host)
            return raw, provider

        parsed = urlparse(raw)
        if parsed.scheme not in ("https", "http"):
            raise ValueError(
                f"Unsupported remote URL scheme '{parsed.scheme}'. Only 'https://' or 'git@<host>:<org>/<repo>.git' remotes are allowed."
            )
        host = (parsed.hostname or "").lower()
        if not host or host in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or host.startswith("169.254.") or host.startswith("10.") or host.startswith("192.168."):
            raise ValueError(f"Remote host '{host}' is blocked by SSRF/loopback security policy.")
        if ".." in (parsed.path or "") or not parsed.path or parsed.path == "/":
            raise ValueError("Remote URL must include a valid repository path (e.g. https://github.com/org/repo.git).")
        provider = self._detect_provider_from_host(host)
        return raw, provider

    @staticmethod
    def _detect_provider_from_host(host: str) -> GitRemoteProvider:
        if "github.com" in host:
            return "github"
        if "gitlab.com" in host:
            return "gitlab"
        if "bitbucket.org" in host:
            return "bitbucket"
        return "custom"

    def _run_git(
        self,
        proj_dir: Path,
        args: List[str],
        timeout: Optional[float] = None,
    ) -> Tuple[int, str, str]:
        git_bin = self._resolve_git_binary()
        if not git_bin:
            raise RuntimeError(
                "GitUnavailableError: 'git' executable is not installed or not found on PATH in the host environment."
            )

        # Prevent dangerous git protocol overrides
        for arg in args:
            if arg.startswith("--upload-pack") or arg.startswith("--receive-pack") or arg.startswith("--exec"):
                raise PermissionError(f"Forbidden Git option '{arg}' blocked by sandbox security policy.")

        safe_env = terminal_execution_engine._build_sanitized_env(proj_dir, allow_network=False)
        safe_env["GIT_TERMINAL_PROMPT"] = "0"
        safe_env["GIT_AUTHOR_NAME"] = settings.git_default_author_name
        safe_env["GIT_AUTHOR_EMAIL"] = settings.git_default_author_email
        safe_env["GIT_COMMITTER_NAME"] = settings.git_default_author_name
        safe_env["GIT_COMMITTER_EMAIL"] = settings.git_default_author_email

        proc = subprocess.run(
            [git_bin] + args,
            cwd=str(proj_dir),
            env=safe_env,
            capture_output=True,
            text=False,
            timeout=timeout or settings.git_command_timeout_seconds,
            check=False,
        )
        stdout = terminal_execution_engine._redact_secrets(
            proc.stdout.decode("utf-8", errors="replace")
        )
        stderr = terminal_execution_engine._redact_secrets(
            proc.stderr.decode("utf-8", errors="replace")
        )
        return int(proc.returncode), stdout, stderr

    def _is_git_repo(self, proj_dir: Path) -> bool:
        if not (proj_dir / ".git").exists():
            return False
        try:
            code, out, _ = self._run_git(proj_dir, ["rev-parse", "--is-inside-work-tree"])
            return code == 0 and out.strip().lower() == "true"
        except Exception:
            return False

    # =========================================================================
    # Secret & Sensitive File Detection
    # =========================================================================

    def _scan_file_for_secrets(self, proj_dir: Path, rel_path: str) -> Tuple[bool, bool, Optional[str]]:
        """
        Returns (is_sensitive_env_file, has_secret_warning, secret_warning_detail).
        """
        fname = Path(rel_path).name.lower()
        ext = Path(rel_path).suffix.lower()
        is_env = fname in SENSITIVE_ENV_FILENAMES or fname.startswith(".env.") or ext in SENSITIVE_EXTENSIONS
        if is_env:
            return (
                True,
                True,
                f"File '{rel_path}' is an environment/credential file and must not be committed to version control.",
            )

        fpath = (proj_dir / rel_path).resolve()
        if not str(fpath).startswith(str(proj_dir)) or not fpath.exists() or not fpath.is_file():
            return False, False, None

        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return False, False, None

        for pattern, msg in SECRET_SCAN_PATTERNS:
            if pattern.search(content):
                return False, True, f"{rel_path}: {msg}"
        return False, False, None

    def _scan_text_for_secrets(self, text: str, label: str = "diff") -> List[str]:
        warnings: List[str] = []
        for pattern, msg in SECRET_SCAN_PATTERNS:
            if pattern.search(text or ""):
                warnings.append(f"[{label}] {msg}")
        return warnings

    # =========================================================================
    # Operation Persistence
    # =========================================================================

    def _save_operation(
        self,
        record: GitOperationRecord,
        pending_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO git_operations
                    (operation_id, user_id, project_id, record_json, pending_payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.operation_id,
                        record.user_id,
                        record.project_id,
                        record.model_dump_json(),
                        json.dumps(pending_payload) if pending_payload else None,
                        record.created_at.isoformat(),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def list_operations(
        self, user_id: str, project_id: Optional[str] = None, limit: int = 30
    ) -> List[GitOperationRecord]:
        uid = terminal_execution_engine._sanitize_user_id(user_id)
        with self._lock:
            conn = self._get_conn()
            try:
                if project_id:
                    pid = terminal_execution_engine._sanitize_project_id(project_id)
                    rows = conn.execute(
                        "SELECT record_json FROM git_operations WHERE user_id = ? AND project_id = ? ORDER BY created_at DESC LIMIT ?",
                        (uid, pid, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT record_json FROM git_operations WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                        (uid, limit),
                    ).fetchall()
            finally:
                conn.close()
        return [GitOperationRecord.model_validate_json(str(r["record_json"])) for r in rows]

    # =========================================================================
    # Capabilities & Repository Status Inspection
    # =========================================================================

    def get_capabilities(self, user_id: str = "default_user") -> Dict[str, Any]:
        git_bin = self._resolve_git_binary()
        git_version: Optional[str] = None
        if git_bin:
            try:
                res = subprocess.run(
                    [git_bin, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=3.0,
                    check=False,
                )
                if res.returncode == 0:
                    git_version = res.stdout.strip()
            except Exception:
                git_version = None

        return {
            "stage": 19,
            "engine": "GitVersionControlEngine",
            "git_installed": git_bin is not None and git_version is not None,
            "git_version": git_version,
            "default_branch": settings.git_default_branch,
            "supported_providers": ["github", "gitlab", "bitbucket", "custom"],
            "remote_token_configured": bool(settings.git_provider_token.strip()),
            "allowed_remote_hosts": settings.git_allowed_remote_hosts,
            "approval_required_operations": [
                "commit",
                "merge_branch",
                "sync_remote (push/pull)",
                "discard_changes",
                "create_pull_request (remote submission)",
            ],
            "recommended_gitignore_rules": RECOMMENDED_GITIGNORE_RULES,
        }

    def get_status(
        self, user_id: str = "default_user", project_id: str = "proj_default_py"
    ) -> GitRepositoryStatusResponse:
        uid, pid, proj_dir = self._project_root(user_id, project_id)
        git_bin = self._resolve_git_binary()
        if not git_bin:
            return GitRepositoryStatusResponse(
                project_id=pid,
                user_id=uid,
                git_installed=False,
                is_initialized=False,
                current_branch=settings.git_default_branch,
                is_clean=True,
                recommended_gitignore_entries=RECOMMENDED_GITIGNORE_RULES,
            )

        if not self._is_git_repo(proj_dir):
            return GitRepositoryStatusResponse(
                project_id=pid,
                user_id=uid,
                git_installed=True,
                is_initialized=False,
                current_branch=settings.git_default_branch,
                is_clean=True,
                gitignore_present=(proj_dir / ".gitignore").exists(),
                recommended_gitignore_entries=RECOMMENDED_GITIGNORE_RULES,
            )

        # Current branch
        _, br_out, _ = self._run_git(proj_dir, ["branch", "--show-current"])
        current_branch = br_out.strip() or settings.git_default_branch

        # Branches list
        branches: List[GitBranchInfo] = []
        code_b, b_out, _ = self._run_git(
            proj_dir,
            ["for-each-ref", "--format=%(refname:short)|%(objectname:short)|%(subject)", "refs/heads/"],
        )
        if code_b == 0:
            for line in b_out.splitlines():
                if not line.strip():
                    continue
                parts = line.split("|", 2)
                b_name = parts[0].strip()
                b_hash = parts[1].strip() if len(parts) > 1 else ""
                b_subj = parts[2].strip() if len(parts) > 2 else ""
                branches.append(
                    GitBranchInfo(
                        name=b_name,
                        is_current=(b_name == current_branch),
                        commit_hash=b_hash,
                        last_commit_subject=b_subj,
                    )
                )

        # Porcelain status
        _, st_out, _ = self._run_git(proj_dir, ["status", "--porcelain=v1", "-uall"])
        changed_files: List[GitChangedFile] = []
        secret_warnings: List[str] = []
        staged_count = 0
        unstaged_count = 0
        untracked_count = 0

        for line in st_out.splitlines():
            if len(line) < 4:
                continue
            idx_st = line[0]
            wt_st = line[1]
            raw_path = line[3:].strip()
            if " -> " in raw_path:
                raw_path = raw_path.split(" -> ")[-1].strip()
            raw_path = raw_path.strip('"')
            if raw_path.startswith(INTERNAL_BACKUP_DIR) or raw_path == INTERNAL_SANDBOX_FILE:
                continue

            is_untracked = idx_st == "?" and wt_st == "?"
            is_staged = idx_st not in (" ", "?")
            is_unstaged = wt_st not in (" ", "?")

            if is_untracked:
                untracked_count += 1
            if is_staged:
                staged_count += 1
            if is_unstaged:
                unstaged_count += 1

            is_env, has_sec, sec_detail = self._scan_file_for_secrets(proj_dir, raw_path)
            if has_sec and sec_detail:
                secret_warnings.append(sec_detail)

            changed_files.append(
                GitChangedFile(
                    path=raw_path,
                    index_status=idx_st,
                    worktree_status=wt_st,
                    staged=is_staged,
                    unstaged=is_unstaged,
                    untracked=is_untracked,
                    has_secret_warning=has_sec,
                    secret_warning_detail=sec_detail,
                    is_sensitive_env_file=is_env,
                )
            )

        # Remotes
        remotes: List[GitRemoteConfig] = []
        _, rem_out, _ = self._run_git(proj_dir, ["remote", "-v"])
        seen_remotes: Dict[str, str] = {}
        for line in rem_out.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                seen_remotes[parts[0]] = parts[1]

        token_present = bool(settings.git_provider_token.strip())
        for r_name, r_url in seen_remotes.items():
            prov = self._detect_provider_from_host(r_url.lower())
            if not token_present:
                sync_st: Literal[
                    "not_configured",
                    "local_only",
                    "auth_required",
                    "network_disabled",
                    "ready_to_sync",
                    "synced",
                    "sync_failed",
                ] = "auth_required"
            elif not settings.terminal_default_allow_network:
                sync_st = "network_disabled"
            else:
                sync_st = "ready_to_sync"
            remotes.append(
                GitRemoteConfig(
                    name=r_name,
                    url=r_url,
                    provider=prov,
                    token_configured=token_present,
                    sync_status=sync_st,
                )
            )

        recent_commits = self.list_commits(uid, pid, limit=15)
        gitignore_path = proj_dir / ".gitignore"
        existing_ignore = (
            gitignore_path.read_text(encoding="utf-8", errors="replace")
            if gitignore_path.exists()
            else ""
        )
        missing_rules = [
            rule
            for rule in RECOMMENDED_GITIGNORE_RULES
            if not rule.startswith("#") and rule not in existing_ignore
        ]

        return GitRepositoryStatusResponse(
            project_id=pid,
            user_id=uid,
            git_installed=True,
            is_initialized=True,
            current_branch=current_branch,
            is_clean=(len(changed_files) == 0),
            branches=branches,
            changed_files=changed_files,
            staged_count=staged_count,
            unstaged_count=unstaged_count,
            untracked_count=untracked_count,
            secret_warnings=secret_warnings,
            recommended_gitignore_entries=missing_rules,
            gitignore_present=gitignore_path.exists(),
            remotes=remotes,
            recent_commits=recent_commits,
        )

    # =========================================================================
    # Repository Initialization, Staging, Unstaging & .gitignore
    # =========================================================================

    def init_repository(self, req: GitInitRequest) -> GitOperationRecord:
        uid, pid, proj_dir = self._project_root(req.user_id, req.project_id)
        op_id = f"gitop_{uuid.uuid4().hex[:12]}"
        branch = self._validate_branch_name(req.default_branch or settings.git_default_branch)

        if not self._resolve_git_binary():
            rec = GitOperationRecord(
                operation_id=op_id,
                user_id=uid,
                project_id=pid,
                operation_type="init_repo",
                status="FAILED",
                command_display=f"git init -b {branch}",
                verified=False,
                error_message="Git executable is not installed or unavailable on PATH.",
                completed_at=utc_now(),
            )
            self._save_operation(rec)
            return rec

        if req.create_gitignore:
            gitignore_file = proj_dir / ".gitignore"
            existing = (
                gitignore_file.read_text(encoding="utf-8", errors="replace")
                if gitignore_file.exists()
                else ""
            )
            merged_lines = existing.splitlines() if existing else []
            for r in RECOMMENDED_GITIGNORE_RULES:
                if r not in merged_lines:
                    merged_lines.append(r)
            gitignore_file.write_text("\n".join(merged_lines).strip() + "\n", encoding="utf-8")

        code, out, err = self._run_git(proj_dir, ["init", "-b", branch])
        if code != 0:
            # Fallback for older git versions without -b
            code, out, err = self._run_git(proj_dir, ["init"])
            if code == 0:
                self._run_git(proj_dir, ["checkout", "-B", branch])

        author_name = (req.author_name or settings.git_default_author_name).strip()
        author_email = (req.author_email or settings.git_default_author_email).strip()
        self._run_git(proj_dir, ["config", "user.name", author_name])
        self._run_git(proj_dir, ["config", "user.email", author_email])

        commit_out = ""
        if code == 0 and req.initial_commit:
            # Stage safe project files
            self._run_git(proj_dir, ["add", "."])
            _, c_out, c_err = self._run_git(
                proj_dir, ["commit", "-m", "Initial commit: Nexora Stage 19 workspace baseline"]
            )
            commit_out = f"\n{c_out}\n{c_err}".strip()

        verified = self._is_git_repo(proj_dir)
        rec = GitOperationRecord(
            operation_id=op_id,
            user_id=uid,
            project_id=pid,
            operation_type="init_repo",
            status="SUCCEEDED" if verified and code == 0 else "FAILED",
            command_display=f"git init -b {branch}",
            verified=verified,
            stdout=(out + "\n" + commit_out).strip(),
            stderr=err,
            error_message=None if verified else (err or "Failed to verify .git repository."),
            completed_at=utc_now(),
        )
        self._save_operation(rec)
        return rec

    def stage_files(self, req: GitStageRequest) -> GitOperationRecord:
        uid, pid, proj_dir = self._project_root(req.user_id, req.project_id)
        op_id = f"gitop_{uuid.uuid4().hex[:12]}"
        if not self._is_git_repo(proj_dir):
            raise ValueError(f"Project '{pid}' is not an initialized Git repository.")

        target_paths: List[str] = []
        secret_warnings: List[str] = []

        if req.stage_all:
            status = self.get_status(uid, pid)
            target_paths = [f.path for f in status.changed_files]
            if (proj_dir / ".gitignore").exists() and ".gitignore" not in target_paths:
                target_paths.append(".gitignore")
        else:
            for p in req.paths:
                clean_p = p.strip().replace("\\", "/")
                if not clean_p or ".." in clean_p or clean_p.startswith("/") or clean_p.startswith("-"):
                    raise PermissionError(f"Invalid or unsafe path '{p}' rejected.")
                target_paths.append(clean_p)

        for rel_p in target_paths:
            is_env, has_sec, sec_detail = self._scan_file_for_secrets(proj_dir, rel_p)
            if (is_env or has_sec) and sec_detail:
                secret_warnings.append(sec_detail)

        if secret_warnings and not req.allow_sensitive:
            rec = GitOperationRecord(
                operation_id=op_id,
                user_id=uid,
                project_id=pid,
                operation_type="stage_files",
                status="BLOCKED",
                command_display=f"git add -- {' '.join(target_paths)}",
                verified=False,
                secret_warnings=secret_warnings,
                stderr="Blocked staging of sensitive environment or secret-containing files.",
                error_message="Secret protection blocked staging sensitive files: " + "; ".join(secret_warnings),
                completed_at=utc_now(),
            )
            self._save_operation(rec)
            return rec

        if not target_paths:
            rec = GitOperationRecord(
                operation_id=op_id,
                user_id=uid,
                project_id=pid,
                operation_type="stage_files",
                status="SUCCEEDED",
                command_display="git add (no modified files)",
                verified=True,
                stdout="Working tree is already clean; nothing to stage.",
                completed_at=utc_now(),
            )
            self._save_operation(rec)
            return rec

        code, out, err = self._run_git(proj_dir, ["add", "--"] + target_paths)
        rec = GitOperationRecord(
            operation_id=op_id,
            user_id=uid,
            project_id=pid,
            operation_type="stage_files",
            status="SUCCEEDED" if code == 0 else "FAILED",
            command_display=f"git add -- {' '.join(target_paths)}",
            verified=(code == 0),
            stdout=out or f"Staged {len(target_paths)} file(s): {', '.join(target_paths)}",
            stderr=err,
            secret_warnings=secret_warnings,
            error_message=None if code == 0 else err,
            completed_at=utc_now(),
        )
        self._save_operation(rec)
        return rec

    def unstage_files(self, req: GitStageRequest) -> GitOperationRecord:
        uid, pid, proj_dir = self._project_root(req.user_id, req.project_id)
        op_id = f"gitop_{uuid.uuid4().hex[:12]}"
        if not self._is_git_repo(proj_dir):
            raise ValueError(f"Project '{pid}' is not an initialized Git repository.")

        args = ["reset", "HEAD"]
        if not req.stage_all and req.paths:
            for p in req.paths:
                if ".." in p or p.startswith("-"):
                    raise PermissionError(f"Invalid path '{p}'.")
            args.extend(["--"] + req.paths)

        code, out, err = self._run_git(proj_dir, args)
        rec = GitOperationRecord(
            operation_id=op_id,
            user_id=uid,
            project_id=pid,
            operation_type="unstage_files",
            status="SUCCEEDED" if code == 0 else "FAILED",
            command_display="git " + " ".join(args),
            verified=(code == 0),
            stdout=out or "Unstaged selected changes.",
            stderr=err,
            completed_at=utc_now(),
        )
        self._save_operation(rec)
        return rec

    # =========================================================================
    # Unified & Side-by-Side Diff Engine
    # =========================================================================

    @staticmethod
    def _parse_unified_diff_to_files(raw_diff: str) -> List[GitFileDiff]:
        files: List[GitFileDiff] = []
        if not raw_diff.strip():
            return files

        chunks = re.split(r"(?=^diff --git )", raw_diff, flags=re.MULTILINE)
        for chunk in chunks:
            if not chunk.strip().startswith("diff --git"):
                continue
            lines = chunk.splitlines()
            header = lines[0]
            m = re.search(r" b/(.+)$", header)
            file_path = m.group(1).strip().strip('"') if m else "unknown_file"
            is_binary = any(ln.startswith("Binary files ") for ln in lines[:6])

            additions = 0
            deletions = 0
            sbs_lines: List[GitSideBySideLine] = []
            left_no = 1
            right_no = 1

            for ln in lines:
                if ln.startswith("@@"):
                    hunk_m = re.search(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", ln)
                    if hunk_m:
                        left_no = int(hunk_m.group(1))
                        right_no = int(hunk_m.group(2))
                    continue
                if ln.startswith(("diff --git", "index ", "--- ", "+++ ", "new file mode", "deleted file mode")):
                    continue
                if ln.startswith("+"):
                    additions += 1
                    sbs_lines.append(
                        GitSideBySideLine(
                            left_line_no=None,
                            left_content="",
                            right_line_no=right_no,
                            right_content=ln[1:],
                            change_type="add",
                        )
                    )
                    right_no += 1
                elif ln.startswith("-"):
                    deletions += 1
                    sbs_lines.append(
                        GitSideBySideLine(
                            left_line_no=left_no,
                            left_content=ln[1:],
                            right_line_no=None,
                            right_content="",
                            change_type="delete",
                        )
                    )
                    left_no += 1
                elif ln.startswith(" "):
                    sbs_lines.append(
                        GitSideBySideLine(
                            left_line_no=left_no,
                            left_content=ln[1:],
                            right_line_no=right_no,
                            right_content=ln[1:],
                            change_type="context",
                        )
                    )
                    left_no += 1
                    right_no += 1

            files.append(
                GitFileDiff(
                    file_path=file_path,
                    additions=additions,
                    deletions=deletions,
                    is_binary=is_binary,
                    unified_patch=chunk,
                    side_by_side_lines=sbs_lines,
                )
            )
        return files

    def get_diff(
        self,
        user_id: str,
        project_id: str,
        scope: Literal["unstaged", "staged", "all_working", "branch_compare", "commit"] = "all_working",
        base_ref: Optional[str] = None,
        compare_ref: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> GitDiffResponse:
        uid, pid, proj_dir = self._project_root(user_id, project_id)
        if not self._is_git_repo(proj_dir):
            return GitDiffResponse(project_id=pid, target_scope=scope)

        args = ["diff"]
        if scope == "staged":
            args.append("--cached")
        elif scope == "all_working":
            # Compare against HEAD if HEAD exists, otherwise --cached
            code_h, _, _ = self._run_git(proj_dir, ["rev-parse", "--verify", "HEAD"])
            if code_h == 0:
                args.append("HEAD")
            else:
                args.append("--cached")
        elif scope == "branch_compare" and base_ref and compare_ref:
            b1 = self._validate_branch_name(base_ref)
            b2 = self._validate_branch_name(compare_ref)
            args.append(f"{b1}...{b2}")
        elif scope == "commit" and base_ref:
            b1 = self._validate_branch_name(base_ref)
            args = ["show", "--format=", b1]

        if file_path:
            if ".." in file_path or file_path.startswith("-"):
                raise PermissionError("Invalid diff file_path.")
            args.extend(["--", file_path])

        _, diff_out, _ = self._run_git(proj_dir, args)
        file_diffs = self._parse_unified_diff_to_files(diff_out)
        total_add = sum(f.additions for f in file_diffs)
        total_del = sum(f.deletions for f in file_diffs)
        sec_warnings = self._scan_text_for_secrets(diff_out, label="git_diff")

        return GitDiffResponse(
            project_id=pid,
            target_scope=scope,
            base_ref=base_ref,
            compare_ref=compare_ref,
            total_files_changed=len(file_diffs),
            total_additions=total_add,
            total_deletions=total_del,
            unified_diff=diff_out,
            files=file_diffs,
            secret_warnings=sec_warnings,
        )

    # =========================================================================
    # Safe Commits & Commit History Inspection
    # =========================================================================

    def commit_changes(self, req: GitCommitRequest) -> GitOperationRecord:
        uid, pid, proj_dir = self._project_root(req.user_id, req.project_id)
        op_id = f"gitop_{uuid.uuid4().hex[:12]}"
        if not self._is_git_repo(proj_dir):
            raise ValueError(f"Project '{pid}' is not an initialized Git repository.")

        if req.stage_all:
            st_op = self.stage_files(
                GitStageRequest(
                    user_id=uid,
                    project_id=pid,
                    stage_all=True,
                    allow_sensitive=req.allow_secret_override,
                )
            )
            if st_op.status == "BLOCKED":
                st_op.operation_type = "commit"
                self._save_operation(st_op)
                return st_op

        staged_diff = self.get_diff(uid, pid, scope="staged")
        status = self.get_status(uid, pid)
        staged_files = [f for f in status.changed_files if f.staged]

        if not staged_files and staged_diff.total_files_changed == 0:
            rec = GitOperationRecord(
                operation_id=op_id,
                user_id=uid,
                project_id=pid,
                operation_type="commit",
                status="FAILED",
                command_display=f'git commit -m "{req.message}"',
                verified=False,
                error_message="No staged changes to commit. Stage modified files first or enable stage_all.",
                completed_at=utc_now(),
            )
            self._save_operation(rec)
            return rec

        # Check staged files and diff for secrets
        all_secret_warnings = list(staged_diff.secret_warnings)
        for sf in staged_files:
            if sf.has_secret_warning and sf.secret_warning_detail:
                if sf.secret_warning_detail not in all_secret_warnings:
                    all_secret_warnings.append(sf.secret_warning_detail)

        if all_secret_warnings and not req.allow_secret_override:
            rec = GitOperationRecord(
                operation_id=op_id,
                user_id=uid,
                project_id=pid,
                operation_type="commit",
                status="BLOCKED",
                command_display=f'git commit -m "{req.message}"',
                verified=False,
                diff_preview=staged_diff.unified_diff[:4000],
                secret_warnings=all_secret_warnings,
                stderr="Commit blocked by Stage 19 Secret & Environment File Protection.",
                error_message=(
                    "Secret protection blocked commit: "
                    + "; ".join(all_secret_warnings)
                    + ". Remove secrets or add sensitive files to .gitignore."
                ),
                completed_at=utc_now(),
            )
            self._save_operation(rec)
            return rec

        # Safe Change Management: require explicit confirmation before committing
        if not req.confirmed:
            rec = GitOperationRecord(
                operation_id=op_id,
                user_id=uid,
                project_id=pid,
                operation_type="commit",
                status="WAITING_FOR_APPROVAL",
                command_display=f'git commit -m "{req.message}"',
                requires_approval=True,
                approval_reason=(
                    f"Confirm commit of {len(staged_files)} staged file(s) "
                    f"(+{staged_diff.total_additions} / -{staged_diff.total_deletions} lines) to branch '{status.current_branch}'."
                ),
                diff_preview=staged_diff.unified_diff[:4000],
                secret_warnings=all_secret_warnings,
                result_data={
                    "staged_files": [f.path for f in staged_files],
                    "additions": staged_diff.total_additions,
                    "deletions": staged_diff.total_deletions,
                },
            )
            self._save_operation(
                rec,
                pending_payload={
                    "type": "commit",
                    "request": req.model_dump(mode="json"),
                },
            )
            return rec

        return self._execute_confirmed_commit(op_id, uid, pid, proj_dir, req, staged_diff)

    def _execute_confirmed_commit(
        self,
        op_id: str,
        uid: str,
        pid: str,
        proj_dir: Path,
        req: GitCommitRequest,
        staged_diff: GitDiffResponse,
    ) -> GitOperationRecord:
        cmd_args = ["commit", "-m", req.message.strip()]
        if req.description.strip():
            cmd_args.extend(["-m", req.description.strip()])

        code, out, err = self._run_git(proj_dir, cmd_args)
        _, head_hash, _ = self._run_git(proj_dir, ["rev-parse", "--short", "HEAD"])
        verified = code == 0 and bool(head_hash.strip())

        rec = GitOperationRecord(
            operation_id=op_id,
            user_id=uid,
            project_id=pid,
            operation_type="commit",
            status="SUCCEEDED" if verified else "FAILED",
            command_display=f'git commit -m "{req.message.strip()}"',
            requires_approval=True,
            approved=True,
            verified=verified,
            stdout=out,
            stderr=err,
            diff_preview=staged_diff.unified_diff[:4000],
            result_data={"commit_hash": head_hash.strip()},
            error_message=None if verified else (err or out),
            completed_at=utc_now(),
        )
        self._save_operation(rec)
        return rec

    def list_commits(
        self, user_id: str, project_id: str, branch: Optional[str] = None, limit: int = 20
    ) -> List[GitCommitEntry]:
        uid, pid, proj_dir = self._project_root(user_id, project_id)
        if not self._is_git_repo(proj_dir):
            return []

        ref = self._validate_branch_name(branch) if branch else "HEAD"
        code_h, _, _ = self._run_git(proj_dir, ["rev-parse", "--verify", ref])
        if code_h != 0:
            return []

        fmt = "%H%x1f%h%x1f%an%x1f%ae%x1f%aI%x1f%s%x1f%b%x1e"
        code, out, _ = self._run_git(
            proj_dir, ["log", ref, f"-n{min(limit, 50)}", f"--format={fmt}"]
        )
        if code != 0:
            return []

        commits: List[GitCommitEntry] = []
        for raw_entry in out.split("\x1e"):
            stripped = raw_entry.strip()
            if not stripped:
                continue
            fields = stripped.split("\x1f")
            if len(fields) < 6:
                continue
            commits.append(
                GitCommitEntry(
                    commit_hash=fields[0].strip(),
                    short_hash=fields[1].strip(),
                    author_name=fields[2].strip(),
                    author_email=fields[3].strip(),
                    authored_at=fields[4].strip(),
                    subject=fields[5].strip(),
                    body=fields[6].strip() if len(fields) > 6 else "",
                )
            )
        return commits

    # =========================================================================
    # Branch Creation, Dirty-Worktree Switch Guard, Comparison & Merging
    # =========================================================================

    def manage_branch(self, req: GitBranchActionRequest) -> GitOperationRecord:
        uid, pid, proj_dir = self._project_root(req.user_id, req.project_id)
        op_id = f"gitop_{uuid.uuid4().hex[:12]}"
        if not self._is_git_repo(proj_dir):
            raise ValueError(f"Project '{pid}' is not an initialized Git repository.")

        target_branch = self._validate_branch_name(req.branch_name)
        status = self.get_status(uid, pid)

        if req.action == "create":
            args = (
                ["checkout", "-b", target_branch]
                if req.checkout_on_create
                else ["branch", target_branch]
            )
            if req.source_branch:
                args.append(self._validate_branch_name(req.source_branch))
            code, out, err = self._run_git(proj_dir, args)
            rec = GitOperationRecord(
                operation_id=op_id,
                user_id=uid,
                project_id=pid,
                operation_type="create_branch",
                status="SUCCEEDED" if code == 0 else "FAILED",
                command_display="git " + " ".join(args),
                verified=(code == 0),
                stdout=out or f"Created branch '{target_branch}'.",
                stderr=err,
                error_message=None if code == 0 else (err or out),
                completed_at=utc_now(),
            )
            self._save_operation(rec)
            return rec

        if req.action == "switch":
            # Detect uncommitted changes before branch switch!
            if not status.is_clean and not req.allow_dirty_switch:
                dirty_list = [f.path for f in status.changed_files]
                rec = GitOperationRecord(
                    operation_id=op_id,
                    user_id=uid,
                    project_id=pid,
                    operation_type="switch_branch",
                    status="BLOCKED",
                    command_display=f"git checkout {target_branch}",
                    verified=False,
                    stderr="Uncommitted changes detected in working tree before branch switch.",
                    error_message=(
                        f"Cannot switch to branch '{target_branch}': {len(dirty_list)} uncommitted file(s) "
                        f"({', '.join(dirty_list[:5])}) would be affected. Commit changes first or explicitly set allow_dirty_switch=True."
                    ),
                    result_data={"uncommitted_files": dirty_list},
                    completed_at=utc_now(),
                )
                self._save_operation(rec)
                return rec

            code, out, err = self._run_git(proj_dir, ["checkout", target_branch])
            rec = GitOperationRecord(
                operation_id=op_id,
                user_id=uid,
                project_id=pid,
                operation_type="switch_branch",
                status="SUCCEEDED" if code == 0 else "FAILED",
                command_display=f"git checkout {target_branch}",
                verified=(code == 0),
                stdout=out or f"Switched to branch '{target_branch}'.",
                stderr=err,
                error_message=None if code == 0 else (err or out),
                completed_at=utc_now(),
            )
            self._save_operation(rec)
            return rec

        # req.action == "merge" -> Requires explicit confirmation
        diff_preview = self.get_diff(
            uid,
            pid,
            scope="branch_compare",
            base_ref=status.current_branch,
            compare_ref=target_branch,
        )
        if not req.confirmed:
            rec = GitOperationRecord(
                operation_id=op_id,
                user_id=uid,
                project_id=pid,
                operation_type="merge_branch",
                status="WAITING_FOR_APPROVAL",
                command_display=f"git merge --no-ff {target_branch}",
                requires_approval=True,
                approval_reason=(
                    f"Confirm merging branch '{target_branch}' into '{status.current_branch}' "
                    f"({diff_preview.total_files_changed} file(s) changed)."
                ),
                diff_preview=diff_preview.unified_diff[:4000],
            )
            self._save_operation(
                rec,
                pending_payload={
                    "type": "merge",
                    "request": req.model_dump(mode="json"),
                },
            )
            return rec

        return self._execute_confirmed_merge(op_id, uid, pid, proj_dir, target_branch, status.current_branch)

    def _execute_confirmed_merge(
        self,
        op_id: str,
        uid: str,
        pid: str,
        proj_dir: Path,
        source_branch: str,
        target_branch: str,
    ) -> GitOperationRecord:
        code, out, err = self._run_git(
            proj_dir,
            ["merge", "--no-ff", "-m", f"Merge branch '{source_branch}' into {target_branch}", source_branch],
        )
        combined = f"{out}\n{err}"
        if code != 0 and ("CONFLICT" in combined or "Automatic merge failed" in combined):
            # Safely abort the conflicted merge so working tree is not left corrupted
            self._run_git(proj_dir, ["merge", "--abort"])
            rec = GitOperationRecord(
                operation_id=op_id,
                user_id=uid,
                project_id=pid,
                operation_type="merge_branch",
                status="FAILED",
                command_display=f"git merge --no-ff {source_branch}",
                requires_approval=True,
                approved=True,
                verified=False,
                stdout=out,
                stderr=err,
                error_message=(
                    f"Merge conflict detected when merging '{source_branch}' into '{target_branch}'. "
                    "Automatic merge was safely aborted (`git merge --abort`) so working tree remains intact."
                ),
                completed_at=utc_now(),
            )
            self._save_operation(rec)
            return rec

        rec = GitOperationRecord(
            operation_id=op_id,
            user_id=uid,
            project_id=pid,
            operation_type="merge_branch",
            status="SUCCEEDED" if code == 0 else "FAILED",
            command_display=f"git merge --no-ff {source_branch}",
            requires_approval=True,
            approved=True,
            verified=(code == 0),
            stdout=out,
            stderr=err,
            error_message=None if code == 0 else (err or out),
            completed_at=utc_now(),
        )
        self._save_operation(rec)
        return rec

    def compare_branches(
        self, user_id: str, project_id: str, base_branch: str, compare_branch: str
    ) -> GitBranchComparisonResponse:
        uid, pid, proj_dir = self._project_root(user_id, project_id)
        b_base = self._validate_branch_name(base_branch)
        b_comp = self._validate_branch_name(compare_branch)

        code, lr_out, _ = self._run_git(
            proj_dir, ["rev-list", "--left-right", "--count", f"{b_base}...{b_comp}"]
        )
        behind = 0
        ahead = 0
        if code == 0 and lr_out.strip():
            parts = lr_out.strip().split()
            if len(parts) == 2:
                behind = int(parts[0])
                ahead = int(parts[1])

        diff_resp = self.get_diff(
            uid, pid, scope="branch_compare", base_ref=b_base, compare_ref=b_comp
        )
        commits = self.list_commits(uid, pid, branch=b_comp, limit=15)

        # Check potential merge conflicts via git merge-tree
        has_conflicts = False
        conflict_files: List[str] = []
        _, mb_out, _ = self._run_git(proj_dir, ["merge-base", b_base, b_comp])
        merge_base = mb_out.strip()
        if merge_base:
            _, mt_out, _ = self._run_git(proj_dir, ["merge-tree", merge_base, b_base, b_comp])
            if "<<<<<<< " in mt_out or "changed in both" in mt_out:
                has_conflicts = True
                for m in re.finditer(r"^\s+our\s+\d+\s+[0-9a-f]+\s+(.+)$", mt_out, re.MULTILINE):
                    fname = m.group(1).strip()
                    if fname not in conflict_files:
                        conflict_files.append(fname)

        return GitBranchComparisonResponse(
            project_id=pid,
            base_branch=b_base,
            compare_branch=b_comp,
            ahead_count=ahead,
            behind_count=behind,
            can_fast_forward=(behind == 0 and not has_conflicts),
            has_conflicts=has_conflicts,
            conflict_files=conflict_files,
            commits=commits,
            diff=diff_resp,
        )

    # =========================================================================
    # Remote Configuration, Sync & Collaboration (Pull Requests)
    # =========================================================================

    def configure_remote(self, req: GitRemoteConfigRequest) -> GitOperationRecord:
        uid, pid, proj_dir = self._project_root(req.user_id, req.project_id)
        op_id = f"gitop_{uuid.uuid4().hex[:12]}"
        if not self._is_git_repo(proj_dir):
            raise ValueError(f"Project '{pid}' is not an initialized Git repository.")

        r_name = (req.name or "origin").strip()
        if not VALID_REMOTE_NAME_RE.match(r_name):
            raise ValueError(f"Invalid remote name '{r_name}'.")

        valid_url, detected_provider = self._validate_remote_url(req.url)
        _, existing_out, _ = self._run_git(proj_dir, ["remote"])
        existing_remotes = set(existing_out.split())

        if r_name in existing_remotes:
            code, out, err = self._run_git(proj_dir, ["remote", "set-url", r_name, valid_url])
            cmd_str = f"git remote set-url {r_name} {valid_url}"
        else:
            code, out, err = self._run_git(proj_dir, ["remote", "add", r_name, valid_url])
            cmd_str = f"git remote add {r_name} {valid_url}"

        rec = GitOperationRecord(
            operation_id=op_id,
            user_id=uid,
            project_id=pid,
            operation_type="configure_remote",
            status="SUCCEEDED" if code == 0 else "FAILED",
            command_display=cmd_str,
            verified=(code == 0),
            stdout=out or f"Configured remote '{r_name}' -> {valid_url} ({detected_provider}).",
            stderr=err,
            result_data={"remote_name": r_name, "url": valid_url, "provider": detected_provider},
            completed_at=utc_now(),
        )
        self._save_operation(rec)
        return rec

    def sync_remote(self, req: GitRemoteSyncRequest) -> GitOperationRecord:
        uid, pid, proj_dir = self._project_root(req.user_id, req.project_id)
        op_id = f"gitop_{uuid.uuid4().hex[:12]}"
        if not self._is_git_repo(proj_dir):
            raise ValueError(f"Project '{pid}' is not an initialized Git repository.")

        # Block force-push unless explicitly confirmed
        if req.force:
            rec = GitOperationRecord(
                operation_id=op_id,
                user_id=uid,
                project_id=pid,
                operation_type="sync_remote",
                status="BLOCKED",
                command_display=f"git {req.action} --force {req.remote_name}",
                verified=False,
                stderr="Force-push and history rewriting are blocked by Stage 19 Safe Change Management policy.",
                error_message="Force-push (--force) is blocked to prevent overwriting shared remote history.",
                completed_at=utc_now(),
            )
            self._save_operation(rec)
            return rec

        status = self.get_status(uid, pid)
        remote_cfg = next((r for r in status.remotes if r.name == req.remote_name), None)
        if not remote_cfg:
            rec = GitOperationRecord(
                operation_id=op_id,
                user_id=uid,
                project_id=pid,
                operation_type="sync_remote",
                status="FAILED",
                command_display=f"git {req.action} {req.remote_name}",
                verified=False,
                error_message=f"Remote '{req.remote_name}' is not configured for this repository.",
                completed_at=utc_now(),
            )
            self._save_operation(rec)
            return rec

        # Require explicit confirmation before remote push/pull/fetch
        if not req.confirmed:
            rec = GitOperationRecord(
                operation_id=op_id,
                user_id=uid,
                project_id=pid,
                operation_type="sync_remote",
                status="WAITING_FOR_APPROVAL",
                command_display=f"git {req.action} {req.remote_name} {req.branch or status.current_branch}",
                requires_approval=True,
                approval_reason=(
                    f"Remote synchronization ('git {req.action}') contacts external host '{remote_cfg.url}' "
                    "and requires explicit user confirmation."
                ),
            )
            self._save_operation(
                rec,
                pending_payload={
                    "type": "sync_remote",
                    "request": req.model_dump(mode="json"),
                },
            )
            return rec

        # Check authentication & network availability honestly
        if not settings.git_provider_token.strip():
            rec = GitOperationRecord(
                operation_id=op_id,
                user_id=uid,
                project_id=pid,
                operation_type="sync_remote",
                status="FAILED",
                command_display=f"git {req.action} {req.remote_name} {req.branch or status.current_branch}",
                requires_approval=True,
                approved=True,
                verified=False,
                stderr="AuthenticationError: GIT_PROVIDER_TOKEN is not configured in backend environment.",
                error_message=(
                    f"Remote '{req.action}' to '{remote_cfg.url}' could not be authenticated because "
                    "GIT_PROVIDER_TOKEN is not configured. Local commits remain safely stored."
                ),
                completed_at=utc_now(),
            )
            self._save_operation(rec)
            return rec

        if not req.allow_network and not settings.terminal_default_allow_network:
            rec = GitOperationRecord(
                operation_id=op_id,
                user_id=uid,
                project_id=pid,
                operation_type="sync_remote",
                status="FAILED",
                command_display=f"git {req.action} {req.remote_name} {req.branch or status.current_branch}",
                requires_approval=True,
                approved=True,
                verified=False,
                stderr="NetworkDisabledError: Outbound network access is disabled in the sandbox.",
                error_message="Outbound network access is disabled; enable allow_network to contact remote Git hosts.",
                completed_at=utc_now(),
            )
            self._save_operation(rec)
            return rec

        code, out, err = self._run_git(
            proj_dir, [req.action, req.remote_name, req.branch or status.current_branch]
        )
        rec = GitOperationRecord(
            operation_id=op_id,
            user_id=uid,
            project_id=pid,
            operation_type="sync_remote",
            status="SUCCEEDED" if code == 0 else "FAILED",
            command_display=f"git {req.action} {req.remote_name} {req.branch or status.current_branch}",
            requires_approval=True,
            approved=True,
            verified=(code == 0),
            stdout=out,
            stderr=err,
            error_message=None if code == 0 else (err or out),
            completed_at=utc_now(),
        )
        self._save_operation(rec)
        return rec

    def create_pull_request(self, req: GitPullRequestCreateRequest) -> GitPullRequestRecord:
        uid, pid, _ = self._project_root(req.user_id, req.project_id)
        pr_id = f"pr_{uuid.uuid4().hex[:10]}"
        src_b = self._validate_branch_name(req.source_branch)
        tgt_b = self._validate_branch_name(req.target_branch)

        comp = self.compare_branches(uid, pid, tgt_b, src_b)
        review_summary = (
            f"Comparing '{src_b}' -> '{tgt_b}': {comp.ahead_count} commit(s) ahead, "
            f"{comp.diff.total_files_changed} file(s) changed "
            f"(+{comp.diff.total_additions} / -{comp.diff.total_deletions}). "
            f"Conflicts: {'YES' if comp.has_conflicts else 'NONE'}."
        )

        status_info = self.get_status(uid, pid)
        remote_cfg = status_info.remotes[0] if status_info.remotes else None
        provider: GitRemoteProvider = remote_cfg.provider if remote_cfg else "github"

        # Honest separation between local PR preparation and provider-confirmed remote PR
        if not req.submit_to_remote:
            pr_rec = GitPullRequestRecord(
                pr_id=pr_id,
                user_id=uid,
                project_id=pid,
                title=req.title.strip(),
                description=req.description.strip(),
                source_branch=src_b,
                target_branch=tgt_b,
                issue_references=req.issue_references,
                review_summary=review_summary,
                provider=provider,
                status="LOCAL_DRAFT_ONLY",
                local_draft_only=True,
                remote_confirmed=False,
                provider_message="Saved as a local Pull Request draft. Remote submission was not requested.",
            )
        elif not remote_cfg or not settings.git_provider_token.strip():
            pr_rec = GitPullRequestRecord(
                pr_id=pr_id,
                user_id=uid,
                project_id=pid,
                title=req.title.strip(),
                description=req.description.strip(),
                source_branch=src_b,
                target_branch=tgt_b,
                issue_references=req.issue_references,
                review_summary=review_summary,
                provider=provider,
                status="REMOTE_FAILED",
                local_draft_only=True,
                remote_confirmed=False,
                provider_message=(
                    "Local PR specification prepared, but remote PR creation could not be confirmed: "
                    "remote origin or GIT_PROVIDER_TOKEN is not configured."
                ),
            )
        else:
            pr_rec = GitPullRequestRecord(
                pr_id=pr_id,
                user_id=uid,
                project_id=pid,
                title=req.title.strip(),
                description=req.description.strip(),
                source_branch=src_b,
                target_branch=tgt_b,
                issue_references=req.issue_references,
                review_summary=review_summary,
                provider=provider,
                status="LOCAL_DRAFT_ONLY",
                local_draft_only=True,
                remote_confirmed=False,
                provider_message="Prepared local PR bundle; remote API call requires live provider endpoint confirmation.",
            )

        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO git_pull_requests
                    (pr_id, user_id, project_id, record_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        pr_rec.pr_id,
                        uid,
                        pid,
                        pr_rec.model_dump_json(),
                        pr_rec.created_at.isoformat(),
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        return pr_rec

    def list_pull_requests(self, user_id: str, project_id: str) -> List[GitPullRequestRecord]:
        uid, pid, _ = self._project_root(user_id, project_id)
        with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    "SELECT record_json FROM git_pull_requests WHERE user_id = ? AND project_id = ? ORDER BY created_at DESC",
                    (uid, pid),
                ).fetchall()
            finally:
                conn.close()
        return [GitPullRequestRecord.model_validate_json(str(r["record_json"])) for r in rows]

    # =========================================================================
    # AI-Powered Code Review Engine (Verified Defects vs. Possible Concerns)
    # =========================================================================

    async def review_changes(self, req: GitReviewRequest) -> GitCodeReviewResponse:
        uid, pid, proj_dir = self._project_root(req.user_id, req.project_id)
        review_id = f"rev_{uuid.uuid4().hex[:12]}"

        status = self.get_status(uid, pid)
        if req.paths:
            target_files = [p for p in req.paths if ".." not in p]
        elif status.changed_files:
            target_files = [f.path for f in status.changed_files]
        else:
            proj = terminal_execution_engine.get_project(uid, pid)
            target_files = [f.relative_path for f in proj.files]

        findings: List[GitCodeReviewFinding] = []
        reviewed_files: List[str] = []
        has_source_changes = False
        has_test_changes = False

        for rel_path in target_files:
            fpath = (proj_dir / rel_path).resolve()
            if not str(fpath).startswith(str(proj_dir)) or not fpath.exists() or not fpath.is_file():
                continue
            reviewed_files.append(rel_path)
            fname_lower = fpath.name.lower()
            if "test" in fname_lower:
                has_test_changes = True
            elif fpath.suffix.lower() in (".py", ".js", ".ts"):
                has_source_changes = True

            content = fpath.read_text(encoding="utf-8", errors="replace")

            # 1. Secret / Credential scan -> Verified Defect
            _, has_sec, sec_detail = self._scan_file_for_secrets(proj_dir, rel_path)
            if has_sec and sec_detail:
                findings.append(
                    GitCodeReviewFinding(
                        finding_id=f"fnd_{uuid.uuid4().hex[:8]}",
                        file_path=rel_path,
                        line_number=1,
                        category="security",
                        severity="critical",
                        finding_type="verified_defect",
                        title="Hardcoded Secret or Sensitive Environment File",
                        description=sec_detail,
                        suggested_fix="Move credentials to backend environment variables and add the file to .gitignore.",
                        auto_accepted=False,
                    )
                )

            # 2. Python AST & Security/Bug Analysis
            if fpath.suffix.lower() == ".py":
                try:
                    tree = ast.parse(content, filename=rel_path)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                                findings.append(
                                    GitCodeReviewFinding(
                                        finding_id=f"fnd_{uuid.uuid4().hex[:8]}",
                                        file_path=rel_path,
                                        line_number=node.lineno,
                                        category="bug",
                                        severity="high",
                                        finding_type="verified_defect",
                                        title="Literal Division by Zero",
                                        description=f"Line {node.lineno} divides by literal 0, which raises ZeroDivisionError at runtime.",
                                        suggested_fix="Check that the denominator is non-zero before dividing.",
                                    )
                                )
                        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                            if node.func.id in ("eval", "exec"):
                                findings.append(
                                    GitCodeReviewFinding(
                                        finding_id=f"fnd_{uuid.uuid4().hex[:8]}",
                                        file_path=rel_path,
                                        line_number=node.lineno,
                                        category="security",
                                        severity="high",
                                        finding_type="verified_defect",
                                        title=f"Unsafe Dynamic Code Execution ({node.func.id})",
                                        description=f"Calling '{node.func.id}()' on untrusted input enables arbitrary code execution.",
                                        suggested_fix="Use ast.literal_eval() or structured JSON parsing instead.",
                                    )
                                )
                        elif isinstance(node, ast.ExceptHandler) and node.type is None:
                            findings.append(
                                GitCodeReviewFinding(
                                    finding_id=f"fnd_{uuid.uuid4().hex[:8]}",
                                    file_path=rel_path,
                                    line_number=node.lineno,
                                    category="readability",
                                    severity="medium",
                                    finding_type="possible_concern",
                                    title="Bare 'except:' Clause",
                                    description="Bare 'except:' catches SystemExit and masks unexpected errors.",
                                    suggested_fix="Catch 'Exception' or a specific exception subclass.",
                                )
                            )
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            for d_node in node.args.defaults:
                                if isinstance(d_node, (ast.List, ast.Dict, ast.Set)):
                                    findings.append(
                                        GitCodeReviewFinding(
                                            finding_id=f"fnd_{uuid.uuid4().hex[:8]}",
                                            file_path=rel_path,
                                            line_number=node.lineno,
                                            category="bug",
                                            severity="medium",
                                            finding_type="possible_concern",
                                            title=f"Mutable Default Argument in '{node.name}'",
                                            description="Mutable default arguments persist state across function calls.",
                                            suggested_fix="Use None as the default value and initialize inside the function.",
                                        )
                                    )
                except SyntaxError as syn_err:
                    findings.append(
                        GitCodeReviewFinding(
                            finding_id=f"fnd_{uuid.uuid4().hex[:8]}",
                            file_path=rel_path,
                            line_number=syn_err.lineno or 1,
                            category="bug",
                            severity="critical",
                            finding_type="verified_defect",
                            title="Python SyntaxError",
                            description=f"SyntaxError: {syn_err.msg} at line {syn_err.lineno}.",
                            suggested_fix="Fix the syntax error before staging or committing.",
                        )
                    )

            # 3. Readability TODO/FIXME check
            for idx, ln in enumerate(content.splitlines(), start=1):
                if re.search(r"\b(?:TODO|FIXME|HACK)\b", ln):
                    findings.append(
                        GitCodeReviewFinding(
                            finding_id=f"fnd_{uuid.uuid4().hex[:8]}",
                            file_path=rel_path,
                            line_number=idx,
                            category="readability",
                            severity="low",
                            finding_type="possible_concern",
                            title="Unresolved TODO/FIXME Marker",
                            description=f"Line {idx} contains an unresolved marker: '{ln.strip()[:100]}'.",
                            suggested_fix="Resolve the TODO item or track it in an issue reference before release.",
                        )
                    )

        # 4. Missing test coverage concern when implementation files changed without test updates
        if has_source_changes and not has_test_changes and len(status.changed_files) > 0:
            findings.append(
                GitCodeReviewFinding(
                    finding_id=f"fnd_{uuid.uuid4().hex[:8]}",
                    file_path=reviewed_files[0] if reviewed_files else "main.py",
                    line_number=1,
                    category="missing_tests",
                    severity="low",
                    finding_type="possible_concern",
                    title="Implementation Modified Without Corresponding Test Updates",
                    description="Source code files were modified, but no unit test files were updated in the working tree.",
                    suggested_fix="Add or update unit test assertions in test_main.py to cover the modified behavior.",
                )
            )

        # 5. Reuse Stage 18 Testing Tools to verify unit test pass/fail status
        tests_executed = False
        tests_passed: Optional[bool] = None
        if req.run_stage18_tests:
            try:
                exec_rec = await terminal_execution_engine.execute_code(
                    CodeExecuteRequest(
                        user_id=uid,
                        project_id=pid,
                        mode="test",
                    )
                )
                tests_executed = True
                tests_passed = exec_rec.exit_code == 0
                if not tests_passed:
                    findings.append(
                        GitCodeReviewFinding(
                            finding_id=f"fnd_{uuid.uuid4().hex[:8]}",
                            file_path=reviewed_files[0] if reviewed_files else "test_main.py",
                            line_number=1,
                            category="bug",
                            severity="high",
                            finding_type="verified_defect",
                            title="Stage 18 Sandbox Unit Tests Failed",
                            description=(
                                f"Running the project unit test suite exited with code {exec_rec.exit_code}: "
                                f"{(exec_rec.stderr or exec_rec.stdout).strip()[:240]}"
                            ),
                            suggested_fix="Fix failing unit test assertions before committing changes.",
                        )
                    )
            except Exception:
                tests_executed = False

        verified_count = sum(1 for f in findings if f.finding_type == "verified_defect")
        concern_count = sum(1 for f in findings if f.finding_type == "possible_concern")

        summary = (
            f"Reviewed {len(reviewed_files)} file(s): "
            f"{verified_count} verified defect(s), {concern_count} possible concern(s). "
            + (
                f"Stage 18 unit tests: {'PASSED' if tests_passed else 'FAILED'}."
                if tests_executed
                else ""
            )
        )

        resp = GitCodeReviewResponse(
            review_id=review_id,
            project_id=pid,
            user_id=uid,
            reviewed_files=reviewed_files,
            verified_defects_count=verified_count,
            possible_concerns_count=concern_count,
            tests_executed=tests_executed,
            tests_passed=tests_passed,
            findings=findings,
            summary=summary.strip(),
        )
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO git_reviews
                    (review_id, user_id, project_id, record_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        resp.review_id,
                        uid,
                        pid,
                        resp.model_dump_json(),
                        resp.created_at.isoformat(),
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        return resp

    # =========================================================================
    # Approval Gate Execution Handler
    # =========================================================================

    def approve_operation(
        self, operation_id: str, req: GitApproveOperationRequest
    ) -> GitOperationRecord:
        uid = terminal_execution_engine._sanitize_user_id(req.user_id)
        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT record_json, pending_payload_json FROM git_operations WHERE operation_id = ? AND user_id = ?",
                    (operation_id, uid),
                ).fetchone()
                if not row:
                    raise ValueError(f"Git operation '{operation_id}' not found for user '{uid}'.")
            finally:
                conn.close()

        rec = GitOperationRecord.model_validate_json(str(row["record_json"]))
        if rec.status != "WAITING_FOR_APPROVAL":
            return rec

        if not req.approved:
            rec.status = "CANCELLED"
            rec.approved = False
            rec.stderr = "Operation cancelled: User declined confirmation for Git operation."
            rec.completed_at = utc_now()
            self._save_operation(rec)
            return rec

        payload = json.loads(str(row["pending_payload_json"])) if row["pending_payload_json"] else {}
        op_type = payload.get("type")
        req_data = payload.get("request", {})

        if op_type == "commit":
            commit_req = GitCommitRequest.model_validate(req_data)
            commit_req.confirmed = True
            return self.commit_changes(commit_req)
        if op_type == "merge":
            branch_req = GitBranchActionRequest.model_validate(req_data)
            branch_req.confirmed = True
            return self.manage_branch(branch_req)
        if op_type == "sync_remote":
            sync_req = GitRemoteSyncRequest.model_validate(req_data)
            sync_req.confirmed = True
            return self.sync_remote(sync_req)

        rec.status = "FAILED"
        rec.error_message = "Pending operation payload could not be resumed."
        self._save_operation(rec)
        return rec


git_version_control_engine = GitVersionControlEngine()
