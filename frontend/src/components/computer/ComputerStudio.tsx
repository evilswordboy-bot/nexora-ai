import React, { useState, useEffect, useCallback } from 'react';
import {
  Monitor,
  Globe,
  HardDrive,
  Play,
  Pause,
  XCircle,
  RefreshCw,
  ShieldAlert,
  CheckCircle2,
  Eye,
  Lock,
  Terminal,
  Plus,
  Trash2,
  Check,
  X,
  Camera,
} from 'lucide-react';
import { api } from '../../services/api';
import { useChat } from '../../context/ChatContext';
import {
  ComputerActionStep,
  ComputerActionType,
  ComputerAuditLogEntry,
  ComputerCapabilitiesResponse,
  ComputerExecutionSession,
  ComputerTargetDomain,
} from '../../types';

const BROWSER_PRESET_STEPS: ComputerActionStep[] = [
  {
    step_id: 'step_1_open',
    title: 'Open Approved Target URL',
    target_domain: 'browser',
    action_type: 'open_url',
    target_url_or_path: 'https://example.com',
    selector: null,
    input_value: null,
    params: {},
    requires_approval: false,
    approval_reason: null,
    checkpoint_name: 'page_opened',
    timeout_seconds: 15,
  },
  {
    step_id: 'step_2_fill',
    title: 'Enter Search Query in Input',
    target_domain: 'browser',
    action_type: 'fill_text',
    target_url_or_path: '',
    selector: '#search-input',
    input_value: 'Nexora Stage 16 Browser Automation',
    params: {},
    requires_approval: false,
    approval_reason: null,
    checkpoint_name: null,
    timeout_seconds: 15,
  },
  {
    step_id: 'step_3_select',
    title: 'Select Research Category',
    target_domain: 'browser',
    action_type: 'select_option',
    target_url_or_path: '',
    selector: '#category-select',
    input_value: 'research',
    params: {},
    requires_approval: false,
    approval_reason: null,
    checkpoint_name: null,
    timeout_seconds: 15,
  },
  {
    step_id: 'step_4_extract',
    title: 'Extract Headings & Links (Untrusted Isolated)',
    target_domain: 'browser',
    action_type: 'extract_content',
    target_url_or_path: '',
    selector: 'h1, p, a',
    input_value: null,
    params: {},
    requires_approval: false,
    approval_reason: null,
    checkpoint_name: 'dom_extracted',
    timeout_seconds: 15,
  },
  {
    step_id: 'step_5_submit',
    title: 'Submit Form (Requires Explicit Approval)',
    target_domain: 'browser',
    action_type: 'submit_form',
    target_url_or_path: '',
    selector: '#search-form',
    input_value: null,
    params: {},
    requires_approval: true,
    approval_reason: 'Submitting a form is a consequential action requiring explicit user confirmation.',
    checkpoint_name: 'form_submitted',
    timeout_seconds: 15,
  },
];

const LOCAL_OS_PRESET_STEPS: ComputerActionStep[] = [
  {
    step_id: 'step_1_diag',
    title: 'Run Predefined System Diagnostic',
    target_domain: 'local_os',
    action_type: 'run_predefined_diagnostic',
    target_url_or_path: 'system_summary',
    selector: null,
    input_value: null,
    params: {},
    requires_approval: false,
    approval_reason: null,
    checkpoint_name: 'system_checked',
    timeout_seconds: 15,
  },
  {
    step_id: 'step_2_write',
    title: 'Write Sandboxed Verification Note',
    target_domain: 'local_os',
    action_type: 'write_workspace_file',
    target_url_or_path: 'automation_report.txt',
    selector: null,
    input_value: 'Stage 16 verified local workspace execution output.',
    params: {},
    requires_approval: false,
    approval_reason: null,
    checkpoint_name: 'file_written',
    timeout_seconds: 15,
  },
  {
    step_id: 'step_3_list',
    title: 'List Sandboxed Workspace Directory',
    target_domain: 'local_os',
    action_type: 'list_workspace_files',
    target_url_or_path: '.',
    selector: null,
    input_value: null,
    params: {},
    requires_approval: false,
    approval_reason: null,
    checkpoint_name: 'files_listed',
    timeout_seconds: 15,
  },
];

