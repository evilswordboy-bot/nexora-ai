import React, { useEffect, useState } from 'react';
import {
  Cpu,
  Zap,
  CircuitBoard,
  Code2,
  Play,
  ShieldAlert,
  FileSpreadsheet,
  Download,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Plus,
  RefreshCw,
  Wifi,
  ExternalLink,
  Wrench,
  Layers,
} from 'lucide-react';
import { api } from '../../services/api';
import {
  IoTBoardId,
  IoTBoardProfile,
  IoTComponentSpec,
  IoTConnectivityProtocol,
  IoTEnvironmentType,
  IoTFirmwareLanguage,
  IoTMetadataResponse,
  IoTPowerSource,
  IoTProjectExportResponse,
  IoTProjectRecord,
  IoTSimulationResponse,
  IoTWireConnection,
} from '../../types';
import { useChat } from '../../context/ChatContext';

type StudioTab =
  | 'designer'
  | 'components'
  | 'wiring'
  | 'firmware'
  | 'simulator'
  | 'docs_safety_export';

export const IoTProjectBuilderStudio: React.FC = () => {
  const { showToast } = useChat();

  const [activeTab, setActiveTab] = useState<StudioTab>('designer');
  const [metadata, setMetadata] = useState<IoTMetadataResponse | null>(null);
  const [boards, setBoards] = useState<IoTBoardProfile[]>([]);
  const [components, setComponents] = useState<IoTComponentSpec[]>([]);
  const [projects, setProjects] = useState<IoTProjectRecord[]>([]);
  const [selectedProject, setSelectedProject] = useState<IoTProjectRecord | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // Designer form state
  const [projName, setProjName] = useState('Autonomous Solar Greenhouse Controller');
  const [projDesc, setProjDesc] = useState(
    'ESP32 node reading BME280 ambient temperature/humidity and capacitive soil moisture, displaying status on an SSD1306 OLED screen, and controlling an optocoupled 5V irrigation relay over MQTT.'
  );
  const [projBudget, setProjBudget] = useState<number>(45);
  const [projPower, setProjPower] = useState<IoTPowerSource>('usb_5v');
  const [projEnv, setProjEnv] = useState<IoTEnvironmentType>('greenhouse_humid');
  const [projBoardId, setProjBoardId] = useState<IoTBoardId>('esp32_devkit_v1');
  const [projCompIds, setProjCompIds] = useState<string[]>([
    'bme280_sensor',
    'soil_moisture_capacitive',
    'ssd1306_oled_i2c',
    'relay_module_5v_optocoupled',
  ]);
  const [projLang, setProjLang] = useState<IoTFirmwareLanguage>('arduino_cpp');
  const [projProtocol, setProjProtocol] = useState<IoTConnectivityProtocol>('wifi_mqtt');

  // Component library filter state
  const [compCategory, setCompCategory] = useState<string>('all');
  const [compInterface, setCompInterface] = useState<string>('all');
  const [compSearch, setCompSearch] = useState<string>('');

  // Wiring designer manual wire state
  const [newWireFromPin, setNewWireFromPin] = useState<string>('GPIO27');
  const [newWireToComp, setNewWireToComp] = useState<string>('');
  const [newWireToPin, setNewWireToPin] = useState<string>('IN');
  const [newWireSignal, setNewWireSignal] = useState<string>('DIGITAL');
  const [newWireVoltage, setNewWireVoltage] = useState<number>(3.3);

  // Firmware editor state
  const [fwLanguage, setFwLanguage] = useState<IoTFirmwareLanguage>('arduino_cpp');
  const [fwSourceCode, setFwSourceCode] = useState<string>('');
  const [showSecretsTemplate, setShowSecretsTemplate] = useState<boolean>(false);

  // Simulator state
  const [simTicks, setSimTicks] = useState<number>(6);
  const [simFault, setSimFault] = useState<
    'none' | 'sensor_disconnect' | 'overtemperature' | 'brownout_voltage' | 'mqtt_broker_offline'
  >('none');
  const [simResult, setSimResult] = useState<IoTSimulationResponse | null>(null);

  // Export state
  const [bumpVersion, setBumpVersion] = useState<'none' | 'patch' | 'minor' | 'major'>('patch');
  const [lastExport, setLastExport] = useState<IoTProjectExportResponse | null>(null);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [meta, boardList, compList, projList] = await Promise.all([
        api.getIoTMetadata(),
        api.listIoTBoards(),
        api.listIoTComponents(),
        api.listIoTProjects(),
      ]);
      setMetadata(meta);
      setBoards(boardList);
      setComponents(compList);
      setProjects(projList);
      if (projList.length > 0) {
        const first = projList[0];
        setSelectedProject(first);
        setFwLanguage(first.firmware.language);
        setFwSourceCode(first.firmware.source_code);
        setSimResult(first.last_simulation || null);
        if (first.placed_components.length > 0) {
          setNewWireToComp(first.placed_components[0].instance_id);
        }
      }
    } catch (err: any) {
      showToast(err?.message || 'Failed to load IoT Project Builder', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const handleSelectProject = (proj: IoTProjectRecord) => {
    setSelectedProject(proj);
    setFwLanguage(proj.firmware.language);
    setFwSourceCode(proj.firmware.source_code);
    setSimResult(proj.last_simulation || null);
    setLastExport(null);
    if (proj.placed_components.length > 0) {
      setNewWireToComp(proj.placed_components[0].instance_id);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projName.trim() || !projDesc.trim()) {
      showToast('Please provide a project name and invention description.', 'error');
      return;
    }
    setLoading(true);
    try {
      const created = await api.createIoTProject({
        name: projName.trim(),
        invention_description: projDesc.trim(),
        target_budget_usd: projBudget,
        power_source: projPower,
        environment: projEnv,
        preferred_board_id: projBoardId,
        component_ids: projCompIds,
        firmware_language: projLang,
        connectivity_protocol: projProtocol,
        auto_wire: true,
      });
      const updatedList = await api.listIoTProjects();
      setProjects(updatedList);
      handleSelectProject(created);
      showToast(`Created IoT project "${created.name}" (${created.board_profile.name})`, 'success');
      setActiveTab('wiring');
    } catch (err: any) {
      showToast(err?.message || 'Failed to create IoT project', 'error');
    } finally {
      setLoading(false);
    }
  };

  const toggleDesignComponent = (compId: string) => {
    setProjCompIds((prev) =>
      prev.includes(compId) ? prev.filter((id) => id !== compId) : [...prev, compId]
    );
  };

  const handleFilterComponents = async () => {
    try {
      const filtered = await api.listIoTComponents({
        category: compCategory,
        interface: compInterface,
        query: compSearch,
      });
      setComponents(filtered);
    } catch (err: any) {
      showToast(err?.message || 'Failed to filter component catalog', 'error');
    }
  };

  const handleAddComponentToActiveProject = async (compSpec: IoTComponentSpec) => {
    if (!selectedProject) return;
    setLoading(true);
    try {
      const nextIdx = selectedProject.placed_components.length + 1;
      const newPlaced = [
        ...selectedProject.placed_components,
        {
          instance_id: `comp_${nextIdx}_${compSpec.component_id.slice(0, 10)}`,
          component_id: compSpec.component_id,
          label: compSpec.name.split('(')[0].trim(),
          x: 540,
          y: 50 + selectedProject.placed_components.length * 96,
          notes: '',
        },
      ];
      const updated = await api.updateIoTWiring(selectedProject.project_id, {
        placed_components: newPlaced,
        wires: selectedProject.wires,
        auto_regenerate_firmware: true,
      });
      handleSelectProject(updated);
      showToast(`Added ${compSpec.name} to ${updated.name}. Review Wiring tab to connect pins.`, 'info');
    } catch (err: any) {
      showToast(err?.message || 'Failed to add component', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleAddManualWire = async () => {
    if (!selectedProject || !newWireToComp) return;
    setLoading(true);
    try {
      const newWire: IoTWireConnection = {
        wire_id: `wire_manual_${Date.now().toString().slice(-4)}`,
        from_node_id: 'board',
        from_pin: newWireFromPin,
        to_node_id: newWireToComp,
        to_pin: newWireToPin,
        signal_type: newWireSignal,
        wire_color: '#38bdf8',
        label: `Board ${newWireFromPin} -> ${newWireToComp}.${newWireToPin}`,
        voltage_v: newWireVoltage,
      };
      const updated = await api.updateIoTWiring(selectedProject.project_id, {
        placed_components: selectedProject.placed_components,
        wires: [...selectedProject.wires, newWire],
        auto_regenerate_firmware: true,
      });
      handleSelectProject(updated);
      showToast('Added wire connection and re-ran electrical validator.', 'success');
    } catch (err: any) {
      showToast(err?.message || 'Failed to add wire', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveWire = async (wireId: string) => {
    if (!selectedProject) return;
    setLoading(true);
    try {
      const updated = await api.updateIoTWiring(selectedProject.project_id, {
        placed_components: selectedProject.placed_components,
        wires: selectedProject.wires.filter((w) => w.wire_id !== wireId),
        auto_regenerate_firmware: true,
      });
      handleSelectProject(updated);
    } catch (err: any) {
      showToast(err?.message || 'Failed to remove wire', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleInjectFaultyWiringDemo = async () => {
    if (!selectedProject || selectedProject.placed_components.length === 0) return;
    setLoading(true);
    try {
      const firstComp = selectedProject.placed_components[0];
      const faultyWires: IoTWireConnection[] = [
        ...selectedProject.wires,
        {
          wire_id: 'wire_fault_short',
          from_node_id: 'board',
          from_pin: selectedProject.board_profile.pins[0]?.pin_id || '3V3',
          to_node_id: 'board',
          to_pin:
            selectedProject.board_profile.pins.find((p) => p.capabilities.includes('GND'))?.pin_id ||
            'GND_1',
          signal_type: 'POWER',
          wire_color: '#ef4444',
          label: 'DELIBERATE FAULT: Power-to-GND Short',
          voltage_v: 3.3,
        },
        {
          wire_id: 'wire_fault_conflict',
          from_node_id: 'board',
          from_pin:
            selectedProject.board_profile.pins.find((p) => p.capabilities.includes('I2C_SDA'))
              ?.pin_id || 'GPIO21',
          to_node_id: firstComp.instance_id,
          to_pin: 'VCC',
          signal_type: 'DIGITAL',
          wire_color: '#f43f5e',
          label: 'DELIBERATE FAULT: Pin Conflict on SDA',
          voltage_v: 5.0,
        },
      ];
      const updated = await api.updateIoTWiring(selectedProject.project_id, {
        placed_components: selectedProject.placed_components,
        wires: faultyWires,
        auto_regenerate_firmware: false,
      });
      handleSelectProject(updated);
      showToast('Injected electrical wiring faults — inspect validation errors below.', 'info');
    } catch (err: any) {
      showToast(err?.message || 'Failed to inject fault demo', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateOrVerifyFirmware = async (useCustomCode: boolean) => {
    if (!selectedProject) return;
    setLoading(true);
    try {
      const updated = await api.generateIoTFirmware(selectedProject.project_id, {
        language: fwLanguage,
        custom_source_code: useCustomCode ? fwSourceCode : undefined,
        run_compiler_check: true,
      });
      handleSelectProject(updated);
      showToast(`Generated & verified ${updated.firmware.language} firmware.`, 'success');
    } catch (err: any) {
      showToast(err?.message || 'Firmware generation failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRunSimulation = async () => {
    if (!selectedProject) return;
    setLoading(true);
    try {
      const res = await api.simulateIoTProject(selectedProject.project_id, {
        ticks: simTicks,
        inject_fault: simFault,
      });
      setSimResult(res);
      showToast(`Completed ${res.ticks_executed} virtual simulation ticks.`, 'success');
    } catch (err: any) {
      showToast(err?.message || 'Simulation failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleExportProject = async () => {
    if (!selectedProject) return;
    setLoading(true);
    try {
      const exp = await api.exportIoTProject(selectedProject.project_id, {
        bump_version: bumpVersion,
        write_to_workspace_files: true,
      });
      setLastExport(exp);
      const refreshed = await api.getIoTProject(selectedProject.project_id);
      setSelectedProject(refreshed);
      showToast(`Exported ${exp.project_name} v${exp.version} (${exp.files.length} files)`, 'success');
    } catch (err: any) {
      showToast(err?.message || 'Project export failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden">
      {/* Top Studio Header */}
      <div className="border-b border-slate-800 bg-slate-900/80 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/15 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-white">Stage 23: IoT Project Builder & Firmware Studio</h1>
              <span className="px-2 py-0.5 text-[11px] font-semibold rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                {metadata?.boards_count || 5} Boards • {metadata?.components_count || 11} Components
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Hardware Board Selection • Pin-to-Pin Wiring Validator • Honest Compiler Checks • Deterministic Virtual Simulation • Safety & BOM Export
            </p>
          </div>
        </div>

        {/* Active Project Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Active Project:</span>
          <select
            value={selectedProject?.project_id || ''}
            onChange={(e) => {
              const found = projects.find((p) => p.project_id === e.target.value);
              if (found) handleSelectProject(found);
            }}
            className="bg-slate-800 border border-slate-700 text-xs text-slate-100 rounded-lg px-3 py-1.5"
          >
            {projects.map((p) => (
              <option key={p.project_id} value={p.project_id}>
                {p.name} ({p.board_profile.name.split(' ')[0]} • v{p.version})
              </option>
            ))}
          </select>
          <button
            onClick={loadInitialData}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
            title="Refresh IoT Workspace"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Sub-navigation Tabs */}
      <div className="border-b border-slate-800 bg-slate-900/40 px-6 flex items-center gap-2 overflow-x-auto">
        {[
          { id: 'designer', label: '1. Project & Board Designer', icon: Layers },
          { id: 'components', label: '2. Component Library', icon: Wrench },
          { id: 'wiring', label: '3. Wiring Canvas & Validator', icon: CircuitBoard },
          { id: 'firmware', label: '4. Firmware Studio', icon: Code2 },
          { id: 'simulator', label: '5. Virtual Simulator & MQTT', icon: Play },
          { id: 'docs_safety_export', label: '6. BOM, Safety Audit & Export', icon: ShieldAlert },
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as StudioTab)}
              className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
                active
                  ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* TAB 1: PROJECT & BOARD DESIGNER */}
        {activeTab === 'designer' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left: New IoT Project Designer Form */}
            <form
              onSubmit={handleCreateProject}
              className="lg:col-span-5 bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-4"
            >
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Plus className="w-4 h-4 text-cyan-400" />
                  Design New IoT Prototype
                </h2>
                <span className="text-[11px] text-slate-400">Auto-wires & validates netlist</span>
              </div>

              <div>
                <label className="block text-xs text-slate-300 mb-1">Project Name</label>
                <input
                  type="text"
                  value={projName}
                  onChange={(e) => setProjName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100"
                />
              </div>

              <div>
                <label className="block text-xs text-slate-300 mb-1">
                  Invention Description (Natural Language Purpose & Requirements)
                </label>
                <textarea
                  rows={3}
                  value={projDesc}
                  onChange={(e) => setProjDesc(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs text-slate-300 mb-1">Target Budget ($ USD)</label>
                  <input
                    type="number"
                    min={5}
                    max={5000}
                    value={projBudget}
                    onChange={(e) => setProjBudget(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-300 mb-1">Power Source</label>
                  <select
                    value={projPower}
                    onChange={(e) => setProjPower(e.target.value as IoTPowerSource)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-100"
                  >
                    <option value="usb_5v">USB 5V Regulated</option>
                    <option value="battery_lipo_3v7">LiPo / 18650 Battery</option>
                    <option value="dc_barrel_7v_12v">DC 7V–12V Adapter</option>
                    <option value="solar_mppt_5v">Solar MPPT 5V</option>
                    <option value="mains_ac_isolated_psu">Mains AC Isolated PSU</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-slate-300 mb-1">Environment</label>
                  <select
                    value={projEnv}
                    onChange={(e) => setProjEnv(e.target.value as IoTEnvironmentType)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-100"
                  >
                    <option value="indoor_lab">Indoor Clean / Lab</option>
                    <option value="greenhouse_humid">Greenhouse Humid</option>
                    <option value="outdoor_weatherproof">Outdoor Weatherproof</option>
                    <option value="industrial_harsh">Industrial Harsh</option>
                    <option value="wearable_portable">Wearable Portable</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs text-slate-300 mb-1">Target Board</label>
                  <select
                    value={projBoardId}
                    onChange={(e) => setProjBoardId(e.target.value as IoTBoardId)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-100"
                  >
                    {boards.map((b) => (
                      <option key={b.board_id} value={b.board_id}>
                        {b.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-slate-300 mb-1">Firmware Language</label>
                  <select
                    value={projLang}
                    onChange={(e) => setProjLang(e.target.value as IoTFirmwareLanguage)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-100"
                  >
                    <option value="arduino_cpp">Arduino C/C++ (.ino)</option>
                    <option value="micropython">MicroPython (main.py)</option>
                    <option value="esp_idf_c">ESP-IDF C (main.c)</option>
                    <option value="rpi_python_gpiozero">RPi Python gpiozero</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-slate-300 mb-1">Connectivity</label>
                  <select
                    value={projProtocol}
                    onChange={(e) => setProjProtocol(e.target.value as IoTConnectivityProtocol)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-100"
                  >
                    <option value="wifi_mqtt">Wi-Fi MQTT Broker</option>
                    <option value="wifi_http_rest">Wi-Fi HTTP REST</option>
                    <option value="ble_gatt">BLE GATT Telemetry</option>
                    <option value="serial_usb_telemetry">Serial USB Telemetry</option>
                    <option value="none_local_only">Offline Local Only</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs text-slate-300 mb-1.5">
                  Select Sensors, Actuators & Modules ({projCompIds.length} selected)
                </label>
                <div className="max-h-44 overflow-y-auto bg-slate-950 border border-slate-800 rounded-lg p-2 space-y-1">
                  {components.map((c) => {
                    const checked = projCompIds.includes(c.component_id);
                    return (
                      <label
                        key={c.component_id}
                        className={`flex items-center justify-between px-2.5 py-1.5 rounded cursor-pointer text-xs ${
                          checked ? 'bg-cyan-500/15 text-cyan-200' : 'hover:bg-slate-900 text-slate-300'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleDesignComponent(c.component_id)}
                            className="rounded border-slate-700"
                          />
                          <span>{c.name}</span>
                        </div>
                        <span className="text-[10px] text-slate-400">
                          ${c.cost_min_usd}–${c.cost_max_usd}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs transition-colors"
              >
                {loading ? 'Synthesizing IoT Blueprint...' : 'Generate IoT Blueprint, Wiring & Firmware'}
              </button>
            </form>

            {/* Right: Hardware Board Profiles Comparison & Pinout */}
            <div className="lg:col-span-7 space-y-4">
              <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5">
                <h2 className="text-sm font-semibold text-white mb-3">
                  Supported Microcontroller & SBC Board Profiles
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {boards.map((b) => {
                    const isCurrent = selectedProject?.board_id === b.board_id;
                    return (
                      <div
                        key={b.board_id}
                        className={`p-3.5 rounded-xl border ${
                          isCurrent
                            ? 'bg-cyan-950/30 border-cyan-500/50'
                            : 'bg-slate-950/70 border-slate-800'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="text-xs font-bold text-white">{b.name}</div>
                            <div className="text-[11px] text-slate-400">{b.mcu_or_soc}</div>
                          </div>
                          <span
                            className={`px-2 py-0.5 text-[10px] rounded-full font-medium ${
                              b.five_volt_tolerant_pins
                                ? 'bg-emerald-500/20 text-emerald-300'
                                : 'bg-amber-500/20 text-amber-300'
                            }`}
                          >
                            {b.io_logic_voltage_v}V Logic {b.five_volt_tolerant_pins ? '(5V Tol)' : '(3.3V Only)'}
                          </span>
                        </div>

                        <div className="mt-2.5 grid grid-cols-4 gap-1.5 text-[11px] text-slate-300">
                          <div className="bg-slate-900 px-2 py-1 rounded">
                            <span className="text-slate-500 block text-[10px]">GPIO / ADC</span>
                            {b.total_gpio_count} / {b.analog_in_count}
                          </div>
                          <div className="bg-slate-900 px-2 py-1 rounded">
                            <span className="text-slate-500 block text-[10px]">Clock</span>
                            {b.clock_mhz} MHz
                          </div>
                          <div className="bg-slate-900 px-2 py-1 rounded">
                            <span className="text-slate-500 block text-[10px]">SRAM / Flash</span>
                            {b.sram_kb}KB / {b.flash_kb}KB
                          </div>
                          <div className="bg-slate-900 px-2 py-1 rounded">
                            <span className="text-slate-500 block text-[10px]">Pin Max</span>
                            {b.max_pin_current_ma} mA
                          </div>
                        </div>

                        <div className="mt-2 flex flex-wrap gap-1">
                          {b.communication_interfaces.map((iface) => (
                            <span
                              key={iface}
                              className="px-1.5 py-0.5 text-[10px] rounded bg-slate-800 text-slate-300"
                            >
                              {iface}
                            </span>
                          ))}
                        </div>

                        {b.compatibility_warnings.length > 0 && (
                          <div className="mt-2.5 text-[11px] text-amber-300/90 bg-amber-500/10 border border-amber-500/20 rounded p-2 space-y-1">
                            {b.compatibility_warnings.map((w, idx) => (
                              <div key={idx}>• {w}</div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: COMPONENT LIBRARY */}
        {activeTab === 'components' && (
          <div className="space-y-4">
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center gap-3">
              <input
                type="text"
                placeholder="Search sensors, relays, displays, motor drivers..."
                value={compSearch}
                onChange={(e) => setCompSearch(e.target.value)}
                className="flex-1 min-w-[220px] bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100"
              />
              <select
                value={compCategory}
                onChange={(e) => setCompCategory(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100"
              >
                <option value="all">All Categories</option>
                <option value="sensor">Sensors</option>
                <option value="display">Displays</option>
                <option value="relay">Relays</option>
                <option value="actuator">Actuators / Servos</option>
                <option value="motor">Motors</option>
                <option value="motor_driver">Motor Drivers</option>
                <option value="logic_adapter">ADC / Level Shifters</option>
                <option value="power">Power / Batteries</option>
              </select>
              <select
                value={compInterface}
                onChange={(e) => setCompInterface(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100"
              >
                <option value="all">All Interfaces</option>
                <option value="I2C">I2C</option>
                <option value="ADC">Analog ADC</option>
                <option value="DIGITAL">Digital IO</option>
                <option value="PWM">PWM</option>
                <option value="ONEWIRE">OneWire</option>
              </select>
              <button
                onClick={handleFilterComponents}
                className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-xs font-semibold text-white"
              >
                Filter Catalog
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {components.map((c) => (
                <div
                  key={c.component_id}
                  className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col justify-between space-y-3"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="text-xs font-bold text-white">{c.name}</h3>
                      <span
                        className={`px-2 py-0.5 text-[10px] rounded-full whitespace-nowrap ${
                          c.spec_verification_status === 'verified_datasheet_spec'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        }`}
                      >
                        {c.spec_verification_status === 'verified_datasheet_spec'
                          ? 'Verified Datasheet'
                          : 'Estimated Range'}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">{c.description}</p>

                    <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                      <div>
                        <span className="text-slate-500 block text-[10px]">Supply V</span>
                        {c.operating_voltage_min_v}V–{c.operating_voltage_max_v}V
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[10px]">Logic / Typ I</span>
                        {c.logic_voltage_v}V / {c.current_typical_ma}mA
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[10px]">Est. Cost</span>
                        ${c.cost_min_usd}–${c.cost_max_usd}
                      </div>
                    </div>

                    {c.notes && (
                      <div className="mt-2 text-[11px] text-slate-300 bg-slate-800/60 rounded p-2">
                        {c.notes}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-800">
                    {c.datasheet_url ? (
                      <a
                        href={c.datasheet_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[11px] text-cyan-400 hover:underline flex items-center gap-1"
                      >
                        Datasheet <ExternalLink className="w-3 h-3" />
                      </a>
                    ) : (
                      <span className="text-[11px] text-slate-500">Generic Spec</span>
                    )}
                    <button
                      onClick={() => handleAddComponentToActiveProject(c)}
                      className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-cyan-600 text-xs text-slate-200 hover:text-white transition-colors"
                    >
                      + Add to Project
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 3: WIRING DESIGNER & ELECTRICAL VALIDATOR */}
        {activeTab === 'wiring' && selectedProject && (
          <div className="space-y-6">
            {/* Validation Banner */}
            <div
              className={`p-4 rounded-xl border flex flex-wrap items-center justify-between gap-4 ${
                selectedProject.wiring_report.valid
                  ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-200'
                  : 'bg-rose-950/40 border-rose-500/50 text-rose-200'
              }`}
            >
              <div className="flex items-center gap-3">
                {selectedProject.wiring_report.valid ? (
                  <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
                ) : (
                  <XCircle className="w-6 h-6 text-rose-400 shrink-0" />
                )}
                <div>
                  <div className="text-sm font-bold">
                    {selectedProject.wiring_report.valid
                      ? 'Wiring Netlist Validated — Nominal Pin & Voltage Rules Passed'
                      : `Electrical / Pin Validation Failed (${selectedProject.wiring_report.critical_count} Critical, ${selectedProject.wiring_report.error_count} Errors)`}
                  </div>
                  <div className="text-xs opacity-80">
                    3.3V Rail Load: {selectedProject.wiring_report.power_rail_summary.rail_3v3_typical_ma || 0} mA /{' '}
                    {selectedProject.wiring_report.power_rail_summary.rail_3v3_limit_ma || 250} mA • 5V Rail Load:{' '}
                    {selectedProject.wiring_report.power_rail_summary.rail_5v_typical_ma || 0} mA /{' '}
                    {selectedProject.wiring_report.power_rail_summary.rail_5v_limit_ma || 500} mA
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleInjectFaultyWiringDemo}
                  className="px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-200 text-xs font-medium"
                >
                  Test Fault Detector (Inject Short & Conflict)
                </button>
              </div>
            </div>

            {/* Interactive SVG Schematic Canvas */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold text-white">
                  Interactive Pin-to-Pin Schematic Canvas ({selectedProject.board_profile.name})
                </h3>
                <span className="text-[11px] text-slate-400">
                  {selectedProject.placed_components.length} Placed Components • {selectedProject.wires.length} Labeled Wires
                </span>
              </div>
              <div
                className="w-full overflow-x-auto rounded-lg border border-slate-800 bg-slate-950 p-2"
                dangerouslySetInnerHTML={{ __html: selectedProject.wiring_report.svg_diagram }}
              />
            </div>

            {/* Validation Issues List */}
            {selectedProject.wiring_report.issues.length > 0 && (
              <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-2.5">
                <h3 className="text-xs font-semibold text-white">
                  Electrical & Pin Conflict Diagnostics ({selectedProject.wiring_report.issues.length})
                </h3>
                {selectedProject.wiring_report.issues.map((iss) => (
                  <div
                    key={iss.issue_id}
                    className={`p-3 rounded-lg border text-xs ${
                      iss.severity === 'critical' || iss.severity === 'error'
                        ? 'bg-rose-950/30 border-rose-500/40 text-rose-200'
                        : 'bg-amber-950/30 border-amber-500/40 text-amber-200'
                    }`}
                  >
                    <div className="flex items-center justify-between font-bold">
                      <span>
                        [{iss.severity.toUpperCase()} • {iss.code}] {iss.title}
                      </span>
                      <span className="text-[11px] opacity-80">Pins: {iss.affected_pins.join(', ')}</span>
                    </div>
                    <p className="mt-1 opacity-90">{iss.description}</p>
                    <p className="mt-1 text-cyan-300 font-medium">Fix: {iss.remediation}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Add Wire & Netlist Table */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-4">
              <div className="flex flex-wrap items-end gap-3 pb-4 border-b border-slate-800">
                <div>
                  <label className="block text-[11px] text-slate-400 mb-1">Board Pin</label>
                  <select
                    value={newWireFromPin}
                    onChange={(e) => setNewWireFromPin(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs"
                  >
                    {selectedProject.board_profile.pins.map((p) => (
                      <option key={p.pin_id} value={p.pin_id}>
                        {p.label} ({p.voltage_level_v}V)
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] text-slate-400 mb-1">Target Component</label>
                  <select
                    value={newWireToComp}
                    onChange={(e) => setNewWireToComp(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs"
                  >
                    {selectedProject.placed_components.map((c) => (
                      <option key={c.instance_id} value={c.instance_id}>
                        {c.label} ({c.instance_id})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] text-slate-400 mb-1">Component Pin</label>
                  <input
                    type="text"
                    value={newWireToPin}
                    onChange={(e) => setNewWireToPin(e.target.value)}
                    className="w-24 bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-slate-400 mb-1">Signal Type</label>
                  <select
                    value={newWireSignal}
                    onChange={(e) => setNewWireSignal(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs"
                  >
                    <option value="DIGITAL">DIGITAL</option>
                    <option value="ANALOG">ANALOG</option>
                    <option value="PWM">PWM</option>
                    <option value="I2C_SDA">I2C_SDA</option>
                    <option value="I2C_SCL">I2C_SCL</option>
                    <option value="POWER">POWER</option>
                    <option value="GND">GND</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] text-slate-400 mb-1">Signal V</label>
                  <input
                    type="number"
                    step="0.1"
                    value={newWireVoltage}
                    onChange={(e) => setNewWireVoltage(Number(e.target.value))}
                    className="w-20 bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs"
                  />
                </div>
                <button
                  onClick={handleAddManualWire}
                  className="px-3.5 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold"
                >
                  + Connect Pin
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="py-2">Wire ID</th>
                      <th className="py-2">From Node : Pin</th>
                      <th className="py-2">To Node : Pin</th>
                      <th className="py-2">Signal</th>
                      <th className="py-2">Voltage</th>
                      <th className="py-2 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {selectedProject.wires.map((w) => (
                      <tr key={w.wire_id}>
                        <td className="py-2 font-mono text-slate-300">{w.wire_id}</td>
                        <td className="py-2">
                          {w.from_node_id} : <span className="font-mono text-cyan-300">{w.from_pin}</span>
                        </td>
                        <td className="py-2">
                          {w.to_node_id} : <span className="font-mono text-indigo-300">{w.to_pin}</span>
                        </td>
                        <td className="py-2">{w.signal_type}</td>
                        <td className="py-2">{w.voltage_v}V</td>
                        <td className="py-2 text-right">
                          <button
                            onClick={() => handleRemoveWire(w.wire_id)}
                            className="text-rose-400 hover:underline text-[11px]"
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: FIRMWARE STUDIO */}
        {activeTab === 'firmware' && selectedProject && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-8 bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <select
                    value={fwLanguage}
                    onChange={(e) => setFwLanguage(e.target.value as IoTFirmwareLanguage)}
                    className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100"
                  >
                    {selectedProject.board_profile.supported_languages.map((lang) => (
                      <option key={lang} value={lang}>
                        {lang}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => handleGenerateOrVerifyFirmware(false)}
                    className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-xs font-semibold text-white"
                  >
                    Regenerate from Netlist
                  </button>
                  <button
                    onClick={() => handleGenerateOrVerifyFirmware(true)}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-200"
                  >
                    Verify Edited Code
                  </button>
                </div>

                <button
                  onClick={() => setShowSecretsTemplate(!showSecretsTemplate)}
                  className="text-xs text-cyan-400 hover:underline"
                >
                  {showSecretsTemplate
                    ? `View ${selectedProject.firmware.filename}`
                    : `View ${selectedProject.firmware.secrets_template_filename} (Credentials Template)`}
                </button>
              </div>

              {/* Honest Compilation / Syntax Verification Banner */}
              <div
                className={`p-3 rounded-lg border text-xs ${
                  selectedProject.firmware.compilation_tested && selectedProject.firmware.compilation_passed
                    ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-200'
                    : selectedProject.firmware.compilation_tested && selectedProject.firmware.compilation_passed === false
                    ? 'bg-rose-950/30 border-rose-500/40 text-rose-200'
                    : 'bg-amber-950/30 border-amber-500/40 text-amber-200'
                }`}
              >
                <div className="font-bold">
                  Verification Mode: `{selectedProject.firmware.verification_mode}` • Compilation Tested:{' '}
                  {selectedProject.firmware.compilation_tested ? 'YES (Real Host Compiler/AST)' : 'NO (Toolchain Not Installed)'}
                </div>
                <div className="mt-1 opacity-90">{selectedProject.firmware.compiler_output}</div>
                {selectedProject.firmware.missing_dependencies.length > 0 && (
                  <div className="mt-1 text-amber-300">
                    Missing Host Dependencies: {selectedProject.firmware.missing_dependencies.join(', ')}
                  </div>
                )}
              </div>

              <textarea
                rows={18}
                value={
                  showSecretsTemplate
                    ? selectedProject.firmware.secrets_template_code
                    : fwSourceCode
                }
                onChange={(e) => {
                  if (!showSecretsTemplate) setFwSourceCode(e.target.value);
                }}
                readOnly={showSecretsTemplate}
                className="w-full font-mono text-xs bg-slate-950 border border-slate-800 rounded-xl p-4 text-slate-100 leading-relaxed"
              />
            </div>

            <div className="lg:col-span-4 space-y-4">
              <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-3">
                <h3 className="text-xs font-semibold text-white">Pin Mapping Constants</h3>
                <div className="space-y-1.5 text-xs">
                  {Object.entries(selectedProject.firmware.pin_mappings).map(([k, v]) => (
                    <div key={k} className="flex justify-between bg-slate-950 px-2.5 py-1.5 rounded border border-slate-800">
                      <span className="font-mono text-cyan-300">{k}</span>
                      <span className="font-mono text-slate-300">{v}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-2 text-xs">
                <h3 className="font-semibold text-white">Toolchain CLI Commands</h3>
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800 font-mono text-[11px] text-emerald-300">
                  $ {selectedProject.firmware.compile_command}
                </div>
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800 font-mono text-[11px] text-cyan-300">
                  $ {selectedProject.firmware.flash_command}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: VIRTUAL SIMULATOR & CONNECTIVITY */}
        {activeTab === 'simulator' && selectedProject && (
          <div className="space-y-6">
            <div className="p-3.5 rounded-xl bg-indigo-950/40 border border-indigo-500/40 text-indigo-200 text-xs flex items-center justify-between">
              <div>
                <span className="font-bold">DETERMINISTIC VIRTUAL SIMULATION MODE:</span> No physical microcontroller or
                hardware actuator is connected. All sensor stimuli and actuator states below are computed in software.
              </div>
              <span className="px-2 py-0.5 rounded bg-indigo-500/20 border border-indigo-400/30 font-mono text-[11px]">
                is_physical_hardware_execution: false
              </span>
            </div>

            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-wrap items-end gap-4">
              <div>
                <label className="block text-xs text-slate-300 mb-1">Simulation Ticks</label>
                <input
                  type="number"
                  min={1}
                  max={32}
                  value={simTicks}
                  onChange={(e) => setSimTicks(Number(e.target.value))}
                  className="w-24 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-300 mb-1">Fault Injection Scenario</label>
                <select
                  value={simFault}
                  onChange={(e) => setSimFault(e.target.value as any)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs"
                >
                  <option value="none">Nominal Operation (No Faults)</option>
                  <option value="overtemperature">Overtemperature Spike (88.5°C)</option>
                  <option value="sensor_disconnect">I2C Sensor Disconnect (NACK)</option>
                  <option value="brownout_voltage">3.3V Rail Brownout Droop</option>
                  <option value="mqtt_broker_offline">MQTT Broker Offline (Local Ring Buffer)</option>
                </select>
              </div>
              <button
                onClick={handleRunSimulation}
                disabled={loading}
                className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center gap-1.5"
              >
                <Play className="w-3.5 h-3.5" /> Run Virtual Simulation
              </button>
            </div>

            {simResult && (
              <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-white">{simResult.summary}</h3>
                  <span className="text-xs text-cyan-300">
                    Avg Current: {simResult.average_current_ma} mA • Peak: {simResult.peak_current_ma} mA
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400">
                        <th className="py-2">Tick</th>
                        <th className="py-2">Virtual Sensors</th>
                        <th className="py-2">Actuator Outputs</th>
                        <th className="py-2">Current / Power</th>
                        <th className="py-2">Serial Monitor Output</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {simResult.ticks.map((t) => (
                        <tr key={t.tick}>
                          <td className="py-2 font-mono text-slate-300">#{t.tick} ({t.timestamp_ms}ms)</td>
                          <td className="py-2 font-mono text-[11px] text-emerald-300">
                            {JSON.stringify(t.sensor_readings)}
                          </td>
                          <td className="py-2 font-mono text-[11px] text-cyan-300">
                            {JSON.stringify(t.actuator_states)}
                          </td>
                          <td className="py-2">
                            {t.estimated_current_ma} mA ({t.estimated_power_mw} mW)
                          </td>
                          <td className="py-2 font-mono text-[11px] text-slate-300">{t.serial_log}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Connectivity & Mock Broker Config */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-white flex items-center gap-2">
                  <Wifi className="w-4 h-4 text-cyan-400" />
                  Connectivity & Mock Telemetry Broker Configuration
                </h3>
                <span className="px-2 py-0.5 text-[10px] rounded bg-emerald-500/20 text-emerald-300">
                  Mock Mode Active (Safe Offline Preview)
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1">
                  <div>Protocol: <span className="font-mono text-cyan-300">{selectedProject.connectivity.protocol}</span></div>
                  <div>Endpoint: <span className="font-mono text-slate-300">{selectedProject.connectivity.endpoint_or_broker}</span></div>
                  <div>Topic Prefix: <span className="font-mono text-slate-300">{selectedProject.connectivity.topic_prefix}</span></div>
                  <div>Masked Credentials: <span className="font-mono text-amber-300">{JSON.stringify(selectedProject.connectivity.masked_credentials_preview)}</span></div>
                </div>
                <pre className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-emerald-300 overflow-x-auto">
                  {JSON.stringify(selectedProject.connectivity.sample_telemetry_payload, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* TAB 6: BOM, SAFETY AUDIT & VERSIONED EXPORT */}
        {activeTab === 'docs_safety_export' && selectedProject && (
          <div className="space-y-6">
            {/* Physical Safety Disclaimer & Hazard Banner */}
            <div
              className={`p-4 rounded-xl border ${
                selectedProject.safety_report.requires_qualified_electrical_review
                  ? 'bg-amber-950/40 border-amber-500/50 text-amber-200'
                  : 'bg-slate-900/90 border-slate-800 text-slate-200'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="text-sm font-bold flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-400" />
                  Electrical & Physical Safety Audit
                </div>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300">
                  {selectedProject.safety_report.requires_qualified_electrical_review
                    ? 'QUALIFIED ELECTRICAL REVIEW REQUIRED'
                    : 'Nominal SELV Low-Voltage Checks Passed'}
                </span>
              </div>
              <p className="text-xs mt-2 opacity-90">
                {selectedProject.safety_report.physical_safety_disclaimer}
              </p>

              <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
                {selectedProject.safety_report.checks.map((chk) => (
                  <div key={chk.check_id} className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 text-xs">
                    <div className="flex items-center justify-between font-semibold">
                      <span>{chk.title}</span>
                      <span
                        className={`uppercase text-[10px] px-1.5 py-0.5 rounded ${
                          chk.status === 'pass'
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : 'bg-rose-500/20 text-rose-300'
                        }`}
                      >
                        {chk.status}
                      </span>
                    </div>
                    <p className="text-slate-400 mt-1">{chk.detail}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Bill of Materials (BOM) */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-white flex items-center gap-2">
                  <FileSpreadsheet className="w-4 h-4 text-cyan-400" />
                  Bill of Materials (BOM) & Cost Estimation
                </h3>
                <span className="text-xs text-emerald-300 font-semibold">
                  Est. Total: ${selectedProject.build_docs.total_cost_min_usd.toFixed(2)} – $
                  {selectedProject.build_docs.total_cost_max_usd.toFixed(2)} USD (Budget: $
                  {selectedProject.build_docs.target_budget_usd.toFixed(2)})
                </span>
              </div>
              <p className="text-[11px] text-amber-300/90">{selectedProject.build_docs.unverified_specs_notice}</p>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="py-2">Component</th>
                      <th className="py-2">Category</th>
                      <th className="py-2">Qty</th>
                      <th className="py-2">Subtotal Range</th>
                      <th className="py-2">Spec Basis</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {selectedProject.build_docs.bom_items.map((item) => (
                      <tr key={item.item_id}>
                        <td className="py-2 font-medium text-white">{item.name}</td>
                        <td className="py-2 text-slate-400">{item.category}</td>
                        <td className="py-2">{item.quantity}</td>
                        <td className="py-2">
                          ${item.subtotal_min_usd.toFixed(2)} – ${item.subtotal_max_usd.toFixed(2)}
                        </td>
                        <td className="py-2">
                          <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300">
                            {item.spec_verification_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Versioned Project Export */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-xs font-semibold text-white">
                    Versioned Project Export (Current v{selectedProject.version})
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Exports firmware, secrets template, SVG diagram, JSON netlist, CSV/JSON BOM, and build guide to Stage 17 File Workspace.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={bumpVersion}
                    onChange={(e) => setBumpVersion(e.target.value as any)}
                    className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs"
                  >
                    <option value="patch">Bump Patch (x.x.+1)</option>
                    <option value="minor">Bump Minor (x.+1.0)</option>
                    <option value="major">Bump Major (+1.0.0)</option>
                    <option value="none">Keep Current Version</option>
                  </select>
                  <button
                    onClick={handleExportProject}
                    disabled={loading}
                    className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center gap-1.5"
                  >
                    <Download className="w-3.5 h-3.5" /> Export Bundle
                  </button>
                </div>
              </div>

              {lastExport && (
                <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-2 text-xs">
                  <div className="text-emerald-300 font-semibold">{lastExport.summary}</div>
                  <div className="text-[11px] text-slate-400 font-mono">
                    Workspace Path: {lastExport.workspace_relative_dir || lastExport.export_directory}
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2 pt-2">
                    {lastExport.files.map((f) => (
                      <div key={f.relative_path} className="p-2 rounded bg-slate-900 border border-slate-800">
                        <div className="font-mono text-cyan-300 text-[11px]">{f.relative_path}</div>
                        <div className="text-[10px] text-slate-400">
                          {f.size_bytes} bytes • SHA256: {f.sha256.slice(0, 10)}...
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
