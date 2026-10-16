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

// ============================================================================
// Stage 18: Terminal & Code Execution Engine Types
// ============================================================================

export type CodeLanguage =
  | 'python'
  | 'javascript'
  | 'typescript'
  | 'html'
  | 'css'
  | 'json'
  | 'markdown';

export type ProjectTemplateType = 'python' | 'javascript' | 'typescript' | 'web';

export type TerminalExecutionStatus =
  | 'PLANNED'
  | 'WAITING_FOR_APPROVAL'
  | 'RUNNING'
  | 'SUCCEEDED'
  | 'FAILED'
  | 'TIMED_OUT'
  | 'BLOCKED'
  | 'CANCELLED';

export type CommandRiskClassification =
  | 'allowed_safe'
  | 'requires_approval'
  | 'blocked_forbidden';

export interface CodeProjectFile {
  relative_path: string;
  name: string;
  language: CodeLanguage;
  size_bytes: number;
  sha256_hash: string;
  modified_at: string;
  backup_count: number;
  content?: string | null;
}

export interface CodeFileBackup {
  backup_id: string;
  user_id: string;
  project_id: string;
  relative_path: string;
  version_number: number;
  sha256_hash: string;
  size_bytes: number;
  reason: string;
  created_at: string;
}

export interface CodeProjectSummary {
  project_id: string;
  user_id: string;
  name: string;
  description: string;
  template: ProjectTemplateType;
  primary_language: CodeLanguage;
  entrypoint: string;
  test_entrypoint: string;
  file_count: number;
  created_at: string;
  updated_at: string;
  files: CodeProjectFile[];
}

export interface CodeDiagnosticIssue {
  line: number;
  column: number;
  severity: 'error' | 'warning' | 'info';
  code: string;
  message: string;
  rule_source: string;
  suggestion?: string | null;
}

export interface DependencyStatusItem {
  package_name: string;
  ecosystem: 'pip' | 'npm' | 'builtin';
  installed: boolean;
  version?: string | null;
  imported_in: string[];
  install_command?: string | null;
  setup_explanation: string;
}

export interface CodeInspectionResult {
  project_id: string;
  relative_path: string;
  language: CodeLanguage;
  syntax_valid: boolean;
  formatted_content?: string | null;
  formatting_changed: boolean;
  diagnostics: CodeDiagnosticIssue[];
  dependencies: DependencyStatusItem[];
  missing_dependencies_count: number;
  untrusted_instruction_warnings: string[];
  summary: string;
}

export interface TestCaseResult {
  name: string;
  status: 'passed' | 'failed' | 'error' | 'skipped';
  duration_ms: number;
  message?: string | null;
}

export interface TestSuiteResult {
  framework: string;
  executed: boolean;
  passed: number;
  failed: number;
  errors: number;
  skipped: number;
  total: number;
  all_passed: boolean;
  cases: TestCaseResult[];
  raw_summary: string;
}

export interface CommandPreview {
  raw_command: string;
  normalized_command: string;
  classification: CommandRiskClassification;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  target_workspace: string;
  expected_effect: string;
  requires_approval: boolean;
  approval_reason?: string | null;
  blocked_reason?: string | null;
}

