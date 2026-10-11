import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Play,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Clock,
  XCircle,
  RefreshCw,
  Edit3,
  ChevronDown,
  ChevronRight,
  Wrench,
  GitBranch,
  Sparkles,
  Lock,
  Check,
  X,
  FileText,
} from 'lucide-react';
import { api } from '../../services/api';
import { useChat } from '../../context/ChatContext';
import { ReasoningPlan, ReasoningSubtask, ToolDefinitionItem, SubtaskStatus } from '../../types';

const PRESET_EXAMPLES = [
  {
    label: 'Multi-Step Math + Vault',
    badge: 'Complex • 2 Tools',
    query: 'First calculate (450 * 12) + sqrt(625) and then check my uploaded document for budget notes.',
  },
  {
    label: 'Web Search + Tamil Translation',
    badge: 'Complex • Multi-Tool',
    query: 'Search the web for latest AI semiconductor efficiency updates and translate the summary in Tamil.',
  },
  {
    label: 'Simple Direct Query',
    badge: 'Simple • 0 Overhead',
    query: 'What is the difference between TCP and UDP protocols?',
  },
  {
    label: 'Consequential Action (Approval Gate)',
    badge: 'High Risk • Approval Required',
    query: 'Please delete document doc_temp_archive from the document vault.',
  },
];

const statusBadgeStyle = (status: SubtaskStatus | string) => {
  switch (status) {
    case 'COMPLETE':
      return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
    case 'IN PROGRESS':
      return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30 animate-pulse';
    case 'REVIEWING':
      return 'bg-violet-500/15 text-violet-300 border-violet-500/30';
    case 'BLOCKED':
      return 'bg-amber-500/15 text-amber-300 border-amber-500/40';
    case 'CANCELLED':
    case 'FAILED':
      return 'bg-red-500/15 text-red-300 border-red-500/30';
    default:
      return 'bg-slate-800/80 text-slate-300 border-slate-700';
  }
};

