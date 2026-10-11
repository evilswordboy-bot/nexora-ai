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

// Stage 11: Advanced Reasoning Engine Interfaces
export type SubtaskStatus = 'PLANNED' | 'IN PROGRESS' | 'BLOCKED' | 'REVIEWING' | 'COMPLETE' | 'FAILED' | 'CANCELLED';
export type PlanStatus = 'PLANNED' | 'IN PROGRESS' | 'BLOCKED' | 'REVIEWING' | 'COMPLETE' | 'CANCELLED';
export type TaskComplexity = 'simple' | 'moderate' | 'complex';
export type RiskLevel = 'low' | 'medium' | 'high';

export interface ToolExecutionRecord {
  tool_name: string;
  inputs: Record<string, any>;
  output_summary: string;
  raw_output?: any;
  success: boolean;
  duration_ms: number;
  error?: string;
  untrusted_content_quarantined: boolean;
  attempt: number;
  executed_at: string;
}

export interface ReasoningSubtask {
  id: string;
  step_number: number;
  title: string;
  description: string;
  status: SubtaskStatus;
  depends_on: string[];
  expected_output: string;
  completion_criteria: string;
  tool_name?: string;
  tool_input: Record<string, any>;
  tool_executions: ToolExecutionRecord[];
  result_summary?: string;
  verification_passed?: boolean;
  verification_note?: string;
  requires_approval: boolean;
  approval_reason?: string;
  approval_granted?: boolean;
  retry_count: number;
  max_retries: number;
  error_message?: string;
}

export interface TaskClassification {
  complexity: TaskComplexity;
  requires_planning: boolean;
  required_tools: string[];
  uncertainty_level: 'low' | 'medium' | 'high';
  risk_level: RiskLevel;
  has_consequential_actions: boolean;
  consequential_action_details?: string;
  missing_information: string[];
  rationale: string;
}

export interface ReasoningPlan {
  id: string;
  query: string;
  classification: TaskClassification;
  status: PlanStatus;
  assumptions: string[];
  clarification_questions: string[];
  subtasks: ReasoningSubtask[];
  final_answer?: string;
  execution_summary?: string;
  uncertainty_notes: string[];
  total_tool_calls: number;
  revision_history: string[];
  provider: string;
  model: string;
  created_at: string;
  updated_at: string;
}

export interface ToolDefinitionItem {
  name: string;
  description: string;
  parameters_schema: Record<string, any>;
  enabled: boolean;
  stage_introduced: number;
  requires_approval: boolean;
  risk_level: string;
  timeout_seconds: number;
  treats_output_as_untrusted: boolean;
}

// Stage 12: Intelligent Model Routing Engine Interfaces
export type RoutingTaskCategory =
  | 'general_chat'
  | 'coding'
  | 'deep_research'
  | 'document_analysis'
  | 'image_understanding'
  | 'translation'
  | 'voice'
  | 'reasoning';

export type RoutingPreference = 'quality_first' | 'balanced' | 'speed_first';
export type ProviderAvailabilityStatus = 'available' | 'unconfigured' | 'degraded' | 'rate_limited' | 'outage';
export type ModelQualityTier = 'frontier' | 'balanced' | 'fast';

export interface ModelRegistryEntry {
  model_id: string;
  provider: string;
  display_name: string;
  supported_capabilities: RoutingTaskCategory[];
  context_window_tokens: number;
  max_output_tokens: number;
  pricing_per_1k_input_usd?: number | null;
  pricing_per_1k_output_usd?: number | null;
  pricing_note: string;
  quality_tier: ModelQualityTier;
  typical_latency_ms: number;
  timeout_seconds: number;
  configured: boolean;
  availability_status: ProviderAvailabilityStatus;
  is_default: boolean;
}

export interface TokenCostEstimate {
  estimated_prompt_tokens: number;
  estimated_completion_tokens: number;
  estimated_total_tokens: number;
  estimated_cost_usd?: number | null;
  is_exact_cost: boolean;
  pricing_available: boolean;
  cost_note: string;
}

