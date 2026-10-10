from abc import ABC, abstractmethod
from typing import AsyncGenerator, List
from app.models.schemas import ChatRequest, ChatResponse, Message
from app.config import settings


class BaseAIProvider(ABC):
    """
    Abstract Base Class for NEXORA AI Providers.
    Encapsulates context formatting, synchronous generation, and SSE streaming.
    """

    @abstractmethod
    async def generate(self, request: ChatRequest, api_key: str) -> ChatResponse:
        """Non-streaming generation returning complete response."""
        pass

    @abstractmethod
    async def stream(self, request: ChatRequest, api_key: str) -> AsyncGenerator[dict, None]:
        """Streaming token generator yielding structured SSE dictionaries."""
        pass

    def prepare_context_messages(self, messages: List[Message], max_messages: int = None) -> List[Message]:
        """
        Maintains correct message order while respecting configured context limits.
        Keeps the latest `max_messages` to fit context window budget.
        """
        limit = max_messages or settings.max_context_messages
        if len(messages) <= limit:
            return messages
        return messages[-limit:]
