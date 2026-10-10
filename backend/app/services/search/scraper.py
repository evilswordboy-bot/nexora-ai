import ipaddress
import socket
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
import logging

from app.config import settings

logger = logging.getLogger("nexora.scraper")


class WebpageScraper:
    """
    Secure Webpage Scraper for NEXORA AI Deep Research.
    Guards against SSRF, limits payload sizes, and sanitizes untrusted HTML.
    """

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 NexoraBot/3.0"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    @staticmethod
    def is_safe_url(url: str) -> bool:
        """
        SSRF Protection: Rejects private, loopback, multicast, or metadata endpoints.
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False

            hostname = parsed.hostname
            if not hostname:
                return False

            hostname = hostname.lower()
            if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
                return False

            # Check if hostname resolves to private IP range
            try:
                ip_str = socket.gethostbyname(hostname)
                ip_obj = ipaddress.ip_address(ip_str)
                if (
                    ip_obj.is_private
                    or ip_obj.is_loopback
                    or ip_obj.is_link_local
                    or ip_obj.is_multicast
                    or ip_obj.is_reserved
                ):
                    return False
            except Exception:
                # If DNS resolution fails, reject for safety
                return False

            return True
        except Exception:
            return False

    async def fetch_page_content(self, url: str, max_chars: int = 5000) -> str:
        """
        Fetches webpage and returns distilled plain text.
        """
        if not self.is_safe_url(url):
            logger.warning(f"Blocked unsafe or private URL attempt: {url}")
            return ""

        try:
            async with httpx.AsyncClient(
                timeout=settings.scraper_timeout_seconds,
                follow_redirects=True,
                headers=self.HEADERS,
            ) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return ""

                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type and "text/plain" not in content_type:
                    return ""

                html = response.text
                soup = BeautifulSoup(html, "html.parser")

                # Remove non-content elements
                for element in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "svg"]):
                    element.decompose()

                # Extract text
                text = soup.get_text(separator=" ", strip=True)
                cleaned = " ".join(text.split())

                return cleaned[:max_chars]
        except Exception as e:
            logger.debug(f"Failed to fetch webpage content for {url}: {e}")
            return ""


scraper = WebpageScraper()
