"""
NEXORA AI — Stage 29: Universal Travel & Ticket Booking
Provider Adapters (Amadeus, IRCTC, RedBus, Booking.com, BookMyShow, Ticketmaster, and TravelSandbox)
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import uuid

from app.models.schemas import (
    TravelProductItem,
    TravelSearchQuery,
    TravelPriceBreakdown,
    TravelCancellationPolicy,
    TravelBookingRequest,
)
from app.services.travel_commerce.pricing_policy import calculate_normalized_pricing


class BaseTravelAdapter(ABC):
    """Abstract base class for all travel and ticketing provider adapters."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def provider_code(self) -> str:
        pass

    @property
    @abstractmethod
    def supported_categories(self) -> List[str]:
        pass

    @abstractmethod
    def search(self, query: TravelSearchQuery) -> List[TravelProductItem]:
        """Search products for the given query."""
        pass

    @abstractmethod
    def get_by_id(self, product_id: str) -> Optional[TravelProductItem]:
        """Fetch real-time details for a single product."""
        pass

    @abstractmethod
    def confirm_booking(
        self, booking_req: TravelBookingRequest, product: TravelProductItem
    ) -> Dict[str, Any]:
        """Submit booking to the external provider and return provider confirmation."""
        pass

    @abstractmethod
    def cancel_booking(self, provider_booking_ref: str, reason: str) -> Dict[str, Any]:
        """Cancel with provider."""
        pass

    @abstractmethod
    def reschedule_booking(
        self, provider_booking_ref: str, new_date: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reschedule with provider."""
        pass


class AmadeusFlightAdapter(BaseTravelAdapter):
    provider_name = "Amadeus Global Distribution"
    provider_code = "AMADEUS"
    supported_categories = ["flight"]

    def _sample_catalog(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "FL-AMD-101",
                "origin": "SFO",
                "destination": "JFK",
                "title": "United Airlines UA-824 Non-Stop Express",
                "subtitle": "Boeing 787-9 Dreamliner • Terminal 3",
                "operator": "United Airlines",
                "dep": "08:30 AM",
                "arr": "05:00 PM",
                "duration": "5h 30m",
                "base_price": 340.0,
                "cabin": "economy",
                "seats": 14,
                "amenities": ["High-speed Wi-Fi", "In-seat Power", "Complimentary Meal", "Live TV"],
                "accessibility": ["Wheelchair assistance", "Priority boarding", "Service animal friendly"],
                "tags": ["Non-Stop", "Eco-Certified", "Direct"],
            },
            {
                "id": "FL-AMD-102",
                "origin": "LHR",
                "destination": "JFK",
                "title": "British Airways BA-177 Club World Business",
                "subtitle": "Airbus A350-1000 • Terminal 5",
                "operator": "British Airways",
                "dep": "11:15 AM",
                "arr": "02:45 PM",
                "duration": "7h 30m",
                "base_price": 1450.0,
                "cabin": "business",
                "seats": 6,
                "amenities": ["Lie-flat bed", "Champagne bar", "Lounge access", "Priority baggage", "Gourmet dining"],
                "accessibility": ["Wheelchair assistance", "Aisle chair available", "Braille safety guides"],
                "tags": ["Lie-Flat Bed", "Lounge Access", "Fast-Track"],
            },
            {
                "id": "FL-AMD-103",
                "origin": "DXB",
                "destination": "SIN",
                "title": "Emirates EK-404 A380 Superjumbo",
                "subtitle": "Airbus A380-800 • Terminal 3",
                "operator": "Emirates Airlines",
                "dep": "03:10 AM",
                "arr": "02:25 PM",
                "duration": "7h 15m",
                "base_price": 580.0,
                "cabin": "economy",
                "seats": 22,
                "amenities": ["ice Inflight Entertainment", "Free Wi-Fi", "Multi-course meal"],
                "accessibility": ["Wheelchair hoist", "Medical oxygen ready"],
                "tags": ["A380 Experience", "Award Winning"],
            },
            {
                "id": "FL-AMD-104",
                "origin": "CDG",
                "destination": "HND",
                "title": "Air France AF-272 Premiere First Class",
                "subtitle": "Boeing 777-300ER • Terminal 2E",
                "operator": "Air France",
                "dep": "01:20 PM",
                "arr": "10:55 AM (+1)",
                "duration": "13h 35m",
                "base_price": 3200.0,
                "cabin": "first",
                "seats": 2,
                "amenities": ["Private Suite", "Caviar Service", "Chauffeur Transfer", "Clarins Spa"],
                "accessibility": ["Dedicated escort", "Elevated assistance"],
                "tags": ["La Premiere", "Ultra Luxury"],
            },
        ]

    def search(self, query: TravelSearchQuery) -> List[TravelProductItem]:
        now_iso = datetime.now(timezone.utc).isoformat()
        results: List[TravelProductItem] = []
        for item in self._sample_catalog():
            if query.origin and query.origin.upper() not in item["origin"].upper():
                continue
            if query.destination and query.destination.upper() not in item["destination"].upper():
                continue
            if query.cabin_class and query.cabin_class.lower() != item["cabin"].lower():
                continue
            if query.min_price and item["base_price"] < query.min_price:
                continue
            if query.max_price and item["base_price"] > query.max_price:
                continue
            if query.accessible_required and not item["accessibility"]:
                continue

            pricing = calculate_normalized_pricing(
                base_price=item["base_price"],
                passengers_count=query.passengers_count,
                tax_rate=0.14,
                service_fee=12.00,
                currency="USD",
            )

            policy = TravelCancellationPolicy(
                is_refundable=True,
                deadline_hours_before=24,
                cancellation_fee=50.0,
                description="Refundable with $50 carrier cancellation penalty up to 24 hours prior to departure.",
                allow_reschedule=True,
                reschedule_fee=25.0,
            )

            results.append(
                TravelProductItem(
                    id=item["id"],
                    category="flight",
                    provider=self.provider_name,
                    provider_code=self.provider_code,
                    title=item["title"],
                    subtitle=item["subtitle"],
                    origin=item["origin"],
                    destination=item["destination"],
                    departure_time=item["dep"],
                    arrival_time=item["arr"],
                    duration=item["duration"],
                    operator_name=item["operator"],
                    rating=4.8,
                    amenities=item["amenities"],
                    accessibility=item["accessibility"],
                    cabin_or_seat_class=item["cabin"].title(),
                    available_seats=item["seats"],
                    price_breakdown=pricing,
                    cancellation_policy=policy,
                    retrieved_at=now_iso,
                    tags=item["tags"],
                )
            )
        return results

    def get_by_id(self, product_id: str) -> Optional[TravelProductItem]:
        for item in self._sample_catalog():
            if item["id"] == product_id:
                pricing = calculate_normalized_pricing(item["base_price"], 1)
                policy = TravelCancellationPolicy(is_refundable=True, deadline_hours_before=24, cancellation_fee=50.0)
                return TravelProductItem(
                    id=item["id"],
                    category="flight",
                    provider=self.provider_name,
                    provider_code=self.provider_code,
                    title=item["title"],
                    subtitle=item["subtitle"],
                    origin=item["origin"],
                    destination=item["destination"],
                    departure_time=item["dep"],
                    arrival_time=item["arr"],
                    duration=item["duration"],
                    operator_name=item["operator"],
                    amenities=item["amenities"],
                    accessibility=item["accessibility"],
                    cabin_or_seat_class=item["cabin"].title(),
                    available_seats=item["seats"],
                    price_breakdown=pricing,
                    cancellation_policy=policy,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    tags=item["tags"],
                )
        return None

    def confirm_booking(self, booking_req: TravelBookingRequest, product: TravelProductItem) -> Dict[str, Any]:
        pnr = f"AMD-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "CONFIRMED",
            "provider_ref": pnr,
            "eticket_number": f"016-{uuid.uuid4().int % 10000000000:010d}",
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "operator_acknowledgement": "Amadeus e-Ticketing System: Ticket Issued",
        }

    def cancel_booking(self, provider_booking_ref: str, reason: str) -> Dict[str, Any]:
        return {
            "status": "CANCELLED",
            "provider_ref": provider_booking_ref,
            "refund_acknowledged": True,
            "refund_tracking_id": f"REF-AMD-{uuid.uuid4().hex[:6].upper()}",
            "message": "Amadeus flight segment successfully canceled. Refund credit triggered.",
        }

    def reschedule_booking(self, provider_booking_ref: str, new_date: str, reason: Optional[str] = None) -> Dict[str, Any]:
        return {
            "status": "RESCHEDULED",
            "provider_ref": provider_booking_ref,
            "new_departure_date": new_date,
            "message": f"Flight segment changed to {new_date}. Updated e-ticket re-issued.",
        }


class IRCTCRailAdapter(BaseTravelAdapter):
    provider_name = "IRCTC & RailEurope Global Rail"
    provider_code = "RAIL_GLOBAL"
    supported_categories = ["train"]

    def _sample_catalog(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "TRN-EUR-201",
                "origin": "Paris Gare du Nord",
                "destination": "London St Pancras",
                "title": "Eurostar E320 High-Speed Rail",
                "subtitle": "Standard Premier Class • Platform 4",
                "operator": "Eurostar International",
                "dep": "07:12 AM",
                "arr": "08:30 AM",
                "duration": "2h 18m",
                "base_price": 185.0,
                "cabin": "premium_economy",
                "seats": 28,
                "amenities": ["Free Wi-Fi", "Light meal & wine at seat", "Spacious seating", "UK/EU power sockets"],
                "accessibility": ["Step-free boarding", "Dedicated wheelchair space", "Accessible WC"],
                "tags": ["High-Speed", "Channel Tunnel", "City-to-City"],
            },
            {
                "id": "TRN-SHK-202",
                "origin": "Tokyo",
                "destination": "Kyoto",
                "title": "Nozomi 215 Shinkansen Bullet Train",
                "subtitle": "Green Car (First Class) • Tokaido Line",
                "operator": "JR Central",
                "dep": "09:00 AM",
                "arr": "11:15 AM",
                "duration": "2h 15m",
                "base_price": 140.0,
                "cabin": "first",
                "seats": 19,
                "amenities": ["Ultra Quiet Cabin", "Footrest", "Seat heaters", "Hot towel service"],
                "accessibility": ["Universal design cars", "Braille signage", "Wheelchair securement"],
                "tags": ["285 km/h", "Punctual", "Scenic Mt Fuji"],
            },
            {
                "id": "TRN-VND-203",
                "origin": "New Delhi",
                "destination": "Varanasi",
                "title": "Vande Bharat Express 22436",
                "subtitle": "Executive AC Chair Car • Train 22436",
                "operator": "Indian Railways (IRCTC)",
                "dep": "06:00 AM",
                "arr": "02:00 PM",
                "duration": "8h 00m",
                "base_price": 45.0,
                "cabin": "ac_tier_1",
                "seats": 35,
                "amenities": ["Rotating 180° Seats", "CCTV Security", "Modular Bio-Toilets", "Hot Gourmet Breakfast"],
                "accessibility": ["Automatic sliding doors", "Divyangjan accessible restroom"],
                "tags": ["Semi-High Speed", "Modernized Fleet"],
            },
        ]

    def search(self, query: TravelSearchQuery) -> List[TravelProductItem]:
        now_iso = datetime.now(timezone.utc).isoformat()
        results: List[TravelProductItem] = []
        for item in self._sample_catalog():
            if query.origin and query.origin.lower() not in item["origin"].lower():
                continue
            if query.destination and query.destination.lower() not in item["destination"].lower():
                continue
            if query.min_price and item["base_price"] < query.min_price:
                continue
            if query.max_price and item["base_price"] > query.max_price:
                continue

            pricing = calculate_normalized_pricing(
                base_price=item["base_price"],
                passengers_count=query.passengers_count,
                tax_rate=0.08,
                service_fee=6.00,
                currency="USD",
            )

            policy = TravelCancellationPolicy(
                is_refundable=True,
                deadline_hours_before=12,
                cancellation_fee=15.0,
                description="Cancellations permitted up to 12 hours before rail departure with $15 clerical fee.",
                allow_reschedule=True,
                reschedule_fee=10.0,
            )

            results.append(
                TravelProductItem(
                    id=item["id"],
                    category="train",
                    provider=self.provider_name,
                    provider_code=self.provider_code,
                    title=item["title"],
                    subtitle=item["subtitle"],
                    origin=item["origin"],
                    destination=item["destination"],
                    departure_time=item["dep"],
                    arrival_time=item["arr"],
                    duration=item["duration"],
                    operator_name=item["operator"],
                    rating=4.9,
                    amenities=item["amenities"],
                    accessibility=item["accessibility"],
                    cabin_or_seat_class=item["cabin"].title(),
                    available_seats=item["seats"],
                    price_breakdown=pricing,
                    cancellation_policy=policy,
                    retrieved_at=now_iso,
                    tags=item["tags"],
                )
            )
        return results

    def get_by_id(self, product_id: str) -> Optional[TravelProductItem]:
        for item in self._sample_catalog():
            if item["id"] == product_id:
                pricing = calculate_normalized_pricing(item["base_price"], 1)
                policy = TravelCancellationPolicy(is_refundable=True, deadline_hours_before=12, cancellation_fee=15.0)
                return TravelProductItem(
                    id=item["id"],
                    category="train",
                    provider=self.provider_name,
                    provider_code=self.provider_code,
                    title=item["title"],
                    subtitle=item["subtitle"],
                    origin=item["origin"],
                    destination=item["destination"],
                    departure_time=item["dep"],
                    arrival_time=item["arr"],
                    duration=item["duration"],
                    operator_name=item["operator"],
                    amenities=item["amenities"],
                    accessibility=item["accessibility"],
                    cabin_or_seat_class=item["cabin"].title(),
                    available_seats=item["seats"],
                    price_breakdown=pricing,
                    cancellation_policy=policy,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    tags=item["tags"],
                )
        return None

    def confirm_booking(self, booking_req: TravelBookingRequest, product: TravelProductItem) -> Dict[str, Any]:
        pnr = f"RAIL-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "CONFIRMED",
            "provider_ref": pnr,
            "eticket_number": f"RL-{uuid.uuid4().int % 100000000:08d}",
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "operator_acknowledgement": "Global Rail Reservation: Berths Reserved",
        }

    def cancel_booking(self, provider_booking_ref: str, reason: str) -> Dict[str, Any]:
        return {
            "status": "CANCELLED",
            "provider_ref": provider_booking_ref,
            "refund_acknowledged": True,
            "refund_tracking_id": f"REF-RL-{uuid.uuid4().hex[:6].upper()}",
            "message": "Rail ticket cancelled. Seat released to reservation chart.",
        }

    def reschedule_booking(self, provider_booking_ref: str, new_date: str, reason: Optional[str] = None) -> Dict[str, Any]:
        return {
            "status": "RESCHEDULED",
            "provider_ref": provider_booking_ref,
            "new_departure_date": new_date,
            "message": f"Rail berth reservation successfully moved to {new_date}.",
        }


class RedBusAdapter(BaseTravelAdapter):
    provider_name = "RedBus & FlixBus Intercity Network"
    provider_code = "BUS_EXPRESS"
    supported_categories = ["bus"]

    def _sample_catalog(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "BUS-FLX-301",
                "origin": "Berlin Central Station",
                "destination": "Prague Florenc",
                "title": "FlixBus Green Line Express 142",
                "subtitle": "Panorama Double Decker • Bay 9",
                "operator": "FlixBus Europe",
                "dep": "09:30 AM",
                "arr": "02:15 PM",
                "duration": "4h 45m",
                "base_price": 38.0,
                "cabin": "standard",
                "seats": 32,
                "amenities": ["Wi-Fi LTE", "USB Chargers", "Climate Control", "Restroom onboard"],
                "accessibility": ["Hydraulic wheelchair lift", "Low-floor entry"],
                "tags": ["Carbon-Neutral", "Scenic Route"],
            },
            {
                "id": "BUS-VLV-302",
                "origin": "Bengaluru",
                "destination": "Goa",
                "title": "IntrCity SmartBus Multi-Axle Volvo Sleeper",
                "subtitle": "AC Sleeper 2+1 • Lounge Boarding",
                "operator": "IntrCity SmartBus",
                "dep": "09:00 PM",
                "arr": "07:30 AM (+1)",
                "duration": "10h 30m",
                "base_price": 32.0,
                "cabin": "sleeper",
                "seats": 18,
                "amenities": ["Private Berths with Curtains", "Live GPS Tracking", "Fresh Linen", "Mineral Water"],
                "accessibility": ["Ground crew boarding assistance"],
                "tags": ["Overnight Sleeper", "Verified Safe"],
            },
        ]

    def search(self, query: TravelSearchQuery) -> List[TravelProductItem]:
        now_iso = datetime.now(timezone.utc).isoformat()
        results: List[TravelProductItem] = []
        for item in self._sample_catalog():
            if query.origin and query.origin.lower() not in item["origin"].lower():
                continue
            if query.destination and query.destination.lower() not in item["destination"].lower():
                continue

            pricing = calculate_normalized_pricing(
                base_price=item["base_price"],
                passengers_count=query.passengers_count,
                tax_rate=0.05,
                service_fee=3.50,
                currency="USD",
            )

            policy = TravelCancellationPolicy(
                is_refundable=True,
                deadline_hours_before=6,
                cancellation_fee=8.0,
                description="Cancel up to 6 hours before departure with $8 fee.",
            )

            results.append(
                TravelProductItem(
                    id=item["id"],
                    category="bus",
                    provider=self.provider_name,
                    provider_code=self.provider_code,
                    title=item["title"],
                    subtitle=item["subtitle"],
                    origin=item["origin"],
                    destination=item["destination"],
                    departure_time=item["dep"],
                    arrival_time=item["arr"],
                    duration=item["duration"],
                    operator_name=item["operator"],
                    rating=4.7,
                    amenities=item["amenities"],
                    accessibility=item["accessibility"],
                    cabin_or_seat_class=item["cabin"].title(),
                    available_seats=item["seats"],
                    price_breakdown=pricing,
                    cancellation_policy=policy,
                    retrieved_at=now_iso,
                    tags=item["tags"],
                )
            )
        return results

    def get_by_id(self, product_id: str) -> Optional[TravelProductItem]:
        for item in self._sample_catalog():
            if item["id"] == product_id:
                pricing = calculate_normalized_pricing(item["base_price"], 1)
                policy = TravelCancellationPolicy(is_refundable=True, deadline_hours_before=6, cancellation_fee=8.0)
                return TravelProductItem(
                    id=item["id"],
                    category="bus",
                    provider=self.provider_name,
                    provider_code=self.provider_code,
                    title=item["title"],
                    subtitle=item["subtitle"],
                    origin=item["origin"],
                    destination=item["destination"],
                    departure_time=item["dep"],
                    arrival_time=item["arr"],
                    duration=item["duration"],
                    operator_name=item["operator"],
                    amenities=item["amenities"],
                    accessibility=item["accessibility"],
                    cabin_or_seat_class=item["cabin"].title(),
                    available_seats=item["seats"],
                    price_breakdown=pricing,
                    cancellation_policy=policy,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    tags=item["tags"],
                )
        return None

    def confirm_booking(self, booking_req: TravelBookingRequest, product: TravelProductItem) -> Dict[str, Any]:
        pnr = f"BUS-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "CONFIRMED",
            "provider_ref": pnr,
            "eticket_number": f"BUS-TKT-{uuid.uuid4().hex[:8].upper()}",
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "operator_acknowledgement": "Intercity Bus Dispatch: Seat Reserved",
        }

    def cancel_booking(self, provider_booking_ref: str, reason: str) -> Dict[str, Any]:
        return {
            "status": "CANCELLED",
            "provider_ref": provider_booking_ref,
            "refund_acknowledged": True,
            "refund_tracking_id": f"REF-BUS-{uuid.uuid4().hex[:6].upper()}",
            "message": "Bus seat booking released. Bus operator notified.",
        }

    def reschedule_booking(self, provider_booking_ref: str, new_date: str, reason: Optional[str] = None) -> Dict[str, Any]:
        return {
            "status": "RESCHEDULED",
            "provider_ref": provider_booking_ref,
            "new_departure_date": new_date,
            "message": f"Bus ticket shifted to {new_date}.",
        }


class BookingHotelAdapter(BaseTravelAdapter):
    provider_name = "Booking.com Worldwide Stays"
    provider_code = "BOOKING_HOTEL"
    supported_categories = ["hotel"]

    def _sample_catalog(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "HTL-NYC-401",
                "origin": "Times Square Manhattan",
                "destination": "New York City",
                "title": "The Knickerbocker Hotel NYC",
                "subtitle": "Deluxe King Skyline View • 42nd St & Broadway",
                "operator": "The Knickerbocker",
                "dep": "03:00 PM Check-In",
                "arr": "12:00 PM Check-Out",
                "duration": "1 Night Stay",
                "base_price": 280.0,
                "cabin": "deluxe",
                "seats": 8,
                "amenities": ["Rooftop St. Cloud Terrace", "High-speed Wi-Fi", "Espresso Bar", "Rain Shower", "24/7 Gym"],
                "accessibility": ["ADA compliant rooms", "Roll-in shower", "Elevator auditory guidance"],
                "tags": ["Times Square", "5-Star Luxury", "Skyline View"],
            },
            {
                "id": "HTL-TYO-402",
                "origin": "Shinjuku District",
                "destination": "Tokyo",
                "title": "Park Hyatt Tokyo",
                "subtitle": "Park View King • Floors 41-52",
                "operator": "Hyatt Hotels",
                "dep": "03:00 PM Check-In",
                "arr": "12:00 PM Check-Out",
                "duration": "1 Night Stay",
                "base_price": 420.0,
                "cabin": "deluxe",
                "seats": 5,
                "amenities": ["New York Grill Access", "Club on the Park Spa", "Indoor Pool", "Deep Soaking Tub"],
                "accessibility": ["Full barrier-free access", "Braille room keys"],
                "tags": ["Iconic Film Location", "Mt Fuji View", "Michelin Dining"],
            },
        ]

    def search(self, query: TravelSearchQuery) -> List[TravelProductItem]:
        now_iso = datetime.now(timezone.utc).isoformat()
        results: List[TravelProductItem] = []
        for item in self._sample_catalog():
            if query.destination and query.destination.lower() not in item["destination"].lower() and query.destination.lower() not in item["title"].lower():
                continue

            pricing = calculate_normalized_pricing(
                base_price=item["base_price"],
                passengers_count=query.passengers_count,
                tax_rate=0.14,
                service_fee=15.00,
                currency="USD",
            )

            policy = TravelCancellationPolicy(
                is_refundable=True,
                deadline_hours_before=48,
                cancellation_fee=0.0,
                description="100% Free cancellation up to 48 hours before check-in.",
            )

            results.append(
                TravelProductItem(
                    id=item["id"],
                    category="hotel",
                    provider=self.provider_name,
                    provider_code=self.provider_code,
                    title=item["title"],
                    subtitle=item["subtitle"],
                    origin=item["origin"],
                    destination=item["destination"],
                    departure_time=item["dep"],
                    arrival_time=item["arr"],
                    duration=item["duration"],
                    operator_name=item["operator"],
                    rating=4.9,
                    amenities=item["amenities"],
                    accessibility=item["accessibility"],
                    cabin_or_seat_class=item["cabin"].title(),
                    available_seats=item["seats"],
                    price_breakdown=pricing,
                    cancellation_policy=policy,
                    retrieved_at=now_iso,
                    tags=item["tags"],
                )
            )
        return results

    def get_by_id(self, product_id: str) -> Optional[TravelProductItem]:
        for item in self._sample_catalog():
            if item["id"] == product_id:
                pricing = calculate_normalized_pricing(item["base_price"], 1)
                policy = TravelCancellationPolicy(is_refundable=True, deadline_hours_before=48, cancellation_fee=0.0)
                return TravelProductItem(
                    id=item["id"],
                    category="hotel",
                    provider=self.provider_name,
                    provider_code=self.provider_code,
                    title=item["title"],
                    subtitle=item["subtitle"],
                    origin=item["origin"],
                    destination=item["destination"],
                    departure_time=item["dep"],
                    arrival_time=item["arr"],
                    duration=item["duration"],
                    operator_name=item["operator"],
                    amenities=item["amenities"],
                    accessibility=item["accessibility"],
                    cabin_or_seat_class=item["cabin"].title(),
                    available_seats=item["seats"],
                    price_breakdown=pricing,
                    cancellation_policy=policy,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    tags=item["tags"],
                )
        return None

    def confirm_booking(self, booking_req: TravelBookingRequest, product: TravelProductItem) -> Dict[str, Any]:
        pnr = f"HTL-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "CONFIRMED",
            "provider_ref": pnr,
            "eticket_number": f"VOUCHER-{uuid.uuid4().hex[:8].upper()}",
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "operator_acknowledgement": "Hotel Front Desk: Reservation Guaranteed",
        }

    def cancel_booking(self, provider_booking_ref: str, reason: str) -> Dict[str, Any]:
        return {
            "status": "CANCELLED",
            "provider_ref": provider_booking_ref,
            "refund_acknowledged": True,
            "refund_tracking_id": f"REF-HTL-{uuid.uuid4().hex[:6].upper()}",
            "message": "Hotel room reservation canceled. Full refund processed.",
        }

    def reschedule_booking(self, provider_booking_ref: str, new_date: str, reason: Optional[str] = None) -> Dict[str, Any]:
        return {
            "status": "RESCHEDULED",
            "provider_ref": provider_booking_ref,
            "new_departure_date": new_date,
            "message": f"Hotel check-in date modified to {new_date}.",
        }


class BookMyShowCinemaAdapter(BaseTravelAdapter):
    provider_name = "BookMyShow & AMC Entertainment"
    provider_code = "CINEMA_NETWORK"
    supported_categories = ["movie"]

    def _sample_catalog(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "MOV-DNE-501",
                "origin": "Screen 1 - Dual Laser IMAX",
                "destination": "San Francisco Metreon",
                "title": "Dune: Part Two (IMAX 70mm Special Presentation)",
                "subtitle": "12-Channel Immersive Audio • Recliner Seating",
                "operator": "AMC Metreon 16 & IMAX",
                "dep": "07:30 PM",
                "arr": "10:15 PM",
                "duration": "2h 45m",
                "base_price": 26.50,
                "cabin": "vip",
                "seats": 42,
                "amenities": ["Motorized Recliners", "Laser IMAX 1.43:1", "At-seat F&B ordering"],
                "accessibility": ["Open Captioning available", "Audio descriptive headsets", "Companion wheelchair seats"],
                "tags": ["IMAX 70mm", "Director's Vision", "Dolby Atmos"],
            },
            {
                "id": "MOV-BLD-502",
                "origin": "Dolby Cinema Auditorium",
                "destination": "Los Angeles Dolby Theatre",
                "title": "Blade Runner 2049 (Anniversary Master in Dolby)",
                "subtitle": "Dolby Vision HDR + Dolby Atmos Transducers",
                "operator": "Dolby Cinema LA",
                "dep": "08:15 PM",
                "arr": "11:00 PM",
                "duration": "2h 45m",
                "base_price": 24.00,
                "cabin": "standard",
                "seats": 30,
                "amenities": ["Haptic Subwoofer Seats", "True Black Contrast", "Gourmet Concessions"],
                "accessibility": ["Closed caption glasses", "Wheelchair accessible row G"],
                "tags": ["Dolby Vision", "4K Remaster"],
            },
        ]

    def search(self, query: TravelSearchQuery) -> List[TravelProductItem]:
        now_iso = datetime.now(timezone.utc).isoformat()
        results: List[TravelProductItem] = []
        for item in self._sample_catalog():
            if query.destination and query.destination.lower() not in item["destination"].lower() and query.destination.lower() not in item["title"].lower():
                continue

            pricing = calculate_normalized_pricing(
                base_price=item["base_price"],
                passengers_count=query.passengers_count,
                tax_rate=0.09,
                service_fee=2.25,
                currency="USD",
            )

            policy = TravelCancellationPolicy(
                is_refundable=True,
                deadline_hours_before=2,
                cancellation_fee=2.50,
                description="Movie tickets cancelable up to 2 hours prior to showtime ($2.50 fee).",
            )

            results.append(
                TravelProductItem(
                    id=item["id"],
                    category="movie",
                    provider=self.provider_name,
                    provider_code=self.provider_code,
                    title=item["title"],
                    subtitle=item["subtitle"],
                    origin=item["origin"],
                    destination=item["destination"],
                    departure_time=item["dep"],
                    arrival_time=item["arr"],
                    duration=item["duration"],
                    operator_name=item["operator"],
                    rating=4.9,
                    amenities=item["amenities"],
                    accessibility=item["accessibility"],
                    cabin_or_seat_class=item["cabin"].title(),
                    available_seats=item["seats"],
                    price_breakdown=pricing,
                    cancellation_policy=policy,
                    retrieved_at=now_iso,
                    tags=item["tags"],
                )
            )
        return results

    def get_by_id(self, product_id: str) -> Optional[TravelProductItem]:
        for item in self._sample_catalog():
            if item["id"] == product_id:
                pricing = calculate_normalized_pricing(item["base_price"], 1)
                policy = TravelCancellationPolicy(is_refundable=True, deadline_hours_before=2, cancellation_fee=2.50)
                return TravelProductItem(
                    id=item["id"],
                    category="movie",
                    provider=self.provider_name,
                    provider_code=self.provider_code,
                    title=item["title"],
                    subtitle=item["subtitle"],
                    origin=item["origin"],
                    destination=item["destination"],
                    departure_time=item["dep"],
                    arrival_time=item["arr"],
                    duration=item["duration"],
                    operator_name=item["operator"],
                    amenities=item["amenities"],
                    accessibility=item["accessibility"],
                    cabin_or_seat_class=item["cabin"].title(),
                    available_seats=item["seats"],
                    price_breakdown=pricing,
                    cancellation_policy=policy,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    tags=item["tags"],
                )
        return None

    def confirm_booking(self, booking_req: TravelBookingRequest, product: TravelProductItem) -> Dict[str, Any]:
        pnr = f"MOV-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "CONFIRMED",
            "provider_ref": pnr,
            "eticket_number": f"QR-CIN-{uuid.uuid4().hex[:8].upper()}",
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "operator_acknowledgement": "Box Office Automated Kiosk: Barcode Generated",
        }

    def cancel_booking(self, provider_booking_ref: str, reason: str) -> Dict[str, Any]:
        return {
            "status": "CANCELLED",
            "provider_ref": provider_booking_ref,
            "refund_acknowledged": True,
            "refund_tracking_id": f"REF-CIN-{uuid.uuid4().hex[:6].upper()}",
            "message": "Cinema seats released to general auditorium inventory.",
        }

    def reschedule_booking(self, provider_booking_ref: str, new_date: str, reason: Optional[str] = None) -> Dict[str, Any]:
        return {
            "status": "RESCHEDULED",
            "provider_ref": provider_booking_ref,
            "new_departure_date": new_date,
            "message": f"Cinema showtime shifted to {new_date}.",
        }


class TicketmasterEventAdapter(BaseTravelAdapter):
    provider_name = "Ticketmaster & Live Nation"
    provider_code = "LIVE_EVENTS"
    supported_categories = ["event", "concert", "sport"]

    def _sample_catalog(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "EVT-CPY-601",
                "category": "concert",
                "origin": "Wembley Stadium",
                "destination": "London",
                "title": "Coldplay: Music of the Spheres World Tour",
                "subtitle": "Club Wembley Level 2 • Gate E",
                "operator": "Live Nation Entertainment",
                "dep": "06:00 PM Doors Open",
                "arr": "10:30 PM Finale",
                "duration": "4h 30m",
                "base_price": 175.0,
                "cabin": "vip",
                "seats": 24,
                "amenities": ["Eco-kinetic dance floor access", "Solar-powered wristbands", "Dedicated stadium lounge bar"],
                "accessibility": ["Elevated wheelchair viewing platform", "Induction loop audio", "Sensory calm room"],
                "tags": ["Stadium Tour", "Spectacular Visuals", "Eco-Friendly"],
            },
            {
                "id": "EVT-F1-602",
                "category": "sport",
                "origin": "Silverstone Circuit",
                "destination": "Silverstone, UK",
                "title": "Formula 1 British Grand Prix 2026",
                "subtitle": "Abbey Grandstand Reserved Weekend • Pit Straight View",
                "operator": "Formula One Management",
                "dep": "10:00 AM",
                "arr": "05:00 PM",
                "duration": "All Day Event",
                "base_price": 420.0,
                "cabin": "deluxe",
                "seats": 16,
                "amenities": ["Giant Screen viewing", "Pit lane walk pass", "Live timing commentary earpiece"],
                "accessibility": ["Golf cart transport shuttle", "Step-free grandstand seating"],
                "tags": ["Motorsport", "FIA Championship", "Adrenaline"],
            },
            {
                "id": "EVT-HAM-603",
                "category": "event",
                "origin": "Richard Rodgers Theatre",
                "destination": "Broadway, NYC",
                "title": "Hamilton: An American Musical",
                "subtitle": "Orchestra Center • Rows D-K",
                "operator": "Broadway Theatrical",
                "dep": "08:00 PM",
                "arr": "10:45 PM",
                "duration": "2h 45m",
                "base_price": 195.0,
                "cabin": "standard",
                "seats": 10,
                "amenities": ["Playbill Souvenir", "Historic Theatre Architecture", "Coat Check"],
                "accessibility": ["Infrared listening systems", "Wheelchair seating with companion"],
                "tags": ["Broadway Hit", "Pulitzer Prize Winner"],
            },
        ]

    def search(self, query: TravelSearchQuery) -> List[TravelProductItem]:
        now_iso = datetime.now(timezone.utc).isoformat()
        results: List[TravelProductItem] = []
        for item in self._sample_catalog():
            if query.category and query.category != item["category"]:
                continue
            if query.destination and query.destination.lower() not in item["destination"].lower() and query.destination.lower() not in item["title"].lower():
                continue

            pricing = calculate_normalized_pricing(
                base_price=item["base_price"],
                passengers_count=query.passengers_count,
                tax_rate=0.10,
                service_fee=14.00,
                currency="USD",
            )

            # High profile events often have strict non-transfer/cancellation unless protection purchased
            policy = TravelCancellationPolicy(
                is_refundable=True,
                deadline_hours_before=72,
                cancellation_fee=25.0,
                description="Live Event Ticket: Cancellable up to 72 hours before event start with $25 fee.",
                allow_reschedule=False,
            )

            results.append(
                TravelProductItem(
                    id=item["id"],
                    category=item["category"],
                    provider=self.provider_name,
                    provider_code=self.provider_code,
                    title=item["title"],
                    subtitle=item["subtitle"],
                    origin=item["origin"],
                    destination=item["destination"],
                    departure_time=item["dep"],
                    arrival_time=item["arr"],
                    duration=item["duration"],
                    operator_name=item["operator"],
                    rating=4.95,
                    amenities=item["amenities"],
                    accessibility=item["accessibility"],
                    cabin_or_seat_class=item["cabin"].title(),
                    available_seats=item["seats"],
                    price_breakdown=pricing,
                    cancellation_policy=policy,
                    retrieved_at=now_iso,
                    tags=item["tags"],
                )
            )
        return results

    def get_by_id(self, product_id: str) -> Optional[TravelProductItem]:
        for item in self._sample_catalog():
            if item["id"] == product_id:
                pricing = calculate_normalized_pricing(item["base_price"], 1)
                policy = TravelCancellationPolicy(is_refundable=True, deadline_hours_before=72, cancellation_fee=25.0)
                return TravelProductItem(
                    id=item["id"],
                    category=item["category"],
                    provider=self.provider_name,
                    provider_code=self.provider_code,
                    title=item["title"],
                    subtitle=item["subtitle"],
                    origin=item["origin"],
                    destination=item["destination"],
                    departure_time=item["dep"],
                    arrival_time=item["arr"],
                    duration=item["duration"],
                    operator_name=item["operator"],
                    amenities=item["amenities"],
                    accessibility=item["accessibility"],
                    cabin_or_seat_class=item["cabin"].title(),
                    available_seats=item["seats"],
                    price_breakdown=pricing,
                    cancellation_policy=policy,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    tags=item["tags"],
                )
        return None

    def confirm_booking(self, booking_req: TravelBookingRequest, product: TravelProductItem) -> Dict[str, Any]:
        pnr = f"EVT-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "CONFIRMED",
            "provider_ref": pnr,
            "eticket_number": f"TKT-PASS-{uuid.uuid4().hex[:8].upper()}",
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "operator_acknowledgement": "Live Nation Access Control: Digital NFC Passes Provisioned",
        }

    def cancel_booking(self, provider_booking_ref: str, reason: str) -> Dict[str, Any]:
        return {
            "status": "CANCELLED",
            "provider_ref": provider_booking_ref,
            "refund_acknowledged": True,
            "refund_tracking_id": f"REF-EVT-{uuid.uuid4().hex[:6].upper()}",
            "message": "Live event barcode revoked. Official refund workflow registered.",
        }

    def reschedule_booking(self, provider_booking_ref: str, new_date: str, reason: Optional[str] = None) -> Dict[str, Any]:
        return {
            "status": "RESCHEDULED",
            "provider_ref": provider_booking_ref,
            "new_departure_date": new_date,
            "message": f"Event ticket moved to scheduled performance on {new_date}.",
        }


class TravelSandboxProvider(BaseTravelAdapter):
    """
    General fallback and testing adapter supporting all 8 product categories.
    Used for automated tests and sandbox bookings when external credentials are demo-configured.
    """
    provider_name = "NEXORA Universal Travel Sandbox"
    provider_code = "NEXORA_SANDBOX"
    supported_categories = [
        "flight", "train", "bus", "hotel", "movie", "event", "concert", "sport"
    ]

    def search(self, query: TravelSearchQuery) -> List[TravelProductItem]:
        now_iso = datetime.now(timezone.utc).isoformat()
        base_price = 120.0
        if query.category == "flight":
            base_price = 250.0
        elif query.category == "hotel":
            base_price = 180.0
        elif query.category in ("movie", "bus"):
            base_price = 30.0

        item_id = f"SBX-{query.category.upper()}-{uuid.uuid4().hex[:4].upper()}"
        pricing = calculate_normalized_pricing(
            base_price=base_price,
            passengers_count=query.passengers_count,
            tax_rate=0.10,
            service_fee=5.00,
            currency="USD",
        )

        policy = TravelCancellationPolicy(
            is_refundable=True,
            deadline_hours_before=24,
            cancellation_fee=10.0,
            description="Sandbox Flexible Policy: Cancel up to 24 hours prior with minimal fee.",
            allow_reschedule=True,
            reschedule_fee=0.0,
        )

        return [
            TravelProductItem(
                id=item_id,
                category=query.category,
                provider=self.provider_name,
                provider_code=self.provider_code,
                title=f"NEXORA Verified {query.category.title()} — {query.destination}",
                subtitle=f"Direct service to {query.destination} on {query.departure_date}",
                origin=query.origin or "Primary Hub",
                destination=query.destination,
                departure_time="10:00 AM",
                arrival_time="02:00 PM",
                duration="4h 00m",
                operator_name="NEXORA Global Travel Alliance",
                rating=4.9,
                amenities=["Wi-Fi Onboard", "Refreshments", "Power Outlets", "Instant Mobile Pass"],
                accessibility=["Wheelchair Accessible", "Audio Descriptions Available"],
                cabin_or_seat_class=query.cabin_class or "Standard",
                available_seats=15,
                price_breakdown=pricing,
                cancellation_policy=policy,
                retrieved_at=now_iso,
                tags=["Verified Sandbox", "Instant Confirmation"],
            )
        ]

    def get_by_id(self, product_id: str) -> Optional[TravelProductItem]:
        now_iso = datetime.now(timezone.utc).isoformat()
        pricing = calculate_normalized_pricing(150.0, 1)
        policy = TravelCancellationPolicy(is_refundable=True, deadline_hours_before=24, cancellation_fee=10.0)
        return TravelProductItem(
            id=product_id,
            category="flight",
            provider=self.provider_name,
            provider_code=self.provider_code,
            title=f"NEXORA Sandbox Pass ({product_id})",
            subtitle="Verified Real-time Service",
            origin="JFK",
            destination="LHR",
            departure_time="10:00 AM",
            arrival_time="09:00 PM",
            duration="7h 00m",
            operator_name="NEXORA Alliance",
            rating=5.0,
            amenities=["Priority Boarding", "Gourmet Refreshments"],
            accessibility=["Wheelchair Assistance"],
            cabin_or_seat_class="Standard",
            available_seats=10,
            price_breakdown=pricing,
            cancellation_policy=policy,
            retrieved_at=now_iso,
            tags=["Sandbox Pass"],
        )

    def confirm_booking(self, booking_req: TravelBookingRequest, product: TravelProductItem) -> Dict[str, Any]:
        pnr = f"PNR-SBX-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "CONFIRMED",
            "provider_ref": pnr,
            "eticket_number": f"SBX-{uuid.uuid4().int % 10000000:07d}",
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "operator_acknowledgement": "NEXORA Commerce Gateway: Sandbox Transaction Cleared",
        }

    def cancel_booking(self, provider_booking_ref: str, reason: str) -> Dict[str, Any]:
        return {
            "status": "CANCELLED",
            "provider_ref": provider_booking_ref,
            "refund_acknowledged": True,
            "refund_tracking_id": f"REF-SBX-{uuid.uuid4().hex[:6].upper()}",
            "message": "Sandbox booking successfully cancelled and refunded.",
        }

    def reschedule_booking(self, provider_booking_ref: str, new_date: str, reason: Optional[str] = None) -> Dict[str, Any]:
        return {
            "status": "RESCHEDULED",
            "provider_ref": provider_booking_ref,
            "new_departure_date": new_date,
            "message": f"Sandbox booking date updated to {new_date}.",
        }
