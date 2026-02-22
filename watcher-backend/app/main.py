"""
Watcher Backend
---------------
FastAPI backend for the Watcher system - official bulletin analysis.
"""

import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.api import api_router
from app.db.database import init_db
from app.core.scheduler import start_scheduler, stop_scheduler, configure_scheduler_from_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("watcher")

# ---------------------------------------------------------------------------
# Google Generative AI — single global configuration
# ---------------------------------------------------------------------------
_google_api_key = settings.GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY")
if _google_api_key:
    try:
        import google.generativeai as genai
        genai.configure(api_key=_google_api_key)
        logger.info("Google Generative AI configured globally (key …%s)", _google_api_key[-4:])
    except ImportError:
        logger.warning("google-generativeai not installed — skipping global configure")
else:
    logger.warning("GOOGLE_API_KEY not set — Google AI features will be unavailable")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API para análisis de boletines oficiales",
    version="1.1.0",
)


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000

    if not request.url.path.startswith("/api/v1/health"):
        logger.info(
            "%s %s -> %s (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
    return response


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Watcher API [env=%s]", settings.ENVIRONMENT)
    await init_db()
    start_scheduler()
    await configure_scheduler_from_db()
    logger.info("Watcher API ready")


@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()
    logger.info("Watcher API stopped")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "message": f"{settings.PROJECT_NAME} is running",
        "docs_url": "/docs",
        "api_version": settings.API_V1_STR,
        "environment": settings.ENVIRONMENT,
    }
