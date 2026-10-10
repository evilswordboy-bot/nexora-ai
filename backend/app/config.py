import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env if present
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseModel):
    app_name: str = "NEXORA AI Engine"
    app_version: str = "1.0.0-stage1"
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

    # Provider API keys (loaded strictly from environment or backend config)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    default_provider: str = os.getenv("DEFAULT_PROVIDER", "unconfigured")
    default_model: str = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")

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


settings = Settings()
