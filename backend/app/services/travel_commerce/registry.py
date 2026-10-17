"""
NEXORA AI — Stage 29: Universal Travel & Ticket Booking
Provider Adapter Registry
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from app.models.schemas import TravelProductItem, TravelSearchQuery
from app.services.travel_commerce.adapters import (
    BaseTravelAdapter,
    AmadeusFlightAdapter,
    IRCTCRailAdapter,
    RedBusAdapter,
    BookingHotelAdapter,
    BookMyShowCinemaAdapter,
    TicketmasterEventAdapter,
    TravelSandboxProvider,
)


class TravelAdapterRegistry:
    def __init__(self):
        self._adapters: Dict[str, BaseTravelAdapter] = {}
        self._register_default_adapters()

    def _register_default_adapters(self):
        self.register(AmadeusFlightAdapter())
        self.register(IRCTCRailAdapter())
        self.register(RedBusAdapter())
        self.register(BookingHotelAdapter())
        self.register(BookMyShowCinemaAdapter())
        self.register(TicketmasterEventAdapter())
        self.register(TravelSandboxProvider())

    def register(self, adapter: BaseTravelAdapter):
        self._adapters[adapter.provider_code] = adapter

    def get_adapter(self, provider_code: str) -> Optional[BaseTravelAdapter]:
        return self._adapters.get(provider_code)

    def get_adapters_for_category(self, category: str) -> List[BaseTravelAdapter]:
        matching = []
        for adapter in self._adapters.values():
            if category in adapter.supported_categories:
                matching.append(adapter)
        return matching

    def list_active_providers(self) -> List[Dict[str, Any]]:
        return [
            {
                "provider_code": a.provider_code,
                "provider_name": a.provider_name,
                "supported_categories": a.supported_categories,
                "status": "OPERATIONAL",
            }
            for a in self._adapters.values()
        ]

    def search_all(self, query: TravelSearchQuery) -> List[TravelProductItem]:
        results: List[TravelProductItem] = []
        adapters = self.get_adapters_for_category(query.category)
        
        # If user explicitly specified a provider
        if query.provider:
            adapters = [a for a in adapters if query.provider.lower() in a.provider_name.lower() or query.provider.lower() in a.provider_code.lower()]

        for adapter in adapters:
            try:
                found = adapter.search(query)
                results.extend(found)
            except Exception:
                continue

        # Sort results by price ascending
        results.sort(key=lambda x: x.price_breakdown.total_amount)
        return results

    def find_product_by_id(self, product_id: str) -> Optional[TravelProductItem]:
        # Search across adapters
        for adapter in self._adapters.values():
            try:
                prod = adapter.get_by_id(product_id)
                if prod:
                    return prod
            except Exception:
                continue
        return None


travel_registry = TravelAdapterRegistry()
