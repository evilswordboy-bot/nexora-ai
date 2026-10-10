import React from 'react';
import { useChat } from '../../context/ChatContext';
import {
  Sparkles,
  Code2,
  BookOpen,
  Database,
  Layers,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Cpu,
} from 'lucide-react';

export const WelcomeScreen: React.FC = () => {
  const { sendMessage, isBackendConnected, providerStatus, settings, setSettingsModalOpen } = useChat();

  const isConfigured = Boolean(
    providerStatus?.configured ||
    settings.geminiApiKey ||
    settings.openaiApiKey ||
    settings.anthropicApiKey
  );

  const promptCards = [
    {
      title: 'Software Architecture',
      description: 'Design a clean modular architecture for an event-driven system',
      prompt: 'Design a clean, production-grade modular architecture for an event-driven distributed system in TypeScript.',
      icon: Code2,
      badge: 'Stage 1 Core',
    },
    {
      title: 'Medical / Biology Inquiry',
      description: 'Verify educational & anatomical safety filter adherence',
      prompt: 'Explain the physiological mechanisms of human endocrine signaling and reproductive biology in high-school textbooks.',
      icon: BookOpen,
      badge: 'Safety Filter Test',
    },
    {
      title: 'Database Systems',
      description: 'Deep technical comparison of B-Trees vs Log-Structured Merge Trees',
      prompt: 'Compare the performance tradeoffs and write amplification between B-Trees and LSM-Trees in storage engines.',
      icon: Database,
      badge: 'Deep Reasoning',
    },
    {
      title: '100-Phase Roadmap Audit',
      description: 'Explore the 100 development phases planned for NEXORA AI',
      prompt: 'Summarize the 100-phase architectural roadmap of NEXORA AI and explain what Stage 1 Foundation achieves.',
      icon: Layers,
      badge: 'Roadmap Audit',
    },
  ];

  return (
    <div className="flex-1 overflow-y-auto px-4 py-8 sm:py-12 flex flex-col items-center justify-center max-w-4xl mx-auto w-full">
      {/* Brand Hero */}
      <div className="text-center space-y-3 mb-8">
        <div className="relative inline-flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 rounded-3xl bg-gradient-to-tr from-cyan-500 via-violet-600 to-indigo-600 shadow-cyan-glow mb-2 animate-pulse-subtle">
          <Sparkles className="w-8 h-8 sm:w-10 sm:h-10 text-white" />
        </div>

        <div className="flex items-center justify-center gap-2">
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-cyan-100 to-slate-200 bg-clip-text text-transparent">
            NEXORA AI
          </h1>
          <span className="text-xs px-2.5 py-1 rounded-full bg-cyan-500/10 text-cyan-400 font-semibold border border-cyan-500/30">
            Stage 1
          </span>
        </div>

        <p className="text-sm sm:text-base text-slate-400 max-w-lg mx-auto">
          Universal, production-engineered AI assistant platform designed to scale across 100 architectural phases.
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
                Honest Setup State: No Provider Key Configured
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                NEXORA AI strictly forbids fake AI hallucination responses. Enter a free Google Gemini or OpenAI API key to activate live inference.
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
          <Cpu className="w-4 h-4 text-cyan-400 shrink-0" />
          <div className="text-left">
            <div className="text-xs font-medium text-slate-200">FastAPI Backbone</div>
            <div className="text-[10px] text-slate-500">Sliding Window Limiter</div>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-midnight-900/60 border border-slate-800/80 flex items-center gap-2.5">
          <ShieldCheck className="w-4 h-4 text-violet-400 shrink-0" />
          <div className="text-left">
            <div className="text-xs font-medium text-slate-200">Safety Guardrail</div>
            <div className="text-[10px] text-slate-500">Medical Exception Aware</div>
          </div>
        </div>

        <div className="col-span-2 sm:col-span-1 p-3 rounded-xl bg-midnight-900/60 border border-slate-800/80 flex items-center gap-2.5">
          <Layers className="w-4 h-4 text-cyan-400 shrink-0" />
          <div className="text-left">
            <div className="text-xs font-medium text-slate-200">100-Phase Tracker</div>
            <div className="text-[10px] text-slate-500">Zero Mocking Policy</div>
          </div>
        </div>
      </div>

      {/* Suggestion Prompts */}
      <div className="w-full space-y-2">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 px-1">
          Explore Foundation Capabilities
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {promptCards.map((card, idx) => {
            const Icon = card.icon;
            return (
              <button
                key={idx}
                onClick={() => sendMessage(card.prompt)}
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
