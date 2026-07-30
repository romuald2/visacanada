from pydantic import model_validator
from pydantic_settings import BaseSettings

# Sentinel default for the JWT signing key. This value is intentionally
# insecure and is rejected at startup in production (see _validate_security).
_INSECURE_SECRET_DEFAULT = "change-me-in-production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "VisaCanada"
    app_env: str = "development"
    debug: bool = False

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Security
    # Must be overridden via the SECRET_KEY env var. In production the app
    # refuses to boot with the insecure default or a too-short key.
    secret_key: str = _INSECURE_SECRET_DEFAULT
    cors_origins: str = "http://localhost:3000"

    # JWT
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database
    database_url: str = (
        "postgresql+asyncpg://visacanada:visacanada_dev_password@localhost:5432/visacanada"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ca-central-1"
    s3_bucket_name: str = "visacanada-documents"

    # Azure Document Intelligence
    azure_doc_intel_endpoint: str = ""
    azure_doc_intel_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Embeddings (Voyage AI) - optional; falls back to deterministic local embedding
    voyage_api_key: str = ""
    embedding_model: str = "voyage-3"
    embedding_dim: int = 256

    # Google OAuth2 (Gmail)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/email/callback/gmail"

    # Microsoft OAuth2 (Outlook)
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_redirect_uri: str = "http://localhost:8000/email/callback/outlook"

    # Outbound SMTP (alert and invoice-reminder delivery). Empty host disables
    # sending: the app degrades to dashboard-only notifications.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    smtp_timeout_seconds: int = 10

    # Twilio WhatsApp
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_currency: str = "cad"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in ("production", "prod")

    @model_validator(mode="after")
    def _validate_security(self) -> "Settings":
        """Fail fast on insecure security configuration in production."""
        if self.is_production:
            if self.secret_key == _INSECURE_SECRET_DEFAULT:
                raise ValueError(
                    "SECRET_KEY must be set to a strong secret in production "
                    "(the default 'change-me-in-production' is not allowed)."
                )
            if len(self.secret_key) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters in production."
                )
            if "*" in self.cors_origins:
                raise ValueError(
                    "CORS origins cannot contain '*' with credentials enabled "
                    "in production; set an explicit allowlist."
                )
            if self.debug:
                raise ValueError("debug must be disabled in production.")
        return self


settings = Settings()
