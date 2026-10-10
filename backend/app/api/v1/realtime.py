"""
NEXORA AI — Real-Time Intelligence API Router
Provides:
- POST /api/v1/realtime/query: Live web search & evidence synthesis
- GET /api/v1/realtime/topics: List saved monitored topics and feeds
- POST /api/v1/realtime/topics: Create a new topic or URL to monitor
- DELETE /api/v1/realtime/topics/{id}: Remove a monitored topic
- POST /api/v1/realtime/topics/{id}/refresh: Manual trigger to check for live changes
- GET /api/v1/realtime/notifications: List live alert notifications
- POST /api/v1/realtime/notifications/read: Mark all alerts as read
- DELETE /api/v1/realtime/notifications: Clear alert notifications
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional

from app.models.schemas import (
    LiveCategory,
    MonitoredTopic,
    LiveNotification,
    LiveQueryRequest,
    LiveQueryResponse
)
from app.services.realtime.engine import realtime_engine

router = APIRouter(prefix="/realtime", tags=["Real-Time Intelligence Engine"])


class CreateTopicRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    query_or_url: str = Field(..., min_length=3, max_length=500)
    category: LiveCategory = "general"
    check_interval_minutes: int = Field(60, ge=15, le=1440)


class RefreshTopicRequest(BaseModel):
    provider: Optional[str] = "auto"
    model: Optional[str] = "gemini-1.5-flash"
    client_api_key: Optional[str] = None


@router.post("/query", response_model=LiveQueryResponse)
async def query_live_intelligence(request: LiveQueryRequest):
    """Executes a live information retrieval query with freshness tracking and citations."""
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    try:
        return await realtime_engine.execute_live_query(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Live intelligence query failed: {str(e)}")


@router.get("/topics", response_model=List[MonitoredTopic])
async def list_monitored_topics():
    """Returns list of active monitored topics, feeds, and websites."""
    return realtime_engine.get_monitored_topics()


@router.post("/topics", response_model=MonitoredTopic)
async def create_monitored_topic(request: CreateTopicRequest):
    """Adds a new research topic or URL for continuous change monitoring."""
    return realtime_engine.create_monitored_topic(
        name=request.name,
        query_or_url=request.query_or_url,
        category=request.category,
        check_interval_minutes=request.check_interval_minutes
    )


@router.delete("/topics/{topic_id}")
async def delete_monitored_topic(topic_id: str):
    """Deletes a monitored topic."""
    success = realtime_engine.delete_monitored_topic(topic_id)
    if not success:
        raise HTTPException(status_code=404, detail="Monitored topic not found.")
    return {"status": "deleted", "topic_id": topic_id}


@router.post("/topics/{topic_id}/refresh", response_model=MonitoredTopic)
async def refresh_monitored_topic(topic_id: str, request: RefreshTopicRequest = RefreshTopicRequest()):
    """Triggers an on-demand freshness check and change comparison."""
    try:
        topic, notification = await realtime_engine.refresh_monitored_topic(
            topic_id=topic_id,
            provider=request.provider or "auto",
            model=request.model or "gemini-1.5-flash",
            client_api_key=request.client_api_key
        )
        return topic
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Topic refresh failed: {str(e)}")


@router.get("/notifications", response_model=List[LiveNotification])
async def get_live_notifications():
    """Returns all change notifications from monitored feeds."""
    return realtime_engine.get_notifications()


@router.post("/notifications/read")
async def mark_notifications_as_read():
    """Marks all live notifications as read."""
    realtime_engine.mark_notifications_read()
    return {"status": "success", "message": "All notifications marked as read."}


@router.delete("/notifications")
async def clear_all_notifications():
    """Clears notification history."""
    realtime_engine.clear_notifications()
    return {"status": "success", "message": "Notification history cleared."}
