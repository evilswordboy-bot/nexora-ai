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

    # Stage 4: Document Intelligence & Knowledge Engine
    document_storage_dir: str = os.getenv("DOCUMENT_STORAGE_DIR", str(Path(__file__).resolve().parent.parent / "data" / "documents"))
    max_upload_size_bytes: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(25 * 1024 * 1024))) # 25MB max
    chunk_size_tokens: int = int(os.getenv("CHUNK_SIZE_TOKENS", "500"))
    chunk_overlap_tokens: int = int(os.getenv("CHUNK_OVERLAP_TOKENS", "50"))
    top_k_chunks: int = int(os.getenv("TOP_K_CHUNKS", "5"))
    tesseract_cmd: str = os.getenv("TESSERACT_CMD", "")

    # Security & Rate Limiting
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    enable_safety_guardrails: bool = os.getenv("ENABLE_SAFETY_GUARDRAILS", "true").lower() in ("true", "1", "yes")

    # Stage 12: Intelligent Model Routing & Cost Controls
    default_routing_mode: str = os.getenv("DEFAULT_ROUTING_MODE", "balanced")  # quality_first | balanced | speed_first
    max_routing_fallbacks: int = int(os.getenv("MAX_ROUTING_FALLBACKS", "2"))
    daily_spending_limit_usd: float = float(os.getenv("DAILY_SPENDING_LIMIT_USD", "10.0"))
    per_request_max_cost_usd: float = float(os.getenv("PER_REQUEST_MAX_COST_USD", "0.50"))
    routing_timeout_seconds: float = float(os.getenv("ROUTING_TIMEOUT_SECONDS", "30.0"))

    # Stage 13: Persistent Memory Engine
    memory_db_path: str = os.getenv(
        "MEMORY_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "memory" / "nexora_memory.db"),
    )
    memory_enabled_by_default: bool = os.getenv("MEMORY_ENABLED_BY_DEFAULT", "true").lower() in ("true", "1", "yes")
    memory_encryption_secret: str = os.getenv("MEMORY_ENCRYPTION_SECRET", "nexora-stage13-local-at-rest-secret")
    max_memories_per_user: int = int(os.getenv("MAX_MEMORIES_PER_USER", "500"))
    top_k_memories: int = int(os.getenv("TOP_K_MEMORIES", "5"))

    # Stage 14: Multi-Agent Intelligence System
    agent_max_steps_per_task: int = int(os.getenv("AGENT_MAX_STEPS_PER_TASK", "6"))
    agent_max_parallel_tasks: int = int(os.getenv("AGENT_MAX_PARALLEL_TASKS", "3"))
    agent_task_timeout_seconds: float = float(os.getenv("AGENT_TASK_TIMEOUT_SECONDS", "25.0"))
    agent_max_cost_usd_per_run: float = float(os.getenv("AGENT_MAX_COST_USD_PER_RUN", "0.25"))

    # Stage 15: Workflow Automation Engine
    workflow_db_path: str = os.getenv(
        "WORKFLOW_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "workflows" / "nexora_workflows.db"),
    )
    workflow_max_steps: int = int(os.getenv("WORKFLOW_MAX_STEPS", "15"))
    workflow_max_step_retries: int = int(os.getenv("WORKFLOW_MAX_STEP_RETRIES", "3"))
    workflow_step_timeout_seconds: float = float(os.getenv("WORKFLOW_STEP_TIMEOUT_SECONDS", "30.0"))
    workflow_max_cost_usd_per_run: float = float(os.getenv("WORKFLOW_MAX_COST_USD_PER_RUN", "0.50"))
    workflow_rate_limit_per_minute: int = int(os.getenv("WORKFLOW_RATE_LIMIT_PER_MINUTE", "20"))
    workflow_scheduler_poll_seconds: float = float(os.getenv("WORKFLOW_SCHEDULER_POLL_SECONDS", "15.0"))
    notification_webhook_url: str = os.getenv("NOTIFICATION_WEBHOOK_URL", "")
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from_email: str = os.getenv("SMTP_FROM_EMAIL", "")

    # Stage 16: Computer Control & Digital Execution Engine
    computer_workspace_dir: str = os.getenv(
        "COMPUTER_WORKSPACE_DIR",
        str(Path(__file__).resolve().parent.parent / "data" / "computer_workspace"),
    )
    computer_db_path: str = os.getenv(
        "COMPUTER_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "computer_workspace" / "nexora_computer.db"),
    )
    computer_max_steps_per_task: int = int(os.getenv("COMPUTER_MAX_STEPS_PER_TASK", "12"))
    computer_step_timeout_seconds: float = float(os.getenv("COMPUTER_STEP_TIMEOUT_SECONDS", "20.0"))
    computer_enable_local_os_runner: bool = os.getenv("COMPUTER_ENABLE_LOCAL_OS_RUNNER", "true").lower() in ("true", "1", "yes")
    computer_strict_url_allowlist: bool = os.getenv("COMPUTER_STRICT_URL_ALLOWLIST", "false").lower() in ("true", "1", "yes")
    computer_allowed_domains: list[str] = [
        d.strip().lower()
        for d in os.getenv(
            "COMPUTER_ALLOWED_DOMAINS",
            "example.com,wikipedia.org,en.wikipedia.org,github.com,python.org,fastapi.tiangolo.com,developer.mozilla.org,news.ycombinator.com",
        ).split(",")
        if d.strip()
    ]

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
# Ensure document storage directory exists
Path(settings.document_storage_dir).mkdir(parents=True, exist_ok=True)
