import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env if present
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseModel):
    app_name: str = "NEXORA AI Engine"
    app_version: str = "3.0.0-stage3"
    environment: str = os.getenv("ENVIRONMENT", "development")
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]

    # AI Provider API keys
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Search Provider API keys
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    serper_api_key: str = os.getenv("SERPER_API_KEY", "")
    brave_api_key: str = os.getenv("BRAVE_API_KEY", "")

    # Default Active Settings
    default_provider: str = os.getenv("DEFAULT_PROVIDER", "auto")
    default_model: str = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
    default_search_engine: str = os.getenv("DEFAULT_SEARCH_ENGINE", "auto")

    # Conversation Context & Message Limits
    max_context_messages: int = int(os.getenv("MAX_CONTEXT_MESSAGES", "20"))
    max_message_chars: int = int(os.getenv("MAX_MESSAGE_CHARS", "32000"))
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "45.0"))

    # Stage 3: Universal Search & Research Configuration
    max_search_results: int = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
    max_research_sources: int = int(os.getenv("MAX_RESEARCH_SOURCES", "8"))
    scraper_timeout_seconds: float = float(os.getenv("SCRAPER_TIMEOUT_SECONDS", "10.0"))

    # Security & Rate Limiting
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    enable_safety_guardrails: bool = os.getenv("ENABLE_SAFETY_GUARDRAILS", "true").lower() in ("true", "1", "yes")

    def get_configured_providers(self) -> list[str]:
        configured = []
        if self.gemini_api_key and self.gemini_api_key.strip():
            configured.append("gemini")
        if self.openai_api_key and self.openai_api_key.strip():
            configured.append("openai")
        if self.anthropic_api_key and self.anthropic_api_key.strip():
            configured.append("anthropic")
        return configured

    def get_configured_search_engines(self) -> list[str]:
        configured = []
        if self.tavily_api_key and self.tavily_api_key.strip():
            configured.append("tavily")
        if self.serper_api_key and self.serper_api_key.strip():
            configured.append("serper")
        if self.brave_api_key and self.brave_api_key.strip():
            configured.append("brave")
        # DuckDuckGo is always available as zero-config engine
        configured.append("duckduckgo")
        return configured


settings = Settings()
