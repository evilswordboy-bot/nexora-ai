import React, { useState, useMemo } from 'react';
import { useChat } from '../../context/ChatContext';
import { Conversation } from '../../types';
import {
  Plus,
  MessageSquare,
  Search,
  Trash2,
  Edit2,
  Check,
  X,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Bot,
} from 'lucide-react';

interface SidebarProps {
  onConfirmDelete: (conv: Conversation) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onConfirmDelete }) => {
  const {
    conversations,
    activeConversationId,
    selectConversation,
    createNewConversation,
    renameConversation,
    searchQuery,
    setSearchQuery,
    sidebarCollapsed,
    setSidebarCollapsed,
    mobileMenuOpen,
    setMobileMenuOpen,
    settings,
  } = useChat();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  // Group conversations by time category
  const filteredConversations = useMemo(() => {
    if (!searchQuery.trim()) return conversations;
    const q = searchQuery.toLowerCase();
    return conversations.filter(
      (c) =>
        c.title.toLowerCase().includes(q) ||
        c.messages.some((m) => m.content.toLowerCase().includes(q))
    );
  }, [conversations, searchQuery]);

  const grouped = useMemo(() => {
    const today: Conversation[] = [];
    const yesterday: Conversation[] = [];
    const past7Days: Conversation[] = [];
    const older: Conversation[] = [];

    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const startOfYesterday = startOfToday - 86400000;
    const startOfPast7 = startOfToday - 7 * 86400000;

    filteredConversations.forEach((conv) => {
      const convTime = new Date(conv.updated_at || conv.created_at).getTime();
      if (convTime >= startOfToday) {
        today.push(conv);
      } else if (convTime >= startOfYesterday) {
        yesterday.push(conv);
      } else if (convTime >= startOfPast7) {
        past7Days.push(conv);
      } else {
        older.push(conv);
      }
    });

    return [
      { label: 'Today', items: today },
      { label: 'Yesterday', items: yesterday },
      { label: 'Previous 7 Days', items: past7Days },
      { label: 'Older', items: older },
    ].filter((g) => g.items.length > 0);
  }, [filteredConversations]);

  const handleStartRename = (e: React.MouseEvent, conv: Conversation) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const handleSaveRename = (e: React.MouseEvent | React.FormEvent, id: string) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      renameConversation(id, editTitle.trim());
    }
    setEditingId(null);
  };

  const handleCancelRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden transition-opacity"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-50 flex flex-col bg-midnight-900 border-r border-slate-800/80 transition-all duration-300 ease-in-out ${
          sidebarCollapsed ? 'w-0 md:w-16 overflow-hidden' : 'w-72 sm:w-80'
        } ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}
      >
        {/* Top Header / New Chat */}
        <div className="p-3.5 border-b border-slate-800/80 flex items-center justify-between gap-2 shrink-0">
          {!sidebarCollapsed ? (
            <>
              <button
                onClick={() => createNewConversation()}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-500/20 to-violet-500/20 hover:from-cyan-500/30 hover:to-violet-500/30 border border-cyan-500/30 hover:border-cyan-400/50 text-cyan-200 font-medium text-sm transition-all shadow-sm group"
              >
                <Plus className="w-4 h-4 text-cyan-400 group-hover:scale-110 transition-transform" />
                <span>New Conversation</span>
              </button>
              <button
                onClick={() => setSidebarCollapsed(true)}
                className="hidden md:flex p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 rounded-lg transition-colors"
                title="Collapse sidebar"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="md:hidden p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </>
          ) : (
            <div className="flex flex-col items-center gap-3 w-full">
              <button
                onClick={() => createNewConversation()}
                className="w-10 h-10 rounded-xl bg-gradient-to-r from-cyan-500/20 to-violet-500/20 border border-cyan-500/30 text-cyan-400 flex items-center justify-center hover:scale-105 transition-transform"
                title="New Chat"
              >
                <Plus className="w-5 h-5" />
              </button>
              <button
                onClick={() => setSidebarCollapsed(false)}
                className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 rounded-lg transition-colors"
                title="Expand sidebar"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          )}
        </div>

        {!sidebarCollapsed && (
          <>
            {/* Search Filter */}
            <div className="px-3.5 py-2.5 shrink-0">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search chats..."
                  className="w-full bg-midnight-950/70 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 transition-all"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Conversation History List */}
            <div className="flex-1 overflow-y-auto px-2 space-y-4 py-2 scrollbar-thin scrollbar-thumb-slate-800">
              {grouped.length === 0 ? (
                <div className="text-center py-12 px-4">
                  <div className="w-10 h-10 mx-auto rounded-full bg-slate-800/50 flex items-center justify-center text-slate-500 mb-2">
                    <MessageSquare className="w-5 h-5" />
                  </div>
                  <p className="text-xs text-slate-400">
                    {searchQuery ? 'No matching conversations' : 'No conversations yet'}
                  </p>
                  <p className="text-[11px] text-slate-600 mt-1">
                    Start a new chat to begin exploring
                  </p>
                </div>
              ) : (
                grouped.map((group) => (
                  <div key={group.label} className="space-y-1">
                    <div className="px-3 py-1 text-[11px] font-semibold tracking-wider uppercase text-slate-500">
                      {group.label}
                    </div>
                    {group.items.map((conv) => {
                      const isActive = conv.id === activeConversationId;
                      const isEditing = conv.id === editingId;

                      return (
                        <div
                          key={conv.id}
                          onClick={() => !isEditing && selectConversation(conv.id)}
                          className={`group relative flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer text-xs transition-all ${
                            isActive
                              ? 'bg-gradient-to-r from-cyan-500/15 to-violet-500/10 border border-cyan-500/30 text-slate-100 font-medium'
                              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 border border-transparent'
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0 flex-1 mr-2">
                            <MessageSquare
                              className={`w-4 h-4 shrink-0 ${
                                isActive ? 'text-cyan-400' : 'text-slate-500 group-hover:text-slate-400'
                              }`}
                            />
                            {isEditing ? (
                              <input
                                type="text"
                                value={editTitle}
                                onChange={(e) => setEditTitle(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') handleSaveRename(e, conv.id);
                                  if (e.key === 'Escape') setEditingId(null);
                                }}
                                autoFocus
                                className="bg-midnight-950 border border-cyan-500/50 rounded px-1.5 py-0.5 text-xs text-slate-100 w-full focus:outline-none"
                                onClick={(e) => e.stopPropagation()}
                              />
                            ) : (
                              <span className="truncate">{conv.title}</span>
                            )}
                          </div>

                          {/* Hover Action Buttons */}
                          <div
                            className={`flex items-center gap-1 shrink-0 ${
                              isEditing ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                            } transition-opacity`}
                            onClick={(e) => e.stopPropagation()}
                          >
                            {isEditing ? (
                              <>
                                <button
                                  onClick={(e) => handleSaveRename(e, conv.id)}
                                  className="p-1 hover:text-cyan-400 text-slate-400"
                                  title="Save"
                                >
                                  <Check className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={handleCancelRename}
                                  className="p-1 hover:text-red-400 text-slate-400"
                                  title="Cancel"
                                >
                                  <X className="w-3.5 h-3.5" />
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  onClick={(e) => handleStartRename(e, conv)}
                                  className="p-1 hover:text-slate-200 text-slate-500 transition-colors"
                                  title="Rename"
                                >
                                  <Edit2 className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onConfirmDelete(conv);
                                  }}
                                  className="p-1 hover:text-red-400 text-slate-500 transition-colors"
                                  title="Delete"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))
              )}
            </div>

            {/* Bottom active model badge */}
            <div className="p-3 border-t border-slate-800/80 bg-midnight-950/40 shrink-0">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <div className="flex items-center gap-2.5">
                  <img
                    src="/assets/nexora-eagle-logo.jpg"
                    alt="NEXORA AI Logo"
                    className="w-7 h-7 rounded-lg object-cover border border-cyan-400/40 shadow-sm"
                  />
                  <div>
                    <div className="text-[11px] font-semibold text-slate-200">
                      {settings.selectedModel}
                    </div>
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider">
                      NEXORA AI · Active Model
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </aside>
    </>
  );
};
