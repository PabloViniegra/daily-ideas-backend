import os
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for the application."""

    app_name: str = "Daily Projects API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")

    api_v1_str: str = "/api/v1"
    backend_cors_origins: List[str] = Field(
        default=["http://localhost:8000", "http://localhost:8001"],
        env="BACKEND_CORS_ORIGINS"
    )

    redis_url: str = Field(env="REDIS_URL")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    redis_retry_on_timeout: bool = Field(
        default=True, env="REDIS_RETRY_ON_TIMEOUT")

    deepseek_api_key: str = Field(env="DEEPSEEK_API_KEY")
    deepseek_api_url: str = Field(
        default="https://api.deepseek.com/v1/chat/completions",
        env="DEEPSEEK_API_URL"
    )
    deepseek_model: str = Field(default="deepseek-chat", env="DEEPSEEK_MODEL")
    deepseek_max_tokens: int = Field(default=2000, env="DEEPSEEK_MAX_TOKENS")
    deepseek_temperature: float = Field(
        default=0.8, env="DEEPSEEK_TEMPERATURE")
    deepseek_timeout: int = Field(default=30, env="DEEPSEEK_TIMEOUT")

    # Google AI Configuration
    google_api_key: str = Field(default="", env="GOOGLE_API_KEY")
    google_model: str = Field(default="gemini-1.5-flash", env="GOOGLE_MODEL")
    google_max_tokens: int = Field(default=2000, env="GOOGLE_MAX_TOKENS")
    google_temperature: float = Field(default=0.8, env="GOOGLE_TEMPERATURE")
    google_timeout: int = Field(default=30, env="GOOGLE_TIMEOUT")

    daily_projects_ttl: int = Field(
        default=86400 * 7, env="DAILY_PROJECTS_TTL")
    generation_lock_ttl: int = Field(default=300, env="GENERATION_LOCK_TTL")

    max_requests_per_minute: int = Field(
        default=60, env="MAX_REQUESTS_PER_MINUTE")

    @validator("redis_url")
    def validate_redis_url(cls, v):
        """Validate the Redis URL."""
        if not v:
            raise ValueError("REDIS_URL is required")
        return v

    @validator("deepseek_api_key")
    def validate_deepseek_key(cls, v):
        """Validate the DeepSeek API key."""
        if not v:
            raise ValueError("DEEPSEEK_API_KEY is required")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        """Check if we are in production."""
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        """Check if we are in development."""
        return self.environment.lower() == "development"


settings = Settings()
