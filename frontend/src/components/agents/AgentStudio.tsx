import React, { useState, useEffect } from 'react';
import {
  Users,
  Play,
  RotateCcw,
  XCircle,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Sparkles,
  Layers,
  Lock,
  ExternalLink,
  FileText,
  DollarSign,
  Clock,
  Wrench,
  HelpCircle,
} from 'lucide-react';
import { api } from '../../services/api';
import { useChat } from '../../context/ChatContext';
import {
  AgentRoleId,
  SpecializedAgentSpec,
  MultiAgentOrchestrationRun,
} from '../../types';

export const AgentStudio: React.FC = () => {
  const { settings, selectedDocumentIds } = useChat();
  const [agents, setAgents] = useState<SpecializedAgentSpec[]>([]);
  const [goal, setGoal] = useState('');
  const [selectionMode, setSelectionMode] = useState<'auto' | 'manual'>('auto');
  const [manualAgents, setManualAgents] = useState<AgentRoleId[]>(['research_agent', 'coding_agent']);
  const [allowParallel, setAllowParallel] = useState(true);
  const [maxCostUsd, setMaxCostUsd] = useState(0.25);
  const [targetLanguage, setTargetLanguage] = useState('en');
  const [activeRun, setActiveRun] = useState<MultiAgentOrchestrationRun | null>(null);
  const [recentRuns, setRecentRuns] = useState<MultiAgentOrchestrationRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRegistryAndRuns = async () => {
    try {
      const [reg, runs] = await Promise.all([
        api.getAgentRegistry(),
        api.getMultiAgentRuns('default_user'),
      ]);
      setAgents(reg);
      setRecentRuns(runs);
      if (!activeRun && runs.length > 0) {
        setActiveRun(runs[0]);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load Multi-Agent Registry.');
    }
  };

  useEffect(() => {
    loadRegistryAndRuns();
  }, []);

  const toggleManualAgent = (agentId: AgentRoleId) => {
    setManualAgents((prev) =>
      prev.includes(agentId) ? prev.filter((id) => id !== agentId) : [...prev, agentId]
    );
  };

  const handleRunOrchestrator = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const run = await api.executeMultiAgentRun(
        {
          goal: goal.trim(),
          user_id: 'default_user',
          selection_mode: selectionMode,
          manual_agents: selectionMode === 'manual' ? manualAgents : [],
          document_ids: selectedDocumentIds,
          target_language: targetLanguage,
          allow_parallel: allowParallel,
          max_cost_usd: maxCostUsd,
          memory_enabled: true,
        },
        settings
      );
      setActiveRun(run);
      await loadRegistryAndRuns();
    } catch (err: any) {
      setError(err?.message || 'Multi-agent orchestration failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveSubtask = async (subtaskId: string, approved: boolean) => {
    if (!activeRun) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await api.approveMultiAgentSubtask(
        activeRun.run_id,
        {
          subtask_id: subtaskId,
          approved,
          user_note: approved ? 'Approved via Agent Workspace' : 'Declined by user',
        },
        settings
      );
      setActiveRun(updated);
      await loadRegistryAndRuns();
    } catch (err: any) {
      setError(err?.message || 'Failed to process approval decision.');
    } finally {
      setLoading(false);
    }
  };

  const handleRetryRun = async (subtaskId?: string) => {
    if (!activeRun) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await api.retryMultiAgentRun(activeRun.run_id, subtaskId, settings);
      setActiveRun(updated);
      await loadRegistryAndRuns();
    } catch (err: any) {
      setError(err?.message || 'Retry failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleCancelRun = async () => {
    if (!activeRun) return;
    try {
      const updated = await api.cancelMultiAgentRun(activeRun.run_id);
      setActiveRun(updated);
      await loadRegistryAndRuns();
    } catch (err: any) {
      setError(err?.message || 'Cancellation failed.');
    }
  };

  const statusBadge = (st: string) => {
    switch (st) {
      case 'COMPLETED':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
      case 'WAITING_APPROVAL':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 'FAILED':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/40';
      case 'CANCELLED':
        return 'bg-slate-700/60 text-slate-300 border-slate-600';
      default:
        return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-slate-950 text-slate-100 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/90 border border-slate-800 rounded-2xl p-5">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-violet-500/15 border border-violet-500/30 text-violet-400">
                <Users className="w-5 h-5" />
              </div>
              <h1 className="text-xl font-bold text-white">
                Stage 14: Multi-Agent Intelligence System & Orchestrator
              </h1>
              <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-violet-500/15 text-violet-300 border border-violet-500/30">
                8 Specialized Agents
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Coordinate specialized agents with least-privilege permissions, tool deduplication, parallel execution,
              and explicit separation of facts, assumptions, and unresolved questions.
            </p>
          </div>
        </div>

        {/* Specialized Agent Registry Grid */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-violet-400" />
              Specialized Agent Registry (Click in Manual Mode to Select/Deselect)
            </h2>
            <span className="text-xs text-slate-400">
              {agents.filter((a) => a.available).length} / {agents.length} Agents Ready
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {agents.map((agent) => {
              const isSelectedManual =
                selectionMode === 'manual' && manualAgents.includes(agent.agent_id);
              const isUsedInActiveRun = activeRun?.selected_agents.includes(agent.agent_id);
              return (
                <div
                  key={agent.agent_id}
                  onClick={() => selectionMode === 'manual' && toggleManualAgent(agent.agent_id)}
                  className={`rounded-2xl border p-4 transition-all ${
                    selectionMode === 'manual' ? 'cursor-pointer' : ''
                  } ${
                    isSelectedManual
                      ? 'bg-violet-500/15 border-violet-500/50'
                      : isUsedInActiveRun
                      ? 'bg-cyan-500/10 border-cyan-500/40'
                      : 'bg-slate-900/75 border-slate-800/90 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="text-xs font-bold text-white">{agent.name}</span>
                    <span
                      className={`px-2 py-0.5 text-[10px] rounded-full font-semibold ${
                        agent.available
                          ? 'bg-emerald-500/15 text-emerald-300'
                          : 'bg-rose-500/20 text-rose-300'
                      }`}
                    >
                      {agent.available ? 'READY' : 'UNAVAILABLE'}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-snug mb-2.5">{agent.purpose}</p>
                  <div className="flex flex-wrap gap-1 mt-auto">
                    <span className="px-1.5 py-0.5 text-[10px] rounded bg-slate-950 text-slate-300 border border-slate-800 flex items-center gap-1">
                      <Lock className="w-2.5 h-2.5 text-violet-400" />
                      {agent.permission_scope}
                    </span>
                    {agent.allowed_tools.map((t) => (
                      <span
                        key={t}
                        className="px-1.5 py-0.5 text-[10px] rounded bg-indigo-500/15 text-indigo-300"
                      >
                        tool:{t}
                      </span>
                    ))}
                  </div>
                  {!agent.available && agent.unavailable_reason && (
                    <div className="mt-2 text-[10px] text-rose-300 bg-rose-950/40 p-1.5 rounded">
                      {agent.unavailable_reason}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Orchestrator Launcher Form */}
        <form
          onSubmit={handleRunOrchestrator}
          className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-4"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-violet-400" />
              <span className="text-sm font-semibold text-white">
                Multi-Agent Task Orchestration Console
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {[
                'Implement a Python algorithm, calculate 120 * 15 + 40, and explain the concept as a study guide',
                'Research renewable energy storage trends, analyze 450 * 1.25, and draft an executive summary',
                'Organize a sprint launch checklist and publish publicly to external stakeholders',
              ].map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setGoal(preset)}
                  className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                >
                  "{preset.slice(0, 38)}..."
                </button>
              ))}
            </div>
          </div>

          <textarea
            rows={2}
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="Describe a complex multi-step task (e.g., research sources, write code, analyze data, draft study materials, or translate)..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500"
            required
          />

          <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
            <div className="flex flex-wrap items-center gap-4">
              {/* Auto vs Manual */}
              <div className="flex items-center gap-1.5 bg-slate-950 border border-slate-800 rounded-xl p-1">
                <button
                  type="button"
                  onClick={() => setSelectionMode('auto')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold ${
                    selectionMode === 'auto'
                      ? 'bg-violet-600 text-white'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Auto-Select Agents
                </button>
                <button
                  type="button"
                  onClick={() => setSelectionMode('manual')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold ${
                    selectionMode === 'manual'
                      ? 'bg-violet-600 text-white'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Manual Selection ({manualAgents.length})
                </button>
              </div>

              {/* Parallel Toggle */}
              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={allowParallel}
                  onChange={(e) => setAllowParallel(e.target.checked)}
                  className="rounded border-slate-700"
                />
                <span>Parallel Execution (Safe Independent Tasks)</span>
              </label>

              {/* Cost Cap */}
              <div className="flex items-center gap-2 text-xs text-slate-300">
                <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
                <span>Max Budget:</span>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max="5.00"
                  value={maxCostUsd}
                  onChange={(e) => setMaxCostUsd( parseFloat(e.target.value) || 0.25 )}
                  className="w-20 bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-white"
                />
                <span className="text-slate-500">USD</span>
              </div>

              {/* Target Language */}
              <div className="flex items-center gap-1.5 text-xs text-slate-300">
                <span>Language:</span>
                <select
                  value={targetLanguage}
                  onChange={(e) => setTargetLanguage(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-white"
                >
                  <option value="en">English (en)</option>
                  <option value="ta">Tamil (ta)</option>
                  <option value="hi">Hindi (hi)</option>
                  <option value="te">Telugu (te)</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-xs font-bold text-white transition-colors"
            >
              <Play className="w-4 h-4" />
              {loading ? 'Orchestrating Agents...' : 'Launch Multi-Agent Run'}
            </button>
          </div>
        </form>

        {error && (
          <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Active Orchestration Run Inspector */}
        {activeRun && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column: Subtask Execution Graph & Controls */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-mono text-slate-400">{activeRun.run_id}</span>
                  <h3 className="text-sm font-bold text-white mt-0.5">Execution Plan & Subtasks</h3>
                </div>
                <span
                  className={`px-2.5 py-0.5 text-xs font-bold rounded-full border ${statusBadge(
                    activeRun.status
                  )}`}
                >
                  {activeRun.status}
                </span>
              </div>

              <p className="text-xs text-slate-400 leading-relaxed">{activeRun.plan_summary}</p>

              {/* Run Telemetry Pills */}
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-2">
                  <div className="text-xs font-bold text-cyan-300">{activeRun.execution_mode}</div>
                  <div className="text-[10px] text-slate-500">Mode</div>
                </div>
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-2">
                  <div className="text-xs font-bold text-emerald-300">
                    ${activeRun.total_estimated_cost_usd.toFixed(5)}
                  </div>
                  <div className="text-[10px] text-slate-500">Est. Cost</div>
                </div>
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-2">
                  <div className="text-xs font-bold text-amber-300">
                    {activeRun.duplicate_tool_calls_prevented}
                  </div>
                  <div className="text-[10px] text-slate-500">Deduped Calls</div>
                </div>
              </div>

              {/* Subtask Cards */}
              <div className="space-y-3">
                {activeRun.subtasks.map((st) => (
                  <div
                    key={st.subtask_id}
                    className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-white">{st.agent_name}</span>
                      <span
                        className={`px-2 py-0.5 text-[10px] font-semibold rounded border ${statusBadge(
                          st.status
                        )}`}
                      >
                        {st.status}
                      </span>
                    </div>

                    <div className="text-[11px] text-slate-400">{st.title}</div>

                    {st.tools_invoked.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1">
                        <Wrench className="w-3 h-3 text-indigo-400" />
                        {st.tools_invoked.map((t) => (
                          <span
                            key={t}
                            className="px-1.5 py-0.5 text-[10px] rounded bg-indigo-500/15 text-indigo-300"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}

                    {st.status === 'WAITING_APPROVAL' && (
                      <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 space-y-2">
                        <div className="flex items-start gap-1.5 text-[11px] text-amber-200">
                          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                          <span>{st.approval_reason}</span>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleApproveSubtask(st.subtask_id, true)}
                            className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-[11px] font-bold text-white"
                          >
                            Approve & Execute
                          </button>
                          <button
                            onClick={() => handleApproveSubtask(st.subtask_id, false)}
                            className="px-2.5 py-1 rounded bg-rose-600/80 hover:bg-rose-500 text-[11px] font-semibold text-white"
                          >
                            Decline
                          </button>
                        </div>
                      </div>
                    )}

                    {st.error_message && (
                      <div className="text-[11px] text-rose-300 bg-rose-950/40 p-2 rounded">
                        {st.error_message}
                      </div>
                    )}

                    <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {st.latency_ms}ms
                      </span>
                      {st.status === 'FAILED' && (
                        <button
                          onClick={() => handleRetryRun(st.subtask_id)}
                          className="text-cyan-400 hover:underline flex items-center gap-1"
                        >
                          <RotateCcw className="w-3 h-3" /> Retry Subtask
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Run Actions */}
              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => handleRetryRun()}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Retry Failed
                </button>
                <button
                  onClick={handleCancelRun}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl bg-rose-950/50 hover:bg-rose-900/60 border border-rose-500/30 text-xs font-medium text-rose-300"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  Cancel Run
                </button>
              </div>
            </div>

            {/* Right 2 Columns: Consolidated Synthesis & Epistemic Breakdown */}
            <div className="lg:col-span-2 space-y-5">
              {/* Combined Output */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  Synthesized Multi-Agent Deliverable
                </h3>
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
                  {activeRun.combined_response}
                </div>
              </div>

              {/* Epistemic Separation: Facts vs Assumptions vs Unresolved Questions */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-slate-900/75 border border-slate-800 rounded-2xl p-4 space-y-2">
                  <div className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Verified Facts ({activeRun.consolidated_facts.length})
                  </div>
                  <ul className="space-y-1.5 text-[11px] text-slate-300">
                    {activeRun.consolidated_facts.map((f, i) => (
                      <li key={i} className="leading-snug">• {f}</li>
                    ))}
                  </ul>
                </div>

                <div className="bg-slate-900/75 border border-slate-800 rounded-2xl p-4 space-y-2">
                  <div className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Working Assumptions ({activeRun.consolidated_assumptions.length})
                  </div>
                  <ul className="space-y-1.5 text-[11px] text-slate-300">
                    {activeRun.consolidated_assumptions.map((a, i) => (
                      <li key={i} className="leading-snug">• {a}</li>
                    ))}
                  </ul>
                </div>

                <div className="bg-slate-900/75 border border-slate-800 rounded-2xl p-4 space-y-2">
                  <div className="text-xs font-bold text-cyan-400 flex items-center gap-1.5">
                    <HelpCircle className="w-3.5 h-3.5" />
                    Unresolved / Pending ({activeRun.unresolved_questions.length})
                  </div>
                  {activeRun.unresolved_questions.length === 0 ? (
                    <div className="text-[11px] text-slate-500">None — all subtasks resolved cleanly.</div>
                  ) : (
                    <ul className="space-y-1.5 text-[11px] text-slate-300">
                      {activeRun.unresolved_questions.map((u, i) => (
                        <li key={i} className="leading-snug">• {u}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              {/* Citations, File References & Shared Memory Context */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-900/75 border border-slate-800 rounded-2xl p-4 space-y-2">
                  <div className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                    <ExternalLink className="w-3.5 h-3.5 text-cyan-400" />
                    Preserved Citations & File References
                  </div>
                  {activeRun.citations.length === 0 && activeRun.file_references.length === 0 ? (
                    <div className="text-[11px] text-slate-500">
                      No external URLs or vault files referenced in this run.
                    </div>
                  ) : (
                    <div className="space-y-1.5 text-[11px]">
                      {activeRun.citations.map((c, idx) => (
                        <a
                          key={idx}
                          href={c.url}
                          target="_blank"
                          rel="noreferrer"
                          className="block text-cyan-400 hover:underline truncate"
                        >
                          [{idx + 1}] {c.title} ({c.url})
                        </a>
                      ))}
                      {activeRun.file_references.map((f, idx) => (
                        <div key={idx} className="flex items-center gap-1 text-slate-300">
                          <FileText className="w-3 h-3 text-amber-400" />
                          <span>{f}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="bg-slate-900/75 border border-slate-800 rounded-2xl p-4 space-y-2">
                  <div className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5 text-emerald-400" />
                    Isolated User Memories Passed ({activeRun.used_memories.length})
                  </div>
                  {activeRun.used_memories.length === 0 ? (
                    <div className="text-[11px] text-slate-500">
                      No matching user memories required for this task.
                    </div>
                  ) : (
                    <ul className="space-y-1 text-[11px] text-slate-300">
                      {activeRun.used_memories.map((m, idx) => (
                        <li key={idx}>
                          <span className="text-emerald-400 font-semibold">[{m.category}]</span> {m.content}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
