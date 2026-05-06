from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = True
    app_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    cohere_api_key: str = ""
    cohere_embed_model: str = "embed-multilingual-v3.0"

    azure_doc_intelligence_endpoint: str = ""
    azure_doc_intelligence_key: str = ""

    database_url: str = "postgresql://lexitor:lexitor@localhost:5432/lexitor"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    storage_backend: Literal["local", "azure_blob"] = "local"
    local_storage_path: str = "./data/uploads"
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "lexitor-documents"

    jwt_secret_key: str = "change-me-in-production"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    api_host: str = "0.0.0.0"  # noqa: S104
    api_port: int = 8000
    api_cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:8501", "http://localhost:3000"]
    )

    streamlit_server_port: int = 8501

    applicationinsights_connection_string: str = ""
    sentry_dsn: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
