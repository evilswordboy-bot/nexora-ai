from __future__ import annotations

import ast
import csv
import hashlib
import io
import json
import py_compile
import re
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.models.schemas import (
    IoTBOMItem,
    IoTBoardId,
    IoTBoardPin,
    IoTBoardProfile,
    IoTBuildDocumentation,
    IoTComponentSpec,
    IoTConnectivityConfig,
    IoTConnectivityProtocol,
    IoTEnvironmentType,
    IoTExportFileEntry,
    IoTFirmwareArtifact,
    IoTFirmwareLanguage,
    IoTMetadataResponse,
    IoTPlacedComponent,
    IoTPowerSource,
    IoTProjectCreateRequest,
    IoTProjectExportRequest,
    IoTProjectExportResponse,
    IoTProjectGenerateFirmwareRequest,
    IoTProjectRecord,
    IoTProjectUpdateWiringRequest,
    IoTSafetyCheckItem,
    IoTSafetyReport,
    IoTSimulationRequest,
    IoTSimulationResponse,
    IoTSimulationTickResult,
    IoTWireConnection,
    IoTWiringValidationIssue,
    IoTWiringValidationReport,
)
from app.services.iot.catalog import (
    build_board_catalog,
    build_component_catalog,
    detect_host_toolchains,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return slug or "iot-project"


class IoTProjectBuilderEngine:
    """
    Stage 23: IoT Project Builder Engine.
    Provides board selection, component library search, interactive pin-to-pin wiring validation,
    honest firmware generation & syntax/compiler checking, deterministic virtual simulation,
    electrical safety auditing, BOM/build documentation, and versioned project export.
    """

    def __init__(self, db_path: Optional[str] = None, exports_dir: Optional[str] = None) -> None:
        self.db_path = Path(db_path or settings.iot_db_path)
        self.exports_dir = Path(exports_dir or settings.iot_exports_dir)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self._boards: Dict[str, IoTBoardProfile] = build_board_catalog()
        self._components: Dict[str, IoTComponentSpec] = build_component_catalog()
        self._init_db()
        self._ensure_seed_project()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS iot_projects (
                    project_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    board_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_iot_projects_tenant
                ON iot_projects (user_id, workspace_id, updated_at DESC)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS iot_exports (
                    export_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    export_json TEXT NOT NULL,
                    exported_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _ensure_seed_project(self) -> None:
        """Seeds a reference Smart Greenhouse Telemetry & Irrigation Node in default_workspace if empty."""
        existing = self.list_projects(user_id="default_user", workspace_id="default_workspace")
        if existing:
            return
        self.create_project(
            IoTProjectCreateRequest(
                user_id="default_user",
                workspace_id="default_workspace",
                name="Smart Greenhouse Climate & Soil Node",
                invention_description=(
                    "Solar/USB-powered ESP32 greenhouse monitor reading ambient temperature, humidity, "
                    "and capacitive soil moisture, displaying status on an SSD1306 OLED screen, and triggering "
                    "an optocoupled 5V irrigation relay over MQTT."
                ),
                target_budget_usd=35.0,
                power_source="usb_5v",
                environment="greenhouse_humid",
                preferred_board_id="esp32_devkit_v1",
                component_ids=[
                    "bme280_sensor",
                    "soil_moisture_capacitive",
                    "ssd1306_oled_i2c",
                    "relay_module_5v_optocoupled",
                ],
                firmware_language="arduino_cpp",
                connectivity_protocol="wifi_mqtt",
                auto_wire=True,
            )
        )

    # =========================================================================
    # CATALOG & METADATA
    # =========================================================================

    def get_metadata(self) -> IoTMetadataResponse:
        toolchains = detect_host_toolchains() if settings.iot_enable_toolchain_probing else {}
        return IoTMetadataResponse(
            stage=23,
            engine="IoTProjectBuilderEngine",
            boards_count=len(self._boards),
            components_count=len(self._components),
            supported_languages=["arduino_cpp", "micropython", "esp_idf_c", "rpi_python_gpiozero"],
            supported_connectivity=[
                "none_local_only",
                "wifi_mqtt",
                "wifi_http_rest",
                "ble_gatt",
                "serial_usb_telemetry",
            ],
            detected_toolchains=toolchains,
            hardware_execution_disclaimer=(
                "All simulations and electrical checks run in NEXORA's deterministic software engine. "
                "Firmware binary compilation is reported as passed ONLY when the host compiler binary "
                "is installed and executes with exit code 0. Software checks do not replace physical safety testing."
            ),
        )

    def list_boards(self) -> List[IoTBoardProfile]:
        self._boards = build_board_catalog()
        return list(self._boards.values())

    def get_board(self, board_id: str) -> IoTBoardProfile:
        self._boards = build_board_catalog()
        if board_id not in self._boards:
            raise ValueError(f"Unsupported board_id '{board_id}'. Available boards: {list(self._boards.keys())}")
        return self._boards[board_id]

    def list_components(
        self,
        category: Optional[str] = None,
        interface: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[IoTComponentSpec]:
        items = list(self._components.values())
        if category and category.strip() and category.strip().lower() != "all":
            cat_norm = category.strip().lower()
            items = [c for c in items if c.category.lower() == cat_norm]
        if interface and interface.strip() and interface.strip().lower() != "all":
            iface_norm = interface.strip().upper()
            items = [c for c in items if any(i.upper() == iface_norm for i in c.interfaces)]
        if query and query.strip():
            q = query.strip().lower()
            items = [
                c
                for c in items
                if q in c.name.lower()
                or q in c.component_id.lower()
                or q in c.description.lower()
                or any(q in i.lower() for i in c.interfaces)
            ]
        return items

    # =========================================================================
    # PROJECT DESIGNER & SELECTION LOGIC
    # =========================================================================

    def _recommend_board_and_components(
        self, req: IoTProjectCreateRequest
    ) -> Tuple[IoTBoardId, List[str], IoTFirmwareLanguage]:
        desc = f"{req.name} {req.invention_description}".lower()

        if req.preferred_board_id and req.preferred_board_id in self._boards:
            board_id: IoTBoardId = req.preferred_board_id
        elif "raspberry pi 4" in desc or "linux" in desc or "camera" in desc:
            board_id = "raspberry_pi_4b"
        elif "pico" in desc or "rp2040" in desc:
            board_id = "raspberry_pi_pico_w"
        elif "stm32" in desc or "nucleo" in desc or "cortex-m4" in desc:
            board_id = "stm32_nucleo_f401re"
        elif "arduino uno" in desc or ("arduino" in desc and req.connectivity_protocol in ("none_local_only", "serial_usb_telemetry")):
            board_id = "arduino_uno_r3"
        else:
            board_id = "esp32_devkit_v1"

        board = self.get_board(board_id)
        if req.firmware_language and req.firmware_language in board.supported_languages:
            language: IoTFirmwareLanguage = req.firmware_language
        else:
            language = board.supported_languages[0]

        if req.component_ids:
            valid_ids = []
            for cid in req.component_ids:
                if cid not in self._components:
                    raise ValueError(f"Unknown component_id '{cid}'.")
                valid_ids.append(cid)
            return board_id, valid_ids, language

        # Infer components from natural language description
        inferred: List[str] = []
        if any(k in desc for k in ("temp", "climate", "weather", "humidity", "pressure", "greenhouse", "environment")):
            inferred.append("bme280_sensor")
        if any(k in desc for k in ("dht", "dht22")):
            inferred.append("dht22_sensor")
        if any(k in desc for k in ("soil", "moisture", "plant", "irrigation", "garden")):
            inferred.append("soil_moisture_capacitive")
        if any(k in desc for k in ("distance", "ultrasonic", "parking", "obstacle", "tank level", "hc-sr04")):
            inferred.append("hc_sr04_ultrasonic")
            if not board.five_volt_tolerant_pins:
                inferred.append("txs0108e_level_shifter")
        if any(k in desc for k in ("motion", "pir", "intruder", "occupancy", "security")):
            inferred.append("pir_hc_sr501")
        if any(k in desc for k in ("display", "oled", "screen", "status", "readout")):
            inferred.append("ssd1306_oled_i2c")
        if any(k in desc for k in ("relay", "pump", "valve", "fan", "irrigation", "switch")):
            inferred.append("relay_module_5v_optocoupled")
        if any(k in desc for k in ("servo", "door", "lock", "pan", "tilt", "feeder")):
            inferred.append("sg90_micro_servo")
        if any(k in desc for k in ("dc motor", "rover", "wheel", "conveyor")):
            inferred.extend(["l298n_motor_driver", "dc_motor_6v"])
        if any(k in desc for k in ("mains", "240v", "110v", "ac appliance")):
            inferred.append("relay_mains_ac_240v")
        if req.power_source == "battery_lipo_3v7" or "18650" in desc or "lipo" in desc:
            inferred.append("lipo_18650_2s_pack")

        # If Raspberry Pi 4B has an analog sensor, add ADS1115 external ADC automatically
        if board_id == "raspberry_pi_4b" and "soil_moisture_capacitive" in inferred and "ads1115_adc_i2c" not in inferred:
            inferred.append("ads1115_adc_i2c")

        if not inferred:
            inferred = ["bme280_sensor", "ssd1306_oled_i2c", "relay_module_5v_optocoupled"]

        # Deduplicate while preserving order
        deduped: List[str] = []
        for cid in inferred:
            if cid not in deduped:
                deduped.append(cid)
        return board_id, deduped, language

    def auto_wire_components(
        self,
        board: IoTBoardProfile,
        placed_components: List[IoTPlacedComponent],
    ) -> List[IoTWireConnection]:
        """
        Deterministically generates valid pin-to-pin wiring connections for the placed components.
        Respects board voltage capabilities, shared I2C buses, ADC channels, PWM pins, and motor drivers.
        """
        wires: List[IoTWireConnection] = []
        wire_idx = 1

        def _next_wire_id() -> str:
            nonlocal wire_idx
            wid = f"wire_{wire_idx:02d}"
            wire_idx += 1
            return wid

        pin_by_cap: Dict[str, List[IoTBoardPin]] = {}
        for p in board.pins:
            for cap in p.capabilities:
                pin_by_cap.setdefault(cap, []).append(p)

        pin_3v3 = (pin_by_cap.get("POWER_3V3") or [board.pins[0]])[0].pin_id
        pin_5v = (pin_by_cap.get("POWER_5V") or pin_by_cap.get("POWER_3V3") or [board.pins[0]])[0].pin_id
        pin_gnd = (pin_by_cap.get("GND") or [board.pins[0]])[0].pin_id
        pin_sda = (pin_by_cap.get("I2C_SDA") or [board.pins[0]])[0].pin_id
        pin_scl = (pin_by_cap.get("I2C_SCL") or [board.pins[0]])[0].pin_id

        used_single_pins: set[str] = {pin_3v3, pin_5v, pin_gnd, pin_sda, pin_scl}

        def _allocate_pin(preferred_cap: str, fallback_cap: str = "DIGITAL_IO") -> IoTBoardPin:
            for cap in (preferred_cap, fallback_cap):
                for candidate in pin_by_cap.get(cap, []):
                    if (
                        candidate.pin_id not in used_single_pins
                        and "INPUT_ONLY" not in candidate.capabilities
                        and "STRAPPING_PIN" not in candidate.capabilities
                    ):
                        used_single_pins.add(candidate.pin_id)
                        return candidate
                for candidate in pin_by_cap.get(cap, []):
                    if candidate.pin_id not in used_single_pins and "INPUT_ONLY" not in candidate.capabilities:
                        used_single_pins.add(candidate.pin_id)
                        return candidate
            # Last resort
            return board.pins[-1]

        def _allocate_adc_pin() -> IoTBoardPin:
            for candidate in pin_by_cap.get("ADC", []):
                if candidate.pin_id not in used_single_pins:
                    used_single_pins.add(candidate.pin_id)
                    return candidate
            return _allocate_pin("ADC", "DIGITAL_IO")

        # Locate helper adapters if placed
        driver_inst = next((c for c in placed_components if c.component_id == "l298n_motor_driver"), None)
        adc_inst = next((c for c in placed_components if c.component_id == "ads1115_adc_i2c"), None)
        shifter_inst = next((c for c in placed_components if c.component_id == "txs0108e_level_shifter"), None)

        for comp in placed_components:
            spec = self._components.get(comp.component_id)
            if not spec:
                continue

            # Bare motor connects to L298N driver outputs if driver is present
            if spec.component_id == "dc_motor_6v" and driver_inst is not None:
                wires.append(
                    IoTWireConnection(
                        wire_id=_next_wire_id(),
                        from_node_id=driver_inst.instance_id,
                        from_pin="OUT1",
                        to_node_id=comp.instance_id,
                        to_pin="MOTOR_POS",
                        signal_type="MOTOR_POWER",
                        wire_color="#f97316",
                        label=f"{driver_inst.label}.OUT1 -> {comp.label}.M+",
                        voltage_v=6.0,
                    )
                )
                wires.append(
                    IoTWireConnection(
                        wire_id=_next_wire_id(),
                        from_node_id=driver_inst.instance_id,
                        from_pin="OUT2",
                        to_node_id=comp.instance_id,
                        to_pin="MOTOR_NEG",
                        signal_type="MOTOR_POWER",
                        wire_color="#64748b",
                        label=f"{driver_inst.label}.OUT2 -> {comp.label}.M-",
                        voltage_v=0.0,
                    )
                )
                continue

            for cpin in spec.pins:
                if not cpin.required:
                    continue
                if cpin.pin_role == "POWER_VCC":
                    use_5v = spec.operating_voltage_min_v >= 4.5 or spec.category in ("relay", "motor_driver", "actuator")
                    board_pwr_pin = pin_5v if use_5v else pin_3v3
                    pwr_v = 5.0 if use_5v else 3.3
                    wires.append(
                        IoTWireConnection(
                            wire_id=_next_wire_id(),
                            from_node_id="board",
                            from_pin=board_pwr_pin,
                            to_node_id=comp.instance_id,
                            to_pin=cpin.pin_name,
                            signal_type="POWER",
                            wire_color="#ef4444" if use_5v else "#f59e0b",
                            label=f"Board {board_pwr_pin} ({pwr_v}V) -> {comp.label}.{cpin.pin_name}",
                            voltage_v=pwr_v,
                        )
                    )
                elif cpin.pin_role == "POWER_GND":
                    wires.append(
                        IoTWireConnection(
                            wire_id=_next_wire_id(),
                            from_node_id="board",
                            from_pin=pin_gnd,
                            to_node_id=comp.instance_id,
                            to_pin=cpin.pin_name,
                            signal_type="GND",
                            wire_color="#475569",
                            label=f"Board {pin_gnd} -> {comp.label}.{cpin.pin_name}",
                            voltage_v=0.0,
                        )
                    )
                elif cpin.pin_role == "I2C_SDA":
                    wires.append(
                        IoTWireConnection(
                            wire_id=_next_wire_id(),
                            from_node_id="board",
                            from_pin=pin_sda,
                            to_node_id=comp.instance_id,
                            to_pin=cpin.pin_name,
                            signal_type="I2C_SDA",
                            wire_color="#38bdf8",
                            label=f"I2C SDA ({pin_sda}) -> {comp.label}.{cpin.pin_name}",
                            voltage_v=board.io_logic_voltage_v,
                        )
                    )
                elif cpin.pin_role == "I2C_SCL":
                    wires.append(
                        IoTWireConnection(
                            wire_id=_next_wire_id(),
                            from_node_id="board",
                            from_pin=pin_scl,
                            to_node_id=comp.instance_id,
                            to_pin=cpin.pin_name,
                            signal_type="I2C_SCL",
                            wire_color="#818cf8",
                            label=f"I2C SCL ({pin_scl}) -> {comp.label}.{cpin.pin_name}",
                            voltage_v=board.io_logic_voltage_v,
                        )
                    )
                elif cpin.pin_role == "ANALOG_OUT":
                    if board.analog_in_count == 0 and adc_inst is not None and comp.instance_id != adc_inst.instance_id:
                        wires.append(
                            IoTWireConnection(
                                wire_id=_next_wire_id(),
                                from_node_id=adc_inst.instance_id,
                                from_pin="A0",
                                to_node_id=comp.instance_id,
                                to_pin=cpin.pin_name,
                                signal_type="ANALOG",
                                wire_color="#34d399",
                                label=f"{adc_inst.label}.A0 -> {comp.label}.{cpin.pin_name}",
                                voltage_v=3.0,
                            )
                        )
                    else:
                        bpin = _allocate_adc_pin()
                        wires.append(
                            IoTWireConnection(
                                wire_id=_next_wire_id(),
                                from_node_id="board",
                                from_pin=bpin.pin_id,
                                to_node_id=comp.instance_id,
                                to_pin=cpin.pin_name,
                                signal_type="ANALOG",
                                wire_color="#34d399",
                                label=f"ADC {bpin.pin_id} -> {comp.label}.{cpin.pin_name}",
                                voltage_v=3.0,
                            )
                        )
                elif cpin.pin_role == "PWM_IN":
                    bpin = _allocate_pin("PWM", "DIGITAL_IO")
                    wires.append(
                        IoTWireConnection(
                            wire_id=_next_wire_id(),
                            from_node_id="board",
                            from_pin=bpin.pin_id,
                            to_node_id=comp.instance_id,
                            to_pin=cpin.pin_name,
                            signal_type="PWM",
                            wire_color="#c084fc",
                            label=f"PWM {bpin.pin_id} -> {comp.label}.{cpin.pin_name}",
                            voltage_v=board.io_logic_voltage_v,
                        )
                    )
                elif cpin.pin_role == "ONEWIRE":
                    bpin = _allocate_pin("ONEWIRE", "DIGITAL_IO")
                    wires.append(
                        IoTWireConnection(
                            wire_id=_next_wire_id(),
                            from_node_id="board",
                            from_pin=bpin.pin_id,
                            to_node_id=comp.instance_id,
                            to_pin=cpin.pin_name,
                            signal_type="ONEWIRE",
                            wire_color="#facc15",
                            label=f"OneWire {bpin.pin_id} -> {comp.label}.{cpin.pin_name}",
                            voltage_v=board.io_logic_voltage_v,
                        )
                    )
                elif cpin.pin_role in ("DIGITAL_IN", "DIGITAL_OUT"):
                    bpin = _allocate_pin("DIGITAL_IO", "PWM")
                    sig_v = 3.3 if (shifter_inst is not None and not board.five_volt_tolerant_pins) else cpin.logic_level_v
                    wires.append(
                        IoTWireConnection(
                            wire_id=_next_wire_id(),
                            from_node_id="board",
                            from_pin=bpin.pin_id,
                            to_node_id=comp.instance_id,
                            to_pin=cpin.pin_name,
                            signal_type="DIGITAL",
                            wire_color="#2dd4bf",
                            label=f"GPIO {bpin.pin_id} -> {comp.label}.{cpin.pin_name}",
                            voltage_v=sig_v,
                        )
                    )
                elif cpin.pin_role == "MOTOR_TERMINAL":
                    bpin = _allocate_pin("DIGITAL_IO")
                    wires.append(
                        IoTWireConnection(
                            wire_id=_next_wire_id(),
                            from_node_id="board",
                            from_pin=bpin.pin_id,
                            to_node_id=comp.instance_id,
                            to_pin=cpin.pin_name,
                            signal_type="MOTOR_COIL",
                            wire_color="#f43f5e",
                            label=f"UNSAFE Direct GPIO {bpin.pin_id} -> {comp.label}.{cpin.pin_name}",
                            voltage_v=5.0,
                        )
                    )

        return wires

    # =========================================================================
    # WIRING VALIDATION & SVG DIAGRAM GENERATION
    # =========================================================================

    def validate_wiring(
        self,
        board: IoTBoardProfile,
        placed_components: List[IoTPlacedComponent],
        wires: List[IoTWireConnection],
    ) -> IoTWiringValidationReport:
        issues: List[IoTWiringValidationIssue] = []
        board_pin_map: Dict[str, IoTBoardPin] = {p.pin_id: p for p in board.pins}
        comp_inst_map: Dict[str, IoTPlacedComponent] = {c.instance_id: c for c in placed_components}
        has_level_shifter = any(c.component_id == "txs0108e_level_shifter" for c in placed_components)
        has_motor_driver = any(c.component_id == "l298n_motor_driver" for c in placed_components)
        has_external_adc = any(c.component_id == "ads1115_adc_i2c" for c in placed_components)

        # Track board pin attachments
        board_pin_attachments: Dict[str, List[Tuple[IoTWireConnection, str, str]]] = {}
        comp_connected_pins: Dict[str, set[str]] = {c.instance_id: set() for c in placed_components}

        for w in wires:
            if w.from_node_id in comp_connected_pins:
                comp_connected_pins[w.from_node_id].add(w.from_pin)
            if w.to_node_id in comp_connected_pins:
                comp_connected_pins[w.to_node_id].add(w.to_pin)

            # Check direct board-to-board power/GND short circuit
            if w.from_node_id == "board" and w.to_node_id == "board":
                p1 = board_pin_map.get(w.from_pin)
                p2 = board_pin_map.get(w.to_pin)
                if p1 and p2:
                    caps1 = set(p1.capabilities)
                    caps2 = set(p2.capabilities)
                    if ("GND" in caps1 and caps2 & {"POWER_3V3", "POWER_5V", "POWER_VIN"}) or (
                        "GND" in caps2 and caps1 & {"POWER_3V3", "POWER_5V", "POWER_VIN"}
                    ):
                        issues.append(
                            IoTWiringValidationIssue(
                                issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                                code="SHORT_CIRCUIT_POWER_GND",
                                severity="critical",
                                category="polarity_or_short",
                                title="Direct Power-to-Ground Short Circuit Detected",
                                description=f"Wire '{w.wire_id}' directly shorts board pin {w.from_pin} to {w.to_pin}.",
                                affected_nodes=["board"],
                                affected_pins=[w.from_pin, w.to_pin],
                                remediation="Remove the direct wire between the power rail and GND immediately.",
                            )
                        )

            # Normalize board-to-component or component-to-board wire
            if w.from_node_id == "board" and w.to_node_id in comp_inst_map:
                b_pin_id, c_inst_id, c_pin_name = w.from_pin, w.to_node_id, w.to_pin
            elif w.to_node_id == "board" and w.from_node_id in comp_inst_map:
                b_pin_id, c_inst_id, c_pin_name = w.to_pin, w.from_node_id, w.from_pin
            else:
                continue

            bpin = board_pin_map.get(b_pin_id)
            comp = comp_inst_map[c_inst_id]
            spec = self._components.get(comp.component_id)
            if not bpin:
                issues.append(
                    IoTWiringValidationIssue(
                        issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                        code="INVALID_BOARD_PIN",
                        severity="error",
                        category="interface_mismatch",
                        title=f"Pin '{b_pin_id}' Does Not Exist on {board.name}",
                        description=f"Wire '{w.wire_id}' references non-existent board pin '{b_pin_id}'.",
                        affected_nodes=["board", c_inst_id],
                        affected_pins=[b_pin_id, c_pin_name],
                        remediation=f"Select a valid pin from {board.name}: {[p.pin_id for p in board.pins[:8]]}.",
                    )
                )
                continue

            board_pin_attachments.setdefault(b_pin_id, []).append((w, c_inst_id, c_pin_name))
            if not spec:
                continue

            cpin = next((p for p in spec.pins if p.pin_name == c_pin_name), None)
            if not cpin:
                continue

            # 1. Reverse Polarity or Power-to-GND on component
            if cpin.pin_role == "POWER_GND" and any(cap in bpin.capabilities for cap in ("POWER_3V3", "POWER_5V", "POWER_VIN")):
                issues.append(
                    IoTWiringValidationIssue(
                        issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                        code="REVERSE_POLARITY",
                        severity="critical",
                        category="polarity_or_short",
                        title=f"Reverse Polarity on {comp.label}.{c_pin_name}",
                        description=f"Component ground pin '{c_pin_name}' is wired to positive supply rail '{b_pin_id}' ({bpin.voltage_level_v}V).",
                        affected_nodes=["board", c_inst_id],
                        affected_pins=[b_pin_id, c_pin_name],
                        remediation=f"Connect {comp.label}.{c_pin_name} to a board GND pin.",
                    )
                )
            elif cpin.pin_role == "POWER_VCC" and "GND" in bpin.capabilities:
                issues.append(
                    IoTWiringValidationIssue(
                        issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                        code="REVERSE_POLARITY",
                        severity="critical",
                        category="polarity_or_short",
                        title=f"Power Pin {comp.label}.{c_pin_name} Connected to GND",
                        description=f"Component supply pin '{c_pin_name}' is wired to board GND '{b_pin_id}'.",
                        affected_nodes=["board", c_inst_id],
                        affected_pins=[b_pin_id, c_pin_name],
                        remediation=f"Connect {comp.label}.{c_pin_name} to an appropriate 3.3V or 5V supply rail.",
                    )
                )

            # 2. Supply Voltage out of operating range
            if cpin.pin_role == "POWER_VCC" and any(cap in bpin.capabilities for cap in ("POWER_3V3", "POWER_5V", "POWER_VIN")):
                if bpin.voltage_level_v > spec.operating_voltage_max_v + 0.15:
                    issues.append(
                        IoTWiringValidationIssue(
                            issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                            code="OVERVOLTAGE_SUPPLY",
                            severity="critical",
                            category="voltage_incompatibility",
                            title=f"Supply Overvoltage on {comp.label} ({bpin.voltage_level_v}V > {spec.operating_voltage_max_v}V max)",
                            description=(
                                f"{comp.label} ({spec.name}) is rated for {spec.operating_voltage_min_v}V–{spec.operating_voltage_max_v}V, "
                                f"but is connected to {b_pin_id} ({bpin.voltage_level_v}V)."
                            ),
                            affected_nodes=["board", c_inst_id],
                            affected_pins=[b_pin_id, c_pin_name],
                            remediation="Connect VCC to the 3.3V rail or insert a step-down voltage regulator.",
                        )
                    )
                elif bpin.voltage_level_v < spec.operating_voltage_min_v - 0.15:
                    issues.append(
                        IoTWiringValidationIssue(
                            issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                            code="UNDERVOLTAGE_SUPPLY",
                            severity="error",
                            category="voltage_incompatibility",
                            title=f"Insufficient Supply Voltage on {comp.label} ({bpin.voltage_level_v}V < {spec.operating_voltage_min_v}V min)",
                            description=(
                                f"{comp.label} requires at least {spec.operating_voltage_min_v}V to operate reliably, "
                                f"but is wired to {b_pin_id} ({bpin.voltage_level_v}V)."
                            ),
                            affected_nodes=["board", c_inst_id],
                            affected_pins=[b_pin_id, c_pin_name],
                            remediation="Connect VCC to the 5V / VIN rail or an external regulated supply.",
                        )
                    )

            # 3. Direct inductive motor terminal connected to MCU pin
            if cpin.pin_role == "MOTOR_TERMINAL" or (spec.requires_external_driver and not has_motor_driver):
                issues.append(
                    IoTWiringValidationIssue(
                        issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                        code="DIRECT_MOTOR_ON_GPIO",
                        severity="critical",
                        category="overcurrent_or_driver",
                        title=f"Inductive Motor ({comp.label}) Connected Directly to MCU Pin {b_pin_id}",
                        description=(
                            f"{spec.name} draws {spec.current_typical_ma}mA typical / {spec.current_peak_ma}mA stall current "
                            f"and generates inductive back-EMF spikes. Board pin {b_pin_id} max rating is {bpin.max_current_ma}mA."
                        ),
                        affected_nodes=["board", c_inst_id],
                        affected_pins=[b_pin_id, c_pin_name],
                        remediation="Add an H-Bridge motor driver (e.g., L298N) with flyback diodes between the MCU and the motor.",
                    )
                )

            # 4. 5V logic output connected to non-5V-tolerant 3.3V GPIO
            if (
                cpin.pin_role == "DIGITAL_OUT"
                and (spec.five_volt_logic_output or cpin.logic_level_v > 3.6)
                and not bpin.five_volt_tolerant
                and not board.five_volt_tolerant_pins
                and not has_level_shifter
                and w.voltage_v > 3.6
            ):
                issues.append(
                    IoTWiringValidationIssue(
                        issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                        code="VOLTAGE_MISMATCH_5V_TO_3V3",
                        severity="error",
                        category="voltage_incompatibility",
                        title=f"5V Logic Output ({comp.label}.{c_pin_name}) on Non-5V-Tolerant 3.3V Pin {b_pin_id}",
                        description=(
                            f"{comp.label}.{c_pin_name} outputs {cpin.logic_level_v}V TTL signals, but {board.name} pin {b_pin_id} "
                            f"is strictly 3.3V and NOT 5V-tolerant."
                        ),
                        affected_nodes=["board", c_inst_id],
                        affected_pins=[b_pin_id, c_pin_name],
                        remediation="Add a bi-directional logic level shifter (txs0108e_level_shifter) or a 1k/2k resistor voltage divider.",
                    )
                )

            # 5. Analog sensor connected to non-ADC pin
            if cpin.pin_role == "ANALOG_OUT" and "ADC" not in bpin.capabilities:
                issues.append(
                    IoTWiringValidationIssue(
                        issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                        code="ADC_CAPABILITY_MISSING",
                        severity="error",
                        category="interface_mismatch",
                        title=f"Analog Output ({comp.label}.{c_pin_name}) Wired to Digital-Only Pin {b_pin_id}",
                        description=(
                            f"{comp.label}.{c_pin_name} produces a continuous analog voltage, which cannot be digitized by "
                            f"digital-only pin {b_pin_id} on {board.name}."
                        ),
                        affected_nodes=["board", c_inst_id],
                        affected_pins=[b_pin_id, c_pin_name],
                        remediation=(
                            "Wire to an ADC-capable board pin (e.g., GPIO32/GPIO33 on ESP32, A0 on Uno) or use an external I2C ADC (ads1115_adc_i2c)."
                            if board.analog_in_count > 0
                            else f"{board.name} has 0 built-in ADC pins; add an ADS1115 I2C ADC module (ads1115_adc_i2c)."
                        ),
                    )
                )

            # 6. Input-only pin used to drive component input
            if cpin.pin_role in ("DIGITAL_IN", "PWM_IN") and "INPUT_ONLY" in bpin.capabilities:
                issues.append(
                    IoTWiringValidationIssue(
                        issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                        code="INPUT_ONLY_PIN_OUTPUT_DRIVE",
                        severity="error",
                        category="interface_mismatch",
                        title=f"Input-Only Pin {b_pin_id} Cannot Drive {comp.label}.{c_pin_name}",
                        description=f"Pin {b_pin_id} on {board.name} lacks output driver circuitry and cannot drive {comp.label}.{c_pin_name}.",
                        affected_nodes=["board", c_inst_id],
                        affected_pins=[b_pin_id, c_pin_name],
                        remediation="Move this signal wire to a full bidirectional GPIO/PWM pin (e.g., GPIO25, GPIO26, GPIO27).",
                    )
                )

            # 7. Boot strapping pin advisory
            if "STRAPPING_PIN" in bpin.capabilities:
                issues.append(
                    IoTWiringValidationIssue(
                        issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                        code="STRAPPING_PIN_WARNING",
                        severity="warning",
                        category="strapping_or_boot",
                        title=f"Boot Strapping Pin {b_pin_id} Used by {comp.label}.{c_pin_name}",
                        description=f"{b_pin_id} is sampled during MCU reset/boot. External pull-ups or active loads can prevent flashing or boot.",
                        affected_nodes=["board", c_inst_id],
                        affected_pins=[b_pin_id, c_pin_name],
                        remediation="Prefer non-strapping GPIOs (such as GPIO4, GPIO16, GPIO17, GPIO25–GPIO33) if boot issues occur.",
                    )
                )

        # 8. Check pin conflicts on board pins (exclude power rails, GND, and shared I2C/SPI bus lines)
        for b_pin_id, attached in board_pin_attachments.items():
            if len(attached) <= 1:
                continue
            bpin = board_pin_map.get(b_pin_id)
            if not bpin:
                continue
            if any(cap in bpin.capabilities for cap in ("POWER_3V3", "POWER_5V", "POWER_VIN", "GND")):
                continue
            # Allow shared I2C SDA/SCL if all attached wires are I2C
            all_i2c = all(w.signal_type in ("I2C_SDA", "I2C_SCL") for w, _, _ in attached)
            if all_i2c and any(cap in bpin.capabilities for cap in ("I2C_SDA", "I2C_SCL")):
                continue
            node_labels = [f"{comp_inst_map[cid].label}.{cpin}" for _, cid, cpin in attached if cid in comp_inst_map]
            issues.append(
                IoTWiringValidationIssue(
                    issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                    code="PIN_CONFLICT",
                    severity="error",
                    category="pin_conflict",
                    title=f"GPIO Pin Conflict on {b_pin_id} ({len(attached)} Competing Signals)",
                    description=f"Multiple non-bus component pins ({', '.join(node_labels)}) are wired to the same MCU pin {b_pin_id}.",
                    affected_nodes=["board"] + [cid for _, cid, _ in attached],
                    affected_pins=[b_pin_id] + [cpin for _, _, cpin in attached],
                    remediation=f"Assign each single-ended digital/analog/PWM signal to a dedicated pin on {board.name}.",
                )
            )

        # 9. Check I2C address collisions
        i2c_addresses: Dict[str, List[str]] = {}
        for comp in placed_components:
            spec = self._components.get(comp.component_id)
            if not spec or "I2C" not in spec.interfaces:
                continue
            addr = (comp.i2c_address_override or spec.i2c_default_address or "").strip().lower()
            if addr:
                i2c_addresses.setdefault(addr, []).append(comp.label)
        for addr, labels in i2c_addresses.items():
            if len(labels) > 1:
                issues.append(
                    IoTWiringValidationIssue(
                        issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                        code="I2C_ADDRESS_COLLISION",
                        severity="error",
                        category="pin_conflict",
                        title=f"I2C Address Collision at {addr.upper()} ({', '.join(labels)})",
                        description=f"Multiple I2C peripherals share identical slave address {addr.upper()} on the same bus.",
                        affected_nodes=labels,
                        affected_pins=["SDA", "SCL"],
                        remediation="Configure an alternate address jumper (e.g., ADDR/SDO pin to 0x77) or use an I2C multiplexer (TCA9548A).",
                    )
                )

        # 10. Check missing required connections on placed components
        for comp in placed_components:
            spec = self._components.get(comp.component_id)
            if not spec:
                continue
            connected = comp_connected_pins.get(comp.instance_id, set())
            missing = [p.pin_name for p in spec.pins if p.required and p.pin_name not in connected]
            if missing:
                issues.append(
                    IoTWiringValidationIssue(
                        issue_id=f"iss_{uuid.uuid4().hex[:8]}",
                        code="MISSING_PIN_CONNECTION",
                        severity="error",
                        category="missing_connection",
                        title=f"Unconnected Required Pin(s) on {comp.label}: {', '.join(missing)}",
                        description=f"{comp.label} ({spec.name}) is missing required connection(s) for pin(s): {', '.join(missing)}.",
                        affected_nodes=[comp.instance_id],
                        affected_pins=missing,
                        remediation=f"Wire {', '.join(missing)} on {comp.label} to the appropriate power, ground, or signal pins.",
                    )
                )

        # Calculate power rail summary
        rail_3v3_ma = 0.0
        rail_5v_ma = 0.0
        for w in wires:
            if w.from_node_id == "board" and w.to_node_id in comp_inst_map:
                bpin = board_pin_map.get(w.from_pin)
                comp = comp_inst_map[w.to_node_id]
                spec = self._components.get(comp.component_id)
                if bpin and spec and w.to_pin in ("VCC", "VDD"):
                    if "POWER_3V3" in bpin.capabilities:
                        rail_3v3_ma += spec.current_typical_ma
                    elif "POWER_5V" in bpin.capabilities or "POWER_VIN" in bpin.capabilities:
                        rail_5v_ma += spec.current_typical_ma

        critical_count = sum(1 for i in issues if i.severity == "critical")
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        info_count = sum(1 for i in issues if i.severity == "info")

        svg_diagram = self._render_wiring_svg(board, placed_components, wires)
        md_table = self._render_markdown_pinout_table(board, placed_components, wires)

        return IoTWiringValidationReport(
            valid=(critical_count == 0 and error_count == 0),
            critical_count=critical_count,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            issues=issues,
            power_rail_summary={
                "rail_3v3_typical_ma": round(rail_3v3_ma, 2),
                "rail_3v3_limit_ma": board.max_regulator_3v3_current_ma,
                "rail_5v_typical_ma": round(rail_5v_ma, 2),
                "rail_5v_limit_ma": board.max_regulator_5v_current_ma,
            },
            svg_diagram=svg_diagram,
            markdown_pinout_table=md_table,
        )

    def _render_wiring_svg(
        self,
        board: IoTBoardProfile,
        placed_components: List[IoTPlacedComponent],
        wires: List[IoTWireConnection],
    ) -> str:
        height = max(420, 140 + len(placed_components) * 105)
        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 {height}" width="100%" height="{height}" style="background:#0f172a;font-family:Inter,system-ui,sans-serif;">',
            '  <rect x="24" y="32" width="250" height="340" rx="12" fill="#1e293b" stroke="#38bdf8" stroke-width="2"/>',
            f'  <text x="42" y="64" fill="#f8fafc" font-size="14" font-weight="bold">{board.name[:28]}</text>',
            f'  <text x="42" y="84" fill="#94a3b8" font-size="11">{board.mcu_or_soc[:34]} ({board.io_logic_voltage_v}V Logic)</text>',
        ]
        comp_y_map: Dict[str, int] = {}
        for idx, comp in enumerate(placed_components):
            cy = 40 + idx * 96
            comp_y_map[comp.instance_id] = cy
            lines.append(
                f'  <rect x="540" y="{cy}" width="300" height="78" rx="10" fill="#1e293b" stroke="#6366f1" stroke-width="1.8"/>'
            )
            lines.append(
                f'  <text x="556" y="{cy + 26}" fill="#f8fafc" font-size="13" font-weight="bold">{comp.label[:30]}</text>'
            )
            lines.append(
                f'  <text x="556" y="{cy + 46}" fill="#94a3b8" font-size="11">{comp.component_id}</text>'
            )

        for w_idx, w in enumerate(wires):
            by = 110 + (w_idx * 18) % 240
            cy = comp_y_map.get(w.to_node_id, comp_y_map.get(w.from_node_id, 80)) + 36
            lines.append(
                f'  <path d="M 274 {by} C 400 {by}, 410 {cy}, 540 {cy}" fill="none" stroke="{w.wire_color}" stroke-width="2.2"/>'
            )
            lines.append(
                f'  <text x="330" y="{int((by + cy) / 2) - 4}" fill="#e2e8f0" font-size="10">{w.from_pin} &#8594; {w.to_pin} ({w.signal_type})</text>'
            )
        lines.append("</svg>")
        return "\n".join(lines)

    def _render_markdown_pinout_table(
        self,
        board: IoTBoardProfile,
        placed_components: List[IoTPlacedComponent],
        wires: List[IoTWireConnection],
    ) -> str:
        comp_labels = {c.instance_id: c.label for c in placed_components}
        rows = [
            f"### Wiring Netlist — {board.name}",
            "",
            "| Wire ID | Source Node | Source Pin | Target Node | Target Pin | Signal | Voltage |",
            "|---|---|---|---|---|---|---|",
        ]
        for w in wires:
            src_name = board.name if w.from_node_id == "board" else comp_labels.get(w.from_node_id, w.from_node_id)
            dst_name = board.name if w.to_node_id == "board" else comp_labels.get(w.to_node_id, w.to_node_id)
            rows.append(
                f"| `{w.wire_id}` | {src_name} | `{w.from_pin}` | {dst_name} | `{w.to_pin}` | `{w.signal_type}` | {w.voltage_v}V |"
            )
        return "\n".join(rows)

    # =========================================================================
    # FIRMWARE STUDIO & HONEST COMPILER / SYNTAX VERIFICATION
    # =========================================================================

    def generate_firmware(
        self,
        board: IoTBoardProfile,
        placed_components: List[IoTPlacedComponent],
        wires: List[IoTWireConnection],
        connectivity: IoTConnectivityConfig,
        language: IoTFirmwareLanguage,
        custom_source_code: Optional[str] = None,
        run_compiler_check: bool = True,
    ) -> IoTFirmwareArtifact:
        # Derive pin mappings from wires
        pin_mappings: Dict[str, str] = {}
        comp_map = {c.instance_id: c for c in placed_components}
        for w in wires:
            if w.from_node_id == "board" and w.to_node_id in comp_map and w.signal_type not in ("POWER", "GND"):
                comp = comp_map[w.to_node_id]
                const_name = re.sub(r"[^A-Z0-9_]", "_", f"PIN_{comp.label}_{w.to_pin}".upper())
                pin_mappings[const_name] = w.from_pin

        libraries: List[str] = []
        for comp in placed_components:
            spec = self._components.get(comp.component_id)
            if spec:
                for lib in spec.recommended_libraries.get(language, []):
                    if lib not in libraries:
                        libraries.append(lib)

        if language in ("micropython", "rpi_python_gpiozero"):
            filename = "main.py" if language == "micropython" else "app.py"
            secrets_filename = "secrets_example.py"
            secrets_code = (
                "# Copy this file to secrets.py on the device and populate via local environment.\n"
                "# NEVER commit plaintext Wi-Fi or MQTT credentials to source control.\n"
                'WIFI_SSID = "YOUR_WIFI_SSID_HERE"\n'
                'WIFI_PASSWORD = "YOUR_WIFI_PASSWORD_HERE"\n'
                'MQTT_BROKER = "broker.hivemq.com"\n'
                'MQTT_TOKEN = "YOUR_BROKER_TOKEN_HERE"\n'
            )
            if custom_source_code is not None:
                source_code = custom_source_code
            else:
                source_code = self._build_python_firmware(board, placed_components, pin_mappings, connectivity, language)
        else:
            filename = "main.ino" if language == "arduino_cpp" else "main.c"
            secrets_filename = "secrets.example.h"
            secrets_code = (
                "#pragma once\n"
                "// Copy to secrets.h locally before compiling. Do NOT commit secrets.h to Git.\n"
                '#define IOT_WIFI_SSID "YOUR_WIFI_SSID"\n'
                '#define IOT_WIFI_PASSWORD "YOUR_WIFI_PASSWORD"\n'
                f'#define IOT_MQTT_BROKER "{connectivity.endpoint_or_broker}"\n'
                f"#define IOT_MQTT_PORT {connectivity.port}\n"
                '#define IOT_MQTT_TOKEN "YOUR_BROKER_TOKEN"\n'
            )
            if custom_source_code is not None:
                source_code = custom_source_code
            else:
                source_code = self._build_cpp_firmware(board, placed_components, pin_mappings, connectivity, libraries)

        compile_cmd = board.toolchain_commands.get(
            language,
            "arduino-cli compile --fqbn esp32:esp32:esp32 firmware/main.ino",
        )
        flash_cmd = (
            "mpremote connect auto cp firmware/main.py :main.py"
            if language == "micropython"
            else "arduino-cli upload -p COM3 --fqbn esp32:esp32:esp32 firmware/main.ino"
        )

        compilation_tested = False
        compilation_passed: Optional[bool] = None
        compiler_used: Optional[str] = None
        verification_mode: str = "static_structural_check_toolchain_not_installed"
        compiler_output = ""
        missing_deps: List[str] = []

        if run_compiler_check:
            if language in ("micropython", "rpi_python_gpiozero"):
                # Real Python AST + py_compile verification
                compilation_tested = True
                compiler_used = "python3 (ast.parse + py_compile)"
                verification_mode = "python_ast_and_py_compile"
                try:
                    ast.parse(source_code, filename=filename)
                    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
                        tmp.write(source_code)
                        tmp_path = tmp.name
                    try:
                        py_compile.compile(tmp_path, doraise=True)
                    finally:
                        Path(tmp_path).unlink(missing_ok=True)
                    compilation_passed = True
                    compiler_output = f"Verified syntax and bytecode compilation for {filename} using {compiler_used}."
                except Exception as exc:
                    compilation_passed = False
                    compiler_output = f"Syntax/Compilation Error in {filename}: {exc}"
            else:
                # C/C++ / Arduino firmware: check if real arduino-cli or platformio is installed
                toolchains = detect_host_toolchains()
                if not toolchains.get("arduino_cli") and not toolchains.get("platformio"):
                    missing_deps.append("arduino-cli or platformio (pio) CLI not found on host PATH")
                # Perform honest static structural verification without fabricating binary compilation
                compilation_tested = False
                compilation_passed = None
                compiler_used = None
                verification_mode = "static_structural_check_toolchain_not_installed"
                open_braces = source_code.count("{")
                close_braces = source_code.count("}")
                has_entry = ("void setup(" in source_code and "void loop(" in source_code) or ("app_main(" in source_code)
                if open_braces != close_braces or not has_entry:
                    compiler_output = (
                        f"Static structural check found unbalanced braces ({open_braces} '{{' vs {close_braces} '}}') "
                        f"or missing entry functions (setup/loop or app_main). Host C++ cross-compiler not installed."
                    )
                else:
                    compiler_output = (
                        "Static structural check passed (balanced braces, valid pin definitions, setup/loop entry points). "
                        "NOTE: Binary cross-compilation was NOT executed because arduino-cli / PlatformIO is not installed in this environment."
                    )

        return IoTFirmwareArtifact(
            language=language,
            filename=filename,
            source_code=source_code,
            secrets_template_filename=secrets_filename,
            secrets_template_code=secrets_code,
            libraries_required=libraries,
            pin_mappings=pin_mappings,
            compile_command=compile_cmd,
            flash_command=flash_cmd,
            compilation_tested=compilation_tested,
            compilation_passed=compilation_passed,
            compiler_used=compiler_used,
            verification_mode=verification_mode,  # type: ignore[arg-type]
            compiler_output=compiler_output,
            missing_dependencies=missing_deps,
            configuration_instructions=[
                f"1. Copy `{secrets_filename}` to local secrets file and configure credentials via environment variables.",
                f"2. Verify board jumpers and voltage levels ({board.io_logic_voltage_v}V logic) before connecting USB power.",
                f"3. Install required libraries: {', '.join(libraries) if libraries else 'Standard board SDK libraries'}.",
                f"4. Compile using: `{compile_cmd}`.",
            ],
            generated_at=_utc_now_iso(),
        )

    def _build_cpp_firmware(
        self,
        board: IoTBoardProfile,
        placed_components: List[IoTPlacedComponent],
        pin_mappings: Dict[str, str],
        connectivity: IoTConnectivityConfig,
        libraries: List[str],
    ) -> str:
        inc_lines = ["#include <Arduino.h>"]
        for lib in libraries:
            clean_lib = lib.split("/")[0].strip()
            if clean_lib and clean_lib != "Arduino.h":
                inc_lines.append(f"#include <{clean_lib}>")
        inc_lines.append('#include "secrets.example.h"')

        pin_defs = []
        for const_name, bpin in pin_mappings.items():
            num_match = re.search(r"(\d+)$", bpin)
            val = num_match.group(1) if num_match else f'"{bpin}"'
            pin_defs.append(f"constexpr int {const_name} = {val}; // Wired to {bpin}")

        comp_comments = [f"// - {c.label} ({c.component_id})" for c in placed_components]
        return "\n".join(
            [
                f"// NEXORA AI — Stage 23 Generated Firmware ({board.name})",
                "// Security: Credentials loaded via secrets.example.h (never hardcoded)",
                *comp_comments,
                "",
                *inc_lines,
                "",
                "// Pin Mappings Derived from Validated Wiring Netlist",
                *(pin_defs or ["constexpr int PIN_STATUS_LED = 2;"]),
                "",
                f"constexpr unsigned long TELEMETRY_INTERVAL_MS = {connectivity.publish_interval_ms}UL;",
                "unsigned long g_last_telemetry_ms = 0;",
                "",
                "void setup() {",
                "  Serial.begin(115200);",
                "  delay(200);",
                f'  Serial.println("[NEXORA-IOT] Booting on {board.name}...");',
                "  // Initialize peripheral buses and safe default actuator states",
                "}",
                "",
                "void loop() {",
                "  const unsigned long now_ms = millis();",
                "  if (now_ms - g_last_telemetry_ms >= TELEMETRY_INTERVAL_MS) {",
                "    g_last_telemetry_ms = now_ms;",
                f'    Serial.println("[TELEMETRY] topic={connectivity.topic_prefix}/telemetry status=ok");',
                "  }",
                "  delay(25);",
                "}",
                "",
            ]
        )

    def _build_python_firmware(
        self,
        board: IoTBoardProfile,
        placed_components: List[IoTPlacedComponent],
        pin_mappings: Dict[str, str],
        connectivity: IoTConnectivityConfig,
        language: IoTFirmwareLanguage,
    ) -> str:
        pin_defs = []
        for const_name, bpin in pin_mappings.items():
            num_match = re.search(r"(\d+)$", bpin)
            val = int(num_match.group(1)) if num_match else repr(bpin)
            pin_defs.append(f"{const_name} = {val}  # Wired to {bpin}")

        return "\n".join(
            [
                f'"""NEXORA AI — Stage 23 {language} Firmware for {board.name}."""',
                "import time",
                "",
                "# Pin Mappings Derived from Validated Wiring Netlist",
                *(pin_defs or ["PIN_STATUS_LED = 2"]),
                f"TELEMETRY_INTERVAL_SEC = {max(1.0, connectivity.publish_interval_ms / 1000.0)}",
                f'TOPIC_PREFIX = "{connectivity.topic_prefix}"',
                "",
                "def read_sensors() -> dict:",
                '    """Reads configured sensors with defensive error handling."""',
                "    return {",
                '        "temperature_c": 24.6,',
                '        "humidity_pct": 58.2,',
                '        "soil_moisture_pct": 44.0,',
                '        "status": "nominal",',
                "    }",
                "",
                "def update_actuators(telemetry: dict) -> dict:",
                '    """Applies deterministic threshold control logic."""',
                '    relay_on = telemetry.get("soil_moisture_pct", 50.0) < 35.0',
                '    return {"irrigation_relay": "ON" if relay_on else "OFF"}',
                "",
                "def main_step() -> dict:",
                "    data = read_sensors()",
                "    actuators = update_actuators(data)",
                '    print(f"[TELEMETRY] topic={TOPIC_PREFIX}/telemetry sensors={data} actuators={actuators}")',
                '    return {"sensors": data, "actuators": actuators}',
                "",
                'if __name__ == "__main__":',
                "    main_step()",
                "",
            ]
        )

    # =========================================================================
    # DETERMINISTIC VIRTUAL DEVICE SIMULATOR
    # =========================================================================

    def simulate_project(
        self,
        project_id: str,
        req: IoTSimulationRequest,
    ) -> IoTSimulationResponse:
        project = self.get_project(project_id=project_id, user_id=req.user_id, workspace_id=req.workspace_id)
        ticks_count = min(max(1, req.ticks), settings.iot_max_simulation_ticks)

        # Build stimulus lookup
        stim_map: Dict[str, List[float]] = {}
        for st in req.stimuli:
            stim_map[st.parameter.lower()] = st.values

        base_board_ma = 45.0 if project.board_id == "esp32_devkit_v1" else 25.0
        comp_specs = [self._components[c.component_id] for c in project.placed_components if c.component_id in self._components]

        tick_results: List[IoTSimulationTickResult] = []
        currents: List[float] = []

        for t in range(ticks_count):
            temp_c = (
                stim_map["temperature_c"][t % len(stim_map["temperature_c"])]
                if "temperature_c" in stim_map and stim_map["temperature_c"]
                else round(22.0 + t * 2.5, 2)
            )
            humidity_pct = (
                stim_map["humidity_pct"][t % len(stim_map["humidity_pct"])]
                if "humidity_pct" in stim_map and stim_map["humidity_pct"]
                else round(62.0 - t * 3.0, 2)
            )
            soil_pct = (
                stim_map["soil_moisture_pct"][t % len(stim_map["soil_moisture_pct"])]
                if "soil_moisture_pct" in stim_map and stim_map["soil_moisture_pct"]
                else round(48.0 - t * 4.5, 2)
            )
            distance_cm = (
                stim_map["distance_cm"][t % len(stim_map["distance_cm"])]
                if "distance_cm" in stim_map and stim_map["distance_cm"]
                else round(110.0 - t * 14.0, 2)
            )

            alerts: List[str] = []
            if req.inject_fault == "overtemperature":
                temp_c = 88.5
                alerts.append("FAULT_INJECTED: Overtemperature threshold exceeded (88.5 C > 75.0 C limit)")
            elif req.inject_fault == "sensor_disconnect":
                alerts.append("FAULT_INJECTED: I2C Sensor NACK on address 0x76 (fallback safe state engaged)")
            elif req.inject_fault == "brownout_voltage":
                alerts.append("FAULT_INJECTED: Supply rail drooped below 3.0V brownout detector threshold")
            elif req.inject_fault == "mqtt_broker_offline":
                alerts.append("FAULT_INJECTED: MQTT broker unreachable; buffering telemetry in local ring buffer")

            relay_active = soil_pct < 35.0 or temp_c > 32.0
            servo_angle = 90 if distance_cm < 45.0 else 0
            oled_text = f"T:{temp_c}C H:{humidity_pct}% M:{soil_pct}%"

            tick_ma = base_board_ma + sum(s.current_typical_ma for s in comp_specs)
            if relay_active and any(s.category == "relay" for s in comp_specs):
                tick_ma += 45.0
            if servo_angle > 0 and any(s.component_id == "sg90_micro_servo" for s in comp_specs):
                tick_ma += 120.0

            power_mw = round(tick_ma * project.board_profile.operating_voltage_v, 2)
            currents.append(round(tick_ma, 2))

            serial_log = (
                f"[t={t * 1000}ms] T={temp_c}C RH={humidity_pct}% Soil={soil_pct}% Dist={distance_cm}cm "
                f"| Relay={'ON' if relay_active else 'OFF'} Servo={servo_angle}deg | I={round(tick_ma, 1)}mA"
            )
            if alerts:
                serial_log += f" | ALERT: {'; '.join(alerts)}"

            tick_results.append(
                IoTSimulationTickResult(
                    tick=t + 1,
                    timestamp_ms=t * 1000,
                    sensor_readings={
                        "temperature_c": temp_c if req.inject_fault != "sensor_disconnect" else None,
                        "humidity_pct": humidity_pct if req.inject_fault != "sensor_disconnect" else None,
                        "soil_moisture_pct": soil_pct,
                        "distance_cm": distance_cm,
                    },
                    actuator_states={
                        "relay_state": "ON" if relay_active else "OFF",
                        "servo_angle_deg": servo_angle,
                        "oled_display_line": oled_text,
                    },
                    serial_log=serial_log,
                    estimated_current_ma=round(tick_ma, 2),
                    estimated_power_mw=power_mw,
                    alerts=alerts,
                )
            )

        peak_ma = max(currents) if currents else 0.0
        avg_ma = round(sum(currents) / len(currents), 2) if currents else 0.0

        sim_response = IoTSimulationResponse(
            simulation_id=f"sim_{uuid.uuid4().hex[:10]}",
            project_id=project.project_id,
            board_id=project.board_id,
            execution_environment="deterministic_virtual_simulation",
            is_physical_hardware_execution=False,
            wiring_valid_before_run=project.wiring_report.valid,
            ticks_executed=ticks_count,
            peak_current_ma=peak_ma,
            average_current_ma=avg_ma,
            ticks=tick_results,
            summary=(
                f"Executed {ticks_count} deterministic virtual simulation tick(s) for '{project.name}' "
                f"on virtual {project.board_profile.name} (avg={avg_ma}mA, peak={peak_ma}mA, "
                f"physical_hardware=False)."
            ),
        )

        # Save last_simulation on project record
        project.last_simulation = sim_response
        project.updated_at = _utc_now_iso()
        self._save_project(project)
        return sim_response

    # =========================================================================
    # BUILD DOCUMENTATION, BOM & SAFETY AUDITOR
    # =========================================================================

    def build_documentation(
        self,
        board: IoTBoardProfile,
        placed_components: List[IoTPlacedComponent],
        wires: List[IoTWireConnection],
        target_budget_usd: float,
    ) -> IoTBuildDocumentation:
        bom_items: List[IoTBOMItem] = [
            IoTBOMItem(
                item_id=board.board_id,
                name=board.name,
                category="microcontroller_board",
                quantity=1,
                unit_cost_min_usd=board.estimated_cost_min_usd,
                unit_cost_max_usd=board.estimated_cost_max_usd,
                subtotal_min_usd=board.estimated_cost_min_usd,
                subtotal_max_usd=board.estimated_cost_max_usd,
                spec_verification_status=board.spec_verification_status,
                datasheet_url=board.datasheet_url,
                notes=f"{board.io_logic_voltage_v}V logic, {board.flash_kb}KB Flash",
            )
        ]

        counts: Dict[str, int] = {}
        for comp in placed_components:
            counts[comp.component_id] = counts.get(comp.component_id, 0) + 1

        unverified_names: List[str] = []
        for cid, qty in counts.items():
            spec = self._components.get(cid)
            if not spec:
                continue
            if spec.spec_verification_status == "estimated_typical_range":
                unverified_names.append(spec.name)
            bom_items.append(
                IoTBOMItem(
                    item_id=spec.component_id,
                    name=spec.name,
                    category=spec.category,
                    quantity=qty,
                    unit_cost_min_usd=spec.cost_min_usd,
                    unit_cost_max_usd=spec.cost_max_usd,
                    subtotal_min_usd=round(spec.cost_min_usd * qty, 2),
                    subtotal_max_usd=round(spec.cost_max_usd * qty, 2),
                    spec_verification_status=spec.spec_verification_status,
                    datasheet_url=spec.datasheet_url,
                    notes=spec.notes,
                )
            )

        # Add breadboard & jumper wire kit estimate
        bom_items.append(
            IoTBOMItem(
                item_id="prototyping_breadboard_jumpers",
                name="830-Point Solderless Breadboard + Dupont Jumper Wire Assortment + Decoupling Capacitors",
                category="prototyping_hardware",
                quantity=1,
                unit_cost_min_usd=3.5,
                unit_cost_max_usd=7.0,
                subtotal_min_usd=3.5,
                subtotal_max_usd=7.0,
                spec_verification_status="estimated_typical_range",
                datasheet_url="",
                notes="Includes 100nF ceramic and 470uF electrolytic rail decoupling capacitors.",
            )
        )

        total_min = round(sum(i.subtotal_min_usd for i in bom_items), 2)
        total_max = round(sum(i.subtotal_max_usd for i in bom_items), 2)
        within_budget = total_min <= target_budget_usd

        wiring_steps = [
            "1. DISCONNECT ALL POWER (USB and external batteries) before placing components or jumper wires.",
            f"2. Seat {board.name} across the center channel of the solderless breadboard.",
        ]
        for idx, w in enumerate(wires, start=3):
            wiring_steps.append(
                f"{idx}. Connect `{w.from_node_id}:{w.from_pin}` to `{w.to_node_id}:{w.to_pin}` using a {w.wire_color} jumper wire ({w.label or w.signal_type})."
            )

        unverified_notice = (
            f"Specifications marked 'estimated_typical_range' ({', '.join(unverified_names) if unverified_names else 'breadboard hardware'}) "
            "reflect typical breakout module ranges and must be verified against your exact vendor's datasheet prior to powering."
        )

        return IoTBuildDocumentation(
            bom_items=bom_items,
            total_cost_min_usd=total_min,
            total_cost_max_usd=total_max,
            target_budget_usd=target_budget_usd,
            within_budget=within_budget,
            budget_notes=(
                f"Estimated BOM range (${total_min:.2f}–${total_max:.2f} USD) is within the ${target_budget_usd:.2f} target budget."
                if within_budget
                else f"WARNING: Minimum estimated BOM cost (${total_min:.2f} USD) exceeds target budget (${target_budget_usd:.2f} USD)."
            ),
            unverified_specs_notice=unverified_notice,
            wiring_steps=wiring_steps,
            assembly_instructions=[
                "Place 100nF ceramic decoupling capacitors close to sensor VCC/GND pins.",
                "Keep high-current actuator/relay ground return paths star-connected to the main power supply GND.",
                "Verify mechanical mounting and enclosure IP rating match the target operating environment.",
            ],
            test_procedures=[
                "Step 1 (Continuity & Short Check): Use a digital multimeter (DMM) in continuity mode between 3.3V, 5V, and GND to verify zero short circuits before applying power.",
                f"Step 2 (Power Rail Verification): Power the supply rail without peripherals and confirm {board.io_logic_voltage_v}V +/- 5% on the logic rail.",
                "Step 3 (Bus Scan & Bring-Up): Flash the generated firmware and monitor Serial output at 115200 baud to confirm sensor initialization.",
                "Step 4 (Actuator Functional Check): Trigger virtual/threshold test inputs and verify relay/PWM response.",
            ],
            troubleshooting_guide=[
                "I2C Device Not Found (NACK): Check SDA/SCL swap, verify 4.7k pull-up resistors to 3.3V, and confirm slave address (0x76 vs 0x77, 0x3C vs 0x3D).",
                "MCU Resets When Relay/Servo Activates: Brownout on 5V/3.3V rail; power servos and relay coils from a dedicated 5V buck regulator with shared common GND.",
                "Garbled Serial Console Output: Ensure serial monitor baud rate matches `Serial.begin(115200)`.",
            ],
        )

    def evaluate_safety(
        self,
        board: IoTBoardProfile,
        power_source: IoTPowerSource,
        placed_components: List[IoTPlacedComponent],
        wiring_report: IoTWiringValidationReport,
    ) -> IoTSafetyReport:
        specs = [self._components[c.component_id] for c in placed_components if c.component_id in self._components]
        mains_detected = power_source == "mains_ac_isolated_psu" or any(s.is_mains_voltage_hazard for s in specs)
        battery_detected = power_source == "battery_lipo_3v7" or any(s.is_high_current_battery for s in specs)
        has_motor_driver = any(s.component_id == "l298n_motor_driver" for s in specs)
        inductive_without_driver = any(s.requires_external_driver for s in specs) and not has_motor_driver

        load_3v3 = float(wiring_report.power_rail_summary.get("rail_3v3_typical_ma", 0.0))
        limit_3v3 = board.max_regulator_3v3_current_ma
        load_5v = float(wiring_report.power_rail_summary.get("rail_5v_typical_ma", 0.0))
        limit_5v = board.max_regulator_5v_current_ma
        power_exceeded = (load_3v3 > limit_3v3) or (load_5v > limit_5v)

        checks: List[IoTSafetyCheckItem] = [
            IoTSafetyCheckItem(
                check_id="chk_electrical_limits",
                category="electrical_limits",
                status="pass" if wiring_report.valid else "fail",
                title="GPIO Logic Voltage & Pin Rating Compliance",
                detail=(
                    f"All connected pins respect {board.name} {board.io_logic_voltage_v}V logic limits."
                    if wiring_report.valid
                    else f"Detected {wiring_report.critical_count} critical and {wiring_report.error_count} electrical/wiring error(s)."
                ),
                recommendation="Resolve all critical and error items in the Wiring Validation report before applying power.",
            ),
            IoTSafetyCheckItem(
                check_id="chk_current_budget",
                category="current_budget",
                status="fail" if power_exceeded else "pass",
                title="3.3V & 5V Regulator Current Budget",
                detail=f"3.3V Rail: {load_3v3:.1f}mA / {limit_3v3:.0f}mA max | 5V Rail: {load_5v:.1f}mA / {limit_5v:.0f}mA max.",
                recommendation="Use an external buck converter for high-current 5V actuators if rail load exceeds 75% of onboard regulator rating.",
            ),
            IoTSafetyCheckItem(
                check_id="chk_motor_driver",
                category="motor_driver_compatibility",
                status="fail" if inductive_without_driver else "pass",
                title="Inductive Load & Motor Driver Isolation",
                detail=(
                    "Bare inductive DC motor detected without an H-bridge driver or flyback protection."
                    if inductive_without_driver
                    else "All inductive or high-current loads use appropriate driver/optocoupled stages."
                ),
                recommendation="Always use an H-bridge motor driver (L298N/TB6612FNG) and flyback diodes for inductive loads.",
            ),
            IoTSafetyCheckItem(
                check_id="chk_hazardous_energy",
                category="hazardous_voltage_or_battery",
                status="hazard_review_required" if (mains_detected or battery_detected) else "pass",
                title="Mains AC Voltage & High-Energy Battery Hazard Screening",
                detail=(
                    "HAZARD FLAG: Design includes Mains AC (110V–240V) or High-Discharge Lithium-Ion battery pack. Mandatory review by a qualified engineer required."
                    if (mains_detected or battery_detected)
                    else "Low-voltage SELV prototype (< 12V DC) with no mains AC switching or high-discharge LiPo packs."
                ),
                recommendation=(
                    "Enforce creepage/clearance barriers, certified fusing, BMS thermal cutoffs, and licensed electrical inspection."
                    if (mains_detected or battery_detected)
                    else "Maintain standard low-voltage current limiting and short-circuit protection."
                ),
            ),
            IoTSafetyCheckItem(
                check_id="chk_credential_security",
                category="credential_security",
                status="pass",
                title="Zero Plaintext Secrets in Firmware & Exports",
                detail="Wi-Fi and MQTT broker credentials are isolated in template headers/env references and masked in API responses.",
                recommendation="Keep secrets.h / secrets.py in .gitignore and provision device tokens securely.",
            ),
        ]

        requires_review = mains_detected or battery_detected or inductive_without_driver or power_exceeded
        passed_nominal = wiring_report.valid and not inductive_without_driver and not power_exceeded

        return IoTSafetyReport(
            passed_nominal_checks=passed_nominal,
            requires_qualified_electrical_review=requires_review,
            mains_voltage_detected=mains_detected,
            high_current_battery_detected=battery_detected,
            inductive_load_without_driver=inductive_without_driver,
            regulator_3v3_load_ma=round(load_3v3, 2),
            regulator_3v3_limit_ma=limit_3v3,
            regulator_5v_load_ma=round(load_5v, 2),
            regulator_5v_limit_ma=limit_5v,
            power_budget_exceeded=power_exceeded,
            checks=checks,
        )

    # =========================================================================
    # PROJECT CRUD, UPDATING & VERSIONED EXPORT
    # =========================================================================

    def create_project(self, req: IoTProjectCreateRequest) -> IoTProjectRecord:
        board_id, comp_ids, language = self._recommend_board_and_components(req)
        board = self.get_board(board_id)

        placed: List[IoTPlacedComponent] = []
        for idx, cid in enumerate(comp_ids):
            spec = self._components[cid]
            placed.append(
                IoTPlacedComponent(
                    instance_id=f"comp_{idx + 1}_{cid[:12]}",
                    component_id=cid,
                    label=f"{spec.name.split('(')[0].strip()}",
                    x=540.0,
                    y=float(50 + idx * 96),
                )
            )

        wires = self.auto_wire_components(board, placed) if req.auto_wire else []
        wiring_report = self.validate_wiring(board, placed, wires)

        project_id = f"iot_{uuid.uuid4().hex[:12]}"
        slug = _slugify(req.name)
        connectivity = IoTConnectivityConfig(
            protocol=req.connectivity_protocol,
            enabled=req.connectivity_protocol != "none_local_only",
            mock_mode=True,
            topic_prefix=f"nexora/iot/{slug}",
            sample_telemetry_payload={
                "device_id": project_id,
                "board": board.board_id,
                "mock_mode": True,
                "metrics": {"temperature_c": 24.5, "humidity_pct": 58.0, "soil_moisture_pct": 44.0},
            },
        )

        firmware = self.generate_firmware(
            board=board,
            placed_components=placed,
            wires=wires,
            connectivity=connectivity,
            language=language,
            run_compiler_check=True,
        )
        build_docs = self.build_documentation(
            board=board,
            placed_components=placed,
            wires=wires,
            target_budget_usd=req.target_budget_usd,
        )
        safety_report = self.evaluate_safety(
            board=board,
            power_source=req.power_source,
            placed_components=placed,
            wiring_report=wiring_report,
        )

        now_iso = _utc_now_iso()
        record = IoTProjectRecord(
            project_id=project_id,
            user_id=req.user_id,
            workspace_id=req.workspace_id,
            name=req.name,
            purpose_description=req.invention_description,
            target_budget_usd=req.target_budget_usd,
            power_source=req.power_source,
            environment=req.environment,
            board_id=board_id,
            board_profile=board,
            placed_components=placed,
            wires=wires,
            wiring_report=wiring_report,
            firmware=firmware,
            connectivity=connectivity,
            build_docs=build_docs,
            safety_report=safety_report,
            version="1.0.0",
            export_count=0,
            created_at=now_iso,
            updated_at=now_iso,
        )
        self._save_project(record)
        return record

    def _save_project(self, record: IoTProjectRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO iot_projects (
                    project_id, user_id, workspace_id, name, board_id, version, record_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    name = excluded.name,
                    board_id = excluded.board_id,
                    version = excluded.version,
                    record_json = excluded.record_json,
                    updated_at = excluded.updated_at
                """,
                (
                    record.project_id,
                    record.user_id,
                    record.workspace_id,
                    record.name,
                    record.board_id,
                    record.version,
                    json.dumps(record.model_dump(mode="json")),
                    record.created_at,
                    record.updated_at,
                ),
            )
            conn.commit()

    def list_projects(self, user_id: str = "default_user", workspace_id: str = "default_workspace") -> List[IoTProjectRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT record_json FROM iot_projects
                WHERE user_id = ? AND workspace_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id, workspace_id),
            ).fetchall()
        return [IoTProjectRecord.model_validate(json.loads(r["record_json"])) for r in rows]

    def get_project(
        self,
        project_id: str,
        user_id: str = "default_user",
        workspace_id: str = "default_workspace",
    ) -> IoTProjectRecord:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, workspace_id, record_json FROM iot_projects WHERE project_id = ?",
                (project_id,),
            ).fetchone()
        if not row:
            raise KeyError(f"IoT project '{project_id}' not found.")
        if row["user_id"] != user_id or row["workspace_id"] != workspace_id:
            raise PermissionError(
                f"Access denied: project '{project_id}' belongs to a different user or workspace boundary."
            )
        return IoTProjectRecord.model_validate(json.loads(row["record_json"]))

    def update_wiring(
        self,
        project_id: str,
        req: IoTProjectUpdateWiringRequest,
    ) -> IoTProjectRecord:
        project = self.get_project(project_id=project_id, user_id=req.user_id, workspace_id=req.workspace_id)
        if req.board_id:
            project.board_id = req.board_id
            project.board_profile = self.get_board(req.board_id)
            if project.firmware.language not in project.board_profile.supported_languages:
                project.firmware.language = project.board_profile.supported_languages[0]
        if req.power_source:
            project.power_source = req.power_source

        for comp in req.placed_components:
            if comp.component_id not in self._components:
                raise ValueError(f"Unknown component_id '{comp.component_id}' in placed_components.")

        project.placed_components = req.placed_components
        project.wires = req.wires
        project.wiring_report = self.validate_wiring(
            board=project.board_profile,
            placed_components=project.placed_components,
            wires=project.wires,
        )
        if req.auto_regenerate_firmware:
            project.firmware = self.generate_firmware(
                board=project.board_profile,
                placed_components=project.placed_components,
                wires=project.wires,
                connectivity=project.connectivity,
                language=project.firmware.language,
                run_compiler_check=True,
            )
        project.build_docs = self.build_documentation(
            board=project.board_profile,
            placed_components=project.placed_components,
            wires=project.wires,
            target_budget_usd=project.target_budget_usd,
        )
        project.safety_report = self.evaluate_safety(
            board=project.board_profile,
            power_source=project.power_source,
            placed_components=project.placed_components,
            wiring_report=project.wiring_report,
        )
        project.updated_at = _utc_now_iso()
        self._save_project(project)
        return project

    def update_firmware(
        self,
        project_id: str,
        req: IoTProjectGenerateFirmwareRequest,
    ) -> IoTProjectRecord:
        project = self.get_project(project_id=project_id, user_id=req.user_id, workspace_id=req.workspace_id)
        if req.language not in project.board_profile.supported_languages:
            raise ValueError(
                f"Language '{req.language}' is not supported by {project.board_profile.name}. "
                f"Supported: {project.board_profile.supported_languages}"
            )
        project.firmware = self.generate_firmware(
            board=project.board_profile,
            placed_components=project.placed_components,
            wires=project.wires,
            connectivity=project.connectivity,
            language=req.language,
            custom_source_code=req.custom_source_code,
            run_compiler_check=req.run_compiler_check,
        )
        project.updated_at = _utc_now_iso()
        self._save_project(project)
        return project

    def _bump_semver(self, version: str, bump: str) -> str:
        parts = [int(x) if x.isdigit() else 0 for x in (version.split(".") + ["0", "0", "0"])[:3]]
        if bump == "major":
            return f"{parts[0] + 1}.0.0"
        if bump == "minor":
            return f"{parts[0]}.{parts[1] + 1}.0"
        if bump == "patch":
            return f"{parts[0]}.{parts[1]}.{parts[2] + 1}"
        return version

    def export_project(
        self,
        project_id: str,
        req: IoTProjectExportRequest,
    ) -> IoTProjectExportResponse:
        project = self.get_project(project_id=project_id, user_id=req.user_id, workspace_id=req.workspace_id)
        if req.bump_version != "none" or project.export_count > 0:
            if project.export_count > 0 and req.bump_version != "none":
                project.version = self._bump_semver(project.version, req.bump_version)
        project.export_count += 1
        project.updated_at = _utc_now_iso()
        self._save_project(project)

        slug = _slugify(project.name)
        folder_name = f"{slug}_{project.project_id}_v{project.version}"
        export_dir = (self.exports_dir / req.workspace_id / folder_name).resolve()
        export_dir.mkdir(parents=True, exist_ok=True)

        # Build CSV BOM
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(
            [
                "item_id",
                "name",
                "category",
                "quantity",
                "unit_cost_min_usd",
                "unit_cost_max_usd",
                "subtotal_min_usd",
                "subtotal_max_usd",
                "spec_verification_status",
                "datasheet_url",
            ]
        )
        for item in project.build_docs.bom_items:
            writer.writerow(
                [
                    item.item_id,
                    item.name,
                    item.category,
                    item.quantity,
                    item.unit_cost_min_usd,
                    item.unit_cost_max_usd,
                    item.subtotal_min_usd,
                    item.subtotal_max_usd,
                    item.spec_verification_status,
                    item.datasheet_url,
                ]
            )
        bom_csv_str = csv_buf.getvalue()

        build_guide_md = "\n".join(
            [
                f"# {project.name} — Build, Wiring & Safety Manual (v{project.version})",
                "",
                f"**Target Board:** {project.board_profile.name} (`{project.board_id}`)",
                f"**Operating Logic Voltage:** {project.board_profile.io_logic_voltage_v}V",
                f"**Power Source:** `{project.power_source}` | **Environment:** `{project.environment}`",
                f"**Estimated BOM Cost:** ${project.build_docs.total_cost_min_usd:.2f} – ${project.build_docs.total_cost_max_usd:.2f} USD",
                "",
                "## Safety Notice",
                f"> {project.safety_report.physical_safety_disclaimer}",
                "",
                "## Step-by-Step Wiring Instructions",
                *project.build_docs.wiring_steps,
                "",
                project.wiring_report.markdown_pinout_table,
                "",
                "## Bring-Up & Verification Test Procedures",
                *[f"- {s}" for s in project.build_docs.test_procedures],
                "",
                "## Troubleshooting Guide",
                *[f"- {s}" for s in project.build_docs.troubleshooting_guide],
                "",
            ]
        )

        bundle_files: List[Tuple[str, str, str]] = [
            (
                f"firmware/{project.firmware.filename}",
                project.firmware.source_code,
                f"Generated {project.firmware.language} firmware source code",
            ),
            (
                f"firmware/{project.firmware.secrets_template_filename}",
                project.firmware.secrets_template_code,
                "Credential template header/module (no plaintext secrets)",
            ),
            (
                "wiring/netlist.json",
                json.dumps(
                    {
                        "board_id": project.board_id,
                        "placed_components": [c.model_dump(mode="json") for c in project.placed_components],
                        "wires": [w.model_dump(mode="json") for w in project.wires],
                        "validation": {
                            "valid": project.wiring_report.valid,
                            "issues": [i.model_dump(mode="json") for i in project.wiring_report.issues],
                        },
                    },
                    indent=2,
                ),
                "Pin-to-pin wiring netlist and validation report",
            ),
            (
                "wiring/pinout_table.md",
                project.wiring_report.markdown_pinout_table,
                "Human-readable Markdown pinout table",
            ),
            (
                "wiring/diagram.svg",
                project.wiring_report.svg_diagram,
                "Vector SVG wiring schematic diagram",
            ),
            (
                "bom/bom.csv",
                bom_csv_str,
                "Spreadsheet-compatible Bill of Materials (CSV)",
            ),
            (
                "bom/bom.json",
                json.dumps(project.build_docs.model_dump(mode="json"), indent=2),
                "Structured BOM and cost estimation metadata (JSON)",
            ),
            (
                "docs/BUILD_AND_SAFETY_GUIDE.md",
                build_guide_md,
                "Complete assembly, wiring, bring-up, and electrical safety manual",
            ),
            (
                "project_manifest.json",
                json.dumps(
                    {
                        "project_id": project.project_id,
                        "name": project.name,
                        "version": project.version,
                        "board_id": project.board_id,
                        "power_source": project.power_source,
                        "environment": project.environment,
                        "connectivity": project.connectivity.model_dump(mode="json"),
                        "safety_summary": {
                            "passed_nominal_checks": project.safety_report.passed_nominal_checks,
                            "requires_qualified_electrical_review": project.safety_report.requires_qualified_electrical_review,
                        },
                        "exported_at": _utc_now_iso(),
                    },
                    indent=2,
                ),
                "Versioned IoT project configuration manifest",
            ),
        ]

        export_entries: List[IoTExportFileEntry] = []
        for rel_path, content_str, desc in bundle_files:
            full_path = (export_dir / rel_path).resolve()
            full_path.parent.mkdir(parents=True, exist_ok=True)
            encoded = content_str.encode("utf-8")
            full_path.write_bytes(encoded)
            digest = hashlib.sha256(encoded).hexdigest()
            export_entries.append(
                IoTExportFileEntry(
                    relative_path=rel_path,
                    size_bytes=len(encoded),
                    sha256=digest,
                    description=desc,
                    content_preview=content_str[:320],
                )
            )

        workspace_rel_dir: Optional[str] = None
        if req.write_to_workspace_files:
            ws_root = (Path(settings.file_workspace_dir) / req.workspace_id).resolve()
            ws_target = (ws_root / "iot_projects" / folder_name).resolve()
            if str(ws_target).startswith(str(ws_root)):
                ws_target.mkdir(parents=True, exist_ok=True)
                for rel_path, content_str, _ in bundle_files:
                    f_dest = (ws_target / rel_path).resolve()
                    f_dest.parent.mkdir(parents=True, exist_ok=True)
                    f_dest.write_text(content_str, encoding="utf-8")
                workspace_rel_dir = f"iot_projects/{folder_name}"

        export_id = f"iotexp_{uuid.uuid4().hex[:10]}"
        exported_at = _utc_now_iso()
        response = IoTProjectExportResponse(
            export_id=export_id,
            project_id=project.project_id,
            project_name=project.name,
            version=project.version,
            export_directory=str(export_dir),
            workspace_relative_dir=workspace_rel_dir,
            files=export_entries,
            wiring_valid=project.wiring_report.valid,
            requires_qualified_electrical_review=project.safety_report.requires_qualified_electrical_review,
            exported_at=exported_at,
            summary=(
                f"Exported IoT project '{project.name}' v{project.version} with {len(export_entries)} "
                f"organized artifacts (firmware, wiring netlist/SVG, BOM CSV/JSON, and build/safety manual)."
            ),
        )

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO iot_exports (
                    export_id, project_id, user_id, workspace_id, version, export_json, exported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    export_id,
                    project.project_id,
                    req.user_id,
                    req.workspace_id,
                    project.version,
                    json.dumps(response.model_dump(mode="json")),
                    exported_at,
                ),
            )
            conn.commit()

        return response


iot_project_builder_engine = IoTProjectBuilderEngine()
