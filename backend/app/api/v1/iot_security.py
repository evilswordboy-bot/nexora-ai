from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import (
    BehavioralAnomalyRecord,
    ConfigAuditRequest,
    ConfigurationAuditFinding,
    DefensiveActionRecord,
    DefensiveActionRequest,
    DeviceSecurityPosture,
    FirmwareIntegritySpec,
    IoTSecurityOverviewResponse,
    SecurityIncidentRecord,
    SecurityIncidentUpdateRequest,
)
from app.services.iot_security.engine import (
    FIRMWARE_INTEGRITY_SPECS,
    iot_security_engine,
)

router = APIRouter(prefix="/iot-security", tags=["Stage 26: IoT Security & Threat Detection"])


@router.get("/overview", response_model=IoTSecurityOverviewResponse)
async def get_security_overview(workspace_id: str = Query("default_workspace")):
    """Retrieves fleet-wide IoT security posture, active findings, anomalies, and open incidents."""
    return iot_security_engine.get_security_overview(workspace_id=workspace_id)


@router.get("/devices/{device_id}/posture", response_model=DeviceSecurityPosture)
async def get_device_security_posture(
    device_id: str, workspace_id: str = Query("default_workspace")
):
    """Calculates granular security posture and risk score for a single registered device."""
    try:
        return iot_security_engine.assess_device_posture(device_id, workspace_id=workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/audit/config", response_model=List[ConfigurationAuditFinding])
async def audit_configuration(req: ConfigAuditRequest):
    """Executes rule-based configuration audit for exposed credentials, plaintext protocols, or wildcards."""
    return iot_security_engine.audit_configuration(req)


@router.get("/audit/findings", response_model=List[ConfigurationAuditFinding])
async def list_audit_findings(
    workspace_id: str = Query("default_workspace"),
    device_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query("active", alias="status"),
):
    """Lists configuration audit findings with severity and status filters."""
    return iot_security_engine.list_findings(
        workspace_id=workspace_id,
        device_id=device_id,
        severity=severity,
        status=status_filter,
    )


@router.post("/devices/{device_id}/analyze-behavior", response_model=List[BehavioralAnomalyRecord])
async def analyze_device_behavior(
    device_id: str, workspace_id: str = Query("default_workspace")
):
    """Analyzes telemetry streams, sequence resets, and auth attempts for behavioral anomalies."""
    return iot_security_engine.analyze_device_behavior(device_id, workspace_id=workspace_id)


@router.get("/anomalies", response_model=List[BehavioralAnomalyRecord])
async def list_behavioral_anomalies(
    workspace_id: str = Query("default_workspace"),
    device_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Lists recent behavioral anomaly records."""
    return iot_security_engine.list_anomalies(
        workspace_id=workspace_id,
        device_id=device_id,
        severity=severity,
        limit=limit,
    )


@router.get("/incidents", response_model=List[SecurityIncidentRecord])
async def list_security_incidents(
    workspace_id: str = Query("default_workspace"),
    status_filter: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = Query(None),
):
    """Lists correlated security incidents."""
    return iot_security_engine.list_incidents(
        workspace_id=workspace_id,
        status=status_filter,
        severity=severity,
    )


@router.post("/incidents", response_model=SecurityIncidentRecord, status_code=status.HTTP_201_CREATED)
async def create_security_incident(payload: Dict[str, Any]):
    """Creates a new tracked security incident linking evidence and affected devices."""
    workspace_id = payload.get("workspace_id", "default_workspace")
    title = payload.get("title", "Detected Security Anomaly")
    severity = payload.get("severity", "medium")
    classification = payload.get("classification", "heuristic_alert")
    affected_device_ids = payload.get("affected_device_ids", [])
    root_cause = payload.get("root_cause_hypothesis", "Investigation pending")
    confidence = payload.get("confidence_level", "medium")
    evidence = payload.get("evidence_records", [])
    remediations = payload.get("recommended_remediations", [])

    return iot_security_engine.create_or_correlate_incident(
        workspace_id=workspace_id,
        title=title,
        severity=severity,
        classification=classification,
        affected_device_ids=affected_device_ids,
        root_cause_hypothesis=root_cause,
        confidence_level=confidence,
        evidence_records=evidence,
        recommended_remediations=remediations,
    )


@router.get("/incidents/{incident_id}", response_model=SecurityIncidentRecord)
async def get_security_incident(
    incident_id: str, workspace_id: str = Query("default_workspace")
):
    """Retrieves deep investigation details for a security incident."""
    try:
        return iot_security_engine.get_incident(incident_id, workspace_id=workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/incidents/{incident_id}", response_model=SecurityIncidentRecord)
async def update_security_incident_status(
    incident_id: str, req: SecurityIncidentUpdateRequest
):
    """Updates incident investigation status (e.g. mitigated, closed, false_positive)."""
    try:
        return iot_security_engine.update_incident_status(incident_id, req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/defensive-actions", response_model=DefensiveActionRecord)
async def execute_defensive_action(req: DefensiveActionRequest):
    """
    Executes or gates a defensive response action (credential revocation, quarantine, network isolation).
    Disruptive actions require confirmed=True.
    """
    try:
        return iot_security_engine.execute_defensive_action(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/defensive-actions", response_model=List[DefensiveActionRecord])
async def list_defensive_actions(
    workspace_id: str = Query("default_workspace"),
    device_id: Optional[str] = Query(None),
):
    """Lists audit logs of defensive response actions."""
    return iot_security_engine.list_defensive_actions(
        workspace_id=workspace_id, device_id=device_id
    )


@router.get("/firmware-integrity-matrix", response_model=List[FirmwareIntegritySpec])
async def get_firmware_integrity_matrix():
    """Returns verified hardware Secure Boot, signed firmware, and recovery specifications."""
    return list(FIRMWARE_INTEGRITY_SPECS.values())
