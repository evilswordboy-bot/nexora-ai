import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../../context/ChatContext';
import { SearchMode } from '../../types';
import {
  Send,
  Square,
  Mic,
  MicOff,
  Paperclip,
  Globe,
  Compass,
  Cpu,
  Sparkles,
  Volume2,
} from 'lucide-react';
import { speechService } from '../../services/speech';

export const MessageInput: React.FC = () => {
  const {
    sendMessage,
    stopGeneration,
    isLoading,
    isStreaming,
    showToast,
    settings,
    searchMode,
    setSearchMode,
    setActiveWorkspaceView,
    isListening,
    setIsListening,
    isSpeaking,
    stopSpeaking,
  } = useChat();

  const [content, setContent] = useState('');
  const [interimVoiceText, setInterimVoiceText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea up to 200px
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [content, interimVoiceText]);

  const handleToggleMic = () => {
    if (isListening) {
      speechService.stopListening();
      setIsListening(false);
      setInterimVoiceText('');
      return;
    }

    // Interruption handling: Stop ongoing audio response before speaking
    if (isSpeaking) {
      stopSpeaking();
    }

    const langCode = settings.preferredLanguage !== 'auto' ? settings.preferredLanguage : 'en-US';

    const started = speechService.startListening(langCode, {
      onStart: () => {
        setIsListening(true);
        showToast('Listening... Speak now into your microphone.', 'info');
      },
      onResult: (transcript, isFinal) => {
        if (isFinal) {
          setContent((prev) => (prev ? `${prev.trim()} ${transcript}` : transcript));
          setInterimVoiceText('');
          // If Voice Chat mode is active, automatically send prompt upon turn completion
          if (settings.voiceMode === 'voice_chat') {
            const finalPrompt = content ? `${content.trim()} ${transcript}` : transcript;
            if (finalPrompt.trim()) {
              sendMessage(finalPrompt.trim());
              setContent('');
            }
          }
        } else {
          setInterimVoiceText(transcript);
        }
      },
      onError: (errMsg) => {
        setIsListening(false);
        setInterimVoiceText('');
        showToast(errMsg, 'error');
      },
      onEnd: () => {
        setIsListening(false);
        setInterimVoiceText('');
      },
    });

    if (!started) {
      setIsListening(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (!content.trim() || isLoading) return;
    sendMessage(content.trim());
    setContent('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleStageFeatureNotice = (featureName: string, phase: number) => {
    showToast(`${featureName} is scheduled for development in Phase ${phase} of the 100-phase roadmap.`, 'info');
  };

  const estimatedTokens = Math.ceil(content.length / 4);

  const searchModes: { id: SearchMode; label: string; icon: React.FC<{ className?: string }>; desc: string }[] = [
    {
      id: 'ai_only',
      label: 'AI Only',
      icon: Cpu,
      desc: 'Direct LLM reasoning without external web lookup',
    },
    {
      id: 'web_search',
      label: 'Web Search',
      icon: Globe,
      desc: 'Real-time web search with verified inline citations',
    },
    {
      id: 'deep_research',
      label: 'Deep Research',
      icon: Compass,
      desc: 'Multi-pass vector decomposition and evidence synthesis report',
    },
  ];

  return (
    <div className="p-3 sm:p-4 bg-midnight-950/80 border-t border-slate-800/80 backdrop-blur-lg">
      <div className="max-w-3xl mx-auto space-y-2">
        {/* Stage 3 Mode Selector Pills */}
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-midnight-900/90 border border-slate-800/80">
            {searchModes.map((mode) => {
              const Icon = mode.icon;
              const isActive = searchMode === mode.id;

              return (
                <button
                  key={mode.id}
                  type="button"
                  onClick={() => setSearchMode(mode.id)}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    isActive
                      ? mode.id === 'deep_research'
                        ? 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-violet-glow'
                        : mode.id === 'web_search'
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                        : 'bg-slate-800 text-slate-100 border border-slate-700/60 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                  title={mode.desc}
                >
                  <Icon className="w-3.5 h-3.5 shrink-0" />
                  <span>{mode.label}</span>
                </button>
              );
            })}
          </div>

          <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-slate-500 font-mono">
            <span>Engine: {settings.selectedSearchEngine || 'auto'}</span>
          </div>
        </div>

        {/* Active Speech Recognition Banner */}
        {isListening && (
          <div className="px-4 py-2 bg-red-950/40 border border-red-500/30 rounded-xl flex items-center justify-between animate-in fade-in">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping" />
              <span className="text-xs font-semibold text-red-300">Listening to your voice...</span>
              {interimVoiceText && (
                <span className="text-xs text-slate-300 italic">"{interimVoiceText}"</span>
              )}
            </div>
            <button
              onClick={handleToggleMic}
              className="text-[11px] px-2 py-0.5 rounded bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/40"
            >
              Done / Stop
            </button>
          </div>
        )}

        {/* Input Container Box */}
        <div className="relative rounded-2xl bg-midnight-900 border border-slate-800 focus-within:border-cyan-500/50 focus-within:ring-1 focus-within:ring-cyan-500/30 transition-all shadow-lg">
          {/* Main Textarea */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              searchMode === 'deep_research'
                ? `Ask a complex question for Deep Research investigation...`
                : searchMode === 'web_search'
                ? `Search web & ask NEXORA (${settings.selectedModel})...`
                : `Message NEXORA (${settings.selectedModel})...`
            }
            disabled={isLoading && !isStreaming}
            className="w-full bg-transparent px-4 pt-3.5 pb-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none resize-none min-h-[46px] max-h-[200px] scrollbar-thin scrollbar-thumb-slate-800 disabled:opacity-50"
          />

          {/* Controls Bar */}
          <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
            {/* Left: Future capabilities preview pills with honest tooltips */}
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setActiveWorkspaceView('documents')}
                className="p-1.5 rounded-lg text-slate-400 hover:text-cyan-300 hover:bg-slate-800/60 transition-colors"
                title="Documents Vault (Stage 4)"
              >
                <Paperclip className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={handleToggleMic}
                className={`p-1.5 rounded-lg transition-all ${
                  isListening
                    ? 'bg-red-500/20 text-red-400 border border-red-500/40 animate-pulse shadow-sm'
                    : 'text-slate-400 hover:text-cyan-300 hover:bg-slate-800/60'
                }`}
                title={isListening ? 'Stop recording (Listening...)' : 'Voice Input / Dictation (Stage 7)'}
              >
                {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>
            </div>

            {/* Right: Counter & Send/Stop Button */}
            <div className="flex items-center gap-3">
              {content.length > 0 && (
                <span className="text-[11px] text-slate-500 font-mono hidden sm:inline">
                  {content.length} chars (~{estimatedTokens} tokens)
                </span>
              )}

              {isLoading ? (
                <button
                  type="button"
                  onClick={stopGeneration}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/40 text-xs font-semibold transition-colors"
                  title="Stop generation"
                >
                  <Square className="w-3.5 h-3.5 fill-current animate-pulse" />
                  <span>Stop</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleSend}
                  disabled={!content.trim()}
                  className={`w-8 h-8 rounded-xl flex items-center justify-center transition-all ${
                    content.trim()
                      ? searchMode === 'deep_research'
                        ? 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-violet-glow hover:opacity-90'
                        : 'bg-gradient-to-r from-cyan-500 to-teal-600 text-white shadow-cyan-glow hover:opacity-90'
                      : 'bg-slate-800/60 text-slate-600 cursor-not-allowed'
                  }`}
                  title="Send message (Enter)"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Footer info text */}
        <div className="text-center text-[11px] text-slate-500 flex items-center justify-center gap-1.5">
          <Sparkles className="w-3 h-3 text-cyan-400/80" />
          <span>Stage 3 Universal Search & Deep Research • Shift+Enter for new line</span>
        </div>
      </div>
    </div>
  );
};
