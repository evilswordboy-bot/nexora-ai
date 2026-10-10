from typing import List
import httpx
import logging
from app.services.search.base import BaseSearchEngine
from app.models.schemas import SearchResultItem

logger = logging.getLogger("nexora.search.tavily")


class TavilySearchEngine(BaseSearchEngine):
    """
    Tavily Search API Engine: Purpose-built for AI agents with factual groundings.
    """

    async def search(self, query: str, max_results: int = 5, api_key: str = "") -> List[SearchResultItem]:
        if not api_key:
            return []

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "include_answer": False,
            "max_results": max_results,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    logger.error(f"Tavily returned status {res.status_code}: {res.text}")
                    return []

                data = res.json()
                results = []
                for item in data.get("results", []):
                    target_url = item.get("url", "")
                    if not target_url:
                        continue
                    results.append(
                        SearchResultItem(
                            title=item.get("title", "Untitled Webpage"),
                            url=target_url,
                            snippet=self.clean_text(item.get("content", "")),
                            domain=self.extract_domain(target_url),
                            published_date=item.get("published_date"),
                            content=item.get("raw_content") or item.get("content"),
                        )
                    )
                return results
        except Exception as e:
            logger.error(f"Tavily search exception: {e}")
            return []
