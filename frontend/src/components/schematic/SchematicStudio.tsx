import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
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
  ArrowRight
} from 'lucide-react';
import { api } from '../../services/api';
import {
  SchematicOverviewResponse,
  SchematicComponentDef,
  SchematicProject,
  SchematicSheet,
  ComponentInstance,
  SchematicNet,
  ERCReport,
  SPICESimulationResult,
  AICircuitDesignResponse,
  SchematicExportResponse,
  VoltageDividerResult,
  LEDResistorResult,
  RCTimeConstantResult,
  TransistorBiasResult,
  PowerThermalResult,
  LogicExpressionResult
} from '../../types';

export const SchematicStudio: React.FC = () => {
  // Navigation tabs
  const [activeTab, setActiveTab] = useState<'canvas' | 'erc' | 'calculators' | 'simulation' | 'export' | 'ai'>('canvas');
  const [activeCalc, setActiveCalc] = useState<'ohms' | 'divider' | 'led' | 'rc' | 'bjt' | 'thermal' | 'logic'>('divider');

  // Core data
  const [isLoading, setIsLoading] = useState(false);
  const [, setOverview] = useState<SchematicOverviewResponse | null>(null);
  const [catalog, setCatalog] = useState<SchematicComponentDef[]>([]);
  const [, setProjects] = useState<SchematicProject[]>([]);
  const [currentProject, setCurrentProject] = useState<SchematicProject | null>(null);
  const [currentSheet, setCurrentSheet] = useState<SchematicSheet | null>(null);

  // Status and feedback
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Canvas interaction state
  const [selectedInstanceId, setSelectedInstanceId] = useState<string | null>(null);
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<string>('all');
  const [searchCatalogQuery, setSearchCatalogQuery] = useState('');
  const [wireStartPin, setWireStartPin] = useState<{ instanceId: string; pinId: string; x: number; y: number } | null>(null);
  const [mousePos, setMousePos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1.0);
  const [pan, setPan] = useState({ x: 40, y: 40 });
  const [draggedInstanceId, setDraggedInstanceId] = useState<string | null>(null);
  const [snapToGrid, setSnapToGrid] = useState(true);

  // Undo/Redo stack
  const [history, setHistory] = useState<SchematicSheet[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  // Studio feature states
  const [ercReport, setErcReport] = useState<ERCReport | null>(null);
  const [isErcRunning, setIsErcRunning] = useState(false);
  const [simulationResult, setSimulationResult] = useState<SPICESimulationResult | null>(null);
  const [isSimRunning, setIsSimRunning] = useState(false);
  const [exportFormat, setExportFormat] = useState<'spice' | 'kicad' | 'bom_csv' | 'bom_json' | 'connection_table' | 'svg'>('spice');
  const [exportResult, setExportResult] = useState<SchematicExportResponse | null>(null);

  // AI Assistant state
  const [aiPrompt, setAiPrompt] = useState('5V to 3.3V voltage regulator circuit with decoupling capacitors and power LED indicator');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiDesignResponse, setAiDesignResponse] = useState<AICircuitDesignResponse | null>(null);

  // Calculators state
  // 1. Ohm's law
  const [ohmsV, setOhmsV] = useState<string>('5.0');
  const [ohmsI, setOhmsI] = useState<string>('0.02');
  const [ohmsR, setOhmsR] = useState<string>('');
  const [ohmsResult, setOhmsResult] = useState<any>(null);

  // 2. Voltage divider
  const [vdVin, setVdVin] = useState<string>('5.0');
  const [vdR1, setVdR1] = useState<string>('10000');
  const [vdR2, setVdR2] = useState<string>('10000');
  const [vdRload, setVdRload] = useState<string>('');
  const [vdResult, setVdResult] = useState<VoltageDividerResult | null>(null);

  // 3. LED Resistor
  const [ledVsupply, setLedVsupply] = useState<string>('5.0');
  const [ledVforward, setLedVforward] = useState<string>('2.0');
  const [ledTargetMa, setLedTargetMa] = useState<string>('15');
  const [ledColor, setLedColor] = useState<string>('red');
  const [ledResult, setLedResult] = useState<LEDResistorResult | null>(null);

  // 4. RC Filter
  const [rcR, setRcR] = useState<string>('10000');
  const [rcC, setRcC] = useState<string>('1e-7');
  const [rcType, setRcType] = useState<'lowpass' | 'highpass'>('lowpass');
  const [rcResult, setRcResult] = useState<RCTimeConstantResult | null>(null);

  // 5. BJT Saturation
  const [bjtVcc, setBjtVcc] = useState<string>('5.0');
  const [bjtIcMa, setBjtIcMa] = useState<string>('100');
  const [bjtVin, setBjtVin] = useState<string>('3.3');
  const [bjtHfe, setBjtHfe] = useState<string>('100');
  const [bjtResult, setBjtResult] = useState<TransistorBiasResult | null>(null);

  // 6. Thermal & Power
  const [thVin, setThVin] = useState<string>('12.0');
  const [thVout, setThVout] = useState<string>('5.0');
  const [thIload, setThIload] = useState<string>('500');
  const [thPackage, setThPackage] = useState<string>('TO-220');
  const [thResult, setThResult] = useState<PowerThermalResult | null>(null);

  // 7. Logic truth table
  const [logicExpr, setLogicExpr] = useState<string>('A and (B or not C)');
  const [logicResult, setLogicResult] = useState<LogicExpressionResult | null>(null);

  const canvasSvgRef = useRef<SVGSVGElement | null>(null);

  const showNotification = (text: string, type: 'success' | 'error' | 'info' = 'info') => {
    setStatusMessage({ text, type });
    setTimeout(() => setStatusMessage(null), 4000);
  };

  // Push sheet to history
  const pushToHistory = useCallback((sheet: SchematicSheet) => {
    setHistory((prev) => {
      const sliced = prev.slice(0, historyIndex + 1);
      return [...sliced, JSON.parse(JSON.stringify(sheet))];
    });
    setHistoryIndex((prev) => prev + 1);
  }, [historyIndex]);

  // Load initial data
  const loadStudioData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [ovData, catData, projData] = await Promise.all([
        api.getSchematicOverview(),
        api.getSchematicCatalog(),
        api.listSchematicProjects()
      ]);
      setOverview(ovData);
      setCatalog(Object.values(catData));
      setProjects(projData);

      if (projData.length > 0) {
        const fullProj = await api.getSchematicProject(projData[0].project_id);
        setCurrentProject(fullProj);
        if (fullProj.sheet) {
          setCurrentSheet(fullProj.sheet);
          setHistory([JSON.parse(JSON.stringify(fullProj.sheet))]);
          setHistoryIndex(0);
        }
      } else {
        // Create initial demo project
        const newProj = await api.createSchematicProject({
          title: 'NEXORA Circuit Demo #1',
          description: 'Initial interactive schematic sheet with 5V power and LED driver',
          sheet: {
            sheet_id: `sheet_${Date.now()}`,
            title: 'Sheet 1',
            components: [],
            nets: [],
            wires: [],
            annotations: []
          }
        });
        const fetched = await api.getSchematicProject(newProj.project_id);
        setCurrentProject(fetched);
        if (fetched.sheet) {
          setCurrentSheet(fetched.sheet);
          setHistory([JSON.parse(JSON.stringify(fetched.sheet))]);
          setHistoryIndex(0);
        }
        setProjects([fetched]);
      }
    } catch (err: any) {
      showNotification(`Failed to load schematic data: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStudioData();
  }, [loadStudioData]);

  // Undo / Redo
  const handleUndo = () => {
    if (historyIndex > 0) {
      const newIdx = historyIndex - 1;
      const targetSheet = JSON.parse(JSON.stringify(history[newIdx]));
      setCurrentSheet(targetSheet);
      setHistoryIndex(newIdx);
      showNotification('Undo applied', 'info');
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      const newIdx = historyIndex + 1;
      const targetSheet = JSON.parse(JSON.stringify(history[newIdx]));
      setCurrentSheet(targetSheet);
      setHistoryIndex(newIdx);
      showNotification('Redo applied', 'info');
    }
  };

  // Add component instance to active sheet
  const handleAddComponent = (def: SchematicComponentDef) => {
    if (!currentSheet) return;

    // Calculate reference designator count
    const prefix = def.ref_des_prefix || 'U';
    const existingPrefixCount = currentSheet.components.filter(c => c.ref_des.startsWith(prefix)).length;
    const ref_des = `${prefix}${existingPrefixCount + 1}`;

    const snapGrid = (val: number) => snapToGrid ? Math.round(val / 20) * 20 : val;
    const newComponent: ComponentInstance = {
      instance_id: `inst_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      component_id: def.component_id,
      ref_des,
      value: def.default_value || '',
      tolerance: def.default_tolerance || '5%',
      pos_x: snapGrid(160 + (currentSheet.components.length % 5) * 60),
      pos_y: snapGrid(140 + Math.floor(currentSheet.components.length / 5) * 60),
      rotation: 0,
      mirror: false,
      attributes: {}
    };

    const updatedSheet: SchematicSheet = {
      ...currentSheet,
      components: [...currentSheet.components, newComponent]
    };

    setCurrentSheet(updatedSheet);
    setSelectedInstanceId(newComponent.instance_id);
    pushToHistory(updatedSheet);
    showNotification(`Added ${ref_des} (${def.name})`, 'success');
  };

  // Rotate selected component
  const handleRotateComponent = (instanceId: string) => {
    if (!currentSheet) return;
    const updatedComponents = currentSheet.components.map(comp => {
      if (comp.instance_id === instanceId) {
        const nextRotation = (comp.rotation + 90) % 360;
        return { ...comp, rotation: nextRotation };
      }
      return comp;
    });

    const updatedSheet: SchematicSheet = {
      ...currentSheet,
      components: updatedComponents
    };
    setCurrentSheet(updatedSheet);
    pushToHistory(updatedSheet);
  };

  // Delete component and all connected nets
  const handleDeleteComponent = (instanceId: string) => {
    if (!currentSheet) return;
    const updatedComponents = currentSheet.components.filter(c => c.instance_id !== instanceId);
    // Remove references to this instance from nets
    const updatedNets = currentSheet.nets.map(net => ({
      ...net,
      connections: net.connections.filter(n => n.instance_id !== instanceId)
    })).filter(net => net.connections.length > 0);

    const updatedSheet: SchematicSheet = {
      ...currentSheet,
      components: updatedComponents,
      nets: updatedNets
    };
    setCurrentSheet(updatedSheet);
    if (selectedInstanceId === instanceId) setSelectedInstanceId(null);
    pushToHistory(updatedSheet);
    showNotification('Component removed from sheet', 'info');
  };

  // Wire creation handling
  const handlePinClick = (instanceId: string, pinId: string, pinX: number, pinY: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!currentSheet) return;

    if (!wireStartPin) {
      // Start wire
      setWireStartPin({ instanceId, pinId, x: pinX, y: pinY });
      showNotification(`Pin selected. Click target pin to complete net.`, 'info');
    } else {
      // Complete wire
      if (wireStartPin.instanceId === instanceId && wireStartPin.pinId === pinId) {
        setWireStartPin(null);
        return;
      }

      // Check if start pin or end pin already belongs to a net
      const targetNet = currentSheet.nets.find(n =>
        n.connections.some(node => node.instance_id === wireStartPin.instanceId && node.pin_id === wireStartPin.pinId)
      );

      let updatedNets = [...currentSheet.nets];

      if (targetNet) {
        // Add second node to existing net if not already present
        const nodeExists = targetNet.connections.some(node => node.instance_id === instanceId && node.pin_id === pinId);
        if (!nodeExists) {
          updatedNets = updatedNets.map(n => {
            if (n.net_id === targetNet.net_id) {
              return {
                ...n,
                connections: [...n.connections, { instance_id: instanceId, pin_id: pinId }]
              };
            }
            return n;
          });
        }
      } else {
        // Create new net
        const netName = `NET_${currentSheet.nets.length + 1}`;
        const newNet: SchematicNet = {
          net_id: `net_${Date.now()}`,
          name: netName,
          is_power: false,
          is_ground: false,
          connections: [
            { instance_id: wireStartPin.instanceId, pin_id: wireStartPin.pinId },
            { instance_id: instanceId, pin_id: pinId }
          ],
          color: '#06b6d4'
        };
        updatedNets.push(newNet);
      }

      const updatedSheet: SchematicSheet = {
        ...currentSheet,
        nets: updatedNets
      };

      setCurrentSheet(updatedSheet);
      setWireStartPin(null);
      pushToHistory(updatedSheet);
      showNotification(`Connected pins on Net`, 'success');
    }
  };

  // Save current project changes to server
  const handleSaveProject = async () => {
    if (!currentProject || !currentSheet) return;
    try {
      setIsLoading(true);
      const saved = await api.updateSchematicProject(currentProject.project_id, {
        title: currentProject.title,
        description: currentProject.description,
        sheet: currentSheet
      });
      setCurrentProject(saved);
      showNotification('Project and sheet snapshot saved successfully', 'success');
    } catch (err: any) {
      showNotification(`Error saving project: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Run Electrical Rule Checks (ERC)
  const handleRunERC = async () => {
    if (!currentSheet) return;
    setIsErcRunning(true);
    try {
      const report = await api.runSchematicERC(currentSheet);
      setErcReport(report);
      setActiveTab('erc');
      if (report.critical_count === 0 && report.warning_count === 0) {
        showNotification(`ERC Clean! 0 violations found.`, 'success');
      } else {
        showNotification(`ERC Completed: ${report.critical_count} critical, ${report.warning_count} warnings.`, 'info');
      }
    } catch (err: any) {
      showNotification(`ERC Check failed: ${err.message}`, 'error');
    } finally {
      setIsErcRunning(false);
    }
  };

  // Run SPICE Simulation / Analytical Linear Solver
  const handleRunSimulation = async () => {
    if (!currentSheet) return;
    setIsSimRunning(true);
    try {
      const res = await api.runSPICESimulation({
        sheet: currentSheet,
        analysis_type: 'op'
      });
      setSimulationResult(res);
      setActiveTab('simulation');
      if (res.sim_status === 'completed_host_engine' || res.sim_status === 'analytical_ideal_solver') {
        showNotification(`Simulation executed (${res.sim_status}): DC operating points ready`, 'success');
      } else {
        showNotification(`Netlist generated: ${res.engine_name}`, 'info');
      }
    } catch (err: any) {
      showNotification(`Simulation error: ${err.message}`, 'error');
    } finally {
      setIsSimRunning(false);
    }
  };

  // Export Schematic in selected format
  const handleExport = async (format: 'spice' | 'kicad' | 'bom_csv' | 'bom_json' | 'connection_table' | 'svg') => {
    if (!currentSheet) return;
    try {
      setIsLoading(true);
      const res = await api.exportSchematic(currentSheet, format);
      setExportResult(res);
      setExportFormat(format);
      setActiveTab('export');
      showNotification(`Export generated: ${res.filename}`, 'success');
    } catch (err: any) {
      showNotification(`Export failed: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Generate Circuit with AI Assistant
  const handleGenerateAICircuit = async () => {
    if (!aiPrompt.trim()) return;
    setAiLoading(true);
    try {
      const res = await api.generateAICircuit({
        prompt: aiPrompt,
        target_supply_voltage_v: 5.0
      });
      setAiDesignResponse(res);
      showNotification(`AI synthesized "${res.circuit_name}". Review design before loading.`, 'success');
    } catch (err: any) {
      showNotification(`AI generation failed: ${err.message}`, 'error');
    } finally {
      setAiLoading(false);
    }
  };

  // Load AI Generated Sheet into Studio
  const handleLoadAISheet = () => {
    if (!aiDesignResponse) return;
    setCurrentSheet(aiDesignResponse.sheet);
    pushToHistory(aiDesignResponse.sheet);
    setActiveTab('canvas');
    showNotification(`Loaded AI-designed schematic into canvas with mandatory review banner`, 'success');
  };

  // Calculators handlers
  const handleCalcOhmsLaw = async () => {
    try {
      const res = await api.calculateOhmsLaw({
        voltage_v: ohmsV ? parseFloat(ohmsV) : undefined,
        current_a: ohmsI ? parseFloat(ohmsI) : undefined,
        resistance_ohms: ohmsR ? parseFloat(ohmsR) : undefined
      });
      setOhmsResult(res);
    } catch (err: any) {
      showNotification(`Ohm's Law calculation error: ${err.message}`, 'error');
    }
  };

  const handleCalcVoltageDivider = async () => {
    try {
      const res = await api.calculateVoltageDivider({
        vin_v: parseFloat(vdVin) || 5.0,
        r1_ohms: parseFloat(vdR1) || 10000,
        r2_ohms: parseFloat(vdR2) || 10000,
        load_resistance_ohms: vdRload ? parseFloat(vdRload) : undefined
      });
      setVdResult(res);
    } catch (err: any) {
      showNotification(`Voltage divider calculation error: ${err.message}`, 'error');
    }
  };

  const handleCalcLED = async () => {
    try {
      const res = await api.calculateLEDResistor({
        supply_voltage_v: parseFloat(ledVsupply) || 5.0,
        led_forward_voltage_v: parseFloat(ledVforward) || 2.0,
        led_current_ma: parseFloat(ledTargetMa) || 15.0,
        led_color: ledColor
      });
      setLedResult(res);
    } catch (err: any) {
      showNotification(`LED resistor calculation error: ${err.message}`, 'error');
    }
  };

  const handleCalcRC = async () => {
    try {
      const res = await api.calculateRCFilter({
        resistance_ohms: parseFloat(rcR) || 10000,
        capacitance_farads: parseFloat(rcC) || 1e-7
      });
      setRcResult(res);
    } catch (err: any) {
      showNotification(`RC filter calculation error: ${err.message}`, 'error');
    }
  };

  const handleCalcBJT = async () => {
    try {
      const res = await api.calculateTransistorBias({
        supply_vcc_v: parseFloat(bjtVcc) || 5.0,
        collector_load_current_ma: parseFloat(bjtIcMa) || 100.0,
        input_base_voltage_v: parseFloat(bjtVin) || 3.3,
        forced_beta_saturation: parseFloat(bjtHfe) || 10.0
      });
      setBjtResult(res);
    } catch (err: any) {
      showNotification(`BJT calculation error: ${err.message}`, 'error');
    }
  };

  const handleCalcThermal = async () => {
    try {
      const res = await api.calculatePowerThermal({
        input_voltage_v: parseFloat(thVin) || 12.0,
        output_voltage_v: parseFloat(thVout) || 5.0,
        load_current_ma: parseFloat(thIload) || 500.0,
        package_type: thPackage
      });
      setThResult(res);
    } catch (err: any) {
      showNotification(`Thermal calculation error: ${err.message}`, 'error');
    }
  };

  const handleCalcLogic = async () => {
    try {
      const res = await api.calculateLogicExpression({
        expression: logicExpr
      });
      setLogicResult(res);
    } catch (err: any) {
      showNotification(`Logic calculation error: ${err.message}`, 'error');
    }
  };

  // Filter component catalog
  const filteredCatalog = useMemo(() => {
    return catalog.filter(comp => {
      const matchesCat = selectedCategoryFilter === 'all' || comp.category === selectedCategoryFilter;
      const matchesSearch = !searchCatalogQuery.trim() ||
        comp.name.toLowerCase().includes(searchCatalogQuery.toLowerCase()) ||
        comp.description.toLowerCase().includes(searchCatalogQuery.toLowerCase());
      return matchesCat && matchesSearch;
    });
  }, [catalog, selectedCategoryFilter, searchCatalogQuery]);

  // Selected component instance
  const selectedInstance = useMemo(() => {
    if (!currentSheet || !selectedInstanceId) return null;
    return currentSheet.components.find(c => c.instance_id === selectedInstanceId) || null;
  }, [currentSheet, selectedInstanceId]);

  // Selected component definition
  const selectedDef = useMemo(() => {
    if (!selectedInstance) return null;
    return catalog.find(d => d.component_id === selectedInstance.component_id) || null;
  }, [selectedInstance, catalog]);

  // Pin coordinate helper
  const getPinCanvasCoords = (comp: ComponentInstance, pinId: string) => {
    const def = catalog.find(c => c.component_id === comp.component_id);
    if (!def) return { x: comp.pos_x, y: comp.pos_y };
    const pin = def.pins.find(p => p.pin_id === pinId);
    if (!pin) return { x: comp.pos_x, y: comp.pos_y };

    const rad = (comp.rotation * Math.PI) / 180;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);

    const rotX = pin.rel_x * cos - pin.rel_y * sin;
    const rotY = pin.rel_x * sin + pin.rel_y * cos;

    return {
      x: Math.round(comp.pos_x + rotX),
      y: Math.round(comp.pos_y + rotY)
    };
  };

  // Render SVG Symbol based on category and shape
  const renderComponentSymbol = (comp: ComponentInstance, isSelected: boolean) => {
    const def = catalog.find(c => c.component_id === comp.component_id);
    const shape = def?.symbol_type || 'box';
    const isGnd = def?.category === 'power_source' && (def.name.toLowerCase().includes('ground') || def.name.toLowerCase().includes('gnd'));
    const isVcc = def?.category === 'power_source' && !isGnd;

    return (
      <g
        transform={`translate(${comp.pos_x}, ${comp.pos_y}) rotate(${comp.rotation})`}
        className="cursor-pointer group"
        onClick={(e) => {
          e.stopPropagation();
          setSelectedInstanceId(comp.instance_id);
        }}
      >
        {/* Selection glow and outline */}
        {isSelected && (
          <rect
            x="-35"
            y="-35"
            width="70"
            height="70"
            rx="6"
            fill="rgba(6, 182, 212, 0.08)"
            stroke="#06b6d4"
            strokeWidth="1.5"
            strokeDasharray="4 3"
          />
        )}

        {/* Component Symbol Graphics */}
        {shape === 'resistor' && (
          <path
            d="M -30 0 L -15 0 L -10 -10 L 0 10 L 10 -10 L 15 0 L 30 0"
            fill="none"
            stroke={isSelected ? '#22d3ee' : '#94a3b8'}
            strokeWidth="2.5"
            strokeLinejoin="round"
          />
        )}

        {shape === 'capacitor' && (
          <g>
            <line x1="-30" y1="0" x2="-8" y2="0" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2.5" />
            <line x1="-8" y1="-16" x2="-8" y2="16" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2.5" />
            <line x1="8" y1="-16" x2="8" y2="16" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2.5" />
            <line x1="8" y1="0" x2="30" y2="0" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2.5" />
          </g>
        )}

        {shape === 'inductor' && (
          <g>
            <line x1="-30" y1="0" x2="-20" y2="0" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2.5" />
            <path d="M -20 0 A 5 5 0 0 1 -10 0 A 5 5 0 0 1 0 0 A 5 5 0 0 1 10 0 A 5 5 0 0 1 20 0" fill="none" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2.5" />
            <line x1="20" y1="0" x2="30" y2="0" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2.5" />
          </g>
        )}

        {shape === 'diode' && (
          <g>
            <line x1="-30" y1="0" x2="-10" y2="0" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2.5" />
            <polygon points="-10,-12 -10,12 10,0" fill={isSelected ? 'rgba(34, 211, 238, 0.2)' : 'rgba(148, 163, 184, 0.2)'} stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2" />
            <line x1="10" y1="-12" x2="10" y2="12" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2.5" />
            <line x1="10" y1="0" x2="30" y2="0" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2.5" />
          </g>
        )}

        {shape === 'led' && (
          <g>
            <line x1="-30" y1="0" x2="-10" y2="0" stroke={isSelected ? '#22d3ee' : '#10b981'} strokeWidth="2.5" />
            <polygon points="-10,-12 -10,12 10,0" fill="rgba(16, 185, 129, 0.25)" stroke="#10b981" strokeWidth="2" />
            <line x1="10" y1="-12" x2="10" y2="12" stroke="#10b981" strokeWidth="2.5" />
            <line x1="10" y1="0" x2="30" y2="0" stroke={isSelected ? '#22d3ee' : '#10b981'} strokeWidth="2.5" />
            {/* Emission light arrows */}
            <line x1="2" y1="-14" x2="12" y2="-22" stroke="#34d399" strokeWidth="1.5" />
            <polygon points="12,-22 8,-20 10,-17" fill="#34d399" />
            <line x1="8" y1="-10" x2="18" y2="-18" stroke="#34d399" strokeWidth="1.5" />
            <polygon points="18,-18 14,-16 16,-13" fill="#34d399" />
          </g>
        )}

        {shape === 'transistor' && (
          <g>
            <circle cx="0" cy="0" r="22" fill="none" stroke="#475569" strokeWidth="1.5" />
            <line x1="-30" y1="0" x2="-10" y2="0" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2.5" />
            <line x1="-10" y1="-14" x2="-10" y2="14" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="3" />
            {/* Collector */}
            <line x1="-10" y1="-6" x2="12" y2="-20" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2.5" />
            <line x1="12" y1="-20" x2="12" y2="-30" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2.5" />
            {/* Emitter with arrow */}
            <line x1="-10" y1="6" x2="12" y2="20" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2.5" />
            <line x1="12" y1="20" x2="12" y2="30" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2.5" />
            <polygon points="12,20 4,14 6,22" fill={isSelected ? '#22d3ee' : '#94a3b8'} />
          </g>
        )}

        {shape === 'opamp' && (
          <g>
            <polygon points="-25,-25 -25,25 25,0" fill="rgba(30, 41, 59, 0.8)" stroke={isSelected ? '#22d3ee' : '#94a3b8'} strokeWidth="2" />
            <text x="-20" y="-10" fill="#94a3b8" fontSize="12" fontWeight="bold">-</text>
            <text x="-20" y="15" fill="#94a3b8" fontSize="12" fontWeight="bold">+</text>
            <line x1="-30" y1="-12" x2="-25" y2="-12" stroke="#94a3b8" strokeWidth="2" />
            <line x1="-30" y1="12" x2="-25" y2="12" stroke="#94a3b8" strokeWidth="2" />
            <line x1="25" y1="0" x2="30" y2="0" stroke="#94a3b8" strokeWidth="2" />
          </g>
        )}

        {isGnd && (
          <g>
            <line x1="0" y1="-20" x2="0" y2="0" stroke={isSelected ? '#22d3ee' : '#38bdf8'} strokeWidth="2.5" />
            <line x1="-14" y1="0" x2="14" y2="0" stroke={isSelected ? '#22d3ee' : '#38bdf8'} strokeWidth="2.5" />
            <line x1="-9" y1="5" x2="9" y2="5" stroke={isSelected ? '#22d3ee' : '#38bdf8'} strokeWidth="2" />
            <line x1="-4" y1="10" x2="4" y2="10" stroke={isSelected ? '#22d3ee' : '#38bdf8'} strokeWidth="1.5" />
          </g>
        )}

        {isVcc && (
          <g>
            <line x1="0" y1="20" x2="0" y2="-4" stroke={isSelected ? '#22d3ee' : '#f43f5e'} strokeWidth="2.5" />
            <polygon points="0,-16 -8,-4 8,-4" fill={isSelected ? '#22d3ee' : '#f43f5e'} />
          </g>
        )}

        {(shape === 'box' || shape === 'ic') && !isGnd && !isVcc && (
          <g>
            <rect
              x="-28"
              y="-28"
              width="56"
              height="56"
              rx="4"
              fill="rgba(15, 23, 42, 0.9)"
              stroke={isSelected ? '#22d3ee' : '#64748b'}
              strokeWidth="2"
            />
            {/* IC notch */}
            <path d="M -6 -28 A 6 6 0 0 0 6 -28" fill="none" stroke="#64748b" strokeWidth="1.5" />
          </g>
        )}

        {/* Labels: Ref Designator & Value */}
        <g transform={`rotate(${-comp.rotation})`}>
          <text
            x="0"
            y={isGnd ? 24 : isVcc ? -24 : -22}
            textAnchor="middle"
            fill={isSelected ? '#22d3ee' : '#e2e8f0'}
            fontSize="11"
            fontWeight="bold"
            fontFamily="monospace"
          >
            {comp.ref_des}
          </text>
          {comp.value && !isGnd && (
            <text
              x="0"
              y="32"
              textAnchor="middle"
              fill="#94a3b8"
              fontSize="10"
              fontFamily="monospace"
            >
              {comp.value}
            </text>
          )}
        </g>

        {/* Pin Connection Dots */}
        {def?.pins.map(pin => {
          const isWireStart = wireStartPin?.instanceId === comp.instance_id && wireStartPin?.pinId === pin.pin_id;
          const isConnected = currentSheet?.nets.some(net =>
            net.connections.some(node => node.instance_id === comp.instance_id && node.pin_id === pin.pin_id)
          );

          return (
            <g key={pin.pin_id} transform={`translate(${pin.rel_x}, ${pin.rel_y})`}>
              <circle
                r="4.5"
                fill={isWireStart ? '#22d3ee' : (isConnected ? '#10b981' : '#f59e0b')}
                stroke="#0f172a"
                strokeWidth="1.5"
                className="hover:scale-150 transition-transform cursor-crosshair"
                onClick={(e) => {
                  const coords = getPinCanvasCoords(comp, pin.pin_id);
                  handlePinClick(comp.instance_id, pin.pin_id, coords.x, coords.y, e);
                }}
              />
              {/* Optional pin label */}
              {def.pins.length > 2 && (
                <text
                  x={pin.rel_x < 0 ? -7 : 7}
                  y="3"
                  textAnchor={pin.rel_x < 0 ? 'end' : 'start'}
                  fill="#64748b"
                  fontSize="8"
                  fontFamily="monospace"
                >
                  {pin.name}
                </text>
              )}
            </g>
          );
        })}
      </g>
    );
  };

  // Render Wire Nets
  const renderNets = () => {
    if (!currentSheet) return null;

    return (
      <g>
        {currentSheet.nets.map(net => {
          if (net.connections.length < 2) return null;

          // Connect nodes in sequence or tree
          const points: { x: number; y: number }[] = net.connections.map(node => {
            const comp = currentSheet.components.find(c => c.instance_id === node.instance_id);
            if (!comp) return { x: 0, y: 0 };
            return getPinCanvasCoords(comp, node.pin_id);
          });

          // Draw orthogonal connection paths
          return (
            <g key={net.net_id}>
              {points.slice(1).map((pt, i) => {
                const prev = points[i];
                const midX = pt.x;
                const pathStr = `M ${prev.x} ${prev.y} L ${midX} ${prev.y} L ${pt.x} ${pt.y}`;

                return (
                  <path
                    key={`seg_${i}`}
                    d={pathStr}
                    fill="none"
                    stroke={net.color || '#06b6d4'}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="hover:stroke-cyan-300 transition-colors"
                  />
                );
              })}

              {/* Junction dots */}
              {points.map((pt, idx) => (
                <circle
                  key={`dot_${idx}`}
                  cx={pt.x}
                  cy={pt.y}
                  r="3.5"
                  fill={net.color || '#06b6d4'}
                />
              ))}
            </g>
          );
        })}

        {/* Temporary wire preview while routing */}
        {wireStartPin && (
          <line
            x1={wireStartPin.x}
            y1={wireStartPin.y}
            x2={mousePos.x}
            y2={mousePos.y}
            stroke="#22d3ee"
            strokeWidth="2"
            strokeDasharray="4 4"
            className="animate-pulse"
          />
        )}
      </g>
    );
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-midnight-950 text-slate-100 overflow-hidden select-none">
      {/* Top Studio Header */}
      <div className="h-14 border-b border-slate-800 bg-midnight-900/90 backdrop-blur px-4 flex items-center justify-between z-20 shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-sm tracking-wide text-slate-100">
                Circuit Schematic Studio
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold">
                STAGE 27
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                {currentSheet?.title || 'Sheet 1'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              Interactive netlist EDA, DRC/ERC diagnostic rules, SPICE simulation & analytical solvers
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 bg-midnight-950 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('canvas')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
              activeTab === 'canvas'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Grid className="w-3.5 h-3.5" />
            <span>Canvas</span>
          </button>
          <button
            onClick={() => setActiveTab('erc')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
              activeTab === 'erc'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Shield className="w-3.5 h-3.5 text-rose-400" />
            <span>ERC Rules</span>
            {ercReport && ercReport.critical_count > 0 && (
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
            )}
          </button>
          <button
            onClick={() => setActiveTab('calculators')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
              activeTab === 'calculators'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Calculator className="w-3.5 h-3.5 text-amber-400" />
            <span>Calculators</span>
          </button>
          <button
            onClick={() => setActiveTab('simulation')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
              activeTab === 'simulation'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Play className="w-3.5 h-3.5 text-emerald-400" />
            <span>SPICE Sim</span>
          </button>
          <button
            onClick={() => setActiveTab('export')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
              activeTab === 'export'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            <span>BOM & Export</span>
          </button>
          <button
            onClick={() => setActiveTab('ai')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
              activeTab === 'ai'
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            <span>AI Designer</span>
          </button>
        </div>

        {/* Global Action Bar */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleRunERC}
            disabled={isErcRunning}
            className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 font-medium flex items-center gap-1.5 transition-colors border border-slate-700"
            title="Run Electrical Rule Checks (ERC)"
          >
            <Shield className="w-3.5 h-3.5 text-rose-400" />
            <span className="hidden md:inline">Run ERC</span>
          </button>
          <button
            onClick={handleRunSimulation}
            disabled={isSimRunning}
            className="px-2.5 py-1.5 rounded-lg bg-emerald-600/30 hover:bg-emerald-600/40 text-xs text-emerald-300 font-medium flex items-center gap-1.5 transition-colors border border-emerald-500/40"
            title="Simulate Operating Point"
          >
            <Play className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Simulate</span>
          </button>
          <button
            onClick={handleSaveProject}
            disabled={isLoading}
            className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-xs text-slate-950 font-bold flex items-center gap-1.5 transition-colors shadow-cyan-glow"
          >
            <FileCode className="w-3.5 h-3.5" />
            <span>Save Sheet</span>
          </button>
        </div>
      </div>

      {/* Floating Status Notification */}
      {statusMessage && (
        <div
          className={`absolute top-16 right-6 z-50 px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 shadow-xl border animate-fade-in ${
            statusMessage.type === 'success'
              ? 'bg-emerald-950/90 text-emerald-300 border-emerald-500/50'
              : statusMessage.type === 'error'
              ? 'bg-rose-950/90 text-rose-300 border-rose-500/50'
              : 'bg-cyan-950/90 text-cyan-300 border-cyan-500/50'
          }`}
        >
          {statusMessage.type === 'success' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
          {statusMessage.type === 'error' && <AlertCircle className="w-4 h-4 text-rose-400" />}
          {statusMessage.type === 'info' && <Info className="w-4 h-4 text-cyan-400" />}
          <span>{statusMessage.text}</span>
        </div>
      )}

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* ===================== TAB 1: INTERACTIVE CANVAS ===================== */}
        {activeTab === 'canvas' && (
          <div className="flex-1 flex overflow-hidden">
            {/* Left Component Palette Sidebar */}
            <div className="w-64 border-r border-slate-800 bg-midnight-900/60 flex flex-col shrink-0">
              <div className="p-3 border-b border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">Components</span>
                  <span className="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-1.5 py-0.5 rounded">
                    {filteredCatalog.length}
                  </span>
                </div>
                <input
                  type="text"
                  placeholder="Search catalog..."
                  value={searchCatalogQuery}
                  onChange={(e) => setSearchCatalogQuery(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
                {/* Category filters */}
                <div className="flex flex-wrap gap-1">
                  {['all', 'passive', 'semiconductor', 'power_source', 'integrated_circuit', 'logic_gate'].map((cat) => (
                    <button
                      key={cat}
                      onClick={() => setSelectedCategoryFilter(cat)}
                      className={`text-[10px] px-2 py-0.5 rounded-full capitalize font-medium transition-colors ${
                        selectedCategoryFilter === cat
                          ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                          : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {cat.replace('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>

              {/* Scrollable Catalog list */}
              <div className="flex-1 overflow-y-auto p-2 space-y-1.5 custom-scrollbar">
                {filteredCatalog.map((item) => (
                  <div
                    key={item.component_id}
                    onClick={() => handleAddComponent(item)}
                    className="p-2.5 rounded-xl bg-midnight-950/70 hover:bg-slate-800/60 border border-slate-800 hover:border-cyan-500/40 cursor-pointer transition-all group"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-xs text-slate-200 group-hover:text-cyan-300">
                        {item.name}
                      </span>
                      <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-slate-800 text-slate-400 uppercase">
                        {item.ref_des_prefix}
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-400 line-clamp-1 mt-0.5">{item.description}</p>
                    <div className="flex items-center justify-between mt-1 text-[9px] text-slate-500 font-mono">
                      <span>{item.pins.length} pins</span>
                      {item.default_value && <span>{item.default_value}</span>}
                    </div>
                  </div>
                ))}
              </div>

              {/* Sheet Summary Bar */}
              <div className="p-3 border-t border-slate-800 bg-midnight-950/80 text-[10px] font-mono text-slate-400 flex items-center justify-between">
                <span>Components: {currentSheet?.components.length || 0}</span>
                <span>Nets: {currentSheet?.nets.length || 0}</span>
              </div>
            </div>

            {/* Center Canvas Area */}
            <div className="flex-1 flex flex-col overflow-hidden relative">
              {/* Canvas Controls Toolbar */}
              <div className="h-10 border-b border-slate-800/80 bg-midnight-900/40 px-3 flex items-center justify-between z-10 shrink-0">
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={handleUndo}
                    disabled={historyIndex <= 0}
                    className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed text-xs"
                    title="Undo (Ctrl+Z)"
                  >
                    Undo
                  </button>
                  <button
                    onClick={handleRedo}
                    disabled={historyIndex >= history.length - 1}
                    className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed text-xs"
                    title="Redo (Ctrl+Y)"
                  >
                    Redo
                  </button>
                  <div className="h-4 w-px bg-slate-800 mx-1" />
                  <button
                    onClick={() => setSnapToGrid(!snapToGrid)}
                    className={`px-2 py-1 rounded text-xs flex items-center gap-1 font-mono ${
                      snapToGrid ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    <Grid className="w-3 h-3" />
                    <span>Snap Grid (20px)</span>
                  </button>
                  {wireStartPin && (
                    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-cyan-950 border border-cyan-500/50 text-[11px] text-cyan-300">
                      <span>Routing Net... Click destination pin</span>
                      <button
                        onClick={() => setWireStartPin(null)}
                        className="text-xs text-rose-400 hover:text-rose-300 ml-1 font-bold"
                      >
                        ✕
                      </button>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => setZoom(Math.max(0.4, zoom - 0.1))}
                    className="p-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300"
                    title="Zoom Out"
                  >
                    <ZoomOut className="w-3.5 h-3.5" />
                  </button>
                  <span className="text-[11px] font-mono text-slate-400 px-1">{Math.round(zoom * 100)}%</span>
                  <button
                    onClick={() => setZoom(Math.min(2.5, zoom + 0.1))}
                    className="p-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300"
                    title="Zoom In"
                  >
                    <ZoomIn className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => {
                      setZoom(1.0);
                      setPan({ x: 40, y: 40 });
                    }}
                    className="p-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300"
                    title="Reset View"
                  >
                    <Maximize2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* SVG Canvas Board */}
              <div
                className="flex-1 bg-midnight-950 overflow-hidden relative cursor-default"
                onMouseMove={(e) => {
                  if (canvasSvgRef.current) {
                    const rect = canvasSvgRef.current.getBoundingClientRect();
                    const rawX = (e.clientX - rect.left - pan.x) / zoom;
                    const rawY = (e.clientY - rect.top - pan.y) / zoom;
                    setMousePos({ x: Math.round(rawX), y: Math.round(rawY) });

                    if (draggedInstanceId && currentSheet) {
                      const snapGrid = (v: number) => snapToGrid ? Math.round(v / 20) * 20 : Math.round(v);
                      const updated = currentSheet.components.map(c => {
                        if (c.instance_id === draggedInstanceId) {
                          return { ...c, pos_x: snapGrid(rawX), pos_y: snapGrid(rawY) };
                        }
                        return c;
                      });
                      setCurrentSheet({ ...currentSheet, components: updated });
                    }
                  }
                }}
                onMouseUp={() => {
                  if (draggedInstanceId && currentSheet) {
                    setDraggedInstanceId(null);
                    pushToHistory(currentSheet);
                  }
                }}
                onClick={() => {
                  setSelectedInstanceId(null);
                }}
              >
                <svg
                  ref={canvasSvgRef}
                  className="w-full h-full"
                  style={{
                    backgroundImage: `radial-gradient(circle, rgba(148, 163, 184, 0.12) 1px, transparent 1px)`,
                    backgroundSize: `${20 * zoom}px ${20 * zoom}px`,
                    backgroundPosition: `${pan.x}px ${pan.y}px`
                  }}
                >
                  <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                    {/* Wires & Nets */}
                    {renderNets()}

                    {/* Component Instances */}
                    {currentSheet?.components.map((comp) => {
                      const isSelected = selectedInstanceId === comp.instance_id;
                      return (
                        <g
                          key={comp.instance_id}
                          onMouseDown={(e) => {
                            e.stopPropagation();
                            setSelectedInstanceId(comp.instance_id);
                            setDraggedInstanceId(comp.instance_id);
                          }}
                        >
                          {renderComponentSymbol(comp, isSelected)}
                        </g>
                      );
                    })}
                  </g>
                </svg>
              </div>
            </div>

            {/* Right Inspector Panel */}
            <div className="w-72 border-l border-slate-800 bg-midnight-900/60 flex flex-col shrink-0 p-3 space-y-4 overflow-y-auto custom-scrollbar">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">Inspector</span>
                {selectedInstance && (
                  <span className="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded">
                    {selectedInstance.ref_des}
                  </span>
                )}
              </div>

              {selectedInstance ? (
                <div className="space-y-3">
                  <div>
                    <label className="text-[11px] font-semibold text-slate-400">Reference Designator</label>
                    <input
                      type="text"
                      value={selectedInstance.ref_des}
                      onChange={(e) => {
                        if (!currentSheet) return;
                        const updated = currentSheet.components.map(c =>
                          c.instance_id === selectedInstance.instance_id ? { ...c, ref_des: e.target.value } : c
                        );
                        setCurrentSheet({ ...currentSheet, components: updated });
                      }}
                      className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-slate-400">Component Value / Part</label>
                    <input
                      type="text"
                      value={selectedInstance.value}
                      placeholder="e.g. 10k, 100nF, 2N3904"
                      onChange={(e) => {
                        if (!currentSheet) return;
                        const updated = currentSheet.components.map(c =>
                          c.instance_id === selectedInstance.instance_id ? { ...c, value: e.target.value } : c
                        );
                        setCurrentSheet({ ...currentSheet, components: updated });
                      }}
                      className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2 rounded-lg bg-midnight-950 border border-slate-800">
                      <span className="text-[10px] text-slate-500 block">Category</span>
                      <span className="font-semibold text-slate-300 capitalize">{selectedDef?.category || 'part'}</span>
                    </div>
                    <div className="p-2 rounded-lg bg-midnight-950 border border-slate-800">
                      <span className="text-[10px] text-slate-500 block">Rotation</span>
                      <span className="font-semibold text-slate-300 font-mono">{selectedInstance.rotation}°</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
                    <button
                      onClick={() => handleRotateComponent(selectedInstance.instance_id)}
                      className="flex-1 py-1.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <RotateCw className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Rotate</span>
                    </button>
                    <button
                      onClick={() => handleDeleteComponent(selectedInstance.instance_id)}
                      className="py-1.5 px-3 rounded-lg bg-rose-950/50 hover:bg-rose-900/50 text-xs font-semibold text-rose-300 border border-rose-500/40 flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Delete</span>
                    </button>
                  </div>

                  {/* Pin status table */}
                  {selectedDef && (
                    <div className="pt-2 border-t border-slate-800">
                      <span className="text-[11px] font-semibold text-slate-400 block mb-1.5">Pin Connections</span>
                      <div className="space-y-1">
                        {selectedDef.pins.map(pin => {
                          const connectedNet = currentSheet?.nets.find(n =>
                            n.connections.some(node => node.instance_id === selectedInstance.instance_id && node.pin_id === pin.pin_id)
                          );
                          return (
                            <div key={pin.pin_id} className="p-1.5 rounded bg-midnight-950/80 border border-slate-800/80 flex items-center justify-between text-[10px] font-mono">
                              <span className="text-slate-300">{pin.pin_number || pin.pin_id} ({pin.name})</span>
                              {connectedNet ? (
                                <span className="text-emerald-400">{connectedNet.name}</span>
                              ) : (
                                <span className="text-amber-400">UNCONNECTED</span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-12 text-slate-500 space-y-2">
                  <Cpu className="w-8 h-8 mx-auto text-slate-600" />
                  <p className="text-xs">No component selected.</p>
                  <p className="text-[10px] text-slate-600">Click a component on the canvas to inspect its parameters and pin connections.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ===================== TAB 2: ELECTRICAL RULE CHECKS (ERC) ===================== */}
        {activeTab === 'erc' && (
          <div className="flex-1 p-6 overflow-y-auto space-y-6 custom-scrollbar max-w-5xl mx-auto w-full">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                  <Shield className="w-5 h-5 text-rose-400" />
                  <span>Electrical Rule Check (ERC) Diagnostics</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Topological static analysis checking floating inputs, power conflicts, missing GND, and net validity.
                </p>
              </div>
              <button
                onClick={handleRunERC}
                disabled={isErcRunning}
                className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-xs font-bold text-slate-950 flex items-center gap-2 shadow-cyan-glow"
              >
                <RefreshCw className={`w-4 h-4 ${isErcRunning ? 'animate-spin' : ''}`} />
                <span>Re-run ERC</span>
              </button>
            </div>

            {/* Non-Physical Safety Disclaimer Banner */}
            <div className="p-3.5 rounded-xl bg-amber-950/30 border border-amber-500/40 text-amber-200 text-xs flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold block">Engineering Verification Notice:</span>
                <p className="text-[11px] text-amber-300/90 mt-0.5">
                  Static schematic rule checks verify logical topology and obvious rating boundaries. They do not replace thermal dissipation testing, RF signal integrity simulation, or physical hardware breadboarding. Always confirm component datasheet limits.
                </p>
              </div>
            </div>

            {ercReport ? (
              <div className="space-y-4">
                {/* Summary badges */}
                <div className="grid grid-cols-4 gap-3">
                  <div className="p-3 rounded-xl bg-midnight-900 border border-slate-800">
                    <span className="text-[11px] text-slate-400 block">Status</span>
                    <span className={`text-sm font-bold capitalize ${ercReport.critical_count === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {ercReport.critical_count === 0 ? 'Passed (Clean)' : 'Issues Detected'}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-midnight-900 border border-slate-800">
                    <span className="text-[11px] text-slate-400 block">Critical Violations</span>
                    <span className="text-sm font-bold text-rose-400 font-mono">{ercReport.critical_count}</span>
                  </div>
                  <div className="p-3 rounded-xl bg-midnight-900 border border-slate-800">
                    <span className="text-[11px] text-slate-400 block">Warnings</span>
                    <span className="text-sm font-bold text-amber-400 font-mono">{ercReport.warning_count}</span>
                  </div>
                  <div className="p-3 rounded-xl bg-midnight-900 border border-slate-800">
                    <span className="text-[11px] text-slate-400 block">Total Checks</span>
                    <span className="text-sm font-bold text-cyan-400 font-mono">{ercReport.total_findings}</span>
                  </div>
                </div>

                {/* Findings list */}
                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Diagnostic Findings ({ercReport.findings.length})</h3>
                  {ercReport.findings.length === 0 ? (
                    <div className="p-8 text-center rounded-xl bg-midnight-900/60 border border-slate-800 text-slate-400 space-y-2">
                      <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-400" />
                      <p className="text-sm font-semibold text-slate-200">No ERC Violations</p>
                      <p className="text-xs text-slate-500">Every placed pin is connected, power rails and grounds are assigned properly.</p>
                    </div>
                  ) : (
                    ercReport.findings.map((item, idx) => (
                      <div
                        key={idx}
                        className={`p-3.5 rounded-xl border flex items-start justify-between gap-4 ${
                          item.severity === 'critical'
                            ? 'bg-rose-950/20 border-rose-500/40 text-rose-200'
                            : item.severity === 'warning'
                            ? 'bg-amber-950/20 border-amber-500/40 text-amber-200'
                            : 'bg-cyan-950/20 border-cyan-500/40 text-cyan-200'
                        }`}
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded uppercase bg-slate-900/80 border border-slate-800">
                              {item.rule_code}
                            </span>
                            <span className="text-xs font-semibold">{item.title}</span>
                          </div>
                          <p className="text-[11px] text-slate-300">{item.message}</p>
                          {item.remediation_steps && (
                            <p className="text-[11px] text-cyan-300 font-medium">
                              💡 Fix hint: {item.remediation_steps}
                            </p>
                          )}
                        </div>
                        <div className="text-right shrink-0">
                          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                            item.severity === 'critical' ? 'bg-rose-500/20 text-rose-300' : 'bg-amber-500/20 text-amber-300'
                          }`}>
                            {item.severity}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-16 text-slate-500 space-y-3">
                <Shield className="w-10 h-10 mx-auto text-slate-600" />
                <p className="text-sm">Click "Re-run ERC" to validate current schematic topology.</p>
              </div>
            )}
          </div>
        )}

        {/* ===================== TAB 3: ENGINEERING CALCULATORS ===================== */}
        {activeTab === 'calculators' && (
          <div className="flex-1 flex overflow-hidden">
            {/* Left Calculator Selector */}
            <div className="w-60 border-r border-slate-800 bg-midnight-900/60 p-3 space-y-1.5 shrink-0">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2 px-1">
                Calculators
              </span>
              {[
                { id: 'divider', name: 'Voltage Divider', desc: 'E24 resistor selection & load' },
                { id: 'led', name: 'LED Current Limiter', desc: 'Forward drop & standard E24' },
                { id: 'rc', name: 'RC Filter & Cutoff', desc: 'Time constant & corner freq' },
                { id: 'bjt', name: 'BJT Saturation Bias', desc: 'Base overdrive & collector saturation' },
                { id: 'thermal', name: 'Thermal & Dissipation', desc: 'Junction temp & heatsink reqs' },
                { id: 'ohms', name: "Ohm's & Power Law", desc: 'V, I, R, P quadrant solver' },
                { id: 'logic', name: 'Logic Expression', desc: 'Multi-variable truth table' }
              ].map(calc => (
                <button
                  key={calc.id}
                  onClick={() => setActiveCalc(calc.id as any)}
                  className={`w-full text-left p-2.5 rounded-xl transition-all ${
                    activeCalc === calc.id
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                      : 'hover:bg-slate-800/60 text-slate-300'
                  }`}
                >
                  <div className="font-semibold text-xs">{calc.name}</div>
                  <div className="text-[10px] text-slate-400">{calc.desc}</div>
                </button>
              ))}
            </div>

            {/* Right Calculator Workspace */}
            <div className="flex-1 p-6 overflow-y-auto custom-scrollbar max-w-4xl mx-auto w-full space-y-6">
              {/* OHM'S LAW */}
              {activeCalc === 'ohms' && (
                <div className="space-y-4">
                  <h3 className="text-base font-bold text-slate-100">Ohm's & Power Law Calculator</h3>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Voltage V (Volts)</label>
                      <input
                        type="number"
                        value={ohmsV}
                        placeholder="Leave blank to solve"
                        onChange={(e) => setOhmsV(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Current I (Amperes)</label>
                      <input
                        type="number"
                        value={ohmsI}
                        placeholder="Leave blank to solve"
                        onChange={(e) => setOhmsI(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Resistance R (Ohms)</label>
                      <input
                        type="number"
                        value={ohmsR}
                        placeholder="Leave blank to solve"
                        onChange={(e) => setOhmsR(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handleCalcOhmsLaw}
                    className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-xs font-bold text-slate-950"
                  >
                    Solve Unknowns
                  </button>
                  {ohmsResult && (
                    <div className="p-4 rounded-xl bg-midnight-900 border border-slate-800 space-y-2 font-mono text-xs">
                      <div className="flex justify-between border-b border-slate-800 pb-1">
                        <span className="text-slate-400">Voltage:</span>
                        <span className="text-cyan-300 font-bold">{ohmsResult.voltage_v.toFixed(3)} V</span>
                      </div>
                      <div className="flex justify-between border-b border-slate-800 pb-1">
                        <span className="text-slate-400">Current:</span>
                        <span className="text-emerald-400 font-bold">{(ohmsResult.current_a * 1000).toFixed(2)} mA ({ohmsResult.current_a.toFixed(4)} A)</span>
                      </div>
                      <div className="flex justify-between border-b border-slate-800 pb-1">
                        <span className="text-slate-400">Resistance:</span>
                        <span className="text-slate-200 font-bold">{ohmsResult.resistance_ohms.toFixed(2)} Ω</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Power Dissipation:</span>
                        <span className="text-amber-300 font-bold">{ohmsResult.power_w.toFixed(3)} W ({ohmsResult.recommended_wattage_rating})</span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* VOLTAGE DIVIDER */}
              {activeCalc === 'divider' && (
                <div className="space-y-4">
                  <h3 className="text-base font-bold text-slate-100">Voltage Divider Calculator</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Vin (Volts)</label>
                      <input
                        type="number"
                        value={vdVin}
                        onChange={(e) => setVdVin(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">R1 (Ohms)</label>
                      <input
                        type="number"
                        value={vdR1}
                        onChange={(e) => setVdR1(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">R2 (Ohms)</label>
                      <input
                        type="number"
                        value={vdR2}
                        onChange={(e) => setVdR2(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Rload (Optional)</label>
                      <input
                        type="number"
                        value={vdRload}
                        placeholder="None (ideal)"
                        onChange={(e) => setVdRload(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handleCalcVoltageDivider}
                    className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-xs font-bold text-slate-950"
                  >
                    Calculate Output
                  </button>
                  {vdResult && (
                    <div className="p-4 rounded-xl bg-midnight-900 border border-slate-800 space-y-2 font-mono text-xs">
                      <div className="flex justify-between border-b border-slate-800 pb-1">
                        <span className="text-slate-400">Ideal Output Voltage:</span>
                        <span className="text-cyan-300 font-bold">{vdResult.ideal_vout_v.toFixed(3)} V</span>
                      </div>
                      {vdResult.loaded_vout_v !== undefined && vdResult.loaded_vout_v !== null && (
                        <div className="flex justify-between border-b border-slate-800 pb-1">
                          <span className="text-slate-400">Loaded Output Voltage:</span>
                          <span className="text-amber-300 font-bold">{vdResult.loaded_vout_v.toFixed(3)} V</span>
                        </div>
                      )}
                      <div className="flex justify-between border-b border-slate-800 pb-1">
                        <span className="text-slate-400">Quiescent Current:</span>
                        <span className="text-slate-200">{vdResult.quiescent_current_ma.toFixed(3)} mA</span>
                      </div>
                      {vdResult.recommended_pairs && vdResult.recommended_pairs.length > 0 && (
                        <div className="text-[11px] text-cyan-400 pt-1">
                          Standard E24 pair: R1 = {vdResult.recommended_pairs[0].r1_ohms}Ω, R2 = {vdResult.recommended_pairs[0].r2_ohms}Ω (Vout: {vdResult.recommended_pairs[0].actual_vout_v.toFixed(3)} V)
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* LED CURRENT LIMITER */}
              {activeCalc === 'led' && (
                <div className="space-y-4">
                  <h3 className="text-base font-bold text-slate-100">LED Current Limiting Resistor</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Supply Voltage (V)</label>
                      <input
                        type="number"
                        value={ledVsupply}
                        onChange={(e) => setLedVsupply(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Forward Drop Vf (V)</label>
                      <input
                        type="number"
                        value={ledVforward}
                        onChange={(e) => setLedVforward(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Target Current (mA)</label>
                      <input
                        type="number"
                        value={ledTargetMa}
                        onChange={(e) => setLedTargetMa(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">LED Color</label>
                      <select
                        value={ledColor}
                        onChange={(e) => setLedColor(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      >
                        <option value="red">Red (~2.0V)</option>
                        <option value="green">Green (~2.2V)</option>
                        <option value="blue">Blue (~3.2V)</option>
                        <option value="white">White (~3.3V)</option>
                      </select>
                    </div>
                  </div>
                  <button
                    onClick={handleCalcLED}
                    className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-xs font-bold text-slate-950"
                  >
                    Calculate Resistor
                  </button>
                  {ledResult && (
                    <div className="p-4 rounded-xl bg-midnight-900 border border-slate-800 space-y-2 font-mono text-xs">
                      <div className="flex justify-between border-b border-slate-800 pb-1">
                        <span className="text-slate-400">Exact Theoretical Resistance:</span>
                        <span className="text-slate-200">{ledResult.calculated_resistance_ohms.toFixed(1)} Ω</span>
                      </div>
                      <div className="flex justify-between border-b border-slate-800 pb-1">
                        <span className="text-slate-400">Nearest Standard E24 Resistor:</span>
                        <span className="text-emerald-400 font-bold">{ledResult.standard_e24_resistor_ohms} Ω</span>
                      </div>
                      <div className="flex justify-between border-b border-slate-800 pb-1">
                        <span className="text-slate-400">Resistor Power Dissipation:</span>
                        <span className="text-amber-300">{ledResult.resistor_power_dissipation_mw.toFixed(1)} mW (Min: {ledResult.recommended_resistor_power_rating})</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Actual LED Operating Current:</span>
                        <span className="text-cyan-300 font-bold">{ledResult.actual_current_with_e24_ma.toFixed(2)} mA</span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* RC FILTER */}
              {activeCalc === 'rc' && (
                <div className="space-y-4">
                  <h3 className="text-base font-bold text-slate-100">RC Time Constant & Cutoff Frequency</h3>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Resistance R (Ω)</label>
                      <input
                        type="number"
                        value={rcR}
                        onChange={(e) => setRcR(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Capacitance C (Farads)</label>
                      <input
                        type="text"
                        value={rcC}
                        placeholder="1e-7 (100nF)"
                        onChange={(e) => setRcC(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Filter Topology</label>
                      <select
                        value={rcType}
                        onChange={(e) => setRcType(e.target.value as any)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      >
                        <option value="lowpass">Low-Pass Filter</option>
                        <option value="highpass">High-Pass Filter</option>
                      </select>
                    </div>
                  </div>
                  <button
                    onClick={handleCalcRC}
                    className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-xs font-bold text-slate-950"
                  >
                    Compute Frequency Response
                  </button>
                  {rcResult && (
                    <div className="p-4 rounded-xl bg-midnight-900 border border-slate-800 space-y-2 font-mono text-xs">
                      <div className="flex justify-between border-b border-slate-800 pb-1">
                        <span className="text-slate-400">Time Constant (τ = R·C):</span>
                        <span className="text-cyan-300 font-bold">{rcResult.tau_formatted}</span>
                      </div>
                      <div className="flex justify-between border-b border-slate-800 pb-1">
                        <span className="text-slate-400">Cutoff Frequency (-3dB fc):</span>
                        <span className="text-emerald-400 font-bold">{rcResult.cutoff_frequency_formatted}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Settling Time (to 95%):</span>
                        <span className="text-slate-200">{(rcResult.time_to_95_pct_seconds * 1000).toFixed(3)} ms</span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* BJT SATURATION BIAS */}
              {activeCalc === 'bjt' && (
                <div className="space-y-4">
                  <h3 className="text-base font-bold text-slate-100">BJT Transistor Saturation Bias Switch</h3>
                  <div className="grid grid-cols-4 gap-3">
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Vcc (V)</label>
                      <input
                        type="number"
                        value={bjtVcc}
                        onChange={(e) => setBjtVcc(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Load Ic (mA)</label>
                      <input
                        type="number"
                        value={bjtIcMa}
                        onChange={(e) => setBjtIcMa(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Control Vin (V)</label>
                      <input
                        type="number"
                        value={bjtVin}
                        onChange={(e) => setBjtVin(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">hFE / Beta (Min)</label>
                      <input
                        type="number"
                        value={bjtHfe}
                        onChange={(e) => setBjtHfe(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handleCalcBJT}
                    className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-xs font-bold text-slate-950"
                  >
                    Calculate Base Resistor Rb
                  </button>
                  {bjtResult && (
                    <div className="p-4 rounded-xl bg-midnight-900 border border-slate-800 space-y-2 font-mono text-xs">
                      <div className="flex justify-between border-b border-slate-800 pb-1">
                        <span className="text-slate-400">Recommended Base Resistor Rb:</span>
                        <span className="text-emerald-400 font-bold">{bjtResult.standard_e24_base_resistor_ohms} Ω</span>
                      </div>
                      <div className="flex justify-between border-b border-slate-800 pb-1">
                        <span className="text-slate-400">Required Base Current:</span>
                        <span className="text-cyan-300">{bjtResult.required_base_current_ma.toFixed(2)} mA</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Saturation Status:</span>
                        <span className="text-emerald-400 font-bold">{bjtResult.saturation_confirmed ? 'CONFIRMED SATURATED' : 'ACTIVE REGION'}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* THERMAL & DISSIPATION */}
              {activeCalc === 'thermal' && (
                <div className="space-y-4">
                  <h3 className="text-base font-bold text-slate-100">Thermal Dissipation & Heatsink Calculator</h3>
                  <div className="grid grid-cols-4 gap-3">
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Vin (V)</label>
                      <input
                        type="number"
                        value={thVin}
                        onChange={(e) => setThVin(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Vout (V)</label>
                      <input
                        type="number"
                        value={thVout}
                        onChange={(e) => setThVout(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Load Current (mA)</label>
                      <input
                        type="number"
                        value={thIload}
                        onChange={(e) => setThIload(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400">Package Type</label>
                      <select
                        value={thPackage}
                        onChange={(e) => setThPackage(e.target.value)}
                        className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200"
                      >
                        <option value="TO-220">TO-220 (Linear)</option>
                        <option value="SOT-223">SOT-223 (SMD)</option>
                        <option value="TO-92">TO-92 (Low Power)</option>
                        <option value="DPAK">DPAK (Surface Mount)</option>
                      </select>
                    </div>
                  </div>
                  <button
                    onClick={handleCalcThermal}
                    className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-xs font-bold text-slate-950"
                  >
                    Analyze Heatsink Need
                  </button>
                  {thResult && (
                    <div className="p-4 rounded-xl bg-midnight-900 border border-slate-800 space-y-2 font-mono text-xs">
                      <div className="flex justify-between border-b border-slate-800 pb-1">
                        <span className="text-slate-400">Junction Temp Without Heatsink:</span>
                        <span className={`font-bold ${thResult.estimated_junction_temp_c > 100 ? 'text-rose-400' : 'text-emerald-400'}`}>
                          {thResult.estimated_junction_temp_c.toFixed(1)} °C
                        </span>
                      </div>
                      <div className="flex justify-between border-b border-slate-800 pb-1">
                        <span className="text-slate-400">Heatsink Required:</span>
                        <span className={`font-bold ${thResult.heatsink_required ? 'text-rose-400' : 'text-emerald-400'}`}>
                          {thResult.heatsink_required ? 'YES (OVERHEATING RISK)' : 'NO (FREE AIR SUFFICIENT)'}
                        </span>
                      </div>
                      {thResult.recommended_heatsink_thermal_resistance_c_per_w !== null && thResult.recommended_heatsink_thermal_resistance_c_per_w !== undefined && (
                        <div className="flex justify-between">
                          <span className="text-slate-400">Required Heatsink Rating:</span>
                          <span className="text-cyan-300 font-bold">≤ {thResult.recommended_heatsink_thermal_resistance_c_per_w.toFixed(1)} °C/W</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* LOGIC EXPRESSION TRUTH TABLE */}
              {activeCalc === 'logic' && (
                <div className="space-y-4">
                  <h3 className="text-base font-bold text-slate-100">Logic Expression Truth Table</h3>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-400">Boolean Expression (Python/C syntax: and, or, not, ^)</label>
                    <input
                      type="text"
                      value={logicExpr}
                      onChange={(e) => setLogicExpr(e.target.value)}
                      className="w-full mt-1 px-2.5 py-1.5 text-xs rounded-lg bg-midnight-950 border border-slate-800 text-slate-200 font-mono"
                    />
                  </div>
                  <button
                    onClick={handleCalcLogic}
                    className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-xs font-bold text-slate-950"
                  >
                    Generate Truth Table
                  </button>
                  {logicResult && (
                    <div className="space-y-2">
                      <div className="text-xs font-mono text-slate-400">Variables: {logicResult.variables.join(', ')}</div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs font-mono border border-slate-800 rounded-lg">
                          <thead>
                            <tr className="bg-midnight-950 text-slate-400 border-b border-slate-800">
                              {logicResult.variables.map(v => (
                                <th key={v} className="p-2 text-center">{v}</th>
                              ))}
                              <th className="p-2 text-center text-cyan-400">Output</th>
                            </tr>
                          </thead>
                          <tbody>
                            {logicResult.truth_table.map((row, rIdx) => (
                              <tr key={rIdx} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                                {logicResult.variables.map(v => (
                                  <td key={v} className="p-2 text-center text-slate-300">{row[v]}</td>
                                ))}
                                <td className={`p-2 text-center font-bold ${row['output'] === 1 ? 'text-emerald-400' : 'text-slate-500'}`}>
                                  {row['output']}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ===================== TAB 4: SPICE & SIMULATION ===================== */}
        {activeTab === 'simulation' && (
          <div className="flex-1 p-6 overflow-y-auto space-y-6 custom-scrollbar max-w-5xl mx-auto w-full">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                  <Play className="w-5 h-5 text-emerald-400" />
                  <span>SPICE Simulation & Operating Point Solver</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Generates standard Berkeley SPICE netlist (.cir), runs local ngspice or analytical linear solver.
                </p>
              </div>
              <button
                onClick={handleRunSimulation}
                disabled={isSimRunning}
                className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-slate-950 flex items-center gap-2 shadow-emerald-glow"
              >
                <Play className="w-4 h-4" />
                <span>Simulate Active Sheet</span>
              </button>
            </div>

            {simulationResult ? (
              <div className="space-y-4">
                {/* Engine status banner */}
                <div className="p-3.5 rounded-xl bg-midnight-900 border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <Activity className="w-4 h-4 text-cyan-400" />
                    <div>
                      <span className="text-xs font-semibold text-slate-200">Execution Engine: </span>
                      <span className="text-xs font-mono font-bold text-cyan-400 uppercase">
                        {simulationResult.sim_status} ({simulationResult.engine_name})
                      </span>
                    </div>
                  </div>
                  <span className="text-[11px] font-mono text-slate-500">
                    Mode: {simulationResult.analysis_type}
                  </span>
                </div>

                {/* Node Voltages Table */}
                {Object.keys(simulationResult.node_voltages || {}).length > 0 && (
                  <div className="p-4 rounded-xl bg-midnight-900 border border-slate-800 space-y-2">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">DC Node Voltages</h3>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      {Object.entries(simulationResult.node_voltages || {}).map(([node, v]) => (
                        <div key={node} className="p-2 rounded bg-midnight-950 border border-slate-800 font-mono text-xs flex justify-between">
                          <span className="text-slate-400">{node}:</span>
                          <span className="text-emerald-400 font-bold">{(v as number).toFixed(3)} V</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Branch Currents Table */}
                {Object.keys(simulationResult.branch_currents || {}).length > 0 && (
                  <div className="p-4 rounded-xl bg-midnight-900 border border-slate-800 space-y-2">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Branch Currents</h3>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      {Object.entries(simulationResult.branch_currents || {}).map(([branch, i]) => (
                        <div key={branch} className="p-2 rounded bg-midnight-950 border border-slate-800 font-mono text-xs flex justify-between">
                          <span className="text-slate-400">{branch}:</span>
                          <span className="text-cyan-400 font-bold">{((i as number) * 1000).toFixed(2)} mA</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Raw SPICE Netlist Inspector */}
                <div className="p-4 rounded-xl bg-midnight-900 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Generated SPICE Netlist (.cir)</h3>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(simulationResult.netlist_text);
                        showNotification('SPICE netlist copied to clipboard', 'success');
                      }}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] text-cyan-300 font-mono flex items-center gap-1"
                    >
                      <Copy className="w-3 h-3" />
                      <span>Copy Netlist</span>
                    </button>
                  </div>
                  <pre className="p-3 rounded-lg bg-midnight-950 border border-slate-800 font-mono text-[11px] text-emerald-300/90 overflow-x-auto">
                    {simulationResult.netlist_text}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="text-center py-16 text-slate-500 space-y-3">
                <Terminal className="w-10 h-10 mx-auto text-slate-600" />
                <p className="text-sm">Click "Simulate Active Sheet" to compile the netlist and solve node operating points.</p>
              </div>
            )}
          </div>
        )}

        {/* ===================== TAB 5: BOM & EXPORTS ===================== */}
        {activeTab === 'export' && (
          <div className="flex-1 p-6 overflow-y-auto space-y-6 custom-scrollbar max-w-5xl mx-auto w-full">
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <Download className="w-5 h-5 text-cyan-400" />
                <span>Multi-Format Schematic & BOM Export</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Generate SPICE netlists, KiCad netlists, Bill of Materials (BOM CSV/JSON), and standalone SVG drawings.
              </p>
            </div>

            {/* Export Format Selector */}
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
              {[
                { id: 'spice', name: 'SPICE (.cir)' },
                { id: 'kicad', name: 'KiCad (.net)' },
                { id: 'bom_csv', name: 'BOM CSV' },
                { id: 'bom_json', name: 'BOM JSON' },
                { id: 'connection_table', name: 'Net Table' },
                { id: 'svg', name: 'SVG Drawing' }
              ].map(fmt => (
                <button
                  key={fmt.id}
                  onClick={() => handleExport(fmt.id as any)}
                  className={`p-2.5 rounded-xl text-center text-xs font-semibold border transition-all ${
                    exportFormat === fmt.id && exportResult
                      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 shadow-sm'
                      : 'bg-midnight-900 border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  {fmt.name}
                </button>
              ))}
            </div>

            {exportResult && (
              <div className="p-4 rounded-xl bg-midnight-900 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-slate-200">{exportResult.filename}</span>
                    <span className="text-[10px] text-slate-500 ml-2 font-mono">({exportResult.mime_type})</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(exportResult.content);
                        showNotification('Export content copied', 'success');
                      }}
                      className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 font-mono flex items-center gap-1.5"
                    >
                      <Copy className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Copy</span>
                    </button>
                    <button
                      onClick={() => {
                        const blob = new Blob([exportResult.content], { type: exportResult.mime_type });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = exportResult.filename;
                        a.click();
                        URL.revokeObjectURL(url);
                        showNotification('File downloaded', 'success');
                      }}
                      className="px-3 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-xs text-slate-950 font-bold flex items-center gap-1.5"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download</span>
                    </button>
                  </div>
                </div>

                <pre className="p-4 rounded-lg bg-midnight-950 border border-slate-800 font-mono text-xs text-slate-200 overflow-x-auto max-h-96">
                  {exportResult.content}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* ===================== TAB 6: AI CIRCUIT DESIGN ASSISTANT ===================== */}
        {activeTab === 'ai' && (
          <div className="flex-1 p-6 overflow-y-auto space-y-6 custom-scrollbar max-w-5xl mx-auto w-full">
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-purple-400" />
                <span>AI Circuit Design Assistant</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Describe desired circuit behavior in natural language; NEXORA synthesizes a complete schematic sheet with engineering justification.
              </p>
            </div>

            {/* Prompt input card */}
            <div className="p-4 rounded-xl bg-midnight-900 border border-slate-800 space-y-3">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">Circuit Goal / Prompt</label>
              <textarea
                rows={3}
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                placeholder="Describe circuit function, inputs, outputs, voltages..."
                className="w-full p-3 rounded-lg bg-midnight-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-purple-500 resize-none font-mono"
              />
              {/* Presets */}
              <div className="flex flex-wrap gap-1.5 text-[10px]">
                <span className="text-slate-500 py-1">Quick Presets:</span>
                {[
                  '5V to 3.3V LDO regulator with filter caps and indicator LED',
                  'Astabel multivibrator LED flasher with 555 timer',
                  'Op-amp non-inverting amplifier with gain of 10'
                ].map((preset, i) => (
                  <button
                    key={i}
                    onClick={() => setAiPrompt(preset)}
                    className="px-2 py-0.5 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300"
                  >
                    {preset.split('with')[0]}
                  </button>
                ))}
              </div>
              <button
                onClick={handleGenerateAICircuit}
                disabled={aiLoading || !aiPrompt.trim()}
                className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-xs font-bold text-slate-100 flex items-center gap-2 shadow-purple-glow"
              >
                <Sparkles className={`w-4 h-4 ${aiLoading ? 'animate-spin' : ''}`} />
                <span>{aiLoading ? 'Synthesizing Circuit...' : 'Synthesize Schematic'}</span>
              </button>
            </div>

            {aiDesignResponse && (
              <div className="space-y-4">
                {/* Mandatory Engineering Review Banner */}
                <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/50 text-amber-200 text-xs space-y-1">
                  <div className="flex items-center gap-2 font-bold text-amber-300">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    <span>Mandatory Engineering Verification Warning</span>
                  </div>
                  <p className="text-[11px] text-amber-200/90">
                    {aiDesignResponse.review_banner}
                  </p>
                </div>

                {/* Circuit Info Card */}
                <div className="p-4 rounded-xl bg-midnight-900 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-bold text-sm text-slate-100">{aiDesignResponse.circuit_name}</h3>
                      <p className="text-xs text-slate-400 mt-0.5">{aiDesignResponse.operational_explanation}</p>
                    </div>
                    <button
                      onClick={handleLoadAISheet}
                      className="px-3.5 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-xs font-bold text-slate-950 flex items-center gap-1.5 shadow-cyan-glow"
                    >
                      <ArrowRight className="w-3.5 h-3.5" />
                      <span>Load into Canvas</span>
                    </button>
                  </div>

                  {/* Component list */}
                  <div className="pt-2 border-t border-slate-800">
                    <span className="text-[11px] font-semibold text-slate-400 block mb-1">Synthesized Components:</span>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      {aiDesignResponse.sheet.components.map(c => (
                        <div key={c.instance_id} className="p-2 rounded bg-midnight-950 border border-slate-800 text-xs font-mono">
                          <span className="text-cyan-400 font-bold">{c.ref_des}: </span>
                          <span className="text-slate-300">{c.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Design notes */}
                  {aiDesignResponse.design_notes.length > 0 && (
                    <div className="pt-2 border-t border-slate-800 space-y-1">
                      <span className="text-[11px] font-semibold text-slate-400 block">Design Notes & Formulas:</span>
                      <ul className="list-disc list-inside text-[11px] text-slate-300 space-y-0.5">
                        {aiDesignResponse.design_notes.map((note, idx) => (
                          <li key={idx}>{note}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
