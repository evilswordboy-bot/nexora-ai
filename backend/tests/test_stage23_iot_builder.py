from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.tools_registry import tool_registry

client = TestClient(app)


def test_stage23_board_and_component_catalog_and_metadata():
    # 1. Verify health endpoint reports Stage 23 and iot_project_builder operational
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200
    h_data = health_res.json()
    assert h_data["stage"] >= 23
    assert h_data["subsystems"]["iot_project_builder"] == "operational"

    # 2. Verify metadata endpoint
    meta_res = client.get("/api/v1/iot/metadata")
    assert meta_res.status_code == 200
    meta = meta_res.json()
    assert meta["stage"] == 23
    assert meta["boards_count"] >= 5
    assert meta["components_count"] >= 10
    assert "arduino_cpp" in meta["supported_languages"]
    assert "micropython" in meta["supported_languages"]

    # 3. Verify board profiles (ESP32, Arduino Uno, STM32, Pico W, Raspberry Pi 4B)
    boards_res = client.get("/api/v1/iot/boards")
    assert boards_res.status_code == 200
    boards = boards_res.json()
    board_ids = {b["board_id"] for b in boards}
    assert {
        "esp32_devkit_v1",
        "arduino_uno_r3",
        "stm32_nucleo_f401re",
        "raspberry_pi_pico_w",
        "raspberry_pi_4b",
    }.issubset(board_ids)

    esp32 = next(b for b in boards if b["board_id"] == "esp32_devkit_v1")
    assert esp32["io_logic_voltage_v"] == 3.3
    assert esp32["five_volt_tolerant_pins"] is False
    assert len(esp32["compatibility_warnings"]) >= 2

    # 4. Verify component filtering
    sensors_res = client.get("/api/v1/iot/components", params={"category": "sensor"})
    assert sensors_res.status_code == 200
    sensors = sensors_res.json()
    assert len(sensors) >= 4
    assert all(s["category"] == "sensor" for s in sensors)

    i2c_res = client.get("/api/v1/iot/components", params={"interface": "I2C", "query": "bme280"})
    assert i2c_res.status_code == 200
    i2c_items = i2c_res.json()
    assert len(i2c_items) == 1
    assert i2c_items[0]["component_id"] == "bme280_sensor"
    assert i2c_items[0]["spec_verification_status"] == "verified_datasheet_spec"


def test_stage23_project_creation_auto_wiring_and_bom_documentation():
    create_payload = {
        "user_id": "iot_engineer_1",
        "workspace_id": "ws_iot_alpha",
        "name": "Automated Precision Hydroponics Controller",
        "invention_description": (
            "ESP32 controller monitoring ambient temperature/humidity via BME280 and soil moisture, "
            "displaying live metrics on an SSD1306 OLED screen, and activating a 5V optocoupled relay."
        ),
        "target_budget_usd": 40.0,
        "power_source": "usb_5v",
        "environment": "greenhouse_humid",
        "preferred_board_id": "esp32_devkit_v1",
        "component_ids": [
            "bme280_sensor",
            "soil_moisture_capacitive",
            "ssd1306_oled_i2c",
            "relay_module_5v_optocoupled",
        ],
        "firmware_language": "arduino_cpp",
        "connectivity_protocol": "wifi_mqtt",
        "auto_wire": True,
    }
    res = client.post("/api/v1/iot/projects", json=create_payload)
    assert res.status_code == 200
    proj = res.json()
    assert proj["board_id"] == "esp32_devkit_v1"
    assert len(proj["placed_components"]) == 4
    assert len(proj["wires"]) >= 12
    assert proj["wiring_report"]["valid"] is True
    assert proj["wiring_report"]["critical_count"] == 0
    assert proj["wiring_report"]["error_count"] == 0
    assert "<svg" in proj["wiring_report"]["svg_diagram"]
    assert "Wiring Netlist" in proj["wiring_report"]["markdown_pinout_table"]

    # Check BOM & Build Documentation
    docs = proj["build_docs"]
    assert len(docs["bom_items"]) >= 5
    assert docs["total_cost_min_usd"] > 0
    assert docs["within_budget"] is True
    statuses = {item["spec_verification_status"] for item in docs["bom_items"]}
    assert "verified_datasheet_spec" in statuses
    assert "estimated_typical_range" in statuses
    assert len(docs["wiring_steps"]) >= 10
    assert len(docs["test_procedures"]) >= 3

    # Verify tool registry integration
    tool_def = tool_registry.get_tool("iot_project_builder")
    assert tool_def is not None
    assert tool_def.stage_introduced == 23


