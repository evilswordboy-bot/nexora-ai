import React, { useEffect, useState, useCallback } from 'react';
import {
  Compass,
  Search,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  BookOpen,
  ShieldCheck,
  Layers,
  GitCompare,
  Sparkles,
  ExternalLink,
  Filter,
  Globe,
  Database,
  FileText,
  X,
} from 'lucide-react';
import { api } from '../../services/api';
import {
  DiscoveryMetadataResponse,
  DiscoveryNormalizedItem,
  DiscoverySearchMode,
  DiscoverySearchResponse,
  DiscoverySourceType,
} from '../../types';

type DiscoveryTab = 'results' | 'synthesis' | 'timeline' | 'comparison' | 'exploration';

export const DiscoveryStudio: React.FC = () => {
  const [metadata, setMetadata] = useState<DiscoveryMetadataResponse | null>(null);
  const [query, setQuery] = useState<string>(
    'FastAPI Python async specification security standards'
  );
  const [mode, setMode] = useState<DiscoverySearchMode>('comprehensive');
  const [selectedSources, setSelectedSources] = useState<DiscoverySourceType[]>([]);
  const [language, setLanguage] = useState<string>('auto');
  const [domainFilter, setDomainFilter] = useState<string>('');
  const [exactPhrase, setExactPhrase] = useState<string>('');
  const [excludeInput, setExcludeInput] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [bypassCache, setBypassCache] = useState<boolean>(false);
  const [simulateFailedConnectors, setSimulateFailedConnectors] = useState<string[]>([]);

  const [discoveryResult, setDiscoveryResult] = useState<DiscoverySearchResponse | null>(null);
  const [selectedItem, setSelectedItem] = useState<DiscoveryNormalizedItem | null>(null);
  const [history, setHistory] = useState<DiscoverySearchResponse[]>([]);
  const [activeTab, setActiveTab] = useState<DiscoveryTab>('results');

  const [loading, setLoading] = useState<boolean>(false);
  const [searching, setSearching] = useState<boolean>(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const loadMetadataAndHistory = useCallback(async () => {
    setLoading(true);
    setErrorBanner(null);
    try {
      const [metaRes, histRes] = await Promise.all([
        api.getDiscoveryMetadata(),
        api.listDiscoveryHistory(10),
      ]);
      setMetadata(metaRes);
      setHistory(histRes);
      if (histRes.length > 0 && !discoveryResult) {
        setDiscoveryResult(histRes[0]);
        setSelectedItem(histRes[0].results[0] || null);
      }
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to load Stage 21 Discovery metadata.');
    } finally {
      setLoading(false);
    }
  }, [discoveryResult]);

  useEffect(() => {
    loadMetadataAndHistory();
  }, [loadMetadataAndHistory]);

  const toggleSourceType = (st: DiscoverySourceType) => {
    setSelectedSources((prev) =>
      prev.includes(st) ? prev.filter((item) => item !== st) : [...prev, st]
    );
  };

  const toggleSimulatedFailure = (connectorId: string) => {
    setSimulateFailedConnectors((prev) =>
      prev.includes(connectorId)
        ? prev.filter((id) => id !== connectorId)
        : [...prev, connectorId]
    );
  };

  const handleSearch = async (overrideQuery?: string, overrideMode?: DiscoverySearchMode) => {
    const targetQuery = (overrideQuery ?? query).trim();
    if (!targetQuery) return;
    setSearching(true);
    setErrorBanner(null);
    try {
      const excludeTerms = excludeInput
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);

      const res = await api.executeDiscoverySearch({
        query: targetQuery,
        mode: overrideMode ?? mode,
        source_types: selectedSources,
        language,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        domain_filter: domainFilter.trim() || undefined,
        exact_phrase: exactPhrase.trim() || undefined,
        exclude_terms: excludeTerms,
        bypass_cache: bypassCache,
        simulate_failed_connectors: simulateFailedConnectors,
      });

      setDiscoveryResult(res);
      setSelectedItem(res.results[0] || null);
      const histRes = await api.listDiscoveryHistory(10);
      setHistory(histRes);
    } catch (err: any) {
      setErrorBanner(err.message || 'Universal Knowledge Discovery search failed.');
    } finally {
      setSearching(false);
    }
  };

  const getOriginalityBadge = (tier: string) => {
    switch (tier) {
      case 'original_primary_source':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      case 'peer_reviewed_or_preprint':
        return 'bg-violet-500/15 text-violet-300 border-violet-500/30';
      case 'syndicated_or_copied':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-b border-slate-800 bg-slate-900/70">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-white">
                Universal Knowledge Discovery Engine
              </h1>
              <span className="px-2 py-0.5 text-[11px] font-semibold rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                Stage 21
              </span>
              {metadata && (
                <span className="px-2 py-0.5 text-[11px] font-mono rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                  {metadata.connectors.length} Multi-Source Connectors
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              Unified Web, Academic, News, Dataset, Official & Local Vault Discovery • Defensible
              Provenance • Zero Fabricated Sources
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadMetadataAndHistory}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

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

      {/* Main Content Grid */}
      <div className="flex-1 grid grid-cols-12 gap-4 p-6 overflow-y-auto">
        {/* Left Column: Search Modes, Connectors & Filters */}
        <div className="col-span-12 lg:col-span-4 space-y-4">
          {/* Search Input & Mode Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300">
              Discovery Query & Operators
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder='Search (supports site:, "exact", -exclude)...'
                className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-cyan-500"
              />
              <button
                onClick={() => handleSearch()}
                disabled={searching || !query.trim()}
                className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-xs font-semibold text-white flex items-center gap-1.5 shrink-0"
              >
                <Search className="w-3.5 h-3.5" />
                {searching ? 'Searching...' : 'Discover'}
              </button>
            </div>

            {/* 5 Functional Search Modes */}
            <div>
              <div className="text-[11px] font-semibold text-slate-400 mb-1.5">
                Functional Discovery Mode
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
                {(['quick', 'comprehensive', 'academic', 'official', 'exploration'] as const).map(
                  (m) => (
                    <button
                      key={m}
                      onClick={() => setMode(m)}
                      className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold capitalize border transition-colors ${
                        mode === m
                          ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                          : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
                      }`}
                    >
                      {m}
                    </button>
                  )
                )}
              </div>
            </div>

            {/* Advanced Filters */}
            <div className="pt-2 border-t border-slate-800 grid grid-cols-2 gap-2 text-xs">
              <div>
                <label className="block text-[10px] text-slate-400 mb-0.5">Language</label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200"
                >
                  <option value="auto">Auto-Detect & Preserve</option>
                  <option value="en">English (en)</option>
                  <option value="ta">Tamil (ta)</option>
                  <option value="hi">Hindi (hi)</option>
                  <option value="es">Spanish (es)</option>
                  <option value="fr">French (fr)</option>
                </select>
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-0.5">
                  Domain Filter (`site:`)
                </label>
                <input
                  type="text"
                  value={domainFilter}
                  onChange={(e) => setDomainFilter(e.target.value)}
                  placeholder="e.g. nist.gov, arxiv.org"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200"
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-0.5">Exact Phrase</label>
                <input
                  type="text"
                  value={exactPhrase}
                  onChange={(e) => setExactPhrase(e.target.value)}
                  placeholder="e.g. risk management"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200"
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-0.5">
                  Exclude Terms (comma-sep)
                </label>
                <input
                  type="text"
                  value={excludeInput}
                  onChange={(e) => setExcludeInput(e.target.value)}
                  placeholder="e.g. rumor, hype"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200"
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-0.5">Date From</label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200"
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-0.5">Date To</label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200"
                />
              </div>
            </div>

            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer pt-1">
              <input
                type="checkbox"
                checked={bypassCache}
                onChange={(e) => setBypassCache(e.target.checked)}
              />
              <span>Bypass discovery cache (force fresh retrieval)</span>
            </label>
          </div>

          {/* Connector Registry & Fault Simulation */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <Filter className="w-3.5 h-3.5 text-cyan-400" />
                Modular Source Connectors
              </h2>
              <button
                onClick={() => setSelectedSources([])}
                className="text-[11px] text-cyan-400 hover:underline"
              >
                Use Mode Default
              </button>
            </div>

            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {(metadata?.connectors || []).map((conn) => {
                const isSelected = selectedSources.includes(conn.source_type);
                const isSimFail = simulateFailedConnectors.includes(conn.connector_id);
                return (
                  <div
                    key={conn.connector_id}
                    className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800 space-y-1.5 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-200">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSourceType(conn.source_type)}
                        />
                        <span>{conn.name}</span>
                      </label>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300">
                        {conn.source_type}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">{conn.description}</p>
                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-900">
                      <span>{conn.provider_notes}</span>
                      <label className="flex items-center gap-1 text-amber-300 cursor-pointer shrink-0">
                        <input
                          type="checkbox"
                          checked={isSimFail}
                          onChange={() => toggleSimulatedFailure(conn.connector_id)}
                        />
                        <span>Simulate Error</span>
                      </label>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Discovery Results, Connector Statuses & Synthesis */}
        <div className="col-span-12 lg:col-span-8 space-y-4">
          {discoveryResult ? (
            <>
              {/* Telemetry & Connector Execution Banner */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 uppercase">
                      Mode: {discoveryResult.mode}
                    </span>
                    <span className="text-xs font-mono text-slate-300">
                      Intent: {discoveryResult.query_intent} • Lang:{' '}
                      {discoveryResult.detected_language_name} ({discoveryResult.preserved_language})
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
                    <span>{discoveryResult.total_filtered_results} Normalized Results</span>
                    <span>•</span>
                    <span>{discoveryResult.deduplicated_count} Duplicates Merged</span>
                    {discoveryResult.ssrf_blocked_count > 0 && (
                      <>
                        <span>•</span>
                        <span className="text-rose-400">
                          {discoveryResult.ssrf_blocked_count} SSRF Blocked
                        </span>
                      </>
                    )}
                    <span>•</span>
                    <span>
                      {discoveryResult.latency_ms.toFixed(1)} ms{' '}
                      {discoveryResult.cache_hit ? '(Cache Hit)' : '(Live)'}
                    </span>
                  </div>
                </div>

                {/* Connector Status Pills (Explicitly surfacing source-specific errors) */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {discoveryResult.connector_statuses.map((cs) => (
                    <div
                      key={cs.connector_id}
                      className={`p-2 rounded-lg border text-[11px] ${
                        cs.status === 'succeeded'
                          ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-200'
                          : cs.status === 'error' || cs.status === 'unavailable'
                          ? 'bg-rose-950/50 border-rose-500/40 text-rose-200'
                          : 'bg-slate-950 border-slate-800 text-slate-400'
                      }`}
                    >
                      <div className="flex items-center justify-between font-semibold">
                        <span className="truncate">{cs.source_type}</span>
                        <span className="uppercase text-[10px]">
                          {cs.status} ({cs.items_returned})
                        </span>
                      </div>
                      {cs.error_message && (
                        <div className="text-[10px] text-rose-300 mt-1 line-clamp-2">
                          {cs.error_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Sub-Navigation Tabs */}
              <div className="flex flex-wrap items-center gap-1.5 border-b border-slate-800 pb-2">
                <button
                  onClick={() => setActiveTab('results')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 ${
                    activeTab === 'results'
                      ? 'bg-cyan-600 text-white'
                      : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Layers className="w-3.5 h-3.5" />
                  Normalized Sources ({discoveryResult.results.length})
                </button>
                <button
                  onClick={() => setActiveTab('synthesis')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 ${
                    activeTab === 'synthesis'
                      ? 'bg-cyan-600 text-white'
                      : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  Synthesis, Conflicts & Gaps
                </button>
                <button
                  onClick={() => setActiveTab('timeline')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 ${
                    activeTab === 'timeline'
                      ? 'bg-cyan-600 text-white'
                      : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Clock className="w-3.5 h-3.5" />
                  Timeline ({discoveryResult.synthesis.timeline.length})
                </button>
                <button
                  onClick={() => setActiveTab('comparison')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 ${
                    activeTab === 'comparison'
                      ? 'bg-cyan-600 text-white'
                      : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <GitCompare className="w-3.5 h-3.5" />
                  Source Comparison Matrix
                </button>
                <button
                  onClick={() => setActiveTab('exploration')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 ${
                    activeTab === 'exploration'
                      ? 'bg-cyan-600 text-white'
                      : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Subqueries & Perspectives
                </button>
              </div>

              {/* TAB 1: NORMALIZED RESULTS & SOURCE INSPECTOR */}
              {activeTab === 'results' && (
                <div className="grid grid-cols-12 gap-4">
                  <div className="col-span-12 xl:col-span-7 space-y-2.5 max-h-[520px] overflow-y-auto pr-1">
                    {discoveryResult.results.map((item) => {
                      const isSelected = selectedItem?.item_id === item.item_id;
                      return (
                        <div
                          key={item.item_id}
                          onClick={() => setSelectedItem(item)}
                          className={`p-3.5 rounded-xl border cursor-pointer transition-colors space-y-2 ${
                            isSelected
                              ? 'bg-cyan-950/30 border-cyan-500/50'
                              : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-2 min-w-0">
                              <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-mono text-xs font-bold shrink-0">
                                [{item.citation_index}]
                              </span>
                              <h3 className="text-xs font-bold text-white truncate">{item.title}</h3>
                            </div>
                            <span className="text-[11px] font-mono text-cyan-300 shrink-0">
                              Rank {(item.combined_rank_score * 100).toFixed(0)}%
                            </span>
                          </div>

                          <p className="text-xs text-slate-300 line-clamp-2">{item.snippet}</p>

                          <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                              {item.domain}
                            </span>
                            <span
                              className={`px-2 py-0.5 rounded border font-semibold ${getOriginalityBadge(
                                item.originality_tier
                              )}`}
                            >
                              {item.originality_tier}
                            </span>
                            {item.is_verified_scholarly && (
                              <span className="px-2 py-0.5 rounded bg-violet-500/20 text-violet-300 border border-violet-500/30 font-semibold">
                                Verified Scholarly
                              </span>
                            )}
                            {item.is_verified_official && (
                              <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold">
                                Verified Official
                              </span>
                            )}
                            {item.publication_date && (
                              <span className="px-2 py-0.5 rounded bg-slate-950 text-slate-400 font-mono">
                                Published: {item.publication_date}
                              </span>
                            )}
                            {item.duplicate_count > 1 && (
                              <span className="px-2 py-0.5 rounded bg-teal-950 text-teal-300 border border-teal-500/30">
                                Merged {item.duplicate_count}x
                              </span>
                            )}
                          </div>

                          {item.is_stale && item.staleness_warning && (
                            <div className="px-2.5 py-1.5 rounded bg-amber-950/60 border border-amber-500/40 text-[11px] text-amber-200 flex items-center gap-1.5">
                              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                              <span>{item.staleness_warning}</span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* Right Inspector Panel */}
                  <div className="col-span-12 xl:col-span-5 bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Source Provenance & Quarantine Preview
                    </h3>
                    {selectedItem ? (
                      <div className="space-y-3 text-xs">
                        <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-cyan-400 font-bold">
                              Citation [{selectedItem.citation_index}]
                            </span>
                            <a
                              href={selectedItem.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-cyan-400 hover:underline flex items-center gap-1 text-[11px]"
                            >
                              <span>Open Source</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                          <div className="font-semibold text-white">{selectedItem.title}</div>
                          <div className="text-[11px] font-mono text-slate-400 break-all">
                            Canonical: {selectedItem.canonical_url}
                          </div>
                        </div>

                        <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                          <div className="text-[10px] uppercase text-slate-400">
                            Defensible Authority Basis
                          </div>
                          <div className="text-slate-200 text-[11px]">
                            {selectedItem.authority_basis}
                          </div>
                        </div>

                        <div className="grid grid-cols-3 gap-2 text-center">
                          <div className="p-2 rounded bg-slate-950 border border-slate-800">
                            <div className="text-[10px] text-slate-400">Relevance</div>
                            <div className="font-bold text-white">
                              {(selectedItem.relevance_score * 100).toFixed(0)}%
                            </div>
                          </div>
                          <div className="p-2 rounded bg-slate-950 border border-slate-800">
                            <div className="text-[10px] text-slate-400">Recency</div>
                            <div className="font-bold text-white">
                              {(selectedItem.recency_score * 100).toFixed(0)}%
                            </div>
                          </div>
                          <div className="p-2 rounded bg-slate-950 border border-slate-800">
                            <div className="text-[10px] text-slate-400">Quality</div>
                            <div className="font-bold text-white">
                              {(selectedItem.quality_score * 100).toFixed(0)}%
                            </div>
                          </div>
                        </div>

                        <div>
                          <div className="text-[11px] font-semibold text-slate-300 mb-1">
                            Quarantined Untrusted Snippet Envelope:
                          </div>
                          <pre className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 whitespace-pre-wrap max-h-40 overflow-y-auto">
                            {selectedItem.quarantined_snippet}
                          </pre>
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 py-8 text-center">
                        Select any discovery result to inspect its canonical URL, authority basis,
                        ranking breakdown, and untrusted content quarantine envelope.
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 2: KNOWLEDGE SYNTHESIS, CONFLICTS & EVIDENCE GAPS */}
              {activeTab === 'synthesis' && (
                <div className="space-y-4">
                  <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-2">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-300">
                      Executive Grounded Summary
                    </h3>
                    <p className="text-xs text-slate-200 leading-relaxed">
                      {discoveryResult.synthesis.concise_summary}
                    </p>
                  </div>

                  {discoveryResult.synthesis.detected_conflicts.length > 0 && (
                    <div className="bg-rose-950/40 border border-rose-500/40 rounded-xl p-4 space-y-2">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-rose-300">
                        Conflicting Information Detected (
                        {discoveryResult.synthesis.detected_conflicts.length})
                      </h3>
                      {discoveryResult.synthesis.detected_conflicts.map((cf, i) => (
                        <div
                          key={i}
                          className="p-2.5 rounded-lg bg-slate-950/80 border border-rose-500/30 text-xs space-y-1"
                        >
                          <div className="font-semibold text-rose-200">
                            Subject Terms: {cf.topic}
                          </div>
                          <div className="text-slate-300">
                            <strong>[{cf.citation_a}]:</strong> {cf.claim_a}
                          </div>
                          <div className="text-slate-300">
                            <strong>[{cf.citation_b}]:</strong> {cf.claim_b}
                          </div>
                          <div className="text-[11px] text-rose-300">{cf.explanation}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {discoveryResult.synthesis.evidence_gaps.length > 0 && (
                    <div className="bg-amber-950/40 border border-amber-500/40 rounded-xl p-4 space-y-2">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-amber-300">
                        Identified Evidence Gaps & Provider Limitations
                      </h3>
                      <ul className="list-disc list-inside text-xs text-amber-100 space-y-1">
                        {discoveryResult.synthesis.evidence_gaps.map((g, i) => (
                          <li key={i}>{g}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-2">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Detailed Multi-Section Discovery Report
                    </h3>
                    <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 whitespace-pre-wrap max-h-80 overflow-y-auto">
                      {discoveryResult.synthesis.detailed_report}
                    </pre>
                  </div>
                </div>
              )}

              {/* TAB 3: CHRONOLOGICAL TIMELINE */}
              {activeTab === 'timeline' && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Chronological Evidence Timeline (
                      {discoveryResult.synthesis.timeline.length} Dated Events)
                    </h3>
                    <span className="text-[11px] text-slate-400">
                      Undated sources are excluded rather than assigned fabricated dates
                    </span>
                  </div>
                  {discoveryResult.synthesis.timeline.length === 0 ? (
                    <p className="text-xs text-slate-500 py-6 text-center">
                      No sources with verified publication dates in this result set.
                    </p>
                  ) : (
                    <div className="space-y-2.5">
                      {discoveryResult.synthesis.timeline.map((ev, i) => (
                        <div
                          key={i}
                          className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-start gap-3 text-xs"
                        >
                          <span className="px-2 py-1 rounded bg-cyan-500/15 text-cyan-300 font-mono text-[11px] shrink-0">
                            {ev.date_label}
                          </span>
                          <div className="space-y-1">
                            <div className="font-semibold text-white">{ev.title}</div>
                            <p className="text-slate-300 text-[11px]">{ev.summary}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 4: SOURCE COMPARISON MATRIX */}
              {activeTab === 'comparison' && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 overflow-x-auto">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3">
                    Cross-Source Comparison Matrix
                  </h3>
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-[11px] text-slate-400">
                        <th className="py-2 pr-3">Ref</th>
                        <th className="py-2 pr-3">Domain & Type</th>
                        <th className="py-2 pr-3">Originality Tier</th>
                        <th className="py-2 pr-3">Status</th>
                        <th className="py-2 pr-3">Authority Basis</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {discoveryResult.synthesis.source_comparison.map((row) => (
                        <tr key={row.citation_index} className="hover:bg-slate-950/60">
                          <td className="py-2 pr-3 font-mono text-cyan-400 font-bold">
                            [{row.citation_index}]
                          </td>
                          <td className="py-2 pr-3">
                            <div className="font-semibold text-slate-200">{row.domain}</div>
                            <div className="text-[10px] font-mono text-slate-400">
                              {row.source_type}
                            </div>
                          </td>
                          <td className="py-2 pr-3 font-mono text-[11px] text-slate-300">
                            {row.originality_tier}
                          </td>
                          <td className="py-2 pr-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                row.agreement_status === 'conflicting'
                                  ? 'bg-rose-500/20 text-rose-300'
                                  : row.agreement_status === 'corroborated'
                                  ? 'bg-emerald-500/20 text-emerald-300'
                                  : 'bg-slate-800 text-slate-300'
                              }`}
                            >
                              {row.agreement_status}
                            </span>
                          </td>
                          <td className="py-2 text-[11px] text-slate-400">{row.authority_basis}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* TAB 5: SUBQUERIES, FOLLOW-UPS & ALTERNATIVE PERSPECTIVES */}
              {activeTab === 'exploration' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-2.5">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-300">
                      Expanded Subqueries & Follow-Up Searches
                    </h3>
                    <div className="space-y-1.5">
                      {discoveryResult.expanded_subqueries.map((sq, i) => (
                        <button
                          key={i}
                          onClick={() => {
                            setQuery(sq);
                            handleSearch(sq);
                          }}
                          className="w-full text-left p-2 rounded-lg bg-slate-950 hover:bg-slate-900 border border-slate-800 text-xs text-slate-200 flex items-center justify-between"
                        >
                          <span>{sq}</span>
                          <Search className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                        </button>
                      ))}
                    </div>

                    <h4 className="text-[11px] font-semibold text-slate-400 pt-2">
                      Suggested Follow-Up Questions
                    </h4>
                    <div className="space-y-1.5">
                      {discoveryResult.follow_up_queries.map((fq, i) => (
                        <button
                          key={i}
                          onClick={() => {
                            setQuery(fq);
                            handleSearch(fq);
                          }}
                          className="w-full text-left p-2 rounded-lg bg-slate-950 hover:bg-slate-900 border border-slate-800 text-xs text-cyan-200"
                        >
                          {fq}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-2.5">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-violet-300">
                      Alternative Viewpoints & Related Topics
                    </h3>
                    <div className="space-y-2">
                      {discoveryResult.alternative_viewpoints.map((vp, i) => (
                        <div
                          key={i}
                          className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300"
                        >
                          {vp}
                        </div>
                      ))}
                    </div>
                    <div className="flex flex-wrap gap-1.5 pt-2">
                      {discoveryResult.related_topics.map((rt, i) => (
                        <button
                          key={i}
                          onClick={() => {
                            setQuery(rt);
                            handleSearch(rt, 'exploration');
                          }}
                          className="px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-[11px] text-slate-200 border border-slate-700"
                        >
                          {rt}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-8 text-center space-y-3">
              <Compass className="w-10 h-10 text-cyan-400 mx-auto" />
              <h3 className="text-sm font-bold text-white">
                Universal Multi-Source Knowledge Discovery
              </h3>
              <p className="text-xs text-slate-400 max-w-lg mx-auto">
                Enter a research query on the left and click <strong>Discover</strong> to search
                across configured Web, Academic, Live News, Public Datasets, Official
                Documentation, and Authorized Local Knowledge Bases with automatic URL/content
                deduplication and grounded synthesis.
              </p>
              <button
                onClick={() => handleSearch()}
                className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-xs font-semibold text-white"
              >
                Run Sample Discovery Search
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DiscoveryStudio;
