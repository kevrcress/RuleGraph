"""
Application configuration using Pydantic Settings.
Validates all required environment variables at startup.
Exits with a clear error message if any required variable is missing.
"""
import sys
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    # Database
    database_url: str = Field(..., description="PostgreSQL async connection URL (postgresql+asyncpg://...)")

    # Redis
    redis_url: str = Field(..., description="Redis connection URL (redis://...)")

    # LLM — optional at startup; can be set via Admin → Settings instead
    anthropic_api_key: str = Field(default="", description="Anthropic API key (can be set via admin UI instead)")

    # Security
    jwt_secret_key: str = Field(..., description="Secret key for JWT token signing")
    rulegraph_encryption_key: str = Field(..., description="Encryption key for PAT storage")
    webhook_test_secret: str = Field(default="test-webhook-secret", description="Shared secret for HMAC webhook validation")

    # Application
    app_title: str = "RuleGraph"
    app_version: str = "0.1.0"

    # LLM model routing
    simple_model: str = "claude-haiku-4-5"
    complex_model: str = "claude-sonnet-4-5"
    complexity_threshold: float = 0.5

    # Pagination
    default_page_limit: int = 50
    max_page_limit: int = 200

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL must not be empty")
        # Ensure we use asyncpg driver
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        if not v:
            raise ValueError("REDIS_URL must not be empty")
        return v


def _load_settings() -> Settings:
    try:
        return Settings()
    except Exception as e:
        print(f"\n[RuleGraph] FATAL: Configuration error — {e}", file=sys.stderr)
        print("[RuleGraph] Check that all required environment variables are set.", file=sys.stderr)
        print("[RuleGraph] See .env.example for the full list of required variables.", file=sys.stderr)
        sys.exit(1)


settings = _load_settings()
