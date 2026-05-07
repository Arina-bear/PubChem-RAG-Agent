from functools import lru_cache
import os
from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

ENV_PATH =  "./.env"
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file = ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )
    ollama_base_url: str = "http://localhost:11434"
    app_name: str = "PubChem Compound Explorer API"
    api_version: str = "0.1.0"
    environment: str = "development"
    base_llm_model: str = "gemma3:4b" 

    pubchem_rest_base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    pubchem_view_base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"

    request_timeout_seconds: float = 30.0
    llm_request_timeout_seconds: float = 120.0
    agent_run_timeout_seconds: float = 240.0
    max_retries: int = 2
    candidate_limit: int = 10
    query_rate_limit_per_second: int = 3
    heavy_query_concurrency: int = 1
    agent_max_steps: int = 10

    llm_default_provider: str = "gemini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1-mini"
    modal_glm_base_url: str = "https://api.us-west-2.modal.direct/v1"
    modal_glm_api_key: SecretStr | None = None
    modal_glm_model: str = "zai-org/GLM-5.1-FP8"
    modal_glm_disable_thinking: bool = True
    google_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3-flash-preview"
    # Free tier для gemini-3-flash-preview = 5 RPM, для gemma-4-31b-it / gemini-3.1-flash-lite-preview ≈ 15 RPM.
    # 13 даёт безопасный запас под 15-RPM лимит, при -3-flash-preview лучше переопределить в .env на 4.
    llm_rate_limit_gemini_rpm: int = 13

    langfuse_public_key: SecretStr | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str = "http://localhost:3000"

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
    load_dotenv(str(ENV_PATH))
   # env_key = os.environ.get("MODAL_GLM_API_KEY")
    print(f"\n--- [CRITICAL DEBUG] ---")
    print(f"Путь к .env: {ENV_PATH}")
   # print(f"Ключ в os.environ: {env_key[:5]}***" if env_key else "Ключ в os.environ: MISSING")
    #settings = Settings()

   # print(f"Ключ в Settings объекте: {settings.modal_glm_api_key is not None}")
    #print(f"------------------------\n")
    return Settings()
