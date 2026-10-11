"""
NEXORA AI — Stage 19: Git & Version Control Engine API Router
Provides REST endpoints for:
- Git capabilities & binary detection
- Repository status, changed/staged files, branches, remotes, and recent commits
- Repository initialization & .gitignore recommendations
- Staging & unstaging changes
- Unified & side-by-side diffs + pre-commit secret scanning
- Safe commit creation (with explicit confirmation gate)
- Branch creation, switching (with dirty worktree guard), comparison, and merging
- Remote repository registration & synchronization (push/pull/fetch with explicit confirmation)
- AI-powered code review distinguishing verified defects from possible concerns
- Collaboration & Pull Request draft preparation (honestly separating local drafts from remote provider actions)
- Operation history & pending operation approval/rejection
"""

from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    GitApproveOperationRequest,
    GitBranchActionRequest,
    GitBranchComparisonResponse,
    GitCodeReviewResponse,
    GitCommitRequest,
    GitDiffResponse,
    GitInitRequest,
    GitOperationRecord,
    GitPullRequestCreateRequest,
    GitPullRequestRecord,
    GitRemoteConfigRequest,
    GitRemoteSyncRequest,
    GitRepositoryStatusResponse,
    GitReviewRequest,
    GitStageRequest,
)
from app.services.git.engine import git_version_control_engine

router = APIRouter(prefix="/git", tags=["Stage 19: Git & Version Control Engine"])


@router.get("/capabilities")
async def get_git_capabilities(user_id: str = Query(default="default_user")):
    return git_version_control_engine.get_capabilities(user_id=user_id)


@router.get("/status", response_model=GitRepositoryStatusResponse)
async def get_repository_status(
    project_id: str = Query(default="proj_default_py"),
    user_id: str = Query(default="default_user"),
):
    try:
        return git_version_control_engine.get_status(user_id=user_id, project_id=project_id)
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/init", response_model=GitOperationRecord)
async def initialize_repository(req: GitInitRequest):
    try:
        return git_version_control_engine.init_repository(req)
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/stage", response_model=GitOperationRecord)
async def stage_files(req: GitStageRequest):
    try:
        return git_version_control_engine.stage_files(req)
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/unstage", response_model=GitOperationRecord)
async def unstage_files(req: GitStageRequest):
    try:
        return git_version_control_engine.unstage_files(req)
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/diff", response_model=GitDiffResponse)
async def get_repository_diff(
    project_id: str = Query(default="proj_default_py"),
    user_id: str = Query(default="default_user"),
    scope: Literal["unstaged", "staged", "all_working", "branch_compare", "commit"] = Query(
        default="all_working"
    ),
    staged: Optional[bool] = Query(default=None),
    file_path: Optional[str] = Query(default=None),
    base_ref: Optional[str] = Query(default=None),
    compare_ref: Optional[str] = Query(default=None),
):
    try:
        resolved_scope = "staged" if staged is True else scope
        return git_version_control_engine.get_diff(
            user_id=user_id,
            project_id=project_id,
            scope=resolved_scope,  # type: ignore[arg-type]
            base_ref=base_ref,
            compare_ref=compare_ref,
            file_path=file_path,
        )
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/commit", response_model=GitOperationRecord)
async def commit_changes(req: GitCommitRequest):
    try:
        return git_version_control_engine.commit_changes(req)
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/commits")
async def list_commits(
    project_id: str = Query(default="proj_default_py"),
    user_id: str = Query(default="default_user"),
    branch: Optional[str] = Query(default=None),
    limit: int = Query(default=25, ge=1, le=50),
):
    try:
        commits = git_version_control_engine.list_commits(
            user_id=user_id, project_id=project_id, branch=branch, limit=limit
        )
        return {"project_id": project_id, "commits": commits, "total": len(commits)}
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/branches", response_model=GitOperationRecord)
async def branch_action(req: GitBranchActionRequest):
    try:
        return git_version_control_engine.manage_branch(req)
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/compare", response_model=GitBranchComparisonResponse)
async def compare_branches(
    project_id: str = Query(default="proj_default_py"),
    user_id: str = Query(default="default_user"),
    base_branch: str = Query(default="main"),
    compare_branch: str = Query(default="main"),
):
    try:
        return git_version_control_engine.compare_branches(
            user_id=user_id,
            project_id=project_id,
            base_branch=base_branch,
            compare_branch=compare_branch,
        )
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/remotes", response_model=GitOperationRecord)
async def configure_remote(req: GitRemoteConfigRequest):
    try:
        return git_version_control_engine.configure_remote(req)
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sync", response_model=GitOperationRecord)
async def sync_remote(req: GitRemoteSyncRequest):
    try:
        return git_version_control_engine.sync_remote(req)
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/review", response_model=GitCodeReviewResponse)
async def review_changes(req: GitReviewRequest):
    try:
        return await git_version_control_engine.review_changes(req)
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/pull-requests")
async def list_pull_requests(
    user_id: str = Query(default="default_user"),
    project_id: str = Query(default="proj_default_py"),
):
    prs = git_version_control_engine.list_pull_requests(user_id=user_id, project_id=project_id)
    return {"pull_requests": prs, "total": len(prs)}


@router.post("/pull-requests", response_model=GitPullRequestRecord)
async def create_pull_request(req: GitPullRequestCreateRequest):
    try:
        return git_version_control_engine.create_pull_request(req)
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/operations")
async def list_git_operations(
    user_id: str = Query(default="default_user"),
    project_id: Optional[str] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=200),
):
    ops = git_version_control_engine.list_operations(
        user_id=user_id, project_id=project_id, limit=limit
    )
    return {"operations": ops, "total": len(ops)}


@router.post("/operations/{operation_id}/approve", response_model=GitOperationRecord)
async def approve_git_operation(operation_id: str, req: GitApproveOperationRequest):
    try:
        return git_version_control_engine.approve_operation(operation_id, req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
