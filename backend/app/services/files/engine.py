"""
NEXORA AI — STAGE 17: FILE MANAGEMENT & WORKSPACE AUTOMATION ENGINE

Provides permission-based file management for authorized user workspaces:
- Strict path normalization, directory traversal prevention, and symlink escape rejection
- File discovery, full-text & Stage 4 indexed content search, and rule-based organization
- Text-based file creation/editing with automatic version snapshots (.nexora_versions)
- Binary document processing and conversion (PDF, DOCX, XLSX, CSV, JSON, MD, TXT)
- SHA-256 content-hash duplicate detection and safe deduplication
- Recoverable Trash vault (.nexora_trash), operation audit logs, approval gates, and rollback
"""

import csv
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.models.schemas import (
    DuplicateFileGroup,
    FileBrowserImportRequest,
    FileCategory,
    FileConvertRequest,
    FileCreateFolderRequest,
    FileDeleteRequest,
    FileDuplicateCleanupRequest,
    FileOperationApproveRequest,
    FileOperationPreview,
    FileOperationRecord,
    FileOrganizeRequest,
    FilePlannedChange,
    FileSearchRequest,
    FileTransferRequest,
    FileWriteRequest,
    WorkspaceFileItem,
    WorkspaceFileReadResponse,
    WorkspaceFileVersion,
    WorkspaceTrashItem,
    utc_now,
)
from app.services.documents.parsers import DocumentParser

try:
    import docx
except ImportError:
    docx = None

try:
    import openpyxl
except ImportError:
    openpyxl = None


ALLOWED_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".log",
    ".py",
    ".ts",
    ".js",
}

ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
}

ALLOWED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}

ALL_ALLOWED_EXTENSIONS = (
    ALLOWED_TEXT_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS | ALLOWED_IMAGE_EXTENSIONS
)

FORBIDDEN_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".ps1",
    ".sh",
    ".dll",
    ".so",
    ".dylib",
    ".msi",
    ".scr",
    ".vbs",
    ".com",
    ".pif",
    ".jar",
    ".pem",
    ".key",
    ".pfx",
}

FORBIDDEN_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
    "authorized_keys",
    "known_hosts",
    "credentials.json",
    "secrets.json",
}

INTERNAL_SYSTEM_DIRS = {
    ".nexora_trash",
    ".nexora_versions",
    ".git",
    ".ssh",
    "__pycache__",
}

_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|secret|password|passwd|token|authorization)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.~+/]{8,})['\"]?"
)


def redact_sensitive_log_text(text: str) -> str:
    """Redacts potential credentials or API tokens before writing to operation logs."""
    if not text:
        return ""
    return _SECRET_PATTERN.sub(r"\1=[REDACTED_SECRET]", text)


def compute_sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def classify_file_category(ext: str, is_dir: bool = False) -> FileCategory:
    if is_dir:
        return "folder"
    ext = ext.lower()
    if ext in (".pdf", ".docx"):
        return "document"
    if ext in (".xlsx", ".csv"):
        return "spreadsheet"
    if ext in (".json", ".yaml", ".yml", ".xml"):
        return "data"
    if ext in (".md", ".txt", ".log"):
        return "markdown_text"
    if ext in (".py", ".ts", ".js", ".html"):
        return "code"
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return "image"
    return "other"


def get_supported_conversions(ext: str, is_dir: bool = False) -> List[str]:
    if is_dir:
        return []
    ext = ext.lower()
    mapping = {
        ".csv": ["json", "xlsx", "md", "txt"],
        ".json": ["csv", "xlsx", "md", "txt"],
        ".txt": ["md", "docx", "json"],
        ".md": ["txt", "docx", "json"],
        ".docx": ["txt", "md", "json"],
        ".xlsx": ["csv", "json", "md", "txt"],
        ".pdf": ["txt", "md", "json"],
    }
    return mapping.get(ext, [])


