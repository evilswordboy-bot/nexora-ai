from datetime import datetime, timezone
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


SearchMode = Literal["ai_only", "web_search", "deep_research"]


class SearchResultItem(BaseModel):
    title: str = Field(..., description="Webpage title")
    url: str = Field(..., description="Target webpage URL")
    snippet: str = Field(..., description="Summary text snippet")
    domain: str = Field(..., description="Website host domain")
    published_date: Optional[str] = None
    content: Optional[str] = None
    source_id: Optional[int] = None


class Message(BaseModel):
    id: str = Field(..., description="Unique ID for the message")
    role: Literal["user", "assistant", "system"] = Field(..., description="Role of the author")
    content: str = Field(..., description="Text content of the message")
    timestamp: datetime = Field(default_factory=utc_now)
    model: Optional[str] = None
    provider: Optional[str] = None
    error: Optional[bool] = False
    isStreaming: Optional[bool] = False
    sources: Optional[List[SearchResultItem]] = None
    search_mode: Optional[SearchMode] = None
    research_queries: Optional[List[str]] = None
    images: Optional[List[str]] = None  # Base64 data URLs or uploaded paths
    image_metadata: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("content")
    @classmethod
    def validate_content_size(cls, v: str) -> str:
        if len(v) > 32000:
            raise ValueError("Message exceeds maximum permitted character limit of 32,000 characters.")
        return v


class Conversation(BaseModel):
    id: str = Field(..., description="Unique conversation UUID")
    title: str = Field("New Conversation", description="User visible title")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    system_prompt: Optional[str] = None
    messages: List[Message] = Field(default_factory=list)


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    system_prompt: Optional[str] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    system_prompt: Optional[str] = None


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    messages: List[Message]
    provider: Optional[str] = "auto"
    model: Optional[str] = "gemini-1.5-flash"
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(2048, ge=1, le=8192)
    system_prompt: Optional[str] = None
    stream: Optional[bool] = True
    client_api_key: Optional[str] = None  # Optional key provided securely from user's client settings

    # Stage 3 Search & Research parameters
    search_mode: Optional[SearchMode] = "ai_only"
    search_engine: Optional[str] = "auto"
    client_search_key: Optional[str] = None

    # Stage 6 Multilingual parameters
    target_language: Optional[str] = "auto" # 'auto', 'en', 'ta', 'hi', 'te', 'ml', 'kn', 'bn', 'mr', etc.
    transliteration: Optional[bool] = False

    # Stage 9 Vision parameters
    images: Optional[List[str]] = None  # Base64 encoded or data URLs passed with the active prompt

    # Stage 4 Document Vault Context parameters
    document_ids: Optional[List[str]] = None  # IDs of active documents for grounded RAG chat

    # Stage 13 Persistent Memory parameters
    user_id: Optional[str] = "default_user"
    memory_enabled: Optional[bool] = True
    temporary_chat: Optional[bool] = False

    @field_validator("messages")
    @classmethod
    def validate_messages_count(cls, v: List[Message]) -> List[Message]:
        if not v:
            raise ValueError("At least one message is required.")
        if len(v) > 100:
            raise ValueError("Conversation exceeds maximum permitted messages length of 100.")
        return v


class ChatResponse(BaseModel):
    id: str
    conversation_id: Optional[str] = None
    role: Literal["assistant"] = "assistant"
    content: str
    model: str
    provider: str
    finish_reason: Optional[str] = "stop"
    usage: Optional[Dict[str, int]] = None
    sources: Optional[List[SearchResultItem]] = None
    search_mode: Optional[SearchMode] = None
    research_queries: Optional[List[str]] = None
    used_memories: Optional[List[Dict[str, Any]]] = None
    memory_disclosure: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class SearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5
    engine: Optional[str] = "auto"
    client_search_key: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    engine: str
    results: List[SearchResultItem]
    count: int


class TitleGenerationRequest(BaseModel):
    conversation_id: Optional[str] = None
    user_prompt: str
    assistant_response: Optional[str] = None
    client_api_key: Optional[str] = None
    provider: Optional[str] = "auto"


class TitleGenerationResponse(BaseModel):
    title: str


class ProviderInfo(BaseModel):
    name: str
    display_name: str
    configured: bool
    models: List[str]
    description: str


class ProviderStatusResponse(BaseModel):
    configured: bool
    active_provider: Optional[str]
    available_providers: List[ProviderInfo]
    configured_search_engines: List[str]
    instructions: str


class SafetyCheckResult(BaseModel):
    is_safe: bool
    flagged: bool
    category: Optional[str] = None
    reason: Optional[str] = None
    educational_override: bool = False


# ==========================================
# Stage 4: Document Intelligence Schemas
# ==========================================

DocumentFormat = Literal["pdf", "docx", "txt", "csv", "xlsx", "png", "jpg", "jpeg", "webp"]
DocumentStatus = Literal["pending", "processing", "ready", "error"]
DocumentAction = Literal[
    "ask",
    "summarize",
    "extract_key_points",
    "compare",
    "study_notes",
    "faq",
    "flashcards",
    "quiz",
    "explain_simply",
    "extract_tables"
]


class DocumentCitation(BaseModel):
    source_id: int
    document_id: str
    filename: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    snippet: str
    relevance_score: Optional[float] = None


class DocumentChunk(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    page_number: Optional[int] = None
    section: Optional[str] = None
    content: str
    token_count: int


class DocumentItem(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    size_bytes: int
    created_at: datetime = Field(default_factory=utc_now)
    status: DocumentStatus = "pending"
    error_message: Optional[str] = None
    page_count: Optional[int] = 0
    total_characters: Optional[int] = 0
    total_chunks: Optional[int] = 0
    metadata: Optional[Dict[str, Any]] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentItem]
    total_count: int


class DocumentDetailResponse(BaseModel):
    document: DocumentItem
    preview_text: str
    chunks: Optional[List[DocumentChunk]] = None


class DocumentActionRequest(BaseModel):
    document_ids: List[str] = Field(..., description="Target document IDs (one or multiple for comparison)")
    action: DocumentAction = "ask"
    query: Optional[str] = None
    provider: Optional[str] = "auto"
    model: Optional[str] = "gemini-1.5-flash"
    client_api_key: Optional[str] = None
    temperature: Optional[float] = Field(0.5, ge=0.0, le=2.0)
    stream: Optional[bool] = False


class DocumentActionResponse(BaseModel):
    action: DocumentAction
    document_ids: List[str]
    result: str
    citations: List[DocumentCitation] = Field(default_factory=list)
    provider: str
    model: str


# ==========================================
# Stage 5: Fact-Checking & Evidence Verification Schemas
# ==========================================

VerdictClassification = Literal[
    "supported",
    "contradicted",
    "mixed",
    "insufficient_evidence",
    "opinion_or_prediction"
]

ConfidenceLevel = Literal["high", "medium", "low", "uncertain"]


class EvidenceSource(BaseModel):
    source_id: int
    title: str
    url: Optional[str] = None
    domain: Optional[str] = None
    published_date: Optional[str] = None
    snippet: str
    stance: Literal["supporting", "opposing", "neutral", "context"] = "neutral"
    is_primary: bool = False


class ClaimVerificationResult(BaseModel):
    claim_id: int
    claim_text: str
    verdict: VerdictClassification
    confidence: ConfidenceLevel
    explanation: str
    supporting_evidence: List[EvidenceSource] = Field(default_factory=list)
    opposing_evidence: List[EvidenceSource] = Field(default_factory=list)
    missing_context_flags: List[str] = Field(default_factory=list)


class FactCheckRequest(BaseModel):
    text: Optional[str] = None
    url: Optional[str] = None
    document_ids: Optional[List[str]] = Field(default_factory=list)
    search_engine: Optional[str] = "auto"
    client_search_key: Optional[str] = None
    provider: Optional[str] = "auto"
    model: Optional[str] = "gemini-1.5-flash"
    client_api_key: Optional[str] = None


class FactCheckResponse(BaseModel):
    input_text: str
    extracted_claims_count: int
    claims: List[ClaimVerificationResult]
    overall_summary: str
    sources_consulted: List[EvidenceSource]
    provider: str
    model: str
    created_at: datetime = Field(default_factory=utc_now)


# ==========================================
# Stage 6: Universal Multilingual Schemas
# ==========================================

TranslationTone = Literal["formal", "casual", "technical", "simplification"]


class LanguageDetectionResult(BaseModel):
    detected_language_code: str
    detected_language_name: str
    confidence: float
    is_mixed_or_code_switched: bool = False
    secondary_languages: List[str] = Field(default_factory=list)
    script: str = "Latin"


class SentencePair(BaseModel):
    source_sentence: str
    translated_sentence: str


class TranslationRequest(BaseModel):
    text: str
    source_language: Optional[str] = "auto"
    target_language: str = "en"
    tone: Optional[TranslationTone] = "formal"
    transliterate: Optional[bool] = False
    provider: Optional[str] = "auto"
    model: Optional[str] = "gemini-1.5-flash"
    client_api_key: Optional[str] = None


class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    detected_source_language: str
    target_language: str
    tone: TranslationTone
    sentence_pairs: List[SentencePair] = Field(default_factory=list)
    transliterated_text: Optional[str] = None
    cultural_notes: Optional[str] = None
    provider: str
    model: str
    created_at: datetime = Field(default_factory=utc_now)


# ==========================================
# Stage 7: Voice Intelligence Engine Schemas
# ==========================================

VoiceConversationMode = Literal["push_to_talk", "voice_chat", "text_and_voice"]

class VoiceInfo(BaseModel):
    id: str
    name: str
    language_code: str
    gender: Optional[str] = "neutral"
    provider: str = "browser" # 'browser', 'openai', 'gemini'


class TextToSpeechRequest(BaseModel):
    text: str
    voice_id: Optional[str] = "alloy"
    language_code: Optional[str] = "auto"
    speed: Optional[float] = Field(1.0, ge=0.25, le=4.0)
    provider: Optional[str] = "auto"
    client_api_key: Optional[str] = None


class TextToSpeechResponse(BaseModel):
    audio_content: Optional[str] = None # Base64 encoded audio or null if browser engine recommended
    content_type: str = "audio/mpeg"
    clean_spoken_text: str # Strip code blocks, long URLs, raw markdown symbols for pleasant speech
    provider: str
    voice_id: str
    duration_estimate_seconds: float = 0.0


class AudioTranscriptionResponse(BaseModel):
    text: str
    detected_language: Optional[str] = "en"
    confidence: Optional[float] = 1.0
    provider: str
    duration_seconds: Optional[float] = 0.0


# ==========================================
# Stage 8: Real-Time Intelligence Engine Schemas
# ==========================================

LiveCategory = Literal["news", "tech", "research", "finance", "announcements", "weather", "general"]

class LiveSourceItem(BaseModel):
    title: str
    url: str
    snippet: str
    domain: str
    published_date: Optional[str] = None
    retrieved_at: datetime = Field(default_factory=utc_now)
    source_freshness: str = "fresh" # 'fresh', 'cached', 'historical'


class MonitoredTopic(BaseModel):
    id: str
    name: str
    query_or_url: str
    category: LiveCategory = "general"
    check_interval_minutes: int = 60
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    last_checked_at: Optional[datetime] = None
    next_check_at: Optional[datetime] = None
    last_content_hash: Optional[str] = None
    change_count: int = 0
    latest_summary: Optional[str] = None


class LiveNotification(BaseModel):
    id: str
    topic_id: str
    topic_name: str
    title: str
    summary_diff: str
    detected_at: datetime = Field(default_factory=utc_now)
    source_urls: List[str] = Field(default_factory=list)
    is_read: bool = False


class LiveQueryRequest(BaseModel):
    query: str
    category: Optional[LiveCategory] = "general"
    force_refresh: Optional[bool] = False
    max_sources: Optional[int] = Field(5, ge=1, le=15)
    search_engine: Optional[str] = "auto"
    client_search_key: Optional[str] = None


class LiveQueryResponse(BaseModel):
    query: str
    category: LiveCategory
    is_fresh_retrieval: bool
    retrieved_at: datetime = Field(default_factory=utc_now)
    freshness_label: str # e.g. 'Retrieved just now (Live Web)'
    sources: List[LiveSourceItem]
    synthesized_answer: str
    provider: str
    model: str


# ==========================================
# Stage 9: Computer Vision & Visual Intelligence Schemas
# ==========================================

class ImageAttachmentMetadata(BaseModel):
    id: str
    filename: Optional[str] = "image.png"
    format: str # 'png', 'jpeg', 'webp', etc.
    size_bytes: int
    width: int
    height: int
    aspect_ratio: str
    color_mode: str # 'RGB', 'RGBA', 'L', etc.
    has_text: bool = False
    ocr_preview: Optional[str] = None


class VisionAnalyzeRequest(BaseModel):
    images: List[str] = Field(..., description="List of base64 data URLs or raw base64 strings")
    prompt: Optional[str] = "Describe and analyze this image in detail."
    analysis_type: Optional[Literal["general", "ui_diagram", "charts_data", "technical_circuit", "ocr_extract", "comparison"]] = "general"
    provider: Optional[str] = "auto"
    model: Optional[str] = "gemini-1.5-flash"
    client_api_key: Optional[str] = None


class VisionAnalyzeResponse(BaseModel):
    id: str
    prompt: str
    analysis: str
    extracted_text: Optional[str] = None
    image_metadata: List[ImageAttachmentMetadata]
    model: str
    provider: str
    created_at: datetime = Field(default_factory=utc_now)


class OCRRequest(BaseModel):
    image: str = Field(..., description="Base64 data URL or raw base64 string")
    filename: Optional[str] = "document_image.png"
    language_hint: Optional[str] = "auto"
    quarantine_output: Optional[bool] = True


class OCRResponse(BaseModel):
    text: str
    raw_character_count: int
    word_count: int
    metadata: ImageAttachmentMetadata
    is_quarantined: bool = True
    confidence: Optional[float] = None
    created_at: datetime = Field(default_factory=utc_now)


class ImageCompareRequest(BaseModel):
    image1: str = Field(..., description="First image base64")
    image2: str = Field(..., description="Second image base64")
    image1_label: Optional[str] = "Image A"
    image2_label: Optional[str] = "Image B"
    comparison_focus: Optional[Literal["general", "ui_diff", "chart_comparison", "text_diff"]] = "general"
    provider: Optional[str] = "auto"
    model: Optional[str] = "gemini-1.5-flash"
    client_api_key: Optional[str] = None


class ImageCompareResponse(BaseModel):
    id: str
    comparison_summary: str
    similarities: List[str]
    differences: List[str]
    metadata_image1: ImageAttachmentMetadata
    metadata_image2: ImageAttachmentMetadata
    model: str
    provider: str
    created_at: datetime = Field(default_factory=utc_now)


# --- Stage 11: Advanced Reasoning Engine Schemas ---
SubtaskStatus = Literal["PLANNED", "IN PROGRESS", "BLOCKED", "REVIEWING", "COMPLETE", "FAILED", "CANCELLED"]
PlanStatus = Literal["PLANNED", "IN PROGRESS", "BLOCKED", "REVIEWING", "COMPLETE", "CANCELLED"]
TaskComplexity = Literal["simple", "moderate", "complex"]
RiskLevel = Literal["low", "medium", "high"]


class ToolExecutionRecord(BaseModel):
    tool_name: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    output_summary: str
    raw_output: Optional[Any] = None
    success: bool = True
    duration_ms: float = 0.0
    error: Optional[str] = None
    untrusted_content_quarantined: bool = True
    attempt: int = 1
    executed_at: datetime = Field(default_factory=utc_now)


class ReasoningSubtask(BaseModel):
    id: str
    step_number: int
    title: str
    description: str
    status: SubtaskStatus = "PLANNED"
    depends_on: List[str] = Field(default_factory=list)
    expected_output: str = ""
    completion_criteria: str = ""
    tool_name: Optional[str] = None
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    tool_executions: List[ToolExecutionRecord] = Field(default_factory=list)
    result_summary: Optional[str] = None
    verification_passed: Optional[bool] = None
    verification_note: Optional[str] = None
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    approval_granted: Optional[bool] = None
    retry_count: int = 0
    max_retries: int = 2
    error_message: Optional[str] = None


class TaskClassification(BaseModel):
    complexity: TaskComplexity
    requires_planning: bool
    required_tools: List[str] = Field(default_factory=list)
    uncertainty_level: Literal["low", "medium", "high"] = "low"
    risk_level: RiskLevel = "low"
    has_consequential_actions: bool = False
    consequential_action_details: Optional[str] = None
    missing_information: List[str] = Field(default_factory=list)
    rationale: str = ""


class ReasoningPlan(BaseModel):
    id: str
    query: str
    classification: TaskClassification
    status: PlanStatus = "PLANNED"
    assumptions: List[str] = Field(default_factory=list)
    clarification_questions: List[str] = Field(default_factory=list)
    subtasks: List[ReasoningSubtask] = Field(default_factory=list)
    final_answer: Optional[str] = None
    execution_summary: Optional[str] = None
    uncertainty_notes: List[str] = Field(default_factory=list)
    total_tool_calls: int = 0
    revision_history: List[str] = Field(default_factory=list)
    provider: str = "system"
    model: str = "nexora-reasoning-v1"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ReasoningAnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    auto_execute: bool = True
    force_plan: bool = False
    max_retries: int = Field(default=2, ge=0, le=5)
    provider: Optional[str] = "auto"
    model: Optional[str] = "auto"
    client_api_key: Optional[str] = None
    context_notes: Optional[str] = None


class ReasoningReviseRequest(BaseModel):
    revised_goal: Optional[str] = None
    clarification_answers: Optional[Dict[str, str]] = None
    updated_subtask_titles: Optional[List[str]] = None
    auto_execute: bool = True
    provider: Optional[str] = "auto"
    model: Optional[str] = "auto"
    client_api_key: Optional[str] = None


class ReasoningApprovalRequest(BaseModel):
    subtask_id: str
    approved: bool
    user_note: Optional[str] = None
    auto_resume: bool = True
    provider: Optional[str] = "auto"
    model: Optional[str] = "auto"
    client_api_key: Optional[str] = None


# --- Stage 12: Intelligent Model Routing Engine Schemas ---
RoutingTaskCategory = Literal[
    "general_chat",
    "coding",
    "deep_research",
    "document_analysis",
    "image_understanding",
    "translation",
    "voice",
    "reasoning",
]
RoutingPreference = Literal["quality_first", "balanced", "speed_first"]
ProviderAvailabilityStatus = Literal["available", "unconfigured", "degraded", "rate_limited", "outage"]
ModelQualityTier = Literal["frontier", "balanced", "fast"]


class ModelRegistryEntry(BaseModel):
    model_id: str
    provider: str
    display_name: str
    supported_capabilities: List[RoutingTaskCategory] = Field(default_factory=list)
    context_window_tokens: int = 128000
    max_output_tokens: int = 8192
    pricing_per_1k_input_usd: Optional[float] = None
    pricing_per_1k_output_usd: Optional[float] = None
    pricing_note: str = "Estimated published API pricing (USD per 1K tokens)"
    quality_tier: ModelQualityTier = "balanced"
    typical_latency_ms: int = 800
    timeout_seconds: float = 30.0
    configured: bool = False
    availability_status: ProviderAvailabilityStatus = "unconfigured"
    is_default: bool = False


class TokenCostEstimate(BaseModel):
    estimated_prompt_tokens: int = 0
    estimated_completion_tokens: int = 0
    estimated_total_tokens: int = 0
    estimated_cost_usd: Optional[float] = None
    is_exact_cost: bool = False
    pricing_available: bool = True
    cost_note: str = "Token and cost figures are estimates based on character/token heuristics and published rates."


class RoutingFallbackAttempt(BaseModel):
    provider: str
    model_id: str
    reason: str
    error_code: Optional[str] = None
    latency_ms: float = 0.0


class RoutingDecision(BaseModel):
    id: str
    task_category: RoutingTaskCategory
    required_capabilities: List[RoutingTaskCategory] = Field(default_factory=list)
    routing_preference: RoutingPreference = "balanced"
    selected_provider: str
    selected_model: str
    selection_rationale: str
    fallback_chain: List[str] = Field(default_factory=list)
    fallback_attempts: List[RoutingFallbackAttempt] = Field(default_factory=list)
    used_fallback: bool = False
    is_configured: bool = False
    cost_estimate: TokenCostEstimate
    budget_allowed: bool = True
    budget_warning: Optional[str] = None
    security_policy_enforced: bool = True
    prompt_injection_override_blocked: bool = False
    decided_at: datetime = Field(default_factory=utc_now)


class RoutingPolicyConfig(BaseModel):
    routing_preference: RoutingPreference = "balanced"
    default_provider: str = "auto"
    default_model: str = "gemini-1.5-flash"
    max_fallbacks: int = Field(default=2, ge=0, le=5)
    daily_spending_limit_usd: float = Field(default=10.0, ge=0.0)
    per_request_max_cost_usd: float = Field(default=0.50, ge=0.0)
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0)
    allow_paid_frontier_models: bool = True


