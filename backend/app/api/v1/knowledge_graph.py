from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    KGApproveOperationRequest,
    KGChangeLogEntry,
    KGDeleteRequest,
    KGDestructiveOperationRecord,
    KGDuplicateCandidate,
    KGEntityMergeRequest,
    KGGraphSnapshotResponse,
    KGIngestRequest,
    KGIngestResponse,
    KGMetadataResponse,
    KGQueryRequest,
    KGQueryResponse,
)
from app.services.knowledge_graph.engine import knowledge_graph_engine

router = APIRouter(prefix="/knowledge-graph", tags=["Stage 22: Knowledge Graph Intelligence"])


@router.get("/metadata", response_model=KGMetadataResponse)
async def get_kg_metadata():
    return knowledge_graph_engine.get_metadata()


@router.get("/snapshot", response_model=KGGraphSnapshotResponse)
async def get_kg_snapshot(
    user_id: str = Query(default="default_user"),
    workspace_id: str = Query(default="default_workspace"),
    search: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    relation_type: Optional[str] = Query(default=None),
    fact_basis: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1, le=200),
    page_size: int = Query(default=50, ge=1, le=200),
):
    return knowledge_graph_engine.get_graph_snapshot(
        user_id=user_id,
        workspace_id=workspace_id,
        search=search,
        entity_type=entity_type,
        relation_type=relation_type,
        fact_basis=fact_basis,
        page=page,
        page_size=page_size,
    )


@router.post("/ingest", response_model=KGIngestResponse)
async def ingest_knowledge_graph(req: KGIngestRequest):
    return knowledge_graph_engine.ingest_knowledge(req)


@router.post("/query", response_model=KGQueryResponse)
async def query_knowledge_graph(req: KGQueryRequest):
    return knowledge_graph_engine.query_graph(req)


@router.get("/duplicates", response_model=List[KGDuplicateCandidate])
async def list_duplicate_entities(
    user_id: str = Query(default="default_user"),
    workspace_id: str = Query(default="default_workspace"),
):
    return knowledge_graph_engine.find_duplicate_candidates(user_id=user_id, workspace_id=workspace_id)


@router.post("/entities/merge", response_model=KGDestructiveOperationRecord)
async def merge_entities(req: KGEntityMergeRequest):
    try:
        return knowledge_graph_engine.merge_entities(req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/delete", response_model=KGDestructiveOperationRecord)
async def delete_graph_items(req: KGDeleteRequest):
    return knowledge_graph_engine.delete_items(req)


@router.post("/operations/{op_id}/approve", response_model=KGDestructiveOperationRecord)
async def approve_destructive_operation(op_id: str, req: KGApproveOperationRequest):
    try:
        return knowledge_graph_engine.approve_operation(op_id=op_id, req=req)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/operations", response_model=List[KGDestructiveOperationRecord])
async def list_pending_operations(
    user_id: str = Query(default="default_user"),
    workspace_id: str = Query(default="default_workspace"),
):
    return knowledge_graph_engine.list_pending_operations(user_id=user_id, workspace_id=workspace_id)


@router.get("/history", response_model=List[KGChangeLogEntry])
async def list_change_history(
    user_id: str = Query(default="default_user"),
    workspace_id: str = Query(default="default_workspace"),
    limit: int = Query(default=25, ge=1, le=100),
):
    return knowledge_graph_engine.list_change_history(
        user_id=user_id,
        workspace_id=workspace_id,
        limit=limit,
    )
