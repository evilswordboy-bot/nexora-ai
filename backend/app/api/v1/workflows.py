from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import settings
from app.models.schemas import (
    WorkflowApproveStepRequest,
    WorkflowCreateRequest,
    WorkflowDefinition,
    WorkflowExecutionRun,
    WorkflowNotificationItem,
    WorkflowRetryRunRequest,
    WorkflowScheduleConfig,
    WorkflowStatus,
    WorkflowStepDefinition,
    WorkflowTriggerRunRequest,
    WorkflowUpdateRequest,
    WorkflowValidationResult,
)
from app.services.agents.orchestrator import multi_agent_orchestrator
from app.services.tools_registry import tool_registry
from app.services.workflows import workflow_engine

router = APIRouter(prefix="/workflows", tags=["Stage 15: Workflow Automation Engine"])


class WorkflowValidateBody(BaseModel):
    steps: List[WorkflowStepDefinition] = Field(default_factory=list)
    schedule: Optional[WorkflowScheduleConfig] = None
    max_cost_budget_usd: float = Field(default=0.50, ge=0.001, le=10.0)


class WorkflowStatusBody(BaseModel):
    status: WorkflowStatus


@router.get("/metadata")
async def get_workflow_metadata() -> Dict[str, Any]:
    agents = multi_agent_orchestrator.list_agents()
    tools = tool_registry.list_tools()
    return {
        "available_agents": [a.model_dump(mode="json") for a in agents],
        "available_tools": [t.model_dump(mode="json") for t in tools],
        "supported_timezones": [
            "UTC",
            "Asia/Kolkata",
            "America/New_York",
            "America/Chicago",
            "America/Los_Angeles",
            "Europe/London",
            "Europe/Berlin",
            "Asia/Tokyo",
            "Asia/Singapore",
            "Australia/Sydney",
        ],
        "notification_channels": {
            "in_app": True,
            "webhook_configured": bool(settings.notification_webhook_url.strip()),
            "smtp_configured": bool(settings.smtp_host.strip()),
        },
        "limits": {
            "max_steps": settings.workflow_max_steps,
            "max_step_retries": settings.workflow_max_step_retries,
            "step_timeout_seconds": settings.workflow_step_timeout_seconds,
            "max_cost_usd_per_run": settings.workflow_max_cost_usd_per_run,
            "rate_limit_per_minute": settings.workflow_rate_limit_per_minute,
        },
    }


@router.get("/templates", response_model=List[WorkflowDefinition])
async def list_workflow_templates() -> List[WorkflowDefinition]:
    return workflow_engine.list_templates()


@router.post("/validate", response_model=WorkflowValidationResult)
async def validate_workflow(body: WorkflowValidateBody) -> WorkflowValidationResult:
    return workflow_engine.validate_workflow_definition(
        steps=body.steps,
        schedule=body.schedule,
        max_cost_budget_usd=body.max_cost_budget_usd,
    )


@router.get("", response_model=List[WorkflowDefinition])
async def list_workflows(
    user_id: str = Query(default="default_user"),
    include_templates: bool = Query(default=False),
    status: Optional[str] = Query(default=None),
) -> List[WorkflowDefinition]:
    return workflow_engine.list_workflows(
        user_id=user_id,
        include_templates=include_templates,
        status_filter=status,
    )


@router.post("", response_model=WorkflowDefinition)
async def create_workflow(req: WorkflowCreateRequest) -> WorkflowDefinition:
    try:
        return workflow_engine.create_workflow(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs", response_model=List[WorkflowExecutionRun])
async def list_workflow_runs(
    user_id: str = Query(default="default_user"),
    workflow_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> List[WorkflowExecutionRun]:
    return workflow_engine.list_runs(
        user_id=user_id,
        workflow_id=workflow_id,
        status_filter=status,
        limit=limit,
    )


@router.get("/runs/{run_id}", response_model=WorkflowExecutionRun)
async def get_workflow_run(run_id: str) -> WorkflowExecutionRun:
    run = workflow_engine.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Workflow run '{run_id}' not found.")
    return run


@router.post("/runs/{run_id}/approve", response_model=WorkflowExecutionRun)
async def approve_workflow_step(run_id: str, req: WorkflowApproveStepRequest) -> WorkflowExecutionRun:
    try:
        return await workflow_engine.approve_run_step(run_id, req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/runs/{run_id}/retry", response_model=WorkflowExecutionRun)
async def retry_workflow_run(run_id: str, req: WorkflowRetryRunRequest) -> WorkflowExecutionRun:
    try:
        return await workflow_engine.retry_run(run_id, req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/runs/{run_id}/cancel", response_model=WorkflowExecutionRun)
async def cancel_workflow_run(run_id: str) -> WorkflowExecutionRun:
    try:
        return await workflow_engine.cancel_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/scheduler/tick", response_model=List[WorkflowExecutionRun])
async def tick_scheduler() -> List[WorkflowExecutionRun]:
    return await workflow_engine.tick_scheduler()


@router.post("/scheduler/recover", response_model=List[WorkflowExecutionRun])
async def recover_interrupted_runs() -> List[WorkflowExecutionRun]:
    return await workflow_engine.recover_interrupted_runs_on_startup()


@router.get("/notifications", response_model=List[WorkflowNotificationItem])
async def list_notifications(
    user_id: str = Query(default="default_user"),
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
) -> List[WorkflowNotificationItem]:
    return workflow_engine.list_notifications(
        user_id=user_id,
        unread_only=unread_only,
        limit=limit,
    )


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str) -> Dict[str, Any]:
    updated = workflow_engine.mark_notification_read(notification_id, True)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Notification '{notification_id}' not found.")
    return {"notification_id": notification_id, "read": True}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(user_id: str = Query(default="default_user")) -> Dict[str, Any]:
    count = workflow_engine.mark_all_notifications_read(user_id=user_id)
    return {"marked_read_count": count}


@router.get("/{workflow_id}", response_model=WorkflowDefinition)
async def get_workflow(workflow_id: str) -> WorkflowDefinition:
    wf = workflow_engine.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
    return wf


@router.put("/{workflow_id}", response_model=WorkflowDefinition)
async def update_workflow(workflow_id: str, req: WorkflowUpdateRequest) -> WorkflowDefinition:
    try:
        return workflow_engine.update_workflow(workflow_id, req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{workflow_id}/status", response_model=WorkflowDefinition)
async def update_workflow_status(workflow_id: str, body: WorkflowStatusBody) -> WorkflowDefinition:
    try:
        return workflow_engine.set_workflow_status(workflow_id, body.status)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{workflow_id}/duplicate", response_model=WorkflowDefinition)
async def duplicate_workflow(
    workflow_id: str,
    user_id: str = Query(default="default_user"),
) -> WorkflowDefinition:
    try:
        return workflow_engine.duplicate_workflow(workflow_id, user_id=user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str) -> Dict[str, Any]:
    try:
        deleted = workflow_engine.delete_workflow(workflow_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
    return {"workflow_id": workflow_id, "deleted": True}


@router.post("/{workflow_id}/run", response_model=WorkflowExecutionRun)
async def trigger_workflow_run(workflow_id: str, req: WorkflowTriggerRunRequest) -> WorkflowExecutionRun:
    try:
        return await workflow_engine.trigger_workflow_run(workflow_id, req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