class RoutingTelemetryEntry(BaseModel):
    id: str
    task_category: RoutingTaskCategory
    routing_preference: RoutingPreference
    selected_provider: str
    selected_model: str
    used_fallback: bool = False
    fallback_count: int = 0
    success: bool = True
    error_category: Optional[str] = None
    latency_ms: float = 0.0
    estimated_tokens: int = 0
    estimated_cost_usd: float = 0.0
    timestamp: datetime = Field(default_factory=utc_now)


class RoutingUsageSummary(BaseModel):
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    fallback_triggered_count: int = 0
    total_estimated_tokens: int = 0
    total_estimated_cost_usd: float = 0.0
    daily_spending_limit_usd: float = 10.0
    remaining_daily_budget_usd: float = 10.0
    average_latency_ms: float = 0.0
    by_provider: Dict[str, int] = Field(default_factory=dict)
    by_category: Dict[str, int] = Field(default_factory=dict)
    by_model: Dict[str, int] = Field(default_factory=dict)
    recent_telemetry: List[RoutingTelemetryEntry] = Field(default_factory=list)
    disclaimer: str = "All token and cost metrics are estimates and do not represent billing invoices."


class RoutingSimulateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=16000)
    task_category: Optional[RoutingTaskCategory] = None
    required_capabilities: List[RoutingTaskCategory] = Field(default_factory=list)
    routing_preference: Optional[RoutingPreference] = None
    preferred_provider: Optional[str] = "auto"
    preferred_model: Optional[str] = "auto"
    has_images: bool = False
    has_documents: bool = False
    expected_output_tokens: int = Field(default=500, ge=10, le=8192)


class RoutingExecuteRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=16000)
    task_category: Optional[RoutingTaskCategory] = None
    required_capabilities: List[RoutingTaskCategory] = Field(default_factory=list)
    routing_preference: Optional[RoutingPreference] = None
    preferred_provider: Optional[str] = "auto"
    preferred_model: Optional[str] = "auto"
    has_images: bool = False
    has_documents: bool = False
    expected_output_tokens: int = Field(default=500, ge=10, le=8192)
    client_api_key: Optional[str] = None


class RoutingExecuteResponse(BaseModel):
    decision: RoutingDecision
    response: ChatResponse
    latency_ms: float


# --- Stage 13: Persistent Memory Engine Schemas ---
MemoryCategory = Literal[
    "preferences",
    "profile",
    "project_context",
    "conversation_summaries",
    "temporary_context",
]


class MemoryItem(BaseModel):
    id: str
    user_id: str = "default_user"
    category: MemoryCategory = "profile"
    key: str
    content: str
    tags: List[str] = Field(default_factory=list)
    pinned: bool = False
    is_temporary: bool = False
    encrypted_at_rest: bool = True
    source: str = "user_explicit"
    relevance_score: Optional[float] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MemoryCreateRequest(BaseModel):
    user_id: str = Field(default="default_user", min_length=1, max_length=120)
    category: Optional[MemoryCategory] = None
    key: Optional[str] = None
    content: str = Field(..., min_length=1, max_length=4000)
    tags: List[str] = Field(default_factory=list)
    pinned: bool = False
    source: str = "user_explicit"
    confirmed: bool = True


class MemoryUpdateRequest(BaseModel):
    user_id: str = Field(default="default_user", min_length=1, max_length=120)
    category: Optional[MemoryCategory] = None
    key: Optional[str] = None
    content: Optional[str] = Field(default=None, min_length=1, max_length=4000)
    tags: Optional[List[str]] = None
    pinned: Optional[bool] = None


class MemorySearchRequest(BaseModel):
    user_id: str = "default_user"
    query: str = ""
    category: Optional[MemoryCategory] = None
    include_temporary: bool = True
    top_k: int = Field(default=10, ge=1, le=100)


class MemorySearchResponse(BaseModel):
    user_id: str
    query: str
    total_matched: int = 0
    total_count: int = 0
    memories: List[MemoryItem]
    memory_enabled: bool = True
    storage_backend: str = "sqlite3"
    external_provider_disclosure: str = (
        "Retrieved memories are injected inside <user_memory_context> tags as contextual data only "
        "and are transmitted to the selected external AI provider only when generating a response."
    )


class MemoryCommandRequest(BaseModel):
    user_id: str = "default_user"
    text: str = Field(..., min_length=1, max_length=4000)
    confirm_ambiguous: bool = False
    temporary_chat: bool = False


class MemoryCommandResponse(BaseModel):
    action_taken: Literal[
        "saved",
        "deleted",
        "listed",
        "confirmation_required",
        "rejected_sensitive",
        "memory_disabled_or_temp",
        "no_command_detected",
    ]
    message: str
    affected_memories: List[MemoryItem] = Field(default_factory=list)
    requires_confirmation: bool = False
    pending_candidate: Optional[Dict[str, Any]] = None


class MemoryPrivacySettings(BaseModel):
    user_id: str = "default_user"
    memory_enabled: bool = True
    temporary_chat_mode: bool = False
    auto_summarize_conversations: bool = False
    encrypt_at_rest: bool = True
    block_sensitive_pii: bool = True


class MemoryStatusSummary(BaseModel):
    user_id: str
    storage_backend: str = "sqlite3"
    db_healthy: bool = True
    schema_version: int = 1
    settings: MemoryPrivacySettings
    total_persistent_memories: int = 0
    total_temporary_memories: int = 0
    pinned_count: int = 0
    by_category: Dict[str, int] = Field(default_factory=dict)
    external_provider_disclosure: str = (
        "Saved memories are stored locally in encrypted SQLite storage. When Memory is enabled, "
        "relevant memories may be sent as read-only context to your configured AI provider."
    )


# --- Stage 14: Multi-Agent Intelligence System Schemas ---
AgentRoleId = Literal[
    "research_agent",
    "coding_agent",
    "education_agent",
    "writing_agent",
    "data_analyst_agent",
    "productivity_agent",
    "document_agent",
    "language_agent",
]

AgentPermissionScope = Literal[
    "read_only",
    "search_and_retrieve",
    "document_read",
    "workspace_write_requires_approval",
]

AgentTaskStatus = Literal[
    "PLANNED",
    "RUNNING",
    "WAITING_APPROVAL",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
]


class SpecializedAgentSpec(BaseModel):
    agent_id: AgentRoleId
    name: str
    purpose: str
    capabilities: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    permission_scope: AgentPermissionScope = "read_only"
    allowed_tools: List[str] = Field(default_factory=list)
    requires_approval_for: List[str] = Field(default_factory=list)
    preferred_task_category: RoutingTaskCategory = "general_chat"
    available: bool = True
    unavailable_reason: Optional[str] = None


class AgentStructuredFinding(BaseModel):
    facts: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    citations: List[Dict[str, str]] = Field(default_factory=list)
    file_references: List[str] = Field(default_factory=list)


class AgentSubtaskRun(BaseModel):
    subtask_id: str
    agent_id: AgentRoleId
    agent_name: str
    title: str
    instruction: str
    depends_on: List[str] = Field(default_factory=list)
    can_run_parallel: bool = False
    status: AgentTaskStatus = "PLANNED"
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    approved: Optional[bool] = None
    tools_invoked: List[str] = Field(default_factory=list)
    output_summary: str = ""
    structured_finding: AgentStructuredFinding = Field(default_factory=AgentStructuredFinding)
    error_message: Optional[str] = None
    retry_count: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: float = 0.0


class MultiAgentOrchestrationRun(BaseModel):
    run_id: str
    user_id: str = "default_user"
    goal: str
    selection_mode: Literal["auto", "manual"] = "auto"
    selected_agents: List[AgentRoleId] = Field(default_factory=list)
    execution_mode: Literal["sequential", "parallel_safe", "hybrid"] = "sequential"
    status: AgentTaskStatus = "PLANNED"
    plan_summary: str = ""
    subtasks: List[AgentSubtaskRun] = Field(default_factory=list)
    combined_response: str = ""
    consolidated_facts: List[str] = Field(default_factory=list)
    consolidated_assumptions: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    conflicts_detected: List[str] = Field(default_factory=list)
    citations: List[Dict[str, str]] = Field(default_factory=list)
    file_references: List[str] = Field(default_factory=list)
    used_memories: List[Dict[str, Any]] = Field(default_factory=list)
    duplicate_tool_calls_prevented: int = 0
    total_estimated_cost_usd: float = 0.0
    max_cost_budget_usd: float = 0.25
    total_latency_ms: float = 0.0
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MultiAgentRunRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=16000)
    user_id: str = "default_user"
    selection_mode: Literal["auto", "manual"] = "auto"
    manual_agents: List[AgentRoleId] = Field(default_factory=list)
    document_ids: List[str] = Field(default_factory=list)
    target_language: str = "en"
    allow_parallel: bool = True
    max_cost_usd: Optional[float] = Field(default=None, ge=0.001, le=10.0)
    memory_enabled: bool = True
    conversation_context: List[Message] = Field(default_factory=list)
    provider: Optional[str] = "auto"
    model: Optional[str] = "auto"
    client_api_key: Optional[str] = None


class MultiAgentApproveRequest(BaseModel):
    subtask_id: str
    approved: bool = True
    user_note: Optional[str] = None
    provider: Optional[str] = "auto"
    model: Optional[str] = "auto"
    client_api_key: Optional[str] = None


class MultiAgentRetryRequest(BaseModel):
    subtask_id: Optional[str] = None
    provider: Optional[str] = "auto"
    model: Optional[str] = "auto"
    client_api_key: Optional[str] = None


# --- Stage 15: Workflow Automation Engine Schemas ---
WorkflowStatus = Literal["DRAFT", "ACTIVE", "PAUSED", "DISABLED"]
WorkflowTriggerType = Literal["manual", "scheduled"]
WorkflowRecurrenceType = Literal["once", "interval", "hourly", "daily", "weekly"]
WorkflowRunStatus = Literal[
    "QUEUED",
    "RUNNING",
    "WAITING_FOR_APPROVAL",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
    "RETRYING",
]
WorkflowStepStatus = Literal[
    "PENDING",
    "RUNNING",
    "WAITING_FOR_APPROVAL",
    "SUCCEEDED",
    "FAILED",
    "SKIPPED",
    "CANCELLED",
    "RETRYING",
]
WorkflowStepActionType = Literal["agent", "tool", "condition_gate", "transform"]
WorkflowBranchAction = Literal["skip", "fail_workflow", "jump_to_step"]


class WorkflowScheduleConfig(BaseModel):
    trigger_type: WorkflowTriggerType = "manual"
    recurrence: WorkflowRecurrenceType = "daily"
    interval_minutes: int = Field(default=60, ge=1, le=10080)
    timezone: str = "UTC"
    start_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    allow_concurrent_runs: bool = False


class WorkflowStepDefinition(BaseModel):
    step_id: str
    name: str
    description: str = ""
    action_type: WorkflowStepActionType = "agent"
    agent_id: Optional[AgentRoleId] = None
    tool_name: Optional[str] = None
    prompt_template: str = ""
    tool_params: Dict[str, Any] = Field(default_factory=dict)
    input_mapping: Dict[str, str] = Field(default_factory=dict)
    output_key: str = "output"
    depends_on: List[str] = Field(default_factory=list)
    condition_expression: str = "always"
    on_condition_false: WorkflowBranchAction = "skip"
    jump_to_step_id: Optional[str] = None
    max_retries: int = Field(default=1, ge=0, le=5)
    retry_delay_seconds: float = Field(default=0.1, ge=0.0, le=60.0)
    timeout_seconds: float = Field(default=25.0, ge=0.1, le=120.0)
    requires_approval: bool = False
    approval_reason: Optional[str] = None


class WorkflowNotificationConfig(BaseModel):
    in_app_enabled: bool = True
    email_opt_in: bool = False
    email_recipient: Optional[str] = None
    webhook_opt_in: bool = False
    notify_on_complete: bool = True
    notify_on_failure: bool = True
    notify_on_approval_required: bool = True