export interface RoutingFallbackAttempt {
  provider: string;
  model_id: string;
  reason: string;
  error_code?: string;
  latency_ms: number;
}

export interface RoutingDecision {
  id: string;
  task_category: RoutingTaskCategory;
  required_capabilities: RoutingTaskCategory[];
  routing_preference: RoutingPreference;
  selected_provider: string;
  selected_model: string;
  selection_rationale: string;
  fallback_chain: string[];
  fallback_attempts: RoutingFallbackAttempt[];
  used_fallback: boolean;
  is_configured: boolean;
  cost_estimate: TokenCostEstimate;
  budget_allowed: boolean;
  budget_warning?: string;
  security_policy_enforced: boolean;
  prompt_injection_override_blocked: boolean;
  decided_at: string;
}

export interface RoutingPolicyConfig {
  routing_preference: RoutingPreference;
  default_provider: string;
  default_model: string;
  max_fallbacks: number;
  daily_spending_limit_usd: number;
  per_request_max_cost_usd: number;
  timeout_seconds: number;
  allow_paid_frontier_models: boolean;
}

export interface RoutingTelemetryEntry {
  id: string;
  task_category: RoutingTaskCategory;
  routing_preference: RoutingPreference;
  selected_provider: string;
  selected_model: string;
  used_fallback: boolean;
  fallback_count: number;
  success: boolean;
  error_category?: string;
  latency_ms: number;
  estimated_tokens: number;
  estimated_cost_usd: number;
  timestamp: string;
}

export interface RoutingUsageSummary {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  fallback_triggered_count: number;
  total_estimated_tokens: number;
  total_estimated_cost_usd: number;
  daily_spending_limit_usd: number;
  remaining_daily_budget_usd: number;
  average_latency_ms: number;
  by_provider: Record<string, number>;
  by_category: Record<string, number>;
  by_model: Record<string, number>;
  recent_telemetry: RoutingTelemetryEntry[];
  disclaimer: string;
}

export interface RoutingExecuteResponse {
  decision: RoutingDecision;
  response: {
    id: string;
    role: string;
    content: string;
    model: string;
    provider: string;
    finish_reason?: string;
  };
  latency_ms: number;
}

// Stage 13: Persistent Memory Engine Interfaces
export type MemoryCategory =
  | 'preferences'
  | 'profile'
  | 'project_context'
  | 'conversation_summaries'
  | 'temporary_context';

