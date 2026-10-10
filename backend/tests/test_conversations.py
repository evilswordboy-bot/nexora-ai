from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_conversations_crud():
    # 1. Create conversation
    create_res = client.post("/api/v1/conversations", json={"title": "Test Chat"})
    assert create_res.status_code == 201
    conv = create_res.json()
    conv_id = conv["id"]
    assert conv["title"] == "Test Chat"

    # 2. Get conversation
    get_res = client.get(f"/api/v1/conversations/{conv_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == conv_id

    # 3. Update conversation
    patch_res = client.patch(f"/api/v1/conversations/{conv_id}", json={"title": "Updated Title"})
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Updated Title"

    # 4. List conversations
    list_res = client.get("/api/v1/conversations")
    assert list_res.status_code == 200
    assert any(c["id"] == conv_id for c in list_res.json())

    # 5. Delete conversation
    del_res = client.delete(f"/api/v1/conversations/{conv_id}")
    assert del_res.status_code == 204

    # 6. Verify 404
    verify_res = client.get(f"/api/v1/conversations/{conv_id}")
    assert verify_res.status_code == 404


def test_honest_unconfigured_chat_response():
    # Send a chat message when no API key is provided
    payload = {
        "messages": [
            {"id": "msg-1", "role": "user", "content": "Hello NEXORA"}
        ],
        "provider": "auto",
    }
    res = client.post("/api/v1/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    # Must NOT return fake AI hallucinations! Must report unconfigured status honestly
    assert "Setup Required" in data["content"] or "No active AI provider" in data["content"]
    assert data["finish_reason"] == "unconfigured_provider"
