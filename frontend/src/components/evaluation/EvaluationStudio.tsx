import React, { useEffect, useState, useCallback } from 'react';
import {
  ShieldCheck,
  Play,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Database,
  GitCompare,
  FileDown,
  Plus,
  Sparkles,
  Trash2,
  BookOpen,
  Lock,
  Filter,
  Info,
  Activity,
  X,
} from 'lucide-react';
import { api } from '../../services/api';
import {
  EvalMetadataResponse,
  EvalRunRecord,
  EvalSuiteId,
  EvalTestCase,
  EvalCaseExecutionResult,
  EvalRegressionAlert,
} from '../../types';

type StudioTab = 'results' | 'comparison' | 'dataset' | 'rules';

export const EvaluationStudio: React.FC = () => {
  const [metadata, setMetadata] = useState<EvalMetadataResponse | null>(null);
  const [cases, setCases] = useState<EvalTestCase[]>([]);
  const [runs, setRuns] = useState<EvalRunRecord[]>([]);
  const [activeRun, setActiveRun] = useState<EvalRunRecord | null>(null);
  const [selectedCaseResult, setSelectedCaseResult] = useState<EvalCaseExecutionResult | null>(null);

  const [selectedSuites, setSelectedSuites] = useState<EvalSuiteId[]>([]);
  const [includePendingSynthetic, setIncludePendingSynthetic] = useState(false);
  const [baselineRunId, setBaselineRunId] = useState<string>('');
  const [simulateProviderFailure, setSimulateProviderFailure] = useState<boolean>(false);
  const [simulateInterruptionCount, setSimulateInterruptionCount] = useState<string>('');

  const [activeTab, setActiveTab] = useState<StudioTab>('results');
  const [resultFilter, setResultFilter] = useState<'all' | 'failed' | 'critical'>('all');
  const [suiteFilter, setSuiteFilter] = useState<EvalSuiteId | ''>('');

  // Comparison state
  const [compareBaselineId, setCompareBaselineId] = useState<string>('');
  const [compareCandidateId, setCompareCandidateId] = useState<string>('');
  const [comparisonResult, setComparisonResult] = useState<{
    baseline_run_id: string;
    candidate_run_id: string;
    baseline_dataset_version: string;
    candidate_dataset_version: string;
    regression_alerts: EvalRegressionAlert[];
    has_critical_regressions: boolean;
    candidate_verdict: string;
  } | null>(null);

  // Report export preview
  const [exportedReportText, setExportedReportText] = useState<string>('');

  // Dataset creation / synthetic generation state
  const [newCaseSuite, setNewCaseSuite] = useState<EvalSuiteId>('general_qa');
  const [newCaseTitle, setNewCaseTitle] = useState('');
  const [newCasePrompt, setNewCasePrompt] = useState(
    'Provide a numbered list of 2 architecture principles for reliable AI evaluation.'
  );
  const [newCaseCritical, setNewCaseCritical] = useState(false);
  const [newCasePrivateFlag, setNewCasePrivateFlag] = useState(false);

  const [synthSuite, setSynthSuite] = useState<EvalSuiteId>('fact_checking');
  const [synthTopic, setSynthTopic] = useState('citation_grounding_and_uncertainty');
  const [synthCount, setSynthCount] = useState(2);

  const [loading, setLoading] = useState(false);
  const [runningEval, setRunningEval] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [statusNotice, setStatusNotice] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setErrorBanner(null);
    try {
      const [metaRes, casesRes, runsRes] = await Promise.all([
        api.getEvaluationMetadata(),
        api.listEvaluationCases(undefined, true),
        api.listEvaluationRuns(25),
      ]);
      setMetadata(metaRes);
      setCases(casesRes.cases);
      setRuns(runsRes.runs);
      if (runsRes.runs.length > 0 && !activeRun) {
        setActiveRun(runsRes.runs[0]);
        setSelectedCaseResult(runsRes.runs[0].case_results[0] || null);
      }
      if (selectedSuites.length === 0 && metaRes.suites.length > 0) {
        setSelectedSuites(metaRes.suites.map((s) => s.suite_id));
      }
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to load Stage 20 Evaluation metadata.');
    } finally {
      setLoading(false);
    }
  }, [activeRun, selectedSuites.length]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const toggleSuite = (suiteId: EvalSuiteId) => {
    setSelectedSuites((prev) =>
      prev.includes(suiteId) ? prev.filter((s) => s !== suiteId) : [...prev, suiteId]
    );
  };

  const handleRunEvaluation = async () => {
    setRunningEval(true);
    setErrorBanner(null);
    setStatusNotice(null);
    try {
      const simInterrupt = simulateInterruptionCount.trim()
        ? parseInt(simulateInterruptionCount.trim(), 10)
        : undefined;

      const run = await api.executeEvaluationRun({
        suites: selectedSuites,
        include_pending_synthetic: includePendingSynthetic,
        baseline_run_id: baselineRunId || undefined,
        simulate_provider_failure: simulateProviderFailure,
        simulate_interrupted_after_n:
          simInterrupt !== undefined && !isNaN(simInterrupt) ? simInterrupt : undefined,
      });

      setActiveRun(run);
      setSelectedCaseResult(run.case_results[0] || null);
      setStatusNotice(
        `Evaluation Run ${run.run_id} finished (${run.status}) — Verdict: ${run.release_gate_verdict}`
      );
      const runsRes = await api.listEvaluationRuns(25);
      setRuns(runsRes.runs);
    } catch (err: any) {
      setErrorBanner(err.message || 'Evaluation run failed.');
    } finally {
      setRunningEval(false);
    }
  };

  const handleCompareRuns = async () => {
    if (!compareBaselineId || !compareCandidateId) {
      setErrorBanner('Select both a Baseline Run and a Candidate Run to compare.');
      return;
    }
    setErrorBanner(null);
    try {
      const res = await api.compareEvaluationRuns({
        baseline_run_id: compareBaselineId,
        candidate_run_id: compareCandidateId,
      });
      setComparisonResult(res);
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to compare evaluation runs.');
    }
  };

  const handleExportReport = async (format: 'markdown' | 'json') => {
    if (!activeRun) return;
    setErrorBanner(null);
    try {
      const res = await api.exportEvaluationRunReport(activeRun.run_id, format);
      if (format === 'markdown' && res.markdown_report) {
        setExportedReportText(res.markdown_report);
      } else {
        setExportedReportText(JSON.stringify(res, null, 2));
      }
      setActiveTab('comparison');
      setStatusNotice(`Exported ${format.toUpperCase()} report for ${activeRun.run_id}.`);
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to export evaluation report.');
    }
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCaseTitle.trim()) return;
    setErrorBanner(null);
    setStatusNotice(null);
    try {
      const created = await api.createEvaluationCase({
        suite_id: newCaseSuite,
        title: newCaseTitle.trim(),
        description: 'User-added benchmark evaluation case',
        source_type: 'curated_benchmark',
        is_critical: newCaseCritical,
        input_payload: {
          prompt: newCasePrompt,
          action: 'instruction_format',
        },
        expected_criteria: {
          required_bullet_count: 2,
          forbidden_words: ['hack'],
        },
        contains_private_conversation_data: newCasePrivateFlag,
      });
      setStatusNotice(
        `Added case "${created.title}". Dataset version bumped to ${created.dataset_version}.`
      );
      setNewCaseTitle('');
      const [metaRes, casesRes] = await Promise.all([
        api.getEvaluationMetadata(),
        api.listEvaluationCases(undefined, true),
      ]);
      setMetadata(metaRes);
      setCases(casesRes.cases);
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to create evaluation case.');
    }
  };

  const handleGenerateSynthetic = async () => {
    setErrorBanner(null);
    setStatusNotice(null);
    try {
      const res = await api.generateSyntheticCases({
        suite_id: synthSuite,
        count: synthCount,
        topic_focus: synthTopic,
      });
      setStatusNotice(
        `Generated ${res.generated_count} synthetic labeled cases (Dataset: ${res.dataset_version}).`
      );
      const [metaRes, casesRes] = await Promise.all([
        api.getEvaluationMetadata(),
        api.listEvaluationCases(undefined, true),
      ]);
      setMetadata(metaRes);
      setCases(casesRes.cases);
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to generate synthetic test cases.');
    }
  };

  const handleReviewCase = async (
    caseId: string,
    status: 'approved' | 'rejected'
  ) => {
    setErrorBanner(null);
    try {
      const updated = await api.reviewEvaluationCase(caseId, {
        review_status: status,
        reviewer_note: `Reviewed in Stage 20 Evaluation Studio (${status})`,
      });
      setStatusNotice(
        `Updated case ${caseId} -> ${status.toUpperCase()} (Dataset ${updated.dataset_version})`
      );
      const [metaRes, casesRes] = await Promise.all([
        api.getEvaluationMetadata(),
        api.listEvaluationCases(undefined, true),
      ]);
      setMetadata(metaRes);
      setCases(casesRes.cases);
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to review case.');
    }
  };

  const handleDeleteCase = async (caseId: string) => {
    setErrorBanner(null);
    try {
      const res = await api.deleteEvaluationCase(caseId);
      setStatusNotice(`Removed case ${caseId} (Dataset ${res.dataset_version})`);
      const [metaRes, casesRes] = await Promise.all([
        api.getEvaluationMetadata(),
        api.listEvaluationCases(undefined, true),
      ]);
      setMetadata(metaRes);
      setCases(casesRes.cases);
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to delete case.');
    }
  };

  const handleExportDataset = async () => {
    setErrorBanner(null);
    try {
      const res = await api.exportEvaluationDataset();
      setExportedReportText(JSON.stringify(res, null, 2));
      setActiveTab('comparison');
      setStatusNotice(
        `Exported dataset ${res.dataset_version} (${res.total_cases} cases).`
      );
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to export dataset.');
    }
  };

  const filteredCaseResults = (activeRun?.case_results || []).filter((r) => {
    if (resultFilter === 'failed') return !r.passed;
    if (resultFilter === 'critical') return r.is_critical;
    return true;
  });

  const filteredDatasetCases = cases.filter((c) =>
    suiteFilter ? c.suite_id === suiteFilter : true
  );

  const formatScore = (val: number | null | undefined, isPct = true) => {
    if (val === null || val === undefined) {
      return 'N/A (Unverified)';
    }
    return isPct ? `${(val * 100).toFixed(1)}%` : String(val);
  };

  const getVerdictBadgeStyle = (verdict?: string) => {
    switch (verdict) {
      case 'RELEASE_APPROVED':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40';
      case 'RELEASE_BLOCKED_CRITICAL_FAILURE':
      case 'RELEASE_BLOCKED_REGRESSION':
        return 'bg-rose-500/15 text-rose-300 border-rose-500/40';
      default:
        return 'bg-amber-500/15 text-amber-300 border-amber-500/40';
    }
  };

  const unavailableEntries = activeRun
    ? Object.entries(activeRun.metrics.unavailable_metrics_notes || {})
    : [];

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden">
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-b border-slate-800 bg-slate-900/70">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-white">
                AI Evaluation & Quality Assurance Engine
              </h1>
              <span className="px-2 py-0.5 text-[11px] font-semibold rounded-full bg-teal-500/20 text-teal-300 border border-teal-500/30">
                Stage 20
              </span>
              {metadata && (
                <span className="px-2 py-0.5 text-[11px] font-mono rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                  Dataset {metadata.dataset_version} ({metadata.approved_cases}/
                  {metadata.total_cases} approved)
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              Repeatable 10-suite benchmark harness across Stages 1–19 • Zero fabricated scores •
              Automated regression & release gating
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadAll}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={handleRunEvaluation}
            disabled={runningEval || selectedSuites.length === 0}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white shadow-sm transition-colors"
          >
            <Play className="w-3.5 h-3.5" />
            {runningEval
              ? 'Executing Suites...'
              : `Run Evaluation (${selectedSuites.length} Suites)`}
          </button>
        </div>
      </div>

      {/* Alerts */}
      {errorBanner && (
        <div className="mx-6 mt-3 px-4 py-2.5 rounded-lg bg-rose-950/70 border border-rose-500/40 text-rose-200 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorBanner}</span>
          </div>
          <button onClick={() => setErrorBanner(null)} className="text-rose-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {statusNotice && (
        <div className="mx-6 mt-3 px-4 py-2 rounded-lg bg-teal-950/60 border border-teal-500/40 text-teal-200 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-400 shrink-0" />
            <span>{statusNotice}</span>
          </div>
          <button onClick={() => setStatusNotice(null)} className="text-teal-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Content Layout */}
      <div className="flex-1 grid grid-cols-12 gap-4 p-6 overflow-y-auto">
        {/* Left Sidebar: Suite Selection, Run Controls & Run History */}
        <div className="col-span-12 lg:col-span-4 space-y-4">
          {/* Suite Selector Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <Filter className="w-3.5 h-3.5 text-teal-400" />
                Configurable Test Suites (10)
              </h2>
              <div className="flex items-center gap-2 text-[11px]">
                <button
                  onClick={() =>
                    metadata && setSelectedSuites(metadata.suites.map((s) => s.suite_id))
                  }
                  className="text-teal-400 hover:underline"
                >
                  All
                </button>
                <span className="text-slate-600">|</span>
                <button
                  onClick={() => setSelectedSuites([])}
                  className="text-slate-400 hover:underline"
                >
                  None
                </button>
              </div>
            </div>

            <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
              {(metadata?.suites || []).map((suite) => {
                const checked = selectedSuites.includes(suite.suite_id);
                return (
                  <label
                    key={suite.suite_id}
                    className={`flex items-start gap-2.5 p-2 rounded-lg border cursor-pointer transition-colors ${
                      checked
                        ? 'bg-teal-950/30 border-teal-500/40 text-slate-100'
                        : 'bg-slate-950/50 border-slate-800/80 text-slate-400'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleSuite(suite.suite_id)}
                      className="mt-0.5 rounded border-slate-700 text-teal-500 focus:ring-teal-500"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-xs font-semibold truncate">{suite.name}</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 shrink-0">
                          {suite.stage_coverage}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">
                        {suite.description}
                      </p>
                    </div>
                  </label>
                );
              })}
            </div>

            {/* Execution Options & Edge-Case Controls */}
            <div className="pt-2 border-t border-slate-800 space-y-2.5 text-xs">
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">
                  Compare Against Baseline Run (Optional)
                </label>
                <select
                  value={baselineRunId}
                  onChange={(e) => setBaselineRunId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                >
                  <option value="">No Baseline Comparison</option>
                  {runs.map((r) => (
                    <option key={r.run_id} value={r.run_id}>
                      {r.run_id} ({r.dataset_version} •{' '}
                      {(r.metrics.task_success_rate * 100).toFixed(0)}% pass)
                    </option>
                  ))}
                </select>
              </div>

              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includePendingSynthetic}
                  onChange={(e) => setIncludePendingSynthetic(e.target.checked)}
                  className="rounded border-slate-700 text-teal-500"
                />
                <span>Include unreviewed synthetic test cases</span>
              </label>

              <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2">
                <div className="text-[11px] font-semibold text-amber-300 flex items-center gap-1">
                  <Activity className="w-3.5 h-3.5" />
                  Fault & Edge-Case Verification Controls
                </div>
                <div className="grid grid-cols-2 gap-2 items-center">
                  <label className="flex items-center gap-1.5 text-[11px] text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={simulateProviderFailure}
                      onChange={(e) => setSimulateProviderFailure(e.target.checked)}
                    />
                    <span>Simulate Provider Error</span>
                  </label>
                  <div>
                    <label className="block text-[10px] text-slate-400 mb-0.5">
                      Interrupt After N Cases
                    </label>
                    <input
                      type="number"
                      min={1}
                      value={simulateInterruptionCount}
                      onChange={(e) => setSimulateInterruptionCount(e.target.value)}
                      placeholder="e.g. 3"
                      className="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1 text-[11px] text-slate-200"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Historical Runs List */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-teal-400" />
              Recorded Evaluation Runs ({runs.length})
            </h2>
            {runs.length === 0 ? (
              <p className="text-xs text-slate-500 py-4 text-center">
                No evaluation runs recorded yet. Click &ldquo;Run Evaluation&rdquo; above to execute
                actual Stage 1–19 benchmark suites.
              </p>
            ) : (
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {runs.map((r) => {
                  const isSelected = activeRun?.run_id === r.run_id;
                  return (
                    <button
                      key={r.run_id}
                      onClick={() => {
                        setActiveRun(r);
                        setSelectedCaseResult(r.case_results[0] || null);
                      }}
                      className={`w-full text-left p-2.5 rounded-lg border transition-colors ${
                        isSelected
                          ? 'bg-teal-950/40 border-teal-500/50'
                          : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-mono font-semibold text-slate-200">
                          {r.run_id}
                        </span>
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${getVerdictBadgeStyle(
                            r.release_gate_verdict
                          )}`}
                        >
                          {r.release_gate_verdict}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1">
                        <span>
                          {r.passed_cases}/{r.sample_size} passed (
                          {(r.metrics.task_success_rate * 100).toFixed(0)}%)
                        </span>
                        <span>
                          {r.metrics.avg_latency_ms.toFixed(1)} ms avg • {r.dataset_version}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Main Area: Release Gate Banner, Metrics & Sub-Tabs */}
        <div className="col-span-12 lg:col-span-8 space-y-4">
          {/* Release Gate Verdict & Isolation Banner */}
          {activeRun ? (
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <span
                    className={`px-3 py-1 rounded-lg text-xs font-bold border ${getVerdictBadgeStyle(
                      activeRun.release_gate_verdict
                    )}`}
                  >
                    {activeRun.release_gate_verdict}
                  </span>
                  <span className="text-xs font-mono text-slate-300">
                    Run: {activeRun.run_id} • Status: {activeRun.status}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[11px]">
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-teal-300 border border-slate-700 flex items-center gap-1">
                    <Lock className="w-3 h-3" />
                    Env: {activeRun.isolated_environment_id}
                  </span>
                  {activeRun.consequential_actions_blocked && (
                    <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-500/30">
                      Consequential Side-Effects Blocked
                    </span>
                  )}
                </div>
              </div>

              <div className="space-y-1">
                {activeRun.release_gate_reasons.map((reason, idx) => (
                  <p key={idx} className="text-xs text-slate-300 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-teal-400 shrink-0" />
                    {reason}
                  </p>
                ))}
              </div>

              {/* Metric Summary Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-2">
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                  <div className="text-[10px] uppercase text-slate-400">Task Success Rate</div>
                  <div className="text-base font-bold text-white mt-0.5">
                    {formatScore(activeRun.metrics.task_success_rate)}
                  </div>
                  <div className="text-[10px] text-slate-500">
                    {activeRun.passed_cases}/{activeRun.sample_size} cases passed
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                  <div className="text-[10px] uppercase text-slate-400">
                    Safety & Policy Compliance
                  </div>
                  <div className="text-base font-bold text-emerald-400 mt-0.5">
                    {formatScore(activeRun.metrics.safety_compliance_rate)}
                  </div>
                  <div className="text-[10px] text-slate-500">
                    Critical failures: {activeRun.critical_failures}
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                  <div className="text-[10px] uppercase text-slate-400">
                    Factual & Citation Grounding
                  </div>
                  <div className="text-base font-bold text-teal-300 mt-0.5">
                    {formatScore(activeRun.metrics.factual_support_score)} /{' '}
                    {formatScore(activeRun.metrics.citation_validity_score)}
                  </div>
                  <div className="text-[10px] text-slate-500">Factual / Citation validity</div>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                  <div className="text-[10px] uppercase text-slate-400">Latency (Avg / P95)</div>
                  <div className="text-base font-bold text-slate-200 mt-0.5">
                    {activeRun.metrics.avg_latency_ms.toFixed(1)} /{' '}
                    {activeRun.metrics.p95_latency_ms.toFixed(1)} ms
                  </div>
                  <div className="text-[10px] text-slate-500">
                    Error rate: {formatScore(activeRun.metrics.error_rate)}
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                  <div className="text-[10px] uppercase text-slate-400">
                    Extraction & Language Quality
                  </div>
                  <div className="text-xs font-semibold text-slate-200 mt-1">
                    Doc: {formatScore(activeRun.metrics.extraction_accuracy_score)} • Lang:{' '}
                    {formatScore(activeRun.metrics.language_quality_score)}
                  </div>
                  <div className="text-[10px] text-amber-400/90">
                    Lang score is heuristic (non-ground-truth)
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                  <div className="text-[10px] uppercase text-slate-400">Tool Call Success</div>
                  <div className="text-xs font-semibold text-slate-200 mt-1">
                    {formatScore(activeRun.metrics.tool_call_success_rate)}
                  </div>
                  <div className="text-[10px] text-slate-500">Stages 11, 14, 15, 16–19</div>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 col-span-2">
                  <div className="text-[10px] uppercase text-slate-400">
                    Token Usage & Estimated Cost (Anti-Fabrication Verified)
                  </div>
                  <div className="text-xs font-semibold text-slate-200 mt-1">
                    Tokens:{' '}
                    {activeRun.metrics.total_tokens !== null &&
                    activeRun.metrics.total_tokens !== undefined
                      ? activeRun.metrics.total_tokens
                      : 'null (Local/Offline — Not Fabricated)'}{' '}
                    • Cost:{' '}
                    {activeRun.metrics.estimated_cost_usd !== null &&
                    activeRun.metrics.estimated_cost_usd !== undefined
                      ? `$${activeRun.metrics.estimated_cost_usd.toFixed(6)}`
                      : 'null (No Billable Cloud Call)'}
                  </div>
                  {unavailableEntries.length > 0 && (
                    <div className="text-[10px] text-slate-400 mt-0.5 line-clamp-1">
                      Note ({unavailableEntries[0][0]}): {unavailableEntries[0][1]}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 text-center space-y-2">
              <ShieldCheck className="w-8 h-8 text-teal-400 mx-auto" />
              <h3 className="text-sm font-semibold text-white">
                Ready to Execute Stage 20 Evaluation Benchmark
              </h3>
              <p className="text-xs text-slate-400 max-w-lg mx-auto">
                Select one or more test suites on the left and click{' '}
                <strong>Run Evaluation</strong> to execute real functional and safety tests across
                Stages 1–19 in an isolated workspace namespace.
              </p>
            </div>
          )}

          {/* Navigation Sub-Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setActiveTab('results')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  activeTab === 'results'
                    ? 'bg-teal-600 text-white'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                }`}
              >
                Case Results & Inspector ({activeRun?.case_results.length || 0})
              </button>
              <button
                onClick={() => setActiveTab('comparison')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                  activeTab === 'comparison'
                    ? 'bg-teal-600 text-white'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                }`}
              >
                <GitCompare className="w-3.5 h-3.5" />
                Regressions & Reports
              </button>
              <button
                onClick={() => setActiveTab('dataset')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                  activeTab === 'dataset'
                    ? 'bg-teal-600 text-white'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                }`}
              >
                <Database className="w-3.5 h-3.5" />
                Dataset Manager ({cases.length})
              </button>
              <button
                onClick={() => setActiveTab('rules')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                  activeTab === 'rules'
                    ? 'bg-teal-600 text-white'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                }`}
              >
                <BookOpen className="w-3.5 h-3.5" />
                Scoring Rules & Rubrics
              </button>
            </div>

            {activeRun && (
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => handleExportReport('markdown')}
                  className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] text-slate-200 border border-slate-700"
                >
                  <FileDown className="w-3 h-3" />
                  Export MD
                </button>
                <button
                  onClick={() => handleExportReport('json')}
                  className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] text-slate-200 border border-slate-700"
                >
                  <FileDown className="w-3 h-3" />
                  Export JSON
                </button>
              </div>
            )}
          </div>

          {/* TAB 1: CASE RESULTS & FAILED CASE DRILLDOWN */}
          {activeTab === 'results' && (
            <div className="grid grid-cols-12 gap-4">
              <div className="col-span-12 xl:col-span-7 bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                    Executed Test Cases ({filteredCaseResults.length})
                  </h3>
                  <div className="flex items-center gap-1 text-[11px]">
                    {(['all', 'failed', 'critical'] as const).map((f) => (
                      <button
                        key={f}
                        onClick={() => setResultFilter(f)}
                        className={`px-2 py-0.5 rounded capitalize ${
                          resultFilter === f
                            ? 'bg-teal-600 text-white'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {f}
                      </button>
                    ))}
                  </div>
                </div>

                {filteredCaseResults.length === 0 ? (
                  <p className="text-xs text-slate-500 py-6 text-center">
                    No matching case results to display.
                  </p>
                ) : (
                  <div className="space-y-1.5 max-h-96 overflow-y-auto pr-1">
                    {filteredCaseResults.map((res) => {
                      const active = selectedCaseResult?.case_id === res.case_id;
                      return (
                        <button
                          key={res.case_id}
                          onClick={() => setSelectedCaseResult(res)}
                          className={`w-full text-left p-2.5 rounded-lg border transition-colors ${
                            active
                              ? 'bg-teal-950/40 border-teal-500/50'
                              : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2 min-w-0">
                              {res.passed ? (
                                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                              ) : (
                                <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                              )}
                              <span className="text-xs font-semibold text-slate-200 truncate">
                                {res.title}
                              </span>
                            </div>
                            <span className="text-[10px] font-mono text-slate-400 shrink-0">
                              {res.latency_ms.toFixed(1)} ms
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                            <span className="font-mono">{res.suite_id}</span>
                            <div className="flex items-center gap-1.5">
                              {res.is_critical && (
                                <span className="px-1.5 py-0.2 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30">
                                  Critical Safety
                                </span>
                              )}
                              <span>Score: {(res.score * 100).toFixed(0)}%</span>
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Case Inspector Drilldown */}
              <div className="col-span-12 xl:col-span-5 bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Case Execution & Assertion Inspector
                </h3>
                {selectedCaseResult ? (
                  <div className="space-y-3 text-xs">
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] text-teal-400">
                          {selectedCaseResult.case_id}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            selectedCaseResult.passed
                              ? 'bg-emerald-500/20 text-emerald-300'
                              : 'bg-rose-500/20 text-rose-300'
                          }`}
                        >
                          {selectedCaseResult.passed ? 'PASSED' : 'FAILED'}
                        </span>
                      </div>
                      <div className="font-semibold text-slate-100 mt-1">
                        {selectedCaseResult.title}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1">
                        Method: <code className="text-teal-300">{selectedCaseResult.scoring_method}</code>{' '}
                        {selectedCaseResult.is_subjective_advisory && (
                          <span className="text-amber-300">(Advisory / Non-Ground-Truth)</span>
                        )}
                      </div>
                    </div>

                    {selectedCaseResult.error_detail && (
                      <div className="p-2.5 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-200">
                        <div className="font-semibold text-[11px] mb-0.5">Error Detail:</div>
                        <div className="font-mono text-[11px] break-all">
                          {selectedCaseResult.error_detail}
                        </div>
                      </div>
                    )}

                    <div>
                      <div className="text-[11px] font-semibold text-slate-300 mb-1">
                        Expected Criteria Summary:
                      </div>
                      <div className="p-2 rounded bg-slate-950 border border-slate-800 text-[11px] text-slate-300 font-mono">
                        {selectedCaseResult.expected_summary}
                      </div>
                    </div>

                    <div>
                      <div className="text-[11px] font-semibold text-slate-300 mb-1">
                        Actual Output Excerpt:
                      </div>
                      <pre className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-300 font-mono whitespace-pre-wrap max-h-40 overflow-y-auto">
                        {selectedCaseResult.actual_output_excerpt || '(No output excerpt)'}
                      </pre>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 py-8 text-center">
                    Select a test case result on the left to inspect its assertions, domain scores,
                    and actual output.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: REGRESSION COMPARISON & EXPORTED REPORTS */}
          {activeTab === 'comparison' && (
            <div className="space-y-4">
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Compare Historical Runs for Regressions
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
                  <div>
                    <label className="block text-[11px] text-slate-400 mb-1">Baseline Run</label>
                    <select
                      value={compareBaselineId}
                      onChange={(e) => setCompareBaselineId(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                    >
                      <option value="">Select Baseline...</option>
                      {runs.map((r) => (
                        <option key={r.run_id} value={r.run_id}>
                          {r.run_id} ({(r.metrics.task_success_rate * 100).toFixed(0)}% pass)
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-400 mb-1">Candidate Run</label>
                    <select
                      value={compareCandidateId}
                      onChange={(e) => setCompareCandidateId(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                    >
                      <option value="">Select Candidate...</option>
                      {runs.map((r) => (
                        <option key={r.run_id} value={r.run_id}>
                          {r.run_id} ({(r.metrics.task_success_rate * 100).toFixed(0)}% pass)
                        </option>
                      ))}
                    </select>
                  </div>
                  <button
                    onClick={handleCompareRuns}
                    className="px-4 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-xs font-semibold text-white"
                  >
                    Compare Runs
                  </button>
                </div>

                {comparisonResult && (
                  <div className="pt-3 border-t border-slate-800 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-200">
                        Comparison: {comparisonResult.baseline_run_id} vs{' '}
                        {comparisonResult.candidate_run_id}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                          comparisonResult.has_critical_regressions
                            ? 'bg-rose-500/20 text-rose-300'
                            : 'bg-emerald-500/20 text-emerald-300'
                        }`}
                      >
                        {comparisonResult.has_critical_regressions
                          ? 'CRITICAL REGRESSION DETECTED'
                          : 'NO CRITICAL REGRESSIONS'}
                      </span>
                    </div>

                    {comparisonResult.regression_alerts.length === 0 ? (
                      <p className="text-xs text-emerald-300">
                        No quality, safety, error-rate, or latency regressions detected between the
                        selected runs.
                      </p>
                    ) : (
                      <div className="space-y-1.5">
                        {comparisonResult.regression_alerts.map((alert, i) => (
                          <div
                            key={i}
                            className="p-2.5 rounded-lg bg-rose-950/40 border border-rose-500/40 text-xs text-rose-200"
                          >
                            <div className="font-semibold">
                              [{alert.severity.toUpperCase()}] {alert.metric_name} (Delta:{' '}
                              {alert.delta})
                            </div>
                            <div className="text-[11px] mt-0.5">{alert.message}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {exportedReportText && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Exported Evaluation Report / Dataset Preview
                    </h3>
                    <button
                      onClick={() => setExportedReportText('')}
                      className="text-xs text-slate-400 hover:text-white"
                    >
                      Close
                    </button>
                  </div>
                  <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-200 whitespace-pre-wrap max-h-80 overflow-y-auto">
                    {exportedReportText}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: DATASET VERSION MANAGER */}
          {activeTab === 'dataset' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Add Curated Case Form */}
                <form
                  onSubmit={handleCreateCase}
                  className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-2.5"
                >
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                    <Plus className="w-3.5 h-3.5 text-teal-400" />
                    Add Benchmark Evaluation Case
                  </h3>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-[10px] text-slate-400 mb-0.5">Suite</label>
                      <select
                        value={newCaseSuite}
                        onChange={(e) => setNewCaseSuite(e.target.value as EvalSuiteId)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200"
                      >
                        {(metadata?.suites || []).map((s) => (
                          <option key={s.suite_id} value={s.suite_id}>
                            {s.suite_id}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-400 mb-0.5">Case Title</label>
                      <input
                        type="text"
                        value={newCaseTitle}
                        onChange={(e) => setNewCaseTitle(e.target.value)}
                        placeholder="e.g. Strict 2-Item Numbered Output"
                        className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-400 mb-0.5">
                      Input Prompt (`input_payload.prompt`)
                    </label>
                    <input
                      type="text"
                      value={newCasePrompt}
                      onChange={(e) => setNewCasePrompt(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200"
                    />
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-300">
                    <label className="flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={newCaseCritical}
                        onChange={(e) => setNewCaseCritical(e.target.checked)}
                      />
                      <span>Critical Safety Case</span>
                    </label>
                    <label className="flex items-center gap-1.5 cursor-pointer text-amber-300">
                      <input
                        type="checkbox"
                        checked={newCasePrivateFlag}
                        onChange={(e) => setNewCasePrivateFlag(e.target.checked)}
                      />
                      <span>Contains Private User Chat (Test Privacy Guard)</span>
                    </label>
                  </div>
                  <button
                    type="submit"
                    className="w-full py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-xs font-semibold text-white"
                  >
                    Add Case & Bump Dataset Version
                  </button>
                </form>

                {/* Generate Synthetic Labeled Cases */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-2.5">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                    Generate Labeled Synthetic Cases
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Generated cases are explicitly labeled{' '}
                    <code className="text-amber-300">synthetic_labeled</code> with{' '}
                    <code className="text-amber-300">pending_review</code> status until approved.
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-[10px] text-slate-400 mb-0.5">Target Suite</label>
                      <select
                        value={synthSuite}
                        onChange={(e) => setSynthSuite(e.target.value as EvalSuiteId)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200"
                      >
                        {(metadata?.suites || []).map((s) => (
                          <option key={s.suite_id} value={s.suite_id}>
                            {s.suite_id}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-400 mb-0.5">Count (1–5)</label>
                      <input
                        type="number"
                        min={1}
                        max={5}
                        value={synthCount}
                        onChange={(e) => setSynthCount(Number(e.target.value))}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-400 mb-0.5">Focus Topic</label>
                    <input
                      type="text"
                      value={synthTopic}
                      onChange={(e) => setSynthTopic(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200"
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleGenerateSynthetic}
                      className="flex-1 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-xs font-semibold text-white"
                    >
                      Generate Synthetic Cases
                    </button>
                    <button
                      onClick={handleExportDataset}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 border border-slate-700"
                    >
                      Export Dataset
                    </button>
                  </div>
                </div>
              </div>

              {/* Dataset Cases Table */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                    Versioned Dataset Cases ({filteredDatasetCases.length})
                  </h3>
                  <select
                    value={suiteFilter}
                    onChange={(e) => setSuiteFilter(e.target.value as EvalSuiteId | '')}
                    className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200"
                  >
                    <option value="">All Suites</option>
                    {(metadata?.suites || []).map((s) => (
                      <option key={s.suite_id} value={s.suite_id}>
                        {s.suite_id}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5 max-h-80 overflow-y-auto pr-1">
                  {filteredDatasetCases.map((c) => (
                    <div
                      key={c.case_id}
                      className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[11px] text-teal-400">{c.case_id}</span>
                          <span className="font-semibold text-slate-200 truncate">{c.title}</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 font-mono">
                            {c.suite_id}
                          </span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                              c.source_type === 'synthetic_labeled'
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                : 'bg-teal-500/15 text-teal-300'
                            }`}
                          >
                            {c.source_type}
                          </span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                              c.review_status === 'approved'
                                ? 'bg-emerald-500/20 text-emerald-300'
                                : c.review_status === 'pending_review'
                                ? 'bg-amber-500/20 text-amber-300'
                                : 'bg-rose-500/20 text-rose-300'
                            }`}
                          >
                            {c.review_status}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5">
                        {c.review_status !== 'approved' && (
                          <button
                            onClick={() => handleReviewCase(c.case_id, 'approved')}
                            className="px-2 py-0.5 rounded bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-200 text-[11px]"
                          >
                            Approve
                          </button>
                        )}
                        {c.review_status !== 'rejected' && (
                          <button
                            onClick={() => handleReviewCase(c.case_id, 'rejected')}
                            className="px-2 py-0.5 rounded bg-amber-600/30 hover:bg-amber-600/50 text-amber-200 text-[11px]"
                          >
                            Reject
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteCase(c.case_id)}
                          className="p-1 rounded bg-rose-950/60 hover:bg-rose-900 text-rose-300"
                          title="Delete case"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: SCORING RULES & LIMITATIONS */}
          {activeTab === 'rules' && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-teal-400" />
                  Metric-Specific Scoring Rules & Ground-Truth Limitations
                </h3>
              </div>
              <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                {(metadata?.scoring_rules || []).map((rule) => (
                  <div
                    key={rule.metric_id}
                    className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-white">
                        {rule.name}{' '}
                        <span className="font-mono text-[11px] text-teal-400">
                          ({rule.metric_id})
                        </span>
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          rule.is_definitive_ground_truth
                            ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                            : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                        }`}
                      >
                        {rule.is_definitive_ground_truth
                          ? `Deterministic (${rule.range_display})`
                          : `Heuristic / Non-Ground-Truth (${rule.range_display})`}
                      </span>
                    </div>
                    <p className="text-slate-300 text-[11px]">{rule.rule_description}</p>
                    <p className="text-amber-300/90 text-[11px]">
                      <strong>Limitation:</strong> {rule.limitations}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default EvaluationStudio;
