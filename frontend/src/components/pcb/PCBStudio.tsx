import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  Layers,
  Cpu,
  Zap,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  FileCode,
  Download,
  Copy,
  Trash2,
  RotateCw,
  RefreshCw,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Sparkles,
  Play,
  Calculator,
  Terminal,
  Grid,
  Info,
  Shield,
  Activity,
  ArrowRight,
  Eye,
  EyeOff,
  Box,
  Compass,
  Sliders,
  DollarSign,
  Package,
  Wrench,
  HelpCircle,
  Plus,
  Save,
  Clock,
  History,
  Move
} from 'lucide-react';
import { pcbApi, schematicApi } from '../../services/api';
import {
  PCBOverviewResponse,
  PCBFootprintDef,
  PCBProject,
  PCBBoard,
  PCBComponent,
  PCBTrack,
  PCBVia,
  PCBNet,
  PCBRatsnestLine,
  PCBDrcReport,
  TraceWidthRequest,
  TraceWidthResult,
  ImpedanceRequest,
  ImpedanceResult,
  PCBBOMItem,
  PCBCostEstimateRequest,
  PCBCostEstimateResult,
  PCBExportResponse,
  SchematicProject
} from '../../types';

export const PCBStudio: React.FC = () => {
  // Navigation tabs
  const [activeTab, setActiveTab] = useState<'board' | '3d' | 'drc' | 'calculators' | 'bom_cost' | 'export'>('board');
  const [activeCalc, setActiveCalc] = useState<'trace_width' | 'impedance'>('trace_width');

  // Core data states
  const [isLoading, setIsLoading] = useState(false);
  const [overview, setOverview] = useState<PCBOverviewResponse | null>(null);
  const [footprints, setFootprints] = useState<PCBFootprintDef[]>([]);
  const [projects, setProjects] = useState<PCBProject[]>([]);
  const [currentProject, setCurrentProject] = useState<PCBProject | null>(null);
  const [currentBoard, setCurrentBoard] = useState<PCBBoard | null>(null);

  // Schematic conversion modal
  const [showImportModal, setShowImportModal] = useState(false);
  const [schematicProjects, setSchematicProjects] = useState<SchematicProject[]>([]);
  const [selectedSchProjectId, setSelectedSchProjectId] = useState<string>('');
  const [importWidth, setImportWidth] = useState(100);
  const [importHeight, setImportHeight] = useState(80);
  const [conversionReport, setConversionReport] = useState<{
    mapped_count: number;
    unmapped_components: Array<Record<string, string>>;
    warnings: string[];
  } | null>(null);

  // Revisions modal
  const [showRevisionsModal, setShowRevisionsModal] = useState(false);
  const [revisions, setRevisions] = useState<Array<Record<string, any>>>([]);

  // DRC State
  const [drcReport, setDrcReport] = useState<PCBDrcReport | null>(null);
  const [isDrcRunning, setIsDrcRunning] = useState(false);

  // Routing and Ratsnest
  const [ratsnest, setRatsnest] = useState<PCBRatsnestLine[]>([]);
  const [routingStats, setRoutingStats] = useState<{
    total_connections: number;
    routed_connections: number;
    unrouted_connections: number;
    completion_percentage: number;
  }>({ total_connections: 0, routed_connections: 0, unrouted_connections: 0, completion_percentage: 100 });

  // Layer visibility
  const [visibleLayers, setVisibleLayers] = useState({
    'F.Cu': true,
    'B.Cu': true,
    'F.SilkS': true,
    'B.SilkS': false,
    'Edge.Cuts': true,
    'Ratsnest': true,
    'Vias': true,
    'Pads': true,
  });

  // Canvas editor state
  const [zoom, setZoom] = useState(4.5);
  const [pan, setPan] = useState({ x: 40, y: 30 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [gridSnap, setGridSnap] = useState(1.0); // mm
  const [activeTool, setActiveTool] = useState<'select' | 'route' | 'via' | 'component'>('select');
  const [activeLayer, setActiveLayer] = useState<'F.Cu' | 'B.Cu'>('F.Cu');
  const [activeTrackWidth, setActiveTrackWidth] = useState(0.40); // mm
  const [selectedComponentId, setSelectedComponentId] = useState<string | null>(null);
  const [draggingCompId, setDraggingCompId] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  // Route drawing in progress
  const [routeStartPad, setRouteStartPad] = useState<{ compId: string; padNum: string; x: number; y: number; netId: string } | null>(null);
  const [mouseBoardPos, setMouseBoardPos] = useState({ x: 0, y: 0 });

  // 3D Visualizer state
  const [solderMaskColor, setSolderMaskColor] = useState<'green' | 'black' | 'blue' | 'red'>('green');
  const [surfaceFinish, setSurfaceFinish] = useState<'ENIG' | 'HASL'>('ENIG');
  const [orbitRotX, setOrbitRotX] = useState(35);
  const [orbitRotY, setOrbitRotY] = useState(-25);
  const [orbitZoom, setOrbitZoom] = useState(1.0);

  // Calculators State
  const [traceCalcReq, setTraceCalcReq] = useState<TraceWidthRequest>({
    current_a: 2.0,
    temp_rise_c: 10.0,
    copper_thickness_oz: 1.0,
    layer_type: 'external',
  });
  const [traceCalcRes, setTraceCalcRes] = useState<TraceWidthResult | null>(null);

  const [impedanceCalcReq, setImpedanceCalcReq] = useState<ImpedanceRequest>({
    trace_width_mm: 0.35,
    dielectric_height_mm: 1.6,
    copper_thickness_oz: 1.0,
    dielectric_constant_er: 4.5,
  });
  const [impedanceCalcRes, setImpedanceCalcRes] = useState<ImpedanceResult | null>(null);

  // BOM & Cost Estimator State
  const [bomItems, setBomItems] = useState<PCBBOMItem[]>([]);
  const [costReq, setCostReq] = useState<PCBCostEstimateRequest>({
    board_width_mm: 80,
    board_height_mm: 55,
    layer_count: 2,
    quantity: 5,
    surface_finish: 'HASL_lead_free',
    lead_time_days: 5,
  });
  const [costRes, setCostRes] = useState<PCBCostEstimateResult | null>(null);

  // Export State
  const [exportFormat, setExportFormat] = useState<
    'gerber_zip' | 'kicad_pcb' | 'excellon_drill' | 'pick_and_place_csv' | 'bom_csv' | 'svg_board'
  >('gerber_zip');
  const [exportedData, setExportedData] = useState<PCBExportResponse | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  // Feedback banner
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  const svgCanvasRef = useRef<SVGSVGElement | null>(null);

  const showBanner = (type: 'success' | 'error' | 'info', text: string) => {
    setStatusMessage({ type, text });
    setTimeout(() => setStatusMessage(null), 5000);
  };

  // 1. Initial Data Fetch
  const loadInitialData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [ovData, fpList, prjList] = await Promise.all([
        pcbApi.getOverview(),
        pcbApi.getFootprints(),
        pcbApi.getProjects(),
      ]);
      setOverview(ovData);
      setFootprints(fpList);
      setProjects(prjList);

      if (prjList.length > 0) {
        const activePrj = prjList[0];
        setCurrentProject(activePrj);
        setCurrentBoard(activePrj.board);
        setCostReq(prev => ({
          ...prev,
          board_width_mm: activePrj.board.width_mm,
          board_height_mm: activePrj.board.height_mm,
          layer_count: activePrj.board.layer_count,
        }));
      }
    } catch (err: any) {
      showBanner('error', `Failed to load PCB Studio data: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Load schematic projects for import modal
  const loadSchematicProjects = async () => {
    try {
      const schList = await schematicApi.getProjects();
      setSchematicProjects(schList);
      if (schList.length > 0) {
        setSelectedSchProjectId(schList[0].project_id);
      }
    } catch (err) {
      console.error('Failed to load schematic projects', err);
    }
  };

  // 2. Ratsnest computation
  const refreshRatsnest = useCallback(async (board: PCBBoard) => {
    try {
      const res = await pcbApi.computeRatsnest(board);
      setRatsnest(res.ratsnest);
      setRoutingStats({
        total_connections: res.total_connections,
        routed_connections: res.routed_connections,
        unrouted_connections: res.unrouted_connections,
        completion_percentage: res.completion_percentage,
      });
    } catch (err) {
      console.error('Failed to compute ratsnest', err);
    }
  }, []);

  useEffect(() => {
    if (currentBoard) {
      refreshRatsnest(currentBoard);
    }
  }, [currentBoard, refreshRatsnest]);

  // 3. Save Project
  const handleSaveProject = async (versionBump = false) => {
    if (!currentProject || !currentBoard) return;
    setIsLoading(true);
    try {
      const updatedProject: PCBProject = {
        ...currentProject,
        board: currentBoard,
      };
      const saved = await pcbApi.saveProject(updatedProject, versionBump, `Saved from UI ${new Date().toLocaleTimeString()}`);
      setCurrentProject(saved);
      setCurrentBoard(saved.board);
      showBanner('success', `Saved project '${saved.title}' (${saved.version})`);
      const prjList = await pcbApi.getProjects();
      setProjects(prjList);
    } catch (err: any) {
      showBanner('error', `Failed to save project: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // 4. Run DRC
  const handleRunDrc = async () => {
    if (!currentBoard) return;
    setIsDrcRunning(true);
    try {
      const report = await pcbApi.runDRC(currentBoard);
      setDrcReport(report);
      if (report.passed) {
        showBanner('success', `DRC Passed! 0 critical violations, completion: ${report.routing_completion_pct}%`);
      } else {
        showBanner('error', `DRC Failed: ${report.critical_count} critical violations detected.`);
      }
    } catch (err: any) {
      showBanner('error', `DRC check failed: ${err.message}`);
    } finally {
      setIsDrcRunning(false);
    }
  };

  // 5. Convert Schematic to PCB
  const handleConvertSchematic = async () => {
    if (!selectedSchProjectId) return;
    setIsLoading(true);
    try {
      const resp = await pcbApi.convertSchematic({
        schematic_project_id: selectedSchProjectId,
        board_width_mm: importWidth,
        board_height_mm: importHeight,
        layer_count: 2,
      });

      setConversionReport({
        mapped_count: resp.mapped_count,
        unmapped_components: resp.unmapped_components,
        warnings: resp.warnings,
      });

      // Create new PCB project from converted board
      const newPrj: PCBProject = {
        project_id: `prj_pcb_${Date.now()}`,
        user_id: 'default_user',
        workspace_id: 'default_workspace',
        title: `PCB - ${resp.board.title}`,
        description: `Imported from schematic ${selectedSchProjectId}`,
        schematic_project_id: selectedSchProjectId,
        version: 'v1.0.0',
        board: resp.board,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        history_revisions: [],
      };

      const saved = await pcbApi.saveProject(newPrj, false, 'Imported from schematic');
      setCurrentProject(saved);
      setCurrentBoard(saved.board);
      setProjects(prev => [saved, ...prev]);

      showBanner(
        resp.unmapped_components.length > 0 ? 'info' : 'success',
        `Converted ${resp.mapped_count} components. ${resp.unmapped_components.length} unmapped footprints flagged.`
      );
    } catch (err: any) {
      showBanner('error', `Conversion failed: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // 6. Run Trace Width Calculation
  const handleCalcTraceWidth = async () => {
    try {
      const res = await pcbApi.calculateTraceWidth(traceCalcReq);
      setTraceCalcRes(res);
    } catch (err: any) {
      showBanner('error', `Trace calculation error: ${err.message}`);
    }
  };

  // 7. Run Impedance Calculation
  const handleCalcImpedance = async () => {
    try {
      const res = await pcbApi.calculateImpedance(impedanceCalcReq);
      setImpedanceCalcRes(res);
    } catch (err: any) {
      showBanner('error', `Impedance calculation error: ${err.message}`);
    }
  };

  // 8. Fetch BOM & Estimate Cost
  const handleFetchBomAndCost = async () => {
    if (!currentBoard) return;
    setIsLoading(true);
    try {
      const [bom, cost] = await Promise.all([
        pcbApi.getBOM(currentBoard),
        pcbApi.estimateCost({
          ...costReq,
          board_width_mm: currentBoard.width_mm,
          board_height_mm: currentBoard.height_mm,
          layer_count: currentBoard.layer_count,
        }),
      ]);
      setBomItems(bom);
      setCostRes(cost);
    } catch (err: any) {
      showBanner('error', `BOM/Cost error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // 9. Run Export
  const handleExport = async () => {
    if (!currentBoard) return;
    setIsExporting(true);
    try {
      const resp = await pcbApi.exportPcb({
        board: currentBoard,
        export_format: exportFormat,
      });
      setExportedData(resp);
      showBanner('success', `Export generated: ${resp.filename}`);
    } catch (err: any) {
      showBanner('error', `Export failed: ${err.message}`);
    } finally {
      setIsExporting(false);
    }
  };

  // 10. Footprint helper
  const getFp = useCallback((fpId: string): PCBFootprintDef | undefined => {
    return footprints.find(f => f.footprint_id === fpId);
  }, [footprints]);

  // 11. Coordinate helpers for canvas
  const screenToBoard = (clientX: number, clientY: number) => {
    if (!svgCanvasRef.current) return { x: 0, y: 0 };
    const rect = svgCanvasRef.current.getBoundingClientRect();
    const svgX = clientX - rect.left;
    const svgY = clientY - rect.top;
    const rawX = (svgX - pan.x) / zoom;
    const rawY = (svgY - pan.y) / zoom;
    // Snap to grid
    const snappedX = Math.round(rawX / gridSnap) * gridSnap;
    const snappedY = Math.round(rawY / gridSnap) * gridSnap;
    return { x: snappedX, y: snappedY };
  };

  // Component Dragging Handlers
  const handleComponentMouseDown = (e: React.MouseEvent, comp: PCBComponent) => {
    if (activeTool !== 'select') return;
    e.stopPropagation();
    setSelectedComponentId(comp.component_instance_id);
    setDraggingCompId(comp.component_instance_id);
    const bPos = screenToBoard(e.clientX, e.clientY);
    setDragOffset({
      x: bPos.x - comp.pos_x_mm,
      y: bPos.y - comp.pos_y_mm,
    });
  };

  const handleCanvasMouseMove = (e: React.MouseEvent) => {
    const bPos = screenToBoard(e.clientX, e.clientY);
    setMouseBoardPos(bPos);

    if (isPanning) {
      setPan({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y,
      });
      return;
    }

    if (draggingCompId && currentBoard) {
      const newX = Math.max(2, Math.min(currentBoard.width_mm - 2, bPos.x - dragOffset.x));
      const newY = Math.max(2, Math.min(currentBoard.height_mm - 2, bPos.y - dragOffset.y));

      setCurrentBoard(prev => {
        if (!prev) return null;
        return {
          ...prev,
          components: prev.components.map(c =>
            c.component_instance_id === draggingCompId
              ? { ...c, pos_x_mm: Math.round(newX * 10) / 10, pos_y_mm: Math.round(newY * 10) / 10 }
              : c
          ),
        };
      });
    }
  };

  const handleCanvasMouseUp = () => {
    setDraggingCompId(null);
    setIsPanning(false);
  };

  // Rotate selected component
  const handleRotateSelected = () => {
    if (!selectedComponentId || !currentBoard) return;
    setCurrentBoard(prev => {
      if (!prev) return null;
      return {
        ...prev,
        components: prev.components.map(c =>
          c.component_instance_id === selectedComponentId
            ? { ...c, rotation_deg: (c.rotation_deg + 90) % 360 }
            : c
        ),
      };
    });
  };

  // Delete selected component
  const handleDeleteSelected = () => {
    if (!selectedComponentId || !currentBoard) return;
    setCurrentBoard(prev => {
      if (!prev) return null;
      return {
        ...prev,
        components: prev.components.filter(c => c.component_instance_id !== selectedComponentId),
      };
    });
    setSelectedComponentId(null);
  };

  // Route Pad Click Handler
  const handlePadClick = (
    e: React.MouseEvent,
    comp: PCBComponent,
    padNum: string,
    absX: number,
    absY: number
  ) => {
    e.stopPropagation();

    // Find net for this pad
    let foundNet = currentBoard?.nets.find(n =>
      n.connections.some(conn => conn.component_instance_id === comp.component_instance_id && conn.pad_number === padNum)
    );

    const netId = foundNet?.net_id || 'NET_USER';

    if (activeTool === 'route') {
      if (!routeStartPad) {
        // Start route from this pad
        setRouteStartPad({ compId: comp.component_instance_id, padNum, x: absX, y: absY, netId });
        showBanner('info', `Routing net '${netId}' from ${comp.ref_des}.${padNum}. Click target pad to complete.`);
      } else {
        // Complete route to this pad
        if (routeStartPad.compId === comp.component_instance_id && routeStartPad.padNum === padNum) {
          setRouteStartPad(null);
          return;
        }

        const newTrack: PCBTrack = {
          track_id: `tr_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
          net_id: routeStartPad.netId,
          layer: activeLayer,
          start_x_mm: routeStartPad.x,
          start_y_mm: routeStartPad.y,
          end_x_mm: absX,
          end_y_mm: absY,
          width_mm: activeTrackWidth,
        };

        setCurrentBoard(prev => {
          if (!prev) return null;
          return {
            ...prev,
            tracks: [...prev.tracks, newTrack],
          };
        });

        showBanner('success', `Routed track on ${activeLayer} between ${routeStartPad.compId} and ${comp.ref_des}`);
        setRouteStartPad(null);
      }
    } else {
      setSelectedComponentId(comp.component_instance_id);
    }
  };

  // Add Via at mouse position
  const handleAddVia = () => {
    if (!currentBoard) return;
    const newVia: PCBVia = {
      via_id: `via_${Date.now()}`,
      net_id: 'GND',
      x_mm: mouseBoardPos.x,
      y_mm: mouseBoardPos.y,
      diameter_mm: 0.6,
      drill_mm: 0.3,
      start_layer: 'F.Cu',
      end_layer: 'B.Cu',
    };

    setCurrentBoard(prev => {
      if (!prev) return null;
      return {
        ...prev,
        vias: [...prev.vias, newVia],
      };
    });
    showBanner('success', `Added via at (${mouseBoardPos.x}, ${mouseBoardPos.y})`);
  };

  // Selected Component info
  const selectedComponent = useMemo(() => {
    if (!selectedComponentId || !currentBoard) return null;
    return currentBoard.components.find(c => c.component_instance_id === selectedComponentId);
  }, [selectedComponentId, currentBoard]);

  return (
    <div className="flex flex-col h-full bg-[#0a0f1d] text-slate-200 select-none overflow-hidden font-sans">
      {/* Top Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-[#0e1628] border-b border-cyan-900/40">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-wider text-white text-sm">NEXORA PCB STUDIO</span>
              <span className="text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/60 font-mono">
                STAGE 28
              </span>
              <span className="text-xs text-slate-400 font-mono">
                {currentProject?.title || 'No Project'} ({currentProject?.version || 'v1.0.0'})
              </span>
            </div>
            <div className="text-[11px] text-slate-400">
              EDA Layout Canvas • Multilayer Routing • IPC-2152 DRC • 3D Orbital Preview • Gerber/KiCad Export
            </div>
          </div>
        </div>

        {/* Global Action Controls */}
        <div className="flex items-center gap-2">
          {/* Schematic Import Button */}
          <button
            onClick={() => {
              loadSchematicProjects();
              setShowImportModal(true);
            }}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
            title="Import and convert schematic to PCB layout"
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>Import Schematic</span>
          </button>

          {/* Revisions history */}
          <button
            onClick={async () => {
              if (currentProject) {
                const revs = await pcbApi.getRevisions(currentProject.project_id);
                setRevisions(revs);
                setShowRevisionsModal(true);
              }
            }}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
            title="View revision snapshots and rollback"
          >
            <History className="w-3.5 h-3.5 text-amber-400" />
            <span>Revisions</span>
          </button>

          {/* Run DRC quick button */}
          <button
            onClick={handleRunDrc}
            disabled={isDrcRunning}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
              drcReport && !drcReport.passed
                ? 'bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-800'
                : 'bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-800'
            }`}
          >
            <Shield className="w-3.5 h-3.5" />
            <span>{isDrcRunning ? 'Checking...' : drcReport ? (drcReport.passed ? 'DRC: Passed' : `DRC: ${drcReport.critical_count} Violations`) : 'Check DRC'}</span>
          </button>

          {/* Save Button */}
          <button
            onClick={() => handleSaveProject(false)}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-900/30 transition-colors"
          >
            <Save className="w-3.5 h-3.5" />
            <span>Save Board</span>
          </button>
        </div>
      </div>

      {/* Sub-Header Tabs */}
      <div className="flex items-center justify-between px-4 bg-[#090e1c] border-b border-slate-800 text-xs">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab('board')}
            className={`px-3 py-2 border-b-2 font-medium flex items-center gap-2 transition-colors ${
              activeTab === 'board'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Grid className="w-4 h-4" />
            <span>Board Editor</span>
          </button>
          <button
            onClick={() => setActiveTab('3d')}
            className={`px-3 py-2 border-b-2 font-medium flex items-center gap-2 transition-colors ${
              activeTab === '3d'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Box className="w-4 h-4 text-purple-400" />
            <span>3D Orbit View</span>
          </button>
          <button
            onClick={() => setActiveTab('drc')}
            className={`px-3 py-2 border-b-2 font-medium flex items-center gap-2 transition-colors ${
              activeTab === 'drc'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Shield className="w-4 h-4 text-rose-400" />
            <span>Design Rule Check (DRC)</span>
            {drcReport && drcReport.critical_count > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-rose-900 text-rose-200 font-bold">
                {drcReport.critical_count}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('calculators')}
            className={`px-3 py-2 border-b-2 font-medium flex items-center gap-2 transition-colors ${
              activeTab === 'calculators'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Calculator className="w-4 h-4 text-amber-400" />
            <span>IPC Constraints & Calculators</span>
          </button>
          <button
            onClick={() => {
              setActiveTab('bom_cost');
              handleFetchBomAndCost();
            }}
            className={`px-3 py-2 border-b-2 font-medium flex items-center gap-2 transition-colors ${
              activeTab === 'bom_cost'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <DollarSign className="w-4 h-4 text-emerald-400" />
            <span>BOM & Prototype Cost</span>
          </button>
          <button
            onClick={() => setActiveTab('export')}
            className={`px-3 py-2 border-b-2 font-medium flex items-center gap-2 transition-colors ${
              activeTab === 'export'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Download className="w-4 h-4 text-blue-400" />
            <span>Fabrication Exports (Gerber/KiCad)</span>
          </button>
        </div>

        {/* Quick routing status */}
        <div className="flex items-center gap-3 text-[11px] text-slate-400">
          <span>Routing: <strong className="text-cyan-400">{routingStats.completion_percentage}%</strong></span>
          <span>Flylines: <strong className="text-amber-400">{routingStats.unrouted_connections}</strong></span>
          <span>Layers: <strong className="text-slate-300">{currentBoard?.layer_count || 2}L</strong></span>
          <span>Size: <strong className="text-slate-300">{currentBoard?.width_mm || 0}×{currentBoard?.height_mm || 0}mm</strong></span>
        </div>
      </div>

      {/* Status banner */}
      {statusMessage && (
        <div
          className={`px-4 py-2 text-xs flex items-center justify-between ${
            statusMessage.type === 'success'
              ? 'bg-emerald-950/90 text-emerald-300 border-b border-emerald-800'
              : statusMessage.type === 'error'
              ? 'bg-rose-950/90 text-rose-300 border-b border-rose-800'
              : 'bg-cyan-950/90 text-cyan-300 border-b border-cyan-800'
          }`}
        >
          <div className="flex items-center gap-2">
            {statusMessage.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4" />
            ) : statusMessage.type === 'error' ? (
              <AlertCircle className="w-4 h-4" />
            ) : (
              <Info className="w-4 h-4" />
            )}
            <span>{statusMessage.text}</span>
          </div>
          <button onClick={() => setStatusMessage(null)} className="text-xs hover:text-white">✕</button>
        </div>
      )}

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden">
        {activeTab === 'board' && (
          <>
            {/* Left Layer & Tool Panel */}
            <div className="w-64 bg-[#0d1424] border-r border-slate-800 flex flex-col justify-between p-3 overflow-y-auto">
              <div className="space-y-4">
                {/* Active Tool Selector */}
                <div>
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Editor Tools</div>
                  <div className="grid grid-cols-2 gap-1.5">
                    <button
                      onClick={() => { setActiveTool('select'); setRouteStartPad(null); }}
                      className={`flex items-center gap-2 px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${
                        activeTool === 'select'
                          ? 'bg-cyan-600 text-white'
                          : 'bg-slate-800/80 hover:bg-slate-700 text-slate-300'
                      }`}
                    >
                      <Move className="w-3.5 h-3.5" />
                      <span>Select / Drag</span>
                    </button>
                    <button
                      onClick={() => setActiveTool('route')}
                      className={`flex items-center gap-2 px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${
                        activeTool === 'route'
                          ? 'bg-cyan-600 text-white'
                          : 'bg-slate-800/80 hover:bg-slate-700 text-slate-300'
                      }`}
                    >
                      <Zap className="w-3.5 h-3.5 text-amber-300" />
                      <span>Route Trace</span>
                    </button>
                    <button
                      onClick={handleAddVia}
                      className="flex items-center gap-2 px-2.5 py-1.5 rounded text-xs font-medium bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition-colors"
                      title="Place via at cursor position"
                    >
                      <Layers className="w-3.5 h-3.5 text-blue-300" />
                      <span>Add Via</span>
                    </button>
                    <button
                      onClick={handleRotateSelected}
                      disabled={!selectedComponentId}
                      className="flex items-center gap-2 px-2.5 py-1.5 rounded text-xs font-medium bg-slate-800/80 hover:bg-slate-700 text-slate-300 disabled:opacity-40 transition-colors"
                      title="Rotate selected component 90° (R key)"
                    >
                      <RotateCw className="w-3.5 h-3.5 text-purple-300" />
                      <span>Rotate 90°</span>
                    </button>
                  </div>
                </div>

                {/* Routing Parameters */}
                <div>
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Routing Options</div>
                  <div className="space-y-2 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Active Copper Layer</label>
                      <div className="grid grid-cols-2 gap-1">
                        <button
                          onClick={() => setActiveLayer('F.Cu')}
                          className={`py-1 text-xs font-semibold rounded ${
                            activeLayer === 'F.Cu'
                              ? 'bg-cyan-600 text-white'
                              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                          }`}
                        >
                          Top (F.Cu)
                        </button>
                        <button
                          onClick={() => setActiveLayer('B.Cu')}
                          className={`py-1 text-xs font-semibold rounded ${
                            activeLayer === 'B.Cu'
                              ? 'bg-blue-600 text-white'
                              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                          }`}
                        >
                          Bottom (B.Cu)
                        </button>
                      </div>
                    </div>

                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Trace Width (mm)</label>
                      <select
                        value={activeTrackWidth}
                        onChange={e => setActiveTrackWidth(parseFloat(e.target.value))}
                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-white"
                      >
                        <option value={0.25}>0.25mm (Standard Signal)</option>
                        <option value={0.40}>0.40mm (Default Power/Signal)</option>
                        <option value={0.60}>0.60mm (High Current 1-2A)</option>
                        <option value={1.00}>1.00mm (Main Power Rail 3A)</option>
                        <option value={1.50}>1.50mm (Heavy Current 5A)</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Grid Snapping</label>
                      <select
                        value={gridSnap}
                        onChange={e => setGridSnap(parseFloat(e.target.value))}
                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-white"
                      >
                        <option value={0.25}>0.25 mm</option>
                        <option value={0.50}>0.50 mm</option>
                        <option value={1.00}>1.00 mm (Default)</option>
                        <option value={2.54}>2.54 mm (100 mil DIP)</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Layer Visibility Stack */}
                <div>
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Layer Visibility</div>
                  <div className="space-y-1 bg-slate-900/60 p-2 rounded-lg border border-slate-800">
                    {[
                      { key: 'F.Cu', name: 'Top Copper (F.Cu)', color: '#06b6d4' },
                      { key: 'B.Cu', name: 'Bottom Copper (B.Cu)', color: '#3b82f6' },
                      { key: 'F.SilkS', name: 'Top Silkscreen (F.SilkS)', color: '#f8fafc' },
                      { key: 'Edge.Cuts', name: 'Board Outline (Edge.Cuts)', color: '#f59e0b' },
                      { key: 'Ratsnest', name: 'Ratsnest Flylines', color: '#10b981' },
                      { key: 'Vias', name: 'Vias & Drill Holes', color: '#eab308' },
                      { key: 'Pads', name: 'SMD / THT Pads', color: '#fbbf24' },
                    ].map(layer => (
                      <div
                        key={layer.key}
                        onClick={() =>
                          setVisibleLayers(prev => ({
                            ...prev,
                            [layer.key]: !prev[layer.key as keyof typeof prev],
                          }))
                        }
                        className="flex items-center justify-between px-2 py-1 rounded hover:bg-slate-800/60 cursor-pointer text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: layer.color }} />
                          <span className="text-slate-300">{layer.name}</span>
                        </div>
                        {visibleLayers[layer.key as keyof typeof visibleLayers] ? (
                          <Eye className="w-3.5 h-3.5 text-cyan-400" />
                        ) : (
                          <EyeOff className="w-3.5 h-3.5 text-slate-600" />
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Selected Component Properties Inspector */}
                {selectedComponent ? (
                  <div className="bg-slate-900/80 p-3 rounded-lg border border-cyan-800/40">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold text-cyan-300">{selectedComponent.ref_des}</span>
                      <button
                        onClick={handleDeleteSelected}
                        className="text-rose-400 hover:text-rose-300 p-1"
                        title="Delete component"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <div className="space-y-1 text-[11px] text-slate-300">
                      <div><strong className="text-slate-400">Value:</strong> {selectedComponent.value}</div>
                      <div><strong className="text-slate-400">Footprint:</strong> {selectedComponent.footprint_id}</div>
                      <div><strong className="text-slate-400">Position:</strong> ({selectedComponent.pos_x_mm}, {selectedComponent.pos_y_mm}) mm</div>
                      <div><strong className="text-slate-400">Rotation:</strong> {selectedComponent.rotation_deg}°</div>
                      <div><strong className="text-slate-400">Side:</strong> {selectedComponent.side}</div>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 bg-slate-900/30 rounded-lg text-center text-xs text-slate-500 border border-slate-800/50">
                    Click a component or pad to inspect electrical and placement properties.
                  </div>
                )}
              </div>

              {/* Bottom canvas hint */}
              <div className="text-[10px] text-slate-500 pt-3 border-t border-slate-800">
                Left Click: Select/Drag • Right Drag: Pan Canvas • Wheel: Zoom
              </div>
            </div>

            {/* Canvas Main Viewport */}
            <div
              className="flex-1 relative bg-[#060a14] overflow-hidden cursor-crosshair"
              onMouseDown={e => {
                if (e.button === 2 || e.button === 1 || activeTool === 'select') {
                  if (e.button === 2 || e.button === 1) {
                    setIsPanning(true);
                    setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
                  }
                }
              }}
              onContextMenu={e => e.preventDefault()}
              onMouseMove={handleCanvasMouseMove}
              onMouseUp={handleCanvasMouseUp}
              onWheel={e => {
                e.preventDefault();
                const delta = e.deltaY < 0 ? 1.15 : 0.85;
                setZoom(z => Math.max(1.5, Math.min(15.0, z * delta)));
              }}
            >
              {/* Canvas Overlay Controls */}
              <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5 bg-slate-900/90 p-1.5 rounded-lg border border-slate-800 shadow-xl backdrop-blur-sm">
                <button
                  onClick={() => setZoom(z => Math.min(15.0, z * 1.2))}
                  className="p-1.5 hover:bg-slate-800 rounded text-slate-300"
                  title="Zoom In"
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setZoom(z => Math.max(1.5, z * 0.8))}
                  className="p-1.5 hover:bg-slate-800 rounded text-slate-300"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <button
                  onClick={() => { setZoom(4.5); setPan({ x: 40, y: 30 }); }}
                  className="p-1.5 hover:bg-slate-800 rounded text-slate-300"
                  title="Fit to Board"
                >
                  <Maximize2 className="w-4 h-4" />
                </button>
              </div>

              {/* Board Coordinates readout */}
              <div className="absolute bottom-3 left-3 z-10 bg-slate-900/80 px-2.5 py-1 rounded border border-slate-800 text-[11px] text-slate-400 font-mono">
                X: {mouseBoardPos.x.toFixed(2)}mm | Y: {mouseBoardPos.y.toFixed(2)}mm | Grid: {gridSnap}mm | Zoom: {(zoom * 10).toFixed(0)}%
              </div>

              {/* Interactive SVG Canvas */}
              <svg
                ref={svgCanvasRef}
                className="w-full h-full"
                style={{
                  transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                  transformOrigin: '0 0',
                }}
              >
                <defs>
                  {/* Grid pattern */}
                  <pattern id="pcbGridSmall" width={gridSnap} height={gridSnap} patternUnits="userSpaceOnUse">
                    <circle cx={gridSnap / 2} cy={gridSnap / 2} r="0.08" fill="#1e293b" />
                  </pattern>
                  <pattern id="pcbGridLarge" width={gridSnap * 5} height={gridSnap * 5} patternUnits="userSpaceOnUse">
                    <rect width={gridSnap * 5} height={gridSnap * 5} fill="none" stroke="#172554" strokeWidth="0.1" />
                  </pattern>

                  {/* Solder mask and pad gradients */}
                  <linearGradient id="boardSubstrate" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#064e3b" />
                    <stop offset="100%" stopColor="#022c22" />
                  </linearGradient>
                  <linearGradient id="padGold" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#fef08a" />
                    <stop offset="100%" stopColor="#eab308" />
                  </linearGradient>
                </defs>

                {currentBoard && (
                  <>
                    {/* Background Grid */}
                    <rect
                      x="-50"
                      y="-50"
                      width={currentBoard.width_mm + 100}
                      height={currentBoard.height_mm + 100}
                      fill="url(#pcbGridSmall)"
                    />
                    <rect
                      x="-50"
                      y="-50"
                      width={currentBoard.width_mm + 100}
                      height={currentBoard.height_mm + 100}
                      fill="url(#pcbGridLarge)"
                    />

                    {/* Board Substrate */}
                    <rect
                      x="0"
                      y="0"
                      width={currentBoard.width_mm}
                      height={currentBoard.height_mm}
                      rx={currentBoard.corner_radius_mm}
                      fill="url(#boardSubstrate)"
                      stroke="#10b981"
                      strokeWidth="0.3"
                    />

                    {/* Edge.Cuts Outline */}
                    {visibleLayers['Edge.Cuts'] && (
                      <rect
                        x="0"
                        y="0"
                        width={currentBoard.width_mm}
                        height={currentBoard.height_mm}
                        rx={currentBoard.corner_radius_mm}
                        fill="none"
                        stroke="#f59e0b"
                        strokeWidth="0.2"
                        strokeDasharray="1,1"
                      />
                    )}

                    {/* Bottom Copper Tracks (B.Cu - Blue) */}
                    {visibleLayers['B.Cu'] && currentBoard.tracks.filter(t => t.layer === 'B.Cu').map(track => (
                      <line
                        key={track.track_id}
                        x1={track.start_x_mm}
                        y1={track.start_y_mm}
                        x2={track.end_x_mm}
                        y2={track.end_y_mm}
                        stroke="#3b82f6"
                        strokeWidth={track.width_mm}
                        strokeLinecap="round"
                        opacity={0.7}
                      />
                    ))}

                    {/* Top Copper Tracks (F.Cu - Cyan) */}
                    {visibleLayers['F.Cu'] && currentBoard.tracks.filter(t => t.layer === 'F.Cu').map(track => (
                      <line
                        key={track.track_id}
                        x1={track.start_x_mm}
                        y1={track.start_y_mm}
                        x2={track.end_x_mm}
                        y2={track.end_y_mm}
                        stroke="#06b6d4"
                        strokeWidth={track.width_mm}
                        strokeLinecap="round"
                      />
                    ))}

                    {/* Active routing preview line */}
                    {routeStartPad && (
                      <line
                        x1={routeStartPad.x}
                        y1={routeStartPad.y}
                        x2={mouseBoardPos.x}
                        y2={mouseBoardPos.y}
                        stroke="#fbbf24"
                        strokeWidth={activeTrackWidth}
                        strokeLinecap="round"
                        strokeDasharray="0.8,0.8"
                      />
                    )}

                    {/* Ratsnest Unrouted Flylines (Lime dashed) */}
                    {visibleLayers['Ratsnest'] && ratsnest.map((rn, idx) => (
                      <line
                        key={`rn_${idx}`}
                        x1={rn.start_x}
                        y1={rn.start_y}
                        x2={rn.end_x}
                        y2={rn.end_y}
                        stroke="#10b981"
                        strokeWidth="0.15"
                        strokeDasharray="0.6,0.6"
                        opacity={0.8}
                      />
                    ))}

                    {/* Vias */}
                    {visibleLayers['Vias'] && currentBoard.vias.map(via => (
                      <g key={via.via_id}>
                        <circle
                          cx={via.x_mm}
                          cy={via.y_mm}
                          r={via.diameter_mm / 2}
                          fill="url(#padGold)"
                          stroke="#0284c7"
                          strokeWidth="0.08"
                        />
                        <circle
                          cx={via.x_mm}
                          cy={via.y_mm}
                          r={via.drill_mm / 2}
                          fill="#090d16"
                        />
                      </g>
                    ))}

                    {/* Components, Silkscreen and Pads */}
                    {currentBoard.components.map(comp => {
                      const fp = getFp(comp.footprint_id);
                      const w = fp ? fp.width_mm : 4.0;
                      const h = fp ? fp.height_mm : 4.0;
                      const isSelected = selectedComponentId === comp.component_instance_id;

                      return (
                        <g
                          key={comp.component_instance_id}
                          transform={`translate(${comp.pos_x_mm}, ${comp.pos_y_mm}) rotate(${comp.rotation_deg})`}
                          onMouseDown={e => handleComponentMouseDown(e, comp)}
                          className="cursor-move"
                        >
                          {/* Selection Halo */}
                          {isSelected && (
                            <rect
                              x={-w / 2 - 0.6}
                              y={-h / 2 - 0.6}
                              width={w + 1.2}
                              height={h + 1.2}
                              fill="none"
                              stroke="#06b6d4"
                              strokeWidth="0.25"
                              strokeDasharray="0.8,0.8"
                            />
                          )}

                          {/* Silkscreen Box & Reference */}
                          {visibleLayers['F.SilkS'] && (
                            <>
                              <rect
                                x={-w / 2}
                                y={-h / 2}
                                width={w}
                                height={h}
                                fill="none"
                                stroke="#f8fafc"
                                strokeWidth="0.12"
                                opacity={0.7}
                              />
                              <text
                                x="0"
                                y={-h / 2 - 0.4}
                                fill="#38bdf8"
                                fontSize="1.1"
                                fontFamily="monospace"
                                textAnchor="middle"
                              >
                                {comp.ref_des}
                              </text>
                            </>
                          )}

                          {/* Component Pads */}
                          {visibleLayers['Pads'] && fp?.pads.map(pad => {
                            const isPadHovered = false;
                            // Calculate absolute pad coordinate in board frame
                            const rad = (comp.rotation_deg * Math.PI) / 180;
                            const absX = comp.pos_x_mm + (pad.rel_x_mm * Math.cos(rad) - pad.rel_y_mm * Math.sin(rad));
                            const absY = comp.pos_y_mm + (pad.rel_x_mm * Math.sin(rad) + pad.rel_y_mm * Math.cos(rad));

                            if (pad.pad_type === 'thru_hole') {
                              return (
                                <g
                                  key={pad.pad_number}
                                  onClick={e => handlePadClick(e, comp, pad.pad_number, absX, absY)}
                                  className="cursor-pointer hover:opacity-80"
                                >
                                  <circle
                                    cx={pad.rel_x_mm}
                                    cy={pad.rel_y_mm}
                                    r={pad.width_mm / 2}
                                    fill="url(#padGold)"
                                    stroke="#ca8a04"
                                    strokeWidth="0.08"
                                  />
                                  {pad.drill_diameter_mm && (
                                    <circle
                                      cx={pad.rel_x_mm}
                                      cy={pad.rel_y_mm}
                                      r={pad.drill_diameter_mm / 2}
                                      fill="#090d16"
                                    />
                                  )}
                                </g>
                              );
                            }

                            return (
                              <rect
                                key={pad.pad_number}
                                x={pad.rel_x_mm - pad.width_mm / 2}
                                y={pad.rel_y_mm - pad.height_mm / 2}
                                width={pad.width_mm}
                                height={pad.height_mm}
                                rx="0.1"
                                fill="url(#padGold)"
                                stroke="#ca8a04"
                                strokeWidth="0.08"
                                onClick={e => handlePadClick(e, comp, pad.pad_number, absX, absY)}
                                className="cursor-pointer hover:opacity-80"
                              />
                            );
                          })}
                        </g>
                      );
                    })}
                  </>
                )}
              </svg>
            </div>
          </>
        )}

        {/* 3D Orbit View Tab */}
        {activeTab === '3d' && (
          <div className="flex-1 flex flex-col bg-[#070b14] p-4 overflow-hidden">
            {/* 3D Controls Bar */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-xs">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <span className="text-slate-400 font-medium">Solder Mask:</span>
                  <div className="flex items-center gap-1">
                    {[
                      { id: 'green', name: 'Forest Green', bg: 'bg-[#064e3b]' },
                      { id: 'black', name: 'Midnight Onyx', bg: 'bg-[#0f172a]' },
                      { id: 'blue', name: 'Cobalt Blue', bg: 'bg-[#1e3a8a]' },
                      { id: 'red', name: 'Ruby Red', bg: 'bg-[#7f1d1d]' },
                    ].map(c => (
                      <button
                        key={c.id}
                        onClick={() => setSolderMaskColor(c.id as any)}
                        className={`w-5 h-5 rounded-full ${c.bg} border-2 ${
                          solderMaskColor === c.id ? 'border-cyan-400 scale-110' : 'border-transparent'
                        }`}
                        title={c.name}
                      />
                    ))}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-slate-400 font-medium">Surface Finish:</span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setSurfaceFinish('ENIG')}
                      className={`px-2 py-0.5 rounded text-xs ${
                        surfaceFinish === 'ENIG' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/50' : 'text-slate-400'
                      }`}
                    >
                      ENIG Gold
                    </button>
                    <button
                      onClick={() => setSurfaceFinish('HASL')}
                      className={`px-2 py-0.5 rounded text-xs ${
                        surfaceFinish === 'HASL' ? 'bg-slate-400/20 text-slate-200 border border-slate-400/50' : 'text-slate-400'
                      }`}
                    >
                      HASL Silver
                    </button>
                  </div>
                </div>
              </div>

              {/* Orbit Controls */}
              <div className="flex items-center gap-4 text-slate-400">
                <div className="flex items-center gap-1">
                  <span>Pitch ({orbitRotX}°):</span>
                  <input
                    type="range"
                    min="10"
                    max="80"
                    value={orbitRotX}
                    onChange={e => setOrbitRotX(parseInt(e.target.value))}
                    className="w-20 accent-cyan-400"
                  />
                </div>
                <div className="flex items-center gap-1">
                  <span>Yaw ({orbitRotY}°):</span>
                  <input
                    type="range"
                    min="-180"
                    max="180"
                    value={orbitRotY}
                    onChange={e => setOrbitRotY(parseInt(e.target.value))}
                    className="w-20 accent-cyan-400"
                  />
                </div>
                <button
                  onClick={() => { setOrbitRotX(35); setOrbitRotY(-25); setOrbitZoom(1.0); }}
                  className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded"
                >
                  Reset 3D
                </button>
              </div>
            </div>

            {/* 3D Visualizer Canvas Container */}
            <div className="flex-1 flex items-center justify-center overflow-hidden" style={{ perspective: '1200px' }}>
              {currentBoard && (
                <div
                  style={{
                    width: `${currentBoard.width_mm * 5}px`,
                    height: `${currentBoard.height_mm * 5}px`,
                    transform: `rotateX(${orbitRotX}deg) rotateY(${orbitRotY}deg) scale3d(${orbitZoom}, ${orbitZoom}, ${orbitZoom})`,
                    transformStyle: 'preserve-3d',
                    transition: 'transform 0.1s ease-out',
                  }}
                  className="relative shadow-2xl rounded-lg"
                >
                  {/* Top Layer Board Substrate */}
                  <div
                    style={{
                      backgroundColor:
                        solderMaskColor === 'green'
                          ? '#064e3b'
                          : solderMaskColor === 'black'
                          ? '#0a0f1d'
                          : solderMaskColor === 'blue'
                          ? '#1e3a8a'
                          : '#7f1d1d',
                      boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
                    }}
                    className="w-full h-full rounded-lg border border-cyan-500/20 relative overflow-hidden"
                  >
                    {/* Render Tracks on 3D */}
                    <svg className="w-full h-full absolute inset-0 pointer-events-none">
                      {currentBoard.tracks.filter(t => t.layer === 'F.Cu').map(t => (
                        <line
                          key={t.track_id}
                          x1={t.start_x_mm * 5}
                          y1={t.start_y_mm * 5}
                          x2={t.end_x_mm * 5}
                          y2={t.end_y_mm * 5}
                          stroke="#06b6d4"
                          strokeWidth={t.width_mm * 5}
                          strokeLinecap="round"
                          opacity={0.8}
                        />
                      ))}
                    </svg>

                    {/* 3D Extruded Component Blocks */}
                    {currentBoard.components.map(c => {
                      const fp = getFp(c.footprint_id);
                      const w = (fp ? fp.width_mm : 4) * 5;
                      const h = (fp ? fp.height_mm : 4) * 5;
                      const isIC = c.footprint_id.includes('SOIC') || c.footprint_id.includes('DIP');
                      const blockHeight = isIC ? 16 : 8;

                      return (
                        <div
                          key={c.component_instance_id}
                          style={{
                            left: `${c.pos_x_mm * 5 - w / 2}px`,
                            top: `${c.pos_y_mm * 5 - h / 2}px`,
                            width: `${w}px`,
                            height: `${h}px`,
                            transform: `translateZ(${blockHeight}px) rotate(${c.rotation_deg}deg)`,
                            transformStyle: 'preserve-3d',
                          }}
                          className="absolute bg-slate-900 border border-slate-700/80 rounded flex flex-col items-center justify-center shadow-lg"
                        >
                          <span className="text-[9px] font-mono text-cyan-300 font-bold">{c.ref_des}</span>
                          <span className="text-[7px] font-mono text-slate-400 truncate max-w-full px-1">{c.value}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* DRC Findings Tab */}
        {activeTab === 'drc' && (
          <div className="flex-1 bg-[#0a0f1d] p-6 overflow-y-auto">
            <div className="max-w-5xl mx-auto space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Shield className="w-5 h-5 text-cyan-400" />
                    <span>Design Rule Checking (DRC) Report</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Validates copper clearance, trace width, board-edge clearance, drill sizes, shorts, and unrouted flylines.
                  </p>
                </div>
                <button
                  onClick={handleRunDrc}
                  disabled={isDrcRunning}
                  className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-md shadow-md flex items-center gap-2"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isDrcRunning ? 'animate-spin' : ''}`} />
                  <span>Run DRC Verification</span>
                </button>
              </div>

              {/* Status Summary Banner */}
              {drcReport && (
                <div className="grid grid-cols-4 gap-4">
                  <div className="p-4 rounded-lg bg-slate-900/80 border border-slate-800">
                    <span className="text-xs text-slate-400">Fabrication Status</span>
                    <div className="text-xl font-bold mt-1">
                      {drcReport.passed ? (
                        <span className="text-emerald-400 flex items-center gap-1.5">
                          <CheckCircle2 className="w-5 h-5" /> PASSED
                        </span>
                      ) : (
                        <span className="text-rose-400 flex items-center gap-1.5">
                          <AlertCircle className="w-5 h-5" /> ACTION NEEDED
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-900/80 border border-slate-800">
                    <span className="text-xs text-slate-400">Critical Violations</span>
                    <div className="text-2xl font-bold text-rose-400 mt-1">{drcReport.critical_count}</div>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-900/80 border border-slate-800">
                    <span className="text-xs text-slate-400">Warnings / Advisories</span>
                    <div className="text-2xl font-bold text-amber-400 mt-1">{drcReport.warning_count}</div>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-900/80 border border-slate-800">
                    <span className="text-xs text-slate-400">Routing Completion</span>
                    <div className="text-2xl font-bold text-cyan-400 mt-1">{drcReport.routing_completion_pct}%</div>
                  </div>
                </div>
              )}

              {/* Findings Table */}
              <div className="bg-[#0e1628] rounded-lg border border-slate-800 overflow-hidden">
                <div className="px-4 py-3 border-b border-slate-800 text-xs font-bold text-slate-300">
                  DRC Findings List ({drcReport?.findings.length || 0})
                </div>
                {drcReport && drcReport.findings.length > 0 ? (
                  <div className="divide-y divide-slate-800/80">
                    {drcReport.findings.map(finding => (
                      <div key={finding.finding_id} className="p-4 hover:bg-slate-900/40 transition-colors">
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                                finding.severity === 'critical'
                                  ? 'bg-rose-950 text-rose-300 border border-rose-800'
                                  : finding.severity === 'warning'
                                  ? 'bg-amber-950 text-amber-300 border border-amber-800'
                                  : 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                              }`}
                            >
                              {finding.severity}
                            </span>
                            <span className="font-mono text-xs text-slate-400">{finding.rule_code}</span>
                            <span className="font-bold text-white text-sm">{finding.title}</span>
                          </div>
                          {finding.pos_x_mm !== null && (
                            <span className="text-xs font-mono text-slate-400">
                              Pos: ({finding.pos_x_mm}, {finding.pos_y_mm}) mm
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-300 mt-1">{finding.message}</p>
                        <div className="mt-2 text-xs bg-slate-900/80 p-2.5 rounded border border-slate-800 text-cyan-300">
                          <strong>Remediation:</strong> {finding.remediation_steps}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 text-center text-slate-400 text-xs">
                    No DRC violations detected. Click 'Run DRC Verification' to check the board.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* IPC Constraints & Calculators Tab */}
        {activeTab === 'calculators' && (
          <div className="flex-1 bg-[#0a0f1d] p-6 overflow-y-auto">
            <div className="max-w-4xl mx-auto space-y-6">
              <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                <button
                  onClick={() => setActiveCalc('trace_width')}
                  className={`px-3 py-1.5 rounded-md text-xs font-semibold ${
                    activeCalc === 'trace_width'
                      ? 'bg-cyan-600 text-white'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  IPC-2152 Trace Width Calculator
                </button>
                <button
                  onClick={() => setActiveCalc('impedance')}
                  className={`px-3 py-1.5 rounded-md text-xs font-semibold ${
                    activeCalc === 'impedance'
                      ? 'bg-cyan-600 text-white'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  IPC-2141 Microstrip Impedance
                </button>
              </div>

              {/* IPC-2152 Trace Width */}
              {activeCalc === 'trace_width' && (
                <div className="bg-[#0e1628] p-5 rounded-lg border border-slate-800 space-y-4">
                  <h3 className="font-bold text-white text-sm">IPC-2152 / IPC-2221 Current-Carrying Trace Width</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Target Current (Amperes)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={traceCalcReq.current_a}
                        onChange={e => setTraceCalcReq(p => ({ ...p, current_a: parseFloat(e.target.value) || 0.1 }))}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-white"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Max Allowable Temp Rise ΔT (°C)</label>
                      <input
                        type="number"
                        value={traceCalcReq.temp_rise_c}
                        onChange={e => setTraceCalcReq(p => ({ ...p, temp_rise_c: parseFloat(e.target.value) || 10 }))}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-white"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Copper Thickness</label>
                      <select
                        value={traceCalcReq.copper_thickness_oz}
                        onChange={e => setTraceCalcReq(p => ({ ...p, copper_thickness_oz: parseFloat(e.target.value) }))}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-white"
                      >
                        <option value={1.0}>1.0 oz (35 µm - Standard)</option>
                        <option value={2.0}>2.0 oz (70 µm - High Current)</option>
                        <option value={0.5}>0.5 oz (18 µm - Thin Foil)</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Layer Type</label>
                      <select
                        value={traceCalcReq.layer_type}
                        onChange={e => setTraceCalcReq(p => ({ ...p, layer_type: e.target.value as any }))}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-white"
                      >
                        <option value="external">External Surface Layer</option>
                        <option value="internal">Internal Plane Layer</option>
                      </select>
                    </div>
                  </div>

                  <button
                    onClick={handleCalcTraceWidth}
                    className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs rounded shadow"
                  >
                    Calculate Recommended Trace Width
                  </button>

                  {traceCalcRes && (
                    <div className="mt-4 p-4 bg-slate-900/90 rounded border border-cyan-800/40 space-y-2">
                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <span className="text-[11px] text-slate-400">Min Trace Width:</span>
                          <div className="text-lg font-bold text-cyan-400">
                            {traceCalcRes.min_width_mm} mm ({traceCalcRes.min_width_mils} mils)
                          </div>
                        </div>
                        <div>
                          <span className="text-[11px] text-slate-400">Resistance / meter:</span>
                          <div className="text-base font-bold text-slate-200">
                            {traceCalcRes.resistance_per_meter_ohms} Ω/m
                          </div>
                        </div>
                        <div>
                          <span className="text-[11px] text-slate-400">Voltage Drop / meter:</span>
                          <div className="text-base font-bold text-slate-200">
                            {traceCalcRes.voltage_drop_per_meter_v} V/m
                          </div>
                        </div>
                      </div>
                      <div className="text-xs text-slate-400 font-mono pt-2">
                        Formula: {traceCalcRes.standard_documented_formula}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* IPC-2141 Controlled Impedance */}
              {activeCalc === 'impedance' && (
                <div className="bg-[#0e1628] p-5 rounded-lg border border-slate-800 space-y-4">
                  <h3 className="font-bold text-white text-sm">IPC-2141 Microstrip Transmission Line Impedance</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Trace Width w (mm)</label>
                      <input
                        type="number"
                        step="0.05"
                        value={impedanceCalcReq.trace_width_mm}
                        onChange={e => setImpedanceCalcReq(p => ({ ...p, trace_width_mm: parseFloat(e.target.value) || 0.1 }))}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-white"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Dielectric Height h (mm)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={impedanceCalcReq.dielectric_height_mm}
                        onChange={e => setImpedanceCalcReq(p => ({ ...p, dielectric_height_mm: parseFloat(e.target.value) || 1.6 }))}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-white"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Dielectric Constant εr (FR-4 ~ 4.5)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={impedanceCalcReq.dielectric_constant_er}
                        onChange={e => setImpedanceCalcReq(p => ({ ...p, dielectric_constant_er: parseFloat(e.target.value) || 4.5 }))}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-white"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Copper Thickness</label>
                      <select
                        value={impedanceCalcReq.copper_thickness_oz}
                        onChange={e => setImpedanceCalcReq(p => ({ ...p, copper_thickness_oz: parseFloat(e.target.value) }))}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-white"
                      >
                        <option value={1.0}>1.0 oz (35 µm)</option>
                        <option value={0.5}>0.5 oz (18 µm)</option>
                      </select>
                    </div>
                  </div>

                  <button
                    onClick={handleCalcImpedance}
                    className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs rounded shadow"
                  >
                    Calculate Characteristic Impedance
                  </button>

                  {impedanceCalcRes && (
                    <div className="mt-4 p-4 bg-slate-900/90 rounded border border-cyan-800/40 space-y-2">
                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <span className="text-[11px] text-slate-400">Impedance Z0:</span>
                          <div className="text-xl font-bold text-cyan-400">
                            {impedanceCalcRes.characteristic_impedance_ohms} Ω
                          </div>
                        </div>
                        <div>
                          <span className="text-[11px] text-slate-400">Propagation Delay:</span>
                          <div className="text-base font-bold text-slate-200">
                            {impedanceCalcRes.propagation_delay_ps_per_mm} ps/mm
                          </div>
                        </div>
                        <div>
                          <span className="text-[11px] text-slate-400">Effective Dielectric εeff:</span>
                          <div className="text-base font-bold text-slate-200">
                            {impedanceCalcRes.effective_dielectric_constant}
                          </div>
                        </div>
                      </div>
                      <p className="text-xs text-slate-300 pt-2">{impedanceCalcRes.advisory}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* BOM & Cost Estimator Tab */}
        {activeTab === 'bom_cost' && (
          <div className="flex-1 bg-[#0a0f1d] p-6 overflow-y-auto">
            <div className="max-w-5xl mx-auto space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Package className="w-5 h-5 text-emerald-400" />
                    <span>Bill of Materials & Prototype Fabrication Cost</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Transparent cost estimates based on board surface area, layer count, surface finish, and BOM sourcing.
                  </p>
                </div>
                <button
                  onClick={handleFetchBomAndCost}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded shadow flex items-center gap-2"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Refresh Estimates</span>
                </button>
              </div>

              {/* Cost Estimator Options */}
              <div className="grid grid-cols-4 gap-4 bg-[#0e1628] p-4 rounded-lg border border-slate-800">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Quantity (Units)</label>
                  <select
                    value={costReq.quantity}
                    onChange={e => setCostReq(p => ({ ...p, quantity: parseInt(e.target.value) }))}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white"
                  >
                    <option value={5}>5 pcs (Quick Prototype)</option>
                    <option value={10}>10 pcs</option>
                    <option value={20}>20 pcs</option>
                    <option value={50}>50 pcs</option>
                    <option value={100}>100 pcs (Small Batch)</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Surface Finish</label>
                  <select
                    value={costReq.surface_finish}
                    onChange={e => setCostReq(p => ({ ...p, surface_finish: e.target.value as any }))}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white"
                  >
                    <option value="HASL_lead_free">HASL (Lead-Free)</option>
                    <option value="ENIG">ENIG (Gold Plating)</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Turnaround Time</label>
                  <select
                    value={costReq.lead_time_days}
                    onChange={e => setCostReq(p => ({ ...p, lead_time_days: parseInt(e.target.value) }))}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white"
                  >
                    <option value={5}>5 Working Days (Standard)</option>
                    <option value={3}>3 Working Days (Expedited)</option>
                    <option value={2}>48h Express Rush</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Estimated Total Cost</label>
                  <div className="text-xl font-bold text-emerald-400 py-1">
                    ${costRes ? costRes.estimated_total_prototype_cost_usd.toFixed(2) : '0.00'}
                  </div>
                </div>
              </div>

              {/* Transparent Cost Breakdown */}
              {costRes && (
                <div className="p-4 bg-slate-900/80 rounded-lg border border-slate-800 space-y-2">
                  <div className="text-xs font-bold text-slate-300">Cost Breakdown & Assumptions</div>
                  <div className="grid grid-cols-4 gap-2 text-xs text-slate-400">
                    <div>Tooling Base: <strong className="text-slate-200">${costRes.cost_breakdown.tooling_base_usd}</strong></div>
                    <div>Substrate Material: <strong className="text-slate-200">${costRes.cost_breakdown.substrate_material_usd}</strong></div>
                    <div>Surface Finish Fee: <strong className="text-slate-200">${costRes.cost_breakdown.surface_finish_usd}</strong></div>
                    <div>Unit PCB Fab Cost: <strong className="text-emerald-400">${costRes.estimated_unit_cost_usd} / ea</strong></div>
                  </div>
                  <div className="pt-2 text-[11px] text-slate-500">
                    {costRes.pricing_assumptions.map((p, i) => (
                      <div key={i}>• {p}</div>
                    ))}
                  </div>
                </div>
              )}

              {/* BOM Table */}
              <div className="bg-[#0e1628] rounded-lg border border-slate-800 overflow-hidden">
                <div className="px-4 py-3 border-b border-slate-800 text-xs font-bold text-slate-300">
                  Aggregated Bill of Materials ({bomItems.length} line items)
                </div>
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 text-slate-400 uppercase text-[10px] tracking-wider">
                    <tr>
                      <th className="px-4 py-2.5">Designators</th>
                      <th className="px-4 py-2.5">Value</th>
                      <th className="px-4 py-2.5">Footprint</th>
                      <th className="px-4 py-2.5">Qty</th>
                      <th className="px-4 py-2.5">Est. Unit</th>
                      <th className="px-4 py-2.5">Est. Total</th>
                      <th className="px-4 py-2.5">Supplier Search</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {bomItems.map((item, idx) => (
                      <tr key={idx} className="hover:bg-slate-900/40">
                        <td className="px-4 py-2.5 font-mono text-cyan-400 font-semibold">{item.ref_des}</td>
                        <td className="px-4 py-2.5 text-white">{item.value}</td>
                        <td className="px-4 py-2.5 text-slate-400">{item.package_footprint}</td>
                        <td className="px-4 py-2.5 font-bold text-white">{item.quantity}</td>
                        <td className="px-4 py-2.5 text-slate-300">${item.approx_unit_cost_usd.toFixed(2)}</td>
                        <td className="px-4 py-2.5 text-emerald-400 font-bold">${item.approx_total_cost_usd.toFixed(2)}</td>
                        <td className="px-4 py-2.5">
                          <a
                            href={`https://www.digikey.com/en/products/result?keywords=${encodeURIComponent(`${item.value} ${item.package_footprint}`)}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-cyan-400 hover:underline flex items-center gap-1"
                          >
                            <span>DigiKey</span>
                            <ArrowRight className="w-3 h-3" />
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Fabrication Exports Tab */}
        {activeTab === 'export' && (
          <div className="flex-1 bg-[#0a0f1d] p-6 overflow-y-auto">
            <div className="max-w-4xl mx-auto space-y-6">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Download className="w-5 h-5 text-cyan-400" />
                  <span>Manufacturing & Fabrication Exports</span>
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Generate standard RS-274X Gerber suites, Excellon NC drill files, native KiCad PCB layouts, and Pick-and-Place centroid CSVs.
                </p>
              </div>

              {/* Format Selection Cards */}
              <div className="grid grid-cols-3 gap-3">
                {[
                  {
                    id: 'gerber_zip',
                    title: 'Gerber RS-274X Suite',
                    desc: 'Full 7-layer Gerber archive (.gtl, .gbl, .gto, .gts, .gml) + drill for PCB fabrication houses.',
                    badge: 'Standard Fab',
                  },
                  {
                    id: 'kicad_pcb',
                    title: 'Native KiCad PCB',
                    desc: 'Standard S-expression format (.kicad_pcb) for opening in KiCad 7 / 8 EDA software.',
                    badge: 'KiCad EDA',
                  },
                  {
                    id: 'excellon_drill',
                    title: 'Excellon NC Drill',
                    desc: 'NC drill coordinates and tool sizing definitions for automated drilling machines.',
                    badge: 'CNC Drill',
                  },
                  {
                    id: 'pick_and_place_csv',
                    title: 'Centroid CSV',
                    desc: 'Component centroid coordinates, orientation angle, and board side for SMT pick-and-place.',
                    badge: 'SMT Assembly',
                  },
                  {
                    id: 'bom_csv',
                    title: 'BOM CSV',
                    desc: 'Structured component inventory for procurement and assembly bill-of-materials.',
                    badge: 'Purchasing',
                  },
                  {
                    id: 'svg_board',
                    title: 'SVG Vector Preview',
                    desc: 'High-resolution scalable vector graphic of board layout for documentation and presentation.',
                    badge: 'Vector',
                  },
                ].map(fmt => (
                  <div
                    key={fmt.id}
                    onClick={() => setExportFormat(fmt.id as any)}
                    className={`p-4 rounded-lg border cursor-pointer transition-all ${
                      exportFormat === fmt.id
                        ? 'bg-cyan-950/40 border-cyan-500 shadow-md shadow-cyan-950'
                        : 'bg-[#0e1628] border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-bold text-white text-xs">{fmt.title}</span>
                      <span className="text-[10px] bg-slate-800 text-cyan-300 px-1.5 py-0.5 rounded font-mono">
                        {fmt.badge}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">{fmt.desc}</p>
                  </div>
                ))}
              </div>

              <button
                onClick={handleExport}
                disabled={isExporting}
                className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs rounded-md shadow-lg flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                <span>{isExporting ? 'Generating Package...' : `Export ${exportFormat.toUpperCase()}`}</span>
              </button>

              {/* Exported Result Preview & Download */}
              {exportedData && (
                <div className="bg-[#0e1628] p-4 rounded-lg border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold text-white">{exportedData.filename}</span>
                      <span className="text-[11px] text-slate-400 ml-2">({exportedData.mime_type})</span>
                    </div>
                    <a
                      href={
                        exportedData.export_format === 'gerber_zip'
                          ? `data:application/zip;base64,${exportedData.content}`
                          : `data:${exportedData.mime_type};charset=utf-8,${encodeURIComponent(exportedData.content)}`
                      }
                      download={exportedData.filename}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded flex items-center gap-1.5"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download File</span>
                    </a>
                  </div>

                  {exportedData.export_format !== 'gerber_zip' ? (
                    <pre className="bg-slate-900 p-3 rounded font-mono text-xs text-slate-300 max-h-60 overflow-y-auto border border-slate-800">
                      {exportedData.content}
                    </pre>
                  ) : (
                    <div className="bg-slate-900 p-3 rounded text-xs text-slate-300 space-y-1 border border-slate-800">
                      <span className="text-cyan-400 font-semibold block mb-1">Archived Gerber Layers:</span>
                      {exportedData.files &&
                        Object.keys(exportedData.files).map(fn => (
                          <div key={fn} className="flex items-center gap-2 font-mono text-[11px] text-slate-400">
                            <FileCode className="w-3.5 h-3.5 text-cyan-400" />
                            <span>{fn}</span>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Schematic to PCB Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0e1628] border border-cyan-800/60 rounded-xl max-w-lg w-full p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <span>Import & Convert Circuit Schematic</span>
              </h3>
              <button onClick={() => setShowImportModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <p className="text-xs text-slate-400">
              Converts a validated schematic netlist into PCB components and nets. Unknown footprints will never be silently substituted.
            </p>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Select Schematic Project</label>
                <select
                  value={selectedSchProjectId}
                  onChange={e => setSelectedSchProjectId(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-xs text-white"
                >
                  {schematicProjects.map(sp => (
                    <option key={sp.project_id} value={sp.project_id}>
                      {sp.title} ({sp.sheet.components.length} components)
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Board Width (mm)</label>
                  <input
                    type="number"
                    value={importWidth}
                    onChange={e => setImportWidth(parseFloat(e.target.value) || 80)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Board Height (mm)</label>
                  <input
                    type="number"
                    value={importHeight}
                    onChange={e => setImportHeight(parseFloat(e.target.value) || 60)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-white"
                  />
                </div>
              </div>
            </div>

            {conversionReport && conversionReport.unmapped_components.length > 0 && (
              <div className="p-3 bg-amber-950/60 border border-amber-800/80 rounded text-xs text-amber-200 space-y-1">
                <strong>Notice:</strong> {conversionReport.unmapped_components.length} components have unmapped footprints and were excluded:
                <ul className="list-disc pl-4 text-[11px] text-amber-300">
                  {conversionReport.unmapped_components.map((u, i) => (
                    <li key={i}>{u.ref_des} ({u.requested_footprint}): {u.reason}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowImportModal(false)}
                className="px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800 rounded"
              >
                Close
              </button>
              <button
                onClick={handleConvertSchematic}
                className="px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded shadow"
              >
                Generate PCB Layout
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Revisions History Modal */}
      {showRevisionsModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0e1628] border border-cyan-800/60 rounded-xl max-w-lg w-full p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <History className="w-4 h-4 text-amber-400" />
                <span>Revision History & Rollback</span>
              </h3>
              <button onClick={() => setShowRevisionsModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="max-h-60 overflow-y-auto divide-y divide-slate-800">
              {revisions.map(rev => (
                <div key={rev.revision_id} className="py-2.5 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-bold text-white">{rev.version}</span>
                    <span className="text-[11px] text-slate-400 ml-2">{rev.created_at}</span>
                    <div className="text-[11px] text-slate-400">{rev.notes}</div>
                  </div>
                  <button
                    onClick={async () => {
                      if (currentProject) {
                        const rolled = await pcbApi.rollbackProject(currentProject.project_id, rev.revision_id);
                        setCurrentProject(rolled);
                        setCurrentBoard(rolled.board);
                        setShowRevisionsModal(false);
                        showBanner('success', `Rolled back to revision ${rev.version}`);
                      }
                    }}
                    className="px-2.5 py-1 bg-amber-600/80 hover:bg-amber-500 text-white text-[11px] rounded"
                  >
                    Restore
                  </button>
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowRevisionsModal(false)}
                className="px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800 rounded"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
