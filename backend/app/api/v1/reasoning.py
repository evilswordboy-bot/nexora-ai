"""
NEXORA AI — Stage 11: Advanced Reasoning Engine API Router
Provides endpoints for:
- POST /api/v1/reasoning/analyze: Classify problem, decompose subtasks, and optionally execute
- GET /api/v1/reasoning/plans: List reasoning plans
- GET /api/v1/reasoning/plans/{plan_id}: Inspect a specific plan & subtask statuses
- POST /api/v1/reasoning/plans/{plan_id}/execute: Execute a planned/paused plan
- POST /api/v1/reasoning/plans/{plan_id}/approve: Approve or deny a consequential subtask
- POST /api/v1/reasoning/plans/{plan_id}/revise: Revise goal, supply clarifications, or update subtasks
- POST /api/v1/reasoning/plans/{plan_id}/cancel: Cancel an active or planned reasoning plan
- GET /api/v1/reasoning/tools: List registered tools in ToolRegistry
"""

from typing import List
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    ReasoningPlan,
    ReasoningAnalyzeRequest,
    ReasoningReviseRequest,
    ReasoningApprovalRequest,
)
from app.services.reasoning.engine import reasoning_engine
from app.services.tools_registry import tool_registry, ToolDefinition

router = APIRouter(prefix="/reasoning", tags=["Stage 11: Advanced Reasoning Engine"])


@router.post("/analyze", response_model=ReasoningPlan)
async def analyze_and_plan(request: ReasoningAnalyzeRequest):
    """
    Classifies an incoming request, answers simple queries directly,
    or builds and executes a multi-step tool-assisted reasoning plan.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    try:
        return await reasoning_engine.analyze_and_execute(request)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Reasoning engine failure: {str(exc)}")


@router.get("/plans", response_model=List[ReasoningPlan])
async def list_plans():
    """Returns all reasoning plans ordered by most recently updated."""
    return reasoning_engine.list_plans()


@router.get("/plans/{plan_id}", response_model=ReasoningPlan)
async def get_plan(plan_id: str):
    """Retrieves a specific reasoning plan by ID."""
    plan = reasoning_engine.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Reasoning plan '{plan_id}' not found.")
    return plan


@router.post("/plans/{plan_id}/execute", response_model=ReasoningPlan)
async def execute_existing_plan(plan_id: str):
    """Executes or resumes a reasoning plan."""
    try:
        return await reasoning_engine.execute_plan(plan_id)
    except KeyError as ke:
        raise HTTPException(status_code=404, detail=str(ke))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to execute plan: {str(exc)}")


@router.post("/plans/{plan_id}/approve", response_model=ReasoningPlan)
async def approve_consequential_subtask(plan_id: str, request: ReasoningApprovalRequest):
    """Approves or denies a BLOCKED consequential subtask requiring explicit user permission."""
    try:
        return await reasoning_engine.approve_subtask(plan_id, request)
    except KeyError as ke:
        raise HTTPException(status_code=404, detail=str(ke))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process approval: {str(exc)}")


@router.post("/plans/{plan_id}/revise", response_model=ReasoningPlan)
async def revise_reasoning_plan(plan_id: str, request: ReasoningReviseRequest):
    """Revises a reasoning plan's goal, clarifications, or subtask titles and optionally re-executes."""
    try:
        return await reasoning_engine.revise_plan(plan_id, request)
    except KeyError as ke:
        raise HTTPException(status_code=404, detail=str(ke))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to revise plan: {str(exc)}")


@router.post("/plans/{plan_id}/cancel", response_model=ReasoningPlan)
async def cancel_reasoning_plan(plan_id: str):
    """Cancels an active or planned reasoning plan."""
    try:
        return reasoning_engine.cancel_plan(plan_id)
    except KeyError as ke:
        raise HTTPException(status_code=404, detail=str(ke))


@router.get("/tools", response_model=List[ToolDefinition])
async def list_registered_tools():
    """Returns all tools registered in the NEXORA ToolRegistry with their schemas and risk levels."""
    return tool_registry.list_tools()
