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
  Image as ImageIcon,
  X as CloseIcon,
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
  const [attachedImages, setAttachedImages] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-resize textarea up to 200px
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [content, interimVoiceText]);

  const handleImageFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const allowed = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];

    Array.from(files).forEach((file) => {
      if (!allowed.includes(file.type.toLowerCase())) {
        showToast(`Skipped ${file.name}: only PNG, JPG, JPEG, and WEBP images are supported.`, 'error');
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        showToast(`Skipped ${file.name}: image exceeds 10MB limit.`, 'error');
        return;
      }
      if (attachedImages.length >= 5) {
        showToast('Maximum 5 images allowed per message.', 'error');
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        const res = e.target?.result as string;
        if (res) {
          setAttachedImages((prev) => (prev.length < 5 ? [...prev, res] : prev));
        }
      };
      reader.readAsDataURL(file);
    });
  };

  const removeImage = (index: number) => {
    setAttachedImages((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleImageFiles(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleToggleMic = () => {
    if (isListening) {
      speechService.stopListening();
      setIsListening(false);
      setInterimVoiceText('');
      return;
    }

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
    if ((!content.trim() && attachedImages.length === 0) || isLoading) return;
    sendMessage(content.trim(), attachedImages.length > 0 ? attachedImages : undefined);
    setContent('');
    setAttachedImages([]);
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
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`relative rounded-2xl bg-midnight-900 border transition-all shadow-lg ${
            isDragging
              ? 'border-cyan-400 bg-cyan-950/20 ring-2 ring-cyan-500/40'
              : 'border-slate-800 focus-within:border-cyan-500/50 focus-within:ring-1 focus-within:ring-cyan-500/30'
          }`}
        >
          {/* Hidden Image File Input */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => handleImageFiles(e.target.files)}
            multiple
            accept="image/png,image/jpeg,image/jpg,image/webp"
            className="hidden"
          />

          {/* Attached Images Preview Strip */}
          {attachedImages.length > 0 && (
            <div className="p-3 pb-0 flex flex-wrap gap-2.5">
              {attachedImages.map((imgSrc, idx) => (
                <div
                  key={idx}
                  className="relative group w-16 h-16 rounded-xl overflow-hidden border border-cyan-500/40 bg-midnight-950 shadow-md"
                >
                  <img src={imgSrc} alt="Preview" className="w-full h-full object-cover" />
                  <button
                    type="button"
                    onClick={() => removeImage(idx)}
                    className="absolute top-1 right-1 w-4 h-4 rounded-full bg-red-600/90 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Remove image"
                  >
                    <CloseIcon className="w-2.5 h-2.5" />
                  </button>
                </div>
              ))}
              <div className="flex items-center text-[11px] text-cyan-400 font-medium">
                {attachedImages.length}/5 images attached
              </div>
            </div>
          )}

          {/* Main Textarea */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              attachedImages.length > 0
                ? 'Ask a question or explain instructions for the attached image(s)...'
                : searchMode === 'deep_research'
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
            {/* Left: Actions & Attachment Tools */}
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className={`p-1.5 rounded-lg transition-colors ${
                  attachedImages.length > 0
                    ? 'text-cyan-400 bg-cyan-500/10 border border-cyan-500/30'
                    : 'text-slate-400 hover:text-cyan-300 hover:bg-slate-800/60'
                }`}
                title="Attach Images for Multimodal Vision (PNG, JPG, WEBP)"
              >
                <ImageIcon className="w-4 h-4" />
              </button>
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
                  disabled={!content.trim() && attachedImages.length === 0}
                  className={`w-8 h-8 rounded-xl flex items-center justify-center transition-all ${
                    content.trim() || attachedImages.length > 0
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
          <span>Stage 9 Visual Intelligence • Multimodal Vision & OCR • Shift+Enter for new line</span>
        </div>
      </div>
    </div>
  );
};
