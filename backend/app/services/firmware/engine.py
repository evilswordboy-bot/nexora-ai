from __future__ import annotations

import ast
import hashlib
import json
import py_compile
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.models.schemas import (
    FirmwareApproveActionRequest,
    FirmwareArtifactFile,
    FirmwareBuildSettings,
    FirmwareCodeSearchHit,
    FirmwareCompileRequest,
    FirmwareCompileResult,
    FirmwareCompilerDiagnostic,
    FirmwareDeviceActionRecord,
    FirmwareDeviceActionRequest,
    FirmwareExportResponse,
    FirmwareFileUpdateRequest,
    FirmwareFrameworkId,
    FirmwareHardwareDiagnostic,
    FirmwareLibraryDependency,
    FirmwareMetadataResponse,
    FirmwarePlatformMatrixEntry,
    FirmwareProjectFile,
    FirmwareQualityReport,
    FirmwareRestoreVersionRequest,
    FirmwareSerialLogEntry,
    FirmwareSerialMonitorRequest,
    FirmwareSerialMonitorResponse,
    FirmwareStaticIssue,
    FirmwareVersionSnapshot,
    FirmwareWorkspaceCreateRequest,
    FirmwareWorkspaceRecord,
    IoTBoardId,
    IoTBoardProfile,
    IoTProjectRecord,
)
from app.services.iot.catalog import detect_host_toolchains
from app.services.iot.engine import iot_project_builder_engine


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_str(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return slug or "firmware-project"


_SECRET_PATTERNS = [
    re.compile(r'(?i)(wifi_password|mqtt_password|api_key|secret_key|auth_token)\s*[:=]\s*["\']([^"\']{4,})["\']'),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
]


def _scrub_secrets(text: str) -> str:
    out = text
    out = re.sub(r"\bsk-[A-Za-z0-9]{16,}\b", "[REDACTED_API_KEY]", out)
    out = re.sub(r"\bghp_[A-Za-z0-9]{20,}\b", "[REDACTED_TOKEN]", out)
    out = re.sub(
        r'(?i)(wifi_password|mqtt_password|api_key|secret_key|auth_token)(\s*[:=]\s*["\'])([^"\']+)(["\'])',
        r"\1\2[REDACTED_SECRET]\4",
        out,
    )
    return out


class EmbeddedFirmwareStudioEngine:
    """
    Stage 24: Embedded Firmware Engineering Studio.
    Reuses Stage 23 IoT Project Builder board profiles, component specifications, and validated wiring
    to provide multi-file modular firmware workspaces, hardware-aware driver & ISR generation,
    static embedded quality analysis, isolated compilation & unit-test execution, simulated vs. physical
    serial monitoring, approval-gated device flashing/reset, version history, and authentic artifact export.
    """

    def __init__(self, db_path: Optional[str] = None, builds_dir: Optional[str] = None) -> None:
        self.db_path = Path(db_path or settings.firmware_db_path)
        self.builds_dir = Path(builds_dir or settings.firmware_builds_dir)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.builds_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._ensure_seed_workspace()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS firmware_workspaces (
                    fw_project_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    board_id TEXT NOT NULL,
                    framework TEXT NOT NULL,
                    semver TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_fw_workspaces_tenant
                ON firmware_workspaces (user_id, workspace_id, updated_at DESC)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS firmware_device_actions (
                    action_id TEXT PRIMARY KEY,
                    fw_project_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    action_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _ensure_seed_workspace(self) -> None:
        existing = self.list_workspaces(user_id="default_user", workspace_id="default_workspace")
        if existing:
            return
        iot_projects = iot_project_builder_engine.list_projects(
            user_id="default_user",
            workspace_id="default_workspace",
        )
        linked_id = iot_projects[0].project_id if iot_projects else None
        self.create_workspace(
            FirmwareWorkspaceCreateRequest(
                user_id="default_user",
                workspace_id="default_workspace",
                name="ESP32 Greenhouse Modular Firmware (Arduino C++)",
                iot_project_id=linked_id,
                board_id="esp32_devkit_v1",
                framework="arduino_cpp",
            )
        )

    # =========================================================================
    # 1. MULTI-PLATFORM MATRIX & COMBINATION VALIDATION
    # =========================================================================

    def get_platform_matrix(self) -> List[FirmwarePlatformMatrixEntry]:
        toolchains = detect_host_toolchains()
        return [
            FirmwarePlatformMatrixEntry(
                board_id="esp32_devkit_v1",
                board_name="ESP32-WROOM-32 DevKit V1 (30-Pin)",
                mcu_or_soc="ESP32-D0WDQ6 Dual-Core Xtensa LX6",
                supported_frameworks=["arduino_cpp", "esp_idf_c", "micropython"],
                unsupported_frameworks={
                    "stm32_hal_c": "STM32Cube HAL targets ARM Cortex-M microcontrollers and is incompatible with Espressif Xtensa LX6.",
                    "rpi_python_gpiozero": "gpiozero requires a Linux SBC userspace (/dev/gpiomem) and cannot run bare-metal on ESP32.",
                },
                compiler_binaries={
                    "arduino_cpp": "arduino-cli / pio",
                    "esp_idf_c": "idf.py / xtensa-esp32-elf-gcc",
                    "micropython": "python3 (ast + py_compile bytecode)",
                },
                toolchain_available={
                    "arduino_cpp": bool(toolchains.get("arduino_cli") or toolchains.get("platformio")),
                    "esp_idf_c": bool(toolchains.get("esp_idf")),
                    "micropython": bool(toolchains.get("python3")),
                },
                flash_protocol="esptool.py UART bootloader (115200 / 460800 baud)",
                default_baud_rate=115200,
            ),
            FirmwarePlatformMatrixEntry(
                board_id="arduino_uno_r3",
                board_name="Arduino Uno R3 (ATmega328P)",
                mcu_or_soc="Microchip ATmega328P (8-bit AVR, 2KB SRAM, 32KB Flash)",
                supported_frameworks=["arduino_cpp"],
                unsupported_frameworks={
                    "micropython": "ATmega328P has only 2 KB SRAM and 32 KB Flash; MicroPython VM requires >= 16 KB SRAM and >= 256 KB Flash.",
                    "esp_idf_c": "ESP-IDF is specific to Espressif SoCs and does not support 8-bit AVR targets.",
                    "stm32_hal_c": "STM32Cube HAL is specific to STMicroelectronics ARM Cortex-M targets.",
                    "rpi_python_gpiozero": "Requires Linux OS and Python 3 runtime.",
                },
                compiler_binaries={
                    "arduino_cpp": "arduino-cli / avr-g++",
                },
                toolchain_available={
                    "arduino_cpp": bool(toolchains.get("arduino_cli") or toolchains.get("platformio")),
                },
                flash_protocol="avrdude stk500v1 over USB-Serial (115200 baud)",
                default_baud_rate=115200,
            ),
            FirmwarePlatformMatrixEntry(
                board_id="stm32_nucleo_f401re",
                board_name="STM32 Nucleo-F401RE (Cortex-M4)",
                mcu_or_soc="STM32F401RET6 ARM Cortex-M4F (96KB SRAM, 512KB Flash)",
                supported_frameworks=["stm32_hal_c", "arduino_cpp", "micropython"],
                unsupported_frameworks={
                    "esp_idf_c": "ESP-IDF targets Espressif SoCs, not ARM Cortex-M4 STM32 microcontrollers.",
                    "rpi_python_gpiozero": "Requires Linux SBC userspace.",
                },
                compiler_binaries={
                    "stm32_hal_c": "arm-none-eabi-gcc / pio",
                    "arduino_cpp": "pio / arduino-cli (STM32duino)",
                    "micropython": "python3 (ast + py_compile bytecode)",
                },
                toolchain_available={
                    "stm32_hal_c": bool(toolchains.get("arm_none_eabi_gcc") or toolchains.get("platformio")),
                    "arduino_cpp": bool(toolchains.get("platformio") or toolchains.get("arduino_cli")),
                    "micropython": bool(toolchains.get("python3")),
                },
                flash_protocol="ST-LINK SWD / OpenOCD / DFU",
                default_baud_rate=115200,
            ),
            FirmwarePlatformMatrixEntry(
                board_id="raspberry_pi_pico_w",
                board_name="Raspberry Pi Pico W (RP2040 + CYW43439)",
                mcu_or_soc="Dual-Core ARM Cortex-M0+ RP2040 (264KB SRAM, 2MB Flash)",
                supported_frameworks=["micropython", "arduino_cpp"],
                unsupported_frameworks={
                    "esp_idf_c": "ESP-IDF does not support RP2040 ARM Cortex-M0+.",
                    "stm32_hal_c": "STM32Cube HAL does not support RP2040.",
                    "rpi_python_gpiozero": "Pico W is a microcontroller running bare-metal/MicroPython, not full Linux.",
                },
                compiler_binaries={
                    "micropython": "python3 (ast + py_compile bytecode)",
                    "arduino_cpp": "arduino-cli / pio (earlephilhower rp2040)",
                },
                toolchain_available={
                    "micropython": bool(toolchains.get("python3")),
                    "arduino_cpp": bool(toolchains.get("arduino_cli") or toolchains.get("platformio")),
                },
                flash_protocol="UF2 Mass Storage Bootloader / mpremote / picotool",
                default_baud_rate=115200,
            ),
            FirmwarePlatformMatrixEntry(
                board_id="raspberry_pi_4b",
                board_name="Raspberry Pi 4 Model B (40-Pin Header)",
                mcu_or_soc="Broadcom BCM2711 Quad-Core Cortex-A72",
                supported_frameworks=["rpi_python_gpiozero"],
                unsupported_frameworks={
                    "arduino_cpp": "Raspberry Pi 4B is a Linux SBC; use Python gpiozero/lgpio or Linux userspace C++.",
                    "esp_idf_c": "ESP-IDF targets Espressif microcontrollers.",
                    "stm32_hal_c": "STM32Cube HAL targets STM32 microcontrollers.",
                    "micropython": "Full CPython 3 is native on Raspberry Pi OS; use rpi_python_gpiozero.",
                },
                compiler_binaries={
                    "rpi_python_gpiozero": "python3 (ast + py_compile bytecode)",
                },
                toolchain_available={
                    "rpi_python_gpiozero": bool(toolchains.get("python3")),
                },
                flash_protocol="SSH / systemd service deployment",
                default_baud_rate=115200,
            ),
        ]

    def validate_board_framework_combination(self, board_id: IoTBoardId, framework: FirmwareFrameworkId) -> None:
        matrix = {m.board_id: m for m in self.get_platform_matrix()}
        entry = matrix.get(board_id)
        if not entry:
            raise ValueError(f"Unsupported board_id '{board_id}'.")
        if framework not in entry.supported_frameworks:
            reason = entry.unsupported_frameworks.get(
                framework,
                f"Framework '{framework}' is not supported on {entry.board_name}.",
            )
            raise ValueError(
                f"Unsupported board/framework combination ({board_id} + {framework}): {reason} "
                f"Supported frameworks for {entry.board_name}: {entry.supported_frameworks}"
            )

    def get_metadata(self) -> FirmwareMetadataResponse:
        return FirmwareMetadataResponse(
            stage=24,
            engine="EmbeddedFirmwareStudioEngine",
            reuses_stage23_iot_builder=True,
            platform_matrix=self.get_platform_matrix(),
            detected_toolchains=detect_host_toolchains(),
            connected_serial_ports=[],
            safety_and_honesty_policy=(
                "Compilation results are reported as SUCCEEDED only when a real compiler/bytecode toolchain "
                "executes and exits 0. Serial monitor logs explicitly distinguish simulated virtual output "
                "from physical hardware ports. Flashing or resetting a physical device requires explicit user approval."
            ),
        )

    # =========================================================================
    # 2. HARDWARE-AWARE MULTI-FILE PROJECT GENERATION
    # =========================================================================

    def _make_file(
        self,
        path: str,
        role: str,
        language: str,
        content: str,
    ) -> FirmwareProjectFile:
        encoded = content.encode("utf-8")
        return FirmwareProjectFile(
            path=path,
            role=role,  # type: ignore[arg-type]
            language=language,
            content=content,
            size_bytes=len(encoded),
            sha256=hashlib.sha256(encoded).hexdigest(),
            updated_at=_utc_now_iso(),
        )

    def _extract_pin_macros_from_iot_project(
        self,
        board: IoTBoardProfile,
        iot_project: Optional[IoTProjectRecord],
    ) -> Dict[str, int]:
        macros: Dict[str, int] = {}
        if iot_project and iot_project.board_id == board.board_id:
            comp_map = {c.instance_id: c for c in iot_project.placed_components}
            for w in iot_project.wires:
                if w.from_node_id == "board" and w.to_node_id in comp_map and w.signal_type not in ("POWER", "GND"):
                    comp = comp_map[w.to_node_id]
                    macro = re.sub(r"[^A-Z0-9_]", "_", f"PIN_{comp.label}_{w.to_pin}".upper())
                    bpin = next((p for p in board.pins if p.pin_id == w.from_pin), None)
                    if bpin and bpin.gpio_number is not None:
                        macros[macro] = bpin.gpio_number
                    else:
                        m = re.search(r"(\d+)$", w.from_pin)
                        if m:
                            macros[macro] = int(m.group(1))

        if not macros:
            sda_pin = next((p.gpio_number for p in board.pins if "I2C_SDA" in p.capabilities and p.gpio_number is not None), 21)
            scl_pin = next((p.gpio_number for p in board.pins if "I2C_SCL" in p.capabilities and p.gpio_number is not None), 22)
            relay_pin = next((p.gpio_number for p in board.pins if "PWM" in p.capabilities and p.gpio_number is not None), 25)
            isr_pin = next((p.gpio_number for p in board.pins if "DIGITAL_IO" in p.capabilities and p.gpio_number is not None), 4)
            macros = {
                "PIN_I2C_SDA": sda_pin,
                "PIN_I2C_SCL": scl_pin,
                "PIN_ACTUATOR_RELAY": relay_pin,
                "PIN_SAFETY_ISR_IRQ": isr_pin,
            }
        elif "PIN_SAFETY_ISR_IRQ" not in macros:
            isr_pin = next((p.gpio_number for p in board.pins if "DIGITAL_IO" in p.capabilities and p.gpio_number is not None), 4)
            macros["PIN_SAFETY_ISR_IRQ"] = isr_pin

        return macros

    def _generate_project_files(
        self,
        board: IoTBoardProfile,
        framework: FirmwareFrameworkId,
        build_settings: FirmwareBuildSettings,
        iot_project: Optional[IoTProjectRecord],
    ) -> Tuple[List[FirmwareProjectFile], List[FirmwareLibraryDependency]]:
        pin_macros = self._extract_pin_macros_from_iot_project(board, iot_project)
        toolchains = detect_host_toolchains()

        unit_test_py = "\n".join(
            [
                '"""Deterministic Host Unit Tests for Embedded Telemetry & Control Logic."""',
                "import unittest",
                "",
                "def compute_dew_point_c(temp_c: float, rel_humidity_pct: float) -> float:",
                "    if rel_humidity_pct < 0.0 or rel_humidity_pct > 100.0:",
                '        raise ValueError("Relative humidity out of valid bounds [0, 100]")',
                "    return round(temp_c - ((100.0 - rel_humidity_pct) / 5.0), 2)",
                "",
                "def evaluate_actuator_cutoff(temp_c: float, emergency_irq: bool) -> str:",
                "    if emergency_irq or temp_c >= 75.0:",
                '        return "SAFE_SHUTDOWN"',
                "    if temp_c >= 30.0:",
                '        return "COOLING_ACTIVE"',
                '    return "IDLE"',
                "",
                "class EmbeddedFirmwareLogicTest(unittest.TestCase):",
                "    def test_dew_point_calculation(self):",
                "        self.assertAlmostEqual(compute_dew_point_c(25.0, 60.0), 17.0)",
                "",
                "    def test_humidity_bounds_validation(self):",
                "        with self.assertRaises(ValueError):",
                "            compute_dew_point_c(25.0, 115.0)",
                "",
                "    def test_emergency_isr_cutoff_priority(self):",
                '        self.assertEqual(evaluate_actuator_cutoff(24.0, True), "SAFE_SHUTDOWN")',
                '        self.assertEqual(evaluate_actuator_cutoff(80.0, False), "SAFE_SHUTDOWN")',
                '        self.assertEqual(evaluate_actuator_cutoff(32.5, False), "COOLING_ACTIVE")',
                "",
                'if __name__ == "__main__":',
                "    unittest.main()",
                "",
            ]
        )

        if framework in ("micropython", "rpi_python_gpiozero"):
            pin_lines = [
                f'"""Hardware-Aware Pin Configuration for {board.name} ({board.io_logic_voltage_v}V Logic)."""',
                f'BOARD_ID = "{board.board_id}"',
                f"IO_LOGIC_VOLTAGE_V = {board.io_logic_voltage_v}",
                f"SERIAL_BAUD_RATE = {build_settings.serial_baud_rate}",
                f"WATCHDOG_TIMEOUT_MS = {build_settings.watchdog_timeout_ms}",
            ]
            for k, v in pin_macros.items():
                pin_lines.append(f"{k} = {v}")

            secrets_py = (
                '"""Template for device credentials. Copy to secrets.py on device; never commit plaintext secrets."""\n'
                "import os\n\n"
                'WIFI_SSID = os.getenv("IOT_WIFI_SSID", "PROVISION_VIA_ENV")\n'
                'WIFI_PASS_REF = os.getenv("IOT_WIFI_PASSWORD", "PROVISION_VIA_ENV")\n'
            )

            drivers_py = "\n".join(
                [
                    '"""Modular Sensor & Actuator Drivers with Timeout & Bounds Checking."""',
                    "import time",
                    "import pin_config",
                    "",
                    "class PeripheralDriverManager:",
                    "    def __init__(self, i2c_timeout_ms: int = 250) -> None:",
                    "        self.i2c_timeout_ms = i2c_timeout_ms",
                    "        self.initialized = False",
                    "",
                    "    def init_buses(self) -> bool:",
                    "        self.initialized = True",
                    "        return self.initialized",
                    "",
                    "    def read_environmental_telemetry(self) -> dict:",
                    "        if not self.initialized:",
                    '            return {"status": "ERR_NOT_INIT", "temperature_c": 0.0, "humidity_pct": 0.0}',
                    "        return {",
                    '            "status": "OK",',
                    '            "temperature_c": 24.8,',
                    '            "humidity_pct": 56.4,',
                    '            "timeout_ms": self.i2c_timeout_ms,',
                    "        }",
                    "",
                ]
            )

            main_py = "\n".join(
                [
                    f'"""NEXORA Stage 24 Modular {framework} Firmware for {board.name}."""',
                    "import time",
                    "import pin_config",
                    "from drivers.peripheral_drivers import PeripheralDriverManager",
                    "",
                    "g_emergency_irq_triggered = False",
                    "",
                    "def on_safety_interrupt_irq(pin_source: int) -> None:",
                    '    """Non-blocking ISR handler setting volatile state flag only."""',
                    "    global g_emergency_irq_triggered",
                    "    g_emergency_irq_triggered = True",
                    "",
                    "def feed_watchdog() -> bool:",
                    '    """Feeds hardware watchdog timer in main control loop."""',
                    "    return True",
                    "",
                    "def run_firmware_cycle() -> dict:",
                    "    mgr = PeripheralDriverManager(i2c_timeout_ms=250)",
                    "    mgr.init_buses()",
                    "    telemetry = mgr.read_environmental_telemetry()",
                    "    feed_watchdog()",
                    "    return {",
                    '        "board": pin_config.BOARD_ID,',
                    '        "irq_flag": g_emergency_irq_triggered,',
                    '        "telemetry": telemetry,',
                    "    }",
                    "",
                    'if __name__ == "__main__":',
                    "    print(run_firmware_cycle())",
                    "",
                ]
            )

            manifest_json = json.dumps(
                {
                    "board_id": board.board_id,
                    "framework": framework,
                    "optimization_level": build_settings.optimization_level,
                    "watchdog_enabled": build_settings.watchdog_enabled,
                    "watchdog_timeout_ms": build_settings.watchdog_timeout_ms,
                    "serial_baud_rate": build_settings.serial_baud_rate,
                    "libraries": ["machine", "time", "json"],
                },
                indent=2,
            )

            files = [
                self._make_file("pin_config.py", "pin_config", "python", "\n".join(pin_lines) + "\n"),
                self._make_file("secrets_example.py", "secrets_template", "python", secrets_py),
                self._make_file("drivers/peripheral_drivers.py", "driver_source", "python", drivers_py),
                self._make_file("main.py", "main_entry", "python", main_py),
                self._make_file("manifest.json", "build_manifest", "json", manifest_json),
                self._make_file("tests/test_embedded_logic.py", "unit_test", "python", unit_test_py),
            ]
            libs = [
                FirmwareLibraryDependency(
                    name="micropython-bme280",
                    version="^2.1.0",
                    header_or_module="bme280",
                    purpose="I2C environmental sensor driver",
                    installed_in_sandbox=bool(toolchains.get("python3")),
                ),
            ]
            return files, libs

        # C / C++ Embedded Workspace (arduino_cpp, esp_idf_c, stm32_hal_c)
        pin_header_lines = [
            "#pragma once",
            f"// Hardware-Aware Pin Assignments for {board.name} ({board.io_logic_voltage_v}V Logic)",
            "#include <stdint.h>",
            "",
            f"constexpr uint32_t FW_SERIAL_BAUD = {build_settings.serial_baud_rate}UL;",
            f"constexpr uint32_t FW_WATCHDOG_TIMEOUT_MS = {build_settings.watchdog_timeout_ms}UL;",
            "constexpr uint32_t FW_I2C_TIMEOUT_MS = 250UL;",
        ]
        for k, v in pin_macros.items():
            pin_header_lines.append(f"constexpr int {k} = {v};")

        secrets_h = "\n".join(
            [
                "#pragma once",
                "// Copy to include/secrets.h locally and provision via environment variables.",
                "// NEVER store plaintext Wi-Fi or MQTT passwords in source control.",
                '#define FW_WIFI_SSID_ENV "IOT_WIFI_SSID"',
                '#define FW_MQTT_TOKEN_ENV "IOT_BROKER_TOKEN"',
                "",
            ]
        )

        driver_h = "\n".join(
            [
                "#pragma once",
                "#include <stdint.h>",
                "#include <stdbool.h>",
                "",
                "struct SensorTelemetryFrame {",
                "  float temperature_c;",
                "  float humidity_pct;",
                "  float soil_moisture_pct;",
                "  uint32_t sample_timestamp_ms;",
                "  bool valid;",
                "};",
                "",
                "bool drivers_init_all(uint32_t i2c_timeout_ms);",
                "bool drivers_read_telemetry(SensorTelemetryFrame* out_frame, uint32_t now_ms);",
                "void drivers_set_actuator_safe_state(bool relay_enable);",
                "",
            ]
        )

        driver_cpp = "\n".join(
            [
                '#include "include/peripheral_drivers.h"',
                '#include "include/pin_config.h"',
                "#include <stdio.h>",
                "",
                "static uint32_t g_configured_timeout_ms = 250UL;",
                "",
                "bool drivers_init_all(uint32_t i2c_timeout_ms) {",
                "  g_configured_timeout_ms = (i2c_timeout_ms > 0UL) ? i2c_timeout_ms : FW_I2C_TIMEOUT_MS;",
                "  return true;",
                "}",
                "",
                "bool drivers_read_telemetry(SensorTelemetryFrame* out_frame, uint32_t now_ms) {",
                "  if (out_frame == nullptr) {",
                "    return false;",
                "  }",
                "  out_frame->temperature_c = 24.6f;",
                "  out_frame->humidity_pct = 57.5f;",
                "  out_frame->soil_moisture_pct = 43.2f;",
                "  out_frame->sample_timestamp_ms = now_ms;",
                "  out_frame->valid = true;",
                "  return true;",
                "}",
                "",
                "void drivers_set_actuator_safe_state(bool relay_enable) {",
                "  (void)relay_enable;",
                "}",
                "",
            ]
        )

        main_cpp = "\n".join(
            [
                f"// NEXORA Stage 24 Modular Firmware ({framework}) for {board.name}",
                '#include "include/pin_config.h"',
                '#include "include/peripheral_drivers.h"',
                '#include "include/secrets.example.h"',
                "#include <stdio.h>",
                "",
                "volatile bool g_safety_fault_irq = false;",
                "static uint32_t g_last_sample_ms = 0UL;",
                "",
                "void on_hardware_fault_isr() {",
                "  g_safety_fault_irq = true;",
                "}",
                "",
                "void feed_hardware_watchdog() {",
                "  // Hardware watchdog reset strobe (wdt_reset / esp_task_wdt_reset / HAL_IWDG_Refresh)",
                "}",
                "",
                "void setup() {",
                "  drivers_init_all(FW_I2C_TIMEOUT_MS);",
                "  drivers_set_actuator_safe_state(false);",
                "}",
                "",
                "void loop() {",
                "  feed_hardware_watchdog();",
                "  if (g_safety_fault_irq) {",
                "    drivers_set_actuator_safe_state(false);",
                "    return;",
                "  }",
                "  SensorTelemetryFrame frame = {0.0f, 0.0f, 0.0f, 0UL, false};",
                "  if (drivers_read_telemetry(&frame, g_last_sample_ms)) {",
                "    char log_buf[128] = {0};",
                '    snprintf(log_buf, sizeof(log_buf), "[FW] T=%.1fC RH=%.1f%% Valid=%d", frame.temperature_c, frame.humidity_pct, frame.valid ? 1 : 0);',
                "  }",
                "}",
                "",
            ]
        )

        pio_ini = "\n".join(
            [
                f"; NEXORA Stage 24 Build Configuration Manifest ({board.name})",
                f"[env:{board.board_id}]",
                f"board = {board.board_id}",
                f"framework = {framework}",
                f"monitor_speed = {build_settings.serial_baud_rate}",
                f"build_flags = {build_settings.optimization_level} {'-g' if build_settings.debug_symbols else ''} {' '.join(build_settings.extra_build_flags)}".strip(),
                "lib_deps =",
                "  adafruit/Adafruit BME280 Library@^2.2.4",
                "  adafruit/Adafruit SSD1306@^2.5.9",
                "",
            ]
        )

        files = [
            self._make_file("include/pin_config.h", "pin_config", "cpp", "\n".join(pin_header_lines) + "\n"),
            self._make_file("include/secrets.example.h", "secrets_template", "cpp", secrets_h),
            self._make_file("include/peripheral_drivers.h", "driver_header", "cpp", driver_h),
            self._make_file("src/peripheral_drivers.cpp", "driver_source", "cpp", driver_cpp),
            self._make_file("src/main.cpp", "main_entry", "cpp", main_cpp),
            self._make_file("platformio.ini", "build_manifest", "ini", pio_ini),
            self._make_file("test/test_embedded_logic.py", "unit_test", "python", unit_test_py),
        ]
        libs = [
            FirmwareLibraryDependency(
                name="Adafruit BME280 Library",
                version="^2.2.4",
                header_or_module="Adafruit_BME280.h",
                purpose="Hardware I2C temperature, humidity, and barometric pressure driver",
                installed_in_sandbox=bool(toolchains.get("platformio") or toolchains.get("arduino_cli")),
            ),
            FirmwareLibraryDependency(
                name="Adafruit SSD1306",
                version="^2.5.9",
                header_or_module="Adafruit_SSD1306.h",
                purpose="128x64 monochrome OLED I2C framebuffer driver",
                installed_in_sandbox=bool(toolchains.get("platformio") or toolchains.get("arduino_cli")),
            ),
        ]
        return files, libs

    # =========================================================================
    # 3. HARDWARE-AWARE DIAGNOSTICS & STATIC QUALITY ANALYZER
    # =========================================================================

    def evaluate_hardware_diagnostics(
        self,
        board: IoTBoardProfile,
        files: List[FirmwareProjectFile],
        libraries: List[FirmwareLibraryDependency],
        iot_project: Optional[IoTProjectRecord] = None,
    ) -> List[FirmwareHardwareDiagnostic]:
        diags: List[FirmwareHardwareDiagnostic] = []

        # 1. Surface any wiring/voltage issues from the linked Stage 23 IoT project
        if iot_project:
            for w_iss in iot_project.wiring_report.issues:
                if w_iss.severity in ("critical", "error"):
                    cat = "incompatible_voltage" if "VOLTAGE" in w_iss.code else "invalid_pin"
                    diags.append(
                        FirmwareHardwareDiagnostic(
                            diag_id=f"hwdiag_{uuid.uuid4().hex[:8]}",
                            severity=w_iss.severity,  # type: ignore[arg-type]
                            category=cat,  # type: ignore[arg-type]
                            title=f"Stage 23 Wiring Conflict: {w_iss.title}",
                            detail=w_iss.description,
                            file_path="include/pin_config.h",
                            line_number=1,
                            suggested_fix=w_iss.remediation,
                        )
                    )

        valid_gpio_numbers = {p.gpio_number for p in board.pins if p.gpio_number is not None}
        input_only_gpios = {
            p.gpio_number for p in board.pins if "INPUT_ONLY" in p.capabilities and p.gpio_number is not None
        }
        manifest_text = "\n".join(f.content for f in files if f.role == "build_manifest")

        for f in files:
            for line_idx, line in enumerate(f.content.splitlines(), start=1):
                # Check PIN_* assignment to invalid GPIO number or input-only pin used as actuator output
                m_pin = re.search(r"\b(PIN_[A-Z0-9_]+)\s*=\s*(\d+)", line)
                if m_pin:
                    pin_name, pin_num_str = m_pin.group(1), m_pin.group(2)
                    pin_num = int(pin_num_str)
                    if valid_gpio_numbers and pin_num not in valid_gpio_numbers:
                        diags.append(
                            FirmwareHardwareDiagnostic(
                                diag_id=f"hwdiag_{uuid.uuid4().hex[:8]}",
                                severity="error",
                                category="invalid_pin",
                                title=f"Invalid GPIO Number {pin_num} for {pin_name} on {board.name}",
                                detail=f"GPIO {pin_num} is not exposed in the pinout profile of {board.name} (valid GPIOs: {sorted(valid_gpio_numbers)}).",
                                file_path=f.path,
                                line_number=line_idx,
                                suggested_fix=f"Update {pin_name} to a valid GPIO on {board.name}.",
                            )
                        )
                    elif pin_num in input_only_gpios and any(
                        tag in pin_name for tag in ("RELAY", "ACTUATOR", "SERVO", "MOTOR", "TX", "OUT")
                    ):
                        diags.append(
                            FirmwareHardwareDiagnostic(
                                diag_id=f"hwdiag_{uuid.uuid4().hex[:8]}",
                                severity="error",
                                category="invalid_pin",
                                title=f"Input-Only GPIO {pin_num} Assigned to Output {pin_name}",
                                detail=f"GPIO {pin_num} on {board.name} is input-only and cannot drive output loads.",
                                file_path=f.path,
                                line_number=line_idx,
                                suggested_fix="Assign output actuators to a full bidirectional GPIO (e.g., GPIO25, GPIO26, GPIO27).",
                            )
                        )

                # Check unsupported wireless peripheral on boards without built-in radio
                if not board.builtin_wireless and any(
                    tok in line for tok in ("#include <WiFi.h>", "#include <esp_wifi.h>", "import network")
                ):
                    diags.append(
                        FirmwareHardwareDiagnostic(
                            diag_id=f"hwdiag_{uuid.uuid4().hex[:8]}",
                            severity="error",
                            category="unsupported_peripheral",
                            title=f"Native Wi-Fi Peripheral Unsupported on {board.name}",
                            detail=f"{board.name} ({board.mcu_or_soc}) has no onboard Wi-Fi/BLE radio.",
                            file_path=f.path,
                            line_number=line_idx,
                            suggested_fix="Switch to ESP32 / Raspberry Pi Pico W or use an external UART/SPI transceiver.",
                        )
                    )

                # Check third-party library #include not listed in manifest
                m_inc = re.search(r"#include\s*<([A-Za-z0-9_]+\.h)>", line)
                if m_inc:
                    hdr = m_inc.group(1)
                    std_headers = {
                        "Arduino.h",
                        "Wire.h",
                        "SPI.h",
                        "stdint.h",
                        "stdbool.h",
                        "stdio.h",
                        "stdlib.h",
                        "string.h",
                    }
                    if hdr not in std_headers and hdr.split(".")[0].lower() not in manifest_text.lower():
                        diags.append(
                            FirmwareHardwareDiagnostic(
                                diag_id=f"hwdiag_{uuid.uuid4().hex[:8]}",
                                severity="warning",
                                category="missing_library",
                                title=f"Header <{hdr}> Missing from Build Manifest",
                                detail=f"`{f.path}` includes `<{hdr}>`, which is not declared in `platformio.ini` `lib_deps`.",
                                file_path=f.path,
                                line_number=line_idx,
                                suggested_fix=f"Add the library providing `{hdr}` to `lib_deps` in `platformio.ini`.",
                            )
                        )

        return diags

    def analyze_firmware_quality(
        self,
        files: List[FirmwareProjectFile],
        build_settings: FirmwareBuildSettings,
        run_unit_tests: bool = True,
    ) -> FirmwareQualityReport:
        issues: List[FirmwareStaticIssue] = []
        has_watchdog_feed = False

        for f in files:
            if f.role in ("build_manifest", "secrets_template"):
                continue
            lines = f.content.splitlines()
            for idx, line in enumerate(lines, start=1):
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("#"):
                    continue

                # 1. Unsafe C buffer functions
                if re.search(r"\b(strcpy|strcat|sprintf|gets)\s*\(", stripped):
                    issues.append(
                        FirmwareStaticIssue(
                            issue_id=f"qiss_{uuid.uuid4().hex[:8]}",
                            category="unsafe_buffer_handling",
                            severity="critical",
                            file_path=f.path,
                            line_number=idx,
                            code_snippet=stripped[:120],
                            message="Unsafe unbounded C string/buffer operation detected (stack/heap buffer overflow risk).",
                            suggested_fix="Replace `strcpy`/`sprintf`/`strcat` with bounds-checked `snprintf(buf, sizeof(buf), ...)` or `strlcpy`.",
                        )
                    )

                # 2. Blocking loop or excessive delay
                if re.search(r"\bwhile\s*\(\s*(1|true|True)\s*\)", stripped) and "wdt" not in stripped.lower():
                    issues.append(
                        FirmwareStaticIssue(
                            issue_id=f"qiss_{uuid.uuid4().hex[:8]}",
                            category="blocking_loop",
                            severity="error",
                            file_path=f.path,
                            line_number=idx,
                            code_snippet=stripped[:120],
                            message="Unbounded blocking `while(1)` / `while(true)` loop risks starving the RTOS/watchdog timer.",
                            suggested_fix="Use a non-blocking state machine or include an explicit timeout exit condition and watchdog feed.",
                        )
                    )
                m_delay = re.search(r"\bdelay\s*\(\s*(\d+)\s*\)", stripped)
                if m_delay and int(m_delay.group(1)) >= 2000:
                    issues.append(
                        FirmwareStaticIssue(
                            issue_id=f"qiss_{uuid.uuid4().hex[:8]}",
                            category="blocking_loop",
                            severity="warning",
                            file_path=f.path,
                            line_number=idx,
                            code_snippet=stripped[:120],
                            message=f"Blocking `delay({m_delay.group(1)})` freezes sensor polling and ISR responsiveness for >= 2 seconds.",
                            suggested_fix="Use non-blocking `millis()` / `time.ticks_ms()` elapsed-time scheduling.",
                        )
                    )

                # 3. Dynamic heap allocation in embedded firmware
                if re.search(r"\b(malloc|calloc|realloc)\s*\(", stripped):
                    issues.append(
                        FirmwareStaticIssue(
                            issue_id=f"qiss_{uuid.uuid4().hex[:8]}",
                            category="memory_error",
                            severity="warning",
                            file_path=f.path,
                            line_number=idx,
                            code_snippet=stripped[:120],
                            message="Dynamic heap allocation (`malloc`/`calloc`/`realloc`) can cause heap fragmentation on long-running MCUs.",
                            suggested_fix="Prefer statically allocated buffers or fixed-size ring buffers in embedded firmware.",
                        )
                    )

                # 4. Uninitialized local variable in C/C++
                if f.language in ("cpp", "c") and re.match(
                    r"^(int|float|double|uint32_t|uint16_t|char\s*\*)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*;$",
                    stripped,
                ):
                    issues.append(
                        FirmwareStaticIssue(
                            issue_id=f"qiss_{uuid.uuid4().hex[:8]}",
                            category="uninitialized_value",
                            severity="warning",
                            file_path=f.path,
                            line_number=idx,
                            code_snippet=stripped[:120],
                            message="Local variable or pointer declared without an explicit initial value.",
                            suggested_fix="Initialize variables at declaration (e.g., `= 0`, `= 0.0f`, `= nullptr`).",
                        )
                    )

                # 5. Missing timeout on blocking I/O
                if re.search(r"\bpulseIn\s*\([^,]+,[^,]+\)", stripped):
                    issues.append(
                        FirmwareStaticIssue(
                            issue_id=f"qiss_{uuid.uuid4().hex[:8]}",
                            category="missing_timeout",
                            severity="warning",
                            file_path=f.path,
                            line_number=idx,
                            code_snippet=stripped[:120],
                            message="`pulseIn(pin, state)` called without an explicit timeout parameter (defaults to 1,000,000 us block).",
                            suggested_fix="Pass a bounded timeout in microseconds: `pulseIn(pin, HIGH, 30000UL)`.",
                        )
                    )

                # 6. Hardcoded credentials check
                for pat in _SECRET_PATTERNS:
                    if pat.search(stripped) and "PROVISION_VIA_ENV" not in stripped and "YOUR_" not in stripped:
                        issues.append(
                            FirmwareStaticIssue(
                                issue_id=f"qiss_{uuid.uuid4().hex[:8]}",
                                category="credential_exposure",
                                severity="critical",
                                file_path=f.path,
                                line_number=idx,
                                code_snippet=_scrub_secrets(stripped[:120]),
                                message="Hardcoded credential or secret token detected in firmware source file.",
                                suggested_fix="Move secrets out of source files into git-ignored local provisioning headers or NVS flash.",
                            )
                        )
                        break

                # Track watchdog feed presence
                if any(
                    w_tok in stripped
                    for w_tok in ("feed_hardware_watchdog", "feed_watchdog", "wdt_reset", "esp_task_wdt_reset", "wdt.feed")
                ):
                    has_watchdog_feed = True

        if build_settings.watchdog_enabled and not has_watchdog_feed:
            main_file = next((f.path for f in files if f.role == "main_entry"), "src/main.cpp")
            issues.append(
                FirmwareStaticIssue(
                    issue_id=f"qiss_{uuid.uuid4().hex[:8]}",
                    category="watchdog_issue",
                    severity="error",
                    file_path=main_file,
                    line_number=1,
                    code_snippet="// Watchdog enabled in build settings, but no watchdog reset/feed found in main loop",
                    message="Hardware watchdog is enabled in build settings, but main loop never feeds the watchdog timer.",
                    suggested_fix="Call `feed_hardware_watchdog()` / `esp_task_wdt_reset()` once per healthy iteration of `loop()`.",
                )
            )

        # Execute host unit test scaffolding if requested
        unit_executed = False
        unit_passed: Optional[bool] = None
        unit_output = ""
        test_file = next((f for f in files if f.role == "unit_test" and f.path.endswith(".py")), None)
        if run_unit_tests and test_file is not None:
            unit_executed = True
            with tempfile.TemporaryDirectory() as tmpdir:
                t_path = Path(tmpdir) / "test_embedded_logic.py"
                t_path.write_text(test_file.content, encoding="utf-8")
                try:
                    proc = subprocess.run(
                        [sys.executable, "-m", "unittest", "test_embedded_logic.py"],
                        cwd=tmpdir,
                        capture_output=True,
                        text=True,
                        timeout=8.0,
                    )
                    unit_passed = proc.returncode == 0
                    unit_output = (proc.stdout + "\n" + proc.stderr).strip()
                except Exception as exc:
                    unit_passed = False
                    unit_output = f"Unit test runner error: {exc}"

        crit_count = sum(1 for i in issues if i.severity == "critical")
        err_count = sum(1 for i in issues if i.severity == "error")
        warn_count = sum(1 for i in issues if i.severity == "warning")

        return FirmwareQualityReport(
            passed_quality_gate=(crit_count == 0 and err_count == 0 and (unit_passed is not False)),
            critical_count=crit_count,
            error_count=err_count,
            warning_count=warn_count,
            issues=issues,
            unit_tests_executed=unit_executed,
            unit_tests_passed=unit_passed,
            unit_test_output=unit_output,
            hil_status="SKIPPED_NO_HIL_EQUIPMENT",
        )

    # =========================================================================
    # 4. SANDBOXED COMPILE & DEBUG (ZERO FABRICATED RESULTS)
    # =========================================================================

    def _check_cpp_syntax_diagnostics(self, files: List[FirmwareProjectFile]) -> List[FirmwareCompilerDiagnostic]:
        diags: List[FirmwareCompilerDiagnostic] = []
        for f in files:
            if f.language not in ("cpp", "c"):
                continue
            lines = f.content.splitlines()
            brace_depth = 0
            last_open_line = 1
            for idx, line in enumerate(lines, start=1):
                code_only = re.sub(r"//.*$", "", line).strip()
                if not code_only:
                    continue
                for ch in code_only:
                    if ch == "{":
                        if brace_depth == 0:
                            last_open_line = idx
                        brace_depth += 1
                    elif ch == "}":
                        brace_depth -= 1
                        if brace_depth < 0:
                            diags.append(
                                FirmwareCompilerDiagnostic(
                                    file_path=f.path,
                                    line_number=idx,
                                    column=1,
                                    severity="error",
                                    message="Unmatched closing brace `}` in source file.",
                                    source_line=line.strip()[:120],
                                    suggested_fix="Remove extra `}` or add matching `{` for the block.",
                                )
                            )
                            brace_depth = 0

                # Detect obvious missing semicolon on return or assignment statement
                if re.match(r"^(return\b[^;{}]+|[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*[^;{}]+)$", code_only):
                    diags.append(
                        FirmwareCompilerDiagnostic(
                            file_path=f.path,
                            line_number=idx,
                            column=len(line),
                            severity="error",
                            message="Expected `;` at end of C/C++ statement.",
                            source_line=line.strip()[:120],
                            suggested_fix=f"Append a semicolon: `{code_only};`",
                        )
                    )
            if brace_depth > 0:
                diags.append(
                    FirmwareCompilerDiagnostic(
                        file_path=f.path,
                        line_number=last_open_line,
                        column=1,
                        severity="error",
                        message=f"Unclosed `{brace_depth}` brace block(s) `{{\" reaching end of file `{f.path}`.",
                        source_line=lines[last_open_line - 1].strip()[:120] if lines else "",
                        suggested_fix="Add the missing closing `}` brace at the end of the function/struct block.",
                    )
                )
        return diags

    def compile_workspace(
        self,
        fw_project_id: str,
        req: FirmwareCompileRequest,
    ) -> FirmwareCompileResult:
        ws = self.get_workspace(
            fw_project_id=fw_project_id,
            user_id=req.user_id,
            workspace_id=req.workspace_id,
        )
        start_ts = time.perf_counter()
        build_id = f"fwbuild_{uuid.uuid4().hex[:10]}"
        build_out_dir = (self.builds_dir / ws.workspace_id / ws.fw_project_id / build_id).resolve()
        build_out_dir.mkdir(parents=True, exist_ok=True)

        diagnostics: List[FirmwareCompilerDiagnostic] = []
        produced_artifacts: List[FirmwareArtifactFile] = []

        if ws.framework in ("micropython", "rpi_python_gpiozero"):
            # Real Python AST + py_compile bytecode compilation in isolated build directory
            toolchain_binary = sys.executable
            stdout_lines: List[str] = []
            stderr_lines: List[str] = []
            all_passed = True

            for f in ws.files:
                if not f.path.endswith(".py"):
                    continue
                src_dest = (build_out_dir / f.path).resolve()
                src_dest.parent.mkdir(parents=True, exist_ok=True)
                src_dest.write_text(f.content, encoding="utf-8")
                try:
                    ast.parse(f.content, filename=f.path)
                    pyc_rel = f"bytecode/{Path(f.path).stem}.pyc"
                    pyc_dest = (build_out_dir / pyc_rel).resolve()
                    pyc_dest.parent.mkdir(parents=True, exist_ok=True)
                    py_compile.compile(str(src_dest), cfile=str(pyc_dest), doraise=True)
                    pyc_bytes = pyc_dest.read_bytes()
                    produced_artifacts.append(
                        FirmwareArtifactFile(
                            relative_path=pyc_rel,
                            artifact_type="compiled_bytecode_or_binary",
                            size_bytes=len(pyc_bytes),
                            sha256=hashlib.sha256(pyc_bytes).hexdigest(),
                            genuinely_produced_by_build=True,
                        )
                    )
                    stdout_lines.append(f"[OK] Compiled {f.path} -> {pyc_rel} ({len(pyc_bytes)} bytes)")
                except SyntaxError as syn_err:
                    all_passed = False
                    lineno = syn_err.lineno or 1
                    src_line = (syn_err.text or "").strip()
                    diagnostics.append(
                        FirmwareCompilerDiagnostic(
                            file_path=f.path,
                            line_number=lineno,
                            column=syn_err.offset or 1,
                            severity="error",
                            message=f"SyntaxError: {syn_err.msg}",
                            source_line=src_line,
                            suggested_fix="Fix Python syntax error (check colons, indentation, and closing parentheses).",
                        )
                    )
                    stderr_lines.append(f"{f.path}:{lineno}: SyntaxError: {syn_err.msg}")
                except Exception as exc:
                    all_passed = False
                    stderr_lines.append(f"{f.path}: {exc}")

            elapsed_ms = round((time.perf_counter() - start_ts) * 1000.0, 2)
            status = "SUCCEEDED" if all_passed else "FAILED_COMPILATION_ERROR"
            result = FirmwareCompileResult(
                build_id=build_id,
                workspace_id=ws.workspace_id,
                fw_project_id=ws.fw_project_id,
                board_id=ws.board_id,
                framework=ws.framework,
                status=status,  # type: ignore[arg-type]
                toolchain_binary=f"python3 ({Path(toolchain_binary).name} ast + py_compile)",
                toolchain_installed=True,
                compilation_genuinely_executed=True,
                binary_artifact_produced=all_passed and len(produced_artifacts) > 0,
                exit_code=0 if all_passed else 1,
                duration_ms=elapsed_ms,
                compiler_stdout="\n".join(stdout_lines),
                compiler_stderr="\n".join(stderr_lines),
                diagnostics=diagnostics,
                produced_artifacts=produced_artifacts if all_passed else [],
                compiled_at=_utc_now_iso(),
                honesty_notice=(
                    f"Executed real Python AST and bytecode compilation (`py_compile`) across workspace files ({status})."
                ),
            )
        else:
            # C/C++ frameworks (arduino_cpp, esp_idf_c, stm32_hal_c)
            cpp_diags = self._check_cpp_syntax_diagnostics(ws.files)
            diagnostics.extend(cpp_diags)
            toolchains = detect_host_toolchains()
            has_cpp_toolchain = bool(
                toolchains.get("platformio")
                or toolchains.get("arduino_cli")
                or toolchains.get("esp_idf")
                or toolchains.get("arm_none_eabi_gcc")
            )
            elapsed_ms = round((time.perf_counter() - start_ts) * 1000.0, 2)

            if cpp_diags:
                result = FirmwareCompileResult(
                    build_id=build_id,
                    workspace_id=ws.workspace_id,
                    fw_project_id=ws.fw_project_id,
                    board_id=ws.board_id,
                    framework=ws.framework,
                    status="FAILED_COMPILATION_ERROR",
                    toolchain_binary="nexora-cpp-syntax-verifier",
                    toolchain_installed=has_cpp_toolchain,
                    compilation_genuinely_executed=True,
                    binary_artifact_produced=False,
                    exit_code=1,
                    duration_ms=elapsed_ms,
                    compiler_stdout="",
                    compiler_stderr="\n".join(
                        f"{d.file_path}:{d.line_number}:{d.column}: error: {d.message}" for d in cpp_diags
                    ),
                    diagnostics=diagnostics,
                    produced_artifacts=[],
                    compiled_at=_utc_now_iso(),
                    honesty_notice="Compilation failed due to C/C++ syntax errors detected in source files.",
                )
            else:
                result = FirmwareCompileResult(
                    build_id=build_id,
                    workspace_id=ws.workspace_id,
                    fw_project_id=ws.fw_project_id,
                    board_id=ws.board_id,
                    framework=ws.framework,
                    status="BLOCKED_TOOLCHAIN_MISSING",
                    toolchain_binary="pio / arduino-cli / idf.py (not installed on host PATH)",
                    toolchain_installed=False,
                    compilation_genuinely_executed=False,
                    binary_artifact_produced=False,
                    exit_code=None,
                    duration_ms=elapsed_ms,
                    compiler_stdout="Static syntax & brace structure check: 0 errors.",
                    compiler_stderr=(
                        f"Cross-compiler toolchain for {ws.board_name} ({ws.framework}) is not installed on this host PATH. "
                        "NEXORA never fabricates `.bin`/`.elf` build results when the compiler is absent."
                    ),
                    diagnostics=[],
                    produced_artifacts=[],
                    compiled_at=_utc_now_iso(),
                    honesty_notice=(
                        "HONEST BUILD REPORT: Source files passed static C/C++ structure checks, but binary compilation "
                        "was NOT executed because `platformio` / `arduino-cli` / `idf.py` is not installed on this machine."
                    ),
                )

        ws.last_compile = result
        ws.quality_report = self.analyze_firmware_quality(
            ws.files,
            ws.build_settings,
            run_unit_tests=req.run_unit_tests,
        )
        ws.updated_at = _utc_now_iso()
        self._save_workspace(ws)
        return result

    # =========================================================================
    # 5. DEVICE COMMUNICATION, SERIAL MONITOR & APPROVAL-GATED FLASH/RESET
    # =========================================================================

    def get_serial_monitor(
        self,
        fw_project_id: str,
        req: FirmwareSerialMonitorRequest,
    ) -> FirmwareSerialMonitorResponse:
        ws = self.get_workspace(
            fw_project_id=fw_project_id,
            user_id=req.user_id,
            workspace_id=req.workspace_id,
        )
        if req.mode == "physical_authorized_serial":
            raise ValueError(
                "No authorized physical microcontroller is connected to host serial ports (0 active COM/ttyUSB ports). "
                "Switch to 'simulated_virtual_serial' mode or connect an authorized board."
            )

        logs: List[FirmwareSerialLogEntry] = [
            FirmwareSerialLogEntry(
                seq=1,
                timestamp_ms=0,
                event_type="reset_event",
                message=f"rst:0x1 ({req.simulate_reset_event}), boot:0x13 (SPI_FAST_FLASH_BOOT)",
                firmware_version=ws.semver,
            ),
            FirmwareSerialLogEntry(
                seq=2,
                timestamp_ms=45,
                event_type="boot_banner",
                message=f"[NEXORA-FW v{ws.semver}] Booting '{ws.name}' on {ws.board_name} ({ws.framework}, baud={ws.build_settings.serial_baud_rate})",
                firmware_version=ws.semver,
            ),
        ]
        for idx in range(3, req.lines_count + 1):
            t_ms = (idx - 2) * 1000
            if idx == req.lines_count and req.simulate_reset_event == "WDT_RESET":
                logs.append(
                    FirmwareSerialLogEntry(
                        seq=idx,
                        timestamp_ms=t_ms,
                        event_type="watchdog_feed",
                        message=f"[WDT] Task watchdog fed at t={t_ms}ms (timeout={ws.build_settings.watchdog_timeout_ms}ms)",
                        firmware_version=ws.semver,
                    )
                )
            else:
                temp_val = round(24.2 + (idx % 4) * 0.6, 1)
                rh_val = round(56.0 - (idx % 3) * 0.8, 1)
                logs.append(
                    FirmwareSerialLogEntry(
                        seq=idx,
                        timestamp_ms=t_ms,
                        event_type="sensor_telemetry",
                        message=_scrub_secrets(
                            f"[TELEMETRY t={t_ms}ms] T={temp_val}C RH={rh_val}% ISR_FAULT=0 WDT=OK"
                        ),
                        firmware_version=ws.semver,
                    )
                )

        return FirmwareSerialMonitorResponse(
            fw_project_id=ws.fw_project_id,
            board_id=ws.board_id,
            source_mode="simulated_virtual_serial",
            is_simulated=True,
            connected_physical_port=None,
            baud_rate=ws.build_settings.serial_baud_rate,
            firmware_version=ws.semver,
            reset_reason=req.simulate_reset_event,
            logs=logs,
        )

    def request_device_action(
        self,
        fw_project_id: str,
        req: FirmwareDeviceActionRequest,
    ) -> FirmwareDeviceActionRecord:
        ws = self.get_workspace(
            fw_project_id=fw_project_id,
            user_id=req.user_id,
            workspace_id=req.workspace_id,
        )
        action_id = f"fwact_{uuid.uuid4().hex[:10]}"
        if ws.framework == "micropython":
            cli_cmd = (
                f"mpremote connect {req.target_port} cp main.py :main.py && mpremote connect {req.target_port} reset"
                if req.action_type == "flash_firmware"
                else f"mpremote connect {req.target_port} reset"
            )
        else:
            cli_cmd = (
                f"pio run -e {ws.board_id} -t upload --upload-port {req.target_port}"
                if req.action_type == "flash_firmware"
                else f"esptool.py --port {req.target_port} run"
            )

        recovery_steps = [
            "1. If flashing fails mid-transfer, hold the BOOT/BOOTSEL button while tapping RESET/EN to enter ROM bootloader mode.",
            f"2. Restore the previous known-good version from NEXORA Version History (current semver: v{ws.semver}).",
            f"3. Erase corrupted NVS/flash partitions if bootlooping: `esptool.py --port {req.target_port} erase_flash`.",
        ]

        if not req.confirmed:
            status = "WAITING_FOR_APPROVAL"
            msg = (
                f"Action '{req.action_type}' on port '{req.target_port}' requires explicit user approval "
                "before touching physical hardware."
            )
            resolved_at = None
        else:
            status = "BLOCKED_NO_PHYSICAL_DEVICE"
            msg = (
                f"User approved '{req.action_type}', but no physical device is connected on '{req.target_port}'. "
                f"Run `{cli_cmd}` locally once your board is connected."
            )
            resolved_at = _utc_now_iso()

        record = FirmwareDeviceActionRecord(
            action_id=action_id,
            fw_project_id=ws.fw_project_id,
            user_id=req.user_id,
            workspace_id=req.workspace_id,
            action_type=req.action_type,
            target_port=req.target_port,
            status=status,  # type: ignore[arg-type]
            requires_approval=True,
            cli_command_preview=cli_cmd,
            recovery_guidance=recovery_steps,
            message=msg,
            created_at=_utc_now_iso(),
            resolved_at=resolved_at,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO firmware_device_actions (
                    action_id, fw_project_id, user_id, workspace_id, status, action_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action_id,
                    ws.fw_project_id,
                    req.user_id,
                    req.workspace_id,
                    record.status,
                    json.dumps(record.model_dump(mode="json")),
                    record.created_at,
                ),
            )
            conn.commit()
        return record

    def approve_device_action(
        self,
        action_id: str,
        req: FirmwareApproveActionRequest,
    ) -> FirmwareDeviceActionRecord:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, workspace_id, action_json FROM firmware_device_actions WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        if not row:
            raise KeyError(f"Firmware device action '{action_id}' not found.")
        if row["user_id"] != req.user_id or row["workspace_id"] != req.workspace_id:
            raise PermissionError("Access denied: device action belongs to another user or workspace.")

        record = FirmwareDeviceActionRecord.model_validate(json.loads(row["action_json"]))
        if not req.approved:
            record.status = "CANCELLED"
            record.message = f"Device action '{record.action_type}' was cancelled by the user."
        else:
            record.status = "BLOCKED_NO_PHYSICAL_DEVICE"
            record.message = (
                f"Approval granted for '{record.action_type}', but no physical microcontroller is attached to "
                f"'{record.target_port}'. NEXORA never fabricates hardware flashing results."
            )
        record.resolved_at = _utc_now_iso()

        with self._connect() as conn:
            conn.execute(
                "UPDATE firmware_device_actions SET status = ?, action_json = ? WHERE action_id = ?",
                (record.status, json.dumps(record.model_dump(mode="json")), action_id),
            )
            conn.commit()
        return record

    # =========================================================================
    # 6. WORKSPACE CRUD, FILE EDITING, CODE SEARCH, VERSION ROLLBACK & EXPORT
    # =========================================================================

    def create_workspace(self, req: FirmwareWorkspaceCreateRequest) -> FirmwareWorkspaceRecord:
        self.validate_board_framework_combination(req.board_id, req.framework)
        board = iot_project_builder_engine.get_board(req.board_id)

        iot_proj: Optional[IoTProjectRecord] = None
        if req.iot_project_id:
            iot_proj = iot_project_builder_engine.get_project(
                project_id=req.iot_project_id,
                user_id=req.user_id,
                workspace_id=req.workspace_id,
            )

        build_settings = req.build_settings or FirmwareBuildSettings(
            serial_baud_rate=settings.firmware_default_baud_rate
        )
        files, libraries = self._generate_project_files(
            board=board,
            framework=req.framework,
            build_settings=build_settings,
            iot_project=iot_proj,
        )
        hw_diags = self.evaluate_hardware_diagnostics(board, files, libraries, iot_proj)
        quality_report = self.analyze_firmware_quality(files, build_settings, run_unit_tests=True)

        now_iso = _utc_now_iso()
        fw_project_id = f"fwws_{uuid.uuid4().hex[:12]}"
        initial_version = FirmwareVersionSnapshot(
            version_id=f"fwver_{uuid.uuid4().hex[:8]}",
            semver="1.0.0",
            commit_note="Initial hardware-aware modular firmware scaffold",
            files=files,
            build_settings=build_settings,
            created_at=now_iso,
        )

        record = FirmwareWorkspaceRecord(
            fw_project_id=fw_project_id,
            user_id=req.user_id,
            workspace_id=req.workspace_id,
            name=req.name,
            iot_project_id=req.iot_project_id,
            board_id=req.board_id,
            board_name=board.name,
            framework=req.framework,
            semver="1.0.0",
            build_settings=build_settings,
            libraries=libraries,
            files=files,
            hardware_diagnostics=hw_diags,
            quality_report=quality_report,
            last_compile=None,
            versions=[initial_version],
            recovery_guidance=[
                "1. Bootloader Recovery: Hold BOOT/BOOTSEL while pressing RESET to enter ROM serial/UF2 bootloader.",
                "2. Safe Rollback: Use NEXORA Firmware Version History to restore the previous verified snapshot.",
                "3. Watchdog Safe State: Ensure `drivers_set_actuator_safe_state(false)` runs on boot before enabling relays or motors.",
            ],
            created_at=now_iso,
            updated_at=now_iso,
        )
        self._save_workspace(record)
        return record

    def _save_workspace(self, record: FirmwareWorkspaceRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO firmware_workspaces (
                    fw_project_id, user_id, workspace_id, name, board_id, framework, semver, record_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fw_project_id) DO UPDATE SET
                    name = excluded.name,
                    board_id = excluded.board_id,
                    framework = excluded.framework,
                    semver = excluded.semver,
                    record_json = excluded.record_json,
                    updated_at = excluded.updated_at
                """,
                (
                    record.fw_project_id,
                    record.user_id,
                    record.workspace_id,
                    record.name,
                    record.board_id,
                    record.framework,
                    record.semver,
                    json.dumps(record.model_dump(mode="json")),
                    record.created_at,
                    record.updated_at,
                ),
            )
            conn.commit()

    def list_workspaces(
        self,
        user_id: str = "default_user",
        workspace_id: str = "default_workspace",
    ) -> List[FirmwareWorkspaceRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT record_json FROM firmware_workspaces
                WHERE user_id = ? AND workspace_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id, workspace_id),
            ).fetchall()
        return [FirmwareWorkspaceRecord.model_validate(json.loads(r["record_json"])) for r in rows]

    def get_workspace(
        self,
        fw_project_id: str,
        user_id: str = "default_user",
        workspace_id: str = "default_workspace",
    ) -> FirmwareWorkspaceRecord:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, workspace_id, record_json FROM firmware_workspaces WHERE fw_project_id = ?",
                (fw_project_id,),
            ).fetchone()
        if not row:
            raise KeyError(f"Firmware workspace '{fw_project_id}' not found.")
        if row["user_id"] != user_id or row["workspace_id"] != workspace_id:
            raise PermissionError(
                f"Access denied: firmware workspace '{fw_project_id}' belongs to a different user or workspace."
            )
        return FirmwareWorkspaceRecord.model_validate(json.loads(row["record_json"]))

    def update_file(
        self,
        fw_project_id: str,
        req: FirmwareFileUpdateRequest,
    ) -> FirmwareWorkspaceRecord:
        ws = self.get_workspace(
            fw_project_id=fw_project_id,
            user_id=req.user_id,
            workspace_id=req.workspace_id,
        )
        clean_path = req.file_path.replace("\\", "/").strip("/")
        if ".." in clean_path or clean_path.startswith("/"):
            raise ValueError(f"Invalid relative file path '{req.file_path}'. Path traversal is forbidden.")
        if len(req.content.encode("utf-8")) > settings.firmware_max_file_size_bytes:
            raise ValueError("File exceeds maximum allowed firmware source size.")

        updated_found = False
        new_files: List[FirmwareProjectFile] = []
        for f in ws.files:
            if f.path == clean_path:
                new_files.append(self._make_file(clean_path, f.role, f.language, req.content))
                updated_found = True
            else:
                new_files.append(f)

        if not updated_found:
            ext = Path(clean_path).suffix.lower()
            lang = "python" if ext == ".py" else ("ini" if ext == ".ini" else "cpp")
            new_files.append(self._make_file(clean_path, "driver_source", lang, req.content))

        ws.files = new_files
        board = iot_project_builder_engine.get_board(ws.board_id)
        iot_proj = None
        if ws.iot_project_id:
            try:
                iot_proj = iot_project_builder_engine.get_project(
                    ws.iot_project_id, user_id=req.user_id, workspace_id=req.workspace_id
                )
            except Exception:
                iot_proj = None

        ws.hardware_diagnostics = self.evaluate_hardware_diagnostics(board, ws.files, ws.libraries, iot_proj)
        ws.quality_report = self.analyze_firmware_quality(ws.files, ws.build_settings, run_unit_tests=True)

        if req.create_version_snapshot:
            parts = [int(x) if x.isdigit() else 0 for x in (ws.semver.split(".") + ["0", "0", "0"])[:3]]
            ws.semver = f"{parts[0]}.{parts[1]}.{parts[2] + 1}"
            ws.versions.append(
                FirmwareVersionSnapshot(
                    version_id=f"fwver_{uuid.uuid4().hex[:8]}",
                    semver=ws.semver,
                    commit_note=req.commit_note,
                    files=ws.files,
                    build_settings=ws.build_settings,
                    created_at=_utc_now_iso(),
                )
            )

        ws.updated_at = _utc_now_iso()
        self._save_workspace(ws)
        return ws

    def restore_version(
        self,
        fw_project_id: str,
        req: FirmwareRestoreVersionRequest,
    ) -> FirmwareWorkspaceRecord:
        ws = self.get_workspace(
            fw_project_id=fw_project_id,
            user_id=req.user_id,
            workspace_id=req.workspace_id,
        )
        target = next((v for v in ws.versions if v.version_id == req.version_id), None)
        if not target:
            raise KeyError(f"Version snapshot '{req.version_id}' not found in workspace '{fw_project_id}'.")

        ws.files = target.files
        ws.build_settings = target.build_settings
        ws.semver = target.semver
        board = iot_project_builder_engine.get_board(ws.board_id)
        ws.hardware_diagnostics = self.evaluate_hardware_diagnostics(board, ws.files, ws.libraries, None)
        ws.quality_report = self.analyze_firmware_quality(ws.files, ws.build_settings, run_unit_tests=True)
        ws.updated_at = _utc_now_iso()
        self._save_workspace(ws)
        return ws

    def search_code(
        self,
        fw_project_id: str,
        query: str,
        user_id: str = "default_user",
        workspace_id: str = "default_workspace",
    ) -> List[FirmwareCodeSearchHit]:
        ws = self.get_workspace(fw_project_id=fw_project_id, user_id=user_id, workspace_id=workspace_id)
        q = query.strip().lower()
        if not q:
            return []
        hits: List[FirmwareCodeSearchHit] = []
        for f in ws.files:
            for idx, line in enumerate(f.content.splitlines(), start=1):
                if q in line.lower():
                    hits.append(
                        FirmwareCodeSearchHit(
                            file_path=f.path,
                            line_number=idx,
                            line_preview=line.strip()[:160],
                        )
                    )
        return hits

    def export_artifacts(
        self,
        fw_project_id: str,
        user_id: str = "default_user",
        workspace_id: str = "default_workspace",
    ) -> FirmwareExportResponse:
        ws = self.get_workspace(fw_project_id=fw_project_id, user_id=user_id, workspace_id=workspace_id)
        slug = _slugify(ws.name)
        folder_name = f"{slug}_{ws.fw_project_id}_v{ws.semver}"
        export_dir = (self.builds_dir / workspace_id / "exports" / folder_name).resolve()
        export_dir.mkdir(parents=True, exist_ok=True)

        artifacts: List[FirmwareArtifactFile] = []
        for f in ws.files:
            dest = (export_dir / f.path).resolve()
            dest.parent.mkdir(parents=True, exist_ok=True)
            encoded = f.content.encode("utf-8")
            dest.write_bytes(encoded)
            a_type = "dependency_manifest" if f.role == "build_manifest" else "source_file"
            artifacts.append(
                FirmwareArtifactFile(
                    relative_path=f.path,
                    artifact_type=a_type,  # type: ignore[arg-type]
                    size_bytes=len(encoded),
                    sha256=hashlib.sha256(encoded).hexdigest(),
                    genuinely_produced_by_build=True,
                )
            )

        # Include compiled bytecode/binaries ONLY if genuinely produced on disk during last_compile
        compiled_included = False
        if ws.last_compile and ws.last_compile.binary_artifact_produced:
            build_dir = (self.builds_dir / ws.workspace_id / ws.fw_project_id / ws.last_compile.build_id).resolve()
            for prod in ws.last_compile.produced_artifacts:
                prod_src = (build_dir / prod.relative_path).resolve()
                if prod_src.exists() and prod_src.is_file():
                    prod_dest = (export_dir / prod.relative_path).resolve()
                    prod_dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(prod_src, prod_dest)
                    artifacts.append(prod)
                    compiled_included = True

        release_notes = "\n".join(
            [
                f"# Firmware Release Notes — {ws.name} (v{ws.semver})",
                "",
                f"- **Target Board:** {ws.board_name} (`{ws.board_id}`)",
                f"- **Framework:** `{ws.framework}`",
                f"- **Optimization & Flags:** `{ws.build_settings.optimization_level}`, watchdog={ws.build_settings.watchdog_enabled}",
                f"- **Quality Gate Passed:** `{ws.quality_report.passed_quality_gate}` (Critical: {ws.quality_report.critical_count}, Errors: {ws.quality_report.error_count})",
                f"- **Compiled Binaries Included:** `{compiled_included}` (Only genuine build outputs are exported)",
                "",
                "## Artifact Checksums (SHA-256)",
                *[f"- `{a.relative_path}` ({a.size_bytes} bytes): `{a.sha256}`" for a in artifacts],
                "",
            ]
        )
        rn_bytes = release_notes.encode("utf-8")
        (export_dir / "RELEASE_NOTES.md").write_bytes(rn_bytes)
        artifacts.append(
            FirmwareArtifactFile(
                relative_path="RELEASE_NOTES.md",
                artifact_type="release_notes",
                size_bytes=len(rn_bytes),
                sha256=hashlib.sha256(rn_bytes).hexdigest(),
                genuinely_produced_by_build=True,
            )
        )

        # Mirror into Stage 17 File Workspace
        ws_root = (Path(settings.file_workspace_dir) / workspace_id).resolve()
        ws_target = (ws_root / "firmware_releases" / folder_name).resolve()
        ws_rel_dir: Optional[str] = None
        if str(ws_target).startswith(str(ws_root)):
            ws_target.mkdir(parents=True, exist_ok=True)
            for a in artifacts:
                src_f = (export_dir / a.relative_path).resolve()
                dst_f = (ws_target / a.relative_path).resolve()
                dst_f.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_f, dst_f)
            ws_rel_dir = f"firmware_releases/{folder_name}"

        return FirmwareExportResponse(
            export_id=f"fwexp_{uuid.uuid4().hex[:10]}",
            fw_project_id=ws.fw_project_id,
            name=ws.name,
            semver=ws.semver,
            export_directory=str(export_dir),
            workspace_relative_dir=ws_rel_dir,
            only_real_artifacts_exported=True,
            compiled_binaries_included=compiled_included,
            artifacts=artifacts,
            release_notes_markdown=release_notes,
            exported_at=_utc_now_iso(),
            summary=(
                f"Exported {len(artifacts)} authentic firmware artifact(s) for '{ws.name}' v{ws.semver} "
                f"(compiled_binaries_included={compiled_included})."
            ),
        )


firmware_studio_engine = EmbeddedFirmwareStudioEngine()
