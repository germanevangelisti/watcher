"""
Watcher Monolith - Backend
-------------------------
FastAPI backend para el sistema Watcher de análisis de boletines oficiales.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.db.database import init_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API para análisis de boletines oficiales",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Inicializa la base de datos al iniciar la aplicación."""
    await init_db()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend Vite default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    """Endpoint de prueba."""
    return {
        "message": f"{settings.PROJECT_NAME} is running",
        "docs_url": "/docs",
        "api_version": settings.API_V1_STR
    }
