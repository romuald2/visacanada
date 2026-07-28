from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.candidates import router as candidates_router
from app.api.dossiers import router as dossiers_router
from app.api.documents import router as documents_router
from app.api.programs import router as programs_router
from app.api.ircc import router as ircc_router
from app.api.upload import router as upload_router
from app.api.extraction import router as extraction_router
from app.api.compliance import router as compliance_router
from app.api.fraud import router as fraud_router
from app.api.ircc_profile import router as ircc_profile_router
from app.api.email import router as email_router
from app.api.notifications import router as notifications_router
from app.api.dashboard import router as dashboard_router
from app.api.crs import router as crs_router
from app.api.letters import router as letters_router
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
app.include_router(ircc_router)
app.include_router(upload_router)
app.include_router(extraction_router)
app.include_router(compliance_router)
app.include_router(fraud_router)
app.include_router(ircc_profile_router)
app.include_router(email_router)
app.include_router(notifications_router)
app.include_router(dashboard_router)
app.include_router(crs_router)
app.include_router(letters_router)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name} API"}
