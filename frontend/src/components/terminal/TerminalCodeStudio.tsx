import React, { useState, useEffect, useCallback } from 'react';
import {
  Terminal,
  Play,
  Square,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Code2,
  FileCode,
  FolderPlus,
  FilePlus,
  Save,
  RotateCcw,
  Wrench,
  Sparkles,
  History,
  ShieldAlert,
  ShieldCheck,
  Package,
  FlaskConical,
  ChevronRight,
  Lock,
  ArrowUpRight,
} from 'lucide-react';
import { api } from '../../services/api';
import {
  CodeFileBackup,
  CodeInspectionResult,
  CodeProjectFile,
  CodeProjectSummary,
  CommandPreview,
  DebugRepairResponse,
  ProjectTemplateType,
  TerminalCapabilitiesResponse,
  TerminalExecutionRecord,
} from '../../types';
import { useChat } from '../../context/ChatContext';

type ConsoleTab =
  | 'console'
  | 'terminal'
  | 'tests'
  | 'diagnostics'
  | 'debugger'
  | 'backups';

export const TerminalCodeStudio: React.FC = () => {
  const { showToast } = useChat();
  const [userId] = useState('default_user');

  const [capabilities, setCapabilities] =
    useState<TerminalCapabilitiesResponse | null>(null);
  const [projects, setProjects] = useState<CodeProjectSummary[]>([]);
  const [activeProject, setActiveProject] =
    useState<CodeProjectSummary | null>(null);
  const [selectedFile, setSelectedFile] = useState<CodeProjectFile | null>(
    null
  );
  const [editorContent, setEditorContent] = useState<string>('');
  const [isDirty, setIsDirty] = useState<boolean>(false);

  const [activeTab, setActiveTab] = useState<ConsoleTab>('console');
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [activeExecution, setActiveExecution] =
    useState<TerminalExecutionRecord | null>(null);
  const [executions, setExecutions] = useState<TerminalExecutionRecord[]>([]);
  const [inspection, setInspection] = useState<CodeInspectionResult | null>(
    null
  );
  const [repairReport, setRepairReport] = useState<DebugRepairResponse | null>(
    null
  );
  const [backups, setBackups] = useState<CodeFileBackup[]>([]);

  // Controlled Terminal State
  const [terminalInput, setTerminalInput] = useState<string>('ls');
  const [allowNetworkToggle, setAllowNetworkToggle] = useState<boolean>(false);
  const [commandPreview, setCommandPreview] = useState<CommandPreview | null>(
    null
  );

  // Modals / Inline forms
  const [showNewProjectForm, setShowNewProjectForm] = useState<boolean>(false);
  const [newProjectName, setNewProjectName] = useState<string>('');
  const [newProjectTemplate, setNewProjectTemplate] =
    useState<ProjectTemplateType>('python');
  const [showNewFileForm, setShowNewFileForm] = useState<boolean>(false);
  const [newFileName, setNewFileName] = useState<string>('');

  const loadWorkspace = useCallback(
    async (preferredProjectId?: string, preferredFilePath?: string) => {
      try {
        const [caps, projList] = await Promise.all([
          api.getTerminalCapabilities(userId),
          api.listCodeProjects(userId),
        ]);
        setCapabilities(caps);
        setProjects(projList);

        const targetProj =
          projList.find((p) => p.project_id === preferredProjectId) ||
          projList[0] ||
          null;
        setActiveProject(targetProj);

        if (targetProj) {
          const targetFile =
            targetProj.files.find(
              (f) => f.relative_path === preferredFilePath
            ) ||
            targetProj.files.find(
              (f) => f.relative_path === targetProj.entrypoint
            ) ||
            targetProj.files[0] ||
            null;
          setSelectedFile(targetFile);
          setEditorContent(targetFile?.content || '');
          setIsDirty(false);

          const [execHistory, bks] = await Promise.all([
            api.listTerminalExecutions(userId, targetProj.project_id, 25),
            api.listCodeProjectBackups(targetProj.project_id, userId),
          ]);
          setExecutions(execHistory);
          if (execHistory.length > 0 && !activeExecution) {
            setActiveExecution(execHistory[0]);
          }
          setBackups(bks);
        }
      } catch (err: any) {
        showToast(err.message || 'Failed to load Stage 18 workspace', 'error');
      }
    },
    [userId, showToast, activeExecution]
  );

  useEffect(() => {
    loadWorkspace();
  }, []);

  const handleSelectProject = async (projectId: string) => {
    await loadWorkspace(projectId);
    setInspection(null);
    setRepairReport(null);
  };

  const handleSelectFile = (file: CodeProjectFile) => {
    setSelectedFile(file);
    setEditorContent(file.content || '');
    setIsDirty(false);
  };

  const handleSaveFile = async () => {
    if (!activeProject || !selectedFile) return;
    try {
      const res = await api.saveCodeProjectFile(activeProject.project_id, {
        user_id: userId,
        relative_path: selectedFile.relative_path,
        content: editorContent,
        create_backup: true,
        backup_reason: 'manual_editor_save',
      });
      setIsDirty(false);
      showToast(
        res.backup
          ? `Saved '${selectedFile.relative_path}' (Backup v${res.backup.version_number} preserved)`
          : `Saved '${selectedFile.relative_path}'`,
        'success'
      );
      await loadWorkspace(
        activeProject.project_id,
        selectedFile.relative_path
      );
    } catch (err: any) {
      showToast(err.message || 'Failed to save file', 'error');
    }
  };

  const handleRunOrTest = async (mode: 'run' | 'test') => {
    if (!activeProject) return;
    setIsRunning(true);
    try {
      if (isDirty && selectedFile) {
        await api.saveCodeProjectFile(activeProject.project_id, {
          user_id: userId,
          relative_path: selectedFile.relative_path,
          content: editorContent,
          create_backup: true,
          backup_reason: `pre_${mode}_autosave`,
        });
        setIsDirty(false);
      }
      const rec = await api.executeProjectCode({
        user_id: userId,
        project_id: activeProject.project_id,
        target_file:
          mode === 'run'
            ? selectedFile?.relative_path || activeProject.entrypoint
            : undefined,
        mode,
        allow_network: allowNetworkToggle,
      });
      setActiveExecution(rec);
      setActiveTab(mode === 'test' ? 'tests' : 'console');
      const updatedExecs = await api.listTerminalExecutions(
        userId,
        activeProject.project_id,
        25
      );
      setExecutions(updatedExecs);

      if (rec.status === 'WAITING_FOR_APPROVAL') {
        showToast(
          'Execution paused: Outbound network access requires explicit user approval.',
          'info'
        );
      } else if (rec.status === 'SUCCEEDED') {
        showToast(
          `${mode === 'test' ? 'Test suite' : 'Execution'} succeeded (${rec.duration_ms}ms)`,
          'success'
        );
      } else {
        showToast(
          `${mode === 'test' ? 'Tests' : 'Execution'} finished with ${rec.status}`,
          'error'
        );
      }
    } catch (err: any) {
      showToast(err.message || 'Execution failed', 'error');
    } finally {
      setIsRunning(false);
    }
  };

  const handleStopExecution = async () => {
    if (!activeExecution) return;
    try {
      const res = await api.stopTerminalExecution(
        activeExecution.execution_id,
        userId
      );
      showToast(res.message, res.stopped ? 'info' : 'error');
    } catch (err: any) {
      showToast(err.message || 'Failed to stop process', 'error');
    }
  };

  const handleInspectAndLint = async (applyFormatting = false) => {
    if (!activeProject || !selectedFile) return;
    try {
      const res = await api.inspectProjectCode({
        user_id: userId,
        project_id: activeProject.project_id,
        relative_path: selectedFile.relative_path,
        content: editorContent,
        apply_formatting: applyFormatting,
      });
      setInspection(res);
      if (applyFormatting && res.formatted_content) {
        setEditorContent(res.formatted_content);
        setIsDirty(false);
        showToast('Formatted code and updated inspection diagnostics', 'success');
      } else {
        showToast(res.summary, res.syntax_valid ? 'info' : 'error');
      }
      setActiveTab('diagnostics');
    } catch (err: any) {
      showToast(err.message || 'Inspection failed', 'error');
    }
  };

  const handleDebugAndRepair = async () => {
    if (!activeProject || !selectedFile) return;
    setIsRunning(true);
    try {
      if (isDirty) {
        await api.saveCodeProjectFile(activeProject.project_id, {
          user_id: userId,
          relative_path: selectedFile.relative_path,
          content: editorContent,
          create_backup: true,
          backup_reason: 'pre_debug_repair_save',
        });
        setIsDirty(false);
      }
      const rep = await api.debugAndRepairCode({
        user_id: userId,
        project_id: activeProject.project_id,
        target_file: selectedFile.relative_path,
        run_tests: true,
        max_attempts: 3,
        auto_apply: true,
      });
      setRepairReport(rep);
      if (rep.final_execution) {
        setActiveExecution(rep.final_execution);
      }
      setActiveTab('debugger');
      await loadWorkspace(
        activeProject.project_id,
        selectedFile.relative_path
      );
      showToast(
        rep.explanation,
        rep.final_verified ? 'success' : 'info'
      );
    } catch (err: any) {
      showToast(err.message || 'Debug & repair failed', 'error');
    } finally {
      setIsRunning(false);
    }
  };

  const handleResetProject = async () => {
    if (!activeProject) return;
    try {
      await api.resetCodeProject(activeProject.project_id, userId);
      showToast(
        'Reset project files to baseline template (backups preserved)',
        'info'
      );
      await loadWorkspace(activeProject.project_id);
    } catch (err: any) {
      showToast(err.message || 'Failed to reset project', 'error');
    }
  };

  const handlePreviewCommand = async (cmdText: string) => {
    if (!activeProject || !cmdText.trim()) {
      setCommandPreview(null);
      return;
    }
    try {
      const prev = await api.classifyTerminalCommand({
        user_id: userId,
        project_id: activeProject.project_id,
        command: cmdText,
        allow_network: allowNetworkToggle,
      });
      setCommandPreview(prev);
    } catch {
      setCommandPreview(null);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      if (activeProject && terminalInput.trim()) {
        handlePreviewCommand(terminalInput);
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [terminalInput, allowNetworkToggle, activeProject?.project_id]);

  const handleRunTerminalCommand = async () => {
    if (!activeProject || !terminalInput.trim()) return;
    setIsRunning(true);
    try {
      const rec = await api.runTerminalCommand({
        user_id: userId,
        project_id: activeProject.project_id,
        command: terminalInput.trim(),
        allow_network: allowNetworkToggle,
        confirmed: false,
      });
      setActiveExecution(rec);
      setActiveTab('terminal');
      const updatedExecs = await api.listTerminalExecutions(
        userId,
        activeProject.project_id,
        25
      );
      setExecutions(updatedExecs);

      if (rec.status === 'BLOCKED') {
        showToast(
          rec.command_preview.blocked_reason || 'Command blocked by sandbox policy',
          'error'
        );
      } else if (rec.status === 'WAITING_FOR_APPROVAL') {
        showToast(
          'Command requires explicit user confirmation before execution.',
          'info'
        );
      } else {
        await loadWorkspace(
          activeProject.project_id,
          selectedFile?.relative_path
        );
      }
    } catch (err: any) {
      showToast(err.message || 'Terminal command failed', 'error');
    } finally {
      setIsRunning(false);
    }
  };

  const handleApproveExecution = async (
    executionId: string,
    approved: boolean
  ) => {
    if (!activeProject) return;
    try {
      const rec = await api.approveTerminalExecution(executionId, {
        user_id: userId,
        approved,
      });
      setActiveExecution(rec);
      const updatedExecs = await api.listTerminalExecutions(
        userId,
        activeProject.project_id,
        25
      );
      setExecutions(updatedExecs);
      await loadWorkspace(
        activeProject.project_id,
        selectedFile?.relative_path
      );
      showToast(
        approved
          ? `Approved and executed (${rec.status})`
          : 'Cancelled consequential operation',
        approved && rec.status === 'SUCCEEDED' ? 'success' : 'info'
      );
    } catch (err: any) {
      showToast(err.message || 'Approval failed', 'error');
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    try {
      const created = await api.createCodeProject({
        user_id: userId,
        name: newProjectName.trim(),
        template: newProjectTemplate,
      });
      setNewProjectName('');
      setShowNewProjectForm(false);
      await loadWorkspace(created.project_id);
      showToast(`Created ${newProjectTemplate} project '${created.name}'`, 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to create project', 'error');
    }
  };

  const handleCreateFile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProject || !newFileName.trim()) return;
    try {
      await api.saveCodeProjectFile(activeProject.project_id, {
        user_id: userId,
        relative_path: newFileName.trim(),
        content: `# ${newFileName.trim()}\n`,
        create_backup: false,
      });
      const targetPath = newFileName.trim();
      setNewFileName('');
      setShowNewFileForm(false);
      await loadWorkspace(activeProject.project_id, targetPath);
      showToast(`Created file '${targetPath}'`, 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to create file', 'error');
    }
  };

  const handleRestoreBackup = async (backup: CodeFileBackup) => {
    if (!activeProject) return;
    try {
      await api.restoreCodeProjectBackup(
        activeProject.project_id,
        backup.backup_id,
        userId
      );
      await loadWorkspace(activeProject.project_id, backup.relative_path);
      showToast(
        `Restored '${backup.relative_path}' to backup v${backup.version_number}`,
        'success'
      );
    } catch (err: any) {
      showToast(err.message || 'Failed to restore backup', 'error');
    }
  };

  const handleSyncToStage17 = async () => {
    if (!activeProject) return;
    try {
      const res = await api.syncCodeProjectWithStage17(
        activeProject.project_id,
        {
          user_id: userId,
          direction: 'to_stage17',
        }
      );
      showToast(res.summary, 'success');
    } catch (err: any) {
      showToast(err.message || 'Stage 17 sync failed', 'error');
    }
  };

  const lineCount = Math.max(1, editorContent.split('\n').length);

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-midnight-950 text-slate-100">
      {/* Top IDE Header Bar */}
      <div className="px-5 py-3 border-b border-slate-800/80 bg-midnight-900/70 flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Terminal className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm sm:text-base font-bold text-slate-100">
                Developer Code & Sandboxed Terminal Studio
              </h1>
              <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                Stage 18 Sandbox Active
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Isolated execution • CPU/Memory/Time limits ({capabilities?.limits.execution_timeout_seconds ?? 5}s,{' '}
              {capabilities?.limits.max_memory_mb ?? 128}MB) • Network disabled by default • Allowlisted terminal
            </p>
          </div>
        </div>

        {/* IDE Action Controls: Run, Stop, Test, Check & Lint, Format, Auto-Debug, Reset, Save */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => handleRunOrTest('run')}
            disabled={isRunning || !selectedFile}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 disabled:opacity-50 transition-all"
          >
            <Play className="w-3.5 h-3.5" />
            <span>Run</span>
          </button>

          <button
            onClick={handleStopExecution}
            disabled={!isRunning && activeExecution?.status !== 'RUNNING'}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-red-500/15 hover:bg-red-500/25 text-red-300 border border-red-500/30 disabled:opacity-40 transition-all"
            title="Stop active process"
          >
            <Square className="w-3.5 h-3.5" />
            <span>Stop</span>
          </button>

          <button
            onClick={() => handleRunOrTest('test')}
            disabled={isRunning || !activeProject}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 disabled:opacity-50 transition-all"
          >
            <FlaskConical className="w-3.5 h-3.5" />
            <span>Test</span>
          </button>

          <button
            onClick={() => handleInspectAndLint(false)}
            disabled={!selectedFile}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
            <span>Check & Lint</span>
          </button>

          <button
            onClick={() => handleInspectAndLint(true)}
            disabled={!selectedFile}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>Format</span>
          </button>

          <button
            onClick={handleDebugAndRepair}
            disabled={isRunning || !selectedFile}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-violet-500/20 hover:bg-violet-500/30 text-violet-300 border border-violet-500/40 disabled:opacity-50 transition-all"
          >
            <Wrench className="w-3.5 h-3.5" />
            <span>Auto-Debug & Repair</span>
          </button>

          <button
            onClick={handleSaveFile}
            disabled={!selectedFile}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
              isDirty
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                : 'bg-slate-800/80 text-slate-300 border-slate-700'
            }`}
          >
            <Save className="w-3.5 h-3.5" />
            <span>{isDirty ? 'Save*' : 'Save'}</span>
          </button>

          <button
            onClick={handleResetProject}
            disabled={!activeProject}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-all"
            title="Reset project files to template (backups preserved)"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>
        </div>
      </div>

      {/* Main 3-Pane IDE Body */}
      <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
        {/* Left Sidebar: Project Selector & File Explorer */}
        <div className="w-full lg:w-64 border-b lg:border-b-0 lg:border-r border-slate-800/80 bg-midnight-900/50 flex flex-col shrink-0">
          {/* Project Switcher */}
          <div className="p-3 border-b border-slate-800/80">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Active Project
              </span>
              <button
                onClick={() => setShowNewProjectForm((prev) => !prev)}
                className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
              >
                <FolderPlus className="w-3.5 h-3.5" />
                <span>New</span>
              </button>
            </div>
            <select
              value={activeProject?.project_id || ''}
              onChange={(e) => handleSelectProject(e.target.value)}
              className="w-full px-2.5 py-1.5 rounded-lg bg-midnight-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              {projects.map((p) => (
                <option key={p.project_id} value={p.project_id}>
                  {p.name} ({p.template})
                </option>
              ))}
            </select>

            {showNewProjectForm && (
              <form
                onSubmit={handleCreateProject}
                className="mt-2 p-2.5 rounded-lg bg-midnight-950 border border-slate-800 space-y-2"
              >
                <input
                  type="text"
                  placeholder="Project name..."
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-2 py-1 rounded bg-slate-900 border border-slate-700 text-xs text-slate-100"
                />
                <select
                  value={newProjectTemplate}
                  onChange={(e) =>
                    setNewProjectTemplate(
                      e.target.value as ProjectTemplateType
                    )
                  }
                  className="w-full px-2 py-1 rounded bg-slate-900 border border-slate-700 text-xs text-slate-200"
                >
                  <option value="python">Python (main.py + unittest)</option>
                  <option value="javascript">JavaScript (Node.js)</option>
                  <option value="typescript">TypeScript (tsconfig)</option>
                  <option value="web">HTML / CSS / JS Web</option>
                </select>
                <div className="flex justify-end gap-1.5">
                  <button
                    type="button"
                    onClick={() => setShowNewProjectForm(false)}
                    className="px-2 py-1 text-[11px] text-slate-400 hover:text-slate-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-2.5 py-1 rounded bg-cyan-600 text-white text-[11px] font-semibold"
                  >
                    Create
                  </button>
                </div>
              </form>
            )}
          </div>

          {/* File Explorer Tree */}
          <div className="flex-1 overflow-y-auto p-3 space-y-1">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Project Files ({activeProject?.files.length || 0})
              </span>
              <button
                onClick={() => setShowNewFileForm((prev) => !prev)}
                className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
              >
                <FilePlus className="w-3.5 h-3.5" />
                <span>Add File</span>
              </button>
            </div>

            {showNewFileForm && (
              <form
                onSubmit={handleCreateFile}
                className="mb-2 p-2 rounded-lg bg-midnight-950 border border-slate-800 space-y-1.5"
              >
                <input
                  type="text"
                  placeholder="e.g. utils.py or styles.css"
                  value={newFileName}
                  onChange={(e) => setNewFileName(e.target.value)}
                  className="w-full px-2 py-1 rounded bg-slate-900 border border-slate-700 text-xs text-slate-100"
                />
                <div className="flex justify-end gap-1.5">
                  <button
                    type="button"
                    onClick={() => setShowNewFileForm(false)}
                    className="px-2 py-0.5 text-[11px] text-slate-400"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-2 py-0.5 rounded bg-cyan-600 text-white text-[11px] font-semibold"
                  >
                    Create
                  </button>
                </div>
              </form>
            )}

            {activeProject?.files.map((file) => {
              const active =
                selectedFile?.relative_path === file.relative_path;
              return (
                <button
                  key={file.relative_path}
                  onClick={() => handleSelectFile(file)}
                  className={`w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-xs transition-all ${
                    active
                      ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/40 font-semibold'
                      : 'text-slate-300 hover:bg-slate-800/60'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <FileCode className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                    <span className="truncate">{file.relative_path}</span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {file.backup_count > 0 && (
                      <span
                        className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400"
                        title={`${file.backup_count} backup version(s)`}
                      >
                        v{file.backup_count}
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Runtime & Stage 17 Bridge Footer */}
          <div className="p-3 border-t border-slate-800/80 bg-midnight-950/60 space-y-2 text-[11px]">
            <div className="flex items-center justify-between text-slate-400">
              <span>Python Runtime</span>
              <span className="text-emerald-400 font-mono">
                {capabilities?.runtimes.python.version || '3.x'}
              </span>
            </div>
            <div className="flex items-center justify-between text-slate-400">
              <span>Network Policy</span>
              <span className="text-amber-300 flex items-center gap-1">
                <Lock className="w-3 h-3" /> Isolated
              </span>
            </div>
            <button
              onClick={handleSyncToStage17}
              className="w-full mt-1 flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-800 text-slate-200 border border-slate-700 text-xs transition-all"
            >
              <ArrowUpRight className="w-3.5 h-3.5 text-emerald-400" />
              <span>Sync to Stage 17 Files</span>
            </button>
          </div>
        </div>

        {/* Center + Bottom: Code Editor & Multi-Tab Developer Console */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0 overflow-hidden">
          {/* Code Editor Pane */}
          <div className="flex-1 flex flex-col min-h-[240px] border-b border-slate-800/80 overflow-hidden">
            {/* Editor File Tab Bar */}
            <div className="px-4 py-2 bg-midnight-900/80 border-b border-slate-800/80 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <Code2 className="w-4 h-4 text-cyan-400" />
                <span className="font-mono font-semibold text-slate-200">
                  {selectedFile?.relative_path || 'No file selected'}
                </span>
                {selectedFile && (
                  <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700">
                    {selectedFile.language}
                  </span>
                )}
                {isDirty && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300">
                    Unsaved changes
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 text-[11px] text-slate-400">
                <span>{lineCount} lines</span>
                <span>{editorContent.length} chars</span>
              </div>
            </div>

            {/* Line-numbered Code Textarea */}
            <div className="flex-1 flex overflow-hidden bg-slate-950 font-mono text-xs sm:text-sm">
              <div className="w-12 py-3 px-2 bg-midnight-950 border-r border-slate-800/80 text-right text-slate-600 select-none overflow-hidden">
                {Array.from({ length: lineCount }, (_, idx) => (
                  <div key={idx + 1} className="leading-6">
                    {idx + 1}
                  </div>
                ))}
              </div>
              <textarea
                value={editorContent}
                onChange={(e) => {
                  setEditorContent(e.target.value);
                  setIsDirty(true);
                }}
                spellCheck={false}
                className="flex-1 p-3 bg-slate-950 text-slate-100 leading-6 focus:outline-none resize-none overflow-y-auto font-mono"
                placeholder="Write or edit project code here..."
              />
            </div>
          </div>

          {/* Bottom Console, Controlled Terminal, Tests, Diagnostics & Debugger */}
          <div className="h-80 sm:h-96 flex flex-col bg-midnight-900/80 shrink-0 overflow-hidden">
            {/* Console Sub-Navigation */}
            <div className="px-4 border-b border-slate-800/80 flex items-center justify-between gap-2 overflow-x-auto bg-midnight-950/70">
              <div className="flex items-center gap-1 py-1.5">
                <button
                  onClick={() => setActiveTab('console')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    activeTab === 'console'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Console Output
                </button>
                <button
                  onClick={() => setActiveTab('terminal')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    activeTab === 'terminal'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Controlled Terminal
                </button>
                <button
                  onClick={() => setActiveTab('tests')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    activeTab === 'tests'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Test Results
                  {activeExecution?.test_results && (
                    <span className="ml-1.5 text-[10px] px-1.5 py-0.2 rounded-full bg-slate-800 text-cyan-300">
                      {activeExecution.test_results.passed}/
                      {activeExecution.test_results.total}
                    </span>
                  )}
                </button>
                <button
                  onClick={() => setActiveTab('diagnostics')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    activeTab === 'diagnostics'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Linter & Dependencies
                  {inspection && (
                    <span className="ml-1.5 text-[10px] px-1.5 py-0.2 rounded-full bg-slate-800 text-amber-300">
                      {inspection.diagnostics.length}
                    </span>
                  )}
                </button>
                <button
                  onClick={() => setActiveTab('debugger')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    activeTab === 'debugger'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  AI Debugger & Repair
                </button>
                <button
                  onClick={() => setActiveTab('backups')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    activeTab === 'backups'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Version Backups ({backups.length})
                </button>
              </div>

              {/* Execution Status Pill */}
              {activeExecution && (
                <div className="flex items-center gap-2 text-xs py-1">
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${
                      activeExecution.status === 'SUCCEEDED'
                        ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                        : activeExecution.status === 'WAITING_FOR_APPROVAL'
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                        : 'bg-red-500/15 text-red-300 border-red-500/30'
                    }`}
                  >
                    {activeExecution.status}
                  </span>
                  {activeExecution.exit_code !== null &&
                    activeExecution.exit_code !== undefined && (
                      <span className="font-mono text-slate-400">
                        exit={activeExecution.exit_code} ({activeExecution.duration_ms}ms)
                      </span>
                    )}
                </div>
              )}
            </div>

            {/* Tab Content Area */}
            <div className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-3">
              {/* Approval Gate Banner if WAITING_FOR_APPROVAL */}
              {activeExecution?.status === 'WAITING_FOR_APPROVAL' && (
                <div className="p-3 rounded-xl bg-amber-950/50 border border-amber-500/40 text-amber-200 font-sans flex flex-wrap items-center justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 font-bold text-xs text-amber-300">
                      <ShieldAlert className="w-4 h-4" />
                      <span>
                        Consequential Operation Requires Explicit User Approval
                      </span>
                    </div>
                    <p className="text-xs text-amber-100/90">
                      <strong>Command:</strong>{' '}
                      <code>{activeExecution.command_preview.raw_command}</code>{' '}
                      • <strong>Workspace:</strong>{' '}
                      <code>
                        {activeExecution.command_preview.target_workspace}
                      </code>
                    </p>
                    <p className="text-[11px] text-amber-200/80">
                      <strong>Reason:</strong>{' '}
                      {activeExecution.command_preview.approval_reason}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() =>
                        handleApproveExecution(
                          activeExecution.execution_id,
                          true
                        )
                      }
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
                    >
                      Approve & Execute
                    </button>
                    <button
                      onClick={() =>
                        handleApproveExecution(
                          activeExecution.execution_id,
                          false
                        )
                      }
                      className="px-3 py-1.5 rounded-lg bg-red-600/80 hover:bg-red-600 text-white text-xs font-semibold"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              )}

              {/* TAB 1: CONSOLE OUTPUT */}
              {activeTab === 'console' && (
                <div className="space-y-3">
                  {!activeExecution ? (
                    <p className="text-slate-500 font-sans">
                      Click <strong>Run</strong> or <strong>Test</strong> to execute project code inside the Stage 18 sandbox.
                    </p>
                  ) : (
                    <>
                      <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400 pb-2 border-b border-slate-800">
                        <span>
                          Command:{' '}
                          <strong className="text-slate-200">
                            {activeExecution.command_preview.raw_command}
                          </strong>
                        </span>
                        <span>•</span>
                        <span>
                          Verified Execution:{' '}
                          <strong className="text-emerald-400">
                            {activeExecution.verified_execution ? 'YES' : 'NO'}
                          </strong>
                        </span>
                        <span>•</span>
                        <span>
                          Memory Limit: {activeExecution.memory_limit_mb}MB
                        </span>
                      </div>

                      {activeExecution.stdout && (
                        <div>
                          <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">
                            Standard Output (stdout)
                          </div>
                          <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-emerald-300 whitespace-pre-wrap overflow-x-auto">
                            {activeExecution.stdout}
                          </pre>
                        </div>
                      )}

                      {activeExecution.stderr && (
                        <div>
                          <div className="text-[10px] uppercase tracking-wider text-red-400 mb-1">
                            Standard Error (stderr)
                          </div>
                          <pre className="p-3 rounded-lg bg-red-950/30 border border-red-500/30 text-red-300 whitespace-pre-wrap overflow-x-auto">
                            {activeExecution.stderr}
                          </pre>
                        </div>
                      )}

                      {activeExecution.error_diagnosis && (
                        <div className="p-3 rounded-lg bg-slate-900 border border-amber-500/30 font-sans space-y-1">
                          <div className="text-xs font-semibold text-amber-300 flex items-center gap-1.5">
                            <AlertTriangle className="w-4 h-4" />
                            <span>
                              Failure Diagnosis: {activeExecution.error_diagnosis}
                            </span>
                          </div>
                          {activeExecution.suggested_fix && (
                            <p className="text-xs text-slate-300">
                              <strong>Suggested Fix:</strong>{' '}
                              {activeExecution.suggested_fix}
                            </p>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* TAB 2: CONTROLLED TERMINAL */}
              {activeTab === 'terminal' && (
                <div className="space-y-3 font-sans">
                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                    <div className="flex-1 flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 font-mono">
                      <ChevronRight className="w-4 h-4 text-cyan-400 shrink-0" />
                      <input
                        type="text"
                        value={terminalInput}
                        onChange={(e) => setTerminalInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleRunTerminalCommand();
                        }}
                        placeholder="Enter allowlisted command (e.g. ls, cat main.py, pytest, pip install requests)..."
                        className="flex-1 bg-transparent text-xs text-slate-100 focus:outline-none"
                      />
                    </div>
                    <label className="flex items-center gap-1.5 text-xs text-slate-300 px-2">
                      <input
                        type="checkbox"
                        checked={allowNetworkToggle}
                        onChange={(e) =>
                          setAllowNetworkToggle(e.target.checked)
                        }
                      />
                      <span>Allow Network (Requires Approval)</span>
                    </label>
                    <button
                      onClick={handleRunTerminalCommand}
                      disabled={isRunning}
                      className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold"
                    >
                      Execute Command
                    </button>
                  </div>

                  {/* Live Pre-Execution Classification Preview */}
                  {commandPreview && (
                    <div className="p-2.5 rounded-lg bg-midnight-950 border border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs">
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            commandPreview.classification === 'allowed_safe'
                              ? 'bg-emerald-500/20 text-emerald-300'
                              : commandPreview.classification ===
                                'requires_approval'
                              ? 'bg-amber-500/20 text-amber-300'
                              : 'bg-red-500/20 text-red-300'
                          }`}
                        >
                          {commandPreview.classification}
                        </span>
                        <span className="text-slate-300">
                          {commandPreview.expected_effect}
                        </span>
                      </div>
                      <span className="text-slate-500 font-mono text-[11px]">
                        Target: {commandPreview.target_workspace}
                      </span>
                    </div>
                  )}

                  {/* Recent Terminal History */}
                  <div className="space-y-2">
                    {executions.slice(0, 8).map((ex) => (
                      <div
                        key={ex.execution_id}
                        onClick={() => setActiveExecution(ex)}
                        className="p-2.5 rounded-lg bg-slate-950/90 border border-slate-800/80 hover:border-slate-700 cursor-pointer space-y-1 font-mono"
                      >
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-cyan-300 font-semibold">
                            $ {ex.command_preview.raw_command}
                          </span>
                          <span className="text-slate-400">
                            {ex.status} (exit={ex.exit_code ?? 'pending'})
                          </span>
                        </div>
                        {(ex.stdout || ex.stderr) && (
                          <pre className="text-[11px] text-slate-300 whitespace-pre-wrap line-clamp-3">
                            {(ex.stdout || ex.stderr).trim()}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 3: TEST RESULTS */}
              {activeTab === 'tests' && (
                <div className="space-y-3 font-sans">
                  {!activeExecution?.test_results ? (
                    <p className="text-slate-400">
                      Click <strong>Test</strong> in the toolbar to run the project unit test suite.
                    </p>
                  ) : (
                    <>
                      <div className="p-3 rounded-xl bg-midnight-950 border border-slate-800 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {activeExecution.test_results.all_passed ? (
                            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                          ) : (
                            <XCircle className="w-5 h-5 text-red-400" />
                          )}
                          <span className="font-bold text-sm text-slate-100">
                            {activeExecution.test_results.raw_summary}
                          </span>
                        </div>
                        <span className="text-xs text-slate-400">
                          Framework: {activeExecution.test_results.framework}
                        </span>
                      </div>

                      <div className="space-y-1.5">
                        {activeExecution.test_results.cases.map((tc, i) => (
                          <div
                            key={i}
                            className="px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs"
                          >
                            <span className="font-mono text-slate-200">
                              {tc.name}
                            </span>
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                tc.status === 'passed'
                                  ? 'bg-emerald-500/20 text-emerald-300'
                                  : 'bg-red-500/20 text-red-300'
                              }`}
                            >
                              {tc.status}
                            </span>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* TAB 4: DIAGNOSTICS, LINTER & MISSING DEPENDENCIES */}
              {activeTab === 'diagnostics' && (
                <div className="space-y-4 font-sans">
                  {!inspection ? (
                    <p className="text-slate-400">
                      Click <strong>Check & Lint</strong> to run AST syntax analysis, linter rules, and dependency inspection.
                    </p>
                  ) : (
                    <>
                      <div className="p-3 rounded-xl bg-midnight-950 border border-slate-800 flex items-center justify-between">
                        <span className="font-semibold text-slate-200">
                          {inspection.summary}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            inspection.syntax_valid
                              ? 'bg-emerald-500/20 text-emerald-300'
                              : 'bg-red-500/20 text-red-300'
                          }`}
                        >
                          {inspection.syntax_valid
                            ? 'Syntax Valid'
                            : 'Syntax Error'}
                        </span>
                      </div>

                      {inspection.diagnostics.length > 0 && (
                        <div className="space-y-2">
                          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                            Diagnostics & Lint Findings
                          </h4>
                          {inspection.diagnostics.map((d, idx) => (
                            <div
                              key={idx}
                              className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1"
                            >
                              <div className="flex items-center justify-between text-xs">
                                <span className="font-semibold text-amber-300">
                                  Line {d.line}:{d.column} [{d.code}] —{' '}
                                  {d.message}
                                </span>
                                <span className="text-[10px] uppercase text-slate-500">
                                  {d.severity}
                                </span>
                              </div>
                              {d.suggestion && (
                                <p className="text-[11px] text-slate-400">
                                  Suggestion: {d.suggestion}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="space-y-2">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                          <Package className="w-3.5 h-3.5 text-cyan-400" />
                          <span>
                            Detected Dependencies ({inspection.dependencies.length})
                          </span>
                        </h4>
                        {inspection.dependencies.map((dep) => (
                          <div
                            key={dep.package_name}
                            className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs"
                          >
                            <div>
                              <span className="font-mono font-bold text-slate-200">
                                {dep.package_name}
                              </span>{' '}
                              <span className="text-slate-500">
                                ({dep.ecosystem})
                              </span>
                              <p className="text-[11px] text-slate-400">
                                {dep.setup_explanation}
                              </p>
                            </div>
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                dep.installed
                                  ? 'bg-emerald-500/20 text-emerald-300'
                                  : 'bg-red-500/20 text-red-300'
                              }`}
                            >
                              {dep.installed
                                ? `Installed (${dep.version || 'ok'})`
                                : 'Missing'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* TAB 5: AI DEBUGGER & BOUNDED REPAIR TRACE */}
              {activeTab === 'debugger' && (
                <div className="space-y-3 font-sans">
                  {!repairReport ? (
                    <p className="text-slate-400">
                      Click <strong>Auto-Debug & Repair</strong> to inspect failures, create a version backup, apply bounded fixes, and re-verify tests.
                    </p>
                  ) : (
                    <>
                      <div className="p-3 rounded-xl bg-midnight-950 border border-slate-800 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-sm text-slate-100">
                            Status: {repairReport.status}
                          </span>
                          <span className="text-xs text-slate-400">
                            Attempts: {repairReport.attempts_used} /{' '}
                            {repairReport.max_attempts}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300">
                          {repairReport.explanation}
                        </p>
                        {repairReport.intervention_reason && (
                          <p className="text-xs text-amber-300">
                            <strong>User Intervention Required:</strong>{' '}
                            {repairReport.intervention_reason}
                          </p>
                        )}
                      </div>

                      {repairReport.iterations.map((step) => (
                        <div
                          key={step.attempt_number}
                          className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1 text-xs"
                        >
                          <div className="flex items-center justify-between font-semibold text-cyan-300">
                            <span>
                              Attempt #{step.attempt_number}: {step.failure_type}
                            </span>
                            <span>
                              {step.tests_passed
                                ? 'VERIFIED PASSED'
                                : 'NEEDS INTERVENTION'}
                            </span>
                          </div>
                          <p className="text-slate-300">{step.diagnosis}</p>
                          <p className="text-slate-400">
                            {step.proposed_patch_summary}
                            {step.backup_id && ` (Backup: ${step.backup_id})`}
                          </p>
                        </div>
                      ))}
                    </>
                  )}
                </div>
              )}

              {/* TAB 6: VERSION BACKUPS */}
              {activeTab === 'backups' && (
                <div className="space-y-2 font-sans">
                  {backups.length === 0 ? (
                    <p className="text-slate-400">
                      No file backups recorded yet. Backups are created automatically before edits and automated repairs.
                    </p>
                  ) : (
                    backups.map((bk) => (
                      <div
                        key={bk.backup_id}
                        className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between gap-2 text-xs"
                      >
                        <div>
                          <div className="font-mono font-semibold text-slate-200">
                            {bk.relative_path} (v{bk.version_number})
                          </div>
                          <div className="text-[11px] text-slate-400">
                            Reason: {bk.reason} • {bk.size_bytes} bytes •{' '}
                            {new Date(bk.created_at).toLocaleTimeString()}
                          </div>
                        </div>
                        <button
                          onClick={() => handleRestoreBackup(bk)}
                          className="flex items-center gap-1 px-2.5 py-1 rounded bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/30 text-xs font-semibold"
                        >
                          <History className="w-3.5 h-3.5" />
                          <span>Restore</span>
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
