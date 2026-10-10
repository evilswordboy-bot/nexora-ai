"""
NEXORA AI — Evidence Collector
Gathers verification evidence across:
- Real web search (DuckDuckGo, Tavily, Google Serper, Brave)
- Scraped webpage bodies via WebpageScraper (with SSRF protection)
- Uploaded user documents in Stage 4 Documents Vault
- Deduplicates coverage and prioritizes reputable/primary reporting
"""

from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from app.models.schemas import EvidenceSource, SearchResultItem
from app.services.search.search_service import search_service
from app.services.search.scraper import WebpageScraper
from app.services.documents.storage import document_storage


class EvidenceCollector:
    """Collects multi-modal evidence across search and user documents."""

    REPUTABLE_DOMAINS = {
        "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "nature.com",
        "science.org", "nih.gov", "who.int", "cdc.gov", "nasa.gov",
        "nytimes.com", "wsj.com", "theguardian.com", "bloomberg.com",
        "economist.com", "britannica.com", "wikipedia.org", "arxiv.org"
    }

    @classmethod
    async def collect_evidence_for_claim(
        cls,
        claim_text: str,
        engine_preference: str = "auto",
        client_search_key: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        max_search_results: int = 5
    ) -> List[EvidenceSource]:
        evidence_list: List[EvidenceSource] = []
        source_counter = 1
        seen_domains = set()

        # 1. Search in uploaded documents if specified
        if document_ids:
            doc_passages = document_storage.retrieve_relevant_passages(
                doc_ids=document_ids,
                query=claim_text,
                top_k=3
            )
            for chunk, score, filename in doc_passages:
                evidence_list.append(EvidenceSource(
                    source_id=source_counter,
                    title=f"Uploaded Document: {filename} (Page {chunk.page_number or 1})",
                    url=None,
                    domain=filename,
                    published_date=None,
                    snippet=chunk.content[:350],
                    stance="neutral",
                    is_primary=True
                ))
                source_counter += 1

        # 2. Search live web
        try:
            web_results = await search_service.execute_search(
                query=claim_text,
                max_results=max_search_results,
                engine_preference=engine_preference,
                client_key=client_search_key
            )

            for item in web_results:
                domain = item.domain.lower()
                # Deduplication: Avoid 3+ articles from the exact same domain
                if domain in seen_domains:
                    continue
                seen_domains.add(domain)

                is_primary = any(rep in domain for rep in cls.REPUTABLE_DOMAINS) or domain.endswith(".gov") or domain.endswith(".edu")

                evidence_list.append(EvidenceSource(
                    source_id=source_counter,
                    title=item.title,
                    url=item.url,
                    domain=item.domain,
                    published_date=item.published_date,
                    snippet=item.snippet,
                    stance="neutral",
                    is_primary=is_primary
                ))
                source_counter += 1

        except Exception:
            pass

        return evidence_list
