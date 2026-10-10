from typing import List
import httpx
import logging
from app.services.search.base import BaseSearchEngine
from app.models.schemas import SearchResultItem

logger = logging.getLogger("nexora.search.brave")


class BraveSearchEngine(BaseSearchEngine):
    """
    Brave Search API Engine: Independent global web search index.
    """

    async def search(self, query: str, max_results: int = 5, api_key: str = "") -> List[SearchResultItem]:
        if not api_key:
            return []

        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
        }
        params = {"q": query, "count": max_results}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, headers=headers, params=params)
                if res.status_code != 200:
                    logger.error(f"Brave returned status {res.status_code}")
                    return []

                data = res.json()
                results = []
                for item in data.get("web", {}).get("results", [])[:max_results]:
                    target_url = item.get("url", "")
                    if not target_url:
                        continue
                    results.append(
                        SearchResultItem(
                            title=item.get("title", "Untitled Webpage"),
                            url=target_url,
                            snippet=self.clean_text(item.get("description", "")),
                            domain=self.extract_domain(target_url),
                            published_date=item.get("page_age"),
                        )
                    )
                return results
        except Exception as e:
            logger.error(f"Brave search exception: {e}")
            return []
