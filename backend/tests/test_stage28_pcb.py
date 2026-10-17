import pytest
import os
import io
import zipfile
from app.models.schemas import (
    SchematicSheet,
    ComponentInstance,
    SchematicNet,
    NetPinConnection,
    PCBBoard,
    PCBComponent,
    PCBTrack,
    PCBVia,
    PCBNet,
    PCBDesignRules,
    TraceWidthRequest,
    ImpedanceRequest,
    PCBCostEstimateRequest,
)
from app.services.pcb_studio import (
    FOOTPRINT_LIBRARY,
    get_footprint_definition,
    map_schematic_footprint_alias,
    list_available_footprints,
    convert_schematic_to_pcb,
    calculate_ratsnest,
    calculate_routing_summary,
    assisted_route_path,
    run_design_rule_check,
    calculate_trace_width,
    calculate_microstrip_impedance,
    extract_pcb_bom,
    estimate_prototype_cost,
    export_pcb_package,
    get_pcb_engine,
)
from app.services.tools_registry import tool_registry


def test_footprint_library_completeness():
    """Verifies standard footprint library coverage and alias resolution."""
    required = [
        "0805", "SOD-123", "TO-92", "TO-220", "SOT-223",
        "SOIC-8", "DIP-8", "DIP-14", "Radial_Cap_D6.3mm",
        "PinHeader_1x02_P2.54mm", "MountingHole_M3"
    ]
    for fp_id in required:
        assert fp_id in FOOTPRINT_LIBRARY, f"Missing standard footprint '{fp_id}'"
        fp = get_footprint_definition(fp_id)
        assert fp is not None
        assert fp.width_mm > 0
        assert fp.height_mm > 0
        assert len(fp.pads) > 0

    # Test alias resolution
    assert map_schematic_footprint_alias("SOIC-8_3.9x4.9mm_P1.27mm") == "SOIC-8"
    assert map_schematic_footprint_alias("TO-220-3_Vertical") == "TO-220"
    assert map_schematic_footprint_alias("DIP-14_W7.62mm") == "DIP-14"
    assert map_schematic_footprint_alias("R_0805_2012Metric") == "0805"


def test_schematic_to_pcb_conversion_and_unmapped_protection():
    """Tests conversion and strict enforcement: never silently substitute unknown footprints."""
    sheet = SchematicSheet(
        sheet_id="sh_test_1",
        title="Test Converter Circuit",
        components=[
            ComponentInstance(
                instance_id="c1",
                component_id="resistor_generic",
                ref_des="R1",
                value="10k",
                pos_x=10.0,
                pos_y=10.0,
            ),
            ComponentInstance(
                instance_id="c2",
                component_id="exotic_mystery_part",
                ref_des="U99",
                value="MYSTERY_CHIP",
                pos_x=30.0,
                pos_y=30.0,
                attributes={"footprint": "BGA_UNKNOWN_100PIN"},
            ),
        ],
        nets=[
            SchematicNet(
                net_id="net_1",
                name="SIG1",
                connections=[
                    NetPinConnection(instance_id="c1", pin_id="1"),
                    NetPinConnection(instance_id="c2", pin_id="1"),
                ],
            )
        ],
    )

    resp = convert_schematic_to_pcb(sheet, board_width_mm=80.0, board_height_mm=60.0)

    # R1 was mapped to 0805
    assert resp.mapped_count == 1
    assert resp.board.components[0].ref_des == "R1"
    assert resp.board.components[0].footprint_id == "0805"

    # U99 with unmapped footprint was flagged, NOT silently substituted
    assert len(resp.unmapped_components) == 1
    assert resp.unmapped_components[0]["ref_des"] == "U99"
    assert "BGA_UNKNOWN_100PIN" in resp.unmapped_components[0]["requested_footprint"]
    assert len(resp.warnings) > 0


