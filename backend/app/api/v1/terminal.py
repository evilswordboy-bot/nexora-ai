"""
Stage 18: Terminal & Code Execution Engine API Router
Provides endpoints for:
- Inspecting sandbox capabilities, language runtimes, resource limits, and command allowlists
- Creating, listing, reading, saving, and resetting isolated developer code projects
- Managing pre-edit and pre-repair version backups and restoring snapshots
- Running AST syntax checks, code formatting, static linting, and missing dependency detection
- Executing code and test suites inside the isolated sandbox with CPU/memory/timeout/network limits
- Running allowlisted terminal commands with 3-tier classification and approval gates for consequential operations
- Running bounded autonomous debugging and code repair loops verified by real execution/test runs
- Syncing code project files with the Stage 17 File Workspace
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    CodeExecuteRequest,
    CodeFileBackup,
    CodeInspectionResult,
    CodeInspectRequest,
    CodeProjectFile,
    CodeProjectSummary,
    CommandPreview,
    CreateCodeProjectRequest,
    DebugRepairRequest,
    DebugRepairResponse,
    SaveCodeFileRequest,
    SyncStage17Request,
    TerminalApproveRequest,
    TerminalCommandRequest,
    TerminalExecutionRecord,
)
from app.services.terminal.engine import terminal_execution_engine

router = APIRouter(prefix="/terminal", tags=["Stage 18: Terminal & Code Execution Engine"])


@router.get("/capabilities")
async def get_terminal_capabilities(user_id: str = Query(default="default_user")) -> Dict[str, Any]:
    """Returns sandbox execution capabilities, installed language runtimes, resource limits, and allowlists."""
    return terminal_execution_engine.get_capabilities(user_id=user_id)


@router.get("/projects", response_model=List[CodeProjectSummary])
async def list_code_projects(user_id: str = Query(default="default_user")):
    """Lists all developer code projects for the user, seeding a starter project if none exist."""
    return terminal_execution_engine.list_projects(user_id=user_id)


@router.post("/projects", response_model=CodeProjectSummary)
async def create_code_project(request: CreateCodeProjectRequest):
    """Creates a new developer code workspace from a language template (python, javascript, typescript, web)."""
    try:
        return terminal_execution_engine.create_project(request)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/projects/{project_id}", response_model=CodeProjectSummary)
async def get_code_project(
    project_id: str,
    user_id: str = Query(default="default_user"),
):
    """Returns a code project summary including all files and content."""
    try:
        return terminal_execution_engine.get_project(user_id=user_id, project_id=project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/projects/{project_id}/reset", response_model=CodeProjectSummary)
async def reset_code_project(
    project_id: str,
    user_id: str = Query(default="default_user"),
):
    """Resets project files to their baseline template while preserving version backups."""
    try:
        return terminal_execution_engine.reset_project(user_id=user_id, project_id=project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/projects/{project_id}/files")
async def save_project_file(
    project_id: str,
    request: SaveCodeFileRequest,
) -> Dict[str, Any]:
    """Saves or creates a file inside the code project with automatic pre-edit backup snapshot."""
    try:
        file_item, backup = terminal_execution_engine.save_file(project_id=project_id, req=request)
        return {
            "file": file_item.model_dump(mode="json"),
            "backup": backup.model_dump(mode="json") if backup else None,
        }
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/projects/{project_id}/backups", response_model=List[CodeFileBackup])
async def list_project_backups(
    project_id: str,
    user_id: str = Query(default="default_user"),
    relative_path: Optional[str] = Query(default=None),
):
    """Lists automatic pre-edit and pre-repair file backups for a project."""
    try:
        return terminal_execution_engine.list_backups(
            user_id=user_id,
            project_id=project_id,
            relative_path=relative_path,
        )
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/projects/{project_id}/backups/{backup_id}/restore", response_model=CodeProjectFile)
async def restore_project_backup(
    project_id: str,
    backup_id: str,
    user_id: str = Query(default="default_user"),
):
    """Restores a previous file snapshot from backup."""
    try:
        return terminal_execution_engine.restore_backup(
            user_id=user_id,
            project_id=project_id,
            backup_id=backup_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/inspect", response_model=CodeInspectionResult)
async def inspect_project_code(request: CodeInspectRequest):
    """Performs AST syntax validation, formatting, static linting, and missing dependency detection."""
    try:
        return terminal_execution_engine.inspect_code(request)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/execute", response_model=TerminalExecutionRecord)
async def execute_project_code(request: CodeExecuteRequest):
    """Executes code or unit tests inside the isolated sandbox with resource limits and network guard."""
    try:
        return await terminal_execution_engine.execute_code(request)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/command/classify", response_model=CommandPreview)
async def classify_terminal_command(request: TerminalCommandRequest):
    """Classifies a proposed terminal command into allowed_safe, requires_approval, or blocked_forbidden."""
    try:
        return terminal_execution_engine.classify_command(
            user_id=request.user_id,
            project_id=request.project_id,
            command=request.command,
            allow_network=request.allow_network,
        )
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/command", response_model=TerminalExecutionRecord)
async def run_controlled_terminal_command(request: TerminalCommandRequest):
    """Executes an allowlisted terminal command or queues consequential operations for explicit user approval."""
    try:
        return await terminal_execution_engine.run_terminal_command(request)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/executions", response_model=List[TerminalExecutionRecord])
async def list_terminal_executions(
    user_id: str = Query(default="default_user"),
    project_id: Optional[str] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
):
    """Lists recent sandbox code runs and controlled terminal execution records."""
    return terminal_execution_engine.list_executions(
        user_id=user_id,
        project_id=project_id,
        limit=limit,
    )


@router.post("/executions/{execution_id}/approve", response_model=TerminalExecutionRecord)
async def approve_terminal_execution(
    execution_id: str,
    request: TerminalApproveRequest,
):
    """Approves or rejects a consequential terminal command or network-enabled execution."""
    try:
        return await terminal_execution_engine.approve_execution(execution_id=execution_id, req=request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/executions/{execution_id}/stop")
async def stop_terminal_execution(
    execution_id: str,
    user_id: str = Query(default="default_user"),
) -> Dict[str, Any]:
    """Terminates a running sandbox process if active."""
    return terminal_execution_engine.stop_execution(user_id=user_id, execution_id=execution_id)


@router.post("/debug-repair", response_model=DebugRepairResponse)
async def debug_and_repair_code(request: DebugRepairRequest):
    """Runs bounded autonomous debugging and code repair with pre-repair backups and real test verification."""
    try:
        return await terminal_execution_engine.debug_and_repair(request)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/projects/{project_id}/sync-stage17")
async def sync_project_with_stage17(
    project_id: str,
    request: SyncStage17Request,
) -> Dict[str, Any]:
    """Synchronizes files between a Stage 18 Code Project and the Stage 17 File Workspace."""
    try:
        return terminal_execution_engine.sync_with_stage17(project_id=project_id, req=request)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
