import React, { createContext, useContext, useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  Conversation,
  Message,
  UserSettings,
  ProviderStatusResponse,
  ToastMessage,
  SearchMode,
  ResearchProgress,
  SearchResultItem,
} from '../types';
import { storage } from '../services/storage';
import { api } from '../services/api';
import { speechService } from '../services/speech';

interface ChatContextType {
  conversations: Conversation[];
  activeConversationId: string | null;
  activeConversation: Conversation | null;
  isLoading: boolean;
  isStreaming: boolean;
  searchMode: SearchMode;
  setSearchMode: (mode: SearchMode) => void;
  researchProgress: ResearchProgress | null;
  isBackendConnected: boolean;
  providerStatus: ProviderStatusResponse | null;
  settings: UserSettings;
  updateSettings: (newSettings: Partial<UserSettings>) => void;
  createNewConversation: () => Promise<string>;
  selectConversation: (id: string) => void;
  renameConversation: (id: string, newTitle: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  clearAllConversations: () => Promise<void>;
  sendMessage: (content: string, images?: string[]) => Promise<void>;
  stopGeneration: () => void;
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
  // Workspace Views (Stages 4, 5, 6, 8, 9, 11, 12, 13, 14)
  activeWorkspaceView: 'chat' | 'documents' | 'factcheck' | 'translation' | 'realtime' | 'vision' | 'reasoning' | 'routing' | 'memory' | 'agents';
  setActiveWorkspaceView: (view: 'chat' | 'documents' | 'factcheck' | 'translation' | 'realtime' | 'vision' | 'reasoning' | 'routing' | 'memory' | 'agents') => void;
  selectedDocumentIds: string[];
  toggleSelectDocument: (docId: string) => void;
  clearSelectedDocuments: () => void;
  // Stage 7 Voice Intelligence State
  isListening: boolean;
  setIsListening: (listening: boolean) => void;
  isSpeaking: boolean;
  setIsSpeaking: (speaking: boolean) => void;
  currentlySpeakingMessageId: string | null;
  speakMessage: (messageId: string, text: string) => Promise<void>;
  stopSpeaking: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [conversations, setConversations] = useState<Conversation[]>(() => storage.getConversations());
  const [activeConversationId, setActiveConversationId] = useState<string | null>(() => storage.getActiveId());
  const [settings, setSettings] = useState<UserSettings>(() => storage.getSettings());
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [researchProgress, setResearchProgress] = useState<ResearchProgress | null>(null);
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [providerStatus, setProviderStatus] = useState<ProviderStatusResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [setupGuideModalOpen, setSetupGuideModalOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  // Workspace Views State (Stages 4, 5, 6, 8, 9, 11, 12, 13, 14)
  const [activeWorkspaceView, setActiveWorkspaceView] = useState<'chat' | 'documents' | 'factcheck' | 'translation' | 'realtime' | 'vision' | 'reasoning' | 'routing' | 'memory' | 'agents'>('chat');
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);

  // Stage 7 Voice Intelligence State
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [currentlySpeakingMessageId, setCurrentlySpeakingMessageId] = useState<string | null>(null);

  const stopSpeaking = useCallback(() => {
    speechService.stopSpeaking();
    setIsSpeaking(false);
    setCurrentlySpeakingMessageId(null);
  }, []);

  const speakMessage = useCallback(async (messageId: string, text: string) => {
    stopSpeaking();
    setCurrentlySpeakingMessageId(messageId);
    setIsSpeaking(true);

    try {
      // 1. Check if backend TTS synthesis is available with audio bytes
      const ttsRes = await api.synthesizeSpeech({
        text,
        voiceId: settings.selectedVoiceId,
        speed: settings.voiceSpeed,
        settings,
      });

      if (ttsRes.audio_content) {
        // High fidelity audio returned from server (e.g. OpenAI TTS)
        speechService.playAudioBase64(ttsRes.audio_content, () => {
          setIsSpeaking(false);
          setCurrentlySpeakingMessageId(null);
        });
      } else {
        // Synthesize via clean text with Web Speech API
        const textToSpeak = ttsRes.clean_spoken_text || text;
        speechService.speakText({
          text: textToSpeak,
          lang: settings.preferredLanguage !== 'auto' ? settings.preferredLanguage : undefined,
          speed: settings.voiceSpeed,
          onStart: () => setIsSpeaking(true),
          onEnd: () => {
            setIsSpeaking(false);
            setCurrentlySpeakingMessageId(null);
          },
          onError: () => {
            setIsSpeaking(false);
            setCurrentlySpeakingMessageId(null);
          },
        });
      }
    } catch (e) {
      // Direct Web Speech API fallback
      speechService.speakText({
        text: text.replace(/```[\s\S]*?```/g, ''),
        speed: settings.voiceSpeed,
        onEnd: () => {
          setIsSpeaking(false);
          setCurrentlySpeakingMessageId(null);
        },
        onError: () => {
          setIsSpeaking(false);
          setCurrentlySpeakingMessageId(null);
        },
      });
    }
  }, [settings, stopSpeaking]);

  const toggleSelectDocument = useCallback((docId: string) => {
    setSelectedDocumentIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  }, []);

  const clearSelectedDocuments = useCallback(() => {
    setSelectedDocumentIds([]);
  }, []);

  const abortControllerRef = useRef<AbortController | null>(null);

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

  useEffect(() => {
    storage.saveConversations(conversations);
  }, [conversations]);

  useEffect(() => {
    storage.setActiveId(activeConversationId);
  }, [activeConversationId]);

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

  useEffect(() => {
    refreshProviderStatus();
    const interval = setInterval(refreshProviderStatus, 15000);
    return () => clearInterval(interval);
  }, [refreshProviderStatus]);

  const activeConversation = useMemo(() => {
    return conversations.find((c) => c.id === activeConversationId) || null;
  }, [conversations, activeConversationId]);

  const updateSettings = useCallback((newSettings: Partial<UserSettings>) => {
    setSettings((prev) => ({ ...prev, ...newSettings }));
    showToast('Settings saved', 'success');
  }, [showToast]);

  const searchMode = settings.searchMode || 'ai_only';
  const setSearchMode = useCallback((mode: SearchMode) => {
    setSettings((prev) => ({ ...prev, searchMode: mode }));
  }, []);

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

    try {
      await api.createConversation(newConv.title);
    } catch {
      // Local storage fallback
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
      // Local storage fallback
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
      // Local storage fallback
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
      // Local storage fallback
    }
    showToast('All conversations cleared', 'info');
  }, [showToast]);

  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setIsStreaming(false);
    setResearchProgress(null);

    setConversations((prev) =>
      prev.map((c) => ({
        ...c,
        messages: c.messages.map((m) => (m.isStreaming ? { ...m, isStreaming: false } : m)),
      }))
    );
    showToast('Generation stopped', 'info');
  }, [showToast]);

  const sendMessage = useCallback(async (content: string, images?: string[]) => {
    if ((!content.trim() && (!images || images.length === 0)) || isLoading) return;

    let targetConvId = activeConversationId;
    let isBrandNew = false;

    if (!targetConvId) {
      isBrandNew = true;
      const newId = 'conv-' + Date.now() + '-' + Math.random().toString(36).substring(2, 6);
      const newConv: Conversation = {
        id: newId,
        title: 'New Conversation',
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
      content: content.trim() || (images && images.length > 0 ? 'Analyze attached image(s)' : ''),
      timestamp: new Date().toISOString(),
      search_mode: settings.searchMode,
      images: images && images.length > 0 ? images : undefined,
    };

    const assistantPlaceholderId = 'msg-' + Date.now() + '-assistant';
    const assistantPlaceholder: Message = {
      id: assistantPlaceholderId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      model: settings.selectedModel,
      provider: settings.selectedProvider,
      search_mode: settings.searchMode,
      isStreaming: true,
      sources: [],
    };

    setConversations((prev) =>
      prev.map((c) => {
        if (c.id === targetConvId) {
          return {
            ...c,
            updated_at: new Date().toISOString(),
            messages: [...c.messages, userMessage, assistantPlaceholder],
          };
        }
        return c;
      })
    );

    setIsLoading(true);
    setIsStreaming(true);
    setResearchProgress(null);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      const currentConv = conversations.find((c) => c.id === targetConvId);
      const existingMessages = currentConv ? currentConv.messages : [];
      const messagesToSend = [...existingMessages, userMessage];

      let accumulatedContent = '';

      await api.streamChatMessage({
        conversationId: targetConvId,
        messages: messagesToSend,
        settings,
        images: images && images.length > 0 ? images : undefined,
        document_ids: selectedDocumentIds.length > 0 ? selectedDocumentIds : undefined,
        signal: abortController.signal,
        onStart: (info) => {
          setConversations((prev) =>
            prev.map((c) => {
              if (c.id === targetConvId) {
                return {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === assistantPlaceholderId
                      ? { ...m, model: info.model, provider: info.provider }
                      : m
                  ),
                };
              }
              return c;
            })
          );
        },
        onResearchProgress: (progress) => {
          setResearchProgress(progress);
        },
        onResearchSources: (sources) => {
          setConversations((prev) =>
            prev.map((c) => {
              if (c.id === targetConvId) {
                return {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === assistantPlaceholderId ? { ...m, sources } : m
                  ),
                };
              }
              return c;
            })
          );
        },
        onChunk: (chunk) => {
          accumulatedContent += chunk;
          setConversations((prev) =>
            prev.map((c) => {
              if (c.id === targetConvId) {
                return {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === assistantPlaceholderId
                      ? { ...m, content: accumulatedContent, isStreaming: true }
                      : m
                  ),
                };
              }
              return c;
            })
          );
        },
        onDone: () => {
          setResearchProgress(null);
          setConversations((prev) =>
            prev.map((c) => {
              if (c.id === targetConvId) {
                return {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === assistantPlaceholderId
                      ? { ...m, content: accumulatedContent, isStreaming: false }
                      : m
                  ),
                };
              }
              return c;
            })
          );
          if (settings.autoSpeakAiResponses || settings.voiceMode === 'voice_chat' || settings.voiceMode === 'text_and_voice') {
            speakMessage(assistantPlaceholderId, accumulatedContent);
          }
        },
        onError: (errorMsg) => {
          setResearchProgress(null);
          setConversations((prev) =>
            prev.map((c) => {
              if (c.id === targetConvId) {
                return {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === assistantPlaceholderId
                      ? {
                          ...m,
                          content: `⚠️ **Generation Error**: ${errorMsg}`,
                          error: true,
                          isStreaming: false,
                        }
                      : m
                  ),
                };
              }
              return c;
            })
          );
        },
      });

      // Auto-generate title
      const convNow = conversations.find((c) => c.id === targetConvId);
      if (isBrandNew || (convNow && convNow.title === 'New Conversation')) {
        api.generateTitle(content, targetConvId, settings).then((smartTitle) => {
          if (smartTitle) {
            setConversations((prev) =>
              prev.map((c) => (c.id === targetConvId ? { ...c, title: smartTitle } : c))
            );
          }
        });
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        const errorText = `⚠️ **Request Error**: ${err.message || 'Connection failure'}`;
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id === targetConvId) {
              return {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === assistantPlaceholderId
                    ? { ...m, content: errorText, error: true, isStreaming: false }
                    : m
                ),
              };
            }
            return c;
          })
        );
      }
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
      setResearchProgress(null);
      abortControllerRef.current = null;
    }
  }, [activeConversationId, conversations, isLoading, settings]);

  const regenerateMessage = useCallback(async (messageId: string) => {
    if (!activeConversation || isLoading) return;

    const msgIdx = activeConversation.messages.findIndex((m) => m.id === messageId);
    if (msgIdx === -1) return;

    let userPrompt = '';
    if (activeConversation.messages[msgIdx].role === 'assistant') {
      const prevMsg = activeConversation.messages[msgIdx - 1];
      if (prevMsg && prevMsg.role === 'user') {
        userPrompt = prevMsg.content;
      }
    }

    if (!userPrompt) return;

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
        isStreaming,
        searchMode,
        setSearchMode,
        researchProgress,
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
        stopGeneration,
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
        activeWorkspaceView,
        setActiveWorkspaceView,
        selectedDocumentIds,
        toggleSelectDocument,
        clearSelectedDocuments,
        isListening,
        setIsListening,
        isSpeaking,
        setIsSpeaking,
        currentlySpeakingMessageId,
        speakMessage,
        stopSpeaking,
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
