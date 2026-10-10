from datetime import datetime, timezone
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Message(BaseModel):
    id: str = Field(..., description="Unique ID for the message")
    role: Literal["user", "assistant", "system"] = Field(..., description="Role of the author")
    content: str = Field(..., description="Text content of the message")
    timestamp: datetime = Field(default_factory=utc_now)
    model: Optional[str] = None
    provider: Optional[str] = None
    error: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None


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
    client_api_key: Optional[str] = None  # Optional key provided securely from user's client settings


class ChatResponse(BaseModel):
    id: str
    conversation_id: Optional[str] = None
    role: Literal["assistant"] = "assistant"
    content: str
    model: str
    provider: str
    finish_reason: Optional[str] = "stop"
    usage: Optional[Dict[str, int]] = None
    created_at: datetime = Field(default_factory=utc_now)


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
    instructions: str


class SafetyCheckResult(BaseModel):
    is_safe: bool
    flagged: bool
    category: Optional[str] = None
    reason: Optional[str] = None
    educational_override: bool = False
