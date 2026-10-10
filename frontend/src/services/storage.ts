import { Conversation, UserSettings } from '../types';

const STORAGE_KEYS = {
  CONVERSATIONS: 'nexora_conversations_v1',
  ACTIVE_ID: 'nexora_active_conversation_id',
  SETTINGS: 'nexora_settings_v1',
};

export const defaultSettings: UserSettings = {
  geminiApiKey: '',
  openaiApiKey: '',
  anthropicApiKey: '',
  selectedProvider: 'auto',
  selectedModel: 'gemini-1.5-flash',
  temperature: 0.7,
  systemPrompt: 'You are NEXORA AI, an intelligent, precision-focused assistant engineered with modular architecture for deep research, coding, and problem solving.',
  enableSafetyGuardrails: true,
  searchMode: 'ai_only',
  selectedSearchEngine: 'auto',
  tavilyApiKey: '',
  serperApiKey: '',
  braveApiKey: '',
  preferredLanguage: 'auto',
  // Stage 7 Voice Intelligence defaults
  voiceMode: 'push_to_talk',
  selectedVoiceId: 'browser_default',
  voiceSpeed: 1.0,
  autoSpeakAiResponses: false,
  transcriptionLanguage: 'auto',
};

export const storage = {
  getConversations(): Conversation[] {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.CONVERSATIONS);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      console.error('Failed to load conversations from storage', e);
      return [];
    }
  },

  saveConversations(conversations: Conversation[]): void {
    try {
      localStorage.setItem(STORAGE_KEYS.CONVERSATIONS, JSON.stringify(conversations));
    } catch (e) {
      console.error('Failed to persist conversations to storage', e);
    }
  },

  getActiveId(): string | null {
    return localStorage.getItem(STORAGE_KEYS.ACTIVE_ID);
  },

  setActiveId(id: string | null): void {
    if (id) {
      localStorage.setItem(STORAGE_KEYS.ACTIVE_ID, id);
    } else {
      localStorage.removeItem(STORAGE_KEYS.ACTIVE_ID);
    }
  },

  getSettings(): UserSettings {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.SETTINGS);
      if (data) {
        return { ...defaultSettings, ...JSON.parse(data) };
      }
    } catch (e) {
      console.error('Failed to load settings', e);
    }
    return defaultSettings;
  },

  saveSettings(settings: UserSettings): void {
    try {
      localStorage.setItem(STORAGE_KEYS.SETTINGS, JSON.stringify(settings));
    } catch (e) {
      console.error('Failed to save settings', e);
    }
  },

  clearAllData(): void {
    localStorage.removeItem(STORAGE_KEYS.CONVERSATIONS);
    localStorage.removeItem(STORAGE_KEYS.ACTIVE_ID);
  },
};
