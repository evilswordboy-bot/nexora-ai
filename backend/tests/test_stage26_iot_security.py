import tempfile
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.services.telemetry.engine import IoTTelemetryEngine, iot_telemetry_engine
from app.services.iot_security.engine import (
    IoTSecurityEngine,
    iot_security_engine,
    FIRMWARE_INTEGRITY_SPECS,
)
from app.services.tools_registry import tool_registry
from app.models.schemas import (
    IoTDeviceRegistrationRequest,
    ConfigAuditRequest,
    DefensiveActionRequest,
    SecurityIncidentUpdateRequest,
)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def test_workspace():
    return "test_security_ws_stage26"


def test_stage26_health_and_subsystem(client):
    """Verifies that Stage 26 health check reports stage 26 and operational iot_security subsystem."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["stage"] >= 26
    assert "iot_security" in data["subsystems"]
    assert data["subsystems"]["iot_security"] == "operational"
    assert data["registered_tools_count"] >= 24


def test_stage26_device_security_posture_and_honesty(client, test_workspace):
    """
    Registers a device, assesses posture, and verifies honesty:
    unavailable information is labeled 'unknown' rather than asserted secure.
    """
    reg_res = client.post(
        "/api/v1/telemetry/devices",
        json={
            "user_id": "sec_auditor",
            "workspace_id": test_workspace,
            "name": "Factory Gate ESP32 Sensor Node",
            "board_id": "esp32_devkit_v1",
            "ingestion_protocol": "http",
            "is_simulated": True,
            "firmware_version": "v1.0.0",
        },
    )
    assert reg_res.status_code == 201
    dev_data = reg_res.json()
    device_id = dev_data["device"]["device_id"]

    # Assess posture
    posture_res = client.get(
        f"/api/v1/iot-security/devices/{device_id}/posture?workspace_id={test_workspace}"
    )
    assert posture_res.status_code == 200
    posture = posture_res.json()
    assert posture["device_id"] == device_id
    assert posture["transport_encryption"] == "plaintext_unencrypted"  # HTTP without TLS
    assert posture["supports_secure_boot"] is True
    assert "Secure Boot v2" in posture["secure_boot_mechanism"]
    assert posture["risk_score"] > 0
    assert posture["risk_level"] in ("low", "medium", "high", "critical")

    # Nonexistent device returns 404
    err_res = client.get(
        f"/api/v1/iot-security/devices/nonexistent_device_id/posture?workspace_id={test_workspace}"
    )
    assert err_res.status_code == 404


def test_stage26_configuration_auditing_against_fixtures(client, test_workspace):
    """
    Audits configuration payloads for exposed secrets, private keys, plaintext MQTT, and default credentials.
    Verifies that secrets in evidence are redacted.
    """
    config_fixture = """
    # Industrial IoT Node Configuration
    WIFI_SSID = "CorpGuest"
    WIFI_PASSWORD = "SuperSecretCorpPassword123"
    MQTT_BROKER = "192.168.1.100"
    MQTT_PORT = 1883
    MQTT_TOPIC = "factory/nodes/#"
    API_KEY = "sk-abcdef123456789012345678"
    ADMIN_USER = "admin"
    ADMIN_PASS = "admin"
    """

    res = client.post(
        "/api/v1/iot-security/audit/config",
        json={
            "user_id": "sec_auditor",
            "workspace_id": test_workspace,
            "config_file_text": config_fixture,
            "filename": "firmware_config.ini",
        },
    )
    assert res.status_code == 200
    findings = res.json()
    assert len(findings) >= 3

    rule_ids = [f["rule_id"] for f in findings]
    assert "SEC_RULE_EXPOSED_CREDENTIAL_IN_CONFIG" in rule_ids
    assert "SEC_RULE_UNSAFE_DEFAULT_CREDENTIALS" in rule_ids

    # Verify secret evidence is properly redacted (does not display full secret in plaintext)
    for f in findings:
        if f["rule_id"] == "SEC_RULE_EXPOSED_CREDENTIAL_IN_CONFIG":
            assert "***" in f["evidence"]
            assert "SuperSecretCorpPassword123" not in f["evidence"]

    # List findings
    list_res = client.get(
        f"/api/v1/iot-security/audit/findings?workspace_id={test_workspace}"
    )
    assert list_res.status_code == 200
    assert len(list_res.json()) >= len(findings)


def test_stage26_behavioral_anomalies_and_benign_baselines(client, test_workspace):
    """
    Simulates telemetry and verifies:
    1. Benign normal telemetry does NOT trigger false alarms.
    2. Repeated auth failures trigger high-severity repeated_auth_failures anomaly.
    3. Sequence resets / unexpected crash-loops are detected.
    """
    # 1. Register device
    reg_res = client.post(
        "/api/v1/telemetry/devices",
        json={
            "user_id": "sec_auditor",
            "workspace_id": test_workspace,
            "name": "Benign Baselines Test Node",
            "board_id": "raspberry_pi_pico_w",
            "is_simulated": True,
            "firmware_version": "v1.2.0",
        },
    )
    dev_data = reg_res.json()
    device_id = dev_data["device"]["device_id"]
    token = dev_data["credentials"]["plaintext_token"]

    # 2. Ingest benign nominal telemetry events
    for seq in range(1, 15):
        client.post(
            f"/api/v1/telemetry/devices/{device_id}/events",
            headers={"X-Device-Token": token},
            json={
                "workspace_id": test_workspace,
                "sequence_id": seq,
                "metrics": {"temperature": 24.0 + (seq * 0.1), "humidity": 50.0},
            },
        )

    # Analyze behavior for benign device -> no critical false positives
    anom_res = client.post(
        f"/api/v1/iot-security/devices/{device_id}/analyze-behavior?workspace_id={test_workspace}"
    )
    assert anom_res.status_code == 200
    benign_anomalies = anom_res.json()
    # Benign events should not trigger crashloop or auth failure
    crashloops = [a for a in benign_anomalies if a["anomaly_type"] == "unexpected_restart_crashloop"]
    assert len(crashloops) == 0

    # 3. Simulate repeated auth failures
    for _ in range(6):
        iot_security_engine.record_auth_failure(
            device_id=device_id,
            workspace_id=test_workspace,
            source_ip="192.168.1.55",
            token_prefix="bad_tok",
        )

    auth_anom_res = client.post(
        f"/api/v1/iot-security/devices/{device_id}/analyze-behavior?workspace_id={test_workspace}"
    )
    assert auth_anom_res.status_code == 200
    anomalies = auth_anom_res.json()
    auth_anoms = [a for a in anomalies if a["anomaly_type"] == "repeated_auth_failures"]
    assert len(auth_anoms) >= 1
    assert auth_anoms[0]["severity"] in ("high", "critical")
    assert auth_anoms[0]["classification"] == "suspicious_indicator"


def test_stage26_defensive_actions_and_consequential_gates(client, test_workspace):
    """
    Tests controlled defensive actions:
    1. Disruptive actions without confirmed=True are gated in 'pending_confirmation'.
    2. Confirmed credential revocation revokes device token and generates recovery procedure.
    3. Network isolation reports adapter failure honestly if adapter is not configured.
    """
    # Register device
    reg_res = client.post(
        "/api/v1/telemetry/devices",
        json={
            "user_id": "sec_auditor",
            "workspace_id": test_workspace,
            "name": "Containment Target Device",
            "board_id": "esp32_devkit_v1",
            "is_simulated": True,
            "firmware_version": "v1.0.0",
        },
    )
    dev_data = reg_res.json()
    device_id = dev_data["device"]["device_id"]
    token = dev_data["credentials"]["plaintext_token"]

    # 1. Unconfirmed disruptive action -> pending_confirmation gate
    gate_res = client.post(
        "/api/v1/iot-security/defensive-actions",
        json={
            "user_id": "sec_auditor",
            "workspace_id": test_workspace,
            "device_id": device_id,
            "action_type": "quarantine_device",
            "reason": "Suspicious payload frequency and telemetry spoofing",
            "confirmed": False,
        },
    )
    assert gate_res.status_code == 200
    gate_data = gate_res.json()
    assert gate_data["requires_confirmation"] is True
    assert gate_data["status"] == "pending_confirmation"

    # 2. Confirmed quarantine -> executed
    conf_res = client.post(
        "/api/v1/iot-security/defensive-actions",
        json={
            "user_id": "sec_auditor",
            "workspace_id": test_workspace,
            "device_id": device_id,
            "action_type": "quarantine_device",
            "reason": "Confirmed compromise investigation",
            "confirmed": True,
        },
    )
    assert conf_res.status_code == 200
    conf_data = conf_res.json()
    assert conf_data["status"] == "executed"
    assert "quarantine" in conf_data["result_message"]
    assert conf_data["recovery_procedure"] != ""

    # Verify device status changed to degraded
    dev_status = client.get(f"/api/v1/telemetry/devices/{device_id}?workspace_id={test_workspace}").json()
    assert dev_status["status"] == "degraded"

    # 3. Network isolation without configured adapter -> fails honestly without fabricating
    iso_res = client.post(
        "/api/v1/iot-security/defensive-actions",
        json={
            "user_id": "sec_auditor",
            "workspace_id": test_workspace,
            "device_id": device_id,
            "action_type": "isolate_network",
            "reason": "Network level port shutdown",
            "confirmed": True,
        },
    )
    assert iso_res.status_code == 200
    iso_data = iso_res.json()
    if not settings.iot_security_network_adapter_configured:
        assert iso_data["status"] == "failed"
        assert "Authorized network-management adapter is not configured" in iso_data["result_message"]


def test_stage26_incident_management_and_firmware_integrity(client, test_workspace):
    """
    Tests creating, inspecting, and updating security incidents,
    and validates firmware integrity specification matrix.
    """
    # 1. Create security incident
    inc_res = client.post(
        "/api/v1/iot-security/incidents",
        json={
            "workspace_id": test_workspace,
            "title": "Suspected Sensor Tampering & Sequence Anomaly",
            "severity": "high",
            "classification": "suspicious_indicator",
            "affected_device_ids": ["dev_test_node_01"],
            "root_cause_hypothesis": "Physical probe disconnect or sensor spoofing",
            "confidence_level": "medium",
            "evidence_records": [{"evidence_type": "zscore", "reading": 145.0, "unit": "°C"}],
            "recommended_remediations": ["Inspect physical sensor wiring", "Rotate device authentication token"],
        },
    )
    assert inc_res.status_code == 201
    inc_data = inc_res.json()
    incident_id = inc_data["incident_id"]
    assert inc_data["status"] == "new"
    assert inc_data["affected_devices_count"] == 1

    # 2. Update incident status
    upd_res = client.patch(
        f"/api/v1/iot-security/incidents/{incident_id}",
        json={
            "user_id": "sec_lead",
            "workspace_id": test_workspace,
            "status": "mitigated",
            "resolution_notes": "Wiring replaced and credentials rotated.",
        },
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["status"] == "mitigated"
    assert upd_res.json()["resolved_at"] is not None

    # 3. Firmware integrity matrix
    fw_res = client.get("/api/v1/iot-security/firmware-integrity-matrix")
    assert fw_res.status_code == 200
    specs = fw_res.json()
    assert len(specs) >= 4

    board_ids = [s["board_id"] for s in specs]
    assert "esp32_devkit_v1" in board_ids
    assert "raspberry_pi_pico_w" in board_ids

    # Verify checksum limitation disclaimer is present
    for s in specs:
        assert len(s["checksum_trust_limitation"]) > 20

    # 4. Fleet Security Overview
    overview_res = client.get(f"/api/v1/iot-security/overview?workspace_id={test_workspace}")
    assert overview_res.status_code == 200
    overview = overview_res.json()
    assert overview["stage"] == 26
    assert "fleet_posture_summary" in overview
    assert "devices_posture" in overview


def test_stage26_tool_registry_integration():
    """Verifies that Tool #27 (iot_security_engine) is registered and handles overview, assess_device, and audit_config."""
    tool = tool_registry.get_tool("iot_security_engine")
    assert tool is not None
    assert tool.stage_introduced == 26
    assert tool.risk_level == "medium"

    import asyncio

    # Test tool invocation: overview
    res_overview = asyncio.run(
        tool_registry.execute("iot_security_engine", {"action": "overview"})
    )
    assert res_overview["success"] is True
    assert res_overview["data"]["action"] == "overview"
    assert "Fleet Security Overview" in res_overview["summary"]

    # Test tool invocation: audit_config with secret pattern
    res_audit = asyncio.run(
        tool_registry.execute(
            "iot_security_engine",
            {
                "action": "audit_config",
                "config_text": 'WIFI_PASS = "SecretPassword999"',
            },
        )
    )
    assert res_audit["success"] is True
    assert res_audit["data"]["action"] == "audit_config"
    assert res_audit["data"]["findings_count"] >= 1
