from abc import ABC, abstractmethod
from typing import List, Optional
from urllib.parse import urlparse
from app.models.schemas import SearchResultItem


class BaseSearchEngine(ABC):
    """
    Abstract Base Class for Web Search Engines.
    Enforces real web retrieval with zero simulation.
    """

    @abstractmethod
    async def search(self, query: str, max_results: int = 5, api_key: str = "") -> List[SearchResultItem]:
        """Perform search query and return list of SearchResultItem."""
        pass

    @staticmethod
    def extract_domain(url: str) -> str:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain or "web"
        except Exception:
            return "web"

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        return " ".join(text.split()).strip()
