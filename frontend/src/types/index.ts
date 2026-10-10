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
  images?: string[];
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
  // Stage 6 Multilingual Settings
  preferredLanguage: string;
  // Stage 7 Voice Intelligence Settings
  voiceMode: 'push_to_talk' | 'voice_chat' | 'text_and_voice';
  selectedVoiceId: string;
  voiceSpeed: number;
  autoSpeakAiResponses: boolean;
  transcriptionLanguage: string;
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

// Stage 7: Voice Intelligence Engine Types
export type VoiceConversationMode = 'push_to_talk' | 'voice_chat' | 'text_and_voice';

export interface VoiceInfo {
  id: string;
  name: string;
  language_code: string;
  gender?: string;
  provider: 'browser' | 'openai' | 'gemini';
}

export interface TextToSpeechResponse {
  audio_content?: string | null;
  content_type: string;
  clean_spoken_text: string;
  provider: string;
  voice_id: string;
  duration_estimate_seconds: number;
}

export interface AudioTranscriptionResponse {
  text: string;
  detected_language?: string;
  confidence?: number;
  provider: string;
  duration_seconds?: number;
}


// Stage 4: Document Intelligence Types
export type DocumentFormat = 'pdf' | 'docx' | 'txt' | 'csv' | 'xlsx' | 'png' | 'jpg' | 'jpeg' | 'webp';
export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'error';
export type DocumentAction =
  | 'ask'
  | 'summarize'
  | 'extract_key_points'
  | 'compare'
  | 'study_notes'
  | 'faq'
  | 'flashcards'
  | 'quiz'
  | 'explain_simply'
  | 'extract_tables';

export interface DocumentCitation {
  source_id: number;
  document_id: string;
  filename: string;
  page_number?: number;
  section?: string;
  snippet: string;
  relevance_score?: number;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  page_number?: number;
  section?: string;
  content: string;
  token_count: number;
}

export interface DocumentItem {
  id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  size_bytes: number;
  created_at: string;
  status: DocumentStatus;
  error_message?: string;
  page_count?: number;
  total_characters?: number;
  total_chunks?: number;
  metadata?: Record<string, any>;
}

export interface DocumentActionResponse {
  action: DocumentAction;
  document_ids: string[];
  result: string;
  citations: DocumentCitation[];
  provider: string;
  model: string;
}

// Stage 5: Fact-Checking & Evidence Verification Types
export type VerdictClassification =
  | 'supported'
  | 'contradicted'
  | 'mixed'
  | 'insufficient_evidence'
  | 'opinion_or_prediction';

export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'uncertain';

export interface EvidenceSource {
  source_id: number;
  title: string;
  url?: string;
  domain?: string;
  published_date?: string;
  snippet: string;
  stance: 'supporting' | 'opposing' | 'neutral' | 'context';
  is_primary: boolean;
}

export interface ClaimVerificationResult {
  claim_id: number;
  claim_text: string;
  verdict: VerdictClassification;
  confidence: ConfidenceLevel;
  explanation: string;
  supporting_evidence: EvidenceSource[];
  opposing_evidence: EvidenceSource[];
  missing_context_flags: string[];
}

export interface FactCheckResponse {
  input_text: string;
  extracted_claims_count: number;
  claims: ClaimVerificationResult[];
  overall_summary: string;
  sources_consulted: EvidenceSource[];
  provider: string;
  model: string;
  created_at: string;
}

// Stage 6: Universal Multilingual Intelligence Engine Types
export type TranslationTone = 'formal' | 'casual' | 'technical' | 'simplified';

export interface SentencePair {
  source_sentence: string;
  target_sentence: string;
  transliteration?: string;
}

export interface LanguageDetectionResult {
  detected_language: string;
  language_name: string;
  confidence: number;
  script?: string;
  is_code_switched: boolean;
  code_switch_types: string[];
  is_rtl: boolean;
}

export interface TranslationRequest {
  text: string;
  source_language?: string;
  target_language: string;
  tone?: TranslationTone;
  include_transliteration?: boolean;
  provider?: string;
  model?: string;
  client_api_key?: string;
}

export interface TranslationResponse {
  source_text: string;
  source_language: string;
  target_language: string;
  tone: TranslationTone;
  translated_text: string;
  sentence_pairs: SentencePair[];
  full_transliteration?: string;
  nuance_notes?: string;
  provider: string;
  model: string;
}

// Stage 8: Real-Time Intelligence Engine Types
export type LiveCategory = 'news' | 'tech' | 'research' | 'finance' | 'announcements' | 'weather' | 'general';

export interface LiveSourceItem {
  title: string;
  url: string;
  snippet: string;
  domain: string;
  published_date?: string;
  retrieved_at: string;
  source_freshness: 'fresh' | 'cached' | 'historical';
}

export interface MonitoredTopic {
  id: string;
  name: string;
  query_or_url: string;
  category: LiveCategory;
  check_interval_minutes: number;
  is_active: boolean;
  created_at: string;
  last_checked_at?: string;
  next_check_at?: string;
  last_content_hash?: string;
  change_count: number;
  latest_summary?: string;
}

export interface LiveNotification {
  id: string;
  topic_id: string;
  topic_name: string;
  title: string;
  summary_diff: string;
  detected_at: string;
  source_urls: string[];
  is_read: boolean;
}

export interface LiveQueryRequest {
  query: string;
  category?: LiveCategory;
  force_refresh?: boolean;
  max_sources?: number;
  search_engine?: string;
  client_search_key?: string;
}

export interface LiveQueryResponse {
  query: string;
  category: LiveCategory;
  is_fresh_retrieval: boolean;
  retrieved_at: string;
  freshness_label: string;
  sources: LiveSourceItem[];
  synthesized_answer: string;
  provider: string;
  model: string;
}

// Stage 9 Vision Interfaces
export interface ImageAttachmentMetadata {
  id: string;
  filename?: string;
  format: string;
  size_bytes: number;
  width: number;
  height: number;
  aspect_ratio: string;
  color_mode: string;
  has_text: boolean;
  ocr_preview?: string;
}

export type VisionAnalysisType = 'general' | 'ui_diagram' | 'charts_data' | 'technical_circuit' | 'ocr_extract' | 'comparison';

export interface VisionAnalyzeRequest {
  images: string[];
  prompt?: string;
  analysis_type?: VisionAnalysisType;
  provider?: string;
  model?: string;
  client_api_key?: string;
}

export interface VisionAnalyzeResponse {
  id: string;
  prompt: string;
  analysis: string;
  extracted_text?: string;
  image_metadata: ImageAttachmentMetadata[];
  model: string;
  provider: string;
  created_at: string;
}

export interface OCRRequest {
  image: string;
  filename?: string;
  language_hint?: string;
  quarantine_output?: boolean;
}

export interface OCRResponse {
  text: string;
  raw_character_count: number;
  word_count: number;
  metadata: ImageAttachmentMetadata;
  is_quarantined: boolean;
  confidence?: number;
  created_at: string;
}

export interface ImageCompareRequest {
  image1: string;
  image2: string;
  image1_label?: string;
  image2_label?: string;
  comparison_focus?: 'general' | 'ui_diff' | 'chart_comparison' | 'text_diff';
  provider?: string;
  model?: string;
  client_api_key?: string;
}

export interface ImageCompareResponse {
  id: string;
  comparison_summary: string;
  similarities: string[];
  differences: string[];
  metadata_image1: ImageAttachmentMetadata;
  metadata_image2: ImageAttachmentMetadata;
  model: string;
  provider: string;
  created_at: string;
}



