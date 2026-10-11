"""
Stage 13: Persistent Memory Engine API Router
Provides user-controlled endpoints for creating, listing, searching, editing, pinning,
deleting, and clearing memories, as well as managing privacy settings, natural-language
commands, and exporting memory backups.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    MemoryCategory,
    MemoryCommandRequest,
    MemoryCommandResponse,
    MemoryCreateRequest,
    MemoryItem,
    MemoryPrivacySettings,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryStatusSummary,
    MemoryUpdateRequest,
)
from app.services.memory.engine import memory_engine

router = APIRouter(prefix="/memory", tags=["Stage 13: Persistent Memory Engine"])


@router.get("/status", response_model=MemoryStatusSummary)
async def get_memory_status(user_id: str = Query(default="default_user")):
    """Returns database health, schema version, privacy settings, and memory counts by category."""
    return memory_engine.get_status_summary(user_id=user_id)


@router.get("/settings", response_model=MemoryPrivacySettings)
async def get_memory_settings(user_id: str = Query(default="default_user")):
    """Returns user-specific memory and privacy settings."""
    return memory_engine.get_user_settings(user_id=user_id)


@router.put("/settings", response_model=MemoryPrivacySettings)
async def update_memory_settings(settings: MemoryPrivacySettings):
    """Updates user-specific memory and privacy settings."""
    return memory_engine.update_user_settings(settings)


@router.get("/items", response_model=List[MemoryItem])
async def list_memories(
    user_id: str = Query(default="default_user"),
    category: Optional[MemoryCategory] = Query(default=None),
    include_temporary: bool = Query(default=True),
):
    """Lists saved memories for a user, optionally filtered by category."""
    return memory_engine.list_memories(
        user_id=user_id,
        category=category,
        include_temporary=include_temporary,
    )


@router.post("/items", response_model=MemoryItem)
async def create_memory(
    request: MemoryCreateRequest,
    temporary_chat: bool = Query(default=False),
):
    """Creates a new persistent or temporary memory item after running the Sensitive PII/Secret Guard."""
    try:
        return memory_engine.create_memory(request, temporary_chat=temporary_chat)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.put("/items/{memory_id}", response_model=MemoryItem)
async def update_memory(memory_id: str, request: MemoryUpdateRequest):
    """Updates content, category, key, tags, or pinned status of an existing memory belonging to the user."""
    try:
        updated = memory_engine.update_memory(memory_id, request)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Memory '{memory_id}' not found for user '{request.user_id}'.")
        return updated
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.delete("/items/{memory_id}")
async def delete_memory(
    memory_id: str,
    user_id: str = Query(default="default_user"),
):
    """Deletes a single memory item from persistent or temporary storage for the specified user."""
    deleted = memory_engine.delete_memory(memory_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Memory '{memory_id}' not found for user '{user_id}'.")
    return {"deleted": True, "memory_id": memory_id, "user_id": user_id}


@router.delete("/clear")
async def clear_memories(
    user_id: str = Query(default="default_user"),
    include_temporary: bool = Query(default=True),
):
    """Clears all memories belonging to the specified user."""
    count = memory_engine.clear_user_memories(user_id=user_id, include_temporary=include_temporary)
    return {"cleared": True, "removed_count": count, "user_id": user_id}


@router.post("/search", response_model=MemorySearchResponse)
async def search_memories(request: MemorySearchRequest):
    """Retrieves relevant memories for a query ranked by lexical overlap, recency, and pin preference."""
    user_prefs = memory_engine.get_user_settings(request.user_id)
    results = memory_engine.retrieve_relevant_memories(
        user_id=request.user_id,
        query=request.query,
        category=request.category,
        include_temporary=request.include_temporary,
        top_k=request.top_k,
    )
    return MemorySearchResponse(
        user_id=request.user_id,
        query=request.query,
        total_matched=len(results),
        memories=results,
        memory_enabled=user_prefs.memory_enabled,
        storage_backend=memory_engine.storage_backend,
    )


@router.post("/command", response_model=MemoryCommandResponse)
async def execute_memory_command(request: MemoryCommandRequest):
    """Executes explicit natural-language memory commands ('Remember this...', 'Forget...', 'What do you remember about me?')."""
    return memory_engine.process_memory_command(request)


@router.get("/export")
async def export_memory_backup(user_id: str = Query(default="default_user")) -> Dict[str, Any]:
    """Exports a portable JSON backup of all persistent memories for the specified user."""
    backup = memory_engine.export_backup(user_id=user_id)
    return {
        "user_id": user_id,
        "count": len(backup),
        "memories": backup,
    }
