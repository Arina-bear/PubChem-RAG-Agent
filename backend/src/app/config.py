from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
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

    request_timeout_seconds: float = 20.0
    llm_request_timeout_seconds: float = 90.0
    agent_run_timeout_seconds: float = 240.0
    max_retries: int = 3
    candidate_limit: int = 10
    query_rate_limit_per_second: int = 3
    heavy_query_concurrency: int = 1
    agent_max_steps: int = 6

    llm_default_provider: str = "modal_glm"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1-mini"
    modal_glm_base_url: str = "https://api.us-west-2.modal.direct/v1"
    modal_glm_api_key: SecretStr | None = None
    modal_glm_model: str = "zai-org/GLM-5.1-FP8"
    modal_glm_disable_thinking: bool = True

    langfuse_public_key: SecretStr | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"

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