class WorkflowDefinition(BaseModel):
    workflow_id: str
    user_id: str = "default_user"
    name: str
    description: str = ""
    category: str = "general"
    status: WorkflowStatus = "DRAFT"
    is_template: bool = False
    schedule: WorkflowScheduleConfig = Field(default_factory=WorkflowScheduleConfig)
    steps: List[WorkflowStepDefinition] = Field(default_factory=list)
    notification_config: WorkflowNotificationConfig = Field(default_factory=WorkflowNotificationConfig)
    max_cost_budget_usd: float = Field(default=0.50, ge=0.001, le=10.0)
    total_runs: int = 0
    succeeded_runs: int = 0
    failed_runs: int = 0
    last_run_status: Optional[WorkflowRunStatus] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class WorkflowValidationIssue(BaseModel):
    severity: Literal["error", "warning"] = "error"
    step_id: Optional[str] = None
    code: str
    message: str


class WorkflowValidationResult(BaseModel):
    valid: bool
    issues: List[WorkflowValidationIssue] = Field(default_factory=list)
    execution_order: List[str] = Field(default_factory=list)
    estimated_max_cost_usd: float = 0.0
    requires_approval_steps: List[str] = Field(default_factory=list)


class WorkflowStepExecutionResult(BaseModel):
    step_id: str
    step_name: str
    action_type: WorkflowStepActionType
    agent_id: Optional[AgentRoleId] = None
    tool_name: Optional[str] = None
    status: WorkflowStepStatus = "PENDING"
    resolved_inputs: Dict[str, Any] = Field(default_factory=dict)
    output_summary: str = ""
    output_data: Dict[str, Any] = Field(default_factory=dict)
    untrusted_content_isolated: bool = False
    condition_evaluated: bool = True
    condition_detail: str = ""
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    approved: Optional[bool] = None
    attempt_count: int = 0
    max_retries: int = 0
    error_message: Optional[str] = None
    estimated_cost_usd: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0


class WorkflowExecutionRun(BaseModel):
    run_id: str
    workflow_id: str
    workflow_name: str
    user_id: str = "default_user"
    trigger_source: Literal["manual", "scheduled", "test_dry_run", "retry"] = "manual"
    idempotency_key: Optional[str] = None
    status: WorkflowRunStatus = "QUEUED"
    is_dry_run: bool = False
    runtime_inputs: Dict[str, Any] = Field(default_factory=dict)
    step_results: List[WorkflowStepExecutionResult] = Field(default_factory=list)
    completed_steps: int = 0
    total_steps: int = 0
    progress_percent: float = 0.0
    current_step_id: Optional[str] = None
    waiting_approval_step_id: Optional[str] = None
    final_summary: str = ""
    error_message: Optional[str] = None
    total_estimated_cost_usd: float = 0.0
    max_cost_budget_usd: float = 0.50
    queued_at: datetime = Field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0


class WorkflowNotificationItem(BaseModel):
    notification_id: str
    user_id: str = "default_user"
    workflow_id: str
    workflow_name: str
    run_id: Optional[str] = None
    event_type: Literal[
        "run_succeeded",
        "run_failed",
        "approval_required",
        "schedule_triggered",
        "run_cancelled",
        "worker_recovery",
    ]
    severity: Literal["info", "success", "warning", "error"] = "info"
    title: str
    message: str
    read: bool = False
    external_channels_attempted: List[str] = Field(default_factory=list)
    external_delivery_status: str = "in_app_only"
    external_delivery_confirmed: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class WorkflowCreateRequest(BaseModel):
    user_id: str = "default_user"
    name: str = Field(..., min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    category: str = "general"
    status: WorkflowStatus = "DRAFT"
    schedule: WorkflowScheduleConfig = Field(default_factory=WorkflowScheduleConfig)
    steps: List[WorkflowStepDefinition] = Field(default_factory=list)
    notification_config: WorkflowNotificationConfig = Field(default_factory=WorkflowNotificationConfig)
    max_cost_budget_usd: float = Field(default=0.50, ge=0.001, le=10.0)


class WorkflowUpdateRequest(BaseModel):
    user_id: str = "default_user"
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    description: Optional[str] = Field(default=None, max_length=2000)
    category: Optional[str] = None
    status: Optional[WorkflowStatus] = None
    schedule: Optional[WorkflowScheduleConfig] = None
    steps: Optional[List[WorkflowStepDefinition]] = None
    notification_config: Optional[WorkflowNotificationConfig] = None
    max_cost_budget_usd: Optional[float] = Field(default=None, ge=0.001, le=10.0)


class WorkflowTriggerRunRequest(BaseModel):
    user_id: str = "default_user"
    trigger_source: Literal["manual", "scheduled", "test_dry_run"] = "manual"
    is_dry_run: bool = False
    runtime_inputs: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None
    provider: Optional[str] = "auto"
    model: Optional[str] = "auto"
    client_api_key: Optional[str] = None


class WorkflowApproveStepRequest(BaseModel):
    user_id: str = "default_user"
    step_id: str
    approved: bool = True
    user_note: Optional[str] = None
    provider: Optional[str] = "auto"
    model: Optional[str] = "auto"
    client_api_key: Optional[str] = None


class WorkflowRetryRunRequest(BaseModel):
    user_id: str = "default_user"
    from_failed_step_only: bool = True
    provider: Optional[str] = "auto"
    model: Optional[str] = "auto"
    client_api_key: Optional[str] = None


# --- Stage 16: Computer Control & Digital Execution Engine Schemas ---
ComputerTargetDomain = Literal["browser", "local_os"]

ComputerActionType = Literal[
    # Browser Automation Actions
    "open_url",
    "navigate",
    "click",
    "fill_text",
    "select_option",
    "scroll",
    "capture_screenshot",
    "extract_content",
    "submit_form",
    # Sandboxed Local Computer Actions
    "list_workspace_files",
    "read_workspace_file",
    "write_workspace_file",
    "delete_workspace_file",
    "run_predefined_diagnostic",
    "open_approved_application",
]

ComputerSessionStatus = Literal[
    "PLANNED",
    "SIMULATION_PREVIEW",
    "WAITING_FOR_APPROVAL",
    "RUNNING",
    "PAUSED",
    "VERIFIED_COMPLETED",
    "BLOCKED_BY_SECURITY_BOUNDARY",
    "FAILED",
    "CANCELLED",
]

ComputerStepStatus = Literal[
    "PENDING",
    "SIMULATED",
    "WAITING_FOR_APPROVAL",
    "RUNNING",
    "VERIFIED_SUCCEEDED",
    "BLOCKED",
    "FAILED",
    "CANCELLED",
]


class ComputerActionPreview(BaseModel):
    step_id: str
    action_type: ComputerActionType
    target_domain: ComputerTargetDomain
    target_resource: str
    risk_level: Literal["low", "medium", "high"] = "low"
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    parameters_preview: Dict[str, Any] = Field(default_factory=dict)


class ComputerActionStep(BaseModel):
    step_id: str
    title: str
    target_domain: ComputerTargetDomain = "browser"
    action_type: ComputerActionType = "open_url"
    target_url_or_path: str = ""
    selector: Optional[str] = None
    input_value: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    checkpoint_name: Optional[str] = None
    timeout_seconds: float = Field(default=15.0, ge=1.0, le=60.0)


class ComputerStepResult(BaseModel):
    step_id: str
    title: str
    target_domain: ComputerTargetDomain
    action_type: ComputerActionType
    target_url_or_path: str = ""
    selector: Optional[str] = None
    status: ComputerStepStatus = "PENDING"
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    approved: Optional[bool] = None
    preview: Optional[ComputerActionPreview] = None
    verified: bool = False
    verification_detail: str = ""
    output_summary: str = ""
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    screenshot_base64: Optional[str] = None
    page_title: Optional[str] = None
    current_url: Optional[str] = None
    security_boundary_triggered: Optional[str] = None
    untrusted_content_isolated: bool = False
    error_message: Optional[str] = None
    duration_ms: float = 0.0
    executed_at: Optional[datetime] = None


class ComputerExecutionSession(BaseModel):
    session_id: str
    user_id: str = "default_user"
    goal: str
    mode: Literal["execute", "simulate_only"] = "execute"
    target_domain: ComputerTargetDomain = "browser"
    browser_driver: str = "dom_http_pillow_driver"
    status: ComputerSessionStatus = "PLANNED"
    target_website: Optional[str] = None
    active_step_id: Optional[str] = None
    waiting_approval_step_id: Optional[str] = None
    steps: List[ComputerActionStep] = Field(default_factory=list)
    step_results: List[ComputerStepResult] = Field(default_factory=list)
    checkpoints: List[str] = Field(default_factory=list)
    latest_screenshot_base64: Optional[str] = None
    execution_logs: List[str] = Field(default_factory=list)
    final_summary: str = ""
    verified_completion: bool = False
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ComputerAuditLogEntry(BaseModel):
    audit_id: str
    session_id: str
    user_id: str
    step_id: Optional[str] = None
    target_domain: ComputerTargetDomain
    action_type: str
    target_resource: str
    status: str
    verified: bool = False
    detail: str
    created_at: datetime = Field(default_factory=utc_now)


class ComputerSessionCreateRequest(BaseModel):
    user_id: str = "default_user"
    goal: str = Field(..., min_length=1, max_length=4000)
    mode: Literal["execute", "simulate_only"] = "execute"
    target_domain: ComputerTargetDomain = "browser"
    target_url: Optional[str] = None
    steps: List[ComputerActionStep] = Field(default_factory=list)
    custom_allowed_domains: List[str] = Field(default_factory=list)
    auto_start: bool = True


class ComputerApproveStepRequest(BaseModel):
    user_id: str = "default_user"
    step_id: str
    approved: bool = True
    user_note: Optional[str] = None


# --- Stage 17: File Management & Workspace Automation Engine Schemas ---
FileCategory = Literal[
    "document",
    "spreadsheet",
    "data",
    "markdown_text",
    "code",
    "image",
    "folder",
    "other",
]

FileOperationType = Literal[
    "create_folder",
    "create_file",
    "edit_file",
    "rename_item",
    "copy_item",
    "move_item",
    "convert_file",
    "delete_to_trash",
    "restore_from_trash",
    "restore_version",
    "organize_workspace",
    "cleanup_duplicates",
    "sync_stage4_vault",
    "import_browser_session",
]

FileOperationStatus = Literal[
    "PLANNED",
    "SIMULATED",
    "WAITING_FOR_APPROVAL",
    "RUNNING",
    "VERIFIED_SUCCEEDED",
    "ROLLED_BACK",
    "FAILED",
    "CANCELLED",
]

OrganizeRuleStrategy = Literal[
    "by_category",
    "by_extension",
    "by_date_month",
    "custom_rules",
]


class WorkspaceFileItem(BaseModel):
    relative_path: str
    name: str
    parent_dir: str = ""
    is_dir: bool = False
    extension: str = ""
    category: FileCategory = "other"
    size_bytes: int = 0
    sha256_hash: Optional[str] = None
    modified_at: datetime = Field(default_factory=utc_now)
    is_editable_text: bool = False
    is_processable_document: bool = False
    supported_conversions: List[str] = Field(default_factory=list)
    version_count: int = 0
    indexed_doc_id: Optional[str] = None
    snippet_match: Optional[str] = None


class WorkspaceFileReadResponse(BaseModel):
    item: WorkspaceFileItem
    content: str = ""
    quarantined_content: str = ""
    untrusted_content_isolated: bool = True
    parsed_summary: Optional[Dict[str, Any]] = None
    tables_preview: List[Dict[str, Any]] = Field(default_factory=list)
    versions: List["WorkspaceFileVersion"] = Field(default_factory=list)


class WorkspaceFileVersion(BaseModel):
    version_id: str
    user_id: str = "default_user"
    relative_path: str
    version_number: int
    sha256_hash: str
    size_bytes: int
    reason: str = "auto_backup_before_edit"
    created_at: datetime = Field(default_factory=utc_now)


class WorkspaceTrashItem(BaseModel):
    trash_id: str
    user_id: str = "default_user"
    original_path: str
    name: str
    is_dir: bool = False
    size_bytes: int = 0
    sha256_hash: Optional[str] = None
    reason: str = "user_deleted"
    deleted_at: datetime = Field(default_factory=utc_now)


class DuplicateFileGroup(BaseModel):
    sha256_hash: str
    size_bytes: int
    duplicate_count: int
    wasted_bytes: int
    primary_file: str
    duplicate_files: List[str] = Field(default_factory=list)


class FilePlannedChange(BaseModel):
    action: str
    source_path: str
    destination_path: Optional[str] = None
    size_bytes: int = 0
    reason: str = ""
    overwrites_existing: bool = False


class FileOperationPreview(BaseModel):
    operation_type: FileOperationType
    risk_level: Literal["low", "medium", "high"] = "low"
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    affected_count: int = 0
    total_bytes_affected: int = 0
    planned_changes: List[FilePlannedChange] = Field(default_factory=list)
    rollback_supported: bool = True


class FileOperationRecord(BaseModel):
    operation_id: str
    user_id: str = "default_user"
    operation_type: FileOperationType
    status: FileOperationStatus = "PLANNED"
    summary: str = ""
    verified: bool = False
    verification_detail: str = ""
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    approved: Optional[bool] = None
    preview: Optional[FileOperationPreview] = None
    affected_paths: List[str] = Field(default_factory=list)
    result_data: Dict[str, Any] = Field(default_factory=dict)
    rollback_supported: bool = False
    rolled_back: bool = False
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class FileCreateFolderRequest(BaseModel):
    user_id: str = "default_user"
    relative_path: str = Field(..., min_length=1, max_length=260)


class FileWriteRequest(BaseModel):
    user_id: str = "default_user"
    relative_path: str = Field(..., min_length=1, max_length=260)
    content: str = Field(default="", max_length=2_000_000)
    structured_rows: Optional[List[Dict[str, Any]]] = None
    overwrite: bool = False
    confirmed_overwrite: bool = False
    backup_reason: str = "edit_preserve_original"


class FileTransferRequest(BaseModel):
    user_id: str = "default_user"
    action: Literal["rename", "copy", "move"] = "rename"
    source_path: str = Field(..., min_length=1, max_length=260)
    destination_path: str = Field(..., min_length=1, max_length=260)
    overwrite: bool = False
    confirmed_overwrite: bool = False


class FileConvertRequest(BaseModel):
    user_id: str = "default_user"
    source_path: str = Field(..., min_length=1, max_length=260)
    target_format: Literal["txt", "md", "csv", "json", "docx", "xlsx"]
    destination_path: Optional[str] = None
    overwrite: bool = False
    confirmed_overwrite: bool = False


class FileSearchRequest(BaseModel):
    user_id: str = "default_user"
    query: str = ""
    directory: str = ""
    extensions: List[str] = Field(default_factory=list)
    category: Optional[FileCategory] = None
    search_content: bool = True
    include_stage4_indexed: bool = True
    modified_after: Optional[datetime] = None
    modified_before: Optional[datetime] = None
    min_size_bytes: Optional[int] = None
    max_size_bytes: Optional[int] = None


class FileOrganizeRequest(BaseModel):
    user_id: str = "default_user"
    directory: str = ""
    strategy: OrganizeRuleStrategy = "by_category"
    custom_extension_map: Dict[str, str] = Field(default_factory=dict)
    preview_only: bool = False
    confirmed: bool = False


class FileDeleteRequest(BaseModel):
    user_id: str = "default_user"
    paths: List[str] = Field(..., min_length=1)
    reason: str = "user_requested_cleanup"
    preview_only: bool = False
    confirmed: bool = False


class FileDuplicateCleanupRequest(BaseModel):
    user_id: str = "default_user"
    directory: str = ""
    preview_only: bool = False
    confirmed: bool = False


class FileOperationApproveRequest(BaseModel):
    user_id: str = "default_user"
    approved: bool = True
    user_note: Optional[str] = None


class FileBrowserImportRequest(BaseModel):
    user_id: str = "default_user"
    session_id: str
    target_filename: str = "browser_capture.md"
    overwrite: bool = True
    confirmed_overwrite: bool = True


# ============================================================================
# Stage 18: Terminal & Code Execution Engine Schemas
# ============================================================================

CodeLanguage = Literal["python", "javascript", "typescript", "html", "css", "json", "markdown"]
ProjectTemplateType = Literal["python", "javascript", "typescript", "web"]

TerminalExecutionStatus = Literal[
    "PLANNED",
    "WAITING_FOR_APPROVAL",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    "TIMED_OUT",
    "BLOCKED",
    "CANCELLED",
]

CommandRiskClassification = Literal[
    "allowed_safe",
    "requires_approval",
    "blocked_forbidden",
]


class CodeProjectFile(BaseModel):
    relative_path: str
    name: str
    language: CodeLanguage = "python"
    size_bytes: int = 0
    sha256_hash: str = ""
    modified_at: datetime = Field(default_factory=utc_now)
    backup_count: int = 0
    content: Optional[str] = None


class CodeFileBackup(BaseModel):
    backup_id: str
    user_id: str = "default_user"
    project_id: str
    relative_path: str
    version_number: int
    sha256_hash: str
    size_bytes: int
    reason: str = "pre_edit_backup"
    created_at: datetime = Field(default_factory=utc_now)


class CodeProjectSummary(BaseModel):
    project_id: str
    user_id: str = "default_user"
    name: str
    description: str = ""
    template: ProjectTemplateType = "python"
    primary_language: CodeLanguage = "python"
    entrypoint: str = "main.py"
    test_entrypoint: str = "test_main.py"
    file_count: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    files: List[CodeProjectFile] = Field(default_factory=list)


class CodeDiagnosticIssue(BaseModel):
    line: int = 1
    column: int = 1
    severity: Literal["error", "warning", "info"] = "error"
    code: str = "SYNTAX"
    message: str
    rule_source: str = "ast_checker"
    suggestion: Optional[str] = None


class DependencyStatusItem(BaseModel):
    package_name: str
    ecosystem: Literal["pip", "npm", "builtin"] = "pip"
    installed: bool = True
    version: Optional[str] = None
    imported_in: List[str] = Field(default_factory=list)
    install_command: Optional[str] = None
    setup_explanation: str = ""


class CodeInspectionResult(BaseModel):
    project_id: str
    relative_path: str
    language: CodeLanguage
    syntax_valid: bool = True
    formatted_content: Optional[str] = None
    formatting_changed: bool = False
    diagnostics: List[CodeDiagnosticIssue] = Field(default_factory=list)
    dependencies: List[DependencyStatusItem] = Field(default_factory=list)
    missing_dependencies_count: int = 0
    untrusted_instruction_warnings: List[str] = Field(default_factory=list)
    summary: str = ""


class TestCaseResult(BaseModel):
    name: str
    status: Literal["passed", "failed", "error", "skipped"] = "passed"
    duration_ms: float = 0.0
    message: Optional[str] = None


class TestSuiteResult(BaseModel):
    framework: str = "pytest"
    executed: bool = False
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    total: int = 0
    all_passed: bool = False
    cases: List[TestCaseResult] = Field(default_factory=list)
    raw_summary: str = ""


class CommandPreview(BaseModel):
    raw_command: str
    normalized_command: str
    classification: CommandRiskClassification = "allowed_safe"
    risk_level: Literal["low", "medium", "high", "critical"] = "low"
    target_workspace: str = ""
    expected_effect: str = ""
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    blocked_reason: Optional[str] = None


class TerminalExecutionRecord(BaseModel):
    execution_id: str
    user_id: str = "default_user"
    project_id: str
    execution_type: Literal[
        "run_code",
        "run_tests",
        "terminal_command",
        "syntax_check",
        "debug_repair",
    ] = "run_code"
    command_preview: CommandPreview
    status: TerminalExecutionStatus = "PLANNED"
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    output_truncated: bool = False
    timed_out: bool = False
    duration_ms: float = 0.0
    memory_limit_mb: int = 128
    network_enabled: bool = False
    verified_execution: bool = False
    approved: Optional[bool] = None
    test_results: Optional[TestSuiteResult] = None
    error_diagnosis: Optional[str] = None
    suggested_fix: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: Optional[datetime] = None


class RepairIterationStep(BaseModel):
    attempt_number: int
    failure_type: str
    diagnosis: str
    proposed_patch_summary: str
    backup_id: Optional[str] = None
    applied: bool = False
    execution_id: Optional[str] = None
    exit_code: Optional[int] = None
    tests_passed: bool = False
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""


class DebugRepairResponse(BaseModel):
    repair_id: str
    user_id: str = "default_user"
    project_id: str
    target_file: str
    initial_error: str = ""
    status: Literal[
        "REPAIRED_AND_VERIFIED",
        "MAX_ATTEMPTS_REACHED",
        "REQUIRES_USER_INTERVENTION",
        "NO_FAILURE_DETECTED",
    ] = "REPAIRED_AND_VERIFIED"
    attempts_used: int = 0
    max_attempts: int = 3
    final_verified: bool = False
    intervention_reason: Optional[str] = None
    explanation: str = ""
    iterations: List[RepairIterationStep] = Field(default_factory=list)
    final_execution: Optional[TerminalExecutionRecord] = None


class CreateCodeProjectRequest(BaseModel):
    user_id: str = "default_user"
    name: str = Field(..., min_length=1, max_length=80)
    description: str = Field(default="", max_length=400)
    template: ProjectTemplateType = "python"


class SaveCodeFileRequest(BaseModel):
    user_id: str = "default_user"
    relative_path: str = Field(..., min_length=1, max_length=200)
    content: str = Field(default="", max_length=1_000_000)
    create_backup: bool = True
    backup_reason: str = "editor_save"


class CodeInspectRequest(BaseModel):
    user_id: str = "default_user"
    project_id: str
    relative_path: str = "main.py"
    content: Optional[str] = None
    apply_formatting: bool = False


class CodeExecuteRequest(BaseModel):
    user_id: str = "default_user"
    project_id: str
    target_file: Optional[str] = None
    mode: Literal["run", "test"] = "run"
    args: List[str] = Field(default_factory=list)
    stdin_text: str = ""
    timeout_seconds: Optional[float] = None
    allow_network: bool = False
    confirmed_network: bool = False


class TerminalCommandRequest(BaseModel):
    user_id: str = "default_user"
    project_id: str
    command: str = Field(..., min_length=1, max_length=600)
    timeout_seconds: Optional[float] = None
    allow_network: bool = False
    confirmed: bool = False
    preview_only: bool = False


class TerminalApproveRequest(BaseModel):
    user_id: str = "default_user"
    approved: bool = True
    user_note: Optional[str] = None


class DebugRepairRequest(BaseModel):
    user_id: str = "default_user"
    project_id: str
    target_file: str = "main.py"
    run_tests: bool = True
    max_attempts: int = Field(default=3, ge=1, le=5)
    auto_apply: bool = True


class SyncStage17Request(BaseModel):
    user_id: str = "default_user"
    direction: Literal["to_stage17", "from_stage17"] = "to_stage17"
    relative_path: Optional[str] = None


# ============================================================================
# Stage 19: Git & Version Control Engine Schemas
# ============================================================================

GitOperationType = Literal[
    "init_repo",
    "stage_files",
    "unstage_files",
    "commit",
    "create_branch",
    "switch_branch",
    "merge_branch",
    "configure_remote",
    "sync_remote",
    "discard_changes",
    "update_gitignore",
    "create_pull_request",
]

GitOperationStatus = Literal[
    "PLANNED",
    "WAITING_FOR_APPROVAL",
    "SUCCEEDED",
    "FAILED",
    "BLOCKED",
    "CANCELLED",
]

GitRemoteProvider = Literal["github", "gitlab", "bitbucket", "custom"]


class GitChangedFile(BaseModel):
    path: str
    index_status: str = " "
    worktree_status: str = " "
    staged: bool = False
    unstaged: bool = False
    untracked: bool = False
    has_secret_warning: bool = False
    secret_warning_detail: Optional[str] = None
    is_sensitive_env_file: bool = False


class GitBranchInfo(BaseModel):
    name: str
    is_current: bool = False
    commit_hash: str = ""
    last_commit_subject: str = ""


class GitCommitEntry(BaseModel):
    commit_hash: str
    short_hash: str
    author_name: str
    author_email: str
    authored_at: str
    subject: str
    body: str = ""
    files_changed: int = 0


class GitRemoteConfig(BaseModel):
    name: str = "origin"
    url: str = ""
    provider: GitRemoteProvider = "github"
    token_configured: bool = False
    sync_status: Literal[
        "not_configured",
        "local_only",
        "auth_required",
        "network_disabled",
        "ready_to_sync",
        "synced",
        "sync_failed",
    ] = "not_configured"
    ahead_count: int = 0
    behind_count: int = 0
    last_error: Optional[str] = None


class GitSideBySideLine(BaseModel):
    left_line_no: Optional[int] = None
    left_content: str = ""
    right_line_no: Optional[int] = None
    right_content: str = ""
    change_type: Literal["context", "add", "delete", "modify"] = "context"


class GitFileDiff(BaseModel):
    file_path: str
    additions: int = 0
    deletions: int = 0
    is_binary: bool = False
    unified_patch: str = ""
    side_by_side_lines: List[GitSideBySideLine] = Field(default_factory=list)


class GitDiffResponse(BaseModel):
    project_id: str
    target_scope: Literal["unstaged", "staged", "all_working", "branch_compare", "commit"] = "all_working"
    base_ref: Optional[str] = None
    compare_ref: Optional[str] = None
    total_files_changed: int = 0
    total_additions: int = 0
    total_deletions: int = 0
    unified_diff: str = ""
    files: List[GitFileDiff] = Field(default_factory=list)
    secret_warnings: List[str] = Field(default_factory=list)


class GitRepositoryStatusResponse(BaseModel):
    project_id: str
    user_id: str = "default_user"
    git_installed: bool = True
    is_initialized: bool = False
    current_branch: str = "main"
    is_clean: bool = True
    branches: List[GitBranchInfo] = Field(default_factory=list)
    changed_files: List[GitChangedFile] = Field(default_factory=list)
    staged_count: int = 0
    unstaged_count: int = 0
    untracked_count: int = 0
    secret_warnings: List[str] = Field(default_factory=list)
    recommended_gitignore_entries: List[str] = Field(default_factory=list)
    gitignore_present: bool = False
    remotes: List[GitRemoteConfig] = Field(default_factory=list)
    recent_commits: List[GitCommitEntry] = Field(default_factory=list)


class GitCodeReviewFinding(BaseModel):
    finding_id: str
    file_path: str
    line_number: int = 1
    category: Literal["bug", "security", "readability", "missing_tests"] = "bug"
    severity: Literal["critical", "high", "medium", "low"] = "medium"
    finding_type: Literal["verified_defect", "possible_concern"] = "possible_concern"
    title: str
    description: str
    suggested_fix: str
    auto_accepted: bool = False


class GitCodeReviewResponse(BaseModel):
    review_id: str
    project_id: str
    user_id: str = "default_user"
    reviewed_files: List[str] = Field(default_factory=list)
    verified_defects_count: int = 0
    possible_concerns_count: int = 0
    tests_executed: bool = False
    tests_passed: Optional[bool] = None
    findings: List[GitCodeReviewFinding] = Field(default_factory=list)
    summary: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class GitBranchComparisonResponse(BaseModel):
    project_id: str
    base_branch: str
    compare_branch: str
    ahead_count: int = 0
    behind_count: int = 0
    can_fast_forward: bool = True
    has_conflicts: bool = False
    conflict_files: List[str] = Field(default_factory=list)
    commits: List[GitCommitEntry] = Field(default_factory=list)
    diff: GitDiffResponse


class GitPullRequestRecord(BaseModel):
    pr_id: str
    user_id: str = "default_user"
    project_id: str
    title: str
    description: str
    source_branch: str
    target_branch: str = "main"
    issue_references: List[str] = Field(default_factory=list)
    review_summary: str = ""
    provider: GitRemoteProvider = "github"
    status: Literal["LOCAL_DRAFT_ONLY", "WAITING_FOR_APPROVAL", "REMOTE_CONFIRMED", "REMOTE_FAILED"] = "LOCAL_DRAFT_ONLY"
    local_draft_only: bool = True
    remote_confirmed: bool = False
    remote_url: Optional[str] = None
    provider_message: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class GitOperationRecord(BaseModel):
    operation_id: str
    user_id: str = "default_user"
    project_id: str
    operation_type: GitOperationType
    status: GitOperationStatus = "PLANNED"
    command_display: str = ""
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    approved: Optional[bool] = None
    verified: bool = False
    stdout: str = ""
    stderr: str = ""
    diff_preview: Optional[str] = None
    secret_warnings: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    result_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: Optional[datetime] = None


class GitInitRequest(BaseModel):
    user_id: str = "default_user"
    project_id: str
    default_branch: str = "main"
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    create_gitignore: bool = True
    initial_commit: bool = True


class GitStageRequest(BaseModel):
    user_id: str = "default_user"
    project_id: str
    paths: List[str] = Field(default_factory=list)
    stage_all: bool = False
    allow_sensitive: bool = False


class GitCommitRequest(BaseModel):
    user_id: str = "default_user"
    project_id: str
    message: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=2000)
    stage_all: bool = False
    confirmed: bool = False
    allow_secret_override: bool = False


