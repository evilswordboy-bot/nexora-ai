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
  DuplicateFileGroup,
  FileCategory,
  FileOperationRecord,
  FileWorkspaceCapabilitiesResponse,
  OrganizeRuleStrategy,
  WorkspaceFileItem,
  WorkspaceFileReadResponse,
  WorkspaceFileVersion,
  WorkspaceTrashItem,
  CodeFileBackup,
  CodeInspectionResult,
  CodeProjectFile,
  CodeProjectSummary,
  CommandPreview,
  DebugRepairResponse,
  ProjectTemplateType,
  TerminalCapabilitiesResponse,
  TerminalExecutionRecord,
  GitBranchComparisonResponse,
  GitCapabilitiesResponse,
  GitCodeReviewResponse,
  GitCommitEntry,
  GitDiffResponse,
  GitOperationRecord,
  GitPullRequestRecord,
  GitRemoteProvider,
  GitRepositoryStatusResponse,
  EvalAcceptanceThresholds,
  EvalCaseReviewStatus,
  EvalCaseSourceType,
  EvalMetadataResponse,
  EvalRegressionAlert,
  EvalReleaseGateVerdict,
  EvalRunRecord,
  EvalSuiteId,
  EvalTestCase,
  DiscoveryMetadataResponse,
  DiscoverySearchMode,
  DiscoverySearchResponse,
  DiscoverySourceType,
  KGChangeLogEntry,
  KGDestructiveOperationRecord,
  KGDuplicateCandidate,
  KGEntityType,
  KGFactBasis,
  KGGraphSnapshotResponse,
  KGIngestResponse,
  KGMetadataResponse,
  KGQueryMode,
  KGQueryResponse,
  KGRelationType,
  IoTBoardId,
  IoTBoardProfile,
  IoTComponentSpec,
  IoTConnectivityProtocol,
  IoTEnvironmentType,
  IoTFirmwareLanguage,
  IoTMetadataResponse,
  IoTPlacedComponent,
  IoTPowerSource,
  IoTProjectExportResponse,
  IoTProjectRecord,
  IoTSimulationResponse,
  IoTSimulationStimulus,
  IoTWireConnection,
  FirmwareBuildSettings,
  FirmwareCodeSearchHit,
  FirmwareCompileResult,
  FirmwareDeviceActionRecord,
  FirmwareExportResponse,
  FirmwareFrameworkId,
  FirmwareMetadataResponse,
  FirmwarePlatformMatrixEntry,
  FirmwareSerialMonitorResponse,
  FirmwareWorkspaceRecord,
  IoTDeviceRecord,
  IoTDeviceTokenResponse,
  TelemetryEventRecord,
  AlertRuleRecord,
  AlertRecord,
  DeviceCommandRecord,
  TelemetryDeviceStatsResponse,
  TelemetryExportResponse,
  TelemetryMetadataResponse,
  DeviceSecurityPosture,
  ConfigurationAuditFinding,
  BehavioralAnomalyRecord,
  SecurityIncidentRecord,
  DefensiveActionRecord,
  FirmwareIntegritySpec,
  IoTSecurityOverviewResponse,
  DefensiveActionType,
  IncidentStatus,
  SchematicPin,
  SchematicComponentDef,
  ComponentInstance,
  SchematicNet,
  SchematicSheet,
  SchematicProject,
  ERCFinding,
  ERCReport,
  OhmsLawResult,
  VoltageDividerResult,
  LEDResistorResult,
  RCTimeConstantResult,
  TransistorBiasResult,
  PowerThermalResult,
  LogicExpressionResult,
  SPICESimulationResult,
  AICircuitDesignResponse,
  SchematicExportResponse,
  SchematicOverviewResponse,
  PCBPadDef,
  PCBFootprintDef,
  PCBComponent,
  PCBTrack,
  PCBVia,
  PCBZone,
  PCBNetPadConnection,
  PCBNet,
  PCBRatsnestLine,
  PCBDesignRules,
  PCBBoard,
  PCBProject,
  SchematicToPCBRequest,
  SchematicToPCBResponse,
  PCBDrcFinding,
  PCBDrcReport,
  TraceWidthRequest,
  TraceWidthResult,
  ImpedanceRequest,
  ImpedanceResult,
  PCBBOMItem,
  PCBCostEstimateRequest,
  PCBCostEstimateResult,
  PCBExportRequest,
  PCBExportResponse,
  PCBOverviewResponse,

  TravelCategory,
  TravelProductItem,
  TravelSearchQuery,
  TravelHoldRequest,
  TravelHoldResponse,
  TravelBookingRequest,
  TravelBookingRecord,
  TravelCancellationRequest,
  TravelRescheduleRequest,
  TravelAuditRecord,
  TravelOverviewResponse,
} from '../types';
import { handleClientStandaloneRequest, generateContextualEdgeResponse } from './standaloneSimulation';

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
      // If endpoint is missing or running on static hosting (e.g. GitHub Pages 404), use client standalone simulation
      if (res.status === 404 || res.status === 405 || res.status === 502) {
        const simulated = handleClientStandaloneRequest<T>(endpoint, options);
        if (simulated !== undefined) {
          return simulated;
        }
      }

      let errorMsg = `Server error (${res.status})`;
      let detail = null;
      try {
        const text = await res.text();
        if (text) {
          try {
            const errJson = JSON.parse(text);
            detail = errJson;
            errorMsg = errJson.detail || errJson.message || text;
          } catch {
            errorMsg = text;
          }
        }
      } catch {
        // Safe ignore
      }
      throw new ApiError(res.status, errorMsg, detail);
    }
    if (res.status === 204) {
      return null as unknown as T;
    }
    return await res.json();
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    // On offline / network error / static CORS failure, fall back to standalone simulation
    const simulated = handleClientStandaloneRequest<T>(endpoint, options);
    if (simulated !== undefined) {
      return simulated;
    }
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

