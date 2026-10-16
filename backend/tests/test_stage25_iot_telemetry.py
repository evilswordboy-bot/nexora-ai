from __future__ import annotations

import time
from fastapi.testclient import TestClient

from app.main import app
from app.services.tools_registry import tool_registry

client = TestClient(app)


def test_stage25_health_metadata_and_subsystem():
    # 1. Health check reports stage 25 and operational iot_telemetry subsystem
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200
    h_data = health_res.json()
    assert h_data["stage"] >= 25
    assert h_data["subsystems"]["iot_telemetry"] == "operational"

    # 2. Metadata returns supported physical metrics, broker config, and security specs
    meta_res = client.get("/api/v1/telemetry/metadata")
    assert meta_res.status_code == 200
    meta = meta_res.json()
    assert meta["stage"] == 25
    assert meta["engine"] == "IoTTelemetryEngine"
    metric_keys = [m["key"] for m in meta["supported_metrics"]]
    assert "temperature" in metric_keys
    assert "vibration" in metric_keys
    assert "voltage" in metric_keys
    assert meta["security_policy"]["plaintext_tokens_never_stored"] is True


def test_stage25_device_registration_token_rotation_and_revocation():
    # 1. Register a physical ESP32 device
    reg_res = client.post(
        "/api/v1/telemetry/devices",
        json={
            "user_id": "test_user_tel",
            "workspace_id": "ws_iot_tel",
            "name": "Factory Vibration Monitor ESP32",
            "board_id": "esp32_devkit_v1",
            "is_simulated": False,
            "mac_address": "24:6F:28:AB:CD:EF",
            "firmware_version": "1.2.0",
            "rate_limit_per_minute": 30,
        },
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    dev = reg_data["device"]
    creds = reg_data["credentials"]
    dev_id = dev["device_id"]
    token = creds["plaintext_token"]

    assert dev["name"] == "Factory Vibration Monitor ESP32"
    assert dev["is_simulated"] is False
    assert dev["status"] == "unprovisioned"
    assert token.startswith("nxt_live_")

    # Verify device record via GET
    get_res = client.get(f"/api/v1/telemetry/devices/{dev_id}?workspace_id=ws_iot_tel")
    assert get_res.status_code == 200
    assert get_res.json()["device_id"] == dev_id

    # 2. Rotate token
    rot_res = client.post(
        f"/api/v1/telemetry/devices/{dev_id}/rotate-token",
        json={"user_id": "test_user_tel", "workspace_id": "ws_iot_tel"},
    )
    assert rot_res.status_code == 200
    new_token = rot_res.json()["plaintext_token"]
    assert new_token != token

    # Old token is now invalid for ingestion
    bad_old = client.post(
        "/api/v1/telemetry/ingest/http",
        headers={"X-Device-Token": token},
        json={"device_id": dev_id, "metrics": {"temperature": 25.0}},
    )
    assert bad_old.status_code == 403

    # New token is accepted
    good_new = client.post(
        "/api/v1/telemetry/ingest/http",
        headers={"X-Device-Token": new_token},
        json={"device_id": dev_id, "metrics": {"temperature": 26.5}},
    )
    assert good_new.status_code == 200
    assert good_new.json()["status"] == "ACCEPTED"

    # 3. Revoke token
    rev_res = client.post(
        f"/api/v1/telemetry/devices/{dev_id}/revoke-token?user_id=test_user_tel&workspace_id=ws_iot_tel"
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["status"] == "REVOKED"

    # Ingestion blocked after revocation
    blocked = client.post(
        "/api/v1/telemetry/ingest/http",
        headers={"X-Device-Token": new_token},
        json={"device_id": dev_id, "metrics": {"temperature": 27.0}},
    )
    assert blocked.status_code == 403


def test_stage25_http_ingestion_validation_deduplication_and_rate_limiting():
    # Register device with rate limit of 3 msgs/min
    reg = client.post(
        "/api/v1/telemetry/devices",
        json={
            "user_id": "test_user_tel",
            "workspace_id": "ws_iot_tel",
            "name": "Rate Limited Sensor Node",
            "board_id": "stm32_nucleo_f401re",
            "is_simulated": True,
            "rate_limit_per_minute": 3,
        },
    ).json()
    dev_id = reg["device"]["device_id"]
    token = reg["credentials"]["plaintext_token"]

    # 1. Missing token -> 401
    no_auth = client.post(
        "/api/v1/telemetry/ingest/http",
        json={"device_id": dev_id, "metrics": {"temperature": 22.0}},
    )
    assert no_auth.status_code == 401

    # 2. Valid ingestion -> 200 ACCEPTED
    res1 = client.post(
        "/api/v1/telemetry/ingest/http",
        headers={"X-Device-Token": token},
        json={"device_id": dev_id, "sequence_id": 101, "metrics": {"temperature": 22.4, "humidity": 55.0}},
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "ACCEPTED"
    assert res1.json()["received_metrics_count"] == 2

    # 3. Duplicate payload within window -> DUPLICATE_IGNORED
    res_dup = client.post(
        "/api/v1/telemetry/ingest/http",
        headers={"X-Device-Token": token},
        json={"device_id": dev_id, "sequence_id": 101, "metrics": {"temperature": 22.4, "humidity": 55.0}},
    )
    assert res_dup.status_code == 200
    assert res_dup.json()["status"] == "DUPLICATE_IGNORED"

    # 4. Ingest 2nd & 3rd message to exhaust limit of 3 msgs/min
    client.post(
        "/api/v1/telemetry/ingest/http",
        headers={"X-Device-Token": token},
        json={"device_id": dev_id, "sequence_id": 102, "metrics": {"temperature": 23.0}},
    )
    client.post(
        "/api/v1/telemetry/ingest/http",
        headers={"X-Device-Token": token},
        json={"device_id": dev_id, "sequence_id": 103, "metrics": {"temperature": 23.5}},
    )

    # 5. 4th message exceeds rate limit -> 429
    res_rl = client.post(
        "/api/v1/telemetry/ingest/http",
        headers={"X-Device-Token": token},
        json={"device_id": dev_id, "sequence_id": 104, "metrics": {"temperature": 24.0}},
    )
    assert res_rl.status_code == 429
    assert "Rate limit exceeded" in res_rl.json()["detail"]


def test_stage25_alerts_thresholds_cooldown_and_auto_resolution():
    # Register device
    reg = client.post(
        "/api/v1/telemetry/devices",
        json={
            "user_id": "test_user_tel",
            "workspace_id": "ws_iot_alerts",
            "name": "HVAC Chiller Monitor",
            "board_id": "esp32_devkit_v1",
            "is_simulated": True,
            "rate_limit_per_minute": 100,
        },
    ).json()
    dev_id = reg["device"]["device_id"]
    token = reg["credentials"]["plaintext_token"]

    # 1. Create a custom alert rule: Temperature > 50.0 °C with 120s cooldown
    rule_res = client.post(
        f"/api/v1/telemetry/devices/{dev_id}/alert-rules",
        json={
            "user_id": "test_user_tel",
            "workspace_id": "ws_iot_alerts",
            "metric_key": "temperature",
            "operator": "gt",
            "threshold_val_primary": 50.0,
            "severity": "critical",
            "cooldown_seconds": 120,
            "description": "High Chiller Overheat Alert",
        },
    )
    assert rule_res.status_code == 201
    rule_id = rule_res.json()["rule_id"]

    # 2. Ingest normal telemetry (temperature=35.0) -> No alert triggered
    ok_ingest = client.post(
        "/api/v1/telemetry/ingest/http",
        headers={"X-Device-Token": token},
        json={"device_id": dev_id, "sequence_id": 1, "metrics": {"temperature": 35.0}},
    ).json()
    assert len(ok_ingest["triggered_alerts"]) == 0

    # 3. Ingest breached telemetry (temperature=58.2) -> Alert triggered!
    breach1 = client.post(
        "/api/v1/telemetry/ingest/http",
        headers={"X-Device-Token": token},
        json={"device_id": dev_id, "sequence_id": 2, "metrics": {"temperature": 58.2}},
    ).json()
    assert any("High Chiller Overheat Alert" in a for a in breach1["triggered_alerts"])

    # Query active alerts
    alerts_res = client.get("/api/v1/telemetry/alerts?workspace_id=ws_iot_alerts&status=active")
    assert alerts_res.status_code == 200
    active_alerts = alerts_res.json()
    assert len(active_alerts) >= 1
    alert_record = active_alerts[0]
    alert_id = alert_record["alert_id"]
    assert alert_record["status"] == "active"
    assert alert_record["measured_value"] == 58.2

    # 4. Immediate second breach (temperature=59.0) within cooldown -> Alert suppressed from triggering duplicate notifications
    breach2 = client.post(
        "/api/v1/telemetry/ingest/http",
        headers={"X-Device-Token": token},
        json={"device_id": dev_id, "sequence_id": 3, "metrics": {"temperature": 59.0}},
    ).json()
    assert not any("High Chiller Overheat Alert" in a for a in breach2["triggered_alerts"])

    # 5. Acknowledge alert
    ack_res = client.post(
        f"/api/v1/telemetry/alerts/{alert_id}/acknowledge",
        json={"user_id": "test_user_tel", "workspace_id": "ws_iot_alerts"},
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "acknowledged"

    # 6. Ingest safe reading (temperature=42.0) -> Alert resolves
    client.post(
        "/api/v1/telemetry/ingest/http",
        headers={"X-Device-Token": token},
        json={"device_id": dev_id, "sequence_id": 4, "metrics": {"temperature": 42.0}},
    )
    resolved_res = client.get(f"/api/v1/telemetry/alerts?workspace_id=ws_iot_alerts&device_id={dev_id}&status=resolved")
    assert any(a["rule_id"] == rule_id for a in resolved_res.json())


def test_stage25_device_commands_authorization_and_consequential_confirmation():
    # Register a simulated device
    reg = client.post(
        "/api/v1/telemetry/devices",
        json={
            "user_id": "test_user_tel",
            "workspace_id": "ws_iot_cmd",
            "name": "Robotic Actuator Node",
            "board_id": "raspberry_pi_pico_w",
            "is_simulated": True,
        },
    ).json()
    dev_id = reg["device"]["device_id"]

    # 1. Non-consequential command ('set_telemetry_interval') -> auto-dispatched & acknowledged on simulated device
    cmd1 = client.post(
        f"/api/v1/telemetry/devices/{dev_id}/commands",
        json={
            "user_id": "test_user_tel",
            "workspace_id": "ws_iot_cmd",
            "command_type": "set_telemetry_interval",
            "parameters": {"interval_seconds": 10},
        },
    )
    assert cmd1.status_code == 201
    c1 = cmd1.json()
    assert c1["is_consequential"] is False
    assert c1["requires_confirmation"] is False
    assert c1["dispatch_status"] == "acknowledged"

    # 2. Consequential command ('reboot') -> requires explicit confirmation
    cmd2 = client.post(
        f"/api/v1/telemetry/devices/{dev_id}/commands",
        json={
            "user_id": "test_user_tel",
            "workspace_id": "ws_iot_cmd",
            "command_type": "reboot",
            "parameters": {"force": True},
        },
    )
    assert cmd2.status_code == 201
    c2 = cmd2.json()
    cmd2_id = c2["command_id"]
    assert c2["is_consequential"] is True
    assert c2["requires_confirmation"] is True
    assert c2["confirmation_status"] == "pending_confirmation"
    assert c2["dispatch_status"] == "queued"

    # 3. Confirm command execution
    conf_res = client.post(
        f"/api/v1/telemetry/commands/{cmd2_id}/confirm",
        json={"user_id": "test_user_tel", "workspace_id": "ws_iot_cmd", "confirmed": True},
    )
    assert conf_res.status_code == 200
    c2_conf = conf_res.json()
    assert c2_conf["confirmation_status"] == "confirmed"
    assert c2_conf["dispatch_status"] == "acknowledged"


def test_stage25_simulator_ticks_dataset_export_and_workspace_isolation():
    # 1. Register simulated device in Workspace A
    dev_a = client.post(
        "/api/v1/telemetry/devices",
        json={
            "user_id": "user_a",
            "workspace_id": "ws_telemetry_a",
            "name": "Simulated Weather Station A",
            "board_id": "esp32_devkit_v1",
            "is_simulated": True,
        },
    ).json()["device"]
    dev_a_id = dev_a["device_id"]

    # 2. Run deterministic simulation ticks
    sim_res = client.post(
        f"/api/v1/telemetry/devices/{dev_a_id}/simulate-tick",
        json={"user_id": "user_a", "workspace_id": "ws_telemetry_a", "tick_count": 3},
    )
    assert sim_res.status_code == 200
    s_data = sim_res.json()
    assert s_data["ticks_generated"] == 3
    assert len(s_data["generated_events"]) == 3
    assert s_data["generated_events"][0]["data_provenance"] == "deterministic_simulation"

    # 3. Stats & freshness check
    stats_res = client.get(f"/api/v1/telemetry/devices/{dev_a_id}/stats?user_id=user_a&workspace_id=ws_telemetry_a")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_events"] == 3
    assert "temperature" in stats["latest_metrics"]
    assert "humidity" in stats["latest_metrics"]
    assert stats["data_freshness_label"].startswith("Real-time Live")

    # 4. Workspace isolation: Workspace B cannot see Device A
    iso_res = client.get(f"/api/v1/telemetry/devices/{dev_a_id}?workspace_id=ws_telemetry_b")
    assert iso_res.status_code == 404

    # 5. Export dataset in CSV format
    exp_csv = client.post(
        f"/api/v1/telemetry/devices/{dev_a_id}/export",
        json={"user_id": "user_a", "workspace_id": "ws_telemetry_a", "format": "csv", "time_range": "24h"},
    )
    assert exp_csv.status_code == 200
    csv_data = exp_csv.json()
    assert csv_data["total_events_exported"] >= 3
    assert "event_id,device_timestamp" in csv_data["content_preview"]
    assert csv_data["file_path"].endswith(".csv")

    # 6. Verify tool registry integration
    assert tool_registry.get_tool("iot_telemetry_engine") is not None
