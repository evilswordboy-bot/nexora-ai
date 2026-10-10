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