async function handleCloudStandaloneChat(
  params: {
    messages: Message[];
    settings: UserSettings;
    onStart?: (info: { id: string; model: string; provider: string }) => void;
    onChunk: (chunk: string) => void;
    onDone?: (info: { id: string; finish_reason?: string }) => void;
    onError?: (errorMsg: string) => void;
  },
  _clientApiKey: string
): Promise<void> {
  const msgId = `cloud_${Date.now()}`;
  const lastUserMsg =
    [...params.messages].reverse().find((m) => m.role === 'user')?.content || '';

  // 1. Direct Browser-to-Gemini execution if user provided a Gemini API key in Settings
  if (params.settings.geminiApiKey) {
    try {
      const model = params.settings.selectedModel.startsWith('gemini')
        ? params.settings.selectedModel
        : 'gemini-1.5-flash';
      params.onStart?.({ id: msgId, model, provider: 'gemini-cloud-direct' });
      const gemRes = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(
          params.settings.geminiApiKey
        )}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: params.messages.map((m) => ({
              role: m.role === 'assistant' ? 'model' : 'user',
              parts: [{ text: m.content }],
            })),
          }),
        }
      );
      if (gemRes.ok) {
        const gemJson = await gemRes.json();
        const text =
          gemJson?.candidates?.[0]?.content?.parts?.[0]?.text ||
          'No response returned from Gemini API.';
        params.onChunk(text);
        params.onDone?.({ id: msgId, finish_reason: 'stop' });
        return;
      }
    } catch {
      // Fall through to interactive Cloud Edge response
    }
  }

  // 2. Direct Browser-to-OpenAI execution if user provided an OpenAI API key in Settings
  if (params.settings.openaiApiKey) {
    try {
      params.onStart?.({ id: msgId, model: 'gpt-4o-mini', provider: 'openai-cloud-direct' });
      const oaiRes = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${params.settings.openaiApiKey}`,
        },
        body: JSON.stringify({
          model: 'gpt-4o-mini',
          messages: params.messages.map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });
      if (oaiRes.ok) {
        const oaiJson = await oaiRes.json();
        const text =
          oaiJson?.choices?.[0]?.message?.content || 'No response returned from OpenAI API.';
        params.onChunk(text);
        params.onDone?.({ id: msgId, finish_reason: 'stop' });
        return;
      }
    } catch {
      // Fall through to edge synthesis
    }
  }

  // 3. Autonomous Contextual Edge AI Engine (Always available 24/7 on GitHub Pages without keys)
  params.onStart?.({
    id: msgId,
    model: params.settings.selectedModel || 'nexora-edge-v29',
    provider: 'nexora-edge',
  });

  const reply = generateContextualEdgeResponse(lastUserMsg, params.messages);

  const words = reply.split(' ');
  for (let i = 0; i < words.length; i += 3) {
    params.onChunk(words.slice(i, i + 3).join(' ') + ' ');
    await new Promise((r) => setTimeout(r, 14));
  }
  params.onDone?.({ id: msgId, finish_reason: 'stop' });
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
        if (response.status === 404 || response.status === 405 || response.status === 502) {
          await handleCloudStandaloneChat(params, clientApiKey);
          return;
        }
        let errorMsg = `Server error (${response.status})`;
        try {
          const text = await response.text();
          if (text) {
            try {
              const errData = JSON.parse(text);
              errorMsg = errData.detail || errData.message || text;
            } catch {
              errorMsg = text;
            }
          }
        } catch {
          // Stream read safeguard
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
      await handleCloudStandaloneChat(params, clientApiKey);
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
    try {
      const res = await fetch(`${BASE_URL}/documents/upload`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        let errDetail = 'Failed to upload document';
        try {
          const t = await res.text();
          if (t) {
            try {
              const errJson = JSON.parse(t);
              errDetail = errJson.detail || errJson.message || t;
            } catch {
              errDetail = t;
            }
          }
        } catch {}
        throw new ApiError(res.status, errDetail);
      }
      return await res.json();
    } catch (err: any) {
      if (err instanceof ApiError) throw err;
      // Client standalone fallback for GitHub Pages
      return {
        id: `doc_${Date.now()}`,
        filename: file.name,
        original_filename: file.name,
        file_type: file.type || 'text/plain',
        size_bytes: file.size,
        status: 'ready',
        total_chunks: 3,
        created_at: new Date().toISOString(),
        metadata: {
          summary: `Document ${file.name} uploaded and indexed successfully in Standalone Edge Mode.`,
        },
      };
    }
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

  // Stage 17: File Management & Workspace Automation Engine Methods
  async getFileWorkspaceCapabilities(userId = 'default_user'): Promise<FileWorkspaceCapabilitiesResponse> {
    return request<FileWorkspaceCapabilitiesResponse>(
      `/files/capabilities?user_id=${encodeURIComponent(userId)}`
    );
  },

  async listWorkspaceFiles(params?: {
    userId?: string;
    directory?: string;
    recursive?: boolean;
  }): Promise<WorkspaceFileItem[]> {
    const q = new URLSearchParams();
    q.set('user_id', params?.userId || 'default_user');
    if (params?.directory) q.set('directory', params.directory);
    if (params?.recursive !== undefined) q.set('recursive', String(params.recursive));
    return request<WorkspaceFileItem[]>(`/files/list?${q.toString()}`);
  },

  async searchWorkspaceFiles(params: {
    user_id?: string;
    query: string;
    directory?: string;
    extensions?: string[];
    category?: FileCategory;
    search_content?: boolean;
    include_stage4_indexed?: boolean;
    min_size_bytes?: number;
    max_size_bytes?: number;
  }): Promise<{
    query: string;
    total_matches: number;
    items: WorkspaceFileItem[];
    stage4_indexed_matches: {
      doc_id: string;
      filename: string;
      page_number: number;
      score: number;
      snippet: string;
    }[];
  }> {
    return request('/files/search', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        query: params.query,
        directory: params.directory || '',
        extensions: params.extensions || [],
        category: params.category,
        search_content: params.search_content ?? true,
        include_stage4_indexed: params.include_stage4_indexed ?? true,
        min_size_bytes: params.min_size_bytes,
        max_size_bytes: params.max_size_bytes,
      }),
    });
  },

  async readWorkspaceFile(path: string, userId = 'default_user'): Promise<WorkspaceFileReadResponse> {
    return request<WorkspaceFileReadResponse>(
      `/files/read?path=${encodeURIComponent(path)}&user_id=${encodeURIComponent(userId)}`
    );
  },

  async createWorkspaceFolder(relativePath: string, userId = 'default_user'): Promise<FileOperationRecord> {
    return request<FileOperationRecord>('/files/folders', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        relative_path: relativePath,
      }),
    });
  },

  async writeWorkspaceFile(params: {
    user_id?: string;
    relative_path: string;
    content: string;
    overwrite?: boolean;
    confirmed_overwrite?: boolean;
    backup_reason?: string;
  }): Promise<FileOperationRecord> {
    return request<FileOperationRecord>('/files/write', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        relative_path: params.relative_path,
        content: params.content,
        overwrite: params.overwrite ?? false,
        confirmed_overwrite: params.confirmed_overwrite ?? false,
        backup_reason: params.backup_reason || 'edit_preserve_original',
      }),
    });
  },

  async transferWorkspaceItem(params: {
    user_id?: string;
    action: 'rename' | 'copy' | 'move';
    source_path: string;
    destination_path: string;
    overwrite?: boolean;
    confirmed_overwrite?: boolean;
  }): Promise<FileOperationRecord> {
    return request<FileOperationRecord>('/files/transfer', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        action: params.action,
        source_path: params.source_path,
        destination_path: params.destination_path,
        overwrite: params.overwrite ?? false,
        confirmed_overwrite: params.confirmed_overwrite ?? false,
      }),
    });
  },

  async convertWorkspaceFile(params: {
    user_id?: string;
    source_path: string;
    target_format: 'txt' | 'md' | 'csv' | 'json' | 'docx' | 'xlsx';
    destination_path?: string;
    overwrite?: boolean;
    confirmed_overwrite?: boolean;
  }): Promise<FileOperationRecord> {
    return request<FileOperationRecord>('/files/convert', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        source_path: params.source_path,
        target_format: params.target_format,
        destination_path: params.destination_path,
        overwrite: params.overwrite ?? true,
        confirmed_overwrite: params.confirmed_overwrite ?? true,
      }),
    });
  },

  async findWorkspaceDuplicates(userId = 'default_user', directory = ''): Promise<DuplicateFileGroup[]> {
    return request<DuplicateFileGroup[]>(
      `/files/duplicates?user_id=${encodeURIComponent(userId)}&directory=${encodeURIComponent(directory)}`
    );
  },

  async cleanupWorkspaceDuplicates(params: {
    user_id?: string;
    directory?: string;
    preview_only?: boolean;
    confirmed?: boolean;
  }): Promise<FileOperationRecord> {
    return request<FileOperationRecord>('/files/duplicates/cleanup', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        directory: params.directory || '',
        preview_only: params.preview_only ?? false,
        confirmed: params.confirmed ?? false,
      }),
    });
  },

  async organizeWorkspaceFiles(params: {
    user_id?: string;
    directory?: string;
    strategy: OrganizeRuleStrategy;
    custom_extension_map?: Record<string, string>;
    preview_only?: boolean;
    confirmed?: boolean;
  }): Promise<FileOperationRecord> {
    return request<FileOperationRecord>('/files/organize', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        directory: params.directory || '',
        strategy: params.strategy,
        custom_extension_map: params.custom_extension_map || {},
        preview_only: params.preview_only ?? false,
        confirmed: params.confirmed ?? false,
      }),
    });
  },

  async deleteWorkspaceItemsToTrash(params: {
    user_id?: string;
    paths: string[];
    reason?: string;
    preview_only?: boolean;
    confirmed?: boolean;
  }): Promise<FileOperationRecord> {
    return request<FileOperationRecord>('/files/delete', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        paths: params.paths,
        reason: params.reason || 'user_requested_cleanup',
        preview_only: params.preview_only ?? false,
        confirmed: params.confirmed ?? false,
      }),
    });
  },

  async listWorkspaceTrash(userId = 'default_user'): Promise<WorkspaceTrashItem[]> {
    return request<WorkspaceTrashItem[]>(`/files/trash?user_id=${encodeURIComponent(userId)}`);
  },

  async restoreWorkspaceTrashItem(trashId: string, userId = 'default_user'): Promise<FileOperationRecord> {
    return request<FileOperationRecord>(
      `/files/trash/${encodeURIComponent(trashId)}/restore?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' }
    );
  },

  async listWorkspaceFileVersions(path: string, userId = 'default_user'): Promise<WorkspaceFileVersion[]> {
    return request<WorkspaceFileVersion[]>(
      `/files/versions?path=${encodeURIComponent(path)}&user_id=${encodeURIComponent(userId)}`
    );
  },

  async restoreWorkspaceFileVersion(
    versionId: string,
    relativePath: string,
    userId = 'default_user'
  ): Promise<FileOperationRecord> {
    return request<FileOperationRecord>(
      `/files/versions/${encodeURIComponent(versionId)}/restore`,
      {
        method: 'POST',
        body: JSON.stringify({
          user_id: userId,
          relative_path: relativePath,
        }),
      }
    );
  },

  async listFileOperations(userId = 'default_user', limit = 50): Promise<FileOperationRecord[]> {
    return request<FileOperationRecord[]>(
      `/files/operations?user_id=${encodeURIComponent(userId)}&limit=${limit}`
    );
  },

  async approveFileOperation(
    operationId: string,
    params: {
      user_id?: string;
      approved: boolean;
      user_note?: string;
    }
  ): Promise<FileOperationRecord> {
    return request<FileOperationRecord>(
      `/files/operations/${encodeURIComponent(operationId)}/approve`,
      {
        method: 'POST',
        body: JSON.stringify({
          user_id: params.user_id || 'default_user',
          approved: params.approved,
          user_note: params.user_note,
        }),
      }
    );
  },

  async rollbackFileOperation(operationId: string, userId = 'default_user'): Promise<FileOperationRecord> {
    return request<FileOperationRecord>(
      `/files/operations/${encodeURIComponent(operationId)}/rollback?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' }
    );
  },

  async syncWorkspaceFileToStage4(relativePath: string, userId = 'default_user'): Promise<FileOperationRecord> {
    return request<FileOperationRecord>('/files/sync-stage4', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        relative_path: relativePath,
      }),
    });
  },

  async importStage16BrowserSessionToFile(params: {
    user_id?: string;
    session_id: string;
    target_filename: string;
  }): Promise<FileOperationRecord> {
    return request<FileOperationRecord>('/files/import-browser-session', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        session_id: params.session_id,
        target_filename: params.target_filename,
        overwrite: true,
        confirmed_overwrite: true,
      }),
    });
  },

  // =========================================================================
  // Stage 18: Terminal & Code Execution Engine
  // =========================================================================

  async getTerminalCapabilities(userId = 'default_user'): Promise<TerminalCapabilitiesResponse> {
    return request<TerminalCapabilitiesResponse>(
      `/terminal/capabilities?user_id=${encodeURIComponent(userId)}`
    );
  },

  async listCodeProjects(userId = 'default_user'): Promise<CodeProjectSummary[]> {
    return request<CodeProjectSummary[]>(
      `/terminal/projects?user_id=${encodeURIComponent(userId)}`
    );
  },

  async createCodeProject(params: {
    user_id?: string;
    name: string;
    description?: string;
    template: ProjectTemplateType;
  }): Promise<CodeProjectSummary> {
    return request<CodeProjectSummary>('/terminal/projects', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        name: params.name,
        description: params.description || '',
        template: params.template,
      }),
    });
  },

  async getCodeProject(projectId: string, userId = 'default_user'): Promise<CodeProjectSummary> {
    return request<CodeProjectSummary>(
      `/terminal/projects/${encodeURIComponent(projectId)}?user_id=${encodeURIComponent(userId)}`
    );
  },

  async resetCodeProject(projectId: string, userId = 'default_user'): Promise<CodeProjectSummary> {
    return request<CodeProjectSummary>(
      `/terminal/projects/${encodeURIComponent(projectId)}/reset?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' }
    );
  },

  async saveCodeProjectFile(
    projectId: string,
    params: {
      user_id?: string;
      relative_path: string;
      content: string;
      create_backup?: boolean;
      backup_reason?: string;
    }
  ): Promise<{ file: CodeProjectFile; backup: CodeFileBackup | null }> {
    return request<{ file: CodeProjectFile; backup: CodeFileBackup | null }>(
      `/terminal/projects/${encodeURIComponent(projectId)}/files`,
      {
        method: 'POST',
        body: JSON.stringify({
          user_id: params.user_id || 'default_user',
          relative_path: params.relative_path,
          content: params.content,
          create_backup: params.create_backup ?? true,
          backup_reason: params.backup_reason || 'editor_save',
        }),
      }
    );
  },

  async listCodeProjectBackups(
    projectId: string,
    userId = 'default_user',
    relativePath?: string
  ): Promise<CodeFileBackup[]> {
    const query = new URLSearchParams({ user_id: userId });
    if (relativePath) query.set('relative_path', relativePath);
    return request<CodeFileBackup[]>(
      `/terminal/projects/${encodeURIComponent(projectId)}/backups?${query.toString()}`
    );
  },

  async restoreCodeProjectBackup(
    projectId: string,
    backupId: string,
    userId = 'default_user'
  ): Promise<CodeProjectFile> {
    return request<CodeProjectFile>(
      `/terminal/projects/${encodeURIComponent(projectId)}/backups/${encodeURIComponent(backupId)}/restore?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' }
    );
  },

  async inspectProjectCode(params: {
    user_id?: string;
    project_id: string;
    relative_path: string;
    content?: string;
    apply_formatting?: boolean;
  }): Promise<CodeInspectionResult> {
    return request<CodeInspectionResult>('/terminal/inspect', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        project_id: params.project_id,
        relative_path: params.relative_path,
        content: params.content,
        apply_formatting: params.apply_formatting ?? false,
      }),
    });
  },

  async executeProjectCode(params: {
    user_id?: string;
    project_id: string;
    target_file?: string;
    mode: 'run' | 'test';
    args?: string[];
    stdin_text?: string;
    timeout_seconds?: number;
    allow_network?: boolean;
    confirmed_network?: boolean;
  }): Promise<TerminalExecutionRecord> {
    return request<TerminalExecutionRecord>('/terminal/execute', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        project_id: params.project_id,
        target_file: params.target_file,
        mode: params.mode,
        args: params.args || [],
        stdin_text: params.stdin_text || '',
        timeout_seconds: params.timeout_seconds,
        allow_network: params.allow_network ?? false,
        confirmed_network: params.confirmed_network ?? false,
      }),
    });
  },

  async classifyTerminalCommand(params: {
    user_id?: string;
    project_id: string;
    command: string;
    allow_network?: boolean;
  }): Promise<CommandPreview> {
    return request<CommandPreview>('/terminal/command/classify', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        project_id: params.project_id,
        command: params.command,
        allow_network: params.allow_network ?? false,
      }),
    });
  },

  async runTerminalCommand(params: {
    user_id?: string;
    project_id: string;
    command: string;
    timeout_seconds?: number;
    allow_network?: boolean;
    confirmed?: boolean;
    preview_only?: boolean;
  }): Promise<TerminalExecutionRecord> {
    return request<TerminalExecutionRecord>('/terminal/command', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        project_id: params.project_id,
        command: params.command,
        timeout_seconds: params.timeout_seconds,
        allow_network: params.allow_network ?? false,
        confirmed: params.confirmed ?? false,
        preview_only: params.preview_only ?? false,
      }),
    });
  },

  async listTerminalExecutions(
    userId = 'default_user',
    projectId?: string,
    limit = 30
  ): Promise<TerminalExecutionRecord[]> {
    const query = new URLSearchParams({ user_id: userId, limit: String(limit) });
    if (projectId) query.set('project_id', projectId);
    return request<TerminalExecutionRecord[]>(`/terminal/executions?${query.toString()}`);
  },

  async approveTerminalExecution(
    executionId: string,
    params: {
      user_id?: string;
      approved: boolean;
      user_note?: string;
    }
  ): Promise<TerminalExecutionRecord> {
    return request<TerminalExecutionRecord>(
      `/terminal/executions/${encodeURIComponent(executionId)}/approve`,
      {
        method: 'POST',
        body: JSON.stringify({
          user_id: params.user_id || 'default_user',
          approved: params.approved,
          user_note: params.user_note,
        }),
      }
    );
  },

  async stopTerminalExecution(
    executionId: string,
    userId = 'default_user'
  ): Promise<{ execution_id: string; stopped: boolean; message: string }> {
    return request<{ execution_id: string; stopped: boolean; message: string }>(
      `/terminal/executions/${encodeURIComponent(executionId)}/stop?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' }
    );
  },

  async debugAndRepairCode(params: {
    user_id?: string;
    project_id: string;
    target_file: string;
    run_tests?: boolean;
    max_attempts?: number;
    auto_apply?: boolean;
  }): Promise<DebugRepairResponse> {
    return request<DebugRepairResponse>('/terminal/debug-repair', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        project_id: params.project_id,
        target_file: params.target_file,
        run_tests: params.run_tests ?? true,
        max_attempts: params.max_attempts ?? 3,
        auto_apply: params.auto_apply ?? true,
      }),
    });
  },

  async syncCodeProjectWithStage17(
    projectId: string,
    params: {
      user_id?: string;
      direction: 'to_stage17' | 'from_stage17';
      relative_path?: string;
    }
  ): Promise<{
    project_id: string;
    direction: string;
    synced_count: number;
    synced_files: string[];
    summary: string;
  }> {
    return request(`/terminal/projects/${encodeURIComponent(projectId)}/sync-stage17`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        direction: params.direction,
        relative_path: params.relative_path,
      }),
    });
  },

  // =========================================================================
  // Stage 19: Git & Version Control Engine
  // =========================================================================

  async getGitCapabilities(userId = 'default_user'): Promise<GitCapabilitiesResponse> {
    return request<GitCapabilitiesResponse>(
      `/git/capabilities?user_id=${encodeURIComponent(userId)}`
    );
  },

  async getGitRepositoryStatus(
    projectId = 'proj_default_py',
    userId = 'default_user'
  ): Promise<GitRepositoryStatusResponse> {
    return request<GitRepositoryStatusResponse>(
      `/git/status?project_id=${encodeURIComponent(projectId)}&user_id=${encodeURIComponent(userId)}`
    );
  },

  async initGitRepository(params: {
    user_id?: string;
    project_id: string;
    default_branch?: string;
    author_name?: string;
    author_email?: string;
    create_gitignore?: boolean;
    initial_commit?: boolean;
  }): Promise<GitOperationRecord> {
    return request<GitOperationRecord>('/git/init', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        project_id: params.project_id,
        default_branch: params.default_branch || 'main',
        author_name: params.author_name,
        author_email: params.author_email,
        create_gitignore: params.create_gitignore ?? true,
        initial_commit: params.initial_commit ?? true,
      }),
    });
  },

  async stageGitFiles(params: {
    user_id?: string;
    project_id: string;
    paths?: string[];
    stage_all?: boolean;
    allow_sensitive?: boolean;
  }): Promise<GitOperationRecord> {
    return request<GitOperationRecord>('/git/stage', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        project_id: params.project_id,
        paths: params.paths || [],
        stage_all: params.stage_all ?? false,
        allow_sensitive: params.allow_sensitive ?? false,
      }),
    });
  },

  async unstageGitFiles(params: {
    user_id?: string;
    project_id: string;
    paths?: string[];
    stage_all?: boolean;
  }): Promise<GitOperationRecord> {
    return request<GitOperationRecord>('/git/unstage', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        project_id: params.project_id,
        paths: params.paths || [],
        stage_all: params.stage_all ?? false,
      }),
    });
  },

  async getGitDiff(params: {
    user_id?: string;
    project_id: string;
    scope?: 'unstaged' | 'staged' | 'all_working' | 'branch_compare' | 'commit';
    file_path?: string;
    base_ref?: string;
    compare_ref?: string;
  }): Promise<GitDiffResponse> {
    const q = new URLSearchParams({
      user_id: params.user_id || 'default_user',
      project_id: params.project_id,
      scope: params.scope || 'all_working',
    });
    if (params.file_path) q.set('file_path', params.file_path);
    if (params.base_ref) q.set('base_ref', params.base_ref);
    if (params.compare_ref) q.set('compare_ref', params.compare_ref);
    return request<GitDiffResponse>(`/git/diff?${q.toString()}`);
  },

  async commitGitChanges(params: {
    user_id?: string;
    project_id: string;
    message: string;
    description?: string;
    stage_all?: boolean;
    confirmed?: boolean;
    allow_secret_override?: boolean;
  }): Promise<GitOperationRecord> {
    return request<GitOperationRecord>('/git/commit', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        project_id: params.project_id,
        message: params.message,
        description: params.description || '',
        stage_all: params.stage_all ?? false,
        confirmed: params.confirmed ?? false,
        allow_secret_override: params.allow_secret_override ?? false,
      }),
    });
  },

  async listGitCommits(
    projectId: string,
    userId = 'default_user',
    limit = 25
  ): Promise<{ project_id: string; commits: GitCommitEntry[]; total: number }> {
    return request(
      `/git/commits?project_id=${encodeURIComponent(projectId)}&user_id=${encodeURIComponent(userId)}&limit=${limit}`
    );
  },

  async manageGitBranch(params: {
    user_id?: string;
    project_id: string;
    action: 'create' | 'switch' | 'merge';
    branch_name: string;
    source_branch?: string;
    checkout_on_create?: boolean;
    allow_dirty_switch?: boolean;
    confirmed?: boolean;
  }): Promise<GitOperationRecord> {
    return request<GitOperationRecord>('/git/branches', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        project_id: params.project_id,
        action: params.action,
        branch_name: params.branch_name,
        source_branch: params.source_branch,
        checkout_on_create: params.checkout_on_create ?? true,
        allow_dirty_switch: params.allow_dirty_switch ?? false,
        confirmed: params.confirmed ?? false,
      }),
    });
  },

  async compareGitBranches(params: {
    user_id?: string;
    project_id: string;
    base_branch: string;
    compare_branch: string;
  }): Promise<GitBranchComparisonResponse> {
    const q = new URLSearchParams({
      user_id: params.user_id || 'default_user',
      project_id: params.project_id,
      base_branch: params.base_branch,
      compare_branch: params.compare_branch,
    });
    return request<GitBranchComparisonResponse>(`/git/compare?${q.toString()}`);
  },

  async configureGitRemote(params: {
    user_id?: string;
    project_id: string;
    name?: string;
    url: string;
    provider?: GitRemoteProvider;
  }): Promise<GitOperationRecord> {
    return request<GitOperationRecord>('/git/remotes', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        project_id: params.project_id,
        name: params.name || 'origin',
        url: params.url,
        provider: params.provider || 'github',
      }),
    });
  },

  async syncGitRemote(params: {
    user_id?: string;
    project_id: string;
    remote_name?: string;
    action: 'fetch' | 'pull' | 'push';
    branch?: string;
    force?: boolean;
    allow_network?: boolean;
    confirmed?: boolean;
  }): Promise<GitOperationRecord> {
    return request<GitOperationRecord>('/git/sync', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        project_id: params.project_id,
        remote_name: params.remote_name || 'origin',
        action: params.action,
        branch: params.branch,
        force: params.force ?? false,
        allow_network: params.allow_network ?? false,
        confirmed: params.confirmed ?? false,
      }),
    });
  },

  async reviewGitChanges(params: {
    user_id?: string;
    project_id: string;
    paths?: string[];
    run_stage18_tests?: boolean;
  }): Promise<GitCodeReviewResponse> {
    return request<GitCodeReviewResponse>('/git/review', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        project_id: params.project_id,
        paths: params.paths || [],
        run_stage18_tests: params.run_stage18_tests ?? true,
      }),
    });
  },

  async listGitPullRequests(
    projectId: string,
    userId = 'default_user'
  ): Promise<{ pull_requests: GitPullRequestRecord[]; total: number }> {
    return request(
      `/git/pull-requests?project_id=${encodeURIComponent(projectId)}&user_id=${encodeURIComponent(userId)}`
    );
  },

  async createGitPullRequest(params: {
    user_id?: string;
    project_id: string;
    title: string;
    description?: string;
    source_branch: string;
    target_branch?: string;
    issue_references?: string[];
    submit_to_remote?: boolean;
    confirmed?: boolean;
  }): Promise<GitPullRequestRecord> {
    return request<GitPullRequestRecord>('/git/pull-requests', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        project_id: params.project_id,
        title: params.title,
        description: params.description || '',
        source_branch: params.source_branch,
        target_branch: params.target_branch || 'main',
        issue_references: params.issue_references || [],
        submit_to_remote: params.submit_to_remote ?? false,
        confirmed: params.confirmed ?? false,
      }),
    });
  },

  async listGitOperations(
    projectId?: string,
    userId = 'default_user',
    limit = 30
  ): Promise<{ operations: GitOperationRecord[]; total: number }> {
    const q = new URLSearchParams({ user_id: userId, limit: String(limit) });
    if (projectId) q.set('project_id', projectId);
    return request(`/git/operations?${q.toString()}`);
  },

  async approveGitOperation(
    operationId: string,
    params: {
      user_id?: string;
      approved: boolean;
      user_note?: string;
    }
  ): Promise<GitOperationRecord> {
    return request<GitOperationRecord>(
      `/git/operations/${encodeURIComponent(operationId)}/approve`,
      {
        method: 'POST',
        body: JSON.stringify({
          user_id: params.user_id || 'default_user',
          approved: params.approved,
          user_note: params.user_note,
        }),
      }
    );
  },

  // =========================================================================
  // Stage 20: AI Evaluation & Quality Assurance Engine
  // =========================================================================

  async getEvaluationMetadata(): Promise<EvalMetadataResponse> {
    return request<EvalMetadataResponse>('/evaluation/metadata');
  },

  async listEvaluationCases(
    suiteId?: EvalSuiteId,
    includeRejected = false
  ): Promise<{ dataset_version: string; total: number; cases: EvalTestCase[] }> {
    const q = new URLSearchParams({ include_rejected: String(includeRejected) });
    if (suiteId) q.set('suite_id', suiteId);
    return request(`/evaluation/cases?${q.toString()}`);
  },

  async createEvaluationCase(params: {
    suite_id: EvalSuiteId;
    title: string;
    description?: string;
    input_payload: Record<string, any>;
    expected_criteria: Record<string, any>;
    scoring_rubric?: string;
    is_edge_case?: boolean;
    is_critical?: boolean;
    known_limitations?: string;
    source_type?: EvalCaseSourceType;
    contains_private_conversation_data?: boolean;
  }): Promise<EvalTestCase> {
    return request<EvalTestCase>('/evaluation/cases', {
      method: 'POST',
      body: JSON.stringify({
        suite_id: params.suite_id,
        title: params.title,
        description: params.description || '',
        input_payload: params.input_payload,
        expected_criteria: params.expected_criteria,
        scoring_rubric: params.scoring_rubric || 'Deterministic assertion check',
        is_edge_case: params.is_edge_case ?? false,
        is_critical: params.is_critical ?? false,
        known_limitations: params.known_limitations || '',
        source_type: params.source_type || 'curated_benchmark',
        contains_private_conversation_data: params.contains_private_conversation_data ?? false,
      }),
    });
  },

  async generateSyntheticCases(params: {
    suite_id: EvalSuiteId;
    topic_focus?: string;
    count?: number;
  }): Promise<{
    dataset_version: string;
    generated_count: number;
    cases: EvalTestCase[];
  }> {
    return request('/evaluation/cases/synthetic', {
      method: 'POST',
      body: JSON.stringify({
        suite_id: params.suite_id,
        topic_focus: params.topic_focus || 'edge_case_boundary',
        count: params.count || 2,
      }),
    });
  },

  async reviewEvaluationCase(
    caseId: string,
    params: {
      review_status: EvalCaseReviewStatus;
      reviewer_note?: string;
    }
  ): Promise<EvalTestCase> {
    return request<EvalTestCase>(`/evaluation/cases/${encodeURIComponent(caseId)}/review`, {
      method: 'POST',
      body: JSON.stringify({
        review_status: params.review_status,
        reviewer_note: params.reviewer_note || '',
      }),
    });
  },

  async deleteEvaluationCase(
    caseId: string
  ): Promise<{ deleted: boolean; case_id: string; dataset_version: string }> {
    return request(`/evaluation/cases/${encodeURIComponent(caseId)}`, {
      method: 'DELETE',
    });
  },

  async exportEvaluationDataset(): Promise<{
    dataset_version: string;
    total_cases: number;
    cases: EvalTestCase[];
    changelog: any[];
  }> {
    return request('/evaluation/datasets/export');
  },

  async executeEvaluationRun(params: {
    label?: string;
    suites?: EvalSuiteId[];
    include_pending_synthetic?: boolean;
    baseline_run_id?: string;
    thresholds?: EvalAcceptanceThresholds;
    simulate_interrupted_after_n?: number;
    simulate_provider_failure?: boolean;
  }): Promise<EvalRunRecord> {
    return request<EvalRunRecord>('/evaluation/runs', {
      method: 'POST',
      body: JSON.stringify({
        label: params.label || 'Stage 20 QA Benchmark Run',
        suites: params.suites || [],
        include_pending_synthetic: params.include_pending_synthetic ?? false,
        baseline_run_id: params.baseline_run_id || undefined,
        thresholds: params.thresholds,
        simulate_interrupted_after_n: params.simulate_interrupted_after_n,
        simulate_provider_failure: params.simulate_provider_failure ?? false,
      }),
    });
  },

  async listEvaluationRuns(
    limit = 25
  ): Promise<{ runs: EvalRunRecord[]; total: number }> {
    return request(`/evaluation/runs?limit=${limit}`);
  },

  async getEvaluationRun(runId: string): Promise<EvalRunRecord> {
    return request<EvalRunRecord>(`/evaluation/runs/${encodeURIComponent(runId)}`);
  },

  async compareEvaluationRuns(params: {
    baseline_run_id: string;
    candidate_run_id: string;
    thresholds?: EvalAcceptanceThresholds;
  }): Promise<{
    baseline_run_id: string;
    candidate_run_id: string;
    baseline_dataset_version: string;
    candidate_dataset_version: string;
    regression_alerts: EvalRegressionAlert[];
    has_critical_regressions: boolean;
    candidate_verdict: EvalReleaseGateVerdict;
  }> {
    return request('/evaluation/compare', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async exportEvaluationRunReport(
    runId: string,
    format: 'markdown' | 'json' = 'markdown'
  ): Promise<any> {
    return request(
      `/evaluation/runs/${encodeURIComponent(runId)}/export?format=${encodeURIComponent(format)}`
    );
  },

  // =========================================================================
  // Stage 21: Universal Knowledge Discovery Engine
  // =========================================================================

  async getDiscoveryMetadata(): Promise<DiscoveryMetadataResponse> {
    return request<DiscoveryMetadataResponse>('/discovery/metadata');
  },

  async executeDiscoverySearch(params: {
    query: string;
    mode?: DiscoverySearchMode;
    source_types?: DiscoverySourceType[];
    language?: string;
    date_from?: string;
    date_to?: string;
    domain_filter?: string;
    exclude_terms?: string[];
    exact_phrase?: string;
    page?: number;
    page_size?: number;
    bypass_cache?: boolean;
    simulate_failed_connectors?: string[];
    user_id?: string;
  }): Promise<DiscoverySearchResponse> {
    return request<DiscoverySearchResponse>('/discovery/search', {
      method: 'POST',
      body: JSON.stringify({
        query: params.query,
        mode: params.mode || 'comprehensive',
        source_types: params.source_types || [],
        language: params.language || 'auto',
        date_from: params.date_from || undefined,
        date_to: params.date_to || undefined,
        domain_filter: params.domain_filter || undefined,
        exclude_terms: params.exclude_terms || [],
        exact_phrase: params.exact_phrase || undefined,
        page: params.page || 1,
        page_size: params.page_size || 10,
        bypass_cache: params.bypass_cache ?? false,
        simulate_failed_connectors: params.simulate_failed_connectors || [],
        user_id: params.user_id || 'default_user',
      }),
    });
  },

  async listDiscoveryHistory(limit = 15): Promise<DiscoverySearchResponse[]> {
    return request<DiscoverySearchResponse[]>(`/discovery/history?limit=${limit}`);
  },

  // =========================================================================
  // Stage 22: Knowledge Graph Intelligence Engine
  // =========================================================================

  async getKnowledgeGraphMetadata(): Promise<KGMetadataResponse> {
    return request<KGMetadataResponse>('/knowledge-graph/metadata');
  },

  async getKnowledgeGraphSnapshot(params?: {
    user_id?: string;
    workspace_id?: string;
    search?: string;
    entity_type?: string;
    relation_type?: string;
    fact_basis?: string;
    page?: number;
    page_size?: number;
  }): Promise<KGGraphSnapshotResponse> {
    const q = new URLSearchParams();
    q.set('user_id', params?.user_id || 'default_user');
    q.set('workspace_id', params?.workspace_id || 'default_workspace');
    if (params?.search) q.set('search', params.search);
    if (params?.entity_type) q.set('entity_type', params.entity_type);
    if (params?.relation_type) q.set('relation_type', params.relation_type);
    if (params?.fact_basis) q.set('fact_basis', params.fact_basis);
    q.set('page', String(params?.page || 1));
    q.set('page_size', String(params?.page_size || 50));
    return request<KGGraphSnapshotResponse>(`/knowledge-graph/snapshot?${q.toString()}`);
  },

  async ingestKnowledgeGraph(params: {
    user_id?: string;
    workspace_id?: string;
    source_title: string;
    source_url?: string;
    page_or_section?: string;
    source_text?: string;
    vault_document_ids?: string[];
    discovery_id?: string;
    explicit_entities?: Array<{
      label: string;
      entity_type: KGEntityType;
      aliases?: string[];
      description?: string;
    }>;
    explicit_relationships?: Array<{
      source_label: string;
      source_type: KGEntityType;
      target_label: string;
      target_type: KGEntityType;
      relation_type: KGRelationType;
      fact_basis?: KGFactBasis;
      passage?: string;
      page_or_section?: string;
      source_title?: string;
      source_url?: string;
    }>;
    derive_inferred_relationships?: boolean;
  }): Promise<KGIngestResponse> {
    return request<KGIngestResponse>('/knowledge-graph/ingest', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        source_title: params.source_title,
        source_url: params.source_url || undefined,
        page_or_section: params.page_or_section || 'Section 1',
        source_text: params.source_text || '',
        vault_document_ids: params.vault_document_ids || [],
        discovery_id: params.discovery_id || undefined,
        explicit_entities: params.explicit_entities || [],
        explicit_relationships: params.explicit_relationships || [],
        derive_inferred_relationships: params.derive_inferred_relationships ?? true,
      }),
    });
  },

  async queryKnowledgeGraph(params: {
    user_id?: string;
    workspace_id?: string;
    mode?: KGQueryMode;
    question?: string;
    source_entity?: string;
    target_entity?: string;
    max_depth?: number;
    include_inferred?: boolean;
    relation_types?: KGRelationType[];
  }): Promise<KGQueryResponse> {
    return request<KGQueryResponse>('/knowledge-graph/query', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        mode: params.mode || 'natural_language',
        question: params.question || '',
        source_entity: params.source_entity || undefined,
        target_entity: params.target_entity || undefined,
        max_depth: params.max_depth || 4,
        include_inferred: params.include_inferred ?? true,
        relation_types: params.relation_types || [],
      }),
    });
  },

  async listDuplicateEntities(
    userId = 'default_user',
    workspaceId = 'default_workspace'
  ): Promise<KGDuplicateCandidate[]> {
    return request<KGDuplicateCandidate[]>(
      `/knowledge-graph/duplicates?user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}`
    );
  },

  async mergeKnowledgeGraphEntities(params: {
    user_id?: string;
    workspace_id?: string;
    source_entity_id: string;
    target_entity_id: string;
    confirmed?: boolean;
  }): Promise<KGDestructiveOperationRecord> {
    return request<KGDestructiveOperationRecord>('/knowledge-graph/entities/merge', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        source_entity_id: params.source_entity_id,
        target_entity_id: params.target_entity_id,
        confirmed: params.confirmed ?? false,
      }),
    });
  },

  async deleteKnowledgeGraphItems(params: {
    user_id?: string;
    workspace_id?: string;
    entity_ids?: string[];
    relationship_ids?: string[];
    clear_workspace?: boolean;
    confirmed?: boolean;
  }): Promise<KGDestructiveOperationRecord> {
    return request<KGDestructiveOperationRecord>('/knowledge-graph/delete', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        entity_ids: params.entity_ids || [],
        relationship_ids: params.relationship_ids || [],
        clear_workspace: params.clear_workspace ?? false,
        confirmed: params.confirmed ?? false,
      }),
    });
  },

  async approveKnowledgeGraphOperation(
    opId: string,
    params: {
      user_id?: string;
      workspace_id?: string;
      approved: boolean;
    }
  ): Promise<KGDestructiveOperationRecord> {
    return request<KGDestructiveOperationRecord>(
      `/knowledge-graph/operations/${encodeURIComponent(opId)}/approve`,
      {
        method: 'POST',
        body: JSON.stringify({
          user_id: params.user_id || 'default_user',
          workspace_id: params.workspace_id || 'default_workspace',
          approved: params.approved,
        }),
      }
    );
  },

  async listKnowledgeGraphOperations(
    userId = 'default_user',
    workspaceId = 'default_workspace'
  ): Promise<KGDestructiveOperationRecord[]> {
    return request<KGDestructiveOperationRecord[]>(
      `/knowledge-graph/operations?user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}`
    );
  },

  async listKnowledgeGraphHistory(
    userId = 'default_user',
    workspaceId = 'default_workspace',
    limit = 25
  ): Promise<KGChangeLogEntry[]> {
    return request<KGChangeLogEntry[]>(
      `/knowledge-graph/history?user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}&limit=${limit}`
    );
  },

  // Stage 23: IoT Project Builder Methods
  async getIoTMetadata(): Promise<IoTMetadataResponse> {
    return request<IoTMetadataResponse>('/iot/metadata');
  },

  async listIoTBoards(): Promise<IoTBoardProfile[]> {
    return request<IoTBoardProfile[]>('/iot/boards');
  },

  async listIoTComponents(params?: {
    category?: string;
    interface?: string;
    query?: string;
  }): Promise<IoTComponentSpec[]> {
    const qs = new URLSearchParams();
    if (params?.category && params.category !== 'all') qs.set('category', params.category);
    if (params?.interface && params.interface !== 'all') qs.set('interface', params.interface);
    if (params?.query) qs.set('query', params.query);
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    return request<IoTComponentSpec[]>(`/iot/components${suffix}`);
  },

  async listIoTProjects(
    userId = 'default_user',
    workspaceId = 'default_workspace'
  ): Promise<IoTProjectRecord[]> {
    return request<IoTProjectRecord[]>(
      `/iot/projects?user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}`
    );
  },

  async createIoTProject(params: {
    user_id?: string;
    workspace_id?: string;
    name: string;
    invention_description: string;
    target_budget_usd?: number;
    power_source?: IoTPowerSource;
    environment?: IoTEnvironmentType;
    preferred_board_id?: IoTBoardId;
    component_ids?: string[];
    firmware_language?: IoTFirmwareLanguage;
    connectivity_protocol?: IoTConnectivityProtocol;
    auto_wire?: boolean;
  }): Promise<IoTProjectRecord> {
    return request<IoTProjectRecord>('/iot/projects', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        name: params.name,
        invention_description: params.invention_description,
        target_budget_usd: params.target_budget_usd ?? 45.0,
        power_source: params.power_source || 'usb_5v',
        environment: params.environment || 'indoor_lab',
        preferred_board_id: params.preferred_board_id,
        component_ids: params.component_ids || [],
        firmware_language: params.firmware_language,
        connectivity_protocol: params.connectivity_protocol || 'wifi_mqtt',
        auto_wire: params.auto_wire ?? true,
      }),
    });
  },

  async getIoTProject(
    projectId: string,
    userId = 'default_user',
    workspaceId = 'default_workspace'
  ): Promise<IoTProjectRecord> {
    return request<IoTProjectRecord>(
      `/iot/projects/${encodeURIComponent(projectId)}?user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}`
    );
  },

  async updateIoTWiring(
    projectId: string,
    params: {
      user_id?: string;
      workspace_id?: string;
      board_id?: IoTBoardId;
      power_source?: IoTPowerSource;
      placed_components: IoTPlacedComponent[];
      wires: IoTWireConnection[];
      auto_regenerate_firmware?: boolean;
    }
  ): Promise<IoTProjectRecord> {
    return request<IoTProjectRecord>(`/iot/projects/${encodeURIComponent(projectId)}/wiring`, {
      method: 'PUT',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        board_id: params.board_id,
        power_source: params.power_source,
        placed_components: params.placed_components,
        wires: params.wires,
        auto_regenerate_firmware: params.auto_regenerate_firmware ?? true,
      }),
    });
  },

  async generateIoTFirmware(
    projectId: string,
    params: {
      user_id?: string;
      workspace_id?: string;
      language: IoTFirmwareLanguage;
      custom_source_code?: string;
      run_compiler_check?: boolean;
    }
  ): Promise<IoTProjectRecord> {
    return request<IoTProjectRecord>(`/iot/projects/${encodeURIComponent(projectId)}/firmware`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        language: params.language,
        custom_source_code: params.custom_source_code,
        run_compiler_check: params.run_compiler_check ?? true,
      }),
    });
  },

  async simulateIoTProject(
    projectId: string,
    params: {
      user_id?: string;
      workspace_id?: string;
      ticks?: number;
      stimuli?: IoTSimulationStimulus[];
      inject_fault?: 'none' | 'sensor_disconnect' | 'overtemperature' | 'brownout_voltage' | 'mqtt_broker_offline';
    }
  ): Promise<IoTSimulationResponse> {
    return request<IoTSimulationResponse>(`/iot/projects/${encodeURIComponent(projectId)}/simulate`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        ticks: params.ticks ?? 6,
        stimuli: params.stimuli || [],
        inject_fault: params.inject_fault || 'none',
      }),
    });
  },

  async exportIoTProject(
    projectId: string,
    params?: {
      user_id?: string;
      workspace_id?: string;
      bump_version?: 'none' | 'patch' | 'minor' | 'major';
      write_to_workspace_files?: boolean;
    }
  ): Promise<IoTProjectExportResponse> {
    return request<IoTProjectExportResponse>(`/iot/projects/${encodeURIComponent(projectId)}/export`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: params?.user_id || 'default_user',
        workspace_id: params?.workspace_id || 'default_workspace',
        bump_version: params?.bump_version || 'patch',
        write_to_workspace_files: params?.write_to_workspace_files ?? true,
      }),
    });
  },

  // Stage 24: Embedded Firmware Engineering Studio Methods
  async getFirmwareMetadata(): Promise<FirmwareMetadataResponse> {
    return request<FirmwareMetadataResponse>('/firmware/metadata');
  },

  async listFirmwarePlatforms(): Promise<FirmwarePlatformMatrixEntry[]> {
    return request<FirmwarePlatformMatrixEntry[]>('/firmware/platforms');
  },

  async listFirmwareWorkspaces(
    userId = 'default_user',
    workspaceId = 'default_workspace'
  ): Promise<FirmwareWorkspaceRecord[]> {
    return request<FirmwareWorkspaceRecord[]>(
      `/firmware/workspaces?user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}`
    );
  },

  async createFirmwareWorkspace(params: {
    user_id?: string;
    workspace_id?: string;
    name: string;
    iot_project_id?: string | null;
    board_id: IoTBoardId;
    framework: FirmwareFrameworkId;
    build_settings?: FirmwareBuildSettings;
  }): Promise<FirmwareWorkspaceRecord> {
    return request<FirmwareWorkspaceRecord>('/firmware/workspaces', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        name: params.name,
        iot_project_id: params.iot_project_id || null,
        board_id: params.board_id,
        framework: params.framework,
        build_settings: params.build_settings,
      }),
    });
  },

  async getFirmwareWorkspace(
    fwProjectId: string,
    userId = 'default_user',
    workspaceId = 'default_workspace'
  ): Promise<FirmwareWorkspaceRecord> {
    return request<FirmwareWorkspaceRecord>(
      `/firmware/workspaces/${encodeURIComponent(fwProjectId)}?user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}`
    );
  },

  async updateFirmwareFile(
    fwProjectId: string,
    params: {
      user_id?: string;
      workspace_id?: string;
      file_path: string;
      content: string;
      commit_note?: string;
      create_version_snapshot?: boolean;
    }
  ): Promise<FirmwareWorkspaceRecord> {
    return request<FirmwareWorkspaceRecord>(`/firmware/workspaces/${encodeURIComponent(fwProjectId)}/files`, {
      method: 'PUT',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        file_path: params.file_path,
        content: params.content,
        commit_note: params.commit_note || 'Updated firmware source file',
        create_version_snapshot: params.create_version_snapshot ?? true,
      }),
    });
  },

  async searchFirmwareCode(
    fwProjectId: string,
    query: string,
    userId = 'default_user',
    workspaceId = 'default_workspace'
  ): Promise<FirmwareCodeSearchHit[]> {
    return request<FirmwareCodeSearchHit[]>(
      `/firmware/workspaces/${encodeURIComponent(fwProjectId)}/search?query=${encodeURIComponent(query)}&user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}`
    );
  },

  async compileFirmwareWorkspace(
    fwProjectId: string,
    params?: {
      user_id?: string;
      workspace_id?: string;
      run_unit_tests?: boolean;
    }
  ): Promise<FirmwareCompileResult> {
    return request<FirmwareCompileResult>(`/firmware/workspaces/${encodeURIComponent(fwProjectId)}/compile`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: params?.user_id || 'default_user',
        workspace_id: params?.workspace_id || 'default_workspace',
        run_unit_tests: params?.run_unit_tests ?? true,
      }),
    });
  },

  async readFirmwareSerialMonitor(
    fwProjectId: string,
    params?: {
      user_id?: string;
      workspace_id?: string;
      mode?: 'simulated_virtual_serial' | 'physical_authorized_serial';
      serial_port?: string;
      simulate_reset_event?: 'POWERON_RESET' | 'SW_CPU_RESET' | 'WDT_RESET' | 'BROWNOUT_RST';
      lines_count?: number;
    }
  ): Promise<FirmwareSerialMonitorResponse> {
    return request<FirmwareSerialMonitorResponse>(`/firmware/workspaces/${encodeURIComponent(fwProjectId)}/serial`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: params?.user_id || 'default_user',
        workspace_id: params?.workspace_id || 'default_workspace',
        mode: params?.mode || 'simulated_virtual_serial',
        serial_port: params?.serial_port,
        simulate_reset_event: params?.simulate_reset_event || 'POWERON_RESET',
        lines_count: params?.lines_count ?? 8,
      }),
    });
  },

  async requestFirmwareDeviceAction(
    fwProjectId: string,
    params: {
      user_id?: string;
      workspace_id?: string;
      action_type: 'flash_firmware' | 'reset_device';
      target_port?: string;
      confirmed?: boolean;
    }
  ): Promise<FirmwareDeviceActionRecord> {
    return request<FirmwareDeviceActionRecord>(
      `/firmware/workspaces/${encodeURIComponent(fwProjectId)}/device-action`,
      {
        method: 'POST',
        body: JSON.stringify({
          user_id: params.user_id || 'default_user',
          workspace_id: params.workspace_id || 'default_workspace',
          action_type: params.action_type,
          target_port: params.target_port || 'COM3',
          confirmed: params.confirmed ?? false,
        }),
      }
    );
  },

  async approveFirmwareDeviceAction(
    actionId: string,
    params?: {
      user_id?: string;
      workspace_id?: string;
      approved?: boolean;
    }
  ): Promise<FirmwareDeviceActionRecord> {
    return request<FirmwareDeviceActionRecord>(
      `/firmware/device-actions/${encodeURIComponent(actionId)}/approve`,
      {
        method: 'POST',
        body: JSON.stringify({
          user_id: params?.user_id || 'default_user',
          workspace_id: params?.workspace_id || 'default_workspace',
          approved: params?.approved ?? true,
        }),
      }
    );
  },

  async restoreFirmwareWorkspaceVersion(
    fwProjectId: string,
    versionId: string,
    userId = 'default_user',
    workspaceId = 'default_workspace'
  ): Promise<FirmwareWorkspaceRecord> {
    return request<FirmwareWorkspaceRecord>(
      `/firmware/workspaces/${encodeURIComponent(fwProjectId)}/restore-version`,
      {
        method: 'POST',
        body: JSON.stringify({
          user_id: userId,
          workspace_id: workspaceId,
          version_id: versionId,
        }),
      }
    );
  },

  async exportFirmwareWorkspace(
    fwProjectId: string,
    userId = 'default_user',
    workspaceId = 'default_workspace'
  ): Promise<FirmwareExportResponse> {
    return request<FirmwareExportResponse>(
      `/firmware/workspaces/${encodeURIComponent(fwProjectId)}/export?user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}`,
      { method: 'POST' }
    );
  },

  // =========================================================================
  // Stage 25: IoT Device Connectivity & Live Telemetry
  // =========================================================================

  async getTelemetryMetadata(): Promise<TelemetryMetadataResponse> {
    try {
      return await request<TelemetryMetadataResponse>('/telemetry/metadata');
    } catch {
      // Standalone Cloud Demo fallback
      return {
        stage: 25,
        engine: 'IoTTelemetryEngine',
        supported_metrics: [
          { key: 'temperature', unit: '°C', min: -50, max: 150, description: 'Ambient or process temperature' },
          { key: 'humidity', unit: '%RH', min: 0, max: 100, description: 'Relative humidity' },
          { key: 'vibration', unit: 'g', min: 0, max: 50, description: 'Tri-axial peak vibration acceleration' },
          { key: 'current', unit: 'mA', min: 0, max: 5000, description: 'Electrical current' },
          { key: 'voltage', unit: 'V', min: 0, max: 60, description: 'Bus voltage' },
        ],
        supported_protocols: ['http', 'mqtt', 'dual'],
        mqtt_broker_config: { broker_host: 'mqtt.nexora.local', broker_port: 8883, tls_enabled: true },
        security_policy: { token_storage: 'salted_pbkdf2_hmac_sha256', header_name: 'X-Device-Token' },
        reliability_specs: { max_payload_size_bytes: 65536, max_events_retention_per_device: 2000 },
      };
    }
  },

  async listIoTDevices(workspaceId = 'default_workspace', userId = 'default_user'): Promise<IoTDeviceRecord[]> {
    try {
      return await request<IoTDeviceRecord[]>(
        `/telemetry/devices?workspace_id=${encodeURIComponent(workspaceId)}&user_id=${encodeURIComponent(userId)}`
      );
    } catch {
      // Cloud fallback simulated devices
      return [
        {
          device_id: 'dev_cloud_demo_01',
          user_id: userId,
          workspace_id: workspaceId,
          name: 'Factory Floor Chiller ESP32',
          board_id: 'esp32_devkit_v1',
          is_simulated: true,
          mac_address: '02:00:1A:2B:3C:4D',
          firmware_version: '1.0.0',
          status: 'online',
          ingestion_protocol: 'dual',
          mqtt_topic_telemetry: `nexora/${workspaceId}/dev_cloud_demo_01/telemetry`,
          mqtt_topic_commands: `nexora/${workspaceId}/dev_cloud_demo_01/commands`,
          rate_limit_per_minute: 60,
          last_seen_at: new Date().toISOString(),
          last_reading_age_seconds: 4.2,
          total_events_received: 148,
          active_alerts_count: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ];
    }
  },

  async registerIoTDevice(params: {
    name: string;
    board_id?: string;
    is_simulated?: boolean;
    mac_address?: string;
    firmware_version?: string;
    rate_limit_per_minute?: number;
    iot_project_id?: string;
    fw_project_id?: string;
    workspace_id?: string;
    user_id?: string;
  }): Promise<{ device: IoTDeviceRecord; credentials: IoTDeviceTokenResponse }> {
    return request<{ device: IoTDeviceRecord; credentials: IoTDeviceTokenResponse }>('/telemetry/devices', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        name: params.name,
        board_id: params.board_id || 'esp32_devkit_v1',
        is_simulated: params.is_simulated ?? true,
        mac_address: params.mac_address,
        firmware_version: params.firmware_version || '1.0.0',
        rate_limit_per_minute: params.rate_limit_per_minute || 60,
        iot_project_id: params.iot_project_id,
        fw_project_id: params.fw_project_id,
      }),
    });
  },

  async rotateIoTDeviceToken(
    deviceId: string,
    workspaceId = 'default_workspace',
    userId = 'default_user'
  ): Promise<IoTDeviceTokenResponse> {
    return request<IoTDeviceTokenResponse>(`/telemetry/devices/${encodeURIComponent(deviceId)}/rotate-token`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, workspace_id: workspaceId }),
    });
  },

  async revokeIoTDeviceToken(
    deviceId: string,
    workspaceId = 'default_workspace',
    userId = 'default_user'
  ): Promise<{ status: string; message: string }> {
    return request<{ status: string; message: string }>(
      `/telemetry/devices/${encodeURIComponent(deviceId)}/revoke-token?user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}`,
      { method: 'POST' }
    );
  },

  async deregisterIoTDevice(
    deviceId: string,
    workspaceId = 'default_workspace',
    userId = 'default_user'
  ): Promise<{ status: string; message: string }> {
    return request<{ status: string; message: string }>(
      `/telemetry/devices/${encodeURIComponent(deviceId)}?user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}`,
      { method: 'DELETE' }
    );
  },

  async getIoTDeviceStats(
    deviceId: string,
    workspaceId = 'default_workspace',
    userId = 'default_user'
  ): Promise<TelemetryDeviceStatsResponse> {
    try {
      return await request<TelemetryDeviceStatsResponse>(
        `/telemetry/devices/${encodeURIComponent(deviceId)}/stats?user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}`
      );
    } catch {
      // Cloud demo fallback stats
      const now = new Date().toISOString();
      return {
        device_id: deviceId,
        device_name: 'Cloud Demo ESP32 Node',
        status: 'online',
        is_simulated: true,
        last_seen_at: now,
        last_seen_seconds_ago: 2.1,
        data_freshness_label: 'Real-time Live (< 15s)',
        total_events: 42,
        latest_metrics: { temperature: 24.8, humidity: 56.2, vibration: 0.45, voltage: 3.82, current: 142.0 },
        metric_ranges: {
          temperature: { min: 21.2, max: 27.6, avg: 24.4, current: 24.8 },
          humidity: { min: 48.0, max: 64.0, avg: 56.0, current: 56.2 },
          vibration: { min: 0.38, max: 0.62, avg: 0.44, current: 0.45 },
          voltage: { min: 3.75, max: 3.92, avg: 3.84, current: 3.82 },
        },
        recent_events: [],
        active_alerts: [],
        pending_commands: [],
      };
    }
  },

  async listTelemetryEvents(
    deviceId: string,
    params?: { workspace_id?: string; limit?: number; since_iso?: string }
  ): Promise<TelemetryEventRecord[]> {
    try {
      const q = new URLSearchParams();
      if (params?.workspace_id) q.set('workspace_id', params.workspace_id);
      if (params?.limit) q.set('limit', String(params.limit));
      if (params?.since_iso) q.set('since_iso', params.since_iso);
      return await request<TelemetryEventRecord[]>(`/telemetry/devices/${encodeURIComponent(deviceId)}/events?${q.toString()}`);
    } catch {
      return [];
    }
  },

  async simulateTelemetryTick(
    deviceId: string,
    params?: { tick_count?: number; anomaly_inject?: string; workspace_id?: string; user_id?: string }
  ): Promise<{ ticks_generated: number; triggered_alerts: string[]; message: string }> {
    return request<{ ticks_generated: number; triggered_alerts: string[]; message: string }>(
      `/telemetry/devices/${encodeURIComponent(deviceId)}/simulate-tick`,
      {
        method: 'POST',
        body: JSON.stringify({
          user_id: params?.user_id || 'default_user',
          workspace_id: params?.workspace_id || 'default_workspace',
          tick_count: params?.tick_count ?? 1,
          anomaly_inject: params?.anomaly_inject,
        }),
      }
    );
  },

  async createAlertRule(
    deviceId: string,
    params: {
      metric_key: string;
      operator: string;
      threshold_val_primary: number;
      threshold_val_secondary?: number;
      severity?: string;
      cooldown_seconds?: number;
      description?: string;
      workspace_id?: string;
      user_id?: string;
    }
  ): Promise<AlertRuleRecord> {
    return request<AlertRuleRecord>(`/telemetry/devices/${encodeURIComponent(deviceId)}/alert-rules`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        metric_key: params.metric_key,
        operator: params.operator,
        threshold_val_primary: params.threshold_val_primary,
        threshold_val_secondary: params.threshold_val_secondary,
        severity: params.severity || 'warning',
        cooldown_seconds: params.cooldown_seconds ?? 300,
        description: params.description,
      }),
    });
  },

  async listAlertRules(deviceId: string, workspaceId = 'default_workspace'): Promise<AlertRuleRecord[]> {
    return request<AlertRuleRecord[]>(
      `/telemetry/devices/${encodeURIComponent(deviceId)}/alert-rules?workspace_id=${encodeURIComponent(workspaceId)}`
    );
  },

  async listAlerts(
    workspaceId = 'default_workspace',
    deviceId?: string,
    status?: string
  ): Promise<AlertRecord[]> {
    try {
      const q = new URLSearchParams({ workspace_id: workspaceId });
      if (deviceId) q.set('device_id', deviceId);
      if (status) q.set('status', status);
      return await request<AlertRecord[]>(`/telemetry/alerts?${q.toString()}`);
    } catch {
      return [];
    }
  },

  async acknowledgeAlert(
    alertId: string,
    workspaceId = 'default_workspace',
    userId = 'default_user'
  ): Promise<AlertRecord> {
    return request<AlertRecord>(`/telemetry/alerts/${encodeURIComponent(alertId)}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, workspace_id: workspaceId }),
    });
  },

  async createDeviceCommand(
    deviceId: string,
    params: {
      command_type: string;
      parameters?: Record<string, any>;
      reason?: string;
      workspace_id?: string;
      user_id?: string;
    }
  ): Promise<DeviceCommandRecord> {
    return request<DeviceCommandRecord>(`/telemetry/devices/${encodeURIComponent(deviceId)}/commands`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        command_type: params.command_type,
        parameters: params.parameters || {},
        reason: params.reason,
      }),
    });
  },

  async confirmDeviceCommand(
    commandId: string,
    confirmed = true,
    workspaceId = 'default_workspace',
    userId = 'default_user'
  ): Promise<DeviceCommandRecord> {
    return request<DeviceCommandRecord>(`/telemetry/commands/${encodeURIComponent(commandId)}/confirm`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, workspace_id: workspaceId, confirmed }),
    });
  },

  async listDeviceCommands(deviceId: string, workspaceId = 'default_workspace'): Promise<DeviceCommandRecord[]> {
    try {
      return await request<DeviceCommandRecord[]>(
        `/telemetry/devices/${encodeURIComponent(deviceId)}/commands?workspace_id=${encodeURIComponent(workspaceId)}`
      );
    } catch {
      return [];
    }
  },

  async exportTelemetry(
    deviceId: string,
    params?: {
      format?: 'csv' | 'json';
      time_range?: '1h' | '6h' | '24h' | '7d' | 'all';
      handoff_to_file_workspace?: boolean;
      workspace_id?: string;
      user_id?: string;
    }
  ): Promise<TelemetryExportResponse> {
    return request<TelemetryExportResponse>(`/telemetry/devices/${encodeURIComponent(deviceId)}/export`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: params?.user_id || 'default_user',
        workspace_id: params?.workspace_id || 'default_workspace',
        format: params?.format || 'csv',
        time_range: params?.time_range || '24h',
        handoff_to_file_workspace: params?.handoff_to_file_workspace ?? false,
      }),
    });
  },

  // Stage 26: IoT Security & Device Threat Detection APIs
  async getIoTSecurityOverview(workspaceId = 'default_workspace'): Promise<IoTSecurityOverviewResponse> {
    try {
      return await request<IoTSecurityOverviewResponse>(
        `/iot-security/overview?workspace_id=${encodeURIComponent(workspaceId)}`
      );
    } catch {
      return {
        stage: 26,
        fleet_posture_summary: {
          total_devices_monitored: 0,
          average_fleet_risk_score: 0,
          risk_distribution: { critical: 0, high: 0, medium: 0, low: 0, unknown: 0 },
          active_config_findings: 0,
          recent_behavioral_anomalies: 0,
          open_security_incidents: 0,
          tls_enforced_devices_count: 0,
          unencrypted_transport_devices_count: 0,
        },
        devices_posture: [],
        active_incidents: [],
        recent_anomalies: [],
        config_findings: [],
        firmware_integrity_matrix: [],
        last_assessment_at: new Date().toISOString(),
      };
    }
  },

  async getDeviceSecurityPosture(
    deviceId: string,
    workspaceId = 'default_workspace'
  ): Promise<DeviceSecurityPosture> {
    return request<DeviceSecurityPosture>(
      `/iot-security/devices/${encodeURIComponent(deviceId)}/posture?workspace_id=${encodeURIComponent(workspaceId)}`
    );
  },

  async auditIoTConfiguration(params: {
    user_id?: string;
    workspace_id?: string;
    device_id?: string;
    config_file_text?: string;
    filename?: string;
    config_payload?: Record<string, any>;
  }): Promise<ConfigurationAuditFinding[]> {
    return request<ConfigurationAuditFinding[]>('/iot-security/audit/config', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        device_id: params.device_id,
        config_file_text: params.config_file_text,
        filename: params.filename,
        config_payload: params.config_payload,
      }),
    });
  },

  async listIoTFindings(
    workspace_id = 'default_workspace',
    deviceId?: string,
    severity?: string,
    status = 'active'
  ): Promise<ConfigurationAuditFinding[]> {
    try {
      const q = new URLSearchParams({ workspace_id, status });
      if (deviceId) q.set('device_id', deviceId);
      if (severity) q.set('severity', severity);
      return await request<ConfigurationAuditFinding[]>(`/iot-security/audit/findings?${q.toString()}`);
    } catch {
      return [];
    }
  },

  async analyzeDeviceBehavior(
    deviceId: string,
    workspaceId = 'default_workspace'
  ): Promise<BehavioralAnomalyRecord[]> {
    return request<BehavioralAnomalyRecord[]>(
      `/iot-security/devices/${encodeURIComponent(deviceId)}/analyze-behavior?workspace_id=${encodeURIComponent(workspaceId)}`,
      { method: 'POST' }
    );
  },

  async listIoTAnomalies(
    workspace_id = 'default_workspace',
    deviceId?: string,
    severity?: string,
    limit = 50
  ): Promise<BehavioralAnomalyRecord[]> {
    try {
      const q = new URLSearchParams({ workspace_id, limit: String(limit) });
      if (deviceId) q.set('device_id', deviceId);
      if (severity) q.set('severity', severity);
      return await request<BehavioralAnomalyRecord[]>(`/iot-security/anomalies?${q.toString()}`);
    } catch {
      return [];
    }
  },

  async listSecurityIncidents(
    workspace_id = 'default_workspace',
    status?: string,
    severity?: string
  ): Promise<SecurityIncidentRecord[]> {
    try {
      const q = new URLSearchParams({ workspace_id });
      if (status) q.set('status', status);
      if (severity) q.set('severity', severity);
      return await request<SecurityIncidentRecord[]>(`/iot-security/incidents?${q.toString()}`);
    } catch {
      return [];
    }
  },

  async createSecurityIncident(payload: {
    workspace_id?: string;
    title: string;
    severity?: string;
    classification?: string;
    affected_device_ids?: string[];
    root_cause_hypothesis?: string;
    confidence_level?: string;
    evidence_records?: Record<string, any>[];
    recommended_remediations?: string[];
  }): Promise<SecurityIncidentRecord> {
    return request<SecurityIncidentRecord>('/iot-security/incidents', {
      method: 'POST',
      body: JSON.stringify({
        workspace_id: payload.workspace_id || 'default_workspace',
        title: payload.title,
        severity: payload.severity || 'medium',
        classification: payload.classification || 'heuristic_alert',
        affected_device_ids: payload.affected_device_ids || [],
        root_cause_hypothesis: payload.root_cause_hypothesis || 'Under investigation',
        confidence_level: payload.confidence_level || 'medium',
        evidence_records: payload.evidence_records || [],
        recommended_remediations: payload.recommended_remediations || [],
      }),
    });
  },

  async getSecurityIncident(
    incidentId: string,
    workspaceId = 'default_workspace'
  ): Promise<SecurityIncidentRecord> {
    return request<SecurityIncidentRecord>(
      `/iot-security/incidents/${encodeURIComponent(incidentId)}?workspace_id=${encodeURIComponent(workspaceId)}`
    );
  },

  async updateSecurityIncidentStatus(
    incidentId: string,
    status: IncidentStatus,
    resolutionNotes?: string,
    workspaceId = 'default_workspace',
    userId = 'default_user'
  ): Promise<SecurityIncidentRecord> {
    return request<SecurityIncidentRecord>(
      `/iot-security/incidents/${encodeURIComponent(incidentId)}`,
      {
        method: 'PATCH',
        body: JSON.stringify({
          user_id: userId,
          workspace_id: workspaceId,
          status,
          resolution_notes: resolutionNotes,
        }),
      }
    );
  },

  async executeDefensiveAction(params: {
    device_id: string;
    action_type: DefensiveActionType;
    reason: string;
    confirmed?: boolean;
    workspace_id?: string;
    user_id?: string;
  }): Promise<DefensiveActionRecord> {
    return request<DefensiveActionRecord>('/iot-security/defensive-actions', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        device_id: params.device_id,
        action_type: params.action_type,
        reason: params.reason,
        confirmed: params.confirmed ?? false,
      }),
    });
  },

  async listDefensiveActions(
    workspaceId = 'default_workspace',
    deviceId?: string
  ): Promise<DefensiveActionRecord[]> {
    try {
      const q = new URLSearchParams({ workspace_id: workspaceId });
      if (deviceId) q.set('device_id', deviceId);
      return await request<DefensiveActionRecord[]>(`/iot-security/defensive-actions?${q.toString()}`);
    } catch {
      return [];
    }
  },

  async getFirmwareIntegrityMatrix(): Promise<FirmwareIntegritySpec[]> {
    try {
      return await request<FirmwareIntegritySpec[]>('/iot-security/firmware-integrity-matrix');
    } catch {
      return [];
    }
  },

  // =========================================================================
  // Stage 27: Electronic Circuit Schematic Design Studio
  // =========================================================================

  async getSchematicOverview(
    userId = 'default_user',
    workspaceId = 'default_workspace'
  ): Promise<SchematicOverviewResponse> {
    try {
      return await request<SchematicOverviewResponse>(
        `/schematic/overview?user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}`
      );
    } catch {
      return {
        stage: 27,
        projects_count: 0,
        custom_components_count: 0,
        recent_projects: [],
        standard_components_count: 30,
        toolchains: {},
      };
    }
  },

  async getSchematicCatalog(): Promise<Record<string, SchematicComponentDef>> {
    try {
      return await request<Record<string, SchematicComponentDef>>('/schematic/catalog');
    } catch {
      return {};
    }
  },

  async listSchematicProjects(
    userId = 'default_user',
    workspaceId = 'default_workspace'
  ): Promise<SchematicProject[]> {
    try {
      return await request<SchematicProject[]>(
        `/schematic/projects?user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}`
      );
    } catch {
      return [];
    }
  },

  async createSchematicProject(params: {
    title: string;
    description?: string;
    sheet?: SchematicSheet;
    user_id?: string;
    workspace_id?: string;
  }): Promise<SchematicProject> {
    return request<SchematicProject>('/schematic/projects', {
      method: 'POST',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        title: params.title,
        description: params.description || '',
        sheet: params.sheet,
      }),
    });
  },

  async getSchematicProject(
    projectId: string,
    userId = 'default_user',
    workspaceId = 'default_workspace'
  ): Promise<SchematicProject> {
    return request<SchematicProject>(
      `/schematic/projects/${encodeURIComponent(projectId)}?user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}`
    );
  },

  async updateSchematicProject(
    projectId: string,
    params: {
      title?: string;
      description?: string;
      sheet?: SchematicSheet;
      bump_version?: boolean;
      change_note?: string;
      user_id?: string;
      workspace_id?: string;
    }
  ): Promise<SchematicProject> {
    return request<SchematicProject>(`/schematic/projects/${encodeURIComponent(projectId)}`, {
      method: 'PUT',
      body: JSON.stringify({
        user_id: params.user_id || 'default_user',
        workspace_id: params.workspace_id || 'default_workspace',
        title: params.title,
        description: params.description,
        sheet: params.sheet,
        bump_version: params.bump_version ?? false,
        change_note: params.change_note,
      }),
    });
  },

  async deleteSchematicProject(
    projectId: string,
    userId = 'default_user',
    workspaceId = 'default_workspace'
  ): Promise<{ status: string; project_id: string }> {
    return request<{ status: string; project_id: string }>(
      `/schematic/projects/${encodeURIComponent(projectId)}?user_id=${encodeURIComponent(userId)}&workspace_id=${encodeURIComponent(workspaceId)}`,
      { method: 'DELETE' }
    );
  },

  async runSchematicERC(sheet: SchematicSheet): Promise<ERCReport> {
    return request<ERCReport>('/schematic/erc', {
      method: 'POST',
      body: JSON.stringify(sheet),
    });
  },

  async calculateOhmsLaw(params: {
    voltage_v?: number;
    current_a?: number;
    resistance_ohms?: number;
    power_w?: number;
  }): Promise<OhmsLawResult> {
    return request<OhmsLawResult>('/schematic/calculators/ohms-law', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async calculateVoltageDivider(params: {
    vin_v: number;
    r1_ohms?: number;
    r2_ohms?: number;
    target_vout_v?: number;
    load_resistance_ohms?: number;
  }): Promise<VoltageDividerResult> {
    return request<VoltageDividerResult>('/schematic/calculators/voltage-divider', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async calculateLEDResistor(params: {
    supply_voltage_v: number;
    led_forward_voltage_v?: number;
    led_current_ma?: number;
    led_color?: string;
  }): Promise<LEDResistorResult> {
    return request<LEDResistorResult>('/schematic/calculators/led-resistor', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async calculateRCFilter(params: {
    resistance_ohms: number;
    capacitance_farads: number;
    step_voltage_v?: number;
  }): Promise<RCTimeConstantResult> {
    return request<RCTimeConstantResult>('/schematic/calculators/rc-filter', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async calculateTransistorBias(params: {
    supply_vcc_v: number;
    input_base_voltage_v?: number;
    collector_load_current_ma?: number;
    forced_beta_saturation?: number;
  }): Promise<TransistorBiasResult> {
    return request<TransistorBiasResult>('/schematic/calculators/transistor-bias', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async calculatePowerThermal(params: {
    input_voltage_v: number;
    output_voltage_v: number;
    load_current_ma: number;
    package_type?: string;
  }): Promise<PowerThermalResult> {
    return request<PowerThermalResult>('/schematic/calculators/power-thermal', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async calculateLogicExpression(params: {
    expression: string;
    variables?: string[];
  }): Promise<LogicExpressionResult> {
    return request<LogicExpressionResult>('/schematic/calculators/logic-expression', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async runSPICESimulation(params: {
    sheet: SchematicSheet;
    analysis_type?: 'op' | 'transient' | 'ac';
    tstep_seconds?: number;
    tstop_seconds?: number;
  }): Promise<SPICESimulationResult> {
    return request<SPICESimulationResult>('/schematic/simulation/run', {
      method: 'POST',
      body: JSON.stringify({
        sheet: params.sheet,
        analysis_type: params.analysis_type || 'op',
        tstep_seconds: params.tstep_seconds || 1e-6,
        tstop_seconds: params.tstop_seconds || 1e-3,
      }),
    });
  },

  async generateAICircuit(params: {
    prompt: string;
    target_supply_voltage_v?: number;
  }): Promise<AICircuitDesignResponse> {
    return request<AICircuitDesignResponse>('/schematic/ai-assistant', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async exportSchematic(
    sheet: SchematicSheet,
    exportFormat: string
  ): Promise<SchematicExportResponse> {
    return request<SchematicExportResponse>(
      `/schematic/export?export_format=${encodeURIComponent(exportFormat)}`,
      {
        method: 'POST',
        body: JSON.stringify(sheet),
      }
    );
  },

  // ==========================================
  // Stage 29: Universal Travel & Ticket Booking
  // ==========================================
  async getTravelOverview(userId = 'default_user'): Promise<TravelOverviewResponse> {
    return request<TravelOverviewResponse>(`/travel/overview?user_id=${encodeURIComponent(userId)}`);
  },

  async getTravelProviders(): Promise<{ providers: any[]; total_active: number }> {
    return request<{ providers: any[]; total_active: number }>('/travel/providers');
  },

  async searchTravel(query: TravelSearchQuery): Promise<TravelProductItem[]> {
    return request<TravelProductItem[]>('/travel/search', {
      method: 'POST',
      body: JSON.stringify(query),
    });
  },

  async getTravelProductDetails(productId: string): Promise<TravelProductItem> {
    return request<TravelProductItem>(`/travel/products/${encodeURIComponent(productId)}`);
  },

  async holdTravelInventory(req: TravelHoldRequest): Promise<TravelHoldResponse> {
    return request<TravelHoldResponse>('/travel/hold', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  async bookTravel(req: TravelBookingRequest, idempotencyKey?: string): Promise<TravelBookingRecord> {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers['Idempotency-Key'] = idempotencyKey;
    }
    return request<TravelBookingRecord>('/travel/book', {
      method: 'POST',
      headers,
      body: JSON.stringify(req),
    });
  },

  async listTravelBookings(
    userId?: string,
    category?: string,
    status?: string
  ): Promise<TravelBookingRecord[]> {
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    if (category) params.append('category', category);
    if (status) params.append('status', status);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request<TravelBookingRecord[]>(`/travel/bookings${qs}`);
  },

  async getTravelBookingDetails(bookingId: string): Promise<TravelBookingRecord> {
    return request<TravelBookingRecord>(`/travel/bookings/${encodeURIComponent(bookingId)}`);
  },

  async cancelTravelBooking(
    req: TravelCancellationRequest,
    userId = 'default_user'
  ): Promise<TravelBookingRecord> {
    return request<TravelBookingRecord>(`/travel/cancel?user_id=${encodeURIComponent(userId)}`, {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  async rescheduleTravelBooking(
    req: TravelRescheduleRequest,
    userId = 'default_user'
  ): Promise<TravelBookingRecord> {
    return request<TravelBookingRecord>(`/travel/reschedule?user_id=${encodeURIComponent(userId)}`, {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  async getTravelAuditTrail(bookingId?: string): Promise<TravelAuditRecord[]> {
    const qs = bookingId ? `?booking_id=${encodeURIComponent(bookingId)}` : '';
    return request<TravelAuditRecord[]>(`/travel/audit${qs}`);
  },
};


export const schematicApi = {
  getProjects: (userId = 'default_user', workspaceId = 'default_workspace') =>
    api.listSchematicProjects(userId, workspaceId),
  getProject: (projectId: string, userId = 'default_user', workspaceId = 'default_workspace') =>
    api.getSchematicProject(projectId, userId, workspaceId),
  getOverview: (userId = 'default_user') => api.getSchematicOverview(userId),
};

export const pcbApi = {
  async getOverview(userId = 'default_user'): Promise<PCBOverviewResponse> {
    return request<PCBOverviewResponse>(`/pcb/overview?user_id=${encodeURIComponent(userId)}`);
  },

  async getFootprints(): Promise<PCBFootprintDef[]> {
    return request<PCBFootprintDef[]>('/pcb/footprints');
  },

  async convertSchematic(req: SchematicToPCBRequest): Promise<SchematicToPCBResponse> {
    return request<SchematicToPCBResponse>('/pcb/convert-schematic', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  async getProjects(userId = 'default_user'): Promise<PCBProject[]> {
    return request<PCBProject[]>(`/pcb/projects?user_id=${encodeURIComponent(userId)}`);
  },

  async getProject(projectId: string): Promise<PCBProject> {
    return request<PCBProject>(`/pcb/projects/${encodeURIComponent(projectId)}`);
  },

  async saveProject(project: PCBProject, versionBump = false, notes = ''): Promise<PCBProject> {
    return request<PCBProject>(
      `/pcb/projects?version_bump=${versionBump}&notes=${encodeURIComponent(notes)}`,
      {
        method: 'POST',
        body: JSON.stringify(project),
      }
    );
  },

  async deleteProject(projectId: string): Promise<{ success: boolean; message: string }> {
    return request<{ success: boolean; message: string }>(
      `/pcb/projects/${encodeURIComponent(projectId)}`,
      { method: 'DELETE' }
    );
  },

  async getRevisions(projectId: string): Promise<Array<Record<string, any>>> {
    return request<Array<Record<string, any>>>(
      `/pcb/projects/${encodeURIComponent(projectId)}/revisions`
    );
  },

  async rollbackProject(projectId: string, revisionId: string): Promise<PCBProject> {
    return request<PCBProject>(
      `/pcb/projects/${encodeURIComponent(projectId)}/rollback?revision_id=${encodeURIComponent(revisionId)}`,
      { method: 'POST' }
    );
  },

  async runDRC(board: PCBBoard): Promise<PCBDrcReport> {
    return request<PCBDrcReport>('/pcb/drc', {
      method: 'POST',
      body: JSON.stringify(board),
    });
  },

  async computeRatsnest(board: PCBBoard): Promise<{
    total_connections: number;
    routed_connections: number;
    unrouted_connections: number;
    completion_percentage: number;
    ratsnest: PCBRatsnestLine[];
  }> {
    return request('/pcb/routing/ratsnest', {
      method: 'POST',
      body: JSON.stringify(board),
    });
  },

  async computeAssistedRoute(
    startX: number,
    startY: number,
    endX: number,
    endY: number,
    mode = '45_degree'
  ): Promise<{ mode: string; waypoints: Array<{ x: number; y: number }> }> {
    return request(
      `/pcb/routing/assist?start_x=${startX}&start_y=${startY}&end_x=${endX}&end_y=${endY}&mode=${encodeURIComponent(mode)}`,
      { method: 'POST' }
    );
  },

  async calculateTraceWidth(req: TraceWidthRequest): Promise<TraceWidthResult> {
    return request<TraceWidthResult>('/pcb/calculate/trace-width', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  async calculateImpedance(req: ImpedanceRequest): Promise<ImpedanceResult> {
    return request<ImpedanceResult>('/pcb/calculate/impedance', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  async getBOM(board: PCBBoard): Promise<PCBBOMItem[]> {
    return request<PCBBOMItem[]>('/pcb/bom', {
      method: 'POST',
      body: JSON.stringify(board),
    });
  },

  async estimateCost(req: PCBCostEstimateRequest): Promise<PCBCostEstimateResult> {
    return request<PCBCostEstimateResult>('/pcb/cost-estimate', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  async exportPcb(req: PCBExportRequest): Promise<PCBExportResponse> {
    return request<PCBExportResponse>('/pcb/export', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  async diffBoards(
    boardA: PCBBoard,
    boardB: PCBBoard
  ): Promise<Record<string, any>> {
    return request<Record<string, any>>('/pcb/diff', {
      method: 'POST',
      body: JSON.stringify({ board_a: boardA, board_b: boardB }),
    });
  },
};

// ==========================================
// Stage 29: Universal Travel & Ticket Booking API
// ==========================================
export const travelApi = {
  getOverview: (userId = 'default_user') => api.getTravelOverview(userId),
  getProviders: () => api.getTravelProviders(),
  search: (query: TravelSearchQuery) => api.searchTravel(query),
  getProductDetails: (productId: string) => api.getTravelProductDetails(productId),
  holdInventory: (req: TravelHoldRequest) => api.holdTravelInventory(req),
  book: (req: TravelBookingRequest, idempotencyKey?: string) => api.bookTravel(req, idempotencyKey),
  listBookings: (userId?: string, category?: string, status?: string) =>
    api.listTravelBookings(userId, category, status),
  getBookingDetails: (bookingId: string) => api.getTravelBookingDetails(bookingId),
  cancelBooking: (req: TravelCancellationRequest, userId = 'default_user') =>
    api.cancelTravelBooking(req, userId),
  rescheduleBooking: (req: TravelRescheduleRequest, userId = 'default_user') =>
    api.rescheduleTravelBooking(req, userId),
  getAuditTrail: (bookingId?: string) => api.getTravelAuditTrail(bookingId),
};



