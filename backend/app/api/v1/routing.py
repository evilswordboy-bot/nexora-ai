"""
NEXORA AI — Stage 12: Intelligent Model Routing API Router
Provides endpoints for:
- GET /api/v1/routing/models: Inspect modular Provider & Model Registry (capabilities, context window, pricing, availability)
- POST /api/v1/routing/models: Dynamically register a model entry
- DELETE /api/v1/routing/models/{model_id}: Dynamically unregister a model entry
- GET /api/v1/routing/policy: Get active routing preferences and spending/fallback limits
- PUT /api/v1/routing/policy: Update routing preferences and spending/fallback limits
- POST /api/v1/routing/simulate: Simulate routing decision, fallback chain, and token/cost estimate
- POST /api/v1/routing/execute: Execute routed request with bounded fallback and budget controls
- GET /api/v1/routing/usage: Retrieve privacy-preserving usage summary, latency, and cost telemetry
- DELETE /api/v1/routing/usage: Reset usage telemetry
"""

from typing import List
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    ModelRegistryEntry,
    RoutingPolicyConfig,
    RoutingSimulateRequest,
    RoutingDecision,
    RoutingExecuteRequest,
    RoutingExecuteResponse,
    RoutingUsageSummary,
)
from app.services.routing.engine import model_routing_engine

router = APIRouter(prefix="/routing", tags=["Stage 12: Intelligent Model Routing Engine"])


@router.get("/models", response_model=List[ModelRegistryEntry])
async def list_registered_models():
    """Returns all registered models with capabilities, context limits, pricing metadata, and verified availability."""
    return model_routing_engine.registry.list_models()


@router.post("/models", response_model=ModelRegistryEntry)
async def register_custom_model(entry: ModelRegistryEntry):
    """Dynamically adds or updates a model in the ProviderModelRegistry without code changes."""
    if not entry.model_id or not entry.provider:
        raise HTTPException(status_code=400, detail="model_id and provider are required.")
    return model_routing_engine.registry.register_model(entry)


@router.delete("/models/{model_id}")
async def unregister_custom_model(model_id: str):
    """Dynamically removes a model from the ProviderModelRegistry."""
    removed = model_routing_engine.registry.unregister_model(model_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found in registry.")
    return {"model_id": model_id, "removed": True}


@router.get("/policy", response_model=RoutingPolicyConfig)
async def get_routing_policy():
    """Returns current routing policy, preference mode, fallback limit, and spending budgets."""
    return model_routing_engine.get_policy()


@router.put("/policy", response_model=RoutingPolicyConfig)
async def update_routing_policy(policy: RoutingPolicyConfig):
    """Updates routing preference (quality_first, balanced, speed_first) and cost/fallback controls."""
    return model_routing_engine.update_policy(policy)


@router.post("/simulate", response_model=RoutingDecision)
async def simulate_routing_decision(request: RoutingSimulateRequest):
    """
    Classifies a task and previews the routing decision, capability matching,
    fallback chain, and estimated token/cost breakdown.
    """
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    return model_routing_engine.select_route(request, allow_unconfigured_preview=True)


@router.post("/execute", response_model=RoutingExecuteResponse)
async def execute_routed_query(request: RoutingExecuteRequest):
    """
    Dispatches a request through the Intelligent Model Router with capability checks,
    spending limit enforcement, bounded fallback recovery, and telemetry logging.
    """
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    try:
        return await model_routing_engine.execute_routed_request(request)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Model routing execution error: {str(exc)}")


@router.get("/usage", response_model=RoutingUsageSummary)
async def get_routing_usage_summary():
    """Returns aggregated token usage, estimated costs, latency metrics, and privacy-safe routing logs."""
    return model_routing_engine.get_usage_summary()


@router.delete("/usage")
async def reset_routing_usage_summary():
    """Clears accumulated routing telemetry logs and resets session spend counters."""
    model_routing_engine.clear_telemetry()
    return {"cleared": True}
