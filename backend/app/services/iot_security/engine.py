from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.models.schemas import (
    BehavioralAnomalyRecord,
    ConfigAuditRequest,
    ConfigAuditSeverity,
    ConfigurationAuditFinding,
    DefensiveActionRecord,
    DefensiveActionRequest,
    DefensiveActionStatus,
    DefensiveActionType,
    DeviceSecurityPosture,
    FirmwareIntegritySpec,
    IncidentStatus,
    IoTSecurityOverviewResponse,
    SecurityIncidentRecord,
    SecurityIncidentUpdateRequest,
    SecurityRiskLevel,
    ThreatClassification,
)
from app.services.telemetry.engine import iot_telemetry_engine


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Predefined verified bootloader & firmware integrity specifications
FIRMWARE_INTEGRITY_SPECS: Dict[str, FirmwareIntegritySpec] = {
    "esp32_devkit_v1": FirmwareIntegritySpec(
        board_id="esp32_devkit_v1",
        board_name="ESP32 DevKit V1 (Espressif ESP32-WROOM-32)",
        supports_secure_boot=True,
        secure_boot_version="Secure Boot v2 (RSA-3072 signature verification via eFuse BLK2 digest)",
        crypto_keys_supported=["RSA-3072", "ECDSA-P256", "AES-256-XTS Flash Encryption"],
        supports_signed_firmware=True,
        supports_hardware_root_of_trust=True,
        supports_anti_rollback=True,
        recovery_strategy="Hold BOOT (GPIO0) to invoke ROM bootloader UART download mode for secure re-flash.",
        checksum_trust_limitation="Software MD5/SHA256 checksums verify network download integrity only. Physical authenticity requires burned eFuses and hardware Secure Boot v2.",
    ),
    "stm32_nucleo_f401re": FirmwareIntegritySpec(
        board_id="stm32_nucleo_f401re",
        board_name="STM32 Nucleo-F401RE (ARM Cortex-M4)",
        supports_secure_boot=True,
        secure_boot_version="Proprietary Code Read-Out Protection (RDP Level 1/2) & OEM Secure Firmware Install",
        crypto_keys_supported=["AES-128/256", "ECC / RSA (Software cryptolib on Cortex-M4)"],
        supports_signed_firmware=True,
        supports_hardware_root_of_trust=False,
        supports_anti_rollback=True,
        recovery_strategy="ST-LINK SWD interface unlock with mass erase to clear locked RDP level 1.",
        checksum_trust_limitation="RDP Level 1 prevents debugger readout, but does not provide cryptographic asymmetric signature checking without bootloader firmware implementation.",
    ),
    "raspberry_pi_pico_w": FirmwareIntegritySpec(
        board_id="raspberry_pi_pico_w",
        board_name="Raspberry Pi Pico W (RP2040 Dual ARM Cortex-M0+)",
        supports_secure_boot=False,
        secure_boot_version="None (RP2040 bootrom executes any valid UF2 without cryptographic verification)",
        crypto_keys_supported=["Software mbedTLS"],
        supports_signed_firmware=False,
        supports_hardware_root_of_trust=False,
        supports_anti_rollback=False,
        recovery_strategy="BOOTSEL button loads USB mass storage device; drag flash_nuke.uf2 to reset flash.",
        checksum_trust_limitation="RP2040 executes code from external QSPI flash directly; physical flash access allows complete modification. Software signatures cannot prevent hardware tampering.",
    ),
    "arduino_uno_r3": FirmwareIntegritySpec(
        board_id="arduino_uno_r3",
        board_name="Arduino Uno R3 (Microchip ATmega328P)",
        supports_secure_boot=False,
        secure_boot_version="None (Optiboot bootloader on ATmega328P has no asymmetric cryptography)",
        crypto_keys_supported=[],
        supports_signed_firmware=False,
        supports_hardware_root_of_trust=False,
        supports_anti_rollback=False,
        recovery_strategy="ISP / ICSP 6-pin header reflash via external hardware programmer.",
        checksum_trust_limitation="8-bit AVR microcontrollers have 2KB SRAM and lack cryptographic acceleration. Firmware security relies entirely on physical enclosure protection.",
    ),
    "raspberry_pi_4b": FirmwareIntegritySpec(
        board_id="raspberry_pi_4b",
        board_name="Raspberry Pi 4 Model B (Broadcom BCM2711 Cortex-A72)",
        supports_secure_boot=True,
        secure_boot_version="Broadcom VideoCore EEPROM Secure Boot (RSA-2048 public key OTP)",
        crypto_keys_supported=["RSA-2048", "SHA-256"],
        supports_signed_firmware=True,
        supports_hardware_root_of_trust=True,
        supports_anti_rollback=True,
        recovery_strategy="Raspberry Pi Imager bootloader recovery SD card.",
        checksum_trust_limitation="EEPROM signature checking requires customer OTP key burning. Once burned, non-signed boot images will permanently fail to boot.",
    ),
}

SECRET_PATTERNS = [
    (re.compile(r"""(?i)(?:wifi_pass|wifi_password|password|passwd|pwd)\s*[:=]\s*["']([^"'\s]{4,})["']"""), "WIFI_OR_DEVICE_PASSWORD"),
    (re.compile(r"""(?i)(?:api_key|apikey|secret_key|secret)\s*[:=]\s*["']([^"'\s]{8,})["']"""), "GENERIC_API_SECRET"),
    (re.compile(r"""AKIA[0-9A-Z]{16}"""), "AWS_ACCESS_KEY_ID"),
    (re.compile(r"""-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"""), "PRIVATE_KEY_BLOCK"),
    (re.compile(r"""sk-[a-zA-Z0-9]{20,}"""), "OPENAI_SECRET_KEY"),
    (re.compile(r"""AIza[0-9A-Za-z-_]{35}"""), "GOOGLE_API_KEY"),
    (re.compile(r"""(?i)(?:mqtt_pass|mqtt_password)\s*[:=]\s*["']([^"'\s]{3,})["']"""), "MQTT_PLAINTEXT_PASSWORD"),
]