def test_drc_rules_and_violations():
    """Tests geometric and electrical Design Rule Checks (DRC)."""
    # 1. Clean board test
    clean_board = PCBBoard(
        board_id="brd_clean",
        width_mm=100.0,
        height_mm=80.0,
        components=[
            PCBComponent(
                component_instance_id="c1",
                ref_des="R1",
                value="10k",
                footprint_id="0805",
                pos_x_mm=30.0,
                pos_y_mm=30.0,
            )
        ],
        tracks=[
            PCBTrack(
                track_id="t1",
                net_id="NET1",
                layer="F.Cu",
                start_x_mm=20.0,
                start_y_mm=20.0,
                end_x_mm=40.0,
                end_y_mm=20.0,
                width_mm=0.30,
            )
        ],
        vias=[
            PCBVia(
                via_id="v1",
                net_id="NET1",
                x_mm=40.0,
                y_mm=20.0,
                drill_mm=0.35,
            )
        ],
        nets=[
            PCBNet(net_id="NET1", name="NET1", connections=[])
        ],
        design_rules=PCBDesignRules(min_trace_width_mm=0.25, min_drill_diameter_mm=0.30),
    )

    report_clean = run_design_rule_check(clean_board)
    assert report_clean.passed is True
    assert report_clean.critical_count == 0

    # 2. Violating board test: thin trace, small drill, edge violation, and short circuit
    bad_board = PCBBoard(
        board_id="brd_bad",
        width_mm=50.0,
        height_mm=50.0,
        components=[],
        tracks=[
            # Violation 1: Under min width (0.10mm < 0.25mm)
            PCBTrack(
                track_id="t_thin",
                net_id="NET_A",
                layer="F.Cu",
                start_x_mm=10.0,
                start_y_mm=10.0,
                end_x_mm=10.0,
                end_y_mm=30.0,
                width_mm=0.10,
            ),
            # Violation 2: Crossing track of different net -> Short Circuit
            PCBTrack(
                track_id="t_cross",
                net_id="NET_B",
                layer="F.Cu",
                start_x_mm=5.0,
                start_y_mm=20.0,
                end_x_mm=25.0,
                end_y_mm=20.0,
                width_mm=0.30,
            ),
            # Violation 3: Too close to board edge (x=0.2mm < min_edge 0.50mm)
            PCBTrack(
                track_id="t_edge",
                net_id="NET_C",
                layer="F.Cu",
                start_x_mm=0.2,
                start_y_mm=5.0,
                end_x_mm=0.2,
                end_y_mm=15.0,
                width_mm=0.30,
            ),
        ],
        vias=[
            # Violation 4: Too small drill (0.15mm < 0.30mm)
            PCBVia(
                via_id="v_small",
                net_id="NET_A",
                x_mm=10.0,
                y_mm=10.0,
                drill_mm=0.15,
            )
        ],
        design_rules=PCBDesignRules(
            min_trace_width_mm=0.25,
            min_clearance_mm=0.20,
            min_board_edge_clearance_mm=0.50,
            min_drill_diameter_mm=0.30,
        ),
    )

    report_bad = run_design_rule_check(bad_board)
    assert report_bad.passed is False
    assert report_bad.critical_count >= 3
    rule_codes = {f.rule_code for f in report_bad.findings}
    assert "DRC_MIN_TRACE_WIDTH" in rule_codes
    assert "DRC_MIN_DRILL_DIAMETER" in rule_codes
    assert "DRC_BOARD_EDGE_CLEARANCE" in rule_codes
    assert "DRC_ELECTRICAL_SHORT" in rule_codes


def test_ratsnest_and_assisted_routing():
    """Verifies ratsnest computation and 45-degree routing assistance."""
    board = PCBBoard(
        board_id="brd_route_test",
        width_mm=80.0,
        height_mm=60.0,
        components=[
            PCBComponent(
                component_instance_id="r1",
                ref_des="R1",
                value="10k",
                footprint_id="0805",
                pos_x_mm=20.0,
                pos_y_mm=20.0,
            ),
            PCBComponent(
                component_instance_id="r2",
                ref_des="R2",
                value="10k",
                footprint_id="0805",
                pos_x_mm=40.0,
                pos_y_mm=35.0,
            ),
        ],
        tracks=[],
        nets=[
            PCBNet(
                net_id="NET_A",
                name="NET_A",
                connections=[
                    {"component_instance_id": "r1", "pad_number": "1"},
                    {"component_instance_id": "r2", "pad_number": "1"},
                ],
            )
        ],
    )

    summary = calculate_routing_summary(board)
    assert summary["total_connections"] == 1
    assert summary["unrouted_connections"] == 1
    assert summary["completion_percentage"] == 0.0
    assert len(summary["ratsnest"]) == 1

    # Test assisted 45-degree route
    pts = assisted_route_path(10.0, 10.0, 30.0, 20.0, mode="45_degree")
    assert len(pts) == 3
    assert pts[0] == (10.0, 10.0)
    assert pts[2] == (30.0, 20.0)