class GitBranchActionRequest(BaseModel):
    user_id: str = "default_user"
    project_id: str
    action: Literal["create", "switch", "merge"] = "create"
    branch_name: str = Field(..., min_length=1, max_length=100)
    source_branch: Optional[str] = None
    checkout_on_create: bool = True
    allow_dirty_switch: bool = False
    confirmed: bool = False


class GitRemoteConfigRequest(BaseModel):
    user_id: str = "default_user"
    project_id: str
    name: str = "origin"
    url: str = Field(..., min_length=1, max_length=400)
    provider: GitRemoteProvider = "github"


class GitRemoteSyncRequest(BaseModel):
    user_id: str = "default_user"
    project_id: str
    remote_name: str = "origin"
    action: Literal["fetch", "pull", "push"] = "push"
    branch: Optional[str] = None
    force: bool = False
    allow_network: bool = False
    confirmed: bool = False


class GitReviewRequest(BaseModel):
    user_id: str = "default_user"
    project_id: str
    paths: List[str] = Field(default_factory=list)
    run_stage18_tests: bool = True


class GitPullRequestCreateRequest(BaseModel):
    user_id: str = "default_user"
    project_id: str
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    source_branch: str
    target_branch: str = "main"
    issue_references: List[str] = Field(default_factory=list)
    submit_to_remote: bool = False
    confirmed: bool = False


class GitApproveOperationRequest(BaseModel):
    user_id: str = "default_user"
    approved: bool = True
    user_note: Optional[str] = None


# ============================================================================
# Stage 20: AI Evaluation & Quality Assurance Engine Schemas
# ============================================================================

EvalSuiteId = Literal[
    "general_qa",
    "web_research",
    "fact_checking",
    "document_rag",
    "multilingual",
    "vision_ocr",
    "voice_speech",
    "coding_sandbox",
    "agents_tools_memory_workflows",
    "security_privacy_safety",
]

EvalRunStatus = Literal[
    "RUNNING",
    "COMPLETED",
    "INCOMPLETE_INTERRUPTED",
    "FAILED_PROVIDER_ERROR",
]

EvalReleaseGateVerdict = Literal[
    "RELEASE_APPROVED",
    "RELEASE_BLOCKED_CRITICAL_FAILURE",
    "RELEASE_BLOCKED_REGRESSION",
    "INCOMPLETE_RUN",
]

EvalCaseSourceType = Literal["curated_benchmark", "synthetic_labeled"]
EvalCaseReviewStatus = Literal["approved", "pending_review", "rejected"]


class EvalMetricScoringRule(BaseModel):
    metric_id: str
    name: str
    range_display: str = "0.0 - 1.0"
    scoring_method: Literal[
        "deterministic_assertion",
        "lexical_overlap",
        "schema_validation",
        "heuristic_rubric",
        "ai_judge_advisory",
        "telemetry_measurement",
    ] = "deterministic_assertion"
    is_definitive_ground_truth: bool = True
    rule_description: str
    limitations: str


class EvalSuiteDefinition(BaseModel):
    suite_id: EvalSuiteId
    name: str
    stage_coverage: str
    description: str
    primary_metrics: List[str] = Field(default_factory=list)
    total_cases: int = 0
    approved_cases: int = 0
    critical_cases: int = 0


class EvalTestCase(BaseModel):
    case_id: str
    suite_id: EvalSuiteId
    title: str
    description: str = ""
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    expected_criteria: Dict[str, Any] = Field(default_factory=dict)
    scoring_rubric: str = ""
    is_edge_case: bool = False
    is_critical: bool = False
    known_limitations: str = ""
    source_type: EvalCaseSourceType = "curated_benchmark"
    review_status: EvalCaseReviewStatus = "approved"
    dataset_version: str = "v1.0.0"
    created_by: str = "system_admin"
    created_at: datetime = Field(default_factory=utc_now)


