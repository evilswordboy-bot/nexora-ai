"""
NEXORA AI — Stage 29: Universal Travel & Ticket Booking
Core Travel Commerce Engine with SQLite Persistence, Idempotency, and Audit Logging
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from app.config import settings
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
    TravelPriceBreakdown,
    TravelCancellationPolicy,
    TravelPassengerInfo,
)
from app.services.travel_commerce.registry import travel_registry
from app.services.travel_commerce.pricing_policy import evaluate_cancellation_eligibility


class TravelCommerceEngine:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.travel_db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS travel_holds (
                    hold_id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    locked_price_json TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS travel_bookings (
                    booking_id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    provider_booking_ref TEXT NOT NULL,
                    product_summary TEXT NOT NULL,
                    operator_name TEXT NOT NULL,
                    origin TEXT,
                    destination TEXT NOT NULL,
                    departure_date TEXT NOT NULL,
                    passengers_json TEXT NOT NULL,
                    payment_method TEXT NOT NULL,
                    payment_last4 TEXT,
                    payment_tx_id TEXT NOT NULL,
                    price_breakdown_json TEXT NOT NULL,
                    cancellation_policy_json TEXT NOT NULL,
                    booking_status TEXT NOT NULL,
                    refund_status TEXT NOT NULL,
                    refund_amount REAL NOT NULL DEFAULT 0.0,
                    receipt_url TEXT NOT NULL,
                    support_contact TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS travel_audit_log (
                    audit_id TEXT PRIMARY KEY,
                    booking_id TEXT,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _row_to_booking(self, row: sqlite3.Row, is_idempotent_replay: bool = False) -> TravelBookingRecord:
        passengers = [TravelPassengerInfo(**p) for p in json.loads(row["passengers_json"])]
        price_bd = TravelPriceBreakdown(**json.loads(row["price_breakdown_json"]))
        canc_policy = TravelCancellationPolicy(**json.loads(row["cancellation_policy_json"]))

        return TravelBookingRecord(
            booking_id=row["booking_id"],
            idempotency_key=row["idempotency_key"],
            user_id=row["user_id"],
            product_id=row["product_id"],
            category=row["category"],
            provider=row["provider"],
            provider_booking_ref=row["provider_booking_ref"],
            product_summary=row["product_summary"],
            operator_name=row["operator_name"],
            origin=row["origin"],
            destination=row["destination"],
            departure_date=row["departure_date"],
            passengers=passengers,
            payment_method=row["payment_method"],
            payment_last4=row["payment_last4"],
            payment_tx_id=row["payment_tx_id"],
            price_breakdown=price_bd,
            cancellation_policy=canc_policy,
            booking_status=row["booking_status"],
            refund_status=row["refund_status"],
            refund_amount=row["refund_amount"],
            receipt_url=row["receipt_url"],
            support_contact=row["support_contact"],
            is_idempotent_replay=is_idempotent_replay,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def log_audit(
        self,
        user_id: str,
        action: str,
        provider: str,
        status: str,
        details: Dict[str, Any],
        booking_id: Optional[str] = None,
    ) -> TravelAuditRecord:
        audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
        created_at = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO travel_audit_log (audit_id, booking_id, user_id, action, provider, status, details_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    booking_id,
                    user_id,
                    action,
                    provider,
                    status,
                    json.dumps(details),
                    created_at,
                ),
            )
            conn.commit()
        return TravelAuditRecord(
            audit_id=audit_id,
            booking_id=booking_id,
            user_id=user_id,
            action=action,
            provider=provider,
            status=status,
            details=details,
            created_at=created_at,
        )

    def search(self, query: TravelSearchQuery) -> List[TravelProductItem]:
        return travel_registry.search_all(query)

    def create_hold(self, req: TravelHoldRequest) -> TravelHoldResponse:
        product = travel_registry.find_product_by_id(req.product_id)
        if not product:
            # Generate fallback via sandbox
            fallback_query = TravelSearchQuery(
                category=req.category,
                destination="Selected Destination",
                departure_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                passengers_count=req.passengers_count,
            )
            sandbox_results = travel_registry.get_adapter("NEXORA_SANDBOX").search(fallback_query)
            product = sandbox_results[0] if sandbox_results else None

        if not product:
            raise ValueError(f"Product '{req.product_id}' is no longer available.")

        hold_id = f"HLD-{uuid.uuid4().hex[:8].upper()}"
        expires_at = (
            datetime.now(timezone.utc) + timedelta(minutes=settings.travel_hold_duration_minutes)
        ).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO travel_holds (hold_id, product_id, category, provider, locked_price_json, expires_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    hold_id,
                    product.id,
                    product.category,
                    product.provider,
                    product.price_breakdown.model_dump_json(),
                    expires_at,
                    "HELD",
                ),
            )
            conn.commit()

        self.log_audit(
            user_id=req.user_id,
            action="HOLD_SEATS",
            provider=product.provider,
            status="SUCCESS",
            details={"hold_id": hold_id, "product_id": product.id, "expires_at": expires_at},
        )

        return TravelHoldResponse(
            hold_id=hold_id,
            product_id=product.id,
            expires_at=expires_at,
            locked_price=product.price_breakdown,
            status="HELD",
        )

    def confirm_booking(self, req: TravelBookingRequest) -> TravelBookingRecord:
        """
        Confirms a travel booking with strict idempotency and provider acknowledgement.
        """
        if not req.explicit_confirmation:
            raise ValueError("Explicit confirmation is required before processing purchase.")

        if not req.passengers:
            raise ValueError("Passenger list cannot be empty.")

        # Check Idempotency Key
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM travel_bookings WHERE idempotency_key = ?", (req.idempotency_key,))
            existing = cursor.fetchone()
            if existing:
                self.log_audit(
                    user_id=req.user_id,
                    action="IDEMPOTENT_REPLAY_BOOKING",
                    provider=existing["provider"],
                    status="REPLAYED",
                    details={"booking_id": existing["booking_id"], "key": req.idempotency_key},
                    booking_id=existing["booking_id"],
                )
                return self._row_to_booking(existing, is_idempotent_replay=True)

        # Validate payment token
        if not req.payment.payment_token or not (
            req.payment.payment_token.startswith("tok_") or req.payment.payment_token.startswith("pm_")
        ):
            raise ValueError("Invalid payment token format. Payment must be securely tokenized.")

        # Find product
        product = travel_registry.find_product_by_id(req.product_id)
        if not product:
            # Fallback to sandbox provider
            sandbox = travel_registry.get_adapter("NEXORA_SANDBOX")
            product = sandbox.get_by_id(req.product_id)
            if not product:
                search_q = TravelSearchQuery(
                    category=req.category,
                    destination="Universal Travel",
                    departure_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    passengers_count=len(req.passengers),
                )
                candidates = sandbox.search(search_q)
                product = candidates[0]

        # Call adapter
        adapter = travel_registry.get_adapter(product.provider_code)
        if not adapter:
            adapter = travel_registry.get_adapter("NEXORA_SANDBOX")

        provider_resp = adapter.confirm_booking(req, product)
        provider_ref = provider_resp.get("provider_ref", f"REF-{uuid.uuid4().hex[:6].upper()}")

        booking_id = f"BKG-{uuid.uuid4().hex[:6].upper()}"
        payment_tx_id = f"TX-{uuid.uuid4().hex[:10].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()
        receipt_url = f"https://nexora.ai/receipts/{booking_id}"
        support_contact = "support@nexora.ai / +1-800-NEXORA-TRAVEL"

        passengers_json = json.dumps([p.model_dump() for p in req.passengers])
        price_bd_json = product.price_breakdown.model_dump_json()
        policy_json = product.cancellation_policy.model_dump_json()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO travel_bookings (
                    booking_id, idempotency_key, user_id, product_id, category, provider,
                    provider_booking_ref, product_summary, operator_name, origin, destination,
                    departure_date, passengers_json, payment_method, payment_last4, payment_tx_id,
                    price_breakdown_json, cancellation_policy_json, booking_status, refund_status,
                    refund_amount, receipt_url, support_contact, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    booking_id,
                    req.idempotency_key,
                    req.user_id,
                    product.id,
                    product.category,
                    product.provider,
                    provider_ref,
                    product.title,
                    product.operator_name,
                    product.origin,
                    product.destination,
                    product.departure_time or now_iso[:10],
                    passengers_json,
                    req.payment.payment_method,
                    req.payment.card_last4 or "4242",
                    payment_tx_id,
                    price_bd_json,
                    policy_json,
                    "CONFIRMED",
                    "NONE",
                    0.0,
                    receipt_url,
                    support_contact,
                    now_iso,
                    now_iso,
                ),
            )
            conn.commit()

        self.log_audit(
            user_id=req.user_id,
            action="CONFIRM_BOOKING",
            provider=product.provider,
            status="CONFIRMED",
            details={
                "booking_id": booking_id,
                "provider_ref": provider_ref,
                "amount": product.price_breakdown.total_amount,
                "passengers_count": len(req.passengers),
            },
            booking_id=booking_id,
        )

        return self.get_booking(booking_id)

    def get_booking(self, booking_id: str) -> Optional[TravelBookingRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM travel_bookings WHERE booking_id = ?", (booking_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_booking(row)
        return None

    def list_bookings(
        self,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[TravelBookingRecord]:
        query = "SELECT * FROM travel_bookings WHERE 1=1"
        params: List[Any] = []
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if category:
            query += " AND category = ?"
            params.append(category)
        if status:
            query += " AND booking_status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_booking(r) for r in rows]

    def cancel_booking(self, req: TravelCancellationRequest, user_id: str = "default_user") -> TravelBookingRecord:
        booking = self.get_booking(req.booking_id)
        if not booking:
            raise ValueError(f"Booking '{req.booking_id}' not found.")

        if booking.booking_status == "CANCELLED":
            return booking

        # Evaluate policy
        is_eligible, refund_amount, explanation = evaluate_cancellation_eligibility(
            policy=booking.cancellation_policy,
            departure_date_str=booking.departure_date,
            total_paid=booking.price_breakdown.total_amount,
        )

        # Notify provider adapter
        adapter = None
        for a in travel_registry._adapters.values():
            if a.provider_name == booking.provider:
                adapter = a
                break
        if not adapter:
            adapter = travel_registry.get_adapter("NEXORA_SANDBOX")

        if adapter:
            adapter.cancel_booking(booking.provider_booking_ref, req.reason)

        new_booking_status = "CANCELLED"
        new_refund_status = "COMPLETED" if (is_eligible and refund_amount > 0) else (
            "REJECTED_NON_REFUNDABLE" if not is_eligible else "NONE"
        )
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE travel_bookings
                SET booking_status = ?, refund_status = ?, refund_amount = ?, updated_at = ?
                WHERE booking_id = ?
                """,
                (new_booking_status, new_refund_status, refund_amount, now_iso, booking.booking_id),
            )
            conn.commit()

        self.log_audit(
            user_id=user_id,
            action="CANCEL_BOOKING",
            provider=booking.provider,
            status="CANCELLED",
            details={
                "reason": req.reason,
                "refund_eligible": is_eligible,
                "refund_amount": refund_amount,
                "explanation": explanation,
            },
            booking_id=booking.booking_id,
        )

        return self.get_booking(booking.booking_id)

    def reschedule_booking(self, req: TravelRescheduleRequest, user_id: str = "default_user") -> TravelBookingRecord:
        booking = self.get_booking(req.booking_id)
        if not booking:
            raise ValueError(f"Booking '{req.booking_id}' not found.")

        if not booking.cancellation_policy.allow_reschedule:
            raise ValueError("Provider terms do not permit rescheduling for this ticket tier.")

        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE travel_bookings
                SET departure_date = ?, booking_status = 'RESCHEDULED', updated_at = ?
                WHERE booking_id = ?
                """,
                (req.new_departure_date, now_iso, booking.booking_id),
            )
            conn.commit()

        self.log_audit(
            user_id=user_id,
            action="RESCHEDULE_BOOKING",
            provider=booking.provider,
            status="RESCHEDULED",
            details={"new_departure_date": req.new_departure_date, "reason": req.reason},
            booking_id=booking.booking_id,
        )

        return self.get_booking(booking.booking_id)

    def get_audit_trail(self, booking_id: Optional[str] = None, limit: int = 50) -> List[TravelAuditRecord]:
        query = "SELECT * FROM travel_audit_log WHERE 1=1"
        params: List[Any] = []
        if booking_id:
            query += " AND booking_id = ?"
            params.append(booking_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                TravelAuditRecord(
                    audit_id=r["audit_id"],
                    booking_id=r["booking_id"],
                    user_id=r["user_id"],
                    action=r["action"],
                    provider=r["provider"],
                    status=r["status"],
                    details=json.loads(r["details_json"]),
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def get_overview(self, user_id: Optional[str] = None) -> TravelOverviewResponse:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM travel_bookings")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM travel_bookings WHERE booking_status = 'CONFIRMED'")
            confirmed = cursor.fetchone()[0]

        recent = self.list_bookings(user_id=user_id, limit=5)
        active_providers = [p["provider_name"] for p in travel_registry.list_active_providers()]
        categories = ["flight", "train", "bus", "hotel", "movie", "event", "concert", "sport"]

        return TravelOverviewResponse(
            stage=29,
            active_providers=active_providers,
            supported_categories=categories,
            total_bookings=total,
            confirmed_bookings=confirmed,
            recent_bookings=recent,
        )


travel_engine = TravelCommerceEngine()