def test_stage23_invalid_connections_electrical_conflicts_and_safety_hazards():
    # Create project on ESP32 (3.3V non-5V-tolerant)
    create_res = client.post(
        "/api/v1/iot/projects",
        json={
            "user_id": "iot_safety_tester",
            "workspace_id": "ws_safety",
            "name": "Faulty Prototype Fixture",
            "invention_description": "Test fixture for wiring validation and hazard detection",
            "preferred_board_id": "esp32_devkit_v1",
            "component_ids": ["hc_sr04_ultrasonic", "dc_motor_6v", "relay_mains_ac_240v", "lipo_18650_2s_pack"],
            "auto_wire": False,
        },
    )
    assert create_res.status_code == 200
    proj = create_res.json()
    project_id = proj["project_id"]
    placed = proj["placed_components"]
    comp_by_type = {c["component_id"]: c["instance_id"] for c in placed}

    # Construct deliberate electrical faults:
    # 1. Direct 3V3 to GND short circuit on board
    # 2. Reverse polarity on HC-SR04 (VCC connected to GND_1)
    # 3. 5V ECHO output connected directly to non-5V-tolerant 3.3V GPIO27 without level shifter
    # 4. Input-only pin GPIO34 attempting to drive HC-SR04 TRIG input
    # 5. Bare inductive DC motor connected directly to GPIO25
    # 6. Pin conflict on GPIO27 (both ECHO and Mains Relay IN connected to GPIO27)
    faulty_wires = [
        {
            "wire_id": "w_short",
            "from_node_id": "board",
            "from_pin": "3V3",
            "to_node_id": "board",
            "to_pin": "GND_1",
            "signal_type": "POWER",
            "wire_color": "#ef4444",
            "label": "Short 3V3 to GND",
            "voltage_v": 3.3,
        },
        {
            "wire_id": "w_rev_pol",
            "from_node_id": "board",
            "from_pin": "GND_1",
            "to_node_id": comp_by_type["hc_sr04_ultrasonic"],
            "to_pin": "VCC",
            "signal_type": "POWER",
            "wire_color": "#ef4444",
            "label": "Reverse polarity VCC->GND",
            "voltage_v": 0.0,
        },
        {
            "wire_id": "w_5v_echo",
            "from_node_id": "board",
            "from_pin": "GPIO27",
            "to_node_id": comp_by_type["hc_sr04_ultrasonic"],
            "to_pin": "ECHO",
            "signal_type": "DIGITAL",
            "wire_color": "#2dd4bf",
            "label": "5V ECHO to 3.3V GPIO27",
            "voltage_v": 5.0,
        },
        {
            "wire_id": "w_in_only",
            "from_node_id": "board",
            "from_pin": "GPIO34",
            "to_node_id": comp_by_type["hc_sr04_ultrasonic"],
            "to_pin": "TRIG",
            "signal_type": "DIGITAL",
            "wire_color": "#38bdf8",
            "label": "Input-only GPIO34 to TRIG",
            "voltage_v": 3.3,
        },
        {
            "wire_id": "w_direct_motor",
            "from_node_id": "board",
            "from_pin": "GPIO25",
            "to_node_id": comp_by_type["dc_motor_6v"],
            "to_pin": "MOTOR_POS",
            "signal_type": "MOTOR_COIL",
            "wire_color": "#f43f5e",
            "label": "Direct motor on GPIO25",
            "voltage_v": 5.0,
        },
        {
            "wire_id": "w_conflict",
            "from_node_id": "board",
            "from_pin": "GPIO27",
            "to_node_id": comp_by_type["relay_mains_ac_240v"],
            "to_pin": "IN",
            "signal_type": "DIGITAL",
            "wire_color": "#a855f7",
            "label": "Conflicting signal on GPIO27",
            "voltage_v": 3.3,
        },
    ]

    upd_res = client.put(
        f"/api/v1/iot/projects/{project_id}/wiring",
        json={
            "user_id": "iot_safety_tester",
            "workspace_id": "ws_safety",
            "placed_components": placed,
            "wires": faulty_wires,
            "auto_regenerate_firmware": True,
        },
    )
    assert upd_res.status_code == 200
    updated = upd_res.json()
    report = updated["wiring_report"]
    assert report["valid"] is False
    assert report["critical_count"] >= 3
    assert report["error_count"] >= 3

    issue_codes = {i["code"] for i in report["issues"]}
    assert "SHORT_CIRCUIT_POWER_GND" in issue_codes
    assert "REVERSE_POLARITY" in issue_codes
    assert "VOLTAGE_MISMATCH_5V_TO_3V3" in issue_codes
    assert "INPUT_ONLY_PIN_OUTPUT_DRIVE" in issue_codes
    assert "DIRECT_MOTOR_ON_GPIO" in issue_codes
    assert "PIN_CONFLICT" in issue_codes
    assert "MISSING_PIN_CONNECTION" in issue_codes

    # Verify Safety Report flags Mains AC, High-Current Battery, and Missing Motor Driver
    safety = updated["safety_report"]
    assert safety["passed_nominal_checks"] is False
    assert safety["requires_qualified_electrical_review"] is True
    assert safety["mains_voltage_detected"] is True
    assert safety["high_current_battery_detected"] is True
    assert safety["inductive_load_without_driver"] is True
    assert "NEVER proof of physical electrical safety" in safety["physical_safety_disclaimer"]


