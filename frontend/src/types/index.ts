export type MessageRole = 'user' | 'assistant' | 'system';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  model?: string;
  provider?: string;
  error?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  system_prompt?: string;
  messages: Message[];
}

export interface ProviderInfo {
  name: string;
  display_name: string;
  configured: boolean;
  models: string[];
  description: string;
}

export interface ProviderStatusResponse {
  configured: boolean;
  active_provider: string | null;
  available_providers: ProviderInfo[];
  instructions: string;
}

export interface UserSettings {
  geminiApiKey: string;
  openaiApiKey: string;
  anthropicApiKey: string;
  selectedProvider: string;
  selectedModel: string;
  temperature: number;
  systemPrompt: string;
  enableSafetyGuardrails: boolean;
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}