export interface TerminalExecutionRecord {
  execution_id: string;
  user_id: string;
  project_id: string;
  execution_type:
    | 'run_code'
    | 'run_tests'
    | 'terminal_command'
    | 'syntax_check'
    | 'debug_repair';
  command_preview: CommandPreview;
  status: TerminalExecutionStatus;
  exit_code?: number | null;
  stdout: string;
  stderr: string;
  output_truncated: boolean;
  timed_out: boolean;
  duration_ms: number;
  memory_limit_mb: number;
  network_enabled: boolean;
  verified_execution: boolean;
  approved?: boolean | null;
  test_results?: TestSuiteResult | null;
  error_diagnosis?: string | null;
  suggested_fix?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface RepairIterationStep {
  attempt_number: number;
  failure_type: string;
  diagnosis: string;
  proposed_patch_summary: string;
  backup_id?: string | null;
  applied: boolean;
  execution_id?: string | null;
  exit_code?: number | null;
  tests_passed: boolean;
  stdout_excerpt: string;
  stderr_excerpt: string;
}

export interface DebugRepairResponse {
  repair_id: string;
  user_id: string;
  project_id: string;
  target_file: string;
  initial_error: string;
  status:
    | 'REPAIRED_AND_VERIFIED'
    | 'MAX_ATTEMPTS_REACHED'
    | 'REQUIRES_USER_INTERVENTION'
    | 'NO_FAILURE_DETECTED';
  attempts_used: number;
  max_attempts: number;
  final_verified: boolean;
  intervention_reason?: string | null;
  explanation: string;
  iterations: RepairIterationStep[];
  final_execution?: TerminalExecutionRecord | null;
}

export interface TerminalCapabilitiesResponse {
  stage: number;
  engine: string;
  sandbox_mode: string;
  supported_languages: string[];
  runtimes: {
    python: {
      available: boolean;
      version: string;
      executable: string;
      pytest_available: boolean;
      unittest_available: boolean;
    };
    node: {
      available: boolean;
      executable?: string | null;
    };
    git: {
      available: boolean;
    };
  };
  limits: {
    execution_timeout_seconds: number;
    max_output_bytes: number;
    max_memory_mb: number;
    max_processes: number;
    max_concurrent_runs_per_user: number;
    max_repair_attempts: number;
    default_allow_network: boolean;
  };
  allowlisted_commands: string[];
  approval_required_operations: string[];
}

// ============================================================================
// Stage 19: Git & Version Control Engine Types
// ============================================================================

export type GitOperationType =
  | 'init_repo'
  | 'stage_files'
  | 'unstage_files'
  | 'commit'
  | 'create_branch'
  | 'switch_branch'
  | 'merge_branch'
  | 'configure_remote'
  | 'sync_remote'
  | 'discard_changes'
  | 'update_gitignore'
  | 'create_pull_request';

export type GitOperationStatus =
  | 'PLANNED'
  | 'WAITING_FOR_APPROVAL'
  | 'SUCCEEDED'
  | 'FAILED'
  | 'BLOCKED'
  | 'CANCELLED';

export type GitRemoteProvider = 'github' | 'gitlab' | 'bitbucket' | 'custom';

export interface GitChangedFile {
  path: string;
  index_status: string;
  worktree_status: string;
  staged: boolean;
  unstaged: boolean;
  untracked: boolean;
  has_secret_warning: boolean;
  secret_warning_detail?: string | null;
  is_sensitive_env_file: boolean;
}

export interface GitBranchInfo {
  name: string;
  is_current: boolean;
  commit_hash: string;
  last_commit_subject: string;
}

export interface GitCommitEntry {
  commit_hash: string;
  short_hash: string;
  author_name: string;
  author_email: string;
  authored_at: string;
  subject: string;
  body: string;
  files_changed: number;
}

export interface GitRemoteConfig {
  name: string;
  url: string;
  provider: GitRemoteProvider;
  token_configured: boolean;
  sync_status:
    | 'not_configured'
    | 'local_only'
    | 'auth_required'
    | 'network_disabled'
    | 'ready_to_sync'
    | 'synced'
    | 'sync_failed';
  ahead_count: number;
  behind_count: number;
  last_error?: string | null;
}

export interface GitSideBySideLine {
  left_line_no?: number | null;
  left_content: string;
  right_line_no?: number | null;
  right_content: string;
  change_type: 'context' | 'add' | 'delete' | 'modify';
}

export interface GitFileDiff {
  file_path: string;
  additions: number;
  deletions: number;
  is_binary: boolean;
  unified_patch: string;
  side_by_side_lines: GitSideBySideLine[];
}

export interface GitDiffResponse {
  project_id: string;
  target_scope: 'unstaged' | 'staged' | 'all_working' | 'branch_compare' | 'commit';
  base_ref?: string | null;
  compare_ref?: string | null;
  total_files_changed: number;
  total_additions: number;
  total_deletions: number;
  unified_diff: string;
  files: GitFileDiff[];
  secret_warnings: string[];
}

export interface GitRepositoryStatusResponse {
  project_id: string;
  user_id: string;
  git_installed: boolean;
  is_initialized: boolean;
  current_branch: string;
  is_clean: boolean;
  branches: GitBranchInfo[];
  changed_files: GitChangedFile[];
  staged_count: number;
  unstaged_count: number;
  untracked_count: number;
  secret_warnings: string[];
  recommended_gitignore_entries: string[];
  gitignore_present: boolean;
  remotes: GitRemoteConfig[];
  recent_commits: GitCommitEntry[];
}

export interface GitCodeReviewFinding {
  finding_id: string;
  file_path: string;
  line_number: number;
  category: 'bug' | 'security' | 'readability' | 'missing_tests';
  severity: 'critical' | 'high' | 'medium' | 'low';
  finding_type: 'verified_defect' | 'possible_concern';
  title: string;
  description: string;
  suggested_fix: string;
  auto_accepted: boolean;
}

export interface GitCodeReviewResponse {
  review_id: string;
  project_id: string;
  user_id: string;
  reviewed_files: string[];
  verified_defects_count: number;
  possible_concerns_count: number;
  tests_executed: boolean;
  tests_passed?: boolean | null;
  findings: GitCodeReviewFinding[];
  summary: string;
  created_at: string;
}

export interface GitBranchComparisonResponse {
  project_id: string;
  base_branch: string;
  compare_branch: string;
  ahead_count: number;
  behind_count: number;
  can_fast_forward: boolean;
  has_conflicts: boolean;
  conflict_files: string[];
  commits: GitCommitEntry[];
  diff: GitDiffResponse;
}

export interface GitPullRequestRecord {
  pr_id: string;
  user_id: string;
  project_id: string;
  title: string;
  description: string;
  source_branch: string;
  target_branch: string;
  issue_references: string[];
  review_summary: string;
  provider: GitRemoteProvider;
  status: 'LOCAL_DRAFT_ONLY' | 'WAITING_FOR_APPROVAL' | 'REMOTE_CONFIRMED' | 'REMOTE_FAILED';
  local_draft_only: boolean;
  remote_confirmed: boolean;
  remote_url?: string | null;
  provider_message: string;
  created_at: string;
}

export interface GitOperationRecord {
  operation_id: string;
  user_id: string;
  project_id: string;
  operation_type: GitOperationType;
  status: GitOperationStatus;
  command_display: string;
  requires_approval: boolean;
  approval_reason?: string | null;
  approved?: boolean | null;
  verified: boolean;
  stdout: string;
  stderr: string;
  diff_preview?: string | null;
  secret_warnings: string[];
  error_message?: string | null;
  result_data: Record<string, any>;
  created_at: string;
  completed_at?: string | null;
}

export interface GitCapabilitiesResponse {
  stage: number;
  engine: string;
  git_installed: boolean;
  git_version?: string | null;
  default_branch: string;
  supported_providers: GitRemoteProvider[];
  remote_token_configured: boolean;
  allowed_remote_hosts: string[];
  approval_required_operations: string[];
  recommended_gitignore_rules: string[];
}

// ==========================================
// Stage 20: AI Evaluation & Quality Assurance Engine Interfaces
// ==========================================

export type EvalSuiteId =
  | 'general_qa'
  | 'web_research'
  | 'fact_checking'
  | 'document_rag'
  | 'multilingual'
  | 'vision_ocr'
  | 'voice_speech'
  | 'coding_sandbox'
  | 'agents_tools_memory_workflows'
  | 'security_privacy_safety';

export type EvalRunStatus =
  | 'COMPLETED'
  | 'INCOMPLETE_INTERRUPTED'
  | 'FAILED_PROVIDER_ERROR';

export type EvalReleaseGateVerdict =
  | 'RELEASE_APPROVED'
  | 'RELEASE_BLOCKED_CRITICAL_FAILURE'
  | 'RELEASE_BLOCKED_REGRESSION'
  | 'INCOMPLETE_RUN';

export type EvalCaseSourceType = 'curated_benchmark' | 'synthetic_labeled';
export type EvalCaseReviewStatus = 'approved' | 'pending_review' | 'rejected';

export interface EvalMetricScoringRule {
  metric_id: string;
  name: string;
  range_display: string;
  scoring_method:
    | 'deterministic_assertion'
    | 'lexical_overlap'
    | 'schema_validation'
    | 'heuristic_rubric'
    | 'ai_judge_advisory'
    | 'telemetry_measurement';
  is_definitive_ground_truth: boolean;
  rule_description: string;
  limitations: string;
}

export interface EvalSuiteDefinition {
  suite_id: EvalSuiteId;
  name: string;
  stage_coverage: string;
  description: string;
  primary_metrics: string[];
  total_cases: number;
  approved_cases: number;
  critical_cases: number;
}

export interface EvalTestCase {
  case_id: string;
  suite_id: EvalSuiteId;
  title: string;
  description: string;
  input_payload: Record<string, any>;
  expected_criteria: Record<string, any>;
  scoring_rubric: string;
  is_edge_case: boolean;
  is_critical: boolean;
  known_limitations: string;
  source_type: EvalCaseSourceType;
  review_status: EvalCaseReviewStatus;
  dataset_version: string;
  created_by: string;
  created_at: string;
}

export interface EvalCaseExecutionResult {
  case_id: string;
  suite_id: EvalSuiteId;
  title: string;
  is_critical: boolean;
  is_edge_case: boolean;
  source_type: EvalCaseSourceType;
  passed: boolean;
  score: number;
  scoring_method: string;
  is_subjective_advisory: boolean;
  latency_ms: number;
  actual_output_excerpt: string;
  expected_summary: string;
  metrics_breakdown: Record<string, number | null>;
  unavailable_metrics: string[];
  error_detail?: string | null;
  prevented_side_effect: boolean;
}

export interface EvalAcceptanceThresholds {
  min_task_success_rate: number;
  min_safety_compliance_rate: number;
  max_error_rate: number;
  max_latency_regression_pct: number;
  block_on_critical_failure: boolean;
}

export interface EvalMetricSummary {
  task_success_rate: number;
  factual_support_score?: number | null;
  citation_validity_score?: number | null;
  extraction_accuracy_score?: number | null;
  language_quality_score?: number | null;
  tool_call_success_rate?: number | null;
  safety_compliance_rate?: number | null;
  error_rate: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  total_tokens?: number | null;
  estimated_cost_usd?: number | null;
  unavailable_metrics_notes: Record<string, string>;
}

export interface EvalRegressionAlert {
  metric_name: string;
  baseline_value: number;
  candidate_value: number;
  delta: number;
  severity: 'critical' | 'warning' | 'info';
  message: string;
}

export interface EvalRunRecord {
  run_id: string;
  label: string;
  dataset_version: string;
  status: EvalRunStatus;
  suites_selected: EvalSuiteId[];
  sample_size: number;
  completed_cases: number;
  passed_cases: number;
  failed_cases: number;
  critical_failures: number;
  model_configuration: Record<string, any>;
  isolated_environment_id: string;
  consequential_actions_blocked: boolean;
  metrics: EvalMetricSummary;
  thresholds: EvalAcceptanceThresholds;
  release_gate_verdict: EvalReleaseGateVerdict;
  release_gate_reasons: string[];
  baseline_run_id?: string | null;
  regression_alerts: EvalRegressionAlert[];
  case_results: EvalCaseExecutionResult[];
  created_at: string;
  completed_at?: string | null;
}

export interface EvalMetadataResponse {
  stage: number;
  engine: string;
  dataset_version: string;
  total_cases: number;
  approved_cases: number;
  exclude_private_conversations_by_default: boolean;
  consequential_side_effects_blocked: boolean;
  configured_providers: string[];
  default_thresholds: EvalAcceptanceThresholds;
  suites: EvalSuiteDefinition[];
  scoring_rules: EvalMetricScoringRule[];
}

// ============================================================================
// Stage 21: Universal Knowledge Discovery Engine Interfaces
// ============================================================================

export type DiscoverySourceType =
  | 'general_web'
  | 'academic_publications'
  | 'news_live'
  | 'public_datasets'
  | 'official_documentation'
  | 'authorized_knowledge_base';

export type DiscoverySearchMode =
  | 'quick'
  | 'comprehensive'
  | 'academic'
  | 'official'
  | 'exploration';

export type DiscoveryOriginalityTier =
  | 'original_primary_source'
  | 'peer_reviewed_or_preprint'
  | 'secondary_reporting'
  | 'syndicated_or_copied';

export interface DiscoveryConnectorSpec {
  connector_id: string;
  name: string;
  source_type: DiscoverySourceType;
  description: string;
  configured: boolean;
  status: 'operational' | 'degraded' | 'unavailable';
  supported_syntax: string[];
  supports_date_filter: boolean;
  supports_language_filter: boolean;
  requires_api_key: boolean;
  provider_notes: string;
}

export interface DiscoveryConnectorExecutionStatus {
  connector_id: string;
  name: string;
  source_type: DiscoverySourceType;
  status: 'succeeded' | 'unavailable' | 'error' | 'skipped';
  items_returned: number;
  latency_ms: number;
  error_message?: string | null;
}

export interface DiscoveryNormalizedItem {
  item_id: string;
  citation_index: number;
  title: string;
  url: string;
  canonical_url: string;
  domain: string;
  snippet: string;
  quarantined_snippet: string;
  source_type: DiscoverySourceType;
  connector_id: string;
  publication_date?: string | null;
  retrieval_timestamp: string;
  language: string;
  originality_tier: DiscoveryOriginalityTier;
  is_verified_scholarly: boolean;
  is_verified_official: boolean;
  authority_basis: string;
  relevance_score: number;
  recency_score: number;
  quality_score: number;
  combined_rank_score: number;
  is_stale: boolean;
  staleness_warning?: string | null;
  duplicate_count: number;
  merged_from_connectors: string[];
  authors_or_publisher?: string | null;
  doi_or_identifier?: string | null;
}

export interface DiscoveryTimelineEvent {
  date_label: string;
  title: string;
  summary: string;
  citation_indices: number[];
  source_urls: string[];
}

export interface DiscoverySourceComparisonRow {
  citation_index: number;
  title: string;
  domain: string;
  source_type: DiscoverySourceType;
  originality_tier: DiscoveryOriginalityTier;
  publication_date?: string | null;
  key_claim: string;
  agreement_status: 'corroborated' | 'unique_finding' | 'conflicting';
  authority_basis: string;
}

export interface DiscoveryConflictItem {
  topic: string;
  claim_a: string;
  citation_a: number;
  claim_b: string;
  citation_b: number;
  explanation: string;
}

export interface DiscoverySynthesisPayload {
  concise_summary: string;
  detailed_report: string;
  grouped_findings: Record<string, string[]>;
  timeline: DiscoveryTimelineEvent[];
  source_comparison: DiscoverySourceComparisonRow[];
  detected_conflicts: DiscoveryConflictItem[];
  evidence_gaps: string[];
}

export interface DiscoverySearchResponse {
  discovery_id: string;
  query: string;
  preserved_language: string;
  detected_language_name: string;
  mode: DiscoverySearchMode;
  query_intent: string;
  parsed_operators: Record<string, any>;
  expanded_subqueries: string[];
  connector_statuses: DiscoveryConnectorExecutionStatus[];
  total_raw_candidates: number;
  deduplicated_count: number;
  ssrf_blocked_count: number;
  page: number;
  page_size: number;
  total_filtered_results: number;
  total_pages: number;
  cache_hit: boolean;
  latency_ms: number;
  results: DiscoveryNormalizedItem[];
  follow_up_queries: string[];
  related_topics: string[];
  alternative_viewpoints: string[];
  synthesis: DiscoverySynthesisPayload;
  created_at: string;
}

export interface DiscoveryMetadataResponse {
  stage: number;
  engine: string;
  connectors: DiscoveryConnectorSpec[];
  modes: Array<{ id: string; name: string; description: string }>;
  supported_operators: string[];
  cache_ttl_seconds: number;
  stale_days_threshold: number;
}

// ============================================================================
// Stage 22: Knowledge Graph Intelligence Engine Types
// ============================================================================

export type KGEntityType =
  | 'concept'
  | 'technology'
  | 'organization'
  | 'person'
  | 'event'
  | 'dataset'
  | 'component'
  | 'claim_or_standard';

export type KGRelationType =
  | 'depends_on'
  | 'created_by'
  | 'related_to'
  | 'part_of'
  | 'contradicts'
  | 'supports'
  | 'uses'
  | 'evaluates'
  | 'governed_by';

export type KGFactBasis = 'explicit_fact' | 'ai_inferred';

export type KGUncertaintyLabel =
  | 'verified_explicit'
  | 'hedged_source_statement'
  | 'inferred_transitive'
  | 'inferred_low_confidence';

export type KGSourceKind =
  | 'user_document'
  | 'vault_document'
  | 'discovery_result'
  | 'inferred_transitivity';

export type KGQueryMode =
  | 'natural_language'
  | 'connection_path'
  | 'dependency_impact'
  | 'contradiction_analysis'
  | 'neighborhood_exploration';

export interface KGEvidenceItem {
  evidence_id: string;
  source_kind: KGSourceKind;
  source_id: string;
  source_title: string;
  source_url?: string | null;
  page_or_section?: string | null;
  passage: string;
  quarantined_passage: string;
  stance: 'supporting' | 'contradicting' | 'neutral';
  extracted_at: string;
}

export interface KGEntityNode {
  entity_id: string;
  user_id: string;
  workspace_id: string;
  canonical_key: string;
  label: string;
  entity_type: KGEntityType;
  aliases: string[];
  description: string;
  properties: Record<string, any>;
  provenance: KGEvidenceItem[];
  confidence: number;
  degree: number;
  created_at: string;
  updated_at: string;
}

export interface KGRelationshipEdge {
  relationship_id: string;
  user_id: string;
  workspace_id: string;
  source_entity_id: string;
  source_label: string;
  target_entity_id: string;
  target_label: string;
  relation_type: KGRelationType;
  fact_basis: KGFactBasis;
  is_inferred: boolean;
  uncertainty_label: KGUncertaintyLabel;
  confidence: number;
  explanation: string;
  evidence: KGEvidenceItem[];
  created_at: string;
  updated_at: string;
}

export interface KGChangeLogEntry {
  change_id: string;
  user_id: string;
  workspace_id: string;
  action_type: 'ingest_merge' | 'entity_merge_approved' | 'delete_approved' | 'seed_sample';
  summary: string;
  affected_entity_ids: string[];
  affected_relationship_ids: string[];
  created_at: string;
}

export interface KGIngestResponse {
  user_id: string;
  workspace_id: string;
  entities_created: number;
  entities_updated: number;
  relationships_created: number;
  relationships_updated: number;
  inferred_relationships_created: number;
  prompt_injection_neutralized_count: number;
  ssrf_blocked_urls_count: number;
  entities: KGEntityNode[];
  relationships: KGRelationshipEdge[];
  change_log: KGChangeLogEntry;
  summary: string;
}

export interface KGGraphSnapshotResponse {
  user_id: string;
  workspace_id: string;
  total_nodes_in_workspace: number;
  total_edges_in_workspace: number;
  returned_nodes_count: number;
  returned_edges_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_more: boolean;
  nodes: KGEntityNode[];
  edges: KGRelationshipEdge[];
}

export interface KGPathStep {
  step_index: number;
  relationship_id: string;
  source_entity_id: string;
  source_label: string;
  relation_type: KGRelationType;
  target_entity_id: string;
  target_label: string;
  fact_basis: KGFactBasis;
  is_inferred: boolean;
  uncertainty_label: KGUncertaintyLabel;
  confidence: number;
  evidence: KGEvidenceItem[];
}

export interface KGContradictionItem {
  subject_label: string;
  target_label: string;
  supporting_edge?: KGRelationshipEdge | null;
  contradicting_edge: KGRelationshipEdge;
  supporting_sources: string[];
  contradicting_sources: string[];
  explanation: string;
}

export interface KGQueryResponse {
  query_id: string;
  user_id: string;
  workspace_id: string;
  mode_executed: KGQueryMode;
  question: string;
  answer_summary: string;
  paths: KGPathStep[][];
  dependent_entities: KGEntityNode[];
  contradictions: KGContradictionItem[];
  subgraph_nodes: KGEntityNode[];
  subgraph_edges: KGRelationshipEdge[];
  cycles_detected: number;
  explicit_facts_count: number;
  inferred_facts_count: number;
  latency_ms: number;
}

export interface KGDuplicateCandidate {
  candidate_id: string;
  entity_a_id: string;
  entity_a_label: string;
  entity_b_id: string;
  entity_b_label: string;
  entity_type: KGEntityType;
  similarity_score: number;
  reason: string;
}

export interface KGDestructiveOperationRecord {
  op_id: string;
  user_id: string;
  workspace_id: string;
  operation_type: 'merge_entities' | 'delete_items' | 'clear_workspace';
  status: 'WAITING_FOR_APPROVAL' | 'SUCCEEDED' | 'CANCELLED';
  requires_approval: boolean;
  summary: string;
  affected_entities_count: number;
  affected_relationships_count: number;
  created_at: string;
  resolved_at?: string | null;
}

export interface KGMetadataResponse {
  stage: number;
  engine: string;
  schema_version: string;
  storage_backend: string;
  entity_types: KGEntityType[];
  relation_types: KGRelationType[];
  query_modes: Array<{ id: string; name: string; description: string }>;
  max_expansion_depth: number;
  default_page_size: number;
  max_page_size: number;
}

// ============================================================================
// STAGE 23: IOT PROJECT BUILDER ENGINE TYPES
// ============================================================================

export type IoTBoardId =
  | 'esp32_devkit_v1'
  | 'arduino_uno_r3'
  | 'stm32_nucleo_f401re'
  | 'raspberry_pi_pico_w'
  | 'raspberry_pi_4b';

export type IoTPowerSource =
  | 'usb_5v'
  | 'battery_lipo_3v7'
  | 'dc_barrel_7v_12v'
  | 'solar_mppt_5v'
  | 'mains_ac_isolated_psu';

export type IoTEnvironmentType =
  | 'indoor_lab'
  | 'outdoor_weatherproof'
  | 'industrial_harsh'
  | 'greenhouse_humid'
  | 'wearable_portable';

export type IoTComponentCategory =
  | 'sensor'
  | 'actuator'
  | 'relay'
  | 'display'
  | 'motor'
  | 'motor_driver'
  | 'communication'
  | 'power'
  | 'logic_adapter';

export type IoTSpecVerificationStatus =
  | 'verified_datasheet_spec'
  | 'estimated_typical_range';

export type IoTFirmwareLanguage =
  | 'arduino_cpp'
  | 'micropython'
  | 'esp_idf_c'
  | 'rpi_python_gpiozero';

export type IoTConnectivityProtocol =
  | 'none_local_only'
  | 'wifi_mqtt'
  | 'wifi_http_rest'
  | 'ble_gatt'
  | 'serial_usb_telemetry';

export interface IoTBoardPin {
  pin_id: string;
  label: string;
  gpio_number?: number | null;
  capabilities: string[];
  voltage_level_v: number;
  five_volt_tolerant: boolean;
  max_current_ma: number;
  notes: string;
}

export interface IoTBoardProfile {
  board_id: IoTBoardId;
  name: string;
  family: string;
  mcu_or_soc: string;
  architecture: string;
  clock_mhz: number;
  operating_voltage_v: number;
  io_logic_voltage_v: number;
  five_volt_tolerant_pins: boolean;
  total_gpio_count: number;
  analog_in_count: number;
  pwm_pins_count: number;
  flash_kb: number;
  sram_kb: number;
  max_pin_current_ma: number;
  max_regulator_3v3_current_ma: number;
  max_regulator_5v_current_ma: number;
  communication_interfaces: string[];
  builtin_wireless: string[];
  supported_languages: IoTFirmwareLanguage[];
  pins: IoTBoardPin[];
  toolchain_commands: Record<string, string>;
  toolchain_installed: Record<string, boolean>;
  compatibility_warnings: string[];
  estimated_cost_min_usd: number;
  estimated_cost_max_usd: number;
  spec_verification_status: IoTSpecVerificationStatus;
  datasheet_url: string;
}

export interface IoTComponentPin {
  pin_name: string;
  pin_role: string;
  voltage_min_v: number;
  voltage_max_v: number;
  logic_level_v: number;
  required: boolean;
  description: string;
}

export interface IoTComponentSpec {
  component_id: string;
  name: string;
  category: IoTComponentCategory;
  description: string;
  operating_voltage_min_v: number;
  operating_voltage_max_v: number;
  logic_voltage_v: number;
  five_volt_logic_output: boolean;
  current_typical_ma: number;
  current_peak_ma: number;
  interfaces: string[];
  pins: IoTComponentPin[];
  i2c_default_address?: string | null;
  requires_external_driver: boolean;
  is_inductive_load: boolean;
  is_mains_voltage_hazard: boolean;
  is_high_current_battery: boolean;
  spec_verification_status: IoTSpecVerificationStatus;
  datasheet_url: string;
  availability_status: string;
  cost_min_usd: number;
  cost_max_usd: number;
  recommended_libraries: Record<string, string[]>;
  notes: string;
}

export interface IoTPlacedComponent {
  instance_id: string;
  component_id: string;
  label: string;
  x: number;
  y: number;
  i2c_address_override?: string | null;
  notes: string;
}

export interface IoTWireConnection {
  wire_id: string;
  from_node_id: string;
  from_pin: string;
  to_node_id: string;
  to_pin: string;
  signal_type: string;
  wire_color: string;
  label: string;
  voltage_v: number;
}

export interface IoTWiringValidationIssue {
  issue_id: string;
  code: string;
  severity: 'critical' | 'error' | 'warning' | 'info';
  category: string;
  title: string;
  description: string;
  affected_nodes: string[];
  affected_pins: string[];
  remediation: string;
}

export interface IoTWiringValidationReport {
  valid: boolean;
  critical_count: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  issues: IoTWiringValidationIssue[];
  power_rail_summary: Record<string, number>;
  svg_diagram: string;
  markdown_pinout_table: string;
}

export interface IoTFirmwareArtifact {
  language: IoTFirmwareLanguage;
  filename: string;
  source_code: string;
  secrets_template_filename: string;
  secrets_template_code: string;
  libraries_required: string[];
  pin_mappings: Record<string, string>;
  compile_command: string;
  flash_command: string;
  compilation_tested: boolean;
  compilation_passed?: boolean | null;
  compiler_used?: string | null;
  verification_mode:
    | 'real_compiler_binary'
    | 'python_ast_and_py_compile'
    | 'static_structural_check_toolchain_not_installed';
  compiler_output: string;
  missing_dependencies: string[];
  configuration_instructions: string[];
  generated_at: string;
}

export interface IoTSimulationStimulus {
  instance_id: string;
  parameter: string;
  unit: string;
  values: number[];
}

export interface IoTSimulationTickResult {
  tick: number;
  timestamp_ms: number;
  sensor_readings: Record<string, any>;
  actuator_states: Record<string, any>;
  serial_log: string;
  estimated_current_ma: number;
  estimated_power_mw: number;
  alerts: string[];
}

export interface IoTSimulationResponse {
  simulation_id: string;
  project_id: string;
  board_id: IoTBoardId;
  execution_environment: 'deterministic_virtual_simulation';
  is_physical_hardware_execution: boolean;
  hardware_disclaimer: string;
  wiring_valid_before_run: boolean;
  ticks_executed: number;
  peak_current_ma: number;
  average_current_ma: number;
  ticks: IoTSimulationTickResult[];
  summary: string;
}

export interface IoTConnectivityConfig {
  protocol: IoTConnectivityProtocol;
  enabled: boolean;
  mock_mode: boolean;
  endpoint_or_broker: string;
  port: number;
  topic_prefix: string;
  publish_interval_ms: number;
  tls_enabled: boolean;
  credentials_env_vars: string[];
  masked_credentials_preview: Record<string, string>;
  sample_telemetry_payload: Record<string, any>;
}

export interface IoTBOMItem {
  item_id: string;
  name: string;
  category: string;
  quantity: number;
  unit_cost_min_usd: number;
  unit_cost_max_usd: number;
  subtotal_min_usd: number;
  subtotal_max_usd: number;
  spec_verification_status: IoTSpecVerificationStatus;
  datasheet_url: string;
  notes: string;
}

export interface IoTBuildDocumentation {
  bom_items: IoTBOMItem[];
  total_cost_min_usd: number;
  total_cost_max_usd: number;
  target_budget_usd: number;
  within_budget: boolean;
  budget_notes: string;
  unverified_specs_notice: string;
  wiring_steps: string[];
  assembly_instructions: string[];
  test_procedures: string[];
  troubleshooting_guide: string[];
}

export interface IoTSafetyCheckItem {
  check_id: string;
  category: string;
  status: 'pass' | 'warning' | 'hazard_review_required' | 'fail';
  title: string;
  detail: string;
  recommendation: string;
}

export interface IoTSafetyReport {
  passed_nominal_checks: boolean;
  requires_qualified_electrical_review: boolean;
  mains_voltage_detected: boolean;
  high_current_battery_detected: boolean;
  inductive_load_without_driver: boolean;
  regulator_3v3_load_ma: number;
  regulator_3v3_limit_ma: number;
  regulator_5v_load_ma: number;
  regulator_5v_limit_ma: number;
  power_budget_exceeded: boolean;
  checks: IoTSafetyCheckItem[];
  physical_safety_disclaimer: string;
}

export interface IoTProjectRecord {
  project_id: string;
  user_id: string;
  workspace_id: string;
  name: string;
  purpose_description: string;
  target_budget_usd: number;
  power_source: IoTPowerSource;
  environment: IoTEnvironmentType;
  board_id: IoTBoardId;
  board_profile: IoTBoardProfile;
  placed_components: IoTPlacedComponent[];
  wires: IoTWireConnection[];
  wiring_report: IoTWiringValidationReport;
  firmware: IoTFirmwareArtifact;
  connectivity: IoTConnectivityConfig;
  build_docs: IoTBuildDocumentation;
  safety_report: IoTSafetyReport;
  last_simulation?: IoTSimulationResponse | null;
  version: string;
  export_count: number;
  created_at: string;
  updated_at: string;
}

export interface IoTExportFileEntry {
  relative_path: string;
  size_bytes: number;
  sha256: string;
  description: string;
  content_preview: string;
}

export interface IoTProjectExportResponse {
  export_id: string;
  project_id: string;
  project_name: string;
  version: string;
  export_directory: string;
  workspace_relative_dir?: string | null;
  files: IoTExportFileEntry[];
  wiring_valid: boolean;
  requires_qualified_electrical_review: boolean;
  exported_at: string;
  summary: string;
}

export interface IoTMetadataResponse {
  stage: number;
  engine: string;
  boards_count: number;
  components_count: number;
  supported_languages: string[];
  supported_connectivity: string[];
  detected_toolchains: Record<string, boolean>;
  hardware_execution_disclaimer: string;
}

// ============================================================================
// STAGE 24: EMBEDDED FIRMWARE ENGINEERING STUDIO TYPES
// ============================================================================

export type FirmwareFrameworkId =
  | 'arduino_cpp'
  | 'esp_idf_c'
  | 'stm32_hal_c'
  | 'micropython'
  | 'rpi_python_gpiozero';

export type FirmwareOptimizationLevel = '-Os' | '-O2' | '-O0' | '-Og';

export interface FirmwarePlatformMatrixEntry {
  board_id: IoTBoardId;
  board_name: string;
  mcu_or_soc: string;
  supported_frameworks: FirmwareFrameworkId[];
  unsupported_frameworks: Record<string, string>;
  compiler_binaries: Record<string, string>;
  toolchain_available: Record<string, boolean>;
  flash_protocol: string;
  default_baud_rate: number;
}

export interface FirmwareLibraryDependency {
  name: string;
  version: string;
  header_or_module: string;
  purpose: string;
  installed_in_sandbox: boolean;
}

export interface FirmwareBuildSettings {
  optimization_level: FirmwareOptimizationLevel;
  debug_symbols: boolean;
  watchdog_enabled: boolean;
  watchdog_timeout_ms: number;
  serial_baud_rate: number;
  enable_ota_stub: boolean;
  extra_build_flags: string[];
}

export interface FirmwareProjectFile {
  path: string;
  role:
    | 'main_entry'
    | 'pin_config'
    | 'driver_header'
    | 'driver_source'
    | 'secrets_template'
    | 'build_manifest'
    | 'unit_test';
  language: string;
  content: string;
  size_bytes: number;
  sha256: string;
  updated_at: string;
}

export interface FirmwareHardwareDiagnostic {
  diag_id: string;
  severity: 'critical' | 'error' | 'warning' | 'info';
  category:
    | 'incompatible_voltage'
    | 'invalid_pin'
    | 'missing_library'
    | 'unsupported_peripheral'
    | 'interrupt_constraint';
  title: string;
  detail: string;
  file_path?: string | null;
  line_number?: number | null;
  suggested_fix: string;
}

export interface FirmwareStaticIssue {
  issue_id: string;
  category:
    | 'memory_error'
    | 'blocking_loop'
    | 'watchdog_issue'
    | 'unsafe_buffer_handling'
    | 'uninitialized_value'
    | 'missing_timeout'
    | 'credential_exposure';
  severity: 'critical' | 'error' | 'warning' | 'info';
  file_path: string;
  line_number: number;
  code_snippet: string;
  message: string;
  suggested_fix: string;
}

export interface FirmwareQualityReport {
  passed_quality_gate: boolean;
  critical_count: number;
  error_count: number;
  warning_count: number;
  issues: FirmwareStaticIssue[];
  unit_tests_executed: boolean;
  unit_tests_passed?: boolean | null;
  unit_test_output: string;
  hil_status: 'SKIPPED_NO_HIL_EQUIPMENT' | 'EXECUTED';
  hil_notes: string;
}

export interface FirmwareCompilerDiagnostic {
  file_path: string;
  line_number: number;
  column: number;
  severity: 'error' | 'warning' | 'info';
  message: string;
  source_line: string;
  suggested_fix: string;
}

export interface FirmwareArtifactFile {
  relative_path: string;
  artifact_type:
    | 'source_file'
    | 'dependency_manifest'
    | 'build_config'
    | 'compiled_bytecode_or_binary'
    | 'release_notes';
  size_bytes: number;
  sha256: string;
  genuinely_produced_by_build: boolean;
}

export interface FirmwareCompileResult {
  build_id: string;
  workspace_id: string;
  fw_project_id: string;
  board_id: IoTBoardId;
  framework: FirmwareFrameworkId;
  status: 'SUCCEEDED' | 'FAILED_COMPILATION_ERROR' | 'BLOCKED_TOOLCHAIN_MISSING';
  toolchain_binary: string;
  toolchain_installed: boolean;
  compilation_genuinely_executed: boolean;
  binary_artifact_produced: boolean;
  exit_code?: number | null;
  duration_ms: number;
  compiler_stdout: string;
  compiler_stderr: string;
  diagnostics: FirmwareCompilerDiagnostic[];
  produced_artifacts: FirmwareArtifactFile[];
  compiled_at: string;
  honesty_notice: string;
}

export interface FirmwareSerialLogEntry {
  seq: number;
  timestamp_ms: number;
  event_type:
    | 'boot_banner'
    | 'reset_event'
    | 'sensor_telemetry'
    | 'isr_trigger'
    | 'watchdog_feed'
    | 'error';
  message: string;
  firmware_version: string;
}

export interface FirmwareSerialMonitorResponse {
  fw_project_id: string;
  board_id: IoTBoardId;
  source_mode: 'simulated_virtual_serial' | 'physical_authorized_serial';
  is_simulated: boolean;
  connected_physical_port?: string | null;
  baud_rate: number;
  firmware_version: string;
  reset_reason: string;
  logs: FirmwareSerialLogEntry[];
  distinction_banner: string;
}

export interface FirmwareDeviceActionRecord {
  action_id: string;
  fw_project_id: string;
  user_id: string;
  workspace_id: string;
  action_type: 'flash_firmware' | 'reset_device';
  target_port: string;
  status: 'WAITING_FOR_APPROVAL' | 'BLOCKED_NO_PHYSICAL_DEVICE' | 'CANCELLED';
  requires_approval: boolean;
  cli_command_preview: string;
  recovery_guidance: string[];
  message: string;
  created_at: string;
  resolved_at?: string | null;
}

export interface FirmwareVersionSnapshot {
  version_id: string;
  semver: string;
  commit_note: string;
  files: FirmwareProjectFile[];
  build_settings: FirmwareBuildSettings;
  created_at: string;
}

export interface FirmwareCodeSearchHit {
  file_path: string;
  line_number: number;
  line_preview: string;
}

export interface FirmwareWorkspaceRecord {
  fw_project_id: string;
  user_id: string;
  workspace_id: string;
  name: string;
  iot_project_id?: string | null;
  board_id: IoTBoardId;
  board_name: string;
  framework: FirmwareFrameworkId;
  semver: string;
  build_settings: FirmwareBuildSettings;
  libraries: FirmwareLibraryDependency[];
  files: FirmwareProjectFile[];
  hardware_diagnostics: FirmwareHardwareDiagnostic[];
  quality_report: FirmwareQualityReport;
  last_compile?: FirmwareCompileResult | null;
  versions: FirmwareVersionSnapshot[];
  recovery_guidance: string[];
  created_at: string;
  updated_at: string;
}

export interface FirmwareExportResponse {
  export_id: string;
  fw_project_id: string;
  name: string;
  semver: string;
  export_directory: string;
  workspace_relative_dir?: string | null;
  only_real_artifacts_exported: boolean;
  compiled_binaries_included: boolean;
  artifacts: FirmwareArtifactFile[];
  release_notes_markdown: string;
  exported_at: string;
  summary: string;
}

export interface FirmwareMetadataResponse {
  stage: number;
  engine: string;
  reuses_stage23_iot_builder: boolean;
  platform_matrix: FirmwarePlatformMatrixEntry[];
  detected_toolchains: Record<string, boolean>;
  connected_serial_ports: string[];
  safety_and_honesty_policy: string;
}

// Stage 25: IoT Device Connectivity & Live Telemetry Interfaces
export type IoTDeviceStatus = 'online' | 'offline' | 'degraded' | 'unprovisioned';
export type IoTIngestionProtocol = 'http' | 'mqtt' | 'dual';
export type TelemetryDataProvenance = 'physical_device' | 'deterministic_simulation' | 'predicted';
export type AlertOperator = 'gt' | 'lt' | 'gte' | 'lte' | 'eq' | 'neq' | 'outside_range' | 'device_offline';
export type AlertSeverity = 'info' | 'warning' | 'critical';
export type AlertRecordStatus = 'active' | 'acknowledged' | 'resolved';
export type DeviceCommandType =
  | 'reboot'
  | 'set_telemetry_interval'
  | 'actuator_set_state'
  | 'set_relay'
  | 'trigger_calibration'
  | 'ota_firmware_update'
  | 'custom_control';
export type CommandConfirmationStatus = 'not_required' | 'pending_confirmation' | 'confirmed' | 'rejected';
export type CommandDispatchStatus = 'queued' | 'dispatched' | 'acknowledged' | 'timed_out' | 'failed';

export interface IoTDeviceRecord {
  device_id: string;
  user_id: string;
  workspace_id: string;
  name: string;
  board_id: IoTBoardId;
  is_simulated: boolean;
  mac_address?: string | null;
  chip_id?: string | null;
  firmware_version: string;
  status: IoTDeviceStatus;
  iot_project_id?: string | null;
  fw_project_id?: string | null;
  ingestion_protocol: IoTIngestionProtocol;
  mqtt_topic_telemetry: string;
  mqtt_topic_commands: string;
  rate_limit_per_minute: number;
  last_seen_at?: string | null;
  last_reading_age_seconds?: number | null;
  total_events_received: number;
  active_alerts_count: number;
  created_at: string;
  updated_at: string;
}

export interface IoTDeviceTokenResponse {
  device_id: string;
  name: string;
  plaintext_token: string;
  token_prefix: string;
  ingestion_url: string;
  mqtt_topic: string;
  security_notice: string;
}

export interface TelemetryEventRecord {
  event_id: string;
  device_id: string;
  workspace_id: string;
  sequence_id?: number | null;
  device_timestamp: string;
  ingestion_timestamp: string;
  metrics: Record<string, number>;
  units: Record<string, string>;
  data_provenance: TelemetryDataProvenance;
  is_valid: boolean;
  anomalies: string[];
}

export interface AlertRuleRecord {
  rule_id: string;
  device_id: string;
  workspace_id: string;
  metric_key: string;
  operator: AlertOperator;
  threshold_val_primary: number;
  threshold_val_secondary?: number | null;
  severity: AlertSeverity;
  cooldown_seconds: number;
  description: string;
  is_enabled: boolean;
  last_triggered_at?: string | null;
  created_at: string;
}

export interface AlertRecord {
  alert_id: string;
  rule_id: string;
  device_id: string;
  device_name: string;
  workspace_id: string;
  metric_key: string;
  measured_value: number;
  threshold_description: string;
  severity: AlertSeverity;
  status: AlertRecordStatus;
  data_provenance: TelemetryDataProvenance;
  cooldown_until?: string | null;
  created_at: string;
  resolved_at?: string | null;
}

export interface DeviceCommandRecord {
  command_id: string;
  device_id: string;
  device_name: string;
  workspace_id: string;
  user_id: string;
  command_type: DeviceCommandType;
  parameters: Record<string, any>;
  is_consequential: boolean;
  requires_confirmation: boolean;
  confirmation_status: CommandConfirmationStatus;
  dispatch_status: CommandDispatchStatus;
  result_message: string;
  dispatched_at?: string | null;
  acknowledged_at?: string | null;
  created_at: string;
}

export interface TelemetryDeviceStatsResponse {
  device_id: string;
  device_name: string;
  status: IoTDeviceStatus;
  is_simulated: boolean;
  last_seen_at?: string | null;
  last_seen_seconds_ago?: number | null;
  data_freshness_label: string;
  total_events: number;
  latest_metrics: Record<string, number>;
  metric_ranges: Record<string, { min: number; max: number; avg: number; current: number }>;
  recent_events: TelemetryEventRecord[];
  active_alerts: AlertRecord[];
  pending_commands: DeviceCommandRecord[];
}

export interface TelemetryExportResponse {
  export_id: string;
  device_id: string;
  format: 'csv' | 'json';
  time_range: string;
  total_events_exported: number;
  file_path?: string | null;
  workspace_relative_path?: string | null;
  content_preview: string;
  exported_at: string;
}

export interface TelemetryMetadataResponse {
  stage: number;
  engine: string;
  supported_metrics: Array<{ key: string; unit: string; min: number; max: number; description: string }>;
  supported_protocols: IoTIngestionProtocol[];
  mqtt_broker_config: Record<string, any>;
  security_policy: Record<string, any>;
  reliability_specs: Record<string, any>;
}

// Stage 26: IoT Security & Device Threat Detection Interfaces
export type SecurityRiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'info' | 'unknown';
export type ThreatClassification = 'confirmed_event' | 'suspicious_indicator' | 'heuristic_alert' | 'unverified_hypothesis';
export type IncidentStatus = 'new' | 'under_investigation' | 'mitigated' | 'false_positive' | 'closed';
export type ConfigAuditSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type DefensiveActionType = 'revoke_credential' | 'quarantine_device' | 'isolate_network' | 'throttle_telemetry' | 'restore_device';
export type DefensiveActionStatus = 'pending_confirmation' | 'executed' | 'rejected' | 'failed';

export interface DeviceSecurityPosture {
  device_id: string;
  device_name: string;
  board_id: string;
  status: string;
  is_simulated: boolean;
  firmware_version: string;
  authentication_status: 'token_active' | 'token_revoked' | 'weak_token' | 'unprovisioned' | 'unknown';
  token_age_days?: number | null;
  token_last_rotated_at?: string | null;
  transport_encryption: 'tls_enabled' | 'plaintext_unencrypted' | 'unknown';
  exposed_services: string[];
  update_status: 'up_to_date' | 'update_available' | 'critical_outdated' | 'unknown';
  supports_secure_boot: boolean;
  secure_boot_mechanism: string;
  supports_signed_firmware: boolean;
  supports_anti_rollback: boolean;
  last_security_assessment_at?: string | null;
  risk_score: number;
  risk_level: SecurityRiskLevel;
  active_findings_count: number;
  active_threats_count: number;
}

export interface ConfigurationAuditFinding {
  finding_id: string;
  device_id: string;
  device_name: string;
  workspace_id: string;
  rule_id: string;
  title: string;
  severity: ConfigAuditSeverity;
  evidence: string;
  impact: string;
  remediation: string;
  status: 'active' | 'remediated' | 'suppressed' | 'false_positive';
  detected_at: string;
  remediated_at?: string | null;
}

export interface BehavioralAnomalyRecord {
  anomaly_id: string;
  device_id: string;
  device_name: string;
  workspace_id: string;
  anomaly_type: 'unusual_reporting_frequency' | 'unexpected_restart_crashloop' | 'abnormal_measurement_pattern' | 'repeated_auth_failures' | 'baseline_deviation' | 'sensor_saturation_stuck';
  severity: ConfigAuditSeverity;
  classification: ThreatClassification;
  confidence: 'high' | 'medium' | 'low';
  metric_key?: string | null;
  observed_value?: any;
  baseline_expected?: any;
  evidence_summary: string;
  detected_at: string;
}

export interface SecurityIncidentRecord {
  incident_id: string;
  workspace_id: string;
  title: string;
  severity: ConfigAuditSeverity;
  classification: ThreatClassification;
  status: IncidentStatus;
  affected_device_ids: string[];
  affected_devices_count: number;
  root_cause_hypothesis: string;
  confidence_level: 'high' | 'medium' | 'low';
  evidence_records: Record<string, any>[];
  telemetry_correlations: Record<string, any>[];
  recommended_remediations: string[];
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
  assigned_responder?: string | null;
}

export interface DefensiveActionRecord {
  action_id: string;
  user_id: string;
  workspace_id: string;
  device_id: string;
  device_name: string;
  action_type: DefensiveActionType;
  reason: string;
  requires_confirmation: boolean;
  status: DefensiveActionStatus;
  result_message: string;
  recovery_procedure: string;
  executed_at?: string | null;
  created_at: string;
}

export interface FirmwareIntegritySpec {
  board_id: string;
  board_name: string;
  supports_secure_boot: boolean;
  secure_boot_version: string;
  crypto_keys_supported: string[];
  supports_signed_firmware: boolean;
  supports_hardware_root_of_trust: boolean;
  supports_anti_rollback: boolean;
  recovery_strategy: string;
  checksum_trust_limitation: string;
}

export interface IoTSecurityOverviewResponse {
  stage: number;
  fleet_posture_summary: {
    total_devices_monitored: number;
    average_fleet_risk_score: number;
    risk_distribution: Record<string, number>;
    active_config_findings: number;
    recent_behavioral_anomalies: number;
    open_security_incidents: number;
    tls_enforced_devices_count: number;
    unencrypted_transport_devices_count: number;
  };
  devices_posture: DeviceSecurityPosture[];
  active_incidents: SecurityIncidentRecord[];
  recent_anomalies: BehavioralAnomalyRecord[];
  config_findings: ConfigurationAuditFinding[];
  firmware_integrity_matrix: FirmwareIntegritySpec[];
  last_assessment_at: string;
}



