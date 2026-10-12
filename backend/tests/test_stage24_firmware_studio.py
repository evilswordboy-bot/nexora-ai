from __future__ import annotations

import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.services.tools_registry import tool_registry

client = TestClient(app)


def test_stage24_platform_matrix_and_unsupported_combinations():
    # 1. Verify health endpoint reports Stage 24 and firmware_studio operational
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200
    h_data = health_res.json()
    assert h_data["stage"] >= 24
    assert h_data["subsystems"]["firmware_studio"] == "operational"

    # 2. Verify metadata and platform compatibility matrix
    meta_res = client.get("/api/v1/firmware/metadata")
    assert meta_res.status_code == 200
    meta = meta_res.json()
    assert meta["stage"] == 24
    assert meta["reuses_stage23_iot_builder"] is True
    assert len(meta["platform_matrix"]) >= 5

    plat_res = client.get("/api/v1/firmware/platforms")
    assert plat_res.status_code == 200
    platforms = plat_res.json()
    uno = next(p for p in platforms if p["board_id"] == "arduino_uno_r3")
    assert "arduino_cpp" in uno["supported_frameworks"]
    assert "micropython" in uno["unsupported_frameworks"]
    assert "2 KB SRAM" in uno["unsupported_frameworks"]["micropython"]

    # 3. Attempting to create an unsupported board + framework combination returns HTTP 400
    bad_res = client.post(
        "/api/v1/firmware/workspaces",
        json={
            "user_id": "fw_tester",
            "workspace_id": "fw_ws",
            "name": "Invalid Uno MicroPython",
            "board_id": "arduino_uno_r3",
            "framework": "micropython",
        },
    )
    assert bad_res.status_code == 400
    assert "Unsupported board/framework combination" in bad_res.json()["detail"]


def test_stage24_hardware_aware_codegen_from_stage23_and_diagnostics():
    # 1. Create a Stage 23 IoT project with ESP32 + BME280 + SSD1306 + Relay
    iot_res = client.post(
        "/api/v1/iot/projects",
        json={
            "user_id": "fw_tester",
            "workspace_id": "fw_ws",
            "name": "Stage 23 Smart Node",
            "invention_description": "ESP32 node reading BME280 and controlling relay with SSD1306 display.",
            "preferred_board_id": "esp32_devkit_v1",
            "component_ids": ["bme280_sensor", "ssd1306_oled_i2c", "relay_module_5v_optocoupled"],
            "auto_wire": True,
        },
    )
    assert iot_res.status_code == 200
    iot_proj = iot_res.json()

    # 2. Create a Stage 24 Firmware Workspace linked to the Stage 23 IoT project
    fw_res = client.post(
        "/api/v1/firmware/workspaces",
        json={
            "user_id": "fw_tester",
            "workspace_id": "fw_ws",
            "name": "ESP32 Modular C++ Firmware",
            "iot_project_id": iot_proj["project_id"],
            "board_id": "esp32_devkit_v1",
            "framework": "arduino_cpp",
        },
    )
    assert fw_res.status_code == 200
    ws = fw_res.json()
    fw_id = ws["fw_project_id"]
    assert ws["iot_project_id"] == iot_proj["project_id"]

    file_paths = {f["path"] for f in ws["files"]}
    assert {
        "include/pin_config.h",
        "include/secrets.example.h",
        "include/peripheral_drivers.h",
        "src/peripheral_drivers.cpp",
        "src/main.cpp",
        "platformio.ini",
        "test/test_embedded_logic.py",
    }.issubset(file_paths)

    pin_header = next(f["content"] for f in ws["files"] if f["path"] == "include/pin_config.h")
    assert "PIN_BOSCH_BME280" in pin_header
    assert "= 21;" in pin_header
    assert "= 23;" in pin_header

    # Initial generated scaffold passes static quality gate and unit tests
    assert ws["quality_report"]["passed_quality_gate"] is True
    assert ws["quality_report"]["unit_tests_executed"] is True
    assert ws["quality_report"]["unit_tests_passed"] is True
    assert ws["quality_report"]["hil_status"] == "SKIPPED_NO_HIL_EQUIPMENT"

    # 3. Introduce invalid GPIO (PIN_BAD_GPIO = 99), input-only pin output misuse (PIN_RELAY_OUT = 34),
    #    and undeclared third-party library (#include <FastLED.h>) to verify Hardware-Aware Diagnostics
    main_cpp = next(f["content"] for f in ws["files"] if f["path"] == "src/main.cpp")
    corrupted_hw_cpp = (
        "#include <FastLED.h>\n"
        "constexpr int PIN_RELAY_OUT = 34;\n"
        "constexpr int PIN_BAD_GPIO = 99;\n"
        + main_cpp
    )
    upd_res = client.put(
        f"/api/v1/firmware/workspaces/{fw_id}/files",
        json={
            "user_id": "fw_tester",
            "workspace_id": "fw_ws",
            "file_path": "src/main.cpp",
            "content": corrupted_hw_cpp,
            "commit_note": "Inject hardware pin and library violations",
            "create_version_snapshot": True,
        },
    )
    assert upd_res.status_code == 200
    updated_ws = upd_res.json()
    hw_categories = {d["category"] for d in updated_ws["hardware_diagnostics"]}
    assert "invalid_pin" in hw_categories
    assert "missing_library" in hw_categories


