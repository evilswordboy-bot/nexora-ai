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

    # Stage 17: File Management & Workspace Automation Engine
    file_workspace_dir: str = os.getenv(
        "FILE_WORKSPACE_DIR",
        str(Path(__file__).resolve().parent.parent / "data" / "file_workspace"),
    )
    file_workspace_db_path: str = os.getenv(
        "FILE_WORKSPACE_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "file_workspace" / "nexora_files.db"),
    )
    file_workspace_max_file_size_bytes: int = int(
        os.getenv("FILE_WORKSPACE_MAX_FILE_SIZE_BYTES", str(10 * 1024 * 1024))
    )
    file_workspace_max_bulk_files: int = int(os.getenv("FILE_WORKSPACE_MAX_BULK_FILES", "50"))
    file_workspace_bulk_approval_threshold: int = int(
        os.getenv("FILE_WORKSPACE_BULK_APPROVAL_THRESHOLD", "3")
    )
    file_workspace_max_versions_per_file: int = int(
        os.getenv("FILE_WORKSPACE_MAX_VERSIONS_PER_FILE", "10")
    )

    # Stage 18: Terminal & Code Execution Engine
    terminal_workspace_dir: str = os.getenv(
        "TERMINAL_WORKSPACE_DIR",
        str(Path(__file__).resolve().parent.parent / "data" / "terminal_workspace"),
    )
    terminal_db_path: str = os.getenv(
        "TERMINAL_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "terminal_workspace" / "nexora_terminal.db"),
    )
    terminal_execution_timeout_seconds: float = float(
        os.getenv("TERMINAL_EXECUTION_TIMEOUT_SECONDS", "5.0")
    )
    terminal_max_output_bytes: int = int(
        os.getenv("TERMINAL_MAX_OUTPUT_BYTES", str(64 * 1024))
    )
    terminal_max_memory_mb: int = int(os.getenv("TERMINAL_MAX_MEMORY_MB", "128"))
    terminal_max_processes: int = int(os.getenv("TERMINAL_MAX_PROCESSES", "4"))
    terminal_max_concurrent_runs_per_user: int = int(
        os.getenv("TERMINAL_MAX_CONCURRENT_RUNS_PER_USER", "3")
    )
    terminal_max_repair_attempts: int = int(
        os.getenv("TERMINAL_MAX_REPAIR_ATTEMPTS", "3")
    )
    terminal_default_allow_network: bool = os.getenv(
        "TERMINAL_DEFAULT_ALLOW_NETWORK", "false"
    ).lower() in ("true", "1", "yes")

    # Stage 19: Git & Version Control Engine
    git_db_path: str = os.getenv(
        "GIT_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "terminal_workspace" / "nexora_git.db"),
    )
    git_default_author_name: str = os.getenv("GIT_DEFAULT_AUTHOR_NAME", "Nexora Developer")
    git_default_author_email: str = os.getenv("GIT_DEFAULT_AUTHOR_EMAIL", "developer@nexora.local")
    git_default_branch: str = os.getenv("GIT_DEFAULT_BRANCH", "main")
    git_command_timeout_seconds: float = float(
        os.getenv("GIT_COMMAND_TIMEOUT_SECONDS", "10.0")
    )
    git_provider_token: str = os.getenv("GIT_PROVIDER_TOKEN", "")
    git_allowed_remote_hosts: list[str] = [
        h.strip().lower()
        for h in os.getenv(
            "GIT_ALLOWED_REMOTE_HOSTS",
            "github.com,gitlab.com,bitbucket.org,codeberg.org",
        ).split(",")
        if h.strip()
    ]

    # Stage 20: AI Evaluation & Quality Assurance Engine
    eval_workspace_dir: str = os.getenv(
        "EVAL_WORKSPACE_DIR",
        str(Path(__file__).resolve().parent.parent / "data" / "evaluation"),
    )
    eval_db_path: str = os.getenv(
        "EVAL_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "evaluation" / "nexora_eval.db"),
    )
    eval_min_task_success_rate: float = float(
        os.getenv("EVAL_MIN_TASK_SUCCESS_RATE", "0.85")
    )
    eval_min_safety_compliance_rate: float = float(
        os.getenv("EVAL_MIN_SAFETY_COMPLIANCE_RATE", "1.0")
    )
    eval_max_error_rate: float = float(
        os.getenv("EVAL_MAX_ERROR_RATE", "0.10")
    )
    eval_max_latency_regression_pct: float = float(
        os.getenv("EVAL_MAX_LATENCY_REGRESSION_PCT", "50.0")
    )
    eval_block_on_critical_failure: bool = os.getenv(
        "EVAL_BLOCK_ON_CRITICAL_FAILURE", "true"
    ).lower() in ("true", "1", "yes")
    eval_exclude_private_conversations: bool = os.getenv(
        "EVAL_EXCLUDE_PRIVATE_CONVERSATIONS", "true"
    ).lower() in ("true", "1", "yes")

    # Stage 21: Universal Knowledge Discovery Engine
    discovery_cache_ttl_seconds: float = float(
        os.getenv("DISCOVERY_CACHE_TTL_SECONDS", "300.0")
    )
    discovery_connector_timeout_seconds: float = float(
        os.getenv("DISCOVERY_CONNECTOR_TIMEOUT_SECONDS", "8.0")
    )
    discovery_max_parallel_connectors: int = int(
        os.getenv("DISCOVERY_MAX_PARALLEL_CONNECTORS", "4")
    )
    discovery_default_page_size: int = int(
        os.getenv("DISCOVERY_DEFAULT_PAGE_SIZE", "10")
    )
    discovery_max_page_size: int = int(
        os.getenv("DISCOVERY_MAX_PAGE_SIZE", "30")
    )
    discovery_stale_days_threshold: int = int(
        os.getenv("DISCOVERY_STALE_DAYS_THRESHOLD", "730")
    )
    discovery_enable_live_academic_api: bool = os.getenv(
        "DISCOVERY_ENABLE_LIVE_ACADEMIC_API", "true"
    ).lower() in ("true", "1", "yes")

    # Stage 22: Knowledge Graph Intelligence Engine
    kg_db_path: str = os.getenv(
        "KG_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "knowledge_graph" / "nexora_knowledge_graph.db"),
    )
    kg_max_expansion_depth: int = int(
        os.getenv("KG_MAX_EXPANSION_DEPTH", "6")
    )
    kg_default_page_size: int = int(
        os.getenv("KG_DEFAULT_PAGE_SIZE", "50")
    )
    kg_max_page_size: int = int(
        os.getenv("KG_MAX_PAGE_SIZE", "200")
    )
    kg_enable_ai_inferred_edges: bool = os.getenv(
        "KG_ENABLE_AI_INFERRED_EDGES", "true"
    ).lower() in ("true", "1", "yes")

    # Stage 23: IoT Project Builder Engine
    iot_db_path: str = os.getenv(
        "IOT_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "iot_projects" / "nexora_iot.db"),
    )
    iot_exports_dir: str = os.getenv(
        "IOT_EXPORTS_DIR",
        str(Path(__file__).resolve().parent.parent / "data" / "iot_projects" / "exports"),
    )
    iot_default_simulation_ticks: int = int(
        os.getenv("IOT_DEFAULT_SIMULATION_TICKS", "8")
    )
    iot_max_simulation_ticks: int = int(
        os.getenv("IOT_MAX_SIMULATION_TICKS", "32")
    )
    iot_enable_toolchain_probing: bool = os.getenv(
        "IOT_ENABLE_TOOLCHAIN_PROBING", "true"
    ).lower() in ("true", "1", "yes")

    # Stage 24: Embedded Firmware Engineering Studio
    firmware_db_path: str = os.getenv(
        "FIRMWARE_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "firmware_studio" / "nexora_firmware.db"),
    )
    firmware_builds_dir: str = os.getenv(
        "FIRMWARE_BUILDS_DIR",
        str(Path(__file__).resolve().parent.parent / "data" / "firmware_studio" / "builds"),
    )
    firmware_compile_timeout_seconds: float = float(
        os.getenv("FIRMWARE_COMPILE_TIMEOUT_SECONDS", "15.0")
    )
    firmware_max_file_size_bytes: int = int(
        os.getenv("FIRMWARE_MAX_FILE_SIZE_BYTES", "262144")
    )
    firmware_default_baud_rate: int = int(
        os.getenv("FIRMWARE_DEFAULT_BAUD_RATE", "115200")
    )

    # Stage 25: IoT Device Connectivity & Live Telemetry
    telemetry_db_path: str = os.getenv(
        "TELEMETRY_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "telemetry" / "nexora_telemetry.db"),
    )
    telemetry_exports_dir: str = os.getenv(
        "TELEMETRY_EXPORTS_DIR",
        str(Path(__file__).resolve().parent.parent / "data" / "telemetry" / "exports"),
    )
    telemetry_rate_limit_per_minute: int = int(
        os.getenv("TELEMETRY_RATE_LIMIT_PER_MINUTE", "60")
    )
    telemetry_max_payload_size_bytes: int = int(
        os.getenv("TELEMETRY_MAX_PAYLOAD_SIZE_BYTES", "65536")
    )
    telemetry_max_events_per_device: int = int(
        os.getenv("TELEMETRY_MAX_EVENTS_PER_DEVICE", "2000")
    )
    telemetry_offline_timeout_seconds: float = float(
        os.getenv("TELEMETRY_OFFLINE_TIMEOUT_SECONDS", "90.0")
    )
    telemetry_default_cooldown_seconds: int = int(
        os.getenv("TELEMETRY_DEFAULT_COOLDOWN_SECONDS", "300")
    )
    mqtt_broker_host: str = os.getenv("MQTT_BROKER_HOST", "mqtt.nexora.local")
    mqtt_broker_port: int = int(os.getenv("MQTT_BROKER_PORT", "8883"))
    mqtt_use_tls: bool = os.getenv("MQTT_USE_TLS", "true").lower() in ("true", "1", "yes")

    # Stage 26: IoT Security & Device Threat Detection
    iot_security_db_path: str = os.getenv(
        "IOT_SECURITY_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "iot_security" / "nexora_iot_security.db"),
    )
    iot_security_baseline_window_events: int = int(
        os.getenv("IOT_SECURITY_BASELINE_WINDOW_EVENTS", "100")
    )
    iot_security_auth_failure_threshold: int = int(
        os.getenv("IOT_SECURITY_AUTH_FAILURE_THRESHOLD", "5")
    )
    iot_security_zscore_threshold: float = float(
        os.getenv("IOT_SECURITY_ZSCORE_THRESHOLD", "3.0")
    )
    iot_security_rate_spike_multiplier: float = float(
        os.getenv("IOT_SECURITY_RATE_SPIKE_MULTIPLIER", "3.0")
    )
    iot_security_max_incidents_retained: int = int(
        os.getenv("IOT_SECURITY_MAX_INCIDENTS_RETAINED", "1000")
    )
    iot_security_network_adapter_configured: bool = os.getenv(
        "IOT_SECURITY_NETWORK_ADAPTER_CONFIGURED", "false"
    ).lower() in ("true", "1", "yes")

    # Stage 27: Electronic Circuit Schematic Design Studio
    schematic_db_path: str = os.getenv(
        "SCHEMATIC_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "schematics" / "nexora_schematics.db"),
    )
    schematic_exports_dir: str = os.getenv(
        "SCHEMATIC_EXPORTS_DIR",
        str(Path(__file__).resolve().parent.parent / "data" / "schematics" / "exports"),
    )
    schematic_max_components_per_sheet: int = int(
        os.getenv("SCHEMATIC_MAX_COMPONENTS_PER_SHEET", "200")
    )
    schematic_max_nets_per_sheet: int = int(
        os.getenv("SCHEMATIC_MAX_NETS_PER_SHEET", "300")
    )
    schematic_spice_simulation_timeout_seconds: float = float(
        os.getenv("SCHEMATIC_SPICE_SIMULATION_TIMEOUT_SECONDS", "10.0")
    )
    schematic_enable_analytical_solver: bool = os.getenv(
        "SCHEMATIC_ENABLE_ANALYTICAL_SOLVER", "true"
    ).lower() in ("true", "1", "yes")

    # Stage 28: PCB Layout & Design Studio
    pcb_db_path: str = os.getenv(
        "PCB_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "pcb" / "nexora_pcb.db"),
    )
    pcb_exports_dir: str = os.getenv(
        "PCB_EXPORTS_DIR",
        str(Path(__file__).resolve().parent.parent / "data" / "pcb" / "exports"),
    )
    pcb_default_board_width_mm: float = float(os.getenv("PCB_DEFAULT_BOARD_WIDTH_MM", "100.0"))
    pcb_default_board_height_mm: float = float(os.getenv("PCB_DEFAULT_BOARD_HEIGHT_MM", "80.0"))
    pcb_default_layer_count: int = int(os.getenv("PCB_DEFAULT_LAYER_COUNT", "2"))
    pcb_default_copper_thickness_oz: float = float(os.getenv("PCB_DEFAULT_COPPER_THICKNESS_OZ", "1.0"))
    pcb_min_trace_width_mm: float = float(os.getenv("PCB_MIN_TRACE_WIDTH_MM", "0.25"))
    pcb_min_clearance_mm: float = float(os.getenv("PCB_MIN_CLEARANCE_MM", "0.20"))
    pcb_min_board_edge_clearance_mm: float = float(os.getenv("PCB_MIN_BOARD_EDGE_CLEARANCE_MM", "0.50"))
    pcb_min_drill_diameter_mm: float = float(os.getenv("PCB_MIN_DRILL_DIAMETER_MM", "0.30"))

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
