import React, { useState, useEffect } from 'react';
import {
  Database,
  ShieldCheck,
  Pin,
  Trash2,
  Edit3,
  Plus,
  Search,
  RefreshCw,
  Download,
  Lock,
  EyeOff,
  Terminal,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  UserCheck,
  Clock,
  Tag,
} from 'lucide-react';
import { api } from '../../services/api';
import {
  MemoryCategory,
  MemoryItem,
  MemoryPrivacySettings,
  MemoryStatusSummary,
  MemoryCommandResponse,
} from '../../types';

const CATEGORY_LABELS: { id: MemoryCategory | 'all'; label: string; badgeColor: string; desc: string }[] = [
  { id: 'all', label: 'All Memories', badgeColor: 'bg-slate-700 text-slate-200', desc: 'All saved & session facts' },
  {
    id: 'preferences',
    label: 'Preferences',
    badgeColor: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    desc: 'Response style, language, formatting & accessibility',
  },
  {
    id: 'profile',
    label: 'Profile',
    badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    desc: 'User-approved interests, goals, skills & role',
  },
  {
    id: 'project_context',
    label: 'Project Context',
    badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    desc: 'Architecture decisions, requirements & constraints',
  },
  {
    id: 'conversation_summaries',
    label: 'Summaries',
    badgeColor: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
    desc: 'Concise summaries for continuing previous discussions',
  },
  {
    id: 'temporary_context',
    label: 'Temporary (RAM)',
    badgeColor: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
    desc: 'Volatile task data — never written to persistent disk',
  },
];

