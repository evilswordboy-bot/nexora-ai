from __future__ import annotations

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import (
    SchematicProject,
    SchematicProjectCreate,
    SchematicProjectUpdate,
    SchematicSheet,
    SchematicComponentDef,
    SchematicOverviewResponse,
    ERCReport,
    OhmsLawRequest,
    OhmsLawResult,
    VoltageDividerRequest,
    VoltageDividerResult,
    LEDResistorRequest,
    LEDResistorResult,
    RCTimeConstantRequest,
    RCTimeConstantResult,
    TransistorBiasRequest,
    TransistorBiasResult,
    PowerThermalRequest,
    PowerThermalResult,
    LogicExpressionRequest,
    LogicExpressionResult,
    SPICESimulationRequest,
    SPICESimulationResult,
    AICircuitPromptRequest,
    AICircuitDesignResponse,
    SchematicExportResponse,
)
from app.services.schematic_studio import (
    schematic_studio_engine,
    build_standard_component_catalog,
    calculate_ohms_law,
    calculate_voltage_divider,
    calculate_led_resistor,
    calculate_rc_time_constant,
    calculate_transistor_bias,
    calculate_power_thermal,
    calculate_logic_expression,
    run_electrical_rule_checks,
    generate_spice_netlist,
    run_spice_simulation,
)

router = APIRouter(prefix="/schematic", tags=["Electronic Circuit Schematic Studio"])


# 1. OVERVIEW & TOOLCHAINS
@router.get("/overview", response_model=SchematicOverviewResponse)
async def get_schematic_overview(
    user_id: str = Query("default_user"),
    workspace_id: str = Query("default_workspace"),
):
    try:
        return schematic_studio_engine.get_overview(user_id=user_id, workspace_id=workspace_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 2. COMPONENT CATALOG
@router.get("/catalog", response_model=Dict[str, SchematicComponentDef])
async def get_component_catalog():
    return build_standard_component_catalog()


# 3. CUSTOM COMPONENTS
@router.post("/custom-components", response_model=SchematicComponentDef, status_code=status.HTTP_201_CREATED)
async def register_custom_component(
    comp: SchematicComponentDef,
    user_id: str = Query("default_user"),
):
    try:
        return schematic_studio_engine.register_custom_component(comp, user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/custom-components", response_model=List[SchematicComponentDef])
async def list_custom_components(user_id: str = Query("default_user")):
    return schematic_studio_engine.list_custom_components(user_id=user_id)


# 4. PROJECTS CRUD
@router.get("/projects", response_model=List[SchematicProject])
async def list_projects(
    user_id: str = Query("default_user"),
    workspace_id: str = Query("default_workspace"),
):
    return schematic_studio_engine.list_projects(user_id=user_id, workspace_id=workspace_id)


@router.post("/projects", response_model=SchematicProject, status_code=status.HTTP_201_CREATED)
async def create_project(req: SchematicProjectCreate):
    try:
        return schematic_studio_engine.create_project(req)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/projects/{project_id}", response_model=SchematicProject)
async def get_project(
    project_id: str,
    user_id: str = Query("default_user"),
    workspace_id: str = Query("default_workspace"),
):
    try:
        return schematic_studio_engine.get_project(project_id, user_id=user_id, workspace_id=workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/projects/{project_id}", response_model=SchematicProject)
async def update_project(
    project_id: str,
    req: SchematicProjectUpdate,
):
    try:
        return schematic_studio_engine.update_project(project_id, req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/projects/{project_id}", status_code=status.HTTP_200_OK)
async def delete_project(
    project_id: str,
    user_id: str = Query("default_user"),
    workspace_id: str = Query("default_workspace"),
):
    deleted = schematic_studio_engine.delete_project(project_id, user_id=user_id, workspace_id=workspace_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")
    return {"status": "deleted", "project_id": project_id}


# 5. ELECTRICAL RULE CHECKS (ERC)
@router.post("/erc", response_model=ERCReport)
async def run_erc_checks(sheet: SchematicSheet):
    try:
        return run_electrical_rule_checks(sheet)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# 6. ENGINEERING CALCULATORS
@router.post("/calculators/ohms-law", response_model=OhmsLawResult)
async def ohms_law_calc(req: OhmsLawRequest):
    try:
        return calculate_ohms_law(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/calculators/voltage-divider", response_model=VoltageDividerResult)
async def voltage_divider_calc(req: VoltageDividerRequest):
    try:
        return calculate_voltage_divider(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/calculators/led-resistor", response_model=LEDResistorResult)
async def led_resistor_calc(req: LEDResistorRequest):
    try:
        return calculate_led_resistor(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/calculators/rc-filter", response_model=RCTimeConstantResult)
async def rc_filter_calc(req: RCTimeConstantRequest):
    try:
        return calculate_rc_time_constant(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/calculators/transistor-bias", response_model=TransistorBiasResult)
async def transistor_bias_calc(req: TransistorBiasRequest):
    try:
        return calculate_transistor_bias(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/calculators/power-thermal", response_model=PowerThermalResult)
async def power_thermal_calc(req: PowerThermalRequest):
    try:
        return calculate_power_thermal(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/calculators/logic-expression", response_model=LogicExpressionResult)
async def logic_expression_calc(req: LogicExpressionRequest):
    try:
        return calculate_logic_expression(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# 7. SPICE SIMULATION
@router.post("/simulation/netlist")
async def get_spice_netlist(sheet: SchematicSheet, analysis_type: str = Query("op")):
    try:
        netlist = generate_spice_netlist(sheet, analysis_type=analysis_type)
        return {"netlist": netlist, "title": sheet.title}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/simulation/run", response_model=SPICESimulationResult)
async def execute_simulation(req: SPICESimulationRequest):
    try:
        return run_spice_simulation(req)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# 8. AI CIRCUIT ASSISTANT
@router.post("/ai-assistant", response_model=AICircuitDesignResponse)
async def generate_circuit_design(req: AICircuitPromptRequest):
    try:
        return schematic_studio_engine.generate_circuit_from_prompt(req)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# 9. EXPORTS
@router.post("/export", response_model=SchematicExportResponse)
async def export_schematic_doc(
    sheet: SchematicSheet,
    export_format: str = Query(..., description="spice_netlist, kicad_netlist, bom_json, bom_csv, svg_schematic, connection_table_json"),
):
    try:
        return schematic_studio_engine.export_schematic(sheet, export_format=export_format)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
