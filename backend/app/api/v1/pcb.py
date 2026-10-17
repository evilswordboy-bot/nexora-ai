from __future__ import annotations

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import (
    PCBBoard,
    PCBFootprintDef,
    PCBProject,
    SchematicToPCBRequest,
    SchematicToPCBResponse,
    PCBDrcReport,
    TraceWidthRequest,
    TraceWidthResult,
    ImpedanceRequest,
    ImpedanceResult,
    PCBBOMItem,
    PCBCostEstimateRequest,
    PCBCostEstimateResult,
    PCBExportRequest,
    PCBExportResponse,
    PCBOverviewResponse,
)
from app.services.pcb_studio import (
    get_pcb_engine,
    list_available_footprints,
    convert_schematic_to_pcb,
    run_design_rule_check,
    calculate_ratsnest,
    calculate_routing_summary,
    assisted_route_path,
    calculate_trace_width,
    calculate_microstrip_impedance,
    extract_pcb_bom,
    estimate_prototype_cost,
    export_pcb_package,
)
from app.services.schematic_studio import schematic_studio_engine

router = APIRouter(prefix="/pcb", tags=["PCB Layout & Design Studio"])


@router.get("/overview", response_model=PCBOverviewResponse)
def get_pcb_overview(user_id: str = Query("default_user")):
    """Returns overview statistics of PCB projects and library availability."""
    engine = get_pcb_engine()
    return engine.get_overview(user_id=user_id)


@router.get("/footprints", response_model=List[PCBFootprintDef])
def get_footprints():
    """Returns all verified standard SMD and Through-Hole footprints in the catalog."""
    return list_available_footprints()


@router.post("/convert-schematic", response_model=SchematicToPCBResponse)
def convert_schematic(req: SchematicToPCBRequest):
    """
    Converts a validated schematic project/sheet into a PCB project layout.
    Preserves component references, values, and net connectivity.
    Never silently substitutes unknown footprints.
    """
    sheet = req.schematic_sheet
    if not sheet and req.schematic_project_id:
        sch_project = schematic_studio_engine.get_project(req.schematic_project_id)
        if not sch_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schematic project '{req.schematic_project_id}' not found",
            )
        sheet = sch_project.sheet

    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either schematic_project_id or schematic_sheet must be provided",
        )

    return convert_schematic_to_pcb(
        sheet=sheet,
        board_width_mm=req.board_width_mm or 100.0,
        board_height_mm=req.board_height_mm or 80.0,
        layer_count=req.layer_count or 2,
        custom_footprint_overrides=req.custom_footprint_overrides,
        board_title=sheet.title if hasattr(sheet, "title") else "Converted Board",
    )


@router.get("/projects", response_model=List[PCBProject])
def list_pcb_projects(user_id: str = Query("default_user")):
    """Lists all PCB projects for the user."""
    engine = get_pcb_engine()
    return engine.list_projects(user_id=user_id)


@router.post("/projects", response_model=PCBProject)
def save_pcb_project(
    project: PCBProject,
    version_bump: bool = Query(False),
    notes: str = Query(""),
):
    """Creates or updates a PCB project layout and records a version snapshot."""
    engine = get_pcb_engine()
    return engine.save_project(project, version_bump=version_bump, notes=notes)


@router.get("/projects/{project_id}", response_model=PCBProject)
def get_pcb_project(project_id: str):
    """Retrieves a specific PCB project by ID."""
    engine = get_pcb_engine()
    project = engine.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PCB project '{project_id}' not found",
        )
    return project


@router.delete("/projects/{project_id}")
def delete_pcb_project(project_id: str):
    """Deletes a PCB project and its historical revisions."""
    engine = get_pcb_engine()
    success = engine.delete_project(project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PCB project '{project_id}' not found",
        )
    return {"success": True, "message": f"PCB project '{project_id}' deleted successfully"}


@router.get("/projects/{project_id}/revisions")
def list_pcb_revisions(project_id: str):
    """Lists revision history for a PCB project."""
    engine = get_pcb_engine()
    project = engine.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PCB project '{project_id}' not found",
        )
    return project.history_revisions


@router.post("/projects/{project_id}/rollback", response_model=PCBProject)
def rollback_pcb_project(project_id: str, revision_id: str = Query(...)):
    """Restores a PCB board design to a previous revision snapshot."""
    engine = get_pcb_engine()
    rolled = engine.rollback_to_revision(project_id, revision_id)
    if not rolled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failed to rollback project '{project_id}' to revision '{revision_id}'",
        )
    return rolled


@router.post("/drc", response_model=PCBDrcReport)
def run_drc(board: PCBBoard):
    """Runs geometric and electrical Design Rule Checks on the board layout."""
    return run_design_rule_check(board)


@router.post("/routing/ratsnest")
def compute_ratsnest(board: PCBBoard):
    """Computes unrouted flylines and routing completion metrics."""
    return calculate_routing_summary(board)


@router.post("/routing/assist")
def compute_assisted_route(
    start_x: float = Query(...),
    start_y: float = Query(...),
    end_x: float = Query(...),
    end_y: float = Query(...),
    mode: str = Query("45_degree"),
):
    """Generates 45-degree or orthogonal routed trace waypoints between coordinates."""
    waypoints = assisted_route_path(start_x, start_y, end_x, end_y, mode=mode)
    return {"mode": mode, "waypoints": [{"x": p[0], "y": p[1]} for p in waypoints]}


@router.post("/calculate/trace-width", response_model=TraceWidthResult)
def calculate_trace_width_endpoint(req: TraceWidthRequest):
    """IPC-2152 / IPC-2221 trace width calculator for high-current and thermal limits."""
    return calculate_trace_width(req)


@router.post("/calculate/impedance", response_model=ImpedanceResult)
def calculate_impedance_endpoint(req: ImpedanceRequest):
    """IPC-2141 microstrip controlled impedance and propagation delay calculator."""
    return calculate_microstrip_impedance(req)


@router.post("/bom", response_model=List[PCBBOMItem])
def get_bom(board: PCBBoard):
    """Extracts aggregated Bill of Materials from the PCB board."""
    return extract_pcb_bom(board)


@router.post("/cost-estimate", response_model=PCBCostEstimateResult)
def estimate_cost(req: PCBCostEstimateRequest):
    """Estimates prototype PCB fabrication and assembly cost."""
    return estimate_prototype_cost(req)


@router.post("/export", response_model=PCBExportResponse)
def export_pcb(req: PCBExportRequest):
    """Exports PCB layout in Gerber RS-274X, KiCad PCB, Excellon drill, CSV, or SVG."""
    return export_pcb_package(req.board, req.export_format)


@router.post("/diff")
def diff_boards(boards: Dict[str, PCBBoard]):
    """Diffs two board layouts (keys 'board_a' and 'board_b')."""
    if "board_a" not in boards or "board_b" not in boards:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must include 'board_a' and 'board_b'",
        )
    engine = get_pcb_engine()
    return engine.diff_board_revisions(boards["board_a"], boards["board_b"])
