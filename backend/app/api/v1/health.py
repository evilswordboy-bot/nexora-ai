from fastapi import APIRouter
from app.config import settings
from app.models.schemas import ProviderStatusResponse, ProviderInfo
from app.services.tools_registry import tool_registry

router = APIRouter(tags=["Health & Status"])


@router.get("/health")
async def health_check():
    configured_providers = settings.get_configured_providers()
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "stage": 14,
        "stage_title": "Multi-Agent Intelligence System",
        "environment": settings.environment,
        "providers_configured": len(configured_providers) > 0,
        "configured_providers": configured_providers,
        "registered_tools_count": len(tool_registry.list_tools()),
        "subsystems": {
            "chat": "operational",
            "search_research": "operational",
            "documents_vault": "operational",
            "fact_checking": "operational",
            "multilingual": "operational",
            "voice": "operational",
            "realtime_feed": "operational",
            "vision_intelligence": "operational",
            "reasoning_engine": "operational",
            "model_routing": "operational",
            "persistent_memory": "operational",
            "multi_agent_system": "operational",
        },
    }


@router.get("/providers/status", response_model=ProviderStatusResponse)
async def provider_status():
    configured_list = settings.get_configured_providers()
    is_configured = len(configured_list) > 0

    providers_info = [
        ProviderInfo(
            name="gemini",
            display_name="Google Gemini",
            configured="gemini" in configured_list,
            models=["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
            description="High-speed multimodal intelligence with large context window.",
        ),
        ProviderInfo(
            name="openai",
            display_name="OpenAI",
            configured="openai" in configured_list,
            models=["gpt-4o", "gpt-4o-mini", "o3-mini"],
            description="Industry standard reasoning and conversational intelligence.",
        ),
        ProviderInfo(
            name="anthropic",
            display_name="Anthropic Claude",
            configured="anthropic" in configured_list,
            models=["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
            description="Nuanced reasoning, safety-focused, superior code generation.",
        ),
    ]

    active_provider = configured_list[0] if is_configured else None
    configured_search_engines = settings.get_configured_search_engines()

    instructions = (
        "Configure your API keys in backend/.env or enter your client API key "
        "in the Frontend Settings modal to enable live generation and search."
    )

    return ProviderStatusResponse(
        configured=is_configured,
        active_provider=active_provider,
        available_providers=providers_info,
        configured_search_engines=configured_search_engines,
        instructions=instructions,
    )