export interface MemoryItem {
  id: string;
  user_id: string;
  category: MemoryCategory;
  key: string;
  content: string;
  tags: string[];
  pinned: boolean;
  is_temporary: boolean;
  encrypted_at_rest: boolean;
  source: string;
  relevance_score?: number | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryPrivacySettings {
  user_id: string;
  memory_enabled: boolean;
  temporary_chat_mode: boolean;
  auto_summarize_conversations: boolean;
  encrypt_at_rest: boolean;
  block_sensitive_pii: boolean;
}

export interface MemoryStatusSummary {
  user_id: string;
  storage_backend: string;
  db_healthy: boolean;
  schema_version: number;
  settings: MemoryPrivacySettings;
  total_persistent_memories: number;
  total_temporary_memories: number;
  pinned_count: number;
  by_category: Record<string, number>;
  external_provider_disclosure: string;
}

export interface MemorySearchResponse {
  user_id: string;
  query: string;
  total_matched: number;
  total_count: number;
  memories: MemoryItem[];
  memory_enabled: boolean;
  storage_backend: string;
  external_provider_disclosure: string;
}

export interface MemoryCommandResponse {
  action_taken:
    | 'saved'
    | 'deleted'
    | 'listed'
    | 'confirmation_required'
    | 'rejected_sensitive'
    | 'memory_disabled_or_temp'
    | 'no_command_detected';
  message: string;
  affected_memories: MemoryItem[];
  requires_confirmation: boolean;
  pending_candidate?: Record<string, any> | null;
}

// Stage 14: Multi-Agent Intelligence System Interfaces
export type AgentRoleId =
  | 'research_agent'
  | 'coding_agent'
  | 'education_agent'
  | 'writing_agent'
  | 'data_analyst_agent'
  | 'productivity_agent'
  | 'document_agent'
  | 'language_agent';

export type AgentPermissionScope =
  | 'read_only'
  | 'search_and_retrieve'
  | 'document_read'
  | 'workspace_write_requires_approval';

export type AgentTaskStatus =
  | 'PLANNED'
  | 'RUNNING'
  | 'WAITING_APPROVAL'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export interface SpecializedAgentSpec {
  agent_id: AgentRoleId;
  name: string;
  purpose: string;
  capabilities: string[];
  limitations: string[];
  permission_scope: AgentPermissionScope;
  allowed_tools: string[];
  requires_approval_for: string[];
  preferred_task_category: RoutingTaskCategory;
  available: boolean;
  unavailable_reason?: string | null;
}

export interface AgentStructuredFinding {
  facts: string[];
  assumptions: string[];
  unresolved_questions: string[];
  citations: { title: string; url: string; snippet?: string }[];
  file_references: string[];
}

export interface AgentSubtaskRun {
  subtask_id: string;
  agent_id: AgentRoleId;
  agent_name: string;
  title: string;
  instruction: string;
  depends_on: string[];
  can_run_parallel: boolean;
  status: AgentTaskStatus;
  requires_approval: boolean;
  approval_reason?: string | null;
  approved?: boolean | null;
  tools_invoked: string[];
  output_summary: string;
  structured_finding: AgentStructuredFinding;
  error_message?: string | null;
  retry_count: number;
  estimated_cost_usd: number;
  latency_ms: number;
}

export interface MultiAgentOrchestrationRun {
  run_id: string;
  user_id: string;
  goal: string;
  selection_mode: 'auto' | 'manual';
  selected_agents: AgentRoleId[];
  execution_mode: 'sequential' | 'parallel_safe' | 'hybrid';
  status: AgentTaskStatus;
  plan_summary: string;
  subtasks: AgentSubtaskRun[];
  combined_response: string;
  consolidated_facts: string[];
  consolidated_assumptions: string[];
  unresolved_questions: string[];
  conflicts_detected: string[];
  citations: { title: string; url: string; snippet?: string }[];
  file_references: string[];
  used_memories: Record<string, any>[];
  duplicate_tool_calls_prevented: number;
  total_estimated_cost_usd: number;
  max_cost_budget_usd: number;
  total_latency_ms: number;
  created_at: string;
  updated_at: string;
}

// Stage 15: Workflow Automation Engine Interfaces
export type WorkflowStatus = 'DRAFT' | 'ACTIVE' | 'PAUSED' | 'DISABLED';
export type WorkflowTriggerType = 'manual' | 'scheduled';
export type WorkflowRecurrenceType = 'once' | 'interval' | 'hourly' | 'daily' | 'weekly';
export type WorkflowRunStatus =
  | 'QUEUED'
  | 'RUNNING'
  | 'WAITING_FOR_APPROVAL'
  | 'SUCCEEDED'
  | 'FAILED'
  | 'CANCELLED'
  | 'RETRYING';
export type WorkflowStepStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'WAITING_FOR_APPROVAL'
  | 'SUCCEEDED'
  | 'FAILED'
  | 'SKIPPED'
  | 'CANCELLED'
  | 'RETRYING';
export type WorkflowStepActionType = 'agent' | 'tool' | 'condition_gate' | 'transform';
export type WorkflowBranchAction = 'skip' | 'fail_workflow' | 'jump_to_step';

export interface WorkflowScheduleConfig {
  trigger_type: WorkflowTriggerType;
  recurrence: WorkflowRecurrenceType;
  interval_minutes: number;
  timezone: string;
  start_at?: string | null;
  next_run_at?: string | null;
  last_run_at?: string | null;
  allow_concurrent_runs: boolean;
}

export interface WorkflowStepDefinition {
  step_id: string;
  name: string;
  description: string;
  action_type: WorkflowStepActionType;
  agent_id?: AgentRoleId | null;
  tool_name?: string | null;
  prompt_template: string;
  tool_params: Record<string, any>;
  input_mapping: Record<string, string>;
  output_key: string;
  depends_on: string[];
  condition_expression: string;
  on_condition_false: WorkflowBranchAction;
  jump_to_step_id?: string | null;
  max_retries: number;
  retry_delay_seconds: number;
  timeout_seconds: number;
  requires_approval: boolean;
  approval_reason?: string | null;
}

export interface WorkflowNotificationConfig {
  in_app_enabled: boolean;
  email_opt_in: boolean;
  email_recipient?: string | null;
  webhook_opt_in: boolean;
  notify_on_complete: boolean;
  notify_on_failure: boolean;
  notify_on_approval_required: boolean;
}

export interface WorkflowDefinition {
  workflow_id: string;
  user_id: string;
  name: string;
  description: string;
  category: string;
  status: WorkflowStatus;
  is_template: boolean;
  schedule: WorkflowScheduleConfig;
  steps: WorkflowStepDefinition[];
  notification_config: WorkflowNotificationConfig;
  max_cost_budget_usd: number;
  total_runs: number;
  succeeded_runs: number;
  failed_runs: number;
  last_run_status?: WorkflowRunStatus | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowValidationIssue {
  severity: 'error' | 'warning';
  step_id?: string | null;
  code: string;
  message: string;
}

export interface WorkflowValidationResult {
  valid: boolean;
  issues: WorkflowValidationIssue[];
  execution_order: string[];
  estimated_max_cost_usd: number;
  requires_approval_steps: string[];
}

export interface WorkflowStepExecutionResult {
  step_id: string;
  step_name: string;
  action_type: WorkflowStepActionType;
  agent_id?: AgentRoleId | null;
  tool_name?: string | null;
  status: WorkflowStepStatus;
  resolved_inputs: Record<string, any>;
  output_summary: string;
  output_data: Record<string, any>;
  untrusted_content_isolated: boolean;
  condition_evaluated: boolean;
  condition_detail: string;
  requires_approval: boolean;
  approval_reason?: string | null;
  approved?: boolean | null;
  attempt_count: number;
  max_retries: number;
  error_message?: string | null;
  estimated_cost_usd: number;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms: number;
}

export interface WorkflowExecutionRun {
  run_id: string;
  workflow_id: string;
  workflow_name: string;
  user_id: string;
  trigger_source: 'manual' | 'scheduled' | 'test_dry_run' | 'retry';
  idempotency_key?: string | null;
  status: WorkflowRunStatus;
  is_dry_run: boolean;
  runtime_inputs: Record<string, any>;
  step_results: WorkflowStepExecutionResult[];
  completed_steps: number;
  total_steps: number;
  progress_percent: number;
  current_step_id?: string | null;
  waiting_approval_step_id?: string | null;
  final_summary: string;
  error_message?: string | null;
  total_estimated_cost_usd: number;
  max_cost_budget_usd: number;
  queued_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms: number;
}

export interface WorkflowNotificationItem {
  notification_id: string;
  user_id: string;
  workflow_id: string;
  workflow_name: string;
  run_id?: string | null;
  event_type:
    | 'run_succeeded'
    | 'run_failed'
    | 'approval_required'
    | 'schedule_triggered'
    | 'run_cancelled'
    | 'worker_recovery';
  severity: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  read: boolean;
  external_channels_attempted: string[];
  external_delivery_status: string;
  external_delivery_confirmed: boolean;
  created_at: string;
}

export interface WorkflowMetadataResponse {
  available_agents: SpecializedAgentSpec[];
  available_tools: ToolDefinitionItem[];
  supported_timezones: string[];
  notification_channels: {
    in_app: boolean;
    webhook_configured: boolean;
    smtp_configured: boolean;
  };
  limits: {
    max_steps: number;
    max_step_retries: number;
    step_timeout_seconds: number;
    max_cost_usd_per_run: number;
    rate_limit_per_minute: number;
  };
}

// Stage 16: Computer Control & Digital Execution Engine Interfaces
export type ComputerTargetDomain = 'browser' | 'local_os';

export type ComputerActionType =
  | 'open_url'
  | 'navigate'
  | 'click'
  | 'fill_text'
  | 'select_option'
  | 'scroll'
  | 'capture_screenshot'
  | 'extract_content'
  | 'submit_form'
  | 'list_workspace_files'
  | 'read_workspace_file'
  | 'write_workspace_file'
  | 'delete_workspace_file'
  | 'run_predefined_diagnostic'
  | 'open_approved_application';

export type ComputerSessionStatus =
  | 'PLANNED'
  | 'SIMULATION_PREVIEW'
  | 'WAITING_FOR_APPROVAL'
  | 'RUNNING'
  | 'PAUSED'
  | 'VERIFIED_COMPLETED'
  | 'BLOCKED_BY_SECURITY_BOUNDARY'
  | 'FAILED'
  | 'CANCELLED';

export type ComputerStepStatus =
  | 'PENDING'
  | 'SIMULATED'
  | 'WAITING_FOR_APPROVAL'
  | 'RUNNING'
  | 'VERIFIED_SUCCEEDED'
  | 'BLOCKED'
  | 'FAILED'
  | 'CANCELLED';

export interface ComputerActionPreview {
  step_id: string;
  action_type: ComputerActionType;
  target_domain: ComputerTargetDomain;
  target_resource: string;
  risk_level: 'low' | 'medium' | 'high';
  requires_approval: boolean;
  approval_reason?: string | null;
  parameters_preview: Record<string, any>;
}

export interface ComputerActionStep {
  step_id: string;
  title: string;
  target_domain: ComputerTargetDomain;
  action_type: ComputerActionType;
  target_url_or_path: string;
  selector?: string | null;
  input_value?: string | null;
  params: Record<string, any>;
  requires_approval: boolean;
  approval_reason?: string | null;
  checkpoint_name?: string | null;
  timeout_seconds: number;
}

export interface ComputerStepResult {
  step_id: string;
  title: string;
  target_domain: ComputerTargetDomain;
  action_type: ComputerActionType;
  target_url_or_path: string;
  selector?: string | null;
  status: ComputerStepStatus;
  requires_approval: boolean;
  approval_reason?: string | null;
  approved?: boolean | null;
  preview?: ComputerActionPreview | null;
  verified: boolean;
  verification_detail: string;
  output_summary: string;
  extracted_data: Record<string, any>;
  screenshot_base64?: string | null;
  page_title?: string | null;
  current_url?: string | null;
  security_boundary_triggered?: string | null;
  untrusted_content_isolated: boolean;
  error_message?: string | null;
  duration_ms: number;
  executed_at?: string | null;
}

export interface ComputerExecutionSession {
  session_id: string;
  user_id: string;
  goal: string;
  mode: 'execute' | 'simulate_only';
  target_domain: ComputerTargetDomain;
  browser_driver: string;
  status: ComputerSessionStatus;
  target_website?: string | null;
  active_step_id?: string | null;
  waiting_approval_step_id?: string | null;
  steps: ComputerActionStep[];
  step_results: ComputerStepResult[];
  checkpoints: string[];
  latest_screenshot_base64?: string | null;
  execution_logs: string[];
  final_summary: string;
  verified_completion: boolean;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ComputerAuditLogEntry {
  audit_id: string;
  session_id: string;
  user_id: string;
  step_id?: string | null;
  target_domain: ComputerTargetDomain;
  action_type: string;
  target_resource: string;
  status: string;
  verified: boolean;
  detail: string;
  created_at: string;
}

export interface ComputerCapabilitiesResponse {
  stage: number;
  playwright_package_detected: boolean;
  active_browser_driver: string;
  browser_capabilities: string[];
  local_os_runner_enabled: boolean;
  local_os_capabilities: string[];
  workspace_sandbox_dir: string;
  approved_applications: Record<string, string>;
  predefined_diagnostics: Record<string, string>;
  allowed_domains_default: string[];
  strict_url_allowlist_default: boolean;
  architecture_disclosure: string;
}

// Stage 17: File Management & Workspace Automation Engine Interfaces
export type FileCategory =
  | 'document'
  | 'spreadsheet'
  | 'data'
  | 'markdown_text'
  | 'code'
  | 'image'
  | 'folder'
  | 'other';

export type FileOperationType =
  | 'create_folder'
  | 'create_file'
  | 'edit_file'
  | 'rename_item'
  | 'copy_item'
  | 'move_item'
  | 'convert_file'
  | 'delete_to_trash'
  | 'restore_from_trash'
  | 'restore_version'
  | 'organize_workspace'
  | 'cleanup_duplicates'
  | 'sync_stage4_vault'
  | 'import_browser_session';

export type FileOperationStatus =
  | 'PLANNED'
  | 'SIMULATED'
  | 'WAITING_FOR_APPROVAL'
  | 'RUNNING'
  | 'VERIFIED_SUCCEEDED'
  | 'ROLLED_BACK'
  | 'FAILED'
  | 'CANCELLED';

export type OrganizeRuleStrategy =
  | 'by_category'
  | 'by_extension'
  | 'by_date_month'
  | 'custom_rules';

export interface WorkspaceFileItem {
  relative_path: string;
  name: string;
  parent_dir: string;
  is_dir: boolean;
  extension: string;
  category: FileCategory;
  size_bytes: number;
  sha256_hash?: string | null;
  modified_at: string;
  is_editable_text: boolean;
  is_processable_document: boolean;
  supported_conversions: string[];
  version_count: number;
  indexed_doc_id?: string | null;
  snippet_match?: string | null;
}

export interface WorkspaceFileVersion {
  version_id: string;
  user_id: string;
  relative_path: string;
  version_number: number;
  sha256_hash: string;
  size_bytes: number;
  reason: string;
  created_at: string;
}

export interface WorkspaceFileReadResponse {
  item: WorkspaceFileItem;
  content: string;
  quarantined_content: string;
  untrusted_content_isolated: boolean;
  parsed_summary?: Record<string, any> | null;
  tables_preview: Record<string, any>[];
  versions: WorkspaceFileVersion[];
}

export interface WorkspaceTrashItem {
  trash_id: string;
  user_id: string;
  original_path: string;
  name: string;
  is_dir: boolean;
  size_bytes: number;
  sha256_hash?: string | null;
  reason: string;
  deleted_at: string;
}

export interface DuplicateFileGroup {
  sha256_hash: string;
  size_bytes: number;
  duplicate_count: number;
  wasted_bytes: number;
  primary_file: string;
  duplicate_files: string[];
}

export interface FilePlannedChange {
  action: string;
  source_path: string;
  destination_path?: string | null;
  size_bytes: number;
  reason: string;
  overwrites_existing: boolean;
}

export interface FileOperationPreview {
  operation_type: FileOperationType;
  risk_level: 'low' | 'medium' | 'high';
  requires_approval: boolean;
  approval_reason?: string | null;
  affected_count: number;
  total_bytes_affected: number;
  planned_changes: FilePlannedChange[];
  rollback_supported: boolean;
}

export interface FileOperationRecord {
  operation_id: string;
  user_id: string;
  operation_type: FileOperationType;
  status: FileOperationStatus;
  summary: string;
  verified: boolean;
  verification_detail: string;
  requires_approval: boolean;
  approval_reason?: string | null;
  approved?: boolean | null;
  preview?: FileOperationPreview | null;
  affected_paths: string[];
  result_data: Record<string, any>;
  rollback_supported: boolean;
  rolled_back: boolean;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface FileWorkspaceCapabilitiesResponse {
  stage: number;
  engine: string;
  authorized_workspace_root: string;
  workspace_exists: boolean;
  max_file_size_bytes: number;
  max_bulk_files: number;
  bulk_approval_threshold: number;
  allowed_extensions: string[];
  editable_text_extensions: string[];
  processable_document_extensions: string[];
  trash_count: number;
  recent_operations_count: number;
  security_boundaries: string[];
}