def test_ipc_calculators():
    """Verifies IPC-2152 trace width and IPC-2141 microstrip impedance calculators."""
    # 1. Trace Width
    req_w = TraceWidthRequest(current_a=2.5, temp_rise_c=10.0, copper_thickness_oz=1.0, layer_type="external")
    res_w = calculate_trace_width(req_w)
    assert res_w.min_width_mm > 0.3
    assert res_w.cross_section_area_sq_mils > 0
    assert res_w.resistance_per_meter_ohms > 0
    assert "IPC-2152" in res_w.standard_documented_formula

    # 2. Microstrip Impedance
    req_z = ImpedanceRequest(trace_width_mm=0.35, dielectric_height_mm=1.6, copper_thickness_oz=1.0, dielectric_constant_er=4.5)
    res_z = calculate_microstrip_impedance(req_z)
    assert 50.0 <= res_z.characteristic_impedance_ohms <= 150.0
    assert res_z.propagation_delay_ps_per_mm > 0


def test_bom_and_prototype_cost_estimation():
    """Verifies BOM extraction and manufacturing cost estimator."""
    engine = get_pcb_engine()
    projects = engine.list_projects()
    assert len(projects) > 0
    sample_board = projects[0].board

    bom = extract_pcb_bom(sample_board)
    assert len(bom) >= 4
    for item in bom:
        assert item.quantity >= 1
        assert item.approx_total_cost_usd >= 0

    cost_req = PCBCostEstimateRequest(
        board_width_mm=sample_board.width_mm,
        board_height_mm=sample_board.height_mm,
        layer_count=2,
        quantity=5,
        surface_finish="HASL_lead_free",
    )
    cost_res = estimate_prototype_cost(cost_req, bom_items=bom)
    assert cost_res.estimated_pcb_fabrication_cost_usd > 0
    assert cost_res.estimated_total_prototype_cost_usd > cost_res.estimated_pcb_fabrication_cost_usd
    assert cost_res.is_formal_quote is False
    assert len(cost_res.pricing_assumptions) > 0


def test_fabrication_exports():
    """Verifies Gerber, KiCad PCB, Excellon drill, CSV, and SVG exports."""
    engine = get_pcb_engine()
    board = engine.list_projects()[0].board

    # 1. KiCad PCB
    kicad_exp = export_pcb_package(board, "kicad_pcb")
    assert "(kicad_pcb" in kicad_exp.content
    assert "(layers" in kicad_exp.content
    assert kicad_exp.filename.endswith(".kicad_pcb")

    # 2. Excellon Drill
    drill_exp = export_pcb_package(board, "excellon_drill")
    assert "M48" in drill_exp.content
    assert "METRIC" in drill_exp.content
    assert "M30" in drill_exp.content

    # 3. Pick and Place CSV
    pos_exp = export_pcb_package(board, "pick_and_place_csv")
    assert "Ref,Val,Package,PosX,PosY,Rot,Side" in pos_exp.content
    assert "R1" in pos_exp.content

    # 4. SVG
    svg_exp = export_pcb_package(board, "svg_board")
    assert "<svg" in svg_exp.content
    assert "</svg>" in svg_exp.content

    # 5. Gerber Suite (ZIP)
    gerber_exp = export_pcb_package(board, "gerber_zip")
    assert gerber_exp.export_format == "gerber_zip"
    assert gerber_exp.filename.endswith(".zip")
    assert gerber_exp.files is not None
    assert any(k.endswith(".gtl") for k in gerber_exp.files)
    assert any(k.endswith(".gbl") for k in gerber_exp.files)
    assert any(k.endswith(".gml") for k in gerber_exp.files)


@pytest.mark.asyncio
async def test_pcb_studio_engine_tool_execution():
    """Verifies Tool #29 execution through the NEXORA tool registry."""
    tool = tool_registry.get_tool("pcb_studio_engine")
    assert tool is not None
    assert tool.stage_introduced == 28

    # 1. Overview
    res_ov = await tool_registry.execute("pcb_studio_engine", {"action": "overview"})
    assert res_ov["success"] is True
    assert res_ov["data"]["stage"] == 28
    assert res_ov["data"]["footprints_count"] >= 10

    # 2. Trace width calculation
    res_calc = await tool_registry.execute(
        "pcb_studio_engine",
        {
            "action": "calculate_trace_width",
            "calc_params": {"current_a": 3.0, "temp_rise_c": 15.0},
        },
    )
    assert res_calc["success"] is True
    assert res_calc["data"]["result"]["min_width_mm"] > 0.4
    assert "IPC-2152" in res_calc["data"]["result"]["standard_documented_formula"]

    # 3. Footprints list
    res_fp = await tool_registry.execute("pcb_studio_engine", {"action": "footprints"})
    assert res_fp["success"] is True
    assert res_fp["data"]["count"] >= 10
