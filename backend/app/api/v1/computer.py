from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    ComputerApproveStepRequest,
    ComputerAuditLogEntry,
    ComputerExecutionSession,
    ComputerSessionCreateRequest,
)
from app.services.computer import computer_control_engine

router = APIRouter(prefix="/computer", tags=["Stage 16: Computer Control & Digital Execution Engine"])


@router.get("/capabilities")
async def get_computer_capabilities() -> Dict[str, Any]:
    return computer_control_engine.get_environment_capabilities()


@router.post("/sessions", response_model=ComputerExecutionSession)
async def create_computer_session(req: ComputerSessionCreateRequest) -> ComputerExecutionSession:
    try:
        return await computer_control_engine.create_session(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/sessions", response_model=List[ComputerExecutionSession])
async def list_computer_sessions(
    user_id: str = Query(default="default_user"),
    limit: int = Query(default=40, ge=1, le=200),
) -> List[ComputerExecutionSession]:
    return computer_control_engine.list_sessions(user_id=user_id, limit=limit)


@router.get("/sessions/{session_id}", response_model=ComputerExecutionSession)
async def get_computer_session(session_id: str) -> ComputerExecutionSession:
    session = computer_control_engine.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Computer session '{session_id}' not found.")
    return session


@router.post("/sessions/{session_id}/start", response_model=ComputerExecutionSession)
async def start_or_resume_session(session_id: str) -> ComputerExecutionSession:
    try:
        return await computer_control_engine.run_or_resume_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/approve", response_model=ComputerExecutionSession)
async def approve_computer_step(
    session_id: str,
    req: ComputerApproveStepRequest,
) -> ComputerExecutionSession:
    try:
        return await computer_control_engine.approve_step(session_id, req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/pause", response_model=ComputerExecutionSession)
async def pause_computer_session(session_id: str) -> ComputerExecutionSession:
    try:
        return computer_control_engine.pause_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/cancel", response_model=ComputerExecutionSession)
async def cancel_computer_session(session_id: str) -> ComputerExecutionSession:
    try:
        return computer_control_engine.cancel_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/retry", response_model=ComputerExecutionSession)
async def retry_computer_session(session_id: str) -> ComputerExecutionSession:
    try:
        return await computer_control_engine.retry_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/audit-logs", response_model=List[ComputerAuditLogEntry])
async def list_computer_audit_logs(
    session_id: Optional[str] = Query(default=None),
    limit: int = Query(default=60, ge=1, le=200),
) -> List[ComputerAuditLogEntry]:
    return computer_control_engine.list_audit_logs(session_id=session_id, limit=limit)
