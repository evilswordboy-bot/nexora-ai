"""
Stage 14: Multi-Agent Intelligence System API Router
Provides endpoints to inspect the Specialized Agent Registry, classify requests,
execute multi-agent orchestrated runs (auto or manual selection, sequential or parallel),
approve consequential subtasks, retry failed subtasks, and cancel active runs.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    AgentRoleId,
    SpecializedAgentSpec,
    MultiAgentOrchestrationRun,
    MultiAgentRunRequest,
    MultiAgentApproveRequest,
    MultiAgentRetryRequest,
)
from app.services.agents.orchestrator import multi_agent_orchestrator

router = APIRouter(prefix="/agents", tags=["Stage 14: Multi-Agent Intelligence System"])


@router.get("/registry", response_model=List[SpecializedAgentSpec])
async def get_agent_registry():
    """Returns all registered specialized agents with capabilities, limitations, permissions, and live tool availability."""
    return multi_agent_orchestrator.list_agents()


@router.post("/classify", response_model=List[AgentRoleId])
async def classify_agents_for_goal(request: MultiAgentRunRequest):
    """Classifies a request and returns the recommended specialized agent IDs."""
    return multi_agent_orchestrator.classify_and_select_agents(
        goal=request.goal,
        document_ids=request.document_ids,
        target_language=request.target_language,
    )


@router.post("/run", response_model=MultiAgentOrchestrationRun)
async def execute_multi_agent_run(request: MultiAgentRunRequest):
    """Executes a multi-agent task run with dependency tracking, parallel execution where safe, and cost caps."""
    try:
        return await multi_agent_orchestrator.execute_run(request)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.get("/runs", response_model=List[MultiAgentOrchestrationRun])
async def list_multi_agent_runs(user_id: str = Query(default="default_user")):
    """Lists recent multi-agent runs isolated to the specified user_id."""
    return multi_agent_orchestrator.list_runs(user_id=user_id)


@router.get("/runs/{run_id}", response_model=MultiAgentOrchestrationRun)
async def get_multi_agent_run(
    run_id: str,
    user_id: Optional[str] = Query(default=None),
):
    """Retrieves a specific multi-agent orchestration run by ID."""
    run = multi_agent_orchestrator.get_run(run_id, user_id=user_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Multi-agent run '{run_id}' not found.")
    return run


@router.post("/runs/{run_id}/approve", response_model=MultiAgentOrchestrationRun)
async def approve_multi_agent_subtask(run_id: str, approval: MultiAgentApproveRequest):
    """Approves or declines a consequential agent subtask and resumes execution if approved."""
    try:
        return await multi_agent_orchestrator.approve_subtask(run_id, approval)
    except KeyError as ke:
        raise HTTPException(status_code=404, detail=str(ke))


@router.post("/runs/{run_id}/retry", response_model=MultiAgentOrchestrationRun)
async def retry_multi_agent_run(run_id: str, retry_req: MultiAgentRetryRequest):
    """Retries failed or cancelled subtasks in an orchestration run."""
    try:
        return await multi_agent_orchestrator.retry_run(run_id, retry_req)
    except KeyError as ke:
        raise HTTPException(status_code=404, detail=str(ke))


@router.post("/runs/{run_id}/cancel", response_model=MultiAgentOrchestrationRun)
async def cancel_multi_agent_run(run_id: str):
    """Cancels an orchestration run and marks pending subtasks as CANCELLED."""
    try:
        return multi_agent_orchestrator.cancel_run(run_id)
    except KeyError as ke:
        raise HTTPException(status_code=404, detail=str(ke))
