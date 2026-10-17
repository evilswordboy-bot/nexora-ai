"""
NEXORA AI — Stage 29: Universal Travel & Ticket Booking
Pricing and Cancellation Policy Engine
"""

from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from app.models.schemas import TravelPriceBreakdown, TravelCancellationPolicy


def calculate_normalized_pricing(
    base_price: float,
    passengers_count: int = 1,
    tax_rate: float = 0.12,
    service_fee: float = 8.50,
    discount: float = 0.0,
    currency: str = "USD",
) -> TravelPriceBreakdown:
    """
    Computes a transparent, itemized price breakdown.
    Never conceals hidden fees or inflates checkout totals.
    """
    total_base = round(base_price * max(1, passengers_count), 2)
    taxes = round(total_base * tax_rate, 2)
    fees = round(service_fee * max(1, passengers_count), 2)
    disc = round(min(discount, total_base), 2)
    total = round(total_base + taxes + fees - disc, 2)

    return TravelPriceBreakdown(
        base_amount=total_base,
        taxes_amount=taxes,
        fees_amount=fees,
        discount_amount=disc,
        total_amount=total,
        currency=currency,
    )


def evaluate_cancellation_eligibility(
    policy: TravelCancellationPolicy,
    departure_date_str: str,
    total_paid: float,
) -> Tuple[bool, float, str]:
    """
    Evaluates whether a cancellation is eligible for a refund according to policy rules.
    Returns (is_eligible, refund_amount, explanation).
    """
    if not policy.is_refundable:
        return False, 0.0, "This ticket is strictly non-refundable according to provider terms."

    try:
        # Check departure date
        if "T" in departure_date_str:
            dep_dt = datetime.fromisoformat(departure_date_str.replace("Z", "+00:00"))
        else:
            dep_dt = datetime.fromisoformat(f"{departure_date_str}T09:00:00+00:00")
        
        now = datetime.now(timezone.utc)
        diff_hours = (dep_dt - now).total_seconds() / 3600.0

        deadline = policy.deadline_hours_before or 24
        if diff_hours < deadline:
            return (
                False,
                0.0,
                f"Cancellation window closed. Policy requires cancellation at least {deadline} hours before departure. Current remaining hours: {round(max(0, diff_hours), 1)}.",
            )

        fee = min(policy.cancellation_fee, total_paid)
        refund_amount = round(max(0.0, total_paid - fee), 2)
        return True, refund_amount, f"Eligible for refund of {refund_amount} (cancellation fee: {fee})."
    except Exception as e:
        # Fallback to standard policy evaluation
        fee = min(policy.cancellation_fee, total_paid)
        refund_amount = round(max(0.0, total_paid - fee), 2)
        return True, refund_amount, f"Standard cancellation fee of {fee} applied. Refund: {refund_amount}."
