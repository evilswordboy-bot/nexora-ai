import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Share2,
  Search,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Filter,
  GitMerge,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Sparkles,
  FileText,
  ExternalLink,
  Layers,
  Compass,
  Plus,
  Trash2,
  History,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { api } from '../../services/api';
import { useChat } from '../../context/ChatContext';
import {
  KGChangeLogEntry,
  KGDestructiveOperationRecord,
  KGDuplicateCandidate,
  KGEntityNode,
  KGEntityType,
  KGFactBasis,
  KGGraphSnapshotResponse,
  KGMetadataResponse,
  KGQueryMode,
  KGQueryResponse,
  KGRelationType,
  KGRelationshipEdge,
} from '../../types';

const ENTITY_COLORS: Record<KGEntityType, { fill: string; stroke: string; badge: string }> = {
  technology: {
    fill: '#083344',
    stroke: '#22d3ee',
    badge: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
  },
  component: {
    fill: '#1e1b4b',
    stroke: '#818cf8',
    badge: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
  },
  organization: {
    fill: '#064e3b',
    stroke: '#34d399',
    badge: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  },
  person: {
    fill: '#4c1d95',
    stroke: '#c084fc',
    badge: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
  },
  dataset: {
    fill: '#451a03',
    stroke: '#fbbf24',
    badge: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  },
  claim_or_standard: {
    fill: '#4c0519',
    stroke: '#fb7185',
    badge: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  },
  event: {
    fill: '#1f2937',
    stroke: '#f97316',
    badge: 'bg-orange-500/15 text-orange-300 border-orange-500/30',
  },
  concept: {
    fill: '#0f172a',
    stroke: '#94a3b8',
    badge: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
  },
};

