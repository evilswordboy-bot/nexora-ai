import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../../context/ChatContext';
import {
  Send,
  Square,
  Mic,
  Paperclip,
  Globe,
  Sparkles,
} from 'lucide-react';

export const MessageInput: React.FC = () => {
  const { sendMessage, stopGeneration, isLoading, isStreaming, showToast, settings } = useChat();
  const [content, setContent] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea up to 200px
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [content]);

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

  // Rough estimate of tokens (~4 chars per token)
  const estimatedTokens = Math.ceil(content.length / 4);

  return (
    <div className="p-3 sm:p-4 bg-midnight-950/80 border-t border-slate-800/80 backdrop-blur-lg">
      <div className="max-w-3xl mx-auto">
        {/* Input Container Box */}
        <div className="relative rounded-2xl bg-midnight-900 border border-slate-800 focus-within:border-cyan-500/50 focus-within:ring-1 focus-within:ring-cyan-500/30 transition-all shadow-lg">
          {/* Main Textarea */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Message NEXORA (${settings.selectedModel})...`}
            disabled={isLoading && !isStreaming}
            className="w-full bg-transparent px-4 pt-3.5 pb-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none resize-none min-h-[46px] max-h-[200px] scrollbar-thin scrollbar-thumb-slate-800 disabled:opacity-50"
          />

          {/* Controls Bar */}
          <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
            {/* Left: Future capabilities preview pills with honest tooltips */}
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => handleStageFeatureNotice('Document & File Analysis', 23)}
                className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800/60 transition-colors"
                title="Attach Document / Code (Coming in Phase 23)"
              >
                <Paperclip className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => handleStageFeatureNotice('Real-Time Web Research', 21)}
                className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800/60 transition-colors"
                title="Live Web Search (Coming in Phase 21)"
              >
                <Globe className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => handleStageFeatureNotice('Voice Transcription & Speech', 10)}
                className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800/60 transition-colors"
                title="Voice Dictation (Coming in Phase 10)"
              >
                <Mic className="w-4 h-4" />
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
                      ? 'bg-gradient-to-r from-cyan-500 to-violet-600 text-white shadow-cyan-glow hover:opacity-90'
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
        <div className="text-center mt-2 text-[11px] text-slate-500 flex items-center justify-center gap-1.5">
          <Sparkles className="w-3 h-3 text-cyan-400/80" />
          <span>Stage 2 Intelligence Engine • Real-time SSE streaming • Shift+Enter for new line</span>
        </div>
      </div>
    </div>
  );
};