def test_stage23_firmware_generation_compiler_checks_and_missing_dependencies():
    create_res = client.post(
        "/api/v1/iot/projects",
        json={
            "user_id": "iot_fw_user",
            "workspace_id": "ws_fw",
            "name": "Pico W MicroPython Sensor Node",
            "invention_description": "Raspberry Pi Pico W reading BME280 sensor over I2C",
            "preferred_board_id": "raspberry_pi_pico_w",
            "component_ids": ["bme280_sensor", "ssd1306_oled_i2c"],
            "firmware_language": "micropython",
            "auto_wire": True,
        },
    )
    assert create_res.status_code == 200
    proj = create_res.json()
    project_id = proj["project_id"]

    # 1. MicroPython syntax & bytecode compilation is genuinely tested via Python AST + py_compile
    fw = proj["firmware"]
    assert fw["language"] == "micropython"
    assert fw["compilation_tested"] is True
    assert fw["compilation_passed"] is True
    assert fw["verification_mode"] == "python_ast_and_py_compile"
    assert "YOUR_WIFI_PASSWORD" not in fw["source_code"]  # Secrets kept out of main source code

    # 2. Broken custom MicroPython syntax is caught by real AST/py_compile verifier
    bad_fw_res = client.post(
        f"/api/v1/iot/projects/{project_id}/firmware",
        json={
            "user_id": "iot_fw_user",
            "workspace_id": "ws_fw",
            "language": "micropython",
            "custom_source_code": "def broken_function(\n    print('unclosed syntax'",
            "run_compiler_check": True,
        },
    )
    assert bad_fw_res.status_code == 200
    bad_fw = bad_fw_res.json()["firmware"]
    assert bad_fw["compilation_tested"] is True
    assert bad_fw["compilation_passed"] is False
    assert "Syntax" in bad_fw["compiler_output"]

    # 3. Arduino C++ firmware honestly reports toolchain status without fabricating binary compilation
    cpp_fw_res = client.post(
        f"/api/v1/iot/projects/{project_id}/firmware",
        json={
            "user_id": "iot_fw_user",
            "workspace_id": "ws_fw",
            "language": "arduino_cpp",
            "run_compiler_check": True,
        },
    )
    assert cpp_fw_res.status_code == 200
    cpp_fw = cpp_fw_res.json()["firmware"]
    assert cpp_fw["language"] == "arduino_cpp"
    assert cpp_fw["compilation_tested"] is False
    assert cpp_fw["compilation_passed"] is None
    assert cpp_fw["verification_mode"] == "static_structural_check_toolchain_not_installed"
    assert len(cpp_fw["missing_dependencies"]) >= 1


