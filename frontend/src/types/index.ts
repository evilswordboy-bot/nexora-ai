export type MessageRole = 'user' | 'assistant' | 'system';

export type SearchMode = 'ai_only' | 'web_search' | 'deep_research';

export interface SearchResultItem {
  title: string;
  url: string;
  snippet: string;
  domain: string;
  published_date?: string;
  content?: string;
  source_id?: number;
}

export interface ResearchProgress {
  step: 'decomposing' | 'searching' | 'reading' | 'synthesizing' | 'complete';
  message: string;
  queries?: string[];
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  model?: string;
  provider?: string;
  error?: boolean;
  isStreaming?: boolean;
  sources?: SearchResultItem[];
  search_mode?: SearchMode;
  research_queries?: string[];
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
  configured_search_engines: string[];
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
  // Stage 3 Search Settings
  searchMode: SearchMode;
  selectedSearchEngine: string;
  tavilyApiKey: string;
  serperApiKey: string;
  braveApiKey: string;
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}
