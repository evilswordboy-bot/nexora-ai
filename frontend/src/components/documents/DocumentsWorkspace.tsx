import React, { useState, useEffect, useRef } from 'react';
import { useChat } from '../../context/ChatContext';
import { api } from '../../services/api';
import { DocumentItem, DocumentAction, DocumentActionResponse, DocumentCitation } from '../../types';
import {
  FileText,
  UploadCloud,
  Trash2,
  CheckCircle,
  AlertCircle,
  FileSpreadsheet,
  FileCode,
  Image as ImageIcon,
  Sparkles,
  BookOpen,
  HelpCircle,
  Layers,
  Copy,
  Check,
  Send,
  Loader2,
  Table,
  Cpu,
  ArrowRight
} from 'lucide-react';

export const DocumentsWorkspace: React.FC = () => {
  const { settings, showToast, selectedDocumentIds, toggleSelectDocument, clearSelectedDocuments } = useChat();

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgressText, setUploadProgressText] = useState('');
  const [dragOver, setDragOver] = useState(false);

  // Active Document Action State
  const [activeAction, setActiveAction] = useState<DocumentAction>('ask');
  const [customPrompt, setCustomPrompt] = useState('');
  const [isExecutingAction, setIsExecutingAction] = useState(false);
  const [actionResult, setActionResult] = useState<DocumentActionResponse | null>(null);
  const [copiedResult, setCopiedResult] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load documents
  const loadDocuments = async () => {
    setLoadingDocs(true);
    try {
      const list = await api.listDocuments();
      setDocuments(list);
    } catch {
      showToast('Failed to load documents list from backend.', 'error');
    } finally {
      setLoadingDocs(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  // Handle upload
  const handleUploadFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    setIsUploading(true);
    setUploadProgressText(`Uploading and parsing ${files.length} document(s)...`);

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      try {
        setUploadProgressText(`Processing ${file.name}...`);
        const newDoc = await api.uploadDocument(file);
        setDocuments((prev) => [newDoc, ...prev.filter((d) => d.id !== newDoc.id)]);
        // Automatically select the newly uploaded file
        toggleSelectDocument(newDoc.id);
        showToast(`Document '${file.name}' parsed and indexed successfully.`, 'success');
      } catch (err: any) {
        showToast(err.message || `Failed to process ${file.name}`, 'error');
      }
    }

    setIsUploading(false);
    setUploadProgressText('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Handle delete
  const handleDeleteDocument = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to permanently delete '${name}'?`)) return;

    try {
      await api.deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      if (selectedDocumentIds.includes(id)) {
        toggleSelectDocument(id);
      }
      showToast(`Deleted '${name}'`, 'info');
    } catch {
      showToast(`Failed to delete document '${name}'`, 'error');
    }
  };

  // Execute Action
  const handleExecuteAction = async () => {
    if (selectedDocumentIds.length === 0) {
      showToast('Please select at least one document to analyze.', 'error');
      return;
    }

    if (activeAction === 'compare' && selectedDocumentIds.length < 2) {
      showToast('Document comparison requires selecting at least 2 documents.', 'error');
      return;
    }

    setIsExecutingAction(true);
    setActionResult(null);

    try {
      const response = await api.executeDocumentAction({
        documentIds: selectedDocumentIds,
        action: activeAction,
        query: customPrompt,
        settings,
      });
      setActionResult(response);
    } catch (err: any) {
      showToast(err.message || 'Document analysis failed.', 'error');
    } finally {
      setIsExecutingAction(false);
    }
  };

  // Copy result to clipboard
  const handleCopyResult = () => {
    if (!actionResult) return;
    navigator.clipboard.writeText(actionResult.result);
    setCopiedResult(true);
    setTimeout(() => setCopiedResult(false), 2000);
    showToast('Result copied to clipboard', 'success');
  };

  const getFormatIcon = (type: string) => {
    const t = type.toLowerCase();
    if (t === 'pdf') return <FileText className="w-5 h-5 text-red-400" />;
    if (t === 'csv' || t === 'xlsx') return <FileSpreadsheet className="w-5 h-5 text-emerald-400" />;
    if (t === 'docx') return <FileText className="w-5 h-5 text-blue-400" />;
    if (['png', 'jpg', 'jpeg', 'webp'].includes(t)) return <ImageIcon className="w-5 h-5 text-amber-400" />;
    return <FileCode className="w-5 h-5 text-cyan-400" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="flex-1 flex flex-col md:flex-row h-full overflow-hidden bg-midnight-950 text-slate-100">
      {/* Left Column: Documents Manager & Upload */}
      <div className="w-full md:w-80 lg:w-96 border-r border-slate-800/80 flex flex-col h-full bg-midnight-900/40">
        {/* Upload Header */}
        <div className="p-4 border-b border-slate-800/80">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-cyan-400" />
              <h2 className="text-sm font-bold text-slate-200">Documents Vault</h2>
            </div>
            <span className="text-xs text-slate-500 font-mono">
              {documents.length} File{documents.length !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Drag & Drop Box */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              handleUploadFiles(e.dataTransfer.files);
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-4 text-center cursor-pointer transition-all ${
              dragOver
                ? 'border-cyan-400 bg-cyan-950/30'
                : 'border-slate-800 hover:border-slate-700 bg-midnight-950/60'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.txt,.csv,.xlsx,.png,.jpg,.jpeg,.webp"
              onChange={(e) => handleUploadFiles(e.target.files)}
              className="hidden"
            />
            <div className="flex flex-col items-center gap-1.5">
              <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400">
                {isUploading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <UploadCloud className="w-5 h-5" />
                )}
              </div>
              <p className="text-xs font-semibold text-slate-200">
                {isUploading ? uploadProgressText : 'Click or Drag files to upload'}
              </p>
              <p className="text-[11px] text-slate-500">
                PDF, DOCX, TXT, CSV, XLSX, PNG, JPG (up to 25MB)
              </p>
            </div>
          </div>
        </div>

        {/* Selected Documents Actions Pill */}
        {selectedDocumentIds.length > 0 && (
          <div className="px-4 py-2 bg-cyan-950/40 border-b border-cyan-500/20 flex items-center justify-between text-xs text-cyan-300">
            <span className="font-semibold">{selectedDocumentIds.length} document(s) selected</span>
            <button
              onClick={clearSelectedDocuments}
              className="text-slate-400 hover:text-slate-200 underline text-[11px]"
            >
              Deselect All
            </button>
          </div>
        )}

        {/* Document List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {loadingDocs ? (
            <div className="flex items-center justify-center p-8 text-slate-500 gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
              <span className="text-xs">Loading library...</span>
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center p-8 text-slate-500 space-y-2">
              <FileText className="w-8 h-8 mx-auto text-slate-700" />
              <p className="text-xs">No documents uploaded yet.</p>
              <p className="text-[11px] text-slate-600">
                Upload files above to start asking questions, summarizing, and comparing content.
              </p>
            </div>
          ) : (
            documents.map((doc) => {
              const isSelected = selectedDocumentIds.includes(doc.id);
              return (
                <div
                  key={doc.id}
                  onClick={() => toggleSelectDocument(doc.id)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer flex items-start justify-between gap-2.5 ${
                    isSelected
                      ? 'bg-cyan-950/40 border-cyan-500/40 shadow-sm'
                      : 'bg-midnight-950/40 border-slate-800/80 hover:border-slate-700/80 hover:bg-slate-900/40'
                  }`}
                >
                  <div className="flex items-start gap-2.5 min-w-0">
                    <div className="p-1.5 rounded-lg bg-midnight-900 border border-slate-800 shrink-0 mt-0.5">
                      {getFormatIcon(doc.file_type)}
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-slate-200 truncate" title={doc.filename}>
                        {doc.filename}
                      </p>
                      <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-500">
                        <span>{formatFileSize(doc.size_bytes)}</span>
                        <span>•</span>
                        <span>{doc.page_count} page{doc.page_count !== 1 ? 's' : ''}</span>
                        <span>•</span>
                        <span>{doc.total_chunks} chunks</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    <div
                      className={`w-4 h-4 rounded flex items-center justify-center border transition-colors ${
                        isSelected
                          ? 'bg-cyan-500 border-cyan-400 text-midnight-950'
                          : 'border-slate-700 bg-midnight-900'
                      }`}
                    >
                      {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteDocument(doc.id, doc.filename);
                      }}
                      className="p-1 text-slate-500 hover:text-red-400 rounded transition-colors"
                      title="Delete document"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right Column: Document Intelligence Studio */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-midnight-950">
        {/* Actions Bar */}
        <div className="p-4 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3 bg-midnight-900/30">
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 text-xs font-medium">
            {[
              { id: 'ask', label: 'Ask Question', icon: HelpCircle },
              { id: 'summarize', label: 'Summarize', icon: FileText },
              { id: 'extract_key_points', label: 'Key Points', icon: Sparkles },
              { id: 'compare', label: 'Compare Docs', icon: Layers },
              { id: 'study_notes', label: 'Study Notes', icon: BookOpen },
              { id: 'faq', label: 'FAQ', icon: HelpCircle },
              { id: 'flashcards', label: 'Flashcards', icon: Layers },
              { id: 'quiz', label: 'Quiz', icon: CheckCircle },
              { id: 'explain_simply', label: 'Simplify (ELI12)', icon: Cpu },
              { id: 'extract_tables', label: 'Table Analytics', icon: Table },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeAction === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveAction(tab.id as DocumentAction)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs whitespace-nowrap transition-all ${
                    isActive
                      ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 font-semibold shadow-sm'
                      : 'bg-midnight-900/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          <button
            onClick={handleExecuteAction}
            disabled={isExecutingAction || selectedDocumentIds.length === 0}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold shadow-md transition-all ${
              selectedDocumentIds.length > 0 && !isExecutingAction
                ? 'bg-gradient-to-r from-cyan-500 to-violet-600 text-white shadow-cyan-glow hover:opacity-95'
                : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50'
            }`}
          >
            {isExecutingAction ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-white" />
                <span>Analyzing Documents...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Run {activeAction.replace('_', ' ').toUpperCase()}</span>
              </>
            )}
          </button>
        </div>

        {/* Action Prompt / Query Input (if relevant) */}
        {['ask', 'explain_simply', 'extract_tables', 'compare'].includes(activeAction) && (
          <div className="p-4 border-b border-slate-800/80 bg-midnight-900/20 flex items-center gap-3">
            <input
              type="text"
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleExecuteAction();
              }}
              placeholder={
                activeAction === 'ask'
                  ? 'Ask a question about the selected document(s)...'
                  : activeAction === 'compare'
                  ? 'Specific comparison criteria (optional)...'
                  : activeAction === 'explain_simply'
                  ? 'Enter specific concept to simplify, or leave empty for general summary...'
                  : 'Specific table query or data to analyze...'
              }
              className="flex-1 bg-midnight-950 border border-slate-800 rounded-xl px-4 py-2 text-xs text-slate-200 focus:border-cyan-500/50 focus:outline-none"
            />
            <button
              onClick={handleExecuteAction}
              disabled={isExecutingAction || selectedDocumentIds.length === 0}
              className="p-2 rounded-xl bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Results Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {actionResult ? (
            <div className="space-y-6 max-w-4xl mx-auto">
              {/* Header result info */}
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="text-xs uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                    {actionResult.action.replace('_', ' ')}
                  </span>
                  <span className="text-xs text-slate-400">
                    Model: <code className="text-slate-300">{actionResult.model}</code> ({actionResult.provider})
                  </span>
                </div>
                <button
                  onClick={handleCopyResult}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
                >
                  {copiedResult ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedResult ? 'Copied' : 'Copy Output'}</span>
                </button>
              </div>

              {/* Main Analysis Output */}
              <div className="p-6 rounded-2xl bg-midnight-900/60 border border-slate-800 text-sm leading-relaxed text-slate-200 space-y-4 whitespace-pre-wrap font-sans">
                {actionResult.result}
              </div>

              {/* Document Citations Section */}
              {actionResult.citations && actionResult.citations.length > 0 && (
                <div className="space-y-3 pt-2">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Verified Document Citations ({actionResult.citations.length})</span>
                  </h4>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {actionResult.citations.map((cite) => (
                      <div
                        key={cite.source_id}
                        className="p-3.5 rounded-xl bg-midnight-950 border border-slate-800/80 space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-bold text-cyan-400 bg-cyan-500/10 px-1.5 py-0.5 rounded border border-cyan-500/20">
                            [{cite.source_id}] {cite.filename}
                          </span>
                          <span className="text-[10px] text-slate-500 font-mono">
                            Page {cite.page_number || 1} • {cite.section || 'General'}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 italic line-clamp-3">
                          "{cite.snippet}"
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : isExecutingAction ? (
            <div className="flex flex-col items-center justify-center h-full p-12 text-center space-y-4">
              <div className="relative">
                <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 animate-pulse">
                  <Sparkles className="w-8 h-8" />
                </div>
                <div className="absolute -bottom-1 -right-1">
                  <Loader2 className="w-6 h-6 animate-spin text-violet-400" />
                </div>
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-bold text-slate-200">Processing Document Intelligence</h3>
                <p className="text-xs text-slate-400 max-w-sm">
                  Analyzing document tokens, passages, and evidence boundaries. Answers are strictly grounded in document facts.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full p-12 text-center space-y-4 text-slate-500">
              <BookOpen className="w-12 h-12 text-slate-800 stroke-[1.5]" />
              <div className="space-y-1.5 max-w-md">
                <h3 className="text-sm font-semibold text-slate-300">Document Intelligence Workspace</h3>
                <p className="text-xs text-slate-400">
                  Select one or more documents on the left panel, pick an action (Summarize, Extract Key Points, Compare, Quiz, Flashcards), and click Run.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