def test_stage24_static_quality_analyzer_and_compiler_honesty():
    # 1. Create an ESP32 C++ workspace and inject unsafe embedded patterns + syntax error
    fw_res = client.post(
        "/api/v1/firmware/workspaces",
        json={
            "user_id": "fw_tester",
            "workspace_id": "fw_ws",
            "name": "Quality & Compiler Check C++",
            "board_id": "esp32_devkit_v1",
            "framework": "arduino_cpp",
        },
    )
    assert fw_res.status_code == 200
    ws = fw_res.json()
    fw_id = ws["fw_project_id"]

    # First compile clean C++ source -> should report BLOCKED_TOOLCHAIN_MISSING on host without pio/arduino-cli
    clean_compile_res = client.post(
        f"/api/v1/firmware/workspaces/{fw_id}/compile",
        json={
            "user_id": "fw_tester",
            "workspace_id": "fw_ws",
            "run_unit_tests": True,
        },
    )
    assert clean_compile_res.status_code == 200
    clean_comp = clean_compile_res.json()
    assert clean_comp["status"] in ("BLOCKED_TOOLCHAIN_MISSING", "SUCCEEDED")
    if not clean_comp["toolchain_installed"]:
        assert clean_comp["status"] == "BLOCKED_TOOLCHAIN_MISSING"
        assert clean_comp["binary_artifact_produced"] is False
        assert clean_comp["compilation_genuinely_executed"] is False

    # Inject unsafe buffer handling (strcpy), blocking loop (while(1)), hardcoded secret,
    # missing watchdog feed, and a C++ syntax error (missing semicolon + unclosed brace)
    bad_cpp = """#include <Arduino.h>
const char* wifi_password = "SuperSecretPlaintextPassword123";

void setup() {
    char buf[8];
    strcpy(buf, "overflow_payload_string");
    while(1) {
        delay(8000);
    }
    int x = 42
"""
    upd_res = client.put(
        f"/api/v1/firmware/workspaces/{fw_id}/files",
        json={
            "user_id": "fw_tester",
            "workspace_id": "fw_ws",
            "file_path": "src/main.cpp",
            "content": bad_cpp,
            "commit_note": "Inject unsafe C++ patterns and syntax error",
            "create_version_snapshot": True,
        },
    )
    assert upd_res.status_code == 200
    bad_ws = upd_res.json()
    q_report = bad_ws["quality_report"]
    assert q_report["passed_quality_gate"] is False
    issue_cats = {i["category"] for i in q_report["issues"]}
    assert "unsafe_buffer_handling" in issue_cats
    assert "blocking_loop" in issue_cats
    assert "credential_exposure" in issue_cats
    assert "watchdog_issue" in issue_cats

    # Compile broken C++ -> MUST report FAILED_COMPILATION_ERROR with line numbers and suggested fixes
    err_compile_res = client.post(
        f"/api/v1/firmware/workspaces/{fw_id}/compile",
        json={
            "user_id": "fw_tester",
            "workspace_id": "fw_ws",
            "run_unit_tests": False,
        },
    )
    assert err_compile_res.status_code == 200
    err_comp = err_compile_res.json()
    assert err_comp["status"] == "FAILED_COMPILATION_ERROR"
    assert err_comp["binary_artifact_produced"] is False
    assert len(err_comp["diagnostics"]) >= 1
    assert err_comp["diagnostics"][0]["file_path"] == "src/main.cpp"
    assert err_comp["diagnostics"][0]["line_number"] >= 1
    assert err_comp["diagnostics"][0]["suggested_fix"] != ""


