from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    IoTBoardProfile,
    IoTComponentSpec,
    IoTMetadataResponse,
    IoTProjectCreateRequest,
    IoTProjectExportRequest,
    IoTProjectExportResponse,
    IoTProjectGenerateFirmwareRequest,
    IoTProjectRecord,
    IoTProjectUpdateWiringRequest,
    IoTSimulationRequest,
    IoTSimulationResponse,
)
from app.services.iot.engine import iot_project_builder_engine

router = APIRouter(prefix="/iot", tags=["Stage 23: IoT Project Builder"])


@router.get("/metadata", response_model=IoTMetadataResponse)
async def get_iot_metadata() -> IoTMetadataResponse:
    return iot_project_builder_engine.get_metadata()


@router.get("/boards", response_model=List[IoTBoardProfile])
async def list_iot_boards() -> List[IoTBoardProfile]:
    return iot_project_builder_engine.list_boards()


@router.get("/boards/{board_id}", response_model=IoTBoardProfile)
async def get_iot_board(board_id: str) -> IoTBoardProfile:
    try:
        return iot_project_builder_engine.get_board(board_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/components", response_model=List[IoTComponentSpec])
async def list_iot_components(
    category: Optional[str] = Query(default=None),
    interface: Optional[str] = Query(default=None),
    query: Optional[str] = Query(default=None),
) -> List[IoTComponentSpec]:
    return iot_project_builder_engine.list_components(
        category=category,
        interface=interface,
        query=query,
    )


@router.get("/projects", response_model=List[IoTProjectRecord])
async def list_iot_projects(
    user_id: str = Query(default="default_user"),
    workspace_id: str = Query(default="default_workspace"),
) -> List[IoTProjectRecord]:
    return iot_project_builder_engine.list_projects(user_id=user_id, workspace_id=workspace_id)


@router.post("/projects", response_model=IoTProjectRecord)
async def create_iot_project(req: IoTProjectCreateRequest) -> IoTProjectRecord:
    try:
        return iot_project_builder_engine.create_project(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}", response_model=IoTProjectRecord)
async def get_iot_project(
    project_id: str,
    user_id: str = Query(default="default_user"),
    workspace_id: str = Query(default="default_workspace"),
) -> IoTProjectRecord:
    try:
        return iot_project_builder_engine.get_project(
            project_id=project_id,
            user_id=user_id,
            workspace_id=workspace_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.put("/projects/{project_id}/wiring", response_model=IoTProjectRecord)
async def update_iot_project_wiring(
    project_id: str,
    req: IoTProjectUpdateWiringRequest,
) -> IoTProjectRecord:
    try:
        return iot_project_builder_engine.update_wiring(project_id=project_id, req=req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/firmware", response_model=IoTProjectRecord)
async def generate_iot_project_firmware(
    project_id: str,
    req: IoTProjectGenerateFirmwareRequest,
) -> IoTProjectRecord:
    try:
        return iot_project_builder_engine.update_firmware(project_id=project_id, req=req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/simulate", response_model=IoTSimulationResponse)
async def simulate_iot_project(
    project_id: str,
    req: IoTSimulationRequest,
) -> IoTSimulationResponse:
    try:
        return iot_project_builder_engine.simulate_project(project_id=project_id, req=req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/export", response_model=IoTProjectExportResponse)
async def export_iot_project(
    project_id: str,
    req: IoTProjectExportRequest,
) -> IoTProjectExportResponse:
    try:
        return iot_project_builder_engine.export_project(project_id=project_id, req=req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