class EvalCaseExecutionResult(BaseModel):
    case_id: str
    suite_id: EvalSuiteId
    title: str
    is_critical: bool = False
    is_edge_case: bool = False
    source_type: EvalCaseSourceType = "curated_benchmark"
    passed: bool = False
    score: float = 0.0
    scoring_method: str = "deterministic_assertion"
    is_subjective_advisory: bool = False
    latency_ms: float = 0.0
    actual_output_excerpt: str = ""
    expected_summary: str = ""
    metrics_breakdown: Dict[str, Optional[float]] = Field(default_factory=dict)
    unavailable_metrics: List[str] = Field(default_factory=list)
    error_detail: Optional[str] = None
    prevented_side_effect: bool = False


class EvalAcceptanceThresholds(BaseModel):
    min_task_success_rate: float = Field(default=0.85, ge=0.0, le=1.0)
    min_safety_compliance_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    max_error_rate: float = Field(default=0.10, ge=0.0, le=1.0)
    max_latency_regression_pct: float = Field(default=50.0, ge=0.0, le=500.0)
    block_on_critical_failure: bool = True


class EvalMetricSummary(BaseModel):
    task_success_rate: float = 0.0
    factual_support_score: Optional[float] = None
    citation_validity_score: Optional[float] = None
    extraction_accuracy_score: Optional[float] = None
    language_quality_score: Optional[float] = None
    tool_call_success_rate: Optional[float] = None
    safety_compliance_rate: Optional[float] = None
    error_rate: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    total_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    unavailable_metrics_notes: Dict[str, str] = Field(default_factory=dict)


class EvalRegressionAlert(BaseModel):
    metric_name: str
    baseline_value: float
    candidate_value: float
    delta: float
    severity: Literal["critical", "warning", "info"] = "warning"
    message: str


class EvalRunRecord(BaseModel):
    run_id: str
    label: str = "Evaluation Run"
    dataset_version: str = "v1.0.0"
    status: EvalRunStatus = "COMPLETED"
    suites_selected: List[EvalSuiteId] = Field(default_factory=list)
    sample_size: int = 0
    completed_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    critical_failures: int = 0
    model_configuration: Dict[str, Any] = Field(default_factory=dict)
    isolated_environment_id: str = ""
    consequential_actions_blocked: bool = True
    metrics: EvalMetricSummary = Field(default_factory=EvalMetricSummary)
    thresholds: EvalAcceptanceThresholds = Field(default_factory=EvalAcceptanceThresholds)
    release_gate_verdict: EvalReleaseGateVerdict = "RELEASE_APPROVED"
    release_gate_reasons: List[str] = Field(default_factory=list)
    baseline_run_id: Optional[str] = None
    regression_alerts: List[EvalRegressionAlert] = Field(default_factory=list)
    case_results: List[EvalCaseExecutionResult] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: Optional[datetime] = None


class EvalRunCreateRequest(BaseModel):
    label: str = Field(default="Stage 20 QA Benchmark Run", max_length=120)
    suites: List[EvalSuiteId] = Field(default_factory=list)
    include_pending_synthetic: bool = False
    baseline_run_id: Optional[str] = None
    thresholds: Optional[EvalAcceptanceThresholds] = None
    simulate_interrupted_after_n: Optional[int] = Field(default=None, ge=1, le=100)
    simulate_provider_failure: bool = False
    provider_label: Optional[str] = None
    model_label: Optional[str] = None


class EvalCaseCreateRequest(BaseModel):
    suite_id: EvalSuiteId
    title: str = Field(..., min_length=3, max_length=160)
    description: str = Field(default="", max_length=600)
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    expected_criteria: Dict[str, Any] = Field(default_factory=dict)
    scoring_rubric: str = Field(default="Deterministic assertion check", max_length=400)
    is_edge_case: bool = False
    is_critical: bool = False
    known_limitations: str = Field(default="", max_length=400)
    source_type: EvalCaseSourceType = "curated_benchmark"
    contains_private_conversation_data: bool = False
    admin_actor: str = "admin"


class EvalSyntheticGenerateRequest(BaseModel):
    suite_id: EvalSuiteId
    topic_focus: str = Field(default="edge_case_boundary", max_length=120)
    count: int = Field(default=2, ge=1, le=5)
    admin_actor: str = "admin"


class EvalCaseReviewRequest(BaseModel):
    review_status: EvalCaseReviewStatus
    reviewer_note: str = Field(default="", max_length=300)
    admin_actor: str = "admin"


class EvalCompareRunsRequest(BaseModel):
    baseline_run_id: str
    candidate_run_id: str
    thresholds: Optional[EvalAcceptanceThresholds] = None


# ============================================================================
# Stage 21: Universal Knowledge Discovery Engine Schemas
# ============================================================================

DiscoverySourceType = Literal[
    "general_web",
    "academic_publications",
    "news_live",
    "public_datasets",
    "official_documentation",
    "authorized_knowledge_base",
]

DiscoverySearchMode = Literal[
    "quick",
    "comprehensive",
    "academic",
    "official",
    "exploration",
]

DiscoveryOriginalityTier = Literal[
    "original_primary_source",
    "peer_reviewed_or_preprint",
    "secondary_reporting",
    "syndicated_or_copied",
]


class DiscoveryConnectorSpec(BaseModel):
    connector_id: str
    name: str
    source_type: DiscoverySourceType
    description: str
    configured: bool = True
    status: Literal["operational", "degraded", "unavailable"] = "operational"
    supported_syntax: List[str] = Field(default_factory=list)
    supports_date_filter: bool = True
    supports_language_filter: bool = True
    requires_api_key: bool = False
    provider_notes: str = ""


class DiscoveryConnectorExecutionStatus(BaseModel):
    connector_id: str
    name: str
    source_type: DiscoverySourceType
    status: Literal["succeeded", "unavailable", "error", "skipped"]
    items_returned: int = 0
    latency_ms: float = 0.0
    error_message: Optional[str] = None


class DiscoveryNormalizedItem(BaseModel):
    item_id: str
    citation_index: int
    title: str
    url: str
    canonical_url: str
    domain: str
    snippet: str
    quarantined_snippet: str
    source_type: DiscoverySourceType
    connector_id: str
    publication_date: Optional[str] = None
    retrieval_timestamp: str
    language: str = "en"
    originality_tier: DiscoveryOriginalityTier = "secondary_reporting"
    is_verified_scholarly: bool = False
    is_verified_official: bool = False
    authority_basis: str = "General web source (unverified third-party domain)"
    relevance_score: float = 0.0
    recency_score: float = 0.0
    quality_score: float = 0.0
    combined_rank_score: float = 0.0
    is_stale: bool = False
    staleness_warning: Optional[str] = None
    duplicate_count: int = 1
    merged_from_connectors: List[str] = Field(default_factory=list)
    authors_or_publisher: Optional[str] = None
    doi_or_identifier: Optional[str] = None


class DiscoveryTimelineEvent(BaseModel):
    date_label: str
    title: str
    summary: str
    citation_indices: List[int] = Field(default_factory=list)
    source_urls: List[str] = Field(default_factory=list)


class DiscoverySourceComparisonRow(BaseModel):
    citation_index: int
    title: str
    domain: str
    source_type: DiscoverySourceType
    originality_tier: DiscoveryOriginalityTier
    publication_date: Optional[str] = None
    key_claim: str
    agreement_status: Literal["corroborated", "unique_finding", "conflicting"] = "unique_finding"
    authority_basis: str


class DiscoveryConflictItem(BaseModel):
    topic: str
    claim_a: str
    citation_a: int
    claim_b: str
    citation_b: int
    explanation: str


class DiscoverySynthesisPayload(BaseModel):
    concise_summary: str
    detailed_report: str
    grouped_findings: Dict[str, List[str]] = Field(default_factory=dict)
    timeline: List[DiscoveryTimelineEvent] = Field(default_factory=list)
    source_comparison: List[DiscoverySourceComparisonRow] = Field(default_factory=list)
    detected_conflicts: List[DiscoveryConflictItem] = Field(default_factory=list)
    evidence_gaps: List[str] = Field(default_factory=list)


class DiscoverySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    mode: DiscoverySearchMode = "comprehensive"
    source_types: List[DiscoverySourceType] = Field(default_factory=list)
    language: str = Field(default="auto", max_length=24)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    domain_filter: Optional[str] = None
    exclude_terms: List[str] = Field(default_factory=list)
    exact_phrase: Optional[str] = None
    page: int = Field(default=1, ge=1, le=50)
    page_size: int = Field(default=10, ge=1, le=30)
    bypass_cache: bool = False
    simulate_failed_connectors: List[str] = Field(default_factory=list)
    custom_candidate_items: List[Dict[str, Any]] = Field(default_factory=list)
    user_id: str = "default_user"


class DiscoverySearchResponse(BaseModel):
    discovery_id: str
    query: str
    preserved_language: str
    detected_language_name: str
    mode: DiscoverySearchMode
    query_intent: str
    parsed_operators: Dict[str, Any] = Field(default_factory=dict)
    expanded_subqueries: List[str] = Field(default_factory=list)
    connector_statuses: List[DiscoveryConnectorExecutionStatus] = Field(default_factory=list)
    total_raw_candidates: int = 0
    deduplicated_count: int = 0
    ssrf_blocked_count: int = 0
    page: int = 1
    page_size: int = 10
    total_filtered_results: int = 0
    total_pages: int = 1
    cache_hit: bool = False
    latency_ms: float = 0.0
    results: List[DiscoveryNormalizedItem] = Field(default_factory=list)
    follow_up_queries: List[str] = Field(default_factory=list)
    related_topics: List[str] = Field(default_factory=list)
    alternative_viewpoints: List[str] = Field(default_factory=list)
    synthesis: DiscoverySynthesisPayload
    created_at: datetime = Field(default_factory=utc_now)


class DiscoveryMetadataResponse(BaseModel):
    stage: int = 21
    engine: str = "UniversalKnowledgeDiscoveryEngine"
    connectors: List[DiscoveryConnectorSpec] = Field(default_factory=list)
    modes: List[Dict[str, str]] = Field(default_factory=list)
    supported_operators: List[str] = Field(default_factory=list)
    cache_ttl_seconds: float = 300.0
    stale_days_threshold: int = 730


# ============================================================================
# Stage 22: Knowledge Graph Intelligence Engine Schemas
# ============================================================================

KGEntityType = Literal[
    "concept",
    "technology",
    "organization",
    "person",
    "event",
    "dataset",
    "component",
    "claim_or_standard",
]

KGRelationType = Literal[
    "depends_on",
    "created_by",
    "related_to",
    "part_of",
    "contradicts",
    "supports",
    "uses",
    "evaluates",
    "governed_by",
]

KGFactBasis = Literal["explicit_fact", "ai_inferred"]

KGUncertaintyLabel = Literal[
    "verified_explicit",
    "hedged_source_statement",
    "inferred_transitive",
    "inferred_low_confidence",
]

KGSourceKind = Literal[
    "user_document",
    "vault_document",
    "discovery_result",
    "inferred_transitivity",
]

KGQueryMode = Literal[
    "natural_language",
    "connection_path",
    "dependency_impact",
    "contradiction_analysis",
    "neighborhood_exploration",
]


class KGEvidenceItem(BaseModel):
    evidence_id: str
    source_kind: KGSourceKind = "user_document"
    source_id: str
    source_title: str
    source_url: Optional[str] = None
    page_or_section: Optional[str] = None
    passage: str
    quarantined_passage: str
    stance: Literal["supporting", "contradicting", "neutral"] = "supporting"
    extracted_at: str


class KGEntityNode(BaseModel):
    entity_id: str
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    canonical_key: str
    label: str
    entity_type: KGEntityType = "concept"
    aliases: List[str] = Field(default_factory=list)
    description: str = ""
    properties: Dict[str, Any] = Field(default_factory=dict)
    provenance: List[KGEvidenceItem] = Field(default_factory=list)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    degree: int = 0
    created_at: str
    updated_at: str


class KGRelationshipEdge(BaseModel):
    relationship_id: str
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    source_entity_id: str
    source_label: str = ""
    target_entity_id: str
    target_label: str = ""
    relation_type: KGRelationType = "related_to"
    fact_basis: KGFactBasis = "explicit_fact"
    is_inferred: bool = False
    uncertainty_label: KGUncertaintyLabel = "verified_explicit"
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    explanation: str = ""
    evidence: List[KGEvidenceItem] = Field(default_factory=list)
    created_at: str
    updated_at: str


class KGExplicitEntityInput(BaseModel):
    label: str = Field(..., min_length=1, max_length=160)
    entity_type: KGEntityType = "concept"
    aliases: List[str] = Field(default_factory=list)
    description: str = Field(default="", max_length=1000)
    properties: Dict[str, Any] = Field(default_factory=dict)


class KGExplicitRelationshipInput(BaseModel):
    source_label: str = Field(..., min_length=1, max_length=160)
    source_type: KGEntityType = "technology"
    target_label: str = Field(..., min_length=1, max_length=160)
    target_type: KGEntityType = "technology"
    relation_type: KGRelationType = "depends_on"
    fact_basis: KGFactBasis = "explicit_fact"
    passage: str = Field(default="", max_length=1000)
    page_or_section: Optional[str] = None
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class KGIngestRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    source_title: str = Field(default="User Knowledge Input", max_length=240)
    source_url: Optional[str] = Field(default=None, max_length=600)
    page_or_section: Optional[str] = Field(default="Section 1", max_length=120)
    source_text: str = Field(default="", max_length=32000)
    vault_document_ids: List[str] = Field(default_factory=list)
    discovery_id: Optional[str] = None
    explicit_entities: List[KGExplicitEntityInput] = Field(default_factory=list)
    explicit_relationships: List[KGExplicitRelationshipInput] = Field(default_factory=list)
    derive_inferred_relationships: bool = True


class KGChangeLogEntry(BaseModel):
    change_id: str
    user_id: str
    workspace_id: str
    action_type: Literal[
        "ingest_merge",
        "entity_merge_approved",
        "delete_approved",
        "seed_sample",
    ]
    summary: str
    affected_entity_ids: List[str] = Field(default_factory=list)
    affected_relationship_ids: List[str] = Field(default_factory=list)
    created_at: str


class KGIngestResponse(BaseModel):
    user_id: str
    workspace_id: str
    entities_created: int = 0
    entities_updated: int = 0
    relationships_created: int = 0
    relationships_updated: int = 0
    inferred_relationships_created: int = 0
    prompt_injection_neutralized_count: int = 0
    ssrf_blocked_urls_count: int = 0
    entities: List[KGEntityNode] = Field(default_factory=list)
    relationships: List[KGRelationshipEdge] = Field(default_factory=list)
    change_log: KGChangeLogEntry
    summary: str


class KGGraphSnapshotResponse(BaseModel):
    user_id: str
    workspace_id: str
    total_nodes_in_workspace: int = 0
    total_edges_in_workspace: int = 0
    returned_nodes_count: int = 0
    returned_edges_count: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    has_more: bool = False
    nodes: List[KGEntityNode] = Field(default_factory=list)
    edges: List[KGRelationshipEdge] = Field(default_factory=list)


class KGPathStep(BaseModel):
    step_index: int
    relationship_id: str
    source_entity_id: str
    source_label: str
    relation_type: KGRelationType
    target_entity_id: str
    target_label: str
    fact_basis: KGFactBasis
    is_inferred: bool
    uncertainty_label: KGUncertaintyLabel
    confidence: float
    evidence: List[KGEvidenceItem] = Field(default_factory=list)


class KGContradictionItem(BaseModel):
    subject_label: str
    target_label: str
    supporting_edge: Optional[KGRelationshipEdge] = None
    contradicting_edge: KGRelationshipEdge
    supporting_sources: List[str] = Field(default_factory=list)
    contradicting_sources: List[str] = Field(default_factory=list)
    explanation: str


class KGQueryRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    mode: KGQueryMode = "natural_language"
    question: str = Field(default="", max_length=1000)
    source_entity: Optional[str] = None
    target_entity: Optional[str] = None
    max_depth: int = Field(default=4, ge=1, le=6)
    include_inferred: bool = True
    relation_types: List[KGRelationType] = Field(default_factory=list)


class KGQueryResponse(BaseModel):
    query_id: str
    user_id: str
    workspace_id: str
    mode_executed: KGQueryMode
    question: str
    answer_summary: str
    paths: List[List[KGPathStep]] = Field(default_factory=list)
    dependent_entities: List[KGEntityNode] = Field(default_factory=list)
    contradictions: List[KGContradictionItem] = Field(default_factory=list)
    subgraph_nodes: List[KGEntityNode] = Field(default_factory=list)
    subgraph_edges: List[KGRelationshipEdge] = Field(default_factory=list)
    cycles_detected: int = 0
    explicit_facts_count: int = 0
    inferred_facts_count: int = 0
    latency_ms: float = 0.0


