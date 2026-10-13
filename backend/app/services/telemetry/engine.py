from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import math
import os
import random
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.models.schemas import (
    AlertAcknowledgeRequest,
    AlertOperator,
    AlertRecord,
    AlertRecordStatus,
    AlertRuleCreateRequest,
    AlertRuleRecord,
    AlertSeverity,
    CommandConfirmationStatus,
    CommandDispatchStatus,
    DeviceCommandConfirmRequest,
    DeviceCommandCreateRequest,
    DeviceCommandRecord,
    DeviceCommandType,
    IoTBoardId,
    IoTDeviceRecord,
    IoTDeviceRegistrationRequest,
    IoTDeviceStatus,
    IoTDeviceTokenResponse,
    IoTDeviceTokenRotateRequest,
    IoTIngestionProtocol,
    TelemetryDataProvenance,
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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_token(token: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", token.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()


# Physical allowable metric bounds for validation
METRIC_PHYSICAL_BOUNDS: Dict[str, Dict[str, Any]] = {
    "temperature": {"min": -50.0, "max": 150.0, "unit": "°C", "desc": "Ambient or process temperature"},
    "humidity": {"min": 0.0, "max": 100.0, "unit": "%RH", "desc": "Relative atmospheric humidity"},
    "vibration": {"min": 0.0, "max": 50.0, "unit": "g", "desc": "Tri-axial peak vibration acceleration"},
    "current": {"min": 0.0, "max": 100.0, "unit": "A", "desc": "Electrical current draw"},
    "voltage": {"min": 0.0, "max": 60.0, "unit": "V", "desc": "DC supply or battery bus voltage"},
    "distance": {"min": 0.0, "max": 1000.0, "unit": "cm", "desc": "Ultrasonic or ToF distance measurement"},
    "pressure": {"min": 300.0, "max": 1200.0, "unit": "hPa", "desc": "Barometric atmospheric pressure"},
    "illuminance": {"min": 0.0, "max": 100000.0, "unit": "lux", "desc": "Optical ambient light intensity"},
    "rssi": {"min": -120.0, "max": 0.0, "unit": "dBm", "desc": "Wi-Fi / Cellular signal strength"},
    "battery_level_pct": {"min": 0.0, "max": 100.0, "unit": "%", "desc": "Battery state of charge"},
    "power": {"min": 0.0, "max": 5000.0, "unit": "W", "desc": "Real electrical power consumption"},
}

CONSEQUENTIAL_COMMAND_TYPES = {"reboot", "ota_firmware_update", "custom_control"}


class IoTTelemetryEngine:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or settings.telemetry_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.exports_dir = Path(settings.telemetry_exports_dir)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

        self._rate_limit_history: Dict[str, List[float]] = {}
        self._dedup_cache: Dict[str, float] = {}
        self._sse_listeners: Dict[str, List[asyncio.Queue]] = {}

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS registered_devices (
                    device_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    board_id TEXT NOT NULL,
                    is_simulated INTEGER NOT NULL,
                    mac_address TEXT,
                    chip_id TEXT,
                    firmware_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    iot_project_id TEXT,
                    fw_project_id TEXT,
                    token_hash TEXT NOT NULL,
                    token_salt TEXT NOT NULL,
                    ingestion_protocol TEXT NOT NULL,
                    mqtt_topic_telemetry TEXT NOT NULL,
                    mqtt_topic_commands TEXT NOT NULL,
                    rate_limit_per_minute INTEGER NOT NULL,
                    total_events_received INTEGER NOT NULL DEFAULT 0,
                    last_seen_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_events (
                    event_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    sequence_id INTEGER,
                    device_timestamp TEXT NOT NULL,
                    ingestion_timestamp TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    units_json TEXT NOT NULL,
                    raw_payload_hash TEXT NOT NULL,
                    data_provenance TEXT NOT NULL,
                    is_valid INTEGER NOT NULL DEFAULT 1,
                    anomalies_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (device_id) REFERENCES registered_devices(device_id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_rules (
                    rule_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    metric_key TEXT NOT NULL,
                    operator TEXT NOT NULL,
                    threshold_val_primary REAL NOT NULL,
                    threshold_val_secondary REAL,
                    severity TEXT NOT NULL,
                    cooldown_seconds INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    is_enabled INTEGER NOT NULL DEFAULT 1,
                    last_triggered_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (device_id) REFERENCES registered_devices(device_id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_records (
                    alert_id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    device_name TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    metric_key TEXT NOT NULL,
                    measured_value REAL NOT NULL,
                    threshold_description TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    data_provenance TEXT NOT NULL,
                    cooldown_until TEXT,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    FOREIGN KEY (device_id) REFERENCES registered_devices(device_id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS device_commands (
                    command_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    device_name TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    command_type TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    is_consequential INTEGER NOT NULL,
                    requires_confirmation INTEGER NOT NULL,
                    confirmation_status TEXT NOT NULL,
                    dispatch_status TEXT NOT NULL,
                    result_message TEXT NOT NULL,
                    dispatched_at TEXT,
                    acknowledged_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (device_id) REFERENCES registered_devices(device_id) ON DELETE CASCADE
                );
                """
            )

            # Performance indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_telemetry_device_time ON telemetry_events(device_id, ingestion_timestamp DESC);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_telemetry_workspace ON telemetry_events(workspace_id, ingestion_timestamp DESC);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_alert_records_device ON alert_records(device_id, status);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_commands_device ON device_commands(device_id, created_at DESC);"
            )
            conn.commit()

    # ------------------------------------------------------------------------
    # 1. Device Registry & Token Lifecycle
    # ------------------------------------------------------------------------

    def register_device(self, req: IoTDeviceRegistrationRequest) -> Tuple[IoTDeviceRecord, IoTDeviceTokenResponse]:
        device_id = f"dev_{secrets.token_hex(6)}"
        plaintext_token = f"nxt_live_{secrets.token_hex(20)}"
        salt = secrets.token_hex(16)
        token_hash = _hash_token(plaintext_token, salt)

        mqtt_topic_telemetry = f"nexora/{req.workspace_id}/{device_id}/telemetry"
        mqtt_topic_commands = f"nexora/{req.workspace_id}/{device_id}/commands"
        now = _utc_now_iso()

        status: IoTDeviceStatus = "online" if req.is_simulated else "unprovisioned"

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO registered_devices (
                    device_id, user_id, workspace_id, name, board_id, is_simulated,
                    mac_address, chip_id, firmware_version, status, iot_project_id,
                    fw_project_id, token_hash, token_salt, ingestion_protocol,
                    mqtt_topic_telemetry, mqtt_topic_commands, rate_limit_per_minute,
                    total_events_received, last_seen_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?);
                """,
                (
                    device_id,
                    req.user_id,
                    req.workspace_id,
                    req.name,
                    req.board_id,
                    1 if req.is_simulated else 0,
                    req.mac_address or (f"02:00:{secrets.token_hex(1)}:{secrets.token_hex(1)}:{secrets.token_hex(1)}:{secrets.token_hex(1)}" if req.is_simulated else None),
                    req.chip_id or (f"SIM_{secrets.token_hex(4).upper()}" if req.is_simulated else None),
                    req.firmware_version,
                    status,
                    req.iot_project_id,
                    req.fw_project_id,
                    token_hash,
                    salt,
                    req.ingestion_protocol,
                    mqtt_topic_telemetry,
                    mqtt_topic_commands,
                    req.rate_limit_per_minute,
                    now if req.is_simulated else None,
                    now,
                    now,
                ),
            )
            # Create default safety alert rules for standard board types
            self._create_default_alert_rules_sync(conn, device_id, req.workspace_id)
            conn.commit()

        record = self.get_device(device_id, user_id=req.user_id, workspace_id=req.workspace_id)
        if not record:
            raise RuntimeError(f"Failed to retrieve registered device {device_id}")

        token_resp = IoTDeviceTokenResponse(
            device_id=device_id,
            name=req.name,
            plaintext_token=plaintext_token,
            token_prefix=plaintext_token[:12] + "...",
            ingestion_url="/api/v1/telemetry/ingest/http",
            mqtt_topic=mqtt_topic_telemetry,
        )
        return record, token_resp

    def _create_default_alert_rules_sync(self, conn: sqlite3.Connection, device_id: str, workspace_id: str) -> None:
        defaults = [
            ("temperature", "gt", 70.0, None, "critical", 300, "Critical temperature exceedance (> 70.0 °C)"),
            ("vibration", "gt", 8.5, None, "warning", 180, "Elevated structural vibration (> 8.5 g)"),
            ("voltage", "lt", 3.3, None, "warning", 300, "Low supply voltage brownout risk (< 3.3 V)"),
        ]
        now = _utc_now_iso()
        for metric, op, val1, val2, sev, cd, desc in defaults:
            rule_id = f"rule_{secrets.token_hex(6)}"
            conn.execute(
                """
                INSERT INTO alert_rules (
                    rule_id, device_id, workspace_id, metric_key, operator,
                    threshold_val_primary, threshold_val_secondary, severity,
                    cooldown_seconds, description, is_enabled, last_triggered_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, NULL, ?);
                """,
                (rule_id, device_id, workspace_id, metric, op, val1, val2, sev, cd, desc, now),
            )

    def rotate_device_token(
        self, device_id: str, req: IoTDeviceTokenRotateRequest
    ) -> IoTDeviceTokenResponse:
        device = self.get_device(device_id, user_id=req.user_id, workspace_id=req.workspace_id)
        if not device:
            raise KeyError(f"Device {device_id} not found in workspace {req.workspace_id}")

        plaintext_token = f"nxt_live_{secrets.token_hex(20)}"
        salt = secrets.token_hex(16)
        token_hash = _hash_token(plaintext_token, salt)
        now = _utc_now_iso()

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE registered_devices
                SET token_hash = ?, token_salt = ?, updated_at = ?
                WHERE device_id = ? AND workspace_id = ?;
                """,
                (token_hash, salt, now, device_id, req.workspace_id),
            )
            conn.commit()

        return IoTDeviceTokenResponse(
            device_id=device_id,
            name=device.name,
            plaintext_token=plaintext_token,
            token_prefix=plaintext_token[:12] + "...",
            ingestion_url="/api/v1/telemetry/ingest/http",
            mqtt_topic=device.mqtt_topic_telemetry,
        )

    def revoke_device_token(self, device_id: str, user_id: str, workspace_id: str) -> bool:
        device = self.get_device(device_id, user_id=user_id, workspace_id=workspace_id)
        if not device:
            raise KeyError(f"Device {device_id} not found in workspace {workspace_id}")

        # Set token hash to disabled randomized junk to immediately revoke authorization
        disabled_hash = f"REVOKED_{secrets.token_hex(32)}"
        now = _utc_now_iso()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE registered_devices
                SET token_hash = ?, status = 'unprovisioned', updated_at = ?
                WHERE device_id = ? AND workspace_id = ?;
                """,
                (disabled_hash, now, device_id, workspace_id),
            )
            conn.commit()
        return True

    def authenticate_device(self, device_id: str, raw_token: str) -> Optional[IoTDeviceRecord]:
        if not raw_token or not device_id:
            return None

        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM registered_devices WHERE device_id = ?;", (device_id,)
            ).fetchone()
            if not row:
                return None

            expected_hash = row["token_hash"]
            salt = row["token_salt"]
            computed_hash = _hash_token(raw_token, salt)
            if not secrets.compare_digest(expected_hash, computed_hash):
                return None

            return self._row_to_device(row)

    def get_device(
        self, device_id: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None
    ) -> Optional[IoTDeviceRecord]:
        with self._get_connection() as conn:
            query = "SELECT * FROM registered_devices WHERE device_id = ?"
            params: List[Any] = [device_id]
            if workspace_id:
                query += " AND workspace_id = ?"
                params.append(workspace_id)
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            row = conn.execute(query, tuple(params)).fetchone()
            if not row:
                return None
            return self._row_to_device(row)

    def list_devices(
        self, user_id: Optional[str] = None, workspace_id: Optional[str] = None
    ) -> List[IoTDeviceRecord]:
        with self._get_connection() as conn:
            query = "SELECT * FROM registered_devices WHERE 1=1"
            params: List[Any] = []
            if workspace_id:
                query += " AND workspace_id = ?"
                params.append(workspace_id)
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            query += " ORDER BY created_at DESC;"

            rows = conn.execute(query, tuple(params)).fetchall()
            return [self._row_to_device(r) for r in rows]

    def deregister_device(self, device_id: str, user_id: str, workspace_id: str) -> bool:
        device = self.get_device(device_id, user_id=user_id, workspace_id=workspace_id)
        if not device:
            raise KeyError(f"Device {device_id} not found")

        with self._get_connection() as conn:
            conn.execute("DELETE FROM telemetry_events WHERE device_id = ?;", (device_id,))
            conn.execute("DELETE FROM alert_records WHERE device_id = ?;", (device_id,))
            conn.execute("DELETE FROM alert_rules WHERE device_id = ?;", (device_id,))
            conn.execute("DELETE FROM device_commands WHERE device_id = ?;", (device_id,))
            conn.execute("DELETE FROM registered_devices WHERE device_id = ?;", (device_id,))
            conn.commit()
        return True

    def _row_to_device(self, row: sqlite3.Row) -> IoTDeviceRecord:
        last_seen = row["last_seen_at"]
        age_sec = None
        if last_seen:
            try:
                dt = datetime.fromisoformat(last_seen)
                age_sec = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds())
            except Exception:
                age_sec = None

        # Check offline threshold dynamically
        status: IoTDeviceStatus = row["status"]
        if status == "online" and age_sec is not None and age_sec > settings.telemetry_offline_timeout_seconds:
            status = "offline"

        with self._get_connection() as conn:
            active_alerts = conn.execute(
                "SELECT COUNT(*) AS cnt FROM alert_records WHERE device_id = ? AND status = 'active';",
                (row["device_id"],),
            ).fetchone()["cnt"]

        return IoTDeviceRecord(
            device_id=row["device_id"],
            user_id=row["user_id"],
            workspace_id=row["workspace_id"],
            name=row["name"],
            board_id=row["board_id"],
            is_simulated=bool(row["is_simulated"]),
            mac_address=row["mac_address"],
            chip_id=row["chip_id"],
            firmware_version=row["firmware_version"],
            status=status,
            iot_project_id=row["iot_project_id"],
            fw_project_id=row["fw_project_id"],
            ingestion_protocol=row["ingestion_protocol"],
            mqtt_topic_telemetry=row["mqtt_topic_telemetry"],
            mqtt_topic_commands=row["mqtt_topic_commands"],
            rate_limit_per_minute=row["rate_limit_per_minute"],
            last_seen_at=last_seen,
            last_reading_age_seconds=round(age_sec, 1) if age_sec is not None else None,
            total_events_received=row["total_events_received"],
            active_alerts_count=active_alerts,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # ------------------------------------------------------------------------
    # 2. Telemetry Ingestion Pipeline
    # ------------------------------------------------------------------------

    def ingest_telemetry(
        self, req: TelemetryIngestRequest, authenticated_device: IoTDeviceRecord
    ) -> TelemetryIngestResponse:
        device_id = authenticated_device.device_id
        workspace_id = authenticated_device.workspace_id
        now_ts = time.time()
        now_iso = _utc_now_iso()

        # 1. Rate Limiting Check
        history = self._rate_limit_history.setdefault(device_id, [])
        cutoff = now_ts - 60.0
        self._rate_limit_history[device_id] = [t for t in history if t > cutoff]
        if len(self._rate_limit_history[device_id]) >= authenticated_device.rate_limit_per_minute:
            return TelemetryIngestResponse(
                status="RATE_LIMITED",
                device_id=device_id,
                received_metrics_count=0,
                triggered_alerts=[],
                message=f"Rate limit exceeded ({authenticated_device.rate_limit_per_minute} msgs/min). Backoff applied.",
                ingested_at=now_iso,
            )
        self._rate_limit_history[device_id].append(now_ts)

        # 2. Deduplication check
        payload_hash = hashlib.sha256(
            f"{device_id}_{req.sequence_id}_{sorted(req.metrics.items())}".encode()
        ).hexdigest()
        last_seen_hash_time = self._dedup_cache.get(payload_hash)
        if last_seen_hash_time and (now_ts - last_seen_hash_time) < 60.0:
            return TelemetryIngestResponse(
                status="DUPLICATE_IGNORED",
                device_id=device_id,
                received_metrics_count=len(req.metrics),
                triggered_alerts=[],
                message="Duplicate message detected within deduplication window. Ignored safely.",
                ingested_at=now_iso,
            )
        self._dedup_cache[payload_hash] = now_ts

        # 3. Metric Schema Validation & Physical Bounds Anomaly Checks
        anomalies: List[str] = []
        validated_metrics: Dict[str, float] = {}
        units_map: Dict[str, str] = dict(req.units or {})

        for k, v in req.metrics.items():
            k_norm = k.strip().lower()
            try:
                val_flt = float(v)
            except (ValueError, TypeError):
                anomalies.append(f"Metric '{k}' contains non-numeric value: {v}")
                continue

            # Physical sanity bounds checking
            if k_norm in METRIC_PHYSICAL_BOUNDS:
                spec = METRIC_PHYSICAL_BOUNDS[k_norm]
                if not units_map.get(k_norm):
                    units_map[k_norm] = spec["unit"]
                if val_flt < spec["min"] or val_flt > spec["max"]:
                    anomalies.append(
                        f"Metric '{k_norm}'={val_flt} is outside physical bounds [{spec['min']}, {spec['max']} {spec['unit']}]."
                    )
            validated_metrics[k_norm] = val_flt

        if req.battery_level_pct is not None:
            validated_metrics["battery_level_pct"] = float(req.battery_level_pct)
            units_map["battery_level_pct"] = "%"

        if not validated_metrics:
            return TelemetryIngestResponse(
                status="VALIDATION_FAILED",
                device_id=device_id,
                received_metrics_count=0,
                triggered_alerts=[],
                message="No valid numeric metrics found in telemetry payload.",
                ingested_at=now_iso,
            )

        # 4. Device Timestamp Handling & Clock Drift Detection
        dev_ts = req.device_timestamp
        if dev_ts:
            try:
                dt_dev = datetime.fromisoformat(dev_ts)
                drift_sec = (datetime.now(timezone.utc) - dt_dev).total_seconds()
                if drift_sec < -60.0:
                    anomalies.append(f"Device clock future drift detected ({abs(drift_sec):.1f}s ahead). Clamped to server ingestion time.")
                    dev_ts = now_iso
            except Exception:
                dev_ts = now_iso
        else:
            dev_ts = now_iso

        event_id = f"evt_{secrets.token_hex(8)}"
        event_record = TelemetryEventRecord(
            event_id=event_id,
            device_id=device_id,
            workspace_id=workspace_id,
            sequence_id=req.sequence_id,
            device_timestamp=dev_ts,
            ingestion_timestamp=now_iso,
            metrics=validated_metrics,
            units=units_map,
            data_provenance=req.data_provenance,
            is_valid=len(anomalies) == 0,
            anomalies=anomalies,
        )

        # 5. Persist event, update device state & total count
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO telemetry_events (
                    event_id, device_id, workspace_id, sequence_id,
                    device_timestamp, ingestion_timestamp, metrics_json, units_json,
                    raw_payload_hash, data_provenance, is_valid, anomalies_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event_id,
                    device_id,
                    workspace_id,
                    req.sequence_id,
                    dev_ts,
                    now_iso,
                    json.dumps(validated_metrics),
                    json.dumps(units_map),
                    payload_hash,
                    req.data_provenance,
                    1 if len(anomalies) == 0 else 0,
                    json.dumps(anomalies),
                    now_iso,
                ),
            )
            conn.execute(
                """
                UPDATE registered_devices
                SET status = 'online', last_seen_at = ?, total_events_received = total_events_received + 1, updated_at = ?
                WHERE device_id = ?;
                """,
                (now_iso, now_iso, device_id),
            )
            # 6. Bounded event retention per device
            conn.execute(
                """
                DELETE FROM telemetry_events
                WHERE event_id IN (
                    SELECT event_id FROM telemetry_events
                    WHERE device_id = ?
                    ORDER BY ingestion_timestamp DESC
                    LIMIT -1 OFFSET ?
                );
                """,
                (device_id, settings.telemetry_max_events_per_device),
            )
            conn.commit()

        # 7. Evaluate Alert Rules
        triggered_alert_descriptions = self._evaluate_alert_rules(
            device_id=device_id,
            device_name=authenticated_device.name,
            workspace_id=workspace_id,
            metrics=validated_metrics,
            data_provenance=req.data_provenance,
            now_iso=now_iso,
        )

        # 8. Broadcast to live SSE stream listeners
        self._broadcast_sse_event(device_id, {
            "type": "telemetry",
            "event": event_record.model_dump(),
            "alerts": triggered_alert_descriptions,
        })

        return TelemetryIngestResponse(
            status="ACCEPTED",
            event_id=event_id,
            device_id=device_id,
            received_metrics_count=len(validated_metrics),
            triggered_alerts=triggered_alert_descriptions,
            message="Telemetry event validated, recorded, and evaluated against safety thresholds.",
            ingested_at=now_iso,
        )

    # ------------------------------------------------------------------------
    # 3. Alerts & Safety Thresholds
    # ------------------------------------------------------------------------

    def create_alert_rule(
        self, device_id: str, req: AlertRuleCreateRequest
    ) -> AlertRuleRecord:
        device = self.get_device(device_id, user_id=req.user_id, workspace_id=req.workspace_id)
        if not device:
            raise KeyError(f"Device {device_id} not found in workspace {req.workspace_id}")

        rule_id = f"rule_{secrets.token_hex(6)}"
        now = _utc_now_iso()
        desc = req.description or f"Alert on {req.metric_key} {req.operator} {req.threshold_val_primary}"

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO alert_rules (
                    rule_id, device_id, workspace_id, metric_key, operator,
                    threshold_val_primary, threshold_val_secondary, severity,
                    cooldown_seconds, description, is_enabled, last_triggered_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, NULL, ?);
                """,
                (
                    rule_id,
                    device_id,
                    req.workspace_id,
                    req.metric_key.strip().lower(),
                    req.operator,
                    req.threshold_val_primary,
                    req.threshold_val_secondary,
                    req.severity,
                    req.cooldown_seconds,
                    desc,
                    now,
                ),
            )
            conn.commit()

        return AlertRuleRecord(
            rule_id=rule_id,
            device_id=device_id,
            workspace_id=req.workspace_id,
            metric_key=req.metric_key.strip().lower(),
            operator=req.operator,
            threshold_val_primary=req.threshold_val_primary,
            threshold_val_secondary=req.threshold_val_secondary,
            severity=req.severity,
            cooldown_seconds=req.cooldown_seconds,
            description=desc,
            is_enabled=True,
            last_triggered_at=None,
            created_at=now,
        )

    def list_alert_rules(
        self, device_id: str, workspace_id: Optional[str] = None
    ) -> List[AlertRuleRecord]:
        with self._get_connection() as conn:
            query = "SELECT * FROM alert_rules WHERE device_id = ?"
            params: List[Any] = [device_id]
            if workspace_id:
                query += " AND workspace_id = ?"
                params.append(workspace_id)
            query += " ORDER BY created_at DESC;"

            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                AlertRuleRecord(
                    rule_id=r["rule_id"],
                    device_id=r["device_id"],
                    workspace_id=r["workspace_id"],
                    metric_key=r["metric_key"],
                    operator=r["operator"],
                    threshold_val_primary=r["threshold_val_primary"],
                    threshold_val_secondary=r["threshold_val_secondary"],
                    severity=r["severity"],
                    cooldown_seconds=r["cooldown_seconds"],
                    description=r["description"],
                    is_enabled=bool(r["is_enabled"]),
                    last_triggered_at=r["last_triggered_at"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def _evaluate_alert_rules(
        self,
        device_id: str,
        device_name: str,
        workspace_id: str,
        metrics: Dict[str, float],
        data_provenance: TelemetryDataProvenance,
        now_iso: str,
    ) -> List[str]:
        triggered_desc: List[str] = []
        now_dt = datetime.fromisoformat(now_iso)

        with self._get_connection() as conn:
            rules = conn.execute(
                "SELECT * FROM alert_rules WHERE device_id = ? AND is_enabled = 1;", (device_id,)
            ).fetchall()

            for r in rules:
                metric_key = r["metric_key"]
                if metric_key not in metrics:
                    continue

                val = metrics[metric_key]
                op = r["operator"]
                p1 = r["threshold_val_primary"]
                p2 = r["threshold_val_secondary"]
                is_breached = False

                if op == "gt" and val > p1:
                    is_breached = True
                elif op == "lt" and val < p1:
                    is_breached = True
                elif op == "gte" and val >= p1:
                    is_breached = True
                elif op == "lte" and val <= p1:
                    is_breached = True
                elif op == "eq" and abs(val - p1) < 1e-5:
                    is_breached = True
                elif op == "neq" and abs(val - p1) >= 1e-5:
                    is_breached = True
                elif op == "outside_range" and p2 is not None and (val < p1 or val > p2):
                    is_breached = True

                if is_breached:
                    # Check Cooldown
                    last_trig = r["last_triggered_at"]
                    in_cooldown = False
                    if last_trig:
                        try:
                            last_dt = datetime.fromisoformat(last_trig)
                            if (now_dt - last_dt).total_seconds() < r["cooldown_seconds"]:
                                in_cooldown = True
                        except Exception:
                            in_cooldown = False

                    if not in_cooldown:
                        alert_id = f"alt_{secrets.token_hex(6)}"
                        cooldown_until = datetime.fromtimestamp(
                            now_dt.timestamp() + r["cooldown_seconds"], tz=timezone.utc
                        ).isoformat()
                        desc = f"{r['description']} (measured: {val})"

                        conn.execute(
                            """
                            INSERT INTO alert_records (
                                alert_id, rule_id, device_id, device_name, workspace_id,
                                metric_key, measured_value, threshold_description,
                                severity, status, data_provenance, cooldown_until,
                                created_at, resolved_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, NULL);
                            """,
                            (
                                alert_id,
                                r["rule_id"],
                                device_id,
                                device_name,
                                workspace_id,
                                metric_key,
                                val,
                                desc,
                                r["severity"],
                                data_provenance,
                                cooldown_until,
                                now_iso,
                            ),
                        )
                        conn.execute(
                            "UPDATE alert_rules SET last_triggered_at = ? WHERE rule_id = ?;",
                            (now_iso, r["rule_id"]),
                        )
                        triggered_desc.append(desc)
                else:
                    # Auto-resolve previous active or acknowledged alerts for this rule when metric returns to safe bounds
                    conn.execute(
                        """
                        UPDATE alert_records
                        SET status = 'resolved', resolved_at = ?
                        WHERE rule_id = ? AND status IN ('active', 'acknowledged');
                        """,
                        (now_iso, r["rule_id"]),
                    )

            conn.commit()
        return triggered_desc

    def list_alerts(
        self,
        workspace_id: str,
        device_id: Optional[str] = None,
        status: Optional[AlertRecordStatus] = None,
    ) -> List[AlertRecord]:
        with self._get_connection() as conn:
            query = "SELECT * FROM alert_records WHERE workspace_id = ?"
            params: List[Any] = [workspace_id]
            if device_id:
                query += " AND device_id = ?"
                params.append(device_id)
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY created_at DESC LIMIT 100;"

            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                AlertRecord(
                    alert_id=r["alert_id"],
                    rule_id=r["rule_id"],
                    device_id=r["device_id"],
                    device_name=r["device_name"],
                    workspace_id=r["workspace_id"],
                    metric_key=r["metric_key"],
                    measured_value=r["measured_value"],
                    threshold_description=r["threshold_description"],
                    severity=r["severity"],
                    status=r["status"],
                    data_provenance=r["data_provenance"],
                    cooldown_until=r["cooldown_until"],
                    created_at=r["created_at"],
                    resolved_at=r["resolved_at"],
                )
                for r in rows
            ]

    def acknowledge_alert(
        self, alert_id: str, req: AlertAcknowledgeRequest
    ) -> AlertRecord:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM alert_records WHERE alert_id = ? AND workspace_id = ?;",
                (alert_id, req.workspace_id),
            ).fetchone()
            if not row:
                raise KeyError(f"Alert {alert_id} not found in workspace {req.workspace_id}")

            conn.execute(
                "UPDATE alert_records SET status = 'acknowledged' WHERE alert_id = ?;",
                (alert_id,),
            )
            conn.commit()

            updated = conn.execute(
                "SELECT * FROM alert_records WHERE alert_id = ?;", (alert_id,)
            ).fetchone()
            return AlertRecord(
                alert_id=updated["alert_id"],
                rule_id=updated["rule_id"],
                device_id=updated["device_id"],
                device_name=updated["device_name"],
                workspace_id=updated["workspace_id"],
                metric_key=updated["metric_key"],
                measured_value=updated["measured_value"],
                threshold_description=updated["threshold_description"],
                severity=updated["severity"],
                status=updated["status"],
                data_provenance=updated["data_provenance"],
                cooldown_until=updated["cooldown_until"],
                created_at=updated["created_at"],
                resolved_at=updated["resolved_at"],
            )

    # ------------------------------------------------------------------------
    # 4. Controlled Device Commands
    # ------------------------------------------------------------------------

    def create_command(
        self, device_id: str, req: DeviceCommandCreateRequest
    ) -> DeviceCommandRecord:
        device = self.get_device(device_id, user_id=req.user_id, workspace_id=req.workspace_id)
        if not device:
            raise KeyError(f"Device {device_id} not found in workspace {req.workspace_id}")

        is_consequential = req.command_type in CONSEQUENTIAL_COMMAND_TYPES
        requires_confirmation = is_consequential
        conf_status: CommandConfirmationStatus = (
            "pending_confirmation" if requires_confirmation else "confirmed"
        )
        dispatch_status: CommandDispatchStatus = (
            "queued" if requires_confirmation else "dispatched"
        )

        now = _utc_now_iso()
        cmd_id = f"cmd_{secrets.token_hex(6)}"
        result_msg = (
            "Consequential action queued. Explicit confirmation required before dispatch."
            if requires_confirmation
            else "Command dispatched to device ingestion topic."
        )
        dispatched_at = None if requires_confirmation else now
        acknowledged_at = None

        # Simulated device automatically acknowledges non-consequential commands
        if not requires_confirmation and device.is_simulated:
            dispatch_status = "acknowledged"
            acknowledged_at = now
            result_msg = f"Simulated device {device.name} acknowledged '{req.command_type}' command successfully."

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO device_commands (
                    command_id, device_id, device_name, workspace_id, user_id,
                    command_type, parameters_json, is_consequential, requires_confirmation,
                    confirmation_status, dispatch_status, result_message,
                    dispatched_at, acknowledged_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    cmd_id,
                    device_id,
                    device.name,
                    req.workspace_id,
                    req.user_id,
                    req.command_type,
                    json.dumps(req.parameters),
                    1 if is_consequential else 0,
                    1 if requires_confirmation else 0,
                    conf_status,
                    dispatch_status,
                    result_msg,
                    dispatched_at,
                    acknowledged_at,
                    now,
                ),
            )
            conn.commit()

        record = DeviceCommandRecord(
            command_id=cmd_id,
            device_id=device_id,
            device_name=device.name,
            workspace_id=req.workspace_id,
            user_id=req.user_id,
            command_type=req.command_type,
            parameters=req.parameters,
            is_consequential=is_consequential,
            requires_confirmation=requires_confirmation,
            confirmation_status=conf_status,
            dispatch_status=dispatch_status,
            result_message=result_msg,
            dispatched_at=dispatched_at,
            acknowledged_at=acknowledged_at,
            created_at=now,
        )

        self._broadcast_sse_event(device_id, {"type": "command", "command": record.model_dump()})
        return record

    def confirm_command(
        self, command_id: str, req: DeviceCommandConfirmRequest
    ) -> DeviceCommandRecord:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM device_commands WHERE command_id = ? AND workspace_id = ?;",
                (command_id, req.workspace_id),
            ).fetchone()
            if not row:
                raise KeyError(f"Command {command_id} not found in workspace {req.workspace_id}")

            device = self.get_device(row["device_id"], workspace_id=req.workspace_id)
            now = _utc_now_iso()

            if not req.confirmed:
                conf_status: CommandConfirmationStatus = "rejected"
                dispatch_status: CommandDispatchStatus = "failed"
                msg = "Command confirmation rejected by user. Command cancelled."
                dispatched_at = None
                ack_at = None
            else:
                conf_status = "confirmed"
                dispatch_status = "acknowledged" if (device and device.is_simulated) else "dispatched"
                msg = (
                    f"Command confirmed and executed by simulated device '{row['device_name']}'."
                    if (device and device.is_simulated)
                    else "Command confirmed and dispatched to target device MQTT/HTTP channel."
                )
                dispatched_at = now
                ack_at = now if (device and device.is_simulated) else None

            conn.execute(
                """
                UPDATE device_commands
                SET confirmation_status = ?, dispatch_status = ?, result_message = ?,
                    dispatched_at = ?, acknowledged_at = ?
                WHERE command_id = ?;
                """,
                (conf_status, dispatch_status, msg, dispatched_at, ack_at, command_id),
            )
            conn.commit()

            updated = conn.execute(
                "SELECT * FROM device_commands WHERE command_id = ?;", (command_id,)
            ).fetchone()

            record = DeviceCommandRecord(
                command_id=updated["command_id"],
                device_id=updated["device_id"],
                device_name=updated["device_name"],
                workspace_id=updated["workspace_id"],
                user_id=updated["user_id"],
                command_type=updated["command_type"],
                parameters=json.loads(updated["parameters_json"]),
                is_consequential=bool(updated["is_consequential"]),
                requires_confirmation=bool(updated["requires_confirmation"]),
                confirmation_status=updated["confirmation_status"],
                dispatch_status=updated["dispatch_status"],
                result_message=updated["result_message"],
                dispatched_at=updated["dispatched_at"],
                acknowledged_at=updated["acknowledged_at"],
                created_at=updated["created_at"],
            )
            self._broadcast_sse_event(record.device_id, {"type": "command", "command": record.model_dump()})
            return record

    def list_commands(
        self, device_id: str, workspace_id: Optional[str] = None
    ) -> List[DeviceCommandRecord]:
        with self._get_connection() as conn:
            query = "SELECT * FROM device_commands WHERE device_id = ?"
            params: List[Any] = [device_id]
            if workspace_id:
                query += " AND workspace_id = ?"
                params.append(workspace_id)
            query += " ORDER BY created_at DESC LIMIT 50;"

            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                DeviceCommandRecord(
                    command_id=r["command_id"],
                    device_id=r["device_id"],
                    device_name=r["device_name"],
                    workspace_id=r["workspace_id"],
                    user_id=r["user_id"],
                    command_type=r["command_type"],
                    parameters=json.loads(r["parameters_json"]),
                    is_consequential=bool(r["is_consequential"]),
                    requires_confirmation=bool(r["requires_confirmation"]),
                    confirmation_status=r["confirmation_status"],
                    dispatch_status=r["dispatch_status"],
                    result_message=r["result_message"],
                    dispatched_at=r["dispatched_at"],
                    acknowledged_at=r["acknowledged_at"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # ------------------------------------------------------------------------
    # 5. Deterministic Simulator Engine
    # ------------------------------------------------------------------------

    def simulate_tick(
        self, device_id: str, req: TelemetrySimulatorTickRequest
    ) -> TelemetrySimulatorResponse:
        device = self.get_device(device_id, user_id=req.user_id, workspace_id=req.workspace_id)
        if not device:
            raise KeyError(f"Device {device_id} not found in workspace {req.workspace_id}")
        if not device.is_simulated:
            raise ValueError(
                f"Device '{device.name}' ({device_id}) is registered as a physical hardware device. "
                "Simulated ticks can only be injected into simulated devices to prevent data contamination."
            )

        events: List[TelemetryEventRecord] = []
        all_triggered: List[str] = []

        now_sec = time.time()
        for i in range(req.tick_count):
            t_offset = now_sec + i * 2.0
            t_dt = datetime.fromtimestamp(t_offset, tz=timezone.utc)
            t_iso = t_dt.isoformat()

            # Mathematical sensor models
            # Diurnal sinusoidal temperature (mean 23.5°C, amplitude 4°C + noise)
            hour_angle = (t_dt.hour + t_dt.minute / 60.0) * (2 * math.pi / 24.0)
            temp = round(23.5 + 4.0 * math.sin(hour_angle) + random.uniform(-0.4, 0.4), 2)
            # Anti-correlated relative humidity (mean 58% + noise)
            hum = round(max(10.0, min(95.0, 58.0 - 5.0 * math.sin(hour_angle) + random.uniform(-1.0, 1.0))), 1)
            # Vibration baseline 0.42g with occasional peaks
            vib = round(0.42 + abs(random.gauss(0.0, 0.18)), 3)
            # Battery level and bus voltage
            v_bus = round(3.85 + 0.15 * math.sin(t_offset / 100.0) + random.uniform(-0.02, 0.02), 2)
            current_ma = round(145.0 + 35.0 * math.sin(t_offset / 30.0) + random.uniform(-5.0, 5.0), 1)

            # Anomaly injection
            if req.anomaly_inject == "spike_temperature":
                temp = 74.8
            elif req.anomaly_inject == "high_vibration":
                vib = 12.4
            elif req.anomaly_inject == "low_voltage":
                v_bus = 3.12
            elif req.anomaly_inject == "sensor_disconnect":
                temp = -999.0

            metrics = {
                "temperature": temp,
                "humidity": hum,
                "vibration": vib,
                "voltage": v_bus,
                "current": current_ma,
            }
            units = {
                "temperature": "°C",
                "humidity": "%RH",
                "vibration": "g",
                "voltage": "V",
                "current": "mA",
            }

            ingest_req = TelemetryIngestRequest(
                device_id=device_id,
                sequence_id=device.total_events_received + i + 1,
                device_timestamp=t_iso,
                metrics=metrics,
                units=units,
                firmware_version=device.firmware_version,
                battery_level_pct=round(max(5.0, min(100.0, (v_bus - 3.0) / 1.2 * 100.0)), 1),
                data_provenance="deterministic_simulation",
            )
            ingest_res = self.ingest_telemetry(ingest_req, device)
            if ingest_res.event_id:
                evt = self.get_event(ingest_res.event_id)
                if evt:
                    events.append(evt)
            all_triggered.extend(ingest_res.triggered_alerts)

        return TelemetrySimulatorResponse(
            device_id=device_id,
            ticks_generated=len(events),
            generated_events=events,
            triggered_alerts=list(dict.fromkeys(all_triggered)),
            message=f"Successfully generated {len(events)} deterministic simulated telemetry tick(s) for '{device.name}'.",
        )

    # ------------------------------------------------------------------------
    # 6. Query Events, Aggregated Stats & SSE Live Streaming
    # ------------------------------------------------------------------------

    def get_event(self, event_id: str) -> Optional[TelemetryEventRecord]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM telemetry_events WHERE event_id = ?;", (event_id,)).fetchone()
            if not row:
                return None
            return self._row_to_event(row)

    def list_events(
        self,
        device_id: str,
        workspace_id: Optional[str] = None,
        limit: int = 50,
        since_iso: Optional[str] = None,
    ) -> List[TelemetryEventRecord]:
        with self._get_connection() as conn:
            query = "SELECT * FROM telemetry_events WHERE device_id = ?"
            params: List[Any] = [device_id]
            if workspace_id:
                query += " AND workspace_id = ?"
                params.append(workspace_id)
            if since_iso:
                query += " AND ingestion_timestamp >= ?"
                params.append(since_iso)
            query += " ORDER BY ingestion_timestamp DESC LIMIT ?;"
            params.append(limit)

            rows = conn.execute(query, tuple(params)).fetchall()
            return [self._row_to_event(r) for r in rows]

    def _row_to_event(self, r: sqlite3.Row) -> TelemetryEventRecord:
        return TelemetryEventRecord(
            event_id=r["event_id"],
            device_id=r["device_id"],
            workspace_id=r["workspace_id"],
            sequence_id=r["sequence_id"],
            device_timestamp=r["device_timestamp"],
            ingestion_timestamp=r["ingestion_timestamp"],
            metrics=json.loads(r["metrics_json"]),
            units=json.loads(r["units_json"]),
            data_provenance=r["data_provenance"],
            is_valid=bool(r["is_valid"]),
            anomalies=json.loads(r["anomalies_json"]),
        )

    def get_device_stats(
        self, device_id: str, user_id: str, workspace_id: str
    ) -> TelemetryDeviceStatsResponse:
        device = self.get_device(device_id, user_id=user_id, workspace_id=workspace_id)
        if not device:
            raise KeyError(f"Device {device_id} not found in workspace {workspace_id}")

        recent = self.list_events(device_id, workspace_id=workspace_id, limit=60)
        active_alerts = self.list_alerts(workspace_id, device_id=device_id, status="active")
        commands = self.list_commands(device_id, workspace_id=workspace_id)
        pending_commands = [c for c in commands if c.dispatch_status in ("queued", "dispatched")]

        latest_metrics: Dict[str, float] = {}
        metric_ranges: Dict[str, Dict[str, float]] = {}

        if recent:
            latest_metrics = dict(recent[0].metrics)
            # Calculate min, max, avg for each metric across the sample
            all_keys = set().union(*(e.metrics.keys() for e in recent))
            for k in all_keys:
                vals = [e.metrics[k] for e in recent if k in e.metrics]
                if vals:
                    metric_ranges[k] = {
                        "min": round(min(vals), 2),
                        "max": round(max(vals), 2),
                        "avg": round(sum(vals) / len(vals), 2),
                        "current": round(vals[0], 2),
                    }

        freshness_label = "Never Connected"
        if device.last_reading_age_seconds is not None:
            if device.last_reading_age_seconds < 15.0:
                freshness_label = "Real-time Live (< 15s)"
            elif device.last_reading_age_seconds < 60.0:
                freshness_label = f"Fresh ({int(device.last_reading_age_seconds)}s ago)"
            elif device.last_reading_age_seconds < 300.0:
                freshness_label = f"Delayed ({int(device.last_reading_age_seconds / 60)}m ago)"
            else:
                freshness_label = f"Stale ({int(device.last_reading_age_seconds / 60)}m ago)"

        return TelemetryDeviceStatsResponse(
            device_id=device_id,
            device_name=device.name,
            status=device.status,
            is_simulated=device.is_simulated,
            last_seen_at=device.last_seen_at,
            last_seen_seconds_ago=device.last_reading_age_seconds,
            data_freshness_label=freshness_label,
            total_events=device.total_events_received,
            latest_metrics=latest_metrics,
            metric_ranges=metric_ranges,
            recent_events=recent[:25],
            active_alerts=active_alerts,
            pending_commands=pending_commands,
        )

    def _broadcast_sse_event(self, device_id: str, data: Dict[str, Any]) -> None:
        listeners = self._sse_listeners.get(device_id, [])
        for q in list(listeners):
            try:
                q.put_nowait(data)
            except Exception:
                pass

    def register_sse_listener(self, device_id: str, queue: asyncio.Queue) -> None:
        self._sse_listeners.setdefault(device_id, []).append(queue)

    def unregister_sse_listener(self, device_id: str, queue: asyncio.Queue) -> None:
        listeners = self._sse_listeners.get(device_id, [])
        if queue in listeners:
            listeners.remove(queue)

    # ------------------------------------------------------------------------
    # 7. Dataset Export & Integration
    # ------------------------------------------------------------------------

    def export_telemetry(
        self, device_id: str, req: TelemetryExportRequest
    ) -> TelemetryExportResponse:
        device = self.get_device(device_id, user_id=req.user_id, workspace_id=req.workspace_id)
        if not device:
            raise KeyError(f"Device {device_id} not found in workspace {req.workspace_id}")

        cutoff_iso = None
        now_ts = time.time()
        if req.time_range == "1h":
            cutoff_iso = datetime.fromtimestamp(now_ts - 3600, tz=timezone.utc).isoformat()
        elif req.time_range == "6h":
            cutoff_iso = datetime.fromtimestamp(now_ts - 6 * 3600, tz=timezone.utc).isoformat()
        elif req.time_range == "24h":
            cutoff_iso = datetime.fromtimestamp(now_ts - 24 * 3600, tz=timezone.utc).isoformat()
        elif req.time_range == "7d":
            cutoff_iso = datetime.fromtimestamp(now_ts - 7 * 86400, tz=timezone.utc).isoformat()

        events = self.list_events(
            device_id=device_id,
            workspace_id=req.workspace_id,
            limit=2000,
            since_iso=cutoff_iso,
        )

        export_id = f"exp_tel_{secrets.token_hex(6)}"
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{device.name.replace(' ', '_').lower()}_{device_id}_{req.time_range}_{now_str}.{req.format}"
        file_path = self.exports_dir / filename

        content_preview = ""
        if req.format == "csv":
            metric_cols = sorted(set().union(*(e.metrics.keys() for e in events))) if events else ["temperature"]
            fieldnames = [
                "event_id",
                "device_timestamp",
                "ingestion_timestamp",
                "data_provenance",
                "is_valid",
            ] + metric_cols

            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for e in reversed(events):
                    row: Dict[str, Any] = {
                        "event_id": e.event_id,
                        "device_timestamp": e.device_timestamp,
                        "ingestion_timestamp": e.ingestion_timestamp,
                        "data_provenance": e.data_provenance,
                        "is_valid": e.is_valid,
                    }
                    for m in metric_cols:
                        row[m] = e.metrics.get(m, "")
                    writer.writerow(row)

            # Generate short preview
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [f.readline() for _ in range(6)]
                content_preview = "".join(lines)
        else:
            json_data = [e.model_dump() for e in reversed(events)]
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2)
            content_preview = json.dumps(json_data[:3], indent=2)

        workspace_relative_path = None
        if req.handoff_to_file_workspace:
            ws_export_dir = Path(settings.file_workspace_root) / req.workspace_id / "telemetry_exports"
            ws_export_dir.mkdir(parents=True, exist_ok=True)
            ws_target = ws_export_dir / filename
            import shutil
            shutil.copyfile(str(file_path), str(ws_target))
            workspace_relative_path = f"telemetry_exports/{filename}"

        return TelemetryExportResponse(
            export_id=export_id,
            device_id=device_id,
            format=req.format,
            time_range=req.time_range,
            total_events_exported=len(events),
            file_path=str(file_path),
            workspace_relative_path=workspace_relative_path,
            content_preview=content_preview,
            exported_at=_utc_now_iso(),
        )

    # ------------------------------------------------------------------------
    # 8. Platform Metadata
    # ------------------------------------------------------------------------

    def get_metadata(self) -> TelemetryMetadataResponse:
        metrics_list = [
            {"key": k, "unit": v["unit"], "min": v["min"], "max": v["max"], "description": v["desc"]}
            for k, v in METRIC_PHYSICAL_BOUNDS.items()
        ]
        return TelemetryMetadataResponse(
            stage=25,
            engine="IoTTelemetryEngine",
            supported_metrics=metrics_list,
            supported_protocols=["http", "mqtt", "dual"],
            mqtt_broker_config={
                "broker_host": settings.mqtt_broker_host,
                "broker_port": settings.mqtt_broker_port,
                "tls_enabled": settings.mqtt_use_tls,
                "topic_template_telemetry": "nexora/{workspace_id}/{device_id}/telemetry",
                "topic_template_commands": "nexora/{workspace_id}/{device_id}/commands",
            },
            security_policy={
                "token_storage": "salted_pbkdf2_hmac_sha256",
                "plaintext_tokens_never_stored": True,
                "header_name": "X-Device-Token",
                "consequential_commands_require_confirmation": True,
                "rate_limiting_enforced": True,
            },
            reliability_specs={
                "max_payload_size_bytes": settings.telemetry_max_payload_size_bytes,
                "max_events_retention_per_device": settings.telemetry_max_events_per_device,
                "offline_timeout_seconds": settings.telemetry_offline_timeout_seconds,
                "default_alert_cooldown_seconds": settings.telemetry_default_cooldown_seconds,
            },
        )


iot_telemetry_engine = IoTTelemetryEngine()
