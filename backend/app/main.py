from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.candidates import router as candidates_router
from app.api.dossiers import router as dossiers_router
from app.api.documents import router as documents_router
from app.api.programs import router as programs_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description="AI-powered immigration management platform for Canada",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(candidates_router)
app.include_router(dossiers_router)
app.include_router(documents_router)
app.include_router(programs_router)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name} API"}
