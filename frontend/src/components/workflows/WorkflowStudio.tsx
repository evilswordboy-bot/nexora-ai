import React, { useState, useEffect, useCallback } from 'react';
import {
  Play,
  Pause,
  Plus,
  Trash2,
  Copy,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  RefreshCw,
  Bell,
  ShieldAlert,
  GitBranch,
  Layers,
  Check,
  X,
  Edit3,
  Sparkles,
  Wrench,
  Calendar,
  Activity,
} from 'lucide-react';
import { api } from '../../services/api';
import { useChat } from '../../context/ChatContext';
import {
  WorkflowDefinition,
  WorkflowExecutionRun,
  WorkflowMetadataResponse,
  WorkflowNotificationItem,
  WorkflowScheduleConfig,
  WorkflowStatus,
  WorkflowStepDefinition,
  WorkflowValidationResult,
  AgentRoleId,
} from '../../types';

const DEFAULT_SCHEDULE: WorkflowScheduleConfig = {
  trigger_type: 'manual',
  recurrence: 'daily',
  interval_minutes: 60,
  timezone: 'Asia/Kolkata',
  allow_concurrent_runs: false,
};

const DEFAULT_STEP = (idx: number): WorkflowStepDefinition => ({
  step_id: `step_${idx}`,
  name: `Task Step ${idx}`,
  description: 'Executes automated task step',
  action_type: 'tool',
  agent_id: 'research_agent',
  tool_name: 'calculator',
  prompt_template: 'Analyze and summarize: {{workflow.input.topic}}',
  tool_params: { expression: '100 + 25' },
  input_mapping: {},
  output_key: 'output',
  depends_on: idx > 1 ? [`step_${idx - 1}`] : [],
  condition_expression: 'always',
  on_condition_false: 'skip',
  jump_to_step_id: null,
  max_retries: 1,
  retry_delay_seconds: 0.2,
  timeout_seconds: 25,
  requires_approval: false,
  approval_reason: null,
});