def test_stage23_deterministic_simulation_project_export_and_workspace_permissions():
    create_res = client.post(
        "/api/v1/iot/projects",
        json={
            "user_id": "owner_user",
            "workspace_id": "ws_secure_iot",
            "name": "Industrial Cold-Chain Monitor",
            "invention_description": "ESP32 node monitoring cold-chain temperature and triggering alarm relay",
            "preferred_board_id": "esp32_devkit_v1",
            "component_ids": ["bme280_sensor", "relay_module_5v_optocoupled"],
            "auto_wire": True,
        },
    )
    assert create_res.status_code == 200
    project_id = create_res.json()["project_id"]

    # 1. Run deterministic virtual simulation with fault injection
    sim_res = client.post(
        f"/api/v1/iot/projects/{project_id}/simulate",
        json={
            "user_id": "owner_user",
            "workspace_id": "ws_secure_iot",
            "ticks": 5,
            "stimuli": [
                {"instance_id": "comp_1", "parameter": "temperature_c", "unit": "C", "values": [18.0, 24.0, 31.0, 35.0, 38.0]},
                {"instance_id": "comp_1", "parameter": "soil_moisture_pct", "unit": "%", "values": [50.0, 45.0, 38.0, 30.0, 25.0]},
            ],
            "inject_fault": "overtemperature",
        },
    )
    assert sim_res.status_code == 200
    sim = sim_res.json()
    assert sim["execution_environment"] == "deterministic_virtual_simulation"
    assert sim["is_physical_hardware_execution"] is False
    assert sim["ticks_executed"] == 5
    assert len(sim["ticks"]) == 5
    assert any("Overtemperature" in a for a in sim["ticks"][0]["alerts"])

    # 2. Export versioned project bundle (v1.0.0 -> v1.0.1 on second export)
    exp1_res = client.post(
        f"/api/v1/iot/projects/{project_id}/export",
        json={
            "user_id": "owner_user",
            "workspace_id": "ws_secure_iot",
            "bump_version": "patch",
            "write_to_workspace_files": True,
        },
    )
    assert exp1_res.status_code == 200
    exp1 = exp1_res.json()
    assert exp1["version"] == "1.0.0"
    rel_paths = {f["relative_path"] for f in exp1["files"]}
    assert {
        "firmware/main.ino",
        "firmware/secrets.example.h",
        "wiring/netlist.json",
        "wiring/pinout_table.md",
        "wiring/diagram.svg",
        "bom/bom.csv",
        "bom/bom.json",
        "docs/BUILD_AND_SAFETY_GUIDE.md",
        "project_manifest.json",
    }.issubset(rel_paths)

    exp2_res = client.post(
        f"/api/v1/iot/projects/{project_id}/export",
        json={
            "user_id": "owner_user",
            "workspace_id": "ws_secure_iot",
            "bump_version": "patch",
            "write_to_workspace_files": True,
        },
    )
    assert exp2_res.status_code == 200
    assert exp2_res.json()["version"] == "1.0.1"

    # 3. Verify strict workspace & user permission boundaries (403 Forbidden)
    unauth_get = client.get(
        f"/api/v1/iot/projects/{project_id}",
        params={"user_id": "intruder_user", "workspace_id": "ws_secure_iot"},
    )
    assert unauth_get.status_code == 403

    unauth_export = client.post(
        f"/api/v1/iot/projects/{project_id}/export",
        json={"user_id": "owner_user", "workspace_id": "wrong_workspace"},
    )
    assert unauth_export.status_code == 403

    missing_get = client.get(
        "/api/v1/iot/projects/iot_nonexistent_999",
        params={"user_id": "owner_user", "workspace_id": "ws_secure_iot"},
    )
    assert missing_get.status_code == 404