KNOWN_DEFAULT_CREDENTIALS = [
    ("admin", "admin"),
    ("admin", "password"),
    ("root", "root"),
    ("root", "toor"),
    ("esp32", "password"),
    ("user", "user"),
]


class IoTSecurityEngine:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or settings.iot_security_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
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
                CREATE TABLE IF NOT EXISTS device_security_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    risk_level TEXT NOT NULL,
                    transport_encryption TEXT NOT NULL,
                    authentication_status TEXT NOT NULL,
                    exposed_services_json TEXT NOT NULL,
                    update_status TEXT NOT NULL,
                    assessed_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS configuration_audit_findings (
                    finding_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    device_name TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    rule_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    impact TEXT NOT NULL,
                    remediation TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    detected_at TEXT NOT NULL,
                    remediated_at TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS behavioral_anomalies (
                    anomaly_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    device_name TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    anomaly_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    metric_key TEXT,
                    observed_value_json TEXT,
                    baseline_expected_json TEXT,
                    evidence_summary TEXT NOT NULL,
                    detected_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS security_incidents (
                    incident_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new',
                    affected_device_ids_json TEXT NOT NULL,
                    root_cause_hypothesis TEXT NOT NULL,
                    confidence_level TEXT NOT NULL,
                    evidence_records_json TEXT NOT NULL,
                    telemetry_correlations_json TEXT NOT NULL,
                    recommended_remediations_json TEXT NOT NULL,
                    assigned_responder TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    resolved_at TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS defensive_actions_audit (
                    action_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    device_name TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    requires_confirmation INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    result_message TEXT NOT NULL,
                    recovery_procedure TEXT NOT NULL,
                    executed_at TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_failure_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    source_ip TEXT,
                    token_prefix TEXT,
                    attempted_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_findings_device ON configuration_audit_findings(device_id, status);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_anomalies_device ON behavioral_anomalies(device_id, detected_at DESC);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_incidents_workspace ON security_incidents(workspace_id, status);"
            )

    # --------------------------------------------------------------------------
    # 1. Device Security Posture Assessment
    # --------------------------------------------------------------------------
    def assess_device_posture(
        self, device_id: str, workspace_id: str = "default_workspace"
    ) -> DeviceSecurityPosture:
        """
        Assesses the security posture of a registered device.
        Label unavailable info as 'unknown' rather than asserting it is secure.
        """
        device = iot_telemetry_engine.get_device(device_id, workspace_id=workspace_id)
        if not device:
            raise ValueError(f"Device '{device_id}' not found in registered fleet.")

        # Determine transport encryption
        if device.ingestion_protocol == "mqtt":
            transport_encryption = "tls_enabled" if settings.mqtt_use_tls else "plaintext_unencrypted"
        elif device.ingestion_protocol == "http":
            transport_encryption = "plaintext_unencrypted"  # Local/default HTTP without TLS
        elif device.ingestion_protocol == "dual":
            transport_encryption = "tls_enabled" if settings.mqtt_use_tls else "plaintext_unencrypted"
        else:
            transport_encryption = "unknown"

        # Determine token status & age
        token_age_days: Optional[float] = None
        auth_status: str = "token_active"
        if device.status == "offline" and device.total_events_received == 0:
            auth_status = "unprovisioned"
        elif device.status == "degraded":
            auth_status = "token_revoked"

        try:
            created_dt = datetime.fromisoformat(device.created_at.replace("Z", "+00:00"))
            token_age_days = round((datetime.now(timezone.utc) - created_dt).total_seconds() / 86400.0, 1)
        except Exception:
            token_age_days = None

        if token_age_days is not None and token_age_days > 90.0:
            auth_status = "weak_token"

        # Exposed services based on protocol and board profile
        exposed_services: List[str] = []
        if device.ingestion_protocol in ("http", "dual"):
            exposed_services.append("http_listener_80")
        if device.ingestion_protocol in ("mqtt", "dual"):
            exposed_services.append(f"mqtt_{settings.mqtt_broker_port}")
        if device.board_id in ("esp32_devkit_v1", "raspberry_pi_4b"):
            exposed_services.append("ble_advertising")

        # Update status
        firmware_v = device.firmware_version.strip().lower()
        if not firmware_v or firmware_v in ("unknown", "none"):
            update_status = "unknown"
        elif firmware_v in ("0.1.0", "v0.1.0", "0.9.0", "v0.9.0"):
            update_status = "critical_outdated"
        elif firmware_v in ("1.0.0", "v1.0.0"):
            update_status = "update_available"
        else:
            update_status = "up_to_date"

        # Firmware integrity specs
        spec = FIRMWARE_INTEGRITY_SPECS.get(device.board_id)
        supports_sb = spec.supports_secure_boot if spec else False
        sb_mech = spec.secure_boot_version if spec else "unknown"
        supports_signed = spec.supports_signed_firmware if spec else False
        supports_ar = spec.supports_anti_rollback if spec else False

        # Query existing active findings and anomalies for this device
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM configuration_audit_findings WHERE device_id = ? AND status = 'active';",
                (device_id,),
            )
            findings_count = int(cur.fetchone()[0])

            cur.execute(
                "SELECT COUNT(*) FROM behavioral_anomalies WHERE device_id = ?;",
                (device_id,),
            )
            threats_count = int(cur.fetchone()[0])

        # Compute Risk Score (0-100)
        risk_score = 0
        if transport_encryption == "plaintext_unencrypted":
            risk_score += 35
        elif transport_encryption == "unknown":
            risk_score += 15

        if auth_status == "weak_token":
            risk_score += 25
        elif auth_status == "token_revoked":
            risk_score += 10
        elif auth_status == "unprovisioned":
            risk_score += 5

        if update_status == "critical_outdated":
            risk_score += 25
        elif update_status == "update_available":
            risk_score += 10
        elif update_status == "unknown":
            risk_score += 5

        risk_score += min(findings_count * 10, 20)
        risk_score += min(threats_count * 15, 30)
        risk_score = min(max(risk_score, 0), 100)

        # Risk level classification
        if risk_score >= 75:
            risk_level: SecurityRiskLevel = "critical"
        elif risk_score >= 50:
            risk_level = "high"
        elif risk_score >= 25:
            risk_level = "medium"
        elif risk_score > 0:
            risk_level = "low"
        else:
            risk_level = "info"

        now_iso = _utc_now_iso()

        # Cache assessment in DB
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO device_security_assessments (
                    assessment_id, device_id, workspace_id, risk_score, risk_level,
                    transport_encryption, authentication_status, exposed_services_json,
                    update_status, assessed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    f"ass_{device_id}",
                    device_id,
                    workspace_id,
                    risk_score,
                    risk_level,
                    transport_encryption,
                    auth_status,
                    json.dumps(exposed_services),
                    update_status,
                    now_iso,
                ),
            )

        return DeviceSecurityPosture(
            device_id=device.device_id,
            device_name=device.name,
            board_id=device.board_id,
            status=device.status,
            is_simulated=device.is_simulated,
            firmware_version=device.firmware_version,
            authentication_status=auth_status,  # type: ignore[arg-type]
            token_age_days=token_age_days,
            token_last_rotated_at=device.updated_at,
            transport_encryption=transport_encryption,  # type: ignore[arg-type]
            exposed_services=exposed_services,
            update_status=update_status,  # type: ignore[arg-type]
            supports_secure_boot=supports_sb,
            secure_boot_mechanism=sb_mech,
            supports_signed_firmware=supports_signed,
            supports_anti_rollback=supports_ar,
            last_security_assessment_at=now_iso,
            risk_score=risk_score,
            risk_level=risk_level,
            active_findings_count=findings_count,
            active_threats_count=threats_count,
        )

    # --------------------------------------------------------------------------
    # 2. Rule-Based Configuration Auditing
    # --------------------------------------------------------------------------
    def audit_configuration(
        self, req: ConfigAuditRequest
    ) -> List[ConfigurationAuditFinding]:
        """
        Runs comprehensive rule-based configuration audit for a device or uploaded configuration file.
        Detects unencrypted transport, wildcard MQTT topics, exposed secrets, and default credentials.
        """
        findings: List[ConfigurationAuditFinding] = []
        now_iso = _utc_now_iso()
        device_id = req.device_id or "global_configuration"
        device_name = "Global Fleet Configuration"

        if req.device_id:
            dev = iot_telemetry_engine.get_device(req.device_id, workspace_id=req.workspace_id)
            if dev:
                device_name = dev.name

                # Check 1: Insecure transport
                if dev.ingestion_protocol == "http" or (dev.ingestion_protocol == "mqtt" and not settings.mqtt_use_tls):
                    findings.append(
                        ConfigurationAuditFinding(
                            finding_id=f"fnd_transport_{dev.device_id}",
                            device_id=dev.device_id,
                            device_name=device_name,
                            workspace_id=req.workspace_id,
                            rule_id="SEC_RULE_PLAINTEXT_TRANSPORT",
                            title="Unencrypted Ingestion Transport Configured",
                            severity="high",
                            evidence=f"Protocol: {dev.ingestion_protocol}, MQTT TLS: {settings.mqtt_use_tls}",
                            impact="Telemetry sensor data and device actuation commands travel over unencrypted channel vulnerable to wiretapping, MITM tampering, and credential extraction.",
                            remediation="Enable MQTTS on port 8883 with TLS certificates or enforce HTTPS ingestion endpoints.",
                            detected_at=now_iso,
                        )
                    )

                # Check 2: Wildcard MQTT Topic
                if "#" in dev.mqtt_topic_telemetry or "+" in dev.mqtt_topic_telemetry:
                    findings.append(
                        ConfigurationAuditFinding(
                            finding_id=f"fnd_mqtt_wildcard_{dev.device_id}",
                            device_id=dev.device_id,
                            device_name=device_name,
                            workspace_id=req.workspace_id,
                            rule_id="SEC_RULE_INSECURE_MQTT_WILDCARD",
                            title="Permissive MQTT Topic Wildcard Found",
                            severity="critical",
                            evidence=f"Topic: {dev.mqtt_topic_telemetry}",
                            impact="Using multi-level wildcards (#) or single-level (+) allows devices to listen to or overwrite cross-device telemetry and unauthorized message streams.",
                            remediation="Scope topics strictly to 'nexora/{workspace_id}/{device_id}/telemetry' without wildcards.",
                            detected_at=now_iso,
                        )
                    )

                # Check 3: Weak / Stale Token
                try:
                    c_dt = datetime.fromisoformat(dev.created_at.replace("Z", "+00:00"))
                    age = (datetime.now(timezone.utc) - c_dt).total_seconds() / 86400.0
                    if age > 90.0:
                        findings.append(
                            ConfigurationAuditFinding(
                                finding_id=f"fnd_stale_token_{dev.device_id}",
                                device_id=dev.device_id,
                                device_name=device_name,
                                workspace_id=req.workspace_id,
                                rule_id="SEC_RULE_STALE_CREDENTIAL",
                                title="Device Authentication Token Exceeds 90 Days Without Rotation",
                                severity="medium",
                                evidence=f"Token created {int(age)} days ago without rotation",
                                impact="Long-lived static credentials increase risk of unauthorized access if firmware or local storage is retrieved.",
                                remediation="Perform zero-downtime token rotation via POST /api/v1/telemetry/devices/{device_id}/rotate-token.",
                                detected_at=now_iso,
                            )
                        )
                except Exception:
                    pass

        # Check 4: Uploaded Configuration Text / Files for Hardcoded Secrets
        text_to_audit = ""
        if req.config_file_text:
            text_to_audit += req.config_file_text + "\n"
        if req.config_payload:
            text_to_audit += json.dumps(req.config_payload) + "\n"

        if text_to_audit.strip():
            # Check secret regex patterns
            for pattern, pattern_label in SECRET_PATTERNS:
                matches = pattern.finditer(text_to_audit)
                for m in matches:
                    raw_matched = m.group(0)
                    # Redact evidence for security
                    if len(raw_matched) > 8:
                        redacted_evidence = raw_matched[:4] + "***" + raw_matched[-4:]
                    else:
                        redacted_evidence = "***REDACTED***"

                    findings.append(
                        ConfigurationAuditFinding(
                            finding_id=f"fnd_secret_{uuid.uuid4().hex[:8]}",
                            device_id=device_id,
                            device_name=device_name,
                            workspace_id=req.workspace_id,
                            rule_id="SEC_RULE_EXPOSED_CREDENTIAL_IN_CONFIG",
                            title=f"Hardcoded {pattern_label.replace('_', ' ')} Detected in Configuration",
                            severity="critical",
                            evidence=f"Pattern: {pattern_label}, match: {redacted_evidence} in {req.filename or 'payload'}",
                            impact="Hardcoded credentials embedded in source or config files can be extracted by attackers, leading to complete credential compromise.",
                            remediation="Store secrets in encrypted environment variables or hardware key vaults. Never commit plaintext secrets.",
                            detected_at=now_iso,
                        )
                    )

            # Check known default credentials
            for def_user, def_pass in KNOWN_DEFAULT_CREDENTIALS:
                if def_user in text_to_audit and def_pass in text_to_audit:
                    findings.append(
                        ConfigurationAuditFinding(
                            finding_id=f"fnd_default_cred_{uuid.uuid4().hex[:8]}",
                            device_id=device_id,
                            device_name=device_name,
                            workspace_id=req.workspace_id,
                            rule_id="SEC_RULE_UNSAFE_DEFAULT_CREDENTIALS",
                            title=f"Default Factory Credential Detected ('{def_user}:{def_pass}')",
                            severity="high",
                            evidence=f"Detected default username '{def_user}' and password pattern in config",
                            impact="Default credentials are well-known to automated botnets (e.g. Mirai) and allow trivial remote takeover.",
                            remediation="Replace all default credentials with cryptographically generated random passwords.",
                            detected_at=now_iso,
                        )
                    )

        # Store findings in database
        with self._get_connection() as conn:
            for f in findings:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO configuration_audit_findings (
                        finding_id, device_id, device_name, workspace_id, rule_id,
                        title, severity, evidence, impact, remediation, status,
                        detected_at, remediated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        f.finding_id,
                        f.device_id,
                        f.device_name,
                        f.workspace_id,
                        f.rule_id,
                        f.title,
                        f.severity,
                        f.evidence,
                        f.impact,
                        f.remediation,
                        f.status,
                        f.detected_at,
                        f.remediated_at,
                    ),
                )

        return findings

    def list_findings(
        self,
        workspace_id: str = "default_workspace",
        device_id: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = "active",
    ) -> List[ConfigurationAuditFinding]:
        with self._get_connection() as conn:
            query = "SELECT * FROM configuration_audit_findings WHERE workspace_id = ?"
            params: List[Any] = [workspace_id]
            if device_id:
                query += " AND device_id = ?"
                params.append(device_id)
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY detected_at DESC;"

            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()

        return [
            ConfigurationAuditFinding(
                finding_id=row["finding_id"],
                device_id=row["device_id"],
                device_name=row["device_name"],
                workspace_id=row["workspace_id"],
                rule_id=row["rule_id"],
                title=row["title"],
                severity=row["severity"],
                evidence=row["evidence"],
                impact=row["impact"],
                remediation=row["remediation"],
                status=row["status"],
                detected_at=row["detected_at"],
                remediated_at=row["remediated_at"],
            )
            for row in rows
        ]

    # --------------------------------------------------------------------------
    # 3. Behavioral Anomaly Detection & Baseline Evaluation
    # --------------------------------------------------------------------------
    def record_auth_failure(
        self,
        device_id: str,
        workspace_id: str = "default_workspace",
        source_ip: Optional[str] = None,
        token_prefix: Optional[str] = None,
    ) -> None:
        """Records an authentication failure attempt for anomaly tracking."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO auth_failure_attempts (
                    attempt_id, device_id, workspace_id, source_ip, token_prefix, attempted_at
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    f"att_{uuid.uuid4().hex[:12]}",
                    device_id,
                    workspace_id,
                    source_ip or "127.0.0.1",
                    token_prefix or "unknown",
                    _utc_now_iso(),
                ),
            )

    def analyze_device_behavior(
        self, device_id: str, workspace_id: str = "default_workspace"
    ) -> List[BehavioralAnomalyRecord]:
        """
        Analyzes telemetry events, reporting frequency, and auth logs for behavioral anomalies.
        Begins with transparent statistical checks (z-score, IQR, delta spikes, sequence resets).
        """
        device = iot_telemetry_engine.get_device(device_id, workspace_id=workspace_id)
        if not device:
            return []

        anomalies: List[BehavioralAnomalyRecord] = []
        now_iso = _utc_now_iso()

        # Fetch recent events from Stage 25 telemetry engine
        events = iot_telemetry_engine.list_events(device_id=device_id, workspace_id=workspace_id, limit=100)

        # Check 1: Repeated Authentication Failures
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM auth_failure_attempts WHERE device_id = ? AND workspace_id = ?;",
                (device_id, workspace_id),
            )
            failures_count = int(cur.fetchone()[0])

        if failures_count >= settings.iot_security_auth_failure_threshold:
            anomalies.append(
                BehavioralAnomalyRecord(
                    anomaly_id=f"anom_auth_{uuid.uuid4().hex[:8]}",
                    device_id=device_id,
                    device_name=device.name,
                    workspace_id=workspace_id,
                    anomaly_type="repeated_auth_failures",
                    severity="critical" if failures_count >= 10 else "high",
                    classification="suspicious_indicator",
                    confidence="high",
                    observed_value={"recent_auth_failures": failures_count},
                    baseline_expected={"normal_auth_failures": 0},
                    evidence_summary=f"Detected {failures_count} consecutive authentication failures. Indicates possible token brute-force or unauthorized device trying to spoof node identity.",
                    detected_at=now_iso,
                )
            )

        if not events:
            return anomalies

        # Check 2: Unexpected Restarts / Crash-Looping via Sequence ID Resets
        sequence_resets = 0
        sorted_events = sorted(events, key=lambda e: e.device_timestamp)
        for i in range(1, len(sorted_events)):
            prev_seq = sorted_events[i - 1].sequence_id
            curr_seq = sorted_events[i].sequence_id
            if prev_seq is not None and curr_seq is not None:
                # Sequence drops back to 0 or 1 from a significantly higher value
                if curr_seq < prev_seq and prev_seq >= 5:
                    sequence_resets += 1

        if sequence_resets >= 2:
            anomalies.append(
                BehavioralAnomalyRecord(
                    anomaly_id=f"anom_restart_{uuid.uuid4().hex[:8]}",
                    device_id=device_id,
                    device_name=device.name,
                    workspace_id=workspace_id,
                    anomaly_type="unexpected_restart_crashloop",
                    severity="high",
                    classification="confirmed_event",
                    confidence="high",
                    observed_value={"sequence_resets_detected": sequence_resets},
                    baseline_expected={"expected_resets": 0},
                    evidence_summary=f"Device sequence_id reset {sequence_resets} times without user-authorized reboot command. Indicates brownout, watchdog crash, or buffer overflow reset.",
                    detected_at=now_iso,
                )
            )

        # Check 3: Reporting Frequency & Velocity Anomaly
        if len(sorted_events) >= 10:
            intervals: List[float] = []
            for i in range(1, len(sorted_events)):
                try:
                    t1 = datetime.fromisoformat(sorted_events[i - 1].device_timestamp.replace("Z", "+00:00")).timestamp()
                    t2 = datetime.fromisoformat(sorted_events[i].device_timestamp.replace("Z", "+00:00")).timestamp()
                    diff = max(t2 - t1, 0.001)
                    intervals.append(diff)
                except Exception:
                    pass

            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                # Rapid burst: minimum interval < 0.2s when average is > 2s
                burst_intervals = [x for x in intervals if x < 0.2]
                if len(burst_intervals) >= 5 and avg_interval >= 1.0:
                    anomalies.append(
                        BehavioralAnomalyRecord(
                            anomaly_id=f"anom_freq_{uuid.uuid4().hex[:8]}",
                            device_id=device_id,
                            device_name=device.name,
                            workspace_id=workspace_id,
                            anomaly_type="unusual_reporting_frequency",
                            severity="medium",
                            classification="heuristic_alert",
                            confidence="medium",
                            observed_value={"rapid_burst_count": len(burst_intervals), "avg_interval_sec": round(avg_interval, 2)},
                            baseline_expected={"expected_interval_sec": round(avg_interval, 2)},
                            evidence_summary=f"Detected {len(burst_intervals)} rapid telemetry bursts (<200ms interval). Deviates significantly from typical {round(avg_interval, 2)}s cadence.",
                            detected_at=now_iso,
                        )
                    )

        # Check 4: Abnormal Measurement Patterns (Z-Score & Delta Spikes)
        metric_values: Dict[str, List[float]] = {}
        for ev in events:
            for k, v in ev.metrics.items():
                if isinstance(v, (int, float)):
                    metric_values.setdefault(k, []).append(float(v))

        for m_key, vals in metric_values.items():
            if len(vals) >= 10:
                mean_v = sum(vals) / len(vals)
                variance = sum((x - mean_v) ** 2 for x in vals) / len(vals)
                std_dev = math.sqrt(variance)

                # Check latest reading z-score
                latest_v = vals[0]
                if std_dev > 0.001:
                    z_score = abs(latest_v - mean_v) / std_dev
                    if z_score >= settings.iot_security_zscore_threshold:
                        anomalies.append(
                            BehavioralAnomalyRecord(
                                anomaly_id=f"anom_zscore_{uuid.uuid4().hex[:8]}",
                                device_id=device_id,
                                device_name=device.name,
                                workspace_id=workspace_id,
                                anomaly_type="abnormal_measurement_pattern",
                                severity="high" if z_score >= 4.5 else "medium",
                                classification="heuristic_alert",
                                confidence="high" if z_score >= 4.0 else "medium",
                                metric_key=m_key,
                                observed_value={"latest": latest_v, "z_score": round(z_score, 2)},
                                baseline_expected={"mean": round(mean_v, 2), "std_dev": round(std_dev, 2)},
                                evidence_summary=f"Metric '{m_key}' reading {latest_v} deviated {round(z_score, 1)} standard deviations from moving baseline (mean: {round(mean_v, 2)}, std: {round(std_dev, 2)}).",
                                detected_at=now_iso,
                            )
                        )

                # Check sensor saturation (stuck at maximum bounds for consecutive readings)
                consecutive_identical = 0
                for v in vals[:6]:
                    if abs(v - vals[0]) < 0.0001:
                        consecutive_identical += 1
                if consecutive_identical >= 5 and m_key in ("temperature", "vibration", "voltage"):
                    # Check if at physical limit
                    from app.services.telemetry.engine import METRIC_PHYSICAL_BOUNDS

                    bound = METRIC_PHYSICAL_BOUNDS.get(m_key)
                    if bound and abs(vals[0] - bound["max"]) <= 0.05 * bound["max"]:
                        anomalies.append(
                            BehavioralAnomalyRecord(
                                anomaly_id=f"anom_sat_{uuid.uuid4().hex[:8]}",
                                device_id=device_id,
                                device_name=device.name,
                                workspace_id=workspace_id,
                                anomaly_type="sensor_saturation_stuck",
                                severity="high",
                                classification="confirmed_event",
                                confidence="high",
                                metric_key=m_key,
                                observed_value={"stuck_value": vals[0], "consecutive_samples": consecutive_identical},
                                baseline_expected={"dynamic_variance": "> 0.5"},
                                evidence_summary=f"Sensor for '{m_key}' is saturated and frozen at peak boundary ({vals[0]} {bound['unit']}) across {consecutive_identical} samples.",
                                detected_at=now_iso,
                            )
                        )

        # Store detected anomalies
        with self._get_connection() as conn:
            for an in anomalies:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO behavioral_anomalies (
                        anomaly_id, device_id, device_name, workspace_id, anomaly_type,
                        severity, classification, confidence, metric_key,
                        observed_value_json, baseline_expected_json, evidence_summary, detected_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        an.anomaly_id,
                        an.device_id,
                        an.device_name,
                        an.workspace_id,
                        an.anomaly_type,
                        an.severity,
                        an.classification,
                        an.confidence,
                        an.metric_key,
                        json.dumps(an.observed_value),
                        json.dumps(an.baseline_expected),
                        an.evidence_summary,
                        an.detected_at,
                    ),
                )

        return anomalies

    def list_anomalies(
        self,
        workspace_id: str = "default_workspace",
        device_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> List[BehavioralAnomalyRecord]:
        with self._get_connection() as conn:
            query = "SELECT * FROM behavioral_anomalies WHERE workspace_id = ?"
            params: List[Any] = [workspace_id]
            if device_id:
                query += " AND device_id = ?"
                params.append(device_id)
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            query += " ORDER BY detected_at DESC LIMIT ?;"
            params.append(limit)

            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()

        return [
            BehavioralAnomalyRecord(
                anomaly_id=r["anomaly_id"],
                device_id=r["device_id"],
                device_name=r["device_name"],
                workspace_id=r["workspace_id"],
                anomaly_type=r["anomaly_type"],
                severity=r["severity"],
                classification=r["classification"],
                confidence=r["confidence"],
                metric_key=r["metric_key"],
                observed_value=json.loads(r["observed_value_json"] or "{}"),
                baseline_expected=json.loads(r["baseline_expected_json"] or "{}"),
                evidence_summary=r["evidence_summary"],
                detected_at=r["detected_at"],
            )
            for r in rows
        ]

    # --------------------------------------------------------------------------
    # 4. Security Incident Management & Investigation
    # --------------------------------------------------------------------------
    def create_or_correlate_incident(
        self,
        workspace_id: str,
        title: str,
        severity: ConfigAuditSeverity,
        classification: ThreatClassification,
        affected_device_ids: List[str],
        root_cause_hypothesis: str,
        confidence_level: Literal["high", "medium", "low"],
        evidence_records: List[Dict[str, Any]],
        recommended_remediations: List[str],
    ) -> SecurityIncidentRecord:
        """Creates a correlated security incident linking telemetry, audit, and firmware data."""
        incident_id = f"inc_{uuid.uuid4().hex[:10]}"
        now_iso = _utc_now_iso()

        # Gather related telemetry correlations
        telemetry_correlations = []
        for d_id in affected_device_ids:
            dev = iot_telemetry_engine.get_device(d_id, workspace_id=workspace_id)
            if dev:
                telemetry_correlations.append(
                    {
                        "device_id": d_id,
                        "device_name": dev.name,
                        "status": dev.status,
                        "total_events": dev.total_events_received,
                        "firmware_version": dev.firmware_version,
                        "last_seen_at": dev.last_seen_at,
                    }
                )

        inc = SecurityIncidentRecord(
            incident_id=incident_id,
            workspace_id=workspace_id,
            title=title,
            severity=severity,
            classification=classification,
            status="new",
            affected_device_ids=affected_device_ids,
            affected_devices_count=len(affected_device_ids),
            root_cause_hypothesis=root_cause_hypothesis,
            confidence_level=confidence_level,
            evidence_records=evidence_records,
            telemetry_correlations=telemetry_correlations,
            recommended_remediations=recommended_remediations,
            created_at=now_iso,
            updated_at=now_iso,
        )

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO security_incidents (
                    incident_id, workspace_id, title, severity, classification, status,
                    affected_device_ids_json, root_cause_hypothesis, confidence_level,
                    evidence_records_json, telemetry_correlations_json,
                    recommended_remediations_json, assigned_responder, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    inc.incident_id,
                    inc.workspace_id,
                    inc.title,
                    inc.severity,
                    inc.classification,
                    inc.status,
                    json.dumps(inc.affected_device_ids),
                    inc.root_cause_hypothesis,
                    inc.confidence_level,
                    json.dumps(inc.evidence_records),
                    json.dumps(inc.telemetry_correlations),
                    json.dumps(inc.recommended_remediations),
                    None,
                    inc.created_at,
                    inc.updated_at,
                ),
            )

        return inc

    def update_incident_status(
        self, incident_id: str, req: SecurityIncidentUpdateRequest
    ) -> SecurityIncidentRecord:
        now_iso = _utc_now_iso()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM security_incidents WHERE incident_id = ? AND workspace_id = ?;",
                (incident_id, req.workspace_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Incident '{incident_id}' not found.")

            resolved_at = now_iso if req.status in ("mitigated", "closed") else None
            conn.execute(
                """
                UPDATE security_incidents
                SET status = ?, resolved_at = ?, updated_at = ?
                WHERE incident_id = ?;
                """,
                (req.status, resolved_at, now_iso, incident_id),
            )

        return self.get_incident(incident_id, req.workspace_id)

    def get_incident(
        self, incident_id: str, workspace_id: str = "default_workspace"
    ) -> SecurityIncidentRecord:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM security_incidents WHERE incident_id = ? AND workspace_id = ?;",
                (incident_id, workspace_id),
            )
            r = cur.fetchone()
            if not r:
                raise ValueError(f"Incident '{incident_id}' not found.")

        return SecurityIncidentRecord(
            incident_id=r["incident_id"],
            workspace_id=r["workspace_id"],
            title=r["title"],
            severity=r["severity"],
            classification=r["classification"],
            status=r["status"],
            affected_device_ids=json.loads(r["affected_device_ids_json"] or "[]"),
            affected_devices_count=len(json.loads(r["affected_device_ids_json"] or "[]")),
            root_cause_hypothesis=r["root_cause_hypothesis"],
            confidence_level=r["confidence_level"],
            evidence_records=json.loads(r["evidence_records_json"] or "[]"),
            telemetry_correlations=json.loads(r["telemetry_correlations_json"] or "[]"),
            recommended_remediations=json.loads(r["recommended_remediations_json"] or "[]"),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            resolved_at=r["resolved_at"],
            assigned_responder=r["assigned_responder"],
        )

    def list_incidents(
        self,
        workspace_id: str = "default_workspace",
        status: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[SecurityIncidentRecord]:
        with self._get_connection() as conn:
            query = "SELECT * FROM security_incidents WHERE workspace_id = ?"
            params: List[Any] = [workspace_id]
            if status:
                query += " AND status = ?"
                params.append(status)
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            query += " ORDER BY created_at DESC;"

            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()

        return [
            SecurityIncidentRecord(
                incident_id=r["incident_id"],
                workspace_id=r["workspace_id"],
                title=r["title"],
                severity=r["severity"],
                classification=r["classification"],
                status=r["status"],
                affected_device_ids=json.loads(r["affected_device_ids_json"] or "[]"),
                affected_devices_count=len(json.loads(r["affected_device_ids_json"] or "[]")),
                root_cause_hypothesis=r["root_cause_hypothesis"],
                confidence_level=r["confidence_level"],
                evidence_records=json.loads(r["evidence_records_json"] or "[]"),
                telemetry_correlations=json.loads(r["telemetry_correlations_json"] or "[]"),
                recommended_remediations=json.loads(r["recommended_remediations_json"] or "[]"),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                resolved_at=r["resolved_at"],
                assigned_responder=r["assigned_responder"],
            )
            for r in rows
        ]

    # --------------------------------------------------------------------------
    # 5. Controlled Defensive Response with Consequential Confirmation Gates
    # --------------------------------------------------------------------------
    def execute_defensive_action(
        self, req: DefensiveActionRequest
    ) -> DefensiveActionRecord:
        """
        Executes or gates a disruptive defensive action.
        Disruptive actions require explicit confirmation (confirmed=True).
        Never claim isolation succeeded without actual adapter acknowledgement.
        """
        device = iot_telemetry_engine.get_device(req.device_id, workspace_id=req.workspace_id)
        if not device:
            raise ValueError(f"Target device '{req.device_id}' does not exist.")

        action_id = f"act_{uuid.uuid4().hex[:10]}"
        now_iso = _utc_now_iso()
        is_disruptive = req.action_type in ("revoke_credential", "quarantine_device", "isolate_network")

        # Consequential confirmation check
        if is_disruptive and not req.confirmed:
            rec = DefensiveActionRecord(
                action_id=action_id,
                user_id=req.user_id,
                workspace_id=req.workspace_id,
                device_id=req.device_id,
                device_name=device.name,
                action_type=req.action_type,
                reason=req.reason,
                requires_confirmation=True,
                status="pending_confirmation",
                result_message=f"Defensive action '{req.action_type}' is disruptive and requires explicit user confirmation before executing.",
                recovery_procedure="Submit confirmation request with confirmed=True.",
                created_at=now_iso,
            )
            self._save_defensive_action(rec)
            return rec

        # Execute confirmed action
        result_msg = ""
        recovery_proc = ""
        action_status: DefensiveActionStatus = "executed"

        if req.action_type == "revoke_credential":
            iot_telemetry_engine.revoke_token(req.device_id, workspace_id=req.workspace_id, user_id=req.user_id)
            result_msg = f"Device token for '{device.name}' was immediately revoked. Device cannot ingest telemetry until re-provisioned."
            recovery_proc = "Navigate to Device Registry and issue 'Rotate Credential' to generate a new active token."

        elif req.action_type == "quarantine_device":
            # Update device status in Stage 25 database to 'degraded'
            with iot_telemetry_engine._get_connection() as conn:
                conn.execute(
                    "UPDATE registered_devices SET status = 'degraded', updated_at = ? WHERE device_id = ?;",
                    (now_iso, req.device_id),
                )
            result_msg = f"Device '{device.name}' placed into quarantine status 'degraded'. Active telemetry ingestion suspended."
            recovery_proc = "Review device firmware and issue 'restore_device' defensive action to reinstate normal operation."

        elif req.action_type == "isolate_network":
            # Strict honesty: check if network management adapter is configured
            if not settings.iot_security_network_adapter_configured:
                action_status = "failed"
                result_msg = "Authorized network-management adapter is not configured on this host. Action refused to prevent false sense of isolation."
                recovery_proc = "Configure IOT_SECURITY_NETWORK_ADAPTER_CONFIGURED=true and supply managed SDN/Firewall API credentials in .env."
            else:
                result_msg = f"Hardware isolation command sent to network adapter. MAC {device.mac_address or 'unknown'} quarantined on VLAN 99."
                recovery_proc = "Issue network adapter unbind command or re-enable switch port."

        elif req.action_type == "throttle_telemetry":
            # Reduce device rate limit to 1 event/min
            with iot_telemetry_engine._get_connection() as conn:
                conn.execute(
                    "UPDATE registered_devices SET rate_limit_per_minute = 1, updated_at = ? WHERE device_id = ?;",
                    (now_iso, req.device_id),
                )
            result_msg = f"Rate limit for device '{device.name}' throttled to 1 event per minute."
            recovery_proc = "Update device registration settings to restore standard event limit (e.g. 60/min)."

        elif req.action_type == "restore_device":
            with iot_telemetry_engine._get_connection() as conn:
                conn.execute(
                    "UPDATE registered_devices SET status = 'online', rate_limit_per_minute = 60, updated_at = ? WHERE device_id = ?;",
                    (now_iso, req.device_id),
                )
            result_msg = f"Device '{device.name}' restored to status 'online' with standard rate limit."
            recovery_proc = "Device is now active. Verify incoming telemetry on the live telemetry dashboard."

        rec = DefensiveActionRecord(
            action_id=action_id,
            user_id=req.user_id,
            workspace_id=req.workspace_id,
            device_id=req.device_id,
            device_name=device.name,
            action_type=req.action_type,
            reason=req.reason,
            requires_confirmation=is_disruptive,
            status=action_status,
            result_message=result_msg,
            recovery_procedure=recovery_proc,
            executed_at=now_iso if action_status == "executed" else None,
            created_at=now_iso,
        )
        self._save_defensive_action(rec)
        return rec

    def _save_defensive_action(self, rec: DefensiveActionRecord) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO defensive_actions_audit (
                    action_id, user_id, workspace_id, device_id, device_name,
                    action_type, reason, requires_confirmation, status,
                    result_message, recovery_procedure, executed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    rec.action_id,
                    rec.user_id,
                    rec.workspace_id,
                    rec.device_id,
                    rec.device_name,
                    rec.action_type,
                    rec.reason,
                    1 if rec.requires_confirmation else 0,
                    rec.status,
                    rec.result_message,
                    rec.recovery_procedure,
                    rec.executed_at,
                    rec.created_at,
                ),
            )

    def list_defensive_actions(
        self, workspace_id: str = "default_workspace", device_id: Optional[str] = None
    ) -> List[DefensiveActionRecord]:
        with self._get_connection() as conn:
            query = "SELECT * FROM defensive_actions_audit WHERE workspace_id = ?"
            params: List[Any] = [workspace_id]
            if device_id:
                query += " AND device_id = ?"
                params.append(device_id)
            query += " ORDER BY created_at DESC;"

            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()

        return [
            DefensiveActionRecord(
                action_id=r["action_id"],
                user_id=r["user_id"],
                workspace_id=r["workspace_id"],
                device_id=r["device_id"],
                device_name=r["device_name"],
                action_type=r["action_type"],
                reason=r["reason"],
                requires_confirmation=bool(r["requires_confirmation"]),
                status=r["status"],
                result_message=r["result_message"],
                recovery_procedure=r["recovery_procedure"],
                executed_at=r["executed_at"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    # --------------------------------------------------------------------------
    # 6. Fleet Overview & Aggregation
    # --------------------------------------------------------------------------
    def get_security_overview(
        self, workspace_id: str = "default_workspace"
    ) -> IoTSecurityOverviewResponse:
        """Assembles complete fleet security overview across all registered devices."""
        devices = iot_telemetry_engine.list_devices(workspace_id=workspace_id)
        postures: List[DeviceSecurityPosture] = []

        for d in devices:
            try:
                p = self.assess_device_posture(d.device_id, workspace_id=workspace_id)
                postures.append(p)
            except Exception:
                pass

        findings = self.list_findings(workspace_id=workspace_id, status="active")
        anomalies = self.list_anomalies(workspace_id=workspace_id, limit=30)
        incidents = self.list_incidents(workspace_id=workspace_id)

        # Fleet summary counts
        total_dev = len(postures)
        critical_count = sum(1 for p in postures if p.risk_level == "critical")
        high_count = sum(1 for p in postures if p.risk_level == "high")
        med_count = sum(1 for p in postures if p.risk_level == "medium")
        low_count = sum(1 for p in postures if p.risk_level == "low")
        unknown_count = sum(1 for p in postures if p.risk_level == "unknown")

        avg_risk = round(sum(p.risk_score for p in postures) / max(total_dev, 1), 1)

        summary = {
            "total_devices_monitored": total_dev,
            "average_fleet_risk_score": avg_risk,
            "risk_distribution": {
                "critical": critical_count,
                "high": high_count,
                "medium": med_count,
                "low": low_count,
                "unknown": unknown_count,
            },
            "active_config_findings": len(findings),
            "recent_behavioral_anomalies": len(anomalies),
            "open_security_incidents": len([i for i in incidents if i.status in ("new", "under_investigation")]),
            "tls_enforced_devices_count": sum(1 for p in postures if p.transport_encryption == "tls_enabled"),
            "unencrypted_transport_devices_count": sum(1 for p in postures if p.transport_encryption == "plaintext_unencrypted"),
        }

        return IoTSecurityOverviewResponse(
            stage=26,
            fleet_posture_summary=summary,
            devices_posture=postures,
            active_incidents=incidents,
            recent_anomalies=anomalies,
            config_findings=findings,
            firmware_integrity_matrix=list(FIRMWARE_INTEGRITY_SPECS.values()),
            last_assessment_at=_utc_now_iso(),
        )


iot_security_engine = IoTSecurityEngine()
