from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.alerts import router as alerts_router
from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.candidates import router as candidates_router
from app.api.compliance import router as compliance_router
from app.api.complaint import router as complaint_router
from app.api.crs import router as crs_router
from app.api.dashboard import router as dashboard_router
from app.api.deadlines import router as deadlines_router
from app.api.documents import router as documents_router
from app.api.dossiers import router as dossiers_router
from app.api.email import router as email_router
from app.api.export import router as export_router
from app.api.extraction import router as extraction_router
from app.api.family import router as family_router
from app.api.fraud import router as fraud_router
from app.api.health import router as health_router
from app.api.ircc import router as ircc_router
from app.api.ircc_profile import router as ircc_profile_router
from app.api.knowledge import router as knowledge_router
from app.api.letters import router as letters_router
from app.api.mfa import router as mfa_router
from app.api.notifications import router as notifications_router
from app.api.portal import router as portal_router
from app.api.privacy import router as privacy_router
from app.api.programs import router as programs_router
from app.api.upload import router as upload_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description="AI-powered immigration management platform for Canada",
    version="0.1.0",
    # Interactive docs are disabled in production to avoid exposing the schema.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# CORS: explicit allowlist of origins, methods and headers. Credentials are
# enabled, so the origin must never be a wildcard (enforced in config for prod).
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
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
app.include_router(mfa_router)
app.include_router(portal_router)
app.include_router(alerts_router)
app.include_router(deadlines_router)
app.include_router(analytics_router)
app.include_router(family_router)
app.include_router(billing_router)
app.include_router(knowledge_router)
app.include_router(privacy_router)
app.include_router(complaint_router)
app.include_router(export_router)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name} API"}
