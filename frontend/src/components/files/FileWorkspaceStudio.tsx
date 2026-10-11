import React, { useEffect, useState, useCallback } from 'react';
import {
  FolderOpen,
  FileText,
  Search,
  Plus,
  FolderPlus,
  Trash2,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  RefreshCw,
  ArrowRightLeft,
  Copy,
  Layers,
  History,
  Database,
  Globe,
  FileSpreadsheet,
  FileCode,
  Folder,
  Save,
  Eye,
  XCircle,
} from 'lucide-react';
import { api } from '../../services/api';
import {
  ComputerExecutionSession,
  DuplicateFileGroup,
  FileCategory,
  FileOperationRecord,
  FileWorkspaceCapabilitiesResponse,
  OrganizeRuleStrategy,
  WorkspaceFileItem,
  WorkspaceFileReadResponse,
  WorkspaceTrashItem,
} from '../../types';
import { useChat } from '../../context/ChatContext';

export const FileWorkspaceStudio: React.FC = () => {
  const { showToast } = useChat();

  const [activeSubTab, setActiveSubTab] = useState<
    'explorer' | 'automation' | 'trash' | 'operations'
  >('explorer');

  const [capabilities, setCapabilities] =
    useState<FileWorkspaceCapabilitiesResponse | null>(null);
  const [files, setFiles] = useState<WorkspaceFileItem[]>([]);
  const [selectedFile, setSelectedFile] =
    useState<WorkspaceFileReadResponse | null>(null);
  const [editorContent, setEditorContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [searchInContent, setSearchInContent] = useState<boolean>(true);
  const [stage4Matches, setStage4Matches] = useState<
    { doc_id: string; filename: string; page_number: number; score: number; snippet: string }[]
  >([]);

  // Create File / Folder State
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [newFilePath, setNewFilePath] = useState<string>('notes/project_notes.md');
  const [newFileContent, setNewFileContent] = useState<string>(
    '# Project Notes\n\nCreated in NEXORA Stage 17 File Workspace.\n'
  );
  const [newFolderName, setNewFolderName] = useState<string>('');

  // Transfer (Rename / Copy / Move) State
  const [transferAction, setTransferAction] = useState<'rename' | 'copy' | 'move'>('rename');
  const [transferDestPath, setTransferDestPath] = useState<string>('');

  // Automation / Duplicate / Organize State
  const [organizeStrategy, setOrganizeStrategy] =
    useState<OrganizeRuleStrategy>('by_category');
  const [organizePreview, setOrganizePreview] =
    useState<FileOperationRecord | null>(null);
  const [duplicates, setDuplicates] = useState<DuplicateFileGroup[]>([]);
  const [browserSessions, setBrowserSessions] = useState<ComputerExecutionSession[]>([]);
  const [selectedBrowserSessionId, setSelectedBrowserSessionId] = useState<string>('');
  const [browserImportFilename, setBrowserImportFilename] = useState<string>(
    'captures/browser_capture.md'
  );

  // Trash & Operations State
  const [trashItems, setTrashItems] = useState<WorkspaceTrashItem[]>([]);
  const [operations, setOperations] = useState<FileOperationRecord[]>([]);
  const [showSecurityBoundaries, setShowSecurityBoundaries] = useState<boolean>(false);

  const loadWorkspaceData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [caps, items, trash, ops] = await Promise.all([
        api.getFileWorkspaceCapabilities(),
        api.listWorkspaceFiles(),
        api.listWorkspaceTrash(),
        api.listFileOperations('default_user', 50),
      ]);
      setCapabilities(caps);
      setFiles(items);
      setTrashItems(trash);
      setOperations(ops);
    } catch (err: any) {
      showToast(err.message || 'Failed to load File Workspace', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    loadWorkspaceData();
  }, [loadWorkspaceData]);

  const handleSelectFile = async (item: WorkspaceFileItem) => {
    if (item.is_dir) return;
    try {
      const res = await api.readWorkspaceFile(item.relative_path);
      setSelectedFile(res);
      setEditorContent(res.content);
      setTransferDestPath(item.relative_path);
    } catch (err: any) {
      showToast(err.message || 'Failed to read file', 'error');
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim() && categoryFilter === 'all') {
      setStage4Matches([]);
      await loadWorkspaceData();
      return;
    }
    setIsLoading(true);
    try {
      const res = await api.searchWorkspaceFiles({
        query: searchQuery,
        category:
          categoryFilter !== 'all' ? (categoryFilter as FileCategory) : undefined,
        search_content: searchInContent,
        include_stage4_indexed: true,
      });
      setFiles(res.items);
      setStage4Matches(res.stage4_indexed_matches || []);
    } catch (err: any) {
      showToast(err.message || 'Search failed', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    try {
      const op = await api.createWorkspaceFolder(newFolderName.trim());
      showToast(op.summary, 'success');
      setNewFolderName('');
      await loadWorkspaceData();
    } catch (err: any) {
      showToast(err.message || 'Failed to create folder', 'error');
    }
  };

  const handleCreateNewFile = async () => {
    if (!newFilePath.trim()) return;
    try {
      const op = await api.writeWorkspaceFile({
        relative_path: newFilePath.trim(),
        content: newFileContent,
        overwrite: false,
      });
      showToast(op.summary, 'success');
      setShowCreateModal(false);
      await loadWorkspaceData();
      const created = await api.readWorkspaceFile(newFilePath.trim());
      setSelectedFile(created);
      setEditorContent(created.content);
    } catch (err: any) {
      showToast(err.message || 'Failed to create file', 'error');
    }
  };

  const handleSaveEditedFile = async (requireApprovalGate = false) => {
    if (!selectedFile) return;
    try {
      const op = await api.writeWorkspaceFile({
        relative_path: selectedFile.item.relative_path,
        content: editorContent,
        overwrite: true,
        confirmed_overwrite: !requireApprovalGate,
        backup_reason: 'user_editor_save_with_version_backup',
      });
      if (op.status === 'WAITING_FOR_APPROVAL') {
        showToast('Overwrite queued for confirmation in Approval Banner.', 'info');
      } else {
        showToast(op.summary, 'success');
        const refreshed = await api.readWorkspaceFile(
          selectedFile.item.relative_path
        );
        setSelectedFile(refreshed);
      }
      await loadWorkspaceData();
    } catch (err: any) {
      showToast(err.message || 'Failed to save file', 'error');
    }
  };

  const handleTransferItem = async () => {
    if (!selectedFile || !transferDestPath.trim()) return;
    try {
      const op = await api.transferWorkspaceItem({
        action: transferAction,
        source_path: selectedFile.item.relative_path,
        destination_path: transferDestPath.trim(),
        overwrite: true,
        confirmed_overwrite: false,
      });
      if (op.status === 'WAITING_FOR_APPROVAL') {
        showToast(op.summary, 'info');
      } else {
        showToast(op.summary, 'success');
        const refreshed = await api.readWorkspaceFile(transferDestPath.trim());
        setSelectedFile(refreshed);
        setEditorContent(refreshed.content);
      }
      await loadWorkspaceData();
    } catch (err: any) {
      showToast(err.message || 'File transfer failed', 'error');
    }
  };

  const handleConvertFile = async (
    targetFormat: 'txt' | 'md' | 'csv' | 'json' | 'docx' | 'xlsx'
  ) => {
    if (!selectedFile) return;
    try {
      const op = await api.convertWorkspaceFile({
        source_path: selectedFile.item.relative_path,
        target_format: targetFormat,
        overwrite: true,
        confirmed_overwrite: true,
      });
      showToast(op.summary, 'success');
      await loadWorkspaceData();
      if (op.result_data?.destination_path) {
        const converted = await api.readWorkspaceFile(
          op.result_data.destination_path
        );
        setSelectedFile(converted);
        setEditorContent(converted.content);
      }
    } catch (err: any) {
      showToast(err.message || 'Conversion failed', 'error');
    }
  };

  const handleRestoreVersion = async (versionId: string) => {
    if (!selectedFile) return;
    try {
      const op = await api.restoreWorkspaceFileVersion(
        versionId,
        selectedFile.item.relative_path
      );
      showToast(op.summary, 'success');
      const refreshed = await api.readWorkspaceFile(
        selectedFile.item.relative_path
      );
      setSelectedFile(refreshed);
      setEditorContent(refreshed.content);
      await loadWorkspaceData();
    } catch (err: any) {
      showToast(err.message || 'Failed to restore version', 'error');
    }
  };

  const handleSyncToStage4 = async (relPath: string) => {
    try {
      const op = await api.syncWorkspaceFileToStage4(relPath);
      showToast(op.summary, 'success');
      await loadWorkspaceData();
      if (selectedFile && selectedFile.item.relative_path === relPath) {
        const refreshed = await api.readWorkspaceFile(relPath);
        setSelectedFile(refreshed);
      }
    } catch (err: any) {
      showToast(err.message || 'Stage 4 sync failed', 'error');
    }
  };

  const handleRequestDeleteToTrash = async (relPath: string) => {
    try {
      const op = await api.deleteWorkspaceItemsToTrash({
        paths: [relPath],
        reason: 'user_workspace_delete',
        confirmed: false,
      });
      showToast(op.summary, 'info');
      await loadWorkspaceData();
    } catch (err: any) {
      showToast(err.message || 'Delete request failed', 'error');
    }
  };

  const handleApproveOperation = async (
    operationId: string,
    approved: boolean
  ) => {
    try {
      const op = await api.approveFileOperation(operationId, {
        approved,
        user_note: approved ? 'User confirmed in File Workspace UI' : 'User cancelled',
      });
      showToast(op.summary, approved ? 'success' : 'info');
      await loadWorkspaceData();
      if (selectedFile) {
        try {
          const refreshed = await api.readWorkspaceFile(
            selectedFile.item.relative_path
          );
          setSelectedFile(refreshed);
          setEditorContent(refreshed.content);
        } catch {
          setSelectedFile(null);
        }
      }
    } catch (err: any) {
      showToast(err.message || 'Approval action failed', 'error');
    }
  };

  const handleRollbackOperation = async (operationId: string) => {
    try {
      const op = await api.rollbackFileOperation(operationId);
      showToast(`Rolled back: ${op.verification_detail}`, 'success');
      await loadWorkspaceData();
    } catch (err: any) {
      showToast(err.message || 'Rollback failed', 'error');
    }
  };

  const handleRestoreTrashItem = async (trashId: string) => {
    try {
      const op = await api.restoreWorkspaceTrashItem(trashId);
      showToast(op.summary, 'success');
      await loadWorkspaceData();
    } catch (err: any) {
      showToast(err.message || 'Trash restore failed', 'error');
    }
  };

  const handleScanDuplicates = async () => {
    try {
      const groups = await api.findWorkspaceDuplicates();
      setDuplicates(groups);
      showToast(
        `Scanned workspace by SHA-256 content hash: ${groups.length} duplicate group(s) found.`,
        'info'
      );
    } catch (err: any) {
      showToast(err.message || 'Duplicate scan failed', 'error');
    }
  };

  const handleCleanupDuplicates = async () => {
    try {
      const op = await api.cleanupWorkspaceDuplicates({
        confirmed: false,
      });
      showToast(op.summary, 'info');
      await loadWorkspaceData();
    } catch (err: any) {
      showToast(err.message || 'Duplicate cleanup failed', 'error');
    }
  };

  const handleOrganizeWorkspace = async (previewOnly: boolean) => {
    try {
      const op = await api.organizeWorkspaceFiles({
        strategy: organizeStrategy,
        preview_only: previewOnly,
        confirmed: false,
      });
      setOrganizePreview(op);
      showToast(op.summary, 'info');
      await loadWorkspaceData();
    } catch (err: any) {
      showToast(err.message || 'Organization failed', 'error');
    }
  };

  const loadBrowserSessionsForImport = async () => {
    try {
      const sessions = await api.getComputerSessions();
      setBrowserSessions(sessions);
      if (sessions.length > 0 && !selectedBrowserSessionId) {
        setSelectedBrowserSessionId(sessions[0].session_id);
      }
    } catch {
      // ignore if none
    }
  };

  useEffect(() => {
    if (activeSubTab === 'automation') {
      handleScanDuplicates();
      loadBrowserSessionsForImport();
    }
  }, [activeSubTab]);

  const handleImportBrowserSession = async () => {
    if (!selectedBrowserSessionId || !browserImportFilename.trim()) return;
    try {
      const op = await api.importStage16BrowserSessionToFile({
        session_id: selectedBrowserSessionId,
        target_filename: browserImportFilename.trim(),
      });
      showToast(op.summary, 'success');
      await loadWorkspaceData();
    } catch (err: any) {
      showToast(err.message || 'Browser import failed', 'error');
    }
  };

  const pendingApprovals = operations.filter(
    (op) => op.status === 'WAITING_FOR_APPROVAL'
  );

  const renderCategoryIcon = (item: WorkspaceFileItem) => {
    if (item.is_dir) return <Folder className="w-4 h-4 text-amber-400" />;
    switch (item.category) {
      case 'spreadsheet':
        return <FileSpreadsheet className="w-4 h-4 text-emerald-400" />;
      case 'code':
      case 'data':
        return <FileCode className="w-4 h-4 text-cyan-400" />;
      default:
        return <FileText className="w-4 h-4 text-indigo-400" />;
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden">
      {/* Header Banner */}
      <div className="border-b border-slate-800 bg-slate-900/70 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              <FolderOpen className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-white">
                  File Management & Workspace Automation
                </h1>
                <span className="px-2 py-0.5 text-[11px] font-semibold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  STAGE 17 VERIFIED
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Sandboxed Workspace:{' '}
                <code className="text-emerald-300">
                  {capabilities?.authorized_workspace_root ||
                    'data/file_workspace/default_user'}
                </code>{' '}
                • Auto-Backup Versions • SHA-256 Deduplication • Recoverable Trash
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSecurityBoundaries(!showSecurityBoundaries)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            Security Boundaries
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
          >
            <Plus className="w-3.5 h-3.5" />
            New File
          </button>
          <button
            onClick={loadWorkspaceData}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
            title="Refresh Workspace"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Collapsible Security Boundaries Disclosure */}
      {showSecurityBoundaries && capabilities && (
        <div className="bg-slate-900/90 border-b border-slate-800 px-6 py-3 text-xs text-slate-300 space-y-1.5">
          <div className="font-semibold text-emerald-400 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4" />
            Stage 17 Workspace Security & Isolation Guarantees
          </div>
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-1 text-slate-400 list-disc list-inside">
            {capabilities.security_boundaries.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Pending Approval Gate Banner */}
      {pendingApprovals.length > 0 && (
        <div className="bg-amber-950/50 border-b border-amber-500/40 px-6 py-3 space-y-2">
          {pendingApprovals.map((op) => (
            <div
              key={op.operation_id}
              className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/90 border border-amber-500/40 rounded-lg p-3"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-xs font-bold text-amber-300">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  APPROVAL REQUIRED: {op.operation_type.toUpperCase()} (
                  {op.preview?.affected_count || op.affected_paths.length} item(s))
                </div>
                <p className="text-xs text-slate-300">
                  {op.approval_reason || op.summary}
                </p>
                {op.preview && op.preview.planned_changes.length > 0 && (
                  <div className="text-[11px] text-slate-400 font-mono max-h-20 overflow-y-auto">
                    {op.preview.planned_changes.slice(0, 5).map((ch, idx) => (
                      <div key={idx}>
                        • [{ch.action}] {ch.source_path}
                        {ch.destination_path ? ` → ${ch.destination_path}` : ''} (
                        {ch.size_bytes}B)
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleApproveOperation(op.operation_id, true)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Approve & Execute
                </button>
                <button
                  onClick={() => handleApproveOperation(op.operation_id, false)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  Cancel
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Sub-navigation Tabs */}
      <div className="border-b border-slate-800 bg-slate-900/40 px-6 flex items-center gap-2">
        {[
          {
            id: 'explorer',
            label: `Files & Editor (${files.length})`,
            icon: FolderOpen,
          },
          {
            id: 'automation',
            label: 'Smart Organize & Duplicates',
            icon: Layers,
          },
          {
            id: 'trash',
            label: `Recoverable Trash (${trashItems.length})`,
            icon: Trash2,
          },
          {
            id: 'operations',
            label: `Operation Logs & Rollback (${operations.length})`,
            icon: History,
          },
        ].map((t) => {
          const Icon = t.icon;
          const active = activeSubTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveSubTab(t.id as any)}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
                active
                  ? 'border-emerald-400 text-emerald-300 bg-emerald-500/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeSubTab === 'explorer' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full">
            {/* Left Column: Explorer, Search, Filters */}
            <div className="lg:col-span-5 flex flex-col gap-4 bg-slate-900/60 border border-slate-800 rounded-xl p-4">
              {/* Search & Filter Controls */}
              <div className="space-y-2.5">
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                      placeholder="Search filenames or indexed content..."
                      className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-800 text-slate-100"
                    />
                  </div>
                  <button
                    onClick={handleSearch}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
                  >
                    Search
                  </button>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <select
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    className="px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-slate-300"
                  >
                    <option value="all">All Categories</option>
                    <option value="markdown_text">Notes / Markdown / TXT</option>
                    <option value="spreadsheet">Spreadsheets (CSV / XLSX)</option>
                    <option value="document">Documents (PDF / DOCX)</option>
                    <option value="data">Structured Data (JSON / YAML)</option>
                    <option value="code">Code Scripts</option>
                    <option value="folder">Folders</option>
                  </select>

                  <label className="flex items-center gap-1.5 text-slate-400 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={searchInContent}
                      onChange={(e) => setSearchInContent(e.target.checked)}
                      className="rounded border-slate-700"
                    />
                    Include full-text & Stage 4 index
                  </label>
                </div>

                {/* New Folder Quick Bar */}
                <div className="flex gap-2 pt-1">
                  <input
                    type="text"
                    value={newFolderName}
                    onChange={(e) => setNewFolderName(e.target.value)}
                    placeholder="New folder path (e.g. reports/2026)..."
                    className="flex-1 px-2.5 py-1 text-xs rounded-lg bg-slate-950 border border-slate-800 text-slate-200"
                  />
                  <button
                    onClick={handleCreateFolder}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
                  >
                    <FolderPlus className="w-3.5 h-3.5 text-amber-400" />
                    Create Folder
                  </button>
                </div>
              </div>

              {/* File & Folder List */}
              <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60 border border-slate-800/80 rounded-lg bg-slate-950/60">
                {files.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500">
                    No matching files or folders in workspace.
                  </div>
                ) : (
                  files.map((item) => {
                    const isSelected =
                      selectedFile?.item.relative_path === item.relative_path;
                    return (
                      <div
                        key={item.relative_path}
                        onClick={() => handleSelectFile(item)}
                        className={`p-3 flex items-center justify-between gap-2 transition-colors ${
                          item.is_dir
                            ? 'bg-slate-900/30 cursor-default'
                            : 'cursor-pointer hover:bg-slate-900/80'
                        } ${
                          isSelected
                            ? 'bg-emerald-950/30 border-l-2 border-emerald-400'
                            : ''
                        }`}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            {renderCategoryIcon(item)}
                            <span className="text-xs font-medium text-slate-100 truncate">
                              {item.relative_path}
                            </span>
                            {item.version_count > 0 && (
                              <span className="px-1.5 py-0.5 text-[10px] rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                                {item.version_count} backup(s)
                              </span>
                            )}
                            {item.indexed_doc_id && (
                              <span className="px-1.5 py-0.5 text-[10px] rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                Stage 4 Indexed
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-3 mt-1 text-[11px] text-slate-500">
                            <span>
                              {item.is_dir ? 'Folder' : `${item.size_bytes} B`}
                            </span>
                            {item.sha256_hash && (
                              <span className="font-mono">
                                sha256:{item.sha256_hash.slice(0, 10)}
                              </span>
                            )}
                          </div>
                          {item.snippet_match && (
                            <div className="mt-1 text-[11px] text-emerald-300/90 bg-emerald-950/30 px-2 py-0.5 rounded truncate">
                              {item.snippet_match}
                            </div>
                          )}
                        </div>

                        <div
                          className="flex items-center gap-1"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {!item.is_dir && item.is_processable_document && (
                            <button
                              onClick={() =>
                                handleSyncToStage4(item.relative_path)
                              }
                              title="Index in Stage 4 Document Vault"
                              className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-emerald-400"
                            >
                              <Database className="w-3.5 h-3.5" />
                            </button>
                          )}
                          <button
                            onClick={() =>
                              handleRequestDeleteToTrash(item.relative_path)
                            }
                            title="Move to Recoverable Trash (Requires Approval)"
                            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-rose-400"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Stage 4 Indexed Matches if present */}
              {stage4Matches.length > 0 && (
                <div className="border border-emerald-500/30 bg-emerald-950/20 rounded-lg p-3 space-y-1.5">
                  <div className="text-xs font-semibold text-emerald-300 flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5" />
                    Stage 4 Document Intelligence Matches ({stage4Matches.length})
                  </div>
                  {stage4Matches.map((m, i) => (
                    <div
                      key={i}
                      className="text-[11px] text-slate-300 bg-slate-950/60 p-2 rounded"
                    >
                      <span className="font-semibold text-emerald-400">
                        {m.filename} (p.{m.page_number})
                      </span>
                      : {m.snippet}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Right Column: File Inspector, Editor, Conversions & Version History */}
            <div className="lg:col-span-7 flex flex-col gap-4 bg-slate-900/60 border border-slate-800 rounded-xl p-4">
              {!selectedFile ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-12 text-slate-500">
                  <Eye className="w-10 h-10 mb-3 text-slate-600" />
                  <p className="text-sm font-medium text-slate-300">
                    Select a file from the workspace explorer
                  </p>
                  <p className="text-xs text-slate-500 mt-1 max-w-md">
                    Inspect verified SHA-256 hashes, edit text/Markdown/JSON/CSV
                    files with automatic backup snapshots, convert between
                    DOCX/XLSX/CSV/JSON/MD, or restore historical versions.
                  </p>
                </div>
              ) : (
                <>
                  {/* File Metadata & Action Header */}
                  <div className="border-b border-slate-800 pb-3 flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-white">
                          {selectedFile.item.relative_path}
                        </span>
                        <span className="px-2 py-0.5 text-[10px] rounded bg-slate-800 text-slate-300 uppercase">
                          {selectedFile.item.category}
                        </span>
                        {selectedFile.untrusted_content_isolated && (
                          <span className="px-2 py-0.5 text-[10px] rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                            &lt;untrusted_file_content&gt; isolated
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono mt-1">
                        Size: {selectedFile.item.size_bytes} bytes • SHA-256:{' '}
                        {selectedFile.item.sha256_hash}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {selectedFile.item.is_editable_text && (
                        <>
                          <button
                            onClick={() => handleSaveEditedFile(false)}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
                          >
                            <Save className="w-3.5 h-3.5" />
                            Save & Backup Original
                          </button>
                          <button
                            onClick={() => handleSaveEditedFile(true)}
                            className="px-2.5 py-1.5 rounded-lg text-xs bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30"
                            title="Queue overwrite in Approval Gate first"
                          >
                            Preview Overwrite
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Rename / Move / Copy & Format Conversion Bar */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                    <div className="flex items-center gap-1.5">
                      <select
                        value={transferAction}
                        onChange={(e) => setTransferAction(e.target.value as any)}
                        className="px-2 py-1 text-xs rounded bg-slate-900 border border-slate-700 text-slate-200"
                      >
                        <option value="rename">Rename</option>
                        <option value="move">Move</option>
                        <option value="copy">Copy</option>
                      </select>
                      <input
                        type="text"
                        value={transferDestPath}
                        onChange={(e) => setTransferDestPath(e.target.value)}
                        className="flex-1 px-2 py-1 text-xs rounded bg-slate-900 border border-slate-700 text-slate-200"
                        placeholder="Destination path..."
                      />
                      <button
                        onClick={handleTransferItem}
                        className="px-2.5 py-1 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
                      >
                        Apply
                      </button>
                    </div>

                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-[11px] text-slate-400 flex items-center gap-1">
                        <ArrowRightLeft className="w-3 h-3" /> Convert to:
                      </span>
                      {selectedFile.item.supported_conversions.map((fmt) => (
                        <button
                          key={fmt}
                          onClick={() => handleConvertFile(fmt as any)}
                          className="px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 border border-indigo-500/30 uppercase"
                        >
                          .{fmt}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Text Editor / Parsed Content View */}
                  <div className="flex-1 flex flex-col min-h-[240px]">
                    <textarea
                      value={editorContent}
                      onChange={(e) => setEditorContent(e.target.value)}
                      readOnly={!selectedFile.item.is_editable_text}
                      className="w-full flex-1 p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  {/* Version History & Backup Restoration */}
                  <div className="border-t border-slate-800 pt-3">
                    <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
                      <History className="w-3.5 h-3.5 text-indigo-400" />
                      Immutable Backup Snapshots (.nexora_versions) —{' '}
                      {selectedFile.versions.length} saved
                    </div>
                    {selectedFile.versions.length === 0 ? (
                      <p className="text-[11px] text-slate-500">
                        No prior edits yet. Editing and saving this file
                        automatically preserves the original in{' '}
                        <code>.nexora_versions</code>.
                      </p>
                    ) : (
                      <div className="space-y-1.5 max-h-36 overflow-y-auto">
                        {selectedFile.versions.map((ver) => (
                          <div
                            key={ver.version_id}
                            className="flex items-center justify-between bg-slate-950/80 border border-slate-800 px-3 py-1.5 rounded text-xs"
                          >
                            <div>
                              <span className="font-semibold text-indigo-300">
                                Version #{ver.version_number}
                              </span>{' '}
                              <span className="text-slate-400">
                                ({ver.size_bytes}B • sha256:
                                {ver.sha256_hash.slice(0, 10)})
                              </span>{' '}
                              <span className="text-slate-500">
                                — {ver.reason}
                              </span>
                            </div>
                            <button
                              onClick={() =>
                                handleRestoreVersion(ver.version_id)
                              }
                              className="flex items-center gap-1 px-2 py-0.5 rounded bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 text-[11px]"
                            >
                              <RotateCcw className="w-3 h-3" />
                              Restore v{ver.version_number}
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {activeSubTab === 'automation' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Rule-Based Workspace Organizer */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-emerald-400" />
                <div>
                  <h2 className="text-sm font-bold text-white">
                    Rule-Based Workspace Organizer
                  </h2>
                  <p className="text-xs text-slate-400">
                    Preview planned folder structure changes before moving files.
                    Supports 1-click rollback.
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <select
                  value={organizeStrategy}
                  onChange={(e) =>
                    setOrganizeStrategy(e.target.value as OrganizeRuleStrategy)
                  }
                  className="px-3 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-800 text-slate-200"
                >
                  <option value="by_category">
                    By Category (Documents/, Spreadsheets/, Data/, Notes/, Code/)
                  </option>
                  <option value="by_extension">
                    By File Extension (EXT_MD/, EXT_CSV/, EXT_JSON/)
                  </option>
                  <option value="by_date_month">
                    By Modification Month (YYYY-MM/)
                  </option>
                </select>

                <button
                  onClick={() => handleOrganizeWorkspace(true)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
                >
                  Preview Plan
                </button>
                <button
                  onClick={() => handleOrganizeWorkspace(false)}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
                >
                  Organize Workspace
                </button>
              </div>

              {organizePreview?.preview && (
                <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-2 text-xs">
                  <div className="font-semibold text-emerald-300">
                    Planned Moves ({organizePreview.preview.affected_count}{' '}
                    files, {organizePreview.preview.total_bytes_affected} bytes)
                  </div>
                  <div className="max-h-44 overflow-y-auto space-y-1 font-mono text-[11px] text-slate-400">
                    {organizePreview.preview.planned_changes.map((c, idx) => (
                      <div key={idx}>
                        {c.source_path} →{' '}
                        <span className="text-emerald-300">
                          {c.destination_path}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Stage 16 Browser Session Import Bridge */}
              <div className="border-t border-slate-800 pt-4 space-y-3">
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-xs font-bold text-white">
                    Stage 16 Browser Automation Capture Import
                  </h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <select
                    value={selectedBrowserSessionId}
                    onChange={(e) => setSelectedBrowserSessionId(e.target.value)}
                    className="px-2.5 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-800 text-slate-200"
                  >
                    <option value="">Select Stage 16 Browser Session...</option>
                    {browserSessions.map((s) => (
                      <option key={s.session_id} value={s.session_id}>
                        {s.session_id} — {s.goal.slice(0, 40)}
                      </option>
                    ))}
                  </select>
                  <input
                    type="text"
                    value={browserImportFilename}
                    onChange={(e) => setBrowserImportFilename(e.target.value)}
                    placeholder="captures/browser_capture.md"
                    className="px-2.5 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-800 text-slate-200"
                  />
                </div>
                <button
                  onClick={handleImportBrowserSession}
                  disabled={!selectedBrowserSessionId}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-white"
                >
                  Import Browser Capture to Workspace File
                </button>
              </div>
            </div>

            {/* SHA-256 Duplicate File Scanner */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Copy className="w-5 h-5 text-indigo-400" />
                  <div>
                    <h2 className="text-sm font-bold text-white">
                      SHA-256 Content-Hash Duplicate Finder
                    </h2>
                    <p className="text-xs text-slate-400">
                      Identifies byte-for-byte identical files across folders.
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleScanDuplicates}
                    className="px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
                  >
                    Scan Hashes
                  </button>
                  {duplicates.length > 0 && (
                    <button
                      onClick={handleCleanupDuplicates}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-600 hover:bg-amber-500 text-white"
                    >
                      Move Duplicates to Trash
                    </button>
                  )}
                </div>
              </div>

              {duplicates.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500 bg-slate-950/50 rounded-lg border border-slate-800">
                  No duplicate files detected in workspace.
                </div>
              ) : (
                <div className="space-y-3">
                  {duplicates.map((grp) => (
                    <div
                      key={grp.sha256_hash}
                      className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-indigo-300">
                          SHA-256: {grp.sha256_hash.slice(0, 20)}...
                        </span>
                        <span className="text-amber-300 font-semibold">
                          Wasted: {grp.wasted_bytes} bytes ({grp.duplicate_count}{' '}
                          duplicate copies)
                        </span>
                      </div>
                      <div className="text-emerald-300">
                        Keep Primary: <code>{grp.primary_file}</code>
                      </div>
                      <div className="text-slate-400">
                        Duplicates:{' '}
                        {grp.duplicate_files.map((d) => (
                          <code
                            key={d}
                            className="mr-2 px-1.5 py-0.5 rounded bg-slate-900 text-rose-300"
                          >
                            {d}
                          </code>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeSubTab === 'trash' && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-white">
                  Recoverable Trash Vault (.nexora_trash)
                </h2>
                <p className="text-xs text-slate-400">
                  Deleted files are safely quarantined here instead of immediate
                  destruction and can be restored with SHA-256 verification.
                </p>
              </div>
            </div>

            {trashItems.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                Recoverable Trash is empty.
              </div>
            ) : (
              <div className="divide-y divide-slate-800 border border-slate-800 rounded-lg bg-slate-950">
                {trashItems.map((t) => (
                  <div
                    key={t.trash_id}
                    className="p-3 flex items-center justify-between gap-4 text-xs"
                  >
                    <div>
                      <div className="font-semibold text-slate-200">
                        {t.original_path}{' '}
                        <span className="text-slate-500 font-normal">
                          ({t.size_bytes} bytes)
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        Trash ID: {t.trash_id} • Reason: {t.reason} • SHA-256:{' '}
                        {t.sha256_hash?.slice(0, 14) || 'folder'}
                      </div>
                    </div>
                    <button
                      onClick={() => handleRestoreTrashItem(t.trash_id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      Restore to Workspace
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeSubTab === 'operations' && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
            <div>
              <h2 className="text-sm font-bold text-white">
                Verified Operation Audit Log & 1-Click Rollback
              </h2>
              <p className="text-xs text-slate-400">
                Every file operation is verified on disk before completion and
                supports rollback where technically possible.
              </p>
            </div>

            <div className="divide-y divide-slate-800 border border-slate-800 rounded-lg bg-slate-950">
              {operations.map((op) => (
                <div
                  key={op.operation_id}
                  className="p-3 flex flex-wrap items-center justify-between gap-3 text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-200 uppercase">
                        {op.operation_type}
                      </span>
                      <span
                        className={`px-2 py-0.5 text-[10px] font-semibold rounded ${
                          op.status === 'VERIFIED_SUCCEEDED'
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : op.status === 'WAITING_FOR_APPROVAL'
                            ? 'bg-amber-500/20 text-amber-300'
                            : op.status === 'ROLLED_BACK'
                            ? 'bg-indigo-500/20 text-indigo-300'
                            : 'bg-slate-800 text-slate-300'
                        }`}
                      >
                        {op.status}
                      </span>
                      {op.verified && (
                        <span className="text-[11px] text-emerald-400 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> Verified
                        </span>
                      )}
                    </div>
                    <div className="text-slate-300">{op.summary}</div>
                    <div className="text-[11px] text-slate-500 font-mono">
                      {op.verification_detail}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {op.rollback_supported &&
                      !op.rolled_back &&
                      op.status === 'VERIFIED_SUCCEEDED' && (
                        <button
                          onClick={() =>
                            handleRollbackOperation(op.operation_id)
                          }
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          Rollback Operation
                        </button>
                      )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Create New File Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-lg w-full p-5 space-y-4">
            <h3 className="text-sm font-bold text-white">
              Create New Workspace File
            </h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">
                  Relative Path (.md, .txt, .csv, .json, .docx, .xlsx)
                </label>
                <input
                  type="text"
                  value={newFilePath}
                  onChange={(e) => setNewFilePath(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">
                  Initial Content
                </label>
                <textarea
                  rows={6}
                  value={newFileContent}
                  onChange={(e) => setNewFileContent(e.target.value)}
                  className="w-full p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-slate-100"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-3 py-1.5 rounded-lg text-xs bg-slate-800 text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateNewFile}
                className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                Create & Verify File
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
