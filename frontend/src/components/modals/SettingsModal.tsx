import React, { useState } from 'react';
import { useChat } from '../../context/ChatContext';
import {
  X,
  Key,
  Sliders,
  Shield,
  Database,
  Download,
  Upload,
  Trash2,
  Check,
  Eye,
  EyeOff,
  Sparkles,
  Search,
  Globe,
} from 'lucide-react';

export const SettingsModal: React.FC = () => {
  const {
    settings,
    updateSettings,
    settingsModalOpen,
    setSettingsModalOpen,
    conversations,
    clearAllConversations,
    showToast,
  } = useChat();

  const [activeTab, setActiveTab] = useState<'api' | 'search' | 'model' | 'safety' | 'data'>('api');
  const [showGeminiKey, setShowGeminiKey] = useState(false);
  const [showOpenAiKey, setShowOpenAiKey] = useState(false);
  const [showAnthropicKey, setShowAnthropicKey] = useState(false);
  const [showTavilyKey, setShowTavilyKey] = useState(false);
  const [showSerperKey, setShowSerperKey] = useState(false);
  const [showBraveKey, setShowBraveKey] = useState(false);

  // Local form state
  const [form, setForm] = useState({ ...settings });

  if (!settingsModalOpen) return null;

  const handleSave = () => {
    updateSettings(form);
    setSettingsModalOpen(false);
  };

  const handleExportData = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(conversations, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `nexora_conversations_backup_${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    showToast('Exported conversations backup successfully', 'success');
  };

  const handleImportData = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target?.result as string);
        if (Array.isArray(parsed)) {
          localStorage.setItem('nexora_conversations_v1', JSON.stringify(parsed));
          window.location.reload();
        } else {
          showToast('Invalid backup format. Must be an array of conversations.', 'error');
        }
      } catch {
        showToast('Failed to parse backup file.', 'error');
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-midnight-900 border border-slate-800 rounded-3xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/80">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">Settings & Configuration</h2>
              <p className="text-xs text-slate-400">Configure AI providers, parameters, and storage</p>
            </div>
          </div>
          <button
            onClick={() => setSettingsModalOpen(false)}
            className="p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800 px-6 gap-6 text-xs font-medium">
          <button
            onClick={() => setActiveTab('api')}
            className={`py-3 flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === 'api'
                ? 'border-cyan-400 text-cyan-300 font-semibold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Key className="w-4 h-4" />
            <span>AI Providers & Keys</span>
          </button>

          <button
            onClick={() => setActiveTab('search')}
            className={`py-3 flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === 'search'
                ? 'border-cyan-400 text-cyan-300 font-semibold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Globe className="w-4 h-4" />
            <span>Search & Research</span>
          </button>

          <button
            onClick={() => setActiveTab('model')}
            className={`py-3 flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === 'model'
                ? 'border-cyan-400 text-cyan-300 font-semibold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>Model Parameters</span>
          </button>

          <button
            onClick={() => setActiveTab('safety')}
            className={`py-3 flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === 'safety'
                ? 'border-cyan-400 text-cyan-300 font-semibold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Shield className="w-4 h-4" />
            <span>Content Safety</span>
          </button>

          <button
            onClick={() => setActiveTab('data')}
            className={`py-3 flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === 'data'
                ? 'border-cyan-400 text-cyan-300 font-semibold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Database className="w-4 h-4" />
            <span>Data Vault</span>
          </button>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-sm">
          {activeTab === 'api' && (
            <div className="space-y-5">
              <div className="p-3.5 rounded-xl bg-midnight-950/70 border border-cyan-500/20 text-xs text-slate-300 space-y-1">
                <span className="font-semibold text-cyan-400">Client-Side Secure Storage:</span>
                <p className="text-slate-400">
                  Keys saved here remain in your browser session and are relayed securely to the backend dispatcher without permanent disk logging.
                </p>
              </div>

              {/* Provider Selection */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Active Provider Priority
                </label>
                <select
                  value={form.selectedProvider}
                  onChange={(e) => setForm({ ...form, selectedProvider: e.target.value })}
                  className="w-full bg-midnight-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-slate-200 text-sm focus:border-cyan-500/50 focus:outline-none"
                >
                  <option value="auto">Auto-Detect Configured Key (Recommended)</option>
                  <option value="gemini">Google Gemini</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic Claude</option>
                </select>
              </div>

              {/* Google Gemini Key */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Google Gemini API Key
                </label>
                <div className="relative">
                  <input
                    type={showGeminiKey ? 'text' : 'password'}
                    value={form.geminiApiKey}
                    onChange={(e) => setForm({ ...form, geminiApiKey: e.target.value })}
                    placeholder="AIzaSy..."
                    className="w-full bg-midnight-950 border border-slate-800 rounded-xl px-3.5 py-2.5 pr-10 text-slate-200 text-sm focus:border-cyan-500/50 focus:outline-none font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowGeminiKey(!showGeminiKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showGeminiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Get a free key at <a href="https://aistudio.google.com" target="_blank" rel="noreferrer" className="text-cyan-400 underline">aistudio.google.com</a>
                </p>
              </div>

              {/* OpenAI Key */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  OpenAI API Key
                </label>
                <div className="relative">
                  <input
                    type={showOpenAiKey ? 'text' : 'password'}
                    value={form.openaiApiKey}
                    onChange={(e) => setForm({ ...form, openaiApiKey: e.target.value })}
                    placeholder="sk-proj-..."
                    className="w-full bg-midnight-950 border border-slate-800 rounded-xl px-3.5 py-2.5 pr-10 text-slate-200 text-sm focus:border-cyan-500/50 focus:outline-none font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowOpenAiKey(!showOpenAiKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showOpenAiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Anthropic Key */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Anthropic API Key
                </label>
                <div className="relative">
                  <input
                    type={showAnthropicKey ? 'text' : 'password'}
                    value={form.anthropicApiKey}
                    onChange={(e) => setForm({ ...form, anthropicApiKey: e.target.value })}
                    placeholder="sk-ant-..."
                    className="w-full bg-midnight-950 border border-slate-800 rounded-xl px-3.5 py-2.5 pr-10 text-slate-200 text-sm focus:border-cyan-500/50 focus:outline-none font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowAnthropicKey(!showAnthropicKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showAnthropicKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'search' && (
            <div className="space-y-5">
              <div className="p-3.5 rounded-xl bg-midnight-950/70 border border-cyan-500/20 text-xs text-slate-300 space-y-1">
                <span className="font-semibold text-cyan-400">Universal Web Search & Deep Research Engine:</span>
                <p className="text-slate-400">
                  Nexora searches real-time web sources with zero fake links or simulated citations. DuckDuckGo works out of the box with zero credentials. Configure Tavily, Serper, or Brave for high-speed AI web grounding.
                </p>
              </div>

              {/* Default Search Engine */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Preferred Search Engine
                </label>
                <select
                  value={form.selectedSearchEngine}
                  onChange={(e) => setForm({ ...form, selectedSearchEngine: e.target.value })}
                  className="w-full bg-midnight-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-slate-200 text-sm focus:border-cyan-500/50 focus:outline-none"
                >
                  <option value="auto">Auto (Configured Key or DuckDuckGo fallback)</option>
                  <option value="duckduckgo">DuckDuckGo (Free / Zero-Config)</option>
                  <option value="tavily">Tavily AI Search (High Accuracy)</option>
                  <option value="serper">Serper Google API</option>
                  <option value="brave">Brave Search API</option>
                </select>
              </div>

              {/* Tavily API Key */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-slate-300">
                    Tavily Search API Key
                  </label>
                  <a
                    href="https://tavily.com"
                    target="_blank"
                    rel="noreferrer"
                    className="text-[11px] text-cyan-400 hover:underline"
                  >
                    Get free key
                  </a>
                </div>
                <div className="relative">
                  <input
                    type={showTavilyKey ? 'text' : 'password'}
                    value={form.tavilyApiKey}
                    onChange={(e) => setForm({ ...form, tavilyApiKey: e.target.value })}
                    placeholder="tvly-..."
                    className="w-full bg-midnight-950 border border-slate-800 rounded-xl px-3.5 py-2.5 pr-10 text-slate-200 text-sm focus:border-cyan-500/50 focus:outline-none font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowTavilyKey(!showTavilyKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showTavilyKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Serper API Key */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-slate-300">
                    Serper (Google Search) API Key
                  </label>
                  <a
                    href="https://serper.dev"
                    target="_blank"
                    rel="noreferrer"
                    className="text-[11px] text-cyan-400 hover:underline"
                  >
                    serper.dev
                  </a>
                </div>
                <div className="relative">
                  <input
                    type={showSerperKey ? 'text' : 'password'}
                    value={form.serperApiKey}
                    onChange={(e) => setForm({ ...form, serperApiKey: e.target.value })}
                    placeholder="Enter Serper API Key..."
                    className="w-full bg-midnight-950 border border-slate-800 rounded-xl px-3.5 py-2.5 pr-10 text-slate-200 text-sm focus:border-cyan-500/50 focus:outline-none font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowSerperKey(!showSerperKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showSerperKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Brave API Key */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-slate-300">
                    Brave Search API Key
                  </label>
                  <a
                    href="https://brave.com/search/api/"
                    target="_blank"
                    rel="noreferrer"
                    className="text-[11px] text-cyan-400 hover:underline"
                  >
                    brave.com/search/api
                  </a>
                </div>
                <div className="relative">
                  <input
                    type={showBraveKey ? 'text' : 'password'}
                    value={form.braveApiKey}
                    onChange={(e) => setForm({ ...form, braveApiKey: e.target.value })}
                    placeholder="BSA..."
                    className="w-full bg-midnight-950 border border-slate-800 rounded-xl px-3.5 py-2.5 pr-10 text-slate-200 text-sm focus:border-cyan-500/50 focus:outline-none font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowBraveKey(!showBraveKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showBraveKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'model' && (
            <div className="space-y-5">
              {/* Model Choice */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Model Selection
                </label>
                <select
                  value={form.selectedModel}
                  onChange={(e) => setForm({ ...form, selectedModel: e.target.value })}
                  className="w-full bg-midnight-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-slate-200 text-sm focus:border-cyan-500/50 focus:outline-none font-mono"
                >
                  <optgroup label="Google Gemini">
                    <option value="gemini-1.5-flash">gemini-1.5-flash (Fast & Capable)</option>
                    <option value="gemini-1.5-pro">gemini-1.5-pro (Deep Reasoning)</option>
                    <option value="gemini-2.0-flash">gemini-2.0-flash (Next-Gen Preview)</option>
                  </optgroup>
                  <optgroup label="OpenAI">
                    <option value="gpt-4o">gpt-4o (Omni Flagship)</option>
                    <option value="gpt-4o-mini">gpt-4o-mini (Lightweight & Swift)</option>
                  </optgroup>
                  <optgroup label="Anthropic">
                    <option value="claude-3-5-sonnet-20241022">claude-3-5-sonnet (High Precision)</option>
                    <option value="claude-3-5-haiku-20241022">claude-3-5-haiku (Rapid)</option>
                  </optgroup>
                </select>
              </div>

              {/* Temperature */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Temperature ({form.temperature})
                  </label>
                  <span className="text-xs text-slate-500">
                    {form.temperature < 0.4 ? 'Focused & Deterministic' : form.temperature > 0.8 ? 'Creative & Exploratory' : 'Balanced'}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.5"
                  step="0.1"
                  value={form.temperature}
                  onChange={(e) => setForm({ ...form, temperature: parseFloat(e.target.value) })}
                  className="w-full accent-cyan-400 bg-slate-800 h-2 rounded-lg cursor-pointer"
                />
              </div>

              {/* System Prompt Customizer */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  System Persona Directive
                </label>
                <textarea
                  rows={4}
                  value={form.systemPrompt}
                  onChange={(e) => setForm({ ...form, systemPrompt: e.target.value })}
                  className="w-full bg-midnight-950 border border-slate-800 rounded-xl p-3 text-slate-200 text-xs focus:border-cyan-500/50 focus:outline-none"
                  placeholder="Define Nexora assistant behavior..."
                />
              </div>
            </div>
          )}

          {activeTab === 'safety' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-midnight-950/80 border border-violet-500/30 flex items-start gap-3">
                <Shield className="w-5 h-5 text-violet-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h4 className="text-sm font-semibold text-slate-100">
                    Adult-Content Guardrail with Medical & Educational Exemption
                  </h4>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Nexora AI implements a dual-classifier safety barrier:
                  </p>
                  <ul className="text-xs text-slate-300 list-disc pl-4 space-y-1 pt-1">
                    <li>Strictly blocks sexually gratuitous pornography and erotica.</li>
                    <li>
                      <strong>Preserves legitimate academic inquiries:</strong> human reproductive anatomy, medical clinical diagnostics, pathology, and biology education.
                    </li>
                  </ul>
                </div>
              </div>

              <div className="flex items-center justify-between p-4 rounded-xl bg-midnight-950/40 border border-slate-800">
                <div>
                  <div className="text-sm font-medium text-slate-200">Enforce Safety Shield</div>
                  <div className="text-xs text-slate-500">Evaluates prompts on FastAPI backend</div>
                </div>
                <input
                  type="checkbox"
                  checked={form.enableSafetyGuardrails}
                  onChange={(e) => setForm({ ...form, enableSafetyGuardrails: e.target.checked })}
                  className="w-4 h-4 accent-cyan-400 rounded cursor-pointer"
                />
              </div>
            </div>
          )}

          {activeTab === 'data' && (
            <div className="space-y-5">
              <div>
                <h4 className="text-sm font-semibold text-slate-200 mb-1">Export / Import Conversations</h4>
                <p className="text-xs text-slate-400 mb-3">Backup your conversation history locally in JSON format.</p>
                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={handleExportData}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors"
                  >
                    <Download className="w-4 h-4 text-cyan-400" />
                    <span>Export JSON Backup</span>
                  </button>

                  <label className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold cursor-pointer transition-colors">
                    <Upload className="w-4 h-4 text-violet-400" />
                    <span>Import JSON Backup</span>
                    <input
                      type="file"
                      accept=".json"
                      onChange={handleImportData}
                      className="hidden"
                    />
                  </label>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800">
                <h4 className="text-sm font-semibold text-red-400 mb-1">Danger Zone</h4>
                <p className="text-xs text-slate-400 mb-3">Permanently delete all conversation threads from local cache and backend memory.</p>
                <button
                  onClick={() => {
                    if (window.confirm('Are you sure you want to delete ALL conversations? This cannot be undone.')) {
                      clearAllConversations();
                      setSettingsModalOpen(false);
                    }
                  }}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-950/40 hover:bg-red-900/60 border border-red-500/30 text-red-300 text-xs font-semibold transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Clear All Conversations</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-midnight-950/60 border-t border-slate-800/80 flex items-center justify-end gap-3">
          <button
            onClick={() => setSettingsModalOpen(false)}
            className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-violet-600 text-white text-xs font-semibold shadow-cyan-glow hover:opacity-90 transition-all"
          >
            <Check className="w-4 h-4" />
            <span>Save Settings</span>
          </button>
        </div>
      </div>
    </div>
  );
};
