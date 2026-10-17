import React from 'react';
import { useChat } from '../../context/ChatContext';
import {
  Sparkles,
  Code2,
  BookOpen,
  Globe,
  Compass,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Cpu,
  Search,
} from 'lucide-react';

export const WelcomeScreen: React.FC = () => {
  const { sendMessage, isBackendConnected, providerStatus, settings, setSettingsModalOpen, setSearchMode } = useChat();

  const isConfigured = Boolean(
    providerStatus?.configured ||
    settings.selectedProvider === 'gemini' ||
    settings.geminiApiKey ||
    settings.openaiApiKey ||
    settings.anthropicApiKey
  );

  const promptCards = [
    {
      title: 'Live Web Search',
      description: 'Find current breakthroughs with real verified citations',
      prompt: 'What are the latest breakthroughs and commercial developments in solid-state batteries this year?',
      icon: Globe,
      badge: 'Web Grounded',
      mode: 'web_search' as const,
    },
    {
      title: 'Deep Research Synthesis',
      description: 'Multi-pass vector decomposition and comparative evidence report',
      prompt: 'Compare the architectural tradeoffs and retrieval precision between Vector Embeddings vs Graph RAG for knowledge systems.',
      icon: Compass,
      badge: 'Deep Research',
      mode: 'deep_research' as const,
    },
    {
      title: 'Systems & Architecture',
      description: 'Design distributed architectures with precise technical trade-offs',
      prompt: 'Design a high-throughput event-driven microservices architecture using Apache Kafka and CQRS pattern.',
      icon: Code2,
      badge: 'AI Only',
      mode: 'ai_only' as const,
    },
    {
      title: 'Medical / Biology Research',
      description: 'Synthesize clinical literature with safety-filter compliance',
      prompt: 'Explain cellular autophagy mechanisms and recent clinical developments in neurodegenerative therapeutics.',
      icon: BookOpen,
      badge: 'Web Grounded',
      mode: 'web_search' as const,
    },
  ];

  const handlePromptClick = (prompt: string, mode: 'ai_only' | 'web_search' | 'deep_research') => {
    setSearchMode(mode);
    sendMessage(prompt);
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 py-8 sm:py-12 flex flex-col items-center justify-center max-w-4xl mx-auto w-full">
      {/* Brand Hero */}
      <div className="text-center space-y-3 mb-8">
        <div className="relative inline-flex items-center justify-center mb-2">
          <img
            src="assets/nexora-eagle-logo.jpg"
            alt="NEXORA AI Official Metallic Eagle Logo"
            className="w-20 h-20 sm:w-24 sm:h-24 rounded-3xl object-cover border border-cyan-400/50 shadow-[0_0_30px_rgba(6,182,212,0.35)]"
          />
        </div>

        <div className="flex items-center justify-center gap-2">
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-cyan-100 to-slate-200 bg-clip-text text-transparent">
            NEXORA AI
          </h1>
          <span className="text-xs px-2.5 py-1 rounded-full bg-cyan-500/10 text-cyan-400 font-semibold border border-cyan-500/30">
            Stage 24
          </span>
        </div>

        <p className="text-sm sm:text-base text-slate-400 max-w-lg mx-auto">
          Unified Intelligence Workspace — Evidence-grounded research, multi-agent collaboration, sandboxed coding, and embedded systems engineering.
        </p>
      </div>

      {/* Honest Provider Status Callout */}
      {!isConfigured && (
        <div className="w-full mb-8 p-4 rounded-2xl bg-midnight-900/90 border border-amber-500/30 shadow-lg flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-amber-200">
                Honest Setup State: AI Key Needed for Synthesis
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Web search and scraping are fully functional. To synthesize evidence into answers, provide a free Gemini or OpenAI key in Settings.
              </p>
            </div>
          </div>
          <button
            onClick={() => setSettingsModalOpen(true)}
            className="shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-300 text-xs font-semibold transition-colors"
          >
            <span>Configure Key</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Highlights / Badges */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 w-full mb-8">
        <div className="p-3 rounded-xl bg-midnight-900/60 border border-slate-800/80 flex items-center gap-2.5">
          <Search className="w-4 h-4 text-cyan-400 shrink-0" />
          <div className="text-left">
            <div className="text-xs font-medium text-slate-200">Universal Search</div>
            <div className="text-[10px] text-slate-500">Tavily / Brave / DDG</div>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-midnight-900/60 border border-slate-800/80 flex items-center gap-2.5">
          <Compass className="w-4 h-4 text-violet-400 shrink-0" />
          <div className="text-left">
            <div className="text-xs font-medium text-slate-200">Deep Research</div>
            <div className="text-[10px] text-slate-500">Multi-Pass Synthesis</div>
          </div>
        </div>

        <div className="col-span-2 sm:col-span-1 p-3 rounded-xl bg-midnight-900/60 border border-slate-800/80 flex items-center gap-2.5">
          <ShieldCheck className="w-4 h-4 text-teal-400 shrink-0" />
          <div className="text-left">
            <div className="text-xs font-medium text-slate-200">SSRF & Injection Shield</div>
            <div className="text-[10px] text-slate-500">Untrusted Data Isolation</div>
          </div>
        </div>
      </div>

      {/* Suggestion Prompts */}
      <div className="w-full space-y-2">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 px-1">
          Explore Research Capabilities
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {promptCards.map((card, idx) => {
            const Icon = card.icon;
            return (
              <button
                key={idx}
                onClick={() => handlePromptClick(card.prompt, card.mode)}
                className="group p-4 rounded-2xl bg-midnight-900/70 hover:bg-midnight-850 border border-slate-800/80 hover:border-cyan-500/40 text-left transition-all duration-200 hover:shadow-cyan-glow flex flex-col justify-between"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="p-2 rounded-xl bg-slate-800/70 text-cyan-400 group-hover:bg-cyan-500/10 group-hover:text-cyan-300 transition-colors">
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700/50">
                    {card.badge}
                  </span>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-200 group-hover:text-white">
                    {card.title}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                    {card.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