class KGDuplicateCandidate(BaseModel):
    candidate_id: str
    entity_a_id: str
    entity_a_label: str
    entity_b_id: str
    entity_b_label: str
    entity_type: KGEntityType
    similarity_score: float
    reason: str


class KGDestructiveOperationRecord(BaseModel):
    op_id: str
    user_id: str
    workspace_id: str
    operation_type: Literal["merge_entities", "delete_items", "clear_workspace"]
    status: Literal["WAITING_FOR_APPROVAL", "SUCCEEDED", "CANCELLED"]
    requires_approval: bool = True
    summary: str
    affected_entities_count: int = 0
    affected_relationships_count: int = 0
    created_at: str
    resolved_at: Optional[str] = None


class KGEntityMergeRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    source_entity_id: str
    target_entity_id: str
    confirmed: bool = False


class KGDeleteRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    entity_ids: List[str] = Field(default_factory=list)
    relationship_ids: List[str] = Field(default_factory=list)
    clear_workspace: bool = False
    confirmed: bool = False


class KGApproveOperationRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    approved: bool = True


class KGMetadataResponse(BaseModel):
    stage: int = 22
    engine: str = "KnowledgeGraphIntelligenceEngine"
    schema_version: str = "v1.0.0"
    storage_backend: str = "SQLite Relational-Graph Engine with Adjacency Indexing"
    entity_types: List[str] = Field(default_factory=list)
    relation_types: List[str] = Field(default_factory=list)
    query_modes: List[Dict[str, str]] = Field(default_factory=list)
    max_expansion_depth: int = 6
    default_page_size: int = 50
    max_page_size: int = 200


# ============================================================================
# STAGE 23: IOT PROJECT BUILDER ENGINE SCHEMAS
# ============================================================================

IoTBoardId = Literal[
    "esp32_devkit_v1",
    "arduino_uno_r3",
    "stm32_nucleo_f401re",
    "raspberry_pi_pico_w",
    "raspberry_pi_4b",
]

IoTPowerSource = Literal[
    "usb_5v",
    "battery_lipo_3v7",
    "dc_barrel_7v_12v",
    "solar_mppt_5v",
    "mains_ac_isolated_psu",
]

IoTEnvironmentType = Literal[
    "indoor_lab",
    "outdoor_weatherproof",
    "industrial_harsh",
    "greenhouse_humid",
    "wearable_portable",
]

IoTComponentCategory = Literal[
    "sensor",
    "actuator",
    "relay",
    "display",
    "motor",
    "motor_driver",
    "communication",
    "power",
    "logic_adapter",
]

IoTSpecVerificationStatus = Literal[
    "verified_datasheet_spec",
    "estimated_typical_range",
]

IoTFirmwareLanguage = Literal[
    "arduino_cpp",
    "micropython",
    "esp_idf_c",
    "rpi_python_gpiozero",
]

IoTConnectivityProtocol = Literal[
    "none_local_only",
    "wifi_mqtt",
    "wifi_http_rest",
    "ble_gatt",
    "serial_usb_telemetry",
]

IoTIssueSeverity = Literal["critical", "error", "warning", "info"]


class IoTBoardPin(BaseModel):
    pin_id: str
    label: str
    gpio_number: Optional[int] = None
    capabilities: List[str] = Field(default_factory=list)
    voltage_level_v: float = 3.3
    five_volt_tolerant: bool = False
    max_current_ma: float = 12.0
    notes: str = ""


class IoTBoardProfile(BaseModel):
    board_id: IoTBoardId
    name: str
    family: str
    mcu_or_soc: str
    architecture: str
    clock_mhz: float
    operating_voltage_v: float
    io_logic_voltage_v: float
    five_volt_tolerant_pins: bool
    total_gpio_count: int
    analog_in_count: int
    pwm_pins_count: int
    flash_kb: int
    sram_kb: int
    max_pin_current_ma: float
    max_regulator_3v3_current_ma: float
    max_regulator_5v_current_ma: float
    communication_interfaces: List[str] = Field(default_factory=list)
    builtin_wireless: List[str] = Field(default_factory=list)
    supported_languages: List[IoTFirmwareLanguage] = Field(default_factory=list)
    pins: List[IoTBoardPin] = Field(default_factory=list)
    toolchain_commands: Dict[str, str] = Field(default_factory=dict)
    toolchain_installed: Dict[str, bool] = Field(default_factory=dict)
    compatibility_warnings: List[str] = Field(default_factory=list)
    estimated_cost_min_usd: float = 4.0
    estimated_cost_max_usd: float = 12.0
    spec_verification_status: IoTSpecVerificationStatus = "verified_datasheet_spec"
    datasheet_url: str = ""


class IoTComponentPin(BaseModel):
    pin_name: str
    pin_role: Literal[
        "POWER_VCC",
        "POWER_GND",
        "DIGITAL_IN",
        "DIGITAL_OUT",
        "ANALOG_OUT",
        "PWM_IN",
        "I2C_SDA",
        "I2C_SCL",
        "SPI_MOSI",
        "SPI_MISO",
        "SPI_SCK",
        "SPI_CS",
        "UART_TX",
        "UART_RX",
        "ONEWIRE",
        "MOTOR_TERMINAL",
        "MAINS_AC_TERMINAL",
    ]
    voltage_min_v: float = 0.0
    voltage_max_v: float = 5.0
    logic_level_v: float = 3.3
    required: bool = True
    description: str = ""


class IoTComponentSpec(BaseModel):
    component_id: str
    name: str
    category: IoTComponentCategory
    description: str
    operating_voltage_min_v: float
    operating_voltage_max_v: float
    logic_voltage_v: float
    five_volt_logic_output: bool = False
    current_typical_ma: float
    current_peak_ma: float
    interfaces: List[str] = Field(default_factory=list)
    pins: List[IoTComponentPin] = Field(default_factory=list)
    i2c_default_address: Optional[str] = None
    requires_external_driver: bool = False
    is_inductive_load: bool = False
    is_mains_voltage_hazard: bool = False
    is_high_current_battery: bool = False
    spec_verification_status: IoTSpecVerificationStatus = "verified_datasheet_spec"
    datasheet_url: str = ""
    availability_status: Literal["common_in_stock", "specialty_module", "lead_time_varies"] = "common_in_stock"
    cost_min_usd: float = 1.5
    cost_max_usd: float = 5.0
    recommended_libraries: Dict[str, List[str]] = Field(default_factory=dict)
    notes: str = ""


class IoTPlacedComponent(BaseModel):
    instance_id: str
    component_id: str
    label: str
    x: float = 320.0
    y: float = 120.0
    i2c_address_override: Optional[str] = None
    notes: str = ""


class IoTWireConnection(BaseModel):
    wire_id: str
    from_node_id: str  # "board" or component instance_id
    from_pin: str
    to_node_id: str  # "board" or component instance_id
    to_pin: str
    signal_type: str = "DIGITAL"
    wire_color: str = "#38bdf8"
    label: str = ""
    voltage_v: float = 3.3


class IoTWiringValidationIssue(BaseModel):
    issue_id: str
    code: str
    severity: IoTIssueSeverity
    category: Literal[
        "pin_conflict",
        "voltage_incompatibility",
        "missing_connection",
        "overcurrent_or_driver",
        "polarity_or_short",
        "interface_mismatch",
        "strapping_or_boot",
    ]
    title: str
    description: str
    affected_nodes: List[str] = Field(default_factory=list)
    affected_pins: List[str] = Field(default_factory=list)
    remediation: str


class IoTWiringValidationReport(BaseModel):
    valid: bool
    critical_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    issues: List[IoTWiringValidationIssue] = Field(default_factory=list)
    power_rail_summary: Dict[str, Any] = Field(default_factory=dict)
    svg_diagram: str = ""
    markdown_pinout_table: str = ""


class IoTFirmwareArtifact(BaseModel):
    language: IoTFirmwareLanguage
    filename: str
    source_code: str
    secrets_template_filename: str
    secrets_template_code: str
    libraries_required: List[str] = Field(default_factory=list)
    pin_mappings: Dict[str, str] = Field(default_factory=dict)
    compile_command: str
    flash_command: str
    compilation_tested: bool = False
    compilation_passed: Optional[bool] = None
    compiler_used: Optional[str] = None
    verification_mode: Literal[
        "real_compiler_binary",
        "python_ast_and_py_compile",
        "static_structural_check_toolchain_not_installed",
    ] = "static_structural_check_toolchain_not_installed"
    compiler_output: str = ""
    missing_dependencies: List[str] = Field(default_factory=list)
    configuration_instructions: List[str] = Field(default_factory=list)
    generated_at: str


class IoTSimulationStimulus(BaseModel):
    instance_id: str
    parameter: str
    unit: str = ""
    values: List[float] = Field(default_factory=list)


class IoTSimulationTickResult(BaseModel):
    tick: int
    timestamp_ms: int
    sensor_readings: Dict[str, Any] = Field(default_factory=dict)
    actuator_states: Dict[str, Any] = Field(default_factory=dict)
    serial_log: str
    estimated_current_ma: float
    estimated_power_mw: float
    alerts: List[str] = Field(default_factory=list)


class IoTSimulationRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    ticks: int = Field(default=6, ge=1, le=32)
    stimuli: List[IoTSimulationStimulus] = Field(default_factory=list)
    inject_fault: Optional[Literal["none", "sensor_disconnect", "overtemperature", "brownout_voltage", "mqtt_broker_offline"]] = "none"


class IoTSimulationResponse(BaseModel):
    simulation_id: str
    project_id: str
    board_id: IoTBoardId
    execution_environment: Literal["deterministic_virtual_simulation"] = "deterministic_virtual_simulation"
    is_physical_hardware_execution: bool = False
    hardware_disclaimer: str = (
        "SIMULATION ONLY: Executed in NEXORA's deterministic virtual device simulator. "
        "No physical microcontroller, sensor, or actuator hardware was controlled or tested."
    )
    wiring_valid_before_run: bool = True
    ticks_executed: int = 0
    peak_current_ma: float = 0.0
    average_current_ma: float = 0.0
    ticks: List[IoTSimulationTickResult] = Field(default_factory=list)
    summary: str


class IoTConnectivityConfig(BaseModel):
    protocol: IoTConnectivityProtocol = "wifi_mqtt"
    enabled: bool = True
    mock_mode: bool = True
    endpoint_or_broker: str = "mqtt://broker.hivemq.com"
    port: int = 1883
    topic_prefix: str = "nexora/iot/prototype"
    publish_interval_ms: int = 5000
    tls_enabled: bool = True
    credentials_env_vars: List[str] = Field(
        default_factory=lambda: ["IOT_WIFI_SSID", "IOT_WIFI_PASSWORD", "IOT_BROKER_TOKEN"]
    )
    masked_credentials_preview: Dict[str, str] = Field(
        default_factory=lambda: {
            "IOT_WIFI_SSID": "<set-in-secrets.h>",
            "IOT_WIFI_PASSWORD": "******** (never stored in plaintext)",
            "IOT_BROKER_TOKEN": "******** (loaded via env/secrets)",
        }
    )
    sample_telemetry_payload: Dict[str, Any] = Field(default_factory=dict)


class IoTBOMItem(BaseModel):
    item_id: str
    name: str
    category: str
    quantity: int = 1
    unit_cost_min_usd: float
    unit_cost_max_usd: float
    subtotal_min_usd: float
    subtotal_max_usd: float
    spec_verification_status: IoTSpecVerificationStatus
    datasheet_url: str = ""
    notes: str = ""


class IoTBuildDocumentation(BaseModel):
    bom_items: List[IoTBOMItem] = Field(default_factory=list)
    total_cost_min_usd: float = 0.0
    total_cost_max_usd: float = 0.0
    target_budget_usd: float = 50.0
    within_budget: bool = True
    budget_notes: str = ""
    unverified_specs_notice: str = ""
    wiring_steps: List[str] = Field(default_factory=list)
    assembly_instructions: List[str] = Field(default_factory=list)
    test_procedures: List[str] = Field(default_factory=list)
    troubleshooting_guide: List[str] = Field(default_factory=list)


class IoTSafetyCheckItem(BaseModel):
    check_id: str
    category: Literal[
        "electrical_limits",
        "current_budget",
        "polarity_and_shorts",
        "isolation_and_flyback",
        "motor_driver_compatibility",
        "hazardous_voltage_or_battery",
        "credential_security",
    ]
    status: Literal["pass", "warning", "hazard_review_required", "fail"]
    title: str
    detail: str
    recommendation: str


class IoTSafetyReport(BaseModel):
    passed_nominal_checks: bool
    requires_qualified_electrical_review: bool = False
    mains_voltage_detected: bool = False
    high_current_battery_detected: bool = False
    inductive_load_without_driver: bool = False
    regulator_3v3_load_ma: float = 0.0
    regulator_3v3_limit_ma: float = 250.0
    regulator_5v_load_ma: float = 0.0
    regulator_5v_limit_ma: float = 500.0
    power_budget_exceeded: bool = False
    checks: List[IoTSafetyCheckItem] = Field(default_factory=list)
    physical_safety_disclaimer: str = (
        "IMPORTANT SAFETY NOTICE: Software electrical rules check nominal pin ratings and topology only. "
        "Software validation is NEVER proof of physical electrical safety, thermal stability, or regulatory compliance. "
        "Any design involving mains AC voltage, lithium battery packs, or high-power loads requires inspection by a qualified electrical engineer."
    )


class IoTProjectRecord(BaseModel):
    project_id: str
    user_id: str
    workspace_id: str
    name: str
    purpose_description: str
    target_budget_usd: float = 45.0
    power_source: IoTPowerSource = "usb_5v"
    environment: IoTEnvironmentType = "indoor_lab"
    board_id: IoTBoardId = "esp32_devkit_v1"
    board_profile: IoTBoardProfile
    placed_components: List[IoTPlacedComponent] = Field(default_factory=list)
    wires: List[IoTWireConnection] = Field(default_factory=list)
    wiring_report: IoTWiringValidationReport
    firmware: IoTFirmwareArtifact
    connectivity: IoTConnectivityConfig
    build_docs: IoTBuildDocumentation
    safety_report: IoTSafetyReport
    last_simulation: Optional[IoTSimulationResponse] = None
    version: str = "1.0.0"
    export_count: int = 0
    created_at: str
    updated_at: str


class IoTProjectCreateRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    name: str = Field(..., min_length=2, max_length=160)
    invention_description: str = Field(..., min_length=5, max_length=3000)
    target_budget_usd: float = Field(default=45.0, ge=5.0, le=5000.0)
    power_source: IoTPowerSource = "usb_5v"
    environment: IoTEnvironmentType = "indoor_lab"
    preferred_board_id: Optional[IoTBoardId] = None
    component_ids: List[str] = Field(default_factory=list)
    firmware_language: Optional[IoTFirmwareLanguage] = None
    connectivity_protocol: IoTConnectivityProtocol = "wifi_mqtt"
    auto_wire: bool = True


class IoTProjectUpdateWiringRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    board_id: Optional[IoTBoardId] = None
    power_source: Optional[IoTPowerSource] = None
    placed_components: List[IoTPlacedComponent] = Field(default_factory=list)
    wires: List[IoTWireConnection] = Field(default_factory=list)
    auto_regenerate_firmware: bool = True


class IoTProjectGenerateFirmwareRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    language: IoTFirmwareLanguage = "arduino_cpp"
    custom_source_code: Optional[str] = None
    run_compiler_check: bool = True


class IoTProjectExportRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    bump_version: Literal["none", "patch", "minor", "major"] = "patch"
    write_to_workspace_files: bool = True


class IoTExportFileEntry(BaseModel):
    relative_path: str
    size_bytes: int
    sha256: str
    description: str
    content_preview: str


class IoTProjectExportResponse(BaseModel):
    export_id: str
    project_id: str
    project_name: str
    version: str
    export_directory: str
    workspace_relative_dir: Optional[str] = None
    files: List[IoTExportFileEntry] = Field(default_factory=list)
    wiring_valid: bool
    requires_qualified_electrical_review: bool
    exported_at: str
    summary: str


class IoTMetadataResponse(BaseModel):
    stage: int = 23
    engine: str = "IoTProjectBuilderEngine"
    boards_count: int
    components_count: int
    supported_languages: List[str] = Field(default_factory=list)
    supported_connectivity: List[str] = Field(default_factory=list)
    detected_toolchains: Dict[str, bool] = Field(default_factory=dict)
    hardware_execution_disclaimer: str


# ============================================================================
# STAGE 24: EMBEDDED FIRMWARE ENGINEERING STUDIO SCHEMAS
# ============================================================================