export const WorkflowStudio: React.FC = () => {
  const { settings, showToast } = useChat();

  const [activeTab, setActiveTab] = useState<'dashboard' | 'builder' | 'runs' | 'notifications'>('dashboard');
  const [metadata, setMetadata] = useState<WorkflowMetadataResponse | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowDefinition[]>([]);
  const [templates, setTemplates] = useState<WorkflowDefinition[]>([]);
  const [runs, setRuns] = useState<WorkflowExecutionRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<WorkflowExecutionRun | null>(null);
  const [notifications, setNotifications] = useState<WorkflowNotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Filters
  const [wfStatusFilter, setWfStatusFilter] = useState<string>('ALL');
  const [runStatusFilter, setRunStatusFilter] = useState<string>('ALL');

  // Runtime inputs JSON string for quick execution
  const [runtimeInputText, setRuntimeInputText] = useState<string>(
    '{\n  "topic": "AI Agent Security & Automation",\n  "audit_query": "compliance obligations",\n  "feature_summary": "Stage 15 Workflow Automation Engine",\n  "target_language": "ta",\n  "formula": "(240 * 1.15) + 50",\n  "recipient": "ops-team-channel"\n}'
  );

  // Builder State
  const [editingWorkflowId, setEditingWorkflowId] = useState<string | null>(null);
  const [wfName, setWfName] = useState('Automated Research & Verification Pipeline');
  const [wfDescription, setWfDescription] = useState(
    'Executes sequential tool and agent tasks with input/output mapping and safety guardrails.'
  );
  const [wfCategory, setWfCategory] = useState('research');
  const [wfStatus, setWfStatus] = useState<WorkflowStatus>('ACTIVE');
  const [wfBudget, setWfBudget] = useState(0.35);
  const [wfSchedule, setWfSchedule] = useState<WorkflowScheduleConfig>(DEFAULT_SCHEDULE);
  const [wfSteps, setWfSteps] = useState<WorkflowStepDefinition[]>([
    {
      step_id: 'step_1',
      name: 'Calculate Baseline Metric',
      description: 'Computes deterministic formula via AST calculator',
      action_type: 'tool',
      agent_id: null,
      tool_name: 'calculator',
      prompt_template: '',
      tool_params: { expression: '{{workflow.input.formula}}' },
      input_mapping: {},
      output_key: 'calc_output',
      depends_on: [],
      condition_expression: 'always',
      on_condition_false: 'skip',
      jump_to_step_id: null,
      max_retries: 1,
      retry_delay_seconds: 0.1,
      timeout_seconds: 20,
      requires_approval: false,
      approval_reason: null,
    },
    {
      step_id: 'step_2',
      name: 'Synthesize Executive Note',
      description: 'Uses Writing Agent to summarize the computed metric',
      action_type: 'agent',
      agent_id: 'writing_agent',
      tool_name: null,
      prompt_template:
        'Draft a concise operational update for {{workflow.input.topic}} incorporating calculated metric: {{steps.step_1.output}}',
      tool_params: {},
      input_mapping: {},
      output_key: 'summary_output',
      depends_on: ['step_1'],
      condition_expression: 'previous_succeeded',
      on_condition_false: 'skip',
      jump_to_step_id: null,
      max_retries: 1,
      retry_delay_seconds: 0.2,
      timeout_seconds: 25,
      requires_approval: false,
      approval_reason: null,
    },
  ]);
  const [emailOptIn, setEmailOptIn] = useState(false);
  const [webhookOptIn, setWebhookOptIn] = useState(false);
  const [validationResult, setValidationResult] = useState<WorkflowValidationResult | null>(null);

  const loadAll = useCallback(async () => {
    setIsLoading(true);
    try {
      const [metaRes, wfRes, tplRes, runsRes, notifRes] = await Promise.all([
        api.getWorkflowMetadata(),
        api.getWorkflows({ includeTemplates: false }),
        api.getWorkflowTemplates(),
        api.getWorkflowRuns(),
        api.getWorkflowNotifications(false),
      ]);
      setMetadata(metaRes);
      setWorkflows(wfRes);
      setTemplates(tplRes);
      setRuns(runsRes);
      if (runsRes.length > 0 && !selectedRun) {
        setSelectedRun(runsRes[0]);
      } else if (selectedRun) {
        const updated = runsRes.find((r) => r.run_id === selectedRun.run_id);
        if (updated) setSelectedRun(updated);
      }
      setNotifications(notifRes);
    } catch (err: any) {
      showToast(err?.message || 'Failed to load Workflow Automation data.', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [selectedRun, showToast]);

  useEffect(() => {
    loadAll();
  }, []);

  const parseRuntimeInputs = (): Record<string, any> => {
    try {
      const parsed = JSON.parse(runtimeInputText || '{}');
      return typeof parsed === 'object' && parsed !== null ? parsed : {};
    } catch {
      return { topic: runtimeInputText };
    }
  };

  const handleRunWorkflow = async (wfId: string, isDryRun = false) => {
    setIsLoading(true);
    try {
      const run = await api.triggerWorkflowRun(
        wfId,
        {
          trigger_source: isDryRun ? 'test_dry_run' : 'manual',
          is_dry_run: isDryRun,
          runtime_inputs: parseRuntimeInputs(),
        },
        settings
      );
      setSelectedRun(run);
      setActiveTab('runs');
      await loadAll();
      if (run.status === 'WAITING_FOR_APPROVAL') {
        showToast('Workflow paused at approval gate. Review and approve to continue.', 'info');
      } else if (run.status === 'SUCCEEDED') {
        showToast(isDryRun ? 'Dry-run validation succeeded!' : 'Workflow execution succeeded!', 'success');
      } else {
        showToast(`Workflow ended with status: ${run.status}`, 'error');
      }
    } catch (err: any) {
      showToast(err?.message || 'Failed to execute workflow.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleWorkflowStatus = async (wf: WorkflowDefinition) => {
    const nextStatus: WorkflowStatus = wf.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
    try {
      await api.setWorkflowStatus(wf.workflow_id, nextStatus);
      showToast(`Workflow '${wf.name}' is now ${nextStatus}.`, 'success');
      await loadAll();
    } catch (err: any) {
      showToast(err?.message || 'Failed to update workflow status.', 'error');
    }
  };

  const handleDuplicate = async (wfId: string) => {
    try {
      const cloned = await api.duplicateWorkflow(wfId);
      showToast(`Cloned workflow: ${cloned.name}`, 'success');
      await loadAll();
    } catch (err: any) {
      showToast(err?.message || 'Failed to duplicate workflow.', 'error');
    }
  };

  const handleDelete = async (wfId: string) => {
    try {
      await api.deleteWorkflow(wfId);
      showToast('Workflow deleted.', 'info');
      await loadAll();
    } catch (err: any) {
      showToast(err?.message || 'Failed to delete workflow.', 'error');
    }
  };

  const handleLoadIntoBuilder = (wf: WorkflowDefinition) => {
    setEditingWorkflowId(wf.is_template ? null : wf.workflow_id);
    setWfName(wf.is_template ? `${wf.name} (Custom)` : wf.name);
    setWfDescription(wf.description);
    setWfCategory(wf.category);
    setWfStatus(wf.is_template ? 'ACTIVE' : wf.status);
    setWfBudget(wf.max_cost_budget_usd);
    setWfSchedule({ ...wf.schedule });
    setWfSteps(wf.steps.map((s) => ({ ...s })));
    setEmailOptIn(wf.notification_config.email_opt_in);
    setWebhookOptIn(wf.notification_config.webhook_opt_in);
    setValidationResult(null);
    setActiveTab('builder');
  };

  const handleValidateBuilder = async () => {
    try {
      const res = await api.validateWorkflow({
        steps: wfSteps,
        schedule: wfSchedule,
        max_cost_budget_usd: wfBudget,
      });
      setValidationResult(res);
      if (res.valid) {
        showToast('Workflow DAG & configuration are valid!', 'success');
      } else {
        showToast(`Validation found ${res.issues.length} issue(s).`, 'error');
      }
    } catch (err: any) {
      showToast(err?.message || 'Validation request failed.', 'error');
    }
  };

  const handleSaveWorkflow = async () => {
    setIsLoading(true);
    try {
      const notifConfig = {
        in_app_enabled: true,
        email_opt_in: emailOptIn,
        email_recipient: null,
        webhook_opt_in: webhookOptIn,
        notify_on_complete: true,
        notify_on_failure: true,
        notify_on_approval_required: true,
      };
      if (editingWorkflowId) {
        await api.updateWorkflow(editingWorkflowId, {
          name: wfName,
          description: wfDescription,
          category: wfCategory,
          status: wfStatus,
          schedule: wfSchedule,
          steps: wfSteps,
          notification_config: notifConfig,
          max_cost_budget_usd: wfBudget,
        });
        showToast('Workflow updated!', 'success');
      } else {
        const created = await api.createWorkflow({
          name: wfName,
          description: wfDescription,
          category: wfCategory,
          status: wfStatus,
          schedule: wfSchedule,
          steps: wfSteps,
          notification_config: notifConfig,
          max_cost_budget_usd: wfBudget,
        });
        setEditingWorkflowId(created.workflow_id);
        showToast('Workflow created!', 'success');
      }
      await loadAll();
      setActiveTab('dashboard');
    } catch (err: any) {
      showToast(err?.message || 'Failed to save workflow.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleApproveStep = async (runId: string, stepId: string, approved: boolean) => {
    setIsLoading(true);
    try {
      const updated = await api.approveWorkflowStep(
        runId,
        {
          step_id: stepId,
          approved,
          user_note: approved ? 'Approved by user in Automation Studio' : 'Rejected by user in Automation Studio',
        },
        settings
      );
      setSelectedRun(updated);
      await loadAll();
      showToast(
        approved ? 'Step approved and workflow resumed!' : 'Approval rejected; workflow cancelled.',
        approved ? 'success' : 'info'
      );
    } catch (err: any) {
      showToast(err?.message || 'Failed to process approval.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetryRun = async (runId: string) => {
    setIsLoading(true);
    try {
      const updated = await api.retryWorkflowRun(runId, true, settings);
      setSelectedRun(updated);
      await loadAll();
      showToast(`Retry completed with status: ${updated.status}`, 'info');
    } catch (err: any) {
      showToast(err?.message || 'Failed to retry workflow run.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelRun = async (runId: string) => {
    try {
      const updated = await api.cancelWorkflowRun(runId);
      setSelectedRun(updated);
      await loadAll();
      showToast('Workflow run cancelled.', 'info');
    } catch (err: any) {
      showToast(err?.message || 'Failed to cancel run.', 'error');
    }
  };

  const handleTickScheduler = async () => {
    setIsLoading(true);
    try {
      const triggered = await api.tickWorkflowScheduler();
      await loadAll();
      showToast(
        triggered.length > 0
          ? `Scheduler triggered ${triggered.length} due workflow(s).`
          : 'Scheduler checked: 0 workflows currently due.',
        'info'
      );
    } catch (err: any) {
      showToast(err?.message || 'Scheduler tick failed.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const unreadCount = notifications.filter((n) => !n.read).length;
  const filteredWorkflows = workflows.filter((w) => wfStatusFilter === 'ALL' || w.status === wfStatusFilter);
  const filteredRuns = runs.filter((r) => runStatusFilter === 'ALL' || r.status === runStatusFilter);

  const statusBadgeColor = (status: string) => {
    switch (status) {
      case 'SUCCEEDED':
      case 'ACTIVE':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      case 'RUNNING':
      case 'RETRYING':
      case 'QUEUED':
        return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
      case 'WAITING_FOR_APPROVAL':
      case 'PAUSED':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      case 'FAILED':
        return 'bg-red-500/15 text-red-300 border-red-500/30';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-midnight-950 text-slate-100">
      {/* Top Banner */}
      <div className="border-b border-slate-800/80 bg-midnight-900/60 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <GitBranch className="w-5 h-5 text-cyan-400" />
            <h1 className="text-lg font-bold tracking-wide text-slate-100">
              Workflow Automation Engine
            </h1>
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
              Stage 15 • Durable DAG & Scheduler
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Execute multi-step AI agent & tool pipelines with timezone scheduling, input/output templating, bounded retries, and mandatory approval gates.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleTickScheduler}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700 transition-all"
            title="Evaluate due scheduled workflows now"
          >
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>Check Due Schedules</span>
          </button>

          <button
            onClick={() => {
              setEditingWorkflowId(null);
              setWfName('New Custom Automation Workflow');
              setWfSteps([DEFAULT_STEP(1), DEFAULT_STEP(2)]);
              setValidationResult(null);
              setActiveTab('builder');
            }}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-500 to-violet-600 hover:from-cyan-400 hover:to-violet-500 text-white shadow-sm transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Workflow</span>
          </button>

          <button
            onClick={loadAll}
            className="p-1.5 rounded-lg bg-slate-800/70 hover:bg-slate-700 text-slate-300 border border-slate-700"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Sub-navigation Tabs */}
      <div className="border-b border-slate-800/80 bg-midnight-900/30 px-6 flex items-center gap-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab('dashboard')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'dashboard'
              ? 'border-cyan-400 text-cyan-300'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Workflows & Templates ({workflows.length + templates.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('builder')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'builder'
              ? 'border-cyan-400 text-cyan-300'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Edit3 className="w-3.5 h-3.5" />
          <span>Visual Workflow Builder</span>
        </button>

        <button
          onClick={() => setActiveTab('runs')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'runs'
              ? 'border-cyan-400 text-cyan-300'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Execution Monitor ({runs.length})</span>
          {runs.some((r) => r.status === 'WAITING_FOR_APPROVAL') && (
            <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
              Approval Needed
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('notifications')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'notifications'
              ? 'border-cyan-400 text-cyan-300'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Bell className="w-3.5 h-3.5" />
          <span>Notification Center</span>
          {unreadCount > 0 && (
            <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
              {unreadCount}
            </span>
          )}
        </button>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Runtime Input Bar & Status Filters */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 p-4 rounded-xl bg-midnight-900/70 border border-slate-800/80 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Your Workflows ({filteredWorkflows.length})
                  </span>
                  <div className="flex items-center gap-1.5">
                    {['ALL', 'ACTIVE', 'DRAFT', 'PAUSED', 'DISABLED'].map((st) => (
                      <button
                        key={st}
                        onClick={() => setWfStatusFilter(st)}
                        className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                          wfStatusFilter === st
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                            : 'bg-slate-800/60 text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        {st}
                      </button>
                    ))}
                  </div>
                </div>

                {filteredWorkflows.length === 0 ? (
                  <div className="p-6 text-center rounded-lg border border-dashed border-slate-800 text-slate-400 text-xs">
                    No custom workflows match filter "{wfStatusFilter}". Clone a template below or click "+ New Workflow" to build one.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {filteredWorkflows.map((wf) => (
                      <div
                        key={wf.workflow_id}
                        className="p-4 rounded-xl bg-midnight-950/90 border border-slate-800/90 hover:border-slate-700 flex flex-col justify-between gap-3"
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2">
                            <h3 className="text-sm font-semibold text-slate-100">{wf.name}</h3>
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${statusBadgeColor(
                                wf.status
                              )}`}
                            >
                              {wf.status}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400 mt-1 line-clamp-2">{wf.description}</p>

                          <div className="flex flex-wrap items-center gap-2 mt-3 text-[11px] text-slate-400">
                            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
                              {wf.steps.length} steps
                            </span>
                            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 flex items-center gap-1">
                              <Calendar className="w-3 h-3 text-cyan-400" />
                              {wf.schedule.trigger_type === 'scheduled'
                                ? `${wf.schedule.recurrence} (${wf.schedule.timezone})`
                                : 'Manual Trigger'}
                            </span>
                            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
                              Runs: {wf.total_runs} ({wf.succeeded_runs} ok / {wf.failed_runs} fail)
                            </span>
                          </div>
                          {wf.schedule.next_run_at && (
                            <div className="text-[11px] text-cyan-400/90 mt-1.5">
                              Next scheduled run: {new Date(wf.schedule.next_run_at).toLocaleString()}
                            </div>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-800/80">
                          <button
                            onClick={() => handleRunWorkflow(wf.workflow_id, false)}
                            disabled={isLoading}
                            className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/30"
                          >
                            <Play className="w-3 h-3" />
                            <span>Run</span>
                          </button>
                          <button
                            onClick={() => handleRunWorkflow(wf.workflow_id, true)}
                            disabled={isLoading}
                            className="px-2 py-1 rounded-md text-xs bg-slate-800 hover:bg-slate-700 text-slate-300"
                            title="Dry-run test without side effects"
                          >
                            Test
                          </button>
                          <button
                            onClick={() => handleToggleWorkflowStatus(wf)}
                            className="p-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300"
                            title={wf.status === 'ACTIVE' ? 'Pause schedule' : 'Activate workflow'}
                          >
                            {wf.status === 'ACTIVE' ? (
                              <Pause className="w-3.5 h-3.5 text-amber-400" />
                            ) : (
                              <Play className="w-3.5 h-3.5 text-emerald-400" />
                            )}
                          </button>
                          <button
                            onClick={() => handleLoadIntoBuilder(wf)}
                            className="p-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300"
                            title="Edit in Builder"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDuplicate(wf.workflow_id)}
                            className="p-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300"
                            title="Duplicate"
                          >
                            <Copy className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDelete(wf.workflow_id)}
                            className="p-1.5 rounded-md bg-red-950/50 hover:bg-red-900/60 text-red-300 ml-auto"
                            title="Delete"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Runtime Inputs JSON Box */}
              <div className="p-4 rounded-xl bg-midnight-900/70 border border-slate-800/80 flex flex-col justify-between space-y-3">
                <div>
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Runtime Input Variables (JSON)
                  </span>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Referenced inside workflow steps via{' '}
                    <code className="text-cyan-300">{'{{workflow.input.<key>}}'}</code>.
                  </p>
                  <textarea
                    value={runtimeInputText}
                    onChange={(e) => setRuntimeInputText(e.target.value)}
                    rows={7}
                    className="w-full mt-2 p-2.5 rounded-lg bg-midnight-950 border border-slate-800 font-mono text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-[11px] text-slate-400 space-y-1">
                  <div className="font-semibold text-slate-300">Safety & Budget Guardrails Active:</div>
                  <div>• Max steps per workflow: {metadata?.limits.max_steps ?? 15}</div>
                  <div>• Max retries per step: {metadata?.limits.max_step_retries ?? 3}</div>
                  <div>• Consequential actions pause in WAITING_FOR_APPROVAL</div>
                </div>
              </div>
            </div>

            {/* Pre-Built Workflow Templates */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Pre-Built Automation Templates ({templates.length})
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {templates.map((tpl) => (
                  <div
                    key={tpl.workflow_id}
                    className="p-4 rounded-xl bg-midnight-900/60 border border-slate-800/80 hover:border-cyan-500/40 flex flex-col justify-between gap-3 transition-all"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-violet-500/15 text-violet-300 border border-violet-500/30">
                          Template • {tpl.category}
                        </span>
                        <span className="text-[11px] text-slate-400">{tpl.steps.length} steps</span>
                      </div>
                      <h4 className="text-sm font-semibold text-slate-100 mt-2">{tpl.name}</h4>
                      <p className="text-xs text-slate-400 mt-1">{tpl.description}</p>
                    </div>

                    <div className="flex items-center gap-2 pt-2 border-t border-slate-800/80">
                      <button
                        onClick={() => handleRunWorkflow(tpl.workflow_id, false)}
                        disabled={isLoading}
                        className="flex-1 flex items-center justify-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/30"
                      >
                        <Play className="w-3.5 h-3.5" />
                        <span>Run</span>
                      </button>
                      <button
                        onClick={() => handleDuplicate(tpl.workflow_id)}
                        className="flex items-center justify-center gap-1 px-2.5 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-200"
                        title="Clone template to your workflows"
                      >
                        <Copy className="w-3.5 h-3.5" />
                        <span>Clone</span>
                      </button>
                      <button
                        onClick={() => handleLoadIntoBuilder(tpl)}
                        className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                        title="Customize in Builder"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'builder' && (
          <div className="space-y-6 max-w-5xl mx-auto">
            {/* Workflow Metadata & Schedule Card */}
            <div className="p-5 rounded-xl bg-midnight-900/70 border border-slate-800/80 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-slate-100">
                  {editingWorkflowId ? `Editing Workflow (${editingWorkflowId})` : 'Create New Workflow'}
                </h2>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleValidateBuilder}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700"
                  >
                    Validate DAG
                  </button>
                  <button
                    onClick={handleSaveWorkflow}
                    disabled={isLoading}
                    className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-500 to-violet-600 text-white"
                  >
                    Save Workflow
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Workflow Name</label>
                  <input
                    type="text"
                    value={wfName}
                    onChange={(e) => setWfName(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-lg bg-midnight-950 border border-slate-800 text-xs text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Status</label>
                  <select
                    value={wfStatus}
                    onChange={(e) => setWfStatus(e.target.value as WorkflowStatus)}
                    className="w-full px-3 py-1.5 rounded-lg bg-midnight-950 border border-slate-800 text-xs text-slate-100"
                  >
                    <option value="DRAFT">DRAFT</option>
                    <option value="ACTIVE">ACTIVE</option>
                    <option value="PAUSED">PAUSED</option>
                    <option value="DISABLED">DISABLED</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Max Cost Budget (USD)</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.01"
                    max="10"
                    value={wfBudget}
                    onChange={(e) => setWfBudget( parseFloat(e.target.value) || 0.25 )}
                    className="w-full px-3 py-1.5 rounded-lg bg-midnight-950 border border-slate-800 text-xs text-slate-100"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Description</label>
                <input
                  type="text"
                  value={wfDescription}
                  onChange={(e) => setWfDescription(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-midnight-950 border border-slate-800 text-xs text-slate-100"
                />
              </div>

              {/* Trigger & Schedule Configuration */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-3 border-t border-slate-800/80">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Trigger Mode</label>
                  <select
                    value={wfSchedule.trigger_type}
                    onChange={(e) =>
                      setWfSchedule({
                        ...wfSchedule,
                        trigger_type: e.target.value as 'manual' | 'scheduled',
                      })
                    }
                    className="w-full px-3 py-1.5 rounded-lg bg-midnight-950 border border-slate-800 text-xs text-slate-100"
                  >
                    <option value="manual">Manual Trigger</option>
                    <option value="scheduled">Scheduled Trigger</option>
                  </select>
                </div>

                {wfSchedule.trigger_type === 'scheduled' && (
                  <>
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Recurrence Rule</label>
                      <select
                        value={wfSchedule.recurrence}
                        onChange={(e) =>
                          setWfSchedule({
                            ...wfSchedule,
                            recurrence: e.target.value as any,
                          })
                        }
                        className="w-full px-3 py-1.5 rounded-lg bg-midnight-950 border border-slate-800 text-xs text-slate-100"
                      >
                        <option value="once">One-Time</option>
                        <option value="hourly">Hourly</option>
                        <option value="daily">Daily</option>
                        <option value="weekly">Weekly</option>
                        <option value="interval">Custom Interval (Minutes)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Time Zone (IANA)</label>
                      <select
                        value={wfSchedule.timezone}
                        onChange={(e) => setWfSchedule({ ...wfSchedule, timezone: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg bg-midnight-950 border border-slate-800 text-xs text-slate-100"
                      >
                        {(
                          metadata?.supported_timezones || [
                            'UTC',
                            'Asia/Kolkata',
                            'America/New_York',
                            'Europe/London',
                          ]
                        ).map((tz) => (
                          <option key={tz} value={tz}>
                            {tz}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Overlap Protection</label>
                      <label className="flex items-center gap-2 text-xs text-slate-300 mt-2">
                        <input
                          type="checkbox"
                          checked={!wfSchedule.allow_concurrent_runs}
                          onChange={(e) =>
                            setWfSchedule({
                              ...wfSchedule,
                              allow_concurrent_runs: !e.target.checked,
                            })
                          }
                        />
                        <span>Prevent overlapping runs</span>
                      </label>
                    </div>
                  </>
                )}
              </div>

              {/* Honest Notification Opt-in Controls */}
              <div className="flex flex-wrap items-center gap-6 pt-3 border-t border-slate-800/80 text-xs text-slate-300">
                <span className="font-semibold text-slate-400">Notifications:</span>
                <label className="flex items-center gap-1.5">
                  <input type="checkbox" checked readOnly />
                  <span>In-App Notification Center (Active)</span>
                </label>
                <label className="flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    checked={webhookOptIn}
                    onChange={(e) => setWebhookOptIn(e.target.checked)}
                  />
                  <span>
                    Webhook Alert ({metadata?.notification_channels.webhook_configured ? 'Configured' : 'Not Configured in .env'})
                  </span>
                </label>
                <label className="flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    checked={emailOptIn}
                    onChange={(e) => setEmailOptIn(e.target.checked)}
                  />
                  <span>
                    SMTP Email ({metadata?.notification_channels.smtp_configured ? 'Configured' : 'Not Configured in .env'})
                  </span>
                </label>
              </div>
            </div>

            {/* Validation Banner */}
            {validationResult && (
              <div
                className={`p-4 rounded-xl border text-xs space-y-2 ${
                  validationResult.valid
                    ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-200'
                    : 'bg-red-950/30 border-red-500/40 text-red-200'
                }`}
              >
                <div className="font-bold flex items-center gap-2">
                  {validationResult.valid ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-red-400" />
                  )}
                  <span>
                    {validationResult.valid
                      ? `Valid DAG! Topological Execution Order: ${validationResult.execution_order.join(' → ')}`
                      : 'Workflow Validation Failed'}
                  </span>
                </div>
                {validationResult.issues.map((iss, i) => (
                  <div key={i} className="pl-6">
                    • [{iss.severity.toUpperCase()}] {iss.code}: {iss.message}
                  </div>
                ))}
              </div>
            )}

            {/* Step Editor List */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Sequential & Conditional Workflow Steps ({wfSteps.length})
                </h3>
                <button
                  onClick={() => setWfSteps([...wfSteps, DEFAULT_STEP(wfSteps.length + 1)])}
                  className="flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Step</span>
                </button>
              </div>

              {wfSteps.map((step, index) => (
                <div
                  key={step.step_id}
                  className="p-4 rounded-xl bg-midnight-900/70 border border-slate-800/90 space-y-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-mono text-xs font-bold">
                        #{index + 1} ({step.step_id})
                      </span>
                      <input
                        type="text"
                        value={step.name}
                        onChange={(e) => {
                          const copy = [...wfSteps];
                          copy[index] = { ...step, name: e.target.value };
                          setWfSteps(copy);
                        }}
                        className="px-2.5 py-1 rounded bg-midnight-950 border border-slate-800 text-xs font-semibold text-slate-100"
                      />
                    </div>
                    <button
                      onClick={() => setWfSteps(wfSteps.filter((_, i) => i !== index))}
                      disabled={wfSteps.length <= 1}
                      className="p-1.5 rounded bg-red-950/40 hover:bg-red-900/50 text-red-300 disabled:opacity-40"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                    <div>
                      <label className="block text-[11px] text-slate-400 mb-1">Action Type</label>
                      <select
                        value={step.action_type}
                        onChange={(e) => {
                          const copy = [...wfSteps];
                          copy[index] = { ...step, action_type: e.target.value as any };
                          setWfSteps(copy);
                        }}
                        className="w-full px-2.5 py-1.5 rounded bg-midnight-950 border border-slate-800 text-xs text-slate-100"
                      >
                        <option value="agent">Specialized AI Agent</option>
                        <option value="tool">Registered Tool</option>
                        <option value="transform">Data Transform</option>
                        <option value="condition_gate">Condition Gate</option>
                      </select>
                    </div>

                    {step.action_type === 'agent' && (
                      <div>
                        <label className="block text-[11px] text-slate-400 mb-1">Target Agent</label>
                        <select
                          value={step.agent_id || 'research_agent'}
                          onChange={(e) => {
                            const copy = [...wfSteps];
                            copy[index] = { ...step, agent_id: e.target.value as AgentRoleId };
                            setWfSteps(copy);
                          }}
                          className="w-full px-2.5 py-1.5 rounded bg-midnight-950 border border-slate-800 text-xs text-slate-100"
                        >
                          {(metadata?.available_agents || []).map((ag) => (
                            <option key={ag.agent_id} value={ag.agent_id}>
                              {ag.name} ({ag.permission_scope})
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    {step.action_type === 'tool' && (
                      <div>
                        <label className="block text-[11px] text-slate-400 mb-1">Registered Tool</label>
                        <select
                          value={step.tool_name || 'calculator'}
                          onChange={(e) => {
                            const copy = [...wfSteps];
                            copy[index] = { ...step, tool_name: e.target.value };
                            setWfSteps(copy);
                          }}
                          className="w-full px-2.5 py-1.5 rounded bg-midnight-950 border border-slate-800 text-xs text-slate-100"
                        >
                          {(metadata?.available_tools || []).map((t) => (
                            <option key={t.name} value={t.name}>
                              {t.name} {t.requires_approval ? '(Approval Required)' : ''}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    <div>
                      <label className="block text-[11px] text-slate-400 mb-1">
                        Condition (e.g. always, contains:xyz)
                      </label>
                      <input
                        type="text"
                        value={step.condition_expression}
                        onChange={(e) => {
                          const copy = [...wfSteps];
                          copy[index] = { ...step, condition_expression: e.target.value };
                          setWfSteps(copy);
                        }}
                        className="w-full px-2.5 py-1.5 rounded bg-midnight-950 border border-slate-800 text-xs text-slate-100"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] text-slate-400 mb-1">Max Retries (0–3)</label>
                      <input
                        type="number"
                        min={0}
                        max={3}
                        value={step.max_retries}
                        onChange={(e) => {
                          const copy = [...wfSteps];
                          copy[index] = { ...step, max_retries: parseInt(e.target.value, 10) || 0 };
                          setWfSteps(copy);
                        }}
                        className="w-full px-2.5 py-1.5 rounded bg-midnight-950 border border-slate-800 text-xs text-slate-100"
                      />
                    </div>
                  </div>

                  {step.action_type === 'tool' ? (
                    <div>
                      <label className="block text-[11px] text-slate-400 mb-1">
                        Tool Parameters (JSON — supports {'{{workflow.input.x}}'} and {'{{steps.step_1.output}}'})
                      </label>
                      <input
                        type="text"
                        value={JSON.stringify(step.tool_params)}
                        onChange={(e) => {
                          try {
                            const parsed = JSON.parse(e.target.value);
                            const copy = [...wfSteps];
                            copy[index] = { ...step, tool_params: parsed };
                            setWfSteps(copy);
                          } catch {
                            // wait for valid json
                          }
                        }}
                        className="w-full px-2.5 py-1.5 rounded bg-midnight-950 border border-slate-800 font-mono text-xs text-slate-200"
                      />
                    </div>
                  ) : (
                    <div>
                      <label className="block text-[11px] text-slate-400 mb-1">
                        Prompt / Transform Template (supports {'{{workflow.input.x}}'} and {'{{steps.step_1.output}}'})
                      </label>
                      <textarea
                        rows={2}
                        value={step.prompt_template}
                        onChange={(e) => {
                          const copy = [...wfSteps];
                          copy[index] = { ...step, prompt_template: e.target.value };
                          setWfSteps(copy);
                        }}
                        className="w-full px-2.5 py-1.5 rounded bg-midnight-950 border border-slate-800 text-xs text-slate-200"
                      />
                    </div>
                  )}

                  <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-slate-800/60 text-xs">
                    <label className="flex items-center gap-2 text-amber-300">
                      <input
                        type="checkbox"
                        checked={step.requires_approval}
                        onChange={(e) => {
                          const copy = [...wfSteps];
                          copy[index] = { ...step, requires_approval: e.target.checked };
                          setWfSteps(copy);
                        }}
                      />
                      <span>Require explicit user approval before executing this step</span>
                    </label>
                    <div className="text-[11px] text-slate-400">
                      Depends on: {step.depends_on.length > 0 ? step.depends_on.join(', ') : 'None (Root Step)'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'runs' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Run History List */}
            <div className="p-4 rounded-xl bg-midnight-900/70 border border-slate-800/80 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Execution History ({filteredRuns.length})
                </span>
                <select
                  value={runStatusFilter}
                  onChange={(e) => setRunStatusFilter(e.target.value)}
                  className="px-2 py-1 rounded bg-midnight-950 border border-slate-800 text-[11px] text-slate-200"
                >
                  <option value="ALL">All States</option>
                  <option value="WAITING_FOR_APPROVAL">WAITING_FOR_APPROVAL</option>
                  <option value="RUNNING">RUNNING</option>
                  <option value="SUCCEEDED">SUCCEEDED</option>
                  <option value="FAILED">FAILED</option>
                  <option value="CANCELLED">CANCELLED</option>
                </select>
              </div>

              {filteredRuns.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-500">
                  No workflow runs recorded yet. Trigger a workflow from the Dashboard tab.
                </div>
              ) : (
                <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                  {filteredRuns.map((r) => (
                    <button
                      key={r.run_id}
                      onClick={() => setSelectedRun(r)}
                      className={`w-full text-left p-3 rounded-xl border transition-all ${
                        selectedRun?.run_id === r.run_id
                          ? 'bg-cyan-950/30 border-cyan-500/50'
                          : 'bg-midnight-950/80 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-semibold text-slate-100 truncate">
                          {r.workflow_name}
                        </span>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${statusBadgeColor(
                            r.status
                          )}`}
                        >
                          {r.status}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1.5">
                        <span>
                          {r.completed_steps}/{r.total_steps} steps ({r.progress_percent}%)
                        </span>
                        <span>{r.duration_ms.toFixed(0)} ms</span>
                      </div>
                      <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden mt-1.5">
                        <div
                          className="h-full bg-gradient-to-r from-cyan-400 to-violet-500"
                          style={{ width: `${Math.min(100, r.progress_percent)}%` }}
                        />
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Right: Run Detail & Step Inspector */}
            <div className="lg:col-span-2 p-5 rounded-xl bg-midnight-900/70 border border-slate-800/80 space-y-4">
              {!selectedRun ? (
                <div className="p-12 text-center text-xs text-slate-500">
                  Select a workflow execution run on the left to inspect step results, logs, and approval gates.
                </div>
              ) : (
                <>
                  <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-800 pb-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-base font-bold text-slate-100">
                          {selectedRun.workflow_name}
                        </h2>
                        <span
                          className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${statusBadgeColor(
                            selectedRun.status
                          )}`}
                        >
                          {selectedRun.status}
                        </span>
                        {selectedRun.is_dry_run && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-violet-500/20 text-violet-300">
                            DRY-RUN
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-400 mt-1">
                        Run ID: <code className="text-slate-300">{selectedRun.run_id}</code> • Trigger:{' '}
                        <span className="text-slate-300">{selectedRun.trigger_source}</span> • Est. Cost:{' '}
                        <span className="text-cyan-300">
                          ${selectedRun.total_estimated_cost_usd.toFixed(4)} / $
                          {selectedRun.max_cost_budget_usd.toFixed(2)}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {(selectedRun.status === 'FAILED' || selectedRun.status === 'CANCELLED') && (
                        <button
                          onClick={() => handleRetryRun(selectedRun.run_id)}
                          disabled={isLoading}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/30"
                        >
                          <RefreshCw className="w-3.5 h-3.5" />
                          <span>Retry Failed Steps</span>
                        </button>
                      )}
                      {['QUEUED', 'RUNNING', 'RETRYING', 'WAITING_FOR_APPROVAL'].includes(
                        selectedRun.status
                      ) && (
                        <button
                          onClick={() => handleCancelRun(selectedRun.run_id)}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/30"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          <span>Cancel Run</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Step Results Timeline */}
                  <div className="space-y-3">
                    {selectedRun.step_results.map((sr, idx) => (
                      <div
                        key={sr.step_id}
                        className="p-4 rounded-xl bg-midnight-950/90 border border-slate-800 space-y-2"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-slate-400">#{idx + 1}</span>
                            {sr.action_type === 'agent' ? (
                              <Sparkles className="w-3.5 h-3.5 text-violet-400" />
                            ) : (
                              <Wrench className="w-3.5 h-3.5 text-cyan-400" />
                            )}
                            <span className="text-xs font-bold text-slate-100">{sr.step_name}</span>
                            <span className="text-[11px] text-slate-400">
                              ({sr.action_type === 'agent' ? sr.agent_id : sr.tool_name || sr.action_type})
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            {sr.attempt_count > 1 && (
                              <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/15 text-amber-300">
                                Attempts: {sr.attempt_count}/{sr.max_retries + 1}
                              </span>
                            )}
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${statusBadgeColor(
                                sr.status
                              )}`}
                            >
                              {sr.status}
                            </span>
                          </div>
                        </div>

                        {sr.condition_detail && (
                          <div className="text-[11px] text-slate-400">
                            Condition: <span className="text-slate-300">{sr.condition_detail}</span>
                          </div>
                        )}

                        {/* Approval Gate Controls */}
                        {sr.status === 'WAITING_FOR_APPROVAL' && (
                          <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-500/40 flex flex-wrap items-center justify-between gap-3">
                            <div className="flex items-center gap-2 text-xs text-amber-200">
                              <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
                              <span>
                                {sr.approval_reason ||
                                  'Consequential action requires explicit user approval before execution.'}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleApproveStep(selectedRun.run_id, sr.step_id, true)}
                                disabled={isLoading}
                                className="flex items-center gap-1 px-3 py-1 rounded-md text-xs font-semibold bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40"
                              >
                                <Check className="w-3.5 h-3.5" />
                                <span>Approve & Resume</span>
                              </button>
                              <button
                                onClick={() => handleApproveStep(selectedRun.run_id, sr.step_id, false)}
                                disabled={isLoading}
                                className="flex items-center gap-1 px-3 py-1 rounded-md text-xs font-semibold bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/40"
                              >
                                <X className="w-3.5 h-3.5" />
                                <span>Reject</span>
                              </button>
                            </div>
                          </div>
                        )}

                        {sr.output_summary && (
                          <div className="p-2.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs text-slate-200 whitespace-pre-wrap">
                            {sr.output_summary}
                          </div>
                        )}

                        {sr.error_message && (
                          <div className="p-2.5 rounded-lg bg-red-950/40 border border-red-500/30 text-xs text-red-300">
                            {sr.error_message}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {activeTab === 'notifications' && (
          <div className="max-w-4xl mx-auto p-5 rounded-xl bg-midnight-900/70 border border-slate-800/80 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-100">
                  Workflow Notification Center ({notifications.length})
                </h2>
                <p className="text-xs text-slate-400">
                  Tracks workflow completions, failures, approval requests, and verified external delivery status.
                </p>
              </div>
              {unreadCount > 0 && (
                <button
                  onClick={async () => {
                    await api.markAllWorkflowNotificationsRead();
                    await loadAll();
                  }}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-cyan-300"
                >
                  Mark All Read ({unreadCount})
                </button>
              )}
            </div>

            {notifications.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No workflow notifications yet.
              </div>
            ) : (
              <div className="space-y-2.5">
                {notifications.map((n) => (
                  <div
                    key={n.notification_id}
                    className={`p-3.5 rounded-xl border flex items-start justify-between gap-4 ${
                      n.read
                        ? 'bg-midnight-950/50 border-slate-800/70 text-slate-400'
                        : 'bg-midnight-950 border-cyan-500/30 text-slate-100'
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold">{n.title}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
                          {n.event_type}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-cyan-300">
                          Delivery: {n.external_delivery_status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300">{n.message}</p>
                      <div className="text-[10px] text-slate-500">
                        {new Date(n.created_at).toLocaleString()}
                      </div>
                    </div>
                    {!n.read && (
                      <button
                        onClick={async () => {
                          await api.markWorkflowNotificationRead(n.notification_id);
                          await loadAll();
                        }}
                        className="px-2.5 py-1 rounded text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-200 shrink-0"
                      >
                        Mark Read
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
