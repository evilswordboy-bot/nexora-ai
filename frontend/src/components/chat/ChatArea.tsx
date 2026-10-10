import React, { useRef, useEffect, useState } from 'react';
import { useChat } from '../../context/ChatContext';
import { MessageItem } from './MessageItem';
import { WelcomeScreen } from './WelcomeScreen';
import { MessageInput } from './MessageInput';
import { ResearchProgressCard } from './ResearchProgressCard';
import { ArrowDown, Loader2 } from 'lucide-react';

export const ChatArea: React.FC = () => {
  const { activeConversation, isLoading, researchProgress } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);

  const messages = activeConversation?.messages || [];

  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  useEffect(() => {
    scrollToBottom('smooth');
  }, [messages.length, isLoading]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isUp = scrollHeight - scrollTop - clientHeight > 150;
    setShowScrollBottom(isUp);
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-midnight-950 relative">
      {/* Scrollable messages container */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-800"
      >
        {messages.length === 0 ? (
          <WelcomeScreen />
        ) : (
          <div className="py-4 divide-y divide-slate-800/40">
            {messages.map((message, idx) => (
              <MessageItem
                key={message.id}
                message={message}
                isLast={idx === messages.length - 1}
              />
            ))}

            {/* Deep Research Progress Card */}
            {researchProgress && (
              <ResearchProgressCard progress={researchProgress} />
            )}

            {/* Live generation loading indicator */}
            {isLoading && !researchProgress && (
              <div className="py-5 px-4 sm:px-6 bg-midnight-900/40 border-y border-slate-800/40">
                <div className="max-w-3xl mx-auto flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500 to-violet-600 shadow-cyan-glow flex items-center justify-center text-white">
                    <Loader2 className="w-4 h-4 animate-spin" />
                  </div>
                  <div className="flex items-center gap-2 text-sm text-cyan-300 font-medium">
                    <span>NEXORA is synthesizing response...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} className="h-4" />
          </div>
        )}
      </div>

      {/* Floating scroll to bottom button */}
      {showScrollBottom && (
        <button
          onClick={() => scrollToBottom('smooth')}
          className="absolute bottom-24 right-8 p-2.5 rounded-full bg-midnight-800/90 border border-slate-700 text-cyan-400 hover:text-cyan-300 shadow-xl backdrop-blur-md transition-all hover:scale-105 z-20"
          title="Jump to bottom"
        >
          <ArrowDown className="w-4 h-4" />
        </button>
      )}

      {/* Fixed Message Input */}
      <MessageInput />
    </div>
  );
};
