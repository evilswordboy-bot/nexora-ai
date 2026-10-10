import React, { useState } from 'react';
import { Message } from '../../types';
import { useChat } from '../../context/ChatContext';
import { MarkdownRenderer } from './MarkdownRenderer';
import { SourcesSection } from './SourcesSection';
import {
  Sparkles,
  User,
  Copy,
  Check,
  RotateCcw,
  Edit3,
  X,
  AlertCircle,
  KeyRound,
  ShieldAlert,
  Globe,
  Compass,
  Volume2,
  VolumeX,
  Loader2,
} from 'lucide-react';

interface MessageItemProps {
  message: Message;
  isLast: boolean;
}

export const MessageItem: React.FC<MessageItemProps> = ({ message, isLast }) => {
  const {
    regenerateMessage,
    editAndResend,
    setSettingsModalOpen,
    isLoading,
    speakMessage,
    stopSpeaking,
    currentlySpeakingMessageId,
    isSpeaking,
  } = useChat();
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);

  const isUser = message.role === 'user';
  const isCurrentlySpeaking = currentlySpeakingMessageId === message.id && isSpeaking;
  const isSafetyGuard = message.provider === 'nexora-safety' || message.content.includes('Safety Guardrail');
  const isUnconfigured = message.content.includes('Setup Required') || message.content.includes('No active AI provider');

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSaveEdit = () => {
    if (editContent.trim() && editContent !== message.content) {
      editAndResend(message.id, editContent.trim());
    }
    setIsEditing(false);
  };

  const formatTime = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div
      className={`py-5 px-4 sm:px-6 transition-colors ${
        isUser ? 'bg-transparent' : 'bg-midnight-900/40 border-y border-slate-800/40'
      }`}
    >
      <div className="max-w-3xl mx-auto flex gap-3.5 sm:gap-4">
        {/* Avatar */}
        <div className="shrink-0 pt-0.5">
          {isUser ? (
            <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700/80 flex items-center justify-center text-slate-300">
              <User className="w-4 h-4" />
            </div>
          ) : isSafetyGuard ? (
            <div className="w-8 h-8 rounded-xl bg-violet-950/80 border border-violet-500/50 flex items-center justify-center text-violet-400">
              <ShieldAlert className="w-4 h-4" />
            </div>
          ) : message.search_mode === 'deep_research' ? (
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 shadow-violet-glow flex items-center justify-center text-white">
              <Compass className="w-4 h-4" />
            </div>
          ) : message.search_mode === 'web_search' ? (
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500 to-teal-600 shadow-cyan-glow flex items-center justify-center text-white">
              <Globe className="w-4 h-4" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500 to-violet-600 shadow-cyan-glow flex items-center justify-center text-white">
              <Sparkles className="w-4 h-4" />
            </div>
          )}
        </div>

        {/* Message Body */}
        <div className="flex-1 min-w-0">
          {/* Header (Author, Model tag, Search mode tag, Timestamp) */}
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-semibold text-slate-200">
                {isUser ? 'You' : 'NEXORA'}
              </span>

              {/* Search Mode badge */}
              {message.search_mode === 'deep_research' && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 border border-violet-500/30 flex items-center gap-1 font-medium">
                  <Compass className="w-3 h-3 text-violet-400" />
                  <span>Deep Research</span>
                </span>
              )}

              {message.search_mode === 'web_search' && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 flex items-center gap-1 font-medium">
                  <Globe className="w-3 h-3 text-cyan-400" />
                  <span>Web Search</span>
                </span>
              )}

              {!isUser && message.model && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700/50">
                  {message.model}
                </span>
              )}
            </div>
            <span className="text-[11px] text-slate-500">
              {formatTime(message.timestamp)}
            </span>
          </div>

          {/* Content / Edit View */}
          {isEditing ? (
            <div className="mt-2 space-y-2">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full bg-midnight-950 border border-cyan-500/50 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-cyan-500/40 min-h-[90px] font-sans"
              />
              <div className="flex items-center justify-end gap-2">
                <button
                  onClick={() => setIsEditing(false)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Cancel</span>
                </button>
                <button
                  onClick={handleSaveEdit}
                  className="flex items-center gap-1 px-3.5 py-1.5 rounded-lg text-xs bg-cyan-500 hover:bg-cyan-400 text-midnight-950 font-semibold transition-colors"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Save & Submit</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="mt-1">
              {message.error && (
                <div className="flex items-center gap-2 mb-2 text-red-400 text-xs font-semibold">
                  <AlertCircle className="w-4 h-4" />
                  <span>System Alert</span>
                </div>
              )}

              {/* Render Grounded Sources if available */}
              {!isUser && message.sources && message.sources.length > 0 && (
                <SourcesSection
                  sources={message.sources}
                  researchQueries={message.research_queries}
                />
              )}

              {/* Empty state while initial tokens are buffered */}
              {message.isStreaming && !message.content ? (
                <div className="flex items-center gap-2 py-2 text-xs text-cyan-400 font-medium">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                  <span>
                    {message.search_mode === 'deep_research'
                      ? 'NEXORA Deep Research is investigating...'
                      : message.search_mode === 'web_search'
                      ? 'Searching the web and synthesizing...'
                      : 'NEXORA is generating live response...'}
                  </span>
                </div>
              ) : (
                <div className="relative">
                  <MarkdownRenderer content={message.content} sources={message.sources} />
                  {message.isStreaming && (
                    <span className="inline-block w-2 h-4 ml-1 bg-cyan-400 animate-pulse rounded-sm align-middle shadow-cyan-glow" />
                  )}
                </div>
              )}

              {/* Honest Setup Button inside message if unconfigured */}
              {isUnconfigured && (
                <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between">
                  <span className="text-xs text-slate-400">
                    Ready to connect your AI provider?
                  </span>
                  <button
                    onClick={() => setSettingsModalOpen(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/40 text-cyan-300 text-xs font-semibold transition-colors"
                  >
                    <KeyRound className="w-3.5 h-3.5" />
                    <span>Enter API Key in Settings</span>
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Action Footer (Copy, Regenerate, Edit) */}
          {!isEditing && (
            <div className="flex items-center gap-2 mt-3 pt-1 border-t border-slate-800/30">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-300 transition-colors py-1 px-1.5 rounded hover:bg-slate-800/40"
                title="Copy message"
              >
                {copied ? (
                  <>
                    <Check className="w-3 h-3 text-cyan-400" />
                    <span className="text-cyan-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy</span>
                  </>
                )}
              </button>

              {/* Stage 7: Listen / Speak Control for Assistant Messages */}
              {!isUser && !message.isStreaming && message.content && (
                <button
                  onClick={() => {
                    if (isCurrentlySpeaking) {
                      stopSpeaking();
                    } else {
                      speakMessage(message.id, message.content);
                    }
                  }}
                  className={`flex items-center gap-1 text-[11px] transition-colors py-1 px-1.5 rounded ${
                    isCurrentlySpeaking
                      ? 'text-cyan-300 bg-cyan-500/20 border border-cyan-500/30 font-medium'
                      : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/40'
                  }`}
                  title={isCurrentlySpeaking ? 'Stop speech' : 'Listen to response'}
                >
                  {isCurrentlySpeaking ? (
                    <>
                      <VolumeX className="w-3 h-3 text-cyan-400 animate-pulse" />
                      <span>Stop Listening</span>
                    </>
                  ) : (
                    <>
                      <Volume2 className="w-3 h-3" />
                      <span>Listen</span>
                    </>
                  )}
                </button>
              )}

              {isUser && (
                <button
                  onClick={() => setIsEditing(true)}
                  className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-300 transition-colors py-1 px-1.5 rounded hover:bg-slate-800/40"
                  title="Edit prompt"
                >
                  <Edit3 className="w-3 h-3" />
                  <span>Edit</span>
                </button>
              )}

              {!isUser && isLast && !isLoading && (
                <button
                  onClick={() => regenerateMessage(message.id)}
                  className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-cyan-400 transition-colors py-1 px-1.5 rounded hover:bg-slate-800/40"
                  title="Regenerate response"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Regenerate</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
