import React from 'react';
import { useChat } from '../../context/ChatContext';
import {
  X,
  BookOpen,
  Key,
  ShieldCheck,
  Cpu,
  Layers,
  ExternalLink,
} from 'lucide-react';

export const SetupGuideModal: React.FC = () => {
  const { setupGuideModalOpen, setSetupGuideModalOpen, setSettingsModalOpen } = useChat();

  if (!setupGuideModalOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-midnight-900 border border-slate-800 rounded-3xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/80">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">Stage 2: The Intelligence Engine Guide</h2>
              <p className="text-xs text-slate-400">Nexora AI Universal Assistant Platform</p>
            </div>
          </div>
          <button
            onClick={() => setSetupGuideModalOpen(false)}
            className="p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-xs sm:text-sm text-slate-300">
          {/* Section 1: Core Foundation Philosophy */}
          <div className="space-y-2">
            <h3 className="text-sm font-bold text-cyan-400 flex items-center gap-2">
              <Cpu className="w-4 h-4" />
              <span>1. Zero-Fake-Response Policy</span>
            </h3>
            <p className="text-slate-400 leading-relaxed text-xs">
              Unlike generic templates that simulate AI chat using hardcoded random timers, NEXORA AI operates with genuine integrity. If no external API provider is configured, the system transparently indicates that an API key is required.
            </p>
          </div>

          {/* Section 2: How to Configure Providers */}
          <div className="space-y-3 p-4 rounded-2xl bg-midnight-950/70 border border-slate-800">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Key className="w-4 h-4 text-cyan-400" />
              <span>2. Quick Provider Activation</span>
            </h3>
            <p className="text-xs text-slate-400">
              You can supply an API key in two ways:
            </p>
            <div className="space-y-2 text-xs">
              <div className="p-2.5 rounded-lg bg-midnight-900 border border-slate-800/80">
                <span className="font-semibold text-cyan-300">Option A (Fastest): In Frontend Settings</span>
                <p className="text-slate-400 mt-0.5">
                  Click the gear icon in the top right, paste your Google Gemini or OpenAI key, and click Save. Stored locally in your browser.
                </p>
              </div>
              <div className="p-2.5 rounded-lg bg-midnight-900 border border-slate-800/80">
                <span className="font-semibold text-violet-300">Option B: In Backend .env</span>
                <p className="text-slate-400 mt-0.5">
                  Set <code>GEMINI_API_KEY=your_key</code> in <code>backend/.env</code> and restart the server.
                </p>
              </div>
            </div>
            <div className="pt-2">
              <a
                href="https://aistudio.google.com"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 underline font-medium"
              >
                <span>Get a free Google Gemini API key</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          {/* Section 3: Adult Content Safety Guardrails */}
          <div className="space-y-2">
            <h3 className="text-sm font-bold text-violet-400 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4" />
              <span>3. Adult Content & Educational Guardrail</span>
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Stage 1 incorporates an intelligent regex-classified safety guardrail that blocks explicit pornography, non-consensual erotica, and grooming, while deliberately permitting legitimate biological, reproductive, medical, and scientific anatomical discussions.
            </p>
          </div>

          {/* Section 4: 100-Phase Progression */}
          <div className="space-y-2">
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <span>4. The 100-Phase Master Blueprint</span>
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Track the exact progress of every tier in <code>PHASE_STATUS.md</code>. Only Stage 1 is marked COMPLETE after thorough end-to-end verification. Future phases (Streaming SSE, Web Research, Document RAG, Code Sandboxing, Computer Desktop Automation) build incrementally on top of this foundation.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-midnight-950/60 border-t border-slate-800/80 flex items-center justify-between">
          <span className="text-[11px] text-slate-500">NEXORA AI Architecture Team</span>
          <div className="flex gap-2">
            <button
              onClick={() => {
                setSetupGuideModalOpen(false);
                setSettingsModalOpen(true);
              }}
              className="px-4 py-2 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/40 text-cyan-300 text-xs font-semibold transition-colors"
            >
              Open Settings
            </button>
            <button
              onClick={() => setSetupGuideModalOpen(false)}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
