from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PubChem Compound Explorer API"
    api_version: str = "0.1.0"
    environment: str = "development"

    pubchem_rest_base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    pubchem_view_base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"

    request_timeout_seconds: float = 15.0
    max_retries: int = 3
    candidate_limit: int = 10
    query_rate_limit_per_second: int = 3
    heavy_query_concurrency: int = 1

    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )

    frontend_public_api_base_url: str = Field(
        default="http://127.0.0.1:8000",
        validation_alias=AliasChoices("FRONTEND_PUBLIC_API_BASE_URL", "NEXT_PUBLIC_API_BASE_URL"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

