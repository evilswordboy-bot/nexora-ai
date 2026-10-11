import React, { useEffect, useState, useCallback } from 'react';
import {
  GitBranch,
  GitCommit,
  GitMerge,
  GitPullRequest,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Plus,
  Play,
  FileCode,
  FolderGit2,
  Globe,
  Columns,
  AlignLeft,
  Sparkles,
  Check,
  X,
  UploadCloud,
  DownloadCloud,
  Lock,
  History,
} from 'lucide-react';
import { api } from '../../services/api';
import {
  CodeProjectSummary,
  GitBranchComparisonResponse,
  GitCapabilitiesResponse,
  GitCodeReviewResponse,
  GitDiffResponse,
  GitOperationRecord,
  GitPullRequestRecord,
  GitRemoteProvider,
  GitRepositoryStatusResponse,
} from '../../types';

export const GitVersionControlStudio: React.FC = () => {
  const [capabilities, setCapabilities] = useState<GitCapabilitiesResponse | null>(null);
  const [projects, setProjects] = useState<CodeProjectSummary[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('proj_default_py');
  const [repoStatus, setRepoStatus] = useState<GitRepositoryStatusResponse | null>(null);
  const [diffData, setDiffData] = useState<GitDiffResponse | null>(null);
  const [diffScope, setDiffScope] = useState<'all_working' | 'staged' | 'branch_compare'>('all_working');
  const [diffViewMode, setDiffViewMode] = useState<'side_by_side' | 'unified'>('side_by_side');
  const [selectedDiffFile, setSelectedDiffFile] = useState<string>('');

  const [activeTab, setActiveTab] = useState<'diff' | 'review' | 'commits' | 'collab'>('diff');
  const [loading, setLoading] = useState<boolean>(false);
  const [bannerMessage, setBannerMessage] = useState<{
    type: 'success' | 'error' | 'warning' | 'info';
    text: string;
  } | null>(null);

  // Commit composer state
  const [commitMessage, setCommitMessage] = useState<string>('');
  const [commitDescription, setCommitDescription] = useState<string>('');
  const [stageAllOnCommit, setStageAllOnCommit] = useState<boolean>(true);
  const [directConfirmCommit, setDirectConfirmCommit] = useState<boolean>(false);

  // Branch management state
  const [newBranchName, setNewBranchName] = useState<string>('');
  const [compareBaseBranch, setCompareBaseBranch] = useState<string>('main');
  const [compareTargetBranch, setCompareTargetBranch] = useState<string>('main');
  const [branchComparison, setBranchComparison] = useState<GitBranchComparisonResponse | null>(null);

  // AI Code Review state
  const [reviewResult, setReviewResult] = useState<GitCodeReviewResponse | null>(null);
  const [runTestsOnReview, setRunTestsOnReview] = useState<boolean>(true);
  const [acceptedFindings, setAcceptedFindings] = useState<Record<string, 'accepted' | 'dismissed'>>({});

  // Collaboration & Remote state
  const [remoteName, setRemoteName] = useState<string>('origin');
  const [remoteUrl, setRemoteUrl] = useState<string>('https://github.com/nexora-ai/workspace-repo.git');
  const [remoteProvider, setRemoteProvider] = useState<GitRemoteProvider>('github');
  const [pullRequests, setPullRequests] = useState<GitPullRequestRecord[]>([]);
  const [prTitle, setPrTitle] = useState<string>('');
  const [prDescription, setPrDescription] = useState<string>('');
  const [prIssues, setPrIssues] = useState<string>('#19');
  const [prSubmitRemote, setPrSubmitRemote] = useState<boolean>(false);

  // Operations & Approval Gate
  const [operations, setOperations] = useState<GitOperationRecord[]>([]);

  const loadWorkspaceData = useCallback(
    async (projectId: string, currentScope = diffScope) => {
      setLoading(true);
      try {
        const [caps, projs, status, ops, prs] = await Promise.all([
          api.getGitCapabilities(),
          api.listCodeProjects(),
          api.getGitRepositoryStatus(projectId),
          api.listGitOperations(projectId),
          api.listGitPullRequests(projectId),
        ]);
        setCapabilities(caps);
        setProjects(projs);
        setRepoStatus(status);
        setOperations(ops.operations || []);
        setPullRequests(prs.pull_requests || []);

        if (status.is_initialized) {
          const diff = await api.getGitDiff({
            project_id: projectId,
            scope: currentScope === 'branch_compare' ? 'all_working' : currentScope,
          });
          setDiffData(diff);
          if (diff.files.length > 0 && !selectedDiffFile) {
            setSelectedDiffFile(diff.files[0].file_path);
          } else if (diff.files.length === 0) {
            setSelectedDiffFile('');
          }
        } else {
          setDiffData(null);
          setSelectedDiffFile('');
        }
      } catch (err: any) {
        setBannerMessage({
          type: 'error',
          text: err?.message || 'Failed to load Stage 19 Git workspace state.',
        });
      } finally {
        setLoading(false);
      }
    },
    [diffScope, selectedDiffFile]
  );

  useEffect(() => {
    loadWorkspaceData(selectedProjectId);
  }, [selectedProjectId]);

  const handleInitRepo = async () => {
    setLoading(true);
    setBannerMessage(null);
    try {
      const op = await api.initGitRepository({
        project_id: selectedProjectId,
        default_branch: 'main',
        create_gitignore: true,
        initial_commit: true,
      });
      setBannerMessage({
        type: op.status === 'SUCCEEDED' ? 'success' : 'error',
        text:
          op.status === 'SUCCEEDED'
            ? `Initialized Git repository on branch 'main' with recommended .gitignore and initial baseline commit.`
            : op.error_message || 'Failed to initialize Git repository.',
      });
      await loadWorkspaceData(selectedProjectId);
    } catch (err: any) {
      setBannerMessage({ type: 'error', text: err?.message || 'Git initialization failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleStageFile = async (filePath?: string, stageAll = false) => {
    setLoading(true);
    try {
      const op = await api.stageGitFiles({
        project_id: selectedProjectId,
        paths: filePath ? [filePath] : [],
        stage_all: stageAll,
      });
      setBannerMessage({
        type: op.status === 'SUCCEEDED' ? 'success' : op.status === 'BLOCKED' ? 'warning' : 'error',
        text: op.error_message || op.stdout || 'Updated staged files.',
      });
      await loadWorkspaceData(selectedProjectId);
    } catch (err: any) {
      setBannerMessage({ type: 'error', text: err?.message || 'Staging failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleUnstageFile = async (filePath?: string, unstageAll = false) => {
    setLoading(true);
    try {
      const op = await api.unstageGitFiles({
        project_id: selectedProjectId,
        paths: filePath ? [filePath] : [],
        stage_all: unstageAll,
      });
      setBannerMessage({
        type: op.status === 'SUCCEEDED' ? 'info' : 'error',
        text: op.error_message || op.stdout || 'Unstaged changes.',
      });
      await loadWorkspaceData(selectedProjectId);
    } catch (err: any) {
      setBannerMessage({ type: 'error', text: err?.message || 'Unstaging failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleCommit = async () => {
    if (!commitMessage.trim()) {
      setBannerMessage({ type: 'warning', text: 'Please enter a descriptive commit message before committing.' });
      return;
    }
    setLoading(true);
    try {
      const op = await api.commitGitChanges({
        project_id: selectedProjectId,
        message: commitMessage.trim(),
        description: commitDescription.trim(),
        stage_all: stageAllOnCommit,
        confirmed: directConfirmCommit,
      });
      if (op.status === 'WAITING_FOR_APPROVAL') {
        setBannerMessage({
          type: 'warning',
          text: op.approval_reason || 'Commit staged and waiting for your explicit confirmation below.',
        });
      } else if (op.status === 'BLOCKED') {
        setBannerMessage({
          type: 'error',
          text: op.error_message || 'Commit blocked by Stage 19 Secret & .env Protection.',
        });
      } else if (op.status === 'SUCCEEDED') {
        setCommitMessage('');
        setCommitDescription('');
        setBannerMessage({
          type: 'success',
          text: `Commit verified (${op.result_data?.commit_hash || 'HEAD'}): ${op.stdout}`,
        });
      } else {
        setBannerMessage({
          type: 'error',
          text: op.error_message || 'Commit failed.',
        });
      }
      await loadWorkspaceData(selectedProjectId);
    } catch (err: any) {
      setBannerMessage({ type: 'error', text: err?.message || 'Commit request failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleApproveOperation = async (operationId: string, approved: boolean) => {
    setLoading(true);
    try {
      const op = await api.approveGitOperation(operationId, { approved });
      if (op.status === 'SUCCEEDED') {
        setCommitMessage('');
        setCommitDescription('');
        setBannerMessage({
          type: 'success',
          text: `Approved operation completed & verified: ${op.stdout || op.command_display}`,
        });
      } else if (op.status === 'CANCELLED') {
        setBannerMessage({
          type: 'info',
          text: 'Pending Git operation was declined and cancelled.',
        });
      } else {
        setBannerMessage({
          type: 'error',
          text: op.error_message || `Operation finished with status: ${op.status}`,
        });
      }
      await loadWorkspaceData(selectedProjectId);
    } catch (err: any) {
      setBannerMessage({ type: 'error', text: err?.message || 'Failed to process approval.' });
    } finally {
      setLoading(false);
    }
  };

  const handleBranchAction = async (action: 'create' | 'switch' | 'merge', branchName: string) => {
    if (!branchName.trim()) return;
    setLoading(true);
    try {
      const op = await api.manageGitBranch({
        project_id: selectedProjectId,
        action,
        branch_name: branchName.trim(),
        checkout_on_create: true,
        confirmed: action !== 'merge',
      });
      if (op.status === 'SUCCEEDED') {
        if (action === 'create') setNewBranchName('');
        setBannerMessage({
          type: 'success',
          text: op.stdout || `Branch operation '${action}' on '${branchName}' succeeded.`,
        });
      } else if (op.status === 'WAITING_FOR_APPROVAL') {
        setBannerMessage({
          type: 'warning',
          text: op.approval_reason || 'Merge requires explicit confirmation.',
        });
      } else {
        setBannerMessage({
          type: op.status === 'BLOCKED' ? 'warning' : 'error',
          text: op.error_message || `Branch operation '${action}' did not complete.`,
        });
      }
      await loadWorkspaceData(selectedProjectId);
    } catch (err: any) {
      setBannerMessage({ type: 'error', text: err?.message || 'Branch operation failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleCompareBranches = async () => {
    setLoading(true);
    try {
      const comp = await api.compareGitBranches({
        project_id: selectedProjectId,
        base_branch: compareBaseBranch,
        compare_branch: compareTargetBranch,
      });
      setBranchComparison(comp);
      setDiffData(comp.diff);
      setDiffScope('branch_compare');
      if (comp.diff.files.length > 0) {
        setSelectedDiffFile(comp.diff.files[0].file_path);
      }
      setActiveTab('diff');
    } catch (err: any) {
      setBannerMessage({ type: 'error', text: err?.message || 'Branch comparison failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleRunCodeReview = async () => {
    setLoading(true);
    setActiveTab('review');
    try {
      const res = await api.reviewGitChanges({
        project_id: selectedProjectId,
        run_stage18_tests: runTestsOnReview,
      });
      setReviewResult(res);
      setBannerMessage({
        type: res.verified_defects_count > 0 ? 'warning' : 'success',
        text: res.summary,
      });
    } catch (err: any) {
      setBannerMessage({ type: 'error', text: err?.message || 'AI Code Review failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleConfigureRemote = async () => {
    if (!remoteUrl.trim()) return;
    setLoading(true);
    try {
      const op = await api.configureGitRemote({
        project_id: selectedProjectId,
        name: remoteName.trim() || 'origin',
        url: remoteUrl.trim(),
        provider: remoteProvider,
      });
      setBannerMessage({
        type: op.status === 'SUCCEEDED' ? 'success' : 'error',
        text: op.stdout || op.error_message || 'Configured remote.',
      });
      await loadWorkspaceData(selectedProjectId);
    } catch (err: any) {
      setBannerMessage({ type: 'error', text: err?.message || 'Remote configuration failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleSyncRemote = async (action: 'fetch' | 'pull' | 'push') => {
    setLoading(true);
    try {
      const op = await api.syncGitRemote({
        project_id: selectedProjectId,
        remote_name: remoteName.trim() || 'origin',
        action,
        branch: repoStatus?.current_branch || 'main',
        confirmed: false,
      });
      setBannerMessage({
        type: op.status === 'WAITING_FOR_APPROVAL' ? 'warning' : op.status === 'SUCCEEDED' ? 'success' : 'error',
        text: op.approval_reason || op.error_message || op.stdout || `Remote ${action} requested.`,
      });
      await loadWorkspaceData(selectedProjectId);
    } catch (err: any) {
      setBannerMessage({ type: 'error', text: err?.message || `Remote ${action} failed.` });
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePullRequest = async () => {
    if (!prTitle.trim() || !repoStatus) {
      setBannerMessage({ type: 'warning', text: 'Enter a Pull Request title first.' });
      return;
    }
    setLoading(true);
    try {
      const issueList = prIssues
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      const pr = await api.createGitPullRequest({
        project_id: selectedProjectId,
        title: prTitle.trim(),
        description: prDescription.trim(),
        source_branch: repoStatus.current_branch,
        target_branch: compareBaseBranch || 'main',
        issue_references: issueList,
        submit_to_remote: prSubmitRemote,
      });
      setPrTitle('');
      setPrDescription('');
      setBannerMessage({
        type: pr.remote_confirmed ? 'success' : 'info',
        text: `${pr.status}: ${pr.provider_message}`,
      });
      await loadWorkspaceData(selectedProjectId);
    } catch (err: any) {
      setBannerMessage({ type: 'error', text: err?.message || 'Failed to prepare Pull Request.' });
    } finally {
      setLoading(false);
    }
  };

  const pendingOperations = operations.filter((op) => op.status === 'WAITING_FOR_APPROVAL');
  const activeFileDiff =
    diffData?.files.find((f) => f.file_path === selectedDiffFile) || diffData?.files[0] || null;

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden">
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-3.5 bg-slate-900/90 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-orange-500/15 border border-orange-500/30 text-orange-400">
            <FolderGit2 className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-white tracking-tight">
                Git & Version Control Engine
              </h2>
              <span className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-full bg-orange-500/20 text-orange-300 border border-orange-500/30">
                Stage 19
              </span>
              {capabilities && (
                <span
                  className={`px-2 py-0.5 text-[10px] font-medium rounded-full border ${
                    capabilities.git_installed
                      ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                      : 'bg-red-500/15 text-red-300 border-red-500/30'
                  }`}
                >
                  {capabilities.git_installed ? capabilities.git_version || 'Git Ready' : 'Git Missing'}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              Verified repository status, unified & side-by-side diffs, secret-guarded commits, and AI defect review
            </p>
          </div>
        </div>

        {/* Workspace Project Selector & Quick Actions */}
        <div className="flex items-center gap-2.5">
          <label className="text-xs text-slate-400 font-medium">Project:</label>
          <select
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-xs text-slate-100 rounded-lg px-3 py-1.5 focus:outline-none focus:border-orange-500"
          >
            {projects.map((p) => (
              <option key={p.project_id} value={p.project_id}>
                {p.name} ({p.primary_language})
              </option>
            ))}
          </select>

          {repoStatus && !repoStatus.is_initialized && (
            <button
              onClick={handleInitRepo}
              disabled={loading || !repoStatus.git_installed}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-orange-600 hover:bg-orange-500 text-white transition disabled:opacity-50"
            >
              <Plus className="w-3.5 h-3.5" />
              Initialize Git Repo
            </button>
          )}

          <button
            onClick={handleRunCodeReview}
            disabled={loading || !repoStatus?.is_initialized}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            AI Code Review
          </button>

          <button
            onClick={() => loadWorkspaceData(selectedProjectId)}
            disabled={loading}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            title="Refresh Git status"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Status & Alert Banners */}
      {bannerMessage && (
        <div
          className={`px-6 py-2.5 text-xs flex items-center justify-between border-b ${
            bannerMessage.type === 'success'
              ? 'bg-emerald-950/60 border-emerald-800/60 text-emerald-200'
              : bannerMessage.type === 'error'
              ? 'bg-red-950/60 border-red-800/60 text-red-200'
              : bannerMessage.type === 'warning'
              ? 'bg-amber-950/60 border-amber-800/60 text-amber-200'
              : 'bg-sky-950/60 border-sky-800/60 text-sky-200'
          }`}
        >
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{bannerMessage.text}</span>
          </div>
          <button
            onClick={() => setBannerMessage(null)}
            className="text-slate-400 hover:text-white ml-4"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Secret Protection Warning Banner */}
      {repoStatus && repoStatus.secret_warnings.length > 0 && (
        <div className="px-6 py-2.5 bg-red-950/80 border-b border-red-800 text-xs text-red-200 flex items-center gap-2.5">
          <ShieldAlert className="w-4 h-4 text-red-400 shrink-0" />
          <div>
            <span className="font-semibold text-red-300">
              Stage 19 Secret & .env Protection Active:
            </span>{' '}
            {repoStatus.secret_warnings.join(' | ')}
          </div>
        </div>
      )}

      {/* Pending Approval Gate Banner */}
      {pendingOperations.map((op) => (
        <div
          key={op.operation_id}
          className="px-6 py-3 bg-amber-950/70 border-b border-amber-700/70 flex flex-wrap items-center justify-between gap-3"
        >
          <div className="space-y-0.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-amber-200">
              <Lock className="w-3.5 h-3.5 text-amber-400" />
              <span>Explicit Confirmation Required: {op.command_display}</span>
            </div>
            <p className="text-xs text-amber-300/90">{op.approval_reason}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleApproveOperation(op.operation_id, true)}
              className="flex items-center gap-1 px-3 py-1 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
            >
              <Check className="w-3.5 h-3.5" />
              Approve & Execute
            </button>
            <button
              onClick={() => handleApproveOperation(op.operation_id, false)}
              className="flex items-center gap-1 px-3 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700"
            >
              <X className="w-3.5 h-3.5" />
              Cancel
            </button>
          </div>
        </div>
      ))}

      {/* Main Split Workspace */}
      <div className="flex-1 grid grid-cols-12 overflow-hidden">
        {/* Left Sidebar: Repository Status, Branches, Changed Files & Commit Box */}
        <div className="col-span-12 lg:col-span-4 border-r border-slate-800 flex flex-col overflow-y-auto bg-slate-900/40">
          {/* Repo Summary Card */}
          <div className="p-4 border-b border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-orange-400" />
                <span className="text-xs font-bold text-white">
                  {repoStatus?.is_initialized ? repoStatus.current_branch : 'Uninitialized Workspace'}
                </span>
              </div>
              {repoStatus?.is_initialized && (
                <span
                  className={`px-2 py-0.5 text-[10px] font-semibold rounded-full ${
                    repoStatus.is_clean
                      ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                      : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                  }`}
                >
                  {repoStatus.is_clean
                    ? 'Clean Working Tree'
                    : `${repoStatus.changed_files.length} Modified`}
                </span>
              )}
            </div>

            {/* Branch Switcher & Creator */}
            {repoStatus?.is_initialized && (
              <div className="space-y-2 pt-1">
                <div className="flex items-center gap-1.5">
                  <select
                    value={repoStatus.current_branch}
                    onChange={(e) => handleBranchAction('switch', e.target.value)}
                    className="flex-1 bg-slate-800/90 border border-slate-700 rounded-md px-2.5 py-1 text-xs text-slate-200"
                  >
                    {repoStatus.branches.map((b) => (
                      <option key={b.name} value={b.name}>
                        {b.is_current ? `● ${b.name}` : b.name} ({b.commit_hash})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-1.5">
                  <input
                    type="text"
                    value={newBranchName}
                    onChange={(e) => setNewBranchName(e.target.value)}
                    placeholder="New branch (e.g. feature/auth)"
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-md px-2.5 py-1 text-xs text-slate-200 placeholder-slate-500"
                  />
                  <button
                    onClick={() => handleBranchAction('create', newBranchName)}
                    disabled={!newBranchName.trim() || loading}
                    className="px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 disabled:opacity-40"
                  >
                    Branch
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Working Tree & Staged Files */}
          <div className="p-4 border-b border-slate-800 flex-1 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Working Tree ({repoStatus?.changed_files.length || 0})
              </span>
              {repoStatus?.is_initialized && repoStatus.changed_files.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => handleStageFile(undefined, true)}
                    className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30"
                  >
                    Stage All
                  </button>
                  <button
                    onClick={() => handleUnstageFile(undefined, true)}
                    className="text-[11px] px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
                  >
                    Unstage All
                  </button>
                </div>
              )}
            </div>

            {!repoStatus?.is_initialized ? (
              <div className="p-4 rounded-lg bg-slate-900/70 border border-slate-800 text-xs text-slate-400 space-y-2">
                <p>This project workspace is not yet a Git repository.</p>
                {repoStatus?.recommended_gitignore_entries && (
                  <div>
                    <p className="text-[11px] font-semibold text-slate-300 mb-1">
                      Recommended .gitignore rules ready to apply:
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {repoStatus.recommended_gitignore_entries.slice(0, 6).map((r) => (
                        <span
                          key={r}
                          className="px-1.5 py-0.5 text-[10px] font-mono bg-slate-800 text-slate-300 rounded"
                        >
                          {r}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : repoStatus.changed_files.length === 0 ? (
              <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800/80 text-center text-xs text-slate-400">
                Working tree is clean. Modify files in the Stage 18 Code Studio to inspect diffs.
              </div>
            ) : (
              <div className="space-y-1.5">
                {repoStatus.changed_files.map((file) => (
                  <div
                    key={file.path}
                    className="flex items-center justify-between gap-2 p-2 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 text-xs"
                  >
                    <button
                      onClick={() => {
                        setSelectedDiffFile(file.path);
                        setActiveTab('diff');
                      }}
                      className="flex items-center gap-2 text-left truncate flex-1"
                    >
                      <FileCode className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span className="font-mono text-slate-200 truncate">{file.path}</span>
                      {file.has_secret_warning && (
                        <span
                          title={file.secret_warning_detail || 'Secret detected'}
                          className="px-1.5 py-0.5 text-[9px] font-bold rounded bg-red-500/20 text-red-300 border border-red-500/40"
                        >
                          SECRET
                        </span>
                      )}
                    </button>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {file.staged && (
                        <span className="px-1.5 py-0.5 text-[10px] rounded bg-emerald-500/20 text-emerald-300">
                          Staged
                        </span>
                      )}
                      {file.untracked && (
                        <span className="px-1.5 py-0.5 text-[10px] rounded bg-sky-500/20 text-sky-300">
                          Untracked
                        </span>
                      )}
                      {file.staged ? (
                        <button
                          onClick={() => handleUnstageFile(file.path, false)}
                          className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px]"
                        >
                          Unstage
                        </button>
                      ) : (
                        <button
                          onClick={() => handleStageFile(file.path, false)}
                          className="px-2 py-0.5 rounded bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-200 text-[10px]"
                        >
                          Stage
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Safe Commit Composer */}
          {repoStatus?.is_initialized && (
            <div className="p-4 bg-slate-900/70 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                  <GitCommit className="w-3.5 h-3.5 text-orange-400" />
                  Safe Commit Preparation
                </span>
                <label className="flex items-center gap-1.5 text-[11px] text-slate-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={stageAllOnCommit}
                    onChange={(e) => setStageAllOnCommit(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-800 text-orange-500"
                  />
                  Auto-stage tracked/untracked
                </label>
              </div>

              <input
                type="text"
                value={commitMessage}
                onChange={(e) => setCommitMessage(e.target.value)}
                placeholder="feat: summarize change clearly..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-orange-500"
              />

              <textarea
                value={commitDescription}
                onChange={(e) => setCommitDescription(e.target.value)}
                rows={2}
                placeholder="Optional extended commit body / rationale..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-orange-500"
              />

              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-1.5 text-[11px] text-slate-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={directConfirmCommit}
                    onChange={(e) => setDirectConfirmCommit(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-800 text-emerald-500"
                  />
                  Confirm commit immediately
                </label>

                <button
                  onClick={handleCommit}
                  disabled={loading || !commitMessage.trim()}
                  className="px-3.5 py-1.5 rounded-lg bg-orange-600 hover:bg-orange-500 text-white text-xs font-semibold transition disabled:opacity-40"
                >
                  {directConfirmCommit ? 'Confirm & Commit' : 'Preview & Request Commit'}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Workspace Area: Tabs for Diff Viewer, AI Code Review, History, and Collaboration */}
        <div className="col-span-12 lg:col-span-8 flex flex-col overflow-hidden">
          {/* Sub-navigation Tabs */}
          <div className="flex items-center justify-between px-5 py-2.5 bg-slate-900/60 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('diff')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === 'diff'
                    ? 'bg-orange-500/20 text-orange-300 border border-orange-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Columns className="w-3.5 h-3.5" />
                Diff Inspector ({diffData?.total_files_changed || 0})
              </button>

              <button
                onClick={() => setActiveTab('review')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === 'review'
                    ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                AI Code Review
                {reviewResult && (
                  <span className="ml-1 px-1.5 py-0.2 text-[10px] rounded-full bg-indigo-500/30 text-indigo-200">
                    {reviewResult.findings.length}
                  </span>
                )}
              </button>

              <button
                onClick={() => setActiveTab('commits')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === 'commits'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <History className="w-3.5 h-3.5" />
                Commits & Audit ({repoStatus?.recent_commits.length || 0})
              </button>

              <button
                onClick={() => setActiveTab('collab')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === 'collab'
                    ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <GitPullRequest className="w-3.5 h-3.5" />
                Remotes & PRs ({pullRequests.length})
              </button>
            </div>

            {activeTab === 'diff' && (
              <div className="flex items-center gap-2">
                <select
                  value={diffScope}
                  onChange={(e) => {
                    const nextScope = e.target.value as 'all_working' | 'staged' | 'branch_compare';
                    setDiffScope(nextScope);
                    if (nextScope !== 'branch_compare') {
                      loadWorkspaceData(selectedProjectId, nextScope);
                    }
                  }}
                  className="bg-slate-800 border border-slate-700 rounded-md px-2 py-1 text-xs text-slate-200"
                >
                  <option value="all_working">All Working Changes</option>
                  <option value="staged">Staged Changes Only</option>
                  <option value="branch_compare">Branch Comparison</option>
                </select>

                <div className="flex rounded-md overflow-hidden border border-slate-700">
                  <button
                    onClick={() => setDiffViewMode('side_by_side')}
                    className={`px-2.5 py-1 text-xs flex items-center gap-1 ${
                      diffViewMode === 'side_by_side'
                        ? 'bg-orange-600 text-white'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    <Columns className="w-3 h-3" />
                    Side-by-Side
                  </button>
                  <button
                    onClick={() => setDiffViewMode('unified')}
                    className={`px-2.5 py-1 text-xs flex items-center gap-1 ${
                      diffViewMode === 'unified'
                        ? 'bg-orange-600 text-white'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    <AlignLeft className="w-3 h-3" />
                    Unified
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-5">
            {/* TAB 1: DIFF INSPECTOR */}
            {activeTab === 'diff' && (
              <div className="space-y-4">
                {/* Branch Compare Bar */}
                {repoStatus?.is_initialized && repoStatus.branches.length > 0 && (
                  <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-xl bg-slate-900/70 border border-slate-800 text-xs">
                    <div className="flex items-center gap-2">
                      <GitMerge className="w-4 h-4 text-orange-400" />
                      <span className="text-slate-300 font-medium">Compare or Merge Branches:</span>
                      <select
                        value={compareBaseBranch}
                        onChange={(e) => setCompareBaseBranch(e.target.value)}
                        className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs"
                      >
                        {repoStatus.branches.map((b) => (
                          <option key={b.name} value={b.name}>
                            base: {b.name}
                          </option>
                        ))}
                      </select>
                      <span className="text-slate-500">←</span>
                      <select
                        value={compareTargetBranch}
                        onChange={(e) => setCompareTargetBranch(e.target.value)}
                        className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs"
                      >
                        {repoStatus.branches.map((b) => (
                          <option key={b.name} value={b.name}>
                            compare: {b.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleCompareBranches}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
                      >
                        Compare Diff
                      </button>
                      <button
                        onClick={() => handleBranchAction('merge', compareTargetBranch)}
                        disabled={compareTargetBranch === repoStatus.current_branch}
                        className="px-2.5 py-1 rounded bg-orange-600/80 hover:bg-orange-600 text-white font-medium disabled:opacity-40"
                      >
                        Merge into {repoStatus.current_branch}
                      </button>
                    </div>
                  </div>
                )}

                {branchComparison && diffScope === 'branch_compare' && (
                  <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-semibold text-white">
                        {branchComparison.compare_branch} vs {branchComparison.base_branch}:
                      </span>{' '}
                      <span className="text-emerald-400">{branchComparison.ahead_count} ahead</span>,{' '}
                      <span className="text-amber-400">{branchComparison.behind_count} behind</span>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        branchComparison.has_conflicts
                          ? 'bg-red-500/20 text-red-300 border border-red-500/40'
                          : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                      }`}
                    >
                      {branchComparison.has_conflicts
                        ? `Conflicts detected (${branchComparison.conflict_files.join(', ')})`
                        : 'No Merge Conflicts'}
                    </span>
                  </div>
                )}

                {!diffData || diffData.files.length === 0 ? (
                  <div className="p-10 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-400">
                    No diff hunks in the selected scope ({diffScope}).
                  </div>
                ) : (
                  <div className="space-y-3">
                    {/* File Selector Pills */}
                    <div className="flex flex-wrap items-center gap-2">
                      {diffData.files.map((f) => (
                        <button
                          key={f.file_path}
                          onClick={() => setSelectedDiffFile(f.file_path)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-mono flex items-center gap-2 border transition ${
                            activeFileDiff?.file_path === f.file_path
                              ? 'bg-slate-800 border-orange-500/60 text-white'
                              : 'bg-slate-900/70 border-slate-800 text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          <span>{f.file_path}</span>
                          <span className="text-emerald-400">+{f.additions}</span>
                          <span className="text-red-400">-{f.deletions}</span>
                        </button>
                      ))}
                    </div>

                    {/* Active File Diff Renderer */}
                    {activeFileDiff && (
                      <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-950">
                        <div className="px-4 py-2 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-xs font-mono">
                          <span className="text-slate-200 font-semibold">{activeFileDiff.file_path}</span>
                          <div className="flex items-center gap-3">
                            <span className="text-emerald-400">+{activeFileDiff.additions} additions</span>
                            <span className="text-red-400">-{activeFileDiff.deletions} deletions</span>
                          </div>
                        </div>

                        {diffViewMode === 'unified' ? (
                          <pre className="p-4 text-xs font-mono overflow-x-auto leading-relaxed">
                            {activeFileDiff.unified_patch.split('\n').map((line, i) => {
                              const cls = line.startsWith('+')
                                ? 'bg-emerald-950/50 text-emerald-300'
                                : line.startsWith('-')
                                ? 'bg-red-950/50 text-red-300'
                                : line.startsWith('@@')
                                ? 'text-sky-400'
                                : 'text-slate-300';
                              return (
                                <div key={i} className={`px-2 ${cls}`}>
                                  {line}
                                </div>
                              );
                            })}
                          </pre>
                        ) : (
                          <div className="divide-y divide-slate-900 text-xs font-mono overflow-x-auto">
                            {activeFileDiff.side_by_side_lines.map((row, idx) => (
                              <div key={idx} className="grid grid-cols-2">
                                <div
                                  className={`flex px-2 py-0.5 border-r border-slate-900 ${
                                    row.change_type === 'delete'
                                      ? 'bg-red-950/45 text-red-200'
                                      : 'text-slate-400'
                                  }`}
                                >
                                  <span className="w-8 select-none text-slate-600 text-right pr-2">
                                    {row.left_line_no ?? ''}
                                  </span>
                                  <span className="whitespace-pre-wrap break-all">{row.left_content}</span>
                                </div>
                                <div
                                  className={`flex px-2 py-0.5 ${
                                    row.change_type === 'add'
                                      ? 'bg-emerald-950/45 text-emerald-200'
                                      : 'text-slate-300'
                                  }`}
                                >
                                  <span className="w-8 select-none text-slate-600 text-right pr-2">
                                    {row.right_line_no ?? ''}
                                  </span>
                                  <span className="whitespace-pre-wrap break-all">{row.right_content}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: AI CODE REVIEW */}
            {activeTab === 'review' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-bold text-white">
                      Stage 19 AI-Powered Code Review & Defect Verification
                    </h3>
                    <p className="text-xs text-slate-400">
                      Distinguishes Verified Defects (AST syntax errors, hardcoded secrets, eval/div-by-zero, failing unit tests) from Possible Concerns (mutable defaults, bare except, TODOs, missing test updates).
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <label className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={runTestsOnReview}
                        onChange={(e) => setRunTestsOnReview(e.target.checked)}
                        className="rounded border-slate-700 bg-slate-800 text-indigo-500"
                      />
                      Execute Stage 18 Unit Tests
                    </label>
                    <button
                      onClick={handleRunCodeReview}
                      disabled={loading}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
                    >
                      <Play className="w-3.5 h-3.5" />
                      Run Code Review
                    </button>
                  </div>
                </div>

                {reviewResult ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-3 gap-3">
                      <div className="p-3 rounded-xl bg-red-950/30 border border-red-800/50">
                        <div className="text-[11px] text-red-300 uppercase font-semibold">
                          Verified Defects
                        </div>
                        <div className="text-xl font-bold text-red-200 mt-0.5">
                          {reviewResult.verified_defects_count}
                        </div>
                      </div>
                      <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-800/50">
                        <div className="text-[11px] text-amber-300 uppercase font-semibold">
                          Possible Concerns
                        </div>
                        <div className="text-xl font-bold text-amber-200 mt-0.5">
                          {reviewResult.possible_concerns_count}
                        </div>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                        <div className="text-[11px] text-slate-400 uppercase font-semibold">
                          Stage 18 Unit Tests
                        </div>
                        <div className="text-sm font-bold text-slate-200 mt-1 flex items-center gap-1.5">
                          {reviewResult.tests_executed ? (
                            reviewResult.tests_passed ? (
                              <>
                                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                                <span className="text-emerald-300">PASSED</span>
                              </>
                            ) : (
                              <>
                                <XCircle className="w-4 h-4 text-red-400" />
                                <span className="text-red-300">FAILED</span>
                              </>
                            )
                          ) : (
                            <span className="text-slate-400">Not Executed</span>
                          )}
                        </div>
                      </div>
                    </div>

                    {reviewResult.findings.length === 0 ? (
                      <div className="p-6 rounded-xl bg-emerald-950/20 border border-emerald-800/40 text-center text-xs text-emerald-200">
                        No defects or concerns found across {reviewResult.reviewed_files.length} reviewed file(s).
                      </div>
                    ) : (
                      <div className="space-y-2.5">
                        {reviewResult.findings.map((f) => {
                          const decision = acceptedFindings[f.finding_id];
                          return (
                            <div
                              key={f.finding_id}
                              className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="flex items-center gap-2">
                                  <span
                                    className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded-full ${
                                      f.finding_type === 'verified_defect'
                                        ? 'bg-red-500/20 text-red-300 border border-red-500/40'
                                        : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                                    }`}
                                  >
                                    {f.finding_type === 'verified_defect'
                                      ? 'Verified Defect'
                                      : 'Possible Concern'}
                                  </span>
                                  <span className="px-2 py-0.5 text-[10px] uppercase rounded bg-slate-800 text-slate-300">
                                    {f.category} • {f.severity}
                                  </span>
                                  <span className="font-mono text-xs text-orange-300">
                                    {f.file_path}:{f.line_number}
                                  </span>
                                </div>

                                <div className="flex items-center gap-1.5">
                                  {decision ? (
                                    <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                                      User {decision}
                                    </span>
                                  ) : (
                                    <>
                                      <button
                                        onClick={() =>
                                          setAcceptedFindings((prev) => ({
                                            ...prev,
                                            [f.finding_id]: 'accepted',
                                          }))
                                        }
                                        className="px-2 py-0.5 rounded bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-200 text-[11px]"
                                      >
                                        Accept Finding
                                      </button>
                                      <button
                                        onClick={() =>
                                          setAcceptedFindings((prev) => ({
                                            ...prev,
                                            [f.finding_id]: 'dismissed',
                                          }))
                                        }
                                        className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 text-[11px]"
                                      >
                                        Dismiss
                                      </button>
                                    </>
                                  )}
                                </div>
                              </div>

                              <div className="text-xs font-semibold text-white">{f.title}</div>
                              <p className="text-xs text-slate-300">{f.description}</p>
                              <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-emerald-300 font-mono">
                                Suggested Fix: {f.suggested_fix}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-10 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-400">
                    Click &ldquo;Run Code Review&rdquo; to inspect modified files for bugs, security risks, readability issues, and missing tests.
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: COMMIT HISTORY & AUDIT LOG */}
            {activeTab === 'commits' && (
              <div className="space-y-5">
                <div className="space-y-2.5">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Commit History ({repoStatus?.recent_commits.length || 0})
                  </h3>
                  {repoStatus?.recent_commits.length === 0 ? (
                    <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800 text-xs text-slate-400 text-center">
                      No commits recorded yet.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {repoStatus?.recent_commits.map((c) => (
                        <div
                          key={c.commit_hash}
                          className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between gap-3 text-xs"
                        >
                          <div className="space-y-0.5">
                            <div className="font-semibold text-white">{c.subject}</div>
                            <div className="text-[11px] text-slate-400">
                              {c.author_name} &lt;{c.author_email}&gt; •{' '}
                              {new Date(c.authored_at).toLocaleString()}
                            </div>
                          </div>
                          <span className="px-2.5 py-1 rounded bg-slate-950 border border-slate-800 font-mono text-orange-300 text-xs">
                            {c.short_hash}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-2.5">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Verified Git Operation Log ({operations.length})
                  </h3>
                  <div className="space-y-1.5">
                    {operations.slice(0, 12).map((op) => (
                      <div
                        key={op.operation_id}
                        className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80 flex items-center justify-between text-xs"
                      >
                        <div className="truncate pr-3">
                          <span className="font-mono text-slate-200">{op.command_display}</span>
                          {op.error_message && (
                            <p className="text-[11px] text-red-300 truncate">{op.error_message}</p>
                          )}
                        </div>
                        <span
                          className={`px-2 py-0.5 text-[10px] font-semibold rounded-full shrink-0 ${
                            op.status === 'SUCCEEDED'
                              ? 'bg-emerald-500/15 text-emerald-300'
                              : op.status === 'WAITING_FOR_APPROVAL'
                              ? 'bg-amber-500/15 text-amber-300'
                              : 'bg-red-500/15 text-red-300'
                          }`}
                        >
                          {op.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* TAB 4: REMOTES & PULL REQUESTS */}
            {activeTab === 'collab' && (
              <div className="space-y-5">
                {/* Remote Configuration Card */}
                <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Globe className="w-4 h-4 text-sky-400" />
                      <h3 className="text-sm font-bold text-white">Remote Repository & Sync Status</h3>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleSyncRemote('fetch')}
                        disabled={!repoStatus?.remotes.length || loading}
                        className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 border border-slate-700 disabled:opacity-40"
                      >
                        <DownloadCloud className="w-3.5 h-3.5" />
                        Fetch
                      </button>
                      <button
                        onClick={() => handleSyncRemote('pull')}
                        disabled={!repoStatus?.remotes.length || loading}
                        className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 border border-slate-700 disabled:opacity-40"
                      >
                        <DownloadCloud className="w-3.5 h-3.5" />
                        Pull
                      </button>
                      <button
                        onClick={() => handleSyncRemote('push')}
                        disabled={!repoStatus?.remotes.length || loading}
                        className="flex items-center gap-1 px-2.5 py-1 rounded bg-sky-600 hover:bg-sky-500 text-xs font-semibold text-white disabled:opacity-40"
                      >
                        <UploadCloud className="w-3.5 h-3.5" />
                        Push
                      </button>
                    </div>
                  </div>

                  {repoStatus?.remotes && repoStatus.remotes.length > 0 && (
                    <div className="space-y-1.5">
                      {repoStatus.remotes.map((r) => (
                        <div
                          key={r.name}
                          className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs"
                        >
                          <div>
                            <span className="font-semibold text-white">{r.name}</span>{' '}
                            <span className="font-mono text-slate-400">({r.url})</span>
                          </div>
                          <span className="px-2 py-0.5 text-[10px] rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
                            {r.sync_status}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="grid grid-cols-12 gap-2 pt-1">
                    <input
                      type="text"
                      value={remoteName}
                      onChange={(e) => setRemoteName(e.target.value)}
                      placeholder="origin"
                      className="col-span-2 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                    />
                    <select
                      value={remoteProvider}
                      onChange={(e) => setRemoteProvider(e.target.value as GitRemoteProvider)}
                      className="col-span-3 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                    >
                      <option value="github">GitHub</option>
                      <option value="gitlab">GitLab</option>
                      <option value="bitbucket">Bitbucket</option>
                      <option value="custom">Custom Host</option>
                    </select>
                    <input
                      type="text"
                      value={remoteUrl}
                      onChange={(e) => setRemoteUrl(e.target.value)}
                      placeholder="https://github.com/org/repo.git"
                      className="col-span-5 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                    />
                    <button
                      onClick={handleConfigureRemote}
                      disabled={loading}
                      className="col-span-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white border border-slate-700"
                    >
                      Save Remote
                    </button>
                  </div>
                </div>

                {/* Pull Request Draft Preparation */}
                <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <GitPullRequest className="w-4 h-4 text-orange-400" />
                      Prepare Pull Request Summary & Issue References
                    </h3>
                    <span className="text-[11px] text-slate-400">
                      Clearly separates Local Drafts from Provider-Confirmed Remote PRs
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                    <input
                      type="text"
                      value={prTitle}
                      onChange={(e) => setPrTitle(e.target.value)}
                      placeholder="PR Title (e.g. feat: add Stage 19 Git integration)"
                      className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200"
                    />
                    <input
                      type="text"
                      value={prIssues}
                      onChange={(e) => setPrIssues(e.target.value)}
                      placeholder="Issue references (comma-separated, e.g. #19, NEX-204)"
                      className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200"
                    />
                  </div>

                  <textarea
                    value={prDescription}
                    onChange={(e) => setPrDescription(e.target.value)}
                    rows={2}
                    placeholder="Describe key changes, verification steps, and rollout notes..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200"
                  />

                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={prSubmitRemote}
                        onChange={(e) => setPrSubmitRemote(e.target.checked)}
                        className="rounded border-slate-700 bg-slate-800 text-sky-500"
                      />
                      Attempt remote provider submission (requires GIT_PROVIDER_TOKEN)
                    </label>
                    <button
                      onClick={handleCreatePullRequest}
                      disabled={loading || !prTitle.trim()}
                      className="px-4 py-1.5 rounded-lg bg-orange-600 hover:bg-orange-500 text-white text-xs font-semibold disabled:opacity-40"
                    >
                      Prepare Pull Request
                    </button>
                  </div>

                  {/* Pull Requests List */}
                  {pullRequests.length > 0 && (
                    <div className="space-y-2 pt-2">
                      {pullRequests.map((pr) => (
                        <div
                          key={pr.pr_id}
                          className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1.5 text-xs"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-white">{pr.title}</span>
                            <span
                              className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${
                                pr.status === 'REMOTE_CONFIRMED'
                                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                                  : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                              }`}
                            >
                              {pr.status}
                            </span>
                          </div>
                          <div className="text-slate-400">
                            {pr.source_branch} → {pr.target_branch} • Issues:{' '}
                            {pr.issue_references.join(', ') || 'None'}
                          </div>
                          <div className="text-slate-300 font-mono text-[11px]">{pr.review_summary}</div>
                          <div className="text-[11px] text-sky-300">{pr.provider_message}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