def test_stage24_micropython_real_bytecode_compile_version_rollback_and_export():
    # 1. Create a Raspberry Pi Pico W MicroPython workspace
    fw_res = client.post(
        "/api/v1/firmware/workspaces",
        json={
            "user_id": "fw_tester",
            "workspace_id": "fw_ws",
            "name": "Pico W MicroPython Sensor Node",
            "board_id": "raspberry_pi_pico_w",
            "framework": "micropython",
        },
    )
    assert fw_res.status_code == 200
    ws = fw_res.json()
    fw_id = ws["fw_project_id"]
    initial_version_id = ws["versions"][0]["version_id"]

    # 2. Compile clean MicroPython project -> produces real .pyc bytecode artifacts on disk
    comp_res = client.post(
        f"/api/v1/firmware/workspaces/{fw_id}/compile",
        json={
            "user_id": "fw_tester",
            "workspace_id": "fw_ws",
            "run_unit_tests": True,
        },
    )
    assert comp_res.status_code == 200
    comp = comp_res.json()
    assert comp["status"] == "SUCCEEDED"
    assert comp["compilation_genuinely_executed"] is True
    assert comp["binary_artifact_produced"] is True
    assert len(comp["produced_artifacts"]) >= 3
    assert all(a["relative_path"].endswith(".pyc") for a in comp["produced_artifacts"])

    # 3. Export artifacts -> verifies real source files + real .pyc files + RELEASE_NOTES.md exist on disk
    exp_res = client.post(
        f"/api/v1/firmware/workspaces/{fw_id}/export",
        params={"user_id": "fw_tester", "workspace_id": "fw_ws"},
    )
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert exp_data["only_real_artifacts_exported"] is True
    assert exp_data["compiled_binaries_included"] is True
    export_dir = Path(exp_data["export_directory"])
    assert export_dir.exists()
    assert (export_dir / "main.py").exists()
    assert (export_dir / "RELEASE_NOTES.md").exists()

    # 4. Code search across workspace files
    search_res = client.get(
        f"/api/v1/firmware/workspaces/{fw_id}/search",
        params={"query": "feed_watchdog", "user_id": "fw_tester", "workspace_id": "fw_ws"},
    )
    assert search_res.status_code == 200
    hits = search_res.json()
    assert len(hits) >= 1

    # 5. Break main.py with a Python SyntaxError, verify compilation fails, then rollback to v1.0.0
    client.put(
        f"/api/v1/firmware/workspaces/{fw_id}/files",
        json={
            "user_id": "fw_tester",
            "workspace_id": "fw_ws",
            "file_path": "main.py",
            "content": "def broken_syntax(\n    print('missing colon and paren')\n",
            "commit_note": "Broken Python syntax",
            "create_version_snapshot": True,
        },
    )
    bad_comp = client.post(
        f"/api/v1/firmware/workspaces/{fw_id}/compile",
        json={"user_id": "fw_tester", "workspace_id": "fw_ws"},
    ).json()
    assert bad_comp["status"] == "FAILED_COMPILATION_ERROR"
    assert bad_comp["binary_artifact_produced"] is False

    restore_res = client.post(
        f"/api/v1/firmware/workspaces/{fw_id}/restore-version",
        json={
            "user_id": "fw_tester",
            "workspace_id": "fw_ws",
            "version_id": initial_version_id,
        },
    )
    assert restore_res.status_code == 200
    restored_ws = restore_res.json()
    assert restored_ws["semver"] == "1.0.0"


