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


@app.get("/")
async def root():
    return {
        "platform": "NEXORA AI",
        "stage": 1,
        "phase": "Foundation & Core UI",
        "status": "online",
        "docs": "/docs",
    }
