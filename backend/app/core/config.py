from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "VisaCanada"
    app_env: str = "development"
    debug: bool = True

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Security
    secret_key: str = "change-me-in-production"
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

    # Twilio WhatsApp
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
