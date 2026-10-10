import { Message, ProviderStatusResponse, UserSettings, Conversation } from '../types';

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
        // Fallback to text
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

export const api = {
  async getHealth(): Promise<{ status: string; providers_configured: boolean; configured_providers: string[] }> {
    return request('/health');
  },

  async getProviderStatus(): Promise<ProviderStatusResponse> {
    return request('/providers/status');
  },

  async sendChatMessage(params: {
    conversationId?: string;
    messages: Message[];
    settings: UserSettings;
  }): Promise<{ id: string; content: string; model: string; provider: string; finish_reason?: string }> {
    // Determine client API key to pass if configured in client settings
    let clientApiKey = '';
    const { selectedProvider, geminiApiKey, openaiApiKey, anthropicApiKey } = params.settings;
    if (selectedProvider === 'gemini' || selectedProvider === 'auto') {
      clientApiKey = geminiApiKey || '';
    } else if (selectedProvider === 'openai') {
      clientApiKey = openaiApiKey || '';
    } else if (selectedProvider === 'anthropic') {
      clientApiKey = anthropicApiKey || '';
    }

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
      }),
    });
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
};
