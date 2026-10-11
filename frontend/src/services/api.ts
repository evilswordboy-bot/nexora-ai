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
  ReasoningPlan,
  ToolDefinitionItem,
  ModelRegistryEntry,
  RoutingPolicyConfig,
  RoutingDecision,
  RoutingUsageSummary,
  RoutingExecuteResponse,
  RoutingTaskCategory,
  RoutingPreference,
  MemoryCategory,
  MemoryItem,
  MemoryPrivacySettings,
  MemoryStatusSummary,
  MemorySearchResponse,
  MemoryCommandResponse,
  AgentRoleId,
  SpecializedAgentSpec,
  MultiAgentOrchestrationRun,
  WorkflowDefinition,
  WorkflowExecutionRun,
  WorkflowMetadataResponse,
  WorkflowNotificationConfig,
  WorkflowNotificationItem,
  WorkflowScheduleConfig,
  WorkflowStatus,
  WorkflowStepDefinition,
  WorkflowValidationResult,
  ComputerActionStep,
  ComputerAuditLogEntry,
  ComputerCapabilitiesResponse,
  ComputerExecutionSession,
  ComputerTargetDomain,
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
    document_ids?: string[];
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
        document_ids: params.document_ids,
        stream: false,
      }),
    });
  },

  async streamChatMessage(params: {
    conversationId?: string;
    messages: Message[];
    settings: UserSettings;
    images?: string[];
    document_ids?: string[];
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
          document_ids: params.document_ids,
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

  // Stage 11: Advanced Reasoning Engine Methods
  async analyzeReasoning(
    params: {
      query: string;
      auto_execute?: boolean;
      force_plan?: boolean;
      max_retries?: number;
      context_notes?: string;
    },
    settings?: UserSettings
  ): Promise<ReasoningPlan> {
    const clientApiKey = settings ? resolveClientApiKey(settings) : undefined;
    return request<ReasoningPlan>('/reasoning/analyze', {
      method: 'POST',
      body: JSON.stringify({
        query: params.query,
        auto_execute: params.auto_execute ?? true,
        force_plan: params.force_plan ?? false,
        max_retries: params.max_retries ?? 2,
        context_notes: params.context_notes,
        provider: settings?.selectedProvider || 'auto',
        model: settings?.selectedModel || 'gemini-1.5-flash',
        client_api_key: clientApiKey,
      }),
    });
  },

  async getReasoningPlans(): Promise<ReasoningPlan[]> {
    return request<ReasoningPlan[]>('/reasoning/plans');
  },

  async getReasoningPlan(planId: string): Promise<ReasoningPlan> {
    return request<ReasoningPlan>(`/reasoning/plans/${planId}`);
  },

  async executeReasoningPlan(planId: string): Promise<ReasoningPlan> {
    return request<ReasoningPlan>(`/reasoning/plans/${planId}/execute`, {
      method: 'POST',
    });
  },

  async approveReasoningSubtask(
    planId: string,
    params: {
      subtask_id: string;
      approved: boolean;
      user_note?: string;
      auto_resume?: boolean;
    },
    settings?: UserSettings
  ): Promise<ReasoningPlan> {
    const clientApiKey = settings ? resolveClientApiKey(settings) : undefined;
    return request<ReasoningPlan>(`/reasoning/plans/${planId}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        ...params,
        auto_resume: params.auto_resume ?? true,
        provider: settings?.selectedProvider || 'auto',
        model: settings?.selectedModel || 'gemini-1.5-flash',
        client_api_key: clientApiKey,
      }),
    });
  },

  async reviseReasoningPlan(
    planId: string,
    params: {
      revised_goal?: string;
      clarification_answers?: Record<string, string>;
      updated_subtask_titles?: string[];
      auto_execute?: boolean;
    },
    settings?: UserSettings
  ): Promise<ReasoningPlan> {
    const clientApiKey = settings ? resolveClientApiKey(settings) : undefined;
    return request<ReasoningPlan>(`/reasoning/plans/${planId}/revise`, {
      method: 'POST',
      body: JSON.stringify({
        ...params,
        auto_execute: params.auto_execute ?? true,
        provider: settings?.selectedProvider || 'auto',
        model: settings?.selectedModel || 'gemini-1.5-flash',
        client_api_key: clientApiKey,
      }),
    });
  },

  async cancelReasoningPlan(planId: string): Promise<ReasoningPlan> {
    return request<ReasoningPlan>(`/reasoning/plans/${planId}/cancel`, {
      method: 'POST',
    });
  },

  async getRegisteredTools(): Promise<ToolDefinitionItem[]> {
    return request<ToolDefinitionItem[]>('/reasoning/tools');
  },

  // Stage 12: Intelligent Model Routing Engine Methods
  async getRegisteredModels(): Promise<ModelRegistryEntry[]> {
    return request<ModelRegistryEntry[]>('/routing/models');
  },

  async getRoutingPolicy(): Promise<RoutingPolicyConfig> {
    return request<RoutingPolicyConfig>('/routing/policy');
  },

  async updateRoutingPolicy(policy: RoutingPolicyConfig): Promise<RoutingPolicyConfig> {
    return request<RoutingPolicyConfig>('/routing/policy', {
      method: 'PUT',
      body: JSON.stringify(policy),
    });
  },

  async simulateRouting(params: {
    prompt: string;
    task_category?: RoutingTaskCategory;
    routing_preference?: RoutingPreference;
    preferred_provider?: string;
    preferred_model?: string;
    has_images?: boolean;
    has_documents?: boolean;
    expected_output_tokens?: number;
  }): Promise<RoutingDecision> {
    return request<RoutingDecision>('/routing/simulate', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async executeRoutedRequest(
    params: {
      prompt: string;
      task_category?: RoutingTaskCategory;
      routing_preference?: RoutingPreference;
      preferred_provider?: string;
      preferred_model?: string;
      has_images?: boolean;
      has_documents?: boolean;
      expected_output_tokens?: number;
    },
    settings?: UserSettings
  ): Promise<RoutingExecuteResponse> {
    const clientApiKey = settings ? resolveClientApiKey(settings) : undefined;
    return request<RoutingExecuteResponse>('/routing/execute', {
      method: 'POST',
      body: JSON.stringify({
        ...params,
        client_api_key: clientApiKey,
      }),
    });
  },

  async getRoutingUsageSummary(): Promise<RoutingUsageSummary> {
    return request<RoutingUsageSummary>('/routing/usage');
  },

  async resetRoutingUsageSummary(): Promise<{ cleared: boolean }> {
    return request<{ cleared: boolean }>('/routing/usage', {
      method: 'DELETE',
    });
  },

  // Stage 13: Persistent Memory Engine Methods
  async getMemoryStatus(userId = 'default_user'): Promise<MemoryStatusSummary> {
    return request<MemoryStatusSummary>(`/memory/status?user_id=${encodeURIComponent(userId)}`);
  },

  async getMemorySettings(userId = 'default_user'): Promise<MemoryPrivacySettings> {
    return request<MemoryPrivacySettings>(`/memory/settings?user_id=${encodeURIComponent(userId)}`);
  },

  async updateMemorySettings(settings: MemoryPrivacySettings): Promise<MemoryPrivacySettings> {
    return request<MemoryPrivacySettings>('/memory/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  },

  async getMemoryItems(params?: {
    userId?: string;
    category?: MemoryCategory;
    includeTemporary?: boolean;
  }): Promise<MemoryItem[]> {
    const q = new URLSearchParams();
    q.set('user_id', params?.userId || 'default_user');
    if (params?.category) q.set('category', params.category);
    if (params?.includeTemporary !== undefined) q.set('include_temporary', String(params.includeTemporary));
    return request<MemoryItem[]>(`/memory/items?${q.toString()}`);
  },

  async createMemoryItem(params: {
    user_id?: string;
    category?: MemoryCategory;
    key?: string;
    content: string;
    tags?: string[];
    pinned?: boolean;
  }): Promise<MemoryItem> {
    return request<MemoryItem>('/memory/items', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        category: params.category,
        key: params.key,
        content: params.content,
        tags: params.tags || [],
        pinned: params.pinned ?? false,
      }),
    });
  },

  async updateMemoryItem(
    memoryId: string,
    params: {
      user_id?: string;
      category?: MemoryCategory;
      key?: string;
      content?: string;
      tags?: string[];
      pinned?: boolean;
    }
  ): Promise<MemoryItem> {
    return request<MemoryItem>(`/memory/items/${encodeURIComponent(memoryId)}`, {
      method: 'PUT',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        ...params,
      }),
    });
  },

  async deleteMemoryItem(memoryId: string, userId = 'default_user'): Promise<{ deleted: boolean }> {
    return request<{ deleted: boolean }>(
      `/memory/items/${encodeURIComponent(memoryId)}?user_id=${encodeURIComponent(userId)}`,
      { method: 'DELETE' }
    );
  },

  async clearAllMemories(userId = 'default_user'): Promise<{ cleared: boolean; removed_count: number }> {
    return request<{ cleared: boolean; removed_count: number }>(
      `/memory/clear?user_id=${encodeURIComponent(userId)}`,
      { method: 'DELETE' }
    );
  },

  async searchMemories(params: {
    user_id?: string;
    query: string;
    category?: MemoryCategory;
    include_temporary?: boolean;
    top_k?: number;
  }): Promise<MemorySearchResponse> {
    return request<MemorySearchResponse>('/memory/search', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        query: params.query,
        category: params.category,
        include_temporary: params.include_temporary ?? true,
        top_k: params.top_k ?? 10,
      }),
    });
  },

  async executeMemoryCommand(params: {
    user_id?: string;
    text: string;
    confirm_ambiguous?: boolean;
    temporary_chat?: boolean;
  }): Promise<MemoryCommandResponse> {
    return request<MemoryCommandResponse>('/memory/command', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        text: params.text,
        confirm_ambiguous: params.confirm_ambiguous ?? false,
        temporary_chat: params.temporary_chat ?? false,
      }),
    });
  },

  async exportMemoryBackup(userId = 'default_user'): Promise<{ user_id: string; count: number; memories: any[] }> {
    return request<{ user_id: string; count: number; memories: any[] }>(
      `/memory/export?user_id=${encodeURIComponent(userId)}`
    );
  },

  // Stage 14: Multi-Agent Intelligence System Methods
  async getAgentRegistry(): Promise<SpecializedAgentSpec[]> {
    return request<SpecializedAgentSpec[]>('/agents/registry');
  },

  async classifyAgentsForGoal(params: {
    goal: string;
    document_ids?: string[];
    target_language?: string;
  }): Promise<AgentRoleId[]> {
    return request<AgentRoleId[]>('/agents/classify', {
      method: 'POST',
      body: JSON.stringify({
        goal: params.goal,
        document_ids: params.document_ids || [],
        target_language: params.target_language || 'en',
      }),
    });
  },

  async executeMultiAgentRun(
    params: {
      goal: string;
      user_id?: string;
      selection_mode?: 'auto' | 'manual';
      manual_agents?: AgentRoleId[];
      document_ids?: string[];
      target_language?: string;
      allow_parallel?: boolean;
      max_cost_usd?: number;
      memory_enabled?: boolean;
    },
    settings?: UserSettings
  ): Promise<MultiAgentOrchestrationRun> {
    const clientApiKey = settings ? resolveClientApiKey(settings) : undefined;
    return request<MultiAgentOrchestrationRun>('/agents/run', {
      method: 'POST',
      body: JSON.stringify({
        goal: params.goal,
        user_id: params.user_id || 'default_user',
        selection_mode: params.selection_mode || 'auto',
        manual_agents: params.manual_agents || [],
        document_ids: params.document_ids || [],
        target_language: params.target_language || 'en',
        allow_parallel: params.allow_parallel ?? true,
        max_cost_usd: params.max_cost_usd,
        memory_enabled: params.memory_enabled ?? true,
        provider: settings?.selectedProvider || 'auto',
        model: settings?.selectedModel || 'auto',
        client_api_key: clientApiKey,
      }),
    });
  },

  async getMultiAgentRuns(userId = 'default_user'): Promise<MultiAgentOrchestrationRun[]> {
    return request<MultiAgentOrchestrationRun[]>(`/agents/runs?user_id=${encodeURIComponent(userId)}`);
  },

  async approveMultiAgentSubtask(
    runId: string,
    params: {
      subtask_id: string;
      approved: boolean;
      user_note?: string;
    },
    settings?: UserSettings
  ): Promise<MultiAgentOrchestrationRun> {
    const clientApiKey = settings ? resolveClientApiKey(settings) : undefined;
    return request<MultiAgentOrchestrationRun>(`/agents/runs/${encodeURIComponent(runId)}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        ...params,
        provider: settings?.selectedProvider || 'auto',
        model: settings?.selectedModel || 'auto',
        client_api_key: clientApiKey,
      }),
    });
  },

  async retryMultiAgentRun(
    runId: string,
    subtaskId?: string,
    settings?: UserSettings
  ): Promise<MultiAgentOrchestrationRun> {
    const clientApiKey = settings ? resolveClientApiKey(settings) : undefined;
    return request<MultiAgentOrchestrationRun>(`/agents/runs/${encodeURIComponent(runId)}/retry`, {
      method: 'POST',
      body: JSON.stringify({
        subtask_id: subtaskId,
        provider: settings?.selectedProvider || 'auto',
        model: settings?.selectedModel || 'auto',
        client_api_key: clientApiKey,
      }),
    });
  },

  async cancelMultiAgentRun(runId: string): Promise<MultiAgentOrchestrationRun> {
    return request<MultiAgentOrchestrationRun>(`/agents/runs/${encodeURIComponent(runId)}/cancel`, {
      method: 'POST',
    });
  },

  // Stage 15: Workflow Automation Engine Methods
  async getWorkflowMetadata(): Promise<WorkflowMetadataResponse> {
    return request<WorkflowMetadataResponse>('/workflows/metadata');
  },

  async getWorkflowTemplates(): Promise<WorkflowDefinition[]> {
    return request<WorkflowDefinition[]>('/workflows/templates');
  },

  async getWorkflows(params?: {
    userId?: string;
    includeTemplates?: boolean;
    status?: string;
  }): Promise<WorkflowDefinition[]> {
    const q = new URLSearchParams();
    q.set('user_id', params?.userId || 'default_user');
    if (params?.includeTemplates !== undefined) q.set('include_templates', String(params.includeTemplates));
    if (params?.status) q.set('status', params.status);
    return request<WorkflowDefinition[]>(`/workflows?${q.toString()}`);
  },

  async validateWorkflow(params: {
    steps: WorkflowStepDefinition[];
    schedule?: WorkflowScheduleConfig;
    max_cost_budget_usd?: number;
  }): Promise<WorkflowValidationResult> {
    return request<WorkflowValidationResult>('/workflows/validate', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async createWorkflow(params: {
    user_id?: string;
    name: string;
    description: string;
    category?: string;
    status?: WorkflowStatus;
    schedule: WorkflowScheduleConfig;
    steps: WorkflowStepDefinition[];
    notification_config?: WorkflowNotificationConfig;
    max_cost_budget_usd?: number;
  }): Promise<WorkflowDefinition> {
    return request<WorkflowDefinition>('/workflows', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        name: params.name,
        description: params.description,
        category: params.category || 'general',
        status: params.status || 'DRAFT',
        schedule: params.schedule,
        steps: params.steps,
        notification_config: params.notification_config,
        max_cost_budget_usd: params.max_cost_budget_usd ?? 0.5,
      }),
    });
  },

  async updateWorkflow(
    workflowId: string,
    params: {
      name?: string;
      description?: string;
      category?: string;
      status?: WorkflowStatus;
      schedule?: WorkflowScheduleConfig;
      steps?: WorkflowStepDefinition[];
      notification_config?: WorkflowNotificationConfig;
      max_cost_budget_usd?: number;
    }
  ): Promise<WorkflowDefinition> {
    return request<WorkflowDefinition>(`/workflows/${encodeURIComponent(workflowId)}`, {
      method: 'PUT',
      body: JSON.stringify(params),
    });
  },

  async setWorkflowStatus(workflowId: string, status: WorkflowStatus): Promise<WorkflowDefinition> {
    return request<WorkflowDefinition>(`/workflows/${encodeURIComponent(workflowId)}/status`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    });
  },

  async duplicateWorkflow(workflowId: string, userId = 'default_user'): Promise<WorkflowDefinition> {
    return request<WorkflowDefinition>(
      `/workflows/${encodeURIComponent(workflowId)}/duplicate?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' }
    );
  },

  async deleteWorkflow(workflowId: string): Promise<{ workflow_id: string; deleted: boolean }> {
    return request<{ workflow_id: string; deleted: boolean }>(
      `/workflows/${encodeURIComponent(workflowId)}`,
      { method: 'DELETE' }
    );
  },

  async triggerWorkflowRun(
    workflowId: string,
    params?: {
      user_id?: string;
      trigger_source?: 'manual' | 'scheduled' | 'test_dry_run';
      is_dry_run?: boolean;
      runtime_inputs?: Record<string, any>;
    },
    settings?: UserSettings
  ): Promise<WorkflowExecutionRun> {
    const clientApiKey = settings ? resolveClientApiKey(settings) : undefined;
    return request<WorkflowExecutionRun>(`/workflows/${encodeURIComponent(workflowId)}/run`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: params?.user_id || 'default_user',
        trigger_source: params?.trigger_source || 'manual',
        is_dry_run: params?.is_dry_run ?? false,
        runtime_inputs: params?.runtime_inputs || {},
        provider: settings?.selectedProvider || 'auto',
        model: settings?.selectedModel || 'auto',
        client_api_key: clientApiKey,
      }),
    });
  },

  async getWorkflowRuns(params?: {
    userId?: string;
    workflowId?: string;
    status?: string;
  }): Promise<WorkflowExecutionRun[]> {
    const q = new URLSearchParams();
    q.set('user_id', params?.userId || 'default_user');
    if (params?.workflowId) q.set('workflow_id', params.workflowId);
    if (params?.status) q.set('status', params.status);
    return request<WorkflowExecutionRun[]>(`/workflows/runs?${q.toString()}`);
  },

  async approveWorkflowStep(
    runId: string,
    params: {
      step_id: string;
      approved: boolean;
      user_note?: string;
    },
    settings?: UserSettings
  ): Promise<WorkflowExecutionRun> {
    const clientApiKey = settings ? resolveClientApiKey(settings) : undefined;
    return request<WorkflowExecutionRun>(`/workflows/runs/${encodeURIComponent(runId)}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        ...params,
        provider: settings?.selectedProvider || 'auto',
        model: settings?.selectedModel || 'auto',
        client_api_key: clientApiKey,
      }),
    });
  },

  async retryWorkflowRun(
    runId: string,
    fromFailedStepOnly = true,
    settings?: UserSettings
  ): Promise<WorkflowExecutionRun> {
    const clientApiKey = settings ? resolveClientApiKey(settings) : undefined;
    return request<WorkflowExecutionRun>(`/workflows/runs/${encodeURIComponent(runId)}/retry`, {
      method: 'POST',
      body: JSON.stringify({
        from_failed_step_only: fromFailedStepOnly,
        provider: settings?.selectedProvider || 'auto',
        model: settings?.selectedModel || 'auto',
        client_api_key: clientApiKey,
      }),
    });
  },

  async cancelWorkflowRun(runId: string): Promise<WorkflowExecutionRun> {
    return request<WorkflowExecutionRun>(`/workflows/runs/${encodeURIComponent(runId)}/cancel`, {
      method: 'POST',
    });
  },

  async tickWorkflowScheduler(): Promise<WorkflowExecutionRun[]> {
    return request<WorkflowExecutionRun[]>('/workflows/scheduler/tick', {
      method: 'POST',
    });
  },

  async getWorkflowNotifications(unreadOnly = false): Promise<WorkflowNotificationItem[]> {
    return request<WorkflowNotificationItem[]>(`/workflows/notifications?unread_only=${unreadOnly}`);
  },

  async markWorkflowNotificationRead(notificationId: string): Promise<{ notification_id: string; read: boolean }> {
    return request<{ notification_id: string; read: boolean }>(
      `/workflows/notifications/${encodeURIComponent(notificationId)}/read`,
      { method: 'POST' }
    );
  },

  async markAllWorkflowNotificationsRead(): Promise<{ marked_read_count: number }> {
    return request<{ marked_read_count: number }>('/workflows/notifications/read-all', {
      method: 'POST',
    });
  },

  // Stage 16: Computer Control & Digital Execution Engine Methods
  async getComputerCapabilities(): Promise<ComputerCapabilitiesResponse> {
    return request<ComputerCapabilitiesResponse>('/computer/capabilities');
  },

  async createComputerSession(params: {
    user_id?: string;
    goal: string;
    mode?: 'execute' | 'simulate_only';
    target_domain?: ComputerTargetDomain;
    target_url?: string;
    steps?: ComputerActionStep[];
    custom_allowed_domains?: string[];
    auto_start?: boolean;
  }): Promise<ComputerExecutionSession> {
    return request<ComputerExecutionSession>('/computer/sessions', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        goal: params.goal,
        mode: params.mode || 'execute',
        target_domain: params.target_domain || 'browser',
        target_url: params.target_url,
        steps: params.steps || [],
        custom_allowed_domains: params.custom_allowed_domains || [],
        auto_start: params.auto_start ?? true,
      }),
    });
  },

  async getComputerSessions(userId = 'default_user'): Promise<ComputerExecutionSession[]> {
    return request<ComputerExecutionSession[]>(
      `/computer/sessions?user_id=${encodeURIComponent(userId)}`
    );
  },

  async getComputerSession(sessionId: string): Promise<ComputerExecutionSession> {
    return request<ComputerExecutionSession>(`/computer/sessions/${encodeURIComponent(sessionId)}`);
  },

  async startComputerSession(sessionId: string): Promise<ComputerExecutionSession> {
    return request<ComputerExecutionSession>(
      `/computer/sessions/${encodeURIComponent(sessionId)}/start`,
      { method: 'POST' }
    );
  },

  async approveComputerStep(
    sessionId: string,
    params: {
      step_id: string;
      approved: boolean;
      user_note?: string;
    }
  ): Promise<ComputerExecutionSession> {
    return request<ComputerExecutionSession>(
      `/computer/sessions/${encodeURIComponent(sessionId)}/approve`,
      {
        method: 'POST',
        body: JSON.stringify(params),
      }
    );
  },

  async pauseComputerSession(sessionId: string): Promise<ComputerExecutionSession> {
    return request<ComputerExecutionSession>(
      `/computer/sessions/${encodeURIComponent(sessionId)}/pause`,
      { method: 'POST' }
    );
  },

  async cancelComputerSession(sessionId: string): Promise<ComputerExecutionSession> {
    return request<ComputerExecutionSession>(
      `/computer/sessions/${encodeURIComponent(sessionId)}/cancel`,
      { method: 'POST' }
    );
  },

  async retryComputerSession(sessionId: string): Promise<ComputerExecutionSession> {
    return request<ComputerExecutionSession>(
      `/computer/sessions/${encodeURIComponent(sessionId)}/retry`,
      { method: 'POST' }
    );
  },

  async getComputerAuditLogs(sessionId?: string): Promise<ComputerAuditLogEntry[]> {
    const q = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
    return request<ComputerAuditLogEntry[]>(`/computer/audit-logs${q}`);
  },
};

