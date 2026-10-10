import React, { useState, useEffect } from 'react';
import { useChat } from '../../context/ChatContext';
import { api } from '../../services/api';
import {
  LiveCategory,
  MonitoredTopic,
  LiveNotification,
  LiveQueryResponse,
  LiveSourceItem,
} from '../../types';
import {
  Activity,
  Radio,
  RefreshCw,
  Search,
  Bell,
  CheckCircle2,
  ExternalLink,
  Plus,
  Trash2,
  Clock,
  Globe,
  Sliders,
  Check,
  Zap,
  Filter,
} from 'lucide-react';

const CATEGORIES: { id: LiveCategory; label: string }[] = [
  { id: 'general', label: 'All Intelligence' },
  { id: 'news', label: 'Global News' },
  { id: 'tech', label: 'Technology' },
  { id: 'research', label: 'Research & Papers' },
  { id: 'finance', label: 'Markets & Finance' },
  { id: 'announcements', label: 'Announcements' },
];

export const RealTimeWorkspace: React.FC = () => {
  const { settings, showToast } = useChat();

  const [activeTab, setActiveTab] = useState<'live_feed' | 'monitored_topics' | 'alerts'>('live_feed');
  const [selectedCategory, setSelectedCategory] = useState<LiveCategory>('general');
  const [queryInput, setQueryInput] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);
  const [liveResult, setLiveResult] = useState<LiveQueryResponse | null>(null);

  // Topics & Monitoring state
  const [topics, setTopics] = useState<MonitoredTopic[]>([]);
  const [isLoadingTopics, setIsLoadingTopics] = useState(false);
  const [refreshingTopicId, setRefreshingTopicId] = useState<string | null>(null);

  // Topic creation modal/form
  const [showAddTopic, setShowAddTopic] = useState(false);
  const [newTopicName, setNewTopicName] = useState('');
  const [newTopicQuery, setNewTopicQuery] = useState('');
  const [newTopicCategory, setNewTopicCategory] = useState<LiveCategory>('general');
  const [newTopicInterval, setNewTopicInterval] = useState(60);

  // Notifications
  const [notifications, setNotifications] = useState<LiveNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  // Load initial data
  useEffect(() => {
    loadTopics();
    loadNotifications();
  }, []);

  const loadTopics = async () => {
    try {
      setIsLoadingTopics(true);
      const res = await api.getMonitoredTopics();
      setTopics(res);
    } catch (err: any) {
      console.error('Failed to load topics:', err);
    } finally {
      setIsLoadingTopics(false);
    }
  };

  const loadNotifications = async () => {
    try {
      const res = await api.getLiveNotifications();
      setNotifications(res);
      setUnreadCount(res.filter((n) => !n.is_read).length);
    } catch (err: any) {
      console.error('Failed to load notifications:', err);
    }
  };

  const handleLiveSearch = async (force: boolean = false) => {
    if (!queryInput.trim()) {
      showToast('Please enter an intelligence query or topic.', 'error');
      return;
    }

    setIsQuerying(true);
    try {
      const res = await api.executeLiveQuery({
        query: queryInput.trim(),
        category: selectedCategory,
        forceRefresh: force,
        maxSources: 6,
        settings,
      });
      setLiveResult(res);
      showToast(force ? 'Live search refreshed from Web.' : 'Live intelligence retrieved.', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to retrieve real-time data.', 'error');
    } finally {
      setIsQuerying(false);
    }
  };

  const handleCreateTopic = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTopicName.trim() || !newTopicQuery.trim()) {
      showToast('Topic title and query or URL are required.', 'error');
      return;
    }

    try {
      const created = await api.createMonitoredTopic({
        name: newTopicName.trim(),
        queryOrUrl: newTopicQuery.trim(),
        category: newTopicCategory,
        checkIntervalMinutes: newTopicInterval,
      });
      setTopics((prev) => [created, ...prev]);
      setShowAddTopic(false);
      setNewTopicName('');
      setNewTopicQuery('');
      showToast(`Topic "${created.name}" registered for monitoring.`, 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to register topic.', 'error');
    }
  };

  const handleDeleteTopic = async (id: string, name: string) => {
    try {
      await api.deleteMonitoredTopic(id);
      setTopics((prev) => prev.filter((t) => t.id !== id));
      showToast(`Removed topic "${name}".`, 'info');
    } catch (err: any) {
      showToast('Failed to delete topic.', 'error');
    }
  };

  const handleRefreshTopic = async (id: string) => {
    try {
      setRefreshingTopicId(id);
      const updated = await api.refreshMonitoredTopic(id, settings);
      setTopics((prev) => prev.map((t) => (t.id === id ? updated : t)));
      loadNotifications();
      showToast('Topic checked for fresh updates.', 'success');
    } catch (err: any) {
      showToast(err.message || 'Refresh failed.', 'error');
    } finally {
      setRefreshingTopicId(null);
    }
  };

  const handleMarkNotificationsRead = async () => {
    try {
      await api.markNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
      showToast('Notifications marked as read.', 'info');
    } catch {
      // Ignored
    }
  };

  const handleClearNotifications = async () => {
    try {
      await api.clearLiveNotifications();
      setNotifications([]);
      setUnreadCount(0);
      showToast('Notification history cleared.', 'info');
    } catch {
      // Ignored
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-midnight-950 px-4 py-6 md:px-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Banner Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-6 rounded-2xl bg-midnight-900/80 border border-slate-800 backdrop-blur-md">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center shadow-cyan-glow">
              <Radio className="w-6 h-6 text-white animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-100">Live Intelligence & Topic Monitor</h1>
                <span className="text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                  Stage 8
                </span>
              </div>
              <p className="text-sm text-slate-400 mt-1">
                Real-time data connectors, continuous change fingerprinting & notifications with honest freshness timestamps.
              </p>
            </div>
          </div>

          {/* Navigation Pill Switcher */}
          <div className="flex items-center p-1 bg-midnight-950 border border-slate-800 rounded-xl text-xs font-semibold">
            <button
              onClick={() => setActiveTab('live_feed')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                activeTab === 'live_feed' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Live Retrieval</span>
            </button>
            <button
              onClick={() => setActiveTab('monitored_topics')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                activeTab === 'monitored_topics' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Monitored Feeds ({topics.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('alerts')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all relative ${
                activeTab === 'alerts' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Bell className="w-3.5 h-3.5" />
              <span>Alerts</span>
              {unreadCount > 0 && (
                <span className="px-1.5 py-0.2 bg-red-500 text-white rounded-full text-[10px] font-bold">
                  {unreadCount}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* TAB 1: Live Intelligence Retrieval */}
        {activeTab === 'live_feed' && (
          <div className="space-y-6">
            {/* Search Input Bar */}
            <div className="p-4 rounded-2xl bg-midnight-900 border border-slate-800 space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                <div className="flex-1 relative">
                  <input
                    type="text"
                    value={queryInput}
                    onChange={(e) => setQueryInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleLiveSearch(false)}
                    placeholder="Ask about live news, recent research, announcements, or current metrics..."
                    className="w-full bg-midnight-950 border border-slate-800 rounded-xl px-4 py-2.5 pl-10 text-slate-100 text-sm focus:border-cyan-500/50 focus:outline-none"
                  />
                  <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                </div>

                <div className="flex items-center gap-2">
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value as LiveCategory)}
                    className="bg-midnight-950 border border-slate-800 text-slate-300 text-xs rounded-xl px-3 py-2.5 focus:outline-none cursor-pointer"
                  >
                    {CATEGORIES.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.label}
                      </option>
                    ))}
                  </select>

                  <button
                    onClick={() => handleLiveSearch(false)}
                    disabled={isQuerying || !queryInput.trim()}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white text-xs font-bold shadow-cyan-glow transition-all disabled:opacity-50"
                  >
                    {isQuerying ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>Searching...</span>
                      </>
                    ) : (
                      <>
                        <Zap className="w-4 h-4" />
                        <span>Live Fetch</span>
                      </>
                    )}
                  </button>

                  {liveResult && (
                    <button
                      onClick={() => handleLiveSearch(true)}
                      disabled={isQuerying}
                      className="p-2.5 rounded-xl bg-slate-800/60 hover:bg-slate-700 text-slate-300 transition-colors"
                      title="Force live bypass cache"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* Sample Queries */}
              <div className="flex items-center gap-2 overflow-x-auto text-[11px] pt-1">
                <span className="text-slate-500 shrink-0">Sample queries:</span>
                <button
                  onClick={() => setQueryInput('Latest Nobel prize in physics announcement')}
                  className="px-2 py-0.5 rounded bg-slate-800/60 text-slate-300 hover:text-cyan-300 hover:bg-slate-800 shrink-0"
                >
                  Nobel Physics
                </button>
                <button
                  onClick={() => setQueryInput('Recent quantum computing hardware milestone')}
                  className="px-2 py-0.5 rounded bg-slate-800/60 text-slate-300 hover:text-cyan-300 hover:bg-slate-800 shrink-0"
                >
                  Quantum Milestone
                </button>
                <button
                  onClick={() => setQueryInput('Major global artificial intelligence summit 2026')}
                  className="px-2 py-0.5 rounded bg-slate-800/60 text-slate-300 hover:text-cyan-300 hover:bg-slate-800 shrink-0"
                >
                  AI Summit
                </button>
              </div>
            </div>

            {/* Results Presentation */}
            {liveResult && (
              <div className="space-y-6 animate-in fade-in">
                {/* Synthesis Card */}
                <div className="p-6 rounded-2xl bg-midnight-900 border border-slate-800 space-y-4 shadow-xl">
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-800/80">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                      <span className="text-xs font-semibold text-emerald-300">
                        {liveResult.freshness_label}
                      </span>
                      <span className="text-[11px] font-mono text-slate-500">
                        [{new Date(liveResult.retrieved_at).toLocaleTimeString()}]
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-[10px]">
                      <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                        {liveResult.sources.length} Verified Sources
                      </span>
                      <span className="px-2 py-0.5 rounded-full bg-cyan-950/60 text-cyan-300 border border-cyan-800/40">
                        {liveResult.provider}
                      </span>
                    </div>
                  </div>

                  <div className="text-sm leading-relaxed text-slate-100 whitespace-pre-wrap">
                    {liveResult.synthesized_answer}
                  </div>
                </div>

                {/* Sources Cards Grid */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                    <span>Live Cited Sources & Evidence ({liveResult.sources.length})</span>
                    <span className="text-[11px] text-slate-500 font-normal">Original sources with publication dates</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {liveResult.sources.map((src, idx) => (
                      <a
                        key={idx}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-4 rounded-xl bg-midnight-900/80 border border-slate-800/80 hover:border-cyan-500/50 hover:bg-midnight-900 transition-all group flex flex-col justify-between"
                      >
                        <div className="space-y-1.5">
                          <div className="flex items-start justify-between gap-2">
                            <span className="text-xs font-bold text-slate-200 group-hover:text-cyan-300 transition-colors line-clamp-1">
                              [{idx + 1}] {src.title}
                            </span>
                            <ExternalLink className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400 shrink-0 transition-colors" />
                          </div>
                          <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                            {src.snippet}
                          </p>
                        </div>

                        <div className="flex items-center justify-between pt-3 mt-3 border-t border-slate-800/60 text-[11px] text-slate-500">
                          <span className="font-mono text-cyan-400/90">{src.domain}</span>
                          <span>{src.published_date || 'Date unindexed'}</span>
                        </div>
                      </a>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: Monitored Feeds & Topics */}
        {activeTab === 'monitored_topics' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-100">Saved Topics & Monitored Feeds</h2>
                <p className="text-xs text-slate-400">
                  Continuous change fingerprinting checks content every 15-120 minutes.
                </p>
              </div>
              <button
                onClick={() => setShowAddTopic(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 text-xs font-semibold transition-all"
              >
                <Plus className="w-4 h-4" />
                <span>Add Monitored Topic</span>
              </button>
            </div>

            {/* Add Topic Form Modal/Banner */}
            {showAddTopic && (
              <form
                onSubmit={handleCreateTopic}
                className="p-5 rounded-2xl bg-midnight-900 border border-cyan-500/40 space-y-4 animate-in fade-in"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-slate-100">Register New Monitored Resource</span>
                  <button
                    type="button"
                    onClick={() => setShowAddTopic(false)}
                    className="text-xs text-slate-500 hover:text-slate-300"
                  >
                    Cancel
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Topic Name</label>
                    <input
                      type="text"
                      value={newTopicName}
                      onChange={(e) => setNewTopicName(e.target.value)}
                      placeholder="e.g. Space Exploration Updates"
                      className="w-full bg-midnight-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 text-xs focus:outline-none focus:border-cyan-500/50"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Search Query or Web URL</label>
                    <input
                      type="text"
                      value={newTopicQuery}
                      onChange={(e) => setNewTopicQuery(e.target.value)}
                      placeholder="e.g. latest mars rover discovery OR https://example.com"
                      className="w-full bg-midnight-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 text-xs focus:outline-none focus:border-cyan-500/50"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Category</label>
                    <select
                      value={newTopicCategory}
                      onChange={(e) => setNewTopicCategory(e.target.value as LiveCategory)}
                      className="w-full bg-midnight-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 text-xs focus:outline-none"
                    >
                      {CATEGORIES.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Check Frequency</label>
                    <select
                      value={newTopicInterval}
                      onChange={(e) => setNewTopicInterval(parseInt(e.target.value))}
                      className="w-full bg-midnight-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 text-xs focus:outline-none"
                    >
                      <option value={15}>Every 15 minutes</option>
                      <option value={30}>Every 30 minutes</option>
                      <option value={60}>Every 1 hour</option>
                      <option value={120}>Every 2 hours</option>
                      <option value={360}>Every 6 hours</option>
                    </select>
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-midnight-950 font-bold text-xs shadow-cyan-glow transition-all"
                  >
                    Save & Start Monitoring
                  </button>
                </div>
              </form>
            )}

            {/* Topic Cards List */}
            <div className="space-y-3">
              {topics.map((t) => (
                <div
                  key={t.id}
                  className="p-5 rounded-2xl bg-midnight-900 border border-slate-800 hover:border-slate-700 transition-colors space-y-3"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
                      <h3 className="font-bold text-sm text-slate-100">{t.name}</h3>
                      <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-slate-800 text-cyan-300 border border-slate-700">
                        {t.category}
                      </span>
                      {t.change_count > 0 && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-950 text-violet-300 border border-violet-700/50">
                          {t.change_count} updates detected
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleRefreshTopic(t.id)}
                        disabled={refreshingTopicId === t.id}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors disabled:opacity-50"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${refreshingTopicId === t.id ? 'animate-spin' : ''}`} />
                        <span>Check Now</span>
                      </button>

                      <button
                        onClick={() => handleDeleteTopic(t.id, t.name)}
                        className="p-1 text-slate-500 hover:text-red-400 transition-colors"
                        title="Delete topic"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-slate-400 font-mono bg-midnight-950 p-2 rounded-lg border border-slate-800/60 line-clamp-1">
                    Target: {t.query_or_url}
                  </p>

                  {t.latest_summary && (
                    <p className="text-xs text-slate-300 leading-relaxed pl-2 border-l-2 border-cyan-500/50">
                      {t.latest_summary}
                    </p>
                  )}

                  <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-800/50">
                    <div className="flex items-center gap-3">
                      <span>Interval: {t.check_interval_minutes}m</span>
                      <span>
                        Last Check:{' '}
                        {t.last_checked_at ? new Date(t.last_checked_at).toLocaleTimeString() : 'Pending'}
                      </span>
                    </div>
                    <span>
                      Next Check:{' '}
                      {t.next_check_at ? new Date(t.next_check_at).toLocaleTimeString() : 'Scheduled'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 3: Change Alerts & Notifications */}
        {activeTab === 'alerts' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-100">Live Change Notifications</h2>
                <p className="text-xs text-slate-400">
                  Alerts generated when fingerprint comparisons detect meaningful updates on monitored topics.
                </p>
              </div>

              {notifications.length > 0 && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleMarkNotificationsRead}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800/60 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Mark All Read</span>
                  </button>
                  <button
                    onClick={handleClearNotifications}
                    className="px-3 py-1.5 rounded-xl bg-red-950/40 hover:bg-red-900/40 border border-red-500/30 text-red-300 text-xs transition-colors"
                  >
                    Clear History
                  </button>
                </div>
              )}
            </div>

            {notifications.length === 0 ? (
              <div className="p-12 text-center rounded-2xl bg-midnight-900 border border-slate-800 text-slate-500">
                <Bell className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                <p className="text-sm font-semibold">No recent alerts</p>
                <p className="text-xs mt-1">Monitored topics have not detected fresh changes since last review.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {notifications.map((n) => (
                  <div
                    key={n.id}
                    className={`p-4 rounded-xl border transition-all ${
                      n.is_read
                        ? 'bg-midnight-900/60 border-slate-800 text-slate-400'
                        : 'bg-midnight-900 border-cyan-500/40 text-slate-200 shadow-md'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-2">
                        {!n.is_read && <span className="w-2 h-2 rounded-full bg-cyan-400" />}
                        <span className="font-bold text-xs text-slate-200">{n.title}</span>
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {new Date(n.detected_at).toLocaleString()}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed mb-2">{n.summary_diff}</p>

                    {n.source_urls.length > 0 && (
                      <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/40 text-[11px]">
                        <span className="text-slate-500">Sources:</span>
                        {n.source_urls.slice(0, 3).map((u, i) => (
                          <a
                            key={i}
                            href={u}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-cyan-400 hover:underline flex items-center gap-1 font-mono"
                          >
                            <span>Link {i + 1}</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        ))}
                      </div>
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
