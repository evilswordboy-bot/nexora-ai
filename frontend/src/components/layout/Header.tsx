import React from 'react';
import { useChat } from '../../context/ChatContext';
import { Menu, Sparkles, Settings as SettingsIcon, HelpCircle, Shield, AlertTriangle, CheckCircle2, BookOpen, ShieldCheck, Globe, Radio, Cpu, Network, Database, Users, GitBranch, Monitor, FolderOpen } from 'lucide-react';

export const Header: React.FC = () => {
  const {
    isBackendConnected,
    providerStatus,
    settings,
    setSettingsModalOpen,
    setSetupGuideModalOpen,
    setMobileMenuOpen,
    activeWorkspaceView,
    setActiveWorkspaceView,
  } = useChat();

  const isConfigured = Boolean(
    providerStatus?.configured ||
    settings.geminiApiKey ||
    settings.openaiApiKey ||
    settings.anthropicApiKey
  );

  return (
    <header className="h-16 border-b border-slate-800/80 bg-midnight-900/70 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between z-30 shrink-0">
      {/* Left: Mobile hamburger & Brand */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setMobileMenuOpen(true)}
          className="md:hidden p-2 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800/50 transition-colors"
          aria-label="Open mobile menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2.5">
          <div className="relative flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-violet-600 shadow-cyan-glow">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base sm:text-lg tracking-wider bg-gradient-to-r from-slate-100 via-cyan-100 to-slate-200 bg-clip-text text-transparent">
                NEXORA
              </span>
              <span className="text-[10px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                Stage 17
              </span>
            </div>
          </div>
        </div>

        {/* Workspace Switcher */}
        <div className="hidden md:flex items-center p-1 rounded-xl bg-midnight-950/80 border border-slate-800/80 ml-2 overflow-x-auto">
          <button
            onClick={() => setActiveWorkspaceView('chat')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeWorkspaceView === 'chat'
                ? 'bg-cyan-500/20 text-cyan-300 shadow-sm border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Chat & Search</span>
          </button>
          <button
            onClick={() => setActiveWorkspaceView('files')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeWorkspaceView === 'files'
                ? 'bg-cyan-500/20 text-cyan-300 shadow-sm border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FolderOpen className="w-3.5 h-3.5 text-emerald-400" />
            <span>File Workspace</span>
          </button>
          <button
            onClick={() => setActiveWorkspaceView('computer')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeWorkspaceView === 'computer'
                ? 'bg-cyan-500/20 text-cyan-300 shadow-sm border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Monitor className="w-3.5 h-3.5 text-cyan-400" />
            <span>Computer Actions</span>
          </button>
          <button
            onClick={() => setActiveWorkspaceView('workflows')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeWorkspaceView === 'workflows'
                ? 'bg-cyan-500/20 text-cyan-300 shadow-sm border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <GitBranch className="w-3.5 h-3.5 text-cyan-400" />
            <span>Workflows</span>
          </button>
          <button
            onClick={() => setActiveWorkspaceView('agents')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeWorkspaceView === 'agents'
                ? 'bg-cyan-500/20 text-cyan-300 shadow-sm border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Users className="w-3.5 h-3.5 text-violet-400" />
            <span>Agent Swarm</span>
          </button>
          <button
            onClick={() => setActiveWorkspaceView('reasoning')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeWorkspaceView === 'reasoning'
                ? 'bg-cyan-500/20 text-cyan-300 shadow-sm border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span>Reasoning</span>
          </button>
          <button
            onClick={() => setActiveWorkspaceView('routing')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeWorkspaceView === 'routing'
                ? 'bg-cyan-500/20 text-cyan-300 shadow-sm border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Network className="w-3.5 h-3.5 text-cyan-400" />
            <span>Model Router</span>
          </button>
          <button
            onClick={() => setActiveWorkspaceView('memory')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeWorkspaceView === 'memory'
                ? 'bg-cyan-500/20 text-cyan-300 shadow-sm border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Database className="w-3.5 h-3.5 text-emerald-400" />
            <span>Memory Center</span>
          </button>
          <button
            onClick={() => setActiveWorkspaceView('vision')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeWorkspaceView === 'vision'
                ? 'bg-cyan-500/20 text-cyan-300 shadow-sm border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>Vision Studio</span>
          </button>
          <button
            onClick={() => setActiveWorkspaceView('documents')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeWorkspaceView === 'documents'
                ? 'bg-cyan-500/20 text-cyan-300 shadow-sm border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Documents Vault</span>
          </button>
          <button
            onClick={() => setActiveWorkspaceView('factcheck')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeWorkspaceView === 'factcheck'
                ? 'bg-cyan-500/20 text-cyan-300 shadow-sm border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Fact Check</span>
          </button>
          <button
            onClick={() => setActiveWorkspaceView('translation')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeWorkspaceView === 'translation'
                ? 'bg-cyan-500/20 text-cyan-300 shadow-sm border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Globe className="w-3.5 h-3.5" />
            <span>Translate</span>
          </button>
          <button
            onClick={() => setActiveWorkspaceView('realtime')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeWorkspaceView === 'realtime'
                ? 'bg-cyan-500/20 text-cyan-300 shadow-sm border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Radio className="w-3.5 h-3.5" />
            <span>Live Feed</span>
          </button>
        </div>
      </div>

      {/* Center: Status indicators */}
      <div className="hidden sm:flex items-center gap-2.5">
        {/* Backend Connectivity Status */}
        <div
          className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
            isBackendConnected
              ? 'bg-slate-900/60 border-slate-700/60 text-slate-300'
              : 'bg-red-950/40 border-red-500/30 text-red-300'
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              isBackendConnected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
            }`}
          />
          <span>{isBackendConnected ? 'FastAPI Engine Active' : 'Backend Disconnected'}</span>
        </div>

        {/* Honest Provider Status */}
        <button
          onClick={() => setSettingsModalOpen(true)}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-all ${
            isConfigured
              ? 'bg-cyan-950/40 border-cyan-500/40 text-cyan-300 hover:border-cyan-400'
              : 'bg-amber-950/40 border-amber-500/40 text-amber-300 hover:border-amber-400 hover:bg-amber-950/60'
          }`}
          title="Click to configure AI providers"
        >
          {isConfigured ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>Provider: Ready</span>
            </>
          ) : (
            <>
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
              <span>Provider: Setup Needed</span>
            </>
          )}
        </button>

        {/* Guardrail badge */}
        <div
          className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-midnight-950/60 border border-slate-800 text-slate-400"
          title="Adult content guardrail active; educational/medical content permitted"
        >
          <Shield className="w-3.5 h-3.5 text-violet-400" />
          <span>Safety Shield Active</span>
        </div>
      </div>

      {/* Right: Actions (Guide, Settings) */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setSetupGuideModalOpen(true)}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-slate-400 hover:text-cyan-300 rounded-lg hover:bg-slate-800/50 transition-colors"
          title="Stage 1 Architecture Guide"
        >
          <HelpCircle className="w-4 h-4" />
          <span className="hidden md:inline">Docs & Setup</span>
        </button>

        <button
          onClick={() => setSettingsModalOpen(true)}
          className="p-2 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800/50 transition-colors relative"
          title="Settings & API Keys"
          aria-label="Settings"
        >
          <SettingsIcon className="w-5 h-5" />
          {!isConfigured && (
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-amber-400 animate-ping" />
          )}
        </button>
      </div>
    </header>
  );
};
