from typing import List
import httpx
from bs4 import BeautifulSoup
import logging
from app.services.search.base import BaseSearchEngine
from app.models.schemas import SearchResultItem

logger = logging.getLogger("nexora.search.ddg")


class DuckDuckGoSearchEngine(BaseSearchEngine):
    """
    DuckDuckGo Search Engine:
    Zero-configuration engine. Uses ddgs library with direct HTML fallback.
    """

    async def search(self, query: str, max_results: int = 5, api_key: str = "") -> List[SearchResultItem]:
        # 1. Try ddgs library first
        try:
            from ddgs import DDGS
            ddgs_client = DDGS()
            raw_results = ddgs_client.text(query, max_results=max_results)
            results = []
            for item in raw_results:
                url = item.get("href") or item.get("url", "")
                if not url:
                    continue
                results.append(
                    SearchResultItem(
                        title=item.get("title", "Untitled Webpage"),
                        url=url,
                        snippet=self.clean_text(item.get("body", "")),
                        domain=self.extract_domain(url),
                    )
                )
            if results:
                return results[:max_results]
        except Exception as e:
            logger.debug(f"DDGS library query failed, falling back to HTML endpoint: {e}")

        # 2. Resilient HTML fallback endpoint
        try:
            url = "https://html.duckduckgo.com/html/"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
            }
            data = {"q": query, "b": ""}

            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                res = await client.post(url, data=data, headers=headers)
                if res.status_code != 200:
                    return []

                soup = BeautifulSoup(res.text, "html.parser")
                results = []
                for result in soup.find_all("div", class_="result")[:max_results]:
                    title_elem = result.find("a", class_="result__snippet") or result.find("a", class_="result__url")
                    link_elem = result.find("a", class_="result__url")
                    snippet_elem = result.find("a", class_="result__snippet")

                    if link_elem:
                        href = link_elem.get("href", "")
                        # DuckDuckGo redirect link cleanup: //duckduckgo.com/l/?uddg=...
                        if "uddg=" in href:
                            import urllib.parse
                            parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                            actual_url = parsed_qs.get("uddg", [href])[0]
                        else:
                            actual_url = href

                        if not actual_url.startswith("http"):
                            continue

                        title = link_elem.get_text(strip=True) if link_elem else "Web Result"
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                        results.append(
                            SearchResultItem(
                                title=title,
                                url=actual_url,
                                snippet=self.clean_text(snippet),
                                domain=self.extract_domain(actual_url),
                            )
                        )
                return results[:max_results]
        except Exception as e:
            logger.error(f"DuckDuckGo fallback search failed: {e}")
            return []
