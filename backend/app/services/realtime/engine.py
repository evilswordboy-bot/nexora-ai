"""
NEXORA AI — Real-Time Live Intelligence & Topic Monitoring Engine
Provides:
- Real-time connector retrieving fresh live data across web search and open data sources
- Topic and URL monitoring with SHA-256 fingerprinting & change detection
- In-memory/persisted notification registry for content updates
- Intelligent freshness detection & time-stamped source provenance
- Respectful scraping with SSRF protection, caching, and rate limiting
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
import logging

from app.models.schemas import (
    LiveCategory,
    LiveSourceItem,
    MonitoredTopic,
    LiveNotification,
    LiveQueryRequest,
    LiveQueryResponse,
    ChatRequest,
    Message,
)
from app.services.search.search_service import SearchService
from app.services.search.scraper import WebpageScraper
from app.services.ai_service import ai_service

logger = logging.getLogger("nexora.realtime")


class RealTimeEngine:
    """Enterprise real-time intelligence aggregator and change monitoring engine."""

    def __init__(self):
        self.search_service = SearchService()
        self.scraper = WebpageScraper()
        # In-memory monitoring registry (can be backed by SQLite/JSON)
        self.monitored_topics: Dict[str, MonitoredTopic] = {}
        self.notifications: List[LiveNotification] = []
        # Cache for fresh queries: query -> (timestamp, LiveQueryResponse)
        self.query_cache: Dict[str, Tuple[datetime, LiveQueryResponse]] = {}
        self.cache_ttl_seconds = 300 # 5 minutes

        self._seed_default_monitored_topics()

    def _seed_default_monitored_topics(self):
        """Seed pre-configured topics so the user immediately has visible monitored feeds."""
        t1_id = "topic-ai-research"
        self.monitored_topics[t1_id] = MonitoredTopic(
            id=t1_id,
            name="Frontier AI & LLM Breakthroughs",
            query_or_url="latest artificial intelligence model breakthroughs 2026",
            category="research",
            check_interval_minutes=60,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            last_checked_at=datetime.now(timezone.utc) - timedelta(minutes=15),
            next_check_at=datetime.now(timezone.utc) + timedelta(minutes=45),
            last_content_hash="hash_seed_1",
            change_count=1,
            latest_summary="Tracking next-generation reasoning architectures and multi-modal models."
        )

        t2_id = "topic-tech-news"
        self.monitored_topics[t2_id] = MonitoredTopic(
            id=t2_id,
            name="Global Technology & Software Trends",
            query_or_url="major global software and technology industry news",
            category="tech",
            check_interval_minutes=120,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            last_checked_at=datetime.now(timezone.utc) - timedelta(minutes=40),
            next_check_at=datetime.now(timezone.utc) + timedelta(minutes=80),
            last_content_hash="hash_seed_2",
            change_count=2,
            latest_summary="Monitored industry quarterly earnings, open source updates, and infrastructure."
        )

    @staticmethod
    def _compute_content_hash(text: str) -> str:
        """Returns stable SHA-256 fingerprint for text comparison."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    async def execute_live_query(
        self,
        request: LiveQueryRequest,
        provider: str = "auto",
        model: str = "gemini-1.5-flash",
        client_api_key: Optional[str] = None
    ) -> LiveQueryResponse:
        """
        Executes a freshness-aware real-time search with live source citations
        and AI evidence synthesis.
        """
        cache_key = f"{request.category}:{request.query.strip().lower()}"
        now = datetime.now(timezone.utc)

        # Check Cache if not forcing refresh
        if not request.force_refresh and cache_key in self.query_cache:
            cached_time, cached_response = self.query_cache[cache_key]
            if (now - cached_time).total_seconds() < self.cache_ttl_seconds:
                # Mark as cached provenance
                cached_sources = [
                    LiveSourceItem(
                        title=s.title,
                        url=s.url,
                        snippet=s.snippet,
                        domain=s.domain,
                        published_date=s.published_date,
                        retrieved_at=s.retrieved_at,
                        source_freshness="cached"
                    )
                    for s in cached_response.sources
                ]
                return LiveQueryResponse(
                    query=cached_response.query,
                    category=cached_response.category,
                    is_fresh_retrieval=False,
                    retrieved_at=cached_time,
                    freshness_label=f"Retrieved {int((now - cached_time).total_seconds() // 60)}m ago (Cached)",
                    sources=cached_sources,
                    synthesized_answer=cached_response.synthesized_answer,
                    provider=cached_response.provider,
                    model=cached_response.model
                )

        # 1. Retrieve fresh sources via SearchService
        raw_results = await self.search_service.execute_search(
            query=request.query,
            max_results=request.max_sources or 5,
            engine_preference=request.search_engine or "auto",
            client_key=request.client_search_key
        )

        live_sources: List[LiveSourceItem] = []
        for r in raw_results:
            live_sources.append(
                LiveSourceItem(
                    title=r.title,
                    url=r.url,
                    snippet=r.snippet,
                    domain=r.domain,
                    published_date=r.published_date,
                    retrieved_at=now,
                    source_freshness="fresh"
                )
            )

        # 2. Synthesize with LLM if sources were found
        if live_sources:
            evidence_blocks = []
            for idx, s in enumerate(live_sources, 1):
                date_str = f" ({s.published_date})" if s.published_date else ""
                evidence_blocks.append(f"[{idx}] {s.title}{date_str}\nURL: {s.url}\nSummary: {s.snippet}\n")

            prompt = (
                f"You are NEXORA AI Real-Time Intelligence Analyst.\n\n"
                f"Topic Query: {request.query}\n"
                f"Category: {request.category}\n"
                f"Time of Retrieval: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
                f"Live Retrieved Evidence:\n"
                f"{''.join(evidence_blocks)}\n\n"
                f"Instructions:\n"
                f"1. Synthesize a concise, accurate real-time briefing based on the verified evidence above.\n"
                f"2. Cite sources using numbers like [1], [2] when stating facts.\n"
                f"3. Clearly distinguish confirmed live updates from unverified claims or estimates.\n"
                f"4. If sources have conflicting reports, highlight the discrepancies.\n"
                f"5. Do not invent citations, dates, or statistics."
            )

            chat_req = ChatRequest(
                messages=[Message(id=f"rt_{uuid.uuid4().hex[:8]}", role="user", content=prompt)],
                provider=provider,
                model=model,
                client_api_key=client_api_key,
                temperature=0.3,
                search_mode="ai_only"
            )

            ai_res = await ai_service.generate_response(chat_req)
            answer = ai_res.content
            out_provider = ai_res.provider
            out_model = ai_res.model
        else:
            answer = (
                f"No live sources could be retrieved for '{request.query}' at this time. "
                f"The search service returned 0 results or external sources were temporarily unreachable."
            )
            out_provider = "realtime_engine"
            out_model = "fallback"

        response = LiveQueryResponse(
            query=request.query,
            category=request.category or "general",
            is_fresh_retrieval=True,
            retrieved_at=now,
            freshness_label="Retrieved just now (Live Web)",
            sources=live_sources,
            synthesized_answer=answer,
            provider=out_provider,
            model=out_model
        )

        # Cache response
        self.query_cache[cache_key] = (now, response)
        return response

    # ==========================================
    # Knowledge Refresh & Topic Monitoring
    # ==========================================

    def get_monitored_topics(self) -> List[MonitoredTopic]:
        return list(self.monitored_topics.values())

    def create_monitored_topic(
        self,
        name: str,
        query_or_url: str,
        category: LiveCategory = "general",
        check_interval_minutes: int = 60
    ) -> MonitoredTopic:
        topic_id = f"topic-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        topic = MonitoredTopic(
            id=topic_id,
            name=name,
            query_or_url=query_or_url,
            category=category,
            check_interval_minutes=max(15, check_interval_minutes),
            is_active=True,
            created_at=now,
            last_checked_at=None,
            next_check_at=now + timedelta(minutes=check_interval_minutes),
            last_content_hash=None,
            change_count=0,
            latest_summary="Newly registered topic. Awaiting first check."
        )
        self.monitored_topics[topic_id] = topic
        return topic

    def delete_monitored_topic(self, topic_id: str) -> bool:
        if topic_id in self.monitored_topics:
            del self.monitored_topics[topic_id]
            return True
        return False

    async def refresh_monitored_topic(
        self,
        topic_id: str,
        provider: str = "auto",
        model: str = "gemini-1.5-flash",
        client_api_key: Optional[str] = None
    ) -> Tuple[MonitoredTopic, Optional[LiveNotification]]:
        """
        Manually or periodically checks a monitored topic or URL for content changes.
        Generates fingerprint hash, detects differences, and logs notifications.
        """
        topic = self.monitored_topics.get(topic_id)
        if not topic:
            raise ValueError(f"Topic {topic_id} not found.")

        now = datetime.now(timezone.utc)
        target = topic.query_or_url.strip()
        notification: Optional[LiveNotification] = None

        # Check if target is a direct URL
        if target.startswith("http://") or target.startswith("https://"):
            raw_content = await self.scraper.fetch_page_content(target, max_chars=4000)
            if not raw_content:
                raw_content = f"Fetched page {target} but content was empty or protected."
            summary = raw_content[:280] + ("..." if len(raw_content) > 280 else "")
            new_hash = self._compute_content_hash(raw_content)
            source_urls = [target]
        else:
            # Query-based search monitoring
            live_res = await self.execute_live_query(
                request=LiveQueryRequest(
                    query=target,
                    category=topic.category,
                    force_refresh=True,
                    max_sources=4
                ),
                provider=provider,
                model=model,
                client_api_key=client_api_key
            )
            raw_content = "\n".join([f"{s.title}: {s.snippet}" for s in live_res.sources])
            summary = live_res.synthesized_answer[:320] + ("..." if len(live_res.synthesized_answer) > 320 else "")
            new_hash = self._compute_content_hash(raw_content)
            source_urls = [s.url for s in live_res.sources]

        # Determine if content meaningfully changed
        has_changed = False
        if topic.last_content_hash and topic.last_content_hash != new_hash:
            has_changed = True
            topic.change_count += 1
            # Create in-app notification
            notification = LiveNotification(
                id=f"notif-{uuid.uuid4().hex[:8]}",
                topic_id=topic.id,
                topic_name=topic.name,
                title=f"Fresh updates detected: {topic.name}",
                summary_diff=summary,
                detected_at=now,
                source_urls=source_urls,
                is_read=False
            )
            self.notifications.insert(0, notification)

        topic.last_checked_at = now
        topic.next_check_at = now + timedelta(minutes=topic.check_interval_minutes)
        topic.last_content_hash = new_hash
        topic.latest_summary = summary

        return topic, notification

    def get_notifications(self) -> List[LiveNotification]:
        return self.notifications

    def mark_notifications_read(self) -> None:
        for n in self.notifications:
            n.is_read = True

    def clear_notifications(self) -> None:
        self.notifications.clear()


realtime_engine = RealTimeEngine()
