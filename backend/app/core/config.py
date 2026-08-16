from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Query Engine"
    app_env: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    database_url: str = (
        "postgresql+asyncpg://ai_query_app:local_development_only@localhost:5432/"
        "ai_query_engine"
    )
    frontend_origin: AnyHttpUrl = AnyHttpUrl("http://localhost:5173")
    ipl_api_url: AnyHttpUrl | None = None
    ipl_api_key: SecretStr | None = None
    schema_cache_ttl_seconds: int = 900
    ai_provider: Literal["mock", "openai"] = "mock"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5.6-luna"
    query_max_rows: int = 100
    public_api_access_backend: Literal["local", "postgres"] = "local"
    public_api_keys_file: str = ".data/api_clients.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
