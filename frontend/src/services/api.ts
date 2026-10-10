import {
  Message,
  ProviderStatusResponse,
  UserSettings,
  Conversation,
  SearchResultItem,
  ResearchProgress,
  DocumentItem,
  DocumentChunk,
  DocumentAction,
  DocumentActionResponse,
  FactCheckResponse,
  LanguageDetectionResult,
  TranslationRequest,
  TranslationResponse,
  TranslationTone,
  VoiceInfo,
  TextToSpeechResponse,
  AudioTranscriptionResponse,
  MonitoredTopic,
  LiveNotification,
  LiveQueryRequest,
  LiveQueryResponse,
  LiveCategory,
  VisionAnalyzeRequest,
  VisionAnalyzeResponse,
  OCRRequest,
  OCRResponse,
  ImageCompareRequest,
  ImageCompareResponse,
} from '../types';

const BASE_URL = '/api/v1';

export class ApiError extends Error {
  constructor(public status: number, message: string, public detail?: any) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      let errorMsg = `Server error (${res.status})`;
      let detail = null;
      try {
        const errJson = await res.json();
        detail = errJson;
        errorMsg = errJson.detail || errJson.message || errorMsg;
      } catch {
        const text = await res.text();
        if (text) errorMsg = text;
      }
      throw new ApiError(res.status, errorMsg, detail);
    }
    if (res.status === 204) {
      return null as unknown as T;
    }
    return await res.json();
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(0, err.message || 'Network connection failed. Backend might be unreachable.');
  }
}

function resolveClientApiKey(settings: UserSettings): string {
  const { selectedProvider, geminiApiKey, openaiApiKey, anthropicApiKey } = settings;
  if (selectedProvider === 'gemini' || selectedProvider === 'auto') {
    return geminiApiKey || '';
  } else if (selectedProvider === 'openai') {
    return openaiApiKey || '';
  } else if (selectedProvider === 'anthropic') {
    return anthropicApiKey || '';
  }
  return '';
}

function resolveClientSearchKey(settings: UserSettings): string {
  const { selectedSearchEngine, tavilyApiKey, serperApiKey, braveApiKey } = settings;
  if (selectedSearchEngine === 'tavily' || tavilyApiKey) {
    return tavilyApiKey || '';
  } else if (selectedSearchEngine === 'serper' || serperApiKey) {
    return serperApiKey || '';
  } else if (selectedSearchEngine === 'brave' || braveApiKey) {
    return braveApiKey || '';
  }
  return '';
}

