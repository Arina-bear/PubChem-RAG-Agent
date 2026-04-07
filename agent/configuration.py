from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI
    openai_api_key: str###
    openai_model: str = "gpt-4o"######
    openai_temperature: float = 0.0

    # MCP Server
    mcp_server_name: str = "pubchem-tools"
    mcp_transport: str = "stdio"

    #pubChemAPI
    pubchem_rest_base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    pubchem_view_base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"
    request_timeout_seconds: float = 15.0
    max_retries: int = 3
    candidate_limit: int = 10
    query_rate_limit_per_second: int = 3
    heavy_query_concurrency: int = 1

#веб интерфейс
  #  cors_origins: tuple[str, ...] = (
   #     "http://localhost:3000",
    #    "http://127.0.0.1:3000",
    #)

    #frontend_public_api_base_url: str = Field(
     #   default="http://127.0.0.1:8000",
      #  validation_alias=AliasChoices("FRONTEND_PUBLIC_API_BASE_URL", "NEXT_PUBLIC_API_BASE_URL"),
    #)

#Singletone
@lru_cache
def get_settings() -> Settings:
    """Возвращает единственный экземпляр настроек"""
    return Settings()

#глобальный объект
settings = get_settings()