FirmwareFrameworkId = Literal[
    "arduino_cpp",
    "esp_idf_c",
    "stm32_hal_c",
    "micropython",
    "rpi_python_gpiozero",
]

FirmwareOptimizationLevel = Literal["-Os", "-O2", "-O0", "-Og"]


class FirmwarePlatformMatrixEntry(BaseModel):
    board_id: IoTBoardId
    board_name: str
    mcu_or_soc: str
    supported_frameworks: List[FirmwareFrameworkId] = Field(default_factory=list)
    unsupported_frameworks: Dict[str, str] = Field(default_factory=dict)
    compiler_binaries: Dict[str, str] = Field(default_factory=dict)
    toolchain_available: Dict[str, bool] = Field(default_factory=dict)
    flash_protocol: str
    default_baud_rate: int = 115200


class FirmwareLibraryDependency(BaseModel):
    name: str
    version: str = "^1.0.0"
    header_or_module: str
    purpose: str
    installed_in_sandbox: bool = False


class FirmwareBuildSettings(BaseModel):
    optimization_level: FirmwareOptimizationLevel = "-Os"
    debug_symbols: bool = True
    watchdog_enabled: bool = True
    watchdog_timeout_ms: int = 5000
    serial_baud_rate: int = 115200
    enable_ota_stub: bool = False
    extra_build_flags: List[str] = Field(default_factory=lambda: ["-Wall", "-Wextra"])


class FirmwareProjectFile(BaseModel):
    path: str
    role: Literal[
        "main_entry",
        "pin_config",
        "driver_header",
        "driver_source",
        "secrets_template",
        "build_manifest",
        "unit_test",
    ]
    language: str
    content: str
    size_bytes: int
    sha256: str
    updated_at: str


class FirmwareHardwareDiagnostic(BaseModel):
    diag_id: str
    severity: Literal["critical", "error", "warning", "info"]
    category: Literal[
        "incompatible_voltage",
        "invalid_pin",
        "missing_library",
        "unsupported_peripheral",
        "interrupt_constraint",
    ]
    title: str
    detail: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggested_fix: str


class FirmwareStaticIssue(BaseModel):
    issue_id: str
    category: Literal[
        "memory_error",
        "blocking_loop",
        "watchdog_issue",
        "unsafe_buffer_handling",
        "uninitialized_value",
        "missing_timeout",
        "credential_exposure",
    ]
    severity: Literal["critical", "error", "warning", "info"]
    file_path: str
    line_number: int
    code_snippet: str
    message: str
    suggested_fix: str


class FirmwareQualityReport(BaseModel):
    passed_quality_gate: bool
    critical_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    issues: List[FirmwareStaticIssue] = Field(default_factory=list)
    unit_tests_executed: bool = False
    unit_tests_passed: Optional[bool] = None
    unit_test_output: str = ""
    hil_status: Literal["SKIPPED_NO_HIL_EQUIPMENT", "EXECUTED"] = "SKIPPED_NO_HIL_EQUIPMENT"
    hil_notes: str = (
        "Hardware-in-the-Loop (HIL) physical test rig is not connected to this host; "
        "host-side deterministic unit tests were executed instead."
    )


class FirmwareCompilerDiagnostic(BaseModel):
    file_path: str
    line_number: int
    column: int = 1
    severity: Literal["error", "warning", "info"]
    message: str
    source_line: str = ""
    suggested_fix: str = ""


class FirmwareArtifactFile(BaseModel):
    relative_path: str
    artifact_type: Literal[
        "source_file",
        "dependency_manifest",
        "build_config",
        "compiled_bytecode_or_binary",
        "release_notes",
    ]
    size_bytes: int
    sha256: str
    genuinely_produced_by_build: bool = True


class FirmwareCompileResult(BaseModel):
    build_id: str
    workspace_id: str
    fw_project_id: str
    board_id: IoTBoardId
    framework: FirmwareFrameworkId
    status: Literal[
        "SUCCEEDED",
        "FAILED_COMPILATION_ERROR",
        "BLOCKED_TOOLCHAIN_MISSING",
    ]
    toolchain_binary: str
    toolchain_installed: bool
    compilation_genuinely_executed: bool
    binary_artifact_produced: bool
    exit_code: Optional[int] = None
    duration_ms: float = 0.0
    compiler_stdout: str = ""
    compiler_stderr: str = ""
    diagnostics: List[FirmwareCompilerDiagnostic] = Field(default_factory=list)
    produced_artifacts: List[FirmwareArtifactFile] = Field(default_factory=list)
    compiled_at: str
    honesty_notice: str


class FirmwareSerialLogEntry(BaseModel):
    seq: int
    timestamp_ms: int
    event_type: Literal["boot_banner", "reset_event", "sensor_telemetry", "isr_trigger", "watchdog_feed", "error"]
    message: str
    firmware_version: str


class FirmwareSerialMonitorResponse(BaseModel):
    fw_project_id: str
    board_id: IoTBoardId
    source_mode: Literal["simulated_virtual_serial", "physical_authorized_serial"] = "simulated_virtual_serial"
    is_simulated: bool = True
    connected_physical_port: Optional[str] = None
    baud_rate: int = 115200
    firmware_version: str = "1.0.0"
    reset_reason: str = "POWERON_RESET"
    logs: List[FirmwareSerialLogEntry] = Field(default_factory=list)
    distinction_banner: str = (
        "SIMULATED SERIAL MONITOR: No physical serial device is attached. Logs are generated from the "
        "firmware's deterministic state machine and sensor driver model."
    )


class FirmwareDeviceActionRecord(BaseModel):
    action_id: str
    fw_project_id: str
    user_id: str
    workspace_id: str
    action_type: Literal["flash_firmware", "reset_device"]
    target_port: str = "auto"
    status: Literal[
        "WAITING_FOR_APPROVAL",
        "BLOCKED_NO_PHYSICAL_DEVICE",
        "CANCELLED",
    ]
    requires_approval: bool = True
    cli_command_preview: str
    recovery_guidance: List[str] = Field(default_factory=list)
    message: str
    created_at: str
    resolved_at: Optional[str] = None


class FirmwareVersionSnapshot(BaseModel):
    version_id: str
    semver: str
    commit_note: str
    files: List[FirmwareProjectFile] = Field(default_factory=list)
    build_settings: FirmwareBuildSettings
    created_at: str


class FirmwareCodeSearchHit(BaseModel):
    file_path: str
    line_number: int
    line_preview: str


class FirmwareWorkspaceRecord(BaseModel):
    fw_project_id: str
    user_id: str
    workspace_id: str
    name: str
    iot_project_id: Optional[str] = None
    board_id: IoTBoardId
    board_name: str
    framework: FirmwareFrameworkId
    semver: str = "1.0.0"
    build_settings: FirmwareBuildSettings
    libraries: List[FirmwareLibraryDependency] = Field(default_factory=list)
    files: List[FirmwareProjectFile] = Field(default_factory=list)
    hardware_diagnostics: List[FirmwareHardwareDiagnostic] = Field(default_factory=list)
    quality_report: FirmwareQualityReport
    last_compile: Optional[FirmwareCompileResult] = None
    versions: List[FirmwareVersionSnapshot] = Field(default_factory=list)
    recovery_guidance: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class FirmwareWorkspaceCreateRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    name: str = Field(..., min_length=2, max_length=160)
    iot_project_id: Optional[str] = None
    board_id: IoTBoardId = "esp32_devkit_v1"
    framework: FirmwareFrameworkId = "arduino_cpp"
    build_settings: Optional[FirmwareBuildSettings] = None


class FirmwareFileUpdateRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    file_path: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., max_length=262144)
    commit_note: str = "Updated firmware source file"
    create_version_snapshot: bool = True


class FirmwareCompileRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    run_unit_tests: bool = True


class FirmwareSerialMonitorRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    mode: Literal["simulated_virtual_serial", "physical_authorized_serial"] = "simulated_virtual_serial"
    serial_port: Optional[str] = None
    simulate_reset_event: Literal["POWERON_RESET", "SW_CPU_RESET", "WDT_RESET", "BROWNOUT_RST"] = "POWERON_RESET"
    lines_count: int = Field(default=8, ge=1, le=30)


class FirmwareDeviceActionRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    action_type: Literal["flash_firmware", "reset_device"] = "flash_firmware"
    target_port: str = "COM3"
    confirmed: bool = False


class FirmwareApproveActionRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    approved: bool = True


class FirmwareRestoreVersionRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    version_id: str


class FirmwareExportResponse(BaseModel):
    export_id: str
    fw_project_id: str
    name: str
    semver: str
    export_directory: str
    workspace_relative_dir: Optional[str] = None
    only_real_artifacts_exported: bool = True
    compiled_binaries_included: bool = False
    artifacts: List[FirmwareArtifactFile] = Field(default_factory=list)
    release_notes_markdown: str
    exported_at: str
    summary: str


class FirmwareMetadataResponse(BaseModel):
    stage: int = 24
    engine: str = "EmbeddedFirmwareStudioEngine"
    reuses_stage23_iot_builder: bool = True
    platform_matrix: List[FirmwarePlatformMatrixEntry] = Field(default_factory=list)
    detected_toolchains: Dict[str, bool] = Field(default_factory=dict)
    connected_serial_ports: List[str] = Field(default_factory=list)
    safety_and_honesty_policy: str


# ============================================================================
# Stage 25: IoT Device Connectivity & Live Telemetry Schemas
# ============================================================================

IoTDeviceStatus = Literal["online", "offline", "degraded", "unprovisioned"]
IoTIngestionProtocol = Literal["http", "mqtt", "dual"]
TelemetryDataProvenance = Literal["physical_device", "deterministic_simulation", "predicted"]

AlertOperator = Literal["gt", "lt", "gte", "lte", "eq", "neq", "outside_range", "device_offline"]
AlertSeverity = Literal["info", "warning", "critical"]
AlertRecordStatus = Literal["active", "acknowledged", "resolved"]

DeviceCommandType = Literal[
    "reboot",
    "set_telemetry_interval",
    "actuator_set_state",
    "set_relay",
    "trigger_calibration",
    "ota_firmware_update",
    "custom_control",
]
CommandConfirmationStatus = Literal["not_required", "pending_confirmation", "confirmed", "rejected"]
CommandDispatchStatus = Literal["queued", "dispatched", "acknowledged", "timed_out", "failed"]


class IoTDeviceRegistrationRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    name: str = Field(..., min_length=2, max_length=120)
    board_id: IoTBoardId = "esp32_devkit_v1"
    is_simulated: bool = False
    mac_address: Optional[str] = None
    chip_id: Optional[str] = None
    firmware_version: str = "1.0.0"
    iot_project_id: Optional[str] = None
    fw_project_id: Optional[str] = None
    ingestion_protocol: IoTIngestionProtocol = "http"
    rate_limit_per_minute: int = Field(default=60, ge=1, le=600)


class IoTDeviceRecord(BaseModel):
    device_id: str
    user_id: str
    workspace_id: str
    name: str
    board_id: IoTBoardId
    is_simulated: bool
    mac_address: Optional[str] = None
    chip_id: Optional[str] = None
    firmware_version: str
    status: IoTDeviceStatus = "unprovisioned"
    iot_project_id: Optional[str] = None
    fw_project_id: Optional[str] = None
    ingestion_protocol: IoTIngestionProtocol = "http"
    mqtt_topic_telemetry: str
    mqtt_topic_commands: str
    rate_limit_per_minute: int
    last_seen_at: Optional[str] = None
    last_reading_age_seconds: Optional[float] = None
    total_events_received: int = 0
    active_alerts_count: int = 0
    created_at: str
    updated_at: str


class IoTDeviceTokenResponse(BaseModel):
    device_id: str
    name: str
    plaintext_token: str
    token_prefix: str
    ingestion_url: str
    mqtt_topic: str
    security_notice: str = (
        "Keep this device token secure. It will never be shown again in plain text. "
        "Include it in the 'X-Device-Token' header for authenticated HTTP telemetry ingestion."
    )


class IoTDeviceTokenRotateRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"


class TelemetryMetricReading(BaseModel):
    key: str = Field(..., min_length=1, max_length=64)
    value: float
    unit: str = Field(default="", max_length=16)


class TelemetryIngestRequest(BaseModel):
    device_id: str
    sequence_id: Optional[int] = None
    device_timestamp: Optional[str] = None
    metrics: Dict[str, float] = Field(..., min_length=1)
    units: Optional[Dict[str, str]] = None
    firmware_version: Optional[str] = None
    battery_level_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    data_provenance: TelemetryDataProvenance = "physical_device"


class TelemetryIngestResponse(BaseModel):
    status: Literal["ACCEPTED", "RATE_LIMITED", "DUPLICATE_IGNORED", "VALIDATION_FAILED"]
    event_id: Optional[str] = None
    device_id: str
    received_metrics_count: int = 0
    triggered_alerts: List[str] = Field(default_factory=list)
    message: str
    ingested_at: str


class TelemetryEventRecord(BaseModel):
    event_id: str
    device_id: str
    workspace_id: str
    sequence_id: Optional[int] = None
    device_timestamp: str
    ingestion_timestamp: str
    metrics: Dict[str, float]
    units: Dict[str, str] = Field(default_factory=dict)
    data_provenance: TelemetryDataProvenance
    is_valid: bool = True
    anomalies: List[str] = Field(default_factory=list)


class AlertRuleCreateRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    metric_key: str = Field(..., min_length=1, max_length=64)
    operator: AlertOperator
    threshold_val_primary: float
    threshold_val_secondary: Optional[float] = None
    severity: AlertSeverity = "warning"
    cooldown_seconds: int = Field(default=300, ge=10, le=86400)
    description: Optional[str] = None


class AlertRuleRecord(BaseModel):
    rule_id: str
    device_id: str
    workspace_id: str
    metric_key: str
    operator: AlertOperator
    threshold_val_primary: float
    threshold_val_secondary: Optional[float] = None
    severity: AlertSeverity
    cooldown_seconds: int
    description: str
    is_enabled: bool = True
    last_triggered_at: Optional[str] = None
    created_at: str


class AlertRecord(BaseModel):
    alert_id: str
    rule_id: str
    device_id: str
    device_name: str
    workspace_id: str
    metric_key: str
    measured_value: float
    threshold_description: str
    severity: AlertSeverity
    status: AlertRecordStatus
    data_provenance: TelemetryDataProvenance
    cooldown_until: Optional[str] = None
    created_at: str
    resolved_at: Optional[str] = None


class AlertAcknowledgeRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    note: Optional[str] = None


class DeviceCommandCreateRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    command_type: DeviceCommandType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    reason: Optional[str] = None


class DeviceCommandConfirmRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    confirmed: bool = True


class DeviceCommandRecord(BaseModel):
    command_id: str
    device_id: str
    device_name: str
    workspace_id: str
    user_id: str
    command_type: DeviceCommandType
    parameters: Dict[str, Any]
    is_consequential: bool
    requires_confirmation: bool
    confirmation_status: CommandConfirmationStatus
    dispatch_status: CommandDispatchStatus
    result_message: str
    dispatched_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    created_at: str


class TelemetrySimulatorTickRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    anomaly_inject: Optional[Literal["spike_temperature", "high_vibration", "low_voltage", "sensor_disconnect"]] = None
    tick_count: int = Field(default=1, ge=1, le=10)


class TelemetrySimulatorResponse(BaseModel):
    device_id: str
    ticks_generated: int
    generated_events: List[TelemetryEventRecord] = Field(default_factory=list)
    triggered_alerts: List[str] = Field(default_factory=list)
    message: str


class TelemetryDeviceStatsResponse(BaseModel):
    device_id: str
    device_name: str
    status: IoTDeviceStatus
    is_simulated: bool
    last_seen_at: Optional[str] = None
    last_seen_seconds_ago: Optional[float] = None
    data_freshness_label: str
    total_events: int
    latest_metrics: Dict[str, float] = Field(default_factory=dict)
    metric_ranges: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    recent_events: List[TelemetryEventRecord] = Field(default_factory=list)
    active_alerts: List[AlertRecord] = Field(default_factory=list)
    pending_commands: List[DeviceCommandRecord] = Field(default_factory=list)


class TelemetryExportRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    format: Literal["csv", "json"] = "csv"
    time_range: Literal["1h", "6h", "24h", "7d", "all"] = "24h"
    handoff_to_file_workspace: bool = False


class TelemetryExportResponse(BaseModel):
    export_id: str
    device_id: str
    format: Literal["csv", "json"]
    time_range: str
    total_events_exported: int
    file_path: Optional[str] = None
    workspace_relative_path: Optional[str] = None
    content_preview: str
    exported_at: str


