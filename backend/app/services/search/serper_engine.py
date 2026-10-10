from typing import List
import httpx
import logging
from app.services.search.base import BaseSearchEngine
from app.models.schemas import SearchResultItem

logger = logging.getLogger("nexora.search.serper")


class SerperSearchEngine(BaseSearchEngine):
    """
    Google Serper API Engine: Real-time Google search results index.
    """

    async def search(self, query: str, max_results: int = 5, api_key: str = "") -> List[SearchResultItem]:
        if not api_key:
            return []

        url = "https://google.serper.dev/search"
        payload = {"q": query, "num": max_results}
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code != 200:
                    logger.error(f"Serper returned status {res.status_code}")
                    return []

                data = res.json()
                results = []
                for item in data.get("organic", [])[:max_results]:
                    target_url = item.get("link", "")
                    if not target_url:
                        continue
                    results.append(
                        SearchResultItem(
                            title=item.get("title", "Untitled Webpage"),
                            url=target_url,
                            snippet=self.clean_text(item.get("snippet", "")),
                            domain=self.extract_domain(target_url),
                            published_date=item.get("date"),
                        )
                    )
                return results
        except Exception as e:
            logger.error(f"Serper search exception: {e}")
            return []
