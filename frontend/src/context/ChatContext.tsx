import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import { Conversation, Message, UserSettings, ProviderStatusResponse, ToastMessage } from '../types';
import { storage } from '../services/storage';
import { api } from '../services/api';

interface ChatContextType {
  conversations: Conversation[];
  activeConversationId: string | null;
  activeConversation: Conversation | null;
  isLoading: boolean;
  isBackendConnected: boolean;
  providerStatus: ProviderStatusResponse | null;
  settings: UserSettings;
  updateSettings: (newSettings: Partial<UserSettings>) => void;
  createNewConversation: () => Promise<string>;
  selectConversation: (id: string) => void;
  renameConversation: (id: string, newTitle: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  clearAllConversations: () => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  regenerateMessage: (messageId: string) => Promise<void>;
  editAndResend: (messageId: string, newContent: string) => Promise<void>;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean | ((prev: boolean) => boolean)) => void;
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
  settingsModalOpen: boolean;
  setSettingsModalOpen: (open: boolean) => void;
  setupGuideModalOpen: boolean;
  setSetupGuideModalOpen: (open: boolean) => void;
  toasts: ToastMessage[];
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
  removeToast: (id: string) => void;
  refreshProviderStatus: () => Promise<void>;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [conversations, setConversations] = useState<Conversation[]>(() => storage.getConversations());
  const [activeConversationId, setActiveConversationId] = useState<string | null>(() => storage.getActiveId());
  const [settings, setSettings] = useState<UserSettings>(() => storage.getSettings());
  const [isLoading, setIsLoading] = useState(false);
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [providerStatus, setProviderStatus] = useState<ProviderStatusResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [setupGuideModalOpen, setSetupGuideModalOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = useCallback((message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Save conversations to localStorage whenever changed
  useEffect(() => {
    storage.saveConversations(conversations);
  }, [conversations]);

  // Save activeId whenever changed
  useEffect(() => {
    storage.setActiveId(activeConversationId);
  }, [activeConversationId]);

  // Save settings whenever changed
  useEffect(() => {
    storage.saveSettings(settings);
  }, [settings]);

  const refreshProviderStatus = useCallback(async () => {
    try {
      const statusData = await api.getProviderStatus();
      setProviderStatus(statusData);
      setIsBackendConnected(true);
    } catch {
      setIsBackendConnected(false);
    }
  }, []);

  // Periodic health check & provider inspection
  useEffect(() => {
    refreshProviderStatus();
    const interval = setInterval(refreshProviderStatus, 15000);
    return () => clearInterval(interval);
  }, [refreshProviderStatus]);

  const activeConversation = useMemo(() => {
    return conversations.find((c) => c.id === activeConversationId) || null;
  }, [conversations, activeConversationId]);

  const updateSettings = useCallback((newSettings: Partial<UserSettings>) => {
    setSettings((prev) => {
      const updated = { ...prev, ...newSettings };
      return updated;
    });
    showToast('Settings saved', 'success');
  }, [showToast]);

  const createNewConversation = useCallback(async (): Promise<string> => {
    const newConv: Conversation = {
      id: 'conv-' + Date.now() + '-' + Math.random().toString(36).substring(2, 6),
      title: 'New Conversation',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      messages: [],
    };

    setConversations((prev) => [newConv, ...prev]);
    setActiveConversationId(newConv.id);
    setMobileMenuOpen(false);

    // Sync to backend if connected
    try {
      await api.createConversation(newConv.title);
    } catch {
      // Backend offline or local fallback - seamlessly continue
    }

    return newConv.id;
  }, []);

  const selectConversation = useCallback((id: string) => {
    setActiveConversationId(id);
    setMobileMenuOpen(false);
  }, []);

  const renameConversation = useCallback(async (id: string, newTitle: string) => {
    const trimmed = newTitle.trim();
    if (!trimmed) return;

    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title: trimmed, updated_at: new Date().toISOString() } : c))
    );

    try {
      await api.updateConversation(id, { title: trimmed });
    } catch {
      // Offline fallback ok
    }
    showToast('Conversation renamed', 'success');
  }, [showToast]);

  const deleteConversation = useCallback(async (id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeConversationId === id) {
      setActiveConversationId(null);
    }
    try {
      await api.deleteConversation(id);
    } catch {
      // Offline fallback ok
    }
    showToast('Conversation deleted', 'info');
  }, [activeConversationId, showToast]);

  const clearAllConversations = useCallback(async () => {
    setConversations([]);
    setActiveConversationId(null);
    storage.clearAllData();
    try {
      await api.clearAllConversations();
    } catch {
      // Offline fallback ok
    }
    showToast('All conversations cleared', 'info');
  }, [showToast]);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    let targetConvId = activeConversationId;

    // Create a new conversation if none is active
    if (!targetConvId) {
      const newId = 'conv-' + Date.now() + '-' + Math.random().toString(36).substring(2, 6);
      const newConv: Conversation = {
        id: newId,
        title: content.trim().split('\n')[0].substring(0, 36) || 'New Conversation',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        messages: [],
      };
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversationId(newId);
      targetConvId = newId;
    }

    const userMessage: Message = {
      id: 'msg-' + Date.now() + '-user',
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };

    // Optimistically update conversation state
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id === targetConvId) {
          const updatedTitle =
            c.title === 'New Conversation' ? content.trim().split('\n')[0].substring(0, 36) : c.title;
          return {
            ...c,
            title: updatedTitle,
            updated_at: new Date().toISOString(),
            messages: [...c.messages, userMessage],
          };
        }
        return c;
      })
    );

    setIsLoading(true);

    try {
      // Get complete message chain for context
      const currentConv = conversations.find((c) => c.id === targetConvId);
      const existingMessages = currentConv ? currentConv.messages : [];
      const messagesToSend = [...existingMessages, userMessage];

      const response = await api.sendChatMessage({
        conversationId: targetConvId,
        messages: messagesToSend,
        settings,
      });

      const assistantMessage: Message = {
        id: response.id,
        role: 'assistant',
        content: response.content,
        timestamp: new Date().toISOString(),
        model: response.model,
        provider: response.provider,
      };

      setConversations((prev) =>
        prev.map((c) => {
          if (c.id === targetConvId) {
            return {
              ...c,
              updated_at: new Date().toISOString(),
              messages: [...c.messages, assistantMessage],
            };
          }
          return c;
        })
      );
    } catch (err: any) {
      // Honest, transparent error representation
      const isConnectionErr = err.status === 0 || err.message?.includes('Network');
      const errorMessage: Message = {
        id: 'msg-' + Date.now() + '-err',
        role: 'assistant',
        content: isConnectionErr
          ? '🔌 **Backend Offline**\n\nCould not reach the Nexora FastAPI backend at `http://127.0.0.1:8000`. Please ensure the backend is running (`python run.py`) to process messages.'
          : `⚠️ **Request Error (${err.status || '500'})**\n\n${err.message || 'An unexpected error occurred.'}`,
        timestamp: new Date().toISOString(),
        error: true,
      };

      setConversations((prev) =>
        prev.map((c) => (c.id === targetConvId ? { ...c, messages: [...c.messages, errorMessage] } : c))
      );
    } finally {
      setIsLoading(false);
    }
  }, [activeConversationId, conversations, isLoading, settings]);

  const regenerateMessage = useCallback(async (messageId: string) => {
    if (!activeConversation || isLoading) return;

    // Find the message index
    const msgIdx = activeConversation.messages.findIndex((m) => m.id === messageId);
    if (msgIdx === -1) return;

    // Determine user prompt that triggered it
    let userPrompt = '';
    if (activeConversation.messages[msgIdx].role === 'assistant') {
      const prevMsg = activeConversation.messages[msgIdx - 1];
      if (prevMsg && prevMsg.role === 'user') {
        userPrompt = prevMsg.content;
      }
    }

    if (!userPrompt) return;

    // Remove the assistant message and re-send
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id === activeConversation.id) {
          return {
            ...c,
            messages: c.messages.slice(0, msgIdx),
          };
        }
        return c;
      })
    );

    await sendMessage(userPrompt);
  }, [activeConversation, isLoading, sendMessage]);

  const editAndResend = useCallback(async (messageId: string, newContent: string) => {
    if (!activeConversation || isLoading) return;

    const msgIdx = activeConversation.messages.findIndex((m) => m.id === messageId);
    if (msgIdx === -1) return;

    // Truncate messages after this message
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id === activeConversation.id) {
          return {
            ...c,
            messages: c.messages.slice(0, msgIdx),
          };
        }
        return c;
      })
    );

    await sendMessage(newContent);
  }, [activeConversation, isLoading, sendMessage]);

  return (
    <ChatContext.Provider
      value={{
        conversations,
        activeConversationId,
        activeConversation,
        isLoading,
        isBackendConnected,
        providerStatus,
        settings,
        updateSettings,
        createNewConversation,
        selectConversation,
        renameConversation,
        deleteConversation,
        clearAllConversations,
        sendMessage,
        regenerateMessage,
        editAndResend,
        searchQuery,
        setSearchQuery,
        sidebarCollapsed,
        setSidebarCollapsed,
        mobileMenuOpen,
        setMobileMenuOpen,
        settingsModalOpen,
        setSettingsModalOpen,
        setupGuideModalOpen,
        setSetupGuideModalOpen,
        toasts,
        showToast,
        removeToast,
        refreshProviderStatus,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};