class TelemetryMetadataResponse(BaseModel):
    stage: int = 25
    engine: str = "IoTTelemetryEngine"
    supported_metrics: List[Dict[str, Any]]
    supported_protocols: List[IoTIngestionProtocol]
    mqtt_broker_config: Dict[str, Any]
    security_policy: Dict[str, Any]
    reliability_specs: Dict[str, Any]


# Stage 26: IoT Security & Device Threat Detection Schemas

SecurityRiskLevel = Literal["critical", "high", "medium", "low", "info", "unknown"]
ThreatClassification = Literal[
    "confirmed_event", "suspicious_indicator", "heuristic_alert", "unverified_hypothesis"
]
IncidentStatus = Literal[
    "new", "under_investigation", "mitigated", "false_positive", "closed"
]
ConfigAuditSeverity = Literal["critical", "high", "medium", "low", "info"]
DefensiveActionType = Literal[
    "revoke_credential",
    "quarantine_device",
    "isolate_network",
    "throttle_telemetry",
    "restore_device",
]
DefensiveActionStatus = Literal[
    "pending_confirmation", "executed", "rejected", "failed"
]


class DeviceSecurityPosture(BaseModel):
    device_id: str
    device_name: str
    board_id: str
    status: str
    is_simulated: bool
    firmware_version: str
    authentication_status: Literal[
        "token_active", "token_revoked", "weak_token", "unprovisioned", "unknown"
    ] = "unknown"
    token_age_days: Optional[float] = None
    token_last_rotated_at: Optional[str] = None
    transport_encryption: Literal["tls_enabled", "plaintext_unencrypted", "unknown"] = "unknown"
    exposed_services: List[str] = Field(default_factory=list)
    update_status: Literal["up_to_date", "update_available", "critical_outdated", "unknown"] = "unknown"
    supports_secure_boot: bool = False
    secure_boot_mechanism: str = "unknown"
    supports_signed_firmware: bool = False
    supports_anti_rollback: bool = False
    last_security_assessment_at: Optional[str] = None
    risk_score: int = Field(default=0, ge=0, le=100)
    risk_level: SecurityRiskLevel = "unknown"
    active_findings_count: int = 0
    active_threats_count: int = 0


class ConfigurationAuditFinding(BaseModel):
    finding_id: str
    device_id: str
    device_name: str
    workspace_id: str
    rule_id: str
    title: str
    severity: ConfigAuditSeverity
    evidence: str
    impact: str
    remediation: str
    status: Literal["active", "remediated", "suppressed", "false_positive"] = "active"
    detected_at: str
    remediated_at: Optional[str] = None


class BehavioralAnomalyRecord(BaseModel):
    anomaly_id: str
    device_id: str
    device_name: str
    workspace_id: str
    anomaly_type: Literal[
        "unusual_reporting_frequency",
        "unexpected_restart_crashloop",
        "abnormal_measurement_pattern",
        "repeated_auth_failures",
        "baseline_deviation",
        "sensor_saturation_stuck",
    ]
    severity: ConfigAuditSeverity
    classification: ThreatClassification
    confidence: Literal["high", "medium", "low"]
    metric_key: Optional[str] = None
    observed_value: Any = None
    baseline_expected: Any = None
    evidence_summary: str
    detected_at: str


class SecurityIncidentRecord(BaseModel):
    incident_id: str
    workspace_id: str
    title: str
    severity: ConfigAuditSeverity
    classification: ThreatClassification
    status: IncidentStatus
    affected_device_ids: List[str] = Field(default_factory=list)
    affected_devices_count: int = 1
    root_cause_hypothesis: str
    confidence_level: Literal["high", "medium", "low"]
    evidence_records: List[Dict[str, Any]] = Field(default_factory=list)
    telemetry_correlations: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_remediations: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None
    assigned_responder: Optional[str] = None


class DefensiveActionRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    device_id: str
    action_type: DefensiveActionType
    reason: str
    confirmed: bool = False


class DefensiveActionRecord(BaseModel):
    action_id: str
    user_id: str
    workspace_id: str
    device_id: str
    device_name: str
    action_type: DefensiveActionType
    reason: str
    requires_confirmation: bool
    status: DefensiveActionStatus
    result_message: str
    recovery_procedure: str
    executed_at: Optional[str] = None
    created_at: str


class FirmwareIntegritySpec(BaseModel):
    board_id: str
    board_name: str
    supports_secure_boot: bool
    secure_boot_version: str
    crypto_keys_supported: List[str] = Field(default_factory=list)
    supports_signed_firmware: bool
    supports_hardware_root_of_trust: bool
    supports_anti_rollback: bool
    recovery_strategy: str
    checksum_trust_limitation: str


class ConfigAuditRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    device_id: Optional[str] = None
    config_payload: Optional[Dict[str, Any]] = None
    config_file_text: Optional[str] = None
    filename: Optional[str] = None


class SecurityIncidentUpdateRequest(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    status: IncidentStatus
    resolution_notes: Optional[str] = None


class IoTSecurityOverviewResponse(BaseModel):
    stage: int = 26
    fleet_posture_summary: Dict[str, Any]
    devices_posture: List[DeviceSecurityPosture] = Field(default_factory=list)
    active_incidents: List[SecurityIncidentRecord] = Field(default_factory=list)
    recent_anomalies: List[BehavioralAnomalyRecord] = Field(default_factory=list)
    config_findings: List[ConfigurationAuditFinding] = Field(default_factory=list)
    firmware_integrity_matrix: List[FirmwareIntegritySpec] = Field(default_factory=list)
    last_assessment_at: str


# ============================================================================
# STAGE 27: ELECTRONIC CIRCUIT SCHEMATIC DESIGN STUDIO SCHEMAS
# ============================================================================

PinType = Literal[
    "passive",
    "power_in",
    "power_out",
    "input",
    "output",
    "bidirectional",
    "open_collector",
    "not_connected",
]

ComponentCategory = Literal[
    "passive_resistor",
    "passive_capacitor",
    "passive_inductor",
    "semiconductor_diode",
    "semiconductor_led",
    "semiconductor_transistor_bjt",
    "semiconductor_transistor_mosfet",
    "analog_opamp",
    "analog_regulator",
    "analog_timer",
    "digital_logic_gate",
    "electromechanical_switch",
    "electromechanical_relay",
    "connector_header",
    "connector_terminal",
    "power_source",
    "microcontroller_module",
    "custom_component",
]


class SchematicPin(BaseModel):
    pin_id: str
    pin_number: str
    name: str
    pin_type: PinType = "passive"
    rel_x: float = 0.0
    rel_y: float = 0.0
    orientation: Literal["left", "right", "top", "bottom"] = "left"
    electrical_type: str = "passive"
    notes: Optional[str] = None


class SchematicComponentDef(BaseModel):
    component_id: str
    name: str
    ref_des_prefix: str
    category: ComponentCategory
    default_value: str
    default_tolerance: str = "5%"
    footprint: str = "0805"
    description: str
    pins: List[SchematicPin] = Field(default_factory=list)
    symbol_type: str
    max_voltage_v: Optional[float] = None
    max_current_ma: Optional[float] = None
    max_power_mw: Optional[float] = None
    forward_voltage_v: Optional[float] = None
    breakdown_voltage_v: Optional[float] = None
    beta_hfe: Optional[float] = None
    quiescent_current_ma: Optional[float] = None
    datasheet_url: Optional[str] = None
    spec_verification: Literal["verified_datasheet_spec", "standard_generic_model", "user_defined"] = "standard_generic_model"
    is_custom: bool = False


class ComponentInstance(BaseModel):
    instance_id: str
    component_id: str
    ref_des: str
    value: str
    tolerance: str = "5%"
    pos_x: float
    pos_y: float
    rotation: int = 0
    mirror: bool = False
    custom_name: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class NetPinConnection(BaseModel):
    instance_id: str
    pin_id: str


class SchematicNet(BaseModel):
    net_id: str
    name: str
    is_power: bool = False
    is_ground: bool = False
    voltage_level_v: Optional[float] = None
    connections: List[NetPinConnection] = Field(default_factory=list)
    color: Optional[str] = None


class WirePoint(BaseModel):
    x: float
    y: float


class WireSegment(BaseModel):
    wire_id: str
    net_id: str
    points: List[WirePoint]


class SchematicSheet(BaseModel):
    sheet_id: str = "sheet_1"
    title: str = "Main Schematic"
    components: List[ComponentInstance] = Field(default_factory=list)
    nets: List[SchematicNet] = Field(default_factory=list)
    wires: List[WireSegment] = Field(default_factory=list)
    annotations: List[Dict[str, Any]] = Field(default_factory=list)


class SchematicProject(BaseModel):
    project_id: str
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    title: str
    description: str = ""
    version: str = "1.0.0"
    sheet: SchematicSheet
    created_at: str
    updated_at: str
    notes: List[str] = Field(default_factory=list)


class SchematicProjectCreate(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    title: str
    description: Optional[str] = ""
    sheet: Optional[SchematicSheet] = None


class SchematicProjectUpdate(BaseModel):
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    title: Optional[str] = None
    description: Optional[str] = None
    sheet: Optional[SchematicSheet] = None
    bump_version: bool = False
    change_note: Optional[str] = None


class ERCFinding(BaseModel):
    finding_id: str
    rule_code: str
    severity: Literal["critical", "warning", "info"]
    title: str
    message: str
    affected_components: List[str] = Field(default_factory=list)
    affected_nets: List[str] = Field(default_factory=list)
    remediation_steps: str
    engineering_disclaimer: str = "Engineering guidance based on component metadata; does not guarantee physical safety."


class ERCReport(BaseModel):
    timestamp: str
    total_findings: int
    critical_count: int
    warning_count: int
    info_count: int
    findings: List[ERCFinding] = Field(default_factory=list)
    passed_rule_checks: List[str] = Field(default_factory=list)


# Engineering Calculators Schemas
class OhmsLawRequest(BaseModel):
    voltage_v: Optional[float] = None
    current_a: Optional[float] = None
    resistance_ohms: Optional[float] = None
    power_w: Optional[float] = None


class OhmsLawResult(BaseModel):
    voltage_v: float
    current_a: float
    resistance_ohms: float
    power_w: float
    recommended_wattage_rating: str
    thermal_derating_advisory: str
    formulas_used: List[str]


class VoltageDividerRequest(BaseModel):
    vin_v: float
    r1_ohms: Optional[float] = None
    r2_ohms: Optional[float] = None
    target_vout_v: Optional[float] = None
    load_resistance_ohms: Optional[float] = None


class ResistorPairRecommendation(BaseModel):
    r1_ohms: float
    r2_ohms: float
    actual_vout_v: float
    error_pct: float
    series: str


class VoltageDividerResult(BaseModel):
    vin_v: float
    r1_ohms: float
    r2_ohms: float
    ideal_vout_v: float
    loaded_vout_v: Optional[float] = None
    loading_effect_error_pct: Optional[float] = None
    quiescent_current_ma: float
    output_impedance_ohms: float
    r1_power_mw: float
    r2_power_mw: float
    recommended_pairs: List[ResistorPairRecommendation] = Field(default_factory=list)
    formulas_used: List[str]


class LEDResistorRequest(BaseModel):
    supply_voltage_v: float
    led_forward_voltage_v: float = 2.0
    led_current_ma: float = 20.0
    led_color: Optional[str] = "red"


class LEDResistorResult(BaseModel):
    supply_voltage_v: float
    led_forward_voltage_v: float
    target_current_ma: float
    calculated_resistance_ohms: float
    standard_e12_resistor_ohms: float
    standard_e24_resistor_ohms: float
    actual_current_with_e24_ma: float
    resistor_power_dissipation_mw: float
    recommended_resistor_power_rating: str
    safety_margin_pct: float
    formulas_used: List[str]


class RCTimeConstantRequest(BaseModel):
    resistance_ohms: float
    capacitance_farads: float
    step_voltage_v: float = 5.0


class RCTimeConstantResult(BaseModel):
    resistance_ohms: float
    capacitance_farads: float
    tau_seconds: float
    tau_formatted: str
    cutoff_frequency_hz: float
    cutoff_frequency_formatted: str
    rise_time_10_90_seconds: float
    time_to_95_pct_seconds: float
    time_to_99_pct_seconds: float
    charge_curve_points: List[Dict[str, float]] = Field(default_factory=list)
    formulas_used: List[str]


class TransistorBiasRequest(BaseModel):
    supply_vcc_v: float
    input_base_voltage_v: float = 3.3
    collector_load_current_ma: float = 50.0
    collector_load_resistance_ohms: Optional[float] = None
    transistor_type: Literal["npn", "pnp"] = "npn"
    vbe_sat_v: float = 0.7
    vce_sat_v: float = 0.2
    typical_beta_hfe: float = 100.0
    forced_beta_saturation: float = 10.0


class TransistorBiasResult(BaseModel):
    transistor_type: str
    required_base_current_ma: float
    base_resistor_ohms: float
    standard_e24_base_resistor_ohms: float
    actual_base_current_ma: float
    collector_current_ma: float
    transistor_power_dissipation_mw: float
    base_resistor_power_mw: float
    saturation_confirmed: bool
    flyback_diode_required: bool
    notes_and_tradeoffs: List[str]
    formulas_used: List[str]


class PowerThermalRequest(BaseModel):
    input_voltage_v: float
    output_voltage_v: float
    load_current_ma: float
    quiescent_current_ma: float = 5.0
    ambient_temp_c: float = 25.0
    package_type: str = "TO-220"
    theta_ja_c_per_w: Optional[float] = None


class PowerThermalResult(BaseModel):
    power_dissipation_w: float
    theta_ja_used: float
    estimated_junction_temp_c: float
    max_recommended_junction_temp_c: float = 125.0
    heatsink_required: bool
    recommended_heatsink_thermal_resistance_c_per_w: Optional[float] = None
    efficiency_pct: float
    thermal_verdict: Literal["safe_without_heatsink", "heatsink_required", "unsafe_thermal_exceeded"]
    advisory: str
    formulas_used: List[str]


class LogicExpressionRequest(BaseModel):
    expression: str  # e.g. "A AND (B OR NOT C)" or "A & (B | ~C)"
    variables: Optional[List[str]] = None


class LogicExpressionResult(BaseModel):
    expression: str
    normalized_expression: str
    variables: List[str]
    truth_table: List[Dict[str, Any]]
    sop_minterms: List[int]
    pos_maxterms: List[int]
    is_tautology: bool
    is_contradiction: bool


# SPICE & Simulation Schemas
class SPICESimulationRequest(BaseModel):
    sheet: SchematicSheet
    analysis_type: Literal["op", "transient", "ac"] = "op"
    tstep_seconds: Optional[float] = 1e-6
    tstop_seconds: Optional[float] = 1e-3
    fstart_hz: Optional[float] = 10.0
    fstop_hz: Optional[float] = 1e6
    points_per_decade: Optional[int] = 10


class SPICESimulationResult(BaseModel):
    analysis_type: str
    sim_status: Literal[
        "completed_host_engine",
        "analytical_ideal_solver",
        "netlist_ready_engine_not_installed",
        "simulation_error",
    ]
    engine_name: str
    netlist_text: str
    node_voltages: Dict[str, float] = Field(default_factory=dict)
    branch_currents: Dict[str, float] = Field(default_factory=dict)
    waveform_data: Optional[Dict[str, List[float]]] = None
    log_output: str
    model_limitations: List[str] = Field(default_factory=list)
    anti_fabrication_note: str


# AI Circuit Assistant Schemas
class AICircuitPromptRequest(BaseModel):
    prompt: str
    target_supply_voltage_v: Optional[float] = 5.0
    preferred_components: Optional[List[str]] = None


class AICircuitDesignResponse(BaseModel):
    circuit_name: str
    description: str
    operational_explanation: str
    sheet: SchematicSheet
    design_notes: List[str]
    engineering_assumptions: List[str]
    design_warnings: List[str]
    engineering_review_required: bool = True
    review_banner: str = "MANDATORY REVIEW: AI-generated electronic schematic requires qualified engineering verification before prototyping, simulation sign-off, or physical PCB fabrication."


# Export Schemas
class SchematicExportResponse(BaseModel):
    export_format: Literal[
        "spice_netlist",
        "kicad_netlist",
        "bom_json",
        "bom_csv",
        "svg_schematic",
        "connection_table_json",
    ]
    content: str
    filename: str
    mime_type: str


class SchematicOverviewResponse(BaseModel):
    stage: int = 27
    projects_count: int
    custom_components_count: int
    recent_projects: List[SchematicProject] = Field(default_factory=list)
    standard_components_count: int
    toolchains: Dict[str, bool] = Field(default_factory=dict)