export const ComputerStudio: React.FC = () => {
  const { showToast } = useChat();

  const [capabilities, setCapabilities] = useState<ComputerCapabilitiesResponse | null>(null);
  const [sessions, setSessions] = useState<ComputerExecutionSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<ComputerExecutionSession | null>(null);
  const [auditLogs, setAuditLogs] = useState<ComputerAuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Task Builder State
  const [goal, setGoal] = useState(
    'Open Example Portal, fill search query, extract DOM elements, and submit form with user approval'
  );
  const [targetDomain, setTargetDomain] = useState<ComputerTargetDomain>('browser');
  const [targetUrl, setTargetUrl] = useState('https://example.com');
  const [executionMode, setExecutionMode] = useState<'execute' | 'simulate_only'>('execute');
  const [steps, setSteps] = useState<ComputerActionStep[]>(BROWSER_PRESET_STEPS);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [capRes, sessRes, logsRes] = await Promise.all([
        api.getComputerCapabilities(),
        api.getComputerSessions(),
        api.getComputerAuditLogs(),
      ]);
      setCapabilities(capRes);
      setSessions(sessRes);
      setAuditLogs(logsRes);
      if (sessRes.length > 0 && !selectedSession) {
        setSelectedSession(sessRes[0]);
      } else if (selectedSession) {
        const updated = sessRes.find((s) => s.session_id === selectedSession.session_id);
        if (updated) setSelectedSession(updated);
      }
    } catch (err: any) {
      showToast(err?.message || 'Failed to load Computer Control workspace.', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [selectedSession, showToast]);

  useEffect(() => {
    loadData();
  }, []);

  const handleDomainSwitch = (domain: ComputerTargetDomain) => {
    setTargetDomain(domain);
    if (domain === 'browser') {
      setGoal('Open Example Portal, fill search query, extract DOM elements, and submit form with user approval');
      setSteps(BROWSER_PRESET_STEPS.map((s) => ({ ...s })));
    } else {
      setGoal('Run predefined diagnostic, write report in sandboxed workspace, and list workspace files');
      setSteps(LOCAL_OS_PRESET_STEPS.map((s) => ({ ...s })));
    }
  };

  const handleLaunchSession = async (modeOverride?: 'execute' | 'simulate_only') => {
    const modeToUse = modeOverride || executionMode;
    setIsLoading(true);
    try {
      const created = await api.createComputerSession({
        goal,
        mode: modeToUse,
        target_domain: targetDomain,
        target_url: targetDomain === 'browser' ? targetUrl : undefined,
        steps,
        auto_start: true,
      });
      setSelectedSession(created);
      await loadData();
      if (created.status === 'WAITING_FOR_APPROVAL') {
        showToast('Paused at consequential action approval gate. Confirm preview to continue.', 'info');
      } else if (created.status === 'SIMULATION_PREVIEW') {
        showToast('Simulation preview generated (no actions executed).', 'info');
      } else if (created.status === 'VERIFIED_COMPLETED') {
        showToast('Computer session completed and verified!', 'success');
      } else {
        showToast(`Session status: ${created.status}`, 'error');
      }
    } catch (err: any) {
      showToast(err?.message || 'Failed to launch computer session.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleApproveStep = async (sessionId: string, stepId: string, approved: boolean) => {
    setIsLoading(true);
    try {
      const updated = await api.approveComputerStep(sessionId, {
        step_id: stepId,
        approved,
        user_note: approved ? 'Confirmed in Computer Actions Studio' : 'Declined in Computer Actions Studio',
      });
      setSelectedSession(updated);
      await loadData();
      showToast(
        approved ? 'Action approved and verified!' : 'Action declined; session cancelled.',
        approved ? 'success' : 'info'
      );
    } catch (err: any) {
      showToast(err?.message || 'Approval request failed.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleControlSession = async (
    sessionId: string,
    action: 'start' | 'pause' | 'cancel' | 'retry'
  ) => {
    setIsLoading(true);
    try {
      let updated: ComputerExecutionSession;
      if (action === 'start') updated = await api.startComputerSession(sessionId);
      else if (action === 'pause') updated = await api.pauseComputerSession(sessionId);
      else if (action === 'cancel') updated = await api.cancelComputerSession(sessionId);
      else updated = await api.retryComputerSession(sessionId);

      setSelectedSession(updated);
      await loadData();
      showToast(`Session ${action} -> ${updated.status}`, 'info');
    } catch (err: any) {
      showToast(err?.message || `Failed to ${action} session.`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'VERIFIED_COMPLETED':
      case 'VERIFIED_SUCCEEDED':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      case 'SIMULATION_PREVIEW':
      case 'SIMULATED':
        return 'bg-violet-500/15 text-violet-300 border-violet-500/30';
      case 'WAITING_FOR_APPROVAL':
      case 'PAUSED':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      case 'BLOCKED_BY_SECURITY_BOUNDARY':
      case 'BLOCKED':
      case 'FAILED':
        return 'bg-red-500/15 text-red-300 border-red-500/30';
      case 'RUNNING':
        return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-midnight-950 text-slate-100">
      {/* Top Header Banner */}
      <div className="border-b border-slate-800/80 bg-midnight-900/60 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <Monitor className="w-5 h-5 text-cyan-400" />
            <h1 className="text-lg font-bold tracking-wide text-slate-100">
              Computer Control & Digital Execution Engine
            </h1>
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
              Stage 16 • Verified Browser & Sandboxed OS Actions
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {capabilities?.architecture_disclosure ||
              'Browser automation is strictly separated from sandboxed local OS tasks. Consequential actions require preview-and-confirm approval.'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => handleLaunchSession('simulate_only')}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-violet-500/20 hover:bg-violet-500/30 text-violet-300 border border-violet-500/40"
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Simulate Preview</span>
          </button>
          <button
            onClick={() => handleLaunchSession('execute')}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-500 to-violet-600 hover:from-cyan-400 hover:to-violet-500 text-white shadow-sm"
          >
            <Play className="w-3.5 h-3.5" />
            <span>Start Verified Execution</span>
          </button>
          <button
            onClick={loadData}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 xl:grid-cols-12 gap-6">
        {/* Left Column: Task Planner & Action Steps (5 cols) */}
        <div className="xl:col-span-5 space-y-4">
          <div className="p-4 rounded-xl bg-midnight-900/70 border border-slate-800/80 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                1. Execution Domain (Strictly Separated)
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => handleDomainSwitch('browser')}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    targetDomain === 'browser'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  <Globe className="w-3.5 h-3.5" />
                  <span>Browser Automation</span>
                </button>
                <button
                  onClick={() => handleDomainSwitch('local_os')}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    targetDomain === 'local_os'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  <HardDrive className="w-3.5 h-3.5" />
                  <span>Sandboxed Local Runner</span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Task Goal</label>
              <input
                type="text"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg bg-midnight-950 border border-slate-800 text-xs text-slate-100"
              />
            </div>

            {targetDomain === 'browser' && (
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">
                  Target Website (SSRF & Local-Network Protected)
                </label>
                <input
                  type="text"
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-midnight-950 border border-slate-800 font-mono text-xs text-cyan-300"
                />
              </div>
            )}

            {/* Step List Editor */}
            <div className="space-y-2 pt-2 border-t border-slate-800">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">
                  Action Plan Steps ({steps.length})
                </span>
                <button
                  onClick={() =>
                    setSteps([
                      ...steps,
                      {
                        step_id: `step_${steps.length + 1}`,
                        title: `Step ${steps.length + 1}`,
                        target_domain: targetDomain,
                        action_type:
                          targetDomain === 'browser' ? 'capture_screenshot' : 'list_workspace_files',
                        target_url_or_path: targetDomain === 'browser' ? '' : '.',
                        selector: null,
                        input_value: null,
                        params: {},
                        requires_approval: false,
                        approval_reason: null,
                        checkpoint_name: null,
                        timeout_seconds: 15,
                      },
                    ])
                  }
                  className="flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                >
                  <Plus className="w-3 h-3" />
                  <span>Add Step</span>
                </button>
              </div>

              <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
                {steps.map((st, idx) => (
                  <div
                    key={st.step_id}
                    className="p-2.5 rounded-lg bg-midnight-950/90 border border-slate-800 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-[11px] text-cyan-400">#{idx + 1}</span>
                      <input
                        type="text"
                        value={st.title}
                        onChange={(e) => {
                          const copy = [...steps];
                          copy[idx] = { ...st, title: e.target.value };
                          setSteps(copy);
                        }}
                        className="flex-1 px-2 py-1 rounded bg-slate-900 border border-slate-800 text-xs text-slate-100"
                      />
                      <button
                        onClick={() => setSteps(steps.filter((_, i) => i !== idx))}
                        disabled={steps.length <= 1}
                        className="p-1 text-red-400 hover:text-red-300 disabled:opacity-40"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <select
                        value={st.action_type}
                        onChange={(e) => {
                          const copy = [...steps];
                          copy[idx] = { ...st, action_type: e.target.value as ComputerActionType };
                          setSteps(copy);
                        }}
                        className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-[11px] text-slate-200"
                      >
                        {(targetDomain === 'browser'
                          ? capabilities?.browser_capabilities || [
                              'open_url',
                              'click',
                              'fill_text',
                              'select_option',
                              'scroll',
                              'extract_content',
                              'capture_screenshot',
                              'submit_form',
                            ]
                          : capabilities?.local_os_capabilities || [
                              'list_workspace_files',
                              'read_workspace_file',
                              'write_workspace_file',
                              'delete_workspace_file',
                              'run_predefined_diagnostic',
                              'open_approved_application',
                            ]
                        ).map((act) => (
                          <option key={act} value={act}>
                            {act}
                          </option>
                        ))}
                      </select>

                      <input
                        type="text"
                        placeholder={targetDomain === 'browser' ? 'URL or Selector (#id)' : 'Sandbox relative path'}
                        value={st.selector || st.target_url_or_path || ''}
                        onChange={(e) => {
                          const copy = [...steps];
                          if (['click', 'fill_text', 'select_option', 'extract_content', 'submit_form'].includes(st.action_type)) {
                            copy[idx] = { ...st, selector: e.target.value };
                          } else {
                            copy[idx] = { ...st, target_url_or_path: e.target.value };
                          }
                          setSteps(copy);
                        }}
                        className="px-2 py-1 rounded bg-slate-900 border border-slate-800 font-mono text-[11px] text-slate-200"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Session History List */}
          <div className="p-4 rounded-xl bg-midnight-900/70 border border-slate-800/80 space-y-2.5">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Recent Isolated Sessions ({sessions.length})
            </span>
            <div className="space-y-2 max-h-[240px] overflow-y-auto pr-1">
              {sessions.map((s) => (
                <button
                  key={s.session_id}
                  onClick={() => setSelectedSession(s)}
                  className={`w-full text-left p-2.5 rounded-lg border transition-all ${
                    selectedSession?.session_id === s.session_id
                      ? 'bg-cyan-950/30 border-cyan-500/50'
                      : 'bg-midnight-950/80 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-slate-100 truncate">{s.goal}</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${statusColor(
                        s.status
                      )}`}
                    >
                      {s.status}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                    <span>
                      {s.target_domain.toUpperCase()} • {s.session_id}
                    </span>
                    <span>{s.verified_completion ? '✓ Verified' : 'Unverified / Pending'}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Active Session Inspector, Viewport Screenshot, Approval Gates & Logs (7 cols) */}
        <div className="xl:col-span-7 space-y-4">
          {!selectedSession ? (
            <div className="p-12 rounded-xl bg-midnight-900/50 border border-slate-800 text-center text-xs text-slate-400">
              Launch a Browser Automation or Sandboxed Local Session on the left to inspect live viewport screenshots, permission gates, and verified results.
            </div>
          ) : (
            <>
              {/* Session Status & Controls Bar */}
              <div className="p-4 rounded-xl bg-midnight-900/70 border border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${statusColor(
                        selectedSession.status
                      )}`}
                    >
                      {selectedSession.status}
                    </span>
                    <span className="text-xs font-mono text-slate-400">
                      {selectedSession.session_id}
                    </span>
                    {selectedSession.verified_completion && (
                      <span className="flex items-center gap-1 text-xs font-semibold text-emerald-400">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Verified Outcome</span>
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-200 mt-1 font-medium">{selectedSession.goal}</p>
                  {selectedSession.target_website && (
                    <div className="text-[11px] text-cyan-400 mt-0.5">
                      Target Website: {selectedSession.target_website}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-1.5">
                  {selectedSession.status === 'PAUSED' && (
                    <button
                      onClick={() => handleControlSession(selectedSession.session_id, 'start')}
                      className="flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 text-xs font-semibold border border-emerald-500/30"
                    >
                      <Play className="w-3.5 h-3.5" />
                      <span>Resume</span>
                    </button>
                  )}
                  {selectedSession.status === 'RUNNING' && (
                    <button
                      onClick={() => handleControlSession(selectedSession.session_id, 'pause')}
                      className="flex items-center gap-1 px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 text-xs font-semibold border border-amber-500/30"
                    >
                      <Pause className="w-3.5 h-3.5" />
                      <span>Pause</span>
                    </button>
                  )}
                  {['FAILED', 'CANCELLED', 'BLOCKED_BY_SECURITY_BOUNDARY'].includes(
                    selectedSession.status
                  ) && (
                    <button
                      onClick={() => handleControlSession(selectedSession.session_id, 'retry')}
                      className="flex items-center gap-1 px-2.5 py-1 rounded bg-cyan-500/20 text-cyan-300 text-xs font-semibold border border-cyan-500/30"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Retry</span>
                    </button>
                  )}
                  {['RUNNING', 'WAITING_FOR_APPROVAL', 'PAUSED'].includes(
                    selectedSession.status
                  ) && (
                    <button
                      onClick={() => handleControlSession(selectedSession.session_id, 'cancel')}
                      className="flex items-center gap-1 px-2.5 py-1 rounded bg-red-500/20 text-red-300 text-xs font-semibold border border-red-500/30"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Cancel</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Viewport Screenshot Panel */}
              {selectedSession.latest_screenshot_base64 && (
                <div className="p-4 rounded-xl bg-midnight-900/70 border border-slate-800/80 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="flex items-center gap-1.5 font-semibold text-slate-200">
                      <Camera className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Verified Browser Viewport Capture (Secrets Masked)</span>
                    </span>
                    {selectedSession.checkpoints.length > 0 && (
                      <span className="text-[11px] text-emerald-300">
                        Checkpoints: {selectedSession.checkpoints.join(' → ')}
                      </span>
                    )}
                  </div>
                  <img
                    src={selectedSession.latest_screenshot_base64}
                    alt="Verified Browser Viewport Screenshot"
                    className="w-full rounded-lg border border-slate-800 shadow-lg"
                  />
                </div>
              )}

              {/* Step Execution Cards & Approval Gate */}
              <div className="p-4 rounded-xl bg-midnight-900/70 border border-slate-800/80 space-y-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Step Verification & Permission Status ({selectedSession.step_results.length})
                </span>
                <div className="space-y-2.5">
                  {selectedSession.step_results.map((sr, i) => (
                    <div
                      key={sr.step_id}
                      className="p-3.5 rounded-xl bg-midnight-950/90 border border-slate-800 space-y-2"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-slate-400">#{i + 1}</span>
                          <span className="text-xs font-bold text-slate-100">{sr.title}</span>
                          <span className="text-[11px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-cyan-300 font-mono">
                            {sr.action_type}
                          </span>
                        </div>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${statusColor(
                            sr.status
                          )}`}
                        >
                          {sr.status}
                        </span>
                      </div>

                      {sr.verification_detail && (
                        <div className="text-[11px] text-emerald-300/90">
                          ✓ {sr.verification_detail}
                        </div>
                      )}

                      {/* Visible Preview-and-Confirm Flow for Consequential Actions */}
                      {sr.status === 'WAITING_FOR_APPROVAL' && (
                        <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-500/40 space-y-2">
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2 text-xs font-bold text-amber-200">
                              <ShieldAlert className="w-4 h-4 text-amber-400" />
                              <span>Preview & Confirm Consequential Action</span>
                            </div>
                            <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-amber-500/20 text-amber-300">
                              Risk: {sr.preview?.risk_level || 'high'}
                            </span>
                          </div>
                          <p className="text-xs text-amber-100/90">
                            {sr.approval_reason ||
                              'This action modifies external or workspace state and requires explicit confirmation.'}
                          </p>
                          {sr.preview && (
                            <div className="p-2 rounded bg-midnight-950/80 border border-amber-500/20 font-mono text-[11px] text-slate-300">
                              Target: {sr.preview.target_resource} | Params:{' '}
                              {JSON.stringify(sr.preview.parameters_preview)}
                            </div>
                          )}
                          <div className="flex items-center gap-2 pt-1">
                            <button
                              onClick={() =>
                                handleApproveStep(selectedSession.session_id, sr.step_id, true)
                              }
                              disabled={isLoading}
                              className="flex items-center gap-1 px-3 py-1 rounded-md text-xs font-semibold bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40"
                            >
                              <Check className="w-3.5 h-3.5" />
                              <span>Confirm & Execute</span>
                            </button>
                            <button
                              onClick={() =>
                                handleApproveStep(selectedSession.session_id, sr.step_id, false)
                              }
                              disabled={isLoading}
                              className="flex items-center gap-1 px-3 py-1 rounded-md text-xs font-semibold bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/40"
                            >
                              <X className="w-3.5 h-3.5" />
                              <span>Reject & Cancel</span>
                            </button>
                          </div>
                        </div>
                      )}

                      {sr.output_summary && (
                        <div className="p-2 rounded bg-slate-900/90 border border-slate-800 text-xs text-slate-200 whitespace-pre-wrap font-mono">
                          {sr.output_summary}
                        </div>
                      )}

                      {sr.error_message && (
                        <div className="p-2 rounded bg-red-950/40 border border-red-500/30 text-xs text-red-300">
                          {sr.error_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Execution Logs & Security Audit Trail */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-midnight-900/70 border border-slate-800/80 space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300">
                    <Terminal className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Session Execution Logs (Secrets Redacted)</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-midnight-950 border border-slate-800 font-mono text-[11px] text-slate-300 space-y-1 max-h-44 overflow-y-auto">
                    {selectedSession.execution_logs.map((line, idx) => (
                      <div key={idx}>{line}</div>
                    ))}
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-midnight-900/70 border border-slate-800/80 space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300">
                    <Lock className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Security Audit Trail ({auditLogs.length})</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-midnight-950 border border-slate-800 font-mono text-[11px] text-slate-300 space-y-1.5 max-h-44 overflow-y-auto">
                    {auditLogs.slice(0, 12).map((a) => (
                      <div key={a.audit_id} className="border-b border-slate-800/60 pb-1">
                        <span className="text-cyan-400">[{a.action_type}]</span> {a.status} —{' '}
                        {a.detail}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