export const api = {
  async getHealth(): Promise<{ status: string; providers_configured: boolean; configured_providers: string[] }> {
    return request('/health');
  },

  async getProviderStatus(): Promise<ProviderStatusResponse> {
    return request('/providers/status');
  },

  async searchWeb(query: string, maxResults: number = 5, settings?: UserSettings): Promise<{ results: SearchResultItem[] }> {
    return request('/search', {
      method: 'POST',
      body: JSON.stringify({
        query,
        max_results: maxResults,
        engine: settings?.selectedSearchEngine || 'auto',
        client_search_key: settings ? resolveClientSearchKey(settings) : undefined,
      }),
    });
  },

  async sendChatMessage(params: {
    conversationId?: string;
    messages: Message[];
    settings: UserSettings;
    images?: string[];
  }): Promise<{ id: string; content: string; model: string; provider: string; sources?: SearchResultItem[]; finish_reason?: string }> {
    const clientApiKey = resolveClientApiKey(params.settings);
    const clientSearchKey = resolveClientSearchKey(params.settings);

    return request('/chat', {
      method: 'POST',
      body: JSON.stringify({
        conversation_id: params.conversationId,
        messages: params.messages,
        provider: params.settings.selectedProvider,
        model: params.settings.selectedModel,
        temperature: params.settings.temperature,
        system_prompt: params.settings.systemPrompt,
        client_api_key: clientApiKey || undefined,
        search_mode: params.settings.searchMode,
        search_engine: params.settings.selectedSearchEngine,
        client_search_key: clientSearchKey || undefined,
        target_language: params.settings.preferredLanguage && params.settings.preferredLanguage !== 'auto' ? params.settings.preferredLanguage : undefined,
        images: params.images,
        stream: false,
      }),
    });
  },

  async streamChatMessage(params: {
    conversationId?: string;
    messages: Message[];
    settings: UserSettings;
    images?: string[];
    signal?: AbortSignal;
    onStart?: (info: { id: string; model: string; provider: string }) => void;
    onResearchProgress?: (progress: ResearchProgress) => void;
    onResearchSources?: (sources: SearchResultItem[]) => void;
    onChunk: (chunk: string) => void;
    onDone?: (info: { id: string; finish_reason?: string }) => void;
    onError?: (errorMsg: string) => void;
  }): Promise<void> {
    const clientApiKey = resolveClientApiKey(params.settings);
    const clientSearchKey = resolveClientSearchKey(params.settings);
    const url = `${BASE_URL}/chat/stream`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: params.conversationId,
          messages: params.messages,
          provider: params.settings.selectedProvider,
          model: params.settings.selectedModel,
          temperature: params.settings.temperature,
          system_prompt: params.settings.systemPrompt,
          client_api_key: clientApiKey || undefined,
          search_mode: params.settings.searchMode,
          search_engine: params.settings.selectedSearchEngine,
          client_search_key: clientSearchKey || undefined,
          target_language: params.settings.preferredLanguage && params.settings.preferredLanguage !== 'auto' ? params.settings.preferredLanguage : undefined,
          images: params.images,
          stream: true,
        }),
        signal: params.signal,
      });

      if (!response.ok) {
        let errorMsg = `Server error (${response.status})`;
        try {
          const errData = await response.json();
          errorMsg = errData.detail || errData.message || errorMsg;
        } catch {
          const text = await response.text();
          if (text) errorMsg = text;
        }
        params.onError?.(errorMsg);
        return;
      }

      if (!response.body) {
        params.onError?.('Readable stream not supported by browser environment.');
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const event of events) {
          const lines = event.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6).trim();
              if (!dataStr) continue;
              try {
                const parsed = JSON.parse(dataStr);
                if (parsed.type === 'start') {
                  params.onStart?.(parsed);
                } else if (parsed.type === 'research_progress') {
                  params.onResearchProgress?.(parsed);
                } else if (parsed.type === 'research_sources') {
                  params.onResearchSources?.(parsed.sources || []);
                } else if (parsed.type === 'chunk') {
                  params.onChunk(parsed.content);
                } else if (parsed.type === 'done') {
                  params.onDone?.(parsed);
                } else if (parsed.type === 'error') {
                  params.onError?.(parsed.message || 'Stream processing error');
                }
              } catch {
                // Ignore partial JSON parsing glitches
              }
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        return;
      }
      params.onError?.(err.message || 'Streaming connection failed.');
    }
  },

  async generateTitle(userPrompt: string, conversationId?: string, settings?: UserSettings): Promise<string> {
    const clientApiKey = settings ? resolveClientApiKey(settings) : undefined;
    try {
      const res = await request<{ title: string }>('/chat/generate-title', {
        method: 'POST',
        body: JSON.stringify({
          user_prompt: userPrompt,
          conversation_id: conversationId,
          client_api_key: clientApiKey,
          provider: settings?.selectedProvider || 'auto',
        }),
      });
      return res.title;
    } catch {
      return userPrompt.trim().split('\n')[0].substring(0, 32);
    }
  },

  async getConversations(): Promise<Conversation[]> {
    return request('/conversations');
  },

  async createConversation(title?: string): Promise<Conversation> {
    return request('/conversations', {
      method: 'POST',
      body: JSON.stringify({ title: title || 'New Conversation' }),
    });
  },

  async updateConversation(id: string, data: { title?: string }): Promise<Conversation> {
    return request(`/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async deleteConversation(id: string): Promise<void> {
    return request(`/conversations/${id}`, {
      method: 'DELETE',
    });
  },

  async clearAllConversations(): Promise<{ message: string }> {
    return request('/conversations', {
      method: 'DELETE',
    });
  },

  // Stage 4: Document Intelligence Endpoints
  async uploadDocument(file: File): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${BASE_URL}/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      let errDetail = 'Failed to upload document';
      try {
        const errJson = await res.json();
        errDetail = errJson.detail || errJson.message || errDetail;
      } catch {
        const t = await res.text();
        if (t) errDetail = t;
      }
      throw new ApiError(res.status, errDetail);
    }
    return await res.json();
  },

  async listDocuments(): Promise<DocumentItem[]> {
    const res = await request<{ documents: DocumentItem[]; total_count: number }>('/documents');
    return res.documents;
  },

  async getDocumentDetails(documentId: string): Promise<{ document: DocumentItem; preview_text: string; chunks?: DocumentChunk[] }> {
    return request(`/documents/${documentId}`);
  },

  async deleteDocument(documentId: string): Promise<void> {
    return request(`/documents/${documentId}`, {
      method: 'DELETE',
    });
  },

  async executeDocumentAction(params: {
    documentIds: string[];
    action: DocumentAction;
    query?: string;
    settings?: UserSettings;
  }): Promise<DocumentActionResponse> {
    const clientApiKey = params.settings ? resolveClientApiKey(params.settings) : undefined;
    return request<DocumentActionResponse>('/documents/action', {
      method: 'POST',
      body: JSON.stringify({
        document_ids: params.documentIds,
        action: params.action,
        query: params.query || '',
        provider: params.settings?.selectedProvider || 'auto',
        model: params.settings?.selectedModel || 'gemini-1.5-flash',
        client_api_key: clientApiKey,
        temperature: params.settings?.temperature || 0.5,
      }),
    });
  },

  // Stage 5: Fact-Checking & Evidence Verification
  async verifyClaims(params: {
    text?: string;
    url?: string;
    documentIds?: string[];
    settings?: UserSettings;
  }): Promise<FactCheckResponse> {
    const clientApiKey = params.settings ? resolveClientApiKey(params.settings) : undefined;
    return request<FactCheckResponse>('/factcheck', {
      method: 'POST',
      body: JSON.stringify({
        text: params.text,
        url: params.url,
        document_ids: params.documentIds || [],
        search_engine: params.settings?.selectedSearchEngine || 'auto',
        client_search_key: params.settings?.tavilyApiKey || params.settings?.serperApiKey || params.settings?.braveApiKey,
        provider: params.settings?.selectedProvider || 'auto',
        model: params.settings?.selectedModel || 'gemini-1.5-flash',
        client_api_key: clientApiKey,
      }),
    });
  },

  // Stage 6: Universal Multilingual Intelligence
  async detectLanguage(text: string): Promise<LanguageDetectionResult> {
    return request<LanguageDetectionResult>('/multilingual/detect', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  },

  async translateText(params: {
    text: string;
    sourceLanguage?: string;
    targetLanguage: string;
    tone?: TranslationTone;
    includeTransliteration?: boolean;
    settings?: UserSettings;
  }): Promise<TranslationResponse> {
    const clientApiKey = params.settings ? resolveClientApiKey(params.settings) : undefined;
    return request<TranslationResponse>('/multilingual/translate', {
      method: 'POST',
      body: JSON.stringify({
        text: params.text,
        source_language: params.sourceLanguage || 'auto',
        target_language: params.targetLanguage,
        tone: params.tone || 'formal',
        include_transliteration: params.includeTransliteration ?? true,
        provider: params.settings?.selectedProvider || 'auto',
        model: params.settings?.selectedModel || 'gemini-1.5-flash',
        client_api_key: clientApiKey,
      }),
    });
  },

  async getLanguages(): Promise<{ supported_languages: Array<{ code: string; name: string }> }> {
    return request('/multilingual/languages');
  },

  // Stage 7: Voice Intelligence Engine
  async getVoices(): Promise<VoiceInfo[]> {
    return request<VoiceInfo[]>('/voice/voices');
  },

  async synthesizeSpeech(params: {
    text: string;
    voiceId?: string;
    languageCode?: string;
    speed?: number;
    settings?: UserSettings;
  }): Promise<TextToSpeechResponse> {
    const clientApiKey = params.settings ? resolveClientApiKey(params.settings) : undefined;
    return request<TextToSpeechResponse>('/voice/tts', {
      method: 'POST',
      body: JSON.stringify({
        text: params.text,
        voice_id: params.voiceId || params.settings?.selectedVoiceId || 'browser_default',
        language_code: params.languageCode || 'auto',
        speed: params.speed ?? params.settings?.voiceSpeed ?? 1.0,
        provider: params.settings?.selectedProvider || 'auto',
        client_api_key: clientApiKey,
      }),
    });
  },

  async transcribeAudio(params: {
    audioBlob: Blob;
    language?: string;
    settings?: UserSettings;
  }): Promise<AudioTranscriptionResponse> {
    const formData = new FormData();
    formData.append('file', params.audioBlob, 'recording.wav');
    formData.append('language', params.language || 'auto');
    const clientApiKey = params.settings ? resolveClientApiKey(params.settings) : undefined;
    if (clientApiKey) {
      formData.append('client_api_key', clientApiKey);
    }

    const url = `${BASE_URL}/voice/transcribe`;
    const res = await fetch(url, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      throw new ApiError(res.status, 'Audio transcription request failed.');
    }
    return res.json();
  },

  // Stage 8: Real-Time Intelligence Engine
  async executeLiveQuery(params: {
    query: string;
    category?: LiveCategory;
    forceRefresh?: boolean;
    maxSources?: number;
    settings?: UserSettings;
  }): Promise<LiveQueryResponse> {
    const clientSearchKey = params.settings ? resolveClientSearchKey(params.settings) : undefined;
    return request<LiveQueryResponse>('/realtime/query', {
      method: 'POST',
      body: JSON.stringify({
        query: params.query,
        category: params.category || 'general',
        force_refresh: params.forceRefresh ?? false,
        max_sources: params.maxSources ?? 5,
        search_engine: params.settings?.selectedSearchEngine || 'auto',
        client_search_key: clientSearchKey || undefined,
      }),
    });
  },

  async getMonitoredTopics(): Promise<MonitoredTopic[]> {
    return request<MonitoredTopic[]>('/realtime/topics');
  },

  async createMonitoredTopic(params: {
    name: string;
    queryOrUrl: string;
    category?: LiveCategory;
    checkIntervalMinutes?: number;
  }): Promise<MonitoredTopic> {
    return request<MonitoredTopic>('/realtime/topics', {
      method: 'POST',
      body: JSON.stringify({
        name: params.name,
        query_or_url: params.queryOrUrl,
        category: params.category || 'general',
        check_interval_minutes: params.checkIntervalMinutes ?? 60,
      }),
    });
  },

  async deleteMonitoredTopic(topicId: string): Promise<void> {
    return request(`/realtime/topics/${topicId}`, {
      method: 'DELETE',
    });
  },

  async refreshMonitoredTopic(topicId: string, settings?: UserSettings): Promise<MonitoredTopic> {
    const clientApiKey = settings ? resolveClientApiKey(settings) : undefined;
    return request<MonitoredTopic>(`/realtime/topics/${topicId}/refresh`, {
      method: 'POST',
      body: JSON.stringify({
        provider: settings?.selectedProvider || 'auto',
        model: settings?.selectedModel || 'gemini-1.5-flash',
        client_api_key: clientApiKey,
      }),
    });
  },

  async getLiveNotifications(): Promise<LiveNotification[]> {
    return request<LiveNotification[]>('/realtime/notifications');
  },

  async markNotificationsRead(): Promise<void> {
    return request('/realtime/notifications/read', {
      method: 'POST',
    });
  },

  async clearLiveNotifications(): Promise<void> {
    return request('/realtime/notifications', {
      method: 'DELETE',
    });
  },

  // Stage 9 Vision Intelligence Methods
  async analyzeVision(params: VisionAnalyzeRequest, settings?: UserSettings): Promise<VisionAnalyzeResponse> {
    const clientApiKey = settings ? resolveClientApiKey(settings) : undefined;
    return request<VisionAnalyzeResponse>('/vision/analyze', {
      method: 'POST',
      body: JSON.stringify({
        ...params,
        provider: params.provider || settings?.selectedProvider || 'auto',
        model: params.model || settings?.selectedModel || 'gemini-1.5-flash',
        client_api_key: params.client_api_key || clientApiKey,
      }),
    });
  },

  async extractOCR(params: OCRRequest): Promise<OCRResponse> {
    return request<OCRResponse>('/vision/ocr', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async compareImages(params: ImageCompareRequest, settings?: UserSettings): Promise<ImageCompareResponse> {
    const clientApiKey = settings ? resolveClientApiKey(settings) : undefined;
    return request<ImageCompareResponse>('/vision/compare', {
      method: 'POST',
      body: JSON.stringify({
        ...params,
        provider: params.provider || settings?.selectedProvider || 'auto',
        model: params.model || settings?.selectedModel || 'gemini-1.5-flash',
        client_api_key: params.client_api_key || clientApiKey,
      }),
    });
  },
};



