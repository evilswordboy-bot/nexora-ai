import React, { useEffect, useState } from 'react';
import {
  Cpu,
  FileCode,
  Play,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Search,
  Terminal,
  History,
  Download,
  RefreshCw,
  Plus,
  Layers,
  Wrench,
  Zap,
  Lock,
  RotateCcw,
} from 'lucide-react';
import { api } from '../../services/api';
import {
  FirmwareCodeSearchHit,
  FirmwareCompileResult,
  FirmwareDeviceActionRecord,
  FirmwareExportResponse,
  FirmwareFrameworkId,
  FirmwareMetadataResponse,
  FirmwarePlatformMatrixEntry,
  FirmwareSerialMonitorResponse,
  FirmwareWorkspaceRecord,
  IoTBoardId,
  IoTProjectRecord,
} from '../../types';

export const FirmwareEngineeringStudio: React.FC = () => {
  const [metadata, setMetadata] = useState<FirmwareMetadataResponse | null>(null);
  const [platforms, setPlatforms] = useState<FirmwarePlatformMatrixEntry[]>([]);
  const [workspaces, setWorkspaces] = useState<FirmwareWorkspaceRecord[]>([]);
  const [iotProjects, setIotProjects] = useState<IoTProjectRecord[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<FirmwareWorkspaceRecord | null>(null);

  const [selectedFilePath, setSelectedFilePath] = useState<string>('');
  const [editorContent, setEditorContent] = useState<string>('');
  const [commitNote, setCommitNote] = useState<string>('Update modular driver and watchdog logic');

  const [activeSubTab, setActiveSubTab] = useState<
    'editor' | 'quality' | 'compile' | 'serial' | 'versions'
  >('editor');

  // New workspace form state
  const [newWsName, setNewWsName] = useState<string>('ESP32 Industrial Telemetry & Watchdog Firmware');
  const [newBoardId, setNewBoardId] = useState<IoTBoardId>('esp32_devkit_v1');
  const [newFramework, setNewFramework] = useState<FirmwareFrameworkId>('micropython');
  const [linkedIotProjectId, setLinkedIotProjectId] = useState<string>('');

  // Search state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchHits, setSearchHits] = useState<FirmwareCodeSearchHit[]>([]);

  // Compile, Serial, Device Action, Export states
  const [compileResult, setCompileResult] = useState<FirmwareCompileResult | null>(null);
  const [serialMonitor, setSerialMonitor] = useState<FirmwareSerialMonitorResponse | null>(null);
  const [serialMode, setSerialMode] = useState<
    'simulated_virtual_serial' | 'physical_authorized_serial'
  >('simulated_virtual_serial');
  const [resetReason, setResetReason] = useState<
    'POWERON_RESET' | 'SW_CPU_RESET' | 'WDT_RESET' | 'BROWNOUT_RST'
  >('POWERON_RESET');
  const [targetPort, setTargetPort] = useState<string>('COM3');
  const [pendingDeviceAction, setPendingDeviceAction] =
    useState<FirmwareDeviceActionRecord | null>(null);
  const [exportResult, setExportResult] = useState<FirmwareExportResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [statusBanner, setStatusBanner] = useState<string | null>(null);

  const loadInitialData = async () => {
    setLoading(true);
    setErrorBanner(null);
    try {
      const [meta, plats, wsList, iotList] = await Promise.all([
        api.getFirmwareMetadata(),
        api.listFirmwarePlatforms(),
        api.listFirmwareWorkspaces(),
        api.listIoTProjects(),
      ]);
      setMetadata(meta);
      setPlatforms(plats);
      setWorkspaces(wsList);
      setIotProjects(iotList);
      if (iotList.length > 0 && !linkedIotProjectId) {
        setLinkedIotProjectId(iotList[0].project_id);
      }
      if (wsList.length > 0) {
        selectWorkspace(wsList[0]);
      }
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to load Stage 24 Firmware Engineering Studio.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const selectWorkspace = (ws: FirmwareWorkspaceRecord) => {
    setActiveWorkspace(ws);
    setCompileResult(ws.last_compile || null);
    setExportResult(null);
    setPendingDeviceAction(null);
    const defaultFile =
      ws.files.find((f) => f.role === 'main_entry') || ws.files[0] || null;
    if (defaultFile) {
      setSelectedFilePath(defaultFile.path);
      setEditorContent(defaultFile.content);
    }
  };

  const handleSelectFile = (path: string) => {
    if (!activeWorkspace) return;
    const found = activeWorkspace.files.find((f) => f.path === path);
    if (found) {
      setSelectedFilePath(found.path);
      setEditorContent(found.content);
    }
  };

  const selectedPlatformEntry = platforms.find((p) => p.board_id === newBoardId);
  const unsupportedReason =
    selectedPlatformEntry?.unsupported_frameworks?.[newFramework] || null;

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorBanner(null);
    setStatusBanner(null);
    try {
      const created = await api.createFirmwareWorkspace({
        name: newWsName,
        board_id: newBoardId,
        framework: newFramework,
        iot_project_id: linkedIotProjectId || null,
      });
      const updatedList = await api.listFirmwareWorkspaces();
      setWorkspaces(updatedList);
      selectWorkspace(created);
      setStatusBanner(
        `Created firmware workspace "${created.name}" (${created.board_name} / ${created.framework}) v${created.semver}.`
      );
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to create firmware workspace.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveFile = async () => {
    if (!activeWorkspace || !selectedFilePath) return;
    setLoading(true);
    setErrorBanner(null);
    setStatusBanner(null);
    try {
      const updated = await api.updateFirmwareFile(activeWorkspace.fw_project_id, {
        file_path: selectedFilePath,
        content: editorContent,
        commit_note: commitNote || `Updated ${selectedFilePath}`,
        create_version_snapshot: true,
      });
      setActiveWorkspace(updated);
      setWorkspaces((prev) =>
        prev.map((w) => (w.fw_project_id === updated.fw_project_id ? updated : w))
      );
      setStatusBanner(
        `Saved ${selectedFilePath} and snapshot v${updated.semver} (Quality Gate: ${
          updated.quality_report.passed_quality_gate ? 'PASSED' : 'ISSUES DETECTED'
        }).`
      );
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to update firmware file.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !searchQuery.trim()) return;
    setErrorBanner(null);
    try {
      const hits = await api.searchFirmwareCode(activeWorkspace.fw_project_id, searchQuery.trim());
      setSearchHits(hits);
    } catch (err: any) {
      setErrorBanner(err.message || 'Code search failed.');
    }
  };

  const handleCompile = async () => {
    if (!activeWorkspace) return;
    setLoading(true);
    setErrorBanner(null);
    setStatusBanner(null);
    try {
      const res = await api.compileFirmwareWorkspace(activeWorkspace.fw_project_id, {
        run_unit_tests: true,
      });
      setCompileResult(res);
      const refreshed = await api.getFirmwareWorkspace(activeWorkspace.fw_project_id);
      setActiveWorkspace(refreshed);
      setActiveSubTab('compile');
      setStatusBanner(`Build ${res.build_id} finished with status: ${res.status}`);
    } catch (err: any) {
      setErrorBanner(err.message || 'Compilation request failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleReadSerial = async () => {
    if (!activeWorkspace) return;
    setLoading(true);
    setErrorBanner(null);
    try {
      const res = await api.readFirmwareSerialMonitor(activeWorkspace.fw_project_id, {
        mode: serialMode,
        simulate_reset_event: resetReason,
        lines_count: 8,
      });
      setSerialMonitor(res);
    } catch (err: any) {
      setSerialMonitor(null);
      setErrorBanner(err.message || 'Serial monitor connection failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleRequestDeviceAction = async (actionType: 'flash_firmware' | 'reset_device') => {
    if (!activeWorkspace) return;
    setLoading(true);
    setErrorBanner(null);
    try {
      const act = await api.requestFirmwareDeviceAction(activeWorkspace.fw_project_id, {
        action_type: actionType,
        target_port: targetPort,
        confirmed: false,
      });
      setPendingDeviceAction(act);
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to initiate device action.');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveDeviceAction = async (approved: boolean) => {
    if (!pendingDeviceAction) return;
    setLoading(true);
    setErrorBanner(null);
    try {
      const resolved = await api.approveFirmwareDeviceAction(pendingDeviceAction.action_id, {
        approved,
      });
      setPendingDeviceAction(resolved);
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to resolve device action approval.');
    } finally {
      setLoading(false);
    }
  };

  const handleRestoreVersion = async (versionId: string) => {
    if (!activeWorkspace) return;
    setLoading(true);
    setErrorBanner(null);
    try {
      const restored = await api.restoreFirmwareWorkspaceVersion(
        activeWorkspace.fw_project_id,
        versionId
      );
      selectWorkspace(restored);
      setStatusBanner(`Rolled back firmware workspace to v${restored.semver}.`);
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to restore firmware version.');
    } finally {
      setLoading(false);
    }
  };

  const handleExportArtifacts = async () => {
    if (!activeWorkspace) return;
    setLoading(true);
    setErrorBanner(null);
    try {
      const exp = await api.exportFirmwareWorkspace(activeWorkspace.fw_project_id);
      setExportResult(exp);
      setStatusBanner(exp.summary);
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to export firmware release package.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 overflow-y-auto p-6 space-y-6">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Cpu className="w-6 h-6 text-cyan-400" />
            <h1 className="text-xl font-bold tracking-tight text-white">
              Stage 24: Embedded Firmware Engineering Studio
            </h1>
            <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
              Reuses Stage 23 IoT Hardware & Netlist
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Multi-file modular firmware IDE, hardware-aware driver & ISR generator, static safety analyzer,
            sandboxed compiler, and approval-gated device interface.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadInitialData}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Studio
          </button>
          {activeWorkspace && (
            <button
              onClick={handleCompile}
              disabled={loading}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-xs font-semibold text-white shadow"
            >
              <Play className="w-3.5 h-3.5" />
              Compile & Run Unit Tests
            </button>
          )}
        </div>
      </div>

      {/* Honesty & Safety Policy Banner */}
      {metadata && (
        <div className="p-3 rounded-xl bg-slate-900/90 border border-cyan-500/30 flex items-start gap-3 text-xs text-slate-300">
          <ShieldAlert className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-semibold text-cyan-300">
              Authentic Toolchain & Physical Hardware Honesty Policy
            </div>
            <div>{metadata.safety_and_honesty_policy}</div>
            <div className="flex flex-wrap gap-2 pt-1">
              {Object.entries(metadata.detected_toolchains).map(([tc, available]) => (
                <span
                  key={tc}
                  className={`px-2 py-0.5 rounded text-[11px] font-mono border ${
                    available
                      ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                      : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                  }`}
                >
                  {tc}: {available ? 'INSTALLED' : 'NOT ON PATH'}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {errorBanner && (
        <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-500/40 text-xs text-rose-200 flex items-center justify-between">
          <span>{errorBanner}</span>
          <button onClick={() => setErrorBanner(null)} className="text-rose-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {statusBanner && (
        <div className="p-3 rounded-xl bg-emerald-950/50 border border-emerald-500/40 text-xs text-emerald-200 flex items-center justify-between">
          <span>{statusBanner}</span>
          <button onClick={() => setStatusBanner(null)} className="text-emerald-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* Workspace Selector + Create New Firmware Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-cyan-400" />
              Firmware Workspaces ({workspaces.length})
            </h2>
          </div>
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {workspaces.map((ws) => (
              <button
                key={ws.fw_project_id}
                onClick={() => selectWorkspace(ws)}
                className={`w-full text-left p-2.5 rounded-lg border transition ${
                  activeWorkspace?.fw_project_id === ws.fw_project_id
                    ? 'bg-cyan-950/40 border-cyan-500/50 text-white'
                    : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold truncate">{ws.name}</span>
                  <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300">
                    v{ws.semver}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-400">
                  <span>{ws.board_id}</span>
                  <span>•</span>
                  <span className="font-mono text-amber-300">{ws.framework}</span>
                  <span>•</span>
                  <span>{ws.files.length} files</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Create Hardware-Aware Firmware Workspace Form */}
        <form
          onSubmit={handleCreateWorkspace}
          className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3"
        >
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Plus className="w-4 h-4 text-emerald-400" />
              Create Hardware-Aware Multi-File Firmware Workspace
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Firmware Project Name</label>
              <input
                type="text"
                value={newWsName}
                onChange={(e) => setNewWsName(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white"
                required
              />
            </div>

            <div>
              <label className="block text-[11px] text-slate-400 mb-1">
                Link Stage 23 IoT Project (Validated Pinout & Wiring)
              </label>
              <select
                value={linkedIotProjectId}
                onChange={(e) => setLinkedIotProjectId(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white"
              >
                <option value="">Standalone Board Profile (Default Sensor/Relay Netlist)</option>
                {iotProjects.map((p) => (
                  <option key={p.project_id} value={p.project_id}>
                    {p.name} ({p.board_id} — {p.placed_components.length} components)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Target Board Profile</label>
              <select
                value={newBoardId}
                onChange={(e) => setNewBoardId(e.target.value as IoTBoardId)}
                className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white"
              >
                {platforms.map((p) => (
                  <option key={p.board_id} value={p.board_id}>
                    {p.board_name} ({p.mcu_or_soc})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] text-slate-400 mb-1">
                Firmware Framework & Toolchain
              </label>
              <select
                value={newFramework}
                onChange={(e) => setNewFramework(e.target.value as FirmwareFrameworkId)}
                className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white"
              >
                <option value="arduino_cpp">Arduino C++ Framework (arduino_cpp)</option>
                <option value="micropython">MicroPython Embedded VM (micropython)</option>
                <option value="esp_idf_c">Espressif ESP-IDF FreeRTOS C (esp_idf_c)</option>
                <option value="stm32_hal_c">STM32Cube HAL C (stm32_hal_c)</option>
                <option value="rpi_python_gpiozero">Linux Python gpiozero (rpi_python_gpiozero)</option>
              </select>
            </div>
          </div>

          {unsupportedReason ? (
            <div className="p-2.5 rounded-lg bg-amber-950/50 border border-amber-500/40 text-xs text-amber-200 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                <strong>Unsupported Combination ({newBoardId} + {newFramework}):</strong>{' '}
                {unsupportedReason}
              </span>
            </div>
          ) : (
            <div className="text-[11px] text-slate-400 flex items-center justify-between">
              <span>
                Supported frameworks for <strong>{selectedPlatformEntry?.board_name}</strong>:{' '}
                {selectedPlatformEntry?.supported_frameworks.join(', ')}
              </span>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white"
              >
                Generate Modular Workspace
              </button>
            </div>
          )}
        </form>
      </div>

      {/* Main Studio Workspace Area */}
      {activeWorkspace && (
        <div className="space-y-4">
          {/* Sub-navigation Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
            <div className="flex flex-wrap items-center gap-2">
              {[
                { id: 'editor', label: 'Code Editor & Project Tree', icon: FileCode },
                {
                  id: 'quality',
                  label: `Hardware & Static Quality (${activeWorkspace.quality_report.issues.length + activeWorkspace.hardware_diagnostics.length})`,
                  icon: Wrench,
                },
                { id: 'compile', label: 'Sandboxed Compile & Unit Tests', icon: Play },
                { id: 'serial', label: 'Serial Monitor & Device Flash', icon: Terminal },
                {
                  id: 'versions',
                  label: `Versions (${activeWorkspace.versions.length}) & Export`,
                  icon: History,
                },
              ].map((t) => {
                const Icon = t.icon;
                return (
                  <button
                    key={t.id}
                    onClick={() => setActiveSubTab(t.id as any)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                      activeSubTab === t.id
                        ? 'bg-cyan-600 text-white'
                        : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {t.label}
                  </button>
                );
              })}
            </div>

            <div className="flex items-center gap-2 text-xs">
              <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
                Board: <strong className="text-white">{activeWorkspace.board_name}</strong>
              </span>
              <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-cyan-300 font-mono">
                {activeWorkspace.framework}
              </span>
              <span
                className={`px-2.5 py-1 rounded font-semibold ${
                  activeWorkspace.quality_report.passed_quality_gate
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                }`}
              >
                Quality Gate: {activeWorkspace.quality_report.passed_quality_gate ? 'PASS' : 'FAIL'}
              </span>
            </div>
          </div>

          {/* TAB 1: MULTI-FILE CODE EDITOR & PROJECT TREE */}
          {activeSubTab === 'editor' && (
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
              {/* Left File Tree + Code Search + Manifest Info */}
              <div className="space-y-4">
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2">
                  <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Project Files ({activeWorkspace.files.length})
                  </div>
                  <div className="space-y-1">
                    {activeWorkspace.files.map((f) => (
                      <button
                        key={f.path}
                        onClick={() => handleSelectFile(f.path)}
                        className={`w-full text-left px-2.5 py-2 rounded-lg text-xs flex items-center justify-between transition ${
                          selectedFilePath === f.path
                            ? 'bg-cyan-600/20 text-cyan-300 border border-cyan-500/40'
                            : 'hover:bg-slate-800/70 text-slate-300'
                        }`}
                      >
                        <span className="font-mono truncate">{f.path}</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                          {f.role}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Code Search across Workspace */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2">
                  <form onSubmit={handleSearchCode} className="flex gap-1.5">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search symbols, pins, ISR..."
                      className="flex-1 px-2.5 py-1.5 rounded bg-slate-950 border border-slate-800 text-xs text-white"
                    />
                    <button
                      type="submit"
                      className="px-2.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200"
                    >
                      <Search className="w-3.5 h-3.5" />
                    </button>
                  </form>
                  {searchHits.length > 0 && (
                    <div className="space-y-1 max-h-40 overflow-y-auto pt-1">
                      {searchHits.map((hit, idx) => (
                        <button
                          key={`${hit.file_path}-${hit.line_number}-${idx}`}
                          onClick={() => handleSelectFile(hit.file_path)}
                          className="w-full text-left p-1.5 rounded bg-slate-950 hover:bg-slate-800 text-[11px]"
                        >
                          <div className="text-cyan-400 font-mono">
                            {hit.file_path}:{hit.line_number}
                          </div>
                          <div className="text-slate-400 font-mono truncate">{hit.line_preview}</div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Build Settings & Library Manifest */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2 text-xs">
                  <div className="font-semibold text-slate-300 uppercase tracking-wider">
                    Build Settings & Libraries
                  </div>
                  <div className="grid grid-cols-2 gap-1 text-[11px] text-slate-400">
                    <span>Optimization:</span>
                    <span className="font-mono text-white">
                      {activeWorkspace.build_settings.optimization_level}
                    </span>
                    <span>Watchdog Timer:</span>
                    <span className="font-mono text-emerald-300">
                      {activeWorkspace.build_settings.watchdog_enabled
                        ? `${activeWorkspace.build_settings.watchdog_timeout_ms} ms`
                        : 'Disabled'}
                    </span>
                    <span>Serial Baud:</span>
                    <span className="font-mono text-white">
                      {activeWorkspace.build_settings.serial_baud_rate}
                    </span>
                  </div>
                  <div className="pt-2 border-t border-slate-800 space-y-1">
                    {activeWorkspace.libraries.map((lib) => (
                      <div
                        key={lib.name}
                        className="p-1.5 rounded bg-slate-950 border border-slate-800/80 text-[11px]"
                      >
                        <div className="font-semibold text-slate-200">
                          {lib.name} <span className="text-cyan-400 font-mono">{lib.version}</span>
                        </div>
                        <div className="text-slate-400">{lib.purpose}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Right Code Editor */}
              <div className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-semibold text-cyan-300">
                      {selectedFilePath}
                    </span>
                    <span className="text-xs text-slate-500">
                      ({editorContent.split('\n').length} lines)
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={commitNote}
                      onChange={(e) => setCommitNote(e.target.value)}
                      placeholder="Version commit note..."
                      className="px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-xs text-slate-200 w-56"
                    />
                    <button
                      onClick={handleSaveFile}
                      disabled={loading}
                      className="px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white"
                    >
                      Save & Snapshot Version
                    </button>
                  </div>
                </div>

                <textarea
                  value={editorContent}
                  onChange={(e) => setEditorContent(e.target.value)}
                  rows={22}
                  spellCheck={false}
                  className="w-full font-mono text-xs bg-slate-950 text-slate-100 p-4 rounded-xl border border-slate-800 focus:outline-none focus:border-cyan-500 leading-relaxed"
                />
              </div>
            </div>
          )}

          {/* TAB 2: HARDWARE DIAGNOSTICS & STATIC QUALITY ANALYZER */}
          {activeSubTab === 'quality' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Hardware-Aware Diagnostics */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-400" />
                  Hardware-Aware Pin, Voltage & Peripheral Diagnostics (
                  {activeWorkspace.hardware_diagnostics.length})
                </h3>
                {activeWorkspace.hardware_diagnostics.length === 0 ? (
                  <div className="p-4 rounded-lg bg-emerald-950/30 border border-emerald-500/30 text-xs text-emerald-300 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4" />
                    All pin assignments, voltage levels, and peripheral headers match{' '}
                    {activeWorkspace.board_name}.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {activeWorkspace.hardware_diagnostics.map((d) => (
                      <div
                        key={d.diag_id}
                        className="p-3 rounded-lg bg-slate-950 border border-amber-500/40 text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-amber-300">{d.title}</span>
                          <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-200">
                            {d.category} ({d.severity})
                          </span>
                        </div>
                        <p className="text-slate-300">{d.detail}</p>
                        {d.file_path && (
                          <div className="text-[11px] font-mono text-cyan-400">
                            Location: {d.file_path}:{d.line_number || 1}
                          </div>
                        )}
                        <div className="text-[11px] text-emerald-300">
                          <strong>Suggested Fix:</strong> {d.suggested_fix}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Embedded Static Code Quality & Unit Tests */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Wrench className="w-4 h-4 text-cyan-400" />
                  Static Embedded Safety Analyzer & Unit Tests
                </h3>
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2 rounded bg-slate-950 border border-slate-800">
                    <div className="text-slate-400">Critical</div>
                    <div className="text-lg font-bold text-rose-400">
                      {activeWorkspace.quality_report.critical_count}
                    </div>
                  </div>
                  <div className="p-2 rounded bg-slate-950 border border-slate-800">
                    <div className="text-slate-400">Errors</div>
                    <div className="text-lg font-bold text-amber-400">
                      {activeWorkspace.quality_report.error_count}
                    </div>
                  </div>
                  <div className="p-2 rounded bg-slate-950 border border-slate-800">
                    <div className="text-slate-400">Warnings</div>
                    <div className="text-lg font-bold text-yellow-300">
                      {activeWorkspace.quality_report.warning_count}
                    </div>
                  </div>
                </div>

                {activeWorkspace.quality_report.issues.length === 0 ? (
                  <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-500/30 text-xs text-emerald-300">
                    Zero static safety issues (no unsafe strcpy/sprintf, no blocking loops, watchdog fed,
                    no hardcoded secrets).
                  </div>
                ) : (
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {activeWorkspace.quality_report.issues.map((iss) => (
                      <div
                        key={iss.issue_id}
                        className="p-2.5 rounded-lg bg-slate-950 border border-rose-500/40 text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-rose-300">
                            {iss.file_path}:{iss.line_number}
                          </span>
                          <span className="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-200 text-[10px] font-mono">
                            {iss.category} ({iss.severity})
                          </span>
                        </div>
                        <div className="font-mono text-[11px] bg-slate-900 p-1.5 rounded text-slate-200">
                          {iss.code_snippet}
                        </div>
                        <div className="text-slate-300">{iss.message}</div>
                        <div className="text-emerald-300 text-[11px]">
                          <strong>Fix:</strong> {iss.suggested_fix}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-200">
                      Host-Side Embedded Unit Tests:
                    </span>
                    <span
                      className={`font-mono px-2 py-0.5 rounded ${
                        activeWorkspace.quality_report.unit_tests_passed
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : 'bg-rose-500/20 text-rose-300'
                      }`}
                    >
                      {activeWorkspace.quality_report.unit_tests_passed ? 'PASSED' : 'FAILED'}
                    </span>
                  </div>
                  <pre className="text-[11px] font-mono text-slate-400 whitespace-pre-wrap max-h-32 overflow-y-auto">
                    {activeWorkspace.quality_report.unit_test_output}
                  </pre>
                  <div className="text-[11px] text-amber-300 pt-1">
                    <strong>HIL Status ({activeWorkspace.quality_report.hil_status}):</strong>{' '}
                    {activeWorkspace.quality_report.hil_notes}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: SANDBOXED COMPILE & DEBUG */}
          {activeSubTab === 'compile' && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">
                    Isolated Sandboxed Compiler & Bytecode Verifier
                  </h3>
                  <p className="text-xs text-slate-400">
                    Executes real compiler/bytecode toolchains when installed and never fabricates binary
                    build success.
                  </p>
                </div>
                <button
                  onClick={handleCompile}
                  disabled={loading}
                  className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-xs font-semibold text-white"
                >
                  Run Build Now
                </button>
              </div>

              {compileResult ? (
                <div className="space-y-3 text-xs">
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <span className="text-slate-400">Build Status: </span>
                      <span
                        className={`font-mono font-bold px-2 py-0.5 rounded ${
                          compileResult.status === 'SUCCEEDED'
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : compileResult.status === 'BLOCKED_TOOLCHAIN_MISSING'
                            ? 'bg-amber-500/20 text-amber-300'
                            : 'bg-rose-500/20 text-rose-300'
                        }`}
                      >
                        {compileResult.status}
                      </span>
                    </div>
                    <div className="font-mono text-slate-400">
                      Toolchain: <span className="text-slate-200">{compileResult.toolchain_binary}</span>
                    </div>
                    <div className="font-mono text-slate-400">
                      Binary Produced:{' '}
                      <strong className="text-white">
                        {String(compileResult.binary_artifact_produced)}
                      </strong>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-cyan-950/30 border border-cyan-500/30 text-cyan-200">
                    <strong>Build Honesty Notice:</strong> {compileResult.honesty_notice}
                  </div>

                  {compileResult.diagnostics.length > 0 && (
                    <div className="space-y-2">
                      <div className="font-semibold text-rose-300">
                        Compiler Diagnostics ({compileResult.diagnostics.length})
                      </div>
                      {compileResult.diagnostics.map((diag, idx) => (
                        <div
                          key={idx}
                          className="p-2.5 rounded bg-slate-950 border border-rose-500/40 space-y-1"
                        >
                          <div className="font-mono text-rose-300">
                            {diag.file_path}:{diag.line_number}:{diag.column} — {diag.message}
                          </div>
                          {diag.source_line && (
                            <div className="font-mono bg-slate-900 p-1.5 rounded text-slate-200">
                              {diag.source_line}
                            </div>
                          )}
                          <div className="text-emerald-300">
                            <strong>Suggested Fix:</strong> {diag.suggested_fix}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {compileResult.produced_artifacts.length > 0 && (
                    <div className="space-y-1">
                      <div className="font-semibold text-emerald-300">
                        Genuinely Produced Build Artifacts ({compileResult.produced_artifacts.length})
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {compileResult.produced_artifacts.map((art) => (
                          <div
                            key={art.relative_path}
                            className="p-2 rounded bg-slate-950 border border-emerald-500/30 font-mono text-[11px]"
                          >
                            <div className="text-emerald-300">{art.relative_path}</div>
                            <div className="text-slate-400">
                              {art.size_bytes} bytes • SHA256: {art.sha256.slice(0, 16)}...
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {(compileResult.compiler_stdout || compileResult.compiler_stderr) && (
                    <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300 whitespace-pre-wrap">
                      {compileResult.compiler_stdout}
                      {compileResult.compiler_stderr ? `\n${compileResult.compiler_stderr}` : ''}
                    </pre>
                  )}
                </div>
              ) : (
                <div className="text-xs text-slate-400">
                  Click <strong>Run Build Now</strong> to execute sandboxed compilation and unit tests.
                </div>
              )}
            </div>
          )}

          {/* TAB 4: SERIAL MONITOR & APPROVAL-GATED DEVICE FLASH/RESET */}
          {activeSubTab === 'serial' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Serial Monitor Panel */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-cyan-400" />
                  Serial Monitor (Simulated vs. Physical Distinction)
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div>
                    <label className="block text-[11px] text-slate-400 mb-1">Serial Source Mode</label>
                    <select
                      value={serialMode}
                      onChange={(e) => setSerialMode(e.target.value as any)}
                      className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-800 text-white"
                    >
                      <option value="simulated_virtual_serial">
                        Simulated Virtual Serial (Deterministic Model)
                      </option>
                      <option value="physical_authorized_serial">
                        Physical Authorized Serial Port (Hardware Required)
                      </option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] text-slate-400 mb-1">
                      Simulated Reset Event
                    </label>
                    <select
                      value={resetReason}
                      onChange={(e) => setResetReason(e.target.value as any)}
                      className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-800 text-white"
                    >
                      <option value="POWERON_RESET">POWERON_RESET</option>
                      <option value="WDT_RESET">WDT_RESET (Watchdog Trigger)</option>
                      <option value="SW_CPU_RESET">SW_CPU_RESET</option>
                      <option value="BROWNOUT_RST">BROWNOUT_RST</option>
                    </select>
                  </div>
                </div>

                <button
                  onClick={handleReadSerial}
                  disabled={loading}
                  className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-xs font-semibold text-white"
                >
                  Capture Serial Stream
                </button>

                {serialMonitor && (
                  <div className="space-y-2 text-xs">
                    <div className="p-2 rounded bg-amber-950/50 border border-amber-500/40 text-amber-200 text-[11px]">
                      <strong>
                        {serialMonitor.is_simulated ? 'SIMULATED STREAM' : 'PHYSICAL STREAM'}:
                      </strong>{' '}
                      {serialMonitor.distinction_banner}
                    </div>
                    <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px] space-y-1 max-h-60 overflow-y-auto">
                      {serialMonitor.logs.map((entry) => (
                        <div key={entry.seq} className="text-slate-300">
                          <span className="text-slate-500">[{entry.timestamp_ms}ms]</span>{' '}
                          <span className="text-cyan-400">[{entry.event_type}]</span> {entry.message}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Approval-Gated Device Flash & Reset */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Lock className="w-4 h-4 text-amber-400" />
                  Approval-Gated Device Flashing, Reset & Unbricking Guide
                </h3>
                <p className="text-xs text-slate-400">
                  Flashing or resetting a physical board is a consequential operation requiring explicit
                  user approval.
                </p>

                <div className="flex items-center gap-2 text-xs">
                  <input
                    type="text"
                    value={targetPort}
                    onChange={(e) => setTargetPort(e.target.value)}
                    placeholder="Serial Port (e.g. COM3, /dev/ttyUSB0)"
                    className="px-3 py-1.5 rounded bg-slate-950 border border-slate-800 text-white"
                  />
                  <button
                    onClick={() => handleRequestDeviceAction('flash_firmware')}
                    className="px-3 py-1.5 rounded bg-amber-600 hover:bg-amber-500 text-white font-semibold"
                  >
                    Request Flash Firmware
                  </button>
                  <button
                    onClick={() => handleRequestDeviceAction('reset_device')}
                    className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200"
                  >
                    Request Reset
                  </button>
                </div>

                {pendingDeviceAction && (
                  <div className="p-3 rounded-lg bg-slate-950 border border-amber-500/40 text-xs space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-amber-300">
                        Action: {pendingDeviceAction.action_type} ({pendingDeviceAction.target_port})
                      </span>
                      <span className="font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-200">
                        {pendingDeviceAction.status}
                      </span>
                    </div>
                    <div className="font-mono text-[11px] bg-slate-900 p-2 rounded text-cyan-300">
                      $ {pendingDeviceAction.cli_command_preview}
                    </div>
                    <div className="text-slate-300">{pendingDeviceAction.message}</div>
                    {pendingDeviceAction.status === 'WAITING_FOR_APPROVAL' && (
                      <div className="flex items-center gap-2 pt-1">
                        <button
                          onClick={() => handleApproveDeviceAction(true)}
                          className="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold"
                        >
                          Approve Hardware Action
                        </button>
                        <button
                          onClick={() => handleApproveDeviceAction(false)}
                          className="px-3 py-1 rounded bg-rose-700 hover:bg-rose-600 text-white"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                )}

                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1">
                  <div className="font-semibold text-slate-200">
                    Bootloader Recovery & Safe Rollback Guidance
                  </div>
                  {activeWorkspace.recovery_guidance.map((step, i) => (
                    <div key={i} className="text-slate-400 text-[11px]">
                      {step}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: VERSION HISTORY, ROLLBACK & AUTHENTIC ARTIFACT EXPORT */}
          {activeSubTab === 'versions' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Immutable Version Snapshots */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <History className="w-4 h-4 text-cyan-400" />
                  Firmware Version History ({activeWorkspace.versions.length})
                </h3>
                <div className="space-y-2">
                  {activeWorkspace.versions
                    .slice()
                    .reverse()
                    .map((ver) => (
                      <div
                        key={ver.version_id}
                        className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs"
                      >
                        <div>
                          <div className="font-semibold text-white">
                            v{ver.semver} — <span className="text-slate-300">{ver.commit_note}</span>
                          </div>
                          <div className="text-[11px] text-slate-500">
                            {ver.files.length} files • {ver.created_at}
                          </div>
                        </div>
                        <button
                          onClick={() => handleRestoreVersion(ver.version_id)}
                          className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          Restore v{ver.semver}
                        </button>
                      </div>
                    ))}
                </div>
              </div>

              {/* Authentic Artifact Export */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                      <Download className="w-4 h-4 text-emerald-400" />
                      Export Authentic Firmware Release Package
                    </h3>
                    <p className="text-xs text-slate-400">
                      Exports source files, dependency manifests, SHA-256 release notes, and genuinely
                      compiled bytecode/binaries.
                    </p>
                  </div>
                  <button
                    onClick={handleExportArtifacts}
                    disabled={loading}
                    className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white"
                  >
                    Export Release v{activeWorkspace.semver}
                  </button>
                </div>

                {exportResult && (
                  <div className="p-3 rounded-lg bg-slate-950 border border-emerald-500/40 text-xs space-y-2">
                    <div className="font-semibold text-emerald-300">{exportResult.summary}</div>
                    <div className="font-mono text-[11px] text-slate-400">
                      Stage 17 Workspace Folder: {exportResult.workspace_relative_dir}
                    </div>
                    <div className="space-y-1 max-h-48 overflow-y-auto">
                      {exportResult.artifacts.map((art) => (
                        <div
                          key={art.relative_path}
                          className="flex items-center justify-between font-mono text-[11px] p-1.5 rounded bg-slate-900"
                        >
                          <span className="text-cyan-300">{art.relative_path}</span>
                          <span className="text-slate-400">
                            {art.artifact_type} ({art.size_bytes} B)
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
