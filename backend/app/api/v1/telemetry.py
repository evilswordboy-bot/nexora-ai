from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    AlertAcknowledgeRequest,
    AlertRecord,
    AlertRecordStatus,
    AlertRuleCreateRequest,
    AlertRuleRecord,
    DeviceCommandConfirmRequest,
    DeviceCommandCreateRequest,
    DeviceCommandRecord,
    IoTDeviceRecord,
    IoTDeviceRegistrationRequest,
    IoTDeviceTokenResponse,
    IoTDeviceTokenRotateRequest,
    TelemetryDeviceStatsResponse,
    TelemetryEventRecord,
    TelemetryExportRequest,
    TelemetryExportResponse,
    TelemetryIngestRequest,
    TelemetryIngestResponse,
    TelemetryMetadataResponse,
    TelemetrySimulatorResponse,
    TelemetrySimulatorTickRequest,
)
from app.services.telemetry.engine import iot_telemetry_engine

router = APIRouter(prefix="/telemetry", tags=["Stage 25: IoT Device Connectivity & Live Telemetry"])


@router.get("/metadata", response_model=TelemetryMetadataResponse)
async def get_telemetry_metadata():
    """Returns platform metadata, supported telemetry metrics, broker specs, and safety policy."""
    return iot_telemetry_engine.get_metadata()


# ----------------------------------------------------------------------------
# 1. Device Registry & Token Lifecycle
# ----------------------------------------------------------------------------

@router.post("/devices", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def register_device(req: IoTDeviceRegistrationRequest):
    """
    Registers a new IoT hardware or simulated device.
    Generates a secure cryptographically random token returned in plaintext ONCE.
    """
    try:
        device, token_resp = iot_telemetry_engine.register_device(req)
        return {
            "device": device.model_dump(),
            "credentials": token_resp.model_dump(),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/devices", response_model=List[IoTDeviceRecord])
async def list_devices(
    user_id: Optional[str] = Query(default=None),
    workspace_id: Optional[str] = Query(default=None),
):
    """Lists registered devices in workspace with connectivity and alert status."""
    return iot_telemetry_engine.list_devices(user_id=user_id, workspace_id=workspace_id)


@router.get("/devices/{device_id}", response_model=IoTDeviceRecord)
async def get_device(
    device_id: str,
    user_id: Optional[str] = Query(default=None),
    workspace_id: Optional[str] = Query(default=None),
):
    """Retrieves device record and current connectivity freshness."""
    dev = iot_telemetry_engine.get_device(device_id, user_id=user_id, workspace_id=workspace_id)
    if not dev:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found.")
    return dev


@router.delete("/devices/{device_id}", response_model=Dict[str, Any])
async def deregister_device(
    device_id: str,
    user_id: str = Query(default="default_user"),
    workspace_id: str = Query(default="default_workspace"),
):
    """Deregisters a device and cascades deletion of its telemetry events, alerts, and command logs."""
    try:
        iot_telemetry_engine.deregister_device(device_id, user_id=user_id, workspace_id=workspace_id)
        return {"device_id": device_id, "status": "DEREGISTERED", "message": "Device and associated telemetry purged."}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found.")


@router.post("/devices/{device_id}/rotate-token", response_model=IoTDeviceTokenResponse)
async def rotate_device_token(device_id: str, req: IoTDeviceTokenRotateRequest):
    """Rotates the device authentication token. The new token is returned in plaintext ONCE."""
    try:
        return iot_telemetry_engine.rotate_device_token(device_id, req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/devices/{device_id}/revoke-token", response_model=Dict[str, Any])
async def revoke_device_token(
    device_id: str,
    user_id: str = Query(default="default_user"),
    workspace_id: str = Query(default="default_workspace"),
):
    """Revokes the device authentication token, immediately cutting off unauthorized telemetry ingestion."""
    try:
        iot_telemetry_engine.revoke_device_token(device_id, user_id=user_id, workspace_id=workspace_id)
        return {"device_id": device_id, "status": "REVOKED", "message": "Device token revoked successfully."}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ----------------------------------------------------------------------------
# 2. Authenticated Telemetry Ingestion Pipeline
# ----------------------------------------------------------------------------

@router.post("/ingest/http", response_model=TelemetryIngestResponse)
async def ingest_http_telemetry(
    req: TelemetryIngestRequest,
    x_device_token: Optional[str] = Header(default=None, alias="X-Device-Token"),
    authorization: Optional[str] = Header(default=None),
):
    """
    Secure authenticated HTTP ingestion endpoint for physical and gateway devices.
    Requires device token in 'X-Device-Token' header or Bearer authorization header.
    Validates metrics, physical sanity bounds, rate limits, and triggers alert rules.
    """
    token = x_device_token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing device authentication credentials. Provide 'X-Device-Token' header.",
        )

    authenticated_device = iot_telemetry_engine.authenticate_device(req.device_id, token)
    if not authenticated_device:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Invalid or revoked device token for device '{req.device_id}'.",
        )

    res = iot_telemetry_engine.ingest_telemetry(req, authenticated_device)
    if res.status == "RATE_LIMITED":
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=res.message)
    if res.status == "VALIDATION_FAILED":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=res.message)

    return res