class FileWorkspaceEngine:
    """
    Permission-based File Management & Workspace Automation Engine (Stage 17).
    Strictly confines all operations to authorized per-user workspace directories,
    prevents directory traversal and symlink escapes, preserves originals via
    automatic version snapshots, and supports preview/approval/rollback.
    """

    def __init__(
        self,
        workspace_root_dir: Optional[str] = None,
        db_path: Optional[str] = None,
    ):
        self.workspace_root = Path(workspace_root_dir or settings.file_workspace_dir).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path or settings.file_workspace_db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS file_versions (
                        version_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        relative_path TEXT NOT NULL,
                        version_number INTEGER NOT NULL,
                        sha256_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        storage_filename TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trash_items (
                        trash_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        original_path TEXT NOT NULL,
                        name TEXT NOT NULL,
                        is_dir INTEGER NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        sha256_hash TEXT,
                        storage_name TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        deleted_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS file_operations (
                        operation_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        operation_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        verified INTEGER NOT NULL,
                        verification_detail TEXT NOT NULL,
                        requires_approval INTEGER NOT NULL,
                        approval_reason TEXT,
                        approved INTEGER,
                        preview_json TEXT,
                        affected_paths_json TEXT NOT NULL,
                        result_data_json TEXT NOT NULL,
                        rollback_recipe_json TEXT,
                        rollback_supported INTEGER NOT NULL,
                        rolled_back INTEGER NOT NULL,
                        error_message TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS stage4_sync_map (
                        user_id TEXT NOT NULL,
                        relative_path TEXT NOT NULL,
                        sha256_hash TEXT NOT NULL,
                        doc_id TEXT NOT NULL,
                        synced_at TEXT NOT NULL,
                        PRIMARY KEY (user_id, relative_path)
                    )
                    """
                )
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Workspace Isolation & Security Boundary Validation
    # ------------------------------------------------------------------
    def _sanitize_user_id(self, user_id: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_\-]", "_", (user_id or "default_user").strip())
        return cleaned[:64] or "default_user"

    def get_user_workspace_root(self, user_id: str = "default_user", seed_if_empty: bool = True) -> Path:
        safe_uid = self._sanitize_user_id(user_id)
        user_dir = (self.workspace_root / safe_uid).resolve()
        user_dir.mkdir(parents=True, exist_ok=True)
        (user_dir / ".nexora_trash").mkdir(parents=True, exist_ok=True)
        (user_dir / ".nexora_versions").mkdir(parents=True, exist_ok=True)

        if seed_if_empty:
            marker = user_dir / ".nexora_versions" / ".seeded"
            if not marker.exists():
                self._seed_starter_files(user_dir)
                marker.write_text("seeded", encoding="utf-8")
        return user_dir

    def _seed_starter_files(self, user_dir: Path) -> None:
        readme = user_dir / "README_WORKSPACE.md"
        if not readme.exists():
            readme.write_text(
                "# NEXORA AI — Stage 17 Authorized File Workspace\n\n"
                "Welcome to your sandboxed, permission-controlled File Workspace.\n\n"
                "## Supported Capabilities\n"
                "- **Create & Edit**: TXT, Markdown, CSV, JSON, DOCX, XLSX with automatic backup versions.\n"
                "- **Convert**: Seamless conversion across CSV, JSON, XLSX, Markdown, TXT, and DOCX.\n"
                "- **Duplicate Detection**: SHA-256 content-hash duplicate discovery and safe trash cleanup.\n"
                "- **Smart Organization**: Rule-based folder organization with preview & 1-click rollback.\n",
                encoding="utf-8",
            )
        sample_csv = user_dir / "quarterly_metrics.csv"
        if not sample_csv.exists():
            sample_csv.write_text(
                "module,stage,tests_passed,status\n"
                "Reasoning Engine,11,10,Verified\n"
                "Model Routing,12,8,Verified\n"
                "Persistent Memory,13,7,Verified\n"
                "Multi-Agent System,14,6,Verified\n"
                "Workflow Automation,15,7,Verified\n"
                "Computer Control,16,6,Verified\n",
                encoding="utf-8",
            )
        sample_json = user_dir / "workspace_manifest.json"
        if not sample_json.exists():
            sample_json.write_text(
                json.dumps(
                    {
                        "workspace": "NEXORA Stage 17 File Engine",
                        "auto_backup_enabled": True,
                        "trash_recovery_enabled": True,
                        "supported_formats": sorted(list(ALL_ALLOWED_EXTENSIONS)),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

    def resolve_safe_path(
        self,
        user_id: str,
        relative_path: str,
        allow_root: bool = False,
        require_valid_file_extension: bool = False,
    ) -> Tuple[Path, str]:
        """
        Normalizes a user-supplied relative path and enforces:
        1. No null bytes, drive prefixes, absolute paths, or '..' parent traversal.
        2. No access to internal system directories (.nexora_trash, .nexora_versions, .git, .ssh).
        3. No symbolic-link or junction escapes outside the user's workspace root.
        4. No forbidden executable extensions or credential filenames.
        Returns (resolved_path, normalized_posix_relative_path).
        """
        user_root = self.get_user_workspace_root(user_id)

        raw = (relative_path or "").strip()
        if "\x00" in raw:
            raise PermissionError("Path rejected: null byte detected.")

        if raw in ("", "."):
            if allow_root:
                return user_root, ""
            raise ValueError("A valid relative file or folder path is required.")

        # Reject Windows drive letters, UNC paths, or leading slashes
        if re.match(r"^[A-Za-z]:", raw) or raw.startswith("/") or raw.startswith("\\"):
            raise PermissionError(
                "Path rejected: absolute paths and drive letters are prohibited outside the authorized workspace."
            )

        norm_slashes = raw.replace("\\", "/").strip("/")
        parts = [p for p in norm_slashes.split("/") if p and p != "."]
        if not parts:
            if allow_root:
                return user_root, ""
            raise ValueError("Path cannot be empty.")

        for part in parts:
            if part == "..":
                raise PermissionError(
                    "Directory traversal ('..') is strictly blocked by the Stage 17 Workspace Security Boundary."
                )
            if part in INTERNAL_SYSTEM_DIRS:
                raise PermissionError(
                    f"Access to internal protected directory '{part}' is restricted."
                )
            if part.lower() in FORBIDDEN_FILENAMES:
                raise PermissionError(
                    f"Access to sensitive credential or environment file '{part}' is prohibited."
                )

        # Walk component by component to detect any symlink or junction along the path
        curr = user_root
        for part in parts:
            curr = curr / part
            if curr.exists() or curr.is_symlink():
                if curr.is_symlink():
                    raise PermissionError(
                        f"Symbolic link escape rejected at '{part}'. Unauthorized symbolic links are prohibited."
                    )
                resolved_curr = curr.resolve()
                try:
                    resolved_curr.relative_to(user_root)
                except ValueError as exc:
                    raise PermissionError(
                        "Path resolution escaped the authorized workspace boundary."
                    ) from exc

        resolved_target = curr.resolve()
        try:
            rel_posix = resolved_target.relative_to(user_root).as_posix()
        except ValueError as exc:
            raise PermissionError(
                "Target path escapes the authorized user workspace root."
            ) from exc

        ext = resolved_target.suffix.lower()
        if ext in FORBIDDEN_EXTENSIONS:
            raise PermissionError(
                f"File extension '{ext}' is blocked for security reasons (executable/key format)."
            )

        if require_valid_file_extension:
            if not ext or ext not in ALL_ALLOWED_EXTENSIONS:
                raise ValueError(
                    f"Unsupported or missing file extension '{ext}'. Supported extensions: {', '.join(sorted(ALL_ALLOWED_EXTENSIONS))}"
                )

        return resolved_target, rel_posix

    # ------------------------------------------------------------------
    # Capabilities & Metadata Helpers
    # ------------------------------------------------------------------
    def get_capabilities_summary(self, user_id: str = "default_user") -> Dict[str, Any]:
        user_root = self.get_user_workspace_root(user_id)
        trash_items = self.list_trash(user_id)
        operations = self.list_operations(user_id, limit=25)
        return {
            "stage": 17,
            "engine": "FileWorkspaceEngine",
            "authorized_workspace_root": f"data/file_workspace/{self._sanitize_user_id(user_id)}",
            "workspace_exists": user_root.exists(),
            "max_file_size_bytes": settings.file_workspace_max_file_size_bytes,
            "max_bulk_files": settings.file_workspace_max_bulk_files,
            "bulk_approval_threshold": settings.file_workspace_bulk_approval_threshold,
            "allowed_extensions": sorted(list(ALL_ALLOWED_EXTENSIONS)),
            "editable_text_extensions": sorted(list(ALLOWED_TEXT_EXTENSIONS)),
            "processable_document_extensions": sorted(list(ALLOWED_DOCUMENT_EXTENSIONS)),
            "trash_count": len(trash_items),
            "recent_operations_count": len(operations),
            "security_boundaries": [
                "Strict confinement to per-user workspace directory (data/file_workspace/<user_id>)",
                "Directory traversal ('..'), drive letters, and null-byte injection blocked",
                "Symbolic link (symlink) escape detection on every path segment",
                "Automatic immutable backup version created in .nexora_versions before any file edit or overwrite",
                "Deleted files move to Recoverable Trash (.nexora_trash) instead of immediate destruction",
                "Explicit confirmation required for deletes, unconfirmed overwrites, and bulk moves",
                "Document contents wrapped in <untrusted_file_content> tags when returned to AI agents",
                "Server-side workspace storage is strictly separated from local OS control",
            ],
        }

    def _get_version_count(self, user_id: str, rel_posix: str) -> int:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM file_versions WHERE user_id = ? AND relative_path = ?",
                (self._sanitize_user_id(user_id), rel_posix),
            ).fetchone()
            return int(row["cnt"]) if row else 0
        finally:
            conn.close()

    def _get_indexed_doc_id(self, user_id: str, rel_posix: str, sha256_hash: Optional[str]) -> Optional[str]:
        if not sha256_hash:
            return None
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT doc_id, sha256_hash FROM stage4_sync_map WHERE user_id = ? AND relative_path = ?",
                (self._sanitize_user_id(user_id), rel_posix),
            ).fetchone()
            if row and row["sha256_hash"] == sha256_hash:
                return str(row["doc_id"])
            return None
        finally:
            conn.close()

    def _build_file_item(
        self,
        user_id: str,
        user_root: Path,
        path: Path,
        snippet_match: Optional[str] = None,
    ) -> WorkspaceFileItem:
        rel_posix = path.resolve().relative_to(user_root).as_posix()
        parent_posix = path.resolve().parent.relative_to(user_root).as_posix()
        if parent_posix == ".":
            parent_posix = ""
        is_dir = path.is_dir()
        ext = "" if is_dir else path.suffix.lower()
        stat = path.stat()
        size_bytes = 0 if is_dir else int(stat.st_size)
        modified_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        sha256_val = None if is_dir else compute_sha256_file(path)
        category = classify_file_category(ext, is_dir=is_dir)
        is_editable = (not is_dir) and (ext in ALLOWED_TEXT_EXTENSIONS)
        is_processable = (not is_dir) and DocumentParser.is_supported(path.name)
        conversions = get_supported_conversions(ext, is_dir=is_dir)
        v_count = 0 if is_dir else self._get_version_count(user_id, rel_posix)
        doc_id = None if is_dir else self._get_indexed_doc_id(user_id, rel_posix, sha256_val)

        return WorkspaceFileItem(
            relative_path=rel_posix,
            name=path.name,
            parent_dir=parent_posix,
            is_dir=is_dir,
            extension=ext,
            category=category,
            size_bytes=size_bytes,
            sha256_hash=sha256_val,
            modified_at=modified_dt,
            is_editable_text=is_editable,
            is_processable_document=is_processable,
            supported_conversions=conversions,
            version_count=v_count,
            indexed_doc_id=doc_id,
            snippet_match=snippet_match,
        )

    # ------------------------------------------------------------------
    # Listing & Searching
    # ------------------------------------------------------------------
    def list_items(
        self,
        user_id: str = "default_user",
        directory: str = "",
        recursive: bool = True,
    ) -> List[WorkspaceFileItem]:
        user_root = self.get_user_workspace_root(user_id)
        target_dir, _ = self.resolve_safe_path(user_id, directory, allow_root=True)
        if not target_dir.exists():
            raise FileNotFoundError(f"Directory '{directory}' does not exist in workspace.")
        if not target_dir.is_dir():
            raise ValueError(f"Path '{directory}' is not a directory.")

        items: List[WorkspaceFileItem] = []
        iterator = target_dir.rglob("*") if recursive else target_dir.iterdir()
        for entry in iterator:
            rel_parts = entry.relative_to(user_root).parts
            if any(p in INTERNAL_SYSTEM_DIRS for p in rel_parts):
                continue
            if entry.is_symlink():
                continue
            items.append(self._build_file_item(user_id, user_root, entry))

        # Sort folders first, then alphabetically by relative_path
        items.sort(key=lambda x: (not x.is_dir, x.relative_path.lower()))
        return items

    def _extract_searchable_text(self, path: Path) -> str:
        ext = path.suffix.lower()
        try:
            if ext in ALLOWED_TEXT_EXTENSIONS:
                return path.read_text(encoding="utf-8", errors="replace")[:50000]
            if ext in ALLOWED_DOCUMENT_EXTENSIONS:
                parsed = DocumentParser.parse_file(str(path), path.name)
                return "\n".join(p.content for p in parsed.pages)[:50000]
        except Exception:
            return ""
        return ""

    def search_items(self, req: FileSearchRequest) -> Dict[str, Any]:
        all_items = self.list_items(user_id=req.user_id, directory=req.directory, recursive=True)
        user_root = self.get_user_workspace_root(req.user_id)
        query_lower = (req.query or "").strip().lower()
        norm_exts = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in req.extensions if e.strip()}

        matched_items: List[WorkspaceFileItem] = []
        for item in all_items:
            if norm_exts and item.extension.lower() not in norm_exts:
                continue
            if req.category and item.category != req.category:
                continue
            if req.modified_after and item.modified_at < req.modified_after:
                continue
            if req.modified_before and item.modified_at > req.modified_before:
                continue
            if req.min_size_bytes is not None and not item.is_dir and item.size_bytes < req.min_size_bytes:
                continue
            if req.max_size_bytes is not None and not item.is_dir and item.size_bytes > req.max_size_bytes:
                continue

            if not query_lower:
                matched_items.append(item)
                continue

            # Check filename or path match
            if query_lower in item.name.lower() or query_lower in item.relative_path.lower():
                item.snippet_match = f"Filename match: {item.relative_path}"
                matched_items.append(item)
                continue

            # Check indexed / file content match if enabled
            if req.search_content and not item.is_dir:
                abs_path = user_root / item.relative_path
                text_body = self._extract_searchable_text(abs_path)
                idx = text_body.lower().find(query_lower)
                if idx != -1:
                    start = max(0, idx - 50)
                    end = min(len(text_body), idx + len(query_lower) + 90)
                    snippet = re.sub(r"\s+", " ", text_body[start:end]).strip()
                    item.snippet_match = f"...{snippet}..."
                    matched_items.append(item)

        # Also query Stage 4 Document Intelligence Vault if requested
        stage4_matches: List[Dict[str, Any]] = []
        if req.include_stage4_indexed and query_lower:
            try:
                from app.services.documents.storage import document_storage

                docs = document_storage.list_documents()
                if docs:
                    passages = document_storage.retrieve_relevant_passages(
                        doc_ids=[d.id for d in docs],
                        query=req.query,
                        top_k=5,
                    )
                    for chunk, score, fname in passages:
                        stage4_matches.append(
                            {
                                "doc_id": getattr(chunk, "document_id", getattr(chunk, "doc_id", "")),
                                "filename": fname,
                                "page_number": chunk.page_number,
                                "score": score,
                                "snippet": chunk.content[:240],
                            }
                        )
            except Exception:
                pass

        return {
            "query": req.query,
            "total_matches": len(matched_items),
            "items": matched_items,
            "stage4_indexed_matches": stage4_matches,
        }

    # ------------------------------------------------------------------
    # Reading & Previewing Files (with Untrusted Quarantine)
    # ------------------------------------------------------------------
    def read_file(self, user_id: str, relative_path: str) -> WorkspaceFileReadResponse:
        user_root = self.get_user_workspace_root(user_id)
        target, rel_posix = self.resolve_safe_path(user_id, relative_path)
        if not target.exists():
            raise FileNotFoundError(f"File '{rel_posix}' does not exist.")
        if target.is_dir():
            raise ValueError(f"Path '{rel_posix}' is a folder, not a file.")

        item = self._build_file_item(user_id, user_root, target)
        ext = target.suffix.lower()
        raw_content = ""
        parsed_summary: Optional[Dict[str, Any]] = None
        tables_preview: List[Dict[str, Any]] = []

        if ext in ALLOWED_TEXT_EXTENSIONS:
            raw_content = target.read_text(encoding="utf-8", errors="replace")
            if ext == ".csv":
                try:
                    parsed = DocumentParser.parse_file(str(target), target.name)
                    parsed_summary = {
                        "file_type": parsed.file_type,
                        "total_pages": parsed.total_pages,
                        "total_characters": parsed.total_characters,
                        "metadata": parsed.metadata,
                    }
                    tables_preview = parsed.tables
                except Exception:
                    pass
        elif DocumentParser.is_supported(target.name):
            parsed = DocumentParser.parse_file(str(target), target.name)
            raw_content = "\n\n".join(
                f"--- {p.section or f'Page {p.page_number}'} ---\n{p.content}"
                for p in parsed.pages
            )
            parsed_summary = {
                "file_type": parsed.file_type,
                "total_pages": parsed.total_pages,
                "total_characters": parsed.total_characters,
                "metadata": parsed.metadata,
            }
            tables_preview = parsed.tables
        else:
            raw_content = f"[Binary file '{target.name}' ({item.size_bytes} bytes, sha256={item.sha256_hash})]"

        quarantined = (
            f"<untrusted_file_content path=\"{rel_posix}\" sha256=\"{item.sha256_hash}\">\n"
            f"{raw_content}\n"
            f"</untrusted_file_content>"
        )

        versions = self.list_file_versions(user_id, rel_posix)
        return WorkspaceFileReadResponse(
            item=item,
            content=raw_content,
            quarantined_content=quarantined,
            untrusted_content_isolated=True,
            parsed_summary=parsed_summary,
            tables_preview=tables_preview,
            versions=versions,
        )

    # ------------------------------------------------------------------
    # Version Snapshots (.nexora_versions)
    # ------------------------------------------------------------------
    def _create_version_snapshot(
        self,
        user_id: str,
        target: Path,
        rel_posix: str,
        reason: str = "auto_backup_before_edit",
    ) -> WorkspaceFileVersion:
        user_root = self.get_user_workspace_root(user_id)
        versions_dir = user_root / ".nexora_versions"
        versions_dir.mkdir(parents=True, exist_ok=True)

        sha256_val = compute_sha256_file(target)
        size_bytes = int(target.stat().st_size)
        safe_uid = self._sanitize_user_id(user_id)

        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT COALESCE(MAX(version_number), 0) AS max_v FROM file_versions WHERE user_id = ? AND relative_path = ?",
                (safe_uid, rel_posix),
            ).fetchone()
            next_v = int(row["max_v"]) + 1 if row else 1
            version_id = f"ver_{uuid.uuid4().hex[:12]}"
            storage_filename = f"{version_id}_v{next_v}_{target.name}"
            snapshot_path = versions_dir / storage_filename
            shutil.copy2(target, snapshot_path)

            # Verify snapshot integrity immediately
            if not snapshot_path.exists() or compute_sha256_file(snapshot_path) != sha256_val:
                raise RuntimeError("Failed to verify backup snapshot integrity before modifying file.")

            now_iso = utc_now().isoformat()
            with conn:
                conn.execute(
                    """
                    INSERT INTO file_versions (
                        version_id, user_id, relative_path, version_number,
                        sha256_hash, size_bytes, storage_filename, reason, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        version_id,
                        safe_uid,
                        rel_posix,
                        next_v,
                        sha256_val,
                        size_bytes,
                        storage_filename,
                        reason,
                        now_iso,
                    ),
                )

            return WorkspaceFileVersion(
                version_id=version_id,
                user_id=safe_uid,
                relative_path=rel_posix,
                version_number=next_v,
                sha256_hash=sha256_val,
                size_bytes=size_bytes,
                reason=reason,
                created_at=datetime.fromisoformat(now_iso),
            )
        finally:
            conn.close()

    def list_file_versions(self, user_id: str, relative_path: str) -> List[WorkspaceFileVersion]:
        _, rel_posix = self.resolve_safe_path(user_id, relative_path)
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """
                SELECT * FROM file_versions
                WHERE user_id = ? AND relative_path = ?
                ORDER BY version_number DESC
                """,
                (self._sanitize_user_id(user_id), rel_posix),
            ).fetchall()
            return [
                WorkspaceFileVersion(
                    version_id=r["version_id"],
                    user_id=r["user_id"],
                    relative_path=r["relative_path"],
                    version_number=int(r["version_number"]),
                    sha256_hash=r["sha256_hash"],
                    size_bytes=int(r["size_bytes"]),
                    reason=r["reason"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
                for r in rows
            ]
        finally:
            conn.close()

    def restore_version(
        self,
        user_id: str,
        relative_path: str,
        version_id: str,
    ) -> FileOperationRecord:
        user_root = self.get_user_workspace_root(user_id)
        target, rel_posix = self.resolve_safe_path(user_id, relative_path)
        safe_uid = self._sanitize_user_id(user_id)

        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM file_versions WHERE version_id = ? AND user_id = ? AND relative_path = ?",
                (version_id, safe_uid, rel_posix),
            ).fetchone()
        finally:
            conn.close()

        if not row:
            raise ValueError(f"Version '{version_id}' not found for '{rel_posix}'.")

        snapshot_path = user_root / ".nexora_versions" / row["storage_filename"]
        if not snapshot_path.exists():
            raise FileNotFoundError(f"Backup snapshot file for version '{version_id}' is missing.")

        # Preserve current state before restoring
        pre_restore_version: Optional[WorkspaceFileVersion] = None
        if target.exists() and target.is_file():
            pre_restore_version = self._create_version_snapshot(
                user_id, target, rel_posix, reason=f"auto_backup_before_restore_{version_id}"
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snapshot_path, target)

        # Verify restored SHA-256 hash matches version record
        restored_sha = compute_sha256_file(target)
        expected_sha = str(row["sha256_hash"])
        verified = target.exists() and restored_sha == expected_sha
        if not verified:
            raise RuntimeError("Version restoration failed post-write SHA-256 verification.")

        return self._record_operation(
            user_id=user_id,
            operation_type="restore_version",
            status="VERIFIED_SUCCEEDED",
            summary=f"Restored '{rel_posix}' to version #{row['version_number']} ({version_id}).",
            verified=True,
            verification_detail=f"Verified file exists and SHA-256 matches snapshot ({restored_sha[:16]}...).",
            affected_paths=[rel_posix],
            result_data={
                "relative_path": rel_posix,
                "restored_version_id": version_id,
                "restored_version_number": int(row["version_number"]),
                "sha256_hash": restored_sha,
                "pre_restore_backup_version_id": pre_restore_version.version_id if pre_restore_version else None,
            },
            rollback_recipe={
                "type": "restore_version",
                "relative_path": rel_posix,
                "version_id": pre_restore_version.version_id if pre_restore_version else None,
            }
            if pre_restore_version
            else None,
        )

    # ------------------------------------------------------------------
    # Operation Logging & Persistence
    # ------------------------------------------------------------------
    def _record_operation(
        self,
        user_id: str,
        operation_type: Any,
        status: Any,
        summary: str,
        verified: bool,
        verification_detail: str,
        affected_paths: List[str],
        result_data: Optional[Dict[str, Any]] = None,
        requires_approval: bool = False,
        approval_reason: Optional[str] = None,
        approved: Optional[bool] = None,
        preview: Optional[FileOperationPreview] = None,
        rollback_recipe: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        operation_id: Optional[str] = None,
    ) -> FileOperationRecord:
        op_id = operation_id or f"fop_{uuid.uuid4().hex[:12]}"
        safe_uid = self._sanitize_user_id(user_id)
        now_dt = utc_now()
        now_iso = now_dt.isoformat()
        safe_summary = redact_sensitive_log_text(summary)
        safe_detail = redact_sensitive_log_text(verification_detail)
        safe_err = redact_sensitive_log_text(error_message) if error_message else None

        rec = FileOperationRecord(
            operation_id=op_id,
            user_id=safe_uid,
            operation_type=operation_type,
            status=status,
            summary=safe_summary,
            verified=verified,
            verification_detail=safe_detail,
            requires_approval=requires_approval,
            approval_reason=approval_reason,
            approved=approved,
            preview=preview,
            affected_paths=affected_paths,
            result_data=result_data or {},
            rollback_supported=rollback_recipe is not None,
            rolled_back=False,
            error_message=safe_err,
            created_at=now_dt,
            updated_at=now_dt,
        )

        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO file_operations (
                        operation_id, user_id, operation_type, status, summary,
                        verified, verification_detail, requires_approval, approval_reason,
                        approved, preview_json, affected_paths_json, result_data_json,
                        rollback_recipe_json, rollback_supported, rolled_back,
                        error_message, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rec.operation_id,
                        rec.user_id,
                        rec.operation_type,
                        rec.status,
                        rec.summary,
                        1 if rec.verified else 0,
                        rec.verification_detail,
                        1 if rec.requires_approval else 0,
                        rec.approval_reason,
                        None if rec.approved is None else (1 if rec.approved else 0),
                        json.dumps(rec.preview.model_dump(mode="json")) if rec.preview else None,
                        json.dumps(rec.affected_paths),
                        json.dumps(rec.result_data),
                        json.dumps(rollback_recipe) if rollback_recipe else None,
                        1 if rec.rollback_supported else 0,
                        0,
                        rec.error_message,
                        now_iso,
                        now_iso,
                    ),
                )
        finally:
            conn.close()
        return rec

    def list_operations(self, user_id: str = "default_user", limit: int = 50) -> List[FileOperationRecord]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """
                SELECT * FROM file_operations
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (self._sanitize_user_id(user_id), limit),
            ).fetchall()
            return [self._row_to_operation(r) for r in rows]
        finally:
            conn.close()

    def get_operation(self, operation_id: str) -> Optional[FileOperationRecord]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM file_operations WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            return self._row_to_operation(row) if row else None
        finally:
            conn.close()

    def _row_to_operation(self, row: sqlite3.Row) -> FileOperationRecord:
        preview_obj = (
            FileOperationPreview(**json.loads(row["preview_json"]))
            if row["preview_json"]
            else None
        )
        return FileOperationRecord(
            operation_id=row["operation_id"],
            user_id=row["user_id"],
            operation_type=row["operation_type"],
            status=row["status"],
            summary=row["summary"],
            verified=bool(row["verified"]),
            verification_detail=row["verification_detail"],
            requires_approval=bool(row["requires_approval"]),
            approval_reason=row["approval_reason"],
            approved=None if row["approved"] is None else bool(row["approved"]),
            preview=preview_obj,
            affected_paths=json.loads(row["affected_paths_json"] or "[]"),
            result_data=json.loads(row["result_data_json"] or "{}"),
            rollback_supported=bool(row["rollback_supported"]),
            rolled_back=bool(row["rolled_back"]),
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    # ------------------------------------------------------------------
    # Creating Folders, Creating & Editing Files
    # ------------------------------------------------------------------
    def create_folder(self, req: FileCreateFolderRequest) -> FileOperationRecord:
        target, rel_posix = self.resolve_safe_path(req.user_id, req.relative_path)
        if target.exists() and not target.is_dir():
            raise ValueError(f"Cannot create folder '{rel_posix}': a file already exists at that path.")

        already_existed = target.exists()
        target.mkdir(parents=True, exist_ok=True)
        verified = target.exists() and target.is_dir()
        if not verified:
            raise RuntimeError(f"Failed to verify folder creation at '{rel_posix}'.")

        return self._record_operation(
            user_id=req.user_id,
            operation_type="create_folder",
            status="VERIFIED_SUCCEEDED",
            summary=f"Folder '{rel_posix}' created and verified in workspace.",
            verified=True,
            verification_detail=f"Verified directory '{rel_posix}' exists on disk.",
            affected_paths=[rel_posix],
            result_data={"relative_path": rel_posix, "already_existed": already_existed},
            rollback_recipe={"type": "remove_created_folder", "relative_path": rel_posix}
            if not already_existed
            else None,
        )

    def _write_formatted_file_bytes(
        self,
        target: Path,
        ext: str,
        content: str,
        structured_rows: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        ext = ext.lower()
        if ext == ".json":
            # Validate JSON content or serialize structured_rows
            if structured_rows is not None and not content.strip():
                parsed_json = structured_rows
            else:
                try:
                    parsed_json = json.loads(content)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON syntax for '{target.name}': {exc.msg}") from exc
            formatted = json.dumps(parsed_json, indent=2, ensure_ascii=False)
            target.write_text(formatted, encoding="utf-8")
            return

        if ext == ".csv":
            if structured_rows:
                headers = list(structured_rows[0].keys())
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=headers, lineterminator="\n")
                writer.writeheader()
                writer.writerows(structured_rows)
                target.write_text(buf.getvalue(), encoding="utf-8")
            else:
                target.write_text(content, encoding="utf-8")
            return

        if ext == ".docx":
            if not docx:
                raise RuntimeError("python-docx is required to generate .docx files.")
            document = docx.Document()
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("# "):
                    document.add_heading(stripped[2:].strip(), level=1)
                elif stripped.startswith("## "):
                    document.add_heading(stripped[3:].strip(), level=2)
                elif stripped.startswith("### "):
                    document.add_heading(stripped[4:].strip(), level=3)
                else:
                    document.add_paragraph(line)
            if structured_rows:
                headers = list(structured_rows[0].keys())
                tbl = document.add_table(rows=1, cols=len(headers))
                for idx, h in enumerate(headers):
                    tbl.rows[0].cells[idx].text = str(h)
                for row_dict in structured_rows:
                    cells = tbl.add_row().cells
                    for idx, h in enumerate(headers):
                        cells[idx].text = str(row_dict.get(h, ""))
            document.save(str(target))
            return

        if ext == ".xlsx":
            if not openpyxl:
                raise RuntimeError("openpyxl is required to generate .xlsx spreadsheets.")
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Sheet1"
            if structured_rows:
                headers = list(structured_rows[0].keys())
                ws.append(headers)
                for row_dict in structured_rows:
                    ws.append([row_dict.get(h, "") for h in headers])
            else:
                reader = csv.reader(io.StringIO(content))
                rows_written = 0
                for row in reader:
                    ws.append(row)
                    rows_written += 1
                if rows_written == 0 and content.strip():
                    for line in content.splitlines():
                        ws.append([line])
            wb.save(str(target))
            return

        if ext in ALLOWED_TEXT_EXTENSIONS:
            target.write_text(content, encoding="utf-8")
            return

        raise ValueError(f"Direct creation/editing is not supported for extension '{ext}'.")

    def write_file(self, req: FileWriteRequest) -> FileOperationRecord:
        target, rel_posix = self.resolve_safe_path(
            req.user_id, req.relative_path, require_valid_file_extension=True
        )
        ext = target.suffix.lower()

        encoded_len = len((req.content or "").encode("utf-8"))
        if encoded_len > settings.file_workspace_max_file_size_bytes:
            raise ValueError(
                f"Content size ({encoded_len} bytes) exceeds workspace limit ({settings.file_workspace_max_file_size_bytes} bytes)."
            )

        existed_before = target.exists()
        if existed_before and target.is_dir():
            raise ValueError(f"Path '{rel_posix}' is an existing directory.")

        if existed_before and not req.overwrite:
            raise FileExistsError(
                f"File '{rel_posix}' already exists. Enable overwrite to update or replace it."
            )

        # Require explicit confirmation when overwriting an existing file unless confirmed_overwrite=True
        if existed_before and req.overwrite and not req.confirmed_overwrite:
            existing_size = int(target.stat().st_size)
            preview = FileOperationPreview(
                operation_type="edit_file",
                risk_level="medium",
                requires_approval=True,
                approval_reason=f"Overwriting existing file '{rel_posix}' ({existing_size} bytes) requires confirmation. An automatic backup version will be saved.",
                affected_count=1,
                total_bytes_affected=encoded_len,
                planned_changes=[
                    FilePlannedChange(
                        action="overwrite_with_backup",
                        source_path=rel_posix,
                        destination_path=rel_posix,
                        size_bytes=encoded_len,
                        reason=req.backup_reason,
                        overwrites_existing=True,
                    )
                ],
                rollback_supported=True,
            )
            return self._record_operation(
                user_id=req.user_id,
                operation_type="edit_file",
                status="WAITING_FOR_APPROVAL",
                summary=f"Waiting for user approval to overwrite '{rel_posix}'.",
                verified=False,
                verification_detail="Pending explicit overwrite confirmation.",
                affected_paths=[rel_posix],
                result_data={
                    "pending_request_type": "write_file",
                    "request_payload": req.model_dump(mode="json"),
                },
                requires_approval=True,
                approval_reason=preview.approval_reason,
                preview=preview,
            )

        backup_version: Optional[WorkspaceFileVersion] = None
        if existed_before:
            backup_version = self._create_version_snapshot(
                req.user_id, target, rel_posix, reason=req.backup_reason
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        self._write_formatted_file_bytes(target, ext, req.content, req.structured_rows)

        # Post-write verification
        if not target.exists() or not target.is_file():
            raise RuntimeError(f"File write verification failed: '{rel_posix}' not found on disk.")

        new_sha256 = compute_sha256_file(target)
        new_size = int(target.stat().st_size)
        op_type = "edit_file" if existed_before else "create_file"

        rollback_recipe = (
            {
                "type": "restore_version",
                "relative_path": rel_posix,
                "version_id": backup_version.version_id,
            }
            if backup_version
            else {
                "type": "trash_created_file",
                "relative_path": rel_posix,
            }
        )

        return self._record_operation(
            user_id=req.user_id,
            operation_type=op_type,
            status="VERIFIED_SUCCEEDED",
            summary=(
                f"Updated '{rel_posix}' ({new_size} bytes, backup #{backup_version.version_number} saved)."
                if backup_version
                else f"Created '{rel_posix}' ({new_size} bytes, sha256={new_sha256[:12]}...)."
            ),
            verified=True,
            verification_detail=f"Verified file exists on disk ({new_size} bytes, SHA-256={new_sha256}).",
            affected_paths=[rel_posix],
            result_data={
                "relative_path": rel_posix,
                "size_bytes": new_size,
                "sha256_hash": new_sha256,
                "backup_version_id": backup_version.version_id if backup_version else None,
                "backup_version_number": backup_version.version_number if backup_version else None,
            },
            rollback_recipe=rollback_recipe,
        )

    # ------------------------------------------------------------------
    # Rename, Copy, Move
    # ------------------------------------------------------------------
    def transfer_item(self, req: FileTransferRequest) -> FileOperationRecord:
        src, src_rel = self.resolve_safe_path(req.user_id, req.source_path)
        dst, dst_rel = self.resolve_safe_path(
            req.user_id,
            req.destination_path,
            require_valid_file_extension=src.is_file() if src.exists() else False,
        )

        if not src.exists():
            raise FileNotFoundError(f"Source path '{src_rel}' does not exist.")
        if src == dst:
            raise ValueError("Source and destination paths are identical.")

        dst_existed = dst.exists()
        if dst_existed and not req.overwrite:
            raise FileExistsError(
                f"Destination '{dst_rel}' already exists. Enable overwrite to replace it."
            )

        op_type_map = {
            "rename": "rename_item",
            "copy": "copy_item",
            "move": "move_item",
        }
        op_type = op_type_map[req.action]

        if dst_existed and req.overwrite and not req.confirmed_overwrite:
            src_size = 0 if src.is_dir() else int(src.stat().st_size)
            preview = FileOperationPreview(
                operation_type=op_type,  # type: ignore[arg-type]
                risk_level="medium",
                requires_approval=True,
                approval_reason=f"'{req.action}' will overwrite existing file '{dst_rel}'. Explicit confirmation required.",
                affected_count=2,
                total_bytes_affected=src_size,
                planned_changes=[
                    FilePlannedChange(
                        action=req.action,
                        source_path=src_rel,
                        destination_path=dst_rel,
                        size_bytes=src_size,
                        reason=f"{req.action} with overwrite",
                        overwrites_existing=True,
                    )
                ],
                rollback_supported=True,
            )
            return self._record_operation(
                user_id=req.user_id,
                operation_type=op_type,
                status="WAITING_FOR_APPROVAL",
                summary=f"Waiting for approval to {req.action} '{src_rel}' -> '{dst_rel}' (overwrites existing).",
                verified=False,
                verification_detail="Pending explicit overwrite confirmation.",
                affected_paths=[src_rel, dst_rel],
                result_data={
                    "pending_request_type": "transfer_item",
                    "request_payload": req.model_dump(mode="json"),
                },
                requires_approval=True,
                approval_reason=preview.approval_reason,
                preview=preview,
            )

        backup_ver: Optional[WorkspaceFileVersion] = None
        if dst_existed and dst.is_file():
            backup_ver = self._create_version_snapshot(
                req.user_id, dst, dst_rel, reason=f"auto_backup_before_{req.action}_overwrite"
            )

        src_sha_before = None if src.is_dir() else compute_sha256_file(src)
        dst.parent.mkdir(parents=True, exist_ok=True)

        if req.action == "copy":
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            verified = dst.exists() and (dst.is_dir() or compute_sha256_file(dst) == src_sha_before)
            rollback_recipe = {"type": "trash_created_file", "relative_path": dst_rel}
        else:
            # rename or move
            shutil.move(str(src), str(dst))
            verified = (
                dst.exists()
                and not src.exists()
                and (dst.is_dir() or compute_sha256_file(dst) == src_sha_before)
            )
            rollback_recipe = {
                "type": "reverse_move",
                "from_path": dst_rel,
                "to_path": src_rel,
                "overwritten_backup_version_id": backup_ver.version_id if backup_ver else None,
            }

        if not verified:
            raise RuntimeError(f"Failed post-{req.action} verification for '{src_rel}' -> '{dst_rel}'.")

        return self._record_operation(
            user_id=req.user_id,
            operation_type=op_type,
            status="VERIFIED_SUCCEEDED",
            summary=f"Successfully executed {req.action}: '{src_rel}' -> '{dst_rel}'.",
            verified=True,
            verification_detail=(
                f"Verified destination '{dst_rel}' exists and SHA-256 integrity matches ({src_sha_before[:16] if src_sha_before else 'directory'})."
            ),
            affected_paths=[src_rel, dst_rel],
            result_data={
                "action": req.action,
                "source_path": src_rel,
                "destination_path": dst_rel,
                "sha256_hash": src_sha_before,
            },
            rollback_recipe=rollback_recipe,
        )

    # ------------------------------------------------------------------
    # Format Conversion
    # ------------------------------------------------------------------
    def convert_file(self, req: FileConvertRequest) -> FileOperationRecord:
        src, src_rel = self.resolve_safe_path(req.user_id, req.source_path)
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"Source file '{src_rel}' not found.")

        src_ext = src.suffix.lower()
        target_ext = f".{req.target_format.lower().lstrip('.')}"
        supported = get_supported_conversions(src_ext)
        if req.target_format.lower() not in supported:
            raise ValueError(
                f"Conversion from '{src_ext}' to '.{req.target_format}' is not supported. Supported targets: {supported}"
            )

        default_dst = src.with_suffix(target_ext)
        user_root = self.get_user_workspace_root(req.user_id)
        default_dst_rel = default_dst.relative_to(user_root).as_posix()
        dst_path_str = req.destination_path or default_dst_rel
        dst, dst_rel = self.resolve_safe_path(
            req.user_id, dst_path_str, require_valid_file_extension=True
        )

        dst_existed = dst.exists()
        if dst_existed and not req.overwrite:
            raise FileExistsError(
                f"Converted target '{dst_rel}' already exists. Enable overwrite to replace it."
            )

        if dst_existed and req.overwrite and not req.confirmed_overwrite:
            preview = FileOperationPreview(
                operation_type="convert_file",
                risk_level="medium",
                requires_approval=True,
                approval_reason=f"Converting '{src_rel}' will overwrite existing file '{dst_rel}'. Confirmation required.",
                affected_count=1,
                total_bytes_affected=int(src.stat().st_size),
                planned_changes=[
                    FilePlannedChange(
                        action=f"convert_{src_ext.lstrip('.')}_to_{req.target_format}",
                        source_path=src_rel,
                        destination_path=dst_rel,
                        size_bytes=int(src.stat().st_size),
                        reason="Format conversion overwrite",
                        overwrites_existing=True,
                    )
                ],
                rollback_supported=True,
            )
            return self._record_operation(
                user_id=req.user_id,
                operation_type="convert_file",
                status="WAITING_FOR_APPROVAL",
                summary=f"Waiting for approval to overwrite '{dst_rel}' during conversion.",
                verified=False,
                verification_detail="Pending explicit overwrite confirmation.",
                affected_paths=[src_rel, dst_rel],
                result_data={
                    "pending_request_type": "convert_file",
                    "request_payload": req.model_dump(mode="json"),
                },
                requires_approval=True,
                approval_reason=preview.approval_reason,
                preview=preview,
            )

        backup_ver: Optional[WorkspaceFileVersion] = None
        if dst_existed and dst.is_file():
            backup_ver = self._create_version_snapshot(
                req.user_id, dst, dst_rel, reason="auto_backup_before_convert_overwrite"
            )

        # Extract normalized intermediate representation (rows or text/pages)
        rows_data: List[Dict[str, Any]] = []
        text_content = ""

        if src_ext == ".csv":
            with open(src, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                rows_data = [dict(r) for r in reader]
            text_content = src.read_text(encoding="utf-8", errors="replace")
        elif src_ext == ".json":
            raw_json = json.loads(src.read_text(encoding="utf-8", errors="replace"))
            if isinstance(raw_json, list) and all(isinstance(x, dict) for x in raw_json):
                rows_data = raw_json
            elif isinstance(raw_json, dict):
                rows_data = [raw_json]
            text_content = json.dumps(raw_json, indent=2, ensure_ascii=False)
        elif src_ext == ".xlsx":
            if not openpyxl:
                raise RuntimeError("openpyxl is required to convert from .xlsx")
            wb = openpyxl.load_workbook(str(src), data_only=True)
            ws = wb.active
            all_rows = list(ws.iter_rows(values_only=True))
            if all_rows:
                headers = [str(h if h is not None else f"col_{i}") for i, h in enumerate(all_rows[0])]
                for r in all_rows[1:]:
                    rows_data.append(
                        {headers[i]: ("" if r[i] is None else r[i]) for i in range(len(headers))}
                    )
            parsed = DocumentParser.parse_file(str(src), src.name)
            text_content = "\n\n".join(p.content for p in parsed.pages)
        elif src_ext in (".docx", ".pdf"):
            parsed = DocumentParser.parse_file(str(src), src.name)
            text_content = "\n\n".join(p.content for p in parsed.pages)
            rows_data = [
                {
                    "page_number": p.page_number,
                    "section": p.section or f"Page {p.page_number}",
                    "content": p.content,
                }
                for p in parsed.pages
            ]
        else:
            # .txt or .md
            text_content = src.read_text(encoding="utf-8", errors="replace")
            rows_data = [
                {"line_number": idx + 1, "text": line}
                for idx, line in enumerate(text_content.splitlines())
                if line.strip()
            ]

        # Render to target format
        dst.parent.mkdir(parents=True, exist_ok=True)
        if target_ext == ".json":
            payload = rows_data if rows_data else {"source": src.name, "content": text_content}
            dst.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        elif target_ext == ".csv":
            if not rows_data:
                rows_data = [{"content": text_content}]
            self._write_formatted_file_bytes(dst, ".csv", "", structured_rows=rows_data)
        elif target_ext == ".xlsx":
            self._write_formatted_file_bytes(
                dst, ".xlsx", text_content, structured_rows=rows_data if rows_data else None
            )
        elif target_ext == ".docx":
            self._write_formatted_file_bytes(
                dst, ".docx", text_content, structured_rows=rows_data if src_ext in (".csv", ".xlsx") else None
            )
        elif target_ext == ".md":
            if rows_data and src_ext in (".csv", ".xlsx", ".json"):
                headers = list(rows_data[0].keys())
                md_lines = [
                    f"# Converted Dataset: {src.name}",
                    "",
                    "| " + " | ".join(str(h) for h in headers) + " |",
                    "| " + " | ".join(["---"] * len(headers)) + " |",
                ]
                for r in rows_data:
                    md_lines.append("| " + " | ".join(str(r.get(h, "")) for h in headers) + " |")
                dst.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
            else:
                dst.write_text(f"# {src.stem}\n\n{text_content}\n", encoding="utf-8")
        elif target_ext == ".txt":
            dst.write_text(text_content, encoding="utf-8")

        if not dst.exists() or not dst.is_file():
            raise RuntimeError(f"Conversion verification failed: output '{dst_rel}' was not created.")

        out_sha = compute_sha256_file(dst)
        out_size = int(dst.stat().st_size)

        return self._record_operation(
            user_id=req.user_id,
            operation_type="convert_file",
            status="VERIFIED_SUCCEEDED",
            summary=f"Converted '{src_rel}' -> '{dst_rel}' ({out_size} bytes).",
            verified=True,
            verification_detail=f"Verified output '{dst_rel}' exists ({out_size} bytes, SHA-256={out_sha[:16]}...).",
            affected_paths=[src_rel, dst_rel],
            result_data={
                "source_path": src_rel,
                "destination_path": dst_rel,
                "target_format": req.target_format,
                "size_bytes": out_size,
                "sha256_hash": out_sha,
            },
            rollback_recipe=(
                {
                    "type": "restore_version",
                    "relative_path": dst_rel,
                    "version_id": backup_ver.version_id,
                }
                if backup_ver
                else {"type": "trash_created_file", "relative_path": dst_rel}
            ),
        )

    # ------------------------------------------------------------------
    # Duplicate File Discovery & Safe Deduplication
    # ------------------------------------------------------------------
    def find_duplicates(self, user_id: str = "default_user", directory: str = "") -> List[DuplicateFileGroup]:
        items = self.list_items(user_id=user_id, directory=directory, recursive=True)
        by_hash: Dict[str, List[WorkspaceFileItem]] = {}
        for item in items:
            if item.is_dir or not item.sha256_hash:
                continue
            by_hash.setdefault(item.sha256_hash, []).append(item)

        groups: List[DuplicateFileGroup] = []
        for sha, group_items in by_hash.items():
            if len(group_items) < 2:
                continue
            # Sort so shallowest / earliest path is kept as primary
            group_items.sort(key=lambda x: (len(x.relative_path.split("/")), x.relative_path))
            primary = group_items[0]
            dups = [g.relative_path for g in group_items[1:]]
            wasted = primary.size_bytes * len(dups)
            groups.append(
                DuplicateFileGroup(
                    sha256_hash=sha,
                    size_bytes=primary.size_bytes,
                    duplicate_count=len(dups),
                    wasted_bytes=wasted,
                    primary_file=primary.relative_path,
                    duplicate_files=dups,
                )
            )
        groups.sort(key=lambda g: g.wasted_bytes, reverse=True)
        return groups

    def cleanup_duplicates(self, req: FileDuplicateCleanupRequest) -> FileOperationRecord:
        groups = self.find_duplicates(user_id=req.user_id, directory=req.directory)
        planned: List[FilePlannedChange] = []
        dup_paths: List[str] = []
        total_bytes = 0

        for grp in groups:
            for dup_rel in grp.duplicate_files:
                planned.append(
                    FilePlannedChange(
                        action="move_duplicate_to_trash",
                        source_path=dup_rel,
                        destination_path=f".nexora_trash/{Path(dup_rel).name}",
                        size_bytes=grp.size_bytes,
                        reason=f"Exact SHA-256 duplicate of '{grp.primary_file}' ({grp.sha256_hash[:12]}...)",
                        overwrites_existing=False,
                    )
                )
                dup_paths.append(dup_rel)
                total_bytes += grp.size_bytes

        preview = FileOperationPreview(
            operation_type="cleanup_duplicates",
            risk_level="medium" if dup_paths else "low",
            requires_approval=bool(dup_paths),
            approval_reason=(
                f"Moving {len(dup_paths)} duplicate file(s) ({total_bytes} bytes) to Recoverable Trash requires confirmation."
                if dup_paths
                else None
            ),
            affected_count=len(dup_paths),
            total_bytes_affected=total_bytes,
            planned_changes=planned,
            rollback_supported=True,
        )

        if not dup_paths:
            return self._record_operation(
                user_id=req.user_id,
                operation_type="cleanup_duplicates",
                status="VERIFIED_SUCCEEDED",
                summary="No duplicate files found in workspace.",
                verified=True,
                verification_detail="Scanned all workspace files by SHA-256 hash; 0 duplicates detected.",
                affected_paths=[],
                result_data={"duplicates_removed": 0, "reclaimed_bytes": 0},
                preview=preview,
            )

        if req.preview_only:
            return self._record_operation(
                user_id=req.user_id,
                operation_type="cleanup_duplicates",
                status="SIMULATED",
                summary=f"Previewed cleanup of {len(dup_paths)} duplicate file(s) ({total_bytes} bytes).",
                verified=True,
                verification_detail="Simulation preview only; no files were modified.",
                affected_paths=dup_paths,
                result_data={"groups": [g.model_dump(mode="json") for g in groups]},
                preview=preview,
            )

        if not req.confirmed:
            return self._record_operation(
                user_id=req.user_id,
                operation_type="cleanup_duplicates",
                status="WAITING_FOR_APPROVAL",
                summary=f"Waiting for user confirmation to move {len(dup_paths)} duplicate file(s) to Trash.",
                verified=False,
                verification_detail="Pending explicit approval before moving duplicate files to Trash.",
                affected_paths=dup_paths,
                result_data={
                    "pending_request_type": "cleanup_duplicates",
                    "request_payload": req.model_dump(mode="json"),
                },
                requires_approval=True,
                approval_reason=preview.approval_reason,
                preview=preview,
            )

        # Execute move to trash
        trashed_ids: List[str] = []
        for dup_rel in dup_paths:
            t_item = self._move_single_path_to_trash(
                req.user_id, dup_rel, reason="duplicate_sha256_cleanup"
            )
            trashed_ids.append(t_item.trash_id)

        return self._record_operation(
            user_id=req.user_id,
            operation_type="cleanup_duplicates",
            status="VERIFIED_SUCCEEDED",
            summary=f"Moved {len(trashed_ids)} duplicate file(s) ({total_bytes} bytes) to Recoverable Trash.",
            verified=True,
            verification_detail=f"Verified all {len(trashed_ids)} duplicate files were moved to .nexora_trash and primary files remain intact.",
            affected_paths=dup_paths,
            result_data={
                "duplicates_removed": len(trashed_ids),
                "reclaimed_bytes": total_bytes,
                "trash_ids": trashed_ids,
            },
            preview=preview,
            rollback_recipe={"type": "restore_trash_batch", "trash_ids": trashed_ids},
        )

    # ------------------------------------------------------------------
    # Rule-Based Workspace Organization
    # ------------------------------------------------------------------
    def _compute_target_folder_for_item(
        self,
        item: WorkspaceFileItem,
        strategy: str,
        custom_map: Dict[str, str],
    ) -> str:
        ext_clean = item.extension.lower().lstrip(".")
        if strategy == "custom_rules" and custom_map:
            folder = custom_map.get(item.extension.lower()) or custom_map.get(ext_clean)
            if folder:
                return folder.strip("/")
        if strategy == "by_extension":
            return f"EXT_{ext_clean.upper()}" if ext_clean else "Other"
        if strategy == "by_date_month":
            return item.modified_at.strftime("%Y-%m")
        # Default: by_category
        cat_folders = {
            "document": "Documents",
            "spreadsheet": "Spreadsheets",
            "data": "Data",
            "markdown_text": "Notes",
            "code": "Code",
            "image": "Images",
        }
        return cat_folders.get(item.category, "Misc")

    def organize_workspace(self, req: FileOrganizeRequest) -> FileOperationRecord:
        user_root = self.get_user_workspace_root(req.user_id)
        base_dir, base_rel = self.resolve_safe_path(req.user_id, req.directory, allow_root=True)
        if not base_dir.exists() or not base_dir.is_dir():
            raise FileNotFoundError(f"Directory '{req.directory}' not found.")

        # List direct files in base_dir to organize into structured subfolders
        direct_items = self.list_items(user_id=req.user_id, directory=base_rel, recursive=False)
        files_to_organize = [it for it in direct_items if not it.is_dir]

        if len(files_to_organize) > settings.file_workspace_max_bulk_files:
            raise ValueError(
                f"Bulk operation exceeds maximum allowed files ({settings.file_workspace_max_bulk_files})."
            )

        planned: List[FilePlannedChange] = []
        total_bytes = 0
        for item in files_to_organize:
            subfolder = self._compute_target_folder_for_item(
                item, req.strategy, req.custom_extension_map
            )
            dst_rel = f"{base_rel}/{subfolder}/{item.name}".lstrip("/")
            if dst_rel == item.relative_path:
                continue
            dst_abs = user_root / dst_rel
            planned.append(
                FilePlannedChange(
                    action="organize_move",
                    source_path=item.relative_path,
                    destination_path=dst_rel,
                    size_bytes=item.size_bytes,
                    reason=f"Rule '{req.strategy}' -> {subfolder}/",
                    overwrites_existing=dst_abs.exists(),
                )
            )
            total_bytes += item.size_bytes

        needs_approval = len(planned) >= settings.file_workspace_bulk_approval_threshold or any(
            p.overwrites_existing for p in planned
        )
        preview = FileOperationPreview(
            operation_type="organize_workspace",
            risk_level="medium" if needs_approval else "low",
            requires_approval=needs_approval,
            approval_reason=(
                f"Organizing {len(planned)} files across folders using strategy '{req.strategy}' requires user confirmation."
                if needs_approval
                else None
            ),
            affected_count=len(planned),
            total_bytes_affected=total_bytes,
            planned_changes=planned,
            rollback_supported=True,
        )

        if req.preview_only:
            return self._record_operation(
                user_id=req.user_id,
                operation_type="organize_workspace",
                status="SIMULATED",
                summary=f"Previewed workspace organization ({len(planned)} file moves planned via '{req.strategy}').",
                verified=True,
                verification_detail="Preview mode only; no files were moved.",
                affected_paths=[p.source_path for p in planned],
                result_data={"strategy": req.strategy, "planned_count": len(planned)},
                preview=preview,
            )

        if needs_approval and not req.confirmed:
            return self._record_operation(
                user_id=req.user_id,
                operation_type="organize_workspace",
                status="WAITING_FOR_APPROVAL",
                summary=f"Waiting for user confirmation to organize {len(planned)} files ({req.strategy}).",
                verified=False,
                verification_detail="Pending explicit user confirmation for bulk organization.",
                affected_paths=[p.source_path for p in planned],
                result_data={
                    "pending_request_type": "organize_workspace",
                    "request_payload": req.model_dump(mode="json"),
                },
                requires_approval=True,
                approval_reason=preview.approval_reason,
                preview=preview,
            )

        moved_pairs: List[Dict[str, str]] = []
        for change in planned:
            if not change.destination_path:
                continue
            src_abs, src_r = self.resolve_safe_path(req.user_id, change.source_path)
            dst_abs, dst_r = self.resolve_safe_path(req.user_id, change.destination_path)
            if not src_abs.exists():
                continue
            dst_abs.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_abs), str(dst_abs))
            if not dst_abs.exists():
                raise RuntimeError(f"Failed to verify moved file '{dst_r}'.")
            moved_pairs.append({"from_path": dst_r, "to_path": src_r})

        return self._record_operation(
            user_id=req.user_id,
            operation_type="organize_workspace",
            status="VERIFIED_SUCCEEDED",
            summary=f"Organized {len(moved_pairs)} file(s) using strategy '{req.strategy}'.",
            verified=True,
            verification_detail=f"Verified all {len(moved_pairs)} file(s) exist at their organized destination paths.",
            affected_paths=[m["from_path"] for m in moved_pairs],
            result_data={"strategy": req.strategy, "moved_files": moved_pairs},
            preview=preview,
            rollback_recipe={"type": "reverse_bulk_moves", "moves": moved_pairs} if moved_pairs else None,
        )

    # ------------------------------------------------------------------
    # Recoverable Trash (.nexora_trash)
    # ------------------------------------------------------------------
    def _move_single_path_to_trash(
        self,
        user_id: str,
        relative_path: str,
        reason: str = "user_deleted",
    ) -> WorkspaceTrashItem:
        user_root = self.get_user_workspace_root(user_id)
        target, rel_posix = self.resolve_safe_path(user_id, relative_path)
        if not target.exists():
            raise FileNotFoundError(f"Path '{rel_posix}' does not exist.")

        trash_dir = user_root / ".nexora_trash"
        trash_dir.mkdir(parents=True, exist_ok=True)

        is_dir = target.is_dir()
        size_bytes = 0 if is_dir else int(target.stat().st_size)
        sha256_val = None if is_dir else compute_sha256_file(target)
        trash_id = f"tr_{uuid.uuid4().hex[:12]}"
        storage_name = f"{trash_id}_{target.name}"
        trash_target = trash_dir / storage_name

        shutil.move(str(target), str(trash_target))
        if not trash_target.exists() or target.exists():
            raise RuntimeError(f"Failed to verify moving '{rel_posix}' to Recoverable Trash.")

        now_iso = utc_now().isoformat()
        safe_uid = self._sanitize_user_id(user_id)
        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO trash_items (
                        trash_id, user_id, original_path, name, is_dir,
                        size_bytes, sha256_hash, storage_name, reason, deleted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trash_id,
                        safe_uid,
                        rel_posix,
                        target.name,
                        1 if is_dir else 0,
                        size_bytes,
                        sha256_val,
                        storage_name,
                        reason,
                        now_iso,
                    ),
                )
        finally:
            conn.close()

        return WorkspaceTrashItem(
            trash_id=trash_id,
            user_id=safe_uid,
            original_path=rel_posix,
            name=target.name,
            is_dir=is_dir,
            size_bytes=size_bytes,
            sha256_hash=sha256_val,
            reason=reason,
            deleted_at=datetime.fromisoformat(now_iso),
        )

    def delete_to_trash(self, req: FileDeleteRequest) -> FileOperationRecord:
        if len(req.paths) > settings.file_workspace_max_bulk_files:
            raise ValueError(
                f"Cannot delete more than {settings.file_workspace_max_bulk_files} items in a single operation."
            )

        planned: List[FilePlannedChange] = []
        normalized_paths: List[str] = []
        total_bytes = 0

        for p in req.paths:
            target, rel_posix = self.resolve_safe_path(req.user_id, p)
            if not target.exists():
                raise FileNotFoundError(f"Path '{rel_posix}' does not exist.")
            sz = 0 if target.is_dir() else int(target.stat().st_size)
            planned.append(
                FilePlannedChange(
                    action="move_to_recoverable_trash",
                    source_path=rel_posix,
                    destination_path=f".nexora_trash/{target.name}",
                    size_bytes=sz,
                    reason=req.reason,
                    overwrites_existing=False,
                )
            )
            normalized_paths.append(rel_posix)
            total_bytes += sz

        preview = FileOperationPreview(
            operation_type="delete_to_trash",
            risk_level="high" if len(normalized_paths) > 1 else "medium",
            requires_approval=True,
            approval_reason=f"Deleting {len(normalized_paths)} item(s) ({total_bytes} bytes) requires explicit user confirmation. Items will be moved to Recoverable Trash.",
            affected_count=len(normalized_paths),
            total_bytes_affected=total_bytes,
            planned_changes=planned,
            rollback_supported=True,
        )

        if req.preview_only:
            return self._record_operation(
                user_id=req.user_id,
                operation_type="delete_to_trash",
                status="SIMULATED",
                summary=f"Previewed moving {len(normalized_paths)} item(s) to Recoverable Trash.",
                verified=True,
                verification_detail="Preview only; no files were deleted.",
                affected_paths=normalized_paths,
                preview=preview,
            )

        if not req.confirmed:
            return self._record_operation(
                user_id=req.user_id,
                operation_type="delete_to_trash",
                status="WAITING_FOR_APPROVAL",
                summary=f"Waiting for user approval to move {len(normalized_paths)} item(s) to Trash.",
                verified=False,
                verification_detail="Pending explicit confirmation before moving items to Trash.",
                affected_paths=normalized_paths,
                result_data={
                    "pending_request_type": "delete_to_trash",
                    "request_payload": req.model_dump(mode="json"),
                },
                requires_approval=True,
                approval_reason=preview.approval_reason,
                preview=preview,
            )

        trashed_items: List[WorkspaceTrashItem] = []
        for rel_p in normalized_paths:
            trashed_items.append(self._move_single_path_to_trash(req.user_id, rel_p, reason=req.reason))

        trash_ids = [t.trash_id for t in trashed_items]
        return self._record_operation(
            user_id=req.user_id,
            operation_type="delete_to_trash",
            status="VERIFIED_SUCCEEDED",
            summary=f"Moved {len(trashed_items)} item(s) to Recoverable Trash.",
            verified=True,
            verification_detail=f"Verified {len(trashed_items)} item(s) moved to .nexora_trash and removed from active workspace.",
            affected_paths=normalized_paths,
            result_data={
                "trash_ids": trash_ids,
                "trashed_items": [t.model_dump(mode="json") for t in trashed_items],
            },
            preview=preview,
            rollback_recipe={"type": "restore_trash_batch", "trash_ids": trash_ids},
        )

    def list_trash(self, user_id: str = "default_user") -> List[WorkspaceTrashItem]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM trash_items WHERE user_id = ? ORDER BY deleted_at DESC",
                (self._sanitize_user_id(user_id),),
            ).fetchall()
            return [
                WorkspaceTrashItem(
                    trash_id=r["trash_id"],
                    user_id=r["user_id"],
                    original_path=r["original_path"],
                    name=r["name"],
                    is_dir=bool(r["is_dir"]),
                    size_bytes=int(r["size_bytes"]),
                    sha256_hash=r["sha256_hash"],
                    reason=r["reason"],
                    deleted_at=datetime.fromisoformat(r["deleted_at"]),
                )
                for r in rows
            ]
        finally:
            conn.close()

    def restore_from_trash(self, user_id: str, trash_id: str) -> FileOperationRecord:
        user_root = self.get_user_workspace_root(user_id)
        safe_uid = self._sanitize_user_id(user_id)

        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM trash_items WHERE trash_id = ? AND user_id = ?",
                (trash_id, safe_uid),
            ).fetchone()
        finally:
            conn.close()

        if not row:
            raise ValueError(f"Trash item '{trash_id}' not found.")

        trash_source = user_root / ".nexora_trash" / row["storage_name"]
        if not trash_source.exists():
            raise FileNotFoundError(f"Trashed payload for '{trash_id}' is missing from .nexora_trash.")

        dst, dst_rel = self.resolve_safe_path(user_id, row["original_path"])
        if dst.exists():
            # Avoid silently clobbering a newly created file at the same path
            dst = dst.with_name(f"{dst.stem}_restored_{trash_id[-4:]}{dst.suffix}")
            dst_rel = dst.relative_to(user_root).as_posix()

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(trash_source), str(dst))

        expected_sha = row["sha256_hash"]
        actual_sha = None if dst.is_dir() else compute_sha256_file(dst)
        verified = dst.exists() and (expected_sha is None or actual_sha == expected_sha)
        if not verified:
            raise RuntimeError(f"Failed post-restore SHA-256 verification for '{dst_rel}'.")

        conn = self._get_conn()
        try:
            with conn:
                conn.execute("DELETE FROM trash_items WHERE trash_id = ?", (trash_id,))
        finally:
            conn.close()

        return self._record_operation(
            user_id=user_id,
            operation_type="restore_from_trash",
            status="VERIFIED_SUCCEEDED",
            summary=f"Restored '{dst_rel}' from Recoverable Trash.",
            verified=True,
            verification_detail=f"Verified '{dst_rel}' exists in workspace and matches original SHA-256.",
            affected_paths=[dst_rel],
            result_data={"trash_id": trash_id, "restored_path": dst_rel, "sha256_hash": actual_sha},
        )

    # ------------------------------------------------------------------
    # Approving Pending Operations & Rollback Execution
    # ------------------------------------------------------------------
    def approve_or_reject_operation(
        self,
        operation_id: str,
        req: FileOperationApproveRequest,
    ) -> FileOperationRecord:
        op = self.get_operation(operation_id)
        if not op:
            raise ValueError(f"Operation '{operation_id}' not found.")
        if op.status != "WAITING_FOR_APPROVAL":
            raise ValueError(f"Operation '{operation_id}' is in status '{op.status}', not waiting for approval.")

        if not req.approved:
            return self._record_operation(
                user_id=op.user_id,
                operation_type=op.operation_type,
                status="CANCELLED",
                summary=f"Operation '{op.operation_type}' cancelled by user ({req.user_note or 'rejected'}).",
                verified=True,
                verification_detail="Cancelled prior to execution; no files were modified.",
                affected_paths=op.affected_paths,
                result_data=op.result_data,
                requires_approval=True,
                approval_reason=op.approval_reason,
                approved=False,
                preview=op.preview,
                operation_id=operation_id,
            )

        pending_type = op.result_data.get("pending_request_type")
        payload = dict(op.result_data.get("request_payload") or {})

        if pending_type == "write_file":
            payload["confirmed_overwrite"] = True
            res = self.write_file(FileWriteRequest(**payload))
        elif pending_type == "transfer_item":
            payload["confirmed_overwrite"] = True
            res = self.transfer_item(FileTransferRequest(**payload))
        elif pending_type == "convert_file":
            payload["confirmed_overwrite"] = True
            res = self.convert_file(FileConvertRequest(**payload))
        elif pending_type == "delete_to_trash":
            payload["confirmed"] = True
            res = self.delete_to_trash(FileDeleteRequest(**payload))
        elif pending_type == "cleanup_duplicates":
            payload["confirmed"] = True
            res = self.cleanup_duplicates(FileDuplicateCleanupRequest(**payload))
        elif pending_type == "organize_workspace":
            payload["confirmed"] = True
            res = self.organize_workspace(FileOrganizeRequest(**payload))
        else:
            raise ValueError(f"Unsupported pending operation type '{pending_type}'.")

        # Update original operation record as approved and completed
        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE file_operations
                    SET status = ?, summary = ?, verified = ?, verification_detail = ?,
                        approved = 1, result_data_json = ?, updated_at = ?
                    WHERE operation_id = ?
                    """,
                    (
                        res.status,
                        res.summary,
                        1 if res.verified else 0,
                        res.verification_detail,
                        json.dumps(res.result_data),
                        utc_now().isoformat(),
                        operation_id,
                    ),
                )
        finally:
            conn.close()
        return res

    def rollback_operation(self, user_id: str, operation_id: str) -> FileOperationRecord:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM file_operations WHERE operation_id = ? AND user_id = ?",
                (operation_id, self._sanitize_user_id(user_id)),
            ).fetchone()
        finally:
            conn.close()

        if not row:
            raise ValueError(f"Operation '{operation_id}' not found.")
        if bool(row["rolled_back"]):
            raise ValueError(f"Operation '{operation_id}' has already been rolled back.")
        if not row["rollback_recipe_json"]:
            raise ValueError(f"Operation '{operation_id}' does not support automated rollback.")

        recipe = json.loads(row["rollback_recipe_json"])
        rtype = recipe.get("type")

        if rtype == "restore_version":
            rel_p = recipe["relative_path"]
            ver_id = recipe["version_id"]
            self.restore_version(user_id, rel_p, ver_id)
            detail = f"Restored '{rel_p}' to pre-operation snapshot '{ver_id}'."
        elif rtype == "trash_created_file":
            rel_p = recipe["relative_path"]
            self._move_single_path_to_trash(user_id, rel_p, reason=f"rollback_{operation_id}")
            detail = f"Moved created file '{rel_p}' to Recoverable Trash."
        elif rtype == "remove_created_folder":
            rel_p = recipe["relative_path"]
            target, _ = self.resolve_safe_path(user_id, rel_p)
            if target.exists() and target.is_dir() and not any(target.iterdir()):
                target.rmdir()
            detail = f"Removed empty created folder '{rel_p}'."
        elif rtype == "reverse_move":
            from_p = recipe["from_path"]
            to_p = recipe["to_path"]
            src_abs, _ = self.resolve_safe_path(user_id, from_p)
            dst_abs, _ = self.resolve_safe_path(user_id, to_p)
            dst_abs.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_abs), str(dst_abs))
            if recipe.get("overwritten_backup_version_id"):
                self.restore_version(user_id, from_p, recipe["overwritten_backup_version_id"])
            detail = f"Reversed move '{from_p}' -> '{to_p}'."
        elif rtype == "reverse_bulk_moves":
            moves = recipe.get("moves", [])
            for m in reversed(moves):
                src_abs, _ = self.resolve_safe_path(user_id, m["from_path"])
                dst_abs, _ = self.resolve_safe_path(user_id, m["to_path"])
                if src_abs.exists():
                    dst_abs.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src_abs), str(dst_abs))
            detail = f"Reversed {len(moves)} organized file moves back to original locations."
        elif rtype == "restore_trash_batch":
            trash_ids = recipe.get("trash_ids", [])
            for tid in trash_ids:
                self.restore_from_trash(user_id, tid)
            detail = f"Restored {len(trash_ids)} item(s) from Recoverable Trash."
        else:
            raise ValueError(f"Unknown rollback recipe type '{rtype}'.")

        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE file_operations
                    SET status = 'ROLLED_BACK', rolled_back = 1,
                        verification_detail = ?, updated_at = ?
                    WHERE operation_id = ?
                    """,
                    (detail, utc_now().isoformat(), operation_id),
                )
        finally:
            conn.close()

        updated = self.get_operation(operation_id)
        assert updated is not None
        return updated

    # ------------------------------------------------------------------
    # Stage 4 Document Intelligence & Stage 16 Browser Bridges
    # ------------------------------------------------------------------
    def sync_to_stage4_vault(self, user_id: str, relative_path: str) -> FileOperationRecord:
        from app.services.documents.storage import document_storage

        target, rel_posix = self.resolve_safe_path(user_id, relative_path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(f"File '{rel_posix}' does not exist.")
        if not DocumentParser.is_supported(target.name):
            raise ValueError(
                f"File '{target.name}' is not directly supported by Stage 4 Document Vault. Convert it to TXT, CSV, DOCX, or XLSX first."
            )

        file_bytes = target.read_bytes()
        sha256_val = compute_sha256_bytes(file_bytes)
        doc_item = document_storage.save_and_process_upload(
            file_bytes=file_bytes,
            original_filename=target.name,
            content_type="application/octet-stream",
        )

        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO stage4_sync_map (
                        user_id, relative_path, sha256_hash, doc_id, synced_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        self._sanitize_user_id(user_id),
                        rel_posix,
                        sha256_val,
                        doc_item.id,
                        utc_now().isoformat(),
                    ),
                )
        finally:
            conn.close()

        return self._record_operation(
            user_id=user_id,
            operation_type="sync_stage4_vault",
            status="VERIFIED_SUCCEEDED",
            summary=f"Indexed '{rel_posix}' into Stage 4 Document Vault as '{doc_item.id}' ({doc_item.total_chunks} chunks).",
            verified=True,
            verification_detail=f"Verified Stage 4 Document '{doc_item.id}' status='{doc_item.status}' with {doc_item.total_chunks} searchable chunks.",
            affected_paths=[rel_posix],
            result_data={
                "relative_path": rel_posix,
                "doc_id": doc_item.id,
                "total_chunks": doc_item.total_chunks,
                "page_count": doc_item.page_count,
            },
        )

    def import_from_browser_session(self, req: FileBrowserImportRequest) -> FileOperationRecord:
        from app.services.computer.engine import computer_control_engine

        session = computer_control_engine.get_session(req.session_id)
        if not session:
            raise ValueError(f"Stage 16 Browser Session '{req.session_id}' not found.")

        lines = [
            f"# Stage 16 Browser Automation Capture: {session.goal}",
            f"- **Session ID**: `{session.session_id}`",
            f"- **Target Website**: `{session.target_website or 'N/A'}`",
            f"- **Status**: `{session.status}`",
            f"- **Captured At**: `{utc_now().isoformat()}`",
            "",
            "## Step Execution Summary",
        ]
        for sr in session.step_results:
            lines.append(f"### Step `{sr.step_id}`: {sr.title} ({sr.action_type})")
            lines.append(f"- **Status**: `{sr.status}` | **Verified**: `{sr.verified}`")
            lines.append(f"- **Summary**: {sr.output_summary}")
            if sr.extracted_data:
                lines.append("```json")
                lines.append(json.dumps(sr.extracted_data, indent=2, ensure_ascii=False))
                lines.append("```")
            lines.append("")

        write_res = self.write_file(
            FileWriteRequest(
                user_id=req.user_id,
                relative_path=req.target_filename,
                content="\n".join(lines),
                overwrite=req.overwrite,
                confirmed_overwrite=req.confirmed_overwrite,
                backup_reason=f"import_from_browser_session_{req.session_id}",
            )
        )
        return self._record_operation(
            user_id=req.user_id,
            operation_type="import_browser_session",
            status="VERIFIED_SUCCEEDED",
            summary=f"Imported Stage 16 browser session '{req.session_id}' into '{req.target_filename}'.",
            verified=write_res.verified,
            verification_detail=write_res.verification_detail,
            affected_paths=[req.target_filename],
            result_data={
                "session_id": req.session_id,
                "target_filename": req.target_filename,
                "write_operation_id": write_res.operation_id,
            },
        )


file_workspace_engine = FileWorkspaceEngine()
