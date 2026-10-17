import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Plane,
  Train,
  Bus,
  Building2,
  Film,
  Ticket,
  Music,
  Trophy,
  Calendar,
  Users,
  Search,
  Filter,
  CreditCard,
  Clock,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  RefreshCw,
  X,
  ChevronRight,
  ExternalLink,
  Receipt,
  RotateCcw,
  Sparkles,
  Info,
  DollarSign,
  MapPin,
  Lock,
  ArrowRight,
  FileText,
  BookmarkCheck,
} from 'lucide-react';

import {
  TravelCategory,
  TravelProductItem,
  TravelSearchQuery,
  TravelBookingRecord,
  TravelOverviewResponse,
  TravelPassengerInfo,
  TravelPaymentToken,
  TravelHoldResponse,
} from '../../types';
import { api } from '../../services/api';

const CATEGORIES: { id: TravelCategory; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: 'flight', label: 'Flights', icon: Plane },
  { id: 'train', label: 'Trains', icon: Train },
  { id: 'bus', label: 'Buses', icon: Bus },
  { id: 'hotel', label: 'Hotels & Stays', icon: Building2 },
  { id: 'movie', label: 'Movies & Cinema', icon: Film },
  { id: 'event', label: 'Live Events', icon: Ticket },
  { id: 'concert', label: 'Concerts', icon: Music },
  { id: 'sport', label: 'Sports', icon: Trophy },
];

