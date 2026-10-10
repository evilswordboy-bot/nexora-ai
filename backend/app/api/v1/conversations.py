from typing import List
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import Conversation, ConversationCreate, ConversationUpdate
from app.services.conversation_service import conversation_service

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=List[Conversation])
async def list_conversations():
    return conversation_service.list_all()


@router.post("", response_model=Conversation, status_code=status.HTTP_201_CREATED)
async def create_conversation(data: ConversationCreate):
    return conversation_service.create(data)


@router.get("/{conv_id}", response_model=Conversation)
async def get_conversation(conv_id: str):
    conv = conversation_service.get(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.patch("/{conv_id}", response_model=Conversation)
async def update_conversation(conv_id: str, data: ConversationUpdate):
    conv = conversation_service.update(conv_id, data)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conv_id: str):
    success = conversation_service.delete(conv_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return None


@router.delete("", status_code=status.HTTP_200_OK)
async def clear_all_conversations():
    deleted_count = conversation_service.clear_all()
    return {"message": f"Successfully deleted {deleted_count} conversations"}
