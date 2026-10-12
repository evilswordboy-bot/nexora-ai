from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.v1.health import router as health_router
from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.search import router as search_router
from app.api.v1.documents import router as documents_router
from app.api.v1.factcheck import router as factcheck_router
from app.api.v1.multilingual import router as multilingual_router
from app.api.v1.voice import router as voice_router
from app.api.v1.realtime import router as realtime_router
from app.api.v1.vision import router as vision_router
from app.api.v1.reasoning import router as reasoning_router
from app.api.v1.routing import router as routing_router
from app.api.v1.memory import router as memory_router
from app.api.v1.agents import router as agents_router
from app.api.v1.workflows import router as workflows_router
from app.api.v1.computer import router as computer_router
from app.api.v1.files import router as files_router
from app.api.v1.terminal import router as terminal_router
from app.api.v1.git import router as git_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.discovery import router as discovery_router
from app.api.v1.knowledge_graph import router as knowledge_graph_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="NEXORA AI Universal Assistant Engine",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits local development on any port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": str(exc),
            "detail": "An unexpected error occurred in Nexora AI backend.",
        },
    )


# Include API v1 routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(factcheck_router, prefix="/api/v1")
app.include_router(multilingual_router, prefix="/api/v1")
app.include_router(voice_router, prefix="/api/v1")
app.include_router(realtime_router, prefix="/api/v1")
app.include_router(vision_router, prefix="/api/v1")
app.include_router(reasoning_router, prefix="/api/v1")
app.include_router(routing_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(workflows_router, prefix="/api/v1")
app.include_router(computer_router, prefix="/api/v1")
app.include_router(files_router, prefix="/api/v1")
app.include_router(terminal_router, prefix="/api/v1")
app.include_router(git_router, prefix="/api/v1")
app.include_router(evaluation_router, prefix="/api/v1")
app.include_router(discovery_router, prefix="/api/v1")
app.include_router(knowledge_graph_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "platform": "NEXORA AI",
        "stage": 1,
        "phase": "Foundation & Core UI",
        "status": "online",
        "docs": "/docs",
    }