export const KnowledgeGraphStudio: React.FC = () => {
  const { showToast } = useChat();

  const [metadata, setMetadata] = useState<KGMetadataResponse | null>(null);
  const [snapshot, setSnapshot] = useState<KGGraphSnapshotResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Workspace & Filters
  const [workspaceId, setWorkspaceId] = useState('default_workspace');
  const [searchFilter, setSearchFilter] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('');
  const [relationTypeFilter, setRelationTypeFilter] = useState<string>('');
  const [factBasisFilter, setFactBasisFilter] = useState<string>('');
  const [page, setPage] = useState(1);

  // Interactive Canvas State
  const [zoom, setZoom] = useState(1.0);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [layoutMode, setLayoutMode] = useState<'circular' | 'layered'>('circular');
  const [selectedNode, setSelectedNode] = useState<KGEntityNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<KGRelationshipEdge | null>(null);

  // Active Studio Tab
  const [activeTab, setActiveTab] = useState<'explorer' | 'queries' | 'ingest' | 'governance'>('explorer');

  // Knowledge Query State
  const [queryMode, setQueryMode] = useState<KGQueryMode>('natural_language');
  const [questionText, setQuestionText] = useState('How are Nexora Platform and Pydantic connected?');
  const [sourceEntityInput, setSourceEntityInput] = useState('Nexora Platform');
  const [targetEntityInput, setTargetEntityInput] = useState('Pydantic');
  const [maxDepth, setMaxDepth] = useState(4);
  const [includeInferred, setIncludeInferred] = useState(true);
  const [queryResult, setQueryResult] = useState<KGQueryResponse | null>(null);
  const [isQuerying, setIsQuerying] = useState(false);

  // Incremental Ingestion State
  const [ingestTitle, setIngestTitle] = useState('Distributed RAG & Vector Index Specification');
  const [ingestUrl, setIngestUrl] = useState('https://fastapi.tiangolo.com/advanced/');
  const [ingestPage, setIngestPage] = useState('Page 3 — Retrieval Layer');
  const [ingestText, setIngestText] = useState(
    'Document Vault Engine depends on Lexical BM25 Retriever for passage ranking. ' +
      'Lexical BM25 Retriever is part of Nexora Platform. ' +
      'Independent Audit 2025 supports Zero-Trust Sandbox Policy on isolation guarantees.'
  );
  const [deriveInferred, setDeriveInferred] = useState(true);
  const [isIngesting, setIsIngesting] = useState(false);

  // Governance, Duplicates & History State
  const [duplicates, setDuplicates] = useState<KGDuplicateCandidate[]>([]);
  const [pendingOps, setPendingOps] = useState<KGDestructiveOperationRecord[]>([]);
  const [historyLogs, setHistoryLogs] = useState<KGChangeLogEntry[]>([]);
  const [mergeSourceId, setMergeSourceId] = useState('');
  const [mergeTargetId, setMergeTargetId] = useState('');

  const loadGraphData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [metaRes, snapRes, dupRes, opsRes, histRes] = await Promise.all([
        api.getKnowledgeGraphMetadata(),
        api.getKnowledgeGraphSnapshot({
          workspace_id: workspaceId,
          search: searchFilter || undefined,
          entity_type: entityTypeFilter || undefined,
          relation_type: relationTypeFilter || undefined,
          fact_basis: factBasisFilter || undefined,
          page,
          page_size: 50,
        }),
        api.listDuplicateEntities('default_user', workspaceId),
        api.listKnowledgeGraphOperations('default_user', workspaceId),
        api.listKnowledgeGraphHistory('default_user', workspaceId, 20),
      ]);
      setMetadata(metaRes);
      setSnapshot(snapRes);
      setDuplicates(dupRes);
      setPendingOps(opsRes);
      setHistoryLogs(histRes);

      if (snapRes.nodes.length > 0 && !selectedNode) {
        setSelectedNode(snapRes.nodes[0]);
      }
    } catch (err: any) {
      showToast(err.message || 'Failed to load Knowledge Graph workspace', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId, searchFilter, entityTypeFilter, relationTypeFilter, factBasisFilter, page, showToast, selectedNode]);

  useEffect(() => {
    loadGraphData();
  }, [loadGraphData]);

  // Compute deterministic 2D coordinates for SVG interactive canvas
  const nodePositions = useMemo(() => {
    const pos: Record<string, { x: number; y: number }> = {};
    const nodes = snapshot?.nodes || [];
    if (nodes.length === 0) return pos;

    const width = 860;
    const height = 520;
    const cx = width / 2;
    const cy = height / 2;

    if (layoutMode === 'circular') {
      const sorted = [...nodes].sort((a, b) => b.degree - a.degree);
      // Place highest-degree hub at center if > 3 nodes
      if (sorted.length > 3) {
        pos[sorted[0].entity_id] = { x: cx, y: cy };
        const rest = sorted.slice(1);
        const innerCount = Math.min(8, rest.length);
        const outerCount = Math.max(0, rest.length - innerCount);

        rest.slice(0, innerCount).forEach((n, idx) => {
          const angle = (2 * Math.PI * idx) / innerCount - Math.PI / 2;
          pos[n.entity_id] = {
            x: cx + Math.cos(angle) * 155,
            y: cy + Math.sin(angle) * 145,
          };
        });
        rest.slice(innerCount).forEach((n, idx) => {
          const angle = (2 * Math.PI * idx) / Math.max(1, outerCount) - Math.PI / 4;
          pos[n.entity_id] = {
            x: cx + Math.cos(angle) * 290,
            y: cy + Math.sin(angle) * 215,
          };
        });
      } else {
        sorted.forEach((n, idx) => {
          const angle = (2 * Math.PI * idx) / sorted.length - Math.PI / 2;
          pos[n.entity_id] = {
            x: cx + Math.cos(angle) * 160,
            y: cy + Math.sin(angle) * 140,
          };
        });
      }
    } else {
      // Layered by entity_type
      const typeOrder: KGEntityType[] = [
        'organization',
        'person',
        'claim_or_standard',
        'technology',
        'component',
        'dataset',
        'event',
        'concept',
      ];
      const buckets: Record<string, KGEntityNode[]> = {};
      nodes.forEach((n) => {
        buckets[n.entity_type] = buckets[n.entity_type] || [];
        buckets[n.entity_type].push(n);
      });
      const activeLayers = typeOrder.filter((t) => (buckets[t]?.length || 0) > 0);
      activeLayers.forEach((t, layerIdx) => {
        const rowNodes = buckets[t];
        const y = 75 + (layerIdx * (height - 140)) / Math.max(1, activeLayers.length - 1);
        rowNodes.forEach((n, colIdx) => {
          const x = 110 + ((colIdx + 0.5) * (width - 220)) / Math.max(1, rowNodes.length);
          pos[n.entity_id] = { x, y };
        });
      });
    }
    return pos;
  }, [snapshot?.nodes, layoutMode]);

  const handleRunQuery = async (overrideParams?: Partial<{
    mode: KGQueryMode;
    question: string;
    source_entity: string;
    target_entity: string;
  }>) => {
    setIsQuerying(true);
    try {
      const m = overrideParams?.mode || queryMode;
      const q = overrideParams?.question ?? questionText;
      const s = overrideParams?.source_entity ?? sourceEntityInput;
      const t = overrideParams?.target_entity ?? targetEntityInput;

      const res = await api.queryKnowledgeGraph({
        workspace_id: workspaceId,
        mode: m,
        question: q,
        source_entity: s || undefined,
        target_entity: t || undefined,
        max_depth: maxDepth,
        include_inferred: includeInferred,
      });
      setQueryResult(res);
      setActiveTab('queries');
      showToast(`Graph query completed (${res.mode_executed}) in ${res.latency_ms}ms`, 'success');
    } catch (err: any) {
      showToast(err.message || 'Knowledge Graph query failed', 'error');
    } finally {
      setIsQuerying(false);
    }
  };

  const handleExpandNeighborhood = async (node: KGEntityNode) => {
    setSourceEntityInput(node.label);
    setQueryMode('neighborhood_exploration');
    await handleRunQuery({
      mode: 'neighborhood_exploration',
      question: `Expand neighborhood around ${node.label}`,
      source_entity: node.label,
    });
  };

  const handleCheckDependents = async (node: KGEntityNode) => {
    setSourceEntityInput(node.label);
    setQueryMode('dependency_impact');
    await handleRunQuery({
      mode: 'dependency_impact',
      question: `What depends on ${node.label}?`,
      source_entity: node.label,
    });
  };

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ingestText.trim()) {
      showToast('Enter source text or passages to extract into the Knowledge Graph', 'info');
      return;
    }
    setIsIngesting(true);
    try {
      const res = await api.ingestKnowledgeGraph({
        workspace_id: workspaceId,
        source_title: ingestTitle || 'User Knowledge Document',
        source_url: ingestUrl || undefined,
        page_or_section: ingestPage || 'Section 1',
        source_text: ingestText,
        derive_inferred_relationships: deriveInferred,
      });
      showToast(res.summary, 'success');
      await loadGraphData();
      setActiveTab('explorer');
    } catch (err: any) {
      showToast(err.message || 'Failed to ingest into Knowledge Graph', 'error');
    } finally {
      setIsIngesting(false);
    }
  };

  const handleProposeMerge = async (srcId: string, tgtId: string) => {
    if (!srcId || !tgtId || srcId === tgtId) {
      showToast('Select two distinct entities to propose a merge', 'info');
      return;
    }
    try {
      const op = await api.mergeKnowledgeGraphEntities({
        workspace_id: workspaceId,
        source_entity_id: srcId,
        target_entity_id: tgtId,
        confirmed: false,
      });
      showToast(`Merge staged for approval (${op.op_id})`, 'info');
      await loadGraphData();
      setActiveTab('governance');
    } catch (err: any) {
      showToast(err.message || 'Failed to propose entity merge', 'error');
    }
  };

  const handleRequestDeleteNode = async (entityId: string) => {
    try {
      const op = await api.deleteKnowledgeGraphItems({
        workspace_id: workspaceId,
        entity_ids: [entityId],
        confirmed: false,
      });
      showToast(`Entity deletion staged for approval (${op.op_id})`, 'info');
      await loadGraphData();
      setActiveTab('governance');
    } catch (err: any) {
      showToast(err.message || 'Failed to stage deletion', 'error');
    }
  };

  const handleResolveOperation = async (opId: string, approved: boolean) => {
    try {
      const res = await api.approveKnowledgeGraphOperation(opId, {
        workspace_id: workspaceId,
        approved,
      });
      showToast(res.summary, approved ? 'success' : 'info');
      await loadGraphData();
    } catch (err: any) {
      showToast(err.message || 'Failed to resolve operation', 'error');
    }
  };

  const waitingOpsCount = pendingOps.filter((o) => o.status === 'WAITING_FOR_APPROVAL').length;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-midnight-950 text-slate-100">
      {/* Studio Sub-Header */}
      <div className="border-b border-slate-800/80 bg-midnight-900/60 px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500/20 to-violet-500/20 border border-cyan-500/30 flex items-center justify-center">
            <Share2 className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-slate-100">
                Stage 22: Knowledge Graph Intelligence
              </h1>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 font-medium">
                {metadata?.schema_version || 'v1.0.0'} • Explicit vs. AI-Inferred Provenance
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Connected entity & relationship reasoning with passage-level evidence, cycle-safe path queries, and approval-gated merges
            </p>
          </div>
        </div>

        {/* Workspace & Navigation Tabs */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="flex items-center gap-1.5 bg-slate-900/90 border border-slate-800 rounded-lg px-2.5 py-1 text-xs">
            <span className="text-slate-400">Workspace:</span>
            <input
              type="text"
              value={workspaceId}
              onChange={(e) => setWorkspaceId(e.target.value || 'default_workspace')}
              className="bg-transparent text-cyan-300 font-mono w-36 focus:outline-none"
              title="Isolated Knowledge Graph Workspace ID"
            />
          </div>

          <div className="flex items-center bg-slate-900/90 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('explorer')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === 'explorer'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Compass className="w-3.5 h-3.5" />
              <span>Graph Explorer ({snapshot?.total_nodes_in_workspace || 0})</span>
            </button>
            <button
              onClick={() => setActiveTab('queries')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === 'queries'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Knowledge Queries</span>
            </button>
            <button
              onClick={() => setActiveTab('ingest')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === 'ingest'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Ingest & Extract</span>
            </button>
            <button
              onClick={() => setActiveTab('governance')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === 'governance'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <GitMerge className="w-3.5 h-3.5" />
              <span>Merges & History</span>
              {waitingOpsCount > 0 && (
                <span className="px-1.5 py-0.2 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[10px]">
                  {waitingOpsCount}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {/* TAB 1: INTERACTIVE GRAPH EXPLORER */}
        {activeTab === 'explorer' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* Left 8 cols: Interactive Graph Canvas & Filter Bar */}
            <div className="lg:col-span-8 flex flex-col gap-4">
              {/* Filter & Controls Bar */}
              <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2 flex-wrap flex-1">
                  <div className="relative flex-1 min-w-[180px]">
                    <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={searchFilter}
                      onChange={(e) => {
                        setSearchFilter(e.target.value);
                        setPage(1);
                      }}
                      placeholder="Search entities, aliases, descriptions..."
                      className="w-full bg-slate-950/80 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-cyan-500/50"
                    />
                  </div>

                  <select
                    value={entityTypeFilter}
                    onChange={(e) => {
                      setEntityTypeFilter(e.target.value);
                      setPage(1);
                    }}
                    className="bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                    aria-label="Filter by Entity Type"
                  >
                    <option value="">All Entity Types</option>
                    {(metadata?.entity_types || []).map((et) => (
                      <option key={et} value={et}>
                        {et.replace(/_/g, ' ')}
                      </option>
                    ))}
                  </select>

                  <select
                    value={relationTypeFilter}
                    onChange={(e) => setRelationTypeFilter(e.target.value)}
                    className="bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                    aria-label="Filter by Relationship Type"
                  >
                    <option value="">All Relations</option>
                    {(metadata?.relation_types || []).map((rt) => (
                      <option key={rt} value={rt}>
                        {rt.replace(/_/g, ' ')}
                      </option>
                    ))}
                  </select>

                  <select
                    value={factBasisFilter}
                    onChange={(e) => setFactBasisFilter(e.target.value)}
                    className="bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                    aria-label="Filter by Fact Basis"
                  >
                    <option value="">Explicit + AI-Inferred</option>
                    <option value="explicit_fact">Explicit Facts Only</option>
                    <option value="ai_inferred">AI-Inferred Only</option>
                  </select>
                </div>

                {/* Zoom / Pan / Layout Controls */}
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => setLayoutMode((m) => (m === 'circular' ? 'layered' : 'circular'))}
                    className="px-2.5 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-xs text-slate-200 flex items-center gap-1"
                    title="Toggle Graph Layout"
                  >
                    <Layers className="w-3.5 h-3.5 text-cyan-400" />
                    <span>{layoutMode === 'circular' ? 'Radial' : 'Layered'}</span>
                  </button>
                  <button
                    onClick={() => setZoom((z) => Math.min(2.2, +(z + 0.2).toFixed(2)))}
                    className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-200"
                    title="Zoom In"
                  >
                    <ZoomIn className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setZoom((z) => Math.max(0.5, +(z - 0.2).toFixed(2)))}
                    className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-200"
                    title="Zoom Out"
                  >
                    <ZoomOut className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => {
                      setZoom(1.0);
                      setPan({ x: 0, y: 0 });
                    }}
                    className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-200"
                    title="Reset View"
                  >
                    <Maximize2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={loadGraphData}
                    className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-cyan-300"
                    title="Refresh Graph"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </div>

              {/* Interactive SVG Graph Canvas */}
              <div className="relative bg-slate-950 border border-slate-800/90 rounded-2xl overflow-hidden h-[520px] shadow-inner">
                {/* Legend Overlay */}
                <div className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-2 bg-slate-900/90 backdrop-blur-md border border-slate-800/80 rounded-xl px-3 py-1.5 text-[11px]">
                  <span className="flex items-center gap-1 text-cyan-300 font-medium">
                    <span className="w-4 h-0.5 bg-cyan-400 inline-block" /> Explicit Fact
                  </span>
                  <span className="flex items-center gap-1 text-violet-300 font-medium">
                    <span className="w-4 h-0.5 border-b border-dashed border-violet-400 inline-block" /> AI-Inferred
                  </span>
                  <span className="flex items-center gap-1 text-rose-300 font-medium">
                    <span className="w-4 h-0.5 bg-rose-500 inline-block" /> Contradicts
                  </span>
                </div>

                {/* Pan Nudge Controls */}
                <div className="absolute bottom-3 left-3 z-10 flex items-center gap-1 bg-slate-900/90 border border-slate-800 rounded-lg p-1 text-[10px] text-slate-300">
                  <button
                    onClick={() => setPan((p) => ({ ...p, x: p.x + 50 }))}
                    className="px-1.5 py-0.5 hover:bg-slate-800 rounded"
                  >
                    ←
                  </button>
                  <button
                    onClick={() => setPan((p) => ({ ...p, y: p.y + 50 }))}
                    className="px-1.5 py-0.5 hover:bg-slate-800 rounded"
                  >
                    ↑
                  </button>
                  <button
                    onClick={() => setPan((p) => ({ ...p, y: p.y - 50 }))}
                    className="px-1.5 py-0.5 hover:bg-slate-800 rounded"
                  >
                    ↓
                  </button>
                  <button
                    onClick={() => setPan((p) => ({ ...p, x: p.x - 50 }))}
                    className="px-1.5 py-0.5 hover:bg-slate-800 rounded"
                  >
                    →
                  </button>
                </div>

                {snapshot && snapshot.nodes.length > 0 ? (
                  <svg
                    viewBox="0 0 860 520"
                    className="w-full h-full select-none"
                  >
                    <defs>
                      <marker
                        id="arrow-explicit"
                        viewBox="0 0 10 10"
                        refX="24"
                        refY="5"
                        markerWidth="6"
                        markerHeight="6"
                        orient="auto-start-reverse"
                      >
                        <path d="M 0 1 L 10 5 L 0 9 z" fill="#22d3ee" />
                      </marker>
                      <marker
                        id="arrow-inferred"
                        viewBox="0 0 10 10"
                        refX="24"
                        refY="5"
                        markerWidth="6"
                        markerHeight="6"
                        orient="auto-start-reverse"
                      >
                        <path d="M 0 1 L 10 5 L 0 9 z" fill="#a78bfa" />
                      </marker>
                      <marker
                        id="arrow-contradicts"
                        viewBox="0 0 10 10"
                        refX="24"
                        refY="5"
                        markerWidth="6"
                        markerHeight="6"
                        orient="auto-start-reverse"
                      >
                        <path d="M 0 1 L 10 5 L 0 9 z" fill="#fb7185" />
                      </marker>
                    </defs>

                    <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                      {/* Edges */}
                      {snapshot.edges.map((edge) => {
                        const p1 = nodePositions[edge.source_entity_id];
                        const p2 = nodePositions[edge.target_entity_id];
                        if (!p1 || !p2) return null;

                        const isSelected = selectedEdge?.relationship_id === edge.relationship_id;
                        const isContradict = edge.relation_type === 'contradicts';
                        const strokeColor = isContradict
                          ? '#fb7185'
                          : edge.is_inferred
                          ? '#a78bfa'
                          : '#22d3ee';
                        const markerId = isContradict
                          ? 'url(#arrow-contradicts)'
                          : edge.is_inferred
                          ? 'url(#arrow-inferred)'
                          : 'url(#arrow-explicit)';

                        // Slight curve offset for inferred edges so parallel explicit+inferred edges don't overlap
                        const midX = (p1.x + p2.x) / 2;
                        const midY = (p1.y + p2.y) / 2 + (edge.is_inferred ? -16 : 0);

                        return (
                          <g
                            key={edge.relationship_id}
                            onClick={() => {
                              setSelectedEdge(edge);
                              setSelectedNode(null);
                            }}
                            className="cursor-pointer group"
                          >
                            <line
                              x1={p1.x}
                              y1={p1.y}
                              x2={p2.x}
                              y2={p2.y}
                              stroke={strokeColor}
                              strokeWidth={isSelected ? 3.2 : 1.8}
                              strokeDasharray={edge.is_inferred ? '6,4' : undefined}
                              strokeOpacity={isSelected ? 1.0 : 0.72}
                              markerEnd={markerId}
                            />
                            <rect
                              x={midX - 38}
                              y={midY - 9}
                              width={76}
                              height={16}
                              rx={4}
                              fill="#090d16"
                              fillOpacity={0.85}
                              stroke={strokeColor}
                              strokeOpacity={0.4}
                              strokeWidth={0.8}
                            />
                            <text
                              x={midX}
                              y={midY + 2}
                              textAnchor="middle"
                              fill={strokeColor}
                              fontSize="9"
                              fontWeight="600"
                            >
                              {edge.relation_type.replace(/_/g, ' ')}
                              {edge.is_inferred ? ' (AI)' : ''}
                            </text>
                          </g>
                        );
                      })}

                      {/* Nodes */}
                      {snapshot.nodes.map((node) => {
                        const pt = nodePositions[node.entity_id];
                        if (!pt) return null;
                        const palette = ENTITY_COLORS[node.entity_type] || ENTITY_COLORS.concept;
                        const isSelected = selectedNode?.entity_id === node.entity_id;
                        const radius = Math.min(26, 15 + Math.sqrt(node.degree || 1) * 2.5);

                        return (
                          <g
                            key={node.entity_id}
                            transform={`translate(${pt.x}, ${pt.y})`}
                            onClick={() => {
                              setSelectedNode(node);
                              setSelectedEdge(null);
                            }}
                            className="cursor-pointer"
                          >
                            {isSelected && (
                              <circle
                                r={radius + 6}
                                fill="none"
                                stroke="#22d3ee"
                                strokeWidth={2}
                                strokeDasharray="3,3"
                              />
                            )}
                            <circle
                              r={radius}
                              fill={palette.fill}
                              stroke={palette.stroke}
                              strokeWidth={isSelected ? 3 : 2}
                            />
                            <text
                              y={4}
                              textAnchor="middle"
                              fill="#f8fafc"
                              fontSize="10"
                              fontWeight="700"
                            >
                              {node.label.slice(0, 3).toUpperCase()}
                            </text>
                            <text
                              y={radius + 13}
                              textAnchor="middle"
                              fill="#e2e8f0"
                              fontSize="11"
                              fontWeight={isSelected ? '700' : '500'}
                            >
                              {node.label.length > 22 ? `${node.label.slice(0, 20)}…` : node.label}
                            </text>
                          </g>
                        );
                      })}
                    </g>
                  </svg>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-slate-400 p-6 text-center">
                    <Share2 className="w-10 h-10 text-slate-600 mb-2" />
                    <p className="text-sm font-medium text-slate-300">No Knowledge Graph Entities Found</p>
                    <p className="text-xs text-slate-500 max-w-md mt-1">
                      Adjust your entity/relationship filters or switch to the "Ingest & Extract" tab to populate this workspace.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Right 4 cols: Detail Inspector Panel (Selected Node or Selected Relationship) */}
            <div className="lg:col-span-4 flex flex-col gap-4">
              {selectedNode ? (
                <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-4 space-y-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span
                        className={`inline-block text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${
                          ENTITY_COLORS[selectedNode.entity_type]?.badge || ENTITY_COLORS.concept.badge
                        }`}
                      >
                        {selectedNode.entity_type.replace(/_/g, ' ')}
                      </span>
                      <h2 className="text-base font-bold text-slate-100 mt-1.5">{selectedNode.label}</h2>
                      <p className="text-[11px] font-mono text-slate-400">
                        ID: {selectedNode.entity_id} • Key: {selectedNode.canonical_key}
                      </p>
                    </div>
                    <span className="text-xs font-semibold text-cyan-300 bg-cyan-500/10 border border-cyan-500/30 px-2 py-1 rounded-lg">
                      {Math.round(selectedNode.confidence * 100)}% conf
                    </span>
                  </div>

                  {selectedNode.aliases.length > 0 && (
                    <div>
                      <span className="text-[11px] font-semibold text-slate-400 uppercase">Known Aliases</span>
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {selectedNode.aliases.map((al) => (
                          <span
                            key={al}
                            className="text-xs px-2 py-0.5 rounded-md bg-slate-800 text-slate-200 border border-slate-700"
                          >
                            {al}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <p className="text-xs text-slate-300 leading-relaxed">{selectedNode.description}</p>

                  {/* Quick Actions on Node */}
                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <button
                      onClick={() => handleExpandNeighborhood(selectedNode)}
                      className="px-3 py-2 rounded-xl bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/30 text-cyan-300 text-xs font-semibold flex items-center justify-center gap-1.5"
                    >
                      <Compass className="w-3.5 h-3.5" />
                      <span>Expand 2-Hop</span>
                    </button>
                    <button
                      onClick={() => handleCheckDependents(selectedNode)}
                      className="px-3 py-2 rounded-xl bg-violet-500/15 hover:bg-violet-500/25 border border-violet-500/30 text-violet-300 text-xs font-semibold flex items-center justify-center gap-1.5"
                    >
                      <Layers className="w-3.5 h-3.5" />
                      <span>What Depends On This?</span>
                    </button>
                  </div>

                  {/* Provenance & Evidence Passages */}
                  <div className="space-y-2 pt-2 border-t border-slate-800">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-cyan-400" />
                        <span>Originating Provenance ({selectedNode.provenance.length})</span>
                      </span>
                      <button
                        onClick={() => handleRequestDeleteNode(selectedNode.entity_id)}
                        className="text-[11px] text-rose-400 hover:text-rose-300 flex items-center gap-1"
                        title="Stage approval-gated deletion"
                      >
                        <Trash2 className="w-3 h-3" />
                        <span>Delete</span>
                      </button>
                    </div>

                    <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                      {selectedNode.provenance.map((ev) => (
                        <div
                          key={ev.evidence_id}
                          className="p-2.5 rounded-xl bg-slate-950/90 border border-slate-800/80 space-y-1 text-xs"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-semibold text-cyan-300 truncate">{ev.source_title}</span>
                            {ev.page_or_section && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 shrink-0">
                                {ev.page_or_section}
                              </span>
                            )}
                          </div>
                          <p className="text-slate-300 text-[11px] italic">"{ev.passage}"</p>
                          {ev.source_url && (
                            <a
                              href={ev.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-[11px] text-cyan-400 hover:underline"
                            >
                              <span>Source Link</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : selectedEdge ? (
                <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-4 space-y-4">
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${
                        selectedEdge.is_inferred
                          ? 'bg-violet-500/15 text-violet-300 border-violet-500/30'
                          : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                      }`}
                    >
                      {selectedEdge.is_inferred ? 'AI-Inferred Relationship' : 'Explicit Verified Fact'}
                    </span>
                    <span className="text-xs font-mono text-slate-400">
                      Uncertainty: {selectedEdge.uncertainty_label}
                    </span>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between gap-2 text-xs">
                    <span className="font-bold text-slate-100">{selectedEdge.source_label}</span>
                    <span className="px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-mono">
                      {selectedEdge.relation_type}
                    </span>
                    <span className="font-bold text-slate-100">{selectedEdge.target_label}</span>
                  </div>

                  <p className="text-xs text-slate-300">{selectedEdge.explanation}</p>

                  <div className="space-y-2 pt-2 border-t border-slate-800">
                    <span className="text-xs font-bold text-slate-200">
                      Supporting / Contradicting Evidence ({selectedEdge.evidence.length})
                    </span>
                    {selectedEdge.evidence.map((ev) => (
                      <div
                        key={ev.evidence_id}
                        className="p-2.5 rounded-xl bg-slate-950/90 border border-slate-800 space-y-1 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-cyan-300">{ev.source_title}</span>
                          <span className="text-[10px] text-slate-400">{ev.page_or_section}</span>
                        </div>
                        <p className="text-slate-300 text-[11px] italic">"{ev.passage}"</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 text-center text-slate-400">
                  <p className="text-sm font-medium text-slate-300">Select a Node or Relationship Edge</p>
                  <p className="text-xs text-slate-500 mt-1">
                    Click any entity node or relationship line on the canvas to inspect its provenance, uncertainty label, and source passages.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: KNOWLEDGE QUERIES */}
        {activeTab === 'queries' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            <div className="lg:col-span-5 bg-slate-900/80 border border-slate-800/90 rounded-2xl p-5 space-y-4">
              <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <span>Structured Knowledge Graph Queries</span>
              </h2>

              {/* Preset Buttons */}
              <div className="space-y-1.5">
                <span className="text-[11px] font-semibold text-slate-400 uppercase">1-Click Benchmark Queries</span>
                <div className="flex flex-col gap-1.5">
                  <button
                    onClick={() => {
                      setQueryMode('connection_path');
                      setSourceEntityInput('Nexora Platform');
                      setTargetEntityInput('Pydantic');
                      setQuestionText('How are Nexora Platform and Pydantic connected?');
                      handleRunQuery({
                        mode: 'connection_path',
                        question: 'How are Nexora Platform and Pydantic connected?',
                        source_entity: 'Nexora Platform',
                        target_entity: 'Pydantic',
                      });
                    }}
                    className="text-left px-3 py-2 rounded-xl bg-slate-950/90 hover:bg-slate-800/80 border border-slate-800 text-xs text-cyan-300 flex items-center justify-between"
                  >
                    <span>"How are Nexora Platform and Pydantic connected?"</span>
                    <ArrowRight className="w-3.5 h-3.5 shrink-0" />
                  </button>
                  <button
                    onClick={() => {
                      setQueryMode('dependency_impact');
                      setSourceEntityInput('FastAPI');
                      setQuestionText('What depends on FastAPI?');
                      handleRunQuery({
                        mode: 'dependency_impact',
                        question: 'What depends on FastAPI?',
                        source_entity: 'FastAPI',
                      });
                    }}
                    className="text-left px-3 py-2 rounded-xl bg-slate-950/90 hover:bg-slate-800/80 border border-slate-800 text-xs text-violet-300 flex items-center justify-between"
                  >
                    <span>"What depends on FastAPI?"</span>
                    <ArrowRight className="w-3.5 h-3.5 shrink-0" />
                  </button>
                  <button
                    onClick={() => {
                      setQueryMode('contradiction_analysis');
                      setSourceEntityInput('Zero-Trust Sandbox Policy');
                      setQuestionText('Which sources disagree about Zero-Trust Sandbox Policy?');
                      handleRunQuery({
                        mode: 'contradiction_analysis',
                        question: 'Which sources disagree about Zero-Trust Sandbox Policy?',
                        source_entity: 'Zero-Trust Sandbox Policy',
                      });
                    }}
                    className="text-left px-3 py-2 rounded-xl bg-slate-950/90 hover:bg-slate-800/80 border border-slate-800 text-xs text-rose-300 flex items-center justify-between"
                  >
                    <span>"Which sources disagree about Zero-Trust Sandbox Policy?"</span>
                    <ArrowRight className="w-3.5 h-3.5 shrink-0" />
                  </button>
                </div>
              </div>

              <div className="space-y-3 pt-2 border-t border-slate-800">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Query Mode</label>
                  <select
                    value={queryMode}
                    onChange={(e) => setQueryMode(e.target.value as KGQueryMode)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100"
                  >
                    <option value="natural_language">Natural Language Auto-Router</option>
                    <option value="connection_path">Connection Path Finder (A ↔ B)</option>
                    <option value="dependency_impact">Dependency & Upstream Impact</option>
                    <option value="contradiction_analysis">Contradiction & Source Disagreement</option>
                    <option value="neighborhood_exploration">Neighborhood k-Hop Exploration</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Knowledge Question</label>
                  <input
                    type="text"
                    value={questionText}
                    onChange={(e) => setQuestionText(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2.5">
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Source / Focus Entity</label>
                    <input
                      type="text"
                      value={sourceEntityInput}
                      onChange={(e) => setSourceEntityInput(e.target.value)}
                      placeholder="e.g. Nexora Platform"
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-100"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Target Entity (for Path)</label>
                    <input
                      type="text"
                      value={targetEntityInput}
                      onChange={(e) => setTargetEntityInput(e.target.value)}
                      placeholder="e.g. Pydantic"
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-100"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3">
                  <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeInferred}
                      onChange={(e) => setIncludeInferred(e.target.checked)}
                      className="rounded border-slate-700"
                    />
                    <span>Include AI-Inferred Edges</span>
                  </label>
                  <div className="flex items-center gap-1.5 text-xs text-slate-300">
                    <span>Max Depth:</span>
                    <input
                      type="number"
                      min={1}
                      max={6}
                      value={maxDepth}
                      onChange={(e) => setMaxDepth(Number(e.target.value))}
                      className="w-14 bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-center"
                    />
                  </div>
                </div>

                <button
                  onClick={() => handleRunQuery()}
                  disabled={isQuerying}
                  className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-violet-600 hover:from-cyan-400 hover:to-violet-500 text-white font-semibold text-xs shadow-cyan-glow transition-all"
                >
                  {isQuerying ? 'Executing Graph Traversal...' : 'Execute Knowledge Graph Query'}
                </button>
              </div>
            </div>

            {/* Query Result Panel */}
            <div className="lg:col-span-7 bg-slate-900/80 border border-slate-800/90 rounded-2xl p-5 space-y-4">
              {queryResult ? (
                <>
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
                    <div>
                      <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                        Mode: {queryResult.mode_executed}
                      </span>
                      <h3 className="text-sm font-bold text-slate-100 mt-1">{queryResult.question}</h3>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="px-2 py-1 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                        Explicit Facts: {queryResult.explicit_facts_count}
                      </span>
                      <span className="px-2 py-1 rounded-lg bg-violet-500/10 text-violet-300 border border-violet-500/30">
                        AI-Inferred: {queryResult.inferred_facts_count}
                      </span>
                      {queryResult.cycles_detected > 0 && (
                        <span className="px-2 py-1 rounded-lg bg-amber-500/10 text-amber-300 border border-amber-500/30">
                          Cycles Handled: {queryResult.cycles_detected}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-950/90 border border-cyan-500/30 text-xs text-slate-200 leading-relaxed">
                    {queryResult.answer_summary}
                  </div>

                  {/* Connection Paths */}
                  {queryResult.paths.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold text-slate-300 uppercase">
                        Discovered Graph Paths ({queryResult.paths.length})
                      </h4>
                      {queryResult.paths.map((pathSteps, pIdx) => (
                        <div
                          key={pIdx}
                          className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2 text-xs"
                        >
                          <div className="font-semibold text-cyan-300">
                            Path #{pIdx + 1} ({pathSteps.length} hop{pathSteps.length > 1 ? 's' : ''})
                          </div>
                          {pathSteps.map((st) => (
                            <div
                              key={`${pIdx}-${st.step_index}`}
                              className="flex flex-wrap items-center justify-between gap-2 pl-2 border-l-2 border-cyan-500/40"
                            >
                              <div>
                                <span className="font-semibold text-slate-100">{st.source_label}</span>
                                <span className="mx-2 px-2 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono text-[11px]">
                                  --[{st.relation_type}]--&gt;
                                </span>
                                <span className="font-semibold text-slate-100">{st.target_label}</span>
                              </div>
                              <span
                                className={`text-[10px] px-2 py-0.5 rounded-full border ${
                                  st.is_inferred
                                    ? 'bg-violet-500/15 text-violet-300 border-violet-500/30'
                                    : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                                }`}
                              >
                                {st.is_inferred ? `AI-Inferred (${st.uncertainty_label})` : 'Explicit Fact'}
                              </span>
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Contradictions */}
                  {queryResult.contradictions.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold text-rose-300 uppercase flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        <span>Contested Claims & Source Disagreements ({queryResult.contradictions.length})</span>
                      </h4>
                      {queryResult.contradictions.map((c, idx) => (
                        <div
                          key={idx}
                          className="p-3.5 rounded-xl bg-rose-950/20 border border-rose-500/30 space-y-2 text-xs"
                        >
                          <p className="font-semibold text-rose-200">{c.explanation}</p>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
                            <div className="p-2 rounded-lg bg-slate-950/80 border border-emerald-500/30">
                              <span className="text-[10px] font-bold text-emerald-300 uppercase">
                                Supporting Sources
                              </span>
                              <p className="text-slate-300 mt-0.5">
                                {c.supporting_sources.join(', ') || 'None recorded'}
                              </p>
                            </div>
                            <div className="p-2 rounded-lg bg-slate-950/80 border border-rose-500/30">
                              <span className="text-[10px] font-bold text-rose-300 uppercase">
                                Contradicting Sources
                              </span>
                              <p className="text-slate-300 mt-0.5">
                                {c.contradicting_sources.join(', ') || 'None recorded'}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-400 p-8 text-center">
                  <Sparkles className="w-9 h-9 text-slate-600 mb-2" />
                  <p className="text-sm font-medium text-slate-300">Run a Knowledge Graph Query</p>
                  <p className="text-xs text-slate-500 max-w-md mt-1">
                    Select one of the benchmark presets on the left or ask how technologies are connected, what depends on a component, or which sources disagree.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: INCREMENTAL INGESTION & EXTRACTION */}
        {activeTab === 'ingest' && (
          <form
            onSubmit={handleIngest}
            className="max-w-4xl mx-auto bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 space-y-4"
          >
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-100">
                  Incremental Knowledge Graph Extraction & Merge
                </h2>
                <p className="text-xs text-slate-400">
                  Extracts entities and relationships from text passages, deduplicates canonical keys, preserves source history, and quarantines untrusted passages.
                </p>
              </div>
              <span className="text-xs px-2.5 py-1 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
                SSRF & Prompt-Injection Protected
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Source Document / Title</label>
                <input
                  type="text"
                  value={ingestTitle}
                  onChange={(e) => setIngestTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Originating URL (Optional)</label>
                <input
                  type="text"
                  value={ingestUrl}
                  onChange={(e) => setIngestUrl(e.target.value)}
                  placeholder="https://..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Page / Section Citation</label>
                <input
                  type="text"
                  value={ingestPage}
                  onChange={(e) => setIngestPage(e.target.value)}
                  placeholder="Page 3, Section 2"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Authorized Source Text (Supports patterns like "A depends on B", "A created by B", "A contradicts B", "A supports B", "A is part of B")
              </label>
              <textarea
                rows={5}
                value={ingestText}
                onChange={(e) => setIngestText(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-100 font-mono leading-relaxed"
                required
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={deriveInferred}
                  onChange={(e) => setDeriveInferred(e.target.checked)}
                  className="rounded border-slate-700"
                />
                <span>Derive Transitive AI-Inferred Relationships (labeled distinctly as `ai_inferred`)</span>
              </label>

              <button
                type="submit"
                disabled={isIngesting}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-violet-600 hover:from-cyan-400 hover:to-violet-500 text-white font-semibold text-xs shadow-cyan-glow"
              >
                {isIngesting ? 'Extracting & Merging...' : 'Extract & Merge into Knowledge Graph'}
              </button>
            </div>
          </form>
        )}

        {/* TAB 4: DUPLICATE ENTITY RESOLVER, APPROVAL GATES & CHANGE HISTORY */}
        {activeTab === 'governance' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* Left 6 cols: Pending Destructive Approval Gates + Duplicate Entity Resolver */}
            <div className="lg:col-span-6 space-y-5">
              {/* Approval Gate Panel */}
              <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-5 space-y-3">
                <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-amber-400" />
                  <span>Approval Gate: Destructive Merges & Deletions ({pendingOps.length})</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Destructive entity merges and graph deletions require explicit user approval before modifying workspace topology.
                </p>

                {pendingOps.length > 0 ? (
                  <div className="space-y-2.5">
                    {pendingOps.map((op) => (
                      <div
                        key={op.op_id}
                        className="p-3 rounded-xl bg-slate-950/90 border border-slate-800 flex flex-col gap-2 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[11px] text-cyan-300">
                            {op.op_id} • {op.operation_type}
                          </span>
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                              op.status === 'WAITING_FOR_APPROVAL'
                                ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                                : op.status === 'SUCCEEDED'
                                ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                                : 'bg-slate-700/40 text-slate-400 border-slate-700'
                            }`}
                          >
                            {op.status}
                          </span>
                        </div>
                        <p className="text-slate-200">{op.summary}</p>
                        {op.status === 'WAITING_FOR_APPROVAL' && (
                          <div className="flex items-center gap-2 pt-1">
                            <button
                              onClick={() => handleResolveOperation(op.op_id, true)}
                              className="px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 font-semibold flex items-center gap-1"
                            >
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              <span>Approve & Execute</span>
                            </button>
                            <button
                              onClick={() => handleResolveOperation(op.op_id, false)}
                              className="px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 font-semibold flex items-center gap-1"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                              <span>Reject</span>
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic">No pending destructive operations.</p>
                )}
              </div>

              {/* Duplicate Candidates & Manual Merge */}
              <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-5 space-y-3">
                <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                  <GitMerge className="w-4 h-4 text-cyan-400" />
                  <span>Duplicate Entity Detector ({duplicates.length})</span>
                </h3>

                {duplicates.length > 0 ? (
                  <div className="space-y-2">
                    {duplicates.map((d) => (
                      <div
                        key={d.candidate_id}
                        className="p-3 rounded-xl bg-slate-950/90 border border-slate-800 flex items-center justify-between gap-2 text-xs"
                      >
                        <div>
                          <div className="font-semibold text-slate-100">
                            {d.entity_a_label} <span className="text-slate-500">↔</span> {d.entity_b_label}
                          </div>
                          <p className="text-[11px] text-slate-400">{d.reason}</p>
                        </div>
                        <button
                          onClick={() => handleProposeMerge(d.entity_b_id, d.entity_a_id)}
                          className="px-2.5 py-1.5 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border border-cyan-500/30 font-semibold shrink-0"
                        >
                          Stage Merge
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">
                    No unmerged duplicate entity candidates detected in this workspace.
                  </p>
                )}

                {/* Manual Entity Merge Selector */}
                <div className="pt-3 border-t border-slate-800 space-y-2">
                  <span className="text-xs font-semibold text-slate-300">Propose Custom Entity Merge</span>
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      value={mergeSourceId}
                      onChange={(e) => setMergeSourceId(e.target.value)}
                      className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                    >
                      <option value="">Select Source Entity (merged away)</option>
                      {(snapshot?.nodes || []).map((n) => (
                        <option key={n.entity_id} value={n.entity_id}>
                          {n.label}
                        </option>
                      ))}
                    </select>
                    <select
                      value={mergeTargetId}
                      onChange={(e) => setMergeTargetId(e.target.value)}
                      className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                    >
                      <option value="">Select Target Entity (preserved)</option>
                      {(snapshot?.nodes || []).map((n) => (
                        <option key={n.entity_id} value={n.entity_id}>
                          {n.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <button
                    onClick={() => handleProposeMerge(mergeSourceId, mergeTargetId)}
                    className="px-3 py-1.5 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/30 text-xs font-semibold"
                  >
                    Stage Entity Merge for Approval
                  </button>
                </div>
              </div>
            </div>

            {/* Right 6 cols: Change History Audit Log */}
            <div className="lg:col-span-6 bg-slate-900/80 border border-slate-800/90 rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <History className="w-4 h-4 text-cyan-400" />
                <span>Incremental Graph Change History ({historyLogs.length})</span>
              </h3>
              <div className="space-y-2.5 max-h-[500px] overflow-y-auto pr-1">
                {historyLogs.map((chg) => (
                  <div
                    key={chg.change_id}
                    className="p-3 rounded-xl bg-slate-950/90 border border-slate-800 space-y-1 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[11px] text-cyan-300">{chg.action_type}</span>
                      <span className="text-[10px] text-slate-500">
                        {new Date(chg.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-slate-200">{chg.summary}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
