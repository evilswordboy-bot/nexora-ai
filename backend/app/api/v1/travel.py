from __future__ import annotations

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Header, status

from app.models.schemas import (
    TravelProductItem,
    TravelSearchQuery,
    TravelHoldRequest,
    TravelHoldResponse,
    TravelBookingRequest,
    TravelBookingRecord,
    TravelCancellationRequest,
    TravelRescheduleRequest,
    TravelAuditRecord,
    TravelOverviewResponse,
)
from app.services.travel_commerce import travel_engine, travel_registry

router = APIRouter(prefix="/travel", tags=["Universal Travel & Ticket Booking"])


@router.get("/overview", response_model=TravelOverviewResponse)
def get_travel_overview(user_id: str = Query("default_user")):
    """Returns overview statistics of travel providers, bookings, and categories."""
    return travel_engine.get_overview(user_id=user_id)


@router.get("/providers")
def get_registered_providers():
    """Lists all active travel & ticketing provider adapters."""
    return {
        "providers": travel_registry.list_active_providers(),
        "total_active": len(travel_registry.list_active_providers()),
    }


@router.post("/search", response_model=List[TravelProductItem])
def search_travel_products(query: TravelSearchQuery):
    """
    Unified multi-provider search across flights, trains, buses, hotels, movies, and events.
    Applies filters for dates, price range, cabin/class, accessibility, and passenger counts.
    """
    results = travel_engine.search(query)
    return results


@router.get("/products/{product_id}", response_model=TravelProductItem)
def get_product_details(product_id: str):
    """Retrieves live availability, seat counts, and pricing breakdown for a specific product."""
    product = travel_registry.find_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Travel product '{product_id}' was not found or is no longer available.",
        )
    return product


@router.post("/hold", response_model=TravelHoldResponse)
def hold_inventory(req: TravelHoldRequest):
    """Temporarily holds inventory for a guaranteed checkout window (default 15 minutes)."""
    try:
        return travel_engine.create_hold(req)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/book", response_model=TravelBookingRecord)
def book_travel(
    req: TravelBookingRequest,
    idempotency_header: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Executes a purchase with explicit passenger manifest and tokenized payment.
    Enforces strict idempotency — repeating a request with the same idempotency key
    returns the confirmed booking with is_idempotent_replay=True without double billing.
    """
    if idempotency_header and not req.idempotency_key:
        req.idempotency_key = idempotency_header

    if not req.idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required idempotency key. Provide 'idempotency_key' in body or 'Idempotency-Key' header.",
        )

    try:
        booking = travel_engine.confirm_booking(req)
        return booking
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Booking transaction failed: {str(e)}",
        )


@router.get("/bookings", response_model=List[TravelBookingRecord])
def list_bookings(
    user_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
):
    """Lists bookings with optional filters by user, category, or status."""
    return travel_engine.list_bookings(user_id=user_id, category=category, status=status, limit=limit)


@router.get("/bookings/{booking_id}", response_model=TravelBookingRecord)
def get_booking_details(booking_id: str):
    """Retrieves full booking details, provider confirmation references, and receipts."""
    booking = travel_engine.get_booking(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking '{booking_id}' not found.",
        )
    return booking


@router.post("/cancel", response_model=TravelBookingRecord)
def cancel_booking(req: TravelCancellationRequest, user_id: str = Query("default_user")):
    """
    Cancels an existing booking, evaluates provider cancellation policy and refund eligibility,
    and updates booking status and ledger.
    """
    try:
        return travel_engine.cancel_booking(req, user_id=user_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/reschedule", response_model=TravelBookingRecord)
def reschedule_booking(req: TravelRescheduleRequest, user_id: str = Query("default_user")):
    """Reschedules travel dates if permitted by ticket tier and provider rules."""
    try:
        return travel_engine.reschedule_booking(req, user_id=user_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/audit", response_model=List[TravelAuditRecord])
def get_audit_trail(booking_id: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=100)):
    """Retrieves immutable audit trail for security, compliance, and dispute resolution."""
    return travel_engine.get_audit_trail(booking_id=booking_id, limit=limit)
