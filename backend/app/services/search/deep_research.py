import asyncio
import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Tuple

from app.config import settings
from app.models.schemas import SearchResultItem, ChatRequest, Message
from app.services.search.search_service import search_service
from app.services.search.scraper import scraper

logger = logging.getLogger("nexora.deep_research")


class DeepResearchEngine:
    """
    Stage 3 Modular Deep Research Engine.
    Executes multi-step iterative research: query decomposition, multi-pass search,
    page extraction, contradiction analysis, and source-grounded report synthesis.
    """

    def decompose_query(self, user_prompt: str) -> List[str]:
        """
        Decomposes a complex research topic into 2-4 focused search sub-queries.
        """
        clean = " ".join(user_prompt.split()).strip()

        # Deterministic semantic variations
        subqueries = [clean]

        # Add temporal / recent developments query
        subqueries.append(f"{clean} latest analysis OR overview")

        # Add comparison / tradeoffs / empirical evidence query if relevant
        if any(w in clean.lower() for w in ("vs", "compare", "better", "tradeoff", "difference")):
            subqueries.append(f"{clean} performance benchmarks comparison")
        else:
            subqueries.append(f"{clean} architecture key findings")

        return subqueries[:3]

    async def gather_sources(
        self,
        queries: List[str],
        engine_preference: str = "auto",
        client_search_key: str = None,
        max_total_sources: int = 8,
    ) -> List[SearchResultItem]:
        """
        Executes parallel searches across all sub-queries and aggregates deduplicated sources.
        """
        tasks = [
            search_service.execute_search(
                query=q,
                max_results=4,
                engine_preference=engine_preference,
                client_key=client_search_key,
            )
            for q in queries
        ]

        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        seen_urls = set()
        aggregated: List[SearchResultItem] = []

        for res in results_lists:
            if isinstance(res, list):
                for item in res:
                    norm = search_service._normalize_url(item.url)
                    if norm not in seen_urls:
                        seen_urls.add(norm)
                        item.source_id = len(aggregated) + 1
                        aggregated.append(item)
                        if len(aggregated) >= max_total_sources:
                            break
            if len(aggregated) >= max_total_sources:
                break

        return aggregated

    async def extract_deep_contents(self, sources: List[SearchResultItem], max_to_scrape: int = 3) -> None:
        """
        Fetches full-page distilled text for top accessible sources.
        """
        scrape_candidates = sources[:max_to_scrape]

        async def scrape_one(item: SearchResultItem):
            if not item.content or len(item.content) < 300:
                extracted = await scraper.fetch_page_content(item.url, max_chars=4000)
                if extracted:
                    item.content = extracted

        await asyncio.gather(*(scrape_one(item) for item in scrape_candidates), return_exceptions=True)

    def build_research_synthesis_prompt(
        self,
        user_prompt: str,
        sources: List[SearchResultItem],
        queries: List[str],
    ) -> str:
        """
        Constructs a structured prompt instructing the model to synthesize a grounded research report.
        """
        evidence_text = search_service.format_evidence_prompt(sources)

        return f"""You are NEXORA AI's Deep Research Engine. Conduct an exhaustive, objective, source-grounded research synthesis.

USER INQUIRY:
"{user_prompt}"

INVESTIGATION VECTORS CONDUCTED:
{chr(10).join(f"- {q}" for q in queries)}

{evidence_text}

MANDATORY SYNTHESIS DIRECTIVES:
1. Ground every substantive factual claim, statistic, and technical point with numbered inline citations referencing source IDs like [1], [2], [3].
2. Distinguish verified facts from estimates, emerging trends, and areas of debate or conflicting reports.
3. Structure your response clearly using the following markdown format:
   - ## Executive Summary
   - ## In-Depth Analysis & Key Findings (with [X] citations)
   - ## Comparative Tradeoffs & Conflicting Viewpoints
   - ## Evidence Limitations & Gaps
   - ## Conclusion
4. NEVER invent URLs, authors, or statistics not supported by the retrieved web evidence. If evidence is insufficient, explicitly state what remains unanswered.
"""


deep_research_engine = DeepResearchEngine()