export const TravelBookingStudio: React.FC = () => {
  // Global & Overview State
  const [activeCategory, setActiveCategory] = useState<TravelCategory>('flight');
  const [overview, setOverview] = useState<TravelOverviewResponse | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(false);
  const [myBookings, setMyBookings] = useState<TravelBookingRecord[]>([]);
  const [showMyBookings, setShowMyBookings] = useState(false);
  const [showAuditLedger, setShowAuditLedger] = useState(false);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  // Search Parameters
  const [origin, setOrigin] = useState('SFO');
  const [destination, setDestination] = useState('JFK');
  const [departureDate, setDepartureDate] = useState('2026-11-15');
  const [returnDate, setReturnDate] = useState('');
  const [passengersCount, setPassengersCount] = useState(1);
  const [cabinClass, setCabinClass] = useState('economy');
  const [directOnly, setDirectOnly] = useState(false);
  const [accessibleRequired, setAccessibleRequired] = useState(false);
  const [maxPriceFilter, setMaxPriceFilter] = useState<number | null>(null);

  // Search Results
  const [searchResults, setSearchResults] = useState<TravelProductItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<TravelProductItem | null>(null);

  // Active Hold
  const [activeHold, setActiveHold] = useState<TravelHoldResponse | null>(null);
  const [holdTimerSeconds, setHoldTimerSeconds] = useState<number>(0);

  // Checkout Modal State
  const [showCheckoutModal, setShowCheckoutModal] = useState(false);
  const [passengers, setPassengers] = useState<TravelPassengerInfo[]>([
    {
      passenger_id: 'PAX-1',
      first_name: 'Alex',
      last_name: 'Vanguard',
      email: 'alex.vanguard@nexora.ai',
      phone: '+1 (555) 234-5678',
      document_type: 'PASSPORT',
      seat_preference: 'Window',
    },
  ]);
  const [contactEmail, setContactEmail] = useState('alex.vanguard@nexora.ai');
  const [paymentMethod, setPaymentMethod] = useState<'tokenized_card' | 'upi_token' | 'sandbox_token'>('tokenized_card');
  const [explicitConfirmation, setExplicitConfirmation] = useState(true);
  const [isBooking, setIsBooking] = useState(false);
  const [confirmedBooking, setConfirmedBooking] = useState<TravelBookingRecord | null>(null);

  // Post-booking modification state
  const [rescheduleBookingId, setRescheduleBookingId] = useState<string | null>(null);
  const [rescheduleNewDate, setRescheduleNewDate] = useState('');
  const [cancellationBookingId, setCancellationBookingId] = useState<string | null>(null);
  const [cancellationReason, setCancellationReason] = useState('Schedule conflict');
  const [actionMessage, setActionMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Fetch overview on mount
  const loadOverview = useCallback(async () => {
    setLoadingOverview(true);
    try {
      const data = await api.getTravelOverview();
      setOverview(data);
    } catch (err: any) {
      console.error('Failed to load travel overview:', err);
    } finally {
      setLoadingOverview(false);
    }
  }, []);

  // Fetch user bookings
  const loadBookings = useCallback(async () => {
    try {
      const data = await api.listTravelBookings();
      setMyBookings(data);
    } catch (err: any) {
      console.error('Failed to load bookings:', err);
    }
  }, []);

  // Fetch audit trail
  const loadAuditTrail = useCallback(async () => {
    try {
      const data = await api.getTravelAuditTrail();
      setAuditLogs(data);
    } catch (err: any) {
      console.error('Failed to load audit trail:', err);
    }
  }, []);

  useEffect(() => {
    loadOverview();
    loadBookings();
  }, [loadOverview, loadBookings]);

  // Adjust defaults when category changes
  useEffect(() => {
    if (activeCategory === 'flight') {
      setOrigin('SFO');
      setDestination('JFK');
      setCabinClass('economy');
    } else if (activeCategory === 'train') {
      setOrigin('Paris');
      setDestination('London');
      setCabinClass('standard');
    } else if (activeCategory === 'bus') {
      setOrigin('Berlin');
      setDestination('Prague');
      setCabinClass('standard');
    } else if (activeCategory === 'hotel') {
      setOrigin('');
      setDestination('New York City');
      setCabinClass('deluxe');
    } else if (activeCategory === 'movie') {
      setOrigin('');
      setDestination('San Francisco');
      setCabinClass('vip');
    } else if (activeCategory === 'event') {
      setOrigin('');
      setDestination('Broadway, NYC');
      setCabinClass('standard');
    } else if (activeCategory === 'concert') {
      setOrigin('');
      setDestination('London');
      setCabinClass('vip');
    } else if (activeCategory === 'sport') {
      setOrigin('');
      setDestination('Silverstone, UK');
      setCabinClass('deluxe');
    }
    // Auto-search on category change
    handleSearch(activeCategory);
  }, [activeCategory]);

  // Hold Timer countdown
  useEffect(() => {
    if (!activeHold) return;
    const interval = setInterval(() => {
      setHoldTimerSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          setActiveHold(null);
          setActionMessage({ text: 'Reservation hold expired. Prices updated to live rates.', type: 'info' });
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [activeHold]);

  // Sync passengers count with array
  useEffect(() => {
    setPassengers((prev) => {
      const updated = [...prev];
      while (updated.length < passengersCount) {
        updated.push({
          passenger_id: `PAX-${updated.length + 1}`,
          first_name: '',
          last_name: '',
          email: contactEmail,
          seat_preference: 'Standard',
        });
      }
      return updated.slice(0, passengersCount);
    });
  }, [passengersCount, contactEmail]);

  // Perform search
  const handleSearch = async (cat?: TravelCategory) => {
    setIsSearching(true);
    setActionMessage(null);
    try {
      const query: TravelSearchQuery = {
        category: cat || activeCategory,
        origin: origin || null,
        destination: destination,
        departure_date: departureDate,
        return_date: returnDate || null,
        passengers_count: passengersCount,
        cabin_class: cabinClass || null,
        direct_only: directOnly,
        accessible_required: accessibleRequired,
        max_price: maxPriceFilter,
      };
      const results = await api.searchTravel(query);
      setSearchResults(results);
      if (results.length === 0) {
        setActionMessage({ text: 'No direct availability found for chosen criteria. Showing alliance suggestions.', type: 'info' });
      }
    } catch (err: any) {
      setActionMessage({ text: err.message || 'Search query failed.', type: 'error' });
    } finally {
      setIsSearching(false);
    }
  };

  // Hold inventory
  const handleHold = async (product: TravelProductItem) => {
    try {
      const res = await api.holdTravelInventory({
        product_id: product.id,
        category: product.category,
        provider: product.provider,
        passengers_count: passengersCount,
      });
      setActiveHold(res);
      setHoldTimerSeconds(15 * 60); // 15 mins
      setSelectedProduct(product);
      setActionMessage({
        text: `Price & seat guaranteed for 15 minutes! Hold ID: ${res.hold_id}`,
        type: 'success',
      });
    } catch (err: any) {
      setActionMessage({ text: `Unable to hold inventory: ${err.message}`, type: 'error' });
    }
  };

  // Initiate booking
  const handleInitiateBook = (product: TravelProductItem) => {
    setSelectedProduct(product);
    setShowCheckoutModal(true);
  };

  // Confirm booking purchase
  const handleConfirmPurchase = async () => {
    if (!selectedProduct) return;
    setIsBooking(true);
    setActionMessage(null);

    // Validate passengers
    for (let i = 0; i < passengers.length; i++) {
      if (!passengers[i].first_name.trim() || !passengers[i].last_name.trim()) {
        setActionMessage({ text: `Please fill in First and Last Name for Passenger #${i + 1}.`, type: 'error' });
        setIsBooking(false);
        return;
      }
    }

    try {
      // Deterministic idempotency key
      const idempotencyKey = `IDEMP-${Date.now()}-${Math.random().toString(36).substring(2, 9).toUpperCase()}`;

      const paymentToken: TravelPaymentToken = {
        payment_method: paymentMethod,
        payment_token: `tok_secure_${paymentMethod}_${Date.now()}`,
        card_brand: paymentMethod === 'tokenized_card' ? 'Visa' : undefined,
        card_last4: paymentMethod === 'tokenized_card' ? '4242' : undefined,
        billing_name: `${passengers[0].first_name} ${passengers[0].last_name}`,
      };

      const bookingReq = {
        idempotency_key: idempotencyKey,
        product_id: selectedProduct.id,
        hold_id: activeHold?.hold_id || null,
        category: selectedProduct.category,
        passengers: passengers,
        payment: paymentToken,
        explicit_confirmation: explicitConfirmation,
        contact_email: contactEmail,
      };

      const booking = await api.bookTravel(bookingReq, idempotencyKey);
      setConfirmedBooking(booking);
      setShowCheckoutModal(false);
      setActiveHold(null);
      loadBookings();
      loadOverview();
      setActionMessage({
        text: `Booking Confirmed! Provider Reference: ${booking.provider_booking_ref}. Total: $${booking.price_breakdown.total_amount.toFixed(2)}`,
        type: 'success',
      });
    } catch (err: any) {
      setActionMessage({ text: `Purchase failed: ${err.message}`, type: 'error' });
    } finally {
      setIsBooking(false);
    }
  };

  // Reschedule booking
  const handleExecuteReschedule = async () => {
    if (!rescheduleBookingId || !rescheduleNewDate) return;
    try {
      const updated = await api.rescheduleTravelBooking({
        booking_id: rescheduleBookingId,
        new_departure_date: rescheduleNewDate,
        reason: 'Client requested itinerary update',
      });
      setRescheduleBookingId(null);
      setRescheduleNewDate('');
      loadBookings();
      setActionMessage({
        text: `Trip successfully rescheduled to ${updated.departure_date}! PNR: ${updated.provider_booking_ref}`,
        type: 'success',
      });
    } catch (err: any) {
      setActionMessage({ text: `Reschedule failed: ${err.message}`, type: 'error' });
    }
  };

  // Cancel booking
  const handleExecuteCancellation = async () => {
    if (!cancellationBookingId) return;
    try {
      const updated = await api.cancelTravelBooking({
        booking_id: cancellationBookingId,
        reason: cancellationReason,
        confirm_cancellation: true,
      });
      setCancellationBookingId(null);
      loadBookings();
      setActionMessage({
        text: `Booking ${updated.booking_id} cancelled. Refund status: ${updated.refund_status} ($${updated.refund_amount.toFixed(2)} refunded).`,
        type: 'info',
      });
    } catch (err: any) {
      setActionMessage({ text: `Cancellation error: ${err.message}`, type: 'error' });
    }
  };

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  return (
    <div className="flex flex-col h-full bg-[#050811] text-gray-100 overflow-hidden font-sans">
      {/* Studio Header Bar */}
      <div className="border-b border-cyan-900/40 bg-[#090d1a]/80 backdrop-blur-md px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-blue-600 to-indigo-600 p-[1px] shadow-lg shadow-cyan-500/20">
            <div className="w-full h-full bg-[#070b16] rounded-xl flex items-center justify-center">
              <Plane className="w-5 h-5 text-cyan-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                NEXORA TRAVEL COMMERCE
                <span className="text-xs uppercase px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-mono">
                  STAGE 29
                </span>
              </h1>
            </div>
            <p className="text-xs text-gray-400">
              Universal multi-provider booking across 8 product categories with guaranteed live availability & tokenized security
            </p>
          </div>
        </div>

        {/* Global Action Badges */}
        <div className="flex items-center space-x-3">
          {activeHold && (
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs animate-pulse">
              <Clock className="w-4 h-4 text-amber-400" />
              <span>Held Quote: <strong>{formatTimer(holdTimerSeconds)}</strong></span>
            </div>
          )}

          <button
            onClick={() => {
              setShowMyBookings(!showMyBookings);
              setShowAuditLedger(false);
            }}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-800/50 text-cyan-300 text-xs transition"
          >
            <BookmarkCheck className="w-4 h-4 text-cyan-400" />
            <span>My Bookings</span>
            <span className="ml-1 px-1.5 py-0.2 rounded-full bg-cyan-500/20 text-cyan-300 font-mono text-[10px]">
              {myBookings.length}
            </span>
          </button>

          <button
            onClick={() => {
              setShowAuditLedger(!showAuditLedger);
              setShowMyBookings(false);
              loadAuditTrail();
            }}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-900 hover:bg-gray-800 border border-gray-700 text-gray-300 text-xs transition"
          >
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Audit Ledger</span>
          </button>
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionMessage && (
        <div
          className={`px-6 py-2.5 text-xs flex items-center justify-between border-b ${
            actionMessage.type === 'success'
              ? 'bg-emerald-950/60 border-emerald-800/50 text-emerald-300'
              : actionMessage.type === 'error'
              ? 'bg-rose-950/60 border-rose-800/50 text-rose-300'
              : 'bg-cyan-950/60 border-cyan-800/50 text-cyan-300'
          }`}
        >
          <div className="flex items-center space-x-2">
            {actionMessage.type === 'success' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
            {actionMessage.type === 'error' && <AlertCircle className="w-4 h-4 text-rose-400" />}
            {actionMessage.type === 'info' && <Info className="w-4 h-4 text-cyan-400" />}
            <span>{actionMessage.text}</span>
          </div>
          <button onClick={() => setActionMessage(null)} className="text-gray-400 hover:text-white">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Studio Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left / Main Workspace */}
        <div className="flex-1 flex flex-col overflow-y-auto p-6 space-y-6">
          {/* Category Switcher Tabs */}
          <div className="flex items-center space-x-2 overflow-x-auto pb-2 border-b border-gray-800">
            {CATEGORIES.map((cat) => {
              const Icon = cat.icon;
              const isActive = activeCategory === cat.id;
              return (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategory(cat.id)}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-medium whitespace-nowrap transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-md shadow-cyan-500/20'
                      : 'bg-[#0f1424] hover:bg-[#161e36] text-gray-400 hover:text-gray-200 border border-gray-800'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{cat.label}</span>
                </button>
              );
            })}
          </div>

          {/* Search Query Console */}
          <div className="bg-[#0b1021] border border-cyan-900/30 rounded-2xl p-5 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl -z-0 pointer-events-none" />

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative z-10">
              {/* Origin */}
              <div>
                <label className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block mb-1.5">
                  Origin / Departure Point
                </label>
                <div className="relative">
                  <MapPin className="w-4 h-4 text-cyan-400 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="text"
                    value={origin}
                    onChange={(e) => setOrigin(e.target.value)}
                    placeholder={activeCategory === 'hotel' ? 'N/A' : 'e.g. SFO, Paris, Tokyo'}
                    className="w-full bg-[#12182c] border border-gray-800 focus:border-cyan-500 rounded-xl pl-9 pr-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none"
                  />
                </div>
              </div>

              {/* Destination */}
              <div>
                <label className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block mb-1.5">
                  Destination / Venue
                </label>
                <div className="relative">
                  <MapPin className="w-4 h-4 text-blue-400 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="text"
                    value={destination}
                    onChange={(e) => setDestination(e.target.value)}
                    placeholder="e.g. JFK, London, New York"
                    className="w-full bg-[#12182c] border border-gray-800 focus:border-blue-500 rounded-xl pl-9 pr-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none"
                  />
                </div>
              </div>

              {/* Departure Date */}
              <div>
                <label className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block mb-1.5">
                  Date
                </label>
                <div className="relative">
                  <Calendar className="w-4 h-4 text-indigo-400 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="date"
                    value={departureDate}
                    onChange={(e) => setDepartureDate(e.target.value)}
                    className="w-full bg-[#12182c] border border-gray-800 focus:border-indigo-500 rounded-xl pl-9 pr-3 py-2 text-sm text-white focus:outline-none"
                  />
                </div>
              </div>

              {/* Passengers / Attendees Stepper */}
              <div>
                <label className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block mb-1.5">
                  Seats / Manifest Count
                </label>
                <div className="flex items-center space-x-2 bg-[#12182c] border border-gray-800 rounded-xl p-1">
                  <button
                    onClick={() => setPassengersCount((c) => Math.max(1, c - 1))}
                    className="w-8 h-8 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 font-bold flex items-center justify-center transition"
                  >
                    -
                  </button>
                  <div className="flex-1 text-center font-mono text-sm font-semibold text-cyan-300">
                    {passengersCount} {passengersCount === 1 ? 'Guest' : 'Guests'}
                  </div>
                  <button
                    onClick={() => setPassengersCount((c) => Math.min(9, c + 1))}
                    className="w-8 h-8 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 font-bold flex items-center justify-center transition"
                  >
                    +
                  </button>
                </div>
              </div>
            </div>

            {/* Filter Row */}
            <div className="flex flex-wrap items-center justify-between gap-4 mt-4 pt-4 border-t border-gray-800/80">
              <div className="flex flex-wrap items-center gap-3">
                <label className="flex items-center space-x-2 text-xs text-gray-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={directOnly}
                    onChange={(e) => setDirectOnly(e.target.checked)}
                    className="rounded bg-gray-800 border-gray-700 text-cyan-500 focus:ring-0"
                  />
                  <span>Direct / Non-stop only</span>
                </label>

                <label className="flex items-center space-x-2 text-xs text-gray-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={accessibleRequired}
                    onChange={(e) => setAccessibleRequired(e.target.checked)}
                    className="rounded bg-gray-800 border-gray-700 text-cyan-500 focus:ring-0"
                  />
                  <span>Wheelchair Accessible</span>
                </label>

                <select
                  value={cabinClass}
                  onChange={(e) => setCabinClass(e.target.value)}
                  className="bg-[#12182c] border border-gray-800 text-xs text-gray-300 rounded-lg px-2.5 py-1.5 focus:outline-none"
                >
                  <option value="economy">Economy / Standard</option>
                  <option value="premium_economy">Premium Economy</option>
                  <option value="business">Business Class</option>
                  <option value="first">First Class / Suite</option>
                  <option value="vip">VIP / Executive</option>
                  <option value="deluxe">Deluxe Room</option>
                </select>
              </div>

              <button
                onClick={() => handleSearch()}
                disabled={isSearching}
                className="flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-medium text-xs tracking-wide shadow-lg shadow-cyan-500/25 transition disabled:opacity-50"
              >
                {isSearching ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                <span>CHECK LIVE AVAILABILITY</span>
              </button>
            </div>
          </div>

          {/* Results Catalog */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold tracking-wide uppercase text-gray-400 flex items-center gap-2">
                <span>Verified Inventory</span>
                <span className="text-xs font-mono text-cyan-400">({searchResults.length} options)</span>
              </h2>
              <div className="text-xs text-gray-500 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Zero hidden fees • Strict provider terms preserved</span>
              </div>
            </div>

            {isSearching ? (
              <div className="p-12 text-center text-gray-400 flex flex-col items-center justify-center space-y-3">
                <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
                <p className="text-sm">Querying real-time global inventory networks...</p>
              </div>
            ) : searchResults.length === 0 ? (
              <div className="bg-[#0b1021] border border-dashed border-gray-800 rounded-2xl p-12 text-center text-gray-500">
                <Calendar className="w-10 h-10 mx-auto text-gray-600 mb-3" />
                <p className="text-sm font-medium text-gray-300">No scheduled departures found</p>
                <p className="text-xs text-gray-500 mt-1">Try broadening your destination or date range.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {searchResults.map((item) => (
                  <div
                    key={item.id}
                    className="bg-[#0c1224] hover:bg-[#101730] border border-gray-800/80 hover:border-cyan-500/40 rounded-2xl p-5 transition-all shadow-md group"
                  >
                    <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
                      {/* Left: Product Overview */}
                      <div className="space-y-2 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="px-2.5 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-800/60 text-cyan-300 text-[11px] font-mono font-medium">
                            {item.provider}
                          </span>
                          <span className="px-2.5 py-0.5 rounded-full bg-gray-800 text-gray-300 text-[11px] font-mono">
                            {item.cabin_or_seat_class}
                          </span>
                          <span className="text-xs text-amber-400 flex items-center gap-1 font-semibold">
                            ★ {item.rating || 4.9}
                          </span>
                          <span className="text-[11px] text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded-md font-mono">
                            {item.available_seats} seats remaining
                          </span>
                        </div>

                        <h3 className="text-base font-semibold text-white group-hover:text-cyan-300 transition">
                          {item.title}
                        </h3>
                        {item.subtitle && <p className="text-xs text-gray-400">{item.subtitle}</p>}

                        {/* Timing / Origin -> Destination */}
                        <div className="flex items-center space-x-3 text-xs text-gray-300 pt-1">
                          {item.origin && (
                            <>
                              <span className="font-semibold text-white">{item.origin}</span>
                              <ArrowRight className="w-3.5 h-3.5 text-cyan-400" />
                            </>
                          )}
                          <span className="font-semibold text-white">{item.destination}</span>
                          {item.departure_time && (
                            <span className="text-gray-400">
                              • {item.departure_time} {item.arrival_time ? `→ ${item.arrival_time}` : ''}
                            </span>
                          )}
                          {item.duration && <span className="text-gray-500">({item.duration})</span>}
                        </div>

                        {/* Amenities Chips */}
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {item.amenities.slice(0, 4).map((amenity, idx) => (
                            <span
                              key={idx}
                              className="text-[10px] px-2 py-0.5 rounded bg-gray-900 border border-gray-800 text-gray-400"
                            >
                              {amenity}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Right: Pricing Breakdown & Action Buttons */}
                      <div className="flex flex-col items-end space-y-3 min-w-[200px]">
                        <div className="text-right">
                          <div className="text-2xl font-bold font-mono text-cyan-300">
                            ${item.price_breakdown.total_amount.toFixed(2)}
                          </div>
                          <div className="text-[10px] text-gray-400 space-y-0.5">
                            <div>Base: ${item.price_breakdown.base_amount.toFixed(2)}</div>
                            <div>Taxes & Carrier Fees: ${(item.price_breakdown.taxes_amount + item.price_breakdown.fees_amount).toFixed(2)}</div>
                          </div>
                        </div>

                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => handleHold(item)}
                            className="px-3 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-medium transition"
                          >
                            Hold 15m
                          </button>
                          <button
                            onClick={() => handleInitiateBook(item)}
                            className="flex items-center space-x-1.5 px-4 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-medium text-xs tracking-wide shadow-md shadow-cyan-500/20 transition"
                          >
                            <span>Book Now</span>
                            <ChevronRight className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Drawer: My Bookings */}
        {showMyBookings && (
          <div className="w-96 border-l border-gray-800 bg-[#070b16] p-5 flex flex-col space-y-4 overflow-y-auto">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center space-x-2">
                <BookmarkCheck className="w-5 h-5 text-cyan-400" />
                <h3 className="text-sm font-semibold text-white uppercase tracking-wider">My Reservations</h3>
              </div>
              <button onClick={() => setShowMyBookings(false)} className="text-gray-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            {myBookings.length === 0 ? (
              <p className="text-xs text-gray-500 text-center py-8">No travel bookings registered yet.</p>
            ) : (
              <div className="space-y-4">
                {myBookings.map((b) => (
                  <div key={b.booking_id} className="bg-[#0e1428] border border-gray-800 rounded-xl p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-cyan-400">{b.provider_booking_ref}</span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                          b.booking_status === 'CONFIRMED'
                            ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/40'
                            : b.booking_status === 'CANCELLED'
                            ? 'bg-rose-950/60 text-rose-400 border border-rose-800/40'
                            : 'bg-amber-950/60 text-amber-400 border border-amber-800/40'
                        }`}
                      >
                        {b.booking_status}
                      </span>
                    </div>

                    <div>
                      <h4 className="text-xs font-semibold text-white">{b.product_summary}</h4>
                      <p className="text-[11px] text-gray-400">
                        {b.destination} • {b.departure_date}
                      </p>
                    </div>

                    <div className="text-[11px] text-gray-300 font-mono flex items-center justify-between border-t border-gray-800/80 pt-2">
                      <span>Total Paid:</span>
                      <span className="font-bold text-white">${b.price_breakdown.total_amount.toFixed(2)}</span>
                    </div>

                    {b.booking_status === 'CONFIRMED' && (
                      <div className="flex items-center space-x-2 pt-1 border-t border-gray-800">
                        <button
                          onClick={() => {
                            setRescheduleBookingId(b.booking_id);
                            setRescheduleNewDate(b.departure_date);
                          }}
                          className="flex-1 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 text-[10px] font-medium transition"
                        >
                          Reschedule
                        </button>
                        <button
                          onClick={() => setCancellationBookingId(b.booking_id)}
                          className="flex-1 py-1 rounded bg-rose-950/40 hover:bg-rose-900/40 border border-rose-800/40 text-rose-300 text-[10px] font-medium transition"
                        >
                          Cancel / Refund
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Right Drawer: Audit Ledger */}
        {showAuditLedger && (
          <div className="w-96 border-l border-gray-800 bg-[#070b16] p-5 flex flex-col space-y-4 overflow-y-auto font-mono">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <h3 className="text-sm font-semibold text-white uppercase tracking-wider font-sans">
                  Immutable Audit Ledger
                </h3>
              </div>
              <button onClick={() => setShowAuditLedger(false)} className="text-gray-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              {auditLogs.map((log) => (
                <div key={log.audit_id} className="bg-[#0b1021] border border-gray-800 rounded-lg p-3 space-y-1">
                  <div className="flex items-center justify-between text-[10px] text-gray-500">
                    <span>{log.audit_id}</span>
                    <span>{log.created_at.substring(11, 19)} UTC</span>
                  </div>
                  <div className="text-cyan-400 font-semibold">{log.action}</div>
                  <div className="text-gray-400 text-[11px]">Provider: {log.provider}</div>
                  <div className="text-emerald-400 text-[10px]">Status: {log.status}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Checkout & Passenger Manifest Modal */}
      {showCheckoutModal && selectedProduct && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0b1021] border border-cyan-800/60 rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <span>CONFIRM RESERVATION & CHECKOUT</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800 text-cyan-400 font-mono">
                    {selectedProduct.provider}
                  </span>
                </h3>
                <p className="text-xs text-gray-400">{selectedProduct.title}</p>
              </div>
              <button onClick={() => setShowCheckoutModal(false)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-5 flex-1">
              {/* Passenger Manifest Inputs */}
              <div>
                <h4 className="text-xs font-semibold uppercase text-cyan-400 mb-3 flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  <span>Passenger / Guest Manifest ({passengers.length})</span>
                </h4>

                <div className="space-y-3">
                  {passengers.map((pax, idx) => (
                    <div key={pax.passenger_id} className="bg-[#101730] border border-gray-800 rounded-xl p-3.5 space-y-3">
                      <div className="text-[11px] font-semibold text-gray-400">
                        Passenger #{idx + 1}
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <input
                          type="text"
                          value={pax.first_name}
                          onChange={(e) => {
                            const val = e.target.value;
                            setPassengers((prev) =>
                              prev.map((p, i) => (i === idx ? { ...p, first_name: val } : p))
                            );
                          }}
                          placeholder="First Name *"
                          className="bg-[#070b16] border border-gray-800 text-xs text-white rounded-lg p-2 focus:outline-none focus:border-cyan-500"
                        />
                        <input
                          type="text"
                          value={pax.last_name}
                          onChange={(e) => {
                            const val = e.target.value;
                            setPassengers((prev) =>
                              prev.map((p, i) => (i === idx ? { ...p, last_name: val } : p))
                            );
                          }}
                          placeholder="Last Name *"
                          className="bg-[#070b16] border border-gray-800 text-xs text-white rounded-lg p-2 focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Contact Email */}
              <div>
                <label className="text-[11px] font-semibold uppercase text-gray-400 block mb-1.5">
                  E-Ticket Notification Email
                </label>
                <input
                  type="email"
                  value={contactEmail}
                  onChange={(e) => setContactEmail(e.target.value)}
                  className="w-full bg-[#101730] border border-gray-800 text-xs text-white rounded-xl p-2.5 focus:outline-none focus:border-cyan-500"
                />
              </div>

              {/* Tokenized Payment Selector */}
              <div>
                <h4 className="text-xs font-semibold uppercase text-cyan-400 mb-2 flex items-center gap-2">
                  <Lock className="w-4 h-4 text-emerald-400" />
                  <span>Secure Tokenized Payment (No Raw Card Stored)</span>
                </h4>

                <div className="grid grid-cols-3 gap-3">
                  <button
                    type="button"
                    onClick={() => setPaymentMethod('tokenized_card')}
                    className={`p-3 rounded-xl border text-left text-xs transition ${
                      paymentMethod === 'tokenized_card'
                        ? 'border-cyan-500 bg-cyan-950/40 text-cyan-300'
                        : 'border-gray-800 bg-[#101730] text-gray-400'
                    }`}
                  >
                    <CreditCard className="w-4 h-4 mb-1 text-cyan-400" />
                    <div className="font-semibold text-white">Tokenized Card</div>
                    <div className="text-[10px] text-gray-500">tok_visa_4242</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setPaymentMethod('upi_token')}
                    className={`p-3 rounded-xl border text-left text-xs transition ${
                      paymentMethod === 'upi_token'
                        ? 'border-cyan-500 bg-cyan-950/40 text-cyan-300'
                        : 'border-gray-800 bg-[#101730] text-gray-400'
                    }`}
                  >
                    <Sparkles className="w-4 h-4 mb-1 text-blue-400" />
                    <div className="font-semibold text-white">Instant UPI</div>
                    <div className="text-[10px] text-gray-500">tok_upi_verified</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setPaymentMethod('sandbox_token')}
                    className={`p-3 rounded-xl border text-left text-xs transition ${
                      paymentMethod === 'sandbox_token'
                        ? 'border-cyan-500 bg-cyan-950/40 text-cyan-300'
                        : 'border-gray-800 bg-[#101730] text-gray-400'
                    }`}
                  >
                    <ShieldCheck className="w-4 h-4 mb-1 text-emerald-400" />
                    <div className="font-semibold text-white">Zero-Risk Sandbox</div>
                    <div className="text-[10px] text-gray-500">Pre-approved Mock</div>
                  </button>
                </div>
              </div>

              {/* Price Breakdown Summary */}
              <div className="bg-[#070b16] border border-gray-800 rounded-xl p-4 text-xs space-y-1.5 font-mono">
                <div className="flex justify-between text-gray-400">
                  <span>Base Price ({passengers.length} pax):</span>
                  <span>${selectedProduct.price_breakdown.base_amount.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-gray-400">
                  <span>Taxes & Carrier Surcharges:</span>
                  <span>${selectedProduct.price_breakdown.taxes_amount.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-gray-400">
                  <span>Provider Technology Fee:</span>
                  <span>${selectedProduct.price_breakdown.fees_amount.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-white font-bold border-t border-gray-800 pt-2 text-sm">
                  <span>Total Amount Due:</span>
                  <span className="text-cyan-300">${selectedProduct.price_breakdown.total_amount.toFixed(2)} USD</span>
                </div>
              </div>

              {/* Explicit Confirmation Gate */}
              <label className="flex items-start space-x-2.5 text-xs text-gray-300 cursor-pointer pt-1">
                <input
                  type="checkbox"
                  checked={explicitConfirmation}
                  onChange={(e) => setExplicitConfirmation(e.target.checked)}
                  className="rounded mt-0.5 bg-gray-800 border-gray-700 text-cyan-500"
                />
                <span>
                  I explicitly authorize this booking under the provider terms and cancellation policies stated above.
                </span>
              </label>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-gray-800 flex items-center justify-between bg-[#070b16]">
              <button
                type="button"
                onClick={() => setShowCheckoutModal(false)}
                className="px-4 py-2 rounded-xl text-xs text-gray-400 hover:text-white"
              >
                Back to Search
              </button>
              <button
                type="button"
                onClick={handleConfirmPurchase}
                disabled={isBooking || !explicitConfirmation}
                className="flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-xs tracking-wide shadow-lg shadow-cyan-500/20 transition disabled:opacity-50"
              >
                {isBooking ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />}
                <span>PAY & ISSUE TICKET</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmed E-Ticket Digital Pass Modal */}
      {confirmedBooking && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#0b1021] border border-cyan-500/60 rounded-3xl w-full max-w-lg p-6 shadow-2xl relative overflow-hidden space-y-5">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center space-x-2">
                <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                <h3 className="text-base font-bold text-white tracking-wider">BOOKING CONFIRMED</h3>
              </div>
              <button onClick={() => setConfirmedBooking(null)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Digital Pass Boarding Pass Card */}
            <div className="bg-gradient-to-br from-[#0e162e] to-[#0a0e1c] border border-cyan-800/80 rounded-2xl p-5 space-y-4 shadow-xl">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-[10px] uppercase font-mono text-cyan-400 font-semibold tracking-wider">
                    PROVIDER PNR / REFERENCE
                  </span>
                  <div className="text-2xl font-mono font-bold text-white tracking-widest">
                    {confirmedBooking.provider_booking_ref}
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] uppercase font-mono text-gray-400">BOOKING ID</span>
                  <div className="text-xs font-mono text-gray-200">{confirmedBooking.booking_id}</div>
                </div>
              </div>

              <div className="border-t border-dashed border-gray-800 my-2" />

              <div>
                <h4 className="text-sm font-semibold text-white">{confirmedBooking.product_summary}</h4>
                <p className="text-xs text-gray-400">
                  {confirmedBooking.operator_name} • {confirmedBooking.destination}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                <div>
                  <span className="text-gray-500 text-[10px]">DEPARTURE DATE</span>
                  <div className="text-gray-200">{confirmedBooking.departure_date}</div>
                </div>
                <div>
                  <span className="text-gray-500 text-[10px]">PASSENGERS</span>
                  <div className="text-gray-200">{confirmedBooking.passengers.length} Recorded</div>
                </div>
              </div>

              {/* Barcode Mock */}
              <div className="pt-2 text-center">
                <div className="h-10 bg-white/10 rounded flex items-center justify-around px-4">
                  {[...Array(28)].map((_, i) => (
                    <div
                      key={i}
                      className={`h-full ${i % 3 === 0 ? 'w-1 bg-white' : i % 2 === 0 ? 'w-0.5 bg-white/80' : 'w-1.5 bg-white/60'}`}
                    />
                  ))}
                </div>
                <div className="text-[10px] text-gray-500 font-mono mt-1">
                  SECURE CRYPTOGRAPHIC BOARDING PASS BARCODE
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs text-gray-400 pt-2">
              <span>Receipt sent to: <strong>{confirmedBooking.receipt_url}</strong></span>
              <button
                onClick={() => setConfirmedBooking(null)}
                className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-medium transition"
              >
                Close & View Bookings
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reschedule Dialog Modal */}
      {rescheduleBookingId && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-[#0b1021] border border-cyan-800 rounded-2xl w-full max-w-md p-6 space-y-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Reschedule Itinerary</h3>
            <p className="text-xs text-gray-400">
              Select new departure date. Policy fees will be applied where applicable.
            </p>
            <input
              type="date"
              value={rescheduleNewDate}
              onChange={(e) => setRescheduleNewDate(e.target.value)}
              className="w-full bg-[#101730] border border-gray-800 text-xs text-white rounded-xl p-2.5"
            />
            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setRescheduleBookingId(null)}
                className="px-4 py-2 rounded-xl text-xs text-gray-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteReschedule}
                className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold"
              >
                Confirm Reschedule
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cancellation Dialog Modal */}
      {cancellationBookingId && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-[#0b1021] border border-rose-800/80 rounded-2xl w-full max-w-md p-6 space-y-4">
            <h3 className="text-sm font-bold text-rose-300 uppercase tracking-wider">Cancel & Request Refund</h3>
            <p className="text-xs text-gray-400">
              Provider cancellation terms will evaluate eligibility based on remaining hours to departure.
            </p>
            <input
              type="text"
              value={cancellationReason}
              onChange={(e) => setCancellationReason(e.target.value)}
              placeholder="Reason for cancellation..."
              className="w-full bg-[#101730] border border-gray-800 text-xs text-white rounded-xl p-2.5"
            />
            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setCancellationBookingId(null)}
                className="px-4 py-2 rounded-xl text-xs text-gray-400 hover:text-white"
              >
                Keep Booking
              </button>
              <button
                onClick={handleExecuteCancellation}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold"
              >
                Confirm Cancellation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TravelBookingStudio;
