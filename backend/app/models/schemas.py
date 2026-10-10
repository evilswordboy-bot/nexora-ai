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





