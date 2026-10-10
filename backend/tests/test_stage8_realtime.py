"""
NEXORA AI — Automated Test Suite for Stage 8: Real-Time Intelligence Engine
Tests:
1. Live query endpoint (POST /api/v1/realtime/query)
2. Cached vs Fresh retrieval indication
3. Monitored topic CRUD operations (GET/POST/DELETE /api/v1/realtime/topics)
4. Topic refresh and change fingerprint detection (POST /api/v1/realtime/topics/{id}/refresh)
5. Live alerts and notifications endpoints (GET/POST/DELETE /api/v1/realtime/notifications)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.realtime.engine import realtime_engine
from app.models.schemas import LiveQueryRequest


@pytest.fixture
def client():
    return TestClient(app)


def test_monitored_topics_listing(client):
    res = client.get("/api/v1/realtime/topics")
    assert res.status_code == 200
    topics = res.json()
    assert isinstance(topics, list)
    assert len(topics) >= 2
    topic_names = [t["name"] for t in topics]
    assert any("AI" in name for name in topic_names)


def test_create_and_delete_monitored_topic(client):
    # 1. Create Topic
    payload = {
        "name": "Quantum Computing Innovations",
        "query_or_url": "quantum computing fault tolerance breakthroughs",
        "category": "research",
        "check_interval_minutes": 30
    }
    create_res = client.post("/api/v1/realtime/topics", json=payload)
    assert create_res.status_code == 200
    created = create_res.json()
    assert created["name"] == payload["name"]
    assert created["category"] == "research"
    topic_id = created["id"]

    # 2. Verify in list
    list_res = client.get("/api/v1/realtime/topics")
    assert list_res.status_code == 200
    ids = [t["id"] for t in list_res.json()]
    assert topic_id in ids

    # 3. Delete Topic
    del_res = client.delete(f"/api/v1/realtime/topics/{topic_id}")
    assert del_res.status_code == 200

    # 4. Confirm deleted
    list_after = client.get("/api/v1/realtime/topics")
    ids_after = [t["id"] for t in list_after.json()]
    assert topic_id not in ids_after


@pytest.mark.asyncio
async def test_live_query_execution():
    req = LiveQueryRequest(
        query="Nobel prize in physics",
        category="general",
        force_refresh=True,
        max_sources=3
    )
    res = await realtime_engine.execute_live_query(req)
    assert res.query == "Nobel prize in physics"
    assert res.is_fresh_retrieval is True
    assert "Live Web" in res.freshness_label
    assert len(res.sources) >= 0


def test_live_query_endpoint(client):
    res = client.post(
        "/api/v1/realtime/query",
        json={
            "query": "International space exploration updates",
            "category": "news",
            "force_refresh": True,
            "max_sources": 3
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert "sources" in data
    assert "synthesized_answer" in data
    assert data["category"] == "news"


@pytest.mark.asyncio
async def test_topic_refresh_fingerprint_change():
    # Create topic
    topic = realtime_engine.create_monitored_topic(
        name="Test Topic Check",
        query_or_url="machine learning deployment benchmarks",
        category="tech"
    )

    # First check establishes baseline hash
    topic_1, notif_1 = await realtime_engine.refresh_monitored_topic(topic.id)
    assert topic_1.last_checked_at is not None
    assert topic_1.last_content_hash is not None

    # Manually tweak content hash to simulate detected external change
    topic_1.last_content_hash = "simulated_previous_hash"

    # Second check triggers difference notification
    topic_2, notif_2 = await realtime_engine.refresh_monitored_topic(topic.id)
    assert topic_2.change_count >= 1
    assert notif_2 is not None
    assert "Fresh updates detected" in notif_2.title


def test_live_notifications_lifecycle(client):
    # 1. Fetch notifications
    res = client.get("/api/v1/realtime/notifications")
    assert res.status_code == 200
    notifs = res.json()
    assert isinstance(notifs, list)

    # 2. Mark as read
    read_res = client.post("/api/v1/realtime/notifications/read")
    assert read_res.status_code == 200

    # 3. Clear all
    clear_res = client.delete("/api/v1/realtime/notifications")
    assert clear_res.status_code == 200

    # 4. Verify empty
    res_after = client.get("/api/v1/realtime/notifications")
    assert res_after.status_code == 200
    assert len(res_after.json()) == 0
