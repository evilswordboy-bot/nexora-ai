import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Radio,
  Activity,
  Shield,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Plus,
  Key,
  Trash2,
  Play,
  Download,
  Terminal,
  Cpu,
  Layers,
  CheckCircle2,
  XCircle,
  Copy,
  Clock,
  Gauge,
  Sliders,
  Send,
  Eye,
  Server,
  Zap,
} from 'lucide-react';
import { api } from '../../services/api';
import {
  IoTDeviceRecord,
  IoTDeviceTokenResponse,
  TelemetryEventRecord,
  AlertRuleRecord,
  AlertRecord,
  DeviceCommandRecord,
  TelemetryDeviceStatsResponse,
  TelemetryExportResponse,
  TelemetryMetadataResponse,
  IoTBoardId,
  IoTIngestionProtocol,
  AlertOperator,
  AlertSeverity,
  DeviceCommandType,
} from '../../types';

export const IoTTelemetryStudio: React.FC = () => {
  // Navigation & Sub-tabs
  const [activeTab, setActiveTab] = useState<'fleet' | 'telemetry' | 'alerts' | 'commands' | 'export'>('fleet');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Core Data State
  const [metadata, setMetadata] = useState<TelemetryMetadataResponse | null>(null);
  const [devices, setDevices] = useState<IoTDeviceRecord[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
  const [deviceStats, setDeviceStats] = useState<TelemetryDeviceStatsResponse | null>(null);
  const [events, setEvents] = useState<TelemetryEventRecord[]>([]);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [alertRules, setAlertRules] = useState<AlertRuleRecord[]>([]);
  const [commands, setCommands] = useState<DeviceCommandRecord[]>([]);

  // Auto-refresh timer
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date>(new Date());

  // Registration Modal State
  const [showRegModal, setShowRegModal] = useState<boolean>(false);
  const [regName, setRegName] = useState<string>('ESP32 Industrial Telemetry Node');
  const [regBoardId, setRegBoardId] = useState<IoTBoardId>('esp32_devkit_v1');
  const [regProtocol, setRegProtocol] = useState<IoTIngestionProtocol>('http');
  const [regSimulated, setRegSimulated] = useState<boolean>(true);
  const [regFirmwareVersion, setRegFirmwareVersion] = useState<string>('v1.0.0');

  // One-time Token Reveal Modal State
  const [tokenReveal, setTokenReveal] = useState<IoTDeviceTokenResponse | null>(null);
  const [copiedToken, setCopiedToken] = useState<boolean>(false);

  // New Alert Rule Modal State
  const [showRuleModal, setShowRuleModal] = useState<boolean>(false);
  const [ruleMetric, setRuleMetric] = useState<string>('temperature');
  const [ruleOperator, setRuleOperator] = useState<AlertOperator>('gt');
  const [ruleThreshold, setRuleThreshold] = useState<number>(75);
  const [ruleSeverity, setRuleSeverity] = useState<AlertSeverity>('warning');
  const [ruleCooldown, setRuleCooldown] = useState<number>(30);
  const [ruleDescription, setRuleDescription] = useState<string>('High temperature thermal safety breach');

  // Command Dispatch State
  const [cmdType, setCmdType] = useState<DeviceCommandType>('reboot');
  const [cmdParamsJson, setCmdParamsJson] = useState<string>('{\n  "mode": "soft_reset"\n}');
  const [confirmModalCmd, setConfirmModalCmd] = useState<DeviceCommandRecord | null>(null);

  // Simulator & Export State
  const [simTickCount, setSimTickCount] = useState<number>(5);
  const [simAnomaly, setSimAnomaly] = useState<string>('none');
  const [exportFormat, setExportFormat] = useState<'csv' | 'json'>('csv');
  const [exportTimeRange, setExportTimeRange] = useState<string>('24h');
  const [latestExport, setLatestExport] = useState<TelemetryExportResponse | null>(null);

  // 1. Initial Load: Metadata, Devices, Rules, Alerts
  const loadFleetData = useCallback(async () => {
    try {
      setIsLoading(true);
      setErrorMsg(null);
      const [metaRes, devList, alertList] = await Promise.all([
        api.getTelemetryMetadata(),
        api.listIoTDevices(),
        api.listAlerts(),
      ]);
      setMetadata(metaRes);
      setDevices(devList);
      setAlerts(alertList);

      const activeDevId = selectedDeviceId || (devList.length > 0 ? devList[0].device_id : '');
      if (activeDevId) {
        if (!selectedDeviceId) setSelectedDeviceId(activeDevId);
        const ruleList = await api.listAlertRules(activeDevId);
        setAlertRules(ruleList);
      }
      setLastRefreshedAt(new Date());
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load IoT fleet data');
    } finally {
      setIsLoading(false);
    }
  }, [selectedDeviceId]);

  useEffect(() => {
    loadFleetData();
  }, [loadFleetData]);

  // 2. Load Selected Device Specific Stats & Events
  const loadDeviceDetail = useCallback(async (deviceId: string) => {
    if (!deviceId) return;
    try {
      const [statsRes, eventsRes, cmdsRes] = await Promise.all([
        api.getIoTDeviceStats(deviceId),
        api.listTelemetryEvents(deviceId, { limit: 50 }),
        api.listDeviceCommands(deviceId),
      ]);
      setDeviceStats(statsRes);
      setEvents(eventsRes);
      setCommands(cmdsRes);
    } catch (err: any) {
      console.warn('Failed to load device details:', err);
    }
  }, []);

  useEffect(() => {
    if (selectedDeviceId) {
      loadDeviceDetail(selectedDeviceId);
    }
  }, [selectedDeviceId, loadDeviceDetail]);

  // 3. Periodic Poll (10s) if autoRefresh is enabled
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      loadFleetData();
      if (selectedDeviceId) {
        loadDeviceDetail(selectedDeviceId);
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [autoRefresh, loadFleetData, selectedDeviceId, loadDeviceDetail]);

  // Registration Handler
  const handleRegisterDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsLoading(true);
      setErrorMsg(null);
      const res = await api.registerIoTDevice({
        name: regName,
        board_id: regBoardId,
        is_simulated: regSimulated,
        firmware_version: regFirmwareVersion,
      });
      setShowRegModal(false);
      setTokenReveal(res.credentials);
      setSuccessMsg(`Device registered successfully: ${res.device.name}`);
      await loadFleetData();
      setSelectedDeviceId(res.device.device_id);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to register device');
    } finally {
      setIsLoading(false);
    }
  };

  // Token Rotation Handler
  const handleRotateToken = async (deviceId: string) => {
    if (!window.confirm('Are you sure you want to rotate this device credential? The existing token will become immediately invalid.')) {
      return;
    }
    try {
      setIsLoading(true);
      const res = await api.rotateIoTDeviceToken(deviceId);
      setTokenReveal(res);
      setSuccessMsg(`Credential rotated for ${res.name}. PBKDF2 hash updated.`);
      await loadFleetData();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to rotate device credential');
    } finally {
      setIsLoading(false);
    }
  };

  // Token Revocation Handler
  const handleRevokeToken = async (deviceId: string) => {
    if (!window.confirm('Revoke credential? The device will be blocked from sending telemetry or receiving commands until a new token is created.')) {
      return;
    }
    try {
      setIsLoading(true);
      await api.revokeIoTDeviceToken(deviceId);
      setSuccessMsg(`Credential revoked for device ${deviceId}.`);
      await loadFleetData();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to revoke credential');
    } finally {
      setIsLoading(false);
    }
  };

  // Alert Rule Creation Handler
  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDeviceId) {
      setErrorMsg('Select a target device first');
      return;
    }
    try {
      setIsLoading(true);
      await api.createAlertRule(selectedDeviceId, {
        metric_key: ruleMetric,
        operator: ruleOperator,
        threshold_val_primary: Number(ruleThreshold),
        severity: ruleSeverity,
        cooldown_seconds: Number(ruleCooldown),
        description: ruleDescription,
      });
      setShowRuleModal(false);
      setSuccessMsg('Alert rule created and armed.');
      const ruleList = await api.listAlertRules(selectedDeviceId);
      setAlertRules(ruleList);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create alert rule');
    } finally {
      setIsLoading(false);
    }
  };

  // Acknowledge Alert Handler
  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await api.acknowledgeAlert(alertId);
      setSuccessMsg('Alert acknowledged.');
      const alertList = await api.listAlerts();
      setAlerts(alertList);
      if (selectedDeviceId) loadDeviceDetail(selectedDeviceId);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to acknowledge alert');
    }
  };

  // Command Dispatch Handler
  const handleDispatchCommand = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDeviceId) return;
    try {
      let params = {};
      try {
        params = JSON.parse(cmdParamsJson || '{}');
      } catch (pe) {
        setErrorMsg('Invalid JSON parameters format');
        return;
      }

      setIsLoading(true);
      setErrorMsg(null);
      const cmdRes = await api.createDeviceCommand(selectedDeviceId, {
        command_type: cmdType,
        parameters: params,
      });

      if (cmdRes.requires_confirmation) {
        setConfirmModalCmd(cmdRes);
      } else {
        setSuccessMsg(`Command ${cmdRes.command_type} dispatched.`);
      }
      loadDeviceDetail(selectedDeviceId);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to dispatch command');
    } finally {
      setIsLoading(false);
    }
  };

  // Consequential Command Confirmation Handler
  const handleConfirmCommand = async (approved: boolean) => {
    if (!confirmModalCmd) return;
    try {
      setIsLoading(true);
      const res = await api.confirmDeviceCommand(confirmModalCmd.command_id, approved);
      setConfirmModalCmd(null);
      setSuccessMsg(`Command ${res.command_id} ${approved ? 'confirmed and dispatched' : 'rejected'}.`);
      if (selectedDeviceId) loadDeviceDetail(selectedDeviceId);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to confirm command');
    } finally {
      setIsLoading(false);
    }
  };

  // Simulator Tick Handler
  const handleSimulateTick = async () => {
    if (!selectedDeviceId) return;
    try {
      setIsLoading(true);
      setErrorMsg(null);
      const tickRes = await api.simulateTelemetryTick(selectedDeviceId, {
        tick_count: Number(simTickCount),
        anomaly_inject: simAnomaly !== 'none' ? simAnomaly : undefined,
      });
      setSuccessMsg(`Simulated ${tickRes.ticks_generated} deterministic telemetry ticks.`);
      await loadFleetData();
      await loadDeviceDetail(selectedDeviceId);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to simulate telemetry');
    } finally {
      setIsLoading(false);
    }
  };

  // Dataset Export Handler
  const handleExport = async () => {
    if (!selectedDeviceId) return;
    try {
      setIsLoading(true);
      const exportRes = await api.exportTelemetry(selectedDeviceId, {
        format: exportFormat,
        time_range: exportTimeRange as any,
      });
      setLatestExport(exportRes);
      setSuccessMsg(`Exported ${exportRes.total_events_exported} events as ${exportFormat.toUpperCase()}.`);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to export telemetry');
    } finally {
      setIsLoading(false);
    }
  };

  const selectedDevice = useMemo(
    () => devices.find((d) => d.device_id === selectedDeviceId),
    [devices, selectedDeviceId]
  );

  return (
    <div className="flex flex-col h-full bg-midnight-950 text-slate-100 overflow-hidden">
      {/* Top Header / Status Banner */}
      <div className="px-6 py-4 border-b border-slate-800/80 bg-midnight-900/60 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Radio className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-100 tracking-wide">
                IoT Device Connectivity & Live Telemetry
              </h1>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
                STAGE 25
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Authenticated device registry, live sensor streams, anomaly alerts & consequential command gates.
            </p>
          </div>
        </div>

        {/* Global Fleet Quick Stats */}
        <div className="flex items-center gap-2 text-xs">
          <div className="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center gap-2">
            <Server className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-400">Fleet:</span>
            <span className="font-semibold text-slate-200">{devices.length}</span>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            <span className="text-slate-400">Online:</span>
            <span className="font-semibold text-emerald-400">
              {devices.filter((d) => d.status === 'online').length}
            </span>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-slate-400">Active Alerts:</span>
            <span className="font-semibold text-amber-400">
              {alerts.filter((a) => a.status === 'active').length}
            </span>
          </div>
          <button
            onClick={() => {
              loadFleetData();
              if (selectedDeviceId) loadDeviceDetail(selectedDeviceId);
            }}
            disabled={isLoading}
            className="p-2 rounded-lg bg-slate-800/60 hover:bg-slate-700/60 text-slate-300 border border-slate-700 transition"
            title="Refresh Fleet Data"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Notifications / Alerts Bar */}
      {errorMsg && (
        <div className="px-6 py-2.5 bg-rose-500/10 border-b border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-rose-400 hover:text-rose-200">
            &times;
          </button>
        </div>
      )}
      {successMsg && (
        <div className="px-6 py-2.5 bg-emerald-500/10 border-b border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-emerald-200">
            &times;
          </button>
        </div>
      )}

      {/* Sub-tab Navigation */}
      <div className="px-6 border-b border-slate-800/80 bg-midnight-950 flex items-center justify-between">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('fleet')}
            className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition ${
              activeTab === 'fleet'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Server className="w-4 h-4" />
            <span>Device Registry</span>
          </button>
          <button
            onClick={() => setActiveTab('telemetry')}
            className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition ${
              activeTab === 'telemetry'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Live Telemetry</span>
          </button>
          <button
            onClick={() => setActiveTab('alerts')}
            className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition ${
              activeTab === 'alerts'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldAlert className="w-4 h-4" />
            <span>Alerts & Rules</span>
            {alerts.filter((a) => a.status === 'active').length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-rose-500/20 text-rose-300 border border-rose-500/40">
                {alerts.filter((a) => a.status === 'active').length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('commands')}
            className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition ${
              activeTab === 'commands'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Terminal className="w-4 h-4" />
            <span>Commands & Gates</span>
          </button>
          <button
            onClick={() => setActiveTab('export')}
            className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition ${
              activeTab === 'export'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Download className="w-4 h-4" />
            <span>Simulator & Export</span>
          </button>
        </div>

        {/* Device selector quick dropdown */}
        <div className="flex items-center gap-3">
          <label className="text-xs text-slate-400 hidden sm:inline">Active Node:</label>
          <select
            value={selectedDeviceId}
            onChange={(e) => setSelectedDeviceId(e.target.value)}
            className="text-xs bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            {devices.map((d) => (
              <option key={d.device_id} value={d.device_id}>
                {d.name} ({d.board_id}) — {d.status.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* TAB 1: FLEET REGISTRY */}
        {activeTab === 'fleet' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-100">Registered IoT Fleet</h2>
                <p className="text-xs text-slate-400">
                  Provisioned microcontrollers, edge gateways, and simulated endpoints with hardware-hashed tokens.
                </p>
              </div>
              <button
                onClick={() => setShowRegModal(true)}
                className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-midnight-950 font-bold text-xs shadow-cyan-glow transition"
              >
                <Plus className="w-4 h-4" />
                <span>Register New Device</span>
              </button>
            </div>

            {/* Device Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {devices.map((dev) => (
                <div
                  key={dev.device_id}
                  onClick={() => setSelectedDeviceId(dev.device_id)}
                  className={`p-4 rounded-xl border transition cursor-pointer ${
                    dev.device_id === selectedDeviceId
                      ? 'border-cyan-500 bg-cyan-950/20 shadow-cyan-glow/20'
                      : 'border-slate-800 bg-midnight-900/60 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-slate-100">{dev.name}</span>
                        {dev.is_simulated && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                            SIMULATED
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] font-mono text-slate-400 mt-0.5">{dev.device_id}</p>
                    </div>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                        dev.status === 'online'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : dev.status === 'degraded'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'bg-slate-700/40 text-slate-400 border border-slate-700'
                      }`}
                    >
                      {dev.status}
                    </span>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-slate-300">
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800/80">
                      <span className="text-[10px] text-slate-500 block uppercase">Hardware</span>
                      <span className="font-mono text-slate-200 truncate block">{dev.board_id}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800/80">
                      <span className="text-[10px] text-slate-500 block uppercase">Protocol</span>
                      <span className="font-mono text-cyan-300 block">{dev.ingestion_protocol.toUpperCase()}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800/80">
                      <span className="text-[10px] text-slate-500 block uppercase">Firmware</span>
                      <span className="font-mono text-slate-300 block">{dev.firmware_version}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800/80">
                      <span className="text-[10px] text-slate-500 block uppercase">Events Ingested</span>
                      <span className="font-semibold text-slate-200 block">{dev.total_events_received}</span>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
                    <span className="text-slate-500 text-[11px]">
                      {dev.last_seen_at
                        ? `Seen: ${new Date(dev.last_seen_at).toLocaleTimeString()}`
                        : 'Never seen'}
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRotateToken(dev.device_id);
                        }}
                        className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-cyan-300 transition"
                        title="Rotate Token"
                      >
                        <Key className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRevokeToken(dev.device_id);
                        }}
                        className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-rose-400 transition"
                        title="Revoke Token"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 2: LIVE TELEMETRY DASHBOARD */}
        {activeTab === 'telemetry' && (
          <div className="space-y-6">
            {selectedDevice ? (
              <>
                {/* Node Status Banner */}
                <div className="p-4 rounded-xl border border-slate-800 bg-midnight-900/60 flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                      <Cpu className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-bold text-slate-100">{selectedDevice.name}</h3>
                        <span className="font-mono text-xs text-slate-400">({selectedDevice.device_id})</span>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                            selectedDevice.status === 'online'
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {selectedDevice.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400">
                        {deviceStats?.data_freshness_label || 'Awaiting telemetry telemetry stream'} &bull;{' '}
                        {selectedDevice.board_id} &bull; Firmware {selectedDevice.firmware_version}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleSimulateTick}
                      disabled={isLoading}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-200 border border-cyan-500/40 text-xs font-semibold transition"
                    >
                      <Zap className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Trigger Simulator Tick</span>
                    </button>
                  </div>
                </div>

                {/* Metric Summary Cards */}
                {deviceStats?.latest_metrics && Object.keys(deviceStats.latest_metrics).length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {Object.entries(deviceStats.latest_metrics).map(([key, val]) => {
                      const range = deviceStats.metric_ranges?.[key];
                      const meta = metadata?.supported_metrics?.find((m) => m.key === key);
                      const unit = meta?.unit || '';

                      return (
                        <div
                          key={key}
                          className="p-4 rounded-xl border border-slate-800/80 bg-midnight-900/40 relative overflow-hidden"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                              {key.replace('_', ' ')}
                            </span>
                            <Gauge className="w-4 h-4 text-cyan-400" />
                          </div>

                          <div className="mt-2 flex items-baseline gap-1.5">
                            <span className="text-2xl font-bold font-mono text-slate-100">
                              {typeof val === 'number' ? val.toFixed(1) : val}
                            </span>
                            <span className="text-xs font-mono text-slate-400">{unit}</span>
                          </div>

                          {range && (
                            <div className="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
                              <span>Min: {range.min.toFixed(1)}</span>
                              <span>Avg: {range.avg.toFixed(1)}</span>
                              <span>Max: {range.max.toFixed(1)}</span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="p-8 rounded-xl border border-dashed border-slate-800 text-center space-y-3">
                    <Activity className="w-8 h-8 text-slate-600 mx-auto" />
                    <p className="text-sm text-slate-300 font-semibold">Zero Readings Received Yet</p>
                    <p className="text-xs text-slate-500 max-w-md mx-auto">
                      In accordance with strict anti-fabrication standards, disconnected devices report zero
                      fabricated telemetry. Click "Trigger Simulator Tick" or transmit via HTTP API.
                    </p>
                  </div>
                )}

                {/* Recent Telemetry Stream Table */}
                <div className="p-4 rounded-xl border border-slate-800/80 bg-midnight-900/40 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                      Recent Ingested Events (Anti-Tamper & Anomaly Verified)
                    </h4>
                    <span className="text-xs text-slate-500 font-mono">{events.length} Events Logged</span>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left text-slate-300">
                      <thead className="bg-slate-900/60 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
                        <tr>
                          <th className="py-2.5 px-3 font-mono">Timestamp</th>
                          <th className="py-2.5 px-3">Metrics Snapshot</th>
                          <th className="py-2.5 px-3">Provenance</th>
                          <th className="py-2.5 px-3">Validation</th>
                          <th className="py-2.5 px-3">Anomalies</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/50">
                        {events.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="py-6 text-center text-slate-500">
                              No telemetry events stored in local database for this node.
                            </td>
                          </tr>
                        ) : (
                          events.map((evt) => (
                            <tr key={evt.event_id} className="hover:bg-slate-900/40 font-mono text-[11px]">
                              <td className="py-2.5 px-3 text-slate-400 whitespace-nowrap">
                                {new Date(evt.device_timestamp).toLocaleTimeString()}
                              </td>
                              <td className="py-2.5 px-3">
                                <div className="flex flex-wrap gap-1.5">
                                  {Object.entries(evt.metrics).map(([mKey, mVal]) => (
                                    <span
                                      key={mKey}
                                      className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700"
                                    >
                                      {mKey}: <strong className="text-cyan-300">{mVal}</strong>
                                    </span>
                                  ))}
                                </div>
                              </td>
                              <td className="py-2.5 px-3">
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                                  {evt.data_provenance}
                                </span>
                              </td>
                              <td className="py-2.5 px-3">
                                {evt.is_valid ? (
                                  <span className="text-emerald-400 flex items-center gap-1">
                                    <CheckCircle2 className="w-3.5 h-3.5" /> Valid
                                  </span>
                                ) : (
                                  <span className="text-rose-400 flex items-center gap-1">
                                    <XCircle className="w-3.5 h-3.5" /> Corrupted
                                  </span>
                                )}
                              </td>
                              <td className="py-2.5 px-3">
                                {evt.anomalies && evt.anomalies.length > 0 ? (
                                  <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                    {evt.anomalies.join(', ')}
                                  </span>
                                ) : (
                                  <span className="text-slate-500">—</span>
                                )}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            ) : (
              <div className="p-8 text-center text-slate-500">No device selected.</div>
            )}
          </div>
        )}

        {/* TAB 3: ALERTS & RULES */}
        {activeTab === 'alerts' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-100">Threshold Rules & Cooldown Alerts</h2>
                <p className="text-xs text-slate-400">
                  Real-time physical bounds monitoring with cooldown window debouncing and auto-resolution.
                </p>
              </div>
              <button
                onClick={() => setShowRuleModal(true)}
                className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-midnight-950 font-bold text-xs shadow-cyan-glow transition"
              >
                <Plus className="w-4 h-4" />
                <span>Create Alert Rule</span>
              </button>
            </div>

            {/* Active & Historical Alerts List */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">Triggered Alerts</h3>
              {alerts.length === 0 ? (
                <div className="p-6 rounded-xl border border-dashed border-slate-800 text-center text-slate-500 text-xs">
                  All systems nominal. No alerts triggered across the fleet.
                </div>
              ) : (
                <div className="space-y-2">
                  {alerts.map((al) => (
                    <div
                      key={al.alert_id}
                      className={`p-3.5 rounded-xl border flex items-center justify-between gap-4 text-xs ${
                        al.status === 'active'
                          ? 'border-rose-500/50 bg-rose-950/20 text-rose-200'
                          : al.status === 'acknowledged'
                          ? 'border-amber-500/50 bg-amber-950/20 text-amber-200'
                          : 'border-slate-800 bg-midnight-900/40 text-slate-400'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <AlertTriangle
                          className={`w-4 h-4 shrink-0 ${
                            al.severity === 'critical' ? 'text-rose-400 animate-pulse' : 'text-amber-400'
                          }`}
                        />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-slate-100">{al.device_name}</span>
                            <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-slate-900 border border-slate-800">
                              {al.metric_key}
                            </span>
                            <span
                              className={`text-[10px] uppercase font-bold px-1.5 py-0.2 rounded ${
                                al.severity === 'critical'
                                  ? 'bg-rose-500/20 text-rose-300'
                                  : 'bg-amber-500/20 text-amber-300'
                              }`}
                            >
                              {al.severity}
                            </span>
                          </div>
                          <p className="text-[11px] mt-0.5">{al.threshold_description}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <div className="text-right text-[11px]">
                          <span className="block font-mono text-slate-300">
                            Reading: <strong>{al.measured_value}</strong>
                          </span>
                          <span className="text-[10px] text-slate-500">
                            {new Date(al.created_at).toLocaleTimeString()}
                          </span>
                        </div>
                        {al.status === 'active' && (
                          <button
                            onClick={() => handleAcknowledgeAlert(al.alert_id)}
                            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-[11px] font-semibold transition"
                          >
                            Acknowledge
                          </button>
                        )}
                        {al.status === 'resolved' && (
                          <span className="text-[11px] text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Resolved
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Configured Rules List */}
            <div className="space-y-3 pt-4 border-t border-slate-800">
              <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">Configured Rules</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {alertRules.map((r) => (
                  <div
                    key={r.rule_id}
                    className="p-3 rounded-lg border border-slate-800 bg-midnight-900/40 text-xs flex items-center justify-between"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-200">{r.metric_key}</span>
                        <span className="font-mono text-cyan-400">
                          {r.operator} {r.threshold_val_primary}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5">{r.description}</p>
                    </div>
                    <span className="text-[10px] text-slate-500 font-mono">
                      Cooldown: {r.cooldown_seconds}s
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: COMMANDS & GATES */}
        {activeTab === 'commands' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-100">Device Commands & Actuation Console</h2>
                <p className="text-xs text-slate-400">
                  Secure downlink dispatch with strict user approval gates for consequential actions (reboots & OTA).
                </p>
              </div>
            </div>

            {/* Command Dispatch Form */}
            <div className="p-5 rounded-xl border border-slate-800 bg-midnight-900/60 max-w-2xl space-y-4">
              <h3 className="text-xs font-bold uppercase text-cyan-400 tracking-wider flex items-center gap-2">
                <Send className="w-4 h-4" /> Dispatch Downlink Command
              </h3>

              <form onSubmit={handleDispatchCommand} className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-400 mb-1">Target Device</label>
                  <input
                    type="text"
                    disabled
                    value={selectedDevice ? `${selectedDevice.name} (${selectedDevice.device_id})` : 'None'}
                    className="w-full bg-slate-900/80 border border-slate-800 rounded-lg px-3 py-2 text-slate-300 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Command Action</label>
                  <select
                    value={cmdType}
                    onChange={(e) => setCmdType(e.target.value as DeviceCommandType)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="reboot">reboot (Consequential — Requires Gate Confirmation)</option>
                    <option value="ota_firmware_update">
                      ota_firmware_update (Consequential — Requires Gate Confirmation)
                    </option>
                    <option value="set_telemetry_interval">set_telemetry_interval (Safe)</option>
                    <option value="set_relay">set_relay (Safe)</option>
                    <option value="calibrate_sensor">calibrate_sensor (Safe)</option>
                    <option value="custom">custom (Arbitrary Downlink)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Parameters (JSON)</label>
                  <textarea
                    rows={4}
                    value={cmdParamsJson}
                    onChange={(e) => setCmdParamsJson(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 font-mono text-cyan-300 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isLoading || !selectedDeviceId}
                  className="px-4 py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-midnight-950 font-bold transition shadow-cyan-glow flex items-center gap-2"
                >
                  <Send className="w-4 h-4" />
                  <span>Send Command to Device</span>
                </button>
              </form>
            </div>

            {/* Command Execution Log */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
                Command Audit History
              </h3>
              <div className="space-y-2">
                {commands.length === 0 ? (
                  <div className="p-6 rounded-xl border border-dashed border-slate-800 text-center text-slate-500 text-xs">
                    No commands dispatched yet.
                  </div>
                ) : (
                  commands.map((cmd) => (
                    <div
                      key={cmd.command_id}
                      className="p-3.5 rounded-xl border border-slate-800 bg-midnight-900/40 text-xs flex items-center justify-between gap-4 font-mono"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-100">{cmd.command_type}</span>
                          <span className="text-[10px] text-slate-400">ID: {cmd.command_id}</span>
                          {cmd.is_consequential && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                              CONSEQUENTIAL
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400 font-sans mt-0.5">{cmd.result_message}</p>
                      </div>

                      <div className="flex items-center gap-3">
                        <span
                          className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                            cmd.dispatch_status === 'acknowledged' || cmd.dispatch_status === 'dispatched'
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : cmd.confirmation_status === 'pending_confirmation'
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              : 'bg-slate-800 text-slate-300'
                          }`}
                        >
                          {cmd.confirmation_status === 'pending_confirmation' ? 'PENDING GATE' : cmd.dispatch_status}
                        </span>
                        {cmd.confirmation_status === 'pending_confirmation' && (
                          <button
                            onClick={() => setConfirmModalCmd(cmd)}
                            className="px-2.5 py-1 rounded bg-amber-500 hover:bg-amber-400 text-midnight-950 font-bold text-[11px] transition"
                          >
                            Review Gate
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: SIMULATOR & EXPORT */}
        {activeTab === 'export' && (
          <div className="space-y-6 max-w-3xl">
            <div>
              <h2 className="text-base font-bold text-slate-100">Deterministic Simulator & Dataset Export</h2>
              <p className="text-xs text-slate-400">
                Generate reproducible sensor dynamics, inject anomaly stresses, and export verified timeseries data.
              </p>
            </div>

            {/* Simulator Controls */}
            <div className="p-5 rounded-xl border border-slate-800 bg-midnight-900/60 space-y-4">
              <h3 className="text-xs font-bold uppercase text-cyan-400 tracking-wider flex items-center gap-2">
                <Zap className="w-4 h-4" /> Telemetry Simulator Controls
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="block text-slate-400 mb-1">Batch Tick Count</label>
                  <select
                    value={simTickCount}
                    onChange={(e) => setSimTickCount(Number(e.target.value))}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-200"
                  >
                    <option value={1}>1 Tick (Single step)</option>
                    <option value={5}>5 Ticks (Burst)</option>
                    <option value={20}>20 Ticks (Streaming wave)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Inject Physical Anomaly</label>
                  <select
                    value={simAnomaly}
                    onChange={(e) => setSimAnomaly(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-200"
                  >
                    <option value="none">None (Nominal range)</option>
                    <option value="spike_temperature">Temperature Thermal Surge (&gt;90°C)</option>
                    <option value="high_vibration">Bearing Vibration Overload (&gt;15mm/s)</option>
                    <option value="low_voltage">Brownout Voltage Drop (&lt;3.0V)</option>
                    <option value="pressure_drop">Barometric Depressurization (&lt;850hPa)</option>
                  </select>
                </div>
              </div>

              <button
                onClick={handleSimulateTick}
                disabled={isLoading || !selectedDeviceId}
                className="px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-midnight-950 font-bold text-xs transition shadow-cyan-glow flex items-center gap-2"
              >
                <Zap className="w-4 h-4" />
                <span>Inject Simulator Ticks</span>
              </button>
            </div>

            {/* Export Controls */}
            <div className="p-5 rounded-xl border border-slate-800 bg-midnight-900/60 space-y-4">
              <h3 className="text-xs font-bold uppercase text-cyan-400 tracking-wider flex items-center gap-2">
                <Download className="w-4 h-4" /> Export Verified Timeseries Dataset
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="block text-slate-400 mb-1">Format</label>
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 text-slate-300">
                      <input
                        type="radio"
                        name="exportFormat"
                        checked={exportFormat === 'csv'}
                        onChange={() => setExportFormat('csv')}
                      />
                      CSV Format (Tabular)
                    </label>
                    <label className="flex items-center gap-2 text-slate-300">
                      <input
                        type="radio"
                        name="exportFormat"
                        checked={exportFormat === 'json'}
                        onChange={() => setExportFormat('json')}
                      />
                      JSON Array
                    </label>
                  </div>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Time Horizon</label>
                  <select
                    value={exportTimeRange}
                    onChange={(e) => setExportTimeRange(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-200"
                  >
                    <option value="1h">Last 1 Hour</option>
                    <option value="24h">Last 24 Hours</option>
                    <option value="7d">Last 7 Days</option>
                    <option value="all">Entire Retention History</option>
                  </select>
                </div>
              </div>

              <button
                onClick={handleExport}
                disabled={isLoading || !selectedDeviceId}
                className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-midnight-950 font-bold text-xs transition shadow-emerald-glow flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                <span>Export Dataset File</span>
              </button>

              {latestExport && (
                <div className="p-4 rounded-lg bg-slate-900/80 border border-slate-800 space-y-2 text-xs">
                  <div className="flex items-center justify-between text-slate-300">
                    <span>Export ID: <code className="text-cyan-300">{latestExport.export_id}</code></span>
                    <span>Total Events: <strong>{latestExport.total_events_exported}</strong></span>
                  </div>
                  <pre className="p-2.5 rounded bg-midnight-950 border border-slate-800 text-[11px] font-mono text-slate-400 overflow-x-auto max-h-40">
                    {latestExport.content_preview}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* MODAL 1: REGISTER DEVICE */}
      {showRegModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-midnight-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-midnight-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-100">Register IoT Node</h3>
              <button onClick={() => setShowRegModal(false)} className="text-slate-400 hover:text-slate-200">
                &times;
              </button>
            </div>

            <form onSubmit={handleRegisterDevice} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Device Friendly Name</label>
                <input
                  type="text"
                  required
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Target Hardware Profile</label>
                <select
                  value={regBoardId}
                  onChange={(e) => setRegBoardId(e.target.value as IoTBoardId)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-200"
                >
                  <option value="esp32_devkit_v1">ESP32 DevKit V1 (Wi-Fi / BLE)</option>
                  <option value="raspberry_pi_pico_w">Raspberry Pi Pico W (RP2040)</option>
                  <option value="arduino_uno_r3">Arduino Uno R3 (ATmega328P)</option>
                  <option value="stm32_nucleo_f401re">STM32 Nucleo-F401RE (ARM Cortex-M4)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Ingestion Protocol</label>
                <select
                  value={regProtocol}
                  onChange={(e) => setRegProtocol(e.target.value as IoTIngestionProtocol)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-200"
                >
                  <option value="http">HTTP Authenticated Ingestion (REST)</option>
                  <option value="mqtt">MQTT over TLS (Topic Broker)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Firmware Version</label>
                <input
                  type="text"
                  value={regFirmwareVersion}
                  onChange={(e) => setRegFirmwareVersion(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="regSim"
                  checked={regSimulated}
                  onChange={(e) => setRegSimulated(e.target.checked)}
                />
                <label htmlFor="regSim" className="text-slate-300">
                  Enable Software Simulator (Permits virtual tick generation)
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowRegModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-4 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-midnight-950 font-bold"
                >
                  Provision Node
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: ONE-TIME TOKEN REVEAL */}
      {tokenReveal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-midnight-950/80 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-midnight-900 border border-cyan-500/50 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-2 text-cyan-400">
              <Key className="w-5 h-5" />
              <h3 className="text-sm font-bold text-slate-100">Device Security Credential Generated</h3>
            </div>

            <p className="text-xs text-amber-300 bg-amber-500/10 p-3 rounded-lg border border-amber-500/30">
              <strong>Security Policy Notice:</strong> {tokenReveal.security_notice}
            </p>

            <div className="space-y-2 text-xs">
              <label className="text-slate-400">Plaintext Secret Ingestion Token:</label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={tokenReveal.plaintext_token}
                  className="w-full bg-midnight-950 border border-slate-700 rounded-lg p-2.5 font-mono text-cyan-300 select-all"
                />
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(tokenReveal.plaintext_token);
                    setCopiedToken(true);
                    setTimeout(() => setCopiedToken(false), 2000);
                  }}
                  className="px-3 py-2.5 rounded-lg bg-cyan-500 text-midnight-950 font-bold flex items-center gap-1 shrink-0"
                >
                  {copiedToken ? <CheckCircle2 className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  <span>{copiedToken ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-[11px] space-y-1 font-mono text-slate-300">
              <div>HTTP Endpoint: <span className="text-slate-400">{tokenReveal.ingestion_url}</span></div>
              <div>MQTT Topic: <span className="text-slate-400">{tokenReveal.mqtt_topic}</span></div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setTokenReveal(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-100 font-semibold text-xs"
              >
                I have securely saved this token
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: CONSEQUENTIAL COMMAND APPROVAL GATE */}
      {confirmModalCmd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-midnight-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-midnight-900 border border-rose-500/50 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-2 text-rose-400">
              <ShieldAlert className="w-5 h-5" />
              <h3 className="text-sm font-bold text-slate-100">Consequential Action Confirmation Gate</h3>
            </div>

            <p className="text-xs text-slate-300">
              Command <strong>{confirmModalCmd.command_type}</strong> requires explicit human confirmation.
              This operation can disrupt live physical operations on node{' '}
              <code className="text-cyan-300">{confirmModalCmd.device_id}</code>.
            </p>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => handleConfirmCommand(false)}
                className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
              >
                Reject Command
              </button>
              <button
                onClick={() => handleConfirmCommand(true)}
                className="px-4 py-2 rounded-lg bg-rose-500 hover:bg-rose-400 text-white font-bold text-xs"
              >
                Authorize Execution
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 4: CREATE ALERT RULE */}
      {showRuleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-midnight-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-midnight-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-100">Configure Threshold Rule</h3>
              <button onClick={() => setShowRuleModal(false)} className="text-slate-400 hover:text-slate-200">
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateRule} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Target Metric</label>
                <select
                  value={ruleMetric}
                  onChange={(e) => setRuleMetric(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-200"
                >
                  <option value="temperature">temperature (°C)</option>
                  <option value="humidity">humidity (%)</option>
                  <option value="vibration">vibration (mm/s)</option>
                  <option value="voltage">voltage (V)</option>
                  <option value="current">current (A)</option>
                  <option value="distance">distance (cm)</option>
                  <option value="pressure">pressure (hPa)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Operator</label>
                  <select
                    value={ruleOperator}
                    onChange={(e) => setRuleOperator(e.target.value as AlertOperator)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-200"
                  >
                    <option value="gt">&gt; Greater than</option>
                    <option value="gte">&gt;= Greater/Equal</option>
                    <option value="lt">&lt; Less than</option>
                    <option value="lte">&lt;= Less/Equal</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Threshold Value</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={ruleThreshold}
                    onChange={(e) => setRuleThreshold(Number(e.target.value))}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Severity</label>
                  <select
                    value={ruleSeverity}
                    onChange={(e) => setRuleSeverity(e.target.value as AlertSeverity)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-200"
                  >
                    <option value="info">Info</option>
                    <option value="warning">Warning</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Cooldown (Seconds)</label>
                  <input
                    type="number"
                    required
                    value={ruleCooldown}
                    onChange={(e) => setRuleCooldown(Number(e.target.value))}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Rule Description</label>
                <input
                  type="text"
                  required
                  value={ruleDescription}
                  onChange={(e) => setRuleDescription(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowRuleModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-4 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-midnight-950 font-bold"
                >
                  Arm Alert Rule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
