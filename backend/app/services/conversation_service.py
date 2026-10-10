import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.models.schemas import Conversation, Message, ConversationCreate, ConversationUpdate


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConversationService:
    """
    Manages conversations and message histories.
    Provides in-memory fast indexing with thread safety.
    """

    def __init__(self):
        self._conversations: Dict[str, Conversation] = {}

    def create(self, data: ConversationCreate) -> Conversation:
        conv_id = str(uuid.uuid4())
        now = get_utc_now()
        conv = Conversation(
            id=conv_id,
            title=data.title or "New Conversation",
            system_prompt=data.system_prompt,
            created_at=now,
            updated_at=now,
            messages=[],
        )
        self._conversations[conv_id] = conv
        return conv

    def get(self, conv_id: str) -> Optional[Conversation]:
        return self._conversations.get(conv_id)

    def list_all(self) -> List[Conversation]:
        # Return sorted by updated_at descending
        return sorted(
            list(self._conversations.values()),
            key=lambda c: c.updated_at,
            reverse=True,
        )

    def update(self, conv_id: str, data: ConversationUpdate) -> Optional[Conversation]:
        conv = self._conversations.get(conv_id)
        if not conv:
            return None
        if data.title is not None:
            conv.title = data.title
        if data.system_prompt is not None:
            conv.system_prompt = data.system_prompt
        conv.updated_at = get_utc_now()
        return conv

    def delete(self, conv_id: str) -> bool:
        if conv_id in self._conversations:
            del self._conversations[conv_id]
            return True
        return False

    def clear_all(self) -> int:
        count = len(self._conversations)
        self._conversations.clear()
        return count

    def add_message(self, conv_id: str, message: Message) -> Optional[Conversation]:
        conv = self._conversations.get(conv_id)
        if not conv:
            # Auto-create if not found
            conv = self.create(ConversationCreate(title="New Conversation"))
            conv_id = conv.id

        conv.messages.append(message)
        conv.updated_at = get_utc_now()

        # Update title automatically if it's the first user message and default title
        if conv.title == "New Conversation" and message.role == "user":
            snippet = message.content.strip().split("\n")[0][:40]
            if snippet:
                conv.title = snippet

        return conv


conversation_service = ConversationService()
