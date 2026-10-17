"""
NEXORA AI — Stage 29: Universal Travel & Ticket Booking
Comprehensive Test Suite
"""

import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.services.tools_registry import tool_registry
from app.services.travel_commerce import travel_engine, travel_registry

client = TestClient(app)


def test_travel_overview_and_providers():
    response = client.get("/api/v1/travel/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["stage"] == 29
    assert len(data["active_providers"]) >= 6
    assert "flight" in data["supported_categories"]
    assert "hotel" in data["supported_categories"]
    assert "movie" in data["supported_categories"]

    prov_resp = client.get("/api/v1/travel/providers")
    assert prov_resp.status_code == 200
    prov_data = prov_resp.json()
    assert prov_data["total_active"] >= 6


def test_travel_search_multi_category():
    # 1. Flight search
    flight_res = client.post(
        "/api/v1/travel/search",
        json={
            "category": "flight",
            "origin": "SFO",
            "destination": "JFK",
            "departure_date": "2026-11-10",
            "passengers_count": 2,
        },
    )
    assert flight_res.status_code == 200
    flights = flight_res.json()
    assert len(flights) >= 1
    f0 = flights[0]
    assert f0["category"] == "flight"
    assert f0["price_breakdown"]["total_amount"] > 0
    assert f0["cancellation_policy"]["is_refundable"] is True

    # 2. Train search
    train_res = client.post(
        "/api/v1/travel/search",
        json={
            "category": "train",
            "origin": "Paris",
            "destination": "London",
            "departure_date": "2026-11-12",
            "passengers_count": 1,
        },
    )
    assert train_res.status_code == 200
    trains = train_res.json()
    assert len(trains) >= 1

    # 3. Movie search
    movie_res = client.post(
        "/api/v1/travel/search",
        json={
            "category": "movie",
            "destination": "San Francisco",
            "departure_date": "2026-11-05",
            "passengers_count": 1,
        },
    )
    assert movie_res.status_code == 200
    movies = movie_res.json()
    assert len(movies) >= 1
    assert "IMAX" in movies[0]["title"] or "Laser" in movies[0]["origin"]


def test_travel_hold_inventory():
    hold_req = {
        "product_id": "FL-AMD-101",
        "category": "flight",
        "provider": "Amadeus Global Distribution",
        "passengers_count": 1,
        "user_id": "test_traveler",
    }
    resp = client.post("/api/v1/travel/hold", json=hold_req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["hold_id"].startswith("HLD-")
    assert data["status"] == "HELD"
    assert data["locked_price"]["total_amount"] > 0


def test_travel_booking_success_and_idempotency():
    idemp_key = f"TEST-IDEMP-{uuid.uuid4().hex[:10]}"
    booking_payload = {
        "idempotency_key": idemp_key,
        "product_id": "FL-AMD-101",
        "category": "flight",
        "passengers": [
            {
                "passenger_id": "PAX-1",
                "first_name": "Eleanor",
                "last_name": "Vance",
                "email": "eleanor.vance@nexora.ai",
                "seat_preference": "12A Window",
            }
        ],
        "payment": {
            "payment_method": "tokenized_card",
            "payment_token": "tok_visa_4242_stage29",
            "card_brand": "Visa",
            "card_last4": "4242",
            "billing_name": "Eleanor Vance",
        },
        "explicit_confirmation": True,
        "contact_email": "eleanor.vance@nexora.ai",
        "user_id": "user_eleanor",
    }

    # First booking attempt
    resp1 = client.post("/api/v1/travel/book", json=booking_payload)
    assert resp1.status_code == 200
    b1 = resp1.json()
    assert b1["booking_id"].startswith("BKG-")
    assert b1["booking_status"] == "CONFIRMED"
    assert b1["provider_booking_ref"].startswith("AMD-")
    assert b1["is_idempotent_replay"] is False
    assert "receipts" in b1["receipt_url"]

    # Second booking attempt with identical idempotency key -> MUST return exact same booking with is_idempotent_replay=True
    resp2 = client.post("/api/v1/travel/book", json=booking_payload)
    assert resp2.status_code == 200
    b2 = resp2.json()
    assert b2["booking_id"] == b1["booking_id"]
    assert b2["is_idempotent_replay"] is True


def test_travel_cancellation_and_reschedule():
    # Create fresh booking
    idemp_key = f"TEST-CANCEL-{uuid.uuid4().hex[:10]}"
    booking_payload = {
        "idempotency_key": idemp_key,
        "product_id": "TRN-EUR-201",
        "category": "train",
        "passengers": [
            {
                "passenger_id": "PAX-1",
                "first_name": "Arthur",
                "last_name": "Dent",
                "email": "arthur.dent@nexora.ai",
            }
        ],
        "payment": {
            "payment_method": "tokenized_card",
            "payment_token": "tok_visa_4242_train",
            "card_brand": "Mastercard",
            "card_last4": "5555",
            "billing_name": "Arthur Dent",
        },
        "explicit_confirmation": True,
        "contact_email": "arthur.dent@nexora.ai",
        "user_id": "user_arthur",
    }
    book_resp = client.post("/api/v1/travel/book", json=booking_payload)
    assert book_resp.status_code == 200
    booking = book_resp.json()
    b_id = booking["booking_id"]

    # Reschedule
    resch_resp = client.post(
        "/api/v1/travel/reschedule",
        json={
            "booking_id": b_id,
            "new_departure_date": "2026-12-01",
            "reason": "Business trip postponed",
        },
    )
    assert resch_resp.status_code == 200
    resch_data = resch_resp.json()
    assert resch_data["booking_status"] == "RESCHEDULED"
    assert resch_data["departure_date"] == "2026-12-01"

    # Cancel
    canc_resp = client.post(
        "/api/v1/travel/cancel",
        json={
            "booking_id": b_id,
            "reason": "Trip no longer required",
            "confirm_cancellation": True,
        },
    )
    assert canc_resp.status_code == 200
    canc_data = canc_resp.json()
    assert canc_data["booking_status"] == "CANCELLED"
    assert canc_data["refund_status"] in ("COMPLETED", "PARTIAL")
    assert canc_data["refund_amount"] > 0


def test_travel_audit_trail_and_health():
    # Audit log
    audit_resp = client.get("/api/v1/travel/audit")
    assert audit_resp.status_code == 200
    records = audit_resp.json()
    assert len(records) > 0
    assert any(r["action"] == "CONFIRM_BOOKING" for r in records)

    # Health check reflects Stage 29
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    h_data = health_resp.json()
    assert h_data["stage"] == 29
    assert h_data["stage_title"] == "Universal Travel & Ticket Booking Studio"

    assert h_data["subsystems"]["travel_booking"] == "operational"


@pytest.mark.asyncio
async def test_tool_travel_booking_engine():
    tool = tool_registry.get_tool("travel_booking_engine")
    assert tool is not None
    assert tool.stage_introduced == 29

    # Test tool action search
    search_res = await tool_registry.execute(
        "travel_booking_engine",
        {
            "action": "search",
            "category": "flight",
            "destination": "JFK",
            "passengers_count": 1,
        },
    )
    assert search_res["success"] is True
    assert search_res["data"]["action"] == "search"
    assert search_res["data"]["count"] >= 1

    # Test tool action book
    book_res = await tool_registry.execute(
        "travel_booking_engine",
        {
            "action": "book",
            "product_id": "FL-AMD-101",
            "category": "flight",
            "contact_email": "agent.traveler@nexora.ai",
            "user_id": "agent_user",
        },
    )
    assert book_res["success"] is True
    assert book_res["data"]["action"] == "book"
    assert "booking" in book_res["data"]
    assert book_res["data"]["booking"]["booking_status"] == "CONFIRMED"

