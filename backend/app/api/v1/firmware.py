from __future__ import annotations

from typing import List
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    FirmwareApproveActionRequest,
    FirmwareCodeSearchHit,
    FirmwareCompileRequest,
    FirmwareCompileResult,
    FirmwareDeviceActionRecord,
    FirmwareDeviceActionRequest,
    FirmwareExportResponse,
    FirmwareFileUpdateRequest,
    FirmwareMetadataResponse,
    FirmwarePlatformMatrixEntry,
    FirmwareRestoreVersionRequest,
    FirmwareSerialMonitorRequest,
    FirmwareSerialMonitorResponse,
    FirmwareWorkspaceCreateRequest,
    FirmwareWorkspaceRecord,
)
from app.services.firmware.engine import firmware_studio_engine

router = APIRouter(prefix="/firmware", tags=["Stage 24: Embedded Firmware Engineering Studio"])


@router.get("/metadata", response_model=FirmwareMetadataResponse)
async def get_firmware_metadata() -> FirmwareMetadataResponse:
    return firmware_studio_engine.get_metadata()


@router.get("/platforms", response_model=List[FirmwarePlatformMatrixEntry])
async def list_firmware_platforms() -> List[FirmwarePlatformMatrixEntry]:
    return firmware_studio_engine.get_platform_matrix()


@router.get("/workspaces", response_model=List[FirmwareWorkspaceRecord])
async def list_firmware_workspaces(
    user_id: str = Query(default="default_user"),
    workspace_id: str = Query(default="default_workspace"),
) -> List[FirmwareWorkspaceRecord]:
    return firmware_studio_engine.list_workspaces(user_id=user_id, workspace_id=workspace_id)


@router.post("/workspaces", response_model=FirmwareWorkspaceRecord)
async def create_firmware_workspace(req: FirmwareWorkspaceCreateRequest) -> FirmwareWorkspaceRecord:
    try:
        return firmware_studio_engine.create_workspace(req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/workspaces/{fw_project_id}", response_model=FirmwareWorkspaceRecord)
async def get_firmware_workspace(
    fw_project_id: str,
    user_id: str = Query(default="default_user"),
    workspace_id: str = Query(default="default_workspace"),
) -> FirmwareWorkspaceRecord:
    try:
        return firmware_studio_engine.get_workspace(
            fw_project_id=fw_project_id,
            user_id=user_id,
            workspace_id=workspace_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.put("/workspaces/{fw_project_id}/files", response_model=FirmwareWorkspaceRecord)
async def update_firmware_file(
    fw_project_id: str,
    req: FirmwareFileUpdateRequest,
) -> FirmwareWorkspaceRecord:
    try:
        return firmware_studio_engine.update_file(fw_project_id=fw_project_id, req=req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/workspaces/{fw_project_id}/search", response_model=List[FirmwareCodeSearchHit])
async def search_firmware_code(
    fw_project_id: str,
    query: str = Query(..., min_length=1),
    user_id: str = Query(default="default_user"),
    workspace_id: str = Query(default="default_workspace"),
) -> List[FirmwareCodeSearchHit]:
    try:
        return firmware_studio_engine.search_code(
            fw_project_id=fw_project_id,
            query=query,
            user_id=user_id,
            workspace_id=workspace_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/workspaces/{fw_project_id}/compile", response_model=FirmwareCompileResult)
async def compile_firmware_workspace(
    fw_project_id: str,
    req: FirmwareCompileRequest,
) -> FirmwareCompileResult:
    try:
        return firmware_studio_engine.compile_workspace(fw_project_id=fw_project_id, req=req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workspaces/{fw_project_id}/serial", response_model=FirmwareSerialMonitorResponse)
async def read_firmware_serial_monitor(
    fw_project_id: str,
    req: FirmwareSerialMonitorRequest,
) -> FirmwareSerialMonitorResponse:
    try:
        return firmware_studio_engine.get_serial_monitor(fw_project_id=fw_project_id, req=req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workspaces/{fw_project_id}/device-action", response_model=FirmwareDeviceActionRecord)
async def request_firmware_device_action(
    fw_project_id: str,
    req: FirmwareDeviceActionRequest,
) -> FirmwareDeviceActionRecord:
    try:
        return firmware_studio_engine.request_device_action(fw_project_id=fw_project_id, req=req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/device-actions/{action_id}/approve", response_model=FirmwareDeviceActionRecord)
async def approve_firmware_device_action(
    action_id: str,
    req: FirmwareApproveActionRequest,
) -> FirmwareDeviceActionRecord:
    try:
        return firmware_studio_engine.approve_device_action(action_id=action_id, req=req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/workspaces/{fw_project_id}/restore-version", response_model=FirmwareWorkspaceRecord)
async def restore_firmware_workspace_version(
    fw_project_id: str,
    req: FirmwareRestoreVersionRequest,
) -> FirmwareWorkspaceRecord:
    try:
        return firmware_studio_engine.restore_version(fw_project_id=fw_project_id, req=req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/workspaces/{fw_project_id}/export", response_model=FirmwareExportResponse)
async def export_firmware_workspace(
    fw_project_id: str,
    user_id: str = Query(default="default_user"),
    workspace_id: str = Query(default="default_workspace"),
) -> FirmwareExportResponse:
    try:
        return firmware_studio_engine.export_artifacts(
            fw_project_id=fw_project_id,
            user_id=user_id,
            workspace_id=workspace_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