# ----------------------------------------------------------------------------
# 3. Deterministic Simulator Ingestion
# ----------------------------------------------------------------------------

@router.post("/devices/{device_id}/simulate-tick", response_model=TelemetrySimulatorResponse)
async def simulate_device_tick(device_id: str, req: TelemetrySimulatorTickRequest):
    """
    Injects deterministic mathematical multi-sensor telemetry ticks into a simulated device.
    Strictly blocked on physical hardware devices to prevent real-world data pollution.
    """
    try:
        return iot_telemetry_engine.simulate_tick(device_id, req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ----------------------------------------------------------------------------
# 4. Live Telemetry Queries, Aggregated Stats & SSE Stream
# ----------------------------------------------------------------------------

@router.get("/devices/{device_id}/events", response_model=List[TelemetryEventRecord])
async def list_telemetry_events(
    device_id: str,
    workspace_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    since_iso: Optional[str] = Query(default=None),
):
    """Queries chronological telemetry events for a device."""
    return iot_telemetry_engine.list_events(
        device_id=device_id, workspace_id=workspace_id, limit=limit, since_iso=since_iso
    )


@router.get("/devices/{device_id}/stats", response_model=TelemetryDeviceStatsResponse)
async def get_device_stats(
    device_id: str,
    user_id: str = Query(default="default_user"),
    workspace_id: str = Query(default="default_workspace"),
):
    """Calculates real-time min/max/avg statistical ranges, latest values, and connection freshness."""
    try:
        return iot_telemetry_engine.get_device_stats(device_id, user_id=user_id, workspace_id=workspace_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/devices/{device_id}/live-stream")
async def live_stream_telemetry(device_id: str, request: Request):
    """
    Server-Sent Events (SSE) live telemetry stream.
    Broadcasts newly ingested sensor readings, alert triggers, and command updates in real time.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    iot_telemetry_engine.register_sse_listener(device_id, queue)

    async def event_generator():
        try:
            # Initial connection heartbeat
            yield f"data: {json.dumps({'type': 'heartbeat', 'device_id': device_id, 'connected': True})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield f"data: {json.dumps(payload)}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'ping', 'timestamp': asyncio.get_event_loop().time()})}\n\n"
        finally:
            iot_telemetry_engine.unregister_sse_listener(device_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ----------------------------------------------------------------------------
# 5. Alerts & Safety Threshold Rules
# ----------------------------------------------------------------------------

@router.post("/devices/{device_id}/alert-rules", response_model=AlertRuleRecord, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(device_id: str, req: AlertRuleCreateRequest):
    """Creates a safety alert threshold rule for a device metric."""
    try:
        return iot_telemetry_engine.create_alert_rule(device_id, req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/devices/{device_id}/alert-rules", response_model=List[AlertRuleRecord])
async def list_alert_rules(
    device_id: str,
    workspace_id: Optional[str] = Query(default=None),
):
    """Lists configured alert rules for a device."""
    return iot_telemetry_engine.list_alert_rules(device_id, workspace_id=workspace_id)


@router.get("/alerts", response_model=List[AlertRecord])
async def list_alerts(
    workspace_id: str = Query(default="default_workspace"),
    device_id: Optional[str] = Query(default=None),
    status_filter: Optional[AlertRecordStatus] = Query(default=None, alias="status"),
):
    """Lists triggered alerts across the workspace, optionally filtered by device or status."""
    return iot_telemetry_engine.list_alerts(workspace_id=workspace_id, device_id=device_id, status=status_filter)


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertRecord)
async def acknowledge_alert(alert_id: str, req: AlertAcknowledgeRequest):
    """Acknowledges an active alert record."""
    try:
        return iot_telemetry_engine.acknowledge_alert(alert_id, req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ----------------------------------------------------------------------------
# 6. Controlled Device Commands & Actuation Console
# ----------------------------------------------------------------------------

@router.post("/devices/{device_id}/commands", response_model=DeviceCommandRecord, status_code=status.HTTP_201_CREATED)
async def create_device_command(device_id: str, req: DeviceCommandCreateRequest):
    """
    Dispatches a command to a device.
    Consequential actions (reboot, OTA firmware update, custom control) require explicit user confirmation.
    """
    try:
        return iot_telemetry_engine.create_command(device_id, req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/commands/{command_id}/confirm", response_model=DeviceCommandRecord)
async def confirm_device_command(command_id: str, req: DeviceCommandConfirmRequest):
    """Explicitly confirms and authorizes execution of a consequential device command."""
    try:
        return iot_telemetry_engine.confirm_command(command_id, req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/devices/{device_id}/commands", response_model=List[DeviceCommandRecord])
async def list_device_commands(
    device_id: str,
    workspace_id: Optional[str] = Query(default=None),
):
    """Lists command history and execution status for a device."""
    return iot_telemetry_engine.list_commands(device_id, workspace_id=workspace_id)


# ----------------------------------------------------------------------------
# 7. Dataset Export
# ----------------------------------------------------------------------------

@router.post("/devices/{device_id}/export", response_model=TelemetryExportResponse)
async def export_telemetry(device_id: str, req: TelemetryExportRequest):
    """Exports device telemetry dataset to CSV or JSON with optional Stage 17 File Workspace handoff."""
    try:
        return iot_telemetry_engine.export_telemetry(device_id, req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
