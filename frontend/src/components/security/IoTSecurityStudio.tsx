import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Lock,
  Unlock,
  Radio,
  Cpu,
  RefreshCw,
  Search,
  FileCode,
  Terminal,
  Server,
  Zap,
  Activity,
  CheckCircle2,
  XCircle,
  Eye,
  Sliders,
  ChevronRight,
  Send,
  AlertCircle,
  HardDrive,
  Network,
  Fingerprint,
} from 'lucide-react';
import { api } from '../../services/api';
import {
  DeviceSecurityPosture,
  ConfigurationAuditFinding,
  BehavioralAnomalyRecord,
  SecurityIncidentRecord,
  DefensiveActionRecord,
  FirmwareIntegritySpec,
  IoTSecurityOverviewResponse,
  SecurityRiskLevel,
  ConfigAuditSeverity,
  DefensiveActionType,
  IncidentStatus,
} from '../../types';

export const IoTSecurityStudio: React.FC = () => {
  // Navigation & Sub-tabs
  const [activeTab, setActiveTab] = useState<'posture' | 'audit' | 'anomalies' | 'incidents' | 'firmware'>('posture');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Core Data State
  const [overview, setOverview] = useState<IoTSecurityOverviewResponse | null>(null);
  const [postures, setPostures] = useState<DeviceSecurityPosture[]>([]);
  const [findings, setFindings] = useState<ConfigurationAuditFinding[]>([]);
  const [anomalies, setAnomalies] = useState<BehavioralAnomalyRecord[]>([]);
  const [incidents, setIncidents] = useState<SecurityIncidentRecord[]>([]);
  const [firmwareMatrix, setFirmwareMatrix] = useState<FirmwareIntegritySpec[]>([]);
  const [defensiveActions, setDefensiveActions] = useState<DefensiveActionRecord[]>([]);

  // Selection & Filters
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
  const [selectedIncident, setSelectedIncident] = useState<SecurityIncidentRecord | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date>(new Date());

  // Configuration Audit Drawer State
  const [auditConfigText, setAuditConfigText] = useState<string>(
    '# Device Configuration Manifest\nWIFI_SSID = "IoT_Production_Mesh"\nWIFI_PASS = "FactorySecret2026!"\nMQTT_BROKER = "192.168.1.10"\nMQTT_PORT = 1883\nMQTT_TOPIC = "nodes/#"\nAPI_KEY = "sk-live-prod-secret9988"\n'
  );
  const [auditFilename, setAuditFilename] = useState<string>('platformio.ini');

  // Defensive Action Gating Modal State
  const [showActionModal, setShowActionModal] = useState<boolean>(false);
  const [targetActionType, setTargetActionType] = useState<DefensiveActionType>('quarantine_device');
  const [actionReason, setActionReason] = useState<string>('Suspected telemetry spoofing and sequence counter anomalies');
  const [confirmPendingAction, setConfirmPendingAction] = useState<DefensiveActionRecord | null>(null);

  // 1. Initial Load: Full Security Overview & Subsystems
  const loadSecurityData = useCallback(async () => {
    try {
      setIsLoading(true);
      setErrorMsg(null);
      const [overviewRes, fwSpecs, actions] = await Promise.all([
        api.getIoTSecurityOverview(),
        api.getFirmwareIntegrityMatrix(),
        api.listDefensiveActions(),
      ]);

      setOverview(overviewRes || null);
      setPostures(overviewRes?.devices_posture || []);
      setFindings(overviewRes?.config_findings || []);
      setAnomalies(overviewRes?.recent_anomalies || []);
      setIncidents(overviewRes?.active_incidents || []);
      setFirmwareMatrix(fwSpecs || []);
      setDefensiveActions(actions || []);

      if (!selectedDeviceId && overviewRes?.devices_posture && overviewRes.devices_posture.length > 0) {
        setSelectedDeviceId(overviewRes.devices_posture[0].device_id);
      }
      setLastRefreshedAt(new Date());
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load IoT security overview');
    } finally {
      setIsLoading(false);
    }
  }, [selectedDeviceId]);

  useEffect(() => {
    loadSecurityData();
  }, [loadSecurityData]);

  // Periodic Auto-refresh (15s)
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      loadSecurityData();
    }, 15000);
    return () => clearInterval(interval);
  }, [autoRefresh, loadSecurityData]);

  // Handle Manual Configuration Audit
  const handleRunConfigAudit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsLoading(true);
      setErrorMsg(null);
      const newFindings = await api.auditIoTConfiguration({
        device_id: selectedDeviceId || undefined,
        config_file_text: auditConfigText,
        filename: auditFilename,
      });
      setSuccessMsg(`Configuration audit complete: ${newFindings.length} finding(s) detected.`);
      loadSecurityData();
      setActiveTab('audit');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to execute configuration audit');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Behavioral Scan on Active Device
  const handleScanBehavior = async (devId: string) => {
    if (!devId) return;
    try {
      setIsLoading(true);
      const detected = await api.analyzeDeviceBehavior(devId);
      setSuccessMsg(`Behavioral analysis complete: ${detected.length} anomaly indicator(s) identified.`);
      loadSecurityData();
      setActiveTab('anomalies');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to analyze device behavior');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Defensive Action Request & Gating
  const handleRequestDefensiveAction = async (confirmed: boolean = false) => {
    if (!selectedDeviceId) return;
    try {
      setIsLoading(true);
      setErrorMsg(null);
      const res = await api.executeDefensiveAction({
        device_id: selectedDeviceId,
        action_type: targetActionType,
        reason: actionReason,
        confirmed,
      });

      if (res.status === 'pending_confirmation') {
        setConfirmPendingAction(res);
      } else {
        setConfirmPendingAction(null);
        setShowActionModal(false);
        setSuccessMsg(`Defensive action '${res.action_type}' ${res.status}: ${res.result_message}`);
        loadSecurityData();
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Defensive action execution failed');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Incident Status Update
  const handleUpdateIncidentStatus = async (incidentId: string, newStatus: IncidentStatus) => {
    try {
      setIsLoading(true);
      await api.updateSecurityIncidentStatus(incidentId, newStatus, 'Status updated via Threat Detection Dashboard');
      setSuccessMsg(`Incident updated to ${newStatus}`);
      loadSecurityData();
      if (selectedIncident && selectedIncident.incident_id === incidentId) {
        const refreshed = await api.getSecurityIncident(incidentId);
        setSelectedIncident(refreshed);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update incident status');
    } finally {
      setIsLoading(false);
    }
  };

  // Filtered Findings
  const filteredFindings = useMemo(() => {
    if (severityFilter === 'all') return findings;
    return findings.filter((f) => f.severity === severityFilter);
  }, [findings, severityFilter]);

  const selectedDevice = useMemo(
    () => postures.find((p) => p.device_id === selectedDeviceId),
    [postures, selectedDeviceId]
  );

  return (
    <div className="flex flex-col h-full bg-midnight-950 text-slate-100 overflow-hidden">
      {/* Top Header / Threat Posture Banner */}
      <div className="px-6 py-4 border-b border-slate-800/80 bg-midnight-900/60 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400">
            <ShieldAlert className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-100 tracking-wide">
                IoT Security & Device Threat Detection
              </h1>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-300 border border-rose-500/30">
                STAGE 26
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Defensive security posture, configuration auditing, behavioral anomaly detection & gated response actions.
            </p>
          </div>
        </div>

        {/* Global Fleet Security Risk Indicators */}
        <div className="flex items-center gap-2 text-xs">
          <div className="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center gap-2">
            <Shield className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-400">Avg Risk:</span>
            <span
              className={`font-mono font-bold ${
                (overview?.fleet_posture_summary?.average_fleet_risk_score ?? 0) >= 60
                  ? 'text-rose-400'
                  : (overview?.fleet_posture_summary?.average_fleet_risk_score ?? 0) >= 30
                  ? 'text-amber-400'
                  : 'text-emerald-400'
              }`}
            >
              {overview?.fleet_posture_summary?.average_fleet_risk_score ?? 0}/100
            </span>
          </div>

          <div className="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-slate-400">Findings:</span>
            <span className="font-semibold text-amber-400">{findings.length}</span>
          </div>

          <div className="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-rose-400" />
            <span className="text-slate-400">Anomalies:</span>
            <span className="font-semibold text-rose-400">{anomalies.length}</span>
          </div>

          <div className="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center gap-2">
            <AlertCircle className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-slate-400">Incidents:</span>
            <span className="font-semibold text-purple-300">
              {incidents.filter((i) => i.status === 'new' || i.status === 'under_investigation').length}
            </span>
          </div>

          <button
            onClick={() => loadSecurityData()}
            disabled={isLoading}
            className="p-2 rounded-lg bg-slate-800/60 hover:bg-slate-700/60 text-slate-300 border border-slate-700 transition"
            title="Refresh Security Status"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Notifications Bar */}
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
            onClick={() => setActiveTab('posture')}
            className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition ${
              activeTab === 'posture'
                ? 'border-rose-400 text-rose-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Shield className="w-4 h-4" />
            <span>Device Posture</span>
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition ${
              activeTab === 'audit'
                ? 'border-rose-400 text-rose-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileCode className="w-4 h-4" />
            <span>Configuration Audit</span>
            {findings.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/40">
                {findings.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('anomalies')}
            className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition ${
              activeTab === 'anomalies'
                ? 'border-rose-400 text-rose-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Behavioral Anomalies</span>
            {anomalies.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-rose-500/20 text-rose-300 border border-rose-500/40">
                {anomalies.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('incidents')}
            className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition ${
              activeTab === 'incidents'
                ? 'border-rose-400 text-rose-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <AlertCircle className="w-4 h-4" />
            <span>Incidents & Investigation</span>
            {incidents.filter((i) => i.status === 'new').length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/40 animate-pulse">
                {incidents.filter((i) => i.status === 'new').length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('firmware')}
            className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition ${
              activeTab === 'firmware'
                ? 'border-rose-400 text-rose-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Fingerprint className="w-4 h-4" />
            <span>Firmware Integrity & Defensive Controls</span>
          </button>
        </div>

        {/* Device selector quick dropdown */}
        <div className="flex items-center gap-3">
          <label className="text-xs text-slate-400 hidden sm:inline">Target Node:</label>
          <select
            value={selectedDeviceId}
            onChange={(e) => setSelectedDeviceId(e.target.value)}
            className="text-xs bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-rose-500"
          >
            {postures.map((p) => (
              <option key={p.device_id} value={p.device_id}>
                {p.device_name} ({p.risk_level.toUpperCase()} - {p.risk_score}/100)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* TAB 1: DEVICE SECURITY POSTURE */}
        {activeTab === 'posture' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-100">Fleet Security Posture & Inventory</h2>
                <p className="text-xs text-slate-400">
                  Granular security properties, transport encryption verification, and hardware root-of-trust matrix.
                </p>
              </div>
              <button
                onClick={() => {
                  if (selectedDeviceId) handleScanBehavior(selectedDeviceId);
                }}
                className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-rose-500 hover:bg-rose-400 text-midnight-950 font-bold text-xs shadow-rose-glow transition"
              >
                <Activity className="w-4 h-4" />
                <span>Scan Active Node Behavior</span>
              </button>
            </div>

            {/* Posture Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {postures.map((p) => (
                <div
                  key={p.device_id}
                  onClick={() => setSelectedDeviceId(p.device_id)}
                  className={`p-4 rounded-xl border transition cursor-pointer ${
                    p.device_id === selectedDeviceId
                      ? 'border-rose-500 bg-rose-950/20 shadow-rose-glow/20'
                      : 'border-slate-800 bg-midnight-900/60 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-slate-100">{p.device_name}</span>
                        {p.is_simulated && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                            SIMULATED
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] font-mono text-slate-400 mt-0.5">{p.device_id}</p>
                    </div>

                    <div className="text-right">
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                          p.risk_level === 'critical'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                            : p.risk_level === 'high'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            : p.risk_level === 'medium'
                            ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/40'
                            : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                        }`}
                      >
                        Risk: {p.risk_score}/100
                      </span>
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800/80">
                      <span className="text-[10px] text-slate-500 block uppercase">Transport Encryption</span>
                      <span
                        className={`font-semibold text-[11px] flex items-center gap-1 ${
                          p.transport_encryption === 'tls_enabled'
                            ? 'text-emerald-400'
                            : p.transport_encryption === 'plaintext_unencrypted'
                            ? 'text-rose-400'
                            : 'text-slate-400'
                        }`}
                      >
                        {p.transport_encryption === 'tls_enabled' ? (
                          <Lock className="w-3 h-3" />
                        ) : (
                          <Unlock className="w-3 h-3" />
                        )}
                        {p.transport_encryption === 'tls_enabled' ? 'TLS 1.3 / MQTTS' : 'Plaintext HTTP'}
                      </span>
                    </div>

                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800/80">
                      <span className="text-[10px] text-slate-500 block uppercase">Authentication</span>
                      <span className="font-mono text-slate-200 truncate block">{p.authentication_status}</span>
                    </div>

                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800/80">
                      <span className="text-[10px] text-slate-500 block uppercase">Secure Boot</span>
                      <span
                        className={`font-semibold text-[11px] ${
                          p.supports_secure_boot ? 'text-emerald-400' : 'text-slate-500'
                        }`}
                      >
                        {p.supports_secure_boot ? 'Supported (HW RoT)' : 'Unsupported'}
                      </span>
                    </div>

                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800/80">
                      <span className="text-[10px] text-slate-500 block uppercase">Update Status</span>
                      <span className="font-semibold text-slate-300 block">{p.update_status}</span>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-500 text-[11px]">Findings:</span>
                      <span className="font-bold text-amber-400">{p.active_findings_count}</span>
                      <span className="text-slate-500 text-[11px] ml-2">Anomalies:</span>
                      <span className="font-bold text-rose-400">{p.active_threats_count}</span>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedDeviceId(p.device_id);
                        setShowActionModal(true);
                      }}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-[11px] font-semibold transition"
                    >
                      Contain Node
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 2: CONFIGURATION AUDIT */}
        {activeTab === 'audit' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-100">Rule-Based Configuration Auditing</h2>
                <p className="text-xs text-slate-400">
                  Scans firmware manifests, platform configurations, and network settings for plaintext transport and exposed secrets.
                </p>
              </div>

              {/* Severity Filter */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-400">Severity:</span>
                {['all', 'critical', 'high', 'medium', 'low'].map((sev) => (
                  <button
                    key={sev}
                    onClick={() => setSeverityFilter(sev)}
                    className={`px-2.5 py-1 rounded-lg uppercase text-[10px] font-bold transition ${
                      severityFilter === sev
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                        : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200'
                    }`}
                  >
                    {sev}
                  </button>
                ))}
              </div>
            </div>

            {/* Config Auditor Input Drawer */}
            <div className="p-4 rounded-xl border border-slate-800 bg-midnight-900/60 space-y-3">
              <h3 className="text-xs font-bold uppercase text-slate-300 flex items-center gap-2">
                <FileCode className="w-4 h-4 text-cyan-400" /> Audit Configuration File or Manifest
              </h3>
              <form onSubmit={handleRunConfigAudit} className="space-y-3 text-xs">
                <div className="flex items-center gap-3">
                  <input
                    type="text"
                    value={auditFilename}
                    onChange={(e) => setAuditFilename(e.target.value)}
                    placeholder="Filename (e.g. platformio.ini, secrets.h, mosquitto.conf)"
                    className="w-72 bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-200 font-mono text-xs"
                  />
                  <span className="text-slate-500">Target Node: {selectedDevice?.device_name || 'Global'}</span>
                </div>

                <textarea
                  rows={4}
                  value={auditConfigText}
                  onChange={(e) => setAuditConfigText(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 font-mono text-[11px] text-cyan-300 focus:outline-none focus:border-rose-500"
                />

                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-4 py-2 rounded-lg bg-rose-500 hover:bg-rose-400 text-midnight-950 font-bold transition shadow-rose-glow flex items-center gap-2"
                >
                  <Search className="w-4 h-4" />
                  <span>Execute Configuration Audit</span>
                </button>
              </form>
            </div>

            {/* Findings List */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
                Active Audit Findings ({filteredFindings.length})
              </h3>

              {filteredFindings.length === 0 ? (
                <div className="p-8 rounded-xl border border-dashed border-slate-800 text-center space-y-2">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                  <p className="text-sm text-slate-200 font-semibold">Zero Active Findings in this Category</p>
                  <p className="text-xs text-slate-500">Configuration files comply with security baseline rules.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredFindings.map((f) => (
                    <div
                      key={f.finding_id}
                      className="p-4 rounded-xl border border-slate-800 bg-midnight-900/40 space-y-2 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                              f.severity === 'critical'
                                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                                : f.severity === 'high'
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                                : 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/40'
                            }`}
                          >
                            {f.severity}
                          </span>
                          <span className="font-bold text-slate-200">{f.title}</span>
                          <span className="font-mono text-[10px] text-slate-400">({f.rule_id})</span>
                        </div>
                        <span className="text-slate-500 text-[11px]">{new Date(f.detected_at).toLocaleTimeString()}</span>
                      </div>

                      <div className="p-2.5 rounded bg-midnight-950 border border-slate-800/80 font-mono text-[11px] text-rose-300">
                        <span className="text-slate-500 block text-[10px] uppercase">Evidence (Redacted):</span>
                        {f.evidence}
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                        <div className="p-2 rounded bg-slate-900/60 border border-slate-800/60">
                          <strong className="text-slate-400 block mb-0.5">Potential Impact:</strong>
                          <span className="text-slate-300">{f.impact}</span>
                        </div>
                        <div className="p-2 rounded bg-slate-900/60 border border-slate-800/60">
                          <strong className="text-cyan-400 block mb-0.5">Recommended Remediation:</strong>
                          <span className="text-slate-300">{f.remediation}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: BEHAVIORAL ANOMALIES */}
        {activeTab === 'anomalies' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-100">Behavioral Anomaly Detection</h2>
                <p className="text-xs text-slate-400">
                  Statistical baseline evaluation, rate-limit velocity bursts, unexpected crashloops, and auth attack detection.
                </p>
              </div>

              {selectedDeviceId && (
                <button
                  onClick={() => handleScanBehavior(selectedDeviceId)}
                  disabled={isLoading}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-rose-600/30 hover:bg-rose-600/50 text-rose-200 border border-rose-500/40 text-xs font-semibold transition"
                >
                  <Activity className="w-3.5 h-3.5 text-rose-400" />
                  <span>Analyze Selected Node</span>
                </button>
              )}
            </div>

            {/* Anomalies List */}
            <div className="space-y-3">
              {anomalies.length === 0 ? (
                <div className="p-8 rounded-xl border border-dashed border-slate-800 text-center space-y-2">
                  <Activity className="w-8 h-8 text-slate-600 mx-auto" />
                  <p className="text-sm text-slate-200 font-semibold">Zero Behavioral Anomalies Recorded</p>
                  <p className="text-xs text-slate-500">
                    Telemetry arrival rates and sensor ranges comply with moving baseline tolerances.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {anomalies.map((a) => (
                    <div
                      key={a.anomaly_id}
                      className="p-4 rounded-xl border border-slate-800 bg-midnight-900/40 space-y-2 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                              a.severity === 'critical'
                                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                                : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            }`}
                          >
                            {a.severity}
                          </span>
                          <span className="font-bold text-slate-200">{a.anomaly_type.replace('_', ' ')}</span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">
                            {a.classification}
                          </span>
                          <span className="text-[10px] text-cyan-400 font-semibold">
                            Confidence: {a.confidence.toUpperCase()}
                          </span>
                        </div>
                        <span className="text-slate-500 text-[11px]">{new Date(a.detected_at).toLocaleTimeString()}</span>
                      </div>

                      <p className="text-[11px] text-slate-300">{a.evidence_summary}</p>

                      <div className="p-2.5 rounded bg-midnight-950 border border-slate-800 text-[11px] font-mono grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-slate-500 block text-[10px] uppercase">Observed Signal:</span>
                          <span className="text-rose-300">{JSON.stringify(a.observed_value)}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block text-[10px] uppercase">Expected Moving Baseline:</span>
                          <span className="text-emerald-300">{JSON.stringify(a.baseline_expected)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: INCIDENTS & INVESTIGATION */}
        {activeTab === 'incidents' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-100">Security Incidents & Investigation</h2>
                <p className="text-xs text-slate-400">
                  Correlated threat events linking telemetry anomalies, credential attacks, and firmware state.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Incident List */}
              <div className="lg:col-span-1 space-y-3">
                <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
                  Tracked Incidents ({incidents.length})
                </h3>

                {incidents.length === 0 ? (
                  <div className="p-6 rounded-xl border border-dashed border-slate-800 text-center text-xs text-slate-500">
                    No open security incidents.
                  </div>
                ) : (
                  incidents.map((inc) => (
                    <div
                      key={inc.incident_id}
                      onClick={() => setSelectedIncident(inc)}
                      className={`p-3.5 rounded-xl border transition cursor-pointer text-xs space-y-2 ${
                        selectedIncident?.incident_id === inc.incident_id
                          ? 'border-rose-500 bg-rose-950/20'
                          : 'border-slate-800 bg-midnight-900/60 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span
                          className={`text-[10px] font-bold uppercase px-1.5 py-0.2 rounded ${
                            inc.severity === 'critical'
                              ? 'bg-rose-500/20 text-rose-300'
                              : 'bg-amber-500/20 text-amber-300'
                          }`}
                        >
                          {inc.severity}
                        </span>
                        <span className="text-[10px] uppercase font-bold text-slate-400">{inc.status}</span>
                      </div>
                      <h4 className="font-semibold text-slate-200">{inc.title}</h4>
                      <p className="text-[11px] text-slate-400 line-clamp-2">{inc.root_cause_hypothesis}</p>
                      <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500">
                        <span>{inc.affected_devices_count} affected node(s)</span>
                        <span>{new Date(inc.created_at).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Incident Detail Drawer */}
              <div className="lg:col-span-2">
                {selectedIncident ? (
                  <div className="p-5 rounded-xl border border-slate-800 bg-midnight-900/60 space-y-4 text-xs">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                              selectedIncident.severity === 'critical'
                                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                                : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            }`}
                          >
                            {selectedIncident.severity}
                          </span>
                          <h3 className="font-bold text-sm text-slate-100">{selectedIncident.title}</h3>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">
                          Classification: <strong className="text-cyan-300">{selectedIncident.classification}</strong>{' '}
                          &bull; Confidence:{' '}
                          <strong className="text-amber-300">{selectedIncident.confidence_level.toUpperCase()}</strong>
                        </p>
                      </div>

                      {/* Status Update Controls */}
                      <div className="flex items-center gap-2">
                        {['under_investigation', 'mitigated', 'closed'].map((st) => (
                          <button
                            key={st}
                            onClick={() => handleUpdateIncidentStatus(selectedIncident.incident_id, st as IncidentStatus)}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-semibold uppercase border border-slate-700"
                          >
                            Mark {st.replace('_', ' ')}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="p-3 rounded-lg bg-midnight-950 border border-slate-800 space-y-1">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Root Cause Hypothesis:</span>
                      <p className="text-slate-200 text-xs">{selectedIncident.root_cause_hypothesis}</p>
                    </div>

                    {/* Telemetry Correlations */}
                    <div className="space-y-2">
                      <h4 className="text-[11px] uppercase font-bold text-slate-400">Affected Node Correlations</h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {selectedIncident.telemetry_correlations.map((tc, idx) => (
                          <div key={idx} className="p-2 rounded bg-slate-900 border border-slate-800 text-[11px]">
                            <span className="font-semibold text-slate-200">{tc.device_name}</span>
                            <div className="text-[10px] text-slate-400 mt-0.5">
                              Status: <strong className="text-cyan-300">{tc.status}</strong> &bull; Firmware:{' '}
                              {tc.firmware_version}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Recommended Remediations */}
                    <div className="space-y-2">
                      <h4 className="text-[11px] uppercase font-bold text-slate-400">Recommended Next Steps</h4>
                      <ul className="space-y-1 list-disc list-inside text-slate-300 text-[11px]">
                        {selectedIncident.recommended_remediations.map((rem, idx) => (
                          <li key={idx}>{rem}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ) : (
                  <div className="p-8 rounded-xl border border-dashed border-slate-800 text-center text-slate-500 text-xs">
                    Select an incident from the left to view evidence correlation and recommended next steps.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: FIRMWARE INTEGRITY & DEFENSIVE CONTROLS */}
        {activeTab === 'firmware' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-base font-bold text-slate-100">Firmware Integrity & Defensive Controls</h2>
              <p className="text-xs text-slate-400">
                Verified hardware bootloader capabilities, honest checksum boundaries, and gated defensive actuation.
              </p>
            </div>

            {/* Defensive Action Trigger Form */}
            <div className="p-5 rounded-xl border border-slate-800 bg-midnight-900/60 max-w-2xl space-y-4">
              <h3 className="text-xs font-bold uppercase text-rose-400 tracking-wider flex items-center gap-2">
                <ShieldAlert className="w-4 h-4" /> Execute Gated Defensive Response
              </h3>

              <div className="space-y-3 text-xs">
                <div>
                  <label className="block text-slate-400 mb-1">Target Device</label>
                  <input
                    type="text"
                    disabled
                    value={selectedDevice ? `${selectedDevice.device_name} (${selectedDevice.device_id})` : 'None'}
                    className="w-full bg-slate-900/80 border border-slate-800 rounded-lg p-2 text-slate-300 font-mono text-xs"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Defensive Action Type</label>
                  <select
                    value={targetActionType}
                    onChange={(e) => setTargetActionType(e.target.value as DefensiveActionType)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-200"
                  >
                    <option value="quarantine_device">quarantine_device (Disruptive — Requires User Gate)</option>
                    <option value="revoke_credential">revoke_credential (Disruptive — Requires User Gate)</option>
                    <option value="isolate_network">isolate_network (Disruptive — Network SDN Adapter)</option>
                    <option value="throttle_telemetry">throttle_telemetry (Rate limit to 1 event/min)</option>
                    <option value="restore_device">restore_device (Reinstate normal operation)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Audit Justification Reason</label>
                  <input
                    type="text"
                    value={actionReason}
                    onChange={(e) => setActionReason(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
                  />
                </div>

                <button
                  onClick={() => handleRequestDefensiveAction(false)}
                  disabled={isLoading || !selectedDeviceId}
                  className="px-4 py-2.5 rounded-lg bg-rose-500 hover:bg-rose-400 text-midnight-950 font-bold transition shadow-rose-glow flex items-center gap-2"
                >
                  <ShieldAlert className="w-4 h-4" />
                  <span>Dispatch Defensive Action</span>
                </button>
              </div>
            </div>

            {/* Hardware Bootloader Security Matrix */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
                Hardware Bootloader & Firmware Integrity Matrix
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {firmwareMatrix.map((spec) => (
                  <div
                    key={spec.board_id}
                    className="p-4 rounded-xl border border-slate-800 bg-midnight-900/40 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-200">{spec.board_name}</span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                          spec.supports_secure_boot
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {spec.supports_secure_boot ? 'Secure Boot Ready' : 'No HW Secure Boot'}
                      </span>
                    </div>

                    <div className="text-[11px] text-slate-400 space-y-1">
                      <div>
                        <strong>Mechanism:</strong> {spec.secure_boot_version}
                      </div>
                      <div>
                        <strong>Keys:</strong> {spec.crypto_keys_supported.join(', ') || 'None'}
                      </div>
                      <div>
                        <strong>Recovery:</strong> {spec.recovery_strategy}
                      </div>
                    </div>

                    <div className="p-2 rounded bg-amber-500/10 border border-amber-500/30 text-[10px] text-amber-200">
                      <strong>Honesty Limitation:</strong> {spec.checksum_trust_limitation}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Defensive Action Audit History */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
                Defensive Action Audit Trail ({defensiveActions.length})
              </h3>
              <div className="space-y-2">
                {defensiveActions.length === 0 ? (
                  <div className="p-4 rounded-xl border border-dashed border-slate-800 text-center text-slate-500 text-xs">
                    No defensive actions executed yet.
                  </div>
                ) : (
                  defensiveActions.map((act) => (
                    <div
                      key={act.action_id}
                      className="p-3 rounded-lg border border-slate-800 bg-midnight-900/40 text-xs flex items-center justify-between gap-4 font-mono"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-200">{act.action_type}</span>
                          <span className="text-[10px] text-slate-400">Node: {act.device_name}</span>
                        </div>
                        <p className="text-[11px] text-slate-400 font-sans mt-0.5">{act.result_message}</p>
                      </div>

                      <span
                        className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                          act.status === 'executed'
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : act.status === 'pending_confirmation'
                            ? 'bg-amber-500/20 text-amber-300'
                            : 'bg-rose-500/20 text-rose-300'
                        }`}
                      >
                        {act.status}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* CONFIRMATION GATE MODAL */}
      {confirmPendingAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-midnight-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-midnight-900 border border-rose-500/50 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-2 text-rose-400">
              <ShieldAlert className="w-5 h-5" />
              <h3 className="text-sm font-bold text-slate-100">Disruptive Defensive Action Confirmation Gate</h3>
            </div>

            <p className="text-xs text-slate-300">
              Action <strong>{confirmPendingAction.action_type}</strong> on node{' '}
              <code className="text-cyan-300">{confirmPendingAction.device_name}</code> is disruptive and will suspend
              live physical operations.
            </p>

            <div className="p-3 rounded bg-slate-900/80 border border-slate-800 text-[11px] text-slate-400">
              <strong>Recovery Procedure:</strong> {confirmPendingAction.recovery_procedure}
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setConfirmPendingAction(null)}
                className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
              >
                Cancel / Abort
              </button>
              <button
                onClick={() => handleRequestDefensiveAction(true)}
                className="px-4 py-2 rounded-lg bg-rose-500 hover:bg-rose-400 text-white font-bold text-xs"
              >
                Authorize Defensive Execution
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