export const ReasoningStudio: React.FC = () => {
  const { settings, showToast } = useChat();
  const [query, setQuery] = useState('');
  const [autoExecute, setAutoExecute] = useState(true);
  const [forcePlan, setForcePlan] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [activePlan, setActivePlan] = useState<ReasoningPlan | null>(null);
  const [planHistory, setPlanHistory] = useState<ReasoningPlan[]>([]);
  const [registeredTools, setRegisteredTools] = useState<ToolDefinitionItem[]>([]);

  const [isRevising, setIsRevising] = useState(false);
  const [revisedGoalText, setRevisedGoalText] = useState('');
  const [approvalNote, setApprovalNote] = useState('');
  const [showExecutionSummary, setShowExecutionSummary] = useState(true);
  const [showToolRegistry, setShowToolRegistry] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [plans, tools] = await Promise.all([
        api.getReasoningPlans(),
        api.getRegisteredTools(),
      ]);
      setPlanHistory(plans);
      if (plans.length > 0 && !activePlan) {
        setActivePlan(plans[0]);
      }
      setRegisteredTools(tools);
    } catch {
      // Quiet fallback if backend not yet polled
    }
  };

  const refreshHistory = async (updatedPlan?: ReasoningPlan) => {
    if (updatedPlan) {
      setActivePlan(updatedPlan);
      setRevisedGoalText(updatedPlan.query);
    }
    try {
      const plans = await api.getReasoningPlans();
      setPlanHistory(plans);
    } catch {
      // ignore
    }
  };

  const handleAnalyze = async (e?: React.FormEvent, customQuery?: string) => {
    if (e) e.preventDefault();
    const targetQuery = (customQuery ?? query).trim();
    if (!targetQuery) {
      showToast('Please enter a problem or task to analyze.', 'error');
      return;
    }

    setIsSubmitting(true);
    try {
      const plan = await api.analyzeReasoning(
        {
          query: targetQuery,
          auto_execute: autoExecute,
          force_plan: forcePlan,
          max_retries: 2,
        },
        settings
      );
      await refreshHistory(plan);
      if (plan.status === 'BLOCKED') {
        showToast('Plan paused in BLOCKED state — user approval or clarification required.', 'info');
      } else if (plan.status === 'COMPLETE') {
        showToast(
          plan.classification.requires_planning
            ? 'Multi-step reasoning plan executed and verified!'
            : 'Simple query answered directly without planning overhead.',
          'success'
        );
      } else {
        showToast('Execution plan generated in PLANNED state.', 'info');
      }
    } catch (err: any) {
      showToast(err.message || 'Failed to analyze task.', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExecutePlan = async () => {
    if (!activePlan) return;
    setIsSubmitting(true);
    try {
      const updated = await api.executeReasoningPlan(activePlan.id);
      await refreshHistory(updated);
      showToast(`Plan status: ${updated.status}`, 'success');
    } catch (err: any) {
      showToast(err.message || 'Execution failed.', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleApproval = async (subtask: ReasoningSubtask, approved: boolean) => {
    if (!activePlan) return;
    setIsSubmitting(true);
    try {
      const updated = await api.approveReasoningSubtask(
        activePlan.id,
        {
          subtask_id: subtask.id,
          approved,
          user_note: approvalNote || undefined,
          auto_resume: true,
        },
        settings
      );
      setApprovalNote('');
      await refreshHistory(updated);
      showToast(
        approved
          ? `Approved '${subtask.title}' and resumed execution.`
          : `Denied '${subtask.title}' and cancelled plan.`,
        approved ? 'success' : 'info'
      );
    } catch (err: any) {
      showToast(err.message || 'Approval update failed.', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevisePlan = async () => {
    if (!activePlan || !revisedGoalText.trim()) return;
    setIsSubmitting(true);
    try {
      const updated = await api.reviseReasoningPlan(
        activePlan.id,
        {
          revised_goal: revisedGoalText.trim(),
          auto_execute: true,
        },
        settings
      );
      setIsRevising(false);
      await refreshHistory(updated);
      showToast('Plan revised and re-executed!', 'success');
    } catch (err: any) {
      showToast(err.message || 'Revision failed.', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelPlan = async () => {
    if (!activePlan) return;
    setIsSubmitting(true);
    try {
      const updated = await api.cancelReasoningPlan(activePlan.id);
      await refreshHistory(updated);
      showToast('Reasoning plan cancelled.', 'info');
    } catch (err: any) {
      showToast(err.message || 'Failed to cancel plan.', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto bg-midnight-950 text-slate-100 p-4 sm:p-6">
      <div className="max-w-6xl w-full mx-auto space-y-6">
        {/* Studio Header Banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-gradient-to-r from-midnight-900 via-slate-900/90 to-midnight-900 border border-slate-800/80 shadow-xl">
          <div className="flex items-start gap-3.5">
            <div className="p-3 rounded-xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-400 shrink-0">
              <Cpu className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg sm:text-xl font-bold text-white">
                  Stage 11: Advanced Reasoning & Task-Planning Engine
                </h1>
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                  Adaptive Decomposition
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-400 mt-1">
                Classifies complexity, answers simple queries directly, decomposes complex tasks into dependency-tracked subtasks, executes verified tools, and enforces explicit user approval on high-risk actions.
              </p>
            </div>
          </div>

          <button
            onClick={() => setShowToolRegistry(!showToolRegistry)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800/80 hover:bg-slate-800 text-slate-200 border border-slate-700 transition-colors self-start md:self-center shrink-0"
          >
            <Wrench className="w-4 h-4 text-cyan-400" />
            <span>Tool Registry ({registeredTools.length})</span>
            {showToolRegistry ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Collapsible Registered Tool Registry Drawer */}
        {showToolRegistry && (
          <div className="p-4 rounded-2xl bg-midnight-900/80 border border-slate-800/80 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <Wrench className="w-3.5 h-3.5 text-cyan-400" />
                Registered NEXORA Tools (Least-Privilege & Quarantine Policy)
              </h2>
              <span className="text-xs text-slate-500">All external outputs wrapped in &lt;untrusted_tool_output&gt;</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {registeredTools.map((tool) => (
                <div
                  key={tool.name}
                  className="p-3 rounded-xl bg-midnight-950/90 border border-slate-800/80 flex flex-col justify-between gap-2"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs font-bold text-cyan-300">{tool.name}</span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                          tool.requires_approval
                            ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                            : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                        }`}
                      >
                        {tool.requires_approval ? 'Approval Required' : `Risk: ${tool.risk_level}`}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">{tool.description}</p>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-900">
                    <span>Stage {tool.stage_introduced}</span>
                    <span>Timeout: {tool.timeout_seconds}s</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Problem Input & Adaptive Decomposition Form */}
        <form
          onSubmit={(e) => handleAnalyze(e)}
          className="p-5 rounded-2xl bg-midnight-900/90 border border-slate-800/80 space-y-4 shadow-lg"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Task or Problem Statement
            </label>
            <div className="flex items-center gap-4 text-xs text-slate-300">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoExecute}
                  onChange={(e) => setAutoExecute(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-cyan-500"
                />
                <span>Auto-Execute Plan</span>
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={forcePlan}
                  onChange={(e) => setForcePlan(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-cyan-500"
                />
                <span>Force Multi-Step Plan</span>
              </label>
            </div>
          </div>

          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={3}
            placeholder="Ask a simple question or describe a multi-step problem (e.g., 'First calculate (450 * 12) + sqrt(625) and then check my uploaded document for budget notes')..."
            className="w-full rounded-xl bg-midnight-950 border border-slate-800 focus:border-cyan-500/60 focus:outline-none p-3.5 text-sm text-slate-100 placeholder-slate-500 resize-none"
          />

          {/* Quick Preset Scenarios */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-400 mr-1">Try Scenario:</span>
            {PRESET_EXAMPLES.map((preset) => (
              <button
                key={preset.label}
                type="button"
                onClick={() => {
                  setQuery(preset.query);
                  handleAnalyze(undefined, preset.query);
                }}
                className="text-xs px-2.5 py-1.5 rounded-lg bg-slate-800/70 hover:bg-slate-800 text-slate-300 hover:text-cyan-300 border border-slate-700/70 transition-all flex items-center gap-1.5"
              >
                <span>{preset.label}</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-900 text-cyan-400">
                  {preset.badge}
                </span>
              </button>
            ))}
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isSubmitting || !query.trim()}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-cyan-500 to-violet-600 hover:from-cyan-400 hover:to-violet-500 text-white shadow-cyan-glow disabled:opacity-50 transition-all"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Decomposing & Executing...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Analyze & Solve</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Main Workspace Split: Active Plan Inspector + Plan History */}
        {activePlan && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left 2 Columns: Active Plan Decomposition, Subtasks & Synthesis */}
            <div className="lg:col-span-2 space-y-5">
              {/* Plan Status & Classification Card */}
              <div className="p-5 rounded-2xl bg-midnight-900/90 border border-slate-800/80 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`text-xs font-bold px-3 py-1 rounded-full border ${statusBadgeStyle(
                        activePlan.status
                      )}`}
                    >
                      {activePlan.status}
                    </span>
                    <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700 capitalize">
                      Complexity: <strong>{activePlan.classification.complexity}</strong>
                    </span>
                    <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700 capitalize">
                      Risk: <strong>{activePlan.classification.risk_level}</strong>
                    </span>
                    <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                      Tool Calls: <strong>{activePlan.total_tool_calls}</strong>
                    </span>
                  </div>

                  {/* Plan Action Buttons: Execute, Revise, Cancel */}
                  <div className="flex items-center gap-2">
                    {activePlan.status === 'PLANNED' && (
                      <button
                        onClick={handleExecutePlan}
                        disabled={isSubmitting}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 transition-all"
                      >
                        <Play className="w-3.5 h-3.5" />
                        <span>Execute Plan</span>
                      </button>
                    )}
                    <button
                      onClick={() => {
                        setRevisedGoalText(activePlan.query);
                        setIsRevising(!isRevising);
                      }}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span>Revise</span>
                    </button>
                    {activePlan.status !== 'COMPLETE' && activePlan.status !== 'CANCELLED' && (
                      <button
                        onClick={handleCancelPlan}
                        disabled={isSubmitting}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-500/15 hover:bg-red-500/25 text-red-300 border border-red-500/30 transition-all"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Cancel</span>
                      </button>
                    )}
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-white">{activePlan.query}</h3>
                  <p className="text-xs text-slate-400 mt-1">{activePlan.classification.rationale}</p>
                </div>

                {/* Revise Plan Inline Editor */}
                {isRevising && (
                  <div className="p-3.5 rounded-xl bg-midnight-950 border border-cyan-500/40 space-y-2.5">
                    <label className="text-xs font-semibold text-cyan-300">
                      Revise Goal or Provide Missing Clarification:
                    </label>
                    <input
                      type="text"
                      value={revisedGoalText}
                      onChange={(e) => setRevisedGoalText(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg bg-midnight-900 border border-slate-700 text-sm text-white"
                    />
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => setIsRevising(false)}
                        className="px-3 py-1 rounded-lg text-xs text-slate-400 hover:text-white"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={handleRevisePlan}
                        disabled={isSubmitting}
                        className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-cyan-500 text-slate-950 hover:bg-cyan-400"
                      >
                        Save & Re-Execute Plan
                      </button>
                    </div>
                  </div>
                )}

                {/* Assumptions & Uncertainty Notes */}
                {(activePlan.assumptions.length > 0 || activePlan.uncertainty_notes.length > 0) && (
                  <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800 text-xs space-y-1">
                    {activePlan.assumptions.map((a, i) => (
                      <div key={i} className="text-slate-300 flex items-center gap-2">
                        <span className="text-cyan-400 font-semibold">Assumption:</span> {a}
                      </div>
                    ))}
                    {activePlan.uncertainty_notes.map((u, i) => (
                      <div key={i} className="text-amber-300 flex items-center gap-2">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                        <span>{u}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Subtask Execution Pipeline */}
              {activePlan.subtasks.length > 0 ? (
                <div className="p-5 rounded-2xl bg-midnight-900/90 border border-slate-800/80 space-y-4">
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                    <GitBranch className="w-4 h-4 text-cyan-400" />
                    Execution Subtasks & Tool Verification ({activePlan.subtasks.length} Steps)
                  </h2>

                  <div className="space-y-3">
                    {activePlan.subtasks.map((subtask) => (
                      <div
                        key={subtask.id}
                        className={`p-4 rounded-xl border transition-all ${
                          subtask.status === 'BLOCKED'
                            ? 'bg-amber-950/20 border-amber-500/40'
                            : 'bg-midnight-950/90 border-slate-800/80'
                        }`}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2.5">
                            <span className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 text-xs font-bold flex items-center justify-center text-cyan-300">
                              {subtask.step_number}
                            </span>
                            <span className="font-semibold text-sm text-white">{subtask.title}</span>
                            {subtask.tool_name && (
                              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                                tool:{subtask.tool_name}
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-2">
                            {subtask.depends_on.length > 0 && (
                              <span className="text-[11px] text-slate-500">
                                Depends on: {subtask.depends_on.join(', ')}
                              </span>
                            )}
                            <span
                              className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${statusBadgeStyle(
                                subtask.status
                              )}`}
                            >
                              {subtask.status}
                            </span>
                          </div>
                        </div>

                        <p className="text-xs text-slate-400 mt-1.5">{subtask.description}</p>

                        {/* Expected Output & Completion Criteria */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2.5 text-[11px] text-slate-400 bg-slate-900/50 p-2.5 rounded-lg border border-slate-800/60">
                          <div>
                            <span className="text-slate-500 font-semibold">Expected Output: </span>
                            {subtask.expected_output}
                          </div>
                          <div>
                            <span className="text-slate-500 font-semibold">Criteria: </span>
                            {subtask.completion_criteria}
                          </div>
                        </div>

                        {/* Approval Gate UI if BLOCKED on consequential action */}
                        {subtask.status === 'BLOCKED' && subtask.requires_approval && (
                          <div className="mt-3 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-2.5">
                            <div className="flex items-center gap-2 text-xs font-bold text-amber-300">
                              <ShieldAlert className="w-4 h-4" />
                              <span>Explicit User Approval Required (Least-Privilege Safety Gate)</span>
                            </div>
                            <p className="text-xs text-amber-200/90">
                              {subtask.approval_reason || subtask.error_message}
                            </p>
                            <div className="flex flex-wrap items-center gap-2 pt-1">
                              <input
                                type="text"
                                value={approvalNote}
                                onChange={(e) => setApprovalNote(e.target.value)}
                                placeholder="Optional authorization note..."
                                className="flex-1 min-w-[180px] px-2.5 py-1.5 rounded-lg bg-midnight-950 border border-amber-500/30 text-xs text-white"
                              />
                              <button
                                onClick={() => handleApproval(subtask, true)}
                                disabled={isSubmitting}
                                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-all"
                              >
                                <Check className="w-3.5 h-3.5" />
                                <span>Approve & Execute</span>
                              </button>
                              <button
                                onClick={() => handleApproval(subtask, false)}
                                disabled={isSubmitting}
                                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold bg-red-500/20 text-red-300 border border-red-500/30 hover:bg-red-500/30 transition-all"
                              >
                                <X className="w-3.5 h-3.5" />
                                <span>Deny & Cancel</span>
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Tool Executions Log */}
                        {subtask.tool_executions.length > 0 && (
                          <div className="mt-3 space-y-1.5">
                            {subtask.tool_executions.map((exec, idx) => (
                              <div
                                key={idx}
                                className="p-2.5 rounded-lg bg-midnight-900 border border-slate-800 text-xs space-y-1"
                              >
                                <div className="flex items-center justify-between text-[11px]">
                                  <span className="font-mono text-cyan-300">
                                    Attempt #{exec.attempt} • {exec.tool_name}({JSON.stringify(exec.inputs)})
                                  </span>
                                  <span className="text-slate-400 flex items-center gap-2">
                                    {exec.untrusted_content_quarantined && (
                                      <span className="inline-flex items-center gap-1 text-[10px] text-violet-300">
                                        <Lock className="w-3 h-3" /> Quarantined
                                      </span>
                                    )}
                                    <span>{exec.duration_ms}ms</span>
                                  </span>
                                </div>
                                <div className="text-slate-200 whitespace-pre-wrap font-mono text-[11px]">
                                  {exec.output_summary}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Verification Badge */}
                        {subtask.verification_note && (
                          <div className="mt-2.5 flex items-center gap-1.5 text-xs text-emerald-300">
                            <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                            <span>{subtask.verification_note}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-2xl bg-midnight-900/70 border border-slate-800 text-xs text-slate-300 flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>
                    <strong>Adaptive Direct Mode:</strong> This request was classified as simple and answered directly without unnecessary planning overhead.
                  </span>
                </div>
              )}

              {/* Final Synthesized Answer Card */}
              {activePlan.final_answer && (
                <div className="p-5 rounded-2xl bg-midnight-900/90 border border-cyan-500/30 space-y-3 shadow-lg">
                  <div className="flex items-center justify-between">
                    <h2 className="text-xs font-bold uppercase tracking-wider text-cyan-300 flex items-center gap-2">
                      <Sparkles className="w-4 h-4" />
                      Verified Final Response
                    </h2>
                    <span className="text-[11px] text-slate-400">
                      {activePlan.provider} • {activePlan.model}
                    </span>
                  </div>
                  <div className="text-sm text-slate-100 whitespace-pre-wrap leading-relaxed">
                    {activePlan.final_answer}
                  </div>

                  {/* Expandable Execution Summary */}
                  {activePlan.execution_summary && (
                    <div className="pt-3 border-t border-slate-800">
                      <button
                        onClick={() => setShowExecutionSummary(!showExecutionSummary)}
                        className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-cyan-300"
                      >
                        {showExecutionSummary ? (
                          <ChevronDown className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5" />
                        )}
                        <span>Execution Summary & Audit Log</span>
                      </button>
                      {showExecutionSummary && (
                        <pre className="mt-2 p-3 rounded-xl bg-midnight-950 border border-slate-800 text-xs text-slate-300 whitespace-pre-wrap font-mono">
                          {activePlan.execution_summary}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Right Column: Recent Reasoning Plans History */}
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-midnight-900/90 border border-slate-800/80 space-y-3">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-cyan-400" />
                  Reasoning Plan History ({planHistory.length})
                </h2>

                {planHistory.length === 0 ? (
                  <p className="text-xs text-slate-500 py-4 text-center">
                    No plans created yet. Run a scenario above to inspect adaptive decomposition.
                  </p>
                ) : (
                  <div className="space-y-2 max-h-[540px] overflow-y-auto pr-1">
                    {planHistory.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => {
                          setActivePlan(item);
                          setRevisedGoalText(item.query);
                        }}
                        className={`w-full text-left p-3 rounded-xl border transition-all space-y-1.5 ${
                          activePlan?.id === item.id
                            ? 'bg-cyan-500/10 border-cyan-500/40'
                            : 'bg-midnight-950/70 border-slate-800/80 hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${statusBadgeStyle(
                              item.status
                            )}`}
                          >
                            {item.status}
                          </span>
                          <span className="text-[10px] text-slate-500 capitalize">
                            {item.classification.complexity} • {item.subtasks.length} step(s)
                          </span>
                        </div>
                        <p className="text-xs text-slate-200 font-medium line-clamp-2">{item.query}</p>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Revision Audit Trail */}
              {activePlan.revision_history.length > 0 && (
                <div className="p-4 rounded-2xl bg-midnight-900/90 border border-slate-800/80 space-y-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-violet-400" />
                    Revision & Approval Trail
                  </h3>
                  <ul className="space-y-1.5 text-xs text-slate-300">
                    {activePlan.revision_history.map((rev, i) => (
                      <li key={i} className="p-2 rounded-lg bg-midnight-950 border border-slate-800">
                        {rev}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