export const MemoryStudio: React.FC = () => {
  const [userId, setUserId] = useState<string>('default_user');
  const [status, setStatus] = useState<MemoryStatusSummary | null>(null);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<MemoryCategory | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Add Memory form state
  const [newContent, setNewContent] = useState('');
  const [newCategory, setNewCategory] = useState<MemoryCategory>('preferences');
  const [newKey, setNewKey] = useState('');
  const [newTags, setNewTags] = useState('');
  const [newPinned, setNewPinned] = useState(false);

  // Edit Memory state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [editCategory, setEditCategory] = useState<MemoryCategory>('profile');
  const [editKey, setEditKey] = useState('');

  // Natural-language command bar state
  const [commandInput, setCommandInput] = useState('');
  const [commandResult, setCommandResult] = useState<MemoryCommandResponse | null>(null);

  const loadMemoryData = async (activeUser = userId, cat = selectedCategory) => {
    setLoading(true);
    setError(null);
    try {
      const [statusData, itemsData] = await Promise.all([
        api.getMemoryStatus(activeUser),
        api.getMemoryItems({
          userId: activeUser,
          category: cat === 'all' ? undefined : cat,
          includeTemporary: true,
        }),
      ]);
      setStatus(statusData);
      setMemories(itemsData);
    } catch (err: any) {
      setError(err?.message || 'Failed to load persistent memory state.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMemoryData(userId, selectedCategory);
  }, [userId, selectedCategory]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      loadMemoryData();
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.searchMemories({
        user_id: userId,
        query: searchQuery,
        category: selectedCategory === 'all' ? undefined : selectedCategory,
        include_temporary: true,
      });
      setMemories(res.memories);
      setNotice(`Found ${res.total_matched} relevant memory item(s) ranked by overlap, recency, and pin boost.`);
    } catch (err: any) {
      setError(err?.message || 'Memory search failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;
    setError(null);
    setNotice(null);
    try {
      const tagList = newTags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      await api.createMemoryItem({
        user_id: userId,
        category: newCategory,
        key: newKey.trim() || undefined,
        content: newContent.trim(),
        tags: tagList,
        pinned: newPinned,
      });
      setNewContent('');
      setNewKey('');
      setNewTags('');
      setNewPinned(false);
      setNotice(
        newCategory === 'temporary_context'
          ? 'Saved to volatile Temporary Task Context (RAM only).'
          : 'Memory encrypted and saved to persistent SQLite storage.'
      );
      await loadMemoryData();
    } catch (err: any) {
      setError(err?.message || 'Could not save memory.');
    }
  };

  const handleTogglePin = async (item: MemoryItem) => {
    try {
      await api.updateMemoryItem(item.id, {
        user_id: userId,
        pinned: !item.pinned,
      });
      await loadMemoryData();
    } catch (err: any) {
      setError(err?.message || 'Failed to update pin state.');
    }
  };

  const handleStartEdit = (item: MemoryItem) => {
    setEditingId(item.id);
    setEditContent(item.content);
    setEditCategory(item.category);
    setEditKey(item.key);
  };

  const handleSaveEdit = async (memoryId: string) => {
    try {
      await api.updateMemoryItem(memoryId, {
        user_id: userId,
        category: editCategory,
        key: editKey.trim() || undefined,
        content: editContent.trim(),
      });
      setEditingId(null);
      setNotice('Memory updated and re-encrypted at rest.');
      await loadMemoryData();
    } catch (err: any) {
      setError(err?.message || 'Failed to update memory.');
    }
  };

  const handleDeleteMemory = async (memoryId: string) => {
    try {
      await api.deleteMemoryItem(memoryId, userId);
      setNotice('Memory permanently deleted and removed from retrieval index.');
      await loadMemoryData();
    } catch (err: any) {
      setError(err?.message || 'Failed to delete memory.');
    }
  };

  const handleClearAll = async () => {
    try {
      const res = await api.clearAllMemories(userId);
      setNotice(`Cleared ${res.removed_count} memory item(s) for user '${userId}'.`);
      await loadMemoryData();
    } catch (err: any) {
      setError(err?.message || 'Failed to clear memories.');
    }
  };

  const handleToggleSetting = async (field: keyof MemoryPrivacySettings) => {
    if (!status) return;
    const updated: MemoryPrivacySettings = {
      ...status.settings,
      user_id: userId,
      [field]: !status.settings[field],
    };
    try {
      await api.updateMemorySettings(updated);
      await loadMemoryData();
    } catch (err: any) {
      setError(err?.message || 'Failed to update privacy setting.');
    }
  };

  const handleRunCommand = async (confirmAmbiguous = false) => {
    if (!commandInput.trim()) return;
    setError(null);
    try {
      const res = await api.executeMemoryCommand({
        user_id: userId,
        text: commandInput.trim(),
        confirm_ambiguous: confirmAmbiguous,
      });
      setCommandResult(res);
      if (res.action_taken === 'saved' || res.action_taken === 'deleted') {
        await loadMemoryData();
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to execute memory command.');
    }
  };

  const handleExportBackup = async () => {
    try {
      const data = await api.exportMemoryBackup(userId);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `nexora_memory_${userId}_backup.json`;
      a.click();
      URL.revokeObjectURL(url);
      setNotice(`Exported ${data.count} persistent memory item(s) as JSON backup.`);
    } catch (err: any) {
      setError(err?.message || 'Failed to export backup.');
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-slate-950 text-slate-100 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Top Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/90 border border-slate-800 rounded-2xl p-5">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                <Database className="w-5 h-5" />
              </div>
              <h1 className="text-xl font-bold text-white">
                Stage 13: Persistent Memory & Personalization Center
              </h1>
              <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                SQLite + At-Rest Encryption
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Inspect, search, pin, edit, or delete saved facts. Clearly separates persistent memories, volatile
              temporary task context, and active conversation history.
            </p>
          </div>

          {/* Multi-user Isolation Switcher & Actions */}
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5">
              <UserCheck className="w-4 h-4 text-emerald-400" />
              <span className="text-xs text-slate-400">Isolated Profile:</span>
              <select
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                className="bg-transparent text-xs font-semibold text-white focus:outline-none"
                title="Switch active user namespace to verify strict multi-user memory isolation"
              >
                <option value="default_user" className="bg-slate-900">default_user</option>
                <option value="researcher_profile" className="bg-slate-900">researcher_profile</option>
                <option value="enterprise_dev" className="bg-slate-900">enterprise_dev</option>
              </select>
            </div>

            <button
              onClick={handleExportBackup}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Export Backup
            </button>

            <button
              onClick={() => loadMemoryData()}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Status Metrics & Privacy Controls */}
        {status && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Storage & Security Status */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Storage Architecture
                </span>
                <span className="flex items-center gap-1 text-xs text-emerald-400 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {status.storage_backend} (Schema v{status.schema_version})
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 pt-1">
                <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3 text-center">
                  <div className="text-lg font-bold text-white">{status.total_persistent_memories}</div>
                  <div className="text-[11px] text-slate-400">Persistent (Disk)</div>
                </div>
                <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3 text-center">
                  <div className="text-lg font-bold text-cyan-400">{status.total_temporary_memories}</div>
                  <div className="text-[11px] text-slate-400">Temporary (RAM)</div>
                </div>
                <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3 text-center">
                  <div className="text-lg font-bold text-amber-400">{status.pinned_count}</div>
                  <div className="text-[11px] text-slate-400">Pinned Priority</div>
                </div>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed pt-1">
                {status.external_provider_disclosure}
              </p>
            </div>

            {/* Privacy & Governance Toggles */}
            <div className="lg:col-span-2 bg-slate-900/70 border border-slate-800 rounded-2xl p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  Privacy, Encryption & Temporary Chat Controls
                </span>
                <button
                  onClick={handleClearAll}
                  className="flex items-center gap-1 text-xs text-rose-400 hover:text-rose-300 font-medium"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Clear All User Memories
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  onClick={() => handleToggleSetting('memory_enabled')}
                  className={`flex items-center justify-between p-3 rounded-xl border text-left transition-all ${
                    status.settings.memory_enabled
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
                      : 'bg-slate-950 border-slate-800 text-slate-400'
                  }`}
                >
                  <div>
                    <div className="text-xs font-semibold">Persistent Memory Enabled</div>
                    <div className="text-[11px] opacity-80">Retrieve & personalize responses</div>
                  </div>
                  <span className="text-xs font-bold px-2 py-0.5 rounded bg-black/30">
                    {status.settings.memory_enabled ? 'ON' : 'OFF'}
                  </span>
                </button>

                <button
                  onClick={() => handleToggleSetting('temporary_chat_mode')}
                  className={`flex items-center justify-between p-3 rounded-xl border text-left transition-all ${
                    status.settings.temporary_chat_mode
                      ? 'bg-amber-500/15 border-amber-500/40 text-amber-200'
                      : 'bg-slate-950 border-slate-800 text-slate-400'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <EyeOff className="w-4 h-4 text-amber-400 shrink-0" />
                    <div>
                      <div className="text-xs font-semibold">Temporary Chat Mode</div>
                      <div className="text-[11px] opacity-80">Never read or save persistent memories</div>
                    </div>
                  </div>
                  <span className="text-xs font-bold px-2 py-0.5 rounded bg-black/30">
                    {status.settings.temporary_chat_mode ? 'ACTIVE' : 'OFF'}
                  </span>
                </button>

                <button
                  onClick={() => handleToggleSetting('encrypt_at_rest')}
                  className={`flex items-center justify-between p-3 rounded-xl border text-left transition-all ${
                    status.settings.encrypt_at_rest
                      ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-200'
                      : 'bg-slate-950 border-slate-800 text-slate-400'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Lock className="w-4 h-4 text-indigo-400 shrink-0" />
                    <div>
                      <div className="text-xs font-semibold">At-Rest Encryption (enc:v1)</div>
                      <div className="text-[11px] opacity-80">Authenticated HMAC-SHA256 SQLite cipher</div>
                    </div>
                  </div>
                  <span className="text-xs font-bold px-2 py-0.5 rounded bg-black/30">
                    {status.settings.encrypt_at_rest ? 'ON' : 'OFF'}
                  </span>
                </button>

                <button
                  onClick={() => handleToggleSetting('block_sensitive_pii')}
                  className={`flex items-center justify-between p-3 rounded-xl border text-left transition-all ${
                    status.settings.block_sensitive_pii
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
                      : 'bg-slate-950 border-slate-800 text-slate-400'
                  }`}
                >
                  <div>
                    <div className="text-xs font-semibold">Sensitive PII & Secret Guard</div>
                    <div className="text-[11px] opacity-80">Blocks API keys, passwords, SSNs & cards</div>
                  </div>
                  <span className="text-xs font-bold px-2 py-0.5 rounded bg-black/30">
                    {status.settings.block_sensitive_pii ? 'ON' : 'OFF'}
                  </span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Natural-Language Memory Command Console */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-indigo-400" />
              <h2 className="text-sm font-semibold text-white">
                Natural-Language Memory Command Console
              </h2>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {[
                'Remember that I prefer concise TypeScript code examples',
                'What do you remember about me?',
                'Maybe remember that we might migrate to PostgreSQL 16',
                'Forget that I prefer concise TypeScript',
              ].map((sample) => (
                <button
                  key={sample}
                  type="button"
                  onClick={() => setCommandInput(sample)}
                  className="text-[11px] px-2 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition-colors"
                >
                  "{sample.slice(0, 34)}..."
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={commandInput}
              onChange={(e) => setCommandInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleRunCommand(false)}
              placeholder="Try: 'Remember this: Our sprint deadline is Friday' or 'What do you remember about me?' or 'Forget about...' "
              className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
            <button
              onClick={() => handleRunCommand(false)}
              className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-sm font-semibold text-white transition-colors"
            >
              Execute Command
            </button>
          </div>

          {commandResult && (
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300">
                    {commandResult.action_taken}
                  </span>
                  <span className="text-xs text-slate-200 whitespace-pre-wrap">{commandResult.message}</span>
                </div>
              </div>
              {commandResult.requires_confirmation && (
                <button
                  onClick={() => handleRunCommand(true)}
                  className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold shrink-0"
                >
                  Confirm & Proceed
                </button>
              )}
            </div>
          )}
        </div>

        {/* Notifications / Errors */}
        {error && (
          <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        {notice && (
          <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
            <Sparkles className="w-4 h-4 shrink-0" />
            <span>{notice}</span>
          </div>
        )}

        {/* Main Grid: Left Create Form | Right Memory Browser */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Create New Memory Card */}
          <form
            onSubmit={handleCreateMemory}
            className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-4 h-fit"
          >
            <div className="flex items-center gap-2">
              <Plus className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-semibold text-white">Add Approved Memory</h3>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Memory Category</label>
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value as MemoryCategory)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
              >
                <option value="preferences">Preferences (Style, Language, Tone)</option>
                <option value="profile">Profile (Interests, Goals, Skills)</option>
                <option value="project_context">Project Context (Decisions, Constraints)</option>
                <option value="conversation_summaries">Conversation Summaries</option>
                <option value="temporary_context">Temporary Context (Current Session RAM Only)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Topic / Key (Optional)</label>
              <input
                type="text"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                placeholder="e.g., preferred_stack or response_tone"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Memory Fact / Content</label>
              <textarea
                rows={3}
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                placeholder="Enter user-approved preference, project constraint, or temporary task note..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Tags (comma-separated)</label>
              <input
                type="text"
                value={newTags}
                onChange={(e) => setNewTags(e.target.value)}
                placeholder="architecture, python, frontend"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={newPinned}
                onChange={(e) => setNewPinned(e.target.checked)}
                className="rounded border-slate-700"
              />
              <span>Pin memory for priority retrieval</span>
            </label>

            <button
              type="submit"
              className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition-colors"
            >
              Save to Memory Engine
            </button>
          </form>

          {/* Right 2 Columns: Category Filter, Search & Memory List */}
          <div className="lg:col-span-2 space-y-4">
            {/* Category Tabs */}
            <div className="flex flex-wrap gap-2">
              {CATEGORY_LABELS.map((cat) => {
                const count =
                  cat.id === 'all'
                    ? (status?.total_persistent_memories || 0) + (status?.total_temporary_memories || 0)
                    : status?.by_category?.[cat.id] || 0;
                const active = selectedCategory === cat.id;
                return (
                  <button
                    key={cat.id}
                    onClick={() => setSelectedCategory(cat.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-all flex items-center gap-1.5 ${
                      active
                        ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-200'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <span>{cat.label}</span>
                    <span className="px-1.5 py-0.2 rounded-full bg-slate-950/70 text-[10px]">
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Relevance Search Bar */}
            <form onSubmit={handleSearch} className="flex gap-2">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search memories by keyword, project context, or topic relevance..."
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <button
                type="submit"
                className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200"
              >
                Search Relevance
              </button>
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    loadMemoryData();
                  }}
                  className="px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400 hover:text-white"
                >
                  Reset
                </button>
              )}
            </form>

            {/* Memory Cards List */}
            <div className="space-y-3">
              {memories.length === 0 ? (
                <div className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-8 text-center space-y-2">
                  <Database className="w-8 h-8 text-slate-600 mx-auto" />
                  <div className="text-sm font-medium text-slate-300">
                    No saved memories found for this view
                  </div>
                  <p className="text-xs text-slate-500 max-w-md mx-auto">
                    Nexora AI never fabricates memories that were not retained. Add an approved preference or use
                    "Remember that..." in chat or the command bar above.
                  </p>
                </div>
              ) : (
                memories.map((item) => (
                  <div
                    key={item.id}
                    className={`bg-slate-900/80 border rounded-2xl p-4 transition-all ${
                      item.pinned ? 'border-amber-500/40' : 'border-slate-800'
                    }`}
                  >
                    {editingId === item.id ? (
                      <div className="space-y-3">
                        <div className="flex gap-2">
                          <select
                            value={editCategory}
                            onChange={(e) => setEditCategory(e.target.value as MemoryCategory)}
                            className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white"
                          >
                            <option value="preferences">Preferences</option>
                            <option value="profile">Profile</option>
                            <option value="project_context">Project Context</option>
                            <option value="conversation_summaries">Summaries</option>
                            <option value="temporary_context">Temporary Context</option>
                          </select>
                          <input
                            type="text"
                            value={editKey}
                            onChange={(e) => setEditKey(e.target.value)}
                            className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white"
                          />
                        </div>
                        <textarea
                          rows={2}
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white"
                        />
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => setEditingId(null)}
                            className="px-3 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-300"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleSaveEdit(item.id)}
                            className="px-3 py-1.5 rounded-lg bg-emerald-600 text-xs font-semibold text-white"
                          >
                            Save Changes
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="px-2 py-0.5 text-[11px] font-semibold rounded-md border bg-slate-950 text-emerald-300 border-emerald-500/30">
                              {item.category}
                            </span>
                            <span className="text-xs font-mono text-slate-400">{item.key}</span>
                            {item.is_temporary ? (
                              <span className="px-2 py-0.5 text-[10px] rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                                Volatile RAM Only
                              </span>
                            ) : item.encrypted_at_rest ? (
                              <span className="flex items-center gap-1 px-2 py-0.5 text-[10px] rounded bg-indigo-500/15 text-indigo-300">
                                <Lock className="w-2.5 h-2.5" />
                                Encrypted At Rest
                              </span>
                            ) : null}
                            {item.relevance_score !== undefined && item.relevance_score !== null && (
                              <span className="px-2 py-0.5 text-[10px] rounded bg-emerald-500/15 text-emerald-300">
                                Relevance Score: {item.relevance_score}
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0">
                            <button
                              onClick={() => handleTogglePin(item)}
                              title={item.pinned ? 'Unpin memory' : 'Pin memory for priority retrieval'}
                              className={`p-1.5 rounded-lg border transition-colors ${
                                item.pinned
                                  ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                                  : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                              }`}
                            >
                              <Pin className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleStartEdit(item)}
                              title="Edit memory"
                              className="p-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 hover:text-white"
                            >
                              <Edit3 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleDeleteMemory(item.id)}
                              title="Delete memory"
                              className="p-1.5 rounded-lg bg-slate-950 border border-slate-800 text-rose-400 hover:bg-rose-500/20"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>

                        <p className="text-sm text-slate-100 leading-relaxed">{item.content}</p>

                        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-[11px] text-slate-500">
                          <div className="flex items-center gap-2">
                            {item.tags && item.tags.length > 0 && (
                              <div className="flex items-center gap-1">
                                <Tag className="w-3 h-3" />
                                {item.tags.map((t) => (
                                  <span key={t} className="px-1.5 py-0.5 rounded bg-slate-950 text-slate-400">
                                    #{t}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            <span>Updated {new Date(item.updated_at).toLocaleString()}</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