def test_stage24_serial_monitor_approval_gate_permissions_and_tool():
    fw_res = client.post(
        "/api/v1/firmware/workspaces",
        json={
            "user_id": "owner_user",
            "workspace_id": "owner_ws",
            "name": "Serial & Approval Gate Test",
            "board_id": "esp32_devkit_v1",
            "framework": "micropython",
        },
    )
    assert fw_res.status_code == 200
    fw_id = fw_res.json()["fw_project_id"]

    # 1. Cross-tenant access must return HTTP 403
    forbidden_res = client.get(
        f"/api/v1/firmware/workspaces/{fw_id}",
        params={"user_id": "intruder_user", "workspace_id": "owner_ws"},
    )
    assert forbidden_res.status_code == 403

    # 2. Simulated serial monitor returns clearly labeled simulated logs
    sim_serial_res = client.post(
        f"/api/v1/firmware/workspaces/{fw_id}/serial",
        json={
            "user_id": "owner_user",
            "workspace_id": "owner_ws",
            "mode": "simulated_virtual_serial",
            "simulate_reset_event": "WDT_RESET",
            "lines_count": 6,
        },
    )
    assert sim_serial_res.status_code == 200
    serial_data = sim_serial_res.json()
    assert serial_data["is_simulated"] is True
    assert serial_data["source_mode"] == "simulated_virtual_serial"
    assert "SIMULATED SERIAL MONITOR" in serial_data["distinction_banner"]
    assert len(serial_data["logs"]) == 6

    # Requesting physical serial mode when no device is attached returns HTTP 400
    phys_serial_res = client.post(
        f"/api/v1/firmware/workspaces/{fw_id}/serial",
        json={
            "user_id": "owner_user",
            "workspace_id": "owner_ws",
            "mode": "physical_authorized_serial",
        },
    )
    assert phys_serial_res.status_code == 400

    # 3. Flashing physical device requires explicit user approval
    act_res = client.post(
        f"/api/v1/firmware/workspaces/{fw_id}/device-action",
        json={
            "user_id": "owner_user",
            "workspace_id": "owner_ws",
            "action_type": "flash_firmware",
            "target_port": "COM3",
            "confirmed": False,
        },
    )
    assert act_res.status_code == 200
    act_data = act_res.json()
    assert act_data["status"] == "WAITING_FOR_APPROVAL"
    assert act_data["requires_approval"] is True
    action_id = act_data["action_id"]

    # Approving when no physical hardware is connected honestly reports BLOCKED_NO_PHYSICAL_DEVICE
    app_res = client.post(
        f"/api/v1/firmware/device-actions/{action_id}/approve",
        json={
            "user_id": "owner_user",
            "workspace_id": "owner_ws",
            "approved": True,
        },
    )
    assert app_res.status_code == 200
    app_data = app_res.json()
    assert app_data["status"] == "BLOCKED_NO_PHYSICAL_DEVICE"
    assert "never fabricates hardware flashing results" in app_data["message"]

    # 4. Verify ToolRegistry integration for `embedded_firmware_studio`
    tool_res = asyncio.run(
        tool_registry.execute(
            "embedded_firmware_studio",
            {"action": "list_platforms", "user_id": "owner_user", "workspace_id": "owner_ws"},
        )
    )
    assert tool_res["success"] is True
    assert tool_res["data"]["total_boards"] >= 5